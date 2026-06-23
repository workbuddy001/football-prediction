#!/usr/bin/env python3
"""6月份比赛投注回测 V2（只投+1让球）"""
import json, os, sys
sys.path.insert(0, '.')
from verify_handicap_method_v5 import load_match_data, get_handicap_direction, apply_7step_method

with open('分析模板/_scores.json', 'r', encoding='utf-8') as f:
    scores = json.load(f)

# 找出6月比赛
june_matches = []
for key, s in scores.items():
    if not key.isdigit():
        continue
    hs, aw = s.get('home_score'), s.get('away_score')
    if hs is None or aw is None:
        continue
    fp = f'sporttery_data/{key}.json'
    if not os.path.exists(fp):
        continue
    with open(fp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    ft = data.get('fetch_time', '')
    if ft.startswith('2026-06'):
        # ✅ 只保留+1让球的比赛
        hhad = data.get('hhad', {})
        handicap = hhad.get('让球', '')
        if handicap == '+1':
            june_matches.append((key, int(hs), int(aw)))

print(f"找到 {len(june_matches)} 场6月份+1让球有比分的比赛")
print("=" * 80)

results = []
skipped = 0
for mid, hs, aw in june_matches:
    md = load_match_data(mid)
    if not md:
        skipped += 1
        continue
    
    hhad = md.get('hhad', {})
    handicap = hhad.get('让球', '')
    if not handicap:
        skipped += 1
        continue
    
    ad = get_handicap_direction(hs, aw, handicap)
    if not ad:
        skipped += 1
        continue
    
    pred, pred_score, top3_scores, reasons = apply_7step_method(md)
    if not pred:
        skipped += 1
        continue
    
    direction_ok = (pred == ad)
    
    # 赔率权重分配
    match_investment = 0
    match_return = 0
    top3_hit = False
    
    if top3_scores:
        inv_odds = [1.0/max(o, 1.1) for _, _, o in top3_scores[:3]]
        total_w = sum(inv_odds)
        for idx, (h, a, o) in enumerate(top3_scores[:3]):
            stake = (inv_odds[idx] / total_w) * 30
            match_investment += stake
            if h == hs and a == aw:
                top3_hit = True
                match_return = o * stake
                break
    
    results.append({
        'match_id': mid,
        'handicap': handicap,
        'prediction': pred,
        'actual': ad,
        'actual_score': f'{hs}:{aw}',
        'pred_score': f'{pred_score[0]}:{pred_score[1]}' if pred_score else '-',
        'top3': ', '.join(f'{h}:{a}({o})' for h, a, o in (top3_scores or [])),
        'direction_correct': direction_ok,
        'top3_hit': top3_hit,
        'invest': round(match_investment, 2),
        'return': round(match_return, 2),
    })

total = len(results)
dir_correct = sum(1 for r in results if r['direction_correct'])
top3_hit = sum(1 for r in results if r['top3_hit'])
total_inv = sum(r['invest'] for r in results)
total_ret = sum(r['return'] for r in results)
roi = (total_ret - total_inv) / total_inv * 100 if total_inv > 0 else 0

print(f"\n跳过：{skipped}场")
print("=" * 80)
print(f"【6月份+1让球回测】共{total}场")
print(f"方向准确率：{dir_correct}/{total} = {dir_correct/total*100:.1f}%")
print(f"前3命中率：{top3_hit}/{total} = {top3_hit/total*100:.1f}%")
print(f"总投注：{total_inv:.0f}元")
print(f"总回报：{total_ret:.0f}元")
print(f"💰 ROI：{roi:+.1f}%")
print("=" * 80)

hit_results = [r for r in results if r['top3_hit']]
miss_results = [r for r in results if not r['top3_hit']]
hit_inv = sum(r['invest'] for r in hit_results)
hit_ret = sum(r['return'] for r in hit_results)
miss_inv = sum(r['invest'] for r in miss_results)

print(f"\n命中：{len(hit_results)}场（投{hit_inv:.0f}元，回{hit_ret:.0f}元，回报率{hit_ret/hit_inv*100:.0f}%）")
print(f"亏损：{len(miss_results)}场（投{miss_inv:.0f}元，全亏）")

print("\n逐场详情：")
for i, r in enumerate(results, 1):
    ds = "✅" if r['direction_correct'] else "❌"
    ts = "✅" if r['top3_hit'] else "❌"
    pl = r['return'] - r['invest']
    print(f"{i:2d}. {r['match_id']} 实际{r['actual_score']} | 方向{ds} 前3{ts} | "
          f"预测{r['pred_score']} | 候选[{r['top3']}] | {r['invest']:.0f}→{r['return']:.0f}元 {pl:+.0f}元")

outfile = 'june_results_v2.json'
with open(outfile, 'w', encoding='utf-8') as f:
    json.dump({'total': total, 'dir_correct': dir_correct, 'top3_hit': top3_hit,
               'total_investment': round(total_inv, 2), 'total_return': round(total_ret, 2),
               'roi': round(roi, 1), 'results': results}, f, ensure_ascii=False, indent=2)
print(f"\n详细结果已保存到：{outfile}")
