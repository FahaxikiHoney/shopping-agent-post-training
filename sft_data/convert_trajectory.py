# -*- coding: utf-8 -*-
"""
将真实项目跑出的轨迹数据（shopping_trajectory_v1）转换为 SFT 训练格式。

输入：trajectory JSON（单条或 JSONL 文件）
输出：与 trajectories_react.jsonl 兼容的 SFT 格式

转换逻辑：
  1. 从 request.query 取原始 query
  2. 从 llm_calls[stage=shopping, phase=plan_tool_actions].output 取工具调用决策
  3. 从 runtime_events[observation][sku_recall/scenario_related_recall] 取商品结果
  4. 从 llm_calls[stage=response, phase=final_response_stream].output 取最终回复
  5. 组装成标准 messages 格式落盘

用法：
  # 转换单条（stdin）
  python3 convert_trajectory.py --input trajectory.json --output out.jsonl

  # 转换 JSONL 文件
  python3 convert_trajectory.py --input trajectories.jsonl --output sft_data.jsonl
"""

import json
import re
import sys
import argparse
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

SYSTEM_PROMPT_TRAIN = """你是 Shopping 购物助手，负责理解用户需求、调用工具搜索商品、并生成最终推荐回复。

【工具调用规则】
- 普通商品搜索：调用 sku_recall，同时必须调用一次 scenario_related_recall 补充同品类候选
- 用户提到历史商品（"上一个""第一个"）：改用 sku_recall_history
- 用户问优惠券/折扣/促销：调用 promotion_coupon
- 每次只能执行一次召回动作，不能重复调用

【商卡输出规则】
- 工具返回商品后，最终回复必须输出 [product:X] 商卡标签，X 为工具返回的整数索引
- 禁止只输出文字不输出商卡
- 商卡格式只能是 [product:X]，product 必须小写，括号内不加任何其他字符
- 每个商卡在一次回复中只能出现一次
- 推荐理由只能基于工具实际返回的信息，禁止捏造

【无货处理】
- sku_recall 返回 count=0 且 no_stock=true 时，先说明该商品暂时无货，再根据 scenario_related_recall 返回的同类商品进行推荐

【回复格式】
- 每款推荐商品：**商品名摘要**：一句推荐理由（基于工具返回规格）。[product:X]
- 禁止使用序号或列表符号
- 回复简洁直接，不重复用户问题
- 回复语言与用户输入语言保持一致"""


# ─────────────────────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────────────────────

def find_llm_call(llm_calls: List[Dict], stage: str, phase: str) -> Optional[Dict]:
    for c in llm_calls:
        if c.get("stage") == stage and c.get("phase") == phase and c.get("status") == "success":
            return c
    return None


def find_tool_observations(runtime_events: List[Dict], tool_names: List[str]) -> List[Dict]:
    """按顺序取指定工具的 observation 事件"""
    results = []
    for ev in runtime_events:
        if ev.get("event_type") != "observation":
            continue
        callee = ev.get("payload", {}).get("content", {}).get("callee", "")
        if callee in tool_names:
            results.append(ev)
    return results


def _coerce_dict(value):
    """observation.output 可能是 dict 或 JSON 字符串,统一成 dict。"""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def build_global_index_map(runtime_events: List[Dict]) -> Dict[str, int]:
    """
    从 shopping_agent 的 observation 中提取 sku_id → 全局 index 映射。

    真实系统在 shopping_agent 内部把 sku_recall 与 scenario_related_recall 合并、
    去重、经 filter_skus_by_relevance 过滤后,按顺序编号交给 response_agent(即
    `[product 1 begin]...[product N begin]` 里的 N)。最终回复的 [product:X] 引用
    的就是这套全局编号,所以训练数据里的工具 observation 也必须用同一套编号,
    否则会被 validate_product_refs 误判成幻觉而整条丢弃。
    """
    for ev in runtime_events:
        if ev.get("event_type") != "observation":
            continue
        content = ev.get("payload", {}).get("content", {})
        if content.get("callee") != "shopping_agent":
            continue
        out = _coerce_dict(content.get("output"))
        products = out.get("products") or []
        index_map: Dict[str, int] = {}
        for idx, p in enumerate(products, 1):
            sku_id = str(p.get("sku_id", "")).strip()
            if sku_id:
                index_map[sku_id] = idx
        if index_map:
            return index_map
    return {}


def extract_thinking_and_content(raw_output: str) -> tuple[str, str]:
    """
    从模型输出中分离 thinking 和正文。
    支持 <think>...</think> 格式。
    """
    if not raw_output:
        return "", ""
    m = re.search(r'<think>([\s\S]*?)</think>', raw_output)
    if m:
        thinking = m.group(1).strip()
        after = raw_output[m.end():].strip()
        return thinking, after
    return "", raw_output.strip()


def build_tool_calls_from_plan(plan_output: str) -> List[Dict]:
    """
    把 shopping planner 的 JSON 数组输出转成 OpenAI tool_calls 格式。
    plan_output 示例：
      [{"name":"sku_recall","arguments":{"queries":["Apple Pencil Pro"]}}]
    """
    try:
        # 提取 JSON 数组
        m = re.search(r'\[[\s\S]*\]', plan_output)
        if not m:
            return []
        actions = json.loads(m.group())
    except Exception:
        return []

    tool_calls = []
    for i, action in enumerate(actions):
        name = action.get("name", "")
        arguments = action.get("arguments", {})
        tool_calls.append({
            "id": f"call_{uuid.uuid4().hex[:8]}",
            "type": "function",
            "function": {
                "name": name,
                "arguments": json.dumps(arguments, ensure_ascii=False),
            }
        })
    return tool_calls


def format_tool_result(observation_event: Dict, global_index_map: Optional[Dict[str, int]] = None) -> str:
    """把 observation event 的 output 格式化为 tool message content。

    当 global_index_map 提供时,严格用它给商品编号——保证下游 [product:X] 引用与
    工具返回集合能对齐;不在 map 中的商品说明被 filter_skus_by_relevance 过滤掉,
    从训练观测里剔除。map 为空时退回本工具内 1..N 顺序编号(兼容老数据)。
    """
    content = observation_event.get("payload", {}).get("content", {})
    output = _coerce_dict(content.get("output"))
    callee = content.get("callee", "")

    if not output:
        return json.dumps({"status": "empty"}, ensure_ascii=False)

    # 抽取原始商品列表:优先 products,退回 sku_list + sku_map(sku_recall 原始返回)
    raw_products = output.get("products") or []
    if not raw_products and output.get("sku_list") and output.get("sku_map"):
        sku_map = output.get("sku_map") or {}
        raw_products = []
        for sid in output.get("sku_list", []):
            item = dict(sku_map.get(sid, {}))
            item.setdefault("sku_id", sid)
            raw_products.append(item)

    def _slim(p: Dict, idx: int) -> Dict:
        return {
            "index": idx,
            "product_id": str(p.get("sku_id", "") or p.get("product_id", "")),
            "title": p.get("sku_name", p.get("title", "")),
            "price": float(p.get("final_price", p.get("price", 0)) or 0),
            "rating": p.get("good", "") or p.get("rating", ""),
            "sales": p.get("sales", ""),
            "key_specs": p.get("keyword", "") or p.get("key_specs", ""),
            "brand": p.get("brand_name", "") or p.get("brand", ""),
        }

    cleaned_products: List[Dict] = []
    if global_index_map:
        # 用全局编号,过滤掉不在下游最终集合中的商品
        for p in raw_products:
            sid = str(p.get("sku_id", "") or p.get("product_id", "")).strip()
            if sid in global_index_map:
                cleaned_products.append(_slim(p, global_index_map[sid]))
        cleaned_products.sort(key=lambda x: x["index"])
    else:
        for idx, p in enumerate(raw_products, 1):
            cleaned_products.append(_slim(p, idx))

    if cleaned_products:
        return json.dumps({
            "status": "SUCCESS",
            "tool": callee,
            "count": len(cleaned_products),
            "products": cleaned_products,
        }, ensure_ascii=False)

    # 无货场景:原始就没商品,或全部被下游过滤
    raw_count = output.get("count", len(raw_products))
    if raw_count == 0 or not raw_products or not cleaned_products:
        return json.dumps({
            "status": "SUCCESS",
            "tool": callee,
            "count": 0,
            "products": [],
            "no_stock": True,
            "message": "暂时无货",
        }, ensure_ascii=False)

    return json.dumps(output, ensure_ascii=False)[:2000]


def get_valid_product_indexes(tool_messages: List[Dict]) -> set:
    """收集所有工具返回的合法商品 index"""
    indexes = set()
    for msg in tool_messages:
        try:
            r = json.loads(msg["content"])
            for p in r.get("products", []):
                if "index" in p:
                    indexes.add(p["index"])
        except Exception:
            pass
    return indexes


def validate_product_refs(final_response: str, valid_indexes: set) -> bool:
    """检查 [product:X] 引用是否都在合法 index 中"""
    refs = set(int(m) for m in re.findall(r'\[product:(\d+)\]', final_response))
    if not refs and valid_indexes:
        return False  # 有商品但没有商卡
    hallucinated = refs - valid_indexes
    return len(hallucinated) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 主转换函数
# ─────────────────────────────────────────────────────────────────────────────

def convert_trajectory(traj: Dict) -> Optional[Dict]:
    """
    将一条真实轨迹转换为 SFT 格式。
    返回 None 表示跳过（数据不合格）。
    """
    schema = traj.get("schema_version", "")
    if schema != "shopping_trajectory_v1":
        return None

    status = traj.get("status", "")
    if status != "success":
        return None

    trajectory_id = traj.get("trajectory_id", f"real_{uuid.uuid4().hex[:8]}")
    trace_id      = traj.get("trace_id", "")
    query         = traj.get("request", {}).get("query", "")
    if not query:
        return None

    llm_calls      = traj.get("llm_calls", [])
    runtime_events = traj.get("runtime_events", [])

    # ── Step 1: shopping planner → tool_calls ────────────────────────────────
    shopping_call = find_llm_call(llm_calls, "shopping", "plan_tool_actions")
    if not shopping_call:
        return None

    plan_output = shopping_call.get("output", "")
    thinking_shopping, _ = extract_thinking_and_content(plan_output)
    tool_calls = build_tool_calls_from_plan(plan_output)
    if not tool_calls:
        return None

    # assistant message：shopping 决策（含 thinking）
    assistant_tool_msg = {
        "role": "assistant",
        "content": f"<think>\n{thinking_shopping}\n</think>" if thinking_shopping else "",
        "tool_calls": tool_calls,
    }

    # ── Step 2: tool observations → tool messages ─────────────────────────────
    tool_names = ["sku_recall", "scenario_related_recall"]
    observations = find_tool_observations(runtime_events, tool_names)

    # 真实系统会把两个召回工具的结果合并去重再编号交给 response_agent,
    # 用这套全局编号才能对齐最终回复里的 [product:X] 引用
    global_index_map = build_global_index_map(runtime_events)

    tool_messages = []
    for obs in observations:
        content_block = obs.get("payload", {}).get("content", {})
        callee = content_block.get("callee", "")
        # 找对应的 tool_call id
        tc_id = next(
            (tc["id"] for tc in tool_calls
             if tc["function"]["name"] == callee),
            f"call_{uuid.uuid4().hex[:8]}"
        )
        tool_messages.append({
            "role": "tool",
            "tool_call_id": tc_id,
            "content": format_tool_result(obs, global_index_map),
        })

    if not tool_messages:
        return None

    # ── Step 3: response → 最终回复 ───────────────────────────────────────────
    response_call = find_llm_call(llm_calls, "response", "final_response_stream")
    if not response_call:
        return None

    final_output = response_call.get("output", "")
    thinking_response, final_text = extract_thinking_and_content(final_output)

    if not final_text or "[product:" not in final_text:
        return None

    # assistant message：最终回复（含 thinking）
    if thinking_response:
        final_content = f"<think>\n{thinking_response}\n</think>\n\n{final_text}"
    else:
        final_content = final_text

    assistant_final_msg = {
        "role": "assistant",
        "content": final_content,
    }

    # ── Step 4: 校验商卡引用 ──────────────────────────────────────────────────
    valid_indexes = get_valid_product_indexes(tool_messages)
    if not validate_product_refs(final_text, valid_indexes):
        return None

    # ── Step 5: 组装 messages ─────────────────────────────────────────────────
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_TRAIN},
        {"role": "user",   "content": query},
        assistant_tool_msg,
        *tool_messages,
        assistant_final_msg,
    ]

    # ── Step 6: 判断场景类型 ──────────────────────────────────────────────────
    stage_records = traj.get("stage_records", [])
    master_record = next((r for r in stage_records if r.get("stage") == "master"), {})
    intents = master_record.get("data", {}).get("intents", [])
    scenario_type = "search_recommend"
    if "similar" in intents:
        scenario_type = "similar_rec"
    elif "compare" in intents:
        scenario_type = "compare"

    # 无货判断
    for tm in tool_messages:
        try:
            r = json.loads(tm["content"])
            if r.get("no_stock") and r.get("count") == 0:
                scenario_type = "search_no_stock"
                break
        except Exception:
            pass

    return {
        "trajectory_id": trajectory_id,
        "trace_id": trace_id,
        "scenario_type": scenario_type,
        "user_query": query,
        "messages": messages,
        "final_response": final_text,
        "raw_thinking": thinking_response,
        "total_steps": len(tool_calls),
        "status": "done",
        "sft_source": "real_shopping_v1",
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  required=True, help="输入文件路径（JSON 或 JSONL）")
    parser.add_argument("--output", required=True, help="输出 JSONL 文件路径")
    parser.add_argument("--pretty", action="store_true", help="输出单条时格式化 JSON")
    args = parser.parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.output)

    # 读取输入
    raw = input_path.read_text(encoding="utf-8").strip()
    if raw.startswith("[") or (raw.startswith("{") and "\n{" not in raw):
        # 单条 JSON 或 JSON 数组
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
    else:
        # JSONL
        data = [json.loads(line) for line in raw.splitlines() if line.strip()]

    converted = 0
    skipped   = 0

    with open(output_path, "w", encoding="utf-8") as f:
        for item in data:
            result = convert_trajectory(item)
            if result is None:
                skipped += 1
                continue
            if args.pretty and len(data) == 1:
                f.write(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            converted += 1

    print(f"转换完成：{converted} 条成功 | {skipped} 条跳过")
    print(f"输出：{output_path}")


if __name__ == "__main__":
    main()
