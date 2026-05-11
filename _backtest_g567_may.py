#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G5/G6/G7 规则 5月回测"""
import json, os, sys, traceback

# 强制重新导入避免缓存
for m in list(sys.modules):
    if 'v36_analyzer' in m:
        del sys.modules[m]

from v36_analyzer import analyze_match
from sporttery_web import _build_change_hitrate, _build_odds_hitrate

# 预加载命中率数据
_odds_hr = _build_odds_hitrate()
_change_hr = _build_change_hitrate()

SCORES_FILE = '分析模板/_scores.json'
DATA_DIR = 'sporttery_data'

def _safe_float(v, default=999.0):
    try: return float(v)
    except: return default

# 加载比分
with open(SCORES_FILE, 'r', encoding='utf-8') as f:
    all_scores = json.load(f)

# 筛选5月比赛
may_matches = {}
for k, v in all_scores.items():
    rt = str(v.get('record_time', ''))
    if '2026-05' in rt:
        may_matches[k] = v

print(f'5月比赛共 {len(may_matches)} 场')
print('=' * 80)

results = {'G5': [], 'G6': [], 'G7': []}
skipped = 0
errors = 0

for match_id, score_record in may_matches.items():
    filepath = os.path.join(DATA_DIR, f'{match_id}.json')
    if not os.path.exists(filepath):
        skipped += 1
        continue
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        errors += 1
        continue
    
    # 获取实际比分
    actual_home = score_record.get('home_score', 0)
    actual_away = score_record.get('away_score', 0)
    actual_total = actual_home + actual_away
    
    # 运行V3.6分析
    try:
        # 注入命中率数据（v36_analyzer需要）
        data['_odds_hitrate'] = _odds_hr
        data['_change_hitrate'] = _change_hr
        analysis = analyze_match(data)
    except Exception as e:
        errors += 1
        continue
    
    # 提取0球赔率
    tg = data.get('total_goals', {}) or {}
    g0 = _safe_float(tg.get('0球', 0))
    
    # 提取三维排除结果
    exclusion = analysis.get('exclusion', {})
    kept = exclusion.get('kept', [])
    
    # 构建状态映射: {goal_num: status}
    status_map = {}
    for item in kept:
        goal_str = item.get('goal', '')
        try:
            g_num = int(goal_str.replace('球', ''))
        except:
            continue
        status_map[g_num] = item.get('status', '?')
    
    # --- G5: 5球=⚠️警惕造热 + o0>=12 ---
    if status_map.get(5) == '⚠️警惕造热' and g0 >= 12:
        hit = (actual_total == 5)
        results['G5'].append({
            'match_id': match_id,
            'home': score_record.get('home_team', '?'),
            'away': score_record.get('away_team', '?'),
            'score': f'{actual_home}:{actual_away}',
            'total': actual_total,
            'hit': hit,
            'g0': g0,
        })
    
    # --- G6: 6球=✅保留 + o0>=12 ---
    if status_map.get(6) == '✅保留' and g0 >= 12:
        hit = (actual_total == 6)
        results['G6'].append({
            'match_id': match_id,
            'home': score_record.get('home_team', '?'),
            'away': score_record.get('away_team', '?'),
            'score': f'{actual_home}:{actual_away}',
            'total': actual_total,
            'hit': hit,
            'g0': g0,
        })
    
    # --- G7: 7球=✅观察保留或⚠️警惕造热 + o0>=12 ---
    if status_map.get(7) in ('✅观察保留', '⚠️警惕造热') and g0 >= 12:
        hit = (actual_total == 7)
        results['G7'].append({
            'match_id': match_id,
            'home': score_record.get('home_team', '?'),
            'away': score_record.get('away_team', '?'),
            'score': f'{actual_home}:{actual_away}',
            'total': actual_total,
            'hit': hit,
            'g0': g0,
        })

# 输出结果
for rule_name in ['G5', 'G6', 'G7']:
    matches = results[rule_name]
    n = len(matches)
    hits = sum(1 for m in matches if m['hit'])
    hr = hits / n * 100 if n > 0 else 0
    
    print(f'\n### {rule_name} ({n}场触发, 命中{n}场 = {hr:.1f}%) ###')
    if n == 0:
        print('  无触发场次')
        continue
    
    roi_desc = []
    for m in matches:
        tag = '✅命中' if m['hit'] else '❌不中'
        roi_desc.append(f"  {m['match_id']} {tag} {m['home']} {m['score']} {m['away']} (总{m['total']}球, o0={m['g0']})")
    print('\n'.join(roi_desc))

# 汇总
print('\n' + '=' * 80)
print('汇总:')
for rule_name in ['G5', 'G6', 'G7']:
    matches = results[rule_name]
    n = len(matches)
    hits = sum(1 for m in matches if m['hit'])
    hr = hits / n * 100 if n > 0 else 0
    roi = (hits * 30 * 4.0 - n * 30) / (n * 30) * 100 if n > 0 else 0  # 假设5球赔率4.0
    print(f'  {rule_name}: {n}场 命中{hits}场 ({hr:.1f}%)')
    
print(f'\n跳过(无数据文件): {skipped}场')
print(f'分析错误: {errors}场')
