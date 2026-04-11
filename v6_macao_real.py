"""
V6优化版 - 澳门心水判断实盘/诱盘
核心思路：
- 澳门心水 = 玩家倾向
- 庄家赔率 vs 玩家倾向 = 实盘或诱盘

逻辑：
- 澳门主胜 + 赔率支持主胜 = 实盘主胜
- 澳门主胜 + 赔率不支持主胜 = 诱盘（看好客队/平局）
- 澳门和局 + 低平赔 = 真实分散（防平）
- 澳门和局 + 高平赔 = 诱导和局（不防）
"""

import pandas as pd
import os

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

# 威廉+立博即时赔率
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


def analyze_macao_vs_odds(macao_tip, home, draw, away, wl):
    """
    澳门心水 vs 庄家赔率
    庄家是跟随玩家还是反着来？
    """
    if not wl:
        return None, "无威廉立博数据"
    
    w_home, w_draw, w_away = wl[0], wl[1], wl[2]
    l_home, l_draw, l_away = wl[3], wl[4], wl[5]
    
    # 平均赔率
    avg_home = (w_home + l_home) / 2
    avg_draw = (w_draw + l_draw) / 2
    avg_away = (w_away + l_away) / 2
    
    result = {}
    
    if macao_tip == "主胜":
        # 玩家看好主胜
        # 庄家是否支持？
        if avg_home < avg_away:
            # 赔率也支持主胜 → 实盘
            result = {"预测": "主胜", "信心": "A级", "逻辑": "实盘-玩家与庄家一致"}
        else:
            # 赔率不支持主胜 → 诱盘
            # 诱去主胜，真实看客胜或平
            if avg_away < 2.5:
                result = {"预测": "客胜", "信心": "B级", "逻辑": "诱盘-庄家真实看客"}
            else:
                result = {"预测": "防平", "信心": "B级", "逻辑": "诱盘-庄家真实看平"}
    
    elif macao_tip == "客胜":
        # 玩家看好客胜
        if avg_away < avg_home:
            result = {"预测": "客胜", "信心": "A级", "逻辑": "实盘-玩家与庄家一致"}
        else:
            if avg_home < 2.5:
                result = {"预测": "主胜", "信心": "B级", "逻辑": "诱盘-庄家真实看主"}
            else:
                result = {"预测": "防平", "信心": "B级", "逻辑": "诱盘-庄家真实看平"}
    
    elif macao_tip == "和局":
        # 玩家看好和局
        if avg_draw < 3.3:
            # 低平赔 → 真实分散，防平
            result = {"预测": "防平", "信心": "A级", "逻辑": "实盘-低平赔真实分散"}
        else:
            # 高平赔 → 诱导和局，不防
            result = {"预测": "主胜" if avg_home < avg_away else "客胜", "信心": "B级", "逻辑": "诱盘-高平赔诱导和局"}
    
    return result


def v6_predict(row, wl_data, macao_data):
    """V6预测"""
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
    wl = wl_data.get(code)
    
    # 分布
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
    
    # 1. 澳门心水 vs 赔率（最高优先级）
    if macao_tip and wl:
        macao_result = analyze_macao_vs_odds(macao_tip, home, draw, away, wl)
        if macao_result:
            return macao_result["预测"], macao_result["信心"], f"{distribution}+{macao_result['逻辑']}"
    
    # 2. A级：极低赔 + 状态差距大
    if home < 1.6 and state_diff > 20:
        return "主胜", "A级", "极低赔+状态差距大"
    if away < 1.6 and state_diff < -20:
        return "客胜", "A级", "极低赔+状态差距大"
    
    # 3. 顺分布 + 档位差距大
    if distribution == "顺分布" and state_diff > 15:
        return "主胜", "A级", f"{distribution}+状态差"
    
    # 4. 中庸分布 + 低平赔 = 防平
    if distribution == "中庸分布" and draw < 3.2 and abs(state_diff) < 20:
        return "防平", "B级", f"{distribution}+低平"
    
    # 5. 缓冲分布
    if distribution == "缓冲分布":
        if state_diff > 25:
            return "主胜", "B级", distribution
        elif state_diff < -25:
            return "客胜", "B级", distribution
        else:
            if draw < 3.3:
                return "防平", "C级", distribution
    
    # 6. 低平赔 + 状态接近 = 防平
    if draw < 2.9 and abs(state_diff) < 15:
        return "防平", "B级", "低平赔"
    
    # 7. 状态差距大
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
print("=" * 85)
print("V6优化版 - 澳门心水判断实盘/诱盘 - 3.13")
print("=" * 85)

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
    pred, conf, reason = v6_predict(row, WILLIAM_LADBROKES, MACAO_TIP)
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

print("=" * 85)
print(f"准确率: {correct}/{total} = {correct/total*100:.1f}%")
print("=" * 85)
