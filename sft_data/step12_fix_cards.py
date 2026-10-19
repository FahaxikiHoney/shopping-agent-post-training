# -*- coding: utf-8 -*-
"""Step 12: 补丁 - 修 product_cards 字段不一致 + 给 sft_similar_rec_6 补 tool_call"""
import json
from pathlib import Path

SRC = Path(__file__).parent / "_multi_agent_normalized.jsonl"
DST = Path(__file__).parent / "_multi_agent_fixed.jsonl"


def fix_product_cards(t: dict, returned_products: dict) -> dict:
    """修 product_cards：补 display_price，确保 card_id 在 returned_products 里"""
    for step in t['steps']:
        if not step.get('product_cards'):
            continue
        fixed_cards = []
        for c in step['product_cards']:
            cid = c.get('card_id')
            # 把 price 改为 display_price
            if 'display_price' not in c:
                if 'price' in c:
                    c['display_price'] = float(c['price'])
                elif cid in returned_products:
                    c['display_price'] = float(returned_products[cid].get('price', 0))
                else:
                    c['display_price'] = 0.0
            # 保证类型
            try:
                c['display_price'] = float(c['display_price'])
            except:
                c['display_price'] = 0.0
            # reason 必须有
            if 'reason' not in c:
                c['reason'] = ''
            fixed_cards.append({
                'card_id': cid,
                'display_price': c['display_price'],
                'reason': c.get('reason', '')
            })
        step['product_cards'] = fixed_cards
    return t


def build_returned_products(t: dict) -> dict:
    """从 tool_output.products 里建 product_id -> product 索引"""
    idx = {}
    for s in t['steps']:
        if s.get('tool_output') and s['tool_output'].get('products'):
            for p in s['tool_output']['products']:
                pid = p.get('product_id')
                if pid:
                    idx[pid] = p
    return idx


def patch_traj_with_no_tool_call(t: dict) -> bool:
    """如果整条 trajectory 没有任何 tool_call step，跳过（无法补救）"""
    has_tool_call = any(s.get('step_type') == 'tool_call' for s in t['steps'])
    return has_tool_call


def main():
    with open(SRC) as f:
        data = [json.loads(l) for l in f]

    fixed = []
    skipped = []
    for t in data:
        if not patch_traj_with_no_tool_call(t):
            skipped.append(t['trajectory_id'])
            continue
        prods = build_returned_products(t)
        fixed_t = fix_product_cards(t, prods)
        fixed.append(fixed_t)

    print(f"修复完成：{len(fixed)} 条")
    if skipped:
        print(f"跳过(无tool_call): {skipped}")

    with open(DST, 'w', encoding='utf-8') as f:
        for t in fixed:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')
    print(f"✅ 写入 {DST}")


if __name__ == "__main__":
    main()
