import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "audit_mock_trajectory_semantics.py"
SPEC = importlib.util.spec_from_file_location("audit_mock_trajectory_semantics", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class TrajectorySemanticAuditTest(unittest.TestCase):
    def test_extract_json_array_accepts_fenced_json(self):
        parsed = MODULE.extract_json_array(
            "```json\n"
            '[{"sample_id":"a","verdict":"pass","reason":"ok","issue_tags":[]}]'
            "\n```"
        )
        self.assertEqual(parsed[0]["verdict"], "pass")

    def test_build_audit_item_compacts_tool_contract(self):
        result = {
            "success": True,
            "count": 1,
            "products": [{
                "sku_id": "1",
                "sku_name": "Example product",
                "brand_name": "Example",
                "final_price": "9.99",
                "price": "12.99",
                "sales": "10 sold",
                "keyword": "example",
                "img_url": "https://example.invalid/image.jpg",
            }],
        }
        row = {
            "sample": {
                "sample_id": "sample",
                "site_code": "UK-Site",
                "query": "example",
            },
            "trajectory": {
                "status": "done",
                "scenario_type": "search_recommend",
                "final_response": "Example.[product:1]",
                "messages": [
                    {
                        "role": "assistant",
                        "tool_calls": [{
                            "id": "call-1",
                            "function": {
                                "name": "sku_recall",
                                "arguments": json.dumps({"query": "example"}),
                            },
                        }],
                    },
                    {
                        "role": "tool",
                        "tool_call_id": "call-1",
                        "content": json.dumps(result),
                    },
                ],
            },
        }
        item = MODULE.build_audit_item(row)
        self.assertEqual(item["sample_id"], "sample")
        self.assertEqual(item["tool_calls"][0]["arguments"], {"query": "example"})
        product = item["tool_calls"][0]["result"]["products"][0]
        self.assertNotIn("img_url", product)
        self.assertEqual(product["sku_name"], "Example product")

    def test_summarize_counts_verdicts(self):
        self.assertEqual(
            MODULE.summarize([
                {"verdict": "pass"},
                {"verdict": "warn"},
                {"verdict": "fail"},
                {"verdict": "warn"},
            ]),
            {"pass": 1, "warn": 2, "fail": 1},
        )


if __name__ == "__main__":
    unittest.main()
