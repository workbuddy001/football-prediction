"""
3.10和3.11比赛 - 按各选项8变化详细分析
"""

# 比赛数据（含各选项8变化）
matches_310 = [
    # 周二001: 印度女 vs 中国台女
    {"id": "周二001", "match": "印度女 vs 中国台女", "v7": "客胜", "confidence": 65, 
     "home_rate": 40, "away_rate": 60, 
     "total_eight_change": -3,
     "home_eight_change": -2, "draw_eight_change": 0, "away_eight_change": -1,
     "actual": "客胜", "score": "1-3"},
    
    # 周二002: 日本女 vs 越南女
    {"id": "周二002", "match": "日本女 vs 越南女", "v7": "主胜", "confidence": 90, 
     "home_rate": 100, "away_rate": 60, 
     "total_eight_change": 0,
     "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0,
     "actual": "主胜", "score": "4-0"},
    
    # 周二003: 町田泽维 vs 江原FC
    {"id": "周二003", "match": "町田泽维 vs 江原FC", "v7": "主胜", "confidence": 55, 
     "home_rate": 70, "away_rate": 30, 
     "total_eight_change": 1,
     "home_eight_change": 1, "draw_eight_change": 0, "away_eight_change": 0,
     "actual": "主胜", "score": "1-0"},
    
    # 周二004: 布里兰 vs 墨尔本城
    {"id": "周二004", "match": "布里兰 vs 墨尔本城", "v7": "客胜", "confidence": 60, 
     "home_rate": 30, "away_rate": 60, 
     "total_eight_change": -2,
     "home_eight_change": 0, "draw_eight_change": -1, "away_eight_change": -1,
     "actual": "平局", "score": "0-0"},
    
    # 周二005: 加拉塔萨 vs 利物浦
    {"id": "周二005", "match": "加拉塔萨 vs 利物浦", "v7": "客胜", "confidence": 72, 
     "home_rate": 60, "away_rate": 80, 
     "total_eight_change": 2,
     "home_eight_change": 2, "draw_eight_change": 0, "away_eight_change": 0,
     "actual": "主胜", "score": "1-0"},
    
    # 周二006: 朴次茅斯 vs 斯旺西
    {"id": "周二006", "match": "朴次茅斯 vs 斯旺西", "v7": "主胜", "confidence": 58, 
     "home_rate": 60, "away_rate": 40, 
     "total_eight_change": 3,
     "home_eight_change": 2, "draw_eight_change": 1, "away_eight_change": 0,
     "actual": "客胜", "score": "1-2"},
    
    # 周二007: 亚特兰大 vs 拜仁
    {"id": "周二007", "match": "亚特兰大 vs 拜仁", "v7": "客胜", "confidence": 60, 
     "home_rate": 70, "away_rate": 80, 
     "total_eight_change": -1,
     "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": -1,
     "actual": "客胜", "score": "1-6"},
    
    # 周二008: 马竞 vs 热刺
    {"id": "周二008", "match": "马竞 vs 热刺", "v7": "主胜", "confidence": 56, 
     "home_rate": 70, "away_rate": 60, 
     "total_eight_change": 1,
     "home_eight_change": 1, "draw_eight_change": 0, "away_eight_change": 0,
     "actual": "主胜", "score": "5-2"},
    
    # 周二009: 纽卡斯尔 vs 巴萨
    {"id": "周二009", "match": "纽卡斯尔 vs 巴萨", "v7": "客胜", "confidence": 62, 
     "home_rate": 50, "away_rate": 70, 
     "total_eight_change": -2,
     "home_eight_change": -1, "draw_eight_change": 0, "away_eight_change": -1,
     "actual": "平局", "score": "1-1"},
]

matches_311 = [
    # 周三001: 神户胜利 vs 首尔FC
    {"id": "周三001", "match": "神户胜利 vs 首尔FC", "v7": "主胜", "confidence": 58, 
     "home_rate": 60, "away_rate": 50, 
     "total_eight_change": 2,
     "home_eight_change": 2, "draw_eight_change": 0, "away_eight_change": 0,
     "actual": "主胜", "score": "2-1"},
    
    # 周三002: 广岛三箭 vs 柔佛
    {"id": "周三002", "match": "广岛三箭 vs 柔佛", "v7": "主胜", "confidence": 75, 
     "home_rate": 70, "away_rate": 20, 
     "total_eight_change": 0,
     "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0,
     "actual": "主胜", "score": "1-0"},
    
    # 周三003: 叻武里 vs 大阪钢巴
    {"id": "周三003", "match": "叻武里 vs 大阪钢巴", "v7": "客胜", "confidence": 72, 
     "home_rate": 20, "away_rate": 60, 
     "total_eight_change": 1,
     "home_eight_change": 0, "draw_eight_change": 1, "away_eight_change": 0,
     "actual": "平局", "score": "1-1"},
    
    # 周三004: 勒沃库森 vs 阿森纳
    {"id": "周三004", "match": "勒沃库森 vs 阿森纳", "v7": "主胜", "confidence": 65, 
     "home_rate": 80, "away_rate": 70, 
     "total_eight_change": 3,
     "home_eight_change": 2, "draw_eight_change": 1, "away_eight_change": 0,
     "actual": "平局", "score": "1-1"},
    
    # 周三005: 诺维奇 vs 谢菲联
    {"id": "周三005", "match": "诺维奇 vs 谢菲联", "v7": "主胜", "confidence": 55, 
     "home_rate": 50, "away_rate": 40, 
     "total_eight_change": -2,
     "home_eight_change": -1, "draw_eight_change": -1, "away_eight_change": 0,
     "actual": "主胜", "score": "2-1"},
    
    # 周三006: 西布罗姆 vs 南安普敦
    {"id": "周三006", "match": "西布罗姆 vs 南安普敦", "v7": "客胜", "confidence": 58, 
     "home_rate": 40, "away_rate": 50, 
     "total_eight_change": 1,
     "home_eight_change": 0, "draw_eight_change": 1, "away_eight_change": 0,
     "actual": "平局", "score": "1-1"},
    
    # 周三007: 博德闪耀 vs 里斯本
    {"id": "周三007", "match": "博德闪耀 vs 里斯本", "v7": "客胜", "confidence": 62, 
     "home_rate": 90, "away_rate": 70, 
     "total_eight_change": -3,
     "home_eight_change": 0, "draw_eight_change": -1, "away_eight_change": -2,
     "actual": "主胜", "score": "3-0"},
    
    # 周三008: 巴黎圣曼 vs 切尔西
    {"id": "周三008", "match": "巴黎圣曼 vs 切尔西", "v7": "主胜", "confidence": 72, 
     "home_rate": 80, "away_rate": 50, 
     "total_eight_change": 1,
     "home_eight_change": 1, "draw_eight_change": 0, "away_eight_change": 0,
     "actual": None, "score": None},
    
    # 周三009: 皇马 vs 曼城
    {"id": "周三009", "match": "皇马 vs 曼城", "v7": "主胜", "confidence": 55, 
     "home_rate": 70, "away_rate": 80, 
     "total_eight_change": 0,
     "home_eight_change": 0, "draw_eight_change": 0, "away_eight_change": 0,
     "actual": None, "score": None},
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
    """详细分析每个选项的8变化"""
    conf = m['confidence']
    home_change = m['home_eight_change']
    draw_change = m['draw_eight_change']
    away_change = m['away_eight_change']
    v7 = m['v7']
    
    # 找出变化最大的选项
    changes = {'主胜': home_change, '平局': draw_change, '客胜': away_change}
    max_increase = max(changes.items(), key=lambda x: x[1])
    max_decrease = min(changes.items(), key=lambda x: x[1])
    
    state = get_state(m['home_rate'], m['away_rate'])
    
    return {
        'id': m['id'],
        'match': m['match'],
        'v7': v7,
        'confidence': conf,
        'state': state,
        'home_rate': m['home_rate'],
        'away_rate': m['away_rate'],
        'total_change': m['total_eight_change'],
        'home_change': home_change,
        'draw_change': draw_change,
        'away_change': away_change,
        'max_increase': max_increase,
        'max_decrease': max_decrease,
        'actual': m.get('actual'),
        'score': m.get('score'),
    }

# 分析
all_matches = matches_310 + matches_311
results = [analyze_match(m) for m in all_matches]

print("=" * 130)
print("3.10 + 3.11 比赛 - 各选项8变化详细分析")
print("=" * 130)

print(f"| 日期 | 编号 | 对阵 | 置信度 | 状态 | 主胜8 | 平局8 | 客胜8 | 减少最多 | 增加最多 | 实际 | 比分 |")
print(f"|------|------|------|--------|------|--------|--------|--------|----------|----------|------|------|")

for r in results:
    date = "3.10" if r['id'].startswith("周二") else "3.11"
    actual = r['actual'] or "-"
    score = r['score'] or "-"
    
    # 减少最多的选项
    dec_opt = r['max_decrease'][0]
    dec_val = r['max_decrease'][1]
    dec_str = f"{dec_opt}{dec_val:+d}" if dec_val != 0 else "-"
    
    # 增加最多的选项
    inc_opt = r['max_increase'][0]
    inc_val = r['max_increase'][1]
    inc_str = f"{inc_opt}{inc_val:+d}" if inc_val != 0 else "-"
    
    print(f"| {date} | {r['id']} | {r['match']} | {r['confidence']}% | {r['state']} | {r['home_change']:+d} | {r['draw_change']:+d} | {r['away_change']:+d} | {dec_str} | {inc_str} | {actual} | {score} |")

print("\n" + "=" * 130)
print("规律分析")
print("=" * 130)

# 分析：8减少最多的选项 vs 实际结果
print("\n【8减少最多的选项 vs 实际结果】")
hit = 0
total = 0
for r in results:
    if not r['actual']:
        continue
    total += 1
    dec_opt = r['max_decrease'][0]
    if dec_opt == r['actual']:
        hit += 1
        result = "对"
    else:
        result = ""
    print(f"{r['id']}: 减少最多={dec_opt}, 实际={r['actual']} {result}")

print(f"\n命中率: {hit}/{total} = {hit/total*100:.1f}%")

# 分析：8增加最多的选项 vs 实际结果
print("\n【8增加最多的选项 vs 实际结果】")
hit = 0
total = 0
for r in results:
    if not r['actual']:
        continue
    total += 1
    inc_opt = r['max_increase'][0]
    if inc_opt == r['actual']:
        hit += 1
        result = "对"
    else:
        result = ""
    print(f"{r['id']}: 增加最多={inc_opt}, 实际={r['actual']} {result}")

print(f"\n命中率: {hit}/{total} = {hit/total*100:.1f}%")
