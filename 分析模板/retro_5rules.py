"""
用5个规律回溯分析历史比赛
"""
import os
import re

# 从各场比赛的源数据中提取信息
# 这里手动整理已知比赛的关键数据

matches = [
    # 3.15的比赛
    {"id": "周五010", "match": "马赛 vs 欧塞尔", "v7": "主胜", "confidence": 70, "home_rate": 40, "away_rate": 10, "eight_change": -5, "actual": "主胜"},
    {"id": "周日014", "match": "曼联 vs 维拉", "v7": "主胜", "confidence": 59, "home_rate": 40, "away_rate": 20, "eight_change": -5, "actual": "主胜"},
    
    # 3.14的比赛
    {"id": "周六012", "match": "国米 vs 亚特兰大", "v7": "主胜", "confidence": 66, "home_rate": 50, "away_rate": 50, "eight_change": -5, "actual": "平局"},
    {"id": "周六013", "match": "霍芬海姆 vs 沃夫斯堡", "v7": "主胜", "confidence": 70, "home_rate": 30, "away_rate": 0, "eight_change": -2, "actual": "平局"},
    {"id": "周六016", "match": "勒沃库森 vs 拜仁", "v7": "客胜", "confidence": 65, "home_rate": 80, "away_rate": 30, "eight_change": -2, "actual": "平局"},
    {"id": "周五007", "match": "坎布尔 vs 罗达JC", "v7": "主胜", "confidence": 57, "home_rate": 80, "away_rate": 30, "eight_change": -4, "actual": "平局"},
    
    # 3.13的比赛
    {"id": "周日010", "match": "费耶诺德 vs SBV精英", "v7": "主胜", "confidence": 76, "home_rate": 70, "away_rate": 20, "eight_change": 1, "actual": "主胜"},
    {"id": "周六014", "match": "多特蒙德 vs 奥格斯堡", "v7": "主胜", "confidence": 66, "home_rate": 60, "away_rate": 30, "eight_change": 3, "actual": "主胜"},
    {"id": "周六008", "match": "韩国女 vs 乌兹别克", "v7": "主胜", "confidence": 95, "home_rate": 70, "away_rate": 10, "eight_change": 2, "actual": "主胜"},
    {"id": "周日018", "match": "巴萨 vs 塞维利亚", "v7": "主胜", "confidence": 78, "home_rate": 70, "away_rate": 30, "eight_change": 1, "actual": "主胜"},
    
    # 3.12的比赛
    {"id": "周六005", "match": "鹿岛鹿角 vs 川崎前锋", "v7": "主胜", "confidence": 48, "home_rate": 60, "away_rate": 40, "eight_change": 5, "actual": "主胜"},
    {"id": "周日011", "match": "克里斯蒂 vs 博德闪耀", "v7": "客胜", "confidence": 55, "home_rate": 20, "away_rate": 90, "eight_change": 1, "actual": "客胜"},
    
    # 3.11的比赛
    {"id": "周四001", "match": "淡宾尼士 vs 曼谷联", "v7": "客胜", "confidence": 48, "home_rate": 50, "away_rate": 50, "eight_change": 3, "actual": "平局"},
    {"id": "周六010", "match": "考文垂 vs 南安普敦", "v7": "主胜", "confidence": 51, "home_rate": 40, "away_rate": 50, "eight_change": 2, "actual": "客胜"},
    {"id": "周六017", "match": "伯恩利 vs 伯恩茅斯", "v7": "客胜", "confidence": 48, "home_rate": 30, "away_rate": 40, "eight_change": 1, "actual": "平局"},
    {"id": "周六019", "match": "洛里昂 vs 朗斯", "v7": "客胜", "confidence": 49, "home_rate": 50, "away_rate": 60, "eight_change": 6, "actual": "主胜"},
    {"id": "周六021", "match": "莫尔德 vs 罗森博格", "v7": "主胜", "confidence": 47, "home_rate": 70, "away_rate": 40, "eight_change": 3, "actual": "主胜"},
    {"id": "周六023", "match": "切尔西 vs 纽卡斯尔", "v7": "主胜", "confidence": 51, "home_rate": 50, "away_rate": 50, "eight_change": -3, "actual": "客胜"},
    {"id": "周六024", "match": "汉堡 vs 科隆", "v7": "主胜", "confidence": 45, "home_rate": 40, "away_rate": 50, "eight_change": 1, "actual": "平局"},
    {"id": "周日019", "match": "瓦勒伦加 vs 桑纳菲", "v7": "主胜", "confidence": 48, "home_rate": 40, "away_rate": 30, "eight_change": 0, "actual": "主胜"},
    {"id": "周日026", "match": "拉齐奥 vs AC米兰", "v7": "客胜", "confidence": 46, "home_rate": 50, "away_rate": 70, "eight_change": 1, "actual": "主胜"},
    {"id": "周日027", "match": "皇家社会 vs 奥萨苏纳", "v7": "主胜", "confidence": 48, "home_rate": 60, "away_rate": 40, "eight_change": 2, "actual": "主胜"},
    {"id": "周一006", "match": "巴列卡诺 vs 莱万特", "v7": "主胜", "confidence": 55, "home_rate": 43, "away_rate": 14, "eight_change": 3, "actual": "平局"},
    {"id": "周五002", "match": "Austral女 vs 朝鲜女", "v7": "主胜", "confidence": 47, "home_rate": 40, "away_rate": 30, "eight_change": -1, "actual": "平局"},
    {"id": "周五008", "match": "门兴 vs 圣保利", "v7": "主胜", "confidence": 49, "home_rate": 30, "away_rate": 40, "eight_change": -3, "actual": "主胜"},
    {"id": "周六004", "match": "墨胜利 vs 麦克阿瑟", "v7": "主胜", "confidence": 51, "home_rate": 60, "away_rate": 30, "eight_change": -6, "actual": "主胜"},
    {"id": "周六011", "match": "勒阿弗尔 vs 里昂", "v7": "客胜", "confidence": 50, "home_rate": 20, "away_rate": 60, "eight_change": -1, "actual": "平局"},
    {"id": "周日021", "match": "克雷莫纳 vs 佛罗伦萨", "v7": "客胜", "confidence": 47, "home_rate": 20, "away_rate": 50, "eight_change": -1, "actual": "客胜"},
    
    # 3.16的比赛
    {"id": "周一001", "match": "海尔蒙特 vs 坎布尔", "v7": "客胜", "confidence": 58, "home_rate": 20, "away_rate": 70, "eight_change": -5, "actual": "客胜"},
    {"id": "周一004", "match": "布伦特 vs 狼队", "v7": "主胜", "confidence": 64, "home_rate": 40, "away_rate": 30, "eight_change": 3, "actual": "平局"},
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
    
    # 规律1: 8变化-5 + 状态极好
    if eight == -5 and state != "焦灼":
        rec = v7
        rule = "规律1"
        logic = "8减少+状态极好=庄家挡不住=实盘"
    
    # 规律2: 8变化-5 + 状态焦灼
    elif eight == -5 and state == "焦灼":
        rec = "防平/不推荐"
        rule = "规律2"
        logic = "8减少+状态焦灼=主动降赔=诱盘"
    
    # 规律3: 8变化-2~-4
    elif -4 <= eight <= -2:
        rec = "平局"
        rule = "规律3"
        logic = "8减少但不是-5=庄家不挡=最多小赢=平局"
    
    # 规律4: 8变化正数 + 状态极好
    elif eight > 0 and state != "焦灼":
        rec = v7
        rule = "规律4"
        logic = "8增加+状态极好=庄家诱导但基本面强=跟庄家"
    
    # 规律5: 8变化正数 + 状态焦灼
    elif eight > 0 and state == "焦灼":
        # 反向推荐
        if v7 == "主胜":
            rec = "客胜/平局"
        else:
            rec = "主胜/平局"
        rule = "规律5"
        logic = "8增加+状态焦灼=低赔+高回报诱导=诱盘"
    
    # 8变化=0
    elif eight == 0:
        rec = "观察"
        rule = "无规律"
        logic = "8无变化=庄家不作为=观望"
    
    # 其他
    else:
        rec = "观察"
        rule = "其他"
        logic = "需更多观察"
    
    # 检查是否命中
    hit = False
    if m['actual']:
        # 去掉"/"后的选项
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
        'logic': logic,
        'rec': rec,
        'actual': m['actual'],
        'hit': hit
    }

# 分析所有比赛
results = [analyze_match(m) for m in matches]

# 按规律分组统计
rules_stats = {}
for r in results:
    rule = r['rule']
    if rule not in rules_stats:
        rules_stats[rule] = {'total': 0, 'hit': 0}
    rules_stats[rule]['total'] += 1
    if r['hit']:
        rules_stats[rule]['hit'] += 1

print("=" * 100)
print("5个规律回溯分析结果")
print("=" * 100)

print("\n【规律统计】")
print("-" * 60)
for rule, stats in sorted(rules_stats.items()):
    rate = stats['hit'] / stats['total'] * 100 if stats['total'] > 0 else 0
    print(f"{rule}: {stats['hit']}/{stats['total']} = {rate:.1f}%")

print("\n【详细表格】")
print("-" * 100)
print(f"| 编号 | 对阵 | 置信度 | 8变化 | 状态 | 规律 | 推荐 | 实际 | 结果 |")
print(f"|------|------|--------|-------|------|------|------|------|------|")
for r in results:
    hit_mark = "对" if r['hit'] else ""
    print(f"| {r['id']} | {r['match']} | {r['confidence']}% | {r['eight']:+d} | {r['state']} | {r['rule']} | {r['rec']} | {r['actual'] or '-'} | {hit_mark} |")

print("\n【规律详解】")
print("-" * 60)
print("规律1: 8变化-5 + 状态极好 → 推荐主胜/客胜（庄家挡不住，实盘）")
print("规律2: 8变化-5 + 状态焦灼 → 防平/不推荐（庄家主动降赔，诱盘）")
print("规律3: 8变化-2~-4 → 推荐平局（庄家不挡，最多小赢）")
print("规律4: 8变化正数 + 状态极好 → 推荐主胜/客胜（诱导但基本面强）")
print("规律5: 8变化正数 + 状态焦灼 → 反选（低赔+高回报诱导，诱盘）")
