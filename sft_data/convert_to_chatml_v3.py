# -*- coding: utf-8 -*-
"""
数据格式转换 v3：标准 Function Calling 多轮对话格式
trajectories_r1_compressed.jsonl → 标准 OpenAI Function Calling 格式

输出格式：
{
  "messages": [
    {"role": "system",    "content": "系统提示"},
    {"role": "user",      "content": "用户问题"},
    {"role": "assistant", "content": "<think>...</think>",
     "tool_calls": [{"id": "call_0", "type": "function",
                     "function": {"name": "SkuRecallShopping", "arguments": "{...}"}}]},
    {"role": "tool",      "tool_call_id": "call_0", "content": "工具返回JSON"},
    {"role": "assistant", "content": "最终推荐回复"}
  ],
  "tools": [{"type": "function", "function": {"name": "...", "description": "...", "parameters": {}}}]
}
"""
from __future__ import annotations
import json, argparse, random, uuid
from pathlib import Path

INPUT  = Path(__file__).parent / "trajectories_r1_compressed.jsonl"
OUTPUT = Path(__file__).parent / "train_chatml_v3.json"
OUTPUT_VAL = Path(__file__).parent / "val_chatml_v3.json"

# ── 系统提示 ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """你是京东购物助手，负责帮用户找到最合适的商品。

工作流程：
1. 理解用户需求，思考搜索策略（在<think>标签内）
2. 调用工具搜索或查询商品
3. 基于工具返回的真实数据，给出推荐回复

规则：
- 严禁虚构商品信息，只使用工具返回的真实数据
- 推荐理由必须基于具体数字（价格/评分/销量）
- 如召回结果与需求不符，如实说明"""

# ── 工具 Schema 定义 ─────────────────────────────────────────────────────
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "SkuRecallShopping",
            "description": "【搜索推荐/相似品/组合购物场景】根据关键词搜索京东商品，返回匹配的商品列表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query":     {"type": "string",  "description": "搜索关键词，如「保温杯 24h 真空双层」"},
                    "max_price": {"type": "number",  "description": "价格上限（元），不传则不限价格"},
                    "min_price": {"type": "number",  "description": "价格下限（元）"},
                    "page_size": {"type": "integer", "description": "返回商品数量，默认3，bundle场景每品类传2"},
                    "is_jd_self":{"type": "boolean", "description": "是否只搜京东自营，默认true"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "SkuRecallBySkuNames",
            "description": "【商品对比场景专用】按商品名精确召回多款商品，用于对比分析。传入2-4个商品名称，返回精确匹配的商品详情。",
            "parameters": {
                "type": "object",
                "properties": {
                    "skus": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "商品名称列表，如 [\"石头G20S Pro\", \"科沃斯X2 Omni\"]，2-4个",
                    },
                },
                "required": ["skus"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "SkuRecallByStyle",
            "description": "【搭配购物场景专用】根据风格标签召回搭配商品，不限价格。用于「买了X，需要搭配Y」的场景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搭配需求描述"},
                    "style": {
                        "type": "string",
                        "description": "风格标签，可选值：nordic(北欧简约)/mid_century(中古复古)/business_formal(商务正式)/fitness(运动健身)/treadmill(跑步机搭配)/coffee(咖啡机搭配)/camera(相机搭配)/study_room(书房搭配)/iphone_accessories(iPhone配件)",
                    },
                    "max_count": {"type": "integer", "description": "返回搭配件数，默认4"},
                },
                "required": ["query", "style"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "SkuRepurchaseRecall",
            "description": "【复购场景专用】查询用户历史购买记录，返回历史商品及推荐复购/升级款。",
            "parameters": {
                "type": "object",
                "properties": {
                    "category_keyword": {"type": "string", "description": "品类关键词，如「咖啡豆」「洗衣液」「猫粮」"},
                    "time_range":       {"type": "string", "description": "查询时间范围，如 last_3_months、last_6_months"},
                },
                "required": ["category_keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "PythonCalculator",
            "description": "【组合购物场景专用】执行Python代码，用于多品类价格汇总、预算分配计算。在bundle场景每个品类召回后必须调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python代码，用print()输出计算结果，例如：\\na=199\\nb=229\\nprint(f'合计{a+b}元，余{1000-a-b}元')"},
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "OrderQuerySkill",
            "description": "【订单服务场景】查询订单状态/物流，或处理售后需求（退货/换货/价保/发票/取消）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id":   {"type": "string", "description": "订单号，格式如 [ORDER_ID]"},
                    "action":     {"type": "string", "description": "操作类型：query(查询)/refund(退款)/exchange(换货)/logistics(物流)/price_protection(价保)/invoice(发票)/cancel(取消)"},
                    "issue_type": {"type": "string", "description": "问题描述，与action保持一致"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ShoppingPlaceOrderTool",
            "description": "【下单/抢购场景】执行下单操作，或处理预约抢购、白条提前还款等操作。",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "商品ID"},
                    "action":     {"type": "string", "description": "操作类型：place_order(下单)/reservation(预约)/early_payoff(提前还款)"},
                },
            },
        },
    },
]

# 工具名映射：将原始数据里的工具名映射到新拆分的工具名
TOOL_NAME_MAP = {
    # SkuRecallShopping 按参数类型分发
    # （在 convert_one 里动态判断）
    "SkuRepurchaseRecall":    "SkuRepurchaseRecall",
    "PythonCalculator":       "PythonCalculator",
    "OrderQuerySkill":        "OrderQuerySkill",
    "ShoppingPlaceOrderTool": "ShoppingPlaceOrderTool",
}


def get_real_tool_name(tool_name: str, tool_input: dict) -> str:
    """根据实际参数判断 SkuRecallShopping 的真实工具名"""
    if tool_name != "SkuRecallShopping":
        return TOOL_NAME_MAP.get(tool_name, tool_name)
    # 精确匹配模式
    if tool_input.get("skus"):
        return "SkuRecallBySkuNames"
    # 搭配模式
    if tool_input.get("filters", {}).get("style"):
        return "SkuRecallByStyle"
    # 普通搜索
    return "SkuRecallShopping"


def slim_tool_output(tool_output: dict, tool_name: str) -> str:
    """
    工具返回结果序列化为字符串。
    只保留关键字段，避免 token 过长。
    """
    if tool_name == "PythonCalculator":
        return json.dumps({
            "status": tool_output.get("status", "SUCCESS"),
            "output": tool_output.get("output", ""),
        }, ensure_ascii=False)

    products = tool_output.get("products", [])
    slim = {
        "status": tool_output.get("status", "SUCCESS"),
        "products": [
            {
                "product_id": p.get("product_id", ""),
                "title":      p.get("title", ""),
                "price":      p.get("price", 0),
                "rating":     p.get("rating", 0),
                "key_specs":  p.get("key_specs", ""),
                "sales":      p.get("sales", ""),
            }
            for p in products[:5]
        ],
    }
    if tool_output.get("order_id"):
        slim["order_id"] = tool_output["order_id"]
    if tool_output.get("purchase_months_ago"):
        slim["purchase_months_ago"] = tool_output["purchase_months_ago"]

    return json.dumps(slim, ensure_ascii=False)


def convert_one(d: dict, include_thinking: bool = True) -> dict | None:
    """
    将单条轨迹转为标准 Function Calling 多轮对话格式。

    messages 结构：
      system → user → [assistant(tool_calls) → tool] × N → assistant(最终回复)
    """
    user_query  = d.get("user_query", "").strip()
    thinking    = d.get("thinking", "").strip()
    final_resp  = d.get("final_response", "").strip()
    steps       = d.get("steps", [])

    if not user_query or not final_resp or len(final_resp) < 50:
        return None

    tool_steps  = [s for s in steps if s.get("step_type") == "tool_call"]

    messages = []

    # ── 1. system ──────────────────────────────────────────────────────────
    messages.append({"role": "system", "content": SYSTEM_PROMPT})

    # ── 2. 多轮历史（如有） ─────────────────────────────────────────────────
    for h in d.get("conversation_history", []):
        role    = h.get("role", "")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    # ── 3. user ────────────────────────────────────────────────────────────
    messages.append({"role": "user", "content": user_query})

    # ── 4. 工具调用轮（每个 tool_step 对应一次 assistant + tool 交换） ────────
    for i, step in enumerate(tool_steps):
        raw_tool_name = step.get("tool_name", "")
        tool_input    = step.get("tool_input", {})
        tool_output   = step.get("tool_output", {})
        call_id       = f"call_{i}_{uuid.uuid4().hex[:8]}"

        # 将 SkuRecallShopping 按参数类型映射到拆分后的工具名
        tool_name = get_real_tool_name(raw_tool_name, tool_input)

        # 搭配模式：把 filters.style 提升为顶层参数，更清晰
        if tool_name == "SkuRecallByStyle":
            style = tool_input.get("filters", {}).get("style", "")
            tool_input = {
                "query": tool_input.get("query", ""),
                "style": style,
                "max_count": tool_input.get("filters", {}).get("max_count", 4),
            }

        # assistant 发起工具调用
        # 第一次调用时，把 thinking 放在 content 里
        content_for_this_call = ""
        if i == 0 and include_thinking and thinking and len(thinking) > 20:
            content_for_this_call = f"<think>\n{thinking}\n</think>"

        assistant_msg = {
            "role": "assistant",
            "content": content_for_this_call,
            "tool_calls": [
                {
                    "id":   call_id,
                    "type": "function",
                    "function": {
                        "name":      tool_name,
                        "arguments": json.dumps(tool_input, ensure_ascii=False),
                    },
                }
            ],
        }
        messages.append(assistant_msg)

        # tool 返回结果
        tool_msg = {
            "role":         "tool",
            "tool_call_id": call_id,
            "content":      slim_tool_output(tool_output, tool_name),
        }
        messages.append(tool_msg)

    # ── 5. assistant 最终回复 ─────────────────────────────────────────────
    # 如果没有工具调用（异常情况），把 thinking 放在这里
    if not tool_steps and include_thinking and thinking and len(thinking) > 20:
        final_content = f"<think>\n{thinking}\n</think>\n\n{final_resp}"
    else:
        final_content = final_resp

    messages.append({"role": "assistant", "content": final_content})

    return {
        "messages": messages,
        "tools": TOOLS_SCHEMA,
        "_scenario":       d.get("scenario_type", ""),
        "_trajectory_id":  d.get("trajectory_id", ""),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-thinking", action="store_true")
    parser.add_argument("--split",       action="store_true")
    parser.add_argument("--val-ratio",   type=float, default=0.1)
    parser.add_argument("--seed",        type=int,   default=42)
    args = parser.parse_args()

    include_thinking = not args.no_thinking

    records = []
    skip = 0
    with open(INPUT, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            r = convert_one(d, include_thinking)
            if r:
                records.append(r)
            else:
                skip += 1

    # 统计
    from collections import Counter
    role_counts = Counter()
    for r in records:
        for msg in r["messages"]:
            role_counts[msg["role"]] += 1

    print(f"转换完成：{len(records)} 条（跳过 {skip} 条）")
    print(f"角色分布：{dict(role_counts)}")
    avg_turns = sum(len(r["messages"]) for r in records) / len(records)
    print(f"平均对话轮数：{avg_turns:.1f}")

    if args.split:
        random.seed(args.seed)
        random.shuffle(records)
        n_val = max(1, int(len(records) * args.val_ratio))
        val_records   = records[:n_val]
        train_records = records[n_val:]
        with open(OUTPUT,     "w", encoding="utf-8") as f:
            json.dump(train_records, f, ensure_ascii=False, indent=2)
        with open(OUTPUT_VAL, "w", encoding="utf-8") as f:
            json.dump(val_records,   f, ensure_ascii=False, indent=2)
        print(f"train: {len(train_records)} 条 → {OUTPUT.name}")
        print(f"val:   {len(val_records)} 条 → {OUTPUT_VAL.name}")
    else:
        with open(OUTPUT, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"输出：{OUTPUT.name}（{len(records)} 条）")

    # 打印样例
    print("\n=== 样例（标准 Function Calling 格式）===")
    sample = records[0]
    for msg in sample["messages"]:
        role = msg["role"]
        content = msg.get("content", "") or ""
        tool_calls = msg.get("tool_calls", [])
        print(f"\n[{role}]")
        if content:
            print(content[:200])
        if tool_calls:
            print(f"tool_calls: {json.dumps(tool_calls[0], ensure_ascii=False)[:150]}")


if __name__ == "__main__":
    main()
