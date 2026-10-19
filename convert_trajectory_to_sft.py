#!/usr/bin/env python3
"""
将 shopping 原始轨迹 JSONL 转为标准 OpenAI Function Calling SFT 格式。

输出:
  messages: [system, user, assistant(tool_calls), tool*, assistant(final)]
  tools: 工具 schema
  metadata: trajectory_id, query, scenario 等
"""
import json, re, sys, uuid
from typing import Any, Dict, List, Optional, Tuple

# ─── 训练用系统提示词(精简版) ───
SYSTEM_PROMPT_TRAIN = """\
You are a shopping assistant. Analyze the user's shopping need, call tools to retrieve products, then compose a recommendation reply.

## Available Tools

1. **sku_recall** — Main product search. Always call this for shopping queries.
   - Parameters: `query` (string), `page_size` (int, default 10), `queries` (list[string], optional multi-query), `constraints` (string, optional)
   - Returns: `{count, sku_list, sku_map, products}`

2. **scenario_related_recall** — Complementary/related products for cross-sell or style matching.
   - Parameters: `scenario` (string), `queries` (list[string])
   - Returns: `{products: [...]}`

3. **web_search** — Live web search when user asks for latest info, trends, or external evidence.
   - Parameters: `search_query` (string) or `queries` (list[string]), `top_n` (int, optional)
   - Returns: `{results: [...]}`

4. **promotion_coupon** — Query available coupons/promotions for a product or category.
   - Parameters: `query` (string), `sku_ids` (list[string], optional)
   - Returns: `{coupons: [...]}`

## Rules

- You MUST call at least one recall tool (sku_recall or scenario_related_recall) per shopping request.
- You may call web_search BEFORE recall if external info is needed, but always follow with a recall tool.
- Think step-by-step in <think>...</think> before calling tools and before composing the final reply.
- Reference products using [product:N] tags (N = 1-based index in the order products appear in tool results).
- Reply in the same language as the user's query.
- Keep recommendations concise: product name, key specs, price, and why it fits the user's need."""

# ─── 工具 Schema (OpenAI function calling 格式) ───
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "sku_recall",
            "description": "Search products by query keywords. Returns matched SKUs with price, brand, specs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Main search keyword"},
                    "page_size": {"type": "integer", "description": "Max results to return", "default": 10},
                    "queries": {"type": "array", "items": {"type": "string"}, "description": "Multiple query variants for broader recall"},
                    "constraints": {"type": "string", "description": "Additional constraints like price range, brand filter"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scenario_related_recall",
            "description": "Retrieve related/complementary products for cross-sell or scenario matching.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scenario": {"type": "string", "description": "Shopping scenario or category"},
                    "queries": {"type": "array", "items": {"type": "string"}, "description": "Related query terms"},
                },
                "required": ["scenario"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for latest info, trends, reviews, or external evidence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_query": {"type": "string", "description": "Search query"},
                    "queries": {"type": "array", "items": {"type": "string"}, "description": "Multiple search queries"},
                    "top_n": {"type": "integer", "description": "Number of results"},
                },
                "required": ["search_query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "promotion_coupon",
            "description": "Query available coupons and promotions for products or categories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Product or category to search coupons for"},
                    "sku_ids": {"type": "array", "items": {"type": "string"}, "description": "Specific SKU IDs"},
                },
                "required": ["query"],
            },
        },
    },
]


def extract_think(text: str) -> Tuple[str, str]:
    """从 LLM output 中分离 <think> 和正文"""
    m = re.match(r"<think>([\s\S]*?)</think>\s*([\s\S]*)$", text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", text.strip()


def trim_observation(obs_raw: Any, max_products: int = 15) -> str:
    """精简工具返回结果,按商品条数裁剪(保证输出是合法 JSON)"""
    if isinstance(obs_raw, str):
        try:
            obs_raw = json.loads(obs_raw)
        except:
            return obs_raw[:6000]

    if not isinstance(obs_raw, dict):
        return json.dumps(obs_raw, ensure_ascii=False)[:6000]

    def _slim_product(p: dict) -> dict:
        return {
            "sku_id": p.get("sku_id", ""),
            "sku_name": p.get("sku_name", ""),
            "brand_name": p.get("brand_name", ""),
            "final_price": p.get("final_price", ""),
            "price": p.get("price", ""),
            "good": p.get("good", ""),
            "sales": p.get("sales", ""),
        }

    # sku_recall 格式: 有 sku_map 字段
    if "sku_map" in obs_raw:
        sku_list = obs_raw.get("sku_list", [])[:max_products]
        sku_map = obs_raw.get("sku_map", {})
        products = [_slim_product(sku_map.get(sid, {"sku_id": sid})) for sid in sku_list]
        # 如果还有额外的 products 列表(scenario_related 合并),补充进去
        extra = obs_raw.get("products", [])
        if extra and len(products) < max_products:
            for p in extra[:max_products - len(products)]:
                products.append(_slim_product(p))
        slim = {"count": obs_raw.get("count", len(products)), "products": products}
        return json.dumps(slim, ensure_ascii=False)

    # scenario_related_recall 格式: 有 products 字段
    if "products" in obs_raw:
        products = [_slim_product(p) for p in obs_raw["products"][:max_products]]
        slim = {"count": len(products), "products": products}
        return json.dumps(slim, ensure_ascii=False)

    # 其他格式(web_search, promotion_coupon 等)
    return json.dumps(obs_raw, ensure_ascii=False)[:6000]


def convert_one(d: Dict, idx: int) -> Optional[Dict]:
    """转换单条轨迹为 SFT 格式。返回 None 表示跳过。"""
    if d.get("status") != "success":
        return None

    llm_calls = d.get("llm_calls", [])
    events = d.get("runtime_events", [])
    stage_records = d.get("stage_records", [])

    # 1. 找 shopping stage 的 action_plan
    action_plan = []
    for s in stage_records:
        if s.get("stage") == "shopping":
            action_plan = s.get("data", {}).get("action_plan", []) or []
            break
    if not action_plan:
        return None  # 无工具调用,跳过

    # 2. 提取 shopping 阶段的 <think>
    shop_think = ""
    shop_calls = [c for c in llm_calls if c.get("stage") == "shopping" and c.get("phase") == "plan_tool_actions"]
    if shop_calls:
        out = shop_calls[0].get("output", "")
        think_m = re.match(r"<think>([\s\S]*?)</think>", out)
        if think_m:
            shop_think = think_m.group(1).strip()

    # 3. 提取 response 阶段的 <think> + final answer
    resp_calls = [c for c in llm_calls if c.get("stage") == "response"]
    final_think = ""
    final_answer = ""
    if resp_calls:
        out = resp_calls[-1].get("output", "")
        think_m = re.match(r"<think>([\s\S]*?)</think>\s*([\s\S]*)$", out)
        if think_m:
            final_think = think_m.group(1).strip()
            final_answer = think_m.group(2).strip()
        else:
            final_answer = out.strip()
    if not final_answer:
        return None

    # 4. 从 runtime_events 获取工具结果,按调用顺序
    observations = []
    for e in events:
        if e.get("event_type") == "observation":
            p = e.get("payload", {}).get("content", {})
            callee = p.get("callee", "")
            output = p.get("output", "")
            if callee in ("sku_recall", "scenario_related_recall", "web_search", "promotion_coupon"):
                observations.append({"name": callee, "output": output})

    # 5. 构建 messages
    messages = []

    # [0] system
    messages.append({"role": "system", "content": SYSTEM_PROMPT_TRAIN})

    # [1] user
    query = (d.get("request") or {}).get("query", "")
    messages.append({"role": "user", "content": query})

    # [2] assistant with tool_calls
    tool_calls = []
    for i, action in enumerate(action_plan):
        call_id = f"call_{i}"
        args = action.get("arguments", {})
        tool_calls.append({
            "id": call_id,
            "type": "function",
            "function": {
                "name": action["name"],
                "arguments": json.dumps(args, ensure_ascii=False),
            },
        })

    assistant_content = f"<think>\n{shop_think}\n</think>" if shop_think else ""
    messages.append({
        "role": "assistant",
        "content": assistant_content,
        "tool_calls": tool_calls,
    })

    # [3..N-1] tool results
    # 按 action_plan 顺序匹配 observations
    obs_by_name = {}
    for obs in observations:
        obs_by_name.setdefault(obs["name"], []).append(obs["output"])

    for i, action in enumerate(action_plan):
        name = action["name"]
        call_id = f"call_{i}"
        # 取第一个匹配的 observation
        obs_list = obs_by_name.get(name, [])
        raw_output = obs_list.pop(0) if obs_list else "{}"
        content = trim_observation(raw_output)
        messages.append({
            "role": "tool",
            "tool_call_id": call_id,
            "name": name,
            "content": content,
        })

    # [N] final assistant response
    if final_think:
        final_content = f"<think>\n{final_think}\n</think>\n\n{final_answer}"
    else:
        final_content = final_answer
    messages.append({"role": "assistant", "content": final_content})

    # 6. 计算元数据
    trajectory_id = d.get("trajectory_id", f"traj_{idx}")
    return {
        "trajectory_id": trajectory_id,
        "user_query": query,
        "tools": TOOLS_SCHEMA,
        "messages": messages,
        "metadata": {
            "source_idx": idx,
            "status": d.get("status"),
            "n_tool_calls": len(action_plan),
            "tools_used": [a["name"] for a in action_plan],
            "shop_think_len": len(shop_think),
            "final_think_len": len(final_think),
            "n_product_refs": len(re.findall(r"\[product:\d+\]", final_answer)),
        },
    }


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else \
        "data/trajectories/input.jsonl"
    output_path = sys.argv[2] if len(sys.argv) > 2 else \
        "data/train.jsonl"

    lines = open(input_path).read().splitlines()
    converted = []
    skipped = []

    for idx, line in enumerate(lines):
        d = json.loads(line)
        result = convert_one(d, idx)
        if result:
            converted.append(result)
        else:
            skipped.append(idx)

    # 写出
    with open(output_path, "w", encoding="utf-8") as f:
        for item in converted:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # 统计
    print(f"转换完成!")
    print(f"  输入: {len(lines)} 条")
    print(f"  输出: {len(converted)} 条 → {output_path}")
    print(f"  跳过: {len(skipped)} 条 (idx: {skipped})")
    print()
    if converted:
        # messages 长度统计
        msg_lens = [sum(len(m.get("content","")) for m in item["messages"]) for item in converted]
        print(f"  样本 token 估算(字符/3.5):")
        print(f"    min={min(msg_lens)//4:.0f} max={max(msg_lens)//4:.0f} avg={sum(msg_lens)//len(msg_lens)//4:.0f}")
        tool_combos = {}
        for item in converted:
            combo = tuple(item["metadata"]["tools_used"])
            tool_combos[combo] = tool_combos.get(combo, 0) + 1
        print(f"  工具组合分布:")
        for combo, cnt in sorted(tool_combos.items(), key=lambda x: -x[1]):
            print(f"    {combo}: {cnt} 条")


if __name__ == "__main__":
    main()
