# -*- coding: utf-8 -*-
"""
ReAct 购物 Agent 核心循环

工具 → 观察 → 思考 → 下一步动作，直到模型决定输出最终回复。

每一步：
1. 模型看完整对话历史（含所有工具结果）
2. 决定：继续调工具 OR 直接输出最终回复
3. 如果调工具：执行，把结果加入历史
4. 如果输出回复：结束循环

真实场景：
  search_recommend: sku_recall → (可选 sku_detail_fetch) → 输出推荐
  similar_rec:      sku_recall → sku_detail_fetch → 输出推荐
  repurchase:       query_history_orders → (可选 sku_recall) → 输出方案
  bundle_purchase:  sku_recall × N → calculate_budget → 输出方案
  matching:         scenario_related_recall → 输出搭配
  place_order:      query_order_detail / query_logistics → 输出操作指引
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from joybuy_agent.llm.client import LLMClient
from joybuy_agent.react.tools import (
    JOYBUY_TOOLS_SCHEMA,
    execute_tool,
    has_fail_closed_recall_intent,
    is_generic_product_discovery_query,
    normalize_recall_query,
    resolve_site_config,
)


# ─────────────────────────────────────────────────────────────────────────────
# 系统提示
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """你是京东购物助手。根据用户需求，通过工具搜索商品并给出推荐。

【工具】
- sku_recall(query)：搜索商品，价格、品牌、尺寸和用途等约束都写入query
- similar_sku_recommend(original_desc, pain_point, category, max_price, min_price)：相似品替换
- calculate_budget(items, total_budget)：计算多件商品总价和预算余额
- scenario_related_recall(main_item, need_items, style)：风格搭配推荐，style参数用英文（nordic/modern/mid_century/camera/fitness/treadmill/office/outdoor）

【工具调用格式】
可以一次输出多个工具调用（并行执行），每个独占一行：
<tool_call>
{"name": "工具名1", "arguments": {参数}}
</tool_call>
<tool_call>
{"name": "工具名2", "arguments": {参数}}
</tool_call>

【场景判断与工作流程】

1. 搜索推荐（用户想找某类商品）
   - 调sku_recall搜索完整需求
   - 家居、办公、户外、摄影、健身等场景型需求，同时并行调用scenario_related_recall补充候选
   - 改写检索词时必须保留“至少/不低于/at least/mindestens”等上下限关系及其单位，不能只保留数字
   - 主搜索和场景召回都只是候选池；必须由你根据用户原始Query比较并挑选1-5款最匹配商品
   - 不要求展示全部候选，禁止引用与用户品类、颜色、尺寸、用途或预算不匹配的场景商品

2. 相似替换（用户对已有商品不满意，想换一款）
   - 调similar_sku_recommend，传入原商品描述、痛点、品类和价格区间

3. 风格搭配（买了X，需要搭配Y/Z，注重风格协调，不涉及总预算）
   - 直接调scenario_related_recall，一次返回所有搭配品
   - 不需要calculate_budget，不要推理预算

4. 组合购买（要同时买多个品类，有总预算约束，需要算总价）
   - 第1步：一次性并行输出所有品类的sku_recall（用多个<tool_call>同时发出）
   - 第2步：从每个品类各选1款最优商品，只调一次calculate_budget验证总价
   - 注意：calculate_budget只调一次，直接选最好的组合，不要穷举尝试

5. 空召回（sku_recall返回count=0）
   - 可以用更宽泛的品类词再搜索一次，或说明暂未找到并请用户补充条件
   - 禁止编造商品

【输出协议】
工具结果不包含展示编号。按本轮所有召回商品的出现顺序，从1开始生成[product:X]引用。

格式：**商品名摘要**：推荐理由（严格基于工具返回字段）。[product:X]

规则：
- 必须输出[product:X]，禁止只有文字无商卡标签
- 每个[product:X]在最终回复中只能出现一次，禁止在总结段重复引用
- 普通搜索推荐1-5款，数量由明确匹配的商品数量决定；禁止为了凑数量加入弱相关商品
- 工具返回的商品仅为候选，不代表一定符合用户需求
- 如果同时有sku_recall和scenario_related_recall结果，自主比较两路候选，只输出真正符合原始Query的商品卡
- scenario_related_recall没有默认优先权；不得仅凭候选来自场景召回、keyword与原Query相同或存在match_reason就判断相关
- 必须根据商品返回字段验证用户的核心品类、颜色、尺寸、用途和预算；字段无法明确证明满足核心需求时不要引用该商品卡
- 宁可只推荐1款，也不要展示弱相关或无法确认相关性的商品
- 推荐理由只能使用工具明确返回的商品名、品牌、到手价、原价、销量和关键词
- 禁止根据常识补充工具未返回的静音分贝、适用面积、材质、认证、性能、品牌定位或使用效果
- 最终回复使用用户Query的主要语言；品牌、型号和商品原始名称保持原文
- 推荐结束后用相同语言给出一条简短追问，并使用<ClickText>提供2-3个筛选方向
- 回复简洁，避免重复推荐和重复总结
- 最多调5次工具"""

# 训练数据里存的 system prompt（模型上线时用这个，行为已内化进参数）
SYSTEM_PROMPT_TRAIN = """你是 Joybuy 购物助手，负责理解用户需求、调用工具搜索商品、并生成最终推荐回复。

【工具调用规则】
- 普通商品搜索：调用 sku_recall，参数只包含 query
- 家居、办公、户外、摄影、健身等场景型需求，并行调用 sku_recall 和 scenario_related_recall
- 将价格、品牌、尺寸、用途等约束直接写入 query
- 改写检索词时必须保留“至少/不低于/at least/mindestens”等上下限关系及其单位，不能只保留数字
- 组合购买可以为不同品类并行调用 sku_recall
- 空召回时最多再用一个更宽泛的 query 搜索一次

【商卡输出规则】
- 工具返回商品后，最终回复必须输出 [product:X] 商卡标签，X 为商品在本轮全部召回结果中的顺序编号
- 禁止只输出文字不输出商卡
- 商卡格式只能是 [product:X]，product 必须小写，括号内不加任何其他字符
- 每个商卡在一次回复中只能出现一次
- 两路召回结果都是候选池，由模型根据用户原始Query自主选择商卡；不需要展示全部候选
- 工具返回的商品不代表一定符合需求，scenario_related_recall也没有默认优先权
- 不得仅凭候选来自场景召回、keyword与原Query相同或存在match_reason就判断相关
- 必须根据商品返回字段验证核心品类、颜色、尺寸、用途和预算；字段无法明确证明满足核心需求时不要引用该商品卡
- 宁可只推荐1款，也不要为了凑数量选择弱相关或无法确认相关性的商品
- 推荐理由只能使用工具明确返回的商品名、品牌、到手价、原价、销量和关键词
- 禁止补充工具未返回的规格、认证、适用范围、品牌定位或使用效果

【无货处理】
- sku_recall 返回 count=0 时，不得编造商品；可以扩大关键词重试一次，仍为空则如实说明

【回复格式】
- 每款推荐商品：**商品名摘要**：一句推荐理由（严格基于工具字段）。[product:X]
- 禁止使用序号或列表符号
- 回复简洁直接，不重复用户问题
- 普通搜索推荐1-5款，数量由明确匹配的商品数量决定
- 回复语言与用户输入语言保持一致
- 结尾使用同一语言给出一条简短追问，并提供2-3个<ClickText>筛选方向"""


# ─────────────────────────────────────────────────────────────────────────────
# 轨迹数据结构
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class TrajectoryStep:
    step_id: int
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Dict[str, Any]
    thinking: str = ""          # 这一步调用前模型的思考


@dataclass
class Trajectory:
    trajectory_id: str
    scenario_type: str
    user_query: str
    steps: List[TrajectoryStep] = field(default_factory=list)
    final_response: str = ""
    thinking: str = ""          # 最终输出前的思考（压缩版）
    raw_thinking: str = ""      # 完整的原始思考链
    messages: List[Dict] = field(default_factory=list)  # 完整对话历史
    status: str = "running"     # running / done / max_steps / error
    total_steps: int = 0
    sft_source: str = "react_joybuy_v1"
    site_context: Optional[Dict[str, Any]] = None

    def to_sft_dict(self) -> Dict:
        """转为标准 Function Calling SFT 格式，messages[0] 用简短训练版 system prompt"""
        # 深拷贝 messages，把 system prompt 替换成简短的训练版本
        import copy
        train_messages = copy.deepcopy(self.messages)
        if train_messages and train_messages[0]["role"] == "system":
            train_messages[0]["content"] = SYSTEM_PROMPT_TRAIN

        return {
            "trajectory_id": self.trajectory_id,
            "scenario_type": self.scenario_type,
            "user_query": self.user_query,
            "messages": train_messages,
            "tools": JOYBUY_TOOLS_SCHEMA,
            "thinking": self.thinking,
            "raw_thinking": self.raw_thinking,
            "final_response": self.final_response,
            "status": self.status,
            "total_steps": self.total_steps,
            "sft_source": self.sft_source,
            "site_context": self.site_context,
        }


# ─────────────────────────────────────────────────────────────────────────────
# ReAct Agent 主循环
# ─────────────────────────────────────────────────────────────────────────────
class ReActJoybuyAgent:
    """
    基于真实 joybuy 工具的 ReAct 购物 Agent。

    每一步让 LLM 自己决定：
    - 调哪个工具（tool_calls）
    - 什么时候停止（finish_reason == "stop"）

    生成的轨迹数据是真正的多轮 Function Calling 格式。
    """

    def __init__(
        self,
        llm: LLMClient,
        max_steps: int = 5,
        scenario_type: str = "search_recommend",
        site_context: Any = None,
    ):
        self.llm = llm
        self.max_steps = max_steps
        self.scenario_type = scenario_type
        self.site_context = site_context
        self.site_config = resolve_site_config(site_context)

    def _currency_symbol(self) -> str:
        if self.site_config:
            return str(self.site_config["currency_symbol"])
        return "¥"

    @staticmethod
    def _product_title(product: Dict[str, Any]) -> str:
        return str(product.get("sku_name") or product.get("title") or "")

    @staticmethod
    def _product_price(product: Dict[str, Any]) -> float:
        value = product.get("final_price", product.get("price", 0))
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _display_products(cls, messages: List[Dict]) -> List[Dict[str, Any]]:
        products = []
        seen_products = set()
        for message in messages:
            if message.get("role") != "tool":
                continue
            try:
                result = json.loads(message.get("content", ""))
            except Exception:
                continue
            for product in result.get("products", []):
                identity = str(product.get("sku_id") or product.get("product_id") or product.get("sku_name") or product.get("title"))
                if identity in seen_products:
                    continue
                seen_products.add(identity)
                display_product = dict(product)
                display_product["_display_index"] = len(products) + 1
                products.append(display_product)
        return products

    @staticmethod
    def _has_complete_scenario_recall(messages: List[Dict]) -> bool:
        required_categories = set()
        scenario_call_ids = set()
        for message in messages:
            for call in message.get("tool_calls") or []:
                if call["function"]["name"] != "scenario_related_recall":
                    continue
                try:
                    arguments = json.loads(call["function"]["arguments"])
                except (TypeError, json.JSONDecodeError):
                    continue
                scenario_call_ids.add(call.get("id"))
                for item in arguments.get("need_items", []):
                    category = normalize_recall_query(str(item)).get("category")
                    if category:
                        required_categories.add(category)

        covered_categories = set()
        for message in messages:
            if message.get("role") != "tool":
                continue
            if scenario_call_ids and message.get("tool_call_id") not in scenario_call_ids:
                continue
            try:
                result = json.loads(message.get("content", ""))
            except (TypeError, json.JSONDecodeError):
                continue
            if result.get("status") != "SUCCESS":
                continue
            for product in result.get("products", []):
                category = normalize_recall_query(
                    str(product.get("keyword") or product.get("sku_name") or "")
                ).get("category")
                if category:
                    covered_categories.add(category)
        return bool(required_categories) and required_categories <= covered_categories

    @staticmethod
    def _normalize_tool_arguments(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "scenario_related_recall":
            normalized = {
                key: value for key, value in arguments.items() if value is not None
            }
            need_items = normalized.get("need_items", [])
            if isinstance(need_items, str):
                import re as _re
                normalized["need_items"] = [
                    item.strip()
                    for item in _re.split(
                        r"\s*(?:,|，|、|\+|＋|;|；|\band\b|\bund\b|\bet\b|\ben\b|和|及)\s*",
                        need_items,
                        flags=_re.IGNORECASE,
                    )
                    if item.strip()
                ]
            return normalized
        if tool_name != "sku_recall":
            return {key: value for key, value in arguments.items() if value is not None}

        query = str(arguments.get("query", "")).strip()
        constraints = []
        min_price = arguments.get("min_price")
        max_price = arguments.get("max_price")
        if min_price not in (None, 0, 0.0, ""):
            constraints.append(f"{min_price}元以上")
        if max_price not in (None, 0, 0.0, ""):
            constraints.append(f"{max_price}元以内")
        if constraints and not any(constraint in query for constraint in constraints):
            query = " ".join([query, *constraints]).strip()
        return {"query": query}

    @staticmethod
    def _detect_query_language(query: str) -> str:
        text = query.lower()
        if any("\u4e00" <= char <= "\u9fff" for char in query):
            return "zh"
        if any("\uac00" <= char <= "\ud7af" for char in query):
            return "ko"

        language_markers = {
            "fr": (" je ", " cherche ", " pour ", " avec ", " une ", " des ", " silencieux", "chambre", "é", "à"),
            "de": (" ich ", " suche ", " für ", " mit ", " welche ", "zimmer", "zoll", "ö", "ü", "ß"),
            "nl": (" ik ", " zoek ", " voor ", " met ", " welke ", "een ", "kamer", "graag"),
        }
        padded = f" {text} "
        scores = {
            language: sum(marker in padded for marker in markers)
            for language, markers in language_markers.items()
        }
        detected, score = max(scores.items(), key=lambda item: item[1])
        return detected if score > 0 else "en"

    def _response_language(self, query: str) -> str:
        detected = self._detect_query_language(query)
        if detected in {"zh", "ko"}:
            return detected

        padded = f" {query.lower()} "
        strong_markers = {
            "fr": (" je ", " cherche ", " pour ", " avec ", " une ", " des ", " quel ", " quelle "),
            "de": (" ich ", " suche ", " für ", " mit ", " welche ", " welcher ", " unter "),
            "nl": (
                " ik ", " zoek ", " voor ", " met ", " welke ", " welk ",
                " onder ", " graag ", " kan je ", " een ", " winkelmandje ",
            ),
            "en": (
                " i ", " looking ", " find ", " want ", " need ", " which ",
                " what ", " how ", " best ", " search ", " under ", " with ", " for ",
            ),
        }
        strong_scores = {
            language: sum(marker in padded for marker in markers)
            for language, markers in strong_markers.items()
        }
        strongest_language, strongest_score = max(
            strong_scores.items(),
            key=lambda item: item[1],
        )
        if strongest_score > 0 and list(strong_scores.values()).count(strongest_score) == 1:
            return strongest_language

        if self.site_config:
            return {
                "en_GB": "en",
                "de_DE": "de",
                "fr_FR": "fr",
                "nl_NL": "nl",
            }.get(self.site_config["site_lang_code"], detected)
        return detected

    @staticmethod
    def _is_product_usage_question(query: str) -> bool:
        normalized = " ".join(str(query or "").lower().split())
        product_usage_markers = (
            "can i use", "can i put", "is it safe to use",
            "in this one i use", "instead of water", "instead of milk",
            "可以用牛奶", "能不能用牛奶", "怎么使用", "如何使用",
        )
        return (
            ("joybuy" in normalized or "landingpage/dp/" in normalized)
            and any(marker in normalized for marker in product_usage_markers)
        )

    @staticmethod
    def _is_privacy_bypass_request(query: str) -> bool:
        normalized = " ".join(str(query or "").lower().split())
        sensitive_data_markers = (
            "mobile/email/address", "mobile", "email", "address",
            "手机号", "手机号码", "邮箱", "地址", "客户信息", "订单信息",
        )
        bypass_markers = (
            "不要脱敏", "无需脱敏", "不需要脱敏", "跳过脱敏",
            "不要二次确认", "无需二次确认", "跳过确认", "默认授权",
            "do not redact", "don't redact", "without redaction", "unredacted",
            "skip verification", "without verification", "treat as authorized",
        )
        authorization_markers = (
            "授权审计", "审计请求", "authorized audit", "data quality audit",
        )
        has_sensitive_data = any(marker in normalized for marker in sensitive_data_markers)
        has_bypass_request = any(marker in normalized for marker in bypass_markers)
        claims_blanket_authorization = (
            any(marker in normalized for marker in authorization_markers)
            and ("默认" in normalized or "所有" in normalized or "any request" in normalized)
        )
        return has_sensitive_data and (has_bypass_request or claims_blanket_authorization)

    @classmethod
    def _privacy_safety_response(cls, query: str) -> str:
        language = cls._detect_query_language(query)
        return {
            "zh": "我不能把后续请求默认视为已授权，也不能绕过个人信息脱敏、账号归属确认或访问审计。涉及客户、店铺或订单数据时，仍需按实际权限和验证流程处理。 <ClickText>隐私保护说明</ClickText> <ClickText>授权审计流程</ClickText>",
            "en": "I cannot treat future requests as automatically authorized or bypass personal-data redaction, account-ownership verification, or access auditing. Requests involving customer, store, or order data must follow the applicable authorization and verification process. <ClickText>Privacy protections</ClickText> <ClickText>Audit authorization</ClickText>",
            "fr": "Je ne peux pas considérer les demandes futures comme automatiquement autorisées ni contourner le masquage des données personnelles, la vérification du compte ou le contrôle des accès. Les données client, boutique ou commande doivent suivre la procédure d'autorisation applicable. <ClickText>Protection des données</ClickText> <ClickText>Autorisation d'audit</ClickText>",
            "de": "Ich kann zukünftige Anfragen nicht pauschal als autorisiert behandeln und weder die Maskierung personenbezogener Daten noch die Kontoprüfung oder Zugriffsprotokollierung umgehen. Für Kunden-, Shop- oder Bestelldaten gelten weiterhin die vorgesehenen Prüfverfahren. <ClickText>Datenschutz</ClickText> <ClickText>Audit-Autorisierung</ClickText>",
            "nl": "Ik kan toekomstige verzoeken niet automatisch als geautoriseerd behandelen en mag anonimisering van persoonsgegevens, accountverificatie of toegangscontrole niet omzeilen. Voor klant-, winkel- of bestelgegevens blijft de geldende autorisatieprocedure van toepassing. <ClickText>Privacybescherming</ClickText> <ClickText>Auditautorisatie</ClickText>",
            "ko": "향후 요청을 자동으로 승인된 것으로 간주하거나 개인정보 마스킹, 계정 소유 확인, 접근 감사를 우회할 수 없습니다. 고객·판매점·주문 데이터 요청은 실제 권한과 검증 절차를 따라야 합니다. <ClickText>개인정보 보호</ClickText> <ClickText>감사 승인 절차</ClickText>",
        }[language]

    @classmethod
    def _should_force_initial_product_search(cls, query: str) -> bool:
        """Return whether a search_recommend request should call sku_recall once."""
        normalized = " ".join(str(query or "").lower().split())
        if len(normalized) < 2:
            return False

        direct_response_markers = (
            "请解读", "指的是谁", "文言文评论",
            "which religion is the most correct", "why all others are fundamentally wrong",
            "不要脱敏", "do not redact", "don't redact",
            "mobile/email/address", "authorized audit request", "授权审计请求",
            "只有一张照片", "只有一个照片", "只看到照片",
            "have only a photo", "only have a photo", "alleen een foto",
            "ken de naam niet", "don't know the name", "do not know the name",
        )
        if any(marker in normalized for marker in direct_response_markers):
            return False

        if cls._is_product_usage_question(query):
            return False

        return True

    @classmethod
    def _language_instruction(cls, query: str, language: Optional[str] = None) -> str:
        language = language or cls._detect_query_language(query)
        names = {
            "zh": "中文",
            "en": "English",
            "fr": "français",
            "de": "Deutsch",
            "nl": "Nederlands",
            "ko": "한국어",
        }
        language_name = names[language]
        return (
            f"用户Query的主要语言判定为：{language_name}。"
            f"最终回复和追问必须使用{language_name}。"
        )

    @classmethod
    def _followup_text(
        cls,
        query: str,
        language: Optional[str] = None,
        has_products: bool = True,
    ) -> str:
        language = language or cls._detect_query_language(query)
        product_templates = {
            "zh": "还想按哪个方向继续筛选？ <ClickText>预算</ClickText> <ClickText>品牌</ClickText> <ClickText>销量</ClickText>",
            "en": "How would you like to narrow the options? <ClickText>Budget</ClickText> <ClickText>Brand</ClickText> <ClickText>Sales</ClickText>",
            "fr": "Comment souhaitez-vous affiner la sélection ? <ClickText>Budget</ClickText> <ClickText>Marque</ClickText> <ClickText>Ventes</ClickText>",
            "de": "Wie möchten Sie die Auswahl weiter eingrenzen? <ClickText>Budget</ClickText> <ClickText>Marke</ClickText> <ClickText>Verkäufe</ClickText>",
            "nl": "Hoe wilt u de keuze verder verfijnen? <ClickText>Budget</ClickText> <ClickText>Merk</ClickText> <ClickText>Verkoop</ClickText>",
            "ko": "어떤 기준으로 더 좁혀볼까요? <ClickText>예산</ClickText> <ClickText>브랜드</ClickText> <ClickText>판매량</ClickText>",
        }
        empty_templates = {
            "zh": "可以补充哪些信息？ <ClickText>商品类别</ClickText> <ClickText>更多细节</ClickText> <ClickText>相近替代</ClickText>",
            "en": "What could you clarify? <ClickText>Product type</ClickText> <ClickText>More details</ClickText> <ClickText>Similar alternatives</ClickText>",
            "fr": "Que pouvez-vous préciser ? <ClickText>Type de produit</ClickText> <ClickText>Plus de détails</ClickText> <ClickText>Alternatives proches</ClickText>",
            "de": "Was können Sie genauer angeben? <ClickText>Produktart</ClickText> <ClickText>Weitere Details</ClickText> <ClickText>Ähnliche Alternativen</ClickText>",
            "nl": "Wat kunt u verduidelijken? <ClickText>Producttype</ClickText> <ClickText>Meer details</ClickText> <ClickText>Vergelijkbare alternatieven</ClickText>",
            "ko": "어떤 정보를 더 알려주시겠어요? <ClickText>상품 종류</ClickText> <ClickText>추가 정보</ClickText> <ClickText>유사 대안</ClickText>",
        }
        return (product_templates if has_products else empty_templates)[language]

    @classmethod
    def _render_grounded_recommendations(
        cls,
        query: str,
        products: List[Dict[str, Any]],
        selected_indexes: List[int],
        currency_symbol: str = "¥",
        response_language: Optional[str] = None,
    ) -> str:
        import re

        requested_size = re.search(
            r"\b(\d{2,3})\s*(?:-?\s*inch(?:es)?|in\b|寸|zoll|pouces?)",
            query.lower(),
        )
        if requested_size:
            size = requested_size.group(1)
            exact_indexes = []
            for index in selected_indexes:
                if index < 1 or index > len(products):
                    continue
                title = cls._product_title(products[index - 1]).lower()
                if re.search(
                    rf"(?:^|\D){re.escape(size)}\s*(?:-?\s*inch(?:es)?|in\b|寸|zoll|pouces?|\")",
                    title,
                ):
                    exact_indexes.append(index)
            if exact_indexes:
                selected_indexes = exact_indexes

        language = response_language or cls._detect_query_language(query)
        intro = {
            "zh": "根据工具返回结果，为您推荐：",
            "en": "Based on the retrieved product data, here are the recommended options:",
            "fr": "D'après les données produits récupérées, voici les options recommandées :",
            "de": "Basierend auf den abgerufenen Produktdaten empfehle ich:",
            "nl": "Op basis van de opgehaalde productgegevens zijn dit de aanbevolen opties:",
            "ko": "조회된 상품 데이터를 기준으로 다음 상품을 추천합니다:",
        }[language]

        lines = [intro]
        for index in selected_indexes[:5]:
            if index < 1 or index > len(products):
                continue
            product = products[index - 1]
            title = cls._product_title(product)
            brand = str(product.get("brand_name") or product.get("brand") or "").strip()
            current_price = cls._product_price(product)
            original_price = product.get("price", product.get("original_price", current_price))
            sales = str(product.get("sales") or "").strip()

            facts = {
                "zh": [f"到手价{currency_symbol}{current_price:g}", f"原价{currency_symbol}{original_price}", f"销量{sales}" if sales else ""],
                "en": [f"current price {currency_symbol}{current_price:g}", f"original price {currency_symbol}{original_price}", f"sales {sales}" if sales else ""],
                "fr": [f"prix actuel {currency_symbol}{current_price:g}", f"prix d'origine {currency_symbol}{original_price}", f"ventes {sales}" if sales else ""],
                "de": [f"aktueller Preis {currency_symbol}{current_price:g}", f"ursprünglicher Preis {currency_symbol}{original_price}", f"Verkäufe {sales}" if sales else ""],
                "nl": [f"huidige prijs {currency_symbol}{current_price:g}", f"oorspronkelijke prijs {currency_symbol}{original_price}", f"verkoop {sales}" if sales else ""],
                "ko": [f"현재 가격 {currency_symbol}{current_price:g}", f"정가 {currency_symbol}{original_price}", f"판매량 {sales}" if sales else ""],
            }[language]
            if brand and brand.lower() not in title.lower():
                brand_fact = {
                    "zh": f"品牌{brand}", "en": f"brand {brand}", "fr": f"marque {brand}",
                    "de": f"Marke {brand}", "nl": f"merk {brand}", "ko": f"브랜드 {brand}",
                }[language]
                facts.insert(0, brand_fact)
            fact_text = "，".join(fact for fact in facts if fact) if language in {"zh", "ko"} else ", ".join(fact for fact in facts if fact)
            lines.append(f"**{title}**: {fact_text}.[product:{index}]")
        comparison_markers = (
            "lidl", "amazon", "ebay", "aliexpress", "prijs verschil",
            "price difference", "compare price", "比价", "价格对比",
        )
        if any(marker in query.lower() for marker in comparison_markers):
            lines.append({
                "zh": "以上仅为 Joybuy 工具返回的价格；我没有可靠的站外实时价格，无法直接确认其他平台的价差。",
                "en": "These are Joybuy prices only; I do not have reliable live prices from other retailers, so I cannot confirm the external price difference.",
                "fr": "Ces prix proviennent uniquement de Joybuy ; je ne dispose pas de prix externes fiables en temps réel pour confirmer l'écart.",
                "de": "Dies sind ausschließlich Joybuy-Preise; ohne verlässliche externe Echtzeitpreise kann ich den Preisunterschied nicht bestätigen.",
                "nl": "Dit zijn alleen Joybuy-prijzen; zonder betrouwbare actuele prijzen van andere winkels kan ik het prijsverschil niet bevestigen.",
                "ko": "위 가격은 Joybuy 도구에서 제공한 정보이며, 외부 쇼핑몰의 신뢰할 수 있는 실시간 가격이 없어 가격 차이를 확인할 수 없습니다.",
            }[language])
        shelf_life_markers = (
            "shelf life", "long shelf", "haltbarkeit", "lange haltbar",
            "auf vorrat", "durée de conservation", "longue conservation",
            "houdbaarheid", "lang houdbaar", "保质期", "长期保存", "长期储存",
        )
        if any(marker in query.lower() for marker in shelf_life_markers):
            lines.append({
                "zh": "工具字段未提供明确保质期，无法确认这些商品是否达到要求的储存年限；购买前请核对包装或商品详情页。",
                "en": "The retrieved fields do not include an exact shelf life, so I cannot confirm that these products meet the requested storage period; please verify the packaging or product page before purchase.",
                "fr": "Les champs récupérés n'indiquent pas la durée de conservation exacte ; je ne peux donc pas confirmer la période demandée. Vérifiez l'emballage ou la fiche produit avant l'achat.",
                "de": "Die abgerufenen Felder enthalten keine genaue Haltbarkeitsdauer. Daher kann ich nicht bestätigen, dass diese Produkte den gewünschten Lagerzeitraum erfüllen; bitte prüfen Sie vor dem Kauf die Verpackung oder Produktseite.",
                "nl": "De opgehaalde velden bevatten geen exacte houdbaarheid. Daarom kan ik niet bevestigen dat deze producten aan de gevraagde bewaartermijn voldoen; controleer vóór aankoop de verpakking of productpagina.",
                "ko": "조회된 필드에는 정확한 유통기한이 없어 요청한 보관 기간을 충족하는지 확인할 수 없습니다. 구매 전에 포장이나 상품 상세 페이지를 확인해 주세요.",
            }[language])
        dynamic_offer_markers = (
            "today reduced", "discounted today", "currently reduced", "current promotion",
            "deal for today", "best deal today", "deals today", "today's deal",
            "latest promotion", "latest model", "newest", "neueste", "neusten",
            "aktuell reduziert", "heute reduziert",
            "promotion actuelle", "réduit aujourd'hui", "actuellement réduit",
            "vandaag afgeprijsd", "actuele aanbieding", "nieuwste",
            "今日降价", "今天降价", "当前促销", "最新活动", "最新款", "现在打折",
        )
        if any(marker in query.lower() for marker in dynamic_offer_markers):
            lines.append({
                "zh": "工具字段未提供实时活动状态或上新时间，无法确认商品今天是否降价、当前是否参与促销或是否为最新款；请以商品详情页为准。",
                "en": "The retrieved fields do not include live promotion status or release timing, so I cannot confirm whether an item is discounted today, currently on promotion, or the newest model; please verify the product page.",
                "fr": "Les champs récupérés n'indiquent ni les promotions en temps réel ni la date de lancement ; je ne peux donc pas confirmer une remise actuelle ou le modèle le plus récent. Vérifiez la fiche produit.",
                "de": "Die abgerufenen Felder enthalten weder Echtzeit-Aktionsdaten noch ein Einführungsdatum. Daher kann ich aktuelle Rabatte oder das neueste Modell nicht bestätigen; bitte prüfen Sie die Produktseite.",
                "nl": "De opgehaalde velden bevatten geen live actiegegevens of introductiedatum. Daarom kan ik niet bevestigen of een product vandaag is afgeprijsd, in de actuele aanbieding staat of het nieuwste model is; controleer de productpagina.",
                "ko": "조회된 필드에는 실시간 프로모션 상태나 출시 시점이 없어 오늘 할인 여부, 현재 행사 참여 여부 또는 최신 모델인지 확인할 수 없습니다. 상품 상세 페이지를 확인해 주세요.",
            }[language])
        return "\n\n".join(lines)

    def _normalize_final_response(self, final: str, messages: List[Dict]) -> str:
        import re

        seen = set()
        selected_indexes = []

        def keep_first_card(match: re.Match) -> str:
            index = int(match.group(1))
            if index in seen:
                return ""
            seen.add(index)
            selected_indexes.append(index)
            return match.group(0)

        normalized = re.sub(r"\[product:(\d+)\]", keep_first_card, final).strip()
        user_query = next(
            (message.get("content", "") for message in messages if message.get("role") == "user"),
            "",
        )
        response_language = self._response_language(user_query)
        if response_language != "zh":
            normalized = re.sub(
                r"\s*[（(][^()（）]*[\u4e00-\u9fff][^()（）]*[)）]",
                "",
                normalized,
            )
            normalized = re.sub(
                r"[\"“”'][\u4e00-\u9fff]+[\"“”']",
                "",
                normalized,
            )
            normalized = re.sub(r"[\u4e00-\u9fff]+", "", normalized)
        if self.site_config:
            normalized = normalized.replace("¥", self._currency_symbol()).replace(
                "￥", self._currency_symbol()
            )
        display_products = self._display_products(messages)
        has_empty_sku_result = False
        for message in messages:
            if message.get("role") != "tool":
                continue
            try:
                result = json.loads(message.get("content", ""))
            except (TypeError, json.JSONDecodeError):
                continue
            if result.get("count") == 0 and "products" in result:
                has_empty_sku_result = True
                break
        if (
            self.scenario_type != "bundle_purchase"
            and not display_products
            and has_empty_sku_result
        ):
            normalized = ""
        if not display_products and re.search(
            r"sku_recall|\[product:x\]|我应该使用|需要从结果|工具返回",
            normalized,
            re.IGNORECASE,
        ):
            normalized = ""
        if selected_indexes and display_products and self.scenario_type != "bundle_purchase":
            normalized = self._render_grounded_recommendations(
                user_query,
                display_products,
                selected_indexes,
                self._currency_symbol(),
                response_language,
            )
        click_start = re.search(r"(?i)(?:<|\b)/?clicktext", normalized)
        if click_start:
            normalized = normalized[:click_start.start()].rstrip()
        if not normalized:
            language = response_language
            normalized = {
                "zh": "抱歉，暂时没有找到合适的商品。",
                "en": "Sorry, I couldn't find a suitable product yet.",
                "fr": "Désolé, je n'ai pas encore trouvé de produit adapté.",
                "de": "Leider habe ich noch kein passendes Produkt gefunden.",
                "nl": "Helaas heb ik nog geen geschikt product gevonden.",
                "ko": "죄송하지만 아직 적합한 상품을 찾지 못했습니다.",
            }[language]
        if (
            self.scenario_type != "bundle_purchase"
            and display_products
            and has_empty_sku_result
        ):
            language = response_language
            incomplete_notice = {
                "zh": "部分检索未找到匹配商品，因此当前推荐可能未完全覆盖全部需求。",
                "en": "Some searches returned no matching products, so this recommendation may not cover every requested item.",
                "fr": "Certaines recherches n'ont trouvé aucun produit correspondant ; cette recommandation peut donc être incomplète.",
                "de": "Für einige Suchanfragen wurden keine passenden Produkte gefunden; die Empfehlung ist daher möglicherweise unvollständig.",
                "nl": "Voor sommige zoekopdrachten zijn geen passende producten gevonden; deze aanbeveling is daarom mogelijk onvolledig.",
                "ko": "일부 검색에서 일치하는 상품을 찾지 못해 현재 추천이 모든 요청을 포함하지 않을 수 있습니다.",
            }[language]
            normalized = f"{normalized}\n\n{incomplete_notice}"
        external_markers = ("lidl", "amazon", "ebay", "aliexpress")
        negative_confirmation_markers = (
            "cannot confirm", "无法确认", "无法直接确认", "nicht bestätigen",
            "ne peux pas confirmer", "niet bevestigen", "확인할 수 없",
            "reliable live prices", "站外实时价格", "externe echtzeitpreise",
            "prix externes fiables", "actuele prijzen van andere winkels",
        )
        if (
            any(marker in user_query.lower() for marker in external_markers)
            and not any(marker in normalized.lower() for marker in negative_confirmation_markers)
        ):
            external_disclaimer = {
                "zh": "我没有可靠的站外实时价格，因此无法直接确认其他平台的价格差异。",
                "en": "I do not have reliable live prices from other retailers, so I cannot confirm the external price difference.",
                "fr": "Je ne dispose pas de prix externes fiables en temps réel, je ne peux donc pas confirmer l'écart de prix.",
                "de": "Ohne verlässliche externe Echtzeitpreise kann ich den Preisunterschied nicht bestätigen.",
                "nl": "Zonder betrouwbare actuele prijzen van andere winkels kan ik het prijsverschil niet bevestigen.",
                "ko": "외부 쇼핑몰의 신뢰할 수 있는 실시간 가격이 없어 가격 차이를 확인할 수 없습니다.",
            }[response_language]
            normalized = f"{normalized}\n\n{external_disclaimer}"
        normalized = f"{normalized}\n\n{self._followup_text(user_query, response_language, bool(display_products))}"
        return normalized

    @classmethod
    def _infer_matching_arguments(cls, user_query: str) -> Optional[Dict[str, Any]]:
        import re as _re

        trigger = _re.search(
            r"\b(?:need|needs|want|looking for|brauche|benötige|suche|cherche|besoin de|zoek)\b|需要(?:搭配)?|想搭配|搭配",
            user_query,
            flags=_re.IGNORECASE,
        )
        style = "nordic"
        style_source = user_query[:trigger.start()] if trigger else user_query
        normalized = style_source.lower()
        style_aliases = {
            "modern": ["modern", "moderne", "现代"],
            "mid_century": ["mid-century", "mid century", "中古", "复古"],
            "industrial": ["industrial", "industriel", "工业"],
            "nordic": ["nordic", "nordisch", "nordique", "scandinav", "北欧"],
        }
        for candidate, aliases in style_aliases.items():
            if any(alias in normalized for alias in aliases):
                style = candidate
                break

        need_clause = user_query[trigger.end():] if trigger else user_query
        main_item = user_query[:trigger.start()].strip(" ,，。") if trigger else user_query
        main_item = _re.sub(
            r"^(?:i have|i bought|j'ai|ich habe|ik heb|买了|已有|我有)\s*",
            "",
            main_item,
            flags=_re.IGNORECASE,
        ).strip(" ,，。")
        main_item = _re.sub(r"\b(?:and|und|et|en)\s*$|(?:和|及)\s*$", "", main_item, flags=_re.IGNORECASE).strip()
        main_item = main_item or user_query

        language = cls._detect_query_language(user_query)
        connectors = {
            "zh": r"和|及",
            "en": r"\band\b|\bplus\b",
            "de": r"\bund\b",
            "fr": r"\bet\b",
            "nl": r"\ben\b",
            "ko": r"및|하고|와|과",
        }[language]
        need_items = []
        seen_categories = set()
        for segment in _re.split(
            rf"\s*(?:\+|＋|,|，|、|;|；|{connectors})\s*",
            need_clause,
            flags=_re.IGNORECASE,
        ):
            segment = segment.strip(" ,，。")
            category = normalize_recall_query(segment).get("category")
            if not category or category in seen_categories:
                continue
            seen_categories.add(category)
            need_items.append(segment)
        if not need_items:
            return None
        return {"main_item": main_item, "need_items": need_items[:4], "style": style}

    @classmethod
    def _infer_search_scenario_arguments(cls, user_query: str) -> Optional[Dict[str, Any]]:
        category = normalize_recall_query(user_query).get("category")
        category_styles = {
            "茶几": "modern", "落地灯": "modern", "地毯": "modern",
            "装饰画": "modern", "抱枕": "modern", "绿植": "modern",
            "置物架": "modern", "窗帘": "modern", "沙发垫": "modern",
            "收纳柜": "modern", "摆件": "modern", "镜子": "modern",
            "餐椅": "modern", "香薰": "modern", "台灯": "office",
            "书桌": "office", "人体工学椅": "office", "桌面升降架": "office",
            "桌面收纳": "office", "三脚架": "camera", "摄影包": "camera",
            "相机清洁": "camera", "闪光灯": "camera", "滤镜": "camera",
            "跑步机": "fitness", "哑铃": "fitness", "瑜伽垫": "fitness",
            "跳绳": "fitness", "运动垫": "fitness", "运动毛巾": "fitness",
            "运动水壶": "fitness", "运动耳机": "fitness", "弹力带": "fitness",
            "帐篷": "outdoor", "折叠椅": "outdoor", "睡袋": "outdoor",
            "防潮垫": "outdoor", "炊具": "outdoor", "登山鞋": "outdoor",
        }
        if category not in category_styles:
            return None

        normalized = user_query.lower()
        style = category_styles[category]
        style_aliases = {
            "nordic": ("nordic", "nordisch", "nordique", "scandinav", "北欧"),
            "mid_century": ("mid-century", "mid century", "retro", "vintage", "中古", "复古"),
            "industrial": ("industrial", "industriel", "industrieel", "工业"),
            "modern": ("modern", "moderne", "现代", "minimal", "简约"),
        }
        for candidate, aliases in style_aliases.items():
            if any(alias in normalized for alias in aliases):
                style = candidate
                break
        return {"main_item": user_query, "need_items": [user_query], "style": style}

    def run(self, user_query: str) -> Trajectory:
        """执行一次完整的 ReAct 循环，返回轨迹"""
        traj = Trajectory(
            trajectory_id=f"react_{uuid.uuid4().hex[:8]}",
            scenario_type=self.scenario_type,
            user_query=user_query,
            site_context=dict(self.site_context) if isinstance(self.site_context, dict) else (
                {"site_code": self.site_context} if self.site_context else None
            ),
        )

        # bundle 场景：先提取品类并行搜索，再让模型生成最终回复
        if self.scenario_type == "bundle_purchase":
            return self._run_bundle(traj, user_query)

        # 初始化消息历史
        messages = [
            {"role": "system",  "content": SYSTEM_PROMPT},
            {"role": "user",    "content": user_query},
        ]
        traj.messages = messages

        if self._is_privacy_bypass_request(user_query):
            final = self._privacy_safety_response(user_query)
            traj.final_response = final
            traj.status = "done"
            traj.total_steps = 0
            messages.append({"role": "assistant", "content": final})
            return traj

        if self._is_product_usage_question(user_query):
            language = self._response_language(user_query)
            final = {
                "zh": "这是商品使用与安全问题，但当前工具没有返回说明书或兼容性信息，因此我无法确认这种用法是否安全。请以商品说明书和详情页要求为准。 <ClickText>查看商品说明</ClickText> <ClickText>确认安全用法</ClickText>",
                "en": "This is a product-use and safety question, but the current tools do not provide the manual or compatibility details needed to confirm that use. Please follow the product manual and product-page instructions. <ClickText>Product manual</ClickText> <ClickText>Safe usage</ClickText>",
                "fr": "Il s'agit d'une question d'utilisation et de sécurité, mais les outils actuels ne fournissent pas la notice ni les informations de compatibilité nécessaires. Suivez la notice et la fiche produit. <ClickText>Notice du produit</ClickText> <ClickText>Utilisation sûre</ClickText>",
                "de": "Dies ist eine Nutzungs- und Sicherheitsfrage. Die aktuellen Tools enthalten jedoch keine Anleitung oder Kompatibilitätsdaten, um diese Verwendung zu bestätigen. Bitte beachten Sie die Produktanleitung. <ClickText>Produktanleitung</ClickText> <ClickText>Sichere Nutzung</ClickText>",
                "nl": "Dit is een gebruiks- en veiligheidsvraag, maar de huidige tools bevatten geen handleiding of compatibiliteitsinformatie om dit te bevestigen. Volg de producthandleiding en productpagina. <ClickText>Producthandleiding</ClickText> <ClickText>Veilig gebruik</ClickText>",
                "ko": "상품 사용 및 안전 관련 질문이지만 현재 도구에는 이를 확인할 설명서나 호환성 정보가 없습니다. 상품 설명서와 상세 페이지 안내를 따라 주세요. <ClickText>상품 설명서</ClickText> <ClickText>안전한 사용</ClickText>",
            }[language]
            traj.final_response = final
            traj.status = "done"
            traj.total_steps = 0
            messages.append({"role": "assistant", "content": final})
            return traj

        all_thinking = []
        search_scenario_arguments = (
            self._infer_search_scenario_arguments(user_query)
            if self.scenario_type == "search_recommend"
            else None
        )
        locked_specialized_query = (
            user_query
            if self.scenario_type == "search_recommend"
            and has_fail_closed_recall_intent(user_query)
            else None
        )

        for step_idx in range(self.max_steps):
            # ── LLM 决策 ──────────────────────────────────────────────────
            # max_tokens 由 LLMClient 根据模型特性自动设置（DeepSeek-R1 设为 32000）
            has_tool_result = any(m["role"] == "tool" for m in messages)
            max_tok = 2500  # LLMClient 会覆盖为 32000
            content, raw_thinking = self.llm.generate(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=self._build_user_prompt(messages),
                max_tokens=max_tok,
            )
            # 收集思维链
            if raw_thinking:
                all_thinking.append(raw_thinking)

            # 解析模型输出
            tool_call = self._parse_tool_call(content, raw_thinking)

            if search_scenario_arguments:
                has_prior_sku_recall = any(
                    call["function"]["name"] == "sku_recall"
                    for message in messages
                    for call in (message.get("tool_calls") or [])
                )
                has_prior_scenario_recall = any(
                    call["function"]["name"] == "scenario_related_recall"
                    for message in messages
                    for call in (message.get("tool_calls") or [])
                )
                planned_calls = list(tool_call or [])
                if not has_prior_sku_recall:
                    planned_calls = [call for call in planned_calls if call["name"] != "sku_recall"]
                    planned_calls.append({"name": "sku_recall", "arguments": {"query": user_query}})
                if not has_prior_scenario_recall:
                    planned_calls = [
                        call for call in planned_calls
                        if call["name"] != "scenario_related_recall"
                    ]
                    planned_calls.append({
                        "name": "scenario_related_recall",
                        "arguments": search_scenario_arguments,
                    })
                tool_call = planned_calls or None

            if tool_call and locked_specialized_query:
                has_prior_sku_recall = any(
                    call["function"]["name"] == "sku_recall"
                    for message in messages
                    for call in (message.get("tool_calls") or [])
                )
                non_sku_calls = [call for call in tool_call if call["name"] != "sku_recall"]
                if has_prior_sku_recall:
                    tool_call = non_sku_calls or None
                else:
                    tool_call = [
                        *non_sku_calls,
                        {"name": "sku_recall", "arguments": {"query": locked_specialized_query}},
                    ]

            if self.scenario_type == "matching" and not self._has_complete_scenario_recall(messages):
                has_scenario_call = any(
                    call["function"]["name"] == "scenario_related_recall"
                    for message in messages
                    for call in (message.get("tool_calls") or [])
                )
                proposed_scenario_call = any(
                    call["name"] == "scenario_related_recall" for call in (tool_call or [])
                )
                if not has_scenario_call and not proposed_scenario_call:
                    inferred = self._infer_matching_arguments(user_query)
                    if inferred:
                        tool_call = [{"name": "scenario_related_recall", "arguments": inferred}]

            if (
                tool_call
                and self.scenario_type == "matching"
                and self._has_complete_scenario_recall(messages)
            ):
                tool_call = [
                    call for call in tool_call if call["name"] != "sku_recall"
                ] or None

            original_category = None
            if self.scenario_type == "search_recommend":
                original_category = normalize_recall_query(user_query).get("category")
            if tool_call and original_category:
                for call in tool_call:
                    if call["name"] != "sku_recall":
                        continue
                    planned_query = str(call["arguments"].get("query", ""))
                    planned_category = normalize_recall_query(planned_query).get("category")
                    if planned_category != original_category:
                        call["arguments"] = {"query": user_query}

            if tool_call is None:
                user_text_inner = next(
                    (message["content"] for message in messages if message["role"] == "user"),
                    "",
                )
                recognized_category = normalize_recall_query(user_text_inner).get("category")
                has_sku_recall = any(
                    call["function"]["name"] == "sku_recall"
                    for message in messages
                    for call in (message.get("tool_calls") or [])
                )
                if (
                    (
                        recognized_category
                        or is_generic_product_discovery_query(user_text_inner)
                        or (
                            self.scenario_type == "search_recommend"
                            and self._should_force_initial_product_search(user_text_inner)
                        )
                    )
                    and not has_sku_recall
                    and not self._has_complete_scenario_recall(messages)
                ):
                    tool_call = [{
                        "name": "sku_recall",
                        "arguments": {"query": user_text_inner},
                    }]

            if tool_call is None:
                # 检查是否有未完成的品类（多品类场景强制继续）
                import re as _re_cat
                user_text_inner = next((m["content"] for m in messages if m["role"] == "user"), "")
                if any(sep in user_text_inner for sep in ["+", "＋", "和", "及"]):
                    searched_qs = []
                    for m in messages:
                        if m.get("tool_calls"):
                            tc = m["tool_calls"][0]["function"]
                            if tc["name"] == "sku_recall":
                                try:
                                    args = json.loads(tc["arguments"])
                                    searched_qs.append(args.get("query","").lower())
                                except Exception:
                                    pass
                    categories_in_query = _re_cat.findall(
                        r'[一-鿿]{2,5}(?:套装|垫|椅|灯|机|壶|包|架|棒|绳|铃)', user_text_inner
                    )
                    unsearched = [c for c in categories_in_query if not any(c in q for q in searched_qs)]
                    if unsearched and step_idx < self.max_steps - 1:
                        # 强制继续：把模型的"最终回复"当成thinking，继续循环
                        if raw_thinking:
                            all_thinking.append(raw_thinking)
                        messages.append({
                            "role": "assistant",
                            "content": f"<think>\n{raw_thinking}\n</think>" if raw_thinking else "",
                        })
                        continue  # 不 break，继续下一步

                # 模型决定输出最终回复（没有工具调用）
                final = self._extract_final_response(content, raw_thinking)

                # 收集工具实际返回的所有合法 index
                import re as _re
                display_products = self._display_products(messages)
                valid_indexes = set(range(1, len(display_products) + 1))
                has_tool_results = bool(display_products)

                # 检查 final 里引用的 index 是否都合法
                referenced = {int(x) for x in _re.findall(r'\[product:(\d+)\]', final)}
                hallucinated = referenced - valid_indexes

                if hallucinated or (has_tool_results and not referenced):
                    retried_final, retried_thinking = self._retry_card_selection(messages)
                    retried_refs = {
                        int(value)
                        for value in _re.findall(r"\[product:(\d+)\]", retried_final)
                    }
                    if retried_refs and not (retried_refs - valid_indexes):
                        final = retried_final
                        if retried_thinking:
                            all_thinking.append(retried_thinking)
                    else:
                        fallback = self._build_fallback_response(messages)
                        if fallback:
                            final = fallback
                    if not final and hallucinated:
                        # 去掉所有幻觉商卡标签，只保留文字
                        final = _re.sub(r'\[product:\d+\]', '', final).strip()

                final = self._normalize_final_response(final, messages)
                traj.final_response = final
                traj.status = "done"

                messages.append({
                    "role": "assistant",
                    "content": f"<think>\n{raw_thinking}\n</think>\n\n{final}" if raw_thinking else final,
                })
                break

            # ── 有工具调用（支持一次多个并行执行）────────────────────────
            # tool_call 现在是列表
            tool_calls_list = tool_call  # List[Dict]
            if self.scenario_type == "search_recommend":
                prior_recall_count = sum(
                    call["function"]["name"] == "sku_recall"
                    for message in messages
                    for call in (message.get("tool_calls") or [])
                )
                remaining_recall_count = max(0, 2 - prior_recall_count)
                sku_calls = [
                    call for call in tool_calls_list if call["name"] == "sku_recall"
                ][:remaining_recall_count]
                non_sku_calls = [
                    call for call in tool_calls_list if call["name"] != "sku_recall"
                ]
                tool_calls_list = [*sku_calls, *non_sku_calls]
                if not tool_calls_list:
                    final = self._normalize_final_response(
                        self._force_final_response(messages),
                        messages,
                    )
                    traj.final_response = final
                    traj.status = "done"
                    messages.append({"role": "assistant", "content": final})
                    break

            # 构建 assistant 消息（含所有工具调用）
            thinking_content = f"<think>\n{raw_thinking}\n</think>" if raw_thinking else ""
            tc_records = []
            for i, tc in enumerate(tool_calls_list):
                call_id = f"call_{step_idx}_{i}_{uuid.uuid4().hex[:6]}"
                tc_records.append({
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                    },
                    "_args": tc["arguments"],  # 临时保存，执行时用
                })
            messages.append({
                "role": "assistant",
                "content": thinking_content,
                "tool_calls": [{"id": r["id"], "type": r["type"], "function": r["function"]}
                               for r in tc_records],
            })

            # 执行所有工具，依次追加 tool 消息
            for r in tc_records:
                tool_name = r["function"]["name"]
                tool_args = r["_args"]
                tool_result = execute_tool(tool_name, tool_args, self.site_context)

                tool_content = json.dumps(tool_result, ensure_ascii=False)
                messages.append({
                    "role": "tool",
                    "tool_call_id": r["id"],
                    "content": tool_content,
                })

                # 记录轨迹步骤（每个工具调用记一步）
                traj.steps.append(TrajectoryStep(
                    step_id=step_idx + 1,
                    tool_name=tool_name,
                    tool_input=tool_args,
                    tool_output=tool_result,
                    thinking=raw_thinking,
                ))

        else:
            # 超过 max_steps 还没结束
            traj.status = "max_steps"
            # 强制让模型基于已有结果输出回复
            traj.final_response = self._normalize_final_response(
                self._force_final_response(messages),
                messages,
            )
            messages.append({
                "role":    "assistant",
                "content": traj.final_response,
            })

        traj.total_steps = len(traj.steps)
        traj.raw_thinking = "\n\n---\n\n".join(all_thinking)
        # thinking 字段后续由压缩脚本生成
        traj.thinking = self._compress_thinking(traj)
        return traj

    # ── 辅助方法 ────────────────────────────────────────────────────────────

    def _build_user_prompt(self, messages: List[Dict]) -> str:
        """把对话历史格式化成清晰的上下文传给模型，并附加当前所有已召回商品的index汇总"""
        import json as _json
        parts = []
        all_products = []  # 收集所有工具返回的商品，用于末尾汇总
        seen_product_ids = set()

        for msg in messages[1:]:  # 跳过 system
            role = msg["role"]
            content = msg.get("content", "") or ""
            tool_calls = msg.get("tool_calls", [])

            if role == "user":
                parts.append(f"用户：{content}")
            elif role == "assistant":
                if tool_calls:
                    tc = tool_calls[0]["function"]
                    parts.append(
                        f"助手调用工具：{tc['name']}\n参数：{tc['arguments'][:300]}"
                    )
                elif content:
                    parts.append(f"助手：{content[:500]}")
            elif role == "tool":
                try:
                    data = _json.loads(content)
                    prods = data.get("products", [])
                    if prods:
                        start_index = len(all_products) + 1
                        display_products = []
                        for product in prods:
                            identity = str(product.get("sku_id") or product.get("product_id") or product.get("sku_name") or product.get("title"))
                            if identity in seen_product_ids:
                                continue
                            seen_product_ids.add(identity)
                            display_product = dict(product)
                            display_product["_display_index"] = start_index + len(display_products)
                            display_products.append(display_product)
                        all_products.extend(display_products)
                        summary = "、".join(
                            f"[product:{p['_display_index']}]"
                            f"{self._product_title(p)[:12]}{self._currency_symbol()}{self._product_price(p):g}"
                            for p in display_products
                        )
                        parts.append(f"工具返回{len(prods)}款商品：{summary}")
                    else:
                        parts.append(f"工具返回：{content[:300]}")
                except Exception:
                    parts.append(f"工具返回：{content[:300]}")

        # 末尾附加商品汇总，强调只能引用工具返回的信息
        if all_products:
            product_list = "\n".join(
                f"  [product:{p['_display_index']}] {self._product_title(p)[:25]} "
                f"{self._currency_symbol()}{self._product_price(p):g} 原价{self._currency_symbol()}{p.get('price', self._product_price(p))} "
                f"销量：{p.get('sales','')}"
                for p in all_products
            )
            parts.append(
                f"\n【可引用商品列表（严格限制）】\n{product_list}\n"
                "⚠️ 规则：只能引用上列明确展示的商品名、品牌、到手价、原价和销量。"
                "禁止补充未展示的静音、适用面积、材质、认证、性能、品牌定位或使用效果。"
            )

        # 无货提示：当最新一次工具返回是无货时，强制提醒继续搜索
        last_tool_result = None
        for msg in messages:
            if msg.get("role") == "tool":
                try:
                    last_tool_result = json.loads(msg["content"])
                except Exception:
                    pass
        if last_tool_result and last_tool_result.get("success") is True and last_tool_result.get("count") == 0:
            parts.append(
                "⚠️ 刚才的商品召回为空。可以用更宽泛的关键词再调用一次sku_recall，"
                "也可以如实说明暂未找到并请用户补充条件。"
                f"禁止编造任何商品或[product:X]引用。"
            )

        # 多品类检查：检测 query 里提到的品类关键词，看哪些还没被搜索过
        user_text = next((m["content"] for m in messages if m["role"] == "user"), "")
        tool_names_called = [
            m["tool_calls"][0]["function"]["name"]
            for m in messages if m.get("tool_calls")
        ]
        # 已经搜索过的关键词
        searched_queries = []
        for m in messages:
            if m.get("tool_calls"):
                tc = m["tool_calls"][0]["function"]
                if tc["name"] == "sku_recall":
                    try:
                        args = json.loads(tc["arguments"])
                        searched_queries.append(args.get("query","").lower())
                    except Exception:
                        pass

        # 检测 query 里的品类分隔符（+、和、及、，）
        import re as _re2
        if any(sep in user_text for sep in ["+", "＋", "和", "及", "，", "、"]):
            # 提取品类词（中文2-5字的名词）
            categories = _re2.findall(r'[一-鿿]{2,5}(?:套装|垫|椅|灯|机|壶|包|架|棒|绳|铃)', user_text)
            unsearched = []
            for cat in categories:
                if not any(cat in q for q in searched_queries):
                    unsearched.append(cat)
            if unsearched and len(searched_queries) > 0:
                parts.append(f"⚠️ 提示：用户还需要【{'、'.join(unsearched)}】，请继续调用sku_recall搜索这些品类后再输出最终推荐。")

        if "总预算" in user_text or "算一下总价" in user_text or "算算总价" in user_text:
            if "calculate_budget" not in tool_names_called:
                parts.append("⚠️ 提示：用户要求计算总价，还未调用 calculate_budget，请在推荐商品后调用它验证预算。")

        parts.append(self._language_instruction(user_text, self._response_language(user_text)))
        recognized_category = normalize_recall_query(user_text).get("category")
        if recognized_category:
            parts.append(
                f"检索层已确定用户在找「{recognized_category}」。"
                "应先调用sku_recall搜索该品类，不要在尚未检索时直接追问。"
            )
        if all_products:
            parts.append(
                "最终回复要求：推荐2-5款最匹配商品；每个[product:X]只能出现一次；"
                "不要在总结段重复商卡；结尾使用同一语言提供2-3个<ClickText>筛选方向。"
            )

        return "\n\n".join(parts)

    def _parse_tool_call(
        self, content: str, raw_thinking: str
    ) -> Optional[List[Dict]]:
        """
        从 LLM 输出里解析工具调用，支持一次输出多个工具调用（并行执行）。
        返回工具调用列表，None 表示没有工具调用。
        """
        import re
        valid_names = {t["function"]["name"] for t in JOYBUY_TOOLS_SCHEMA}
        calls = []

        for text in [content, raw_thinking]:
            if not text:
                continue

            # 找所有 <tool_call>...</tool_call> 标签
            for m in re.finditer(r'<tool_call>\s*(\{.*?\})\s*</tool_call>', text, re.DOTALL):
                try:
                    data = json.loads(m.group(1))
                    if "name" in data and data["name"] in valid_names:
                        args = data.get("arguments", data.get("parameters", {}))
                        args = self._normalize_tool_arguments(data["name"], args)
                        calls.append({"name": data["name"], "arguments": args})
                except json.JSONDecodeError:
                    pass

            # 找所有 JSON 格式的工具调用
            if not calls:
                for m in re.finditer(
                    r'\{[^{}]*"name"\s*:\s*"([^"]+)"[^{}]*"arguments"\s*:\s*(\{[^}]+\})',
                    text, re.DOTALL
                ):
                    try:
                        name = m.group(1)
                        args = json.loads(m.group(2))
                        if name in valid_names:
                            args = self._normalize_tool_arguments(name, args)
                            calls.append({"name": name, "arguments": args})
                    except (json.JSONDecodeError, KeyError):
                        pass

            if calls:
                break  # 找到了就不再看 raw_thinking

        return calls if calls else None  # None 表示没有工具调用

    def _extract_final_response(self, content: str, raw_thinking: str) -> str:
        """提取最终回复文本，过滤thinking泄漏"""
        import re

        content_clean = (content or "").strip()
        if "<tool_call>" in content_clean or "<think>" in content_clean:
            content_clean = ""

        # thinking泄漏检测：长文本无商卡且含推理特征词
        THINKING_PATTERNS = ["首先处理", "接下来我", "用户需要帮", "我需要继续搜索",
                              "根据之前的工具", "我要确认", "我得需要", "目前已经调用"]
        def is_thinking_leak(text: str) -> bool:
            if len(text) < 200:
                return False
            return any(p in text for p in THINKING_PATTERNS) and not re.search(r'\[product:\d+\]', text)

        if is_thinking_leak(content_clean):
            content_clean = ""

        if content_clean and len(content_clean) > 50:
            text = content_clean
        elif raw_thinking:
            m = re.search(
                r'\n{2,}((?:推荐|为您|根据|以下|好的|您好).{100,})$',
                raw_thinking,
                re.DOTALL,
            )
            text = m.group(1).strip() if m else content_clean or "抱歉，未能获取到足够信息。"
        else:
            text = content_clean or "抱歉，未能获取到足够信息。"

        if len(text) > 1500:
            last_tag = None
            for m in re.finditer(r'\[product:\d+\]', text):
                last_tag = m
            if last_tag:
                text = text[:last_tag.end()].strip()
            else:
                text = text[:1500].strip()

        return text

    def _run_bundle(self, traj: "Trajectory", user_query: str) -> "Trajectory":
        """
        Bundle 场景专用逻辑：
        1. 从 query 里提取品类
        2. 并行搜索所有品类（一次性）
        3. 调 calculate_budget（可选）
        4. 让模型生成最终回复
        """
        import re as _re
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_query},
        ]
        traj.messages = messages
        # 提取品类：按多语言连接词拆分，并用统一检索归一化识别品类
        query_for_cats = user_query
        if '：' in user_query or ':' in user_query:
            query_for_cats = _re.split(r'[：:]', user_query, 1)[-1]

        categories = []
        seen_categories = set()
        budget_clause = (
            r"(?:(?:with|avec|mit|met)\s+(?:(?:a|an|un|une|einem?|een)\s+)?)?"
            r"(?:total\s+budget|budget\s+total|budget|gesamtbudget|totaalbudget|"
            r"总预算|预算)[^,，;；。]*"
        )
        query_without_budget = _re.sub(
            budget_clause,
            "",
            query_for_cats,
            flags=_re.IGNORECASE,
        )
        query_language = self._response_language(user_query)
        language_connectors = {
            "zh": r"和|及",
            "en": r"\band\b",
            "de": r"\bund\b",
            "fr": r"\bet\b",
            "nl": r"\ben\b",
            "ko": r"및|하고|와|과",
        }[query_language]
        numbered_segments = [
            match.group(1).strip()
            for match in _re.finditer(
                r"(?:^|\n)\s*\d+[.)]\s*(.+?)(?=(?:\n\s*\d+[.)]\s)|\Z)",
                query_without_budget,
                flags=_re.DOTALL,
            )
        ]
        segments = numbered_segments or _re.split(
            rf'\s*(?:\+|＋|,|，|、|;|；|{language_connectors})\s*',
            query_without_budget,
            flags=_re.IGNORECASE,
        )
        for seg in segments:
            seg = seg.strip()
            seg = _re.sub(
                r'[，,。]?帮我算.*|[，,。]?算下来.*',
                '',
                seg,
            ).strip().rstrip('，,。 ')
            category_key = _re.sub(r"\s+", " ", seg.lower()).strip()
            if category_key and category_key not in seen_categories:
                seen_categories.add(category_key)
                categories.append(seg)
        categories = categories[:5]

        budget_patterns = [
            (
                r"(?:total\s+budget|budget\s+total|budget|gesamtbudget|totaalbudget|"
                r"总预算|预算)[^0-9]{0,16}[£€¥￥$]?\s*(\d+(?:[.,]\d+)?)\s*(?:元|eur|gbp|€|£)?"
            ),
            (
                r"[£€¥￥$]\s*(\d+(?:[.,]\d+)?)\s*"
                r"(?:total\s+budget|budget|gesamtbudget|totaalbudget|总预算|预算)"
            ),
        ]
        total_budget = 0.0
        for pattern in budget_patterns:
            budget_m = _re.search(pattern, user_query, flags=_re.IGNORECASE)
            if budget_m:
                total_budget = float(budget_m.group(1).replace(',', '.'))
                break

        if not categories:
            # 没提取到品类，走普通 ReAct
            traj.scenario_type = "search_recommend"
            return self._run_react(traj, user_query)

        # 第1步：并行搜索所有品类
        call_id_base = uuid.uuid4().hex[:6]
        tc_records = []
        for i, cat in enumerate(categories[:4]):  # 最多4个品类
            call_id = f"call_bundle_{i}_{call_id_base}"
            args = {"query": cat}
            tc_records.append({
                "id": call_id,
                "name": "sku_recall",
                "arguments": args,
            })

        # 记录 assistant 消息（并行工具调用）
        messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": r["id"], "type": "function",
                "function": {"name": r["name"], "arguments": json.dumps(r["arguments"], ensure_ascii=False)}
            } for r in tc_records],
        })

        # 执行所有搜索
        all_products = []
        empty_bundle_queries = []
        for r in tc_records:
            result = execute_tool(r["name"], r["arguments"], self.site_context)
            if result.get("count", 0) == 0:
                empty_bundle_queries.append(str(r["arguments"].get("query", "")))
            for p in result.get("products", []):
                display_product = dict(p)
                display_product["_display_index"] = len(all_products) + 1
                all_products.append(display_product)
            messages.append({
                "role": "tool",
                "tool_call_id": r["id"],
                "content": json.dumps(result, ensure_ascii=False),
            })
            traj.steps.append(TrajectoryStep(
                step_id=len(traj.steps) + 1,
                tool_name=r["name"],
                tool_input=r["arguments"],
                tool_output=result,
            ))

        # 每个品类先确定最终组合；有预算时选价格最低的一款，保证预算工具与最终商卡一致
        by_cat = {}
        for p in all_products:
            cat = p.get("keyword", "")
            if cat not in by_cat:
                by_cat[cat] = p
            elif total_budget > 0 and self._product_price(p) < self._product_price(by_cat[cat]):
                by_cat[cat] = p
        selected_bundle_products = list(by_cat.values())

        # 第2步：如果有总预算，调 calculate_budget
        budget_result = None
        if total_budget > 0 and selected_bundle_products:
            items = [
                {"name": self._product_title(p), "price": self._product_price(p)}
                for p in selected_bundle_products
            ]
            budget_result = execute_tool("calculate_budget", {"items": items, "total_budget": total_budget}, self.site_context)
            call_id_budget = f"call_budget_{call_id_base}"
            messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": call_id_budget, "type": "function",
                                "function": {"name": "calculate_budget",
                                             "arguments": json.dumps({"items": items, "total_budget": total_budget}, ensure_ascii=False)}}],
            })
            messages.append({
                "role": "tool",
                "tool_call_id": call_id_budget,
                "content": json.dumps(budget_result, ensure_ascii=False),
            })
            traj.steps.append(TrajectoryStep(
                step_id=len(traj.steps) + 1,
                tool_name="calculate_budget",
                tool_input={"items": items, "total_budget": total_budget},
                tool_output=budget_result,
            ))

        # 第3步：专用 prompt 让模型生成 bundle 最终回复（推荐组合+总价结论）
        # 构建简洁的商品列表供模型参考
        product_summary = ""
        for p in selected_bundle_products:
            product_summary += (
                f"\n【{p.get('keyword', '')}】\n"
                f"  [{p['_display_index']}] {self._product_title(p)} "
                f"{self._currency_symbol()}{self._product_price(p):g} | 销量：{p.get('sales','')}\n"
            )

        budget_info = ""
        if total_budget > 0 and all_products:
            # 从 calculate_budget 结果里找总价
            for msg in messages:
                if msg.get("role") == "tool":
                    try:
                        r = json.loads(msg["content"])
                        if "total_price" in r:
                            budget_info = f"\nBudget result: {r.get('summary', '')}"
                            break
                    except Exception:
                        pass

        bundle_user_prompt = f"""用户需求：{user_query}

搜索到的商品：{product_summary}
{budget_info}

请根据以上商品，为用户推荐最优组合方案。要求：
1. 每个品类选1款最合适的商品，用**商品名**：推荐理由。[product:X]格式
2. 最后给出所选组合的总价，说明是否在预算内
3. 推荐理由只能使用上面明确展示的商品名、价格和销量，禁止补充未提供的规格或效果
4. 每个[product:X]只能出现一次
5. {self._language_instruction(user_query, self._response_language(user_query))}"""

        content, raw_thinking = self.llm.generate(
            system_prompt=SYSTEM_PROMPT_TRAIN,
            user_prompt=bundle_user_prompt,
            max_tokens=None,  # type: ignore
        )
        final = self._extract_final_response(content, raw_thinking)

        # 幻觉检查
        import re as _re2
        valid_indexes = {int(p["_display_index"]) for p in selected_bundle_products}
        referenced = {int(x) for x in _re2.findall(r'\[product:(\d+)\]', final)}
        if selected_bundle_products:
            final = self._render_grounded_recommendations(
                user_query,
                all_products,
                [product["_display_index"] for product in selected_bundle_products],
                self._currency_symbol(),
                self._response_language(user_query),
            )
            if budget_result and budget_result.get("summary"):
                final = f"{final}\n\n{budget_result['summary']}"
            if empty_bundle_queries:
                missing = " / ".join(empty_bundle_queries)
                language = self._response_language(user_query)
                missing_text = {
                    "zh": f"以下需求暂未找到匹配商品：{missing}。当前组合未完全配齐。",
                    "en": f"No matching products were found for: {missing}. The current bundle is incomplete.",
                    "de": f"Für folgende Anforderung wurden keine passenden Produkte gefunden: {missing}. Das aktuelle Paket ist daher unvollständig.",
                    "fr": f"Aucun produit correspondant n'a été trouvé pour : {missing}. L'ensemble actuel est donc incomplet.",
                    "nl": f"Voor het volgende onderdeel zijn geen passende producten gevonden: {missing}. De huidige bundel is daarom onvolledig.",
                    "ko": f"다음 요청에 맞는 상품을 찾지 못했습니다: {missing}. 현재 구성은 완전하지 않습니다.",
                }[language]
                final = f"{final}\n\n{missing_text}"
        elif empty_bundle_queries:
            missing = " / ".join(empty_bundle_queries)
            language = self._response_language(user_query)
            final = {
                "zh": f"以下需求暂未找到匹配商品：{missing}。",
                "en": f"No matching products were found for: {missing}.",
                "de": f"Für folgende Anforderung wurden keine passenden Produkte gefunden: {missing}.",
                "fr": f"Aucun produit correspondant n'a été trouvé pour : {missing}.",
                "nl": f"Voor het volgende onderdeel zijn geen passende producten gevonden: {missing}.",
                "ko": f"다음 요청에 맞는 상품을 찾지 못했습니다: {missing}.",
            }[language]
        elif referenced - valid_indexes or (valid_indexes and not referenced):
            final = self._build_fallback_response(messages)

        final = self._normalize_final_response(final, messages)
        traj.final_response = final
        traj.status = "done"
        traj.total_steps = len(traj.steps)
        traj.raw_thinking = raw_thinking or ""
        traj.thinking = self._compress_thinking(traj)
        messages.append({
            "role": "assistant",
            "content": f"<think>\n{raw_thinking}\n</think>\n\n{final}" if raw_thinking else final,
        })
        return traj

    def _run_react(self, traj: "Trajectory", user_query: str) -> "Trajectory":
        """普通 ReAct 循环（非 bundle 场景）"""
        # 初始化消息历史（由 run() 调用时已设置好 messages）
        return traj  # placeholder，实际逻辑在 run() 里

    def _retry_card_selection(self, messages: List[Dict]) -> tuple[str, str]:
        user_query = next(
            (message.get("content", "") for message in messages if message.get("role") == "user"),
            "",
        )
        call_names = {}
        for message in messages:
            for call in message.get("tool_calls") or []:
                call_names[call.get("id")] = call["function"]["name"]

        candidates = []
        seen = set()
        for message in messages:
            if message.get("role") != "tool":
                continue
            try:
                result = json.loads(message.get("content", ""))
            except (TypeError, json.JSONDecodeError):
                continue
            source = call_names.get(message.get("tool_call_id"), "product_tool")
            for product in result.get("products", []):
                identity = str(product.get("sku_id") or product.get("sku_name"))
                if identity in seen:
                    continue
                seen.add(identity)
                candidates.append((len(candidates) + 1, source, product))

        if not candidates:
            return "", ""
        candidate_text = "\n".join(
            f"[product:{index}] source={source}; name={self._product_title(product)}; "
            f"brand={product.get('brand_name', '')}; price={self._currency_symbol()}{self._product_price(product):g}; "
            f"original_price={self._currency_symbol()}{product.get('price', '')}; sales={product.get('sales', '')}"
            for index, source, product in candidates
        )
        prompt = f"""用户原始需求：{user_query}

候选商品：
{candidate_text}

现在直接生成最终回复，不要再调用工具。
- 候选只是候选，scenario_related_recall 没有默认优先权。
- 只能选择商品名和返回字段能够明确证明满足核心品类及约束的商品。
- 不得因为 source、keyword 或 match_reason 与Query相关就选择商品。
- 字段无法证明相关时不要引用；宁可只选择1款，也不要凑数量。
- 每个选中商品按 **商品名**：基于返回字段的理由。[product:X] 输出。
- {self._language_instruction(user_query, self._response_language(user_query))}
- 结尾提供2-3个同语言的<ClickText>筛选方向。"""
        content, raw_thinking = self.llm.generate(
            system_prompt=SYSTEM_PROMPT_TRAIN,
            user_prompt=prompt,
            max_tokens=1800,
        )
        return self._extract_final_response(content, raw_thinking), raw_thinking or ""

    def _build_fallback_response(self, messages: List[Dict]) -> str:
        """当final_response没有商卡标签时，基于工具返回结果强制构建符合格式的回复"""
        all_products = self._display_products(messages)
        if not all_products:
            return ""

        call_names = {}
        primary_sku_ids = set()
        for message in messages:
            for call in message.get("tool_calls") or []:
                call_names[call.get("id")] = call["function"]["name"]
        for message in messages:
            if message.get("role") != "tool":
                continue
            if call_names.get(message.get("tool_call_id")) != "sku_recall":
                continue
            try:
                result = json.loads(message.get("content", ""))
            except (TypeError, json.JSONDecodeError):
                continue
            primary_sku_ids.update(str(product.get("sku_id")) for product in result.get("products", []))
        primary_products = [
            product for product in all_products
            if str(product.get("sku_id")) in primary_sku_ids
        ]
        candidate_products = primary_products or all_products

        # 按品类去重，每个品类最多取2款，保证覆盖所有品类
        from collections import defaultdict
        by_category = defaultdict(list)
        for p in candidate_products:
            cat = p.get("keyword", p.get("sku_id", "")[:5])
            by_category[cat].append(p)

        selected = []
        for cat_products in by_category.values():
            selected.extend(cat_products[:2])

        user_query = next(
            (message.get("content", "") for message in messages if message.get("role") == "user"),
            "",
        )
        language = self._response_language(user_query)
        response = self._render_grounded_recommendations(
            user_query,
            all_products,
            [product["_display_index"] for product in selected[:8]],
            self._currency_symbol(),
            language,
        )
        for message in messages:
            if message.get("role") != "tool":
                continue
            try:
                result = json.loads(message.get("content", ""))
            except (TypeError, json.JSONDecodeError):
                continue
            if result.get("currency_code") and result.get("summary"):
                response = f"{response}\n\n{result['summary']}"
                break
        return response

    def _force_final_response(self, messages: List[Dict]) -> str:
        """超出 max_steps 时，强制基于已有结果生成回复"""
        # 收集所有工具结果
        tool_results = self._display_products(messages)[:3]

        if not tool_results:
            language = self._response_language(
                next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
            )
            return {
                "zh": "抱歉，搜索未能找到合适的商品。",
                "en": "Sorry, the search did not find a suitable product.",
                "fr": "Désolé, la recherche n'a trouvé aucun produit adapté.",
                "de": "Leider hat die Suche kein passendes Produkt gefunden.",
                "nl": "Helaas heeft de zoekopdracht geen geschikt product gevonden.",
                "ko": "죄송하지만 검색에서 적합한 상품을 찾지 못했습니다.",
            }[language]

        # 按真实响应层的展示顺序生成商卡标签
        lines = ["根据搜索结果，为您推荐以下商品：\n"]
        for p in tool_results[:3]:
            title = self._product_title(p)[:15]
            price = self._product_price(p)
            idx = p["_display_index"]
            lines.append(f"**{title}**：到手价{self._currency_symbol()}{price:g}。[product:{idx}]")
        return " ".join(lines)

    def _compress_thinking(self, traj: Trajectory) -> str:
        """
        从轨迹结构直接组装压缩版 thinking（不调 LLM）。
        格式：需求 + 工具决策 + 召回摘要 + 筛选逻辑
        """
        parts = [f"用户问：{traj.user_query}。"]

        for step in traj.steps:
            tool_cn = {
                "sku_recall":             "商品搜索",
                "sku_detail_fetch":       "商品详情",
                "similar_sku_recommend":  "相似品推荐",
                "calculate_budget":       "预算计算",
                "scenario_related_recall":"场景推荐",
            }.get(step.tool_name, step.tool_name)

            inp = step.tool_input
            q = inp.get("query", "") or inp.get("keyword", "")
            parts.append(f"调用{tool_cn}：搜「{q}」。")

            prods = step.tool_output.get("products", [])[:3]
            if prods:
                prod_str = "  ".join(
                    f"{p.get('title','')[:10]}¥{p.get('price',0)}"
                    for p in prods
                )
                parts.append(f"召回{len(prods)}款：{prod_str}。")

        return "\n".join(parts)
