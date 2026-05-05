#!/usr/bin/env python3
"""V3.7 回测：对所有有比分赛果的比赛运行V3.7分析，统计命中率"""
import json, os, glob, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v36_analyzer import analyze_match

DATA_DIR = 'sporttery_data'
SCORES_FILE = '分析模板/_scores.json'

# Pre-compute hitrate caches
print('Loading hitrate caches...')
from sporttery_web import _build_change_hitrate, _build_odds_hitrate
change_hr = _build_change_hitrate()
odds_hr = _build_odds_hitrate()
ch_cnt = sum(len(v) for v in change_hr.values())
print(f'Change hitrate buckets: {ch_cnt}')
exact_keys = odds_hr.get('exact', {})
odds_cnt = sum(len(v) for v in exact_keys.values())
print(f'Odds hitrate entries: {odds_cnt}')

# Load scores
with open(SCORES_FILE, 'r', encoding='utf-8') as f:
    scores = json.load(f)

# Find all match data files with scores
files = sorted(glob.glob(os.path.join(DATA_DIR, '2039*.json')))
results = []

print(f'Total data files: {len(files)}')
print(f'Scores entries: {len(scores)}')

for f in files:
    mid = os.path.basename(f).replace('.json', '')
    
    # Find actual score
    actual = None
    if mid in scores:
        actual = scores[mid]
    if not actual:
        for k in scores:
            if mid in str(k):
                actual = scores[k]
                break
    if not actual:
        continue
    
    hs = actual.get('home_score')
    aws = actual.get('away_score')
    if hs is None or aws is None:
        continue
    
    try:
        hs = int(hs)
        aws = int(aws)
    except:
        continue
    
    # Load match data
    with open(f, 'r', encoding='utf-8') as ff:
        data = json.load(ff)
    
    # Inject hit rate caches
    data['_change_hitrate'] = change_hr
    data['_odds_hitrate'] = odds_hr
    
    # Run V3.7 analysis
    try:
        analysis = analyze_match(data)
    except Exception as e:
        results.append({'mid': mid, 'error': str(e)[:100], 'step0_conf': 'error'})
        continue
    
    actual_total = hs + aws
    actual_score = f'{hs}-{aws}'
    
    rec = analysis.get('recommended', {}) or {}
    step0 = analysis.get('step0', {})
    veto = analysis.get('veto')
    
    pred_goals = rec.get('goals', [])
    pred_direction = rec.get('direction', '?')
    pred_score = rec.get('top_score', '?')
    
    # Check direction
    actual_dir = '大球' if actual_total >= 3 else '小球'
    dir_correct = (pred_direction == actual_dir)
    
    # Check total goals
    goal_hit = actual_total in pred_goals if pred_goals else False
    
    # Check score
    score_hit = (pred_score == actual_score)
    
    results.append({
        'mid': mid,
        'league': analysis['match_info'].get('league', ''),
        'actual_total': actual_total,
        'actual_score': actual_score,
        'pred_direction': pred_direction,
        'pred_goals': pred_goals,
        'pred_score': pred_score,
        'dir_correct': dir_correct,
        'goal_hit': goal_hit,
        'score_hit': score_hit,
        'step0_dir': step0.get('direction', '?'),
        'step0_conf': step0.get('direction_conf', '?'),
        'vetoed': step0.get('vetoed', False),
        'kept_count': len(analysis['exclusion']['kept']),
        'excluded_count': len(analysis['exclusion']['excluded']),
    })

# ==================== Statistics ====================
total = len(results)
dir_correct_count = sum(1 for r in results if r.get('dir_correct'))
goal_hit_count = sum(1 for r in results if r.get('goal_hit'))
score_hit_count = sum(1 for r in results if r.get('score_hit'))

print(f'\n{"="*60}')
print(f'V3.6 回测报告 ({total} 场)')
print(f'{"="*60}')

print(f'\n【方向命中率】')
print(f'  方向正确: {dir_correct_count}/{total} = {dir_correct_count/total:.1%}')

print(f'\n【总进球命中率】')
print(f'  总进球命中: {goal_hit_count}/{total} = {goal_hit_count/total:.1%}')

print(f'\n【比分命中率】')
print(f'  比分命中: {score_hit_count}/{total} = {score_hit_count/total:.1%}')

# By direction confidence
print(f'\n【按方向类型分组】')
for dir_type in ['强', '中', '弱', '修正(否决)']:
    sub = [r for r in results if r['step0_conf'] == dir_type]
    if not sub: continue
    dc = sum(1 for r in sub if r['dir_correct'])
    gc = sum(1 for r in sub if r['goal_hit'])
    sc = sum(1 for r in sub if r['score_hit'])
    print(f'  {dir_type}: n={len(sub)} 方向={dc/len(sub):.1%} 总球={gc/len(sub):.1%} 比分={sc/len(sub):.1%}')

# By veto status
print(f'\n【否决对方向的影响】')
veto_subs = [r for r in results if r['vetoed']]
non_veto = [r for r in results if not r['vetoed']]
if veto_subs:
    vdc = sum(1 for r in veto_subs if r['dir_correct'])
    print(f'  否决触发: n={len(veto_subs)} 方向命中={vdc/len(veto_subs):.1%}')
if non_veto:
    ndc = sum(1 for r in non_veto if r['dir_correct'])
    print(f'  未否决: n={len(non_veto)} 方向命中={ndc/len(non_veto):.1%}')

# By actual total bracket
print(f'\n【按实际总进球分组】')
for lo, hi in [(0, 2), (3, 3), (4, 4), (5, 99)]:
    label = f'{lo}-{hi}球' if lo < hi else f'{lo}球'
    sub = [r for r in results if lo <= r['actual_total'] <= hi]
    if not sub: continue
    gh = sum(1 for r in sub if r['goal_hit'])
    sh = sum(1 for r in sub if r['score_hit'])
    print(f'  {label}: n={len(sub)} 总球命中={gh/len(sub):.1%} 比分命中={sh/len(sub):.1%}')

# Score analysis: where we succeed/fail
print(f'\n【比分命中详情】')
hits = [r for r in results if r['score_hit']]
misses = [r for r in results if not r['score_hit']]
if hits:
    top_hits = [r['actual_score'] + ' ' + r['mid'] for r in hits[:10]]
    print(f'  命中({len(hits)}): {top_hits}')
if misses:
    print(f'  未命中({len(misses)})例子:')
    for r in misses[:10]:
        print(f'    {r["mid"]}: 预测={r["pred_score"]}({r["pred_goals"]}球) 实际={r["actual_score"]}({r["actual_total"]}球)')

# Analysis of gaps
print(f'\n【命中率缺口分析】')
gc_rate = goal_hit_count / max(total, 1)
sc_rate = score_hit_count / max(total, 1)
dc_rate = dir_correct_count / max(total, 1)
print(f'  方向命中率: {dc_rate:.1%}')
print(f'  总球命中率: {gc_rate:.1%} (方向→总球衰减 to {gc_rate/max(dc_rate,0.01):.0f}%)')
print(f'  比分命中率: {sc_rate:.1%} (总球→比分衰减 to {sc_rate/max(gc_rate,0.01):.0f}%)')

# What actual scores are being missed?
print(f'\n【最常见未命中实际比分】')
from collections import Counter
miss_scores = Counter(r['actual_score'] for r in results if not r['score_hit'])
print(f'  TOP10: {miss_scores.most_common(10)}')

# Recommendations
print(f'\n{"="*60}')
print(f'改进建议')
print(f'{"="*60}')
print(f'1. 赔率命中率缺失 → 排除法过于宽松/严格')
print(f'2. 直接比分推荐准确度低 → 需要比分赔率数据')
print(f'3. 考虑增加: HAD赔率变化作为比分方向辅助')
print(f'4. 考虑增加: 比分赔率最低项作为候选加分')

# Save raw results
with open('v36_analysis_raw.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f'\nSaved {len(results)} results to v36_analysis_raw.json')
