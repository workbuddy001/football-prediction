"""
对比修正前后的预测结果
"""

import os
import re
import glob

def extract_jingcai_odds_v5(match_id):
    """提取第四部分 - 竞彩胜平负赔率"""
    file_path = f"d:/work/workbuddy/足球预测/分析模板/3.19/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    if not files:
        return None, None, None
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        home_match = re.search(r'主胜[（(].*?[）)]\s*\|\s*(\d+\.\d+)', content)
        draw_match = re.search(r'平局\s*\|\s*(\d+\.\d+)', content)
        away_match = re.search(r'客胜[（(].*?[）)]\s*\|\s*(\d+\.\d+)', content)
        home = float(home_match.group(1)) if home_match else None
        draw = float(draw_match.group(1)) if draw_match else None
        away = float(away_match.group(1)) if away_match else None
        return home, draw, away
    except:
        return None, None, None

def extract_jingcai_odds_v6(match_id):
    """提取第五部分 - 竞*官*即时赔率"""
    file_path = f"d:/work/workbuddy/足球预测/分析模板/3.19/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    if not files:
        return None, None, None
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.split('\n')
        in_table = False
        for line in lines:
            if '初盘胜' in line and '即时胜' in line:
                in_table = True
                continue
            if in_table:
                if line.startswith('---') or line.startswith('## '):
                    break
                if '竞*官*' in line and '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 9:
                        try:
                            return float(parts[2]), float(parts[5]), float(parts[8])
                        except:
                            pass
        return None, None, None
    except:
        return None, None, None

def calculate_prediction(home, draw, away):
    """计算预测"""
    if home is None:
        return "-"
    total = home + draw + away
    home_rate = (total / home) * 100 / 3
    draw_rate = (total / draw) * 100 / 3
    away_rate = (total / away) * 100 / 3
    total_rate = home_rate + draw_rate + away_rate
    home_rate = home_rate / total_rate * 100
    draw_rate = draw_rate / total_rate * 100
    away_rate = away_rate / total_rate * 100
    
    if home_rate >= draw_rate and home_rate >= away_rate:
        return "主胜"
    elif away_rate >= home_rate and away_rate >= draw_rate:
        return "客胜"
    else:
        return "平局"

def extract_match_name(match_id):
    file_path = f"d:/work/workbuddy/足球预测/分析模板/3.19/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    if not files:
        return match_id
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        home_match = re.search(r'主队\s*\|\s*([^\n|]+)', content)
        away_match = re.search(r'客队\s*\|\s*([^\n|]+)', content)
        home = home_match.group(1).strip() if home_match else "主队"
        away = away_match.group(1).strip() if away_match else "客队"
        return f"{home} vs {away}"
    except:
        return match_id

match_ids = [
    "周四001", "周四002", "周四003", "周四004", "周四005",
    "周四006", "周四007", "周四008", "周四009", "周四010",
    "周五001", "周五002", "周五003", "周五004", "周五005",
    "周五006", "周五007", "周五008", "周五009", "周五010",
    "周五011", "周五012", "周五013", "周五014", "周五015", "周五016"
]

print("=" * 120)
print("竞彩赔率修正前后对比")
print("=" * 120)
print(f"\n| 编号 | 对阵 | 修正前(竞彩胜平负) | 修正后(竞*官*即时) | 修正前预测 | 修正后预测 | 变化 |")
print(f"|------|------|---------------------|---------------------|------------|------------|------|")

changed = 0
unchanged = 0

for mid in match_ids:
    match_name = extract_match_name(mid)
    
    # 修正前 - 第四部分数据
    v5_home, v5_draw, v5_away = extract_jingcai_odds_v5(mid)
    v5_pred = calculate_prediction(v5_home, v5_draw, v5_away)
    
    # 修正后 - 第五部分竞*官*数据
    v6_home, v6_draw, v6_away = extract_jingcai_odds_v6(mid)
    v6_pred = calculate_prediction(v6_home, v6_draw, v6_away)
    
    # 赔率显示
    v5_odds = f"{v5_home}/{v5_draw}/{v5_away}" if v5_home else "未开"
    v6_odds = f"{v6_home}/{v6_draw}/{v6_away}" if v6_home else "未开"
    
    # 变化标记
    if v5_pred != v6_pred and v5_pred != "-" and v6_pred != "-":
        change = "YES"
        changed += 1
    elif v5_pred == v6_pred:
        change = "-"
        unchanged += 1
    else:
        change = "-"
    
    print(f"| {mid} | {match_name} | {v5_odds} | {v6_odds} | {v5_pred} | {v6_pred} | {change} |")

print(f"\n变化场次: {changed} | 未变化: {unchanged}")
