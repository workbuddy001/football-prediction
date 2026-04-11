"""
V4优化版测试3.13
"""

import pandas as pd
import os

# 读取3.13数据
df = pd.read_excel('3.13_V3预测.xlsx')

# 实际结果
actual = {
    '周五001': '平', '周五002': '主胜', '周五003': '平', '周五004': '主胜',
    '周五005': '客胜', '周五006': '平', '周五007': '平', '周五008': '主胜',
    '周五009': '主胜', '周五010': '主胜', '周五011': '主胜', '周五012': '平'
}

# 威廉立博数据（从源数据提取）
WILLIAM_LADBROKES = {
    '周五001': (2.50, 2.90, 2.50, 2.60, 3.50, 2.50),
    '周五002': (1.75, 3.45, 4.00, 1.73, 3.45, 4.00),
    '周五003': (2.35, 3.25, 2.85, 2.30, 3.25, 2.90),
    '周五004': (2.20, 3.10, 2.80, 2.37, 3.40, 2.80),
    '周五005': (2.10, 2.95, 3.40, 2.10, 3.00, 3.40),
    '周五006': (2.50, 3.30, 2.50, 2.50, 3.30, 2.55),
    '周五007': (1.85, 3.60, 3.65, 1.85, 3.60, 3.65),
    '周五008': (1.75, 3.55, 4.20, 1.75, 3.55, 4.20),
    '周五009': (1.80, 3.40, 4.30, 1.80, 3.40, 4.30),
    '周五010': (1.55, 3.80, 5.50, 1.53, 3.80, 5.50),
    '周五011': (2.25, 3.20, 3.00, 2.25, 3.20, 3.00),
    '周五012': (3.20, 3.15, 2.15, 3.20, 3.15, 2.15),
}

def get_distribution_type(home, draw, away):
    """判断分布类型"""
    ratio = home / draw
    if ratio < 0.65:
        return "顺分布"
    elif ratio > 0.85:
        return "逆分布"
    elif abs(home - away) < 0.3:
        return "缓冲分布"
    else:
        return "中庸分布"

def v4_predict(row):
    """V4优化版预测"""
    code = row['编号']
    home = row['主胜']
    draw = row['平局']
    away = row['客胜']
    
    # 状态
    try:
        home_state = float(str(row['主队状态']).replace('%', ''))
    except:
        home_state = 50
    try:
        away_state = float(str(row['客队状态']).replace('%', ''))
    except:
        away_state = 50
    state_diff = home_state - away_state
    
    # 威廉立博
    wl = WILLIAM_LADBROKES.get(code)
    if wl:
        w_home, w_draw, w_away, l_home, l_draw, l_away = wl
        # 使用平均赔率
        avg_home = (w_home + l_home) / 2
        avg_draw = (w_draw + l_draw) / 2
        avg_away = (w_away + l_away) / 2
        distribution = get_distribution_type(avg_home, avg_draw, avg_away)
    else:
        distribution = get_distribution_type(home, draw, away)
    
    # V4核心逻辑
    # A级：极低赔 + 状态差距大
    if home < 1.6 and state_diff > 20:
        return "主胜", "A级", distribution
    if away < 1.6 and state_diff < -20:
        return "客胜", "A级", distribution
    
    # 顺分布 + 档位差距大 = 主胜
    if distribution == "顺分布" and state_diff > 15:
        return "主胜", "A级", distribution
    
    # 中庸分布 + 状态接近 + 低平赔 = 防平
    if distribution == "中庸分布" and draw < 3.2 and abs(state_diff) < 20:
        return "防平", "B级", distribution
    
    # 缓冲分布
    if distribution == "缓冲分布":
        if state_diff > 25:
            return "主胜", "B级", distribution
        elif state_diff < -25:
            return "客胜", "B级", distribution
        else:
            # 状态接近，防平
            if draw < 3.3:
                return "防平", "C级", distribution
    
    # 逆分布
    if distribution == "逆分布":
        # 客队强但赔率接近，低开主胜是诱盘
        if wl and w_home < l_home - 0.1:
            return "客胜", "B级", distribution
        # 反之亦然
        if wl and w_away < l_away - 0.1:
            return "主胜", "B级", distribution
    
    # B级：低平赔 + 状态接近 = 防平
    if draw < 2.9 and abs(state_diff) < 15:
        return "防平", "B级", distribution
    
    # 状态差距大
    if state_diff > 30:
        return "主胜", "B级", distribution
    if state_diff < -30:
        return "客胜", "B级", distribution
    
    # 默认
    if home < away:
        return "主胜", "C级", distribution
    else:
        return "客胜", "C级", distribution

# 测试
print("=" * 70)
print("V4优化版 - 3.13 测试")
print("=" * 70)

correct = 0
total = 0

for _, row in df.iterrows():
    code = row['编号']
    pred, conf, dist = v4_predict(row)
    actual_result = actual.get(code, '')
    
    is_correct = pred == actual_result or ('防平' in pred and actual_result == '平')
    if is_correct:
        correct += 1
        mark = "OK"
    else:
        mark = "X"
    total += 1
    
    print(f"{code}: {pred:4s} {conf} 分布={dist:8s} 实际={actual_result:4s} {mark}")

print("=" * 70)
print(f"准确率: {correct}/{total} = {correct/total*100:.1f}%")
print("=" * 70)
