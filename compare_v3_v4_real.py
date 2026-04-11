# -*- coding: utf-8 -*-
import pandas as pd
import re

# 读取V4预测
df = pd.read_excel('3.14_比赛预测汇总.xlsx')

# 实际结果
actual = {
    '周六001': '主胜', '周六002': '客胜', '周六003': '主胜', '周六004': '客胜',
    '周六005': '客胜', '周六006': '平局', '周六007': '客胜', '周六008': '平局',
    '周六009': '客胜', '周六010': '客胜', '周六011': '主胜', '周六012': '主胜',
    '周六013': '平局', '周六014': '平局', '周六015': '平局', '周六016': '平局',
    '周六017': '主胜', '周六018': '主胜', '周六019': '平局', '周六020': '主胜',
    '周六021': '主胜', '周六022': '客胜', '周六023': '平局', '周六024': '主胜',
    '周六025': '客胜', '周六026': '主胜', '周六027': '客胜', '周六028': '客胜',
    '周六029': '客胜', '周六030': '客胜', '周六031': '主胜', '周六032': '平局',
}

# V3预测 (从analyze_oupei_v3.py)
v3_pred = {
    '周六001': '主胜', '周六002': '客胜', '周六003': '主胜', '周六004': '客胜',
    '周六005': '客胜', '周六006': '平局', '周六007': '客胜', '周六008': '主胜',
    '周六009': '客胜', '周六010': '客胜', '周六011': '主胜', '周六012': '主胜',
    '周六013': '平局', '周六014': '客胜', '周六015': '客胜', '周六016': '主胜',
    '周六017': '主胜', '周六018': '主胜', '周六019': '客胜', '周六020': '主胜',
    '周六021': '主胜', '周六022': '客胜', '周六023': '平局', '周六024': '主胜',
    '周六025': '客胜', '周六026': '主胜', '周六027': '客胜', '周六028': '客胜',
    '周六029': '客胜', '周六030': '客胜', '周六031': '主胜', '周六032': '客胜',
}

def normalize_prediction(pred):
    """将预测结果标准化"""
    if pd.isna(pred):
        return ''
    pred = str(pred)
    # 提取结果类型
    if '主胜' in pred:
        return '主胜'
    elif '客胜' in pred:
        return '客胜'
    elif '平' in pred:
        return '平局'
    return ''

print("=" * 80)
print("V3(欧赔核心思维) vs V4(赔率变化分析) 预测对比 - 3.14")
print("=" * 80)
print(f"{'编号':<8} {'V3预测':<10} {'V4预测':<10} {'实际':<10} {'V3正确':<8} {'V4正确':<8}")
print("-" * 80)

v3_correct = 0
v4_correct = 0
same_count = 0
diff_count = 0
diff_details = []

for idx, row in df.iterrows():
    match_id = row['编号']
    v4_pred_raw = row['预测']
    v4_pred = normalize_prediction(v4_pred_raw)
    actual_result = actual.get(match_id, '')
    v3_result = v3_pred.get(match_id, '')
    
    v3_ok = "O" if v3_result == actual_result else "X"
    v4_ok = "O" if v4_pred == actual_result else "X"
    
    if v3_result == actual_result:
        v3_correct += 1
    if v4_pred == actual_result:
        v4_correct += 1
    
    if v3_result == v4_pred:
        same_count += 1
        mark = ""
    else:
        diff_count += 1
        mark = " <-- DIFF"
        diff_details.append({
            'id': match_id, 'v3': v3_result, 'v4': v4_pred, 'actual': actual_result
        })
    
    print(f"{match_id:<8} {v3_result:<10} {v4_pred:<10} {actual_result:<10} {v3_ok:<8} {v4_ok:<8}{mark}")

print("-" * 80)
print(f"总场次: {len(df)}")
print(f"V3(欧赔核心)正确: {v3_correct}/{len(df)} = {v3_correct/len(df)*100:.1f}%")
print(f"V4(赔率变化)正确: {v4_correct}/{len(df)} = {v4_correct/len(df)*100:.1f}%")
print(f"预测相同: {same_count}场 ({same_count/len(df)*100:.1f}%)")
print(f"预测不同: {diff_count}场")

# 分歧比赛详细分析
if diff_details:
    print("\n" + "=" * 80)
    print("【分歧比赛详细分析】")
    print("=" * 80)
    v3_wins = 0
    v4_wins = 0
    for m in diff_details:
        v3_result = "O" if m['v3'] == m['actual'] else "X"
        v4_result = "O" if m['v4'] == m['actual'] else "X"
        if m['v3'] == m['actual']:
            v3_wins += 1
        if m['v4'] == m['actual']:
            v4_wins += 1
        print(f"{m['id']}: V3={m['v3']}{v3_result}, V4={m['v4']}{v4_result}, 实际={m['actual']}")
    
    print(f"\n分歧时V3正确: {v3_wins}/{len(diff_details)}")
    print(f"分歧时V4正确: {v4_wins}/{len(diff_details)}")
