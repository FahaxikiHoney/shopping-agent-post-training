import json
import tempfile
import unittest
from pathlib import Path

from slime_joybuy_rl.joybuy_slime.build_toolcall_warmup import build_records, normalize_tool_answer


class ToolcallWarmupTest(unittest.TestCase):
    def test_normalize_sku_recall_keeps_only_query(self):
        text = (
            "<think>x</think>\n"
            "<tool_call>{\"name\":\"sku_recall\",\"arguments\":{\"query\":\"耳机\",\"max_price\":500}}</tool_call>"
        )
        normalized = normalize_tool_answer(text)
        self.assertIn("<tool_call>", normalized)
        self.assertIn('"query": "耳机"', normalized)
        self.assertNotIn("max_price", normalized)

    def test_build_records_extracts_first_tool_turn(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "data.json"
            path.write_text(json.dumps([{
                "conversations": [
                    {"from": "system", "value": "s"},
                    {"from": "human", "value": "推荐耳机"},
                    {"from": "gpt", "value": "<tool_call>{\"name\":\"sku_recall\",\"arguments\":{\"query\":\"耳机\"}}</tool_call>"},
                    {"from": "human", "value": "<tool_response>...</tool_response>"},
                ]
            }], ensure_ascii=False), encoding="utf-8")
            records = build_records(path)
        self.assertEqual(len(records), 1)
        self.assertEqual(len(records[0]["conversations"]), 3)


if __name__ == "__main__":
    unittest.main()
