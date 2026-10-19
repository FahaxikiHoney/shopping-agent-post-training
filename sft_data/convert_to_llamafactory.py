# -*- coding: utf-8 -*-
"""
将 trajectories_react.jsonl 转换为 LlamaFactory ShareGPT 格式

LlamaFactory ShareGPT 格式：
{
  "conversations": [
    {"from": "system", "value": "..."},
    {"from": "human", "value": "..."},
    {"from": "gpt", "value": "..."},
    ...
  ]
}

处理逻辑：
- system → from: system
- user → from: human
- assistant（含tool_calls）→ 转为函数调用文本，from: gpt
- tool → 转为工具结果文本，追加到下一个 gpt 消息里
- assistant（最终回复）→ from: gpt
"""
import json
import re
import argparse
from pathlib import Path


def convert_messages_to_sharegpt(messages: list) -> list:
    """把 messages 列表转为 ShareGPT conversations"""
    conversations = []

    # 收集 tool 消息，等待合并到下一个 assistant 消息
    pending_tool_results = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "") or ""
        tool_calls = msg.get("tool_calls", [])

        if role == "system":
            # 使用训练版 system prompt（短版本）
            conversations.append({
                "from": "system",
                "value": content
            })

        elif role == "user":
            # 如果有积累的 tool 结果还没处理，先清空
            pending_tool_results = []
            conversations.append({
                "from": "human",
                "value": content
            })

        elif role == "assistant":
            if tool_calls:
                # 工具调用：转为结构化文本
                tc_texts = []
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    name = fn.get("name", "")
                    args = fn.get("arguments", "")
                    try:
                        args_dict = json.loads(args)
                        args_str = json.dumps(args_dict, ensure_ascii=False)
                    except Exception:
                        args_str = args
                    tc_texts.append(f'<tool_call>\n{{"name": "{name}", "arguments": {args_str}}}\n</tool_call>')

                # thinking 内容 + 工具调用
                think_content = ""
                if content and "<think>" in content:
                    think_content = content  # 保留完整的 <think>...</think>
                elif content:
                    think_content = content

                tool_call_text = "\n".join(tc_texts)
                gpt_value = f"{think_content}\n{tool_call_text}".strip() if think_content else tool_call_text

                conversations.append({
                    "from": "gpt",
                    "value": gpt_value
                })
            else:
                # 最终回复：合并 pending tool 结果（如果有）
                final_content = content

                # 清理 thinking 标签，只保留正文
                if "<think>" in final_content and "</think>" in final_content:
                    think_part = re.search(r'<think>([\s\S]*?)</think>', final_content)
                    after_think = final_content.split("</think>")[-1].strip()
                    if think_part and after_think:
                        # 保留 thinking + 最终回复
                        final_content = f"<think>\n{think_part.group(1).strip()}\n</think>\n\n{after_think}"
                    elif think_part and not after_think:
                        # thinking 截断了，只有 thinking
                        final_content = f"<think>\n{think_part.group(1).strip()}\n</think>"

                if final_content:
                    conversations.append({
                        "from": "gpt",
                        "value": final_content
                    })

        elif role == "tool":
            # 工具结果：格式化后存到 pending
            tool_content = content
            try:
                result = json.loads(content)
                products = result.get("products", [])
                if products:
                    prod_lines = "\n".join(
                        f"  [{p.get('index','-')}] {p['title']} ¥{p['price']} {p.get('rating','')}分 | {p.get('key_specs','')[:50]}"
                        for p in products[:6]
                    )
                    tool_content = f"工具返回 {len(products)} 款商品：\n{prod_lines}"
                elif result.get("summary"):
                    tool_content = f"工具返回：{result['summary']}"
            except Exception:
                pass

            pending_tool_results.append(f"<tool_response>\n{tool_content}\n</tool_response>")

            # 把 tool 结果作为 human 消息追加（LlamaFactory 的工具调用处理方式）
            conversations.append({
                "from": "human",
                "value": "\n".join(pending_tool_results)
            })
            pending_tool_results = []

    return conversations


def convert_file(input_path: str, output_path: str, min_score: float = 0.0,
                 eval_path: str = None):
    """转换整个文件"""
    input_file = Path(input_path)
    output_file = Path(output_path)

    # 加载评估结果（如果有）
    score_map = {}
    if eval_path and Path(eval_path).exists():
        for line in Path(eval_path).read_text().splitlines():
            e = json.loads(line)
            score_map[e["trajectory_id"]] = e.get("score", -1)
        print(f"加载评估结果: {len(score_map)}条")

    data = [json.loads(l) for l in input_file.read_text().splitlines()]

    converted = []
    skipped = 0

    for d in data:
        tid = d.get("trajectory_id", "")

        # 按评估分数过滤
        if score_map and min_score > 0:
            score = score_map.get(tid, -1)
            if score >= 0 and score < min_score:
                skipped += 1
                continue

        messages = d.get("messages", [])
        if not messages:
            skipped += 1
            continue

        conversations = convert_messages_to_sharegpt(messages)

        # 基本验证
        has_gpt = any(c["from"] == "gpt" for c in conversations)
        has_human = any(c["from"] == "human" for c in conversations)
        if not (has_gpt and has_human):
            skipped += 1
            continue

        converted.append({"conversations": conversations})

    # 写出
    output_file.write_text(
        json.dumps(converted, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"转换完成: {len(converted)}条 | 跳过: {skipped}条")
    print(f"输出: {output_file}")

    # 打印一条样例
    if converted:
        print(f"\n=== 样例（第1条）===")
        for c in converted[0]["conversations"][:4]:
            v = c["value"][:100].replace("\n", "\\n")
            print(f"  [{c['from']}]: {v}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default="sft_data/trajectories_react.jsonl")
    parser.add_argument("--output", default="sft_data/train_llamafactory.json")
    parser.add_argument("--eval",   default="sft_data/eval_results.jsonl", help="评估结果文件，用于按分数过滤")
    parser.add_argument("--min-score", type=float, default=0.8, help="最低分数阈值（0=不过滤）")
    args = parser.parse_args()

    convert_file(args.input, args.output, args.min_score, args.eval)


if __name__ == "__main__":
    main()
