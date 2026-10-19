import unittest

from slime_shopping_rl.shopping_slime.sft_smoke_test import clean_final_output, format_tool_response, iter_queries


class SftSmokeTestUtilityTest(unittest.TestCase):
    def test_format_tool_response_outputs_train_style_block(self):
        text = format_tool_response({
            "products": [{
                "sku_name": "Test product",
                "final_price": 99,
                "sales": "100 sold",
                "keyword": "headphones",
            }]
        })
        self.assertIn("<tool_response>", text)
        self.assertIn("[1] Test product", text)
        self.assertIn("</tool_response>", text)

    def test_iter_queries_accepts_cli_queries(self):
        tasks = list(iter_queries(None, ["Football hobby box"], limit=1))
        self.assertEqual(tasks[0]["query"], "Football hobby box")

    def test_clean_final_output_removes_thinking(self):
        text = clean_final_output("<think>hidden</think>\n推荐 A。[product:1]")
        self.assertEqual(text, "推荐 A。[product:1]")

    def test_clean_final_output_normalizes_broken_product_card(self):
        text = clean_final_output("推荐 A。俒product:1]")
        self.assertIn("[product:1]", text)


if __name__ == "__main__":
    unittest.main()
