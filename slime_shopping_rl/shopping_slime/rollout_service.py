"""Small HTTP reward service for local Slime/Shopping smoke tests."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict

try:
    from .reward_adapter import evaluate_completion
    from .metrics_logger import log_rollout_metric
except ImportError:
    from shopping_slime.reward_adapter import evaluate_completion
    from shopping_slime.metrics_logger import log_rollout_metric


class Handler(BaseHTTPRequestHandler):
    max_steps = 5
    tool_cost = 0.01
    use_llm_judge = False

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"ok": True})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/score":
            self.send_error(404)
            return
        try:
            request = self._read_json()
            task = request.get("task") or request.get("metadata") or request.get("prompt") or ""
            completion = str(request.get("completion") or request.get("response") or "")
            result = evaluate_completion(
                task,
                completion,
                max_steps=self.max_steps,
                tool_cost=self.tool_cost,
            )
            if isinstance(task, dict):
                log_rollout_metric(task, completion, result)
            self._json(result)
        except Exception as exc:
            self._json({"reward": -1.0, "error": str(exc)}, status=500)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        data = json.loads(raw.decode("utf-8")) if raw else {}
        if not isinstance(data, dict):
            raise ValueError("request body must be a JSON object")
        return data

    def _json(self, payload: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8791)
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--tool-cost", type=float, default=0.01)
    parser.add_argument("--use-llm-judge", action="store_true")
    args = parser.parse_args()

    Handler.max_steps = args.max_steps
    Handler.tool_cost = args.tool_cost
    if args.use_llm_judge:
        import os

        os.environ["USE_LLM_JUDGE"] = "1"
        Handler.use_llm_judge = True
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Shopping reward service listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
