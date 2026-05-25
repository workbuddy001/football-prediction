#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全规则4-5月ROI回测
调用 ai_reasoning.compute_betting(data, analysis)
统计每个规则的场次/命中/ROI
"""
import json, os, sys
from collections import defaultdict

for m in list(sys.modules):
    if 'v36_analyzer' in m:
        del sys.modules[m]
    if 'ai_reasoning' in m:
        del sys.modules[m]
    if 'sporttery_web' in m:
        del sys.modules[m]

from v36_analyzer import analyze_match
from ai_reasoning import compute_betting
from sporttery_web import _build_change_hitrate, _build_odds_hitrate, _build_score_hitrate_stats

_odds_hr = _build_odds_hitrate()
_change_hr = _build_change_hitrate()
_build_score_hitrate_stats()

DATA_DIR = 'sporttery_data'
SCORES_FILE = '分析模板/_scores.json'

def _safe_float(v, default=999.0):
    try: return float(v)
    except: return default

with open(SCORES_FILE, 'r', encoding='utf-8') as f:
    all_scores = json.load(f)

# 过滤4-5月
matches_45 = {k:v for k,v in all_scores.items()
              if '2026-04' in str(v.get('record_time','')) or '2026-05' in str(v.get('record_time',''))}
print(f"4-5月 scores记录: {len(matches_45)}")

# 规则统计
rule_stats = defaultdict(lambda: {
    'matches': [], 'triggers': 0, 'profit': 0.0, 'invest': 0.0,
    'goal_hits': 0, 'score_hits': 0, 'total_hits': 0,  # 场次命中(至少中一个)
    'zero_return': 0,  # 全丢场次
})

errors = 0
bet_results = []

for match_id, score_record in matches_45.items():
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
    actual_score = f'{actual_home}:{actual_away}'
    
    data['_odds_hitrate'] = _odds_hr
    data['_change_hitrate'] = _change_hr
    
    try:
        analysis = analyze_match(data)
    except Exception as e:
        errors += 1
        continue
    
    bet = compute_betting(data, analysis)
    
    action = bet.get('action', '')
    if action == 'skip':
        continue
    
    rule = bet.get('rule', '')
    if not rule:
        continue
    
    goal_bet = bet.get('goal_bet', {})
    goal_goals = goal_bet.get('goals', [])
    goal_stake = goal_bet.get('stake', 0)
    goal_odds = goal_bet.get('odds', {})
    
    score_bets = bet.get('score_bets', [])
    
    # 计算本场收益
    profit = -goal_stake
    goal_hit = False
    score_hit = False
    
    if goal_goals and actual_total in goal_goals:
        actual_odd = goal_odds.get(str(actual_total), 0)
        profit += goal_stake * actual_odd
        goal_hit = True
    # 7球+特殊处理: 竞彩7球+=≥7球
    elif goal_goals and 7 in goal_goals and actual_total >= 7:
        actual_odd = goal_odds.get('7球+', goal_odds.get('7', 0))
        profit += goal_stake * actual_odd
        goal_hit = True
    
    for sb in score_bets:
        sb_stake = sb.get('stake', 0)
        profit -= sb_stake
        if sb.get('score') == actual_score:
            profit += sb_stake * sb.get('odds', 0)
            score_hit = True
    
    total_invest = goal_stake + sum(s.get('stake', 0) for s in score_bets)
    
    rs = rule_stats[rule]
    rs['triggers'] += 1
    rs['invest'] += total_invest
    rs['profit'] += profit
    if goal_hit: rs['goal_hits'] += 1
    if score_hit: rs['score_hits'] += 1
    if goal_hit or score_hit:
        rs['total_hits'] += 1
    else:
        rs['zero_return'] += 1
    
    rs['matches'].append({
        'match_id': match_id,
        'home': score_record.get('home_team', '?'),
        'away': score_record.get('away_team', '?'),
        'score': actual_score,
        'total': actual_total,
        'goal_bet': f'{goal_goals}' if goal_goals else '无',
        'score_bet': [f"{s['score']}({s.get('stake',0)}元)" for s in score_bets],
        'profit': round(profit, 1),
        'goal_hit': goal_hit,
        'score_hit': score_hit,
    })
    
    bet_results.append({
        'match_id': match_id,
        'home': score_record.get('home_team', '?'),
        'away': score_record.get('away_team', '?'),
        'score': actual_score,
        'total': actual_total,
        'rule': rule,
        'profit': round(profit, 1),
    })

# ===== 输出结果 =====
print(f"\n有效比赛: {len(bet_results)} (errors={errors})")
print("=" * 110)

# 汇总表
print(f"\n{'规则':<6} {'触发':>4} {'命中':>4} {'命中率':>7} {'投入':>8} {'回报':>8} {'盈利':>8} {'ROI':>10}")
print("-" * 110)

total_triggers = 0
total_hits = 0
total_invest = 0.0
total_profit = 0.0

# 按优先级排序
rule_order = ['H5', 'X3', 'R0', 'N1', 'R1', 'S7', 'S4', 'F', 'S5', 'G7', 'S3', 'G6', 'S2', 'H3', 'H2', 'H1', 'G5', 'S1', 'X5', 'X6', 'X4', 'X2']
for rule in rule_order:
    rs = rule_stats.get(rule)
    if not rs:
        continue
    n = rs['triggers']
    hits = rs['total_hits']
    inv = rs['invest']
    ret = rs['profit'] + inv
    roi = (rs['profit'] / inv * 100) if inv > 0 else 0
    
    total_triggers += n
    total_hits += hits
    total_invest += inv
    total_profit += rs['profit']
    
    hr = hits / n * 100 if n > 0 else 0
    print(f"{rule:<6} {n:>4} {hits:>4} {hr:>6.0f}% {inv:>7.0f}元 {ret:>7.0f}元 {rs['profit']:>+7.0f}元 {roi:>+9.0f}%")

# 汇总行
total_ret = total_profit + total_invest
total_roi = total_profit / total_invest * 100 if total_invest > 0 else 0
total_hr = total_hits / total_triggers * 100 if total_triggers > 0 else 0
print("-" * 110)
print(f"{'合计':<6} {total_triggers:>4} {total_hits:>4} {total_hr:>6.0f}% {total_invest:>7.0f}元 {total_ret:>7.0f}元 {total_profit:>+7.0f}元 {total_roi:>+9.0f}%")

# ===== 各规则详细明细 =====
print("\n\n" + "=" * 110)
print("各规则详细明细")
print("=" * 110)

for rule in rule_order:
    rs = rule_stats.get(rule)
    if not rs or rs['triggers'] == 0:
        continue
    
    n = rs['triggers']
    hits = rs['total_hits']
    inv = rs['invest']
    roi = (rs['profit'] / inv * 100) if inv > 0 else 0
    zero = rs['zero_return']
    
    print(f"\n{'─' * 110}")
    print(f"【{rule}】触发{n}场 | 命中{hits}场({hits/n*100:.0f}%) | 全丢{zero}场 | 投入{inv:.0f}元 | ROI {roi:+.0f}%")
    print(f"{'─' * 110}")
    print(f"{'比赛':<32} {'比分':>5} {'总':>3} {'投注':<20} {'收益':>8} {'结果'}")
    print("-" * 110)
    
    for m in rs['matches']:
        name = f"{m['home']}vs{m['away']}"[:31]
        bet_desc = m['goal_bet']
        if m['score_bet']:
            bet_desc += '+' + '+'.join(m['score_bet'])
        status = ''
        if m['goal_hit']: status += '⚽进球中 '
        if m['score_hit']: status += '🎯比分中 '
        if not (m['goal_hit'] or m['score_hit']): status = '❌全丢'
        print(f"{name:<32} {m['score']:>5} {m['total']:>3} {bet_desc:<20} {m['profit']:>+7.0f}元 {status}")

print("\n回测完毕。")
