# -*- coding: utf-8 -*-
"""
V5(欧赔核心思维简化版) 分析3.14比赛
"""

import re
import numpy as np
from pathlib import Path


def parse_team_form(content):
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
    match = re.search(r'澳门推荐\s*\|\s*(.+?)\s*\|', content)
    if match:
        recommend = match.group(1).strip()
        if '和' in recommend or '平' in recommend.lower():
            return "平局"
        elif recommend and recommend != '待补充':
            return recommend
    return None


def parse_odds(content):
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
    home_form, away_form = parse_team_form(content)
    macau = parse_macau(content)
    initial_odds, realtime_odds = parse_odds(content)
    
    if not initial_odds or not realtime_odds:
        return None
    
    init = initial_odds[0]
    rt = realtime_odds[0]
    
    home_change = (rt['home'] - init['home']) / init['home'] * 100
    draw_change = (rt['draw'] - init['draw']) / init['draw'] * 100
    away_change = (rt['away'] - init['away']) / init['away'] * 100
    
    avg_home = np.mean([o['home'] for o in realtime_odds])
    avg_draw = np.mean([o['draw'] for o in realtime_odds])
    avg_away = np.mean([o['away'] for o in realtime_odds])
    
    home_prob = 1/avg_home * 100
    away_prob = 1/avg_away * 100
    
    home_wr = home_form.get('win_rate', 50)
    away_wr = away_form.get('win_rate', 50)
    home_wins = home_form.get('wins', 0)
    away_wins = away_form.get('wins', 0)
    form_diff = home_wr - away_wr
    
    reason = []
    prediction = None
    confidence = "C"
    score = 0
    
    if avg_home < 1.35:
        prediction = "主胜"
        reason.append(f"强主极低赔{avg_home:.2f}")
        score = 90
    elif avg_away < 1.35:
        prediction = "客胜"
        reason.append(f"强客极低赔{avg_away:.2f}")
        score = 90
    elif avg_home < 1.6 and home_wr > away_wr:
        prediction = "主胜"
        reason.append(f"强主低赔{avg_home:.2f}+状态优")
        score = 80
    elif avg_away < 1.6 and away_wr > home_wr:
        prediction = "客胜"
        reason.append(f"强客低赔{avg_away:.2f}+状态优")
        score = 80
    elif home_wins >= 6 and avg_home < 2.2 and home_wr >= away_wr:
        prediction = "主胜"
        reason.append(f"主队近况极佳W{home_wins}")
        score = 75
    elif away_wins >= 6 and avg_away < 2.2 and away_wr >= home_wr:
        prediction = "客胜"
        reason.append(f"客队近况极佳W{away_wins}")
        score = 75
    elif home_change > 10 and home_wr > away_wr and avg_home < 2.5:
        prediction = "主胜"
        reason.append("主队状态好但被看衰，正路")
        score = 70
    elif away_change > 10 and away_wr > home_wr and avg_away < 2.5:
        prediction = "客胜"
        reason.append("客队状态好但被看衰，正路")
        score = 70
    elif abs(form_diff) < 15:
        if -5 <= draw_change <= 5:
            if home_prob > away_prob:
                prediction = "主胜"
                reason.append("状态相近+盘口稳定")
                score = 55
            else:
                prediction = "客胜"
                reason.append("状态相近+盘口稳定")
                score = 55
    
    if prediction is None:
        if macau and '平' in macau:
            prediction = "平局"
            reason.append("澳门推荐平局")
            score = 45
    
    if prediction is None:
        if home_prob > away_prob:
            prediction = "主胜"
            reason.append("概率优先")
            score = 40
        else:
            prediction = "客胜"
            reason.append("概率优先")
            score = 40
    
    if score >= 75:
        confidence = "B"
    elif score >= 55:
        confidence = "C"
    else:
        confidence = "D"
    
    return {
        "编号": None,
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


def main():
    folder = "分析模板/3.14"
    
    results = []
    for filepath in sorted(Path(folder).glob("*.md")):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filename = Path(filepath).stem
        match = re.match(r'周六(\d+)_(.+?)vs(.+?)_源数据', filename)
        if match:
            match_id = f"周六{match.group(1)}"
            result = analyze_oupei_v5(content)
            if result:
                result['编号'] = match_id
                result['对阵'] = f"{match.group(2)} vs {match.group(3)}"
                results.append(result)
    
    print("=" * 95)
    print("V5(欧赔核心思维简化版) 3.14 预测")
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
