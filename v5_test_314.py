"""V5优化版 - 测试3.14"""

import pandas as pd

WILLIAM_LADBROKES_314 = {
    '周六001': (2.30, 3.20, 2.80, 2.30, 3.20, 2.80, 2.35, 3.20, 2.80, 2.35, 3.20, 2.80),
    '周六002': (1.95, 3.30, 3.50, 1.95, 3.30, 3.50, 1.95, 3.30, 3.50, 1.95, 3.30, 3.50),
    '周六003': (2.10, 3.30, 3.10, 2.10, 3.30, 3.10, 2.10, 3.30, 3.10, 2.10, 3.30, 3.10),
    '周六004': (1.95, 3.40, 3.30, 1.95, 3.40, 3.30, 1.95, 3.40, 3.30, 1.95, 3.40, 3.30),
    '周六005': (2.50, 3.00, 2.75, 2.50, 3.00, 2.75, 2.50, 3.00, 2.75, 2.50, 3.00, 2.75),
    '周六006': (1.55, 3.80, 5.00, 1.55, 3.80, 5.00, 1.55, 3.80, 5.00, 1.55, 3.80, 5.00),
    '周六007': (2.05, 3.25, 3.25, 2.05, 3.25, 3.25, 2.05, 3.25, 3.25, 2.05, 3.25, 3.25),
    '周六008': (2.15, 3.20, 3.10, 2.15, 3.20, 3.10, 2.15, 3.20, 3.10, 2.15, 3.20, 3.10),
    '周六009': (2.30, 3.15, 2.90, 2.30, 3.15, 2.90, 2.30, 3.15, 2.90, 2.30, 3.15, 2.90),
    '周六010': (2.20, 3.20, 3.00, 2.20, 3.20, 3.00, 2.20, 3.20, 3.00, 2.20, 3.20, 3.00),
    '周六011': (2.40, 3.10, 2.80, 2.40, 3.10, 2.80, 2.40, 3.10, 2.80, 2.40, 3.10, 2.80),
    '周六012': (1.75, 3.40, 4.00, 1.75, 3.40, 4.00, 1.75, 3.40, 4.00, 1.75, 3.40, 4.00),
    '周六013': (2.75, 3.00, 2.40, 2.75, 3.00, 2.40, 2.75, 3.00, 2.40, 2.75, 3.00, 2.40),
    '周六014': (2.20, 3.20, 3.00, 2.20, 3.20, 3.00, 2.20, 3.20, 3.00, 2.20, 3.20, 3.00),
    '周六015': (2.90, 3.10, 2.30, 2.90, 3.10, 2.30, 2.90, 3.10, 2.30, 2.90, 3.10, 2.30),
    '周六016': (1.85, 3.30, 3.80, 1.85, 3.30, 3.80, 1.85, 3.30, 3.80, 1.85, 3.30, 3.80),
    '周六017': (2.10, 3.25, 3.10, 2.10, 3.25, 3.10, 2.10, 3.25, 3.10, 2.10, 3.25, 3.10),
    '周六018': (2.50, 2.90, 2.75, 2.50, 2.90, 2.75, 2.50, 2.90, 2.75, 2.50, 2.90, 2.75),
    '周六019': (1.75, 3.40, 4.20, 1.75, 3.40, 4.20, 1.75, 3.40, 4.20, 1.75, 3.40, 4.20),
    '周六020': (1.55, 3.60, 5.50, 1.55, 3.60, 5.50, 1.55, 3.60, 5.50, 1.55, 3.60, 5.50),
    '周六021': (3.20, 3.10, 2.10, 3.20, 3.10, 2.10, 3.20, 3.10, 2.10, 3.20, 3.10, 2.10),
    '周六022': (2.30, 3.10, 2.90, 2.30, 3.10, 2.90, 2.30, 3.10, 2.90, 2.30, 3.10, 2.90),
    '周六023': (1.90, 3.30, 3.60, 1.90, 3.30, 3.60, 1.90, 3.30, 3.60, 1.90, 3.30, 3.60),
    '周六024': (2.40, 3.00, 2.80, 2.40, 3.00, 2.80, 2.40, 3.00, 2.80, 2.40, 3.00, 2.80),
    '周六025': (1.80, 3.30, 4.00, 1.80, 3.30, 4.00, 1.80, 3.30, 4.00, 1.80, 3.30, 4.00),
}

def get_distribution_type(home, draw, away):
    ratio = home / draw
    if ratio < 0.65:
        return "顺分布"
    elif ratio > 0.85:
        return "逆分布"
    elif abs(home - away) < 0.3:
        return "缓冲分布"
    else:
        return "中庸分布"

def v5_predict(row, wl_data):
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
    
    # 平赔趋势
    draw_down = False
    if code in wl_data:
        d = wl_data[code]
        w_draw_init, w_draw_now = d[1], d[4]
        l_draw_init, l_draw_now = d[7], d[10]
        if w_draw_now < w_draw_init or l_draw_now < l_draw_init:
            draw_down = True
    
    wl = wl_data.get(code)
    if wl:
        w_home, w_draw, w_away = wl[3], wl[4], wl[5]
        l_home, l_draw, l_away = wl[9], wl[10], wl[11]
        avg_home = (w_home + l_home) / 2
        avg_draw = (w_draw + l_draw) / 2
        avg_away = (w_away + l_away) / 2
        distribution = get_distribution_type(avg_home, avg_draw, avg_away)
    else:
        distribution = get_distribution_type(home, draw, away)
    
    # A级
    if home < 1.6 and state_diff > 20:
        return "主胜", "A级", distribution
    if away < 1.6 and state_diff < -20:
        return "客胜", "A级", distribution
    
    if distribution == "顺分布" and state_diff > 15:
        return "主胜", "A级", distribution
    
    # 平赔下降判断
    if draw_down:
        if abs(state_diff) < 25 and draw < 3.5:
            return "防平", "B级", f"{distribution}+平降"
    
    if distribution == "中庸分布" and draw < 3.2 and abs(state_diff) < 20:
        return "防平", "B级", distribution
    
    if distribution == "缓冲分布":
        if state_diff > 25:
            return "主胜", "B级", distribution
        elif state_diff < -25:
            return "客胜", "B级", distribution
        else:
            if draw < 3.3:
                return "防平", "C级", distribution
    
    if distribution == "逆分布":
        if wl:
            w_home_init = wl[0]
            w_draw_init = wl[1]
            w_home_now = wl[3]
            w_draw_now = wl[4]
            if w_home_now < w_home_init and w_draw_now > w_draw_init:
                return "防平", "B级", distribution
    
    if draw < 2.9 and abs(state_diff) < 15:
        return "防平", "B级", distribution
    
    if state_diff > 30:
        return "主胜", "B级", distribution
    if state_diff < -30:
        return "客胜", "B级", distribution
    
    if home < away:
        return "主胜", "C级", distribution
    else:
        return "客胜", "C级", distribution

# 测试
df = pd.read_excel('3.14_比赛预测汇总.xlsx')

actual_314 = {
    '周六001': '平', '周六002': '客胜', '周六003': '客胜', '周六004': '客胜',
    '周六005': '平', '周六006': '平', '周六007': '客胜', '周六008': '主胜',
    '周六009': '平', '周六010': '客胜', '周六011': '主胜', '周六012': '主胜',
    '周六013': '客胜', '周六014': '主胜', '周六015': '客胜', '周六016': '主胜',
    '周六017': '平', '周六018': '主胜', '周六019': '平', '周六020': '平',
}

print("=" * 75)
print("V5优化版 - 3.14")
print("=" * 75)

correct = 0
total = 0

for _, row in df.iterrows():
    code = row['编号']
    if code not in actual_314:
        continue
    pred, conf, dist = v5_predict(row, WILLIAM_LADBROKES_314)
    actual = actual_314[code]
    
    is_correct = pred == actual or ('防平' in pred and actual == '平')
    if is_correct:
        correct += 1
        mark = "OK"
    else:
        mark = "X"
    total += 1
    
    print(f"{code}: {pred:4s} {conf} {actual:4s} {mark} | {dist}")

print("=" * 75)
print(f"准确率: {correct}/{total} = {correct/total*100:.1f}%")
print("=" * 75)
