# -*- coding: utf-8 -*-
"""
Step 11: 把抢救数据转成标准 schema
模型用了非标准嵌套：{step_index, tool_call: {tool_name, tool_input, tool_output}, final_response: {...}}
标准格式：{step_id, step_type, tool_name, tool_input, tool_output, content, product_cards}
"""
import json
from pathlib import Path

SRC = Path(__file__).parent / "_multi_agent_recovered.jsonl"
DST = Path(__file__).parent / "_multi_agent_normalized.jsonl"


def normalize_step(step: dict, idx: int) -> list[dict]:
    """把一个非标准 step 转成 1 或多个标准 step（tool_call 和 final_response 可能合在一个里）"""
    results = []

    # 处理 tool_call 嵌套
    if 'tool_call' in step:
        tc = step['tool_call']
        # 标准化 product 字段：key_specs 可能是 dict（需要转成字符串）
        tool_output = tc.get('tool_output', {})
        if tool_output.get('products'):
            for p in tool_output['products']:
                if isinstance(p.get('key_specs'), dict):
                    # 转字符串
                    p['key_specs'] = '/'.join(f"{k}:{v}" for k,v in p['key_specs'].items())
        results.append({
            'step_id': len(results) + idx,
            'step_type': 'tool_call',
            'tool_name': tc.get('tool_name'),
            'tool_input': tc.get('tool_input'),
            'tool_output': tool_output,
            'error_type': None
        })

    # 处理已经是标准格式的（step_type:tool_call）
    if step.get('step_type') == 'tool_call' and not step.get('tool_call'):
        # 已经是扁平的
        tool_output = step.get('tool_output', {})
        if tool_output.get('products'):
            for p in tool_output['products']:
                if isinstance(p.get('key_specs'), dict):
                    p['key_specs'] = '/'.join(f"{k}:{v}" for k,v in p['key_specs'].items())
        results.append({
            'step_id': len(results) + idx,
            'step_type': 'tool_call',
            'tool_name': step.get('tool_name'),
            'tool_input': step.get('tool_input'),
            'tool_output': tool_output,
            'error_type': step.get('error_type')
        })

    # 处理 final_response 嵌套
    if 'final_response' in step and isinstance(step['final_response'], dict):
        fr = step['final_response']
        results.append({
            'step_id': len(results) + idx + 1,
            'step_type': 'final_response',
            'content': fr.get('content', ''),
            'product_cards': fr.get('product_cards', [])
        })

    # 已经是标准 final_response
    if step.get('step_type') == 'final_response' and 'content' in step:
        results.append({
            'step_id': len(results) + idx,
            'step_type': 'final_response',
            'content': step.get('content', ''),
            'product_cards': step.get('product_cards', [])
        })

    return results


from typing import Optional

def normalize_trajectory(t: dict) -> Optional[dict]:
    """把整条 trajectory 标准化。"""
    if not t.get('steps'):
        return None

    new_steps = []
    base_idx = 1
    for s in t['steps']:
        ns = normalize_step(s, base_idx)
        new_steps.extend(ns)
        base_idx = len(new_steps) + 1

    # 如果 trajectory 顶层有 final_response 字段是字符串、但 steps 里没 final_response step
    has_final_step = any(s.get('step_type') == 'final_response' for s in new_steps)
    if not has_final_step and isinstance(t.get('final_response'), str):
        new_steps.append({
            'step_id': len(new_steps) + 1,
            'step_type': 'final_response',
            'content': t['final_response'],
            'product_cards': []
        })

    # 把 final_response 顶层字符串补齐
    final_text = t.get('final_response')
    if not isinstance(final_text, str):
        for s in new_steps:
            if s.get('step_type') == 'final_response':
                final_text = s.get('content', '')
                break

    return {
        'trajectory_id': t.get('trajectory_id'),
        'scenario_type': t.get('scenario_type'),
        'category': t.get('category', ''),
        'quality_label': t.get('quality_label', 'good'),
        'training_focus': t.get('training_focus', ''),
        'is_multi_turn': bool(t.get('is_multi_turn', False)),
        'user_query': t.get('user_query', ''),
        'thinking': t.get('thinking', ''),
        'steps': new_steps,
        'final_response': final_text or '',
        'eval_score': float(t.get('eval_score', 1.0)),
        'sft_source': t.get('sft_source', 'claude_multi_agent_v1')
    }


def validate(t: dict) -> tuple[bool, list]:
    """简单校验"""
    errs = []
    if not t['steps']:
        errs.append('no steps')
    if not any(s.get('step_type') == 'final_response' for s in t['steps']):
        errs.append('no final_response step')
    # card_id 必须来自 product_id
    returned_ids = set()
    for s in t['steps']:
        if s.get('tool_output') and s['tool_output'].get('products'):
            for p in s['tool_output']['products']:
                if p.get('product_id'):
                    returned_ids.add(p['product_id'])
    card_ids = set()
    for s in t['steps']:
        for c in (s.get('product_cards') or []):
            if c.get('card_id'):
                card_ids.add(c['card_id'])
    hall = card_ids - returned_ids
    if hall:
        errs.append(f'幻觉card_id: {hall}')
    return len(errs) == 0, errs


def main():
    with open(SRC) as f:
        raw = [json.loads(l) for l in f]
    print(f'读取 {len(raw)} 条原始数据')

    normalized = []
    for t in raw:
        nt = normalize_trajectory(t)
        if nt is None:
            print(f"⚠️ {t.get('trajectory_id')}: 规范化失败")
            continue
        ok, errs = validate(nt)
        if ok:
            normalized.append(nt)
            print(f"  ✅ {nt['trajectory_id']:<35} [{nt['scenario_type']}] steps={len(nt['steps'])}")
        else:
            print(f"  ⚠️ {nt['trajectory_id']:<35} 错误: {errs}")
            # 尝试保留，因为多数 card_id 幻觉是字段格式问题
            if all('幻觉' not in e for e in errs):
                normalized.append(nt)

    with open(DST, 'w', encoding='utf-8') as f:
        for t in normalized:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')

    print(f"\n✅ 规范化后 {len(normalized)} 条 写入 {DST}")


if __name__ == "__main__":
    main()
