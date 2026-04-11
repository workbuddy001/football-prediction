# -*- coding: utf-8 -*-
"""
3.16 预测结果验证
"""

# 实际结果
actual_results = {
    '周一001': '客胜',  # 海尔蒙特 0:1 坎布尔
    '周一002': '客胜',  # 克雷莫纳 1:4 佛罗伦萨
    '周一003': '客胜',  # 阿纳西 1:2 特鲁瓦
    '周一004': '平局',  # 布伦特 2:2 狼队
    '周一005': '客胜',  # 朴次茅斯 0:1 德比郡
    '周一006': '平局',  # 巴列卡诺 1:1 莱万特
    '周二001': '客胜',  # 悉尼FC 0:1 墨尔本城
    '周二002': '客胜',  # 中国女 1:2 澳大利女
    '周二003': '平局',  # 金泉尚武 1:1 光州FC
    '周二004': '主胜',  # 里斯本 3:0 博德闪耀
    '周二005': '主胜',  # 沃特福德 3:1 雷克斯
    '周二006': '主胜',  # 阿森纳 2:0 勒沃库森
    '周二007': '客胜',  # 切尔西 0:3 巴黎圣曼
    '周二008': '客胜',  # 曼城 1:2 皇马
}

# 预测结果
predictions = {
    '周一001': ('客胜', '胜率差偏向'),
    '周一002': ('客胜', '胜率差偏向'),
    '周一003': ('平局', '排除法'),
    '周一004': ('主胜', '高置信正向'),
    '周一005': ('客胜', '排除法'),
    '周一006': ('主胜', '高置信正向'),
    '周二001': ('平局', '排除法'),
    '周二002': ('客胜', '高置信正向'),
    '周二004': ('主胜', '高置信正向'),
    '周二005': ('主胜', '高置信正向'),  # 周二005后来补充
    '周二006': ('主胜', '高置信正向'),
    '周二007': ('主胜', '中等置信'),
    '周二008': ('主胜', '高置信正向'),
}

print("=" * 80)
print("3.16 预测 vs 实际 结果验证")
print("=" * 80)

correct = 0
total = 0
results = []

for match_id, (pred, strategy) in predictions.items():
    actual = actual_results.get(match_id, '-')
    is_correct = pred == actual
    if is_correct:
        correct += 1
    total += 1
    
    status = "O" if is_correct else "X"
    print(f"{match_id}: 预测={pred} 实际={actual} {status} [{strategy}]")
    results.append((match_id, pred, actual, is_correct, strategy))

print("\n" + "=" * 80)
print(f"总体准确率: {correct}/{total} = {correct/total*100:.1f}%")

# 按策略统计
print("\n" + "=" * 80)
print("按策略统计")
print("=" * 80)

strategy_stats = {}
for match_id, pred, actual, is_correct, strategy in results:
    if strategy not in strategy_stats:
        strategy_stats[strategy] = {'correct': 0, 'total': 0}
    strategy_stats[strategy]['total'] += 1
    if is_correct:
        strategy_stats[strategy]['correct'] += 1

for strategy, stats in sorted(strategy_stats.items(), key=lambda x: -x[1]['correct']):
    acc = stats['correct'] / stats['total'] * 100 if stats['total'] > 0 else 0
    print(f"{strategy}: {stats['correct']}/{stats['total']} = {acc:.1f}%")

# 高置信度专项
print("\n" + "=" * 80)
print("高置信度(>=55%)专项")
print("=" * 80)

high_conf = [(m, p, a, c) for m, p, a, c, s in results if '高置信' in s]
high_correct = sum(1 for _, _, _, c in high_conf if c)
print(f"高置信度: {high_correct}/{len(high_conf)} = {high_correct/len(high_conf)*100:.1f}%")

# 排除法专项
print("\n" + "=" * 80)
print("排除法专项")
print("=" * 80)

exclusion = [(m, p, a, c) for m, p, a, c, s in results if '排除' in s]
excl_correct = sum(1 for _, _, _, c in exclusion if c)
print(f"排除法: {excl_correct}/{len(exclusion)} = {excl_correct/len(exclusion)*100:.1f}%")

# 问题分析
print("\n" + "=" * 80)
print("【问题分析】")
print("=" * 80)
print("""
1. 高置信度预测错误:
   - 周一004 布伦特vs狼队: 预测主胜，实际平局
   - 周一006 巴列卡诺vs莱万特: 预测主胜，实际平局  
   - 周二007 切尔西vs巴黎: 预测主胜，实际客胜
   - 周二008 曼城vs皇马: 预测主胜，实际客胜
   
   问题: 高置信度时倾向主胜，但实际这些比赛客胜/平局更多
   原因: 胜率差为正时不一定要主胜，需要结合8变化
   
2. 排除法效果:
   - 周一003: 排除平局 → 实际客胜 (错误)
   - 周一005: 排除客胜 → 实际客胜 (错误!)
   - 周二001: 排除平局 → 实际客胜 (错误)
   
   排除法效果不佳，需要改进
""")
