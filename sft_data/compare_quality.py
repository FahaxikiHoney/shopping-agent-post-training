# -*- coding: utf-8 -*-
"""
质量对比评估：真实轨迹 vs mock 轨迹

对两批数据各抽样50条，用相同的 LLM-as-Judge 打分，输出对比报告。

用法：
    python3 sft_data/compare_quality.py \
        --real-dir sft_data/training-data/data/trajectories \
        --mock-file sft_data/trajectories_react.jsonl \
        --model MiniMax-M3-joybuilder \
        -n 50 -c 4
"""
from __future__ import annotations

import json
import re
import sys
import argparse
import threading
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from joybuy_agent.llm.client import LLMClient

# 直接复用 evaluate.py 的 judge prompt（中文，MiniMax 能正确遵循）
from sft_data.evaluate import JUDGE_SYSTEM, JUDGE_PROMPT_TEMPLATE, format_trajectory as _fmt_react


# ── 工具函数 ──────────────────────────────────────────────────────────────
def compute_score(judge: dict) -> float:
    d1 = judge.get("d1_need_understanding", {}).get("verdict") == "PASS"
    d2 = judge.get("d2_factual_accuracy", {}).get("verdict") == "PASS"
    d3 = judge.get("d3_recommendation_quality", {}).get("verdict") == "PASS"
    d4 = judge.get("d4_completeness", {}).get("verdict") == "PASS"
    d5 = judge.get("d5_recommendation_value", {}).get("verdict") == "PASS"
    if not d1 or not d4:
        return 0.0
    score = 0.40
    score += 0.20 if d2 else 0.0
    score += 0.20 if d3 else 0.0
    score += 0.15 if d4 else 0.0
    score += 0.05 if d5 else 0.0
    return round(score, 2)


def format_react_trajectory(traj: dict) -> str:
    """格式化 trajectories_react.jsonl 格式的轨迹（mock轨迹），复用 evaluate.py 的 format_trajectory"""
    return _fmt_react(traj.get("messages", []))


def build_messages_from_real(traj: dict) -> list[dict]:
    """把真实轨迹（joybuy_trajectory_v1）转成 messages 列表，供 format_trajectory 使用"""
    msgs = []
    query = traj.get("request", {}).get("query", "")
    if query:
        msgs.append({"role": "user", "content": query})

    llm_calls = traj.get("llm_calls", [])
    runtime_events = traj.get("runtime_events", [])

    # shopping tool calls
    for call in llm_calls:
        if call.get("stage") == "shopping" and call.get("phase") == "plan_tool_actions":
            try:
                m = re.search(r'\[[\s\S]*\]', call.get("output", ""))
                if m:
                    actions = json.loads(m.group())
                    tool_calls = [
                        {"id": f"call_{i}", "type": "function",
                         "function": {"name": a.get("name", ""), "arguments": json.dumps(a.get("arguments", {}))}}
                        for i, a in enumerate(actions)
                    ]
                    msgs.append({"role": "assistant", "content": "", "tool_calls": tool_calls})
            except Exception:
                pass
            break

    # tool observations
    for ev in runtime_events:
        if ev.get("event_type") != "observation":
            continue
        content = ev.get("payload", {}).get("content", {})
        callee = content.get("callee", "")
        if callee not in ["sku_recall", "scenario_related_recall"]:
            continue
        out = content.get("output", {})
        if isinstance(out, str):
            try:
                out = json.loads(out)
            except Exception:
                continue
        products = out.get("products", []) or []
        # 转成 evaluate.py 能识别的格式（有 index/title/price/key_specs）
        clean_products = [
            {
                "index": i + 1,
                "title": p.get("sku_name", p.get("title", "")),
                "price": float(p.get("final_price", p.get("price", 0)) or 0),
                "rating": p.get("good", ""),
                "sales": p.get("sales", ""),
                "key_specs": p.get("keyword", ""),
            }
            for i, p in enumerate(products[:6])
        ]
        tool_content = json.dumps(
            {"status": "SUCCESS", "count": len(clean_products), "products": clean_products},
            ensure_ascii=False
        )
        msgs.append({"role": "tool", "tool_call_id": "call_0", "content": tool_content})

    # final response
    final_text = ""
    for call in llm_calls:
        if call.get("stage") == "response" and call.get("phase") == "final_response_stream":
            output = call.get("output", "")
            clean = re.sub(r'<think>[\s\S]*?</think>', '', output).strip()
            if clean:
                final_text = clean
            break
    if not final_text:
        final_text = re.sub(
            r'<think>[\s\S]*?</think>', '',
            traj.get("final", {}).get("response", {}).get("output", {}).get("display_text", "")
        ).strip()
    if final_text:
        msgs.append({"role": "assistant", "content": final_text[:1000]})

    return msgs


def format_real_trajectory(traj: dict) -> str:
    """格式化真实轨迹为 judge 可读文本"""
    msgs = build_messages_from_real(traj)
    return _fmt_react(msgs)


def load_real_trajectories(real_dir: str) -> list[dict]:
    """加载所有真实轨迹"""
    trajs = []
    for path in Path(real_dir).glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                t = json.loads(line)
                if t.get("status") == "success":
                    trajs.append({"_source": "real", "_raw": t})
            except Exception:
                pass
    return trajs


def load_mock_trajectories(mock_file: str) -> list[dict]:
    """加载 mock 轨迹"""
    trajs = []
    for line in Path(mock_file).read_text(encoding="utf-8").splitlines():
        try:
            t = json.loads(line)
            if t.get("status") == "done":
                trajs.append({"_source": "mock", "_raw": t})
        except Exception:
            pass
    return trajs


def evaluate_one(item: dict, llm: LLMClient) -> dict | None:
    source = item["_source"]
    raw = item["_raw"]

    if source == "real":
        query = raw.get("request", {}).get("query", "")
        traj_text = format_real_trajectory(raw)
        tid = raw.get("trajectory_id", "?")
    else:
        query = raw.get("user_query", "")
        traj_text = format_react_trajectory(raw)
        tid = raw.get("trajectory_id", "?")

    if not query or not traj_text:
        return None

    prompt = JUDGE_PROMPT_TEMPLATE.format(user_query=query, trajectory_text=traj_text)
    try:
        content, _ = llm.generate(
            system_prompt=JUDGE_SYSTEM,
            user_prompt=prompt,
            max_tokens=800,
            temperature=0.1,
        )
        m = re.search(r'\{[\s\S]+\}', content)
        judge = json.loads(m.group() if m else content)
        score = compute_score(judge)
        return {
            "trajectory_id": tid,
            "source": source,
            "query": query,
            "score": score,
            "judge": judge,
        }
    except Exception as e:
        return {"trajectory_id": tid, "source": source, "query": query, "score": -1, "error": str(e)}


# ── 主流程 ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-dir",  default="sft_data/training-data/data/trajectories")
    parser.add_argument("--mock-file", default="sft_data/trajectories_react.jsonl")
    parser.add_argument("-n",  type=int, default=50,  help="每批抽样条数")
    parser.add_argument("-c",  type=int, default=4,   help="并发数")
    parser.add_argument("--model", default="MiniMax-M3-joybuilder")
    parser.add_argument("--seed",  type=int, default=42)
    parser.add_argument("--output", default="sft_data/compare_results.jsonl")
    args = parser.parse_args()

    random.seed(args.seed)
    llm = LLMClient(model=args.model)
    write_lock = threading.Lock()
    output_path = Path(args.output)

    # 加载数据
    real_all  = load_real_trajectories(args.real_dir)
    mock_all  = load_mock_trajectories(args.mock_file)
    real_sample = random.sample(real_all,  min(args.n, len(real_all)))
    mock_sample = random.sample(mock_all,  min(args.n, len(mock_all)))
    all_items = real_sample + mock_sample

    print(f"[{datetime.now():%H:%M:%S}] 开始对比评估")
    print(f"  真实轨迹: {len(real_all)} 条 → 抽样 {len(real_sample)} 条")
    print(f"  mock轨迹: {len(mock_all)} 条 → 抽样 {len(mock_sample)} 条")
    print(f"  评估模型: {args.model}  并发: {args.c}")
    print()

    real_scores, mock_scores = [], []
    errors = 0

    with ThreadPoolExecutor(max_workers=args.c) as ex:
        futs = {ex.submit(evaluate_one, item, llm): item for item in all_items}
        for fut in as_completed(futs):
            res = fut.result()
            if res is None or res.get("score", -1) < 0:
                errors += 1
                continue

            src = res["source"]
            score = res["score"]
            query_short = res["query"][:40]

            d1 = res.get("judge", {}).get("d1_need_understanding", {}).get("verdict", "?")
            d4 = res.get("judge", {}).get("d4_completeness", {}).get("verdict", "?")
            tag = "R" if src == "real" else "M"
            print(f"  [{tag}] {score:.2f}  D1={d1}  D4={d4}  {query_short}")

            if src == "real":
                real_scores.append(score)
            else:
                mock_scores.append(score)

            with write_lock:
                with open(output_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(res, ensure_ascii=False) + "\n")

    # 汇总
    print()
    print("=" * 60)
    print("对比结果汇总")
    print("=" * 60)

    def stats(scores, label):
        if not scores:
            print(f"  {label}: 无有效数据")
            return
        avg = sum(scores) / len(scores)
        full = sum(1 for s in scores if s == 1.0)
        hi   = sum(1 for s in scores if s >= 0.8)
        lo   = sum(1 for s in scores if s < 0.6)
        print(f"  {label}:")
        print(f"    条数={len(scores)}  均分={avg:.3f}  满分={full}({full*100//len(scores)}%)"
              f"  ≥0.8={hi}({hi*100//len(scores)}%)  <0.6={lo}({lo*100//len(scores)}%)")

    stats(real_scores, "真实轨迹 (real)")
    stats(mock_scores, "mock轨迹  (mock)")

    if real_scores and mock_scores:
        diff = sum(mock_scores)/len(mock_scores) - sum(real_scores)/len(real_scores)
        print()
        print(f"  mock均分 {'高于' if diff > 0 else '低于'} 真实轨迹 {abs(diff):.3f} 分")

    print(f"\n  评估失败: {errors} 条")
    print(f"  详细结果 → {output_path}")


if __name__ == "__main__":
    main()
