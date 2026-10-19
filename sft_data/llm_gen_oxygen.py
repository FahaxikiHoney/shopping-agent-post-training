# -*- coding: utf-8 -*-
"""
多模型轮询 SFT 数据生成器
支持模型: OxygenLLM-122B-A10B / GLM-5.1 / DeepSeek-V4-Flash / JoyAI-LLM-Pro / GLM-5
限流: 5次/s（每个模型独立限速）
用法: python3 llm_gen_oxygen.py -n 100 --interval 0.2
"""
import json, time, re, uuid, requests, argparse, random, threading, os
try:
    import json5 as _json5
    _HAS_JSON5 = True
except ImportError:
    _HAS_JSON5 = False
from pathlib import Path
from datetime import datetime
from collections import deque

API_URL   = os.environ.get("LLM_API_URL", "https://api.example.com/v1/chat/completions")
API_TOKEN = os.environ.get("LLM_API_KEY", "")
OUTPUT    = Path(__file__).parent / "trajectories_final.jsonl"
WRITE_LOCK = threading.Lock()

MODELS = [
    "DeepSeek-V4-Flash",
    "JoyAI-LLM-Pro",
    "GLM-5",
    # GLM-5.1: reasoning_content 模式导致 JSON 格式不稳定，暂时移除
    # OxygenLLM-122B-A10B: 响应极慢(>120s)，暂时移除
]

# ───────────── 提示词 ─────────────
SYSTEM_PROMPT = """你是购物 Agent 的 SFT 训练数据生成器。

任务：根据场景描述，生成一条完整的 Agent 轨迹数据，严格按照 JSON 格式输出。

## 输出格式（只输出纯 JSON，禁止 markdown 代码块和任何解释文字）

{
  "trajectory_id": "sft_gen_XXXX",
  "scenario_type": "场景英文标识",
  "category": "中文分类",
  "quality_label": "good",
  "training_focus": "一句话核心要点",
  "is_multi_turn": false,
  "conversation_history": [],
  "user_query": "用户原始问题（自然语言）",
  "thinking": "Agent内部思考不超过50字",
  "steps": [
    {
      "step_id": 1,
      "step_type": "tool_call",
      "tool_name": "SkuRecallShopping",
      "tool_input": {"query": "搜索关键词", "max_price": 1000},
      "tool_output": {
        "status": "SUCCESS",
        "products": [
          {
            "product_id": "mock_12345678",
            "title": "品牌 商品名称 规格型号",
            "price": 299,
            "is_platform_self": true,
            "rating": 4.8,
            "key_specs": "核心卖点1/核心卖点2/核心卖点3",
            "sales": "月销2.5万件"
          }
        ]
      },
      "error_type": null
    },
    {
      "step_id": 2,
      "step_type": "final_response",
      "content": "完整的最终回复（含Markdown格式）",
      "product_cards": [
        {
          "card_id": "mock_12345678",
          "display_price": 299,
          "reason": "推荐理由"
        }
      ]
    }
  ],
  "final_response": "与steps[1].content完全相同",
  "eval_score": 1.0,
  "sft_source": "oxygen_llm_v1"
}

## 必须遵守的规则

1. product_cards 里每个 card_id 必须与 tool_output.products 里的 product_id 完全一致，绝对不能凭空创造
2. final_response 与 steps[1].content 内容完全相同
3. final_response 必须包含 Markdown（**加粗**、## 标题、对比表格至少一种），长度 200-500 字（精炼不冗余）
4. 商品数量：similar_rec/sku_comp 推荐3款；bundle/matching 4-5件套；repurchase 2-3款；place_order 1条记录
5. 价格符合真实市场行情，rating 在 4.5-4.9
6. 工具名：搜索推荐→SkuRecallShopping；复购→SkuRepurchaseRecall；下单/订单→ShoppingPlaceOrderTool或OrderQuerySkill
7. 只输出 JSON，第一个字符必须是 {
8. 工具名映射（严格执行）：similar_rec/sku_comp/search_recommend/matching_purchase/bundle_purchase → SkuRecallShopping；repurchase → SkuRepurchaseRecall；place_order（下单操作）→ ShoppingPlaceOrderTool；place_order（订单查询）→ OrderQuerySkill
9. final_response 要体现 Agent 的「思考路径」：先确认需求 → 说明召回逻辑 → 展示对比/推荐 → 给出明确结论
10. 商品卡要有真实的决策辅助信息：price、rating、key_specs（用/分隔核心卖点）、sales（月销X万件）
11. sku_comp 场景：final_response 必须包含 Markdown 对比表格，格式：| 维度 | 商品A | 商品B |
12. bundle_purchase 场景：final_response 必须包含总价计算表格和余额分配建议
13. repurchase 场景：products 第一个标注「(X月前购买)」，key_specs 里写「你X月前购买/品牌/规格」
14. place_order 场景：final_response 必须包含具体操作步骤（带 App 路径：XX App → XX菜单 → XX按钮）"""

TOPICS = {
    "similar_rec": [
        "买的蓝牙耳机漏音严重，要换同价位密封性好的",
        "买的保温杯保温只有5小时，要换24小时保温的款",
        "买的跑鞋太硬磨脚，要换缓震好的同价位款",
        "洗衣机噪音太大影响睡眠，要换超静音款",
        "买的台式电扇风力太小，要换大风量工业级款",
        "买的护肤品味道太刺激，要换无香型同功效款",
        "买的书包背带太硬，要换人体工学减压背带款",
        "买的鼠标滚轮卡顿，要换顺滑高精度同价位款",
        "炒锅涂层掉落不安全，要换不掉涂层的铸铁款",
        "买的充电宝发热严重，要换散热好的安全款",
        "剃须刀刮不干净，要换更贴面高效的同价位款",
        "台灯只有一档亮度不能调，要换多档调光款",
        "买的椅子坐久了腰疼，要换人体工学椅同价位",
        "买的净化器滤芯消耗快，要换长效滤芯款",
        "热水壶烧水慢，要换3分钟速热的同价位款",
    ],
    "sku_comp": [
        "大疆Mini3 Pro和GoPro HERO12拍摄效果对比",
        "国产三大扫地机石头/科沃斯/追觅综合实力对比",
        "戴森V15和小米K10 Pro哪款吸尘器更适合宠物家庭",
        "苹果手表SE和华为GT4哪个运动健康监测更好",
        "三款热门瑜伽垫lululemon/Keep/迪卡侬怎么选",
        "电动牙刷飞利浦9系和欧乐B IO系列有什么区别",
        "投影仪当电视用：极米H6 vs 当贝X4 vs 坚果N1对比",
        "炒锅不粘锅三大材质：铁锅/钛锅/陶瓷锅怎么选",
        "空调选变频还是定频，同价位哪个更省电",
        "跑步机家用选折叠款还是固定款有什么区别",
        "儿童学习桌三个档位对比：500/1000/2000差在哪",
        "三种养发方法对比：防脱洗发水/生发精华/头皮按摩仪",
        "婴儿纸尿裤国产三大品牌：好奇/帮宝适/花王哪个透气",
        "空气净化器三品牌对比：小米/352/飞利浦过滤效果",
        "电竞椅和人体工学椅的区别，久坐哪个更好",
    ],
    "bundle_purchase": [
        "5000元装修新房客厅，配茶几+落地灯+收纳+地毯",
        "800元大学宿舍神器套装，台灯+风扇+收纳架+插排",
        "2000元新手跑步装备，跑鞋+运动裤+心率带+水壶",
        "1500元为父母配养生套装，足浴盆+按摩枕+血压计",
        "3000元电竞外设升级，鼠标+键盘+耳机+鼠标垫",
        "600元秋冬护肤礼盒，洁面+精华+面霜+眼霜",
        "4000元新婚蜜月行李，旅行箱+收纳袋+旅行洗漱+颈枕",
        "1000元居家健身微型组合，哑铃+跳绳+瑜伽垫+弹力带",
        "2500元摄影师出行装备，相机包+三脚架+清洁套+ND滤镜",
        "700元文创礼物套装，钢笔+笔记本+台历+书立",
        "3500元登山徒步全套，登山鞋+登山杖+冲锋衣+帽子",
        "1200元家庭野餐套装，野餐垫+保温箱+餐具+折叠桌椅",
        "900元孩子绘画兴趣班工具，画板+颜料+画笔+素描本",
        "5000元书房改造，书架+台灯+储物柜+升降桌",
        "2000元宠物主子全套，猫粮+猫砂+猫抓板+猫玩具",
    ],
    "repurchase": [
        "洗衣液快用完了，顺便问有没有更好闻的新香型",
        "矿泉水快喝完要补货，问下有没有更便宜的大桶装",
        "宠物猫粮要补货，顺便推荐肠胃好的新品",
        "打印机墨盒用完了要买，问原装和兼容哪个划算",
        "面膜用完了，顺便问有没有同品牌新出的补水款",
        "婴儿纸尿裤要买了，宝宝9个月应该买哪个码数",
        "健身蛋白粉快吃完，问有没有新口味可以试试",
        "咖啡豆快喝完，推荐最近新出的果味豆",
        "狗狗驱虫药要补，顺便问体外和体内要一起用吗",
        "维生素C快吃完，问有没有带锌的复合版更划算",
        "沐浴露快用完，顺便推荐同品牌有没有新香型",
        "洗发水将近底了，同品牌有没有适合油性头皮的款",
        "纸巾买了多包用完了，现在有没有更便宜的大量装",
        "宝宝米粉用完了，从1段升2段该选什么品牌",
        "洗碗机盐要补货了，推荐用量省的大包装",
    ],
    "matching_purchase": [
        "买了北欧风沙发，需要搭配茶几+地毯+落地灯整体风格",
        "买了跑步机，需要配运动垫+风扇+水壶+毛巾架",
        "为新生儿准备，配婴儿床+婴儿车+哺乳椅+换尿台",
        "买了DSLR相机，配镜头+三脚架+包+清洁套装",
        "买了咖啡机，配磨豆机+咖啡豆+马克杯+咖啡桌垫",
        "装修了小书房，配书桌+书架+台灯+人体工学椅",
        "给孩子配学习区，配学习桌+护眼灯+书包+文具盒",
        "宠物新家，配猫爬架+猫砂盆+猫粮碗+玩具套装",
        "厨房升级，配刀具套装+砧板+锅具+调料架",
        "家庭健身角，配哑铃+瑜伽垫+拉力绳+运动地毯",
    ],
    "place_order": [
        "买了台冰箱收到外包装破损如何处理退换货",
        "下单了想参加满300减50活动，怎么凑单最划算",
        "抢到茅台限量款但一账号只能买一瓶，如何多买",
        "买了手机等了7天未发货，如何催单或申请取消",
        "用京豆抵扣如何查询余额和使用规则",
        "明天有个限时秒杀，如何提前准备确保抢到",
        "收到的手机不是自己选的颜色，如何申请换货",
        "找到更便宜同款，怎么申请价保退差价",
        "下单了礼品要送到父母那里，如何修改收货地址",
        "买了电器想开增值税发票，如何申请企业发票",
        "白条分了12期，现在想提前还款操作步骤是什么",
        "商品显示缺货但想买，怎么设置到货提醒",
        "买了两件商品想合并发货，如何操作",
        "购物平台Plus会员快到期了，续费有什么优惠",
        "买的东西用快递暂存，如何延长存储时间",
    ],
}

SCENARIO_CONFIG = {
    "similar_rec":      ("similar_rec",      "相似品推荐", "SkuRecallShopping"),
    "sku_comp":         ("sku_comp",          "商品对比",   "SkuRecallShopping"),
    "bundle_purchase":  ("bundle_purchase",   "组合购物",   "SkuRecallShopping"),
    "matching_purchase":("matching_purchase", "搭配购物",   "SkuRecallShopping"),
    "repurchase":       ("repurchase",        "复购召回",   "SkuRepurchaseRecall"),
    "place_order":      ("place_order",       "购物下单",   "OrderQuerySkill"),
}


# ───────────── 限流器 ─────────────
class RateLimiter:
    """每秒最多 N 次"""
    def __init__(self, rate: float):
        self.rate = rate
        self.lock = threading.Lock()
        self.timestamps = deque()

    def acquire(self):
        with self.lock:
            now = time.time()
            # 移除1秒前的记录
            while self.timestamps and now - self.timestamps[0] > 1.0:
                self.timestamps.popleft()
            if len(self.timestamps) >= self.rate:
                sleep_time = 1.0 - (now - self.timestamps[0]) + 0.01
                time.sleep(sleep_time)
                now = time.time()
                while self.timestamps and now - self.timestamps[0] > 1.0:
                    self.timestamps.popleft()
            self.timestamps.append(time.time())


RATE_LIMITER = RateLimiter(rate=4)  # 保守4次/s，留余量


# ───────────── API 调用 ─────────────
def call_api(model: str, prompt: str, max_tokens: int = 1400) -> str:
    RATE_LIMITER.acquire()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_TOKEN}",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        "stream": True,
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }

    collected = []  # 所有文本（content + reasoning_content 二选一）
    source = "content"

    try:
        resp = requests.post(API_URL, headers=headers, json=payload,
                             stream=True, timeout=120)
        resp.raise_for_status()

        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8", errors="ignore")
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices", [])
            if not choices:
                continue
            delta = choices[0].get("delta", {})

            # 优先收 content；GLM-5.1 只有 reasoning_content
            text = delta.get("content", "")
            if text:
                source = "content"
                collected.append(text)
            else:
                rc = delta.get("reasoning_content", "")
                if rc:
                    source = "reasoning"
                    collected.append(rc)

    except Exception:
        # 连接中途断开——用已收到的内容继续尝试提取
        pass

    raw = "".join(collected).strip()

    # 提取 JSON（可能不完整时补上末尾 }）
    start = raw.find("{")
    if start == -1:
        raise ValueError(f"未找到JSON，原文前200: {raw[:200]}")
    json_str = raw[start:]

    # 尝试修复不完整的 JSON（末尾缺 }）
    end = json_str.rfind("}")
    if end == -1:
        # 尝试补全：统计未闭合的 { 数量
        depth = 0
        for ch in json_str:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
        if depth > 0:
            json_str += "}" * depth
    else:
        json_str = json_str[:end+1]

    return json_str


def extract_json(text: str) -> dict:
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text).strip()
    start = text.find("{")
    end   = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"未找到JSON，原文前200: {text[:200]}")
    json_str = text[start:end+1]

    # 先试标准 json.loads
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # 再试 json5（容忍尾部逗号、单引号、中文符号等）
    if _HAS_JSON5:
        try:
            return _json5.loads(json_str)
        except Exception:
            pass

    # 最后尝试正则修复常见问题后再解析
    fixed = _fix_json_str(json_str)
    return json.loads(fixed)


def _fix_json_str(s: str) -> str:
    """修复模型输出 JSON 的常见问题"""
    # 替换中文引号
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("‘", "'").replace("’", "'")
    # 移除尾部逗号 ,} 和 ,]
    s = re.sub(r",\s*}", "}", s)
    s = re.sub(r",\s*\]", "]", s)
    # 修复字符串内未转义的换行
    s = re.sub(r'(?<!\\)\n', '\\n', s)
    return s


def validate(d: dict) -> list:
    errors = []
    steps = d.get("steps", [])
    if len(steps) < 2:
        errors.append("steps<2")
        return errors

    # 找 final_response 步骤（不一定是 steps[1]）
    final_step = next((s for s in steps if s.get("step_type") == "final_response"), None)
    tool_steps = [s for s in steps if s.get("step_type") == "tool_call"]

    if final_step is None:
        errors.append("缺final_response步骤")
        return errors

    # 收集所有 tool_call 步骤的 products
    all_products = []
    for ts in tool_steps:
        all_products.extend(ts.get("tool_output", {}).get("products", []))

    cards = final_step.get("product_cards", [])
    fr    = d.get("final_response", "")
    content = final_step.get("content", "")

    if not all_products:
        errors.append("products空")
    if not cards:
        errors.append("cards空")

    prod_ids = {p.get("product_id") for p in all_products}
    for c in cards:
        if c.get("card_id") not in prod_ids:
            errors.append(f"card_id幻觉:{c.get('card_id')}")

    if fr.strip() != content.strip():
        d["final_response"] = content
        fr = content

    if len(fr) < 100:  # 降低阈值到100（place_order 操作步骤较短）
        errors.append(f"回复太短:{len(fr)}字")

    for k in ["trajectory_id", "scenario_type", "user_query", "training_focus"]:
        if not d.get(k):
            errors.append(f"缺:{k}")

    return errors


def make_prompt(sc: str, topic: str) -> str:
    _, _, tool_name = SCENARIO_CONFIG[sc]
    uid = f"sft_gen_{uuid.uuid4().hex[:8]}"
    extra = ""
    if sc == "repurchase":
        extra = "products 第一个商品标题里注明「(X月前购买)」，key_specs 里写「你X月前购买」。"
    elif sc == "place_order":
        extra = "products 只需1个商品或记录，重点是 final_response 里给出详细操作步骤。"
    elif sc == "bundle_purchase":
        extra = "products 列出4-5件套餐单品，final_response 包含总价明细表格。"
    elif sc == "sku_comp":
        extra = "products 列2-4款对比商品，final_response 必须包含 Markdown 对比表格。"
    elif sc == "matching_purchase":
        extra = "根据主商品风格/用途，推荐4-5件搭配单品，products 列出所有单品，final_response 包含整套方案表格和风格搭配理由。"

    return f"""生成一条 {sc} 场景的 Agent 轨迹数据。

场景：{topic}
trajectory_id：{uid}
tool_name 使用：{tool_name}
{extra}

只输出 JSON，第一个字符是 {{"""


# ───────────── Mock 模式（无需内网）─────────────
def run_mock_mode(n: int, scenario: str) -> None:
    """
    使用 shopping_agent 框架的 Mock 数据直接生成 SFT 轨迹。
    无需内网，适合快速扩充数据集。

    用法：python3 llm_gen_oxygen.py -n 100 --mock
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from shopping_agent.tools import create_registry
    from shopping_agent.core.context import AgentContext
    from shopping_agent.agents import (
        SimilarRecAgent, SkuCompAgent, SearchRecommendAgent,
        RepurchaseAgent, MatchingAgent, BundleAgent, OrderAgent,
    )

    registry = create_registry()
    agent_map = {
        "similar_rec":      SimilarRecAgent(registry),
        "sku_comp":         SkuCompAgent(registry),
        "search_recommend": SearchRecommendAgent(registry),
        "repurchase":       RepurchaseAgent(registry),
        "matching_purchase": MatchingAgent(registry),
        "bundle_purchase":  BundleAgent(registry),
        "place_order":      OrderAgent(registry),
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    scenarios = list(SCENARIO_CONFIG.keys()) if scenario == "all" else [scenario]
    ok_count = fail_count = 0
    start = time.time()

    print(f"[{datetime.now():%H:%M:%S}] Mock 模式生成 {n} 条 | 场景={scenario}")

    for i in range(n):
        sc    = scenarios[i % len(scenarios)]
        topic = random.choice(TOPICS[sc])
        agent = agent_map.get(sc)

        tag = f"[{i+1:3d}/{n}] Mock {sc:<18} {topic[:30]}"
        print(tag, end=" ", flush=True)

        try:
            ctx = AgentContext(user_query=topic)
            d = agent.run(ctx)

            # 用 validate 校验格式
            errs = validate(d)
            if errs:
                print(f"✗ {errs}")
                fail_count += 1
                continue

            with WRITE_LOCK:
                with open(OUTPUT, "a", encoding="utf-8") as f:
                    f.write(json.dumps(d, ensure_ascii=False) + "\n")

            ok_count += 1
            fr_len = len(d.get("final_response", ""))
            n_steps = len(d.get("steps", []))
            print(f"✓ {fr_len}字/{n_steps}步")

        except Exception as e:
            print(f"✗ {type(e).__name__}:{str(e)[:60]}")
            fail_count += 1

    elapsed = time.time() - start
    with open(OUTPUT) as f:
        total = sum(1 for _ in f)

    print(f"\n{'='*60}")
    print(f"Mock完成: 成功={ok_count} 失败={fail_count} 耗时={elapsed:.1f}s 总条数={total}")


# ───────────── 主流程 ─────────────
def main():
    global OUTPUT
    parser = argparse.ArgumentParser()
    parser.add_argument("-n",         type=int,   default=20,    help="生成条数")
    parser.add_argument("--scenario", default="all",             help="指定场景或all")
    parser.add_argument("--retries",  type=int,   default=2,     help="单条最大重试")
    parser.add_argument("--mock",     action="store_true",       help="Mock模式（无需内网）")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="输出 JSONL 路径；已有文件会追加")
    args = parser.parse_args()
    OUTPUT = args.output
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    # Mock 模式：使用 shopping_agent 框架本地生成，无需内网
    if args.mock:
        run_mock_mode(args.n, args.scenario)
        return

    scenarios = list(SCENARIO_CONFIG.keys()) if args.scenario == "all" else [args.scenario]
    model_cycle = [MODELS[i % len(MODELS)] for i in range(args.n)]

    ok_count = fail_count = 0
    start = time.time()

    # 统计各模型成功率
    model_stats = {m: {"ok": 0, "fail": 0} for m in MODELS}

    print(f"[{datetime.now():%H:%M:%S}] 生成 {args.n} 条 | 场景={args.scenario} | 模型={len(MODELS)}个轮询")
    print(f"模型列表: {MODELS}\n")

    for i in range(args.n):
        sc    = scenarios[i % len(scenarios)]
        topic = random.choice(TOPICS[sc])
        model = model_cycle[i]
        prompt = make_prompt(sc, topic)

        tag = f"[{i+1:3d}/{args.n}] {model:<22} {sc:<18} {topic[:25]}"
        print(tag, end=" ", flush=True)

        success = False
        for attempt in range(args.retries + 1):
            try:
                raw = call_api(model, prompt)
                d   = extract_json(raw)
                errs = validate(d)

                if errs:
                    print(f"✗ {errs}", end=" ")
                    if attempt < args.retries:
                        # 换一个模型重试
                        model = MODELS[(MODELS.index(model) + 1) % len(MODELS)]
                        print(f"→ 换{model}重试", end=" ", flush=True)
                        continue
                    fail_count += 1
                    model_stats[model]["fail"] += 1
                    print()
                    break

                with WRITE_LOCK:
                    with open(OUTPUT, "a", encoding="utf-8") as f:
                        f.write(json.dumps(d, ensure_ascii=False) + "\n")

                ok_count += 1
                model_stats[model]["ok"] += 1
                fr_len = len(d.get("final_response", ""))
                cards  = len(d["steps"][1].get("product_cards", []))
                print(f"✓ {fr_len}字/{cards}卡")
                success = True
                break

            except requests.exceptions.Timeout:
                print(f"✗ 超时", end=" ")
                if attempt < args.retries:
                    model = MODELS[(MODELS.index(model) + 1) % len(MODELS)]
                    print(f"→ 换{model}重试", end=" ", flush=True)
                    continue
                fail_count += 1
                print()
                break
            except Exception as e:
                print(f"✗ {type(e).__name__}:{str(e)[:60]}", end=" ")
                if attempt < args.retries:
                    time.sleep(1)
                    continue
                fail_count += 1
                print()
                break

    elapsed = time.time() - start
    with open(OUTPUT) as f:
        total = sum(1 for _ in f)

    print(f"\n{'='*60}")
    print(f"完成: 成功={ok_count} 失败={fail_count} 耗时={elapsed:.0f}s 总条数={total}")
    print("各模型统计:")
    for m, s in model_stats.items():
        print(f"  {m:<22} ok={s['ok']} fail={s['fail']}")


if __name__ == "__main__":
    main()
