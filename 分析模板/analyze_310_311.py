"""
3.10和3.11比赛详细推理分析
基于5个规律进行分析
"""

# 手动整理比赛数据（从源数据中提取）
matches_310 = [
    {"id": "周二001", "match": "印度女 vs 中国台女", "v7": "客胜", "confidence": 65, "home_rate": 40, "away_rate": 60, "eight_change": -3},
    {"id": "周二002", "match": "日本女 vs 越南女", "v7": "主胜", "confidence": 90, "home_rate": 100, "away_rate": 60, "eight_change": 0},
    {"id": "周二003", "match": "町田泽维 vs 江原FC", "v7": "主胜", "confidence": 55, "home_rate": 70, "away_rate": 30, "eight_change": 1},
    {"id": "周二004", "match": "布里兰 vs 墨尔本城", "v7": "客胜", "confidence": 60, "home_rate": 30, "away_rate": 60, "eight_change": -2},
    {"id": "周二005", "match": "加拉塔萨 vs 利物浦", "v7": "客胜", "confidence": 72, "home_rate": 60, "away_rate": 80, "eight_change": 2},
    {"id": "周二006", "match": "朴次茅斯 vs 斯旺西", "v7": "主胜", "confidence": 58, "home_rate": 60, "away_rate": 40, "eight_change": 3},
    {"id": "周二007", "match": "亚特兰大 vs 拜仁", "v7": "客胜", "confidence": 60, "home_rate": 70, "away_rate": 80, "eight_change": -1},
    {"id": "周二008", "match": "马竞 vs 热刺", "v7": "主胜", "confidence": 56, "home_rate": 70, "away_rate": 60, "eight_change": 1},
    {"id": "周二009", "match": "纽卡斯尔 vs 巴萨", "v7": "客胜", "confidence": 62, "home_rate": 50, "away_rate": 70, "eight_change": -2},
]

matches_311 = [
    {"id": "周三001", "match": "神户胜利 vs 首尔FC", "v7": "主胜", "confidence": 58, "home_rate": 60, "away_rate": 50, "eight_change": 2},
    {"id": "周三002", "match": "广岛三箭 vs 柔佛", "v7": "主胜", "confidence": 75, "home_rate": 70, "away_rate": 20, "eight_change": 0},
    {"id": "周三003", "match": "叻武里 vs 大阪钢巴", "v7": "客胜", "confidence": 72, "home_rate": 20, "away_rate": 60, "eight_change": 1},
    {"id": "周三004", "match": "勒沃库森 vs 阿森纳", "v7": "主胜", "confidence": 65, "home_rate": 80, "away_rate": 70, "eight_change": 3},
    {"id": "周三005", "match": "诺维奇 vs 谢菲联", "v7": "主胜", "confidence": 55, "home_rate": 50, "away_rate": 40, "eight_change": -2},
    {"id": "周三006", "match": "西布罗姆 vs 南安普敦", "v7": "客胜", "confidence": 58, "home_rate": 40, "away_rate": 50, "eight_change": 1},
    {"id": "周三007", "match": "博德闪耀 vs 里斯本", "v7": "客胜", "confidence": 62, "home_rate": 90, "away_rate": 70, "eight_change": -3},
    {"id": "周三008", "match": "巴黎圣曼 vs 切尔西", "v7": "主胜", "confidence": 72, "home_rate": 80, "away_rate": 50, "eight_change": 1},
    {"id": "周三009", "match": "皇马 vs 曼城", "v7": "主胜", "confidence": 55, "home_rate": 70, "away_rate": 80, "eight_change": 0},
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
    
    # 推理步骤
    steps = []
    steps.append(f"【步骤1】置信度: {conf}% {'>=55%' if conf >= 55 else '<55%'}")
    
    if conf < 55:
        steps.append("→ 不推荐，置信度不足")
        return steps, "不推荐", "无"
    
    steps.append(f"【步骤2】总8变化: {eight:+d}")
    steps.append(f"【步骤3】状态: {state} (主{m['home_rate']}% vs 客{m['away_rate']}%)")
    
    # 规律判断
    if eight == -5 and state != "焦灼":
        rec = v7
        rule = "规律1"
        logic = "8减少+状态极好=庄家挡不住=实盘"
    elif eight == -5 and state == "焦灼":
        rec = "防平/不推荐"
        rule = "规律2"
        logic = "8减少+状态焦灼=主动降赔=诱盘"
    elif -4 <= eight <= -2:
        rec = "平局"
        rule = "规律3"
        logic = "8减少但不是-5=庄家不挡=最多小赢=平局"
    elif eight > 0 and state != "焦灼":
        rec = v7
        rule = "规律4"
        logic = "8增加+状态极好=庄家诱导但基本面强=跟庄家"
    elif eight > 0 and state == "焦灼":
        if v7 == "主胜":
            rec = "客胜/平局"
        else:
            rec = "主胜/平局"
        rule = "规律5"
        logic = "8增加+状态焦灼=低赔+高回报诱导=诱盘"
    elif eight == 0:
        rec = "观察"
        rule = "无规律"
        logic = "8无变化=庄家不作为=观望"
    else:
        rec = "观察"
        rule = "其他"
        logic = "需更多观察"
    
    steps.append(f"【步骤4】规律: {rule}")
    steps.append(f"→ 逻辑: {logic}")
    steps.append(f"→ 推荐: {rec}")
    
    return steps, rec, rule

# 分析3.10
print("=" * 90)
print("3.10 比赛详细推理分析")
print("=" * 90)

all_matches = matches_310 + matches_311

for m in all_matches:
    print(f"\n{'='*90}")
    print(f"【{m['id']}】{m['match']}")
    print(f"V7预测: {m['v7']} | 置信度: {m['confidence']}%")
    print("-" * 50)
    
    steps, rec, rule = analyze_match(m)
    for step in steps:
        print(step)
    
    print("-" * 50)
    print(f"【最终推荐】: {rec}")

# 汇总表格
print("\n" + "=" * 90)
print("汇总表格")
print("=" * 90)
print(f"| 日期 | 编号 | 对阵 | 置信度 | 8变化 | 状态 | 规律 | 推荐 |")
print(f"|------|------|------|--------|-------|------|------|------|")

for m in matches_310:
    _, rec, rule = analyze_match(m)
    state = get_state(m['home_rate'], m['away_rate'])
    print(f"| 3.10 | {m['id']} | {m['match']} | {m['confidence']}% | {m['eight_change']:+d} | {state} | {rule} | {rec} |")

for m in matches_311:
    _, rec, rule = analyze_match(m)
    state = get_state(m['home_rate'], m['away_rate'])
    print(f"| 3.11 | {m['id']} | {m['match']} | {m['confidence']}% | {m['eight_change']:+d} | {state} | {rule} | {rec} |")
