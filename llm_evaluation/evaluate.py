# -*- coding: utf-8 -*-
"""
轨迹质量评估脚本 v2 — 适配 convert_trajectory_to_sft.py 输出格式 真实线上环境跑的

评估维度（每个 PASS/FAIL）：
  D1 需求理解          [gate] FAIL → 总分0
  D2 真实性与价格准确性
  D3 推荐相关性与选择质量
  D4 回应完整性与推荐充分性 [gate] FAIL → 总分0
  D5 推荐理由价值感

Gate graders（规则型）：
  G1 card_id_validator  — [product:X] 引用的 index 必须在工具返回的商品范围内
  G3 text_quality       — 最终回复无乱码/无 thinking 泄漏
"""
from __future__ import annotations

import json
import re
import sys
import time
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from joybuy_agent.llm.client import LLMClient

WRITE_LOCK = threading.Lock()

# ─────────────────────────────────────────────────────────────────────────────
# Judge Prompt
# ─────────────────────────────────────────────────────────────────────────────
JUDGE_SYSTEM = """你是一位专业的电商购物助手质量评估专家，负责评估AI购物助手的回复质量。
你必须严格按照指定的JSON格式输出，不输出任何其他内容。"""

JUDGE_PROMPT_TEMPLATE = """请评估以下购物助手的完整执行轨迹质量。

## 任务类型
{scenario_type}

## 用户请求
{user_query}

## 完整执行轨迹
{trajectory_text}

## 工具字段解释

- `final_price` 是当前到手价，`original_price` 是原价，`sales` 是销量；这些字段均可直接用于回复。
- 工具价格数字不携带币种时，助手可以根据站点语言使用对应的本地币种符号；只要数值一致，不应判为价格错误。
- 商品编号按所有工具返回商品的全局出现顺序累计，与 `[product:X]` 一致。

## 评估维度说明

**D1 需求理解** [硬门槛]
判断助手是否正确识别了用户意图：
- PASS：识别了品类、场景、预算等核心约束；若搜索无货，理解需要推替代品
- FAIL：误解品类（如用户要椅子推了桌子）；忽略明确预算约束；无货时未尝试推替代品

**D2 真实性与价格准确性**
判断回复中的信息是否有依据：
- PASS：价格与工具返回一致；规格描述是工具返回信息的合理转述或基于商品类别的行业常识推断
- FAIL：价格与工具返回明显不符（差距超过10%）；捏造需要数据支撑的具体说法（如具体认证、具体数字但工具未提供的声明）
- 注意：用商品名称和品牌信息改写成自然语言属于正常转述；基于商品品类常识的描述属于合理推断，不算幻觉

**D3 推荐相关性**
判断推荐商品与需求的匹配程度：
- PASS：推荐商品品类正确，价格在预算内；无货时替代品与原商品同品类或高度相关
- FAIL：品类明显不符；无货替代品与原商品完全不相关

**D4 回应完整性** [硬门槛]
判断任务是否完成：
- PASS：有[product:X]商卡标签；推荐了至少1款商品；无货场景下说明了无货原因并推荐替代品
- FAIL：没有[product:X]标签；有工具结果但没推荐任何商品；对话戛然而止
- 特殊情况：如果工具确实返回0款商品(count=0)且助手合理说明了情况，视为PASS
- direct_response 特殊情况：非购物请求、隐私越权请求、缺少图片无法识别、商品使用或安全问答，不要求调用商品工具或输出商卡；只要回复准确、安全并给出可执行下一步，即视为PASS

**D5 推荐理由价值感**
判断推荐理由是否有实质内容：
- PASS：推荐理由包含具体参数数值或具体使用场景分析
- FAIL：理由全是空泛话术如"性价比高"、"质量好"，没有任何具体信息

## 输出格式（严格JSON，不输出其他内容）
{{
  "d1_need_understanding": {{"verdict": "PASS或FAIL", "reason": "一句话，说明通过或失败的具体原因"}},
  "d2_factual_accuracy": {{"verdict": "PASS或FAIL", "reason": "一句话，若FAIL需指出具体捏造内容"}},
  "d3_recommendation_quality": {{"verdict": "PASS或FAIL", "reason": "一句话，说明品类/价格/相关性是否匹配"}},
  "d4_completeness": {{"verdict": "PASS或FAIL", "reason": "一句话，说明商卡和推荐完整性"}},
  "d5_recommendation_value": {{"verdict": "PASS或FAIL", "reason": "一句话，说明理由是否具体"}},
  "overall_comment": "一句话概括整体质量"
}}"""


# ─────────────────────────────────────────────────────────────────────────────
# 轨迹格式化（给 judge 看的可读版本）
# ─────────────────────────────────────────────────────────────────────────────
def format_trajectory(messages: list) -> str:
    """将 messages 转为 judge 可读的文本格式"""
    parts = []
    product_index = 0
    for msg in messages:
        role = msg["role"]
        if role == "system":
            continue
        elif role == "user":
            parts.append(f"【用户】{msg['content']}")
        elif role == "assistant":
            tc = msg.get("tool_calls", [])
            content = (msg.get("content") or "").strip()
            if tc:
                # 展示所有 tool_calls
                tool_lines = []
                for t in tc:
                    fn = t["function"]
                    args = fn["arguments"]
                    try:
                        args = json.dumps(json.loads(args), ensure_ascii=False)
                    except Exception:
                        pass
                    tool_lines.append(f"  • {fn['name']}({args})")
                parts.append(f"【助手调用工具】\n" + "\n".join(tool_lines))
            else:
                # 去掉 <think> 标签，只保留正文给 judge
                clean = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
                if clean:
                    parts.append(f"【助手最终回复】\n{clean}")
        elif role == "tool":
            name = msg.get("name", "?")
            try:
                r = json.loads(msg["content"])
                prods = r.get("products", [])
                count = r.get("count", len(prods))
                if prods:
                    prod_lines = []
                    for p in prods[:8]:
                        product_index += 1
                        title = p.get("sku_name") or p.get("title") or "?"
                        final_price = p.get("final_price") or p.get("price") or "?"
                        original_price = p.get("price") or ""
                        brand = p.get("brand_name") or p.get("brand") or ""
                        specs = p.get("key_specs") or p.get("good") or ""
                        sales = p.get("sales") or ""
                        keyword = p.get("keyword") or ""
                        match_reason = p.get("match_reason") or ""
                        fields = [f"final_price={final_price}"]
                        if original_price:
                            fields.append(f"original_price={original_price}")
                        if sales:
                            fields.append(f"sales={sales}")
                        if keyword:
                            fields.append(f"keyword={keyword}")
                        if specs:
                            fields.append(f"specs={str(specs)[:80]}")
                        if match_reason:
                            fields.append(f"match_reason={str(match_reason)[:80]}")
                        identity = " ".join(
                            part for part in (str(brand).strip(), str(title)[:80].strip())
                            if part
                        )
                        prod_lines.append(
                            f"  [{product_index}] {identity} | " + " | ".join(fields)
                        )
                    parts.append(
                        f"【工具返回 {name} — {count}款商品】\n" + "\n".join(prod_lines)
                    )
                elif count == 0:
                    parts.append(f"【工具返回 {name}】无结果(count=0)")
                else:
                    parts.append(f"【工具返回 {name}】{msg['content'][:300]}")
            except Exception:
                parts.append(f"【工具返回 {name}】{msg['content'][:300]}")
    return "\n\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Gate Graders（规则型）
# ─────────────────────────────────────────────────────────────────────────────
def check_card_id_validator(messages: list, final_response: str) -> dict:
    """G1: [product:X] 引用的编号必须在工具返回的商品数量范围内"""
    # 统计工具返回的总商品数(按出现顺序，1-based)
    total_products = 0
    for msg in messages:
        if msg["role"] == "tool":
            try:
                r = json.loads(msg["content"])
                prods = r.get("products", [])
                total_products += len(prods)
            except Exception:
                pass

    # 提取 final response 里的 [product:N] 引用
    referenced = set()
    for m in re.finditer(r'\[product:(\d+)\]', final_response):
        referenced.add(int(m.group(1)))

    if not referenced and total_products > 0:
        # 检查模型是否在显式解释"不匹配/无货"——这是合理行为,不应视为 gate fail
        decline_signals = [
            "unfortunately", "sorry", "not available", "no result", "not match",
            "don't have", "cannot find", "couldn't find", "out of stock",
            "not correspond", "aucun", "leider", "helaas", "keine",
            "ne correspond", "nicht verfügbar", "niet beschikbaar",
            "无", "没有找到", "找不到", "不匹配", "暂无", "缺货",
        ]
        lower = final_response.lower()
        is_decline = any(sig in lower for sig in decline_signals)
        if is_decline:
            return {"pass": True, "reason": f"模型显式说明工具结果不匹配({total_products}款),合理拒绝推荐"}
        # 模型没解释也没推荐——可能是遗漏,交给 LLM judge 判断
        return {"pass": True, "reason": f"有{total_products}款工具返回但无商卡(交LLM judge评估D4)"}
    if not referenced and total_products == 0:
        return {"pass": True, "reason": "工具无结果，无需商卡标签"}

    # 检查引用是否越界
    invalid = [r for r in referenced if r < 1 or r > total_products]
    if invalid:
        return {"pass": False, "reason": f"商卡越界: {sorted(invalid)} (工具只返回了{total_products}款)"}

    return {"pass": True, "reason": f"商卡引用有效({len(referenced)}个, 范围1~{total_products})"}


def check_text_quality(final_response: str) -> dict:
    """G3: 最终回复是否有乱码或明显质量问题"""
    if not final_response or len(final_response) < 20:
        return {"pass": False, "reason": f"回复过短或为空({len(final_response or '')}字)"}
    # 乱码检测
    non_md = re.sub(r'[-=*# \n\|>_`\[\]]', '', final_response)
    if re.search(r'(.)\1{6,}', non_md):
        return {"pass": False, "reason": "疑似乱码（异常重复字符）"}
    # thinking 泄漏
    if "<think>" in final_response:
        return {"pass": False, "reason": "thinking 标签泄漏到最终回复"}
    return {"pass": True, "reason": "文本质量正常"}


# ─────────────────────────────────────────────────────────────────────────────
# 分数计算
# ─────────────────────────────────────────────────────────────────────────────
def compute_score(judge_result: dict) -> float:
    """带gate的加权分数计算"""
    d1 = judge_result.get("d1_need_understanding", {}).get("verdict") == "PASS"
    d2 = judge_result.get("d2_factual_accuracy", {}).get("verdict") == "PASS"
    d3 = judge_result.get("d3_recommendation_quality", {}).get("verdict") == "PASS"
    d4 = judge_result.get("d4_completeness", {}).get("verdict") == "PASS"
    d5 = judge_result.get("d5_recommendation_value", {}).get("verdict") == "PASS"

    if not d1 or not d4:
        return 0.0

    score = 0.40
    score += 0.20 if d2 else 0.0
    score += 0.20 if d3 else 0.0
    score += 0.15 if d4 else 0.0
    score += 0.05 if d5 else 0.0
    return round(score, 2)


# ─────────────────────────────────────────────────────────────────────────────
# 数据预处理：从我们的 SFT 格式提取评估所需字段
# ─────────────────────────────────────────────────────────────────────────────
def prepare_eval_input(sft_item: dict) -> dict:
    """从 convert_trajectory_to_sft 输出格式提取 evaluate 需要的字段"""
    messages = sft_item.get("messages", [])

    # 提取 final_response: 最后一条 assistant 消息,去掉 <think>
    final_response = ""
    for msg in reversed(messages):
        if msg["role"] == "assistant" and not msg.get("tool_calls"):
            content = msg.get("content", "")
            final_response = re.sub(r'<think>[\s\S]*?</think>\s*', '', content).strip()
            break

    # 推断 scenario_type
    tools_used = sft_item.get("metadata", {}).get("tools_used", [])
    query_lower = str(sft_item.get("user_query", "")).lower()
    direct_markers = (
        "which religion is the most correct", "fundamentally wrong",
        "请解读", "指的是谁", "不要脱敏", "mobile/email/address",
        "only have a photo", "alleen een foto", "ken de naam niet",
        "instead of water", "instead of milk", "can i use milk",
    )
    if not tools_used and any(marker in query_lower for marker in direct_markers):
        scenario = "direct_response"
    elif "promotion_coupon" in tools_used:
        scenario = "promotion"
    elif "scenario_related_recall" in tools_used and "sku_recall" not in tools_used:
        scenario = "matching"
    elif "web_search" in tools_used:
        scenario = "research_shopping"
    else:
        scenario = "search_recommend"

    return {
        "trajectory_id": sft_item.get("trajectory_id", "?"),
        "scenario_type": scenario,
        "user_query": sft_item.get("user_query", ""),
        "messages": messages,
        "final_response": final_response,
        "metadata": sft_item.get("metadata", {}),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 单条评估
# ─────────────────────────────────────────────────────────────────────────────
def parse_judge_response(content: str) -> dict:
    """从可能带代码块或前后文本的响应中提取 Judge JSON。"""
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    decoder = json.JSONDecoder()
    required = {
        "d1_need_understanding",
        "d2_factual_accuracy",
        "d3_recommendation_quality",
        "d4_completeness",
        "d5_recommendation_value",
    }
    for start, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and required.issubset(value):
            return value
    raise ValueError("Judge response does not contain a complete JSON object")


def evaluate_one(
    item: dict,
    llm: LLMClient,
    judge_retries: int = 3,
    retry_delay: float = 5.0,
) -> dict:
    tid = item["trajectory_id"]
    sc = item["scenario_type"]
    query = item["user_query"]
    messages = item["messages"]
    final_response = item["final_response"]

    result = {
        "trajectory_id": tid,
        "scenario_type": sc,
        "user_query": query,
    }

    # Gate graders
    g1 = check_card_id_validator(messages, final_response)
    g3 = check_text_quality(final_response)
    result["gate_card_id"] = g1
    result["gate_text_quality"] = g3

    if not g1["pass"] or not g3["pass"]:
        result["judge"] = None
        result["score"] = 0.0
        result["gate_fail"] = True
        return result

    result["gate_fail"] = False

    # LLM judge
    traj_text = format_trajectory(messages)
    user_prompt = JUDGE_PROMPT_TEMPLATE.format(
        scenario_type=sc,
        user_query=query,
        trajectory_text=traj_text,
    )

    last_error = None
    for attempt in range(1, judge_retries + 1):
        try:
            content, _ = llm.generate(
                system_prompt=JUDGE_SYSTEM,
                user_prompt=user_prompt,
                max_tokens=800,
                temperature=0.1,
            )
            judge = parse_judge_response(content)
            result["judge"] = judge
            result["score"] = compute_score(judge)
            result["judge_attempts"] = attempt
            return result
        except Exception as error:
            last_error = error
            if attempt < judge_retries:
                time.sleep(retry_delay * attempt)

    result["judge"] = {"error": str(last_error)[:200]}
    result["score"] = -1.0
    result["judge_attempts"] = judge_retries

    return result


# ─────────────────────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="评估 SFT 轨迹质量")
    parser.add_argument("--input", type=str,
                        default="sft_data/购物助手_思考链_100条.jsonl")
    parser.add_argument("-n", type=int, default=0, help="评估条数，0=全部")
    parser.add_argument("-c", type=int, default=3, help="并发数")
    parser.add_argument("--model", type=str, default="DeepSeek-R1",
                        help="Judge模型: DeepSeek-R1 / JoyAI-LLM-Flash / GLM-5.1")
    parser.add_argument("--output", type=str,
                        default="sft_data/eval_results.jsonl")
    parser.add_argument("--gate-only", action="store_true",
                        help="只跑规则gate,不调LLM")
    parser.add_argument("--judge-retries", type=int, default=3,
                        help="Judge请求或JSON解析失败时的最大尝试次数")
    parser.add_argument("--retry-delay", type=float, default=5.0,
                        help="Judge重试基础等待秒数，按尝试次数递增")
    args = parser.parse_args()

    data_raw = [json.loads(l) for l in Path(args.input).read_text().splitlines() if l.strip()]
    data = [prepare_eval_input(d) for d in data_raw]
    if args.n > 0:
        data = data[:args.n]

    output_path = Path(args.output)
    if output_path.exists():
        output_path.unlink()

    print(f"[{datetime.now():%H:%M:%S}] 开始评估 {len(data)} 条")
    print(f"  模型={args.model} | 并发={args.c} | gate_only={args.gate_only}")
    print(f"{'':5} {'场景':<22} {'分数':>6} {'D1':>4} {'D2':>4} {'D3':>4} {'D4':>4} {'D5':>4}")
    print("-" * 70)

    if args.gate_only:
        # 只跑规则型 gate,不调 LLM
        scores = []
        gate_fails = 0
        for item in data:
            g1 = check_card_id_validator(item["messages"], item["final_response"])
            g3 = check_text_quality(item["final_response"])
            passed = g1["pass"] and g3["pass"]
            if not passed:
                gate_fails += 1
                reason = g1["reason"] if not g1["pass"] else g3["reason"]
                print(f"  {'G':>4} {item['scenario_type']:<22} {0.0:>6.2f} ❌ {reason}")
                scores.append(0.0)
            else:
                scores.append(1.0)
            res = {
                "trajectory_id": item["trajectory_id"],
                "user_query": item["user_query"],
                "gate_card_id": g1,
                "gate_text_quality": g3,
                "gate_pass": passed,
            }
            with open(output_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")

        print(f"\n{'='*70}")
        print(f"Gate 检查完成: {len(data)}条 | 通过={len(data)-gate_fails} | 失败={gate_fails}")
        return

    # 完整评估(规则+LLM)
    llm = LLMClient(model=args.model)
    scores = []
    gate_fails = 0
    judge_errors = 0
    by_scene: dict = {}

    with ThreadPoolExecutor(max_workers=args.c) as ex:
        futs = {
            ex.submit(
                evaluate_one,
                d,
                llm,
                args.judge_retries,
                args.retry_delay,
            ): d
            for d in data
        }
        for fut in as_completed(futs):
            res = fut.result()
            sc = res["scenario_type"]
            score = res["score"]

            if score == -1.0:
                judge_errors += 1
                print(f"  {'✗':>4} {sc:<22} judge错误: {res.get('judge',{}).get('error','')[:50]}")
            elif res.get("gate_fail"):
                gate_fails += 1
                reason = res["gate_card_id"]["reason"] if not res["gate_card_id"]["pass"] else res["gate_text_quality"]["reason"]
                print(f"  {'G':>4} {sc:<22} {score:>6.2f} gate: {reason}")
            else:
                judge = res.get("judge", {})
                d1 = "✓" if judge.get("d1_need_understanding",{}).get("verdict")=="PASS" else "✗"
                d2 = "✓" if judge.get("d2_factual_accuracy",{}).get("verdict")=="PASS" else "✗"
                d3 = "✓" if judge.get("d3_recommendation_quality",{}).get("verdict")=="PASS" else "✗"
                d4 = "✓" if judge.get("d4_completeness",{}).get("verdict")=="PASS" else "✗"
                d5 = "✓" if judge.get("d5_recommendation_value",{}).get("verdict")=="PASS" else "✗"
                print(f"  {score:>5.2f} {sc:<22} {score:>6.2f} {d1:>4} {d2:>4} {d3:>4} {d4:>4} {d5:>4}  {res['user_query'][:30]}")

            scores.append(score)
            by_scene.setdefault(sc, []).append(score)

            with WRITE_LOCK:
                with open(output_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(res, ensure_ascii=False) + "\n")

    valid_scores = [s for s in scores if s >= 0]
    print(f"\n{'='*70}")
    print(f"评估完成: {len(data)}条 | gate失败={gate_fails} | judge错误={judge_errors}")
    if valid_scores:
        avg = sum(valid_scores)/len(valid_scores)
        print(f"平均分: {avg:.3f} | 最低: {min(valid_scores):.2f} | 最高: {max(valid_scores):.2f}")
        print(f"满分(1.0): {sum(1 for s in valid_scores if s==1.0)}条 | 零分: {sum(1 for s in valid_scores if s==0.0)}条")
        print(f"\n分场景平均分:")
        for sc, sc_scores in sorted(by_scene.items()):
            valid = [s for s in sc_scores if s >= 0]
            if valid:
                print(f"  {sc:<25} {sum(valid)/len(valid):.3f} ({len(valid)}条)")
    print(f"\n结果 → {output_path}")


if __name__ == "__main__":
    main()
