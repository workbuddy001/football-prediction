"""
统计不同规律类型的命中率
"""

import os
import re

actual_results = {
    "周四001": "平局", "周四002": "平局", "周四003": "主胜", "周四004": "客胜",
    "周四005": "主胜", "周四006": "平局", "周四007": "客胜", "周四008": "客胜",
    "周四009": "客胜", "周四010": "主胜", "周四011": "客胜", "周四012": "客胜",
    "周五001": "平局", "周五002": "主胜", "周五003": "平局", "周五004": "主胜",
    "周五005": "客胜", "周五006": "平局", "周五007": "平局", "周五008": "主胜",
    "周五009": "主胜", "周五010": "主胜", "周五011": "主胜", "周五012": "平局",
    "周六001": "平局", "周六002": "客胜", "周六003": "平局", "周六004": "客胜",
    "周六005": "主胜", "周六006": "主胜", "周六007": "平局", "周六008": "主胜",
    "周六009": "主胜", "周六010": "客胜", "周六011": "主胜", "周六012": "平局",
    "周六013": "平局", "周六014": "主胜", "周六015": "主胜", "周六016": "平局",
    "周六017": "平局", "周六018": "主胜", "周六019": "主胜", "周六020": "主胜",
    "周六021": "主胜", "周六022": "主胜", "周六023": "客胜", "周六024": "平局",
    "周六025": "主胜", "周六026": "客胜", "周六027": "客胜", "周六028": "客胜",
    "周六029": "平局", "周六030": "主胜", "周六031": "客胜", "周六032": "平局",
    "周日001": "主胜", "周日002": "主胜", "周日003": "客胜", "周日004": "平局",
    "周日005": "主胜", "周日006": "客胜", "周日007": "客胜", "周日008": "平局",
    "周日009": "主胜", "周日010": "主胜", "周日011": "主胜", "周日012": "平局",
    "周日013": "平局", "周日014": "主胜", "周日015": "主胜", "周日016": "客胜",
    "周日017": "客胜", "周日018": "主胜", "周日019": "主胜", "周日020": "平局",
    "周日021": "平局", "周日022": "客胜", "周日023": "主胜", "周日024": "平局",
    "周日025": "主胜", "周日026": "主胜", "周日027": "主胜", "周日028": "主胜",
    "周日029": "主胜",
    "周一001": "客胜", "周一002": "客胜", "周一003": "平局", "周一004": "平局",
    "周一005": "主胜", "周一006": "平局",
    "周二001": "主胜", "周二002": "主胜", "周二004": "平局", "周二006": "平局",
    "周二007": "客胜", "周二008": "客胜",
}

def count_8_in_odds(odds_list):
    count = 0
    for odd in odds_list:
        for o in odd:
            o_str = f"{o:.2f}"
            if o_str.endswith('8'):
                count += 1
    return count

def extract_data(filepath):
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    
    num_match = re.search(r'编号：(\w+)\s*\|', content)
    if not num_match:
        return None
    num = num_match.group(1)
    
    home_match = re.search(r'\| 主队 \|\s*(.+?)\s*\|', content)
    away_match = re.search(r'\| 客队 \|\s*(.+?)\s*\|', content)
    if not home_match or not away_match:
        return None
    
    home_rate_match = re.search(r'主队近况.*?胜率\s*(\d+)%', content)
    away_rate_match = re.search(r'客队近况.*?胜率\s*(\d+)%', content)
    home_rate = int(home_rate_match.group(1)) if home_rate_match else 0
    away_rate = int(away_rate_match.group(1)) if away_rate_match else 0
    
    init_match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    real_match = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    
    init_8 = real_8 = 0
    if init_match:
        try:
            odds_str = '[' + init_match.group(1) + ']'
            init_8 = count_8_in_odds(eval(odds_str))
        except:
            pass
    if real_match:
        try:
            odds_str = '[' + real_match.group(1) + ']'
            real_8 = count_8_in_odds(eval(odds_str))
        except:
            pass
    
    return {
        'num': num,
        'diff': home_rate - away_rate,
        'change_8': real_8 - init_8,
        'actual': actual_results.get(num)
    }

# 提取数据
all_data = []
for day in ['3.12', '3.13', '3.14', '3.15', '3.16']:
    day_dir = f'd:/work/workbuddy/足球预测/分析模板/{day}'
    if not os.path.exists(day_dir):
        continue
    for f in sorted(os.listdir(day_dir)):
        if f.endswith('_源数据.md'):
            d = extract_data(os.path.join(day_dir, f))
            if d and d['actual']:
                all_data.append(d)

# 按规律类型统计
print("=" * 60)
print("按规律类型统计命中率")
print("=" * 60)

# 1. 8增加 + 客队极好 = 反选
rule1_correct = 0
rule1_total = 0
for d in all_data:
    if d['change_8'] > 0 and d['diff'] < -15:
        rule1_total += 1
        if d['actual'] in ['主胜', '平局']:
            rule1_correct += 1

print(f"\n规律1: 8增加 + 客队极好 → 反选(主胜/平局)")
print(f"  命中率: {rule1_correct}/{rule1_total} = {rule1_correct/rule1_total*100:.1f}%")

# 2. 8增加 + 主队极好 = 跟主胜
rule2_correct = 0
rule2_total = 0
for d in all_data:
    if d['change_8'] > 0 and d['diff'] > 15:
        rule2_total += 1
        if d['actual'] == '主胜':
            rule2_correct += 1

print(f"\n规律2: 8增加 + 主队极好 → 跟主胜")
print(f"  命中率: {rule2_correct}/{rule2_total} = {rule2_correct/rule2_total*100:.1f}%")

# 3. 8增加 + 焦灼 = 跟主胜
rule3_correct = 0
rule3_total = 0
for d in all_data:
    if d['change_8'] > 0 and -15 <= d['diff'] <= 15:
        rule3_total += 1
        if d['actual'] == '主胜':
            rule3_correct += 1

print(f"\n规律3: 8增加 + 焦灼 → 跟主胜")
print(f"  命中率: {rule3_correct}/{rule3_total} = {rule3_correct/rule3_total*100:.1f}%")

# 4. 8减少 + 客队极好 = 跟客胜
rule4_correct = 0
rule4_total = 0
for d in all_data:
    if d['change_8'] < 0 and d['diff'] < -15:
        rule4_total += 1
        if d['actual'] == '客胜':
            rule4_correct += 1

print(f"\n规律4: 8减少 + 客队极好 → 跟客胜")
print(f"  命中率: {rule4_correct}/{rule4_total} = {rule4_correct/rule4_total*100:.1f}%")

# 总结
print("\n" + "=" * 60)
total_valid = rule1_total + rule2_total + rule3_total + rule4_total
total_correct = rule1_correct + rule2_correct + rule3_correct + rule4_correct
print(f"总命中率: {total_correct}/{total_valid} = {total_correct/total_valid*100:.1f}%")
