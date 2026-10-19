import random
from core.data_models import Trajectory, DimensionResult
from llm.judge_interface import JudgeInterface

# 每个维度在 scenario 模式下的评分逻辑：根据轨迹特征返回有意义的 mock 分数
_SCENARIO_RULES: dict[str, callable] = {}


def _scenario(dim_id: str):
    def decorator(fn):
        _SCENARIO_RULES[dim_id] = fn
        return fn
    return decorator


@_scenario("d1_intent_understanding")
def _d1_scenario(trajectory: Trajectory) -> tuple[str, float, str, list[str]]:
    query = trajectory.user_query
    tool_inputs = [
        s.tool_input or {} for s in trajectory.steps if s.step_type == "tool_call"
    ]
    # 合并工具调用的所有参数文本（query + filters）
    all_tool_text = " ".join(
        " ".join(str(v) for v in (ti.items() if isinstance(ti, dict) else []))
        for ti in tool_inputs
    )
    # 也检查最终回复中是否体现了理解
    combined = all_tool_text + " " + trajectory.final_response

    keywords_in_query = _extract_keywords(query)
    if not keywords_in_query:
        return ("PASS", 0.80, "无明确约束词，基本理解需求", [])

    # 对每个关键词做宽松匹配：词本身 or 同义词出现在工具参数/最终回复中
    synonym_map = {
        "老人": ["老人", "老年", "长辈", "60"],
        "简单": ["简单", "易用", "一键", "便捷"],
        "预算": ["预算", "500", "300", "200", "以内", "max_price"],
        "跑步鞋": ["跑步鞋", "跑鞋", "running"],
        "防晒": ["防晒", "遮阳"],
        "透气": ["透气", "网面", "breathable"],
    }

    def is_covered(kw: str) -> bool:
        candidates = synonym_map.get(kw, [kw])
        return any(c in combined for c in candidates)

    missing = [kw for kw in keywords_in_query if not is_covered(kw)]
    total = len(keywords_in_query)
    missing_ratio = len(missing) / max(total, 1)

    if missing_ratio > 0.5:
        return ("FAIL", 0.2, f"工具调用严重遗漏用户约束（{len(missing)}/{total}）：{missing}", missing)
    elif missing_ratio > 0.2:
        return ("PASS", 0.72, f"基本理解需求，有少量约束未体现：{missing}", missing)
    return ("PASS", 0.95, f"准确识别用户需求和约束条件（{total} 个关键词全部覆盖）", [])


@_scenario("d2_factuality")
def _d2_scenario(trajectory: Trajectory) -> tuple[str, float, str, list[str]]:
    returned_ids = trajectory.get_all_returned_product_ids()
    card_ids = trajectory.get_all_card_ids()
    hallucinated = card_ids - returned_ids
    if hallucinated:
        return ("FAIL", 0.1, f"回复中引用了幻觉商品ID: {sorted(hallucinated)}", list(hallucinated))

    # 检查价格引用
    final = trajectory.final_response
    tool_products = []
    for step in trajectory.steps:
        if step.tool_output:
            tool_products.extend(step.tool_output.products)
    prices_in_tools = {str(int(p.price)) for p in tool_products}
    price_mentions = [p for p in prices_in_tools if p in final]
    if not price_mentions and tool_products:
        return ("PASS", 0.7, "未明确引用工具返回价格，建议直接标注价格来源", [])
    return ("PASS", 0.92, "价格引用与工具返回结果一致，无幻觉", price_mentions)


@_scenario("d3_relevance")
def _d3_scenario(trajectory: Trajectory) -> tuple[str, float, str, list[str]]:
    query = trajectory.user_query.lower()
    final = trajectory.final_response.lower()
    tool_products = []
    for step in trajectory.steps:
        if step.tool_output:
            tool_products.extend(step.tool_output.products)

    # 简单检查：推荐的商品标题和用户需求是否有关键词重叠
    card_ids = trajectory.get_all_card_ids()
    recommended = [p for p in tool_products if p.product_id in card_ids]
    if not recommended:
        return ("FAIL", 0.2, "最终回复未推荐任何商品", [])

    keywords = _extract_keywords(query)
    matched = []
    for p in recommended:
        title_lower = p.title.lower()
        for kw in keywords:
            if kw in title_lower or kw in final:
                matched.append(kw)
    matched = list(set(matched))

    if len(matched) < max(1, len(keywords) // 2):
        return ("PASS", 0.65, "推荐商品与需求部分匹配，相关性一般", matched)
    return ("PASS", 0.88, f"推荐商品紧扣用户需求，关键词匹配：{matched}", matched)


@_scenario("d4_completeness")
def _d4_scenario(trajectory: Trajectory) -> tuple[str, float, str, list[str]]:
    final = trajectory.final_response
    card_ids = trajectory.get_all_card_ids()
    query = trajectory.user_query

    # 回复过短（少于30字）
    if len(final.strip()) < 30:
        return ("FAIL", 0.1, f"最终回复过短（{len(final.strip())}字），未完整覆盖用户需求", [])

    # 没有商品卡片
    if not card_ids:
        return ("FAIL", 0.2, "回复中未包含任何商品卡片，未完成推荐任务", [])

    # 检测用户明确提出了对比需求但未对比
    needs_comparison = any(w in query for w in ["对比", "竞品", "比较", "哪款好", "值不值", "推荐几款"])
    final_has_comparison = any(w in final for w in ["对比", "相比", "优于", "1.", "1、", "①", "第一", "第二"])
    if needs_comparison and not final_has_comparison:
        return ("FAIL", 0.3, "用户要求对比竞品/多款推荐，但回复未提供对比分析", ["需要对比分析"])

    # 检查是否包含价格（电商场景必须）
    has_price = any(c.isdigit() for c in final)
    if not has_price:
        return ("PASS", 0.65, "有商品卡片但回复中缺少价格信息", [])

    return ("PASS", 0.95, f"回复完整，包含 {len(card_ids)} 个商品卡片、价格信息和推荐理由", [])


@_scenario("d5_reasoning_value")
def _d5_scenario(trajectory: Trajectory) -> tuple[str, float, str, list[str]]:
    final = trajectory.final_response
    vague_words = ["不错", "性价比高", "值得购买", "好用", "品质有保障", "推荐"]
    specific_indicators = ["档", "毫安", "像素", "克", "升", "年保", "防水", "降噪", "小时续航"]

    vague_count = sum(1 for w in vague_words if w in final)
    specific_count = sum(1 for w in specific_indicators if w in final)

    # 每张卡片的 reason 字段平均长度
    all_cards = []
    for step in trajectory.steps:
        all_cards.extend(step.product_cards)
    avg_reason_len = sum(len(c.reason) for c in all_cards) / max(len(all_cards), 1)

    if specific_count >= 2 and avg_reason_len > 15:
        return ("PASS", 0.88, f"推荐理由具体（含 {specific_count} 个产品参数），信息量充足", [])
    elif vague_count >= 3 and specific_count == 0:
        return ("PASS", 0.45, f"推荐理由过于空泛（含{vague_count}个套话），缺乏具体参数支撑", list(set(w for w in vague_words if w in final)))
    return ("PASS", 0.68, "推荐理由有一定具体性，但仍可进一步丰富", [])


def _extract_keywords(query: str) -> list[str]:
    """
    从用户查询中提取关键约束词。
    策略：基于购物领域词表做正向匹配，而不是无监督分词切片，
    确保提取出来的词都是有意义的商品属性/场景/约束词。
    """
    import re

    # 购物场景高频领域词（按重要性排序，优先匹配长词）
    domain_words = [
        # 人群/场景
        "老年人", "老人", "儿童", "小孩", "学生", "女性", "男性", "孕妇",
        # 使用场景
        "跑步", "健身", "办公", "户外", "游泳", "防水", "露营",
        # 功能需求
        "防晒", "透气", "保暖", "降噪", "无线", "蓝牙", "快充", "长续航",
        "操作简单", "简单操作", "简单", "轻便", "折叠",
        # 商品品类（核心）
        "按摩仪", "跑步鞋", "耳机", "手机", "电视", "冰箱", "空调",
        "洗衣机", "净化器", "加湿器", "吸尘器", "扫地机",
        # 预算约束
        "预算",
        # 品牌（常见）
        "小米", "华为", "苹果", "三星", "飞利浦", "索尼",
    ]

    # 按词长度降序排，优先匹配长词，防止"跑步"被"跑步鞋"覆盖后又重复提取
    domain_words.sort(key=len, reverse=True)
    found = []
    remaining = query
    for w in domain_words:
        if w in remaining:
            found.append(w)
            remaining = remaining.replace(w, " ")  # 已匹配的不再重复提取

    # 再提取纯数字（价格/年龄等数值约束）
    numbers = re.findall(r"[0-9]+", query)
    for n in numbers:
        if len(n) >= 2 and n not in found:  # 过滤单个数字
            found.append(n)

    return found[:8]


class MockJudge(JudgeInterface):
    """
    Mock LLM judge，支持三种模式：
    - fixed: 所有维度固定返回 PASS，score=0.85（用于调试 UI）
    - random: 随机分数，偶尔触发 FAIL（用于压力测试）
    - scenario: 根据轨迹特征返回有意义的分数（默认，最适合演示）
    """

    def __init__(self, mode: str = "mock_scenario"):
        assert mode in ("mock_fixed", "mock_random", "mock_scenario"), f"Unknown mode: {mode}"
        self.mode = mode

    def get_judge_name(self) -> str:
        return self.mode

    def evaluate(self, dimension_id: str, dimension_label: str, trajectory: Trajectory) -> DimensionResult:
        if self.mode == "mock_fixed":
            return DimensionResult(
                dimension_id=dimension_id,
                dimension_label=dimension_label,
                verdict="PASS",
                score=0.85,
                reasoning="[Mock-Fixed] 固定返回 PASS，用于 UI 调试",
                evidence=[],
            )
        elif self.mode == "mock_random":
            score = round(random.uniform(0.4, 1.0), 2)
            verdict = "PASS" if score >= 0.6 else "FAIL"
            return DimensionResult(
                dimension_id=dimension_id,
                dimension_label=dimension_label,
                verdict=verdict,
                score=score,
                reasoning=f"[Mock-Random] 随机分数 {score}",
                evidence=[],
            )
        else:  # mock_scenario
            rule_fn = _SCENARIO_RULES.get(dimension_id)
            if rule_fn:
                verdict, score, reasoning, evidence = rule_fn(trajectory)
            else:
                verdict, score, reasoning, evidence = "PASS", 0.80, "[Mock-Scenario] 默认通过", []
            return DimensionResult(
                dimension_id=dimension_id,
                dimension_label=dimension_label,
                verdict=verdict,
                score=score,
                reasoning=reasoning,
                evidence=evidence,
            )
