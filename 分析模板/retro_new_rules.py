"""
用新规律回溯3.10和3.11的比赛
新规律：
1. 胜率差 -15%~+15%（焦灼）：跟8增加最多的选项
2. 胜率差 >15%（主队极好）：跟8增加最多的选项  
3. 胜率差 <-15%（客队极好）：反选8增加最多的选项
"""

# 3.10 + 3.11 比赛数据
matches = [
    # 日期, 编号, 对阵, V7预测, 置信度, 胜率差, 主胜8变化, 平局8变化, 客胜8变化, 实际
    ("3.10", "周二001", "印度女 vs 中国台女", "客胜", 65, -20, -2, 0, -1, "客胜"),
    ("3.10", "周二002", "日本女 vs 越南女", "主胜", 90, +10, 0, 0, 0, "主胜"),
    ("3.10", "周二003", "町田泽维 vs 江原FC", "主胜", 55, +40, +1, 0, 0, "主胜"),
    ("3.10", "周二004", "布里兰 vs 墨尔本城", "客胜", 60, +60, 0, -1, -1, "平局"),
    ("3.10", "周二005", "加拉塔萨 vs 利物浦", "客胜", 72, +10, +2, 0, 0, "主胜"),
    ("3.10", "周二006", "朴次茅斯 vs 斯旺西", "主胜", 58, -20, +2, +1, 0, "客胜"),
    ("3.10", "周二007", "亚特兰大 vs 拜仁", "客胜", 60, -30, 0, 0, -1, "客胜"),
    ("3.10", "周二008", "马竞 vs 热刺", "主胜", 56, +40, +1, 0, 0, "主胜"),
    ("3.10", "周二009", "纽卡斯尔 vs 巴萨", "客胜", 62, -30, -1, 0, -1, "平局"),
    ("3.11", "周三001", "神户胜利 vs 首尔FC", "主胜", 58, +10, +2, 0, 0, "主胜"),
    ("3.11", "周三002", "广岛三箭 vs 柔佛", "主胜", 75, -20, 0, 0, 0, "主胜"),
    ("3.11", "周三003", "叻武里 vs 大阪钢巴", "客胜", 72, 0, 0, +1, 0, "平局"),
    ("3.11", "周三004", "勒沃库森 vs 阿森纳", "主胜", 65, -30, +2, +1, 0, "平局"),
    ("3.11", "周三005", "诺维奇 vs 谢菲联", "主胜", 55, +20, -1, -1, 0, "主胜"),
    ("3.11", "周三006", "西布罗姆 vs 南安普敦", "客胜", 58, -70, 0, +1, 0, "平局"),
    ("3.11", "周三007", "博德闪耀 vs 里斯本", "客胜", 62, +10, 0, -1, -2, "主胜"),
]

def get_zone(diff):
    """根据胜率差判断区间"""
    if diff < -15:
        return "客队极好"
    elif diff > 15:
        return "主队极好"
    else:
        return "焦灼"

def get_prediction(m):
    """根据新规律得出预测"""
    date, num, match, v7, conf, diff, h8, d8, a8, actual = m
    zone = get_zone(diff)
    
    # 找出8变化最大的选项
    changes = [("主胜", h8), ("平局", d8), ("客胜", a8)]
    max_change = max(changes, key=lambda x: x[1])
    
    # 没有8变化的情况
    if max_change[1] == 0:
        return "无8变化", zone, "-"
    
    most_8_option = max_change[0]
    most_8_value = max_change[1]
    
    # 根据规律判断
    if zone == "客队极好":
        # 规律3: 反选
        # 8增加最多的是主胜 → 预测客胜或平局
        # 8增加最多的是平局 → 预测主胜或客胜
        # 8增加最多的是客胜 → 预测主胜或平局
        if most_8_option == "主胜":
            pred = "客胜/平局"
        elif most_8_option == "平局":
            pred = "主胜/客胜"
        else:  # 客胜
            pred = "主胜/平局"
    else:
        # 规律1和2: 跟8增加最多的选项
        pred = most_8_option
    
    return pred, zone, f"{most_8_option}+{most_8_value}"

# 生成表格
print("=" * 100)
print("新规律回溯分析 - 3.10 + 3.11 比赛")
print("=" * 100)
print()
print("| 日期 | 编号 | 对阵 | 胜率差 | 区间 | 8变化 | 按规律预测 | V7预测 | 实际 | 结果 |")
print("|------|------|------|--------|------|-------|------------|--------|------|------|")

total = 0
correct = 0
no_8 = 0

for m in matches:
    date, num, match, v7, conf, diff, h8, d8, a8, actual = m
    
    pred, zone, change_str = get_prediction(m)
    
    # 判断是否命中
    if "无8变化" in pred:
        result = "-"
        no_8 += 1
    elif "/" in pred:
        # 双选命中
        if actual in pred:
            result = "OK"
            correct += 1
        else:
            result = "NO"
        total += 1
    else:
        if pred == actual:
            result = "OK"
            correct += 1
        else:
            result = "NO"
        total += 1
    
    print(f"| {date} | {num} | {match} | {diff:+d}% | {zone} | {change_str} | {pred} | {v7} | {actual} | {result} |")

print()
print("=" * 100)
print("统计结果")
print("=" * 100)

# 按区间统计
print("\n### 按区间统计")
for zone in ["客队极好", "焦灼", "主队极好"]:
    zone_total = 0
    zone_correct = 0
    
    for m in matches:
        date, num, match, v7, conf, diff, h8, d8, a8, actual = m
        if get_zone(diff) == zone:
            pred, _, change_str = get_prediction(m)
            
            if "无8变化" in pred:
                continue
            
            zone_total += 1
            if "/" in pred:
                if actual in pred:
                    zone_correct += 1
            else:
                if pred == actual:
                    zone_correct += 1
    
    if zone_total > 0:
        rate = zone_correct / zone_total * 100
        print(f"{zone}: {zone_correct}/{zone_total} = {rate:.1f}%")

# 总统计
print(f"\n总命中率: {correct}/{total} = {correct/total*100:.1f}% (无8变化: {no_8}场)")
