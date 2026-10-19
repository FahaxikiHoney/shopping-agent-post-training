import json
import unittest

from llm_evaluation.evaluate import (
    evaluate_one,
    format_trajectory,
    parse_judge_response,
    prepare_eval_input,
)


def test_format_trajectory_preserves_product_fields_without_currency_guess():
    messages = [
        {"role": "user", "content": "甜酱油"},
        {
            "role": "tool",
            "name": "sku_recall",
            "content": json.dumps(
                {
                    "count": 1,
                    "products": [
                        {
                            "sku_name": "ABC Kecap Manis 600ml",
                            "brand_name": "ABC",
                            "final_price": "3.99",
                            "price": "4.99",
                            "sales": "9 200+ vendus",
                            "keyword": "甜酱油",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
        },
        {
            "role": "tool",
            "name": "scenario_related_recall",
            "content": json.dumps(
                {
                    "count": 1,
                    "products": [
                        {
                            "sku_name": "Sweet soy sauce 500ml",
                            "final_price": "2.99",
                        }
                    ],
                }
            ),
        },
    ]

    formatted = format_trajectory(messages)

    assert "[1] ABC ABC Kecap Manis 600ml" in formatted
    assert "final_price=3.99" in formatted
    assert "original_price=4.99" in formatted
    assert "sales=9 200+ vendus" in formatted
    assert "keyword=甜酱油" in formatted
    assert "[2] Sweet soy sauce 500ml" in formatted
    assert "$3.99" not in formatted


def test_parse_judge_response_accepts_fenced_json():
    judge = {
        "d1_need_understanding": {"verdict": "PASS", "reason": "ok"},
        "d2_factual_accuracy": {"verdict": "PASS", "reason": "ok"},
        "d3_recommendation_quality": {"verdict": "PASS", "reason": "ok"},
        "d4_completeness": {"verdict": "PASS", "reason": "ok"},
        "d5_recommendation_value": {"verdict": "PASS", "reason": "ok"},
        "overall_comment": "ok",
    }

    parsed = parse_judge_response(
        "结果如下：\n```json\n" + json.dumps(judge, ensure_ascii=False) + "\n```"
    )

    assert parsed == judge


def test_evaluate_one_retries_transient_judge_failure():
    judge = {
        "d1_need_understanding": {"verdict": "PASS", "reason": "ok"},
        "d2_factual_accuracy": {"verdict": "PASS", "reason": "ok"},
        "d3_recommendation_quality": {"verdict": "PASS", "reason": "ok"},
        "d4_completeness": {"verdict": "PASS", "reason": "ok"},
        "d5_recommendation_value": {"verdict": "PASS", "reason": "ok"},
        "overall_comment": "ok",
    }

    class FakeLLM:
        def __init__(self):
            self.calls = 0

        def generate(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary 503")
            return json.dumps(judge), ""

    llm = FakeLLM()
    item = {
        "trajectory_id": "test",
        "scenario_type": "search_recommend",
        "user_query": "coffee",
        "messages": [
            {"role": "user", "content": "coffee"},
            {
                "role": "assistant",
                "content": "Coffee option.[product:1]",
            },
            {
                "role": "tool",
                "name": "sku_recall",
                "content": json.dumps(
                    {"count": 1, "products": [{"sku_name": "Coffee"}]}
                ),
            },
        ],
        "final_response": "Coffee option.[product:1]",
    }

    result = evaluate_one(item, llm, judge_retries=2, retry_delay=0)

    assert result["score"] == 1.0
    assert result["judge_attempts"] == 2
    assert llm.calls == 2


def test_prepare_eval_input_classifies_direct_response_requests():
    item = {
        "trajectory_id": "direct",
        "user_query": "Can I use milk instead of water in this Shopping coffee machine?",
        "metadata": {"tools_used": []},
        "messages": [
            {"role": "user", "content": "Can I use milk instead of water?"},
            {"role": "assistant", "content": "Please follow the product manual."},
        ],
    }
    prepared = prepare_eval_input(item)
    assert prepared["scenario_type"] == "direct_response"


class LlmEvaluationTest(unittest.TestCase):
    def test_product_fields_and_currency(self):
        test_format_trajectory_preserves_product_fields_without_currency_guess()

    def test_fenced_json(self):
        test_parse_judge_response_accepts_fenced_json()

    def test_transient_retry(self):
        test_evaluate_one_retries_transient_judge_failure()

    def test_direct_response_classification(self):
        test_prepare_eval_input_classifies_direct_response_requests()
