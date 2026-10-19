import json
import tempfile
import unittest
from pathlib import Path

from slime_shopping_rl.shopping_slime.metrics_logger import log_rollout_metric
from slime_shopping_rl.shopping_slime.summarize_metrics import load_records, summarize


class MetricsLoggerTest(unittest.TestCase):
    def test_log_and_summarize_metrics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "metrics.jsonl"
            log_rollout_metric(
                {"query": "chair", "site_code": "UK-Site", "scenario_type": "search_recommend"},
                "answer [product:1]",
                {
                    "reward": 0.9,
                    "reward_detail": {
                        "reward_type": "successful_recommendation",
                        "llm_judge": {"score": 0.8, "adjustment": 0.12},
                        "product_count": 3,
                        "card_count": 1,
                    },
                },
                path=str(path),
            )
            records = load_records(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["judge_score"], 0.8)
            summary = summarize(records)
            self.assertEqual(summary["success_rate"], 1.0)
            self.assertEqual(summary["reward_mean"], 0.9)


if __name__ == "__main__":
    unittest.main()
