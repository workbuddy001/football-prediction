"""
3.19 比赛 - 修正后的分析（考虑实际实力）
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

# 实际实力评估（基于球队近况和历史交锋）
strength_analysis = {
    "周四001": {"actual_strength": "客强很多", "reason": "朝鲜女进42球，中国台女进14球，历史交锋朝鲜2战全胜12:0"},
    "周四002": {"actual_strength": "接近", "reason": "弗赖堡近10场2胜2平6负，亨克7胜0平3负，亨克状态更好"},
    "周四003": {"actual_strength": "主强", "reason": "里昂主场强势，塞尔塔实力较弱"},
    "周四004": {"actual_strength": "接近", "reason": "中日德兰 vs 诺丁汉，英超球队诺丁汉实力更强但客场"},
    "周四005": {"actual_strength": "客强", "reason": "水晶宫是英超球队，拉纳卡是塞浦路斯球队"},
    "周四006": {"actual_strength": "主强", "reason": "美因茨是德甲，奥洛穆茨是捷克球队"},
    "周四007": {"actual_strength": "主强", "reason": "罗马是意甲强队，博洛尼亚中游"},
    "周四008": {"actual_strength": "主强", "reason": "波尔图是葡超豪门，斯图加特是德甲中游"},
    "周四009": {"actual_strength": "主强", "reason": "维拉是英超强队，里尔是法甲中游"},
    "周四010": {"actual_strength": "接近", "reason": "贝蒂斯西甲中游，帕纳辛纳是希腊球队但首回合获胜"},
    "周五001": {"actual_strength": "接近", "reason": "澳超中游对决"},
    "周五002": {"actual_strength": "主强", "reason": "汉诺威是德乙中上，不伦瑞克是德乙中下"},
    "周五003": {"actual_strength": "接近", "reason": "德乙中游对决"},
    "周五004": {"actual_strength": "客强", "reason": "那不勒斯是意甲强队，卡利亚里保级队"},
    "周五005": {"actual_strength": "主强", "reason": "克莱蒙是法甲中游，圣旺红星是法乙"},
    "周五006": {"actual_strength": "客强", "reason": "蒙彼利埃是法甲中游，波城FC是法丙升班马"},
    "周五007": {"actual_strength": "接近", "reason": "法乙中游对决"},
    "周五008": {"actual_strength": "主强", "reason": "赫拉克勒是荷甲中游，SBV精英是荷乙"},
    "周五009": {"actual_strength": "主强", "reason": "罗达JC是荷甲中游，海尔蒙特是荷甲倒数第一"},
    "周五010": {"actual_strength": "主强", "reason": "莱红牛是德甲强队，霍芬海姆德甲中游"},
    "周五011": {"actual_strength": "接近", "reason": "意甲中游对决"},
    "周五012": {"actual_strength": "主强", "reason": "朗斯是法甲中上，昂热是法甲倒数第一"},
    "周五013": {"actual_strength": "客强", "reason": "曼联是英超强队，伯恩茅斯是保级队"},
    "周五014": {"actual_strength": "接近", "reason": "英冠中游对决"},
    "周五015": {"actual_strength": "接近", "reason": "西甲中游对决"},
    "周五016": {"actual_strength": "接近", "reason": "葡超中游对决"},
}

def calculate_confidence(home, draw, away):
    """根据赔率计算置信度"""
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

def predict_based_on_strength(odds_prediction, strength_info):
    """根据实际实力修正预测"""
    strength = strength_info.get("actual_strength", "接近")

    # 如果赔率和实力一致，直接用赔率预测
    # 如果不一致，需要修正
    if "客强" in strength and odds_prediction == "主胜":
        return "客胜", "实力修正"
    elif "主强" in strength and odds_prediction == "客胜":
        return "主胜", "实力修正"
    else:
        return odds_prediction, "赔率一致"

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

    # 8变化
    total_change = 0
    is_moderate = True

    # 根据实力修正
    final_pred, adjust_type = predict_based_on_strength(odds_pred, strength_analysis.get(mid, {}))

    results.append({
        'id': mid,
        'match': data['match'],
        'confidence': confidence,
        'rate_diff': rate_diff,
        'odds_pred': odds_pred,
        'strength': strength_analysis.get(mid, {}).get("actual_strength", "接近"),
        'final_pred': final_pred,
        'adjust': adjust_type,
        'is_moderate': is_moderate,
    })

print("=" * 140)
print("3.19 比赛 - 修正后分析（考虑实际实力）")
print("=" * 140)

print(f"\n| 编号 | 对阵 | 置信度 | 赔率预测 | 实际实力 | 修正后预测 | 调整 |")
print(f"|------|------|--------|----------|----------|------------|------|")

for r in results:
    print(f"| {r['id']} | {r['match']} | {r['confidence']:.1f}% | {r['odds_pred']} | {r['strength']} | {r['final_pred']} | {r['adjust']} |")

# 筛选高置信度比赛
high_conf = [r for r in results if r['confidence'] >= 55]
high_conf.sort(key=lambda x: x['confidence'], reverse=True)

print("\n" + "=" * 140)
print("高置信度比赛（>=55%）- 按置信度排序")
print("=" * 140)

print(f"\n| 排名 | 编号 | 对阵 | 置信度 | 胜率差 | 实际实力 | 预测 |")
print(f"|------|------|------|--------|--------|----------|------|")

for i, r in enumerate(high_conf, 1):
    print(f"| {i} | {r['id']} | {r['match']} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {r['strength']} | {r['final_pred']} |")
