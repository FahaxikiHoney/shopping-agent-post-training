# -*- coding: utf-8 -*-
"""
数据格式转换 v2：包含完整工具调用链路
trajectories_r1_compressed.jsonl → ChatML with tool_call

正确的 Agent SFT 格式：

<|im_start|>user
用户问题<|im_end|>
<|im_start|>assistant
<think>
...thinking（决策思路）...
</think>

<tool_call>
{"name": "SkuRecallShopping", "arguments": {"query": "保温杯 24h", "max_price": 250}}
</tool_call>
<tool_response>
{"products": [{"product_id": "mock_xxx", "title": "膳魔师", "price": 199, ...}]}
</tool_response>

膳魔师经典系列保温杯推荐给您...<|im_end|>

这样模型才能学会：
1. 遇到问题 → 先思考（<think>）
2. 思考后决定调用什么工具、传什么参数（<tool_call>）
3. 看到工具返回结果（<tool_response>）
4. 基于结果生成最终回复
"""
from __future__ import annotations
import json, argparse, random
from pathlib import Path

INPUT  = Path(__file__).parent / "trajectories_r1_compressed.jsonl"
OUTPUT = Path(__file__).parent / "train_chatml_v2.json"
OUTPUT_VAL = Path(__file__).parent / "val_chatml_v2.json"


def format_tool_call(tool_name: str, tool_input: dict) -> str:
    """格式化工具调用块"""
    return f"<tool_call>\n{json.dumps({'name': tool_name, 'arguments': tool_input}, ensure_ascii=False)}\n</tool_call>"


def format_tool_response(tool_output: dict) -> str:
    """格式化工具返回块（只保留关键字段，避免过长）"""
    # 只保留 products 的核心字段，节省 token
    products = tool_output.get("products", [])
    slim_products = [
        {
            "product_id": p.get("product_id", ""),
            "title": p.get("title", ""),
            "price": p.get("price", 0),
            "rating": p.get("rating", 0),
            "key_specs": p.get("key_specs", ""),
            "sales": p.get("sales", ""),
        }
        for p in products[:5]  # 最多保留5个，避免超长
    ]
    output_slim = {"status": tool_output.get("status", "SUCCESS"), "products": slim_products}
    return f"<tool_response>\n{json.dumps(output_slim, ensure_ascii=False)}\n</tool_response>"


def convert_one(d: dict, include_thinking: bool = True) -> dict | None:
    """
    将单条轨迹转为包含工具调用的 ChatML 格式。

    assistant 的回复结构：
    [thinking] → [tool_call × N] → [tool_response × N] → [final_response]
    """
    user_query  = d.get("user_query", "").strip()
    thinking    = d.get("thinking", "").strip()
    final_resp  = d.get("final_response", "").strip()
    steps       = d.get("steps", [])

    if not user_query or not final_resp or len(final_resp) < 50:
        return None

    # ── 构建 assistant 内容 ──────────────────────────────────────
    parts = []

    # 1. thinking 块
    if include_thinking and thinking and len(thinking) > 20:
        parts.append(f"<think>\n{thinking}\n</think>")

    # 2. 工具调用链路（可能有多次调用，如 bundle_purchase）
    tool_steps = [s for s in steps if s.get("step_type") == "tool_call"]
    for step in tool_steps:
        tool_name  = step.get("tool_name", "")
        tool_input = step.get("tool_input", {})
        tool_output = step.get("tool_output", {})

        if tool_name and tool_input is not None:
            parts.append(format_tool_call(tool_name, tool_input))

        if tool_output:
            parts.append(format_tool_response(tool_output))

    # 3. 最终回复
    parts.append(final_resp)

    assistant_content = "\n\n".join(parts)

    # ── 构建完整 messages ────────────────────────────────────────
    messages = []

    # 多轮历史（如有）
    for h in d.get("conversation_history", []):
        role    = h.get("role", "")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user",      "content": user_query})
    messages.append({"role": "assistant", "content": assistant_content})

    return {
        "messages": messages,
        # 保留元信息（训练时不用，但便于调试）
        "_scenario": d.get("scenario_type", ""),
        "_trajectory_id": d.get("trajectory_id", ""),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-thinking", action="store_true")
    parser.add_argument("--split",       action="store_true", help="切分 train/val（9:1）")
    parser.add_argument("--val-ratio",   type=float, default=0.1)
    parser.add_argument("--seed",        type=int,   default=42)
    args = parser.parse_args()

    include_thinking = not args.no_thinking

    records = []
    skip = 0
    with open(INPUT, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            converted = convert_one(d, include_thinking)
            if converted:
                records.append(converted)
            else:
                skip += 1

    print(f"转换完成：{len(records)} 条（跳过 {skip} 条）")
    print(f"包含thinking：{include_thinking}")
    print(f"包含tool_call：True（完整工具调用链路）")

    # 统计工具调用分布
    from collections import Counter
    tool_counts = Counter()
    for r in records:
        for msg in r["messages"]:
            if msg["role"] == "assistant":
                tool_counts["has_tool"] += msg["content"].count("<tool_call>")
    print(f"工具调用总次数：{tool_counts['has_tool']}")

    if args.split:
        random.seed(args.seed)
        random.shuffle(records)
        n_val = max(1, int(len(records) * args.val_ratio))
        val_records   = records[:n_val]
        train_records = records[n_val:]

        with open(OUTPUT,     "w", encoding="utf-8") as f:
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
    print("\n=== 样例（含完整工具调用）===")
    sample = records[0]
    for msg in sample["messages"]:
        print(f"\n[{msg['role']}]")
        print(msg["content"][:600])
        print("..." if len(msg["content"]) > 600 else "")


if __name__ == "__main__":
    main()
