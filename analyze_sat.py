# -*- coding: utf-8 -*-
import re
import json

# 读取分析结果
with open('3.21_form_analysis.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print('='*160)
print('周六比赛完整分析列表（含初盘赔率、即时赔率、赔率变化）')
print('='*160)

# 解析周六比赛
sat_matches = []
for i, line in enumerate(lines):
    if line.startswith('周六') and 'vs' in line and '置信度' not in line:
        parts = line.strip().split()
        if len(parts) >= 12:
            match_id = parts[0]
            teams = parts[1] + ' ' + parts[2]
            conf = parts[3].replace('%','')
            
            for j in range(i, min(i+3, len(lines))):
                if '近况差' in lines[j]:
                    lj = lines[j]
                    diff_match = re.search(r'近况差:\s*([+-]?\d+)', lj)
                    odds_match = re.search(r"赔率变化:\s*({[^}]+})", lj)
                    if diff_match:
                        form_diff = diff_match.group(1)
                    if odds_match:
                        odds_str = odds_match.group(1)
                        h_chg = re.search(r"'home':\s*([-\d.]+)", odds_str)
                        d_chg = re.search(r"'draw':\s*([-\d.]+)", odds_str)
                        a_chg = re.search(r"'away':\s*([-\d.]+)", odds_str)
                        hc = float(h_chg.group(1)) if h_chg else 0
                        dc = float(d_chg.group(1)) if d_chg else 0
                        ac = float(a_chg.group(1)) if a_chg else 0
                    break
            
            sat_matches.append((match_id, teams, conf, form_diff, hc, dc, ac))

# 解析单选列表
single_picks = {}
for i, line in enumerate(lines):
    if line.startswith('周六') and 'vs' in line and '置信度' in line:
        parts = line.strip().split()
        if len(parts) >= 6:
            mid = parts[0]
            conf = parts[1].replace('%','')
            macao = parts[2]
            pred = parts[3]
            single_picks[mid] = (macao, pred)

# 解析庄家分析
dispersion = {}
for i, line in enumerate(lines):
    if line.startswith('周六') and 'vs' in line and '筹码' in line:
        parts = line.strip().split()
        if len(parts) >= 8:
            mid = parts[0]
            diff = parts[1]
            chg = parts[2] + ' ' + parts[3] + ' ' + parts[4]
            flow = parts[5]
            behavior = ' '.join(parts[6:-2])
            risk = parts[-2]
            conclusion = parts[-1]
            dispersion[mid] = (flow, behavior, risk, conclusion)

# 打印结果
print(f'{"编号":<8} {"对阵":<22} {"置信度":<6} {"近况差":<6} {"赔率变化(H/D/A)":<20} {"澳门":<10} {"预测":<6} {"风险":<4} {"分析结论"}')
print('-'*160)

for m in sat_matches:
    mid = m[0]
    teams = m[1]
    conf = m[2]
    diff = m[3]
    hc, dc, ac = m[4], m[5], m[6]
    
    macao_pred = single_picks.get(mid, ('', ''))
    macao = macao_pred[0]
    pred = macao_pred[1]
    
    disp = dispersion.get(mid, ('', '', '', ''))
    flow, behavior, risk, conclusion = disp
    
    chg_str = f'H{hc:+.1f}% D{dc:+.1f}% A{ac:+.1f}%'
    
    print(f'{mid:<8} {teams[:20]:<22} {conf}%   {diff:<6} {chg_str:<20} {macao[:8]:<10} {pred:<6} {risk:<4} {conclusion}')
