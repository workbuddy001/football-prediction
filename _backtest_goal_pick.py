#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回测进球数推荐(单选/双选)命中率"""
import json, glob, sys

sys.path.insert(0, '.')
from v36_analyzer import analyze_match
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

records = []
errors = 0
no_data = 0

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
    
    # 找比分
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
    
    # 注入命中率数据
    try:
        data['_change_hitrate'] = _build_change_hitrate()
        data['_odds_hitrate'] = _build_odds_hitrate()
    except:
        no_data += 1
        continue
    
    try:
        result = analyze_match(data)
        fgp = result.get('final_goal_pick', {})
        direction = result.get('step0', {}).get('direction', '?')
    except Exception as e:
        errors += 1
        continue
    
    if not fgp.get('single'):
        continue
    
    single = fgp['single']
    double = fgp.get('double', [])
    conflict = fgp.get('conflict', False)
    kept_goals = fgp.get('all_kept', [])
    
    single_hit = (actual_total == single)
    double_hit = (actual_total in double)
    
    records.append({
        'match_id': match_id,
        'home': mi.get('home_team', '?'),
        'away': mi.get('away_team', '?'),
        'hs': hs, 'ag': ag, 'total': actual_total,
        'direction': direction,
        'single': single,
        'double': double,
        'single_hit': single_hit,
        'double_hit': double_hit,
        'conflict': conflict,
        'kept': kept_goals,
    })

n = len(records)
if n == 0:
    print('No valid records!')
    sys.exit(1)

single_hits = sum(1 for r in records if r['single_hit'])
double_hits = sum(1 for r in records if r['double_hit'])
conflict_count = sum(1 for r in records if r['conflict'])
no_conflict = n - conflict_count

print(f'总有效场次: {n}')
print(f'方向冲突场次: {conflict_count} ({conflict_count/n*100:.1f}%)')
print()

print(f'=== 全部比赛 ===')
print(f'单选命中: {single_hits}/{n} = {single_hits/n*100:.1f}%')
print(f'双选命中: {double_hits}/{n} = {double_hits/n*100:.1f}%')
print()

print(f'=== 排除方向冲突 ===')
n_good = no_conflict
shg = sum(1 for r in records if not r['conflict'] and r['single_hit'])
dhg = sum(1 for r in records if not r['conflict'] and r['double_hit'])
print(f'单选命中: {shg}/{n_good} = {shg/n_good*100:.1f}%')
print(f'双选命中: {dhg}/{n_good} = {dhg/n_good*100:.1f}%')
print()

print(f'=== 仅方向冲突 ===')
n_bad = conflict_count
shb = sum(1 for r in records if r['conflict'] and r['single_hit'])
dhb = sum(1 for r in records if r['conflict'] and r['double_hit'])
print(f'单选命中: {shb}/{n_bad} = {shb/n_bad*100:.1f}%')
print(f'双选命中: {dhb}/{n_bad} = {dhb/n_bad*100:.1f}%')
print()

# 按单选球数分组
print(f'=== 按单选球数分组 ===')
from collections import Counter
by_goal = {}
for r in records:
    g = r['single']
    if g not in by_goal:
        by_goal[g] = {'n': 0, 'single_hit': 0, 'double_hit': 0}
    by_goal[g]['n'] += 1
    if r['single_hit']: by_goal[g]['single_hit'] += 1
    if r['double_hit']: by_goal[g]['double_hit'] += 1

for g in sorted(by_goal.keys()):
    d = by_goal[g]
    print(f'  {g}球: {d["n"]}场, 单选{d["single_hit"]}({d["single_hit"]/d["n"]*100:.0f}%), 双选{d["double_hit"]}({d["double_hit"]/d["n"]*100:.0f}%)')

# 方向组
print(f'\n=== 按方向分组 ===')
by_dir = {}
for r in records:
    d = r['direction']
    if d not in by_dir:
        by_dir[d] = {'n': 0, 'single_hit': 0, 'double_hit': 0}
    by_dir[d]['n'] += 1
    if r['single_hit']: by_dir[d]['single_hit'] += 1
    if r['double_hit']: by_dir[d]['double_hit'] += 1

for d in sorted(by_dir.keys()):
    dd = by_dir[d]
    print(f'  {d}: {dd["n"]}场, 单选{dd["single_hit"]}({dd["single_hit"]/dd["n"]*100:.0f}%), 双选{dd["double_hit"]}({dd["double_hit"]/dd["n"]*100:.0f}%)')

# 方向一致组（方向非模糊+无冲突）
print(f'\n=== 方向一致(非模糊+无冲突) ===')
aligned = [r for r in records if r['direction'] != '模糊' and not r['conflict']]
na = len(aligned)
if na > 0:
    sha = sum(1 for r in aligned if r['single_hit'])
    dha = sum(1 for r in aligned if r['double_hit'])
    print(f'  {na}场, 单选{sha}({sha/na*100:.0f}%), 双选{dha}({dha/na*100:.0f}%)')
    
    # 大球组
    big = [r for r in aligned if r['direction'] == '大球']
    if big:
        sb = sum(1 for r in big if r['single_hit'])
        db = sum(1 for r in big if r['double_hit'])
        print(f'  大球: {len(big)}场, 单选{sb}({sb/len(big)*100:.0f}%), 双选{db}({db/len(big)*100:.0f}%)')
    
    # 小球组
    small = [r for r in aligned if r['direction'] == '小球']
    if small:
        ss = sum(1 for r in small if r['single_hit'])
        ds = sum(1 for r in small if r['double_hit'])
        print(f'  小球: {len(small)}场, 单选{ss}({ss/len(small)*100:.0f}%), 双选{ds}({ds/len(small)*100:.0f}%)')

print(f'\n处理失败: {errors}, 无命中率数据: {no_data}')
