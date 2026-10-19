# -*- coding: utf-8 -*-
"""
轨迹质量评估脚本

核心评估器：trajectory_response_quality_grader
用强模型作为 judge，从用户体验角度对 agent 完整轨迹打分。

5个维度（每个 PASS/FAIL）：
  D1 需求理解          [gate] FAIL → 总分0
  D2 真实性与价格准确性
  D3 推荐相关性与选择质量
  D4 回应完整性与推荐充分性 [gate] FAIL → 总分0
  D5 推荐理由价值感

聚合方式（带gate）：
  D1 or D4 FAIL → score=0
  否则 score = 0.4 + D2*0.2 + D3*0.2 + D4*0.15 + D5*0.05
  满分 = 1.0

Gate graders（规则型）：
  G1 card_id_validator       — [product:X] 引用的 index 必须在工具返回中存在
  G2 tool_call_failure_rate  — 工具调用参数错误直接0分
  G3 text_quality_penalty    — 最终回复有乱码/语义不通
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

sys.path.insert(0, str(Path(__file__).parent.parent))
from joybuy_agent.llm.client import LLMClient

OUTPUT = Path(__file__).parent / "eval_results.jsonl"
WRITE_LOCK = threading.Lock()

# ─────────────────────────────────────────────────────────────────────────────
# Judge Prompt
# ─────────────────────────────────────────────────────────────────────────────
JUDGE_SYSTEM = """你是一位专业的电商购物助手质量评估专家，负责评估AI购物助手的回复质量。
你必须严格按照指定的JSON格式输出，不输出任何其他内容。"""

JUDGE_PROMPT_TEMPLATE = """请评估以下购物助手的完整执行轨迹质量。

## 用户请求
{user_query}

## 完整执行轨迹
{trajectory_text}

## 评估维度说明

**D1 需求理解** [硬门槛]
判断助手是否正确识别了用户意图：
- PASS：识别了品类、场景、预算等核心约束；若搜索无货，理解需要推替代品
- FAIL：误解品类（如用户要椅子推了桌子）；忽略明确预算约束；无货时未尝试推替代品

**D2 真实性与价格准确性**
判断回复中的信息是否有依据：
- PASS：价格与工具返回一致；规格描述是工具key_specs的合理转述或基于商品类别的行业常识推断（如弹力带有阻力范围、头戴式耳机物理隔音好、跑步鞋有缓震技术等）
- FAIL：价格与工具返回明显不符（差距超过10%）；捏造需要数据支撑的具体说法（如"获得BIFMA认证"、"20万用户验证"、"比前代提升30%"等有具体数字但工具未提供的声明）
- 注意：用工具key_specs改写成自然语言属于正常转述；基于商品品类常识的描述（如"天然橡胶防滑"、"弹力带覆盖多档阻力"）属于合理推断，不算幻觉

**D3 推荐相关性**
判断推荐商品与需求的匹配程度：
- PASS：推荐商品品类正确，价格在预算内；无货时替代品与原商品同品类或高度相关
- FAIL：品类明显不符；无货替代品与原商品完全不相关（如用户要高端降噪耳机，推了廉价蓝牙耳机）

**D4 回应完整性** [硬门槛]
判断任务是否完成：
- PASS：有[product:X]商卡标签；推荐了至少1款商品；无货场景下说明了无货原因并推荐替代品
- FAIL：没有[product:X]标签；有工具结果但没推荐任何商品；对话戛然而止

**D5 推荐理由价值感**
判断推荐理由是否有实质内容：
- PASS：推荐理由包含具体参数数值（"42dB降噪"、"7.5h续航"）或具体使用场景（"适合久坐办公"、"跑步运动专用"）
- FAIL：理由全是空泛话术如"性价比高"、"质量好"、"非常值得购买"，没有任何具体信息

## 输出格式（严格JSON，不输出其他内容）
{{
  "d1_need_understanding": {{"verdict": "PASS或FAIL", "reason": "一句话，说明通过或失败的具体原因"}},
  "d2_factual_accuracy": {{"verdict": "PASS或FAIL", "reason": "一句话，若FAIL需指出具体捏造内容"}},
  "d3_recommendation_quality": {{"verdict": "PASS或FAIL", "reason": "一句话，说明品类/价格/相关性是否匹配"}},
  "d4_completeness": {{"verdict": "PASS或FAIL", "reason": "一句话，说明商卡和推荐完整性"}},
  "d5_recommendation_value": {{"verdict": "PASS或FAIL", "reason": "一句话，说明理由是否具体"}},
  "overall_comment": "参考线上评测风格，一句话概括：品类命中情况+主要问题（如：3款保温杯全部在预算内，但推荐理由缺少具体保温参数）"
}}"""


# ─────────────────────────────────────────────────────────────────────────────
# 轨迹格式化（给 judge 看的可读版本）
# ─────────────────────────────────────────────────────────────────────────────
def format_trajectory(messages: list) -> str:
    parts = []
    for msg in messages:
        role = msg["role"]
        if role == "system":
            continue  # judge 不需要看 system prompt
        elif role == "user":
            parts.append(f"【用户】{msg['content']}")
        elif role == "assistant":
            tc = msg.get("tool_calls", [])
            content = (msg.get("content") or "").strip()
            if tc:
                fn = tc[0]["function"]
                args = fn["arguments"]
                try:
                    args = json.dumps(json.loads(args), ensure_ascii=False)
                except Exception:
                    pass
                parts.append(f"【助手调用工具】{fn['name']}\n参数：{args}")
            else:
                # 去掉 <think> 标签，只保留正文
                clean = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
                if clean:
                    parts.append(f"【助手最终回复】\n{clean}")
        elif role == "tool":
            try:
                r = json.loads(msg["content"])
                prods = r.get("products", [])
                if prods:
                    prod_lines = "\n".join(
                        f"  [{p.get('index','-')}] {p['title']} ¥{p['price']} {p.get('rating','')}分 {p.get('sales','')} | {p.get('key_specs','')}"
                        for p in prods[:6]
                    )
                    parts.append(f"【工具返回 {len(prods)}款商品】\n{prod_lines}")
                elif r.get("summary"):
                    parts.append(f"【工具返回】{r['summary']}")
                else:
                    parts.append(f"【工具返回】{msg['content'][:200]}")
            except Exception:
                parts.append(f"【工具返回】{msg['content'][:200]}")
    return "\n\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Gate Graders（规则型）
# ─────────────────────────────────────────────────────────────────────────────
def check_card_id_validator(messages: list, final_response: str) -> dict:
    """G1: [product:X] 引用的 index 必须在工具返回中存在"""
    valid_indexes = set()
    for msg in messages:
        if msg["role"] == "tool":
            try:
                r = json.loads(msg["content"])
                for p in r.get("products", []):
                    if "index" in p:
                        valid_indexes.add(p["index"])
            except Exception:
                pass

    referenced = set()
    for m in re.finditer(r'\[product:(\d+)\]', final_response):
        referenced.add(int(m.group(1)))

    hallucinated = referenced - valid_indexes
    if hallucinated:
        return {"pass": False, "reason": f"商卡幻觉: index {sorted(hallucinated)} 不在工具返回中"}
    if not referenced and valid_indexes:
        return {"pass": False, "reason": "有工具返回但没有[product:X]标签"}
    return {"pass": True, "reason": "商卡index全部有效"}


def check_text_quality(final_response: str) -> dict:
    """G3: 最终回复是否有乱码或明显质量问题"""
    if len(final_response) < 30:
        return {"pass": False, "reason": f"回复过短({len(final_response)}字)"}
    # 乱码检测：排除 Markdown 常见符号（-/=/*/空格），只检测异常中文/字母重复
    non_md = re.sub(r'[-=*# \n\|]', '', final_response)
    if re.search(r'(.)\1{5,}', non_md):
        return {"pass": False, "reason": "疑似乱码（异常重复字符）"}
    # thinking 泄漏检测
    if len(final_response) > 800 and "[product:" not in final_response:
        return {"pass": False, "reason": f"回复过长({len(final_response)}字)且无商卡标签，疑似thinking泄漏"}
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

    # Gate check
    if not d1 or not d4:
        return 0.0

    # 基础分 + 加权
    score = 0.40  # D1+D4 都PASS的基础分
    score += 0.20 if d2 else 0.0
    score += 0.20 if d3 else 0.0
    score += 0.15 if d4 else 0.0  # D4 加权（gate已过）
    score += 0.05 if d5 else 0.0
    return round(score, 2)


# ─────────────────────────────────────────────────────────────────────────────
# 单条评估
# ─────────────────────────────────────────────────────────────────────────────
def evaluate_one(traj_dict: dict, llm: LLMClient) -> dict:
    tid = traj_dict.get("trajectory_id", "?")
    sc = traj_dict.get("scenario_type", "?")
    query = traj_dict.get("user_query", "")
    messages = traj_dict.get("messages", [])
    final_response = traj_dict.get("final_response", "")

    result = {
        "trajectory_id": tid,
        "scenario_type": sc,
        "user_query": query,
        "total_steps": traj_dict.get("total_steps", 0),
    }

    # Gate graders（规则型，不调LLM）
    g1 = check_card_id_validator(messages, final_response)
    g3 = check_text_quality(final_response)
    result["gate_card_id"] = g1
    result["gate_text_quality"] = g3

    # 规则gate失败，不调LLM，直接0分
    if not g1["pass"] or not g3["pass"]:
        result["judge"] = None
        result["score"] = 0.0
        result["gate_fail"] = True
        return result

    result["gate_fail"] = False

    # LLM judge
    traj_text = format_trajectory(messages)
    user_prompt = JUDGE_PROMPT_TEMPLATE.format(
        user_query=query,
        trajectory_text=traj_text,
    )

    try:
        content, _ = llm.generate(
            system_prompt=JUDGE_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=800,
            temperature=0.1,
        )
        # 解析JSON
        m = re.search(r'\{[\s\S]+\}', content)
        if m:
            judge = json.loads(m.group())
        else:
            judge = json.loads(content)

        result["judge"] = judge
        result["score"] = compute_score(judge)
    except Exception as e:
        result["judge"] = {"error": str(e)[:100]}
        result["score"] = -1.0  # -1 表示评估失败

    return result


# ─────────────────────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  type=str, default="sft_data/trajectories_react.jsonl")
    parser.add_argument("-n",       type=int, default=50,  help="评估条数，0表示全部")
    parser.add_argument("-c",       type=int, default=2,   help="并发数")
    parser.add_argument("--model",  type=str, default="DeepSeek-R1")
    parser.add_argument("--output", type=str, default="sft_data/eval_results.jsonl")
    args = parser.parse_args()

    data = [json.loads(l) for l in Path(args.input).read_text().splitlines()]
    if args.n > 0:
        data = data[:args.n]

    llm = LLMClient(model=args.model)
    output_path = Path(args.output)

    scores = []
    gate_fails = 0
    judge_errors = 0
    by_scene: dict = {}

    print(f"[{datetime.now():%H:%M:%S}] 开始评估 {len(data)} 条 | 模型={args.model} | 并发={args.c}")
    print(f"{'':5} {'场景':<22} {'分数':>6} {'D1':>4} {'D2':>4} {'D3':>4} {'D4':>4} {'D5':>4}")
    print("-" * 70)

    with ThreadPoolExecutor(max_workers=args.c) as ex:
        futs = {ex.submit(evaluate_one, d, llm): d for d in data}
        for fut in as_completed(futs):
            res = fut.result()
            sc = res["scenario_type"]
            score = res["score"]

            if score == -1.0:
                judge_errors += 1
                print(f"  {'✗':>4} {sc:<22} judge错误")
                continue

            if res.get("gate_fail"):
                gate_fails += 1
                fail_reason = res["gate_card_id"]["reason"] if not res["gate_card_id"]["pass"] else res["gate_text_quality"]["reason"]
                print(f"  {'G':>4} {sc:<22} {score:>6.2f} gate失败: {fail_reason}")
            else:
                judge = res.get("judge", {})
                d1 = "✓" if judge.get("d1_need_understanding",{}).get("verdict")=="PASS" else "✗"
                d2 = "✓" if judge.get("d2_factual_accuracy",{}).get("verdict")=="PASS" else "✗"
                d3 = "✓" if judge.get("d3_recommendation_quality",{}).get("verdict")=="PASS" else "✗"
                d4 = "✓" if judge.get("d4_completeness",{}).get("verdict")=="PASS" else "✗"
                d5 = "✓" if judge.get("d5_recommendation_value",{}).get("verdict")=="PASS" else "✗"
                print(f"  {score:>5.2f} {sc:<22} {score:>6.2f} {d1:>4} {d2:>4} {d3:>4} {d4:>4} {d5:>4}")

            scores.append(score)
            by_scene.setdefault(sc, []).append(score)

            with WRITE_LOCK:
                with open(output_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(res, ensure_ascii=False) + "\n")

    valid_scores = [s for s in scores if s >= 0]
    print(f"\n{'='*70}")
    print(f"评估完成: {len(data)}条 | gate失败={gate_fails} | judge错误={judge_errors}")
    if valid_scores:
        print(f"平均分: {sum(valid_scores)/len(valid_scores):.3f} | 最低: {min(valid_scores):.2f} | 最高: {max(valid_scores):.2f}")
        print(f"满分(1.0): {sum(1 for s in valid_scores if s==1.0)}条 | 零分: {sum(1 for s in valid_scores if s==0.0)}条")
        print(f"\n分场景平均分:")
        for sc, sc_scores in sorted(by_scene.items()):
            valid = [s for s in sc_scores if s >= 0]
            if valid:
                print(f"  {sc:<25} {sum(valid)/len(valid):.3f} ({len(valid)}条)")
    print(f"\n结果已保存 → {output_path}")


if __name__ == "__main__":
    main()
