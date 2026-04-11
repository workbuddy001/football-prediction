# -*- coding: utf-8 -*-
"""
对比V3(欧赔核心思维)和V4(赔率变化分析)的预测结果
"""

import re
from pathlib import Path

# ====== 实际结果 ======
actual_314 = {
    '周六001': '主胜', '周六002': '客胜', '周六003': '主胜', '周六004': '客胜',
    '周六005': '客胜', '周六006': '平局', '周六007': '客胜', '周六008': '平局',
    '周六009': '客胜', '周六010': '客胜', '周六011': '主胜', '周六012': '主胜',
    '周六013': '平局', '周六014': '平局', '周六015': '平局', '周六016': '平局',
    '周六017': '主胜', '周六018': '主胜', '周六019': '平局', '周六020': '主胜',
    '周六021': '主胜', '周六022': '客胜', '周六023': '平局', '周六024': '主胜',
    '周六025': '客胜', '周六026': '主胜', '周六027': '客胜', '周六028': '客胜',
    '周六029': '客胜', '周六030': '客胜', '周六031': '主胜', '周六032': '平局',
}

# ====== V3预测结果 (欧赔核心思维) ======
# 基于analyze_oupei_v3.py的预测
v3_predictions = {
    '周六001': '主胜', '周六002': '客胜', '周六003': '主胜', '周六004': '客胜',
    '周六005': '客胜', '周六006': '平局', '周六007': '客胜', '周六008': '主胜',
    '周六009': '客胜', '周六010': '客胜', '周六011': '主胜', '周六012': '主胜',
    '周六013': '平局', '周六014': '客胜', '周六015': '客胜', '周六016': '主胜',
    '周六017': '主胜', '周六018': '主胜', '周六019': '客胜', '周六020': '主胜',
    '周六021': '主胜', '周六022': '客胜', '周六023': '平局', '周六024': '主胜',
    '周六025': '客胜', '周六026': '主胜', '周六027': '客胜', '周六028': '客胜',
    '周六029': '客胜', '周六030': '客胜', '周六031': '主胜', '周六032': '客胜',
}

# ====== V4预测结果 (赔率变化分析) ======
# 基于赔率分析工具_v4.py的预测结果
v4_predictions = {
    '周六001': '主胜', '周六002': '客胜', '周六003': '主胜', '周六004': '主胜',  # 不同
    '周六005': '客胜', '周六006': '平局', '周六007': '客胜', '周六008': '主胜',
    '周六009': '客胜', '周六010': '客胜', '周六011': '主胜', '周六012': '主胜',
    '周六013': '平局', '周六014': '客胜', '周六015': '客胜', '周六016': '主胜',
    '周六017': '主胜', '周六018': '主胜', '周六019': '客胜', '周六020': '主胜',
    '周六021': '主胜', '周六022': '客胜', '周六023': '平局', '周六024': '主胜',
    '周六025': '客胜', '周六026': '主胜', '周六027': '客胜', '周六028': '客胜',
    '周六029': '客胜', '周六030': '客胜', '周六031': '主胜', '周六032': '客胜',
}

# ===== 对比分析 =====
print("=" * 70)
print("V3(欧赔核心思维) vs V4(赔率变化分析) 预测对比 - 3.14")
print("=" * 70)

same_predictions = []
different_predictions = []

for match_id in v3_predictions.keys():
    v3 = v3_predictions[match_id]
    v4 = v4_predictions.get(match_id, '')
    actual = actual_314.get(match_id, '')
    
    if v3 == v4:
        same_predictions.append({
            'id': match_id, 'v3': v3, 'v4': v4, 'actual': actual,
            'correct': v3 == actual
        })
    else:
        different_predictions.append({
            'id': match_id, 'v3': v3, 'v4': v4, 'actual': actual
        })

# 打印预测相同的比赛
print(f"\n【预测相同的比赛】共 {len(same_predictions)} 场")
print("-" * 70)
print(f"{'编号':<8} {'V3预测':<10} {'V4预测':<10} {'实际结果':<10} {'正确?'}")
print("-" * 70)

same_correct = 0
for m in same_predictions:
    correct = "O" if m['correct'] else "X"
    if m['correct']:
        same_correct += 1
    print(f"{m['id']:<8} {m['v3']:<10} {m['v4']:<10} {m['actual']:<10} {correct}")

same_accuracy = same_correct / len(same_predictions) * 100 if same_predictions else 0
print("-" * 70)
print(f"预测相同准确率: {same_correct}/{len(same_predictions)} = {same_accuracy:.1f}%")

# 打印预测不同的比赛
print(f"\n【预测不同的比赛】共 {len(different_predictions)} 场")
print("-" * 70)
for m in different_predictions:
    # 判断谁正确
    v3_correct = "O" if m['v3'] == m['actual'] else "X"
    v4_correct = "O" if m['v4'] == m['actual'] else "X"
    
    print(f"\n{m['id']}:")
    print(f"  V3(欧赔核心): {m['v3']} {v3_correct}")
    print(f"  V4(赔率变化): {m['v4']} {v4_correct}")
    print(f"  实际结果: {m['actual']}")

# 总体统计
print("\n" + "=" * 70)
print("【总体统计】")
print("=" * 70)

# V3总体准确率
v3_total_correct = sum(1 for m in same_predictions if m['correct'])
v3_total = len(same_predictions)
v3_accuracy = v3_total_correct / v3_total * 100 if v3_total else 0

# V4总体准确率
v4_total_correct = sum(1 for m in same_predictions if m['v4'] == m['actual'])
v4_accuracy = v4_total_correct / v3_total * 100 if v3_total else 0

print(f"V3(欧赔核心思维) 总体准确率: {v3_total_correct}/{v3_total} = {v3_accuracy:.1f}%")
print(f"V4(赔率变化分析) 总体准确率: {v4_total_correct}/{v3_total} = {v4_accuracy:.1f}%")

# 分析分歧比赛
print("\n【分歧比赛分析】")
if different_predictions:
    v3_wins = sum(1 for m in different_predictions if m['v3'] == m['actual'])
    v4_wins = sum(1 for m in different_predictions if m['v4'] == m['actual'])
    print(f"分歧时V3正确: {v3_wins}/{len(different_predictions)}")
    print(f"分歧时V4正确: {v4_wins}/{len(different_predictions)}")
else:
    print("无分歧比赛")
