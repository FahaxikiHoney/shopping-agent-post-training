import unittest

from slime_joybuy_rl.joybuy_slime.action_parser import parse_actions
from slime_joybuy_rl.joybuy_slime.reward_adapter import evaluate_completion


class SlimeJoybuyAdapterTest(unittest.TestCase):
    def test_parse_xml_tool_call(self):
        actions = parse_actions(
            '<think>search first</think><tool_call>{"name":"sku_recall","arguments":{"query":"Football hobby box"}}</tool_call>'
        )
        self.assertEqual(actions, [{
            "type": "tool_call",
            "name": "sku_recall",
            "arguments": {"query": "Football hobby box"},
        }])

    def test_final_without_search_gets_negative_reward(self):
        result = evaluate_completion(
            {"query": "Football hobby box", "site_code": "UK-Site"},
            "Sorry, I cannot help. <ClickText>Budget</ClickText> <ClickText>Brand</ClickText>",
        )
        self.assertLess(result["reward"], 0)
        self.assertEqual(result["reward_detail"]["reward_type"], "missing_required_search")


if __name__ == "__main__":
    unittest.main()
