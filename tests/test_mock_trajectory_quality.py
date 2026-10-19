import json
import unittest

from joybuy_agent.react.quality_gate import evaluate_trajectory
from joybuy_agent.react.tools import execute_tool


def build_trajectory(
    query="Looking for a 75-inch television",
    site_code="UK-Site",
    tool_name="sku_recall",
    arguments=None,
    tool_result=None,
    final_response=None,
):
    arguments = arguments or {"query": query}
    tool_result = tool_result or execute_tool(tool_name, arguments, site_code)
    products = tool_result.get("products", [])
    final_response = final_response or (
        f"**{products[0]['sku_name']}**: current price £{products[0]['final_price']}."
        "[product:1]\n\n"
        "How would you like to narrow the options? "
        "<ClickText>Budget</ClickText> <ClickText>Brand</ClickText> "
        "<ClickText>Sales</ClickText>"
    )
    call_id = "call_test"
    return {
        "trajectory_id": "test",
        "user_query": query,
        "site_context": {"site_code": site_code},
        "status": "done",
        "messages": [
            {"role": "system", "content": ""},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(arguments),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(tool_result),
            },
            {"role": "assistant", "content": final_response},
        ],
        "final_response": final_response,
    }


class MockTrajectoryQualityGateTest(unittest.TestCase):
    def test_valid_trajectory_passes(self):
        result = evaluate_trajectory(build_trajectory())
        self.assertTrue(result["passed"], result["issues"])

    def test_budget_product_mismatch_fails(self):
        trajectory = build_trajectory()
        budget_call_id = "call_budget"
        budget_result = execute_tool(
            "calculate_budget",
            {
                "items": [{"name": "Different product", "price": 10}],
                "total_budget": 100,
            },
            "UK-Site",
        )
        trajectory["messages"][-1:-1] = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": budget_call_id,
                        "type": "function",
                        "function": {
                            "name": "calculate_budget",
                            "arguments": json.dumps(
                                {
                                    "items": [{"name": "Different product", "price": 10}],
                                    "total_budget": 100,
                                }
                            ),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": budget_call_id,
                "content": json.dumps(budget_result),
            },
        ]
        result = evaluate_trajectory(trajectory)
        self.assertFalse(result["passed"])
        self.assertTrue(
            any("budget item is not referenced" in issue for issue in result["issues"])
        )

    def test_scenario_need_items_string_fails(self):
        trajectory = build_trajectory(
            query="I need a matching coffee table and floor lamp",
            tool_name="scenario_related_recall",
            arguments={
                "main_item": "Nordic sofa",
                "need_items": "coffee table, floor lamp",
                "style": "nordic",
            },
            tool_result=execute_tool(
                "scenario_related_recall",
                {
                    "main_item": "Nordic sofa",
                    "need_items": ["coffee table", "floor lamp"],
                    "style": "nordic",
                },
                "UK-Site",
            ),
        )
        result = evaluate_trajectory(trajectory)
        self.assertFalse(result["passed"])
        self.assertIn(
            "scenario_related_recall.need_items must be an array",
            result["issues"],
        )

    def test_empty_category_requires_final_acknowledgement(self):
        trajectory = build_trajectory()
        call_id = "call_empty"
        arguments = {"query": "hamster cage"}
        empty_result = execute_tool("sku_recall", arguments, "UK-Site")
        trajectory["messages"][-1:-1] = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": "sku_recall",
                            "arguments": json.dumps(arguments),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(empty_result),
            },
        ]
        failed = evaluate_trajectory(trajectory)
        self.assertFalse(failed["passed"])
        self.assertTrue(
            any("is not acknowledged" in issue for issue in failed["issues"])
        )

        acknowledgement = "\n\nNo matching products were found for: hamster cage."
        trajectory["final_response"] += acknowledgement
        trajectory["messages"][-1]["content"] = trajectory["final_response"]
        passed = evaluate_trajectory(trajectory)
        self.assertTrue(passed["passed"], passed["issues"])

    def test_dynamic_promotion_request_requires_disclaimer(self):
        query = "Welcher frische Fisch ist heute aktuell reduziert?"
        trajectory = build_trajectory(
            query=query,
            site_code="DE-Site",
            arguments={"query": "fresh fish"},
            final_response=(
                "**Ocean Fresh Fresh Atlantic Salmon Fischprodukt**: aktueller Preis €12.99."
                "[product:1]\n\n"
                "Wie möchten Sie die Auswahl weiter eingrenzen? "
                "<ClickText>Budget</ClickText> <ClickText>Marke</ClickText> "
                "<ClickText>Verkäufe</ClickText>"
            ),
        )
        failed = evaluate_trajectory(trajectory)
        self.assertFalse(failed["passed"])
        self.assertIn(
            "dynamic promotion or recency request lacks a grounded disclaimer",
            failed["issues"],
        )

        disclaimer = (
            "\n\nDie abgerufenen Felder enthalten keine Echtzeit-Aktionsdaten; "
            "daher kann ich aktuelle Rabatte nicht bestätigen."
        )
        trajectory["final_response"] += disclaimer
        trajectory["messages"][-1]["content"] = trajectory["final_response"]
        passed = evaluate_trajectory(trajectory)
        self.assertTrue(passed["passed"], passed["issues"])

    def test_french_external_price_disclaimer_is_recognized(self):
        query = "Comparer les composants PC avec les prix AliExpress"
        trajectory = build_trajectory(
            query=query,
            site_code="FR-Site",
            arguments={"query": "composants PC"},
            final_response=(
                "**Composants PC** : prix actuel €67.05.[product:1]\n\n"
                "Ces prix proviennent uniquement de Joybuy ; je ne dispose pas de "
                "prix externes fiables en temps réel pour confirmer l'écart.\n\n"
                "Comment affiner ? <ClickText>Budget</ClickText> "
                "<ClickText>Marque</ClickText>"
            ),
        )
        result = evaluate_trajectory(trajectory)
        self.assertTrue(result["passed"], result["issues"])

    def test_specialized_query_rejects_broad_category_products(self):
        broad_result = execute_tool(
            "sku_recall",
            {"query": "shampoo"},
            "UK-Site",
        )
        trajectory = build_trajectory(
            query="Loreal Elvive hair mask",
            site_code="UK-Site",
            arguments={"query": "Loreal Elvive hair mask"},
            tool_result=broad_result,
        )
        result = evaluate_trajectory(trajectory)
        self.assertFalse(result["passed"])
        self.assertTrue(
            any("subtype-mismatched" in issue for issue in result["issues"]),
            result["issues"],
        )

    def test_referenced_products_must_satisfy_minimum_numeric_specs(self):
        broad_result = execute_tool(
            "sku_recall",
            {"query": "power bank"},
            "DE-Site",
        )
        trajectory = build_trajectory(
            query=(
                "Ich suche eine Power Bank mit mindestens 20.000 mA Stunden "
                "und mindestens 65 W Power Output"
            ),
            site_code="DE-Site",
            arguments={"query": "Power Bank 20000mAh 65W 充电宝"},
            tool_result=broad_result,
            final_response=(
                "**Anker A1651 20000mAh 22.5W Powerbank**: aktueller Preis €19.99."
                "[product:2]\n\n"
                "Wie möchten Sie die Auswahl weiter eingrenzen? "
                "<ClickText>Budget</ClickText> <ClickText>Marke</ClickText> "
                "<ClickText>Verkäufe</ClickText>"
            ),
        )
        result = evaluate_trajectory(trajectory)
        self.assertFalse(result["passed"])
        self.assertTrue(
            any("violate requested numeric specifications" in issue for issue in result["issues"]),
            result["issues"],
        )

    def test_referenced_products_must_satisfy_price_and_screen_ranges(self):
        broad_result = execute_tool(
            "sku_recall",
            {"query": "television"},
            "NL-Site",
        )
        trajectory = build_trajectory(
            query="Tv voor ps5 tussen 65-75 inch en onder de 500 euro",
            site_code="NL-Site",
            arguments={"query": "television"},
            tool_result=broad_result,
            final_response=(
                "**TCL P745 75 inch 4K televisie**: actuele prijs €519.99."
                "[product:7]\n\n"
                "Hoe wilt u de opties verfijnen? "
                "<ClickText>Budget</ClickText> <ClickText>Merk</ClickText> "
                "<ClickText>Verkoop</ClickText>"
            ),
        )
        result = evaluate_trajectory(trajectory)
        self.assertFalse(result["passed"])
        self.assertTrue(
            any("violate requested price or screen-size range" in issue for issue in result["issues"]),
            result["issues"],
        )


if __name__ == "__main__":
    unittest.main()
