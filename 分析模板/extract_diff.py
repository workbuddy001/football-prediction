"""
从源数据中提取胜率差
"""
import re
import os

def extract_winrate_diff(filepath):
    """从源数据中提取主客队胜率差"""
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    
    # 提取主队胜率
    home_match = re.search(r'主队近况.*?胜率\s*(\d+)%', content)
    # 提取客队胜率
    away_match = re.search(r'客队近况.*?胜率\s*(\d+)%', content)
    
    if home_match and away_match:
        home_rate = int(home_match.group(1))
        away_rate = int(away_match.group(1))
        return home_rate - away_rate
    return None

# 处理3.12-3.16
all_diffs = {}

for day in ['3.12', '3.13', '3.14', '3.15', '3.16']:
    day_dir = f'd:/work/workbuddy/足球预测/分析模板/{day}'
    
    if not os.path.exists(day_dir):
        continue
    
    files = [f for f in os.listdir(day_dir) if f.endswith('_源数据.md')]
    
    for f in files:
        filepath = os.path.join(day_dir, f)
        
        # 提取编号 - 修正正则
        num_match = re.search(r'周\w+(\d+)', f)
        if not num_match:
            continue
        num = f.split('_')[0]  # 周四001, 周五002 etc
        
        diff = extract_winrate_diff(filepath)
        if diff is not None:
            all_diffs[(day, num)] = diff

# 输出结果
print("| 日期 | 编号 | 胜率差 |")
print("|------|------|--------|")
for (day, num), diff in sorted(all_diffs.items()):
    print(f"| {day} | {num} | {diff:+d}% |")
