# -*- coding: utf-8 -*-
"""
Agent SFT 训练脚本（教学版）
模型：Qwen3.5-0.8B（或任何 Qwen 系列）
框架：trl + transformers + peft
数据：shopping 购物 Agent 轨迹（含 <think> 思维链）

核心设计决策说明见各注释块。
"""

import torch
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer, SFTConfig, DataCollatorForCompletionOnlyLM


# ─────────────────────────────────────────────────────────────────────────────
# 1. 超参配置
#
# 把所有可调参数集中在一个地方，方便实验对比。
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class TrainConfig:
    # 模型
    model_name: str = "Qwen/Qwen3.5-0.8B"  # 或本地路径

    # 数据
    train_file: str = "../sft_data/train_chatml_v3.json"
    val_file:   str = "../sft_data/val_chatml_v3.json"

    # LoRA 参数
    # rank(r) 越大，可训练参数越多，但显存占用也越多。
    # 对于垂域 SFT，r=16 是性价比最高的起点。
    lora_r: int = 16
    lora_alpha: int = 32      # alpha/r = 2，经验上较好的缩放比
    lora_dropout: float = 0.05

    # 训练超参
    max_seq_length: int = 2048       # 覆盖绝大多数样本
    batch_size: int = 2              # 4060Ti 16GB 下安全值
    grad_accum: int = 8              # 等效 batch_size = 2*8 = 16
    learning_rate: float = 5e-5      # SFT 常用范围 1e-5 ~ 1e-4
    num_epochs: int = 3
    warmup_ratio: float = 0.1

    # 输出
    output_dir: str = "./output/qwen3.5-0.8b-shopping"


cfg = TrainConfig()


# ─────────────────────────────────────────────────────────────────────────────
# 2. 加载 Tokenizer
# ─────────────────────────────────────────────────────────────────────────────
tokenizer = AutoTokenizer.from_pretrained(
    cfg.model_name,
    trust_remote_code=True,
    padding_side="right",   # 训练时 pad 在右侧，和 causal LM 方向一致
)
# Qwen 系列的 pad_token 默认未设置，用 eos_token 代替
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token


# ─────────────────────────────────────────────────────────────────────────────
# 3. 加载模型
#
# 【设计决策】用不用 4-bit 量化加载（QLoRA）？
#
# 不量化（full fp16 LoRA）：
#   - 显存：0.8B × 2bytes = ~1.6GB 参数 + LoRA梯度 ~2GB = 共约 4-5GB
#   - 训练速度更快，精度更高
#   - 4060Ti 16GB 完全够用，推荐这种方式
#
# 4-bit 量化（QLoRA）：
#   - 显存更省（约减半），适合显存更小的卡（8GB以下）
#   - 速度更慢，精度略低
#   - 如果显存不够再考虑，这里先不用
# ─────────────────────────────────────────────────────────────────────────────
model = AutoModelForCausalLM.from_pretrained(
    cfg.model_name,
    torch_dtype=torch.float16,    # 4060Ti 不支持 bf16，用 fp16
    device_map="auto",            # 自动放到 GPU
    trust_remote_code=True,
)
model.enable_input_require_grads()  # 开启梯度检查点需要这个


# ─────────────────────────────────────────────────────────────────────────────
# 4. 配置 LoRA
#
# 【核心概念】LoRA 在原始权重旁边加了两个小矩阵 A 和 B（参数量约原来的 0.1%），
# 训练时只更新这两个矩阵，原始权重冻结。
#
# 【target_modules 选择】
# "all-linear" = 所有线性层都加 LoRA（推荐，效果最全面）
# 也可以只选 ["q_proj", "v_proj"]（更省显存，但效果略差）
#
# 【task_type = CAUSAL_LM】
# 因为我们在做语言模型微调（输入→输出），不是分类任务。
# ─────────────────────────────────────────────────────────────────────────────
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=cfg.lora_r,
    lora_alpha=cfg.lora_alpha,
    lora_dropout=cfg.lora_dropout,
    target_modules="all-linear",
    bias="none",              # 不训练 bias，节省显存
)
model = get_peft_model(model, lora_config)

# 打印可训练参数量（对比感受 LoRA 的参数效率）
model.print_trainable_parameters()
# 预期输出类似：trainable params: 3,407,872 || all params: 830,175,232 || trainable%: 0.41%


# ─────────────────────────────────────────────────────────────────────────────
# 5. 加载数据集
# ─────────────────────────────────────────────────────────────────────────────
dataset = load_dataset(
    "json",
    data_files={
        "train": cfg.train_file,
        "validation": cfg.val_file,
    }
)
# dataset["train"][0] 的结构：{"messages": [{"role": "user", ...}, {"role": "assistant", ...}]}


# ─────────────────────────────────────────────────────────────────────────────
# 6. 数据格式化函数
#
# 【关键决策】把 messages 列表转成 Qwen 的 ChatML 格式字符串：
#
#   <|im_start|>user
#   用户问题<|im_end|>
#   <|im_start|>assistant
#   <think>
#   ...thinking...
#   </think>
#
#   ...final_response...<|im_end|>
#
# tokenizer.apply_chat_template 会自动处理这个格式。
# ─────────────────────────────────────────────────────────────────────────────
def format_messages(example):
    """将 messages 列表转换为模型输入字符串"""
    text = tokenizer.apply_chat_template(
        example["messages"],
        tokenize=False,           # 先不 tokenize，返回字符串
        add_generation_prompt=False,  # 训练时不加 generation prompt
    )
    return {"text": text}

dataset = dataset.map(format_messages, batched=False)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Loss Mask 策略（Agent SFT 最关键的设计决策）
#
# 问题：对 user 的输入和 assistant 的输出，都应该计算 loss 吗？
#
# 方案A：只对 assistant 部分计算 loss（Completion-Only）← 本脚本采用
#   - 逻辑：我们希望模型学会"生成正确的回复"，不需要学"预测用户会说什么"
#   - 工具：DataCollatorForCompletionOnlyLM，只对 assistant token 的 loss 保留
#   - 效果：更稳定，避免模型学习 user 说话风格干扰
#
# 方案B：对完整序列（user + assistant）都计算 loss
#   - 逻辑：让模型学习整个对话分布
#   - 效果：通常不如方案A，user 部分的 loss 会引入噪声
#
# 方案C：只对 <think> 之后的 final_response 计算 loss（不对 thinking 计算）
#   - 逻辑：thinking 是辅助，不是目标输出
#   - 问题：模型可能学不会生成 <think>，推理时不会思考
#   - oxygen-jingyan-1.0 的做法：对压缩后的完整 thinking+response 都计算 loss
#     ← 即方案A（对整个 assistant 部分计算），这也是我们的做法
#
# 【本脚本结论】用方案A：assistant 部分（包括 thinking 和 response）都计算 loss
# ─────────────────────────────────────────────────────────────────────────────

# Qwen ChatML 格式中，assistant 的回复以 "<|im_start|>assistant\n" 开头
# DataCollatorForCompletionOnlyLM 会找到这个标记，只对之后的 token 计算 loss
response_template = "<|im_start|>assistant\n"
response_template_ids = tokenizer.encode(response_template, add_special_tokens=False)

collator = DataCollatorForCompletionOnlyLM(
    response_template=response_template_ids,
    tokenizer=tokenizer,
)


# ─────────────────────────────────────────────────────────────────────────────
# 8. 训练参数配置
# ─────────────────────────────────────────────────────────────────────────────
training_args = SFTConfig(
    output_dir=cfg.output_dir,

    # 训练轮数与步数
    num_train_epochs=cfg.num_epochs,

    # Batch size
    # 等效 batch_size = per_device × grad_accum = 2 × 8 = 16
    per_device_train_batch_size=cfg.batch_size,
    per_device_eval_batch_size=cfg.batch_size,
    gradient_accumulation_steps=cfg.grad_accum,

    # 优化器
    learning_rate=cfg.learning_rate,
    lr_scheduler_type="cosine",   # cosine 比 linear 在末尾衰减更平滑
    warmup_ratio=cfg.warmup_ratio,
    optim="adamw_torch",

    # 精度（4060Ti 不支持 bf16）
    fp16=True,
    bf16=False,

    # 梯度检查点：用时间换显存，训练速度略慢但省约 30-40% 显存
    gradient_checkpointing=True,

    # 评估与保存
    eval_strategy="steps",
    eval_steps=100,
    save_strategy="steps",
    save_steps=200,
    save_total_limit=3,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",

    # 日志
    logging_steps=20,
    report_to="none",   # 不上传 wandb，改成 "wandb" 可启用

    # SFT 专属
    max_seq_length=cfg.max_seq_length,
    dataset_text_field="text",          # 使用我们在 step 6 生成的 "text" 字段
    packing=False,                      # 不打包多个样本（Agent 数据长度差异大，不适合 packing）
)


# ─────────────────────────────────────────────────────────────────────────────
# 9. 初始化 SFTTrainer 并开始训练
# ─────────────────────────────────────────────────────────────────────────────
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["validation"],
    data_collator=collator,    # 应用 Loss Mask（只对 assistant 部分计算）
)

# 打印训练信息
print(f"\n{'='*50}")
print(f"模型：{cfg.model_name}")
print(f"训练集：{len(dataset['train'])} 条")
print(f"验证集：{len(dataset['validation'])} 条")
print(f"等效 batch_size：{cfg.batch_size * cfg.grad_accum}")
print(f"最大序列长度：{cfg.max_seq_length}")
print(f"LoRA rank：{cfg.lora_r}")
print(f"输出目录：{cfg.output_dir}")
print(f"{'='*50}\n")

trainer.train()


# ─────────────────────────────────────────────────────────────────────────────
# 10. 保存最终模型（LoRA adapter）
#
# 注意：这里保存的是 LoRA adapter，不是完整模型。
# 推理时需要同时加载原始模型 + adapter。
# 如果要部署，需要用 merge_and_unload() 合并权重。
# ─────────────────────────────────────────────────────────────────────────────
trainer.save_model(cfg.output_dir)
tokenizer.save_pretrained(cfg.output_dir)
print(f"\n训练完成！模型已保存到：{cfg.output_dir}")


# ─────────────────────────────────────────────────────────────────────────────
# 11. 快速推理验证（训练后测试）
# ─────────────────────────────────────────────────────────────────────────────
def inference_test(question: str):
    """用训练好的模型做一次推理"""
    messages = [{"role": "user", "content": question}]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,   # 推理时加上，告诉模型开始回答
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )

    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=False)
    print(f"\n用户：{question}")
    print(f"模型：{response}")

# 测试
inference_test("买的保温杯只保温5小时，换24小时保温的同价位款")
