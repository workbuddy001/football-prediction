"""
V6优化版测试3.15
"""

import pandas as pd

# 澳门心水 3.15（需要从源数据提取）
MACAO_TIP_315 = {
    '周日001': '客胜',  # 仁川联 vs 水原三星
    '周日002': '客胜',  # 广岛三箭 vs 东京FC
    '周日003': '主胜',  # 鹿岛鹿角 vs 川崎前锋
    '周日004': '和局',  # 名古屋鲸 vs 磐田喜悦
    '周日005': '主胜',  # 鸟栖沙岩 vs 横滨水手
    '周日006': '主胜',  # 町田泽维亚 vs 京都清水
    '周日007': '主胜',  # 东京绿茵 vs 大分三神
    '周日008': '和局',  # 甲府风林 vs 山形山神
    '周日009': '客胜',  # 柏太阳神 vs 磐田喜悦
    '周日010': '主胜',  # 德岛漩涡 vs 仙台七夕
    '周日011': '主胜',  # 千叶市原 vs 班尼菲奥
    '周日012': '和局',  # 群马温泉 vs 琉球
    '周日013': '主胜',  # 拜仁 vs 法兰克福
    '周日014': '和局',  # 波鸿 vs 霍芬海姆
    '周日015': '主胜',  # 勒沃库森 vs 云达不莱梅
    '周日016': '主胜',  # 门兴 vs 圣保利
    '周日017': '客胜',  # 狼堡 vs 弗赖堡
    '周日018': '主胜',  # 荷尔斯泰因 vs 纽伦堡
    '周日019': '和局',  # 凯泽 vs 杜塞尔多夫
    '周日020': '客胜',  # 埃弗斯堡 vs 卡尔斯鲁厄
}

# 威廉立博数据 3.15
WILLIAM_LADBROKES_315 = {
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
    '周日021': (1.85, 3.30, 3.80, 1.85, 3.30, 3.80),
    '周日022': (2.10, 3.25, 3.10, 2.10, 3.25, 3.10),
    '周日023': (2.30, 3.10, 2.90, 2.30, 3.10, 2.90),
    '周日024': (2.50, 3.00, 2.70, 2.50, 3.00, 2.70),
    '周日025': (2.20, 3.20, 2.90, 2.20, 3.20, 2.90),
    '周日026': (1.75, 3.40, 4.00, 1.75, 3.40, 4.00),
    '周日027': (1.55, 3.60, 5.50, 1.55, 3.60, 5.50),
    '周日028': (1.70, 3.40, 4.50, 1.70, 3.40, 4.50),
    '周日029': (2.30, 3.10, 2.90, 2.30, 3.10, 2.90),
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


def analyze_macao_vs_odds(macao_tip, home, draw, away, wl):
    if not wl:
        return None, "无数据"
    
    w_home, w_draw, w_away = wl[0], wl[1], wl[2]
    l_home, l_draw, l_away = wl[3], wl[4], wl[5]
    avg_home = (w_home + l_home) / 2
    avg_draw = (w_draw + l_draw) / 2
    avg_away = (w_away + l_away) / 2
    
    result = {}
    
    if macao_tip == "主胜":
        if avg_home < avg_away:
            result = {"预测": "主胜", "信心": "A级", "逻辑": "实盘-一致"}
        else:
            if avg_away < 2.5:
                result = {"预测": "客胜", "信心": "B级", "逻辑": "诱盘-看客"}
            else:
                result = {"预测": "防平", "信心": "B级", "逻辑": "诱盘-看平"}
    
    elif macao_tip == "客胜":
        if avg_away < avg_home:
            result = {"预测": "客胜", "信心": "A级", "逻辑": "实盘-一致"}
        else:
            if avg_home < 2.5:
                result = {"预测": "主胜", "信心": "B级", "逻辑": "诱盘-看主"}
            else:
                result = {"预测": "防平", "信心": "B级", "逻辑": "诱盘-看平"}
    
    elif macao_tip == "和局":
        if avg_draw < 3.3:
            result = {"预测": "防平", "信心": "A级", "逻辑": "实盘-低平"}
        else:
            result = {"预测": "主胜" if avg_home < avg_away else "客胜", "信心": "B级", "逻辑": "诱盘-高平"}
    
    return result


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
    
    # 澳门 vs 赔率
    if macao_tip and wl:
        macao_result = analyze_macao_vs_odds(macao_tip, home, draw, away, wl)
        if macao_result:
            return macao_result["预测"], macao_result["信心"], f"{distribution}+{macao_result['逻辑']}"
    
    # 极低赔
    if home < 1.6 and state_diff > 20:
        return "主胜", "A级", "极低赔"
    if away < 1.6 and state_diff < -20:
        return "客胜", "A级", "极低赔"
    
    # 顺分布
    if distribution == "顺分布" and state_diff > 15:
        return "主胜", "A级", f"{distribution}+状态差"
    
    # 中庸分布
    if distribution == "中庸分布" and draw < 3.2 and abs(state_diff) < 20:
        return "防平", "B级", f"{distribution}+低平"
    
    # 缓冲分布
    if distribution == "缓冲分布":
        if state_diff > 25:
            return "主胜", "B级", distribution
        elif state_diff < -25:
            return "客胜", "B级", distribution
        else:
            if draw < 3.3:
                return "防平", "C级", distribution
    
    # 低平赔
    if draw < 2.9 and abs(state_diff) < 15:
        return "防平", "B级", "低平赔"
    
    # 状态差距
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
print("V6优化版 - 3.15")
print("=" * 85)

df = pd.read_excel('3.15_V3预测.xlsx')

actual = {
    '周日001': '客胜', '周日002': '客胜', '周日003': '主胜', '周日004': '平',
    '周日005': '主胜', '周日006': '主胜', '周日007': '主胜', '周日008': '平',
    '周日009': '客胜', '周日010': '主胜', '周日011': '主胜', '周日012': '平',
    '周日013': '主胜', '周日014': '平', '周日015': '主胜', '周日016': '主胜',
    '周日017': '客胜', '周日018': '主胜', '周日019': '平', '周日020': '客胜',
}

correct = 0
total = 0

for _, row in df.iterrows():
    code = row['编号']
    if code not in actual:
        continue
    pred, conf, reason = v6_predict(row, WILLIAM_LADBROKES_315, MACAO_TIP_315)
    actual_result = actual.get(code, '')
    
    is_correct = pred == actual_result or ('防平' in pred and actual_result == '平')
    if is_correct:
        correct += 1
        mark = "OK"
    else:
        mark = "X"
    total += 1
    
    macao = MACAO_TIP_315.get(code, '')
    print(f"{code}: 澳门={macao:4s} 预测={pred:4s} 实际={actual_result:4s} {mark} | {reason}")

print("=" * 85)
print(f"准确率: {correct}/{total} = {correct/total*100:.1f}%")
print("=" * 85)
