# LoRA SFT 配置

本目录包含 `lora_sft.yaml` 和 `dataset_info.json` 的说明副本。LLaMA-Factory 实际读取 `dataset_dir` 下的 `dataset_info.json`，因此活动注册文件位于 `sft_data/dataset_info.json`。

从仓库根目录安装本地 fork 并启动：

```bash
cd LLaMA-Factory
pip install -e ".[torch,metrics]"
cd ..
llamafactory-cli train training/lora_sft.yaml
```

默认数据为 `sft_data/train_chatml_v3.json` 与 `sft_data/val_chatml_v3.json`。按硬件调整基座模型、精度和 batch 参数，基座模型权重需自行准备。完整步骤见 `docs/03-sft-lora.md`。
