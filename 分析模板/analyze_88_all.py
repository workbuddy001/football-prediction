import re, os, sys
sys.path.append('.')
from final_retrospect import *

# 有末尾88的比赛ID（从之前的分析得到）
matches_with_88 = [
    '周五002', '周五003', '周五004', '周五005',
    '周六003', '周六005', '周六010', '周六013', 
    '周六017', '周六019', '周六021', '周六024', 
    '周六030', '周六032', '周日004', '周日008', 
    '周日013', '周日015', '周日025', '周日026'
]

# 实际结果
actual = {
    '周五002': '平局', '周五003': '客胜', '周五004': '客胜', '周五005': '客胜',
    '周六003': '主胜', '周六005': '平局', '周六010': '平局', '周六013': '平局',
    '周六017': '客胜', '周六019': '平局', '周六021': '平局', '周六024': '客胜',
    '周六032': '客胜', '周日004': '客胜', '周日008': '客胜', '周日013': '客胜',
    '周日015': '客胜', '周日025': '平局', '周日026': '客胜',
}

print('有末尾88的比赛 - V7预测 vs 实际:')
correct = 0
for mid in matches_with_88:
    # 找到对应比赛
    for folder, day in [(r'd:\work\workbuddy\足球预测\分析模板\3.13', '周五'),
                        (r'd:\work\workbuddy\足球预测\分析模板\3.14', '周六'),
                        (r'd:\work\workbuddy\足球预测\分析模板\3.15', '周日')]:
        for f in os.listdir(folder):
            if not f.endswith('_源数据.md'): continue
            if mid in f:
                filepath = os.path.join(folder, f)
                data = extract_odds_from_file(filepath)
                result = analyze_match_v7(data)
                if result:
                    v7_pred = {'home': '主胜', 'draw': '平局', 'away': '客胜'}[result['choice']]
                    actual_result = actual.get(mid, '')
                    is_correct = '[对]' if v7_pred == actual_result else '[错]'
                    if v7_pred == actual_result:
                        correct += 1
                    print(f'{mid}: V7预测{v7_pred}({result["confidence"]:.0f}%) vs 实际{actual_result} {is_correct}')
                    break
print(f'\\n有末尾88的比赛: {len(matches_with_88)}场, V7正确:{correct}场, 命中率:{correct/len(matches_with_88)*100:.1f}%')
