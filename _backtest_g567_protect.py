#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G5/G6/G7 规则 5月回测 + 比分保护"""
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

def pick_protection_scores(score_odds, target_goals, count=2):
    """从比分赔率中挑count个最可能的目标进球数比分（赔率最低的）"""
    candidates = []
    for key, odds_val in score_odds.items():
        if ':' not in key and '-' not in key:
            continue
        sep = ':' if ':' in key else '-'
        parts = key.split(sep)
        try:
            h = int(parts[0])
            a = int(parts[1])
        except:
            continue
        total = h + a
        if total == target_goals:
            odds = _safe_float(odds_val)
            if odds < 900:
                candidates.append((key, odds, h, a))
    # 按赔率从低到高排序（低赔=更可能），取前count个
    candidates.sort(key=lambda x: x[1])
    return candidates[:count]

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

# 收集触发场次
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
    
    score_odds = data.get('score_odds', {}) or {}
    
    def add_trigger(rule, bet_goals, protect_goals):
        triggers[rule].append({
            'match_id': match_id,
            'home': score_record.get('home_team', '?'),
            'away': score_record.get('away_team', '?'),
            'score': f'{actual_home}:{actual_away}',
            'total': actual_total,
            'bet_goals': bet_goals,
            'g0': g0,
            'goal_odds': _safe_float(tg.get(f'{bet_goals}球', 0)),
            'protect_scores': pick_protection_scores(score_odds, protect_goals),
        })
    
    if status_map.get(5) == '⚠️警惕造热' and g0 >= 12:
        add_trigger('G5', 5, 4)
    if status_map.get(6) == '✅保留' and g0 >= 12:
        add_trigger('G6', 6, 5)
    if status_map.get(7) in ('✅观察保留', '⚠️警惕造热') and g0 >= 12:
        add_trigger('G7', 7, 6)

# 计算ROI
STAKE_MAIN = 30
STAKE_PROTECT = 10

for rule_name in ['G5', 'G6', 'G7']:
    matches = triggers[rule_name]
    if not matches:
        print(f'\n### {rule_name}: 无触发 ###')
        continue
    
    n = len(matches)
    total_invest = 0
    total_return_main = 0
    total_return_protect = 0
    hit_main = 0
    hit_protect = 0
    
    print(f'\n{"="*80}')
    print(f'### {rule_name} (主投注30元 + 2×比分保护各10元 = 50元/场) ###')
    
    for m in matches:
        invest = STAKE_MAIN + len(m['protect_scores']) * STAKE_PROTECT
        total_invest += invest
        return_val = 0
        
        actual_score_key = f"{m['score'].replace(':', ':')}"
        
        # 主投注
        main_hit = (m['total'] == m['bet_goals'])
        if main_hit:
            return_val += STAKE_MAIN * m['goal_odds']
            hit_main += 1
        
        # 比分保护
        prot_hit = False
        prot_hit_score = ''
        for skey, odds, h, a in m['protect_scores']:
            if f'{actual_home}:{actual_away}' == skey.replace('-', ':'):
                return_val += STAKE_PROTECT * odds
                hit_protect += 1
                prot_hit = True
                prot_hit_score = f'{h}:{a}'
                break
        
        total_return_main += return_val
        
        tag = '✅主中' if main_hit else ('🛡️保护中' if prot_hit else '❌')
        detail = f'{tag} {m["home"]} {m["score"]} {m["away"]} (总{m["total"]}球, o0={m["g0"]})'
        detail += f'\n    主投{m["bet_goals"]}球赔{m["goal_odds"]}, '
        detail += f'保护{",".join([f"{s}(赔{o})" for s,o,_,_ in m["protect_scores"]])}'
        if prot_hit:
            detail += f' → {prot_hit_score}命中!'
        print(f'  {detail}')
    
    roi = (total_return_main - total_invest) / total_invest * 100
    print(f'\n  投入{total_invest}元, 回报{total_return_main:.0f}元, ROI={roi:+.1f}%')
    print(f'  主投命中: {hit_main}/{n} | 保护命中: {hit_protect}/{n}')
    
    # 无保护对比
    roi_no_protect = (hit_main * STAKE_MAIN * sum(m['goal_odds'] for m in matches if m['total']==m['bet_goals'])/max(hit_main,1) - n*STAKE_MAIN) / (n*STAKE_MAIN) * 100 if hit_main > 0 else -100
    
    # 更准确的无保护计算
    main_only_invest = n * STAKE_MAIN
    main_only_return = sum(STAKE_MAIN * m['goal_odds'] for m in matches if m['total'] == m['bet_goals'])
    main_only_roi = (main_only_return - main_only_invest) / main_only_invest * 100
    print(f'  对比无保护: 投入{main_only_invest}元 → {main_only_return:.0f}元, ROI={main_only_roi:+.1f}%')

# 汇总
print(f'\n{"="*80}')
print('汇总对比:')
print(f'{"规则":<6} {"场次":<6} {"主中":<6} {"护中":<6} {"无保护ROI":<12} {"有保护ROI":<12} {"差值":<10}')
for rule_name in ['G5', 'G6', 'G7']:
    matches = triggers[rule_name]
    if not matches:
        continue
    n = len(matches)
    main_only_invest = n * STAKE_MAIN
    main_only_return = sum(STAKE_MAIN * m['goal_odds'] for m in matches if m['total'] == m['bet_goals'])
    main_only_roi = (main_only_return - main_only_invest) / main_only_invest * 100
    
    total_invest = sum(STAKE_MAIN + len(m['protect_scores']) * STAKE_PROTECT for m in matches)
    total_return = 0
    hit_main = 0
    hit_protect = 0
    for m in matches:
        ret = 0
        main_hit = (m['total'] == m['bet_goals'])
        if main_hit:
            ret += STAKE_MAIN * m['goal_odds']
            hit_main += 1
        actual_home = int(m['score'].split(':')[0])
        actual_away = int(m['score'].split(':')[1])
        for skey, odds, h, a in m['protect_scores']:
            if f'{actual_home}:{actual_away}' == skey.replace('-', ':'):
                ret += STAKE_PROTECT * odds
                hit_protect += 1
                break
        total_return += ret
    
    protect_roi = (total_return - total_invest) / total_invest * 100
    diff = protect_roi - main_only_roi
    print(f'{rule_name:<6} {n:<6} {hit_main:<6} {hit_protect:<6} {main_only_roi:+.1f}%{"":<6} {protect_roi:+.1f}%{"":<6} {diff:+.1f}%')
