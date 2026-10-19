"""5 个维度评分器，每个都委托给 judge 的 evaluate() 方法。"""
from dimensions.base_dimension import BaseDimension
from core.data_models import Trajectory, DimensionResult
from llm.judge_interface import JudgeInterface


def _make_dimension(dim_id: str, label: str) -> type:
    class Dim(BaseDimension):
        dimension_id = dim_id
        dimension_label = label

        def __init__(self, judge: JudgeInterface):
            self.judge = judge

        def evaluate(self, trajectory: Trajectory) -> DimensionResult:
            return self.judge.evaluate(self.dimension_id, self.dimension_label, trajectory)

    Dim.__name__ = f"Dimension_{dim_id}"
    return Dim


D1IntentUnderstanding = _make_dimension("d1_intent_understanding", "需求理解")
D2Factuality = _make_dimension("d2_factuality", "真实性与价格准确性")
D3Relevance = _make_dimension("d3_relevance", "推荐相关性与选择质量")
D4Completeness = _make_dimension("d4_completeness", "回应完整性与推荐充分性")
D5ReasoningValue = _make_dimension("d5_reasoning_value", "推荐理由价值感")

DIMENSION_ORDER = [
    ("d1_intent_understanding", D1IntentUnderstanding),
    ("d2_factuality", D2Factuality),
    ("d3_relevance", D3Relevance),
    ("d4_completeness", D4Completeness),
    ("d5_reasoning_value", D5ReasoningValue),
]
