# -*- coding: utf-8 -*-
"""
LoRA 微调脚本
框架：transformers + peft（不依赖 trl）
适用：Qwen2.5 系列，显存 ≥ 16GB（RTX 3090/4090）

运行：
    python training/train_lora.py

调参入口：底部 TrainConfig dataclass
"""

import json
import os
import math
import torch
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    get_cosine_schedule_with_warmup,
)
from peft import LoraConfig, get_peft_model, TaskType, PeftModel
from torch.cuda.amp import GradScaler, autocast


# ─────────────────────────────────────────────────────────────────────────────
# 超参配置（所有可调项集中在这里）
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class TrainConfig:
    # 模型路径（本地路径或 HuggingFace Hub ID）
    model_name: str = "Qwen/Qwen2.5-7B-Instruct"

    # 数据（ShareGPT 格式 JSON，来自 convert_to_llamafactory.py 输出）
    train_file: str = "sft_data/train_llamafactory.json"
    val_split: float = 0.05          # 从训练集中切 5% 作验证集

    # LoRA 参数
    lora_r: int = 16                 # rank：越大越强但越慢，16 是性价比最优起点
    lora_alpha: int = 32             # 缩放因子，通常 = 2*r
    lora_dropout: float = 0.05
    # 作用层：q/k/v/o + FFN 的 gate/up/down，覆盖全部注意力和前馈
    lora_target_modules: List[str] = None

    # 序列长度（超出截断，太短的样本被过滤）
    max_seq_len: int = 2048
    min_seq_len: int = 64

    # 训练超参
    num_epochs: int = 3
    batch_size: int = 2              # 单卡 batch
    grad_accum_steps: int = 8        # 等效 batch = 2*8 = 16
    learning_rate: float = 5e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    max_grad_norm: float = 1.0       # 梯度裁剪

    # 精度（RTX 3090/4090 支持 bf16；4060Ti 只支持 fp16）
    use_bf16: bool = False           # 改为 True 可在支持 bf16 的卡上使用
    use_fp16: bool = True

    # 梯度检查点（省 30-40% 显存，训练速度降约 20%）
    gradient_checkpointing: bool = True

    # 保存与日志
    output_dir: str = "training/output/lora"
    save_steps: int = 200
    eval_steps: int = 200
    logging_steps: int = 20

    def __post_init__(self):
        if self.lora_target_modules is None:
            # Qwen2.5 的线性层名称
            self.lora_target_modules = [
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj",
            ]


cfg = TrainConfig()


# ─────────────────────────────────────────────────────────────────────────────
# 数据集（ShareGPT 格式 → ChatML token ids + loss mask）
# ─────────────────────────────────────────────────────────────────────────────
class ShareGPTDataset(Dataset):
    """
    读取 convert_to_llamafactory.py 输出的 JSON 文件。

    每条数据格式：
        {"conversations": [
            {"from": "system",  "value": "你是购物助手..."},
            {"from": "human",   "value": "用户问题"},
            {"from": "gpt",     "value": "<think>...</think>\n\n最终回复"},
            {"from": "human",   "value": "<tool_response>...</tool_response>"},
            {"from": "gpt",     "value": "最终回复"},
        ]}

    Loss mask 策略：
        只对 "gpt"（assistant）轮的 token 计算 loss，
        "human"（user/tool）和 "system" 的 token 全部 mask 为 -100。
        这让模型学会"如何回复"，而不是学"用户会说什么"。
    """

    ROLE_MAP = {"system": "system", "human": "user", "gpt": "assistant"}

    def __init__(self, data: List[Dict], tokenizer, max_len: int, min_len: int):
        self.tokenizer = tokenizer
        self.max_len = max_len
        self.samples = []

        for item in data:
            convs = item.get("conversations", [])
            if not convs:
                continue
            # 转成 messages 格式
            messages = []
            for c in convs:
                role = self.ROLE_MAP.get(c["from"])
                if role:
                    messages.append({"role": role, "content": c["value"]})
            if not messages:
                continue

            # 用 apply_chat_template 把 messages 转为带特殊 token 的字符串
            try:
                full_text = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=False,
                )
            except Exception:
                continue

            input_ids = tokenizer.encode(full_text, add_special_tokens=False)
            if len(input_ids) < min_len or len(input_ids) > max_len:
                continue

            # 构造 loss mask：只对 assistant 轮 token 保留 label
            labels = self._make_labels(messages, input_ids)
            self.samples.append({
                "input_ids": input_ids[:max_len],
                "labels":    labels[:max_len],
            })

    def _make_labels(self, messages: List[Dict], input_ids: List[int]) -> List[int]:
        """
        逐轮确定哪些 token 属于 assistant，其余 mask 为 -100。

        做法：
          1. 把 messages 前缀逐轮拼起来 tokenize，获得每轮的起始位置。
          2. "assistant" 轮的 [start, end) 范围保留 label，其余置 -100。
        """
        labels = [-100] * len(input_ids)
        tokenizer = self.tokenizer

        # 逐步拼 prefix，找到每轮 assistant 内容的起始 token 位置
        for i, msg in enumerate(messages):
            if msg["role"] != "assistant":
                continue
            # prefix：不包含本轮的所有消息 + 本轮 header（不含内容）
            prefix_msgs = messages[:i]
            prefix_text = tokenizer.apply_chat_template(
                prefix_msgs,
                tokenize=False,
                add_generation_prompt=True,  # 加上 <|im_start|>assistant\n
            )
            prefix_ids = tokenizer.encode(prefix_text, add_special_tokens=False)
            start = len(prefix_ids)

            # 本轮完整内容（包含 <|im_end|>）
            full_prefix_text = tokenizer.apply_chat_template(
                messages[:i + 1],
                tokenize=False,
                add_generation_prompt=False,
            )
            full_prefix_ids = tokenizer.encode(full_prefix_text, add_special_tokens=False)
            end = len(full_prefix_ids)

            for j in range(start, min(end, len(labels))):
                labels[j] = input_ids[j]

        return labels

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]


def collate_fn(batch, pad_token_id: int, max_len: int) -> Dict[str, torch.Tensor]:
    """把 batch 内序列 pad 到相同长度"""
    max_batch_len = min(max(len(x["input_ids"]) for x in batch), max_len)

    input_ids_list, labels_list, attention_mask_list = [], [], []
    for x in batch:
        ids = x["input_ids"]
        lbls = x["labels"]
        pad_len = max_batch_len - len(ids)

        input_ids_list.append(ids + [pad_token_id] * pad_len)
        labels_list.append(lbls + [-100] * pad_len)
        attention_mask_list.append([1] * len(ids) + [0] * pad_len)

    return {
        "input_ids":      torch.tensor(input_ids_list, dtype=torch.long),
        "labels":         torch.tensor(labels_list,    dtype=torch.long),
        "attention_mask": torch.tensor(attention_mask_list, dtype=torch.long),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 主训练流程
# ─────────────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(cfg.output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"使用设备：{device}")

    # ── 1. Tokenizer ──────────────────────────────────────────────────────────
    print(f"加载 tokenizer：{cfg.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(
        cfg.model_name,
        trust_remote_code=True,
        padding_side="right",
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    pad_id = tokenizer.pad_token_id

    # ── 2. 加载数据 ────────────────────────────────────────────────────────────
    print(f"加载数据：{cfg.train_file}")
    with open(cfg.train_file, encoding="utf-8") as f:
        all_data = json.load(f)

    # 打乱后切分 train/val
    import random
    random.seed(42)
    random.shuffle(all_data)
    val_size = max(1, int(len(all_data) * cfg.val_split))
    train_data = all_data[val_size:]
    val_data   = all_data[:val_size]
    print(f"  训练集 {len(train_data)} 条 | 验证集 {len(val_data)} 条")

    train_dataset = ShareGPTDataset(train_data, tokenizer, cfg.max_seq_len, cfg.min_seq_len)
    val_dataset   = ShareGPTDataset(val_data,   tokenizer, cfg.max_seq_len, cfg.min_seq_len)
    print(f"  有效样本 train={len(train_dataset)} val={len(val_dataset)}")

    _collate = lambda batch: collate_fn(batch, pad_id, cfg.max_seq_len)
    train_loader = DataLoader(train_dataset, batch_size=cfg.batch_size, shuffle=True,
                              collate_fn=_collate, num_workers=0, pin_memory=True)
    val_loader   = DataLoader(val_dataset,   batch_size=cfg.batch_size, shuffle=False,
                              collate_fn=_collate, num_workers=0)

    # ── 3. 加载底座模型 ────────────────────────────────────────────────────────
    print(f"加载模型：{cfg.model_name}")
    dtype = torch.bfloat16 if cfg.use_bf16 else torch.float16
    model = AutoModelForCausalLM.from_pretrained(
        cfg.model_name,
        torch_dtype=dtype,
        device_map="auto",
        trust_remote_code=True,
    )

    if cfg.gradient_checkpointing:
        model.enable_input_require_grads()
        model.gradient_checkpointing_enable()

    # ── 4. 注入 LoRA ──────────────────────────────────────────────────────────
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=cfg.lora_r,
        lora_alpha=cfg.lora_alpha,
        lora_dropout=cfg.lora_dropout,
        target_modules=cfg.lora_target_modules,
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # ── 5. 优化器 & Scheduler ──────────────────────────────────────────────────
    # 只对 LoRA 参数（requires_grad=True）应用 weight_decay
    decay_params    = [p for n, p in model.named_parameters() if p.requires_grad and "bias" not in n]
    no_decay_params = [p for n, p in model.named_parameters() if p.requires_grad and "bias" in n]
    optimizer = torch.optim.AdamW(
        [{"params": decay_params, "weight_decay": cfg.weight_decay},
         {"params": no_decay_params, "weight_decay": 0.0}],
        lr=cfg.learning_rate,
    )

    total_steps   = math.ceil(len(train_loader) / cfg.grad_accum_steps) * cfg.num_epochs
    warmup_steps  = int(total_steps * cfg.warmup_ratio)
    scheduler = get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    scaler = GradScaler(enabled=cfg.use_fp16 and not cfg.use_bf16)

    # ── 6. 训练循环 ────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"LoRA rank={cfg.lora_r}  alpha={cfg.lora_alpha}")
    print(f"等效 batch={cfg.batch_size * cfg.grad_accum_steps}  lr={cfg.learning_rate}")
    print(f"总步数={total_steps}  warmup={warmup_steps}")
    print(f"输出目录：{cfg.output_dir}")
    print(f"{'='*60}\n")

    global_step = 0
    best_val_loss = float("inf")

    for epoch in range(cfg.num_epochs):
        model.train()
        optimizer.zero_grad()
        accum_loss = 0.0

        for step, batch in enumerate(train_loader):
            input_ids      = batch["input_ids"].to(device)
            labels         = batch["labels"].to(device)
            attention_mask = batch["attention_mask"].to(device)

            amp_dtype = torch.bfloat16 if cfg.use_bf16 else torch.float16
            with autocast(dtype=amp_dtype, enabled=cfg.use_fp16 or cfg.use_bf16):
                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels,
                )
                loss = outputs.loss / cfg.grad_accum_steps

            scaler.scale(loss).backward()
            accum_loss += loss.item()

            # 梯度累积满足后更新
            if (step + 1) % cfg.grad_accum_steps == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad],
                    cfg.max_grad_norm,
                )
                scaler.step(optimizer)
                scaler.update()
                scheduler.step()
                optimizer.zero_grad()

                global_step += 1

                # 日志
                if global_step % cfg.logging_steps == 0:
                    lr_now = scheduler.get_last_lr()[0]
                    print(f"  epoch={epoch+1}  step={global_step}/{total_steps}"
                          f"  loss={accum_loss:.4f}  lr={lr_now:.2e}")
                    accum_loss = 0.0

                # 评估
                if global_step % cfg.eval_steps == 0:
                    val_loss = evaluate(model, val_loader, device, cfg)
                    print(f"  >>> eval_loss={val_loss:.4f}")
                    model.train()

                    if val_loss < best_val_loss:
                        best_val_loss = val_loss
                        save_path = os.path.join(cfg.output_dir, "best")
                        model.save_pretrained(save_path)
                        tokenizer.save_pretrained(save_path)
                        print(f"  >>> 保存最佳模型 → {save_path}  (val_loss={best_val_loss:.4f})")

                # 定期保存 checkpoint
                if global_step % cfg.save_steps == 0:
                    ckpt_path = os.path.join(cfg.output_dir, f"step-{global_step}")
                    model.save_pretrained(ckpt_path)
                    tokenizer.save_pretrained(ckpt_path)
                    print(f"  >>> checkpoint → {ckpt_path}")

        print(f"epoch {epoch+1} 完成")

    # ── 7. 保存最终 LoRA adapter ───────────────────────────────────────────────
    final_path = os.path.join(cfg.output_dir, "final")
    model.save_pretrained(final_path)
    tokenizer.save_pretrained(final_path)
    print(f"\n训练完成！LoRA adapter 保存到：{final_path}")
    print("推理时用：PeftModel.from_pretrained(base_model, adapter_path)")
    print("合并时用：model.merge_and_unload() 再 save_pretrained()")


def evaluate(model, val_loader, device, cfg) -> float:
    model.eval()
    total_loss = 0.0
    total_batches = 0
    amp_dtype = torch.bfloat16 if cfg.use_bf16 else torch.float16

    with torch.no_grad():
        for batch in val_loader:
            input_ids      = batch["input_ids"].to(device)
            labels         = batch["labels"].to(device)
            attention_mask = batch["attention_mask"].to(device)

            with autocast(dtype=amp_dtype, enabled=cfg.use_fp16 or cfg.use_bf16):
                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels,
                )
            total_loss += outputs.loss.item()
            total_batches += 1

    return total_loss / max(total_batches, 1)


if __name__ == "__main__":
    main()
