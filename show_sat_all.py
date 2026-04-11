# -*- coding: utf-8 -*-
import re

with open('3.21_form_analysis.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print('='*160)
print('周六比赛完整汇总')
print('='*160)

# 解析所有周六比赛数据
sat_data = {}
current_id = None

for i, line in enumerate(lines):
    if line.startswith('周六') and 'vs' in line and '置信度' not in line:
        # 提取编号和球队
        parts = line.strip().split()
        if len(parts) >= 3:
            current_id = parts[0].replace('周六', '')
            teams = parts[1] + ' vs ' + parts[2]
            sat_data[current_id] = {'teams': teams}
    
    if current_id and '赔率:' in line:
        # 赔率和置信度
        m = re.search(r'赔率:\s*([\d.]+)/([\d.]+)/([\d.]+).*?置信度:\s*(\d+\.?\d*)%', line)
        if m:
            sat_data[current_id]['odds'] = f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
            sat_data[current_id]['conf'] = m.group(4)
    
    if current_id and '近况差:' in line:
        m = re.search(r'近况差:\s*([+-]?\d+)', line)
        if m:
            sat_data[current_id]['diff'] = m.group(1)
        m = re.search(r"'home':\s*([-\d.]+).*?'draw':\s*([-\d.]+).*?'away':\s*([-\d.]+)", line)
        if m:
            sat_data[current_id]['chg'] = f"H{float(m.group(1)):+.1f}% D{float(m.group(2)):+.1f}% A{float(m.group(3)):+.1f}%"
    
    if current_id and '澳门:' in line and '|' in line:
        m = re.search(r'澳门:\s*(.+?)\s+\|\s+预测:\s*(.+?)\s+\|', line)
        if m:
            sat_data[current_id]['macao'] = m.group(1).strip()
            sat_data[current_id]['pred'] = m.group(2).strip()
    
    if current_id and '近况分析:' in line:
        sat_data[current_id]['analysis'] = line.split('近况分析:')[1].strip()

# 打印结果
print(f'{"编号":<8} {"对阵":<24} {"置信度":<6} {"近况差":<6} {"赔率变化(H/D/A)":<20} {"澳门推荐":<12} {"预测":<6}')
print('-'*140)

for mid in sorted(sat_data.keys(), key=lambda x: int(x)):
    d = sat_data[mid]
    teams = d.get('teams', '')[:22]
    conf = d.get('conf', '')
    diff = d.get('diff', '')
    chg = d.get('chg', '')
    macao = d.get('macao', '')[:10]
    pred = d.get('pred', '')
    
    print(f'周六{mid:<5} {teams:<24} {conf}%   {diff:<6} {chg:<20} {macao:<12} {pred:<6}')
