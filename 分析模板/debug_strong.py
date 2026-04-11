# 检查强烈推荐场次
import sys
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location("final_retrospect", "final_retrospect.py")
module = importlib.util.module_from_spec(spec)
# 不执行，只检查

# 手动统计
import os
import re
import numpy as np

def count_wins(form):
    if not form:
        return 0
    return sum(1 for c in form.upper() if c == 'W')

def get_last_digit(odds):
    s = f"{odds:.2f}"
    return s[-1]

def count_ends_with_8(odds_list):
    return sum(1 for o in odds_list if get_last_digit(o) == '8')

def check_ends_with_88(odds):
    s = f"{odds:.2f}"
    return s[-2:] == '88'

def analyze_8_pattern(initial_odds, realtime_odds, choice_type):
    if not initial_odds or not realtime_odds:
        return {}

    idx = {'home': 0, 'draw': 1, 'away': 2}[choice_type]

    real_home = [o[0] for o in realtime_odds]
    real_away = [o[2] for o in realtime_odds]

    init_home = [o[0] for o in initial_odds]
    init_away = [o[2] for o in initial_odds]
    init_home_8 = count_ends_with_8(init_home)
    init_away_8 = count_ends_with_8(init_away)
    real_home_8 = count_ends_with_8(real_home)
    real_away_8 = count_ends_with_8(real_away)
    diff_home_8 = real_home_8 - init_home_8
    diff_away_8 = real_away_8 - init_away_8

    return {
        'diff_home_8': diff_home_8,
        'diff_away_8': diff_away_8,
    }

# 已有的actual_results
actual_results = {}
actual_results['周五001'] = '客胜'
actual_results['周五002'] = '主胜'
actual_results['周五003'] = '客胜'
actual_results['周五004'] = '客胜'
actual_results['周五005'] = '主胜'
actual_results['周五006'] = '客胜'
actual_results['周五007'] = '平局'
actual_results['周五008'] = '客胜'
actual_results['周五009'] = '主胜'
actual_results['周五010'] = '主胜'
actual_results['周五011'] = '主胜'
actual_results['周五012'] = '主胜'
actual_results['周六001'] = '平局'
actual_results['周六002'] = '客胜'
actual_results['周六003'] = '主胜'
actual_results['周六004'] = '客胜'
actual_results['周六005'] = '平局'
actual_results['周六006'] = '客胜'
actual_results['周六007'] = '客胜'
actual_results['周六008'] = '主胜'
actual_results['周六009'] = '主胜'
actual_results['周六010'] = '平局'
actual_results['周六011'] = '客胜'
actual_results['周六012'] = '平局'
actual_results['周六013'] = '平局'
actual_results['周六014'] = '主胜'
actual_results['周六015'] = '主胜'
actual_results['周六016'] = '平局'
actual_results['周日001'] = '主胜'
actual_results['周日002'] = '平局'
actual_results['周日003'] = '客胜'
actual_results['周日004'] = '客胜'
actual_results['周日005'] = '主胜'
actual_results['周日006'] = '客胜'
actual_results['周日007'] = '主胜'
actual_results['周日008'] = '客胜'
actual_results['周日009'] = '平局'
actual_results['周日010'] = '主胜'
actual_results['周日011'] = '主胜'

print("检查原始数据...")
print(f"实际结果总数: {len(actual_results)}")

# 读取原始分析结果
content = open('result.txt', 'r', encoding='utf-8').read()

# 查找所有强烈推荐的比赛
import re
matches = re.findall(r'【([^_]+)_([^-]+)vs[^-]+】.*?推荐: 强烈推荐', content, re.DOTALL)

print(f"\n从result.txt中找到强烈推荐: {len(matches)}场")
for m in matches:
    print(f"  {m[0]}_{m[1]}")
