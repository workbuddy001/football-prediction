"""
3.19 比赛 - 从源数据提取分析
"""

# 竞彩赔率数据 (从各源数据文件提取)
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

# 8变化数据 (从源数据提取的趋势总结)
eight_changes = {
    "周四001": {"home": 0, "draw": 0, "away": 0},  # 朝鲜女超强
    "周四002": {"home": -4, "draw": -1, "away": -2},
    "周四003": {"home": 0, "draw": 0, "away": 0},
    "周四004": {"home": 0, "draw": 0, "away": 0},
    "周四005": {"home": 0, "draw": 0, "away": 0},
    "周四006": {"home": 0, "draw": 0, "away": 0},
    "周四007": {"home": 0, "draw": 0, "away": 0},
    "周四008": {"home": 0, "draw": 0, "away": 0},
    "周四009": {"home": 0, "draw": 0, "away": 0},
    "周四010": {"home": 0, "draw": 0, "away": 0},  # 贝蒂斯主胜被强化
    "周五001": {"home": 0, "draw": 0, "away": 0},
    "周五002": {"home": 0, "draw": 0, "away": 0},
    "周五003": {"home": 0, "draw": 0, "away": 0},
    "周五004": {"home": 0, "draw": 0, "away": 0},
    "周五005": {"home": 0, "draw": 0, "away": 0},
    "周五006": {"home": 0, "draw": 0, "away": 0},
    "周五007": {"home": 0, "draw": 0, "away": 0},
    "周五008": {"home": 0, "draw": 0, "away": 0},
    "周五009": {"home": 0, "draw": 0, "away": 0},
    "周五010": {"home": 0, "draw": 0, "away": 0},
    "周五011": {"home": 0, "draw": 0, "away": 0},
    "周五012": {"home": 0, "draw": 0, "away": 0},
    "周五013": {"home": 0, "draw": 0, "away": 0},
    "周五014": {"home": 0, "draw": 0, "away": 0},
    "周五015": {"home": 0, "draw": 0, "away": 0},
    "周五016": {"home": 0, "draw": 0, "away": 0},
}

def calculate_confidence(home, draw, away):
    """根据赔率计算置信度和胜率"""
    total = home + draw + away
    home_rate = (total / home) * 100 / 3
    draw_rate = (total / draw) * 100 / 3
    away_rate = (total / away) * 100 / 3

    # 归一化
    total_rate = home_rate + draw_rate + away_rate
    home_rate = home_rate / total_rate * 100
    draw_rate = draw_rate / total_rate * 100
    away_rate = away_rate / total_rate * 100

    # 置信度 = 最高胜率
    max_rate = max(home_rate, draw_rate, away_rate)

    return max_rate, home_rate, draw_rate, away_rate

def predict(max_rate, home_rate, away_rate):
    """根据置信度和胜率预测"""
    rate_diff = home_rate - away_rate

    if max_rate == home_rate:
        option = "主胜"
    elif max_rate == away_rate:
        option = "客胜"
    else:
        option = "平局"

    return option, rate_diff

results = []

for mid, data in matches_data.items():
    confidence, home_rate, draw_rate, away_rate = calculate_confidence(data['home'], data['draw'], data['away'])
    prediction, rate_diff = predict(confidence, home_rate, away_rate)

    ec = eight_changes.get(mid, {"home": 0, "draw": 0, "away": 0})
    total_change = abs(ec['home']) + abs(ec['draw']) + abs(ec['away'])
    is_moderate = total_change <= 2

    results.append({
        'id': mid,
        'match': data['match'],
        'home': data['home'],
        'draw': data['draw'],
        'away': data['away'],
        'confidence': confidence,
        'home_rate': home_rate,
        'draw_rate': draw_rate,
        'away_rate': away_rate,
        'rate_diff': rate_diff,
        'home_change': ec['home'],
        'draw_change': ec['draw'],
        'away_change': ec['away'],
        'total_change': total_change,
        'is_moderate': is_moderate,
        'prediction': prediction,
    })

print("=" * 130)
print("3.19 比赛 - 8中庸分析")
print("=" * 130)

print(f"\n| 编号 | 对阵 | 赔率(胜-平-负) | 置信度 | 胜率差 | 8变化 | 总变化 | 8中庸? | 预测 |")
print(f"|------|------|----------------|--------|--------|--------|--------|--------|------|")

for r in results:
    odds = f"{r['home']:.2f}-{r['draw']:.2f}-{r['away']:.2f}"
    eight_change = f"[{r['home_change']:+d},{r['draw_change']:+d},{r['away_change']:+d}]"
    moderate = "是" if r['is_moderate'] else "否"
    print(f"| {r['id']} | {r['match']} | {odds} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_change} | {r['total_change']} | {moderate} | {r['prediction']} |")

# 筛选8中庸比赛
moderate_matches = [r for r in results if r['is_moderate']]

print("\n" + "=" * 130)
print("8中庸比赛（|总8变化| ≤ 2）- 按置信度排序")
print("=" * 130)

moderate_matches.sort(key=lambda x: x['confidence'], reverse=True)

print(f"\n| 排名 | 编号 | 对阵 | 置信度 | 胜率差 | 预测 |")
print(f"|------|------|------|--------|--------|------|")

for i, m in enumerate(moderate_matches, 1):
    print(f"| {i} | {m['id']} | {m['match']} | {m['confidence']:.1f}% | {m['rate_diff']:+.1f}% | {m['prediction']} |")

print("\n" + "=" * 130)
print("统计")
print("=" * 130)
print(f"\n8中庸比赛: {len(moderate_matches)}场")
print(f"非8中庸比赛: {len(results) - len(moderate_matches)}场")
