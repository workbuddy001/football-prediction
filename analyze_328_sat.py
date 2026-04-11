#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量提取3.28周六15场比赛关键数据"""

import os
import re

base_dir = r"d:\work\workbuddy\足球预测\分析模板\3.28"

def calc_form_score(form_str):
    """近况评分：左×2 + 其他×1，W=3 D=1 L=0，满分18"""
    if not form_str or len(form_str) < 2:
        return None, None
    scores = []
    for ch in form_str[:5]:
        if ch == 'W': scores.append(3)
        elif ch == 'D': scores.append(1)
        elif ch == 'L': scores.append(0)
        else: scores.append(0)
    if len(scores) < 5:
        while len(scores) < 5:
            scores.append(0)
    total = scores[0] * 2 + sum(scores[1:])
    pct = round(total / 18 * 100, 1)
    return total, pct

def extract_match(filepath):
    """提取单场比赛数据"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    data = {}
    
    # 编号和队名
    fname = os.path.basename(filepath)
    m = re.match(r'(周六\d+)_(.+?)vs(.+?)_源数据\.md', fname)
    if m:
        data['id'] = m.group(1)
        data['home'] = m.group(2)
        data['away'] = m.group(3)
    
    # 赛事
    m = re.search(r'赛事\s*\|\s*(.+?)\s*$', content, re.MULTILINE)
    if m: data['league'] = m.group(1).strip()
    
    # 近况走势
    m = re.search(r'主队近况走势\s*\|\s*(\S+)', content)
    if m: data['home_form'] = m.group(1).strip()
    m = re.search(r'客队近况走势\s*\|\s*(\S+)', content)
    if m: data['away_form'] = m.group(1).strip()
    
    # 近况评分
    h_score, h_pct = calc_form_score(data.get('home_form', ''))
    a_score, a_pct = calc_form_score(data.get('away_form', ''))
    data['home_score'] = h_score
    data['home_pct'] = h_pct
    data['away_score'] = a_score
    data['away_pct'] = a_pct
    data['score_diff'] = h_pct - a_pct if h_pct is not None and a_pct is not None else None
    data['score_diff_raw'] = h_score - a_score if h_score is not None and a_score is not None else None
    
    # 置信度
    if data['score_diff'] is not None:
        raw = data['score_diff_raw']
        if raw >= 6: data['confidence'] = round(raw / 12 * 100, 1)
        elif raw <= -6: data['confidence'] = round(-raw / 12 * 100, 1)
        elif raw > 0: data['confidence'] = round(raw / 12 * 100, 1)
        elif raw < 0: data['confidence'] = round(-raw / 12 * 100, 1)
        else: data['confidence'] = 50.0
        data['conf_direction'] = '主胜' if data['score_diff'] > 0 else ('客胜' if data['score_diff'] < 0 else '平局')
    else:
        data['confidence'] = None
        data['conf_direction'] = None
    
    # 澳门推荐
    m = re.search(r'澳门推荐\s*\|\s*(.+?)\s*$', content, re.MULTILINE)
    if m:
        rec = m.group(1).strip()
        if '贏' in rec or '赢' in rec:
            data['macau'] = '主胜'
        elif '和' in rec or '平' in rec:
            data['macau'] = '平局'
        elif '负' in rec:
            data['macau'] = '客胜'
        else:
            data['macau'] = rec
    else:
        data['macau'] = '未知'
    
    # 提取所有赔率公司数据（找澳门马会MacaoPass）
    # 尝试多种模式匹配赔率数据
    lines = content.split('\n')
    
    # 找澳门马会或MacaoPass的赔率
    initial_odds = None
    instant_odds = None
    
    # 模式1：公司名后跟 | 胜 | 平 | 负
    # 先找初盘部分
    in_initial = False
    in_instant = False
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        if '初盘赔率' in line_stripped:
            in_initial = True
            in_instant = False
            continue
        if '即时赔率' in line_stripped:
            in_initial = False
            in_instant = True
            continue
        if '###' in line and (in_initial or in_instant):
            in_initial = False
            in_instant = False
            continue
        
        if '澳门马会' in line_stripped or 'MacaoPass' in line_stripped or '澳门' in line_stripped:
            # 找到澳门行，下一行可能是赔率
            for j in range(i+1, min(i+3, len(lines))):
                next_line = lines[j].strip()
                if next_line.startswith('|') and '---' not in next_line:
                    parts = [p.strip() for p in next_line.split('|')]
                    parts = [p for p in parts if p]
                    if len(parts) >= 3:
                        try:
                            h = float(parts[0])
                            d = float(parts[1])
                            a = float(parts[2])
                            if in_initial:
                                initial_odds = (h, d, a)
                            elif in_instant:
                                instant_odds = (h, d, a)
                        except ValueError:
                            pass
                    break
    
    # 如果上面没找到，尝试直接解析表格中澳门马会的行
    if not initial_odds or not instant_odds:
        # 尝试找500.com格式的赔率
        # 初盘
        pattern_initial = r'澳门马会\s*\|[^|]*\|[^|]*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|'
        m = re.search(pattern_initial, content)
        if m:
            try:
                initial_odds = (float(m.group(1)), float(m.group(2)), float(m.group(3)))
            except:
                pass
    
    # 如果还是没找到，尝试找任何澳门相关的赔率行
    if not initial_odds:
        for line in lines:
            if '澳门' in line and '|' in line:
                parts = [p.strip() for p in line.split('|')]
                nums = []
                for p in parts:
                    try:
                        v = float(p)
                        if 1.0 <= v <= 20.0:
                            nums.append(v)
                    except:
                        pass
                if len(nums) >= 3:
                    initial_odds = (nums[0], nums[1], nums[2])
                    break
    
    data['initial_odds'] = initial_odds
    data['instant_odds'] = instant_odds
    
    # 计算赔率变化
    if initial_odds and instant_odds:
        h_change = round((instant_odds[0] - initial_odds[0]) / initial_odds[0] * 100, 1)
        d_change = round((instant_odds[1] - initial_odds[1]) / initial_odds[1] * 100, 1)
        a_change = round((instant_odds[2] - initial_odds[2]) / initial_odds[2] * 100, 1)
        total_change = round(abs(h_change) + abs(d_change) + abs(a_change), 1)
        data['h_change'] = h_change
        data['d_change'] = d_change
        data['a_change'] = a_change
        data['total_change'] = total_change
        
        # 判断格局
        desc = []
        if h_change < 0: desc.append(f"主降{abs(h_change)}%")
        elif h_change > 0: desc.append(f"主升{abs(h_change)}%")
        if d_change < 0: desc.append(f"平降{abs(d_change)}%")
        elif d_change > 0: desc.append(f"平升{abs(d_change)}%")
        if a_change < 0: desc.append(f"客降{abs(a_change)}%")
        elif a_change > 0: desc.append(f"客升{abs(a_change)}%")
        data['pattern'] = ' '.join(desc)
    else:
        data['h_change'] = None
        data['d_change'] = None
        data['a_change'] = None
        data['total_change'] = None
        data['pattern'] = '无数据'
    
    return data

# 主程序
results = []
for fname in sorted(os.listdir(base_dir)):
    if fname.endswith('_源数据.md'):
        filepath = os.path.join(base_dir, fname)
        data = extract_match(filepath)
        results.append(data)

# 打印汇总表
print(f"{'编号':<8} {'对阵':<24} {'近况差':>6} {'置信%':>6} {'方向':<4} {'澳门':<4} {'变化总和':>8} {'格局'}")
print("-" * 120)
for r in results:
    sd = f"{r['score_diff']:+.0f}" if r['score_diff'] is not None else "N/A"
    cf = f"{r['confidence']:.1f}" if r['confidence'] is not None else "N/A"
    cd = r['conf_direction'] or "N/A"
    mc = r['macau'] or "N/A"
    tc = f"{r['total_change']:.1f}" if r['total_change'] is not None else "N/A"
    
    home = r.get('home', '?')[:6]
    away = r.get('away', '?')[:6]
    vs = f"{home} vs {away}"
    
    pt = r.get('pattern', 'N/A')
    
    print(f"{r['id']:<8} {vs:<24} {sd:>6} {cf:>6} {cd:<4} {mc:<4} {tc:>8} {pt}")

print("\n\n=== 详细赔率数据 ===")
for r in results:
    print(f"\n--- {r['id']} {r.get('home','')} vs {r.get('away','')} ---")
    print(f"  主近况: {r.get('home_form','')} ({r.get('home_score','')}/{r.get('home_pct','')}%)")
    print(f"  客近况: {r.get('away_form','')} ({r.get('away_score','')}/{r.get('away_pct','')}%)")
    print(f"  近况差: {r.get('score_diff','')}, 置信度: {r.get('confidence','')}% → {r.get('conf_direction','')}")
    print(f"  澳门推荐: {r.get('macau','')}")
    print(f"  初盘: {r.get('initial_odds','')}")
    print(f"  即时: {r.get('instant_odds','')}")
    print(f"  变化: H{r.get('h_change','')} D{r.get('d_change','')} A{r.get('a_change','')} 总和={r.get('total_change','')}")
    if r.get('instant_odds'):
        h,d,a = r['instant_odds']
        print(f"  即时赔率绝对值: 主{h} 平{d} 客{a}")
