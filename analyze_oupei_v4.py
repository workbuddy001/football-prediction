# -*- coding: utf-8 -*-
"""
基于《欧赔核心思维》的优化算法 V4

改进点：
1. 增加更多判断维度提升把握度
2. 优化平局判断逻辑
3. 区分正路日和冷门日
4. 精细化实盘/诱盘判断
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


def analyze_oupei_v4(content):
    """
    基于《欧赔核心思维》的优化分析 V4
    
    核心改进：
    1. 多维度判断实盘/诱盘
    2. 精细化把握度评估
    3. 区分正路vs冷门特征
    """
    
    home_form, away_form = parse_team_form(content)
    macau = parse_macau(content)
    initial_odds, realtime_odds = parse_odds(content)
    
    if not initial_odds or not realtime_odds:
        return None
    
    # 基础数据
    init = initial_odds[0]
    rt = realtime_odds[0]
    
    # 赔率变化百分比
    home_change = (rt['home'] - init['home']) / init['home'] * 100
    draw_change = (rt['draw'] - init['draw']) / init['draw'] * 100
    away_change = (rt['away'] - init['away']) / init['away'] * 100
    
    # 即时赔率平均值
    avg_home = np.mean([o['home'] for o in realtime_odds])
    avg_draw = np.mean([o['draw'] for o in realtime_odds])
    avg_away = np.mean([o['away'] for o in realtime_odds])
    
    # 概率
    home_prob = 1/avg_home * 100
    draw_prob = 1/avg_draw * 100
    away_prob = 1/avg_away * 100
    
    # 状态数据
    home_wr = home_form.get('win_rate', 50)
    away_wr = away_form.get('win_rate', 50)
    home_wins = home_form.get('wins', 0)
    away_wins = away_form.get('wins', 0)
    home_losses = home_form.get('losses', 0)
    away_losses = away_form.get('losses', 0)
    form_diff = home_wr - away_wr
    
    # ====== 核心判断逻辑 ======
    
    reason = []
    prediction = None
    confidence = "C"
    score_factors = []  # 用于计算把握度
    
    # ====== 规则1: 强队低赔（最可信）======
    if avg_home < 1.4:
        prediction = "主胜"
        reason.append(f"强主超低赔{avg_home:.2f}")
        score_factors.append(90)
    elif avg_away < 1.4:
        prediction = "客胜"
        reason.append(f"强客超低赔{avg_away:.2f}")
        score_factors.append(90)
    
    # ====== 规则2: 状态差距大 + 低赔 = 实盘 ======
    elif form_diff > 35:
        if form_diff > 0 and avg_home < 1.8:
            prediction = "主胜"
            reason.append(f"状态差距大({form_diff}%)+低赔=实盘")
            score_factors.append(80)
        elif form_diff < 0 and avg_away < 1.8:
            prediction = "客胜"
            reason.append(f"状态差距大({form_diff}%)+低赔=实盘")
            score_factors.append(80)
    
    # ====== 规则3: 主/客队近况极好 =======
    if prediction is None:
        if home_wins >= 7 and home_wins >= home_losses and avg_home < 2.2:
            prediction = "主胜"
            reason.append(f"主队近况极佳(W{home_wins})")
            score_factors.append(75)
        elif away_wins >= 7 and away_wins >= away_losses and avg_away < 2.2:
            prediction = "客胜"
            reason.append(f"客队近况极佳(W{away_wins})")
            score_factors.append(75)
    
    # ====== 规则4: 状态相近 + 平赔小幅下降 = 实盘 ======
    if prediction is None:
        if abs(form_diff) < 20:
            if -8 <= draw_change <= 2:
                # 平赔稳定或小幅下降 - 实盘
                if avg_home < avg_away:
                    prediction = "主胜"
                    reason.append(f"状态相近+平赔稳定({draw_change:.1f}%)=实盘")
                    score_factors.append(65)
                else:
                    prediction = "客胜"
                    reason.append(f"状态相近+平赔稳定({draw_change:.1f}%)=实盘")
                    score_factors.append(65)
    
    # ====== 规则5: 状态相近 + 平赔大幅下降 = 诱盘/防冷 ======
    if prediction is None:
        if abs(form_diff) < 20 and draw_change < -8:
            # 诱盘特征
            if macau == "平局":
                prediction = "平局"
                reason.append(f"诱盘+澳门推荐平局")
                score_factors.append(70)
            else:
                # 反向思考
                if avg_home < avg_away:
                    prediction = "主胜"
                    reason.append(f"诱盘防冷({draw_change:.1f}%)")
                    score_factors.append(55)
                else:
                    prediction = "客胜"
                    reason.append(f"诱盘防冷({draw_change:.1f}%)")
                    score_factors.append(55)
    
    # ====== 规则6: 澳门推荐 + 盘型验证 ======
    if prediction is None:
        if macau == "平局":
            # 澳门推荐平局
            if draw_change < -5:
                prediction = "平局"
                reason.append("澳门推荐平局+平赔下降")
                score_factors.append(65)
            else:
                prediction = "平局"
                reason.append("澳门推荐平局")
                score_factors.append(50)
    
    # ====== 规则7: 胜负反向变动 - 拉胜分平 ======
    if prediction is None:
        if home_change < -5 and away_change > 5:
            # 主胜降水，客胜升水 - 分散客胜
            prediction = "主胜"
            reason.append("主胜降水+客胜升水=分散客胜")
            score_factors.append(60)
        elif away_change < -5 and home_change > 5:
            prediction = "客胜"
            reason.append("客胜降水+主胜升水=分散主胜")
            score_factors.append(60)
    
    # ====== 规则8: 默认选择 ======
    if prediction is None:
        if home_prob > away_prob and home_prob > draw_prob:
            prediction = "主胜"
            reason.append("概率最高")
            score_factors.append(40)
        elif away_prob > home_prob and away_prob > draw_prob:
            prediction = "客胜"
            reason.append("概率最高")
            score_factors.append(40)
        else:
            prediction = "平局"
            reason.append("概率最高")
            score_factors.append(40)
    
    # ====== 计算把握度 ======
    if score_factors:
        avg_score = np.mean(score_factors)
        if avg_score >= 75:
            confidence = "B"
        elif avg_score >= 55:
            confidence = "C"
        else:
            confidence = "D"
    
    return {
        "主队近况": f"{home_wr}%",
        "客队近况": f"{away_wr}%",
        "状态差距": f"{form_diff:+.0f}%",
        "即时赔率": f"{avg_home:.2f} / {avg_draw:.2f} / {avg_away:.2f}",
        "赔率变化": f"H:{home_change:+.1f}% D:{draw_change:+.1f}% A:{away_change:+.1f}%",
        "澳门": macau if macau else "-",
        "预测": prediction,
        "把握度": confidence,
        "分析": " | ".join(reason)
    }


def analyze_match(filepath):
    """分析单场比赛"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    filename = Path(filepath).stem
    
    # 匹配不同日期格式
    match = re.match(r'(周六|周日)(\d+)_(.+?)vs(.+?)_源数据', filename)
    if match:
        match_id = f"{match.group(1)}{match.group(2)}"
        home = match.group(3)
        away = match.group(4)
    else:
        return None
    
    result = analyze_oupei_v4(content)
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
    
    # 输出
    print("=" * 100)
    print("V4(欧赔核心思维优化版) 3.15 预测")
    print("=" * 100)
    print(f"{'编号':<8} {'主队状态':<8} {'客队状态':<8} {'状态差':<6} {'赔率':<16} {'预测':<8} {'把握度':<6} {'分析'}")
    print("-" * 100)
    
    for r in results:
        print(f"{r['编号']:<8} {r['主队近况']:<8} {r['客队近况']:<8} {r['状态差距']:<6} {r['即时赔率']:<16} {r['预测']:<8} {r['把握度']:<6} {r['分析'][:40]}")
    
    print("-" * 100)
    print(f"共 {len(results)} 场")


if __name__ == "__main__":
    main()
