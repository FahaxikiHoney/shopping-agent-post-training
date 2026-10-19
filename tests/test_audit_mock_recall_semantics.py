import importlib.util
import socket
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "audit_mock_recall_semantics.py"
SPEC = importlib.util.spec_from_file_location("audit_mock_recall_semantics", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class RecallSemanticAuditTest(unittest.TestCase):
    def test_extract_json_array_accepts_fenced_json(self):
        parsed = MODULE.extract_json_array(
            "result:\n```json\n"
            '[{"sample_id":"a","verdict":"pass","reason":"ok","offending_products":[]}]'
            "\n```"
        )
        self.assertEqual(parsed[0]["sample_id"], "a")

    def test_summarize_counts_supported_verdicts(self):
        summary = MODULE.summarize([
            {"verdict": "pass"},
            {"verdict": "warn"},
            {"verdict": "warn"},
            {"verdict": "fail"},
        ])
        self.assertEqual(summary, {"pass": 1, "warn": 2, "fail": 1})

    def test_build_audit_item_uses_real_contract_products(self):
        item = MODULE.build_audit_item({
            "sample_id": "sample",
            "site_code": "DE-Site",
            "query": "Power Bank 20000mAh 65W",
        })
        self.assertEqual(item["sample_id"], "sample")
        self.assertEqual(len(item["products"]), 1)
        self.assertEqual(
            set(item["products"][0]),
            {
                "sku_id", "sku_name", "brand_name", "final_price", "price",
                "img_url", "good", "sales", "keyword",
            },
        )

    def test_socket_timeout_is_retryable(self):
        self.assertTrue(issubclass(socket.timeout, OSError))
        retryable = (
            MODULE.urllib.error.HTTPError,
            MODULE.urllib.error.URLError,
            MODULE.socket.timeout,
            TimeoutError,
            ValueError,
        )
        self.assertIsInstance(socket.timeout("timed out"), retryable)


if __name__ == "__main__":
    unittest.main()
