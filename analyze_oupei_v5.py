# -*- coding: utf-8 -*-
"""
基于《欧赔核心思维》的优化算法 V5

核心改进：
1. 简化规则，聚焦最可靠的判断
2. 增加"正路日"特征识别
3. 优化平局判断
"""

import re
import numpy as np
from pathlib import Path


def parse_team_form(content):
    """解析球队状态"""
    home_match = re.search(r'主队近况.*?近10场[，,]?(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    away_match = re.search(r'客队近况.*?近10场[，,]?(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    
    home_form = {}
    away_form = {}
    
    if home_match:
        home_form = {
            'wins': int(home_match.group(1)),
            'draws': int(home_match.group(2)),
            'losses': int(home_match.group(3)),
            'win_rate': int(home_match.group(4))
        }
    if away_match:
        away_form = {
            'wins': int(away_match.group(1)),
            'draws': int(away_match.group(2)),
            'losses': int(away_match.group(3)),
            'win_rate': int(away_match.group(4))
        }
    
    return home_form, away_form


def parse_macau(content):
    """解析澳门推荐"""
    match = re.search(r'澳门推荐\s*\|\s*(.+?)\s*\|', content)
    if match:
        recommend = match.group(1).strip()
        if '和' in recommend or '平' in recommend.lower():
            return "平局"
        elif recommend and recommend != '待补充':
            return recommend
    return None


def parse_odds(content):
    """解析赔率"""
    initial_odds = []
    realtime_odds = []
    
    initial_section = re.search(r'## 二、初盘赔率.*?```python(.*?)```', content, re.DOTALL)
    if initial_section:
        odds_text = initial_section.group(1)
        for match in re.finditer(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', odds_text):
            initial_odds.append({
                'home': float(match.group(1)),
                'draw': float(match.group(2)),
                'away': float(match.group(3))
            })
    
    realtime_section = re.search(r'## 三、即时赔率.*?```python(.*?)```', content, re.DOTALL)
    if realtime_section:
        odds_text = realtime_section.group(1)
        for match in re.finditer(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', odds_text):
            realtime_odds.append({
                'home': float(match.group(1)),
                'draw': float(match.group(2)),
                'away': float(match.group(3))
            })
    
    return initial_odds, realtime_odds


def analyze_oupei_v5(content):
    """
    基于《欧赔核心思维》的优化分析 V5
    
    核心思路：
    1. 强队低赔是最高置信度信号
    2. 状态极好是次高置信度
    3. 正路日特征：强队主场/状态好+低赔
    """
    
    home_form, away_form = parse_team_form(content)
    macau = parse_macau(content)
    initial_odds, realtime_odds = parse_odds(content)
    
    if not initial_odds or not realtime_odds:
        return None
    
    # 基础数据
    init = initial_odds[0]
    rt = realtime_odds[0]
    
    # 赔率变化
    home_change = (rt['home'] - init['home']) / init['home'] * 100
    draw_change = (rt['draw'] - init['draw']) / init['draw'] * 100
    away_change = (rt['away'] - init['away']) / init['away'] * 100
    
    # 即时赔率
    avg_home = np.mean([o['home'] for o in realtime_odds])
    avg_draw = np.mean([o['draw'] for o in realtime_odds])
    avg_away = np.mean([o['away'] for o in realtime_odds])
    
    # 概率
    home_prob = 1/avg_home * 100
    away_prob = 1/avg_away * 100
    
    # 状态
    home_wr = home_form.get('win_rate', 50)
    away_wr = away_form.get('win_rate', 50)
    home_wins = home_form.get('wins', 0)
    away_wins = away_form.get('wins', 0)
    form_diff = home_wr - away_wr
    
    reason = []
    prediction = None
    confidence = "C"
    score = 0
    
    # ====== 规则1: 强队极低赔（最高置信度）======
    if avg_home < 1.35:
        prediction = "主胜"
        reason.append(f"强主极低赔{avg_home:.2f}")
        score = 90
    elif avg_away < 1.35:
        prediction = "客胜"
        reason.append(f"强客极低赔{avg_away:.2f}")
        score = 90
    
    # ====== 规则2: 强队低赔 + 状态优势 ======
    elif avg_home < 1.6 and home_wr > away_wr:
        prediction = "主胜"
        reason.append(f"强主低赔{avg_home:.2f}+状态优")
        score = 80
    elif avg_away < 1.6 and away_wr > home_wr:
        prediction = "客胜"
        reason.append(f"强客低赔{avg_away:.2f}+状态优")
        score = 80
    
    # ====== 规则3: 状态极好+赔率合理 ======
    elif home_wins >= 6 and avg_home < 2.2 and home_wr >= away_wr:
        prediction = "主胜"
        reason.append(f"主队近况极佳W{home_wins}")
        score = 75
    elif away_wins >= 6 and avg_away < 2.2 and away_wr >= home_wr:
        prediction = "客胜"
        reason.append(f"客队近况极佳W{away_wins}")
        score = 75
    
    # ====== 规则4: 强队被看衰（正路特征）======
    elif home_change > 10 and home_wr > away_wr and avg_home < 2.5:
        # 主胜被升水，但主队状态更好
        prediction = "主胜"
        reason.append("主队状态好但被看衰，正路")
        score = 70
    elif away_change > 10 and away_wr > home_wr and avg_away < 2.5:
        prediction = "客胜"
        reason.append("客队状态好但被看衰，正路")
        score = 70
    
    # ====== 规则5: 状态相近 + 盘口稳定 ======
    elif abs(form_diff) < 15:
        if -5 <= draw_change <= 5:
            # 平赔稳定
            if home_prob > away_prob:
                prediction = "主胜"
                reason.append("状态相近+盘口稳定")
                score = 55
            else:
                prediction = "客胜"
                reason.append("状态相近+盘口稳定")
                score = 55
    
    # ====== 规则6: 澳门推荐（降权使用）======
    if prediction is None:
        if macau and '平' in macau:
            prediction = "平局"
            reason.append("澳门推荐平局")
            score = 45
    
    # ====== 规则7: 默认 ======
    if prediction is None:
        if home_prob > away_prob:
            prediction = "主胜"
            reason.append("概率优先")
            score = 40
        else:
            prediction = "客胜"
            reason.append("概率优先")
            score = 40
    
    # 把握度
    if score >= 75:
        confidence = "B"
    elif score >= 55:
        confidence = "C"
    else:
        confidence = "D"
    
    return {
        "主队近况": f"{home_wr}%",
        "客队近况": f"{away_wr}%",
        "状态差距": f"{form_diff:+.0f}%",
        "赔率": f"{avg_home:.2f}/{avg_draw:.2f}/{avg_away:.2f}",
        "变化": f"H:{home_change:+.0f}% D:{draw_change:+.0f}%",
        "澳门": macau if macau else "-",
        "预测": prediction,
        "把握度": confidence,
        "理由": " | ".join(reason)
    }


def analyze_match(filepath):
    """分析单场比赛"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    filename = Path(filepath).stem
    match = re.match(r'(周六|周日)(\d+)_(.+?)vs(.+?)_源数据', filename)
    if match:
        match_id = f"{match.group(1)}{match.group(2)}"
        home = match.group(3)
        away = match.group(4)
    else:
        return None
    
    result = analyze_oupei_v5(content)
    if result:
        return {"编号": match_id, "对阵": f"{home} vs {away}", **result}
    return None


def main():
    folder = "分析模板/3.15"
    
    results = []
    for filepath in sorted(Path(folder).glob("*.md")):
        result = analyze_match(filepath)
        if result:
            results.append(result)
    
    print("=" * 95)
    print("V5(欧赔核心思维简化版) 3.15 预测")
    print("=" * 95)
    print(f"{'编号':<8} {'主客状态':<12} {'状态差':<6} {'赔率':<14} {'预测':<8} {'把握度':<6} {'理由'}")
    print("-" * 95)
    
    for r in results:
        status = f"{r['主队近况']}/{r['客队近况']}"
        print(f"{r['编号']:<8} {status:<12} {r['状态差距']:<6} {r['赔率']:<14} {r['预测']:<8} {r['把握度']:<6} {r['理由'][:35]}")
    
    print("-" * 95)
    print(f"共 {len(results)} 场")


if __name__ == "__main__":
    main()
