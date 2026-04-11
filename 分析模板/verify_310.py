"""
3.10和3.11比赛结果验证
"""

# 3.10比赛数据（含实际结果）
matches_310 = [
    {"id": "周二001", "match": "印度女 vs 中国台女", "v7": "客胜", "confidence": 65, "home_rate": 40, "away_rate": 60, "eight_change": -3, "actual": "客胜", "score": "1-3"},
    {"id": "周二002", "match": "日本女 vs 越南女", "v7": "主胜", "confidence": 90, "home_rate": 100, "away_rate": 60, "eight_change": 0, "actual": "主胜", "score": "4-0"},
    {"id": "周二003", "match": "町田泽维 vs 江原FC", "v7": "主胜", "confidence": 55, "home_rate": 70, "away_rate": 30, "eight_change": 1, "actual": "主胜", "score": "1-0"},
    {"id": "周二004", "match": "布里兰 vs 墨尔本城", "v7": "客胜", "confidence": 60, "home_rate": 30, "away_rate": 60, "eight_change": -2, "actual": "平局", "score": "0-0"},
    {"id": "周二005", "match": "加拉塔萨 vs 利物浦", "v7": "客胜", "confidence": 72, "home_rate": 60, "away_rate": 80, "eight_change": 2, "actual": "主胜", "score": "1-0"},
    {"id": "周二006", "match": "朴次茅斯 vs 斯旺西", "v7": "主胜", "confidence": 58, "home_rate": 60, "away_rate": 40, "eight_change": 3, "actual": "客胜", "score": "1-2"},
    {"id": "周二007", "match": "亚特兰大 vs 拜仁", "v7": "客胜", "confidence": 60, "home_rate": 70, "away_rate": 80, "eight_change": -1, "actual": "客胜", "score": "1-6"},
    {"id": "周二008", "match": "马竞 vs 热刺", "v7": "主胜", "confidence": 56, "home_rate": 70, "away_rate": 60, "eight_change": 1, "actual": "主胜", "score": "5-2"},
    {"id": "周二009", "match": "纽卡斯尔 vs 巴萨", "v7": "客胜", "confidence": 62, "home_rate": 50, "away_rate": 70, "eight_change": -2, "actual": None, "score": None},
]

# 3.11比赛数据
matches_311 = [
    {"id": "周三001", "match": "神户胜利 vs 首尔FC", "v7": "主胜", "confidence": 58, "home_rate": 60, "away_rate": 50, "eight_change": 2, "actual": None},
    {"id": "周三002", "match": "广岛三箭 vs 柔佛", "v7": "主胜", "confidence": 75, "home_rate": 70, "away_rate": 20, "eight_change": 0, "actual": None},
    {"id": "周三003", "match": "叻武里 vs 大阪钢巴", "v7": "客胜", "confidence": 72, "home_rate": 20, "away_rate": 60, "eight_change": 1, "actual": None},
    {"id": "周三004", "match": "勒沃库森 vs 阿森纳", "v7": "主胜", "confidence": 65, "home_rate": 80, "away_rate": 70, "eight_change": 3, "actual": None},
    {"id": "周三005", "match": "诺维奇 vs 谢菲联", "v7": "主胜", "confidence": 55, "home_rate": 50, "away_rate": 40, "eight_change": -2, "actual": None},
    {"id": "周三006", "match": "西布罗姆 vs 南安普敦", "v7": "客胜", "confidence": 58, "home_rate": 40, "away_rate": 50, "eight_change": 1, "actual": None},
    {"id": "周三007", "match": "博德闪耀 vs 里斯本", "v7": "客胜", "confidence": 62, "home_rate": 90, "away_rate": 70, "eight_change": -3, "actual": None},
    {"id": "周三008", "match": "巴黎圣曼 vs 切尔西", "v7": "主胜", "confidence": 72, "home_rate": 80, "away_rate": 50, "eight_change": 1, "actual": None},
    {"id": "周三009", "match": "皇马 vs 曼城", "v7": "主胜", "confidence": 55, "home_rate": 70, "away_rate": 80, "eight_change": 0, "actual": None},
]

def get_state(home_rate, away_rate):
    diff = home_rate - away_rate
    if abs(diff) <= 15:
        return "焦灼"
    elif diff > 15:
        return "主队极好"
    else:
        return "客队极好"

def analyze_match(m):
    """用5个规律分析比赛"""
    conf = m['confidence']
    eight = m['eight_change']
    state = get_state(m['home_rate'], m['away_rate'])
    v7 = m['v7']
    
    # 规律判断
    if eight == -5 and state != "焦灼":
        rec = v7
        rule = "规律1"
    elif eight == -5 and state == "焦灼":
        rec = "防平/不推荐"
        rule = "规律2"
    elif -4 <= eight <= -2:
        rec = "平局"
        rule = "规律3"
    elif eight > 0 and state != "焦灼":
        rec = v7
        rule = "规律4"
    elif eight > 0 and state == "焦灼":
        rec = "主胜/平局" if v7 == "客胜" else "客胜/平局"
        rule = "规律5"
    elif eight == 0:
        rec = "观察"
        rule = "无规律"
    else:
        rec = "观察"
        rule = "其他"
    
    # 检查是否命中
    hit = False
    if m.get('actual'):
        rec_options = [x.strip() for x in rec.split('/')]
        if m['actual'] in rec_options:
            hit = True
    
    return {
        'id': m['id'],
        'match': m['match'],
        'v7': v7,
        'confidence': conf,
        'eight': eight,
        'state': state,
        'rule': rule,
        'rec': rec,
        'actual': m.get('actual'),
        'score': m.get('score'),
        'hit': hit
    }

# 分析3.10
print("=" * 100)
print("3.10 比赛结果验证")
print("=" * 100)

results = [analyze_match(m) for m in matches_310]

# 按规律统计
rules_stats = {}
for r in results:
    rule = r['rule']
    if rule not in rules_stats:
        rules_stats[rule] = {'total': 0, 'hit': 0}
    rules_stats[rule]['total'] += 1
    if r['hit']:
        rules_stats[rule]['hit'] += 1

print("\n【规律命中率统计】")
print("-" * 60)
for rule, stats in sorted(rules_stats.items()):
    rate = stats['hit'] / stats['total'] * 100 if stats['total'] > 0 else 0
    print(f"{rule}: {stats['hit']}/{stats['total']} = {rate:.1f}%")

print("\n【详细表格】")
print("-" * 100)
print(f"| 编号 | 对阵 | 置信度 | 8变化 | 状态 | 规律 | 推荐 | 实际 | 比分 | 结果 |")
print(f"|------|------|--------|-------|------|------|------|------|------|------|")
for r in results:
    hit_mark = "对" if r['hit'] else ""
    actual = r['actual'] or "-"
    score = r['score'] or "-"
    print(f"| {r['id']} | {r['match']} | {r['confidence']}% | {r['eight']:+d} | {r['state']} | {r['rule']} | {r['rec']} | {actual} | {score} | {hit_mark} |")

# 统计
total = len(results)
hits = sum(1 for r in results if r['hit'])
print(f"\n【总计】{hits}/{total} = {hits/total*100:.1f}%")
