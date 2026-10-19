from core.data_models import Trajectory, GradeResult, ScoreBreakdown
from core.extra_gate_graders import CardIdValidator, ToolCallFailureRateChecker, TextQualityPenaltyChecker
from dimensions.all_dimensions import DIMENSION_ORDER
from llm.judge_interface import JudgeInterface
import config


class GraderEngine:
    """
    评分流程编排器。执行顺序：
    1. 3 个规则型 Extra Gate（任意失败 → 0 分）
    2. 5 个维度并行评分（委托 judge）
    3. Gate 维度检查（D1 + D4，任意 FAIL → 0 分）
    4. 加权聚合总分
    """

    GATE_DIMS = config.GATE_DIMENSIONS
    WEIGHTS = config.DIMENSION_WEIGHTS
    BASE = config.BASE_SCORE_ON_GATE_PASS

    def __init__(self, judge: JudgeInterface):
        self.judge = judge
        self._card_val = CardIdValidator()
        self._tool_check = ToolCallFailureRateChecker()
        self._text_check = TextQualityPenaltyChecker()

    def grade(self, trajectory: Trajectory) -> GradeResult:
        # ── Step 1: Extra Gate（规则型）──────────────────────────────
        extra_gates = [
            self._card_val.validate(trajectory),
            self._tool_check.check(trajectory),
            self._text_check.check(trajectory),
        ]
        failed_extra = [g for g in extra_gates if not g.passed]
        if failed_extra:
            return GradeResult(
                trajectory_id=trajectory.trajectory_id,
                final_score=0.0,
                is_gate_failed=True,
                gate_failures=[g.name for g in failed_extra],
                extra_gate_results=extra_gates,
                dimension_scores={},
                score_breakdown=ScoreBreakdown(),
                judge_mode=self.judge.get_judge_name(),
            )

        # ── Step 2: 5 维度评分 ────────────────────────────────────────
        dim_results = {}
        for dim_id, DimClass in DIMENSION_ORDER:
            dim = DimClass(self.judge)
            dim_results[dim_id] = dim.evaluate(trajectory)

        # ── Step 3: Gate 维度检查 ─────────────────────────────────────
        gate_failures = [
            dim_id for dim_id in self.GATE_DIMS
            if dim_id in dim_results and dim_results[dim_id].verdict == "FAIL"
        ]
        if gate_failures:
            return GradeResult(
                trajectory_id=trajectory.trajectory_id,
                final_score=0.0,
                is_gate_failed=True,
                gate_failures=gate_failures,
                extra_gate_results=extra_gates,
                dimension_scores=dim_results,
                score_breakdown=ScoreBreakdown(),
                judge_mode=self.judge.get_judge_name(),
            )

        # ── Step 4: 加权聚合 ──────────────────────────────────────────
        d2_score = dim_results.get("d2_factuality")
        d3_score = dim_results.get("d3_relevance")
        d5_score = dim_results.get("d5_reasoning_value")

        d2_contrib = (d2_score.score if d2_score else 0.0) * self.WEIGHTS["d2_factuality"]
        d3_contrib = (d3_score.score if d3_score else 0.0) * self.WEIGHTS["d3_relevance"]
        d5_contrib = (d5_score.score if d5_score else 0.0) * self.WEIGHTS["d5_reasoning_value"]
        total = round(self.BASE + d2_contrib + d3_contrib + d5_contrib, 4)

        return GradeResult(
            trajectory_id=trajectory.trajectory_id,
            final_score=total,
            is_gate_failed=False,
            gate_failures=[],
            extra_gate_results=extra_gates,
            dimension_scores=dim_results,
            score_breakdown=ScoreBreakdown(
                base_score=self.BASE,
                d2_contribution=round(d2_contrib, 4),
                d3_contribution=round(d3_contrib, 4),
                d5_contribution=round(d5_contrib, 4),
                total=total,
            ),
            judge_mode=self.judge.get_judge_name(),
        )
