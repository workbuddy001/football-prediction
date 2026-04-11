"""
V5优化版 - 增加平赔下降判断
核心逻辑：如果判断平局，且即时平赔多数下降，则增加平局信心
"""

import pandas as pd

# 威廉立博数据 + 初盘即时
WILLIAM_LADBROKES = {
    # 格式: (威廉初盘胜, 威廉初盘平, 威廉初盘负, 威廉即时胜, 威廉即时平, 威廉即时负, 立博初盘胜, 立博初盘平, 立博初盘负, 立博即时胜, 立博即时平, 立博即时负)
    '周五001': (2.50, 2.90, 2.50, 2.50, 2.90, 2.50, 2.60, 3.50, 2.50, 2.60, 3.50, 2.50),
    '周五002': (1.70, 3.45, 4.00, 1.75, 3.45, 4.00, 1.73, 3.45, 4.00, 1.73, 3.45, 4.00),
    '周五003': (2.35, 3.25, 2.85, 2.35, 3.25, 2.85, 2.30, 3.25, 2.90, 2.30, 3.25, 2.90),
    '周五004': (2.50, 2.90, 2.50, 2.20, 3.10, 2.80, 2.60, 3.50, 2.50, 2.37, 3.40, 2.80),
    '周五005': (2.10, 2.95, 3.40, 2.10, 2.95, 3.40, 2.10, 3.00, 3.40, 2.10, 3.00, 3.40),
    '周五006': (2.50, 3.30, 2.50, 2.50, 3.30, 2.50, 2.50, 3.30, 2.55, 2.50, 3.30, 2.55),
    '周五007': (1.85, 3.60, 3.65, 1.85, 3.60, 3.65, 1.85, 3.60, 3.65, 1.85, 3.60, 3.65),
    '周五008': (1.75, 3.55, 4.20, 1.75, 3.55, 4.20, 1.75, 3.55, 4.20, 1.75, 3.55, 4.20),
    '周五009': (1.80, 3.40, 4.30, 1.80, 3.40, 4.30, 1.80, 3.40, 4.30, 1.80, 3.40, 4.30),
    '周五010': (1.53, 3.80, 5.50, 1.55, 3.80, 5.50, 1.53, 3.80, 5.50, 1.53, 3.80, 5.50),
    '周五011': (2.25, 3.20, 3.00, 2.25, 3.20, 3.00, 2.25, 3.20, 3.00, 2.25, 3.20, 3.00),
    '周五012': (3.20, 3.15, 2.15, 3.20, 3.15, 2.15, 3.20, 3.15, 2.15, 3.20, 3.15, 2.15),
}

# 3.14数据（部分）
WILLIAM_LADBROKES_314 = {
    '周六001': (2.30, 3.20, 2.80, 2.30, 3.20, 2.80, 2.35, 3.20, 2.80, 2.35, 3.20, 2.80),
    '周六002': (1.95, 3.30, 3.50, 1.95, 3.30, 3.50, 1.95, 3.30, 3.50, 1.95, 3.30, 3.50),
    '周六003': (2.10, 3.30, 3.10, 2.10, 3.30, 3.10, 2.10, 3.30, 3.10, 2.10, 3.30, 3.10),
    '周六004': (1.95, 3.40, 3.30, 1.95, 3.40, 3.30, 1.95, 3.40, 3.30, 1.95, 3.40, 3.30),
    '周六005': (2.50, 3.00, 2.75, 2.50, 3.00, 2.75, 2.50, 3.00, 2.75, 2.50, 3.00, 2.75),
    '周六006': (1.55, 3.80, 5.00, 1.55, 3.80, 5.00, 1.55, 3.80, 5.00, 1.55, 3.80, 5.00),
}

# 3.15数据（部分）
WILLIAM_LADBROKES_315 = {
    '周日013': (1.40, 4.00, 6.50, 1.40, 4.00, 6.50, 1.40, 4.00, 6.50, 1.40, 4.00, 6.50),
    '周日015': (1.60, 3.60, 5.00, 1.60, 3.60, 5.00, 1.60, 3.60, 5.00, 1.60, 3.60, 5.00),
    '周日018': (2.40, 3.20, 2.70, 2.40, 3.20, 2.70, 2.40, 3.20, 2.70, 2.40, 3.20, 2.70),
    '周日027': (1.55, 3.60, 5.50, 1.55, 3.60, 5.50, 1.55, 3.60, 5.50, 1.55, 3.60, 5.50),
}


def check_draw_trend(code, wl_data):
    """
    检查平赔趋势
    返回: (下降公司数, 上升公司数, 总公司数)
    """
    if code not in wl_data:
        return None
    
    d = wl_data[code]
    # 威廉平赔变化
    w_draw_change = d[4] - d[1]  # 即时 - 初盘
    # 立博平赔变化
    l_draw_change = d[7] - d[10]  # 即时 - 初盘
    
    down_count = 0
    up_count = 0
    
    if w_draw_change < 0:
        down_count += 1
    elif w_draw_change > 0:
        up_count += 1
    
    if l_draw_change < 0:
        down_count += 1
    elif l_draw_change > 0:
        up_count += 1
    
    return down_count, up_count, 2


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


def v5_predict(row, wl_data):
    """V5优化版预测 - 增加平赔下降判断"""
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
    
    # 平赔趋势
    draw_trend = check_draw_trend(code, wl_data)
    draw_down = False
    if draw_trend:
        down, up, total = draw_trend
        if down > up:  # 多数下降
            draw_down = True
    
    # 威廉立博
    wl = wl_data.get(code)
    if wl:
        # 威廉即时
        w_home, w_draw, w_away = wl[3], wl[4], wl[5]
        # 立博即时
        l_home, l_draw, l_away = wl[9], wl[10], wl[11]
        # 平均
        avg_home = (w_home + l_home) / 2
        avg_draw = (w_draw + l_draw) / 2
        avg_away = (w_away + l_away) / 2
        distribution = get_distribution_type(avg_home, avg_draw, avg_away)
    else:
        distribution = get_distribution_type(home, draw, away)
    
    # ===== V5核心逻辑 =====
    
    # A级：极低赔 + 状态差距大
    if home < 1.6 and state_diff > 20:
        return "主胜", "A级", distribution
    if away < 1.6 and state_diff < -20:
        return "客胜", "A级", distribution
    
    # 顺分布 + 档位差距大 = 主胜
    if distribution == "顺分布" and state_diff > 15:
        return "主胜", "A级", distribution
    
    # ===== 新增：平赔下降判断 =====
    # 如果平赔多数下降，增加平局信心
    if draw_down:
        # 原本判断胜负，现在考虑防平
        if abs(state_diff) < 25:  # 状态接近
            if draw < 3.5:  # 平赔不太高
                return "防平", "B级", f"{distribution}+平降"
    
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
            if draw < 3.3:
                return "防平", "C级", distribution
    
    # 逆分布
    if distribution == "逆分布":
        if wl:
            w_home_init, w_draw_init = wl[0], wl[1]
            w_home_now, w_draw_now = wl[3], wl[4]
            # 威廉主胜下降 + 平赔上升 = 分散主胜到平局
            if w_home_now < w_home_init and w_draw_now > w_draw_init:
                return "防平", "B级", distribution
    
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


# ===== 测试 =====
def test_v5(date_str, df, wl_data, actual_results):
    print(f"\n{'='*75}")
    print(f"V5优化版 - {date_str}")
    print(f"{'='*75}")
    
    correct = 0
    total = 0
    
    for _, row in df.iterrows():
        code = row['编号']
        pred, conf, dist = v5_predict(row, wl_data)
        actual = actual_results.get(code, '')
        
        is_correct = pred == actual or ('防平' in pred and actual == '平')
        if is_correct:
            correct += 1
            mark = "OK"
        else:
            mark = "X"
        total += 1
        
        print(f"{code}: {pred:4s} {conf} {actual:4s} {mark} | {dist}")
    
    print(f"{'='*75}")
    print(f"准确率: {correct}/{total} = {correct/total*100:.1f}%")
    print(f"{'='*75}")


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
}

actual_315 = {
    '周日001': '客胜', '周日002': '客胜', '周日003': '主胜', '周日004': '平',
    '周日005': '主胜', '周日006': '主胜', '周日007': '主胜', '周日008': '平',
    '周日009': '客胜', '周日010': '主胜', '周日011': '主胜', '周日012': '平',
    '周日013': '主胜', '周日014': '平', '周日015': '主胜', '周日016': '主胜',
    '周日017': '客胜', '周日018': '主胜', '周日019': '平', '周日020': '客胜',
}


if __name__ == "__main__":
    # 3.13测试
    df = pd.read_excel('3.13_V3预测.xlsx')
    test_v5("3.13", df, WILLIAM_LADBROKES, actual_313)
