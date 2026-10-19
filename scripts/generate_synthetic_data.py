#!/usr/bin/env python3
"""Generate deterministic synthetic shopping-agent SFT examples."""
import argparse
import json
import random
from pathlib import Path

SCENARIOS = [
    ("headphones", "通勤时想要一副轻便的无线耳机，预算 500 元。", "先比较佩戴、续航和降噪需求，再按预算筛选。"),
    ("desk_lamp", "请推荐适合小书桌的护眼台灯，最好能调亮度。", "先确认桌面空间和亮度调节，再比较尺寸与供电方式。"),
    ("travel_mug", "找一个适合带去办公室的保温杯，容量约 500 毫升。", "优先满足容量和便携，再比较杯盖密封与清洗便利性。"),
    ("keyboard", "需要一把安静的无线键盘，能连接两台设备。", "关键条件是低噪、无线和多设备切换，应逐项核对。"),
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/synthetic.jsonl")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    rows = []
    for i in range(args.count):
        key, query, rationale = rng.choice(SCENARIOS)
        rows.append({"id": f"synthetic-{i+1:04d}", "scenario": key,
                     "query": query, "rationale": rationale,
                     "response": f"我会按你的核心条件筛选{key}类商品，并优先比较规格、价格和售后信息。"})
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} synthetic rows to {path}")

if __name__ == "__main__":
    main()
