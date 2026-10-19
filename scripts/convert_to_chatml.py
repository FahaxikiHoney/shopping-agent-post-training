#!/usr/bin/env python3
"""Convert synthetic JSONL records to LlamaFactory ShareGPT messages."""
import argparse
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    rows = []
    with Path(args.input).open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            item = json.loads(line)
            for field in ("query", "rationale", "response"):
                if not isinstance(item.get(field), str):
                    raise ValueError(f"line {line_no}: missing string field {field}")
            rows.append({"messages": [
                {"role": "user", "content": item["query"]},
                {"role": "assistant", "content": f"<think>\n{item['rationale']}\n</think>\n\n{item['response']}"},
            ]})
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} examples to {out}")

if __name__ == "__main__":
    main()
