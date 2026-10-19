import unittest

from slime_shopping_rl.shopping_slime.llm_judge import (
    LLMJudgeConfig,
    apply_optional_llm_judge,
    judge_completion,
)


class LLMJudgeTest(unittest.TestCase):
    def test_disabled_judge_leaves_reward_unchanged(self):
        result = {"reward": 0.8, "reward_detail": {}}
        judged = apply_optional_llm_judge("query", "answer", result, config=LLMJudgeConfig(enabled=False))
        self.assertEqual(judged["reward"], 0.8)
        self.assertFalse(judged["reward_detail"]["llm_judge"]["enabled"])

    def test_judge_completion_parses_openai_compatible_response(self):
        def requester(url, headers, payload, timeout):
            self.assertTrue(url.endswith("/chat/completions"))
            self.assertIn("Authorization", headers)
            self.assertEqual(payload["stream"], False)
            return {"choices": [{"message": {"content": '{"score": 0.75, "reason": "grounded"}'}}]}

        judged = judge_completion(
            {"query": "chair"},
            "answer [product:1]",
            {"reward": 0.8, "reward_detail": {}},
            config=LLMJudgeConfig(api_key="test", enabled=True),
            requester=requester,
        )
        self.assertEqual(judged["score"], 0.75)

    def test_negative_rule_reward_cannot_be_rescued(self):
        def requester(url, headers, payload, timeout):
            return {"choices": [{"message": {"content": '{"score": 1.0, "reason": "looks ok"}'}}]}

        result = {"reward": -0.45, "reward_detail": {}}
        judged = apply_optional_llm_judge(
            "query",
            "answer without cards",
            result,
            config=LLMJudgeConfig(api_key="test", enabled=True, adjustment_scale=0.2),
            requester=requester,
        )
        self.assertEqual(judged["reward"], -0.45)


if __name__ == "__main__":
    unittest.main()
