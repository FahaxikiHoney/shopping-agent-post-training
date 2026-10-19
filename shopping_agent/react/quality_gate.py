"""Deterministic quality checks for Shopping ReAct trajectories."""

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from shopping_agent.react.agent import ReActShoppingAgent
from shopping_agent.react.tools import (
    invalid_requested_range_product_ids,
    invalid_requested_spec_product_ids,
    invalid_specialized_product_ids,
)


REAL_PRODUCT_KEYS = {
    "sku_id",
    "sku_name",
    "brand_name",
    "final_price",
    "price",
    "img_url",
    "good",
    "sales",
    "keyword",
}

SITE_CURRENCIES = {
    "UK-Site": ("GBP", "£"),
    "DE-Site": ("EUR", "€"),
    "FR-Site": ("EUR", "€"),
    "NL-Site": ("EUR", "€"),
}


def unwrap_trajectory(record: Dict[str, Any]) -> Dict[str, Any]:
    trajectory = record.get("trajectory")
    return trajectory if isinstance(trajectory, dict) else record


def load_jsonl(paths: Iterable[Path]) -> List[Tuple[str, int, Dict[str, Any]]]:
    records = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                records.append((str(path), line_number, json.loads(line)))
    return records


def _site_code(trajectory: Dict[str, Any]) -> str:
    site_context = trajectory.get("site_context")
    if isinstance(site_context, dict):
        return str(site_context.get("site_code") or "")
    return str(site_context or "")


def _parse_json(value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _display_products(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    products = []
    seen = set()
    for message in messages:
        if message.get("role") != "tool":
            continue
        result = _parse_json(message.get("content")) or {}
        for product in result.get("products", []):
            identity = str(
                product.get("sku_id")
                or product.get("product_id")
                or product.get("sku_name")
                or product.get("title")
            )
            if identity in seen:
                continue
            seen.add(identity)
            display_product = dict(product)
            display_product["_display_index"] = len(products) + 1
            products.append(display_product)
    return products


def _has_negative_confirmation(text: str) -> bool:
    patterns = (
        r"cannot confirm",
        r"无法.{0,8}确认",
        r"nicht bestätigen",
        r"ne (?:peux|pouvons).{0,20}confirmer",
        r"prix externes fiables",
        r"niet bevestigen",
        r"확인할 수 없",
    )
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def evaluate_trajectory(record: Dict[str, Any]) -> Dict[str, Any]:
    trajectory = unwrap_trajectory(record)
    messages = trajectory.get("messages") or []
    query = str(trajectory.get("user_query") or "")
    final = str(trajectory.get("final_response") or "")
    site_code = _site_code(trajectory)
    issues: List[str] = []
    warnings: List[str] = []

    if trajectory.get("status") != "done":
        issues.append(f"trajectory status is {trajectory.get('status')!r}, expected 'done'")
    if not query:
        issues.append("missing user_query")
    if not final:
        issues.append("missing final_response")

    tool_names_by_id = {}
    tool_arguments_by_id = {}
    tool_call_count = 0
    for message in messages:
        for call in message.get("tool_calls") or []:
            tool_call_count += 1
            function = call.get("function") or {}
            name = str(function.get("name") or "")
            tool_names_by_id[call.get("id")] = name
            arguments = _parse_json(function.get("arguments"))
            if arguments is None:
                issues.append(f"{name or 'tool'} has invalid JSON arguments")
                continue
            tool_arguments_by_id[call.get("id")] = arguments
            if name == "sku_recall" and set(arguments) != {"query"}:
                issues.append(f"sku_recall arguments must only contain query: {sorted(arguments)}")
            if name == "scenario_related_recall" and not isinstance(
                arguments.get("need_items"), list
            ):
                issues.append("scenario_related_recall.need_items must be an array")

    tool_result_count = 0
    budget_results = []
    empty_sku_queries = []
    successful_scenario_seen = False
    redundant_sku_after_scenario = False
    for message in messages:
        if message.get("role") == "assistant":
            if successful_scenario_seen:
                redundant_sku_after_scenario = redundant_sku_after_scenario or any(
                    (call.get("function") or {}).get("name") == "sku_recall"
                    for call in message.get("tool_calls") or []
                )
            continue
        if message.get("role") != "tool":
            continue
        tool_result_count += 1
        result = _parse_json(message.get("content"))
        tool_name = tool_names_by_id.get(message.get("tool_call_id"), "")
        if result is None:
            issues.append(f"{tool_name or 'tool'} returned invalid JSON")
            continue
        if result.get("status") == "ERROR":
            issues.append(f"{tool_name or 'tool'} returned ERROR: {result.get('message', '')}")
        if tool_name == "scenario_related_recall" and result.get("status") == "SUCCESS":
            successful_scenario_seen = bool(result.get("products"))
        if tool_name == "calculate_budget":
            budget_results.append(result)
        if tool_name == "sku_recall" and result.get("count") == 0:
            arguments = tool_arguments_by_id.get(message.get("tool_call_id"), {})
            empty_sku_queries.append(str(arguments.get("query") or ""))
        if tool_name == "sku_recall" and result.get("products"):
            arguments = tool_arguments_by_id.get(message.get("tool_call_id"), {})
            invalid_ids = invalid_specialized_product_ids(
                str(arguments.get("query") or ""),
                result.get("products") or [],
            )
            if invalid_ids:
                issues.append(
                    "specialized query returned subtype-mismatched products: "
                    + ", ".join(invalid_ids)
                )
        for product in result.get("products", []):
            actual_keys = set(product)
            expected_keys = set(REAL_PRODUCT_KEYS)
            if tool_name == "scenario_related_recall":
                expected_keys.add("match_reason")
            if actual_keys != expected_keys:
                issues.append(
                    f"{tool_name or 'product tool'} product keys mismatch: "
                    f"missing={sorted(expected_keys - actual_keys)}, "
                    f"extra={sorted(actual_keys - expected_keys)}"
                )
            if site_code and re.search(r"[\u4e00-\u9fff]", str(product.get("sku_name", ""))):
                issues.append(f"localized product title contains Chinese: {product.get('sku_name')}")

    if tool_call_count != tool_result_count:
        issues.append(
            f"tool calls/results are not paired: {tool_call_count}/{tool_result_count}"
        )
    if redundant_sku_after_scenario:
        warnings.append("sku_recall executed after a successful scenario recall")

    display_products = _display_products(messages)
    refs = [int(value) for value in re.findall(r"\[product:(\d+)\]", final)]
    if len(refs) != len(set(refs)):
        issues.append("duplicate product card references")
    invalid_refs = sorted(set(refs) - set(range(1, len(display_products) + 1)))
    if invalid_refs:
        issues.append(f"out-of-range product card references: {invalid_refs}")
    if display_products and not refs:
        issues.append("tool returned products but final response has no product cards")
    if not display_products and refs:
        issues.append("final response has product cards without tool products")
    referenced_products = [
        display_products[index - 1]
        for index in refs
        if 1 <= index <= len(display_products)
    ]
    invalid_spec_ids = invalid_requested_spec_product_ids(query, referenced_products)
    if invalid_spec_ids:
        issues.append(
            "referenced products violate requested numeric specifications: "
            + ", ".join(invalid_spec_ids)
        )
    invalid_range_ids = invalid_requested_range_product_ids(
        query,
        referenced_products,
        site_code,
    )
    if invalid_range_ids:
        issues.append(
            "referenced products violate requested price or screen-size range: "
            + ", ".join(invalid_range_ids)
        )
    if empty_sku_queries:
        no_result_markers = (
            "no matching products", "keine passenden produkte", "aucun produit correspondant",
            "geen passende producten", "未找到匹配商品", "찾지 못했습니다",
            "did not find a suitable product", "kein passendes produkt gefunden",
            "n'a trouvé aucun produit adapté", "geen geschikt product gevonden",
            "couldn't find a suitable product", "habe ich noch kein passendes produkt gefunden",
            "je n'ai pas encore trouvé de produit adapté",
            "heb ik nog geen geschikt product gevonden",
            "未能找到合适的商品", "暂时没有找到合适的商品",
        )
        if not any(marker in final.lower() for marker in no_result_markers):
            issues.append(
                "empty bundle/search result is not acknowledged in the final response: "
                + " / ".join(empty_sku_queries)
            )

    opening_clicks = final.count("<ClickText>")
    closing_clicks = final.count("</ClickText>")
    if opening_clicks != closing_clicks:
        issues.append("unbalanced ClickText tags")
    elif opening_clicks not in {2, 3}:
        issues.append(f"expected 2-3 ClickText tags, found {opening_clicks}")

    expected_language = ReActShoppingAgent(None, site_context=site_code)._response_language(query)
    if expected_language != "zh" and re.search(r"[\u4e00-\u9fff]", final):
        issues.append(f"final response contains Chinese for {expected_language} query")

    if site_code in SITE_CURRENCIES and (display_products or budget_results):
        currency_code, currency_symbol = SITE_CURRENCIES[site_code]
        if currency_symbol not in final:
            issues.append(f"final response is missing site currency {currency_symbol}")
        wrong_symbols = {"£", "€", "¥", "￥"} - {currency_symbol}
        used_wrong = sorted(symbol for symbol in wrong_symbols if symbol in final)
        if used_wrong:
            issues.append(f"final response contains wrong currency symbols: {used_wrong}")
        for budget in budget_results:
            if budget.get("currency_code") != currency_code:
                issues.append(
                    f"budget currency is {budget.get('currency_code')}, expected {currency_code}"
                )
            total_text = f"{float(budget.get('total_price', 0)):.2f}"
            if total_text not in final:
                issues.append(f"final response is missing budget total {total_text}")
            referenced_titles = {
                str(display_products[index - 1].get("sku_name", ""))
                for index in refs
                if 1 <= index <= len(display_products)
            }
            for item in budget.get("items", []):
                if str(item.get("name", "")) not in referenced_titles:
                    issues.append(
                        f"budget item is not referenced by a product card: {item.get('name', '')}"
                    )

    unsupported_fact_patterns = (
        r"\b\d+(?:\.\d+)?\s*dB\b",
        r"\b\d+(?:[-–]\d+)?\s*(?:m²|sqm)\b",
        r"\b(?:CE|FDA|RoHS)\s+(?:certified|认证|zertifiziert)\b",
    )
    for pattern in unsupported_fact_patterns:
        if re.search(pattern, final, re.IGNORECASE):
            issues.append(f"final response contains unsupported product fact: {pattern}")

    lower_query = query.lower()
    if any(marker in lower_query for marker in ("lidl", "amazon", "ebay", "aliexpress")):
        if not _has_negative_confirmation(final):
            issues.append("external price comparison lacks a grounded disclaimer")
    if any(
        marker in lower_query
        for marker in (
            "shelf life", "haltbarkeit", "lange haltbar", "durée de conservation",
            "houdbaarheid", "保质期", "长期保存", "长期储存",
        )
    ):
        if not _has_negative_confirmation(final):
            issues.append("shelf-life request lacks an exact-data disclaimer")
    if any(
        marker in lower_query
        for marker in (
            "today reduced", "discounted today", "currently reduced", "current promotion",
            "latest promotion", "latest model", "newest", "neueste", "neusten",
            "aktuell reduziert", "heute reduziert",
            "promotion actuelle", "réduit aujourd'hui", "actuellement réduit",
            "vandaag afgeprijsd", "actuele aanbieding", "nieuwste",
            "今日降价", "今天降价", "当前促销", "最新活动", "最新款", "现在打折",
        )
    ):
        if not _has_negative_confirmation(final):
            issues.append("dynamic promotion or recency request lacks a grounded disclaimer")

    if re.search(
        r"sku_recall|\[product:x\]|我应该使用|需要调用工具|tool planning",
        final,
        re.IGNORECASE,
    ):
        issues.append("final response leaks internal tool planning")

    issues = list(dict.fromkeys(issues))
    warnings = list(dict.fromkeys(warnings))

    return {
        "trajectory_id": trajectory.get("trajectory_id"),
        "query": query,
        "site_code": site_code,
        "status": trajectory.get("status"),
        "tool_calls": tool_call_count,
        "products": len(display_products),
        "cards": len(refs),
        "issues": issues,
        "warnings": warnings,
        "passed": not issues,
    }


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "total": len(results),
        "passed": sum(result["passed"] for result in results),
        "failed": sum(not result["passed"] for result in results),
        "warnings": sum(len(result["warnings"]) for result in results),
        "issues": sum(len(result["issues"]) for result in results),
    }
