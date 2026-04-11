# -*- coding: utf-8 -*-
"""3.14比赛详细数据列表"""

import re
import ast
from pathlib import Path

DATA_DIR = Path('d:/work/workbuddy/足球预测/分析模板/3.14')

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
    
    # 8变化：末尾为8的赔率数量变化
    init_8_home = sum(1 for o in initial if str(o[0]).replace('.','').endswith('8'))
    init_8_draw = sum(1 for o in initial if str(o[1]).replace('.','').endswith('8'))
    init_8_away = sum(1 for o in initial if str(o[2]).replace('.','').endswith('8'))
    
    real_8_home = sum(1 for o in realtime if str(o[0]).replace('.','').endswith('8'))
    real_8_draw = sum(1 for o in realtime if str(o[1]).replace('.','').endswith('8'))
    real_8_away = sum(1 for o in realtime if str(o[2]).replace('.','').endswith('8'))
    
    home_8 = real_8_home - init_8_home
    draw_8 = real_8_draw - init_8_draw
    away_8 = real_8_away - init_8_away
    
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

files = sorted(DATA_DIR.glob('*_源数据.md'))

print('='*170)
print(f'编号       对阵                     置信度    胜率差    主胜8  平局8  客胜8   8中庸?  实盘?   预测    理由')
print('='*170)

for f in files:
    info = parse_file(f)
    v7v8 = calc_v7v8(info)
    if not v7v8:
        print(f"跳过 {info.get('match_id')}: 无数据")
        continue
    
    mid = info.get('match_id', '')
    home = info.get('home_team', '')
    away = info.get('away_team', '')
    
    conf = v7v8['confidence']
    diff = v7v8['diff']
    h8 = v7v8['home_8']
    d8 = v7v8['draw_8']
    a8 = v7v8['away_8']
    
    # 8中庸判断：|8变化| <= 2
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
    
    # 预测策略
    probs = {'主胜': v7v8['prob_home'], '平局': v7v8['prob_draw'], '客胜': v7v8['prob_away']}
    
    if is_real and conf < 50:
        pred = min(probs, key=probs.get)
        reason = '实盘+低置信排除法'
    elif is_real:
        pred = '主胜' if diff > 0 else '客胜'
        reason = '实盘正向'
    elif conf >= 70:
        pred = max(probs, key=probs.get)
        reason = '高置信正向'
    elif conf < 45:
        pred = min(probs, key=probs.get)
        reason = '低置信排除法'
    elif abs(diff) >= 25:
        pred = '主胜' if diff > 0 else '客胜'
        reason = f'胜率差{diff:+.0f}%'
    else:
        if h8 - a8 >= 2:
            pred = '主胜'
            reason = f'主胜8优势({h8}vs{a8})'
        elif a8 - h8 >= 2:
            pred = '客胜'
            reason = f'客胜8优势({a8}vs{h8})'
        else:
            pred = max(probs, key=probs.get)
            reason = '默认'
    
    print(f'{mid:8} {home} vs {away:20} {conf:5.1f}% {diff:+6.1f}% {h8:+4} {d8:+4} {a8:+4}    {moderate_str:^8}   {real_str:^8}   {pred:<6} {reason}')

print('='*170)
