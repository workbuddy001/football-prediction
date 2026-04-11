"""
3.19 比赛 - 8中庸分析
"""

# 从源数据提取的赔率数据
matches_319 = [
    {"id": "周四001", "match": "中国台女 vs 朝鲜女", "home_rate": 35, "away_rate": 50, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周四002", "match": "弗赖堡 vs 亨克", "home_rate": 45, "away_rate": 35, "home_eight_change": -4, "draw_eight_change": -1, "away_eight_change": -2},
    {"id": "周四003", "match": "里昂 vs 塞尔塔", "home_rate": 55, "away_rate": 30, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周四004", "match": "中日德兰 vs 诺丁汉", "home_rate": 40, "away_rate": 45, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周四005", "match": "拉纳卡 vs 水晶宫", "home_rate": 30, "away_rate": 55, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周四006", "match": "美因茨 vs 奥洛穆茨", "home_rate": 60, "away_rate": 25, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周四007", "match": "罗马 vs 博洛尼亚", "home_rate": 45, "away_rate": 40, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周四008", "match": "波尔图 vs 斯图加特", "home_rate": 50, "away_rate": 35, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周四009", "match": "维拉 vs 里尔", "home_rate": 55, "away_rate": 30, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周四010", "match": "贝蒂斯 vs 帕纳辛纳", "home_rate": 65, "away_rate": 20, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周五001", "match": "西悉尼 vs 阿德莱德", "home_rate": 40, "away_rate": 45, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周五002", "match": "汉诺威96 vs 不伦瑞克", "home_rate": 50, "away_rate": 35, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周五003", "match": "卡斯鲁厄 vs 菲尔特", "home_rate": 45, "away_rate": 40, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周五004", "match": "卡利亚里 vs 那不勒斯", "home_rate": 30, "away_rate": 55, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周五005", "match": "克莱蒙 vs 圣旺红星", "home_rate": 55, "away_rate": 30, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周五006", "match": "波城FC vs 蒙彼利埃", "home_rate": 35, "away_rate": 50, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周五007", "match": "布洛涅 vs 南锡", "home_rate": 40, "away_rate": 45, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周五008", "match": "赫拉克勒 vs SBV精英", "home_rate": 50, "away_rate": 35, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周五009", "match": "罗达JC vs 海尔蒙特", "home_rate": 55, "away_rate": 30, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周五010", "match": "莱红牛 vs 霍芬海姆", "home_rate": 60, "away_rate": 30, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周五011", "match": "热那亚 vs 乌迪内斯", "home_rate": 40, "away_rate": 45, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周五012", "match": "朗斯 vs 昂热", "home_rate": 60, "away_rate": 25, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周五013", "match": "伯恩茅斯 vs 曼联", "home_rate": 35, "away_rate": 50, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周五014", "match": "普雷斯顿 vs 斯托克城", "home_rate": 45, "away_rate": 40, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周五015", "match": "比利亚雷 vs 皇家社会", "home_rate": 50, "away_rate": 35, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
    {"id": "周五016", "match": "阿马多拉 vs 卡萨皮亚", "home_rate": 45, "away_rate": 40, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0},
]

def analyze_match(m):
    home_change = m['home_eight_change']
    draw_change = m['draw_eight_change']
    away_change = m['away_eight_change']

    total_change = abs(home_change) + abs(draw_change) + abs(away_change)
    is_moderate = total_change <= 2

    # 计算胜率差
    rate_diff = m['home_rate'] - m['away_rate']

    # 根据胜率差确定预测
    if rate_diff > 15:
        prediction = "主胜"
    elif rate_diff < -15:
        prediction = "客胜"
    elif rate_diff > 5:
        prediction = "主胜"
    elif rate_diff < -5:
        prediction = "客胜"
    else:
        prediction = "平局"

    return {
        'id': m['id'],
        'match': m['match'],
        'home_rate': m['home_rate'],
        'away_rate': m['away_rate'],
        'rate_diff': rate_diff,
        'home_change': home_change,
        'draw_change': draw_change,
        'away_change': away_change,
        'total_change': total_change,
        'is_moderate': is_moderate,
        'prediction': prediction,
    }

print("=" * 120)
print("3.19 比赛 - 8中庸分析")
print("=" * 120)

results = [analyze_match(m) for m in matches_319]

print(f"\n| 编号 | 对阵 | 胜率差 | 8变化 | 总变化 | 8中庸? | 预测 |")
print(f"|------|------|--------|--------|--------|--------|------|")

for r in results:
    eight_change = f"[{r['home_change']:+d},{r['draw_change']:+d},{r['away_change']:+d}]"
    moderate = "是" if r['is_moderate'] else "否"
    print(f"| {r['id']} | {r['match']} | {r['rate_diff']:+d}% | {eight_change} | {r['total_change']} | {moderate} | {r['prediction']} |")

# 筛选8中庸比赛
moderate_matches = [r for r in results if r['is_moderate']]

print("\n" + "=" * 120)
print("8中庸比赛（|总8变化| ≤ 2）")
print("=" * 120)

# 按胜率差绝对值排序（越大概率越大）
moderate_matches.sort(key=lambda x: abs(x['rate_diff']), reverse=True)

print(f"\n| 排名 | 编号 | 对阵 | 胜率差 | 8变化 | 预测 |")
print(f"|------|------|------|--------|--------|------|")

for i, m in enumerate(moderate_matches, 1):
    eight_change = f"[{m['home_change']:+d},{m['draw_change']:+d},{m['away_change']:+d}]"
    print(f"| {i} | {m['id']} | {m['match']} | {m['rate_diff']:+d}% | {eight_change} | {m['prediction']} |")

print("\n" + "=" * 120)
print("统计")
print("=" * 120)
print(f"\n8中庸比赛: {len(moderate_matches)}场")
print(f"非8中庸比赛: {len(results) - len(moderate_matches)}场")
