# -*- coding: utf-8 -*-
"""
思维链压缩脚本（方案C：混合模式）

前4句：从结构化字段直接组装（tool_input + products，100%与工具对齐）
第5句：用 JoyAI-LLM-Flash 生成推荐判断依据（1句话，约0.5s/条）

用法：
    python3 sft_data/compress_thinking.py --sample 20    # 先跑20条验证
    python3 sft_data/compress_thinking.py -c 3           # 全量，3线程
    python3 sft_data/compress_thinking.py --resume       # 断点续跑
"""
from __future__ import annotations
import json, sys, time, threading, argparse, re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))
from shopping_agent.llm.client import LLMClient

INPUT_FILE  = Path(__file__).parent / "trajectories_r1.jsonl"
OUTPUT_FILE = Path(__file__).parent / "trajectories_r1_compressed.jsonl"
WRITE_LOCK  = threading.Lock()

# ── 场景中文名 ──────────────────────────────────────────────
SC_NAMES = {
    "similar_rec":       "相似品推荐",
    "sku_comp":          "商品对比",
    "search_recommend":  "搜索推荐",
    "matching_purchase": "搭配购物",
    "bundle_purchase":   "组合购物",
    "repurchase":        "复购召回",
    "place_order":       "购物下单",
}

TOOL_NAMES = {
    "SkuRecallShopping":    "商品召回",
    "SkuRepurchaseRecall":  "复购召回",
    "ShoppingPlaceOrderTool": "下单工具",
    "OrderQuerySkill":      "订单查询",
    "PythonCalculator":     "价格计算",
}

# ── 第5句：推荐判断依据的 prompt ────────────────────────────
REASON_SYSTEM = "你是购物推荐助手。用一句话（25-50字）说明最终推荐判断依据，包含：推荐哪款或哪套方案，核心理由是什么。只输出这一句话，不加序号。"


def build_sentence_5(d: dict, llm: LLMClient) -> str:
    """用 LLM 生成第5句：推荐判断依据"""
    sc = d.get("scenario_type", "")
    query = d.get("user_query", "")
    steps = d.get("steps", [])
    tool_step = next((s for s in steps if s.get("step_type") == "tool_call"), None)
    final = next((s for s in steps if s.get("step_type") == "final_response"), None)

    products = tool_step.get("tool_output", {}).get("products", [])[:3] if tool_step else []
    prod_str = "、".join(f"{p.get('title','')[:12]}¥{p.get('price',0)}" for p in products)
    fr_preview = (d.get("final_response", "") or "")[:150]

    user_prompt = f"场景：{SC_NAMES.get(sc, sc)}\n用户问：{query}\n候选商品：{prod_str}\n推荐回复摘要：{fr_preview}"
    content, _ = llm.generate(REASON_SYSTEM, user_prompt, max_tokens=100, temperature=0.5)
    return content.strip()


def build_thinking(d: dict, llm: LLMClient) -> str:
    """
    方案C：前4句结构化组装 + 第5句LLM生成

    第1句：用户核心需求
    第2句：工具调用决策（直接读 tool_input）
    第3句：召回结果摘要（直接读 products）
    第4句：筛选/排除逻辑
    第5句：推荐判断依据（LLM生成）
    """
    sc = d.get("scenario_type", "")
    query = d.get("user_query", "")
    steps = d.get("steps", [])

    tool_steps = [s for s in steps if s.get("step_type") == "tool_call"]
    final = next((s for s in steps if s.get("step_type") == "final_response"), None)

    if not tool_steps:
        return ""

    # 取第一个工具调用（主要决策）
    main_tool = tool_steps[0]
    tool_name = main_tool.get("tool_name", "")
    tool_input = main_tool.get("tool_input", {})
    products = main_tool.get("tool_output", {}).get("products", [])[:3]

    # ── 第1句：用户需求 ──────────────────────────────────────
    s1 = f"用户问：{query}。"

    # ── 第2句：工具调用决策 ──────────────────────────────────
    tool_cn = TOOL_NAMES.get(tool_name, tool_name)
    if tool_name in ("SkuRecallShopping",):
        skus = tool_input.get("skus", [])
        q = tool_input.get("query", "")
        max_p = tool_input.get("max_price", 0)
        filters = tool_input.get("filters", {})

        if skus:
            s2 = f"调用{tool_cn}精确匹配：{' / '.join(str(s)[:15] for s in skus[:3])}。"
        elif filters.get("style"):
            s2 = f"调用{tool_cn}（搭配模式）：风格={filters['style']}，搜「{q[:20]}」。"
        else:
            price_info = f"，≤¥{max_p}" if max_p else ""
            s2 = f"调用{tool_cn}：搜「{q[:25]}」{price_info}，page_size={tool_input.get('page_size', 3)}。"

    elif tool_name == "SkuRepurchaseRecall":
        kw = tool_input.get("category_keyword", "")
        tr = tool_input.get("time_range", "")
        s2 = f"调用{tool_cn}：关键词={kw}，时间范围={tr}。"

    elif tool_name in ("OrderQuerySkill", "ShoppingPlaceOrderTool"):
        action = tool_input.get("action", "") or tool_input.get("issue_type", "")
        s2 = f"调用{tool_cn}：意图={action}。"

    elif tool_name == "PythonCalculator":
        s2 = f"调用{tool_cn}计算各品类价格合计。"

    else:
        s2 = f"调用{tool_cn}：{str(tool_input)[:40]}。"

    # ── 第3句：召回结果摘要 ──────────────────────────────────
    if products:
        prod_parts = []
        for p in products:
            title = p.get("title", "")[:12]
            price = p.get("price", 0)
            rating = p.get("rating", 0)
            sales = p.get("sales", "")
            prod_parts.append(f"{title}¥{price}({rating}分/{sales})")
        s3 = f"召回{len(products)}款：{'，'.join(prod_parts)}。"
    else:
        s3 = "未召回有效商品。"

    # ── 第4句：筛选逻辑（按场景生成规则句） ──────────────────
    if sc == "similar_rec":
        # 找出不符合需求的（如保温不够的）
        s4 = f"筛选：重点关注解决用户抱怨点的改进款，优先评分高且月销量大的。"
    elif sc == "sku_comp":
        if len(products) >= 2:
            cheapest = min(products, key=lambda x: x.get("price", 0))
            best_rated = max(products, key=lambda x: x.get("rating", 0))
            s4 = f"对比维度：价格/评分/核心参数/月销量；性价比看{cheapest.get('title','')[:8]}，品质看{best_rated.get('title','')[:8]}。"
        else:
            s4 = f"仅召回{len(products)}款，数据不完整，以现有数据进行分析。"
    elif sc == "bundle_purchase":
        n_tools = len(tool_steps)
        calc_steps = [s for s in tool_steps if s.get("tool_name") == "PythonCalculator"]
        s4 = f"分{n_tools - len(calc_steps)}个品类分别召回，最后用PythonCalculator算账验证总价。"
    elif sc == "matching_purchase":
        style = tool_input.get("filters", {}).get("style", "")
        s4 = f"搭配场景不限价格，按{style}风格筛选，整套方案风格统一。"
    elif sc == "repurchase":
        purchase_months = d.get("steps", [{}])[0].get("tool_output", {}).get("purchase_months_ago", "?")
        s4 = f"识别到用户{purchase_months}个月前的历史订单，推荐复购同款或升级新品。"
    elif sc == "place_order":
        s4 = f"识别操作意图，提供具体App操作路径（我的订单→对应功能）。"
    else:
        s4 = f"综合评估召回结果，按用户需求优先排序。"

    # ── 第5句：LLM生成推荐判断依据 ───────────────────────────
    try:
        s5 = build_sentence_5(d, llm)
        if not s5 or len(s5) < 10:
            s5 = "推荐综合评分最高、月销量最大的款式，性价比与品质平衡。"
    except Exception:
        s5 = "推荐评分最高、口碑最好的款式。"

    return f"{s1}\n{s2}\n{s3}\n{s4}\n{s5}"


def validate_thinking(thinking: str) -> list:
    errors = []
    if len(thinking) < 50:
        errors.append(f"太短:{len(thinking)}字")
    if len(thinking) > 400:
        errors.append(f"太长:{len(thinking)}字")
    cn_chars = sum(1 for c in thinking if '一' <= c <= '鿿')
    if len(thinking) > 0 and cn_chars / len(thinking) < 0.3:
        errors.append(f"中文率低:{cn_chars/len(thinking):.0%}")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=0)
    parser.add_argument("--concurrency", "-c", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    llm = LLMClient(model="DeepSeek-V3")

    with open(INPUT_FILE, encoding="utf-8") as f:
        records = [json.loads(line) for line in f]

    done_ids = set()
    if args.resume and OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                done_ids.add(d.get("trajectory_id"))
        print(f"[resume] 已有 {len(done_ids)} 条")

    to_process = [d for d in records if d.get("trajectory_id") not in done_ids]
    if args.sample:
        to_process = to_process[:args.sample]

    total = len(to_process)
    print(f"待压缩: {total} 条 | 并发: {args.concurrency} | 模型: {llm.model}")
    print()

    ok = fail = 0
    start = time.time()

    def process_one(idx_d):
        idx, d = idx_d
        try:
            thinking = build_thinking(d, llm)
            errors = validate_thinking(thinking)
            d_out = dict(d)
            d_out["thinking"] = thinking
            return idx, d_out, "ok", errors
        except Exception as e:
            d_out = dict(d)
            d_out["thinking"] = d.get("raw_thinking", "")[:200]
            return idx, d_out, "error", [str(e)[:60]]

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(process_one, (i, d)): i for i, d in enumerate(to_process)}
        for fut in as_completed(futs):
            idx, d_out, status, errors = fut.result()
            n = idx + 1
            thinking = d_out.get("thinking", "")

            with WRITE_LOCK:
                with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(d_out, ensure_ascii=False) + "\n")

            if status == "ok" and not errors:
                ok += 1
                print(f"[{n:>5}/{total}] ✓ {d_out.get('scenario_type',''):<18} {len(thinking)}字")
            elif errors:
                fail += 1
                print(f"[{n:>5}/{total}] ⚠ {errors} | {len(thinking)}字")
            else:
                fail += 1
                print(f"[{n:>5}/{total}] ✗ {errors}")

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"完成: 成功={ok} 失败={fail} 耗时={elapsed:.0f}s ({elapsed/max(total,1):.1f}s/条)")
    print(f"输出: {OUTPUT_FILE.name}")


if __name__ == "__main__":
    main()
