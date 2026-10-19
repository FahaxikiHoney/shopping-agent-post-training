#!/usr/bin/env python3
"""批量检查轨迹数据质量 v2——修正 event_type 匹配,优化品牌检查逻辑。"""
import json, re, sys
from collections import Counter

def check_one(d, idx):
    """检查单条轨迹,返回 (pass:bool, issues:list[str], warnings:list[str], meta:dict)"""
    issues = []    # 硬伤:必须修/丢
    warnings = []  # 软伤:可接受但不完美
    meta = {
        "idx": idx,
        "query": (d.get("request") or {}).get("query", "")[:80],
        "status": d.get("status"),
        "llm_calls": len(d.get("llm_calls", [])),
        "runtime_events": len(d.get("runtime_events", [])),
    }

    # 1. 基本状态
    if d.get("status") != "success":
        issues.append(f"status={d.get('status')}")

    llm_calls = d.get("llm_calls", [])
    events = d.get("runtime_events", [])

    # 2. 阶段完整性
    stages = [c.get("stage") for c in llm_calls]
    if "shopping" not in stages:
        issues.append("缺少 shopping 阶段")
    if "response" not in stages:
        issues.append("缺少 response 阶段")

    # 3. Tool call / observation 成对检查(正确的 event_type)
    n_tool_call = sum(1 for e in events if e.get("event_type") == "tool_call")
    n_observation = sum(1 for e in events if e.get("event_type") == "observation")
    if n_tool_call != n_observation:
        issues.append(f"tool_call({n_tool_call}) != observation({n_observation}) 不成对")
    meta["n_tool_calls"] = n_tool_call
    meta["n_observations"] = n_observation

    # 4. Think 检查
    shop_calls = [c for c in llm_calls if c.get("stage") == "shopping" and c.get("phase") == "plan_tool_actions"]
    shop_think_len = 0
    if shop_calls:
        out = shop_calls[0].get("output", "")
        if isinstance(out, str):
            m = re.match(r"<think>([\s\S]*?)</think>", out)
            shop_think_len = len(m.group(1)) if m else 0
    meta["shop_think_len"] = shop_think_len

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
        warnings.append("shopping <think> 为空")
    if final_think_len == 0:
        warnings.append("final response <think> 为空")

    # 5. Product ID 一致性——区分硬伤(张冠李戴)和软伤(描述性标题)
    product_defs = {}
    if resp_calls:
        msgs = resp_calls[-1].get("messages", [])
        all_input = " ".join(m.get("content", "") for m in msgs)
        blocks = re.findall(r"\[product (\d+) begin\]([\s\S]*?)\[product \1 end\]", all_input)
        for num, body in blocks:
            title_m = re.search(r"title:\s*(.+)", body)
            brand_m = re.search(r"brand(?:_name)?:\s*(.+)", body)
            price_m = re.search(r"final_price:\s*(\S+)", body)
            product_defs[num] = {
                "title": title_m.group(1).strip()[:80] if title_m else "",
                "brand": brand_m.group(1).strip()[:40] if brand_m else "",
                "price": price_m.group(1) if price_m else "",
            }

    refs = re.findall(r"\[product:(\d+)\]", final_ans)
    meta["n_product_refs"] = len(refs)
    meta["n_product_defs"] = len(product_defs)

    # 越界引用
    for r in set(refs):
        if r not in product_defs:
            issues.append(f"[product:{r}] 越界引用(无定义)")

    # 品牌/产品名一致性
    segs = re.split(r"(\[product:\d+\])", final_ans)
    for i, seg in enumerate(segs):
        m = re.match(r"\[product:(\d+)\]", seg)
        if not m or i == 0:
            continue
        num = m.group(1)
        if num not in product_defs:
            continue
        prev = segs[i-1]
        brands = re.findall(r"\*\*(.+?)\*\*", prev)
        if not brands:
            continue
        mentioned = brands[-1].strip()
        defined_title = product_defs[num]["title"]
        defined_brand = product_defs[num]["brand"]

        # 判断"描述性标题" vs "实际品牌/产品名"
        # 描述性标题特征:含中文功能词、不含英文品牌名
        descriptive_patterns = [
            r"款$", r"型$", r"版$", r"类$", r"系列$",
            r"推荐", r"首选", r"入门", r"旗舰", r"性价比",
            r"Option", r"Pick", r"Choice", r"Budget",
            r"€$", r"\$$", r"£$",  # 以价格结尾
        ]
        is_descriptive = any(re.search(p, mentioned) for p in descriptive_patterns)

        if is_descriptive:
            # 描述性标题不算硬伤,只是风格差异
            continue

        # 检查是否与其他 product 的品牌/标题更匹配(张冠李戴)
        mentioned_lower = mentioned.lower()
        # 品牌首词
        m_words = set(re.findall(r'[a-zA-Z\u4e00-\u9fff]+', mentioned_lower))
        d_words = set(re.findall(r'[a-zA-Z\u4e00-\u9fff]+', defined_title.lower()))
        b_words = set(re.findall(r'[a-zA-Z\u4e00-\u9fff]+', defined_brand.lower()))

        # 如果 mentioned 和 defined 至少有一个关键词重合,认为匹配
        overlap = m_words & (d_words | b_words)
        if overlap:
            continue  # 匹配上了

        # 检查是否匹配了其他 product 的定义(真·张冠李戴)
        best_other = None
        best_overlap = 0
        for other_num, other_def in product_defs.items():
            if other_num == num:
                continue
            o_words = set(re.findall(r'[a-zA-Z\u4e00-\u9fff]+', other_def["title"].lower()))
            ob_words = set(re.findall(r'[a-zA-Z\u4e00-\u9fff]+', other_def["brand"].lower()))
            ov = len(m_words & (o_words | ob_words))
            if ov > best_overlap:
                best_overlap = ov
                best_other = other_num

        if best_other and best_overlap >= 1:
            issues.append(
                f"[product:{num}] 张冠李戴: \"{mentioned[:35]}\" 应该是 product:{best_other}(\"{product_defs[best_other]['title'][:35]}\")"
            )
        else:
            # 不匹配当前也不匹配其他——可能是模型自己编的描述词
            warnings.append(
                f"[product:{num}] 标题不匹配定义: \"{mentioned[:35]}\" vs \"{defined_title[:35]}\""
            )

    passed = len(issues) == 0
    return passed, issues, warnings, meta


def main():
    fpath = sys.argv[1] if len(sys.argv) > 1 else "data/trajectories/input.jsonl"
    lines = open(fpath).read().splitlines()
    
    results = []
    pass_count = 0
    warn_only_count = 0
    issue_counter = Counter()
    warning_counter = Counter()
    
    for idx, line in enumerate(lines):
        d = json.loads(line)
        passed, issues, warnings, meta = check_one(d, idx)
        results.append({"passed": passed, "issues": issues, "warnings": warnings, "meta": meta})
        if passed:
            pass_count += 1
            if warnings:
                warn_only_count += 1
        for iss in issues:
            key = re.sub(r'".+?"', '"..."', iss)[:50]
            issue_counter[key] += 1
        for w in warnings:
            key = re.sub(r'".+?"', '"..."', w)[:50]
            warning_counter[key] += 1

    # 报告
    print("=" * 70)
    print("轨迹质量检查报告 v2")
    print(f"源文件: {fpath}")
    print(f"总条数: {len(lines)}")
    print(f"✅ 通过(无硬伤): {pass_count}/{len(lines)} ({100*pass_count/len(lines):.1f}%)")
    print(f"   其中仅有软性警告: {warn_only_count}")
    print(f"❌ 有硬伤需处理: {len(lines)-pass_count}/{len(lines)} ({100*(len(lines)-pass_count)/len(lines):.1f}%)")
    print("=" * 70)
    
    print(f"\n## 硬伤分类(必须修或丢)")
    for iss, cnt in issue_counter.most_common():
        print(f"  {cnt:3d} 条 | {iss}")
    
    print(f"\n## 软性警告(可接受)")
    for w, cnt in warning_counter.most_common():
        print(f"  {cnt:3d} 条 | {w}")
    
    print(f"\n## 有硬伤的条目明细")
    for r in results:
        if not r["passed"]:
            m = r["meta"]
            print(f"\n  [{m['idx']:3d}] query=\"{m['query']}\"")
            for iss in r["issues"]:
                print(f"       ❌ {iss}")
    
    print(f"\n## Think 长度统计")
    shop_thinks = [r["meta"]["shop_think_len"] for r in results]
    final_thinks = [r["meta"]["final_think_len"] for r in results]
    print(f"  shopping think: min={min(shop_thinks)} max={max(shop_thinks)} avg={sum(shop_thinks)//len(shop_thinks)} zero={shop_thinks.count(0)}")
    print(f"  final think:    min={min(final_thinks)} max={max(final_thinks)} avg={sum(final_thinks)//len(final_thinks)} zero={final_thinks.count(0)}")
    
    print(f"\n## 通过的前 15 条")
    for r in [r for r in results if r["passed"]][:15]:
        m = r["meta"]
        w = f" ⚠️{len(r['warnings'])}warn" if r["warnings"] else ""
        print(f"  [{m['idx']:3d}] \"{m['query'][:50]}\" shop_think={m['shop_think_len']} final_think={m['final_think_len']} products={m['n_product_refs']}{w}")


if __name__ == "__main__":
    main()
