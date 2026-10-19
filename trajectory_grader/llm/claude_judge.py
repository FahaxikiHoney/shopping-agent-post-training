"""Claude API judge 占位实现，接口与 MockJudge 完全相同。
替换步骤：pip install anthropic，填入 api_key，切换 config.DEFAULT_JUDGE_MODE = "claude"
"""
from core.data_models import Trajectory, DimensionResult
from llm.judge_interface import JudgeInterface

_DIMENSION_PROMPTS = {
    "d1_intent_understanding": "评估 Agent 是否正确理解了用户的核心需求、使用场景和所有约束（预算、品牌、规格、人群等）。",
    "d2_factuality": "评估回复中的事实（价格、商品属性）是否有轨迹中的工具返回结果作为支撑，有无幻觉或编造。",
    "d3_relevance": "评估最终推荐的商品是否真正匹配用户需求，有无驴唇不对马嘴的情况。",
    "d4_completeness": "评估任务是否被完整覆盖：有没有遗漏用户的关键诉求，该出卡片时有没有出，推荐数量是否充分。",
    "d5_reasoning_value": "评估推荐理由是否具体、有信息量、能帮助用户做决策，而不是'不错/性价比高'这类套话。",
}

_SYSTEM_PROMPT = """你是一个电商 AI 回复质量评估专家。请根据完整的 Agent 执行轨迹对指定维度打分。
输出严格为合法 JSON，格式：{"verdict": "PASS"|"FAIL", "score": 0.0~1.0, "reasoning": "2-3句说明", "evidence": ["引用的具体证据"]}
不要输出任何 JSON 以外的内容。"""


class ClaudeJudge(JudgeInterface):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = model
        except ImportError:
            raise RuntimeError("请先 pip install anthropic")

    def get_judge_name(self) -> str:
        return f"claude:{self.model}"

    def evaluate(self, dimension_id: str, dimension_label: str, trajectory: Trajectory) -> DimensionResult:
        import json
        dim_desc = _DIMENSION_PROMPTS.get(dimension_id, dimension_label)
        user_msg = f"""维度：{dimension_label}
定义：{dim_desc}

用户 Query：{trajectory.user_query}
完整轨迹（JSON）：{trajectory.model_dump_json(indent=2)}

请对该维度打分并输出 JSON。"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()
        data = json.loads(raw)
        return DimensionResult(
            dimension_id=dimension_id,
            dimension_label=dimension_label,
            verdict=data["verdict"],
            score=float(data["score"]),
            reasoning=data.get("reasoning", ""),
            evidence=data.get("evidence", []),
        )
