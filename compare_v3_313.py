# -*- coding: utf-8 -*-
"""
V3(欧赔核心思维)预测 vs 3.13实际结果 对比
"""

# 3.13实际结果
actual_313 = {
    '周五001': '平局', '周五002': '主胜', '周五003': '平局',
    '周五004': '主胜', '周五005': '客胜', '周五006': '平局',
    '周五007': '平局', '周五008': '主胜', '周五009': '主胜',
    '周五010': '主胜', '周五011': '主胜', '周五012': '平局',
}

scores = {
    '周五001': '2:2', '周五002': '2:1', '周五003': '1:1',
    '周五004': '3:2', '周五005': '0:1', '周五006': '1:1',
    '周五007': '1:1', '周五008': '2:0', '周五009': '4:1',
    '周五010': '1:0', '周五011': '2:0', '周五012': '1:1',
}

# V3预测结果
v3_pred = {
    '周五001': ('平局', 'D'),
    '周五002': ('主胜', 'C'),
    '周五003': ('主胜', 'C'),
    '周五004': ('主胜', 'C'),
    '周五005': ('主胜', 'C'),
    '周五006': ('客胜', 'C'),
    '周五007': ('主胜', 'B'),
    '周五008': ('主胜', 'C'),
    '周五009': ('主胜', 'C'),
    '周五010': ('主胜', 'D'),
    '周五011': ('主胜', 'C'),
    '周五012': ('客胜', 'C'),
}

print("=" * 95)
print("V3(欧赔核心思维) 预测 vs 3.13 实际结果 对比")
print("=" * 95)
print(f"{'编号':<8} {'V3预测':<10} {'把握度':<6} {'实际结果':<10} {'比分':<8} {'正确?'}")
print("-" * 95)

correct = 0
b_correct = 0
b_total = 0
c_correct = 0
c_total = 0
d_correct = 0
d_total = 0

for match_id in v3_pred.keys():
    v3, conf = v3_pred[match_id]
    actual = actual_313.get(match_id, '')
    score = scores.get(match_id, '')
    
    is_correct = v3 == actual
    result = "O" if is_correct else "X"
    
    if is_correct:
        correct += 1
        if conf == 'B':
            b_correct += 1
        elif conf == 'C':
            c_correct += 1
        elif conf == 'D':
            d_correct += 1
    
    if conf == 'B':
        b_total += 1
    elif conf == 'C':
        c_total += 1
    elif conf == 'D':
        d_total += 1
    
    mark = " *" if conf == 'B' else ""
    print(f"{match_id:<8} {v3:<10} {conf:<6} {actual:<10} {score:<8} {result}{mark}")

print("-" * 95)
print(f"总场次: {len(v3_pred)}")
print(f"V3正确: {correct}/{len(v3_pred)} = {correct/len(v3_pred)*100:.1f}%")

print("\n" + "=" * 95)
print("按把握度分类")
print("=" * 95)
print(f"把握度B: {b_correct}/{b_total} = {b_correct/b_total*100:.1f}%")
print(f"把握度C: {c_correct}/{c_total} = {c_correct/c_total*100:.1f}%")
print(f"把握度D: {d_correct}/{d_total} = {d_correct/d_total*100:.1f}%")

# 预测分布 vs 实际分布
print("\n" + "=" * 95)
print("预测 vs 实际分布")
print("=" * 95)
v3_counts = {'主胜': 0, '平局': 0, '客胜': 0}
actual_counts = {'主胜': 0, '平局': 0, '客胜': 0}

for k in v3_pred:
    v3_counts[v3_pred[k][0]] = v3_counts.get(v3_pred[k][0], 0) + 1
    actual_counts[actual_313[k]] = actual_counts.get(actual_313[k], 0) + 1

print(f"V3预测: 主胜={v3_counts['主胜']}, 平局={v3_counts['平局']}, 客胜={v3_counts['客胜']}")
print(f"实际结果: 主胜={actual_counts['主胜']}, 平局={actual_counts['平局']}, 客胜={actual_counts['客胜']}")
