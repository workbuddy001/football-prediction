#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从3.12源数据文件中提取关键数据，用V3.2规律体系分析"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r"d:\work\workbuddy\足球预测\分析模板\3.12"

def calc_form_score(form_str, weight_recent=True):
    """近况得分：W=3 D=1 L=0，最近一场（左边第一个）×2权重"""
    weights = [2, 1, 1, 1, 1] if weight_recent else [1, 1, 1, 1, 1]
    score = 0
    for i, c in enumerate(form_str[:5]):
        w = weights[i] if i < len(weights) else 1
        if c == 'W': score += 3 * w
        elif c == 'D': score += 1 * w
    return score

def avg_odds(odds_list):
    """计算平均赔率"""
    if not odds_list: return (0, 0, 0)
    n = len(odds_list)
    h = sum(o[0] for o in odds_list) / n
    d = sum(o[1] for o in odds_list) / n
    a = sum(o[2] for o in odds_list) / n
    return (h, d, a)

def calc_change(initial, realtime):
    """赔率变化%"""
    def pct(i, r):
        if i == 0: return 0
        return (r - i) / i * 100
    return (pct(initial[0], realtime[0]), pct(initial[1], realtime[1]), pct(initial[2], realtime[2]))

def calc_prob(h, d, a):
    """赔率→概率"""
    total = 1/h + 1/d + 1/a
    return (1/h/total*100, 1/d/total*100, 1/a/total*100)

def parse_odds_from_file(content):
    """从源数据文件解析赔率列表"""
    initial = []
    realtime = []
    
    # 解析初盘赔率
    in_initial = False
    in_realtime = False
    for line in content.split('\n'):
        if 'initial_odds = [' in line or '初盘赔率（共' in line:
            in_initial = True
            in_realtime = False
            continue
        if 'realtime_odds = [' in line or '即时赔率（共' in line:
            in_realtime = True
            in_initial = False
            continue
        if ']' in line and line.strip() == ']':
            in_initial = False
            in_realtime = False
            continue
        if in_initial or in_realtime:
            m = re.search(r'\(([\d.]+),\s*([\d.]+),\s*([\d.]+)\)', line)
            if m:
                odds = (float(m.group(1)), float(m.group(2)), float(m.group(3)))
                if in_initial: initial.append(odds)
                if in_realtime: realtime.append(odds)
    
    return initial, realtime

def parse_macao_tip(content):
    """解析澳门推荐"""
    m = re.search(r'澳门推荐\s*\|\s*(.+)', content)
    if m:
        tip = m.group(1).strip()
        if '和' in tip or '平' in tip:
            return '平局'
        return tip
    return '未知'

# ===== 主流程 =====
results = []

for fname in sorted(os.listdir(DATA_DIR)):
    if not fname.endswith('.md'):
        continue
    
    filepath = os.path.join(DATA_DIR, fname)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取编号
    m = re.match(r'(周四\d+)', fname)
    match_id = m.group(1) if m else fname
    
    # 提取主客队
    teams_m = re.search(r'主队\s*\|\s*(.+?)\s*$', content, re.MULTILINE)
    away_m = re.search(r'客队\s*\|\s*(.+?)\s*$', content, re.MULTILINE)
    home_team = teams_m.group(1).strip() if teams_m else '?'
    away_team = away_m.group(1).strip() if away_m else '?'
    teams = f"{home_team} vs {away_team}"
    
    # 近况走势
    home_form_m = re.search(r'主队近况走势\s*\|\s*(\w+)', content)
    away_form_m = re.search(r'客队近况走势\s*\|\s*(\w+)', content)
    home_form = home_form_m.group(1) if home_form_m else 'DDDDD'
    away_form = away_form_m.group(1) if away_form_m else 'DDDDD'
    
    # 近况差
    home_score = calc_form_score(home_form)
    away_score = calc_form_score(away_form)
    form_diff = home_score - away_score
    
    # 澳门推荐
    macao_tip = parse_macao_tip(content)
    
    # 赔率
    initial_list, realtime_list = parse_odds_from_file(content)
    ini_avg = avg_odds(initial_list)
    rt_avg = avg_odds(realtime_list)
    
    hc, dc, ac = calc_change(ini_avg, rt_avg)
    hp, dp, ap = calc_prob(rt_avg[0], rt_avg[1], rt_avg[2])
    
    max_prob = max(hp, dp, ap)
    if hp == max_prob: pred = '主胜'
    elif dp == max_prob: pred = '平局'
    else: pred = '客胜'
    
    results.append({
        'id': match_id, 'teams': teams,
        'home_team': home_team, 'away_team': away_team,
        'home_form': home_form, 'away_form': away_form,
        'form_diff': form_diff,
        'home_score': home_score, 'away_score': away_score,
        'macao': macao_tip,
        'ini': ini_avg, 'rt': rt_avg,
        'change': (hc, dc, ac),
        'prob': (hp, dp, ap),
        'pred': pred, 'conf': max_prob,
        'n_companies': len(initial_list)
    })

# ===== 输出数据 =====
print("=" * 110)
print(f"{'编号':<8} {'对阵':<24} {'近况差':>5} {'澳门':<12} {'初盘(均)':<18} {'即时(均)':<18} {'变化(H/D/A)':<28} {'置信':>5}")
print("=" * 110)

for r in results:
    hc, dc, ac = r['change']
    ini_str = f"{r['ini'][0]:.2f}/{r['ini'][1]:.2f}/{r['ini'][2]:.2f}"
    rt_str = f"{r['rt'][0]:.2f}/{r['rt'][1]:.2f}/{r['rt'][2]:.2f}"
    change_str = f"H{hc:+.1f}% D{dc:+.1f}% A{ac:+.1f}%"
    print(f"{r['id']:<8} {r['teams']:<24} {r['form_diff']:>+4d}  {r['macao']:<12} {ini_str:<18} {rt_str:<18} {change_str:<28} {r['conf']:.1f}%")

print(f"\n共{len(results)}场比赛，赔率公司数：{results[0]['n_companies']}家")
