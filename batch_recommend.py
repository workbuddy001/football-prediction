#!/usr/bin/env python3
"""批量分析所有比赛，输出投注建议"""
import json, os, sys, glob

# 清除模块缓存
for m in list(sys.modules):
    if m in ('v36_analyzer', 'ai_reasoning', 'sporttery_web'):
        del sys.modules[m]

from v36_analyzer import analyze_match
from ai_reasoning import compute_betting
from sporttery_web import _build_change_hitrate, _build_odds_hitrate

_oh = _build_odds_hitrate()
_ch = _build_change_hitrate()

files = sorted(glob.glob('sporttery_data/20*.json'), key=lambda x: int(os.path.basename(x).replace('.json','')), reverse=True)

signals = {}
total = 0
for fp in files:
    mid = os.path.basename(fp).replace('.json', '')
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        continue
    
    data['_odds_hitrate'] = _oh
    data['_change_hitrate'] = _ch
    try:
        analysis = analyze_match(data)
    except:
        continue
    betting = compute_betting(data, analysis)
    rule = betting.get('rule')
    if not rule:
        continue
    
    total += 1
    mi = data.get('match_info', {})
    mid_str = mi.get('match_num_str', mid)
    home = mi.get('home_team', '?')
    away = mi.get('away_team', '?')
    date = mi.get('match_date', '?')
    time = mi.get('match_time', '?')
    stake = betting.get('total_stake', 0)
    summary = betting.get('summary', '?')
    
    signals[mid] = {
        'rule': rule,
        'match': f'{mid_str} {home} vs {away}',
        'datetime': f'{date} {time}',
        'stake': stake,
        'summary': summary,
        'goal_bet': betting.get('goal_bet', {}),
        'score_bets': betting.get('score_bets', []),
        'mid': mid_str,
    }

# 筛选未赛（检查 _scores.json）
import json as json2
try:
    with open('分析模板/_scores.json', 'r', encoding='utf-8') as f:
        scores = json2.load(f)
except:
    scores = {}

unscored = {}
for mid, s in signals.items():
    if mid in scores:
        sr = scores[mid]
        if 'home_score' in sr and sr['home_score'] is not None and isinstance(sr.get('home_score'), (int, float)):
            continue  # 已赛跳过
    unscored[mid] = s

# 改用未赛输出
signals = unscored
print(f'批量分析完成: {len(files)}场扫描, {len(signals)}个未赛信号')
print(f'{"="*80}\n')

if not signals:
    print('当前无未赛信号触发')
    sys.exit(0)

# 按信号分组排序
order = ['R0','R1','F','G7','S4','S5','S3','G6','S2','H3','H2','H1','G5','S6','S1','G4','R3','R4']
rule_order = {r: i for i, r in enumerate(order)}

sorted_signals = sorted(signals.items(), key=lambda x: (rule_order.get(x[1]['rule'], 99), x[0]))

total_stake = 0
for mid, s in sorted_signals:
    total_stake += s['stake']
    print(f"[{s['rule']}] {s['match']}")
    print(f"      {s['datetime']} | 投{s['stake']}元 | {s['summary']}")
    gb = s['goal_bet']
    if gb.get('goals'):
        print(f"      进球: {gb.get('goals')} 赔{gb.get('odds')} 投{gb.get('stake')}元")
    for sb in s['score_bets']:
        print(f"      比分: {sb.get('score')} 赔{sb.get('odds')} 投{sb.get('stake')}元 [{sb.get('tag','')}]")
    print()
    
print(f'合计: {len(signals)}个未赛信号, 总投入{total_stake}元')

