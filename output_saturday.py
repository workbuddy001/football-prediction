# -*- coding: utf-8 -*-
import re

# 读取结果文件
with open('3.21_result.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print('='*140)
print('周六比赛完整预测列表（赔率变化 + 状态分析）')
print('='*140)

# 单选列表
print('\n【单选推荐】澳门分胜负 + 置信度>=66%')
print('-'*140)
print('{:<8} {:<20} {:<14} {:<6} {:<10} {:<4} {:<22} {:<6} {:12}'.format(
    '编号', '对阵', '竞彩即时', '置信度', '澳门', '预测', '赔率变化(H/D/A)', '近况差', '状态分析'))
print('-'*140)

for line in lines:
    if line.startswith('周六') and '特温特' in line or 'AC米兰' in line or '多特' in line or '本菲卡' in line or '尤文' in line or '巴黎' in line:
        # 解析
        match_id = line[:8].strip()
        
        # 对阵
        idx = line.find('vs')
        if idx > 0:
            match_name = line[8:idx].strip()
        
        # 赔率
        odds_match = re.search(r'(\d+\.\d+/\d+\.\d+/\d+\.\d+)', line)
        odds = odds_match.group(1) if odds_match else ''
        
        # 置信度
        conf_match = re.search(r'(\d+\.\d+)%', line)
        conf = conf_match.group(1) if conf_match else ''
        
        # 澳门
        macao_match = re.search(r'(\S+)\s+贏', line)
        macao = macao_match.group(1)[:8] if macao_match else '和局'
        
        # 预测
        pred_match = re.search(r'(主胜|客胜|和局)', line)
        pred = pred_match.group(1) if pred_match else ''
        
        # 赔率变化
        h_chg = re.search(r'H([+-]?\d+\.?\d*)%', line)
        d_chg = re.search(r'D([+-]?\d+\.?\d*)%', line)
        a_chg = re.search(r'A([+-]?\d+\.?\d*)%', line)
        
        if h_chg:
            chg = 'H{}% D{}% A{}%'.format(h_chg.group(1), d_chg.group(1) if d_chg else '0', a_chg.group(1) if a_chg else '0')
        else:
            chg = '0%/0%/0%'
        
        # 近况差
        diff_match = re.search(r'([+-]\d+)\s+\[', line)
        diff = diff_match.group(1) if diff_match else '0'
        
        # 状态分析
        if '近况支持+赔不变' in line:
            analysis = '[高压区-防冷]'
        elif '近况支持但赔上升' in line:
            analysis = '[矛盾-防冷]'
        elif '近况支持+赔率降水' in line:
            analysis = '[OK-正路]'
        else:
            analysis = '[正常]'
        
        print('{:<8} {:<20} {:<14} {:<6} {:<10} {:<4} {:<22} {:<6} {}'.format(
            match_id, match_name, odds, conf, macao, pred, chg, diff, analysis))

# 重点比赛
print('\n\n【重点比赛】需要特别关注')
print('-'*140)

# 过滤周六+有问题的比赛
for line in lines:
    if not line.startswith('周六'):
        continue
    
    # 只显示有问题的比赛
    has_issue = '[' in line and ('!' in line or 'OK' in line or '近况' in line)
    
    if has_issue:
        # 解析
        match_id = line[:8].strip()
        
        # 对阵
        idx = line.find('vs')
        if idx > 0:
            match_name = line[8:idx].strip()
        
        # 赔率
        odds_match = re.search(r'(\d+\.\d+/\d+\.\d+/\d+\.\d+)', line)
        odds = odds_match.group(1) if odds_match else ''
        
        # 澳门
        macao_match = re.search(r'(\S+)\s+贏', line)
        macao = macao_match.group(1)[:8] if macao_match else '和局'
        
        # 预测
        pred_match = re.search(r'(主胜|客胜|和局)', line)
        pred = pred_match.group(1) if pred_match else ''
        
        # 赔率变化
        h_chg = re.search(r'H([+-]?\d+\.?\d*)%', line)
        d_chg = re.search(r'D([+-]?\d+\.?\d*)%', line)
        a_chg = re.search(r'A([+-]?\d+\.?\d*)%', line)
        
        if h_chg:
            chg = 'H{}% D{}% A{}%'.format(h_chg.group(1), d_chg.group(1) if d_chg else '0', a_chg.group(1) if a_chg else '0')
        else:
            chg = '0%/0%/0%'
        
        # 近况差
        diff_match = re.search(r'([+-]\d+)\s+\[', line)
        diff = diff_match.group(1) if diff_match else '0'
        
        # 状态分析
        if '近况支持+赔不变' in line:
            analysis = '[高压区-防冷] 近况好但赔率不变'
        elif '近况支持但赔上升' in line:
            analysis = '[矛盾-防冷] 近况好但赔率上升'
        elif '近况支持+赔率降水' in line:
            analysis = '[OK-正路] 近况支持且赔率降水'
        else:
            analysis = '[其他]'
        
        print('{:<8} {:<20} {:<14} {:<10} {:<4} {:<22} {:<6} {}'.format(
            match_id, match_name, odds, macao, pred, chg, diff, analysis))

print('\n\n【其他比赛】')
print('-'*140)
print('{:<8} {:<20} {:<14} {:<6} {:<10} {:<4} {:<22} {:<6} {:12}'.format(
    '编号', '对阵', '竞彩即时', '置信度', '澳门', '预测', '赔率变化(H/D/A)', '近况差', '状态'))
print('-'*140)

for line in lines:
    if not line.startswith('周六'):
        continue
    
    # 跳过单选和重点
    if '[' in line and ('!' in line or 'OK' in line):
        continue
    
    # 解析
    match_id = line[:8].strip()
    
    # 对阵
    idx = line.find('vs')
    if idx > 0:
        match_name = line[8:idx].strip()
    
    # 赔率
    odds_match = re.search(r'(\d+\.\d+/\d+\.\d+/\d+\.\d+)', line)
    odds = odds_match.group(1) if odds_match else ''
    
    # 置信度
    conf_match = re.search(r'(\d+\.\d+)%', line)
    conf = conf_match.group(1) if conf_match else ''
    
    # 澳门
    macao_match = re.search(r'(\S+)\s+贏', line)
    macao = macao_match.group(1)[:8] if macao_match else '和局'
    
    # 预测
    pred_match = re.search(r'(主胜|客胜|和局)', line)
    pred = pred_match.group(1) if pred_match else ''
    
    # 赔率变化
    h_chg = re.search(r'H([+-]?\d+\.?\d*)%', line)
    d_chg = re.search(r'D([+-]?\d+\.?\d*)%', line)
    a_chg = re.search(r'A([+-]?\d+\.?\d*)%', line)
    
    if h_chg:
        chg = 'H{}% D{}% A{}%'.format(h_chg.group(1), d_chg.group(1) if d_chg else '0', a_chg.group(1) if a_chg else '0')
    else:
        chg = '0%/0%/0%'
    
    # 近况差
    diff_match = re.search(r'([+-]\d+)\s+\[', line)
    diff = diff_match.group(1) if diff_match else '0'
    
    analysis = '[正常]'
    
    print('{:<8} {:<20} {:<14} {:<6} {:<10} {:<4} {:<22} {:<6} {}'.format(
        match_id, match_name, odds, conf, macao, pred, chg, diff, analysis))
