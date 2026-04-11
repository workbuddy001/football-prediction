"""
从源数据文件提取8变化数据
"""
import os
import re
import json

def count_8_in_odds(odds_list):
    """计算赔率中尾数为8的数量"""
    count = 0
    for odd in odds_list:
        # 检查每个赔率的尾数
        for o in odd:
            o_str = f"{o:.2f}"
            if o_str.endswith('8') or o_str.endswith('.8'):
                count += 1
    return count

def extract_8_from_file(filepath):
    """从源数据文件提取8变化"""
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
    except:
        return None
    
    # 提取编号
    num_match = re.search(r'编号：(\w+)\|', content)
    if not num_match:
        return None
    num = num_match.group(1)
    
    # 提取对阵
    home_match = re.search(r'\| 主队 \|\s*(.+)', content)
    away_match = re.search(r'\| 客队 \|\s*(.+)', content)
    if not home_match or not away_match:
        return None
    home = home_match.group(1).strip()
    away = away_match.group(1).strip()
    
    # 提取胜率
    home_rate_match = re.search(r'主队近况.*?胜率\s*(\d+)%', content)
    away_rate_match = re.search(r'客队近况.*?胜率\s*(\d+)%', content)
    home_rate = int(home_rate_match.group(1)) if home_rate_match else 0
    away_rate = int(away_rate_match.group(1)) if away_rate_match else 0
    diff = home_rate - away_rate
    
    # 提取初盘赔率
    init_match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if init_match:
        try:
            odds_str = '[' + init_match.group(1) + ']'
            initial_odds = eval(odds_str)
            init_8 = count_8_in_odds(initial_odds)
        except:
            init_8 = 0
    else:
        init_8 = 0
    
    # 提取即时赔率
    real_match = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if real_match:
        try:
            odds_str = '[' + real_match.group(1) + ']'
            realtime_odds = eval(odds_str)
            real_8 = count_8_in_odds(realtime_odds)
        except:
            real_8 = 0
    else:
        real_8 = 0
    
    return {
        'num': num,
        'match': f"{home} vs {away}",
        'home_rate': home_rate,
        'away_rate': away_rate,
        'diff': diff,
        'init_8': init_8,
        'real_8': real_8,
        'change_8': real_8 - init_8
    }

# 收集所有比赛
all_matches = []

for day in ['3.12', '3.13', '3.14', '3.15', '3.16']:
    day_dir = f'd:/work/workbuddy/足球预测/分析模板/{day}'
    if not os.path.exists(day_dir):
        continue
    
    for f in sorted(os.listdir(day_dir)):
        if f.endswith('_源数据.md'):
            filepath = os.path.join(day_dir, f)
            data = extract_8_from_file(filepath)
            if data:
                all_matches.append((day, data))

# 按日期排序并输出
print("| 日期 | 编号 | 对阵 | 主队胜率 | 客队胜率 | 胜率差 | 初盘8 | 即时8 | 8变化 |")
print("|------|------|------|----------|----------|--------|-------|-------|-------|")

for day, data in sorted(all_matches):
    print(f"| {day} | {data['num']} | {data['match']} | {data['home_rate']}% | {data['away_rate']}% | {data['diff']:+d}% | {data['init_8']} | {data['real_8']} | {data['change_8']:+d} |")

print(f"\n共提取 {len(all_matches)} 场比赛")
