# -*- coding: utf-8 -*-
"""
用 joybuy_agent 框架 + JoyAI-LLM-Flash 生成 100 条 SFT 数据
并发 4 个线程，约 5-15 分钟完成
"""
import sys, json, time, random, threading, traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from joybuy_agent.llm import LLM_FAST, LLM_THINKING, make_agent_with_thinking
from joybuy_agent.llm.client import LLMClient
from joybuy_agent.tools import create_registry
from joybuy_agent.core.context import AgentContext
from joybuy_agent.agents import (
    SimilarRecAgent, SkuCompAgent, SearchRecommendAgent,
    RepurchaseAgent, MatchingAgent, BundleAgent, OrderAgent,
)

OUTPUT = Path(__file__).parent / "trajectories_r1.jsonl"
WRITE_LOCK = threading.Lock()

# ── 每个场景的 query 题库 ──────────────────────────────────────
TOPICS = {
    "similar_rec": [
        "之前买的保温杯只保温5小时，换同价位24小时保温款",
        "买的蓝牙耳机漏音严重，换同价位密封性好的",
        "洗衣机噪音太大影响睡眠，换超静音款",
        "买的跑鞋太硬磨脚，换缓震好的同价位款",
        "台灯只有一档亮度不能调，换多档调光款",
        "买的充电宝发热严重，换散热好的安全款",
        "炒锅涂层掉落不安全，换铸铁无涂层款",
        "买的书包背带太硬，换人体工学减压背带款",
        "椅子坐久了腰疼，换人体工学椅同价位",
        "热水壶烧水太慢，换3分钟速热的同价位款",
        "空气净化器噪音大，换超静音低噪款",
        "鼠标滚轮卡顿，换顺滑高精度同价位款",
        "净化器滤芯消耗快，换长效大容量款",
        "台式电扇风力太小，换大风量工业级款",
        "护肤品味道太刺激，换无香型同功效款",
    ],
    "sku_comp": [
        "帮我对比石头G20S和科沃斯X2 Omni扫地机哪个更好",
        "膳魔师和虎牌保温杯哪个更值得买",
        "飞利浦和欧乐B电动牙刷哪个更好",
        "小米和华为手机同价位哪个性价比高",
        "西昊C300和保友金豪E2人体工学椅对比",
        "索尼WF-C700N和AirPods 4降噪耳机哪个好",
        "格力和美的空调1.5P变频哪个更省电",
        "苏泊尔钛系列和炊大皇麦饭石炒锅哪个好",
        "明基ScreenBar和小米台灯Pro护眼哪个效果好",
        "极米H6和坚果N1投影仪当电视哪个强",
        "德龙和飞利浦咖啡机哪个适合新手",
        "舒华折叠跑步机和小米跑步机对比",
        "DELL S2722DC和LG 27GP850显示器哪个好",
    ],
    "search_recommend": [
        "推荐一款降噪耳机，预算500元以内",
        "帮我找适合老人用的颈椎按摩仪，预算400元以内",
        "推荐家用扫地机器人，预算3000元左右",
        "找一款居家办公用的人体工学椅，预算1500元",
        "推荐保温杯，需要24小时保温，预算200元以内",
        "给孩子找台护眼台灯，预算300元以内",
        "推荐一款性价比高的空气净化器，适用60平方米",
        "找一款跑步鞋，适合初学者，预算250元",
        "推荐家用投影仪，当电视用，预算2000元",
        "帮我选咖啡机，新手入门，预算1500元",
    ],
    "repurchase": [
        "咖啡豆快喝完了，顺便推荐同品牌新口味",
        "洗发水要买了，顺便问有没有新款护发素",
        "猫粮要补货，推荐肠胃好的新品",
        "维生素C快吃完，问有没有带锌的复合版",
        "蛋白粉快吃完，有没有新口味推荐",
        "面膜用完了，同品牌有没有新出补水款",
        "洗衣液快用完，有没有好闻的新香型",
        "矿泉水要补货，有没有大容量装更划算",
        "纸尿裤要买，宝宝8个月该买哪个码",
        "打印机墨盒用完了，问原装和兼容哪个划算",
    ],
    "matching_purchase": [
        "买了北欧风沙发，需要搭配茶几和落地灯",
        "买了跑步机，配运动垫+风扇+水壶",
        "买了DSLR相机，需要配三脚架和相机包",
        "买了咖啡机，配磨豆机和马克杯",
        "装修了小书房，配书桌+台灯+人体工学椅",
        "买了iPhone 15 Pro Max，需要配手机壳和充电器",
        "宠物新家，配猫爬架+猫砂盆+玩具",
        "厨房升级，配刀具+砧板+调料架",
    ],
    "bundle_purchase": [
        "3000元居家办公升级，椅子+显示器+键鼠",
        "1000元居家健身组合，哑铃+瑜伽垫+弹力带",
        "800元大学宿舍神器，台灯+风扇+收纳架",
        "2000元新手跑步装备，跑鞋+运动裤+心率带",
        "1500元为父母配养生套装，足浴盆+按摩枕+血压计",
        "600元秋冬护肤礼盒，洁面+精华+面霜",
        "5000元书房改造，书架+升降桌+台灯+储物柜",
        "2500元摄影师出行装备，相机包+三脚架+清洁套",
        "900元孩子绘画兴趣，画板+颜料+画笔+素描本",
        "4000元新婚旅行装备，旅行箱+颈枕+收纳袋",
    ],
    "place_order": [
        "我买的耳机收到后颜色不对，如何申请换货",
        "买了手机等了7天未发货，怎么催单或取消",
        "找到了更便宜同款，怎么申请价保退差价",
        "收到的冰箱外包装破损，如何处理",
        "下单了礼品要送到父母那里，如何修改地址",
        "买了电器想开增值税发票，如何申请",
        "白条分了12期，现在想提前还款怎么操作",
        "明天有限时秒杀，如何提前准备确保抢到",
        "买了两件商品想合并发货怎么操作",
        "用京豆抵扣如何查询余额和使用规则",
    ],
}

AGENT_MAP = {
    "similar_rec":      SimilarRecAgent,
    "sku_comp":         SkuCompAgent,
    "search_recommend": SearchRecommendAgent,
    "repurchase":       RepurchaseAgent,
    "matching_purchase": MatchingAgent,
    "bundle_purchase":  BundleAgent,
    "place_order":      OrderAgent,
}

# 轮询模型（2:1 偏向 Fast）
MODEL_CYCLE = [
    LLMClient(model="DeepSeek-R1"),
    LLMClient(model="DeepSeek-R1"),
    LLMClient(model="DeepSeek-R1"),
]


def validate(traj: dict) -> list:
    errors = []
    sc    = traj.get("scenario_type", "")
    steps = traj.get("steps", [])
    final = next((s for s in steps if s.get("step_type") == "final_response"), None)
    tool_steps = [s for s in steps if s.get("step_type") == "tool_call"]
    if not final:
        return ["缺final_response"]
    fr = traj.get("final_response", "")
    rt = traj.get("raw_thinking", "")
    cards = final.get("product_cards", [])
    all_pids = {p["product_id"] for s in tool_steps for p in s.get("tool_output", {}).get("products", [])}

    if not cards:
        errors.append("cards空")
    if len(fr) < 80:
        errors.append(f"回复太短:{len(fr)}字")
    if len(fr) > 3000:
        errors.append(f"回复过长:{len(fr)}字(thinking未分离)")
    if rt and fr == rt:
        errors.append("thinking=response未分离")
    for c in cards:
        if c.get("card_id") not in all_pids:
            errors.append(f"card_id幻觉:{c['card_id']}")

    # ── 场景级格式校验 ──────────────────────────────────────
    # sku_comp：必须有 Markdown 对比表格（至少2列）
    if sc == "sku_comp" and "|" not in fr:
        errors.append("sku_comp缺Markdown对比表格")

    # sku_comp：至少召回2款商品才能做对比
    if sc == "sku_comp":
        all_prods = [p for s in tool_steps for p in s.get("tool_output", {}).get("products", [])]
        if len(all_prods) < 2:
            errors.append(f"sku_comp仅召回{len(all_prods)}款，无法对比")

    # bundle_purchase：必须有价格表格
    if sc == "bundle_purchase" and "|" not in fr:
        errors.append("bundle缺总价明细表格")

    # matching_purchase：必须有方案表格
    if sc == "matching_purchase" and "|" not in fr:
        errors.append("matching缺搭配方案表格")

    return errors


def run_one(task_id: int, sc: str, query: str, llm: LLMClient) -> dict:
    registry = create_registry()
    AgentCls = AGENT_MAP[sc]
    # DeepSeek-R1 单模型：<think>思维链 + 正文，100%准确分离
    agent = AgentCls(registry, llm_client=llm)
    ctx = AgentContext(user_query=query)
    t0 = time.time()
    traj = agent.run(ctx)
    elapsed = time.time() - t0
    errs = validate(traj)
    return {"traj": traj, "errs": errs, "elapsed": elapsed, "sc": sc, "query": query, "task_id": task_id}


def main(n=100, concurrency=4):
    # 均匀分配场景
    scenarios = list(AGENT_MAP.keys())
    tasks = []
    for i in range(n):
        sc = scenarios[i % len(scenarios)]
        query = random.choice(TOPICS[sc])
        llm = MODEL_CYCLE[i % len(MODEL_CYCLE)]
        tasks.append((i + 1, sc, query, llm))

    ok = fail = 0
    start = time.time()
    print(f"[{datetime.now():%H:%M:%S}] 开始生成 {n} 条 | 并发={concurrency} | 模型轮询={[c.model for c in MODEL_CYCLE]}\n")

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = {ex.submit(run_one, tid, sc, q, llm): (tid, sc, q) for tid, sc, q, llm in tasks}
        for fut in as_completed(futs):
            tid, sc, q = futs[fut]
            try:
                res = fut.result()
                errs = res["errs"]
                elapsed = res["elapsed"]
                traj = res["traj"]
                fr_len = len(traj.get("final_response", ""))
                n_steps = len(traj.get("steps", []))
                model = traj.get("steps", [{}])[-1]  # 不直接用 model，看 sft_source

                if errs:
                    fail += 1
                    print(f"[{tid:3d}/{n}] ✗ {sc:<18} {q[:25]} | {elapsed:.0f}s | {errs}")
                else:
                    ok += 1
                    with WRITE_LOCK:
                        with open(OUTPUT, "a", encoding="utf-8") as f:
                            f.write(json.dumps(traj, ensure_ascii=False) + "\n")
                    print(f"[{tid:3d}/{n}] ✓ {sc:<18} {q[:25]} | {elapsed:.0f}s | {fr_len}字/{n_steps}步")
            except Exception as e:
                fail += 1
                print(f"[{tid:3d}/{n}] ✗ {sc:<18} {q[:25]} | 异常: {str(e)[:60]}")
                traceback.print_exc()

    elapsed_total = time.time() - start
    with open(OUTPUT) as f:
        total = sum(1 for _ in f)

    print(f"\n{'='*65}")
    print(f"完成: 成功={ok} 失败={fail} 耗时={elapsed_total:.0f}s 总条数={total}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("-n", type=int, default=100)
    p.add_argument("-c", type=int, default=4, help="并发线程数")
    args = p.parse_args()
    main(args.n, args.c)
