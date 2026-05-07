#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回测进球数推荐(双选)的盈亏模拟：每个选项下注30，总投入60"""
import json, glob, sys

sys.path.insert(0, '.')
from v36_analyzer import analyze_match, _safe_float
from sporttery_web import _build_change_hitrate, _build_odds_hitrate

# 加载比分
with open('分析模板/_scores.json', 'r', encoding='utf-8') as f:
    scores_raw = json.load(f)

mid_map = {}
for k, v in scores_raw.items():
    mn = v.get('match_id', '')
    if mn and mn != 'test':
        mid_map[mn] = v
    dt = v.get('date', '')
    if dt and mn:
        mid_map[f'{dt}_{mn}'] = v

results = []
single_results = []

for fp in sorted(glob.glob('sporttery_data/*.json')):
    if 'full_' in fp:
        continue
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        continue
    
    preview = data.get('preview')
    if not preview:
        continue
    
    mi = data.get('match_info', {})
    match_id = data.get('match_id', '')
    match_num = mi.get('match_num_str', '')
    match_date = mi.get('match_date', '')
    
    score = mid_map.get(match_id) or mid_map.get(f'{match_date}_{match_num}')
    if not score:
        for k, v in mid_map.items():
            if match_num and match_num in k:
                score = v; break
    if not score:
        continue
    
    hs = score.get('home_score')
    ag = score.get('away_score')
    if hs is None or ag is None:
        continue
    
    actual_total = hs + ag
    tg = data.get('total_goals', {}) or {}
    
    try:
        data['_change_hitrate'] = _build_change_hitrate()
        data['_odds_hitrate'] = _build_odds_hitrate()
    except:
        continue
    
    try:
        result = analyze_match(data)
        fgp = result.get('final_goal_pick', {})
    except:
        continue
    
    single = fgp.get('single')
    double = fgp.get('double', [])
    dir_conflict = fgp.get('conflict', False)
    
    if not single or not double:
        continue
    
    # 双选盈亏：每选项30，总投入60
    double_win = 0
    double_hit_goal = None
    for g in double[:2]:  # 最多2个
        gk = f'{g}球'
        odds = _safe_float(tg.get(gk, 0))
        if odds == 0:
            continue
        if actual_total == g:
            double_win += 30 * odds
            double_hit_goal = g
    double_profit = double_win - 60
    
    # 单选项盈亏：投入60
    single_win = 0
    gk_s = f'{single}球'
    odds_s = _safe_float(tg.get(gk_s, 0))
    if actual_total == single and odds_s > 0:
        single_win = 60 * odds_s
        single_profit = single_win - 60
    else:
        single_profit = -60
    
    name = f'{mi.get("home_team","?")}vs{mi.get("away_team","?")}'
    
    results.append({
        'match_id': match_id,
        'name': name,
        'total': actual_total,
        'single': single,
        'double': double,
        'single_hit': actual_total == single,
        'double_hit': actual_total in double[:2],
        'double_profit': double_profit,
        'single_profit': single_profit,
        'conflict': dir_conflict,
    })

n = len(results)
if n == 0:
    print('No valid records!')
    sys.exit(1)

double_total_profit = sum(r['double_profit'] for r in results)
single_total_profit = sum(r['single_profit'] for r in results)
double_total_invest = n * 60
single_total_invest = n * 60

print(f'总场次: {n}')
print(f'总投入(双选): {double_total_invest:.0f}')
print(f'总投入(单选): {single_total_invest:.0f}')
print()

print(f'========= 双选（每选项30，总60）=========')
print(f'总盈亏: {double_total_profit:+.0f}')
print(f'回报率: {double_total_profit/double_total_invest*100:+.1f}%')
double_hit_count = sum(1 for r in results if r['double_hit'])
double_return = sum(r['double_profit'] for r in results if r['double_hit'])
print(f'命中场次: {double_hit_count}/{n} ({double_hit_count/n*100:.1f}%)')
print(f'命中时盈利合计: {double_return:+.0f}')
print()

print(f'========= 单选（全压单选，60）=========')
print(f'总盈亏: {single_total_profit:+.0f}')
print(f'回报率: {single_total_profit/single_total_invest*100:+.1f}%')
single_hit_count = sum(1 for r in results if r['single_hit'])
print(f'命中场次: {single_hit_count}/{n} ({single_hit_count/n*100:.1f}%)')
print()

# 排除方向冲突
no_conf = [r for r in results if not r['conflict']]
nc = len(no_conf)
if nc > 0:
    print(f'========= 排除方向冲突({nc}场) =========')
    dp = sum(r['double_profit'] for r in no_conf)
    sp = sum(r['single_profit'] for r in no_conf)
    print(f'双选盈亏: {dp:+.0f} ({dp/(nc*60)*100:+.1f}%)')
    print(f'单选盈亏: {sp:+.0f} ({sp/(nc*60)*100:+.1f}%)')
    print()

# 按单选球数分组
print(f'========= 按单选球数分组（双选）=========')
from collections import defaultdict
by_goal = defaultdict(list)
for r in results:
    by_goal[r['single']].append(r)
for g in sorted(by_goal.keys()):
    gr = by_goal[g]
    gn = len(gr)
    dp = sum(r['double_profit'] for r in gr)
    print(f'  {g}球({gn}场): 盈亏{dp:+.0f} 回报{dp/(gn*60)*100:+.1f}%')

# 大球/小球方向
print(f'\n========= 按Step0方向分组（双选）=========')
from v36_analyzer import _extract_recent_matches, _calc_att_def
by_dir = defaultdict(list)
for r in results:
    # need to re-extract direction... let me just check from the result
    pass
# Instead just use existing direction data

# Top 10 盈利和亏损
print(f'\n========= Top 10 盈利（双选）=========')
top_win = sorted(results, key=lambda x: -x['double_profit'])[:10]
for r in top_win:
    tag = '✅' if r['double_hit'] else '❌'
    print(f'  {tag} {r["name"]}: 实际{r["total"]}球 推荐{r["double"]} 盈亏{r["double_profit"]:+.0f}')

print(f'\n========= Top 10 亏损（双选）=========')
top_loss = sorted(results, key=lambda x: x['double_profit'])[:10]
for r in top_loss:
    tag = '✅' if r['double_hit'] else '❌'
    print(f'  {tag} {r["name"]}: 实际{r["total"]}球 推荐{r["double"]} 盈亏{r["double_profit"]:+.0f}')
