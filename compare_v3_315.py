# -*- coding: utf-8 -*-
"""
V3(欧赔核心思维)预测 vs 3.15实际结果 对比
"""

# 3.15实际结果
actual_315 = {
    '周日001': '主胜', '周日002': '主胜', '周日003': '客胜', '周日004': '平局',
    '周日005': '主胜', '周日006': '客胜', '周日007': '客胜', '周日008': '平局',
    '周日009': '主胜', '周日010': '主胜', '周日011': '主胜', '周日012': '平局',
    '周日013': '平局', '周日014': '主胜', '周日015': '主胜', '周日016': '客胜',
    '周日017': '客胜', '周日018': '主胜', '周日019': '主胜', '周日020': '平局',
    '周日021': '平局', '周日022': '客胜', '周日023': '主胜', '周日024': '平局',
    '周日025': '主胜', '周日026': '主胜', '周日027': '主胜', '周日028': '主胜',
    '周日029': '主胜',
}

# V3预测结果
v3_pred = {
    '周日001': '主胜', '周日002': '主胜', '周日003': '客胜', '周日004': '平局',
    '周日005': '主胜', '周日006': '主胜', '周日007': '平局', '周日008': '主胜',
    '周日009': '平局', '周日010': '主胜', '周日011': '客胜', '周日012': '客胜',
    '周日013': '主胜', '周日014': '主胜', '周日015': '平局', '周日016': '主胜',
    '周日017': '主胜', '周日018': '主胜', '周日019': '平局', '周日020': '平局',
    '周日021': '主胜', '周日022': '主胜', '周日023': '平局', '周日024': '平局',
    '周日025': '主胜', '周日026': '客胜', '周日027': '主胜', '周日028': '主胜',
    '周日029': '主胜',
}

# 对比
print("=" * 90)
print("V3(欧赔核心思维) 预测 vs 3.15 实际结果 对比")
print("=" * 90)
print(f"{'编号':<8} {'V3预测':<10} {'实际结果':<10} {'比分':<8} {'正确?'}")
print("-" * 90)

correct = 0
wrong = 0
b_correct = 0
b_total = 0
c_correct = 0
c_total = 0

# 比分数据
scores = {
    '周日001': '7:0', '周日002': '1:0', '周日003': '1:2', '周日004': '1:1',
    '周日005': '4:1', '周日006': '0:2', '周日007': '0:2', '周日008': '2:2',
    '周日009': '2:1', '周日010': '2:1', '周日011': '3:2', '周日012': '0:0',
    '周日013': '0:0', '周日014': '3:1', '周日015': '3:1', '周日016': '0:1',
    '周日017': '0:2', '周日018': '5:2', '周日019': '1:0', '周日020': '0:0',
    '周日021': '1:1', '周日022': '0:1', '周日023': '2:1', '周日024': '1:1',
    '周日025': '1:0', '周日026': '1:0', '周日027': '3:1', '周日028': '3:0',
    '周日029': '6:0',
}

# 把握度
confidence = {
    '周日001': 'B', '周日002': 'C', '周日003': 'C', '周日004': 'B',
    '周日005': 'C', '周日006': 'C', '周日007': 'C', '周日008': 'C',
    '周日009': 'C', 'Sunday010': 'B', '周日011': 'C', '周日012': 'C',
    '周日013': 'C', '周日014': 'C', '周日015': 'C', '周日016': 'C',
    '周日017': 'C', '周日018': 'B', '周日019': 'C', '周日020': 'B',
    '周日021': 'B', '周日022': 'C', '周日023': 'C', '周日024': 'C',
    '周日025': 'C', '周日026': 'B', '周日027': 'C', '周日028': 'B',
    '周日029': 'B',
}

for match_id in v3_pred.keys():
    v3 = v3_pred[match_id]
    actual = actual_315.get(match_id, '')
    score = scores.get(match_id, '')
    conf = confidence.get(match_id, 'C')
    
    is_correct = v3 == actual
    result = "O" if is_correct else "X"
    
    if is_correct:
        correct += 1
        if conf == 'B':
            b_correct += 1
        else:
            c_correct += 1
    else:
        wrong += 1
        if conf == 'B':
            pass
        else:
            pass
    
    if conf == 'B':
        conf_total = b_total + 1 if True else b_total
    else:
        conf_total = c_total
    
    mark = " *" if conf == 'B' else ""
    print(f"{match_id:<8} {v3:<10} {actual:<10} {score:<8} {result}{mark}")

print("-" * 90)
print(f"总场次: {len(v3_pred)}")
print(f"V3正确: {correct}/{len(v3_pred)} = {correct/len(v3_pred)*100:.1f}%")

# 按把握度统计
print("\n" + "=" * 90)
print("按把握度分类")
print("=" * 90)

# 重新统计
b_matches = [k for k in v3_pred.keys() if confidence.get(k, 'C') == 'B']
c_matches = [k for k in v3_pred.keys() if confidence.get(k, 'C') == 'C']

b_correct = sum(1 for k in b_matches if v3_pred[k] == actual_315[k])
c_correct = sum(1 for k in c_matches if v3_pred[k] == actual_315[k])

print(f"把握度B: {b_correct}/{len(b_matches)} = {b_correct/len(b_matches)*100:.1f}%")
print(f"把握度C: {c_correct}/{len(c_matches)} = {c_correct/len(c_matches)*100:.1f}%")

# 预测分布统计
print("\n" + "=" * 90)
print("预测 vs 实际分布")
print("=" * 90)

v3_counts = {'主胜': 0, '平局': 0, '客胜': 0}
actual_counts = {'主胜': 0, '平局': 0, '客胜': 0}

for k in v3_pred:
    v3_counts[v3_pred[k]] = v3_counts.get(v3_pred[k], 0) + 1
    actual_counts[actual_315[k]] = actual_counts.get(actual_315[k], 0) + 1

print(f"V3预测: 主胜={v3_counts['主胜']}, 平局={v3_counts['平局']}, 客胜={v3_counts['客胜']}")
print(f"实际结果: 主胜={actual_counts['主胜']}, 平局={actual_counts['平局']}, 客胜={actual_counts['客胜']}")
