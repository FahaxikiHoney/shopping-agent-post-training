# -*- coding: utf-8 -*-
"""
ReAct Agent 数据采集脚本

用 DeepSeek-R1 真正跑 ReAct 循环，生成多轮工具调用轨迹。
每条轨迹：模型自己决定调几次工具、调哪个、什么时候输出最终回复。

用法：
    python3 sft_data/gen_react_data.py --sample 5    # 先跑5条验证
    python3 sft_data/gen_react_data.py -n 200 -c 3   # 正式跑200条
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from joybuy_agent.llm.client import LLMClient
from joybuy_agent.react.agent import ReActJoybuyAgent
from joybuy_agent.react.tools import execute_tool

OUTPUT     = Path(__file__).parent / "trajectories_react.jsonl"
WRITE_LOCK = threading.Lock()

# ── 每个场景的 query 题库 ──────────────────────────────────────────────────
TOPICS = {
    "search_recommend": [
        "推荐一款主动降噪耳机，预算500元以内",
        "帮我找适合长期居家办公的人体工学椅，预算1500元",
        "推荐保温效果好的保温杯，24小时保温，200元左右",
        "找一款家用扫地机器人，3000元预算，有自动倒垃圾功能",
        "推荐给60岁老人用的颈椎按摩仪，操作简单，400元以内",
        "找跑步用的蓝牙耳机，要防水防汗，300元以内",
        "帮我选一台咖啡机，新手入门，1500元以内",
        "推荐一款家用投影仪，预算3000元，白天也能看清楚",
        "找一款静音电热水壶，容量1.5L以上，200元以内",
        "推荐空气净化器，适合30平卧室，去甲醛，1000元左右",
        "Looking for a 75-inch smart TV for the living room",
        "I need a quiet robot vacuum for a home with pets",
        "Recommend a comfortable ergonomic chair for working from home",
        "Which coffee machine is easy to use for a beginner?",
        "Je cherche un climatiseur silencieux pour une chambre",
        "Je voudrais un aspirateur robot avec fonction lavage",
        "Quelle chaise de camping est facile à transporter ?",
        "Ich suche einen 27 Zoll Monitor fürs Homeoffice",
        "Empfehlen Sie mir einen leisen Luftreiniger fürs Schlafzimmer",
        "Welche Kaffeemaschine eignet sich für Anfänger?",
        "Ik zoek een smartwatch die met mijn iPhone werkt",
        "Welke robotstofzuiger is geschikt voor een huis met huisdieren?",
        "Ik zoek een waterdichte rugzak voor dagelijks gebruik",
    ],
    "similar_rec": [
        "我买的膳魔师保温杯169元，保温只有5小时，帮我换个同价位但保温24小时的",
        "买的漫步者蓝牙耳机299元，漏音很严重，换同价位密封性好的降噪款",
        "之前那台小米扫地机1999元吸力太弱，换同价位吸力强的款",
        "用的西昊椅子800元，坐久了腰疼，换同价位有腰托的人体工学椅",
        "买的小熊热水壶79元，烧水太慢，换同价位快速加热的款",
        "之前的飞利浦台灯149元，频闪眼睛不舒服，换同价位无频闪护眼款",
        "买的耐克跑步鞋369元，穿着脚疼缓震太差，换缓震好的跑鞋",
    ],
    "bundle_purchase": [
        "帮我配齐居家办公装备，人体工学椅+护眼台灯+无线键鼠套装，总预算3000元，最后算一下总价",
        "1500元配齐书桌办公三件套：护眼台灯+机械键盘+无线鼠标，帮我算算总价",
        "2000元配一套家庭健身装备：可调哑铃+瑜伽垫+跳绳，帮我算总价看是否超预算",
        "配跑步机搭配装备：运动垫+运动耳机，总预算600元，算下来够不够",
        "配相机搭配装备：三脚架+摄影包，总预算1000元，最后帮我算总价",
    ],
    "matching": [
        "买了北欧风的沙发，需要搭配茶几和落地灯",
        "装修现代简约风格客厅，帮我选茶几和地毯",
        "买了中古复古风沙发，搭配茶几和装饰画",
        "买了新帐篷准备露营，需要搭配折叠椅和保温壶",
        "买了哑铃开始健身，搭配瑜伽垫和弹力带",
    ],
    "search_no_stock": [
        "我想买AirPods Max，京东有吗",        # 替代词：头戴式降噪耳机
        "帮我找戴森V15吸尘器",                # 替代词：无线吸尘器
        "任天堂Switch OLED现在有货吗",        # 替代词：掌机/掌上游戏机
        "想买戴森Airwrap卷发棒",              # 替代词：卷发棒
        "帮我搜一下索尼WH-1000XM6",          # 替代词：头戴式降噪耳机
        "苹果Vision Pro有卖吗",               # 替代词：VR头显
    ],
}

SCENARIO_MAP = {
    "search_recommend": "search_recommend",
    "similar_rec":      "similar_rec",
    "bundle_purchase":  "bundle_purchase",
    "matching":         "matching_purchase",
    "search_no_stock":  "search_no_stock",
}

TRAIN_SCENARIO_WEIGHTS = {
    "search_recommend": 70,
    "similar_rec": 12,
    "bundle_purchase": 8,
    "matching": 10,
}


def validate_search_topic_bank() -> None:
    missed = []
    for query in TOPICS["search_recommend"]:
        result = execute_tool("sku_recall", {"query": query})
        if result.get("count", 0) == 0:
            missed.append(query)
    if missed:
        preview = "；".join(missed[:5])
        raise RuntimeError(f"search_recommend题库存在空召回query: {preview}")


def validate(traj) -> list:
    """校验轨迹质量"""
    import re
    errors = []
    if traj.status == "error":
        errors.append("agent运行错误")
    if len(traj.final_response) < 80:
        errors.append(f"回复太短:{len(traj.final_response)}字")
    if len(traj.steps) == 0:
        errors.append("没有工具调用步骤")
    if len(traj.final_response) > 2000:
        errors.append(f"回复过长:{len(traj.final_response)}字")
    if not re.search(r'\[product:\d+\]', traj.final_response):
        errors.append("缺少商卡标签[product:X]")
    product_cards = re.findall(r'\[product:(\d+)\]', traj.final_response)
    if len(product_cards) != len(set(product_cards)):
        errors.append("商卡重复引用")
    if len(set(product_cards)) > 5 and traj.scenario_type == "search_recommend":
        errors.append(f"普通搜索推荐过多:{len(set(product_cards))}款")
    if product_cards and "<ClickText>" not in traj.final_response:
        errors.append("缺少ClickText追问")

    # 乱码/质量检测
    fr = traj.final_response
    # 数字残缺（如 "CADR值达m³/h"、"¥999¥999"）
    if re.search(r'达[a-zA-Z㎡³]|¥\d+¥|值达\s*[a-zA-Z]', fr):
        errors.append("输出乱码:数字残缺")
    # 未闭合的括号/标签
    if re.search(r'\[\s*[^product][^\]]{0,10}$', fr):
        errors.append("输出乱码:未闭合括号")
    # 明显截断（句子中间断开，以非标点结尾且无商卡标签）
    if (
        len(fr) > 100
        and fr[-1] not in '。！？.!?」]）)'
        and not fr.endswith('</ClickText>')
        and '[product:' not in fr[-30:]
    ):
        errors.append("输出疑似截断")
    # thinking 泄漏特征词
    LEAK_PATTERNS = ["首先处理", "接下来我需要", "用户需要帮", "我需要继续搜索", "根据之前的工具调用"]
    if any(p in fr for p in LEAK_PATTERNS) and len(fr) > 300:
        errors.append("thinking泄漏")

    # bundle 场景走专用逻辑，自己控制品类搜索，跳过正则品类检查
    # matching 场景：检查品类完整性
    if traj.scenario_type == "matching_purchase":
        user_text = traj.user_query
        if any(sep in user_text for sep in ["+", "＋", "和", "及"]):
            import json as _json
            searched_queries = []
            used_scenario_recall = False
            total_products_returned = 0
            for msg in traj.messages:
                if msg.get("tool_calls"):
                    tc = msg["tool_calls"][0]["function"]
                    if tc["name"] == "sku_recall":
                        try:
                            args = _json.loads(tc["arguments"])
                            searched_queries.append(args.get("query", "").lower())
                        except Exception:
                            pass
                    elif tc["name"] == "scenario_related_recall":
                        used_scenario_recall = True
                if msg.get("role") == "tool":
                    try:
                        r = _json.loads(msg["content"])
                        total_products_returned += len(r.get("products", []))
                    except Exception:
                        pass

            # scenario_related_recall 场景：只要有商品返回就算通过
            if used_scenario_recall and total_products_returned >= 2:
                pass  # 不检查品类
            else:
                # 只提取 + 号后面的品类（主商品不算）
                categories = re.findall(
                    r'[+＋][^\+＋，。！？]{0,4}([一-鿿]{2,5}(?:套装|垫|椅|灯|机|壶|包|架|棒|绳|铃|耳机))',
                    user_text
                )
                # fallback: 匹配所有品类但排除第一个词（通常是主商品）
                if not categories:
                    all_cats = re.findall(
                        r'[一-鿿]{2,5}(?:套装|垫|椅|灯|机|壶|包|架|棒|绳|铃|耳机)', user_text
                    )
                    categories = all_cats[1:] if len(all_cats) > 1 else all_cats
                unsearched = [c for c in categories if not any(c in q for q in searched_queries)]
                if unsearched:
                    errors.append(f"未搜索品类:{','.join(unsearched)}")

    return errors


def run_one(
    task_id: int,
    sc_key: str,
    query: str,
    llm: LLMClient,
    site_context=None,
) -> dict:
    scenario_type = SCENARIO_MAP.get(sc_key, sc_key)
    agent = ReActJoybuyAgent(
        llm=llm,
        max_steps=5,
        scenario_type=scenario_type,
        site_context=site_context,
    )
    t0 = time.time()
    try:
        traj = agent.run(query)
    except Exception as e:
        return {"traj": None, "errs": [str(e)[:80]], "elapsed": time.time()-t0,
                "sc": sc_key, "query": query, "task_id": task_id}
    elapsed = time.time() - t0
    errs = validate(traj)
    return {"traj": traj, "errs": errs, "elapsed": elapsed,
            "sc": sc_key, "query": query, "task_id": task_id}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n",       type=int, default=50,  help="生成条数")
    parser.add_argument("-c",       type=int, default=2,   help="并发线程数")
    parser.add_argument("--sample", type=int, default=0,   help="先跑N条验证（不写文件，只打印）")
    parser.add_argument("--model",  type=str, default="DeepSeek-R1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--site",
        choices=["UK-Site", "DE-Site", "FR-Site", "NL-Site"],
        help="注入站点上下文；工具参数仍只包含 query",
    )
    parser.add_argument(
        "--include-empty",
        action="store_true",
        help="加入无货专项场景；默认不混入正常训练数据",
    )
    args = parser.parse_args()

    random.seed(args.seed)
    validate_search_topic_bank()
    llm = LLMClient(model=args.model)
    n = args.sample if args.sample else args.n

    # 构造任务列表
    scenario_weights = dict(TRAIN_SCENARIO_WEIGHTS)
    if args.include_empty:
        scenario_weights["search_no_stock"] = 10
    all_keys = list(scenario_weights)
    weights = [scenario_weights[key] for key in all_keys]
    tasks = []
    for i in range(n):
        sc_key = random.choices(all_keys, weights=weights, k=1)[0]
        query  = random.choice(TOPICS[sc_key])
        tasks.append((i + 1, sc_key, query, llm, args.site))

    ok = fail = 0
    start = time.time()

    print(f"[{datetime.now():%H:%M:%S}] ReAct数据采集 | {n}条 | 模型={args.model} | 并发={args.c}")
    print(f"{'':5} {'场景':<18} {'状态'} {'步骤'} {'字数'} {'耗时'}")
    print("-" * 65)

    with ThreadPoolExecutor(max_workers=args.c) as ex:
        futs = {ex.submit(run_one, tid, sc, q, llm, site): (tid, sc, q)
                for tid, sc, q, llm, site in tasks}
        for fut in as_completed(futs):
            tid, sc, q = futs[fut]
            res = fut.result()
            errs    = res["errs"]
            elapsed = res["elapsed"]
            traj    = res["traj"]

            if errs or not traj:
                fail += 1
                print(f"[{tid:>4}] {sc:<18} ✗ {errs}")
                continue

            ok += 1
            n_steps = len(traj.steps)
            fr_len  = len(traj.final_response)
            print(f"[{tid:>4}] {sc:<18} ✓ {n_steps}步 {fr_len}字 {elapsed:.0f}s")

            if args.sample:
                # 打印详细轨迹
                print(f"       query: {traj.user_query}")
                for s in traj.steps:
                    print(f"       → {s.tool_name}({json.dumps(s.tool_input,ensure_ascii=False)[:60]})")
                    prods = s.tool_output.get("products", [])
                    if prods:
                        print(f"         返回{len(prods)}款: {[p.get('sku_name', p.get('title', ''))[:15] for p in prods[:2]]}")
                print(f"       回复: {traj.final_response[:150]}")
                print()
            else:
                # 写入文件
                with WRITE_LOCK:
                    with open(OUTPUT, "a", encoding="utf-8") as f:
                        f.write(json.dumps(traj.to_sft_dict(), ensure_ascii=False) + "\n")

    elapsed_total = time.time() - start
    if not args.sample:
        total = sum(1 for _ in open(OUTPUT))
        print(f"\n完成: 成功={ok} 失败={fail} 耗时={elapsed_total:.0f}s 总条数={total}")
    else:
        print(f"\n验证完成: 成功={ok} 失败={fail}")


if __name__ == "__main__":
    main()
