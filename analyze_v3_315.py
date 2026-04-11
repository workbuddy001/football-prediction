# -*- coding: utf-8 -*-
"""
V3(欧赔核心思维)算法分析3.15比赛
"""
import re
import os
from pathlib import Path
import numpy as np

# 源数据目录
DATA_DIR = Path("分析模板/3.15")

def parse_team_form(content):
    """解析球队状态"""
    results = {'home': {}, 'away': {}}
    
    # 主队近10场
    home_match = re.search(r'主队近况.*?近10场[，,]?(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    if home_match:
        results['home'] = {
            'wins': int(home_match.group(1)),
            'draws': int(home_match.group(2)),
            'losses': int(home_match.group(3)),
            'win_rate': int(home_match.group(4))
        }
    
    # 客队近10场
    away_match = re.search(r'客队近况.*?近10场[，,]?(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    if away_match:
        results['away'] = {
            'wins': int(away_match.group(1)),
            'draws': int(away_match.group(2)),
            'losses': int(away_match.group(3)),
            'win_rate': int(away_match.group(4))
        }
    
    return results


def parse_odds(content):
    """解析赔率数据"""
    initial_odds = []
    realtime_odds = []
    
    # 初盘赔率
    init_section = re.search(r'## 二、初盘赔率.*?```python(.*?)```', content, re.DOTALL)
    if init_section:
        odds_text = init_section.group(1)
        for match in re.finditer(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', odds_text):
            initial_odds.append({
                'home': float(match.group(1)),
                'draw': float(match.group(2)),
                'away': float(match.group(3))
            })
    
    # 即时赔率
    real_section = re.search(r'## 三、即时赔率.*?```python(.*?)```', content, re.DOTALL)
    if real_section:
        odds_text = real_section.group(1)
        for match in re.finditer(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', odds_text):
            realtime_odds.append({
                'home': float(match.group(1)),
                'draw': float(match.group(2)),
                'away': float(match.group(3))
            })
    
    return initial_odds, realtime_odds


def parse_macau_recommend(content):
    """解析澳门推荐"""
    match = re.search(r'澳门推荐\s*\|\s*(.+?)\s*\|', content)
    if match:
        recommend = match.group(1).strip()
        if '和' in recommend or '平' in recommend.lower():
            return "平局"
        elif recommend and recommend != '待补充':
            return recommend
    return None


def analyze_pan_type(home_form, away_form, realtime_odds):
    """分析盘型（实盘/诱盘）"""
    if not realtime_odds:
        return "未知"
    
    avg_odds = np.mean([[o['home'], o['draw'], o['away']] for o in realtime_odds], axis=0)
    avg_home, avg_draw, avg_away = avg_odds
    
    # 状态差距
    home_wr = home_form.get('win_rate', 50)
    away_wr = away_form.get('win_rate', 50)
    form_diff = abs(home_wr - away_wr)
    
    # 赔率位置
    if avg_home < 1.5:
        return "实盘-强主"
    elif avg_away < 1.5:
        return "实盘-强客"
    elif avg_home < 2.0 and home_wr > away_wr:
        return "实盘-主占优"
    elif avg_away < 2.0 and away_wr > home_wr:
        return "实盘-客占优"
    elif form_diff < 20 and 2.0 < avg_home < 2.5:
        return "中庸盘"
    else:
        return "待分析"


def v3_predict(match_id, content):
    """V3(欧赔核心思维)预测"""
    # 解析数据
    team_form = parse_team_form(content)
    initial_odds, realtime_odds = parse_odds(content)
    macau = parse_macau_recommend(content)
    
    if not realtime_odds:
        return None
    
    # 计算平均值
    avg_odds = np.mean([[o['home'], o['draw'], o['away']] for o in realtime_odds], axis=0)
    avg_home, avg_draw, avg_away = avg_odds
    
    # 概率
    home_prob = 1/avg_home * 100
    draw_prob = 1/avg_draw * 100
    away_prob = 1/avg_away * 100
    
    # 状态
    home_wr = team_form['home'].get('win_rate', 50)
    away_wr = team_form['away'].get('win_rate', 50)
    home_wins = team_form['home'].get('wins', 0)
    away_wins = team_form['away'].get('wins', 0)
    home_losses = team_form['home'].get('losses', 0)
    away_losses = team_form['away'].get('losses', 0)
    
    # 状态差距
    form_diff = abs(home_wr - away_wr)
    
    # 盘型分析
    pan_type = analyze_pan_type(team_form['home'], team_form['away'], realtime_odds)
    
    # ====== V3核心逻辑 ======
    prediction = None
    reason = ""
    confidence = "C"
    
    # 规则1: 强队主场(主胜<1.5) → 主胜
    if avg_home < 1.5:
        prediction = "主胜"
        reason = "强队主场，低赔可信"
        confidence = "B"
    
    # 规则2: 强队客场(客胜<1.5) → 客胜
    elif avg_away < 1.5:
        prediction = "客胜"
        reason = "强队客场，低赔可信"
        confidence = "B"
    
    # 规则3: 状态差距大 + 低赔 = 实盘可信
    elif form_diff > 30 and avg_home < 2.0 and home_wr > away_wr:
        prediction = "主胜"
        reason = "状态差距大+低赔=实盘"
        confidence = "B"
    
    elif form_diff > 30 and avg_away < 2.0 and away_wr > home_wr:
        prediction = "客胜"
        reason = "状态差距大+低赔=实盘"
        confidence = "B"
    
    # 规则4: 状态相近 + 平赔小幅下降(0-5%) = 实盘
    elif form_diff < 20:
        # 判断平赔变化
        if initial_odds and realtime_odds:
            init_draw = np.mean([o['draw'] for o in initial_odds])
            real_draw = np.mean([o['draw'] for o in realtime_odds])
            draw_change = (real_draw - init_draw) / init_draw * 100
            
            # 平赔小幅下降或不变
            if -5 <= draw_change <= 0:
                # 继续用低赔判断
                if avg_home < avg_away:
                    prediction = "主胜"
                    reason = f"状态相近+平赔不变({draw_change:.1f}%)=实盘"
                else:
                    prediction = "客胜"
                    reason = f"状态相近+平赔不变({draw_change:.1f}%)=实盘"
                confidence = "C"
    
    # 规则5: 状态相近 + 平赔大幅下降(>5%) = 诱盘/防冷
    if prediction is None:
        if initial_odds and realtime_odds:
            init_draw = np.mean([o['draw'] for o in initial_odds])
            real_draw = np.mean([o['draw'] for o in realtime_odds])
            draw_change = (real_draw - init_draw) / init_draw * 100
            
            if draw_change < -5:
                # 诱盘，防冷
                # 看澳门推荐
                if macau and '平' in macau:
                    prediction = "平局"
                    reason = f"状态相近+平赔大降({draw_change:.1f}%)+澳门推荐平局=诱盘"
                    confidence = "B"
                else:
                    # 反向思考
                    if avg_home < avg_away:
                        prediction = "主胜"
                        reason = f"状态相近+平赔大降({draw_change:.1f}%)=诱盘防主胜"
                    else:
                        prediction = "客胜"
                        reason = f"状态相近+平赔大降({draw_change:.1f}%)=诱盘防客胜"
                    confidence = "C"
    
    # 规则6: 澳门推荐平局 + 多数公司降平赔
    if prediction is None and macau and '平' in macau:
        prediction = "平局"
        reason = "澳门推荐平局"
        confidence = "C"
    
    # 规则7: 主队近况好(W>=L) + 赔率合理
    if prediction is None:
        if home_wins >= home_losses and avg_home < 2.5:
            prediction = "主胜"
            reason = "主队近况好"
        elif away_wins >= away_losses and avg_away < 2.5:
            prediction = "客胜"
            reason = "客队近况好"
    
    # 规则8: 默认选择概率最高的
    if prediction is None:
        if home_prob > away_prob and home_prob > draw_prob:
            prediction = "主胜"
            reason = "概率最高"
        elif away_prob > home_prob and away_prob > draw_prob:
            prediction = "客胜"
            reason = "概率最高"
        else:
            prediction = "平局"
            reason = "概率最高"
    
    return {
        '编号': match_id,
        '主队状态': f"{home_wr}%",
        '客队状态': f"{away_wr}%",
        '状态差': f"{form_diff}%",
        '主胜': f"{avg_home:.2f}",
        '平局': f"{avg_draw:.2f}",
        '客胜': f"{avg_away:.2f}",
        '主胜率': f"{home_prob:.0f}%",
        '平局率': f"{draw_prob:.0f}%",
        '客胜率': f"{away_prob:.0f}%",
        '盘型': pan_type,
        '澳门推荐': macau or '-',
        '预测': prediction,
        '把握度': confidence,
        '理由': reason
    }


# 分析所有比赛
results = []
files = sorted(DATA_DIR.glob("*.md"))

for filepath in files:
    match_id = filepath.stem.split('_')[0]
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    result = v3_predict(match_id, content)
    if result:
        results.append(result)

# 输出结果
print("=" * 100)
print("V3(欧赔核心思维) 3.15 比赛预测")
print("=" * 100)
print(f"{'编号':<8} {'主队状态':<8} {'客队状态':<8} {'状态差':<6} {'主胜':<6} {'平局':<6} {'客胜':<6} {'预测':<8} {'把握度':<6} {'理由'}")
print("-" * 100)

for r in results:
    print(f"{r['编号']:<8} {r['主队状态']:<8} {r['客队状态']:<8} {r['状态差']:<6} {r['主胜']:<6} {r['平局']:<6} {r['客胜']:<6} {r['预测']:<8} {r['把握度']:<6} {r['理由']}")

print("-" * 100)
print(f"共分析 {len(results)} 场比赛")

# 统计
b_count = sum(1 for r in results if r['把握度'] == 'B')
c_count = sum(1 for r in results if r['把握度'] == 'C')
print(f"把握度B: {b_count}场, 把握度C: {c_count}场")
