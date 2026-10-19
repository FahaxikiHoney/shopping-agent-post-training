"""Tiny web dashboard for Joybuy RL rollout metrics."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

try:
    from .summarize_metrics import load_records, summarize
except ImportError:
    from joybuy_slime.summarize_metrics import load_records, summarize


class DashboardHandler(BaseHTTPRequestHandler):
    metrics_path = Path("slime_joybuy_rl/output/rollout_metrics.jsonl")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._html(_html())
            return
        if path == "/api/metrics":
            records = _safe_load(self.metrics_path)
            self._json({
                "summary": summarize(records, tail=200) if records else {},
                "records": records[-1000:],
            })
            return
        if path == "/health":
            self._json({"ok": True, "metrics_path": str(self.metrics_path)})
            return
        self.send_error(404)

    def _html(self, body: str, status: int = 200) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, data: Dict[str, Any], status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def _safe_load(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return load_records(path)


def _html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Joybuy RL Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { margin: 0; font-family: Inter, system-ui, -apple-system, Segoe UI, sans-serif; background: #f6f7f9; color: #172033; }
    header { padding: 18px 24px; background: #111827; color: white; display: flex; justify-content: space-between; align-items: center; }
    main { padding: 20px 24px 32px; }
    .grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; }
    .metric { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; }
    .label { font-size: 12px; color: #667085; }
    .value { font-size: 24px; font-weight: 700; margin-top: 8px; }
    .panel { margin-top: 16px; background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }
    .charts { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 8px 10px; border-bottom: 1px solid #edf0f3; text-align: left; vertical-align: top; }
    th { color: #475467; font-weight: 600; background: #fafafa; }
    .muted { color: #98a2b3; font-size: 13px; }
    @media (max-width: 980px) { .grid { grid-template-columns: repeat(2, 1fr); } .charts { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header>
    <strong>Joybuy RL Dashboard</strong>
    <span class="muted" id="updated">loading</span>
  </header>
  <main>
    <section class="grid" id="metrics"></section>
    <section class="charts">
      <div class="panel"><canvas id="rewardChart" height="120"></canvas></div>
      <div class="panel"><canvas id="typeChart" height="260"></canvas></div>
    </section>
    <section class="panel">
      <h3>Recent Rollouts</h3>
      <table>
        <thead><tr><th>Task</th><th>Reward</th><th>Type</th><th>Judge</th><th>Cards</th><th>Issues</th></tr></thead>
        <tbody id="rows"></tbody>
      </table>
    </section>
  </main>
  <script>
    let rewardChart, typeChart;
    const fmt = (v) => v === null || v === undefined ? "-" : String(v);
    function metric(label, value) {
      return `<div class="metric"><div class="label">${label}</div><div class="value">${fmt(value)}</div></div>`;
    }
    async function refresh() {
      const data = await fetch("/api/metrics").then(r => r.json());
      const s = data.summary || {};
      document.getElementById("updated").textContent = new Date().toLocaleString();
      document.getElementById("metrics").innerHTML = [
        metric("records", s.records || 0),
        metric("reward mean", s.reward_mean),
        metric("success rate", s.success_rate),
        metric("missing cards", s.missing_card_rate),
        metric("judge mean", s.judge_score_mean),
        metric("think rate", s.think_rate),
      ].join("");
      const records = data.records || [];
      const labels = records.map((_, i) => i + 1);
      const rewards = records.map(r => r.reward);
      const judge = records.map(r => r.judge_score);
      if (rewardChart) rewardChart.destroy();
      rewardChart = new Chart(document.getElementById("rewardChart"), {
        type: "line",
        data: { labels, datasets: [
          { label: "reward", data: rewards, borderColor: "#2563eb", pointRadius: 0, tension: 0.2 },
          { label: "judge", data: judge, borderColor: "#16a34a", pointRadius: 0, tension: 0.2 },
        ]},
        options: { responsive: true, scales: { y: { min: -1, max: 1 }}}
      });
      const typeCounts = s.reward_types || {};
      if (typeChart) typeChart.destroy();
      typeChart = new Chart(document.getElementById("typeChart"), {
        type: "doughnut",
        data: { labels: Object.keys(typeCounts), datasets: [{ data: Object.values(typeCounts) }] },
        options: { responsive: true }
      });
      document.getElementById("rows").innerHTML = records.slice(-80).reverse().map(r => `
        <tr>
          <td>${fmt(r.query).slice(0, 90)}</td>
          <td>${fmt(r.reward)}</td>
          <td>${fmt(r.reward_type)}</td>
          <td>${fmt(r.judge_score)}</td>
          <td>${fmt(r.card_count)}/${fmt(r.product_count)}</td>
          <td>${(r.issues || []).join("; ").slice(0, 160)}</td>
        </tr>`).join("");
    }
    refresh();
    setInterval(refresh, 10000);
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8792)
    parser.add_argument("--metrics-path", default="slime_joybuy_rl/output/rollout_metrics.jsonl")
    args = parser.parse_args()
    DashboardHandler.metrics_path = Path(args.metrics_path)
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Joybuy RL dashboard: http://{args.host}:{args.port}")
    print(f"Metrics path: {DashboardHandler.metrics_path}")
    server.serve_forever()


if __name__ == "__main__":
    main()
