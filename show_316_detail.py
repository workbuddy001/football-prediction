# -*- coding: utf-8 -*-
"""3.16比赛详细数据列表"""

import re
import ast
from pathlib import Path

DATA_DIR = Path('d:/work/workbuddy/足球预测/分析模板/3.16')

def parse_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    info = {}
    filename = filepath.stem
    
    match = re.match(r'(周一|周二|周三|周四|周五|周六)(\d+)_([^vs]+)vs(.+?)_源数据', filename)
    if match:
        info['match_id'] = f'{match.group(1)}{match.group(2)}'
        info['home_team'] = match.group(3).strip()
        info['away_team'] = match.group(4).strip()
    
    # 赔率
    initial_odds = []
    match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if match:
        try:
            odds_str = '[' + re.sub(r'#.*', '', match.group(1)) + ']'
            initial_odds = ast.literal_eval(odds_str)
        except: pass
    
    realtime_odds = []
    match = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if match:
        try:
            odds_str = '[' + re.sub(r'#.*', '', match.group(1)) + ']'
            realtime_odds = ast.literal_eval(odds_str)
        except: pass
    
    info['initial_odds'] = initial_odds
    info['realtime_odds'] = realtime_odds
    
    return info

def calc_v7v8(info):
    initial = info.get('initial_odds', [])
    realtime = info.get('realtime_odds', [])
    
    if not initial or not realtime:
        return None
    
    real_home = sum(x[0] for x in realtime) / len(realtime)
    real_draw = sum(x[1] for x in realtime) / len(realtime)
    real_away = sum(x[2] for x in realtime) / len(realtime)
    
    real_prob_home = 1/real_home / (1/real_home + 1/real_draw + 1/real_away)
    real_prob_draw = 1/real_draw / (1/real_home + 1/real_draw + 1/real_away)
    real_prob_away = 1/real_away / (1/real_home + 1/real_draw + 1/real_away)
    
    confidence = max(real_prob_home, real_prob_draw, real_prob_away) * 100
    diff = (real_prob_home - real_prob_away) * 100
    
    # 8变化
    home_8 = sum(1 for i in range(len(initial)) if realtime[i][0] < initial[i][0])
    draw_8 = sum(1 for i in range(len(initial)) if realtime[i][1] < initial[i][1])
    away_8 = sum(1 for i in range(len(initial)) if realtime[i][2] < initial[i][2])
    
    return {
        'confidence': confidence,
        'diff': diff,
        'home_8': home_8,
        'draw_8': draw_8,
        'away_8': away_8,
        'prob_home': real_prob_home * 100,
        'prob_draw': real_prob_draw * 100,
        'prob_away': real_prob_away * 100,
    }

# 实际结果
actual = {
    '周一001': '客胜', '周一002': '客胜', '周一003': '客胜', '周一004': '平局',
    '周一005': '客胜', '周一006': '平局',
    '周二001': '客胜', '周二002': '客胜', '周二003': '平局', '周二004': '主胜',
    '周二005': '主胜', '周二006': '主胜', '周二007': '客胜', '周二008': '客胜',
}

files = sorted(DATA_DIR.glob('*_源数据.md'))

print('='*150)
print(f'编号       对阵                     置信度    胜率差    主胜8   平局8   客胜8   8中庸?  实盘?   预测    实际    结果')
print('='*150)

for f in files:
    info = parse_file(f)
    v7v8 = calc_v7v8(info)
    if not v7v8:
        continue
    
    mid = info.get('match_id', '')
    home = info.get('home_team', '')
    away = info.get('away_team', '')
    
    conf = v7v8['confidence']
    diff = v7v8['diff']
    h8 = v7v8['home_8']
    d8 = v7v8['draw_8']
    a8 = v7v8['away_8']
    
    # 8中庸判断
    is_moderate = abs(h8) <= 2 and abs(d8) <= 2 and abs(a8) <= 2
    moderate_str = '是' if is_moderate else '否'
    
    # 实盘判断
    abs_diff = abs(diff)
    is_real = False
    if is_moderate:
        if 55 <= conf < 65 and 10 <= abs_diff <= 20:
            is_real = True
        elif 65 <= conf < 75 and 30 <= abs_diff <= 40:
            is_real = True
        elif conf >= 75 and abs_diff >= 40:
            is_real = True
    
    real_str = '是' if is_real else '否'
    
    # 预测
    if conf < 45:
        probs = {'主胜': v7v8['prob_home'], '平局': v7v8['prob_draw'], '客胜': v7v8['prob_away']}
        pred = min(probs, key=probs.get)
    elif abs(diff) >= 25:
        pred = '主胜' if diff > 0 else '客胜'
    else:
        if h8 - a8 >= 2:
            pred = '主胜'
        elif a8 - h8 >= 2:
            pred = '客胜'
        else:
            pred = '主胜' if v7v8['prob_home'] > v7v8['prob_away'] else '客胜'
    
    act = actual.get(mid, '')
    result = 'O' if pred == act else 'X'
    
    print(f'{mid:8} {home} vs {away:18} {conf:5.1f}% {diff:+6.1f}% {h8:+4} {d8:+4} {a8:+4}   {moderate_str:^6}   {real_str:^8}   {pred:<6} {act:<6} {result}')

print('='*150)
