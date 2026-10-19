# -*- coding: utf-8 -*-
"""
从 workflow transcript 抢救数据
workflow 整体 stall 失败，但有 32 个子 agent 实际产出了 trajectory 数据
我们直接读 .jsonl transcript，提取 assistant 输出里的 trajectories
"""
import json
import re
from pathlib import Path

TRANSCRIPT_DIR = Path("data/transcripts")
OUTPUT = Path(__file__).parent / "_multi_agent_recovered.jsonl"


def extract_trajectories_from_transcript(jsonl_path: Path) -> list[dict]:
    """从单个 agent transcript 里抽出 trajectories 数组。
    Transcript 格式：每行 {"type": "user"|"assistant", "message": {"role":..., "content":...}}
    """
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except:
                    continue
                # 只看 assistant 消息
                if rec.get('type') != 'assistant':
                    continue
                msg = rec.get('message', {})
                content = msg.get('content', '')

                texts = []
                if isinstance(content, list):
                    for c in content:
                        if not isinstance(c, dict):
                            continue
                        ctype = c.get('type')
                        if ctype == 'text':
                            texts.append(c.get('text', ''))
                        elif ctype == 'tool_use':
                            # StructuredOutput 工具的 input 里可能直接有 trajectories
                            tname = c.get('name', '')
                            inp = c.get('input', {})
                            if isinstance(inp, dict) and 'trajectories' in inp:
                                return inp['trajectories']
                            # 也可能 input.trajectories 直接是数组
                            if 'trajectories' in str(inp):
                                # 把 input 转 json 找
                                try:
                                    inp_str = json.dumps(inp)
                                    m = re.search(r'"trajectories"\s*:\s*(\[.*\])', inp_str, re.DOTALL)
                                    if m:
                                        return json.loads(m.group(1))
                                except:
                                    pass
                elif isinstance(content, str):
                    texts.append(content)

                full = ' '.join(texts)
                if '"trajectories"' in full or "'trajectories'" in full:
                    # 找最外层 JSON 对象
                    try:
                        # 简单粗暴：找 { 开始，匹配大括号
                        start = full.find('{"trajectories"')
                        if start == -1:
                            start = full.find('{\n  "trajectories"')
                        if start == -1:
                            continue
                        # 用 json 解析器逐步扩展
                        depth = 0
                        end = start
                        for i in range(start, len(full)):
                            if full[i] == '{':
                                depth += 1
                            elif full[i] == '}':
                                depth -= 1
                                if depth == 0:
                                    end = i + 1
                                    break
                        try:
                            data = json.loads(full[start:end])
                            return data.get('trajectories', [])
                        except:
                            pass
                    except:
                        pass
    except Exception as e:
        pass
    return []


def main():
    all_files = sorted(TRANSCRIPT_DIR.glob("*.jsonl"))
    print(f"扫描 {len(all_files)} 个 transcript...")

    recovered = []
    success_files = 0
    for f in all_files:
        trajs = extract_trajectories_from_transcript(f)
        if trajs:
            success_files += 1
            for t in trajs:
                # 校验基本字段
                if not isinstance(t, dict): continue
                if not t.get('trajectory_id'): continue
                if not t.get('user_query'): continue
                if not t.get('steps') or len(t['steps']) < 2: continue
                if not t.get('final_response'): continue

                # 检查 card_id 是否都来自工具返回
                returned_ids = set()
                card_ids = set()
                for step in t['steps']:
                    if step.get('tool_output') and step['tool_output'].get('products'):
                        for p in step['tool_output']['products']:
                            if p.get('product_id'):
                                returned_ids.add(p['product_id'])
                    for card in (step.get('product_cards') or []):
                        if card.get('card_id'):
                            card_ids.add(card['card_id'])
                hallucinated = card_ids - returned_ids
                if hallucinated:
                    print(f"  ⚠️ {t['trajectory_id']}: 幻觉卡片 {hallucinated}，跳过")
                    continue

                # 加 sft_source 标记
                t['sft_source'] = 'claude_multi_agent_v1_recovered'
                recovered.append(t)

    print(f"\n📊 抢救结果:")
    print(f"  扫描的 transcript: {len(all_files)} 个")
    print(f"  含有效数据的 transcript: {success_files} 个")
    print(f"  抢救出的有效轨迹: {len(recovered)} 条")

    # 按场景分布
    from collections import Counter
    sc_dist = Counter(t.get('scenario_type', '?') for t in recovered)
    print(f"\n📊 场景分布:")
    for sc, n in sc_dist.most_common():
        print(f"  {sc:<22}: {n}")

    # 去重（按 trajectory_id）
    seen = set()
    unique = []
    for t in recovered:
        if t['trajectory_id'] not in seen:
            seen.add(t['trajectory_id'])
            unique.append(t)
    print(f"\n去重后: {len(unique)} 条")

    # 写入
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        for t in unique:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')
    print(f"\n✅ 已写入 {OUTPUT}")


if __name__ == "__main__":
    main()
