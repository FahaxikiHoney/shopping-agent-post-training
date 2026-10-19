# -*- coding: utf-8 -*-
"""
全参数 SFT 微调脚本
框架：transformers（不依赖 trl/peft）
适用：Qwen2.5-7B，显存 ≥ 40GB（A100/H100）；小模型（0.5B/1.5B）显存 ≥ 16GB

与 LoRA 版的核心区别：
  - 所有参数都参与更新，不冻结任何层
  - 学习率要比 LoRA 低 10x（防止大幅破坏预训练权重）
  - 显存占用 ≈ 参数量 × 16bytes（fp16 参数 + 梯度 + AdamW 两个动量）
  - 效果上限更高，但对数据质量要求也更高

显存估算：
  Qwen2.5-0.5B → 约 8GB  （16GB 卡可用）
  Qwen2.5-1.5B → 约 24GB （40GB 卡可用）
  Qwen2.5-7B   → 约 80GB （A100 80GB 或多卡）
  Qwen2.5-7B + gradient_checkpointing → 约 56GB

运行（单卡）：
    python training/train_full.py

运行（多卡 DDP）：
    torchrun --nproc_per_node=4 training/train_full.py
"""

import json
import os
import math
import torch
import torch.distributed as dist
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from torch.utils.data import Dataset, DataLoader, DistributedSampler
from torch.nn.parallel import DistributedDataParallel as DDP
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    get_cosine_schedule_with_warmup,
)
from torch.cuda.amp import GradScaler, autocast


# ─────────────────────────────────────────────────────────────────────────────
# 超参配置
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class TrainConfig:
    # 模型（全参数微调推荐小模型，或者有足够显存）
    model_name: str = "Qwen/Qwen2.5-7B-Instruct"

    # 数据
    train_file: str = "sft_data/train_llamafactory.json"
    val_split: float = 0.05

    # 序列长度
    max_seq_len: int = 2048
    min_seq_len: int = 64

    # 训练超参
    # 【关键】全参数微调的 lr 要比 LoRA 低约 10 倍，防止过拟合和遗忘预训练知识
    num_epochs: int = 3
    batch_size: int = 1              # 全参显存更大，batch 通常更小
    grad_accum_steps: int = 16       # 等效 batch = 1*16 = 16
    learning_rate: float = 5e-6     # 全参微调的典型值：1e-6 ~ 1e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.05      # 全参微调 warmup 比例可以短一点
    max_grad_norm: float = 1.0

    # 精度
    use_bf16: bool = False
    use_fp16: bool = True

    # 梯度检查点（全参数微调强烈建议开启，省显存约 40%）
    gradient_checkpointing: bool = True

    # DeepSpeed ZeRO（多卡场景，需要 pip install deepspeed）
    # 单卡时忽略
    use_deepspeed: bool = False

    # 保存与日志
    output_dir: str = "training/output/full"
    save_steps: int = 200
    eval_steps: int = 200
    logging_steps: int = 10

    # 是否冻结 embedding 层（全参数微调时，embedding 冻结可以节省一些显存和防遗忘）
    freeze_embeddings: bool = True


cfg = TrainConfig()


# ─────────────────────────────────────────────────────────────────────────────
# 数据集（与 LoRA 版完全相同）
# ─────────────────────────────────────────────────────────────────────────────
class ShareGPTDataset(Dataset):
    """
    ShareGPT 格式 → token ids + loss mask

    Loss mask：只对 assistant（gpt）轮计算 loss，
    system/human/tool_response 全部 mask 为 -100。
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
            messages = []
            for c in convs:
                role = self.ROLE_MAP.get(c["from"])
                if role:
                    messages.append({"role": role, "content": c["value"]})
            if not messages:
                continue

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

            labels = self._make_labels(messages, input_ids)
            self.samples.append({
                "input_ids": input_ids[:max_len],
                "labels":    labels[:max_len],
            })

    def _make_labels(self, messages: List[Dict], input_ids: List[int]) -> List[int]:
        labels = [-100] * len(input_ids)
        tokenizer = self.tokenizer

        for i, msg in enumerate(messages):
            if msg["role"] != "assistant":
                continue
            prefix_text = tokenizer.apply_chat_template(
                messages[:i],
                tokenize=False,
                add_generation_prompt=True,
            )
            prefix_ids = tokenizer.encode(prefix_text, add_special_tokens=False)
            start = len(prefix_ids)

            full_text = tokenizer.apply_chat_template(
                messages[:i + 1],
                tokenize=False,
                add_generation_prompt=False,
            )
            full_ids = tokenizer.encode(full_text, add_special_tokens=False)
            end = len(full_ids)

            for j in range(start, min(end, len(labels))):
                labels[j] = input_ids[j]

        return labels

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]


def collate_fn(batch, pad_token_id: int, max_len: int) -> Dict[str, torch.Tensor]:
    max_batch_len = min(max(len(x["input_ids"]) for x in batch), max_len)
    input_ids_list, labels_list, attention_mask_list = [], [], []

    for x in batch:
        ids  = x["input_ids"]
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
# DDP 工具函数
# ─────────────────────────────────────────────────────────────────────────────
def setup_ddp():
    """初始化 DDP（多卡时由 torchrun 自动传入环境变量）"""
    dist.init_process_group(backend="nccl")
    local_rank = int(os.environ.get("LOCAL_RANK", 0))
    torch.cuda.set_device(local_rank)
    return local_rank


def is_main_process() -> bool:
    if not dist.is_available() or not dist.is_initialized():
        return True
    return dist.get_rank() == 0


def cleanup_ddp():
    if dist.is_available() and dist.is_initialized():
        dist.destroy_process_group()


# ─────────────────────────────────────────────────────────────────────────────
# 主训练流程
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # 判断是否多卡 DDP
    use_ddp = int(os.environ.get("WORLD_SIZE", 1)) > 1
    if use_ddp:
        local_rank = setup_ddp()
        device = torch.device(f"cuda:{local_rank}")
    else:
        local_rank = 0
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if is_main_process():
        os.makedirs(cfg.output_dir, exist_ok=True)
        print(f"使用设备：{device}  {'(DDP 多卡)' if use_ddp else '(单卡)'}")

    # ── 1. Tokenizer ──────────────────────────────────────────────────────────
    if is_main_process():
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
    if is_main_process():
        print(f"加载数据：{cfg.train_file}")
    with open(cfg.train_file, encoding="utf-8") as f:
        all_data = json.load(f)

    import random
    random.seed(42)
    random.shuffle(all_data)
    val_size   = max(1, int(len(all_data) * cfg.val_split))
    train_data = all_data[val_size:]
    val_data   = all_data[:val_size]

    train_dataset = ShareGPTDataset(train_data, tokenizer, cfg.max_seq_len, cfg.min_seq_len)
    val_dataset   = ShareGPTDataset(val_data,   tokenizer, cfg.max_seq_len, cfg.min_seq_len)

    if is_main_process():
        print(f"  有效样本 train={len(train_dataset)} val={len(val_dataset)}")

    _collate = lambda batch: collate_fn(batch, pad_id, cfg.max_seq_len)

    if use_ddp:
        train_sampler = DistributedSampler(train_dataset, shuffle=True)
        train_loader = DataLoader(train_dataset, batch_size=cfg.batch_size,
                                  sampler=train_sampler, collate_fn=_collate,
                                  num_workers=0, pin_memory=True)
    else:
        train_loader = DataLoader(train_dataset, batch_size=cfg.batch_size,
                                  shuffle=True, collate_fn=_collate,
                                  num_workers=0, pin_memory=True)

    val_loader = DataLoader(val_dataset, batch_size=cfg.batch_size, shuffle=False,
                            collate_fn=_collate, num_workers=0)

    # ── 3. 加载模型（全参数，不注入 LoRA）──────────────────────────────────────
    if is_main_process():
        print(f"加载模型：{cfg.model_name}（全参数微调）")
    dtype = torch.bfloat16 if cfg.use_bf16 else torch.float16
    model = AutoModelForCausalLM.from_pretrained(
        cfg.model_name,
        torch_dtype=dtype,
        trust_remote_code=True,
    )
    model = model.to(device)

    # 可选：冻结 embedding 层，防止遗忘 token 语义，也省一些显存
    if cfg.freeze_embeddings:
        for name, param in model.named_parameters():
            if "embed_tokens" in name or "lm_head" in name:
                param.requires_grad = False

    if cfg.gradient_checkpointing:
        model.gradient_checkpointing_enable()

    # 打印可训练参数量
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total     = sum(p.numel() for p in model.parameters())
    if is_main_process():
        print(f"可训练参数：{trainable:,} / {total:,}  ({100*trainable/total:.1f}%)")

    # 多卡 DDP 包装
    if use_ddp:
        model = DDP(model, device_ids=[local_rank], find_unused_parameters=False)

    raw_model = model.module if use_ddp else model

    # ── 4. 优化器 & Scheduler ──────────────────────────────────────────────────
    # 全参微调的 weight_decay 只作用于非 bias 和非 norm 参数
    no_decay_names = ("bias", "layernorm", "layer_norm", "norm")
    decay_params    = [p for n, p in model.named_parameters()
                       if p.requires_grad and not any(nd in n.lower() for nd in no_decay_names)]
    no_decay_params = [p for n, p in model.named_parameters()
                       if p.requires_grad and any(nd in n.lower() for nd in no_decay_names)]

    optimizer = torch.optim.AdamW(
        [{"params": decay_params,    "weight_decay": cfg.weight_decay},
         {"params": no_decay_params, "weight_decay": 0.0}],
        lr=cfg.learning_rate,
        eps=1e-8,
        betas=(0.9, 0.999),
    )

    total_steps   = math.ceil(len(train_loader) / cfg.grad_accum_steps) * cfg.num_epochs
    warmup_steps  = int(total_steps * cfg.warmup_ratio)
    scheduler = get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    scaler = GradScaler(enabled=cfg.use_fp16 and not cfg.use_bf16)

    # ── 5. 训练循环 ────────────────────────────────────────────────────────────
    if is_main_process():
        print(f"\n{'='*60}")
        print(f"全参数微调  lr={cfg.learning_rate}  冻结embedding={cfg.freeze_embeddings}")
        print(f"等效 batch={cfg.batch_size * cfg.grad_accum_steps}  总步数={total_steps}")
        print(f"输出目录：{cfg.output_dir}")
        print(f"{'='*60}\n")

    global_step = 0
    best_val_loss = float("inf")

    for epoch in range(cfg.num_epochs):
        if use_ddp:
            train_loader.sampler.set_epoch(epoch)

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

                if is_main_process() and global_step % cfg.logging_steps == 0:
                    lr_now = scheduler.get_last_lr()[0]
                    print(f"  epoch={epoch+1}  step={global_step}/{total_steps}"
                          f"  loss={accum_loss:.4f}  lr={lr_now:.2e}")
                    accum_loss = 0.0

                if is_main_process() and global_step % cfg.eval_steps == 0:
                    val_loss = evaluate(model, val_loader, device, cfg)
                    print(f"  >>> eval_loss={val_loss:.4f}")
                    model.train()

                    if val_loss < best_val_loss:
                        best_val_loss = val_loss
                        save_path = os.path.join(cfg.output_dir, "best")
                        raw_model.save_pretrained(save_path)
                        tokenizer.save_pretrained(save_path)
                        print(f"  >>> 保存最佳模型 → {save_path}  (val_loss={best_val_loss:.4f})")

                if is_main_process() and global_step % cfg.save_steps == 0:
                    ckpt_path = os.path.join(cfg.output_dir, f"step-{global_step}")
                    raw_model.save_pretrained(ckpt_path)
                    tokenizer.save_pretrained(ckpt_path)
                    print(f"  >>> checkpoint → {ckpt_path}")

        if is_main_process():
            print(f"epoch {epoch+1} 完成")

    # ── 6. 保存最终完整模型 ────────────────────────────────────────────────────
    if is_main_process():
        final_path = os.path.join(cfg.output_dir, "final")
        raw_model.save_pretrained(final_path)
        tokenizer.save_pretrained(final_path)
        print(f"\n训练完成！完整模型保存到：{final_path}")
        print("推理时直接 AutoModelForCausalLM.from_pretrained(final_path)")

    cleanup_ddp()


def evaluate(model, val_loader, device, cfg) -> float:
    model.eval()
    total_loss, total_batches = 0.0, 0
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
