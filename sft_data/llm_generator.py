# -*- coding: utf-8 -*-
"""
LLM 数据生成器：用OpenAI-compatible API生成 SFT trajectory 数据
- 并发 3（默认）
- SSE 流式接收 → 完整 JSON 解析
- 思考模式可开启
- 断点续传：跑过的主题不重做
- 失败重试 3 次 + 指数退避
- 输出对齐 trajectories_final.jsonl 格式
"""
import argparse
import hashlib
import json
import random
import re
import sys
import threading
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests

# ────────────────────────────────────────────────────────────────────
# 配置
# ────────────────────────────────────────────────────────────────────
GW_URL = os.environ.get("LLM_API_URL", "https://api.example.com/v1/chat/completions")
TOKEN = os.environ.get("LLM_API_KEY", "")
MODEL = "DeepSeek-V4-Flash"

HERE = Path(__file__).parent
OUTPUT_PATH = HERE / "trajectories_llm.jsonl"
DONE_PATH = HERE / "_llm_done.txt"          # 已完成主题 hash
LOG_PATH = HERE / "_llm_log.txt"            # 详细日志

WRITE_LOCK = threading.Lock()
LOG_LOCK = threading.Lock()

# ────────────────────────────────────────────────────────────────────
# 主题池：可按需扩充。命令行 -n 控制本次跑几条
# 每个主题 = (scenario_type, focus, seed_query)
# ────────────────────────────────────────────────────────────────────
TOPIC_POOL = [
    # similar_rec ─ 抱怨维度→工具参数调整
    ("similar_rec", "抱怨配色单调 → 调 color_variety 参数", "之前那款手机配色太单调了，换几个配色丰富的同价位手机"),
    ("similar_rec", "抱怨过敏 → 排除特定材质", "买的乳胶枕睡了脸上起疹子，换无乳胶的同价位枕头"),
    ("similar_rec", "抱怨电池差 → battery_min 升级", "充电宝 5000mAh 用不到一天，要长续航的"),
    ("similar_rec", "抱怨噪音大 → noise_max_db 过滤", "之前那台破壁机噪音 85 分贝太吵了，有静音的同价位款吗"),
    ("similar_rec", "抱怨容量不够 → capacity_min 升级", "那台净水器 1L 太小，全家用不够，换大容量的"),
    ("similar_rec", "抱怨甲醛重 → 环保认证筛选", "新买的床垫味道刺鼻，要环保零醛认证的同价位款"),
    ("similar_rec", "抱怨太复杂 → 老人友好版本", "这部手机给爸妈用太复杂了，要简单的老人款"),
    ("similar_rec", "抱怨耗材贵 → 耗材便宜的同档", "上次那台打印机墨盒太贵，要耗材便宜的同价位"),
    ("similar_rec", "抱怨重量大 → 轻量版", "之前的笔记本 2.3kg 背着累，要 1.5kg 以内同价位"),
    ("similar_rec", "抱怨颜值老 → 现代风同款", "买的微波炉太土，要颜值高的同价位现代款"),

    # sku_comp ─ 多商品对比 + 动态维度
    ("sku_comp", "3 款国产旗舰手机对比", "对比小米14、华为Pura 70、vivo X100，6000 价位选哪个"),
    ("sku_comp", "同型号新旧两代对比", "iPad Air 6 比 Air 5 贵 1500，值不值"),
    ("sku_comp", "高端 vs 平价同功能", "戴森 V12 和追觅 V12s Pro 真有 2 倍差距吗"),
    ("sku_comp", "跨品类决策", "扫地机器人和洗地机选哪个，预算 2000 有宠物"),
    ("sku_comp", "套餐 vs 单买", "iPad Pro 套装 8499 vs 单买配件凑 9797，怎么选"),
    ("sku_comp", "动态权重调整", "对比 3 款手机给老人用主要拍照，怎么选"),
    ("sku_comp", "不同芯片代际", "MacBook Air M2/M3/M4 三代差 2000，怎么选"),
    ("sku_comp", "性价比 vs 旗舰", "买无线耳机 200/500/1000/2000 四档差多少"),

    # matching_purchase ─ 风格搭配（不看价格）
    ("matching_purchase", "服装搭配：核心商品风格 → 配饰", "刚买了一件米白色羊毛大衣，配什么围巾"),
    ("matching_purchase", "家居搭配：风格统一", "客厅米色沙发+原木地板，配什么颜色地毯"),
    ("matching_purchase", "3C 搭配：型号兼容", "iPhone 15 Pro Max 钛金属，配什么壳和钢化膜"),
    ("matching_purchase", "工位颜值升级", "工位想升级颜值，配什么白色键鼠+桌垫"),
    ("matching_purchase", "婚礼新郎整体", "下个月结婚，新郎要配西装+衬衫+领带+皮鞋"),
    ("matching_purchase", "运动整体装备", "夏天开始跑步，配身衣服鞋子袜子运动表"),
    ("matching_purchase", "海岛度假整套", "去三亚度假 5 天，配齐泳衣+沙滩裙+草帽+太阳镜"),
    ("matching_purchase", "卫浴整体搭配", "卫生间白色调，配什么浴室柜+龙头+毛巾架"),

    # bundle_purchase ─ 预算拆分 + 多次工具 + 算账
    ("bundle_purchase", "5000 元客厅音响", "客厅音响系统 5000 预算怎么配"),
    ("bundle_purchase", "3000 元学习装备", "3000 给孩子配平板+键盘+耳机学习套装"),
    ("bundle_purchase", "1500 元健身入门", "想开始健身，1500 配齐家用入门装备"),
    ("bundle_purchase", "2000 元厨房刀锅", "2000 配齐厨房刀具+锅具一套"),
    ("bundle_purchase", "4000 元露营装备", "想入门露营，4000 配齐 2 人露营全套"),
    ("bundle_purchase", "8000 元摄影入门", "想入门摄影，8000 配相机+镜头+三脚架+SD+包"),
    ("bundle_purchase", "5000 元新生儿月子包", "宝宝快出生，5000 配齐第一个月用品"),
    ("bundle_purchase", "3500 元自驾游装备", "国庆自驾川西 7 天，3500 配齐车载装备"),

    # place_order ─ 下单（含多场景）
    ("place_order", "凑单+下单", "购物车有 458 的鞋，怎么凑满 500 减 80 最划算并下单"),
    ("place_order", "礼品下单+定制贺卡", "送同事生日，下单巧克力礼盒要包装不放价签附卡片"),
    ("place_order", "大件家电+楼层费", "下单 4999 的冰箱，发到 6 楼无电梯，预约周六上午"),
    ("place_order", "异地下单代收", "给上海父母下单一台电视，我在北京"),

    # repurchase ─ 复购召回
    ("repurchase", "复购日用品", "猫粮快用完了，再买之前的"),
    ("repurchase", "复购+智能升级提醒", "再帮我买一包之前的纸尿裤"),
    ("repurchase", "复购+大包装升级", "再买之前那个洗衣凝珠"),
    ("repurchase", "复购+断货平替", "再买之前那个口红"),
    ("repurchase", "复购+套餐升级", "再买一袋之前的咖啡豆"),
]

# ────────────────────────────────────────────────────────────────────
# Prompt 模板
# ────────────────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """你是购物 Agent 训练数据生成专家。请为下面这个 case 生成一条完整的 SFT 训练 trajectory。

【场景类型】scenario_type = {scenario}
【训练焦点】training_focus = {focus}
【用户 Query】user_query = {query}

# 真实工具（必须只用以下 6 个名字之一）
- SkuRecallShopping     主搜索召回（最常用，几乎都用它）
- SkuImageRecall        图搜召回（用户发图找相似时）
- SkuRepurchaseRecall   复购召回（repurchase 场景用）
- ShoppingPlaceOrderTool 下单（place_order 场景用）
- PythonCalculator      算账（凑单/预算分配时用）
- OrderQuerySkill       查订单/物流

# 必须输出的 JSON 结构（严格按这个 schema，禁止加任何 markdown 代码块标记）

{{
  "trajectory_id": "sft_xxx_001",   // 你自己起个 id
  "scenario_type": "{scenario}",
  "category": "中文场景名（如：相似品推荐 / 商品对比 / 搭配购物 / 组合购物 / 购物下单 / 复购召回）",
  "quality_label": "good",
  "training_focus": "{focus}",
  "is_multi_turn": false,
  "conversation_history": [],
  "user_query": "{query}",
  "thinking": "Agent 的内部推理 80-150 字，体现需求拆解→工具选择→筛选逻辑",
  "steps": [
    {{
      "step_id": 1,
      "step_type": "tool_call",
      "tool_name": "上面 6 个工具名之一",
      "tool_input": {{ "query": "工具关键词", "max_price": 数字或null, "filters": {{}} }},
      "tool_output": {{
        "status": "SUCCESS",
        "products": [
          {{
            "product_id": "mock_xxxxxxxx",
            "title": "完整商品标题（品牌+型号+规格）",
            "price": 数字,
            "is_platform_self": true,
            "rating": 4.7-4.9,
            "key_specs": "2-3 个关键参数",
            "sales": "月销Xxx件"
          }}
          // 建议 2-4 个商品
        ]
      }},
      "error_type": null
    }},
    {{
      "step_id": 2,
      "step_type": "final_response",
      "content": "面向用户的完整回复 300-600 字，要有：核心结论 + 每款的优缺点 + 给谁推荐的具体建议 + 避坑提醒。用 markdown 排版，可用表格和小标题，不要空话",
      "product_cards": [
        {{ "card_id": "必须是上面 tool_output.products 里出现过的 product_id", "display_price": 数字, "reason": "20-40 字具体推荐理由，禁止说性价比高/不错/值得购买这种空话" }}
      ]
    }}
  ],
  "final_response": "和 steps 里最后一个 step 的 content 完全一致",
  "eval_score": 1.0,
  "sft_source": "llm_generated_glm51"
}}

# 硬约束（违反就废了）
1. card_id 必须 100% 来自 tool_output.products 里的 product_id，绝对禁止编造
2. tool_input.query 必须包含核心约束词（品类+人群/场景/价格）
3. 推荐理由禁止套话："性价比高" / "不错" / "值得购买" 一律不准用
4. 月销量要符合常识（爆款 1 万+，小众几百到几千）
5. 价格要符合品类常识
6. final_response 必须有实质对比和具体建议，不能只列商品

只输出 JSON 对象本体，不要 ```json 包裹，不要任何额外解释。"""


# ────────────────────────────────────────────────────────────────────
# 工具函数
# ────────────────────────────────────────────────────────────────────
def topic_hash(topic: tuple) -> str:
    return hashlib.md5("|".join(topic).encode("utf-8")).hexdigest()[:12]


def log(msg: str):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG_LOCK:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def load_done() -> set:
    if not DONE_PATH.exists():
        return set()
    return set(DONE_PATH.read_text(encoding="utf-8").splitlines())


def mark_done(h: str):
    with WRITE_LOCK:
        with open(DONE_PATH, "a", encoding="utf-8") as f:
            f.write(h + "\n")


# ────────────────────────────────────────────────────────────────────
# LLM 调用：SSE 流式聚合
# ────────────────────────────────────────────────────────────────────
RATE_LIMIT_CODES = {429, 502, 503, 504}


class RateLimited(Exception):
    """限流类错误，需要更长退避"""
    pass


def call_llm(prompt: str, enable_thinking: bool = True, timeout: int = 180) -> str:
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "temperature": 0.7,
    }
    # DeepSeek 思考模式（如果支持）
    if enable_thinking:
        payload["thinking"] = {"type": "enabled"}

    resp = requests.post(GW_URL, headers=headers, json=payload, stream=True, timeout=timeout)

    # 限流类状态码单独识别（429 / 5xx）
    if resp.status_code in RATE_LIMIT_CODES:
        body = ""
        try:
            body = resp.text[:200]
        except Exception:
            pass
        raise RateLimited(f"HTTP {resp.status_code} (rate-limit) body={body}")
    resp.raise_for_status()

    chunks = []
    for raw in resp.iter_lines(decode_unicode=True):
        if not raw:
            continue
        line = raw.lstrip()
        if line.startswith("data: "):
            data = line[6:].strip()
        elif line.startswith("data:"):
            data = line[5:].strip()
        else:
            data = line.strip()
        if not data or data == "[DONE]":
            continue
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            continue
        choices = obj.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta", {}) or choices[0].get("message", {})
        # GLM 思考内容可能在 reasoning_content / thinking 字段，正文在 content
        # 我们只收集 content（思考内容用于调试可单独打印）
        c = delta.get("content")
        if c:
            chunks.append(c)
    return "".join(chunks).strip()


# ────────────────────────────────────────────────────────────────────
# JSON 解析（容错）
# ────────────────────────────────────────────────────────────────────
def extract_json(text: str) -> dict:
    if not text:
        raise ValueError("empty response")
    # 去掉 ```json ... ``` 包裹
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    # 找第一个 { 到匹配的 }
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object found")
    depth = 0
    end = -1
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise ValueError("unbalanced braces")
    return json.loads(text[start:end])


# ────────────────────────────────────────────────────────────────────
# 校验：card_id 必须来自 tool_output.products
# ────────────────────────────────────────────────────────────────────
def validate(traj: dict):
    """校验 trajectory，返回 (ok: bool, reason: str)"""
    must = ["trajectory_id", "scenario_type", "user_query", "steps", "final_response"]
    for k in must:
        if k not in traj or not traj[k]:
            return False, f"missing field: {k}"
    returned_ids = set()
    for step in traj.get("steps", []):
        out = step.get("tool_output") or {}
        for p in out.get("products", []) or []:
            pid = p.get("product_id")
            if pid:
                returned_ids.add(pid)
    card_ids = set()
    for step in traj.get("steps", []):
        for c in step.get("product_cards", []) or []:
            cid = c.get("card_id")
            if cid:
                card_ids.add(cid)
    hallucinated = card_ids - returned_ids
    if hallucinated:
        return False, f"hallucinated card_ids: {hallucinated}"
    return True, "ok"


# ────────────────────────────────────────────────────────────────────
# 单任务
# ────────────────────────────────────────────────────────────────────
def task(idx: int, topic: tuple, total: int, enable_thinking: bool, max_retries: int = 5):
    scenario, focus, query = topic
    h = topic_hash(topic)
    prompt = PROMPT_TEMPLATE.format(scenario=scenario, focus=focus, query=query)

    for attempt in range(1, max_retries + 1):
        try:
            t0 = time.time()
            text = call_llm(prompt, enable_thinking=enable_thinking)
            elapsed = time.time() - t0
            if not text:
                raise RuntimeError("empty content")
            traj = extract_json(text)
            ok, reason = validate(traj)
            if not ok:
                raise RuntimeError(f"validate failed: {reason}")
            with WRITE_LOCK:
                with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps(traj, ensure_ascii=False) + "\n")
            mark_done(h)
            log(f"[{idx}/{total}] ✅ {scenario:<20} ({elapsed:.1f}s, try{attempt}) {query[:30]}")
            return True
        except RateLimited as e:
            # 限流：长退避（30 / 60 / 120 / 240 / 480 秒）
            wait = min(30 * (2 ** (attempt - 1)), 600) + random.uniform(0, 5)
            log(f"[{idx}/{total}] ⏸ 限流 try{attempt}: {str(e)[:80]} → 等 {wait:.0f}s")
            time.sleep(wait)
        except requests.HTTPError as e:
            log(f"[{idx}/{total}] HTTPError try{attempt}: {e}")
            time.sleep(2 ** attempt + random.uniform(0, 1))
        except Exception as e:
            log(f"[{idx}/{total}] err try{attempt} ({type(e).__name__}): {str(e)[:120]}")
            time.sleep(2 ** attempt + random.uniform(0, 1))
    log(f"[{idx}/{total}] ❌ {scenario:<20} 放弃 {query[:30]}")
    return False


# ────────────────────────────────────────────────────────────────────
# 主流程
# ────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--count", type=int, default=10, help="本次生成多少条（默认 10）")
    ap.add_argument("-c", "--concurrency", type=int, default=2, help="并发数（默认 2，限流场景建议 1-2）")
    ap.add_argument("--interval", type=float, default=8.0, help="每个任务提交间隔秒数（默认 8，避免触发限流）")
    ap.add_argument("--retries", type=int, default=5, help="单条最大重试次数（默认 5，限流场景多重试）")
    ap.add_argument("--no-thinking", action="store_true", help="关闭思考模式")
    ap.add_argument("--scenario", type=str, default="", help="只跑某个场景类型（如 similar_rec）")
    ap.add_argument("--shuffle", action="store_true", help="打乱主题顺序")
    args = ap.parse_args()

    done = load_done()
    pool = TOPIC_POOL[:]
    if args.scenario:
        pool = [t for t in pool if t[0] == args.scenario]
    if args.shuffle:
        random.shuffle(pool)
    pool = [t for t in pool if topic_hash(t) not in done]
    if not pool:
        print("所有主题已完成，可以扩充 TOPIC_POOL 或删除 _llm_done.txt 重跑")
        return
    todo = pool[: args.count]

    log(f"模型: {MODEL}  网关: {GW_URL}")
    log(f"任务: {len(todo)} 条  并发: {args.concurrency}  思考: {'OFF' if args.no_thinking else 'ON'}")
    log(f"提交间隔: {args.interval}s  单条最大重试: {args.retries}")
    log(f"输出: {OUTPUT_PATH}")
    log("-" * 60)

    success = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = {}
        for i, t in enumerate(todo):
            futures[ex.submit(task, i + 1, t, len(todo), not args.no_thinking, args.retries)] = t
            # 任务提交间隔，避免短时间内打爆网关触发限流
            if i < len(todo) - 1:
                time.sleep(args.interval)
        for fut in as_completed(futures):
            if fut.result():
                success += 1

    log("-" * 60)
    log(f"完成：{success}/{len(todo)} 成功 → 写入 {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
