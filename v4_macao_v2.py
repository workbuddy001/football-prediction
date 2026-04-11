"""
V4优化版 + 澳门心水 v2
澳门主胜+低主赔 = 实盘
澳门和局+低平赔 = 防平
"""

import pandas as pd

# 澳门心水
MACAO_TIP = {
    '周五001': '和局',
    '周五002': '主胜',
    '周五003': '主胜',
    '周五004': '和局',
    '周五005': '主胜',
    '周五006': '客胜',
    '周五007': '主胜',
    '周五008': '主胜',
    '周五009': '客胜',
    '周五010': '主胜',
    '周五011': '主胜',
    '周五012': '客胜',
}

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

def get_distribution(home, draw, away):
    ratio = home / draw
    if ratio < 0.65:
        return "顺分布"
    elif ratio > 0.85:
        return "逆分布"
    elif abs(home - away) < 0.3:
        return "缓冲分布"
    else:
        return "中庸分布"

def v4_macao_v2(row, wl_data, macao_data):
    """V4 + 澳门心水 v2"""
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
    
    macao_tip = macao_data.get(code, '')
    
    # 威廉立博
    wl = wl_data.get(code)
    if wl:
        w_home, w_draw, w_away = wl[0], wl[1], wl[2]
        l_home, l_draw, l_away = wl[3], wl[4], wl[5]
        avg_home = (w_home + l_home) / 2
        avg_draw = (w_draw + l_draw) / 2
        avg_away = (w_away + l_away) / 2
        distribution = get_distribution(avg_home, avg_draw, avg_away)
    else:
        distribution = get_distribution(home, draw, away)
    
    # ===== 核心逻辑 =====
    
    # 1. 澳门主胜 + 主赔低（<2.0）= A级实盘
    if macao_tip == "主胜" and home < 2.0:
        return "主胜", "A级", f"澳门主胜+低赔"
    
    # 2. 澳门客胜 + 客赔低（<2.0）= A级实盘
    if macao_tip == "客胜" and away < 2.0:
        return "客胜", "A级", f"澳门客胜+低赔"
    
    # 3. 澳门和局 + 平赔低（<3.3）= A级防平
    if macao_tip == "和局" and draw < 3.3:
        return "防平", "A级", f"澳门和局+低平"
    
    # 4. 澳门和局 + 逆分布 = 防平
    if macao_tip == "和局" and distribution == "逆分布":
        return "防平", "B级", f"澳门和局+逆分布"
    
    # 5. A级：极低赔 + 状态差距大
    if home < 1.6 and state_diff > 20:
        return "主胜", "A级", f"{distribution}+极低赔"
    if away < 1.6 and state_diff < -20:
        return "客胜", "A级", f"{distribution}+极低赔"
    
    # 6. 顺分布 + 档位差距大
    if distribution == "顺分布" and state_diff > 15:
        return "主胜", "A级", f"{distribution}+状态差"
    
    # 7. 中庸分布 + 低平赔 = 防平
    if distribution == "中庸分布" and draw < 3.2 and abs(state_diff) < 20:
        return "防平", "B级", f"{distribution}+低平"
    
    # 8. 缓冲分布
    if distribution == "缓冲分布":
        if state_diff > 25:
            return "主胜", "B级", distribution
        elif state_diff < -25:
            return "客胜", "B级", distribution
        else:
            if draw < 3.3:
                return "防平", "C级", distribution
    
    # 9. 低平赔 + 状态接近 = 防平
    if draw < 2.9 and abs(state_diff) < 15:
        return "防平", "B级", "低平赔"
    
    # 10. 状态差距大
    if state_diff > 30:
        return "主胜", "B级", "状态差距大"
    if state_diff < -30:
        return "客胜", "B级", "状态差距大"
    
    # 默认
    if home < away:
        return "主胜", "C级", "概率最高"
    else:
        return "客胜", "C级", "概率最高"


# 测试
print("=" * 80)
print("V4 + 澳门心水 v2 - 3.13")
print("=" * 80)

df = pd.read_excel('3.13_V3预测.xlsx')

actual = {
    '周五001': '平', '周五002': '主胜', '周五003': '平', '周五004': '主胜',
    '周五005': '客胜', '周五006': '平', '周五007': '平', '周五008': '主胜',
    '周五009': '主胜', '周五010': '主胜', '周五011': '主胜', '周五012': '平'
}

correct = 0
total = 0

for _, row in df.iterrows():
    code = row['编号']
    pred, conf, reason = v4_macao_v2(row, WILLIAM_LADBROKES, MACAO_TIP)
    actual_result = actual.get(code, '')
    
    is_correct = pred == actual_result or ('防平' in pred and actual_result == '平')
    if is_correct:
        correct += 1
        mark = "OK"
    else:
        mark = "X"
    total += 1
    
    macao = MACAO_TIP.get(code, '')
    print(f"{code}: 澳门={macao:4s} 预测={pred:4s} 实际={actual_result:4s} {mark} | {reason}")

print("=" * 80)
print(f"准确率: {correct}/{total} = {correct/total*100:.1f}%")
print("=" * 80)
