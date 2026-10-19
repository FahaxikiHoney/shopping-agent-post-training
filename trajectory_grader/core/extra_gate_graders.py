import re
from core.data_models import Trajectory, ExtraGateResult


class CardIdValidator:
    """检查回复卡片中的 ID 是否全部出现在工具返回结果里，否则视为幻觉。"""

    def validate(self, trajectory: Trajectory) -> ExtraGateResult:
        returned_ids = trajectory.get_all_returned_product_ids()
        card_ids = trajectory.get_all_card_ids()
        hallucinated = card_ids - returned_ids
        return ExtraGateResult(
            name="card_id_validator",
            passed=len(hallucinated) == 0,
            detail={
                "returned_ids": sorted(returned_ids),
                "card_ids": sorted(card_ids),
                "hallucinated_ids": sorted(hallucinated),
            },
        )


class ToolCallFailureRateChecker:
    """只要存在 CALLER_ERROR（模型自身传参错误）就判定失败，SYSTEM_ERROR 不惩罚。"""

    def check(self, trajectory: Trajectory) -> ExtraGateResult:
        caller_errors = []
        for step in trajectory.steps:
            if step.error_type == "CALLER_ERROR":
                caller_errors.append(f"step_{step.step_id}:{step.tool_name}")
            elif step.tool_output and step.tool_output.status == "CALLER_ERROR":
                caller_errors.append(f"step_{step.step_id}:{step.tool_name}(output)")
        return ExtraGateResult(
            name="tool_call_failure_rate",
            passed=len(caller_errors) == 0,
            detail={"caller_errors": caller_errors},
        )


class TextQualityPenaltyChecker:
    """轻量规则检测最终回复的文本质量问题。"""

    MAX_REPEAT_WINDOW = 20
    JUNK_CHAR_RATIO_THRESHOLD = 0.15

    def check(self, trajectory: Trajectory) -> ExtraGateResult:
        text = trajectory.final_response
        issues = []

        if not text or len(text.strip()) < 5:
            issues.append("回复内容为空或过短")

        # 先剥离 Markdown 表格分隔符行（| --- | --- |），避免误判
        text_for_repeat = re.sub(r"\|[\s\-:|]+\|", "", text)

        # 连续重复字符块检测（如 "的的的的的" 或 "推荐推荐推荐"）
        if re.search(r"(.{3,})\1{3,}", text_for_repeat):
            issues.append("检测到异常重复文本片段")

        # 乱码字符占比（非中文/英文/数字/常用标点）
        total = max(len(text), 1)
        junk_chars = len(re.findall(r"[^一-鿿 -~a-zA-Z0-9，。！？、：；""''（）【】\n\r\t]", text))
        if junk_chars / total > self.JUNK_CHAR_RATIO_THRESHOLD:
            issues.append(f"异常字符占比过高：{junk_chars}/{total}")

        return ExtraGateResult(
            name="text_quality_penalty",
            passed=len(issues) == 0,
            detail={"issues": issues},
        )
