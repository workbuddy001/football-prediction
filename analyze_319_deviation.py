"""
3.19 比赛 - 偏离度分析
"""

# 竞彩赔率数据
matches_data = {
    "周四001": {"match": "中国台女 vs 朝鲜女", "home": 1.72, "draw": 4.65, "away": 3.00},
    "周四002": {"match": "弗赖堡 vs 亨克", "home": 2.41, "draw": 3.38, "away": 2.39},
    "周四003": {"match": "里昂 vs 塞尔塔", "home": 1.53, "draw": 3.65, "away": 4.55},
    "周四004": {"match": "中日德兰 vs 诺丁汉", "home": 2.45, "draw": 3.20, "away": 2.48},
    "周四005": {"match": "拉纳卡 vs 水晶宫", "home": 3.15, "draw": 3.30, "away": 1.91},
    "周四006": {"match": "美因茨 vs 奥洛穆茨", "home": 1.45, "draw": 3.90, "away": 5.20},
    "周四007": {"match": "罗马 vs 博洛尼亚", "home": 1.93, "draw": 3.35, "away": 3.10},
    "周四008": {"match": "波尔图 vs 斯图加特", "home": 1.82, "draw": 3.50, "away": 3.45},
    "周四009": {"match": "维拉 vs 里尔", "home": 1.77, "draw": 3.45, "away": 3.65},
    "周四010": {"match": "贝蒂斯 vs 帕纳辛纳", "home": 2.02, "draw": 3.30, "away": 3.03},
    "周五001": {"match": "西悉尼 vs 阿德莱德", "home": 2.38, "draw": 3.35, "away": 2.48},
    "周五002": {"match": "汉诺威96 vs 不伦瑞克", "home": 2.02, "draw": 3.50, "away": 2.95},
    "周五003": {"match": "卡斯鲁厄 vs 菲尔特", "home": 2.28, "draw": 3.30, "away": 2.70},
    "周五004": {"match": "卡利亚里 vs 那不勒斯", "home": 4.00, "draw": 3.65, "away": 1.66},
    "周五005": {"match": "克莱蒙 vs 圣旺红星", "home": 1.85, "draw": 3.30, "away": 3.55},
    "周五006": {"match": "波城FC vs 蒙彼利埃", "home": 3.10, "draw": 3.20, "away": 2.02},
    "周五007": {"match": "布洛涅 vs 南锡", "home": 2.35, "draw": 3.15, "away": 2.65},
    "周五008": {"match": "赫拉克勒 vs SBV精英", "home": 2.10, "draw": 3.45, "away": 2.80},
    "周五009": {"match": "罗达JC vs 海尔蒙特", "home": 1.75, "draw": 3.65, "away": 3.65},
    "周五010": {"match": "莱红牛 vs 霍芬海姆", "home": 1.62, "draw": 3.90, "away": 4.25},
    "周五011": {"match": "热那亚 vs 乌迪内斯", "home": 2.60, "draw": 3.10, "away": 2.42},
    "周五012": {"match": "朗斯 vs 昂热", "home": 1.50, "draw": 3.70, "away": 5.25},
    "周五013": {"match": "伯恩茅斯 vs 曼联", "home": 3.65, "draw": 3.45, "away": 1.77},
    "周五014": {"match": "普雷斯顿 vs 斯托克城", "home": 2.35, "draw": 3.20, "away": 2.65},
    "周五015": {"match": "比利亚雷 vs 皇家社会", "home": 2.10, "draw": 3.35, "away": 2.90},
    "周五016": {"match": "阿马多拉 vs 卡萨皮亚", "home": 2.48, "draw": 2.95, "away": 2.60},
}

# 实际实力
strength_info = {
    "周四001": "客强很多",
    "周四002": "接近",
    "周四003": "主强",
    "周四004": "接近",
    "周四005": "客强",
    "周四006": "主强",
    "周四007": "主强",
    "周四008": "主强",
    "周四009": "主强",
    "周四010": "接近",
    "周五001": "接近",
    "周五002": "主强",
    "周五003": "接近",
    "周五004": "客强",
    "周五005": "主强",
    "周五006": "客强",
    "周五007": "接近",
    "周五008": "主强",
    "周五009": "主强",
    "周五010": "主强",
    "周五011": "接近",
    "周五012": "主强",
    "周五013": "客强",
    "周五014": "接近",
    "周五015": "接近",
    "周五016": "接近",
}

def calculate_confidence(home, draw, away):
    """根据赔率计算置信度和胜率"""
    total = home + draw + away
    home_rate = (total / home) * 100 / 3
    draw_rate = (total / draw) * 100 / 3
    away_rate = (total / away) * 100 / 3
    total_rate = home_rate + draw_rate + away_rate
    home_rate = home_rate / total_rate * 100
    draw_rate = draw_rate / total_rate * 100
    away_rate = away_rate / total_rate * 100
    max_rate = max(home_rate, draw_rate, away_rate)
    return max_rate, home_rate, draw_rate, away_rate

results = []

for mid, data in matches_data.items():
    confidence, home_rate, draw_rate, away_rate = calculate_confidence(data['home'], data['draw'], data['away'])

    # 赔率预测
    if home_rate >= draw_rate and home_rate >= away_rate:
        odds_pred = "主胜"
    elif away_rate >= home_rate and away_rate >= draw_rate:
        odds_pred = "客胜"
    else:
        odds_pred = "平局"

    rate_diff = home_rate - away_rate
    
    # 计算偏离度 = |胜率差| / 置信度
    if confidence > 0:
        deviation = abs(rate_diff) / confidence
    else:
        deviation = 0
    
    # 实际实力修正
    strength = strength_info.get(mid, "接近")
    if "客强" in strength and odds_pred == "主胜":
        final_pred = "客胜"
    elif "主强" in strength and odds_pred == "客胜":
        final_pred = "主胜"
    else:
        final_pred = odds_pred
    
    # 判断偏离类型
    if deviation > 0.7:
        deviation_type = "偏离过高"
    elif deviation < 0.3:
        deviation_type = "偏离过低"
    else:
        deviation_type = "正常"

    results.append({
        'id': mid,
        'match': data['match'],
        'confidence': confidence,
        'rate_diff': rate_diff,
        'deviation': deviation,
        'deviation_type': deviation_type,
        'odds_pred': odds_pred,
        'final_pred': final_pred,
        'strength': strength,
    })

# 按偏离度排序
results.sort(key=lambda x: x['deviation'], reverse=True)

print("=" * 150)
print("3.19 比赛 - 偏离度分析")
print("=" * 150)

print(f"\n| 编号 | 对阵 | 置信度 | 胜率差 | 偏离度 | 偏离类型 | 预测 |")
print(f"|------|------|--------|--------|--------|----------|------|")

for r in results:
    print(f"| {r['id']} | {r['match']} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {r['deviation']:.2f} | {r['deviation_type']} | {r['final_pred']} |")

# 偏离过高
high_dev = [r for r in results if r['deviation_type'] == "偏离过高"]
high_dev.sort(key=lambda x: x['deviation'], reverse=True)

print("\n" + "=" * 150)
print("偏离过高的比赛（偏离度 > 0.7）")
print("=" * 150)
print(f"\n| 编号 | 对阵 | 置信度 | 胜率差 | 偏离度 | 预测 | 备注 |")
print(f"|------|------|--------|--------|--------|------|------|")

for r in high_dev:
    note = "实力修正" if r['odds_pred'] != r['final_pred'] else ""
    print(f"| {r['id']} | {r['match']} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {r['deviation']:.2f} | {r['final_pred']} | {note} |")

# 偏离过低
low_dev = [r for r in results if r['deviation_type'] == "偏离过低"]
low_dev.sort(key=lambda x: x['deviation'])

print("\n" + "=" * 150)
print("偏离过低的比赛（偏离度 < 0.3）")
print("=" * 150)
print(f"\n| 编号 | 对阵 | 置信度 | 胜率差 | 偏离度 | 预测 | 备注 |")
print(f"|------|------|--------|--------|--------|------|------|")

for r in low_dev:
    note = "实力修正" if r['odds_pred'] != r['final_pred'] else ""
    print(f"| {r['id']} | {r['match']} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {r['deviation']:.2f} | {r['final_pred']} | {note} |")

# 正常偏离
normal_dev = [r for r in results if r['deviation_type'] == "正常"]
normal_dev.sort(key=lambda x: x['confidence'], reverse=True)

print("\n" + "=" * 150)
print("正常偏离的比赛（0.3 ≤ 偏离度 ≤ 0.7）")
print("=" * 150)
print(f"\n| 编号 | 对阵 | 置信度 | 胜率差 | 偏离度 | 预测 |")
print(f"|------|------|--------|--------|--------|------|")

for r in normal_dev:
    print(f"| {r['id']} | {r['match']} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {r['deviation']:.2f} | {r['final_pred']} |")

print("\n" + "=" * 150)
print("统计")
print("=" * 150)
print(f"\n偏离过高: {len(high_dev)}场")
print(f"偏离过低: {len(low_dev)}场")
print(f"正常偏离: {len(normal_dev)}场")
