from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, model_validator


class Product(BaseModel):
    product_id: str
    title: str
    price: float
    is_jd_self: bool = False
    rating: float = 0.0
    attributes: dict = {}


class ProductCard(BaseModel):
    card_id: str
    display_price: float
    reason: str = ""


class ToolOutput(BaseModel):
    status: Literal["SUCCESS", "CALLER_ERROR", "SYSTEM_ERROR", "TIMEOUT"]
    products: list[Product] = []
    raw_data: dict = {}


class TrajectoryStep(BaseModel):
    step_id: int
    step_type: Literal["tool_call", "llm_reasoning", "final_response"]
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    tool_output: Optional[ToolOutput] = None
    content: Optional[str] = None
    product_cards: list[ProductCard] = []
    error_type: Optional[Literal["CALLER_ERROR", "SYSTEM_ERROR", "TIMEOUT"]] = None


class Trajectory(BaseModel):
    trajectory_id: str
    user_query: str
    session_context: dict = {}
    steps: list[TrajectoryStep]
    final_response: str = ""

    @model_validator(mode="after")
    def sync_final_response(self) -> "Trajectory":
        if not self.final_response:
            for step in reversed(self.steps):
                if step.step_type == "final_response" and step.content:
                    self.final_response = step.content
                    break
        return self

    def get_tool_call_steps(self) -> list[TrajectoryStep]:
        return [s for s in self.steps if s.step_type == "tool_call"]

    def get_all_returned_product_ids(self) -> set[str]:
        ids: set[str] = set()
        for step in self.steps:
            if step.tool_output and step.tool_output.products:
                for p in step.tool_output.products:
                    ids.add(p.product_id)
        return ids

    def get_all_card_ids(self) -> set[str]:
        ids: set[str] = set()
        for step in self.steps:
            for card in step.product_cards:
                ids.add(card.card_id)
        return ids

    def has_caller_errors(self) -> bool:
        for step in self.steps:
            if step.error_type == "CALLER_ERROR":
                return True
            if step.tool_output and step.tool_output.status == "CALLER_ERROR":
                return True
        return False


class DimensionResult(BaseModel):
    dimension_id: str
    dimension_label: str
    verdict: Literal["PASS", "FAIL"]
    score: float
    reasoning: str
    evidence: list[str] = []


class ExtraGateResult(BaseModel):
    name: str
    passed: bool
    detail: dict = {}


class ScoreBreakdown(BaseModel):
    base_score: float = 0.0
    d2_contribution: float = 0.0
    d3_contribution: float = 0.0
    d5_contribution: float = 0.0
    total: float = 0.0


class GradeResult(BaseModel):
    trajectory_id: str
    final_score: float
    is_gate_failed: bool
    gate_failures: list[str] = []
    extra_gate_results: list[ExtraGateResult] = []
    dimension_scores: dict[str, DimensionResult] = {}
    score_breakdown: ScoreBreakdown = ScoreBreakdown()
    judge_mode: str = ""
