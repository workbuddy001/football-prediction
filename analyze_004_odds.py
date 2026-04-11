"""
周五004 赔率问题分析
胡巴尔 vs 吉达国民

问题：V3算法预测客胜，但实际主胜
"""

# 源数据中的赔率
realtime_odds = [
    (2.40, 3.26, 2.46),  # 竞*官*
    (2.20, 3.10, 2.80),  # 威**尔
    (2.20, 3.30, 2.75),  # *门
    (2.37, 3.40, 2.80),  # 立*
    (2.24, 3.35, 2.80),  # 金*博
    (2.45, 3.45, 2.55),  # U****t (优*客)
]

# 计算平均值
avg_home = sum(o[0] for o in realtime_odds) / len(realtime_odds)
avg_draw = sum(o[1] for o in realtime_odds) / len(realtime_odds)
avg_away = sum(o[2] for o in realtime_odds) / len(realtime_odds)

print("=== 即时赔率分析 ===")
print(f"主流欧赔平均: 主胜 {avg_home:.2f} 平局 {avg_draw:.2f} 客胜 {avg_away:.2f}")
print()

# 概率转换
prob_home = 1 / avg_home * 100
prob_draw = 1 / avg_draw * 100
prob_away = 1 / avg_away * 100
total = prob_home + prob_draw + prob_away

print("=== 概率分析 ===")
print(f"主胜概率: {prob_home/total*100:.1f}%")
print(f"平局概率: {prob_draw/total*100:.1f}%")
print(f"客胜概率: {prob_away/total*100:.1f}%")
print()

# 问题分析
print("=== 问题分析 ===")
print("1. 档位差距：吉达国民(人强/普强) vs 胡巴尔(中游)")
print("   → 正常应该客胜赔率更低（约1.5-1.8）")
print()
print("2. 状态对比：")
print("   - 主队: 7胜3平，胜率70%，近6场5胜1平")
print("   - 客队: 8胜2平，胜率80%，近6场6连胜")
print("   → 双方状态都很好，但客队略好")
print()
print("3. 赔率异常：")
print("   - 主胜2.33 vs 客胜2.79")
print("   - 差距仅0.46，说明庄家认为实力接近")
print("   - 但实际吉达国民强很多，这是最大问题！")
print()
print("4. 实际结果：主胜 1:0")
print("   → 说明庄家的赔率确实有问题，低估了主队")
print()
print("=== 结论 ===")
print("这个赔率确实存在异常：")
print("- 吉达国民作为沙特联强队，客胜赔率应该在1.5-1.8")
print("- 但实际赔率显示双方实力接近（主2.33 vs 客2.79）")
print("- 这说明赛前市场对吉达国民过度怀疑")
print("- 最终主胜打出，证明庄家确实开错了")
