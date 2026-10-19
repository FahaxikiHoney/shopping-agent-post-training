"""Stateful reinforcement-learning environment for the Shopping Mock tools."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from shopping_agent.react.agent import ReActShoppingAgent, SYSTEM_PROMPT_TRAIN
from shopping_agent.react.quality_gate import evaluate_trajectory
from shopping_agent.react.tools import SHOPPING_TOOLS_SCHEMA, VALID_TOOL_NAMES, execute_tool


class ShoppingEnvironmentStateError(RuntimeError):
    """Raised when reset/step are called in an invalid order."""


@dataclass(frozen=True)
class ShoppingTask:
    query: str
    site_code: str = "UK-Site"
    scenario_type: str = "search_recommend"
    task_id: str = ""


class ShoppingMockEnv:
    """A deterministic reset/step environment around the Shopping Mock tools."""

    reward_version = "shopping-mock-reward-v1"

    def __init__(self, max_steps: int = 5, tool_cost: float = 0.01):
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        if tool_cost < 0:
            raise ValueError("tool_cost must be non-negative")
        self.max_steps = int(max_steps)
        self.tool_cost = float(tool_cost)
        self.task: Optional[ShoppingTask] = None
        self.messages: List[Dict[str, Any]] = []
        self.tool_steps: List[Dict[str, Any]] = []
        self.done = False
        self.step_count = 0
        self._recent_action_signatures: List[str] = []

    def reset(
        self,
        task: ShoppingTask | Dict[str, Any] | str,
        site_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.task = self._coerce_task(task, site_code)
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT_TRAIN},
            {"role": "user", "content": self.task.query},
        ]
        self.tool_steps = []
        self.done = False
        self.step_count = 0
        self._recent_action_signatures = []
        return self._observation()

    def step(self, action: Dict[str, Any] | str) -> Dict[str, Any]:
        self._require_active()
        action_type, payload, error = self._normalize_action(action)
        self.step_count += 1

        if error:
            return self._invalid_action_result(error)
        if action_type == "final":
            return self._finish(str(payload["content"]))
        return self._execute_tool_action(
            str(payload["name"]),
            dict(payload["arguments"]),
        )

    def _execute_tool_action(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        call_id = f"call_{self.step_count}"
        signature = json.dumps(
            {"name": tool_name, "arguments": arguments},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        repeated = signature in self._recent_action_signatures[-3:]
        self._recent_action_signatures.append(signature)

        self.messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": call_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(arguments, ensure_ascii=False),
                },
            }],
        })
        result = execute_tool(tool_name, arguments, self.task.site_code)
        self.messages.append({
            "role": "tool",
            "tool_call_id": call_id,
            "content": json.dumps(result, ensure_ascii=False),
        })
        self.tool_steps.append({
            "name": tool_name,
            "arguments": copy.deepcopy(arguments),
            "result": copy.deepcopy(result),
            "repeated": repeated,
        })

        if self.step_count >= self.max_steps:
            return self._terminate_failure(
                "max_steps",
                -0.8,
                ["maximum environment steps reached before a final response"],
            )

        penalty = -self.tool_cost - (0.07 if repeated else 0.0)
        return {
            **self._observation(latest_result=result),
            "reward": round(penalty, 4),
            "reward_detail": {
                "reward_version": self.reward_version,
                "reward_type": "tool_observation",
                "reward_valid": True,
                "terminal_utility": round(penalty, 4),
                "termination_reason": "",
                "repeated_action": repeated,
            },
        }

    def _finish(self, content: str) -> Dict[str, Any]:
        final = content.strip()
        if not final:
            return self._terminate_failure(
                "invalid_final_response",
                -0.7,
                ["final response is empty"],
            )

        self.messages.append({"role": "assistant", "content": final})
        trajectory = self._trajectory(final)
        gate = evaluate_trajectory(trajectory)
        reward, reward_type, components, issues = self._terminal_reward(final, gate)
        self.done = True
        return {
            **self._observation(),
            "done": True,
            "reward": reward,
            "reward_detail": {
                "reward_version": self.reward_version,
                "reward_type": reward_type,
                "reward_valid": True,
                "terminal_utility": reward,
                "termination_reason": reward_type,
                "components": components,
                "issues": issues,
                "tool_call_count": len(self.tool_steps),
                "product_count": len(self._display_products()),
                "card_count": len(re.findall(r"\[product:(\d+)\]", final)),
            },
            "trajectory": trajectory,
        }

    def _terminal_reward(
        self,
        final: str,
        gate: Dict[str, Any],
    ) -> Tuple[float, str, Dict[str, float], List[str]]:
        products = self._display_products()
        refs = [int(value) for value in re.findall(r"\[product:(\d+)\]", final)]
        valid_ref_set = set(range(1, len(products) + 1))
        invalid_refs = sorted(set(refs) - valid_ref_set)
        duplicate_refs = len(refs) != len(set(refs))
        tool_names = [step["name"] for step in self.tool_steps]
        required_tool = self._required_tool_name()
        requires_search = required_tool is not None
        has_search = required_tool in tool_names if required_tool else False
        gate_issues = list(gate.get("issues") or [])

        components = {
            "tool_use": 0.0,
            "card_grounding": 0.0,
            "response_quality": 0.0,
            "task_completion": 0.0,
            "efficiency": max(0.0, 0.1 - self.tool_cost * len(self.tool_steps)),
        }
        issues = list(gate_issues)

        if requires_search and not has_search:
            issues.append(f"shopping request ended without {required_tool}")
            return -0.6, "missing_required_search", components, issues
        if invalid_refs or duplicate_refs:
            if invalid_refs:
                issues.append(f"invalid product references: {invalid_refs}")
            if duplicate_refs:
                issues.append("duplicate product references")
            return -0.5, "invalid_product_cards", components, issues
        if products and not refs:
            issues.append("products were available but no product card was selected")
            return -0.45, "missing_product_cards", components, issues
        if not products and refs:
            issues.append("product cards were emitted without tool products")
            return -0.5, "hallucinated_product_cards", components, issues
        if required_tool == "sku_recall" and not products:
            canonical_result = execute_tool(
                "sku_recall",
                {"query": self.task.query},
                self.task.site_code,
            )
            if canonical_result.get("count", 0) > 0:
                issues.append(
                    "the original query had products, but the executed search avoided them"
                )
                return -0.4, "avoidable_no_result", components, issues

        components["tool_use"] = 0.2 if has_search else 0.15
        components["card_grounding"] = 0.3 if products and refs else 0.2
        components["response_quality"] = 0.2 if not gate_issues else 0.0

        if products and refs:
            components["task_completion"] = 0.2
            reward_type = "successful_recommendation"
        elif requires_search:
            components["tool_use"] = 0.15
            components["card_grounding"] = 0.1
            components["response_quality"] = 0.1 if not gate_issues else 0.0
            components["task_completion"] = 0.0
            reward_type = "valid_no_result"
        else:
            components["task_completion"] = 0.2
            reward_type = "valid_direct_response"

        reward = round(sum(components.values()), 4)
        if reward_type == "valid_no_result":
            reward = min(reward, 0.45)
        if gate_issues:
            reward = min(reward, 0.25)
            reward_type = "quality_gate_failure"
        return reward, reward_type, components, issues

    def _required_tool_name(self) -> Optional[str]:
        if not ReActShoppingAgent._should_force_initial_product_search(self.task.query):
            return None
        return {
            "matching": "scenario_related_recall",
            "similar_rec": "similar_sku_recommend",
            "bundle_purchase": "sku_recall",
            "search_recommend": "sku_recall",
        }.get(self.task.scenario_type, "sku_recall")

    def _invalid_action_result(self, error: str) -> Dict[str, Any]:
        if self.step_count >= self.max_steps:
            return self._terminate_failure("invalid_action", -0.9, [error])
        return {
            **self._observation(latest_result={"status": "ERROR", "message": error}),
            "reward": -0.15,
            "reward_detail": {
                "reward_version": self.reward_version,
                "reward_type": "invalid_action",
                "reward_valid": True,
                "terminal_utility": -0.15,
                "termination_reason": "",
                "issues": [error],
            },
        }

    def _terminate_failure(
        self,
        reward_type: str,
        reward: float,
        issues: List[str],
    ) -> Dict[str, Any]:
        self.done = True
        return {
            **self._observation(),
            "done": True,
            "reward": reward,
            "reward_detail": {
                "reward_version": self.reward_version,
                "reward_type": reward_type,
                "reward_valid": True,
                "terminal_utility": reward,
                "termination_reason": reward_type,
                "issues": issues,
            },
        }

    def _observation(
        self,
        latest_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "instruction": self.task.query if self.task else "",
            "task_id": self.task.task_id if self.task else "",
            "site_code": self.task.site_code if self.task else "",
            "scenario_type": self.task.scenario_type if self.task else "",
            "tools": copy.deepcopy(SHOPPING_TOOLS_SCHEMA),
            "messages": copy.deepcopy(self.messages),
            "latest_result": copy.deepcopy(latest_result),
            "display_product_count": len(self._display_products()),
            "step": self.step_count,
            "max_steps": self.max_steps,
            "done": self.done,
        }

    def _trajectory(self, final: str) -> Dict[str, Any]:
        return {
            "trajectory_id": f"env_{self.task.task_id or 'task'}",
            "scenario_type": self.task.scenario_type,
            "user_query": self.task.query,
            "messages": copy.deepcopy(self.messages),
            "tools": copy.deepcopy(SHOPPING_TOOLS_SCHEMA),
            "final_response": final,
            "status": "done",
            "total_steps": len(self.tool_steps),
            "site_context": {"site_code": self.task.site_code},
        }

    def _display_products(self) -> List[Dict[str, Any]]:
        products: List[Dict[str, Any]] = []
        seen = set()
        for step in self.tool_steps:
            for product in step["result"].get("products", []):
                identity = str(
                    product.get("sku_id")
                    or product.get("product_id")
                    or product.get("sku_name")
                )
                if identity in seen:
                    continue
                seen.add(identity)
                products.append(product)
        return products

    def _require_active(self) -> None:
        if self.task is None:
            raise ShoppingEnvironmentStateError("reset must be called before step")
        if self.done:
            raise ShoppingEnvironmentStateError("environment is already done; call reset")

    @staticmethod
    def _coerce_task(
        task: ShoppingTask | Dict[str, Any] | str,
        site_code: Optional[str],
    ) -> ShoppingTask:
        if isinstance(task, ShoppingTask):
            return task
        if isinstance(task, str):
            query = task.strip()
            if not query:
                raise ValueError("task query must not be empty")
            return ShoppingTask(query=query, site_code=site_code or "UK-Site")
        if not isinstance(task, dict):
            raise TypeError("task must be ShoppingTask, dict, or string")
        query = str(task.get("query") or task.get("user_query") or "").strip()
        if not query:
            raise ValueError("task query must not be empty")
        return ShoppingTask(
            query=query,
            site_code=str(site_code or task.get("site_code") or "UK-Site"),
            scenario_type=str(task.get("scenario_type") or "search_recommend"),
            task_id=str(task.get("task_id") or task.get("sample_id") or ""),
        )

    @staticmethod
    def _normalize_action(
        action: Dict[str, Any] | str,
    ) -> Tuple[str, Dict[str, Any], Optional[str]]:
        if isinstance(action, str):
            stripped = action.strip()
            if not stripped:
                return "", {}, "action must not be empty"
            try:
                action = json.loads(stripped)
            except json.JSONDecodeError:
                return "final", {"content": stripped}, None
        if not isinstance(action, dict):
            return "", {}, "action must be a JSON object or final response string"

        action_type = str(action.get("type") or "")
        if action_type in {"final", "final_response"} or "content" in action:
            content = action.get("content")
            if not isinstance(content, str):
                return "", {}, "final action content must be a string"
            return "final", {"content": content}, None

        function = action.get("function") if isinstance(action.get("function"), dict) else {}
        name = action.get("name") or function.get("name")
        arguments = action.get("arguments", function.get("arguments", {}))
        if action_type not in {"", "tool", "tool_call", "function"}:
            return "", {}, f"unknown action type: {action_type}"
        if not isinstance(name, str) or not name:
            return "", {}, "tool action is missing name"
        if name not in VALID_TOOL_NAMES:
            return "", {}, f"unknown tool: {name}"
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                return "", {}, "tool arguments must be valid JSON"
        if not isinstance(arguments, dict):
            return "", {}, "tool arguments must be an object"
        return "tool", {"name": name, "arguments": arguments}, None
