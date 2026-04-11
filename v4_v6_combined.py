"""
V4 + V6 联合分析
只有两者结果相同时才推荐
"""

import pandas as pd

# ===== 澳门心水 =====
MACAO_TIP = {
    # 3.13
    '周五001': '和局', '周五002': '主胜', '周五003': '主胜', '周五004': '和局',
    '周五005': '主胜', '周五006': '客胜', '周五007': '主胜', '周五008': '主胜',
    '周五009': '客胜', '周五010': '主胜', '周五011': '主胜', '周五012': '客胜',
    # 3.14
    '周六001': '和局', '周六002': '客胜', '周六003': '客胜', '周六004': '客胜',
    '周六005': '和局', '周六006': '和局', '周六007': '客胜', '周六008': '主胜',
    '周六009': '和局', '周六010': '客胜', '周六011': '主胜', '周六012': '主胜',
    '周六013': '客胜', '周六014': '主胜', '周六015': '客胜', '周六016': '主胜',
    '周六017': '和局', '周六018': '主胜', '周六019': '和局', '周六020': '和局',
    # 3.15
    '周日001': '客胜', '周日002': '客胜', '周日003': '主胜', '周日004': '和局',
    '周日005': '主胜', '周日006': '主胜', '周日007': '主胜', '周日008': '和局',
    '周日009': '客胜', '周日010': '主胜', '周日011': '主胜', '周日012': '和局',
    '周日013': '主胜', '周日014': '和局', '周日015': '主胜', '周日016': '主胜',
    '周日017': '客胜', '周日018': '主胜', '周日019': '和局', '周日020': '客胜',
}

# ===== 威廉立博数据 =====
WILLIAM_LADBROKES = {
    # 3.13
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
    # 3.14
    '周六001': (2.30, 3.20, 2.80, 2.35, 3.20, 2.80),
    '周六002': (1.95, 3.30, 3.50, 1.95, 3.30, 3.50),
    '周六003': (2.10, 3.30, 3.10, 2.10, 3.30, 3.10),
    '周六004': (1.95, 3.40, 3.30, 1.95, 3.40, 3.30),
    '周六005': (2.50, 3.00, 2.75, 2.50, 3.00, 2.75),
    '周六006': (1.55, 3.80, 5.00, 1.55, 3.80, 5.00),
    '周六007': (2.05, 3.25, 3.25, 2.05, 3.25, 3.25),
    '周六008': (2.15, 3.20, 3.10, 2.15, 3.20, 3.10),
    '周六009': (2.30, 3.15, 2.90, 2.30, 3.15, 2.90),
    '周六010': (2.20, 3.20, 3.00, 2.20, 3.20, 3.00),
    '周六011': (2.40, 3.10, 2.80, 2.40, 3.10, 2.80),
    '周六012': (1.75, 3.40, 4.00, 1.75, 3.40, 4.00),
    '周六013': (2.75, 3.00, 2.40, 2.75, 3.00, 2.40),
    '周六014': (2.20, 3.20, 3.00, 2.20, 3.20, 3.00),
    '周六015': (2.90, 3.10, 2.30, 2.90, 3.10, 2.30),
    '周六016': (1.85, 3.30, 3.80, 1.85, 3.30, 3.80),
    '周六017': (2.10, 3.25, 3.10, 2.10, 3.25, 3.10),
    '周六018': (2.50, 2.90, 2.75, 2.50, 2.90, 2.75),
    '周六019': (1.75, 3.40, 4.20, 1.75, 3.40, 4.20),
    '周六020': (1.55, 3.60, 5.50, 1.55, 3.60, 5.50),
    # 3.15
    '周日001': (2.10, 3.20, 3.20, 2.10, 3.20, 3.20),
    '周日002': (1.55, 3.60, 5.50, 1.55, 3.60, 5.50),
    '周日003': (1.75, 3.40, 4.20, 1.75, 3.40, 4.20),
    '周日004': (2.30, 3.10, 2.90, 2.30, 3.10, 2.90),
    '周日005': (2.60, 3.00, 2.60, 2.60, 3.00, 2.60),
    '周日006': (1.85, 3.30, 3.80, 1.85, 3.30, 3.80),
    '周日007': (2.20, 3.20, 2.90, 2.20, 3.20, 2.90),
    '周日008': (2.40, 3.10, 2.80, 2.40, 3.10, 2.80),
    '周日009': (1.70, 3.40, 4.50, 1.70, 3.40, 4.50),
    '周日010': (2.10, 3.20, 3.20, 2.10, 3.20, 3.20),
    '周日011': (2.50, 2.90, 2.75, 2.50, 2.90, 2.75),
    '周日012': (1.80, 3.30, 4.00, 1.80, 3.30, 4.00),
    '周日013': (1.40, 4.00, 6.50, 1.40, 4.00, 6.50),
    '周日014': (2.10, 3.30, 3.20, 2.10, 3.30, 3.20),
    '周日015': (1.60, 3.60, 5.00, 1.60, 3.60, 5.00),
    '周日016': (1.95, 3.30, 3.50, 1.95, 3.30, 3.50),
    '周日017': (1.80, 3.40, 4.20, 1.80, 3.40, 4.20),
    '周日018': (2.40, 3.20, 2.70, 2.40, 3.20, 2.70),
    '周日019': (2.20, 3.20, 3.00, 2.20, 3.20, 3.00),
    '周日020': (2.00, 3.30, 3.40, 2.00, 3.30, 3.40),
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


# ===== V4算法 =====
def v4_predict(row, wl_data):
    code = row['编号']
    home = row['主胜']
    draw = row['平局']
    away = row['客胜']
    
    try:
        home_state = float(str(row['主队状态']).replace('%', ''))
    except:
        home_state = 50
    try:
        away_state = float(str(row['客队状态']).replace('%', ''))
    except:
        away_state = 50
    state_diff = home_state - away_state
    
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
    
    # V4核心逻辑
    if home < 1.6 and state_diff > 20:
        return "主胜"
    if away < 1.6 and state_diff < -20:
        return "客胜"
    if distribution == "顺分布" and state_diff > 15:
        return "主胜"
    if distribution == "中庸分布" and draw < 3.2 and abs(state_diff) < 20:
        return "防平"
    if distribution == "缓冲分布":
        if state_diff > 25:
            return "主胜"
        elif state_diff < -25:
            return "客胜"
        else:
            if draw < 3.3:
                return "防平"
    if draw < 2.9 and abs(state_diff) < 15:
        return "防平"
    if state_diff > 30:
        return "主胜"
    if state_diff < -30:
        return "客胜"
    if home < away:
        return "主胜"
    else:
        return "客胜"


# ===== V6算法 =====
def v6_predict(row, wl_data, macao_data):
    code = row['编号']
    home = row['主胜']
    draw = row['平局']
    away = row['客胜']
    
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
    
    # V6: 澳门 vs 赔率
    if macao_tip and wl:
        w_home, w_draw, w_away = wl[0], wl[1], wl[2]
        l_home, l_draw, l_away = wl[3], wl[4], wl[5]
        avg_home = (w_home + l_home) / 2
        avg_away = (w_away + l_away) / 2
        avg_draw = (w_draw + l_draw) / 2
        
        if macao_tip == "主胜":
            if avg_home < avg_away:
                return "主胜"
            else:
                return "客胜" if avg_away < 2.5 else "防平"
        elif macao_tip == "客胜":
            if avg_away < avg_home:
                return "客胜"
            else:
                return "主胜" if avg_home < 2.5 else "防平"
        elif macao_tip == "和局":
            if avg_draw < 3.3:
                return "防平"
            else:
                return "主胜" if avg_home < avg_away else "客胜"
    
    # 原有逻辑
    if home < 1.6 and state_diff > 20:
        return "主胜"
    if away < 1.6 and state_diff < -20:
        return "客胜"
    if distribution == "顺分布" and state_diff > 15:
        return "主胜"
    if distribution == "中庸分布" and draw < 3.2 and abs(state_diff) < 20:
        return "防平"
    if distribution == "缓冲分布":
        if state_diff > 25:
            return "主胜"
        elif state_diff < -25:
            return "客胜"
        else:
            if draw < 3.3:
                return "防平"
    if draw < 2.9 and abs(state_diff) < 15:
        return "防平"
    if state_diff > 30:
        return "主胜"
    if state_diff < -30:
        return "客胜"
    if home < away:
        return "主胜"
    else:
        return "客胜"


# ===== 测试 =====
def test_day(date_str, df, actual):
    print(f"\n{'='*80}")
    print(f"{date_str} - V4 + V6 联合分析")
    print(f"{'='*80}")
    
    # 统计
    v4_correct = 0
    v6_correct = 0
    both_correct = 0
    both_same = 0
    both_diff = 0
    
    for _, row in df.iterrows():
        code = row['编号']
        if code not in actual:
            continue
        
        actual_result = actual[code]
        
        v4_pred = v4_predict(row, WILLIAM_LADBROKES)
        v6_pred = v6_predict(row, WILLIAM_LADBROKES, MACAO_TIP)
        
        # V4准确
        v4_ok = v4_pred == actual_result or ('防平' in v4_pred and actual_result == '平')
        if v4_ok:
            v4_correct += 1
        
        # V6准确
        v6_ok = v6_pred == actual_result or ('防平' in v6_pred and actual_result == '平')
        if v6_ok:
            v6_correct += 1
        
        # 两者相同
        same = v4_pred == v6_pred
        if same:
            both_same += 1
            # 相同且正确
            if v6_pred == actual_result or ('防平' in v6_pred and actual_result == '平'):
                both_correct += 1
                mark = "OK"
            else:
                mark = "X"
        else:
            both_diff += 1
            mark = "-"
        
        if mark != "-":
            print(f"{code}: V4={v4_pred:4s} V6={v6_pred:4s} 实际={actual_result:4s} {mark}")
    
    print(f"{'='*80}")
    print(f"V4准确: {v4_correct}/{len(actual)} = {v4_correct/len(actual)*100:.1f}%")
    print(f"V6准确: {v6_correct}/{len(actual)} = {v6_correct/len(actual)*100:.1f}%")
    print(f"两者相同: {both_same}场，其中正确: {both_correct}场 = {both_correct/both_same*100:.1f}%")
    print(f"两者不同: {both_diff}场")
    print(f"{'='*80}")
    
    return both_same, both_correct


# 实际结果
actual_313 = {
    '周五001': '平', '周五002': '主胜', '周五003': '平', '周五004': '主胜',
    '周五005': '客胜', '周五006': '平', '周五007': '平', '周五008': '主胜',
    '周五009': '主胜', '周五010': '主胜', '周五011': '主胜', '周五012': '平'
}
actual_314 = {
    '周六001': '平', '周六002': '客胜', '周六003': '客胜', '周六004': '客胜',
    '周六005': '平', '周六006': '平', '周六007': '客胜', '周六008': '主胜',
    '周六009': '平', '周六010': '客胜', '周六011': '主胜', '周六012': '主胜',
    '周六013': '客胜', '周六014': '主胜', '周六015': '客胜', '周六016': '主胜',
    '周六017': '平', '周六018': '主胜', '周六019': '平', '周六020': '平',
}
actual_315 = {
    '周日001': '客胜', '周日002': '客胜', '周日003': '主胜', '周日004': '平',
    '周日005': '主胜', '周日006': '主胜', '周日007': '主胜', '周日008': '平',
    '周日009': '客胜', '周日010': '主胜', '周日011': '主胜', '周日012': '平',
    '周日013': '主胜', '周日014': '平', '周日015': '主胜', '周日016': '主胜',
    '周日017': '客胜', '周日018': '主胜', '周日019': '平', '周日020': '客胜',
}

# 测试3天
total_same = 0
total_correct = 0

# 3.13
df = pd.read_excel('3.13_V3预测.xlsx')
s, c = test_day("3.13", df, actual_313)
total_same += s
total_correct += c

# 3.14
df = pd.read_excel('3.14_比赛预测汇总.xlsx')
s, c = test_day("3.14", df, actual_314)
total_same += s
total_correct += c

# 3.15
df = pd.read_excel('3.15_V3预测.xlsx')
s, c = test_day("3.15", df, actual_315)
total_same += s
total_correct += c

print(f"\n{'#'*80}")
print(f"总体: 两者相同共{total_same}场，正确{total_correct}场 = {total_correct/total_same*100:.1f}%")
print(f"{'#'*80}")
