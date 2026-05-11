#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G5/G6/G7 回测 + 总进球保护（target-1球 10元）"""
import json, os, sys

for m in list(sys.modules):
    if 'v36_analyzer' in m:
        del sys.modules[m]

from v36_analyzer import analyze_match
from sporttery_web import _build_change_hitrate, _build_odds_hitrate

_odds_hr = _build_odds_hitrate()
_change_hr = _build_change_hitrate()

SCORES_FILE = '分析模板/_scores.json'
DATA_DIR = 'sporttery_data'

def _safe_float(v, default=999.0):
    try: return float(v)
    except: return default

with open(SCORES_FILE, 'r', encoding='utf-8') as f:
    all_scores = json.load(f)

may_matches = {k:v for k,v in all_scores.items() if '2026-05' in str(v.get('record_time',''))}

triggers = {'G5': [], 'G6': [], 'G7': []}

for match_id, score_record in may_matches.items():
    filepath = os.path.join(DATA_DIR, f'{match_id}.json')
    if not os.path.exists(filepath):
        continue
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        continue
    
    actual_home = score_record.get('home_score', 0)
    actual_away = score_record.get('away_score', 0)
    actual_total = actual_home + actual_away
    
    data['_odds_hitrate'] = _odds_hr
    data['_change_hitrate'] = _change_hr
    try:
        analysis = analyze_match(data)
    except:
        continue
    
    tg = data.get('total_goals', {}) or {}
    g0 = _safe_float(tg.get('0球', 0))
    
    exclusion = analysis.get('exclusion', {})
    kept = exclusion.get('kept', [])
    
    status_map = {}
    for item in kept:
        try:
            g_num = int(item.get('goal', '').replace('球', ''))
            status_map[g_num] = item.get('status', '?')
        except:
            pass
    
    def add_trigger(rule, main_goals, prot_goals):
        triggers[rule].append({
            'match_id': match_id,
            'home': score_record.get('home_team', '?'),
            'away': score_record.get('away_team', '?'),
            'score': f'{actual_home}:{actual_away}',
            'total': actual_total,
            'main_goals': main_goals,
            'prot_goals': prot_goals,
            'g0': g0,
            'main_odds': _safe_float(tg.get(f'{main_goals}球', 0)),
            'prot_odds': _safe_float(tg.get(f'{prot_goals}球', 0)),
        })
    
    if status_map.get(5) == '⚠️警惕造热' and g0 >= 12:
        add_trigger('G5', 5, 4)
    if status_map.get(6) == '✅保留' and g0 >= 12:
        add_trigger('G6', 6, 5)
    if status_map.get(7) in ('✅观察保留', '⚠️警惕造热') and g0 >= 12:
        add_trigger('G7', 7, 6)

STAKE_MAIN = 30
STAKE_PROTECT = 10

for rule_name in ['G5', 'G6', 'G7']:
    matches = triggers[rule_name]
    if not matches:
        continue
    
    n = len(matches)
    
    # 无保护
    raw_invest = n * STAKE_MAIN
    raw_return = sum(STAKE_MAIN * m['main_odds'] for m in matches if m['total'] == m['main_goals'])
    raw_roi = (raw_return - raw_invest) / raw_invest * 100
    
    # 有保护
    prot_invest = n * (STAKE_MAIN + STAKE_PROTECT)
    prot_return = 0
    hit_main = 0
    hit_protect = 0
    
    goal_map = {'G5':(5,4), 'G6':(6,5), 'G7':(7,6)}
    mg, pg = goal_map[rule_name]
    print(f'\n{"="*80}')
    print(f'### {rule_name} (主投{mg}球30元 + {pg}球10元 = 40元/场) ###')
    
    for m in matches:
        ret = 0
        tags = []
        
        if m['total'] == m['main_goals']:
            ret += STAKE_MAIN * m['main_odds']
            hit_main += 1
            tags.append('主中')
        elif m['total'] == m['prot_goals']:
            ret += STAKE_PROTECT * m['prot_odds']
            hit_protect += 1
            tags.append('保护中')
        else:
            tags.append('全丢')
        
        prot_return += ret
        
        tag = '✅' if ret > 0 else '❌'
        print(f'  {tag} {m["home"]} {m["score"]} {m["away"]} (总{m["total"]}球, o0={m["g0"]})')
        print(f'     主{m["main_goals"]}球赔{m["main_odds"]} | 保护{m["prot_goals"]}球赔{m["prot_odds"]} → {" ".join(tags)}')
    
    prot_roi = (prot_return - prot_invest) / prot_invest * 100
    diff = prot_roi - raw_roi
    
    print(f'\n  无保护: {raw_invest}元→{raw_return:.0f}元 | ROI={raw_roi:+.1f}%')
    print(f'  有保护: {prot_invest}元→{prot_return:.0f}元 | ROI={prot_roi:+.1f}%')
    print(f'  主中{hit_main}/{n} | 保护中{hit_protect}/{n} | 差值{diff:+.1f}%')

# 汇总
print(f'\n{"="*80}')
print(f'{"规则":<6} {"场":<4} {"主中":<4} {"护中":<4} {"无保护ROI":<12} {"有保护ROI":<12} {"差值":<10}')
for rule_name in ['G5', 'G6', 'G7']:
    matches = triggers[rule_name]
    if not matches:
        continue
    n = len(matches)
    raw_invest = n * STAKE_MAIN
    raw_return = sum(STAKE_MAIN * m['main_odds'] for m in matches if m['total'] == m['main_goals'])
    raw_roi = (raw_return - raw_invest) / raw_invest * 100
    
    prot_invest = n * (STAKE_MAIN + STAKE_PROTECT)
    prot_return = 0
    hit_main = 0
    hit_protect = 0
    for m in matches:
        if m['total'] == m['main_goals']:
            prot_return += STAKE_MAIN * m['main_odds']
            hit_main += 1
        elif m['total'] == m['prot_goals']:
            prot_return += STAKE_PROTECT * m['prot_odds']
            hit_protect += 1
    
    prot_roi = (prot_return - prot_invest) / prot_invest * 100
    print(f'{rule_name:<6} {n:<4} {hit_main:<4} {hit_protect:<4} {raw_roi:+.1f}%{"":<7} {prot_roi:+.1f}%{"":<7} {prot_roi-raw_roi:+.1f}%')
