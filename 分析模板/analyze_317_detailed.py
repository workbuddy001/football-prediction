"""
3.17比赛详细推理分析
"""
import os
import re

# 比赛列表和关键数据（手动整理）
matches = [
    {
        "id": "周一001",
        "match": "海尔蒙特 vs 坎布尔",
        "v7": "客胜",
        "confidence": 58,
        "home_rate": 20,  # 主队胜率
        "away_rate": 70,  # 客队胜率
        "eight_change": -5,  # 总8变化
        "home_eight_change": 0,  # 主胜8变化
        "draw_eight_change": 0,  # 平局8变化
        "away_eight_change": -5,  # 客胜8变化
        "actual": "客胜",
    },
    {
        "id": "周一004",
        "match": "布伦特 vs 狼队",
        "v7": "主胜",
        "confidence": 64,
        "home_rate": 40,
        "away_rate": 30,
        "eight_change": 3,
        "home_eight_change": 1,
        "draw_eight_change": 1,
        "away_eight_change": 1,
        "actual": "平局",
    },
    {
        "id": "周一006",
        "match": "巴列卡诺 vs 莱万特",
        "v7": "主胜",
        "confidence": 55,
        "home_rate": 43,
        "away_rate": 14,
        "eight_change": 3,
        "home_eight_change": 1,
        "draw_eight_change": 1,
        "away_eight_change": 1,
        "actual": "平局",
    },
    {
        "id": "周二002",
        "match": "中国女 vs  Austral女",
        "v7": "客胜",
        "confidence": 47,
        "home_rate": 70,
        "away_rate": 70,
        "eight_change": 1,
        "home_eight_change": 0,
        "draw_eight_change": 0,
        "away_eight_change": 1,
        "actual": None,
    },
    {
        "id": "周二004",
        "match": "里斯本 vs 博德闪耀",
        "v7": "主胜",
        "confidence": 62,
        "home_rate": 60,
        "away_rate": 90,
        "eight_change": -2,
        "home_eight_change": 1,
        "draw_eight_change": -1,
        "away_eight_change": -2,
        "actual": None,
    },
    {
        "id": "周二006",
        "match": "阿森纳 vs 勒沃库森",
        "v7": "主胜",
        "confidence": 73,
        "home_rate": 70,
        "away_rate": 30,
        "eight_change": 2,
        "home_eight_change": 2,
        "draw_eight_change": 0,
        "away_eight_change": 0,
        "actual": None,
    },
    {
        "id": "周二008",
        "match": "曼城 vs 皇马",
        "v7": "主胜",
        "confidence": 67,
        "home_rate": 70,
        "away_rate": 80,
        "eight_change": 0,
        "home_eight_change": 0,
        "draw_eight_change": 0,
        "away_eight_change": 0,
        "actual": None,
    },
    {
        "id": "周三001",
        "match": "韩国女 vs 日本女",
        "v7": "客胜",
        "confidence": 63,
        "home_rate": 40,
        "away_rate": 60,
        "eight_change": -3,
        "home_eight_change": 0,
        "draw_eight_change": -1,
        "away_eight_change": -2,
        "actual": None,
    },
]

# 规律定义
def get_state(home_rate, away_rate):
    diff = home_rate - away_rate
    if abs(diff) <= 15:
        return "焦灼", diff
    elif diff > 15:
        return "主队极好", diff
    else:
        return "客队极好", diff

def analyze_match(m):
    """逐步推理分析"""
    steps = []
    
    # ===== 步骤1: 置信度 =====
    conf_pass = m['confidence'] >= 55
    steps.append(f"【步骤1】置信度: {m['confidence']}% {'[OK]' if conf_pass else '[X]'}")
    
    if not conf_pass:
        steps.append("→ 不推荐，置信度不足")
        return steps, "不推荐"
    
    # ===== 步骤2: 8变化 =====
    eight = m['eight_change']
    if eight == -5:
        eight_label = "-5 (大幅减少)"
    elif -4 <= eight <= -2:
        eight_label = f"{eight} (减少)"
    elif eight > 0:
        eight_label = f"+{eight} (增加)"
    else:
        eight_label = f"{eight}"
    steps.append(f"【步骤2】总8变化: {eight_label}")
    
    # ===== 步骤3: 状态 =====
    state, diff = get_state(m['home_rate'], m['away_rate'])
    steps.append(f"【步骤3】状态: {state} (主{m['home_rate']}% vs 客{m['away_rate']}%, 差{diff}%)")
    
    # ===== 步骤4: 规律判断 =====
    v7 = m['v7']
    
    # 规律1: 8变化-5 + 状态极好
    if eight == -5 and state != "焦灼":
        if state == "主队极好":
            recommendation = "主胜"
            steps.append(f"【步骤4】规律判断: 8变化-5 + {state} → 规律1 → 推荐{v7}")
            steps.append("→ 逻辑: 8减少+状态极好 = 庄家挡不住资金涌入 = 实盘")
        else:  # 客队极好
            recommendation = "客胜"
            steps.append(f"【步骤4】规律判断: 8变化-5 + {state} → 规律1 → 推荐{v7}")
            steps.append("→ 逻辑: 8减少+状态极好 = 庄家挡不住资金涌入 = 实盘")
    
    # 规律2: 8变化-5 + 状态焦灼 = 诱盘
    elif eight == -5 and state == "焦灼":
        recommendation = "不推荐/防平"
        steps.append(f"【步骤4】规律判断: 8变化-5 + 状态焦灼 → 规律2")
        steps.append("→ 逻辑: 8减少+状态焦灼 = 庄家主动降赔 = 诱盘风险")
    
    # 规律3: 8变化-2~-4
    elif -4 <= eight <= -2:
        recommendation = "平局"
        steps.append(f"【步骤4】规律判断: 8变化{eight} 在-2~-4区间 → 规律3")
        steps.append("→ 逻辑: 8减少但不是-5 = 庄家不挡 = 最多小赢 = 走水/平局")
    
    # 规律4: 8变化正数 + 状态极好
    elif eight > 0 and state != "焦灼":
        recommendation = v7
        steps.append(f"【步骤4】规律判断: 8变化+{eight} + {state} → 规律4")
        steps.append("→ 逻辑: 8增加+状态极好 = 庄家诱导但基本面强 = 跟庄家")
    
    # 规律5: 8变化正数 + 状态焦灼
    elif eight > 0 and state == "焦灼":
        # 反向推荐
        if v7 == "主胜":
            recommendation = "客胜/平局"
        elif v7 == "客胜":
            recommendation = "主胜/平局"
        else:
            recommendation = "平局"
        steps.append(f"【步骤4】规律判断: 8变化+{eight} + {state} → 规律5")
        steps.append("→ 逻辑: 8增加+状态焦灼 = 低赔+高回报诱导 = 诱盘，打不出预测")
    
    # 8变化=0
    elif eight == 0:
        recommendation = "观察"
        steps.append(f"【步骤4】规律判断: 8变化=0 → 无规律")
        steps.append("→ 逻辑: 8无变化 = 庄家不作为 = 观望")
    
    # 其他
    else:
        recommendation = "观察"
        steps.append(f"【步骤4】规律判断: 8变化{eight} 不在已知规律区间")
        steps.append("→ 逻辑: 需要更多观察")
    
    return steps, recommendation

# 输出分析
print("=" * 80)
print("3.17比赛详细推理分析（老方法：总8变化）")
print("=" * 80)

for m in matches:
    print(f"\n{'='*80}")
    print(f"【{m['id']}】{m['match']}")
    print(f"V7预测: {m['v7']} | 置信度: {m['confidence']}%")
    print("-" * 40)
    
    steps, rec = analyze_match(m)
    for step in steps:
        print(step)
    
    print("-" * 40)
    print(f"【最终推荐】: {rec}")
    if m['actual']:
        is_correct = "对" if rec.replace('不推荐/','').replace('/平局','').replace('/客胜','').replace('/主胜','').strip() == m['actual'] else ""
    print(f"【实际结果】: {m['actual']} {is_correct}")
    print()

print("\n" + "=" * 80)
print("汇总表格")
print("=" * 80)
print(f"| 编号 | 对阵 | 置信度 | 8变化 | 状态 | 规律 | 推荐 |")
print(f"|------|------|--------|-------|------|------|------|")
for m in matches:
    state, diff = get_state(m['home_rate'], m['away_rate'])
    steps, rec = analyze_match(m)
    # 找规律
    eight = m['eight_change']
    if eight == -5 and state != "焦灼":
        rule = "规律1"
    elif eight == -5 and state == "焦灼":
        rule = "规律2"
    elif -4 <= eight <= -2:
        rule = "规律3"
    elif eight > 0 and state != "焦灼":
        rule = "规律4"
    elif eight > 0 and state == "焦灼":
        rule = "规律5"
    elif eight == 0:
        rule = "无规律"
    else:
        rule = "其他"
    
    print(f"| {m['id']} | {m['match']} | {m['confidence']}% | {m['eight_change']:+d} | {state} | {rule} | {rec} |")
