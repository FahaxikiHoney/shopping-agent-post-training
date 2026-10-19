# -*- coding: utf-8 -*-
"""
数据格式转换：trajectories_r1_compressed.jsonl → LLaMA-Factory SFT 格式

输出格式（ChatML with thinking）：
{
  "messages": [
    {"role": "user", "content": "用户问题"},
    {"role": "assistant", "content": "<think>\n...thinking...\n</think>\n\n...final_response..."}
  ]
}

用法：
    python3 sft_data/convert_to_chatml.py
    python3 sft_data/convert_to_chatml.py --no-thinking   # 不包含thinking，纯SFT
    python3 sft_data/convert_to_chatml.py --split         # 自动切分train/val
"""
from __future__ import annotations
import json, argparse, random
from pathlib import Path

INPUT  = Path(__file__).parent / "trajectories_r1_compressed.jsonl"
OUTPUT = Path(__file__).parent / "train_chatml.json"
OUTPUT_VAL = Path(__file__).parent / "val_chatml.json"


def convert_one(d: dict, include_thinking: bool = True) -> dict | None:
    """将单条轨迹转为 ChatML 格式"""
    user_query = d.get("user_query", "").strip()
    thinking   = d.get("thinking", "").strip()
    final_resp = d.get("final_response", "").strip()

    if not user_query or not final_resp:
        return None
    if len(final_resp) < 50:
        return None

    # 构造 assistant 内容
    if include_thinking and thinking and len(thinking) > 20:
        assistant_content = f"<think>\n{thinking}\n</think>\n\n{final_resp}"
    else:
        assistant_content = final_resp

    # 添加多轮对话历史（如有）
    messages = []
    for h in d.get("conversation_history", []):
        role = h.get("role", "")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_query})
    messages.append({"role": "assistant", "content": assistant_content})

    return {"messages": messages}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-thinking", action="store_true", help="不包含thinking字段")
    parser.add_argument("--split", action="store_true", help="切分train/val（9:1）")
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    include_thinking = not args.no_thinking

    # 读取输入
    records = []
    with open(INPUT, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            converted = convert_one(d, include_thinking)
            if converted:
                records.append(converted)

    print(f"转换完成：{len(records)} 条（丢弃 {sum(1 for _ in open(INPUT)) - len(records)} 条）")
    print(f"包含thinking：{include_thinking}")

    if args.split:
        random.seed(args.seed)
        random.shuffle(records)
        n_val = max(1, int(len(records) * args.val_ratio))
        val_records = records[:n_val]
        train_records = records[n_val:]

        with open(OUTPUT, "w", encoding="utf-8") as f:
            json.dump(train_records, f, ensure_ascii=False, indent=2)
        with open(OUTPUT_VAL, "w", encoding="utf-8") as f:
            json.dump(val_records, f, ensure_ascii=False, indent=2)

        print(f"train: {len(train_records)} 条 → {OUTPUT.name}")
        print(f"val:   {len(val_records)} 条 → {OUTPUT_VAL.name}")
    else:
        with open(OUTPUT, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"输出：{OUTPUT.name}（{len(records)} 条）")

    # 打印样例
    print("\n=== 样例 ===")
    sample = records[0]
    for msg in sample["messages"]:
        print(f"[{msg['role']}]")
        print(msg["content"][:200])
        print()


if __name__ == "__main__":
    main()
