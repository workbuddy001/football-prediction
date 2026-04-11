"""
3.10和3.11比赛 - 修正后的完整数据（含V7预测方向）
"""

matches_310 = [
    {"id": "周二001", "match": "印度女 vs 中国台女", "v7": "客胜", "confidence": 65, 
     "home_rate": 40, "away_rate": 60, "home_eight_change": -2, "draw_eight_change": 0, "away_eight_change": -1, "actual": "客胜", "score": "1-3"},
    {"id": "周二002", "match": "日本女 vs 越南女", "v7": "主胜", "confidence": 90, 
     "home_rate": 50, "away_rate": 40, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0, "actual": "主胜", "score": "4-0"},
    {"id": "周二003", "match": "町田泽维 vs 江原FC", "v7": "主胜", "confidence": 55, 
     "home_rate": 50, "away_rate": 10, "home_eight_change": 1, "draw_eight_change": 0, "away_eight_change": 0, "actual": "主胜", "score": "1-0"},
    {"id": "周二004", "match": "布里兰 vs 墨尔本城", "v7": "客胜", "confidence": 60, 
     "home_rate": 80, "away_rate": 20, "home_eight_change": 0, "draw_eight_change": -1, "away_eight_change": -1, "actual": "平局", "score": "0-0"},
    {"id": "周二005", "match": "加拉塔萨 vs 利物浦", "v7": "客胜", "confidence": 72, 
     "home_rate": 80, "away_rate": 70, "home_eight_change": 2, "draw_eight_change": 0, "away_eight_change": 0, "actual": "主胜", "score": "1-0"},
    {"id": "周二006", "match": "朴次茅斯 vs 斯旺西", "v7": "主胜", "confidence": 58, 
     "home_rate": 30, "away_rate": 50, "home_eight_change": 2, "draw_eight_change": 1, "away_eight_change": 0, "actual": "客胜", "score": "1-2"},
    {"id": "周二007", "match": "亚特兰大 vs 拜仁", "v7": "客胜", "confidence": 60, 
     "home_rate": 50, "away_rate": 80, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": -1, "actual": "客胜", "score": "1-6"},
    {"id": "周二008", "match": "马竞 vs 热刺", "v7": "主胜", "confidence": 56, 
     "home_rate": 60, "away_rate": 20, "home_eight_change": 1, "draw_eight_change": 0, "away_eight_change": 0, "actual": "主胜", "score": "5-2"},
    {"id": "周二009", "match": "纽卡斯尔 vs 巴萨", "v7": "客胜", "confidence": 62, 
     "home_rate": 50, "away_rate": 80, "home_eight_change": -1, "draw_eight_change": 0, "away_eight_change": -1, "actual": "平局", "score": "1-1"},
]

matches_311 = [
    {"id": "周三001", "match": "神户胜利 vs 首尔FC", "v7": "主胜", "confidence": 58, 
     "home_rate": 40, "away_rate": 30, "home_eight_change": 2, "draw_eight_change": 0, "away_eight_change": 0, "actual": "主胜", "score": "2-1"},
    {"id": "周三002", "match": "广岛三箭 vs 柔佛", "v7": "主胜", "confidence": 75, 
     "home_rate": 60, "away_rate": 80, "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0, "actual": "主胜", "score": "1-0"},
    {"id": "周三003", "match": "叻武里 vs 大阪钢巴", "v7": "客胜", "confidence": 72, 
     "home_rate": 50, "away_rate": 50, "home_eight_change": 0, "draw_eight_change": 1, "away_eight_change": 0, "actual": "平局", "score": "1-1"},
    {"id": "周三004", "match": "勒沃库森 vs 阿森纳", "v7": "主胜", "confidence": 65, 
     "home_rate": 50, "away_rate": 80, "home_eight_change": 2, "draw_eight_change": 1, "away_eight_change": 0, "actual": "平局", "score": "1-1"},
    {"id": "周三005", "match": "诺维奇 vs 谢菲联", "v7": "主胜", "confidence": 55, 
     "home_rate": 70, "away_rate": 50, "home_eight_change": -1, "draw_eight_change": -1, "away_eight_change": 0, "actual": "主胜", "score": "2-1"},
    {"id": "周三006", "match": "西布罗姆 vs 南安普敦", "v7": "客胜", "confidence": 58, 
     "home_rate": 0, "away_rate": 70, "home_eight_change": 0, "draw_eight_change": 1, "away_eight_change": 0, "actual": "平局", "score": "1-1"},
    {"id": "周三007", "match": "博德闪耀 vs 里斯本", "v7": "客胜", "confidence": 62, 
     "home_rate": 80, "away_rate": 70, "home_eight_change": 0, "draw_eight_change": -1, "away_eight_change": -2, "actual": "主胜", "score": "3-0"},
]

def analyze_match(m):
    home_change = m['home_eight_change']
    draw_change = m['draw_eight_change']
    away_change = m['away_eight_change']

    changes = {'主胜': home_change, '平局': draw_change, '客胜': away_change}
    max_increase = max(changes.items(), key=lambda x: x[1])

    return {
        'id': m['id'],
        'match': m['match'],
        'v7': m['v7'],
        'confidence': m['confidence'],
        'home_rate': m['home_rate'],
        'away_rate': m['away_rate'],
        'rate_diff': m['home_rate'] - m['away_rate'],
        'home_change': home_change,
        'draw_change': draw_change,
        'away_change': away_change,
        'max_increase': max_increase,
        'actual': m.get('actual'),
        'score': m.get('score'),
    }

all_matches = matches_310 + matches_311
results = [analyze_match(m) for m in all_matches]

print("=" * 160)
print("3.10 + 3.11 比赛 - 完整数据")
print("=" * 160)

print(f"| 日期 | 编号 | 对阵 | V7预测 | 置信度 | 胜率差 | 主胜8 | 平局8 | 客胜8 | 增加最多 | 实际 | 比分 | 结果 |")
print(f"|------|------|------|--------|--------|--------|--------|--------|--------|----------|------|------|------|")

for r in results:
    date = "3.10" if r['id'].startswith("周二") else "3.11"
    actual = r['actual'] or "-"
    score = r['score'] or "-"

    inc_opt = r['max_increase'][0]
    inc_val = r['max_increase'][1]
    inc_str = f"{inc_opt}{inc_val:+d}" if inc_val != 0 else "-"

    hit = "对" if r['actual'] and inc_opt == r['actual'] else ""

    print(f"| {date} | {r['id']} | {r['match']} | {r['v7']} | {r['confidence']}% | {r['rate_diff']:+d}% | {r['home_change']:+d} | {r['draw_change']:+d} | {r['away_change']:+d} | {inc_str} | {actual} | {score} | {hit} |")

# 按V7预测和胜率差分类
print("\n" + "=" * 160)
print("按V7预测方向分类 - 8增加最多选项的命中率")
print("=" * 160)

valid_results = [r for r in results if r['actual'] and r['max_increase'][1] != 0]

for v7_pred in ["主胜", "客胜"]:
    v7_results = [r for r in valid_results if r['v7'] == v7_pred]
    if not v7_results:
        continue
    
    hit = sum(1 for r in v7_results if r['max_increase'][0] == r['actual'])
    total = len(v7_results)
    print(f"\n【V7预测={v7_pred}】{hit}/{total} = {hit/total*100:.1f}%")
    for r in v7_results:
        inc_opt = r['max_increase'][0]
        hit_mark = "对" if inc_opt == r['actual'] else ""
        print(f"  {r['id']}: 胜率差{r['rate_diff']:+d}%, 增加最多={inc_opt}, 实际={r['actual']} {hit_mark}")

print("\n【总计】")
hit = sum(1 for r in valid_results if r['max_increase'][0] == r['actual'])
total = len(valid_results)
print(f"{hit}/{total} = {hit/total*100:.1f}%")
