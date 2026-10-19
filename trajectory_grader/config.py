from dataclasses import dataclass, field

DIMENSION_WEIGHTS: dict[str, float] = {
    "d2_factuality": 0.20,
    "d3_relevance": 0.18,
    "d5_reasoning_value": 0.12,
}
BASE_SCORE_ON_GATE_PASS = 0.50
GATE_DIMENSIONS = {"d1_intent_understanding", "d4_completeness"}

# mock judge options: "mock_fixed" | "mock_random" | "mock_scenario"
DEFAULT_JUDGE_MODE = "mock_scenario"
