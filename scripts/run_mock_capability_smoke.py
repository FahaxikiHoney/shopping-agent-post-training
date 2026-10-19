#!/usr/bin/env python3
"""Run the current Shopping Mock capability smoke suite against the live model."""

import argparse
import json
import sys
import time
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shopping_agent.llm.client import LLMClient
from shopping_agent.react.agent import ReActShoppingAgent


SMOKE_CASES = [
    {
        "id": "uk_tv_constraints",
        "site_code": "UK-Site",
        "scenario_type": "search_recommend",
        "query": "Looking for a 75-inch 4K smart TV under £700",
    },
    {
        "id": "uk_bundle_budget",
        "site_code": "UK-Site",
        "scenario_type": "bundle_purchase",
        "query": "I need an ergonomic chair + desk lamp, total budget £300",
    },
    {
        "id": "de_multitool_budget",
        "site_code": "DE-Site",
        "scenario_type": "search_recommend",
        "query": "Ich suche ein Multifunktionswerkzeug unter 150€",
    },
    {
        "id": "de_shelf_life_grounding",
        "site_code": "DE-Site",
        "scenario_type": "search_recommend",
        "query": (
            "Ich suche Lebensmittel, die lange haltbar sind und die man auf Vorrat "
            "kaufen kann. Haltbarkeit ungefähr drei bis fünf Jahre."
        ),
    },
    {
        "id": "fr_matching",
        "site_code": "FR-Site",
        "scenario_type": "matching",
        "query": (
            "J'ai un canapé nordique et je cherche une table basse et un "
            "lampadaire assortis"
        ),
    },
    {
        "id": "fr_quiet_aircon_budget",
        "site_code": "FR-Site",
        "scenario_type": "search_recommend",
        "query": "Je cherche un climatiseur silencieux à moins de 300€ pour une chambre",
    },
    {
        "id": "nl_external_price_comparison",
        "site_code": "NL-Site",
        "scenario_type": "search_recommend",
        "query": "Wat is het prijsverschil van Red Bull tussen Shopping en Lidl?",
    },
    {
        "id": "nl_nail_polish_budget",
        "site_code": "NL-Site",
        "scenario_type": "search_recommend",
        "query": "Ik zoek nagellak onder €15",
    },
    {
        "id": "uk_bundle_natural_language",
        "site_code": "UK-Site",
        "scenario_type": "bundle_purchase",
        "query": (
            "I need an ergonomic chair and a desk lamp with a total budget of £300"
        ),
    },
    {
        "id": "de_bundle_natural_language",
        "site_code": "DE-Site",
        "scenario_type": "bundle_purchase",
        "query": (
            "Ich brauche einen ergonomischen Stuhl und eine Schreibtischlampe, "
            "Gesamtbudget 300€"
        ),
    },
    {
        "id": "fr_bundle_natural_language",
        "site_code": "FR-Site",
        "scenario_type": "bundle_purchase",
        "query": (
            "Je cherche une chaise ergonomique et une lampe de bureau avec un "
            "budget total de 300€"
        ),
    },
    {
        "id": "nl_bundle_natural_language",
        "site_code": "NL-Site",
        "scenario_type": "bundle_purchase",
        "query": (
            "Ik zoek een ergonomische stoel en een bureaulamp, totaalbudget €300"
        ),
    },
    {
        "id": "uk_bundle_three_categories",
        "site_code": "UK-Site",
        "scenario_type": "bundle_purchase",
        "query": (
            "I need an ergonomic chair, a desk lamp, and a keyboard with a total "
            "budget of £400"
        ),
    },
    {
        "id": "de_bundle_three_categories",
        "site_code": "DE-Site",
        "scenario_type": "bundle_purchase",
        "query": (
            "Ich brauche einen ergonomischen Stuhl, eine Schreibtischlampe und "
            "eine Tastatur, Gesamtbudget 400€"
        ),
    },
    {
        "id": "fr_bundle_three_categories",
        "site_code": "FR-Site",
        "scenario_type": "bundle_purchase",
        "query": (
            "Je cherche une chaise ergonomique, une lampe de bureau et un clavier, "
            "budget total 400€"
        ),
    },
    {
        "id": "nl_bundle_three_categories",
        "site_code": "NL-Site",
        "scenario_type": "bundle_purchase",
        "query": (
            "Ik zoek een ergonomische stoel, een bureaulamp en een toetsenbord, "
            "totaalbudget €400"
        ),
    },
    {
        "id": "uk_bundle_partial_recall",
        "site_code": "UK-Site",
        "scenario_type": "bundle_purchase",
        "query": (
            "I need an ergonomic chair and a hamster cage with a total budget of £300"
        ),
    },
    {
        "id": "fr_bundle_partial_recall",
        "site_code": "FR-Site",
        "scenario_type": "bundle_purchase",
        "query": (
            "Je cherche une chaise ergonomique et une cage pour hamster avec un "
            "budget total de 300€"
        ),
    },
    {
        "id": "uk_bundle_all_empty",
        "site_code": "UK-Site",
        "scenario_type": "bundle_purchase",
        "query": (
            "I need a hamster cage and marble eggs with a total budget of £300"
        ),
    },
    {
        "id": "fr_bundle_all_empty",
        "site_code": "FR-Site",
        "scenario_type": "bundle_purchase",
        "query": (
            "Je cherche une cage pour hamster et des œufs en marbre avec un "
            "budget total de 300€"
        ),
    },
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="GLM-5.2")
    parser.add_argument(
        "--output",
        default="sft_data/mock_capability_smoke_latest.jsonl",
    )
    parser.add_argument("--max-steps", type=int, default=7)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--retry-delay", type=int, default=15)
    parser.add_argument(
        "--case",
        action="append",
        dest="case_ids",
        help="Run only the named case; may be repeated",
    )
    args = parser.parse_args()

    selected_cases = [
        case
        for case in SMOKE_CASES
        if not args.case_ids or case["id"] in set(args.case_ids)
    ]
    if args.case_ids and len(selected_cases) != len(set(args.case_ids)):
        known = ", ".join(case["id"] for case in SMOKE_CASES)
        parser.error(f"unknown case id; available cases: {known}")

    client = LLMClient(model=args.model)
    rows = []
    failures = 0
    retryable_codes = {429, 502, 503, 504}

    for case in selected_cases:
        print(f"[{case['id']}] {case['site_code']} {case['query']}")
        last_error = None
        for attempt in range(args.retries):
            try:
                started = time.time()
                trajectory = ReActShoppingAgent(
                    llm=client,
                    max_steps=args.max_steps,
                    scenario_type=case["scenario_type"],
                    site_context=case["site_code"],
                ).run(case["query"])
                row = trajectory.to_sft_dict()
                row["smoke_case_id"] = case["id"]
                row["elapsed_seconds"] = round(time.time() - started, 1)
                rows.append(row)
                print(
                    f"  status={row['status']} steps={row['total_steps']} "
                    f"elapsed={row['elapsed_seconds']}s"
                )
                break
            except urllib.error.HTTPError as error:
                last_error = error
                if error.code not in retryable_codes or attempt == args.retries - 1:
                    break
                delay = args.retry_delay * (attempt + 1)
                print(f"  HTTP {error.code}; retrying in {delay}s")
                time.sleep(delay)
            except Exception as error:
                last_error = error
                break
        else:
            last_error = RuntimeError("retry loop ended without a trajectory")

        if not rows or rows[-1].get("smoke_case_id") != case["id"]:
            failures += 1
            print(f"  failed: {last_error}")

    output = Path(args.output)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"saved={output} completed={len(rows)} failed={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
