# -*- coding: utf-8 -*-
"""每个场景跑1条，打印完整轨迹并保存"""
import sys, json, time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from joybuy_agent.llm.client import LLMClient
from joybuy_agent.react.agent import ReActJoybuyAgent

OUTPUT = Path(__file__).parent / "trajectories_react_sample.jsonl"

SAMPLES = [
    ("search_recommend", "推荐一款主动降噪耳机，预算500元以内"),
    ("similar_rec",      "之前买的保温杯只保温5小时，换同价位但保温24小时的款"),
    ("repurchase",       "保温杯用了一年准备换新的，上次买的那款还是推荐吗"),
    ("bundle_purchase",  "帮我配齐居家办公的装备，椅子+台灯，总预算2000元"),
    ("matching",         "买了北欧风沙发，需要搭配茶几和落地灯"),
]

llm = LLMClient(model="DeepSeek-R1")
results = []

for sc, query in SAMPLES:
    print(f"\n{'='*60}")
    print(f"场景: {sc}")
    print(f"Query: {query}")
    print('='*60)

    agent = ReActJoybuyAgent(llm=llm, max_steps=5, scenario_type=sc)
    t0 = time.time()
    traj = agent.run(query)
    elapsed = time.time() - t0

    print(f"状态: {traj.status} | 步数: {traj.total_steps} | 耗时: {elapsed:.0f}s")
    print()

    # 打印完整对话
    for i, msg in enumerate(traj.messages):
        role = msg["role"]
        content = (msg.get("content") or "").strip()
        tool_calls = msg.get("tool_calls", [])

        if role == "system":
            print(f"[{i}] SYSTEM: {content[:60]}...")
        elif role == "user":
            print(f"[{i}] USER: {content}")
        elif role == "assistant":
            if content:
                # 分离 think 和正文
                if "<think>" in content:
                    think_part = content.split("</think>")[0].replace("<think>","").strip()
                    after_think = content.split("</think>")[-1].strip() if "</think>" in content else ""
                    print(f"[{i}] ASSISTANT <think>: {think_part[:150]}...")
                    if after_think:
                        print(f"      正文: {after_think[:100]}")
                else:
                    print(f"[{i}] ASSISTANT: {content[:200]}")
            if tool_calls:
                tc = tool_calls[0]["function"]
                print(f"      → {tc['name']}({tc['arguments'][:120]})")
        elif role == "tool":
            data = {}
            try: data = json.loads(content)
            except: pass
            prods = data.get("products", [])
            if prods:
                print(f"[{i}] TOOL: 返回{len(prods)}款商品")
                for p in prods[:3]:
                    print(
                        f"      - {p.get('sku_name', p.get('title',''))[:30]} "
                        f"¥{p.get('final_price', p.get('price',0))} {p.get('sales','')}"
                    )
            elif data.get("orders"):
                orders = data["orders"]
                print(f"[{i}] TOOL: 找到{len(orders)}条历史订单")
                for o in orders[:2]:
                    print(f"      - {o.get('title','')[:25]} {o.get('months_ago','?')}个月前购买")
            elif data.get("summary"):
                print(f"[{i}] TOOL: {data['summary']}")
            else:
                print(f"[{i}] TOOL: {content[:100]}")
        print()

    print(f"--- thinking ({len(traj.thinking)}字) ---")
    print(traj.thinking)
    print()
    print(f"--- final_response ({len(traj.final_response)}字) ---")
    print(traj.final_response[:600])

    # 保存
    d = traj.to_sft_dict()
    d["elapsed_seconds"] = round(elapsed, 1)
    results.append(d)

# 落盘
with open(OUTPUT, "w", encoding="utf-8") as f:
    for r in results:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"\n\n{'='*60}")
print(f"已保存 {len(results)} 条轨迹 → {OUTPUT}")
print(f"{'='*60}")
for r in results:
    steps = len([m for m in r["messages"] if m["role"] == "tool"])
    fr_len = len(r["final_response"])
    print(f"  {r['scenario_type']:<22} {steps}步  {fr_len}字  status={r['status']}")
