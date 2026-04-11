"""
从JSON数据中提取各选项的8变化数据
"""
import json
import re

def count_8_in_decimal(value_str):
    """统计尾数为8的赔率数量"""
    if not value_str:
        return 0
    try:
        # 将赔率转为小数形式，检查尾数是否为8
        value = float(value_str)
        # 获取小数部分
        decimal_str = f"{value:.2f}"
        # 检查最后一位是否为8
        last_digit = decimal_str[-1]
        return 1 if last_digit == '8' else 0
    except:
        return 0

def extract_8_changes(odds_list):
    """从赔率列表中提取各选项的8变化"""
    init_home_8 = 0
    init_draw_8 = 0
    init_away_8 = 0
    real_home_8 = 0
    real_draw_8 = 0
    real_away_8 = 0
    
    for odds in odds_list:
        init_home_8 += count_8_in_decimal(odds.get('初盘胜', ''))
        init_draw_8 += count_8_in_decimal(odds.get('初盘平', ''))
        init_away_8 += count_8_in_decimal(odds.get('初盘负', ''))
        
        real_home_8 += count_8_in_decimal(odds.get('即时胜', ''))
        real_draw_8 += count_8_in_decimal(odds.get('即时平', ''))
        real_away_8 += count_8_in_decimal(odds.get('即时负', ''))
    
    # 计算变化
    home_change = real_home_8 - init_home_8
    draw_change = real_draw_8 - init_draw_8
    away_change = real_away_8 - init_away_8
    
    return home_change, draw_change, away_change

# 处理3.12-3.16的JSON文件
days = ['3.12', '3.13', '3.14', '3.15', '3.16']
all_matches = []

for day in days:
    filename = f'matches_full_2026-03-{day.split(".")[1]}.json'
    try:
        with open(filename, encoding='utf-8') as f:
            data = json.load(f)
        
        for match in data:
            match_id = match.get('编号', '')
            home = match.get('主队', '')
            away = match.get('客队', '')
            
            if '欧赔数据' in match and '欧赔列表' in match['欧赔数据']:
                odds_list = match['欧赔数据']['欧赔列表']
                h8, d8, a8 = extract_8_changes(odds_list)
                
                all_matches.append({
                    'date': day,
                    'id': match_id,
                    'match': f"{home} vs {away}",
                    'home_8_change': h8,
                    'draw_8_change': d8,
                    'away_8_change': a8
                })
    except FileNotFoundError:
        print(f"File not found: {filename}")

# 输出结果
print(f"共提取 {len(all_matches)} 场比赛的8变化数据")
print()
print("| 日期 | 编号 | 对阵 | 主胜8变化 | 平局8变化 | 客胜8变化 |")
print("|------|------|------|-----------|-----------|-----------|")

for m in all_matches:
    print(f"| {m['date']} | {m['id']} | {m['match']} | {m['home_8_change']:+d} | {m['draw_8_change']:+d} | {m['away_8_change']:+d} |")
