#!/usr/bin/env python3
"""批量检查轨迹数据质量,输出报告。"""
import json, re, sys
from collections import Counter

def check_one(d, idx):
    """检查单条轨迹,返回 (pass:bool, issues:list[str], meta:dict)"""
    issues = []
    meta = {
        "idx": idx,
        "query": (d.get("request") or {}).get("query", "")[:80],
        "status": d.get("status"),
        "llm_calls": len(d.get("llm_calls", [])),
        "runtime_events": len(d.get("runtime_events", [])),
    }

    # 1. 基本状态检查
    if d.get("status") != "success":
        issues.append(f"status={d.get('status')}(非 success)")

    llm_calls = d.get("llm_calls", [])
    events = d.get("runtime_events", [])

    # 2. 至少要有 shopping 阶段和 response 阶段
    stages = [c.get("stage") for c in llm_calls]
    if "shopping" not in stages:
        issues.append("缺少 shopping 阶段")
    if "response" not in stages:
        issues.append("缺少 response 阶段")

    # 3. 找 shopping/plan_tool_actions 的 think
    shop_calls = [c for c in llm_calls if c.get("stage") == "shopping" and c.get("phase") == "plan_tool_actions"]
    shop_think_len = 0
    if shop_calls:
        out = shop_calls[0].get("output", "")
        if isinstance(out, str):
            m = re.match(r"<think>([\s\S]*?)</think>", out)
            shop_think_len = len(m.group(1)) if m else 0
    meta["shop_think_len"] = shop_think_len

    # 4. 找 response/final_response_stream 的 think
    resp_calls = [c for c in llm_calls if c.get("stage") == "response"]
    final_think_len = 0
    final_ans = ""
    if resp_calls:
        out = resp_calls[-1].get("output", "")
        if isinstance(out, str):
            m = re.match(r"<think>([\s\S]*?)</think>\s*([\s\S]*)$", out)
            if m:
                final_think_len = len(m.group(1))
                final_ans = m.group(2).strip()
            else:
                final_ans = out.strip()
    meta["final_think_len"] = final_think_len

    if shop_think_len == 0:
        issues.append("shopping <think> 为空")
    if final_think_len == 0:
        issues.append("final response <think> 为空")

    # 5. Product ID 一致性检查
    # 从 response 阶段 input messages 里提取 product 定义
    product_defs = {}  # num -> {title, price}
    if resp_calls:
        msgs = resp_calls[-1].get("messages", [])
        all_input = " ".join(m.get("content", "") for m in msgs)
        blocks = re.findall(r"\[product (\d+) begin\]([\s\S]*?)\[product \1 end\]", all_input)
        for num, body in blocks:
            title_m = re.search(r"title:\s*(.+)", body)
            price_m = re.search(r"final_price:\s*(\S+)", body)
            product_defs[num] = {
                "title": title_m.group(1).strip()[:60] if title_m else "",
                "price": price_m.group(1) if price_m else "",
            }

    # 从 final answer 里提取 [product:N] 引用
    refs = re.findall(r"\[product:(\d+)\]", final_ans)
    meta["n_product_refs"] = len(refs)
    meta["n_product_defs"] = len(product_defs)

    # 检查越界
    for r in set(refs):
        if r not in product_defs:
            issues.append(f"[product:{r}] 越界引用(无定义)")

    # 检查品牌名 vs 编号一致性
    segs = re.split(r"(\[product:\d+\])", final_ans)
    for i, seg in enumerate(segs):
        m = re.match(r"\[product:(\d+)\]", seg)
        if m and i > 0:
            num = m.group(1)
            prev = segs[i-1]
            # 找前一段最后一个 **brand** 标记
            brands = re.findall(r"\*\*(.+?)\*\*", prev)
            if brands and num in product_defs:
                mentioned_brand = brands[-1].lower()
                defined_title = product_defs[num]["title"].lower()
                # 取品牌名第一个词对比
                mb_first = mentioned_brand.split()[0].rstrip(",.:;")
                dt_first = defined_title.split()[0].rstrip(",.:;")
                # 如果品牌名第一个词不匹配定义 title 第一个词
                if mb_first != dt_first and mb_first not in defined_title and dt_first not in mentioned_brand:
                    issues.append(
                        f"[product:{num}] 品牌名不匹配: 描述=\"{brands[-1][:40]}\" vs 定义=\"{product_defs[num]['title'][:40]}\""
                    )

    # 6. 检查 tool call/response 成对
    tool_calls_ev = [e for e in events if e.get("event_type") == "tool_call"]
    tool_results_ev = [e for e in events if e.get("event_type") == "tool_result"]
    if len(tool_calls_ev) != len(tool_results_ev):
        issues.append(f"tool_call({len(tool_calls_ev)}) != tool_result({len(tool_results_ev)}) 不成对")

    passed = len(issues) == 0
    return passed, issues, meta


def main():
    fpath = sys.argv[1] if len(sys.argv) > 1 else "data/trajectories/input.jsonl"
    
    lines = open(fpath).read().splitlines()
    
    results = []
    pass_count = 0
    issue_counter = Counter()
    
    for idx, line in enumerate(lines):
        d = json.loads(line)
        passed, issues, meta = check_one(d, idx)
        results.append({"passed": passed, "issues": issues, "meta": meta})
        if passed:
            pass_count += 1
        for iss in issues:
            # 归类 issue
            key = iss.split(":")[0] if ":" in iss else iss[:30]
            issue_counter[key] += 1

    # 输出报告
    print(f"=" * 70)
    print(f"轨迹质量检查报告")
    print(f"源文件: {fpath}")
    print(f"总条数: {len(lines)}")
    print(f"通过: {pass_count}/{len(lines)} ({100*pass_count/len(lines):.1f}%)")
    print(f"有问题: {len(lines)-pass_count}/{len(lines)} ({100*(len(lines)-pass_count)/len(lines):.1f}%)")
    print(f"=" * 70)
    
    print(f"\n## 问题分类统计")
    for iss, cnt in issue_counter.most_common():
        print(f"  {cnt:3d} 条 | {iss}")
    
    print(f"\n## 有问题的条目明细")
    for r in results:
        if not r["passed"]:
            m = r["meta"]
            print(f"\n  [{m['idx']:3d}] query=\"{m['query']}\"")
            print(f"       status={m['status']} shop_think={m['shop_think_len']} final_think={m['final_think_len']}")
            for iss in r["issues"]:
                print(f"       ❌ {iss}")
    
    print(f"\n## Think 长度统计")
    shop_thinks = [r["meta"]["shop_think_len"] for r in results]
    final_thinks = [r["meta"]["final_think_len"] for r in results]
    print(f"  shopping think: min={min(shop_thinks)} max={max(shop_thinks)} avg={sum(shop_thinks)//len(shop_thinks)} zero_count={shop_thinks.count(0)}")
    print(f"  final think:    min={min(final_thinks)} max={max(final_thinks)} avg={sum(final_thinks)//len(final_thinks)} zero_count={final_thinks.count(0)}")
    
    print(f"\n## 通过的条目 query 前 10 条")
    passed_items = [r for r in results if r["passed"]]
    for r in passed_items[:10]:
        m = r["meta"]
        print(f"  [{m['idx']:3d}] \"{m['query']}\" (shop_think={m['shop_think_len']}, final_think={m['final_think_len']}, products={m['n_product_refs']})")


if __name__ == "__main__":
    main()
