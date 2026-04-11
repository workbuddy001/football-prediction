# -*- coding: utf-8 -*-
import json
import re

with open('分析模板/matches_full_2026-03-21.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('3.21_form_analysis.txt', 'r', encoding='utf-8') as f:
    analysis = f.read()

# 提取近况数据
form_data = {}
lines = analysis.split('\n')
current_mid = None
for line in lines:
    m = re.match(r'周六(\d+)\s+([^\s]+)\s+vs\s+(\S+)', line)
    if m:
        current_mid = m.group(1)
        continue
    if current_mid and '近况差:' in line:
        m2 = re.search(r'近况差:\s*([+-]?\d+)', line)
        if m2:
            form_data[current_mid] = int(m2.group(1))
        current_mid = None

single_picks = ['017', '019', '022', '025', '026', '029']

print('='*200)
print('周六比赛完整分析（含初盘赔率、即时赔率、澳门心水、造热判断）')
print('='*200)
print()
print(f'{"编号":<8} {"对阵":<18} {"初盘(主/平/客)":<20} {"即时(主/平/客)":<20} {"变化(H/D/A)":<18} {"近况差":<6} {"澳门":<12} {"预测":<6} {"分析依据"}')
print('-'*200)

for match in data:
    bid = match.get('编号', '')
    if '周六' not in bid:
        continue
    mid = bid.replace('周六', '')
    if mid in single_picks:
        continue
    
    home = match.get('主队', '')
    away = match.get('客队', '')
    
    ou = match.get('欧赔数据', {})
    ou_list = ou.get('欧赔列表', [])
    jc_odds = None
    for o in ou_list:
        if '竞*官*' in o.get('公司', ''):
            jc_odds = o
            break
    if not jc_odds:
        continue
    
    h0 = float(jc_odds.get('初盘胜', 0))
    d0 = float(jc_odds.get('初盘平', 0))
    a0 = float(jc_odds.get('初盘负', 0))
    h1 = float(jc_odds.get('即时胜', 0))
    d1 = float(jc_odds.get('即时平', 0))
    a1 = float(jc_odds.get('即时负', 0))
    
    if not h0:
        continue
    
    h_chg = (h1-h0)/h0*100
    d_chg = (d1-d0)/d0*100 if d0 else 0
    a_chg = (a1-a0)/a0*100 if a0 else 0
    
    form_diff = form_data.get(mid, 0)
    macao = match.get('数据分析', {}).get('澳门推荐', '')[:10]
    
    # 简化分析逻辑
    abs_diff = abs(form_diff)
    if abs_diff <= 5:
        if d_chg < -2 or d0 < 3.20:
            # 排除和局
            macao_clean = macao.replace(' 贏', '').strip()
            is_macao_home = macao_clean == home
            is_macao_away = macao_clean == away
            
            if is_macao_home and h_chg < -4:
                pred = '客胜'; reason = '造热防冷'
            elif is_macao_away and a_chg < -4:
                pred = '主胜'; reason = '造热防冷'
            elif is_macao_home:
                pred = '主胜'; reason = '澳门推主'
            elif is_macao_away:
                pred = '客胜'; reason = '澳门推客'
            elif h_chg < a_chg:
                pred = '主胜'; reason = '主降水'
            else:
                pred = '客胜'; reason = '客降水'
        elif h_chg > 5:
            pred = '和局'; reason = '主胜升>5%'
        else:
            pred = '和局'; reason = '近况接近'
    else:
        if h_chg > 5:
            pred = '和局'; reason = '主胜升>5%'
        elif form_diff >= 6 and h_chg > 2:
            pred = '和局'; reason = '近况支持但反升'
        elif form_diff <= -6 and a_chg > 2:
            pred = '和局'; reason = '近况支持但反升'
        else:
            pred = '和局'; reason = '无方向'
    
    print(f'{bid:<8} {home[:6]}vs{away[:8]:<10} {h0:.2f}/{d0:.2f}/{a0:.2f}       {h1:.2f}/{d1:.2f}/{a1:.2f}       H{h_chg:+.1f}% D{d_chg:+.1f}% A{a_chg:+.1f}%   {form_diff:+d}     {macao:<12} {pred:<6} {reason}')
