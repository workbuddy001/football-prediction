"""
V6优化版测试3.14
"""

import pandas as pd

# 澳门心水 3.14
MACAO_TIP_314 = {
    '周六001': '和局',  # 仁川联 vs 浦项制铁
    '周六002': '客胜',  # 悉尼FC vs 麦克阿瑟
    '周六003': '客胜',  # 横滨水手 vs 川崎前锋
    '周六004': '客胜',  # 神户胜利 vs 名古屋鲸
    '周六005': '和局',  # 鸟栖沙岩 vs 鹿岛鹿角
    '周六006': '和局',  # 广岛三箭 vs 东京FC
    '周六007': '客胜',  # 京都清水
    '周六008': '主胜',  # 东京绿茵 vs 大分三神
    '周六009': '和局',  # 甲府风林 vs 山形山神
    '周六010': '客胜',  # 长崎航海 vs 藤枝
    '周六011': '主胜',  # 冈山绿雉 vs 清水鼓动
    '周六012': '主胜',  # 町田泽维亚 vs 磐田喜悦
    '周六013': '客胜',  # 德岛漩涡 vs 仙台七夕
    '周六014': '主胜',  # 柏太阳神 vs 大宫松鼠
    '周六015': '客胜',  # 千叶市原 vs 班尼菲奥
    '周六016': '主胜',  # 群马温泉 vs 琉球
    '周六017': '和局',  # 金泽塞维 vs 松本山雅
    '周六018': '主胜',  # 磐城FC vs 山口雷诺
    '周六019': '和局',  # 仙台七夕 vs 枥木SC
    '周六020': '和局',  # 町田泽维亚 vs 磐田喜悦
}

# 威廉立博 3.14
WILLIAM_LADBROKES_314 = {
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
print("V6优化版 - 3.14")
print("=" * 85)

df = pd.read_excel('3.14_比赛预测汇总.xlsx')

actual = {
    '周六001': '平', '周六002': '客胜', '周六003': '客胜', '周六004': '客胜',
    '周六005': '平', '周六006': '平', '周六007': '客胜', '周六008': '主胜',
    '周六009': '平', '周六010': '客胜', '周六011': '主胜', '周六012': '主胜',
    '周六013': '客胜', '周六014': '主胜', '周六015': '客胜', '周六016': '主胜',
    '周六017': '平', '周六018': '主胜', '周六019': '平', '周六020': '平',
}

correct = 0
total = 0

for _, row in df.iterrows():
    code = row['编号']
    if code not in actual:
        continue
    pred, conf, reason = v6_predict(row, WILLIAM_LADBROKES_314, MACAO_TIP_314)
    actual_result = actual.get(code, '')
    
    is_correct = pred == actual_result or ('防平' in pred and actual_result == '平')
    if is_correct:
        correct += 1
        mark = "OK"
    else:
        mark = "X"
    total += 1
    
    macao = MACAO_TIP_314.get(code, '')
    print(f"{code}: 澳门={macao:4s} 预测={pred:4s} 实际={actual_result:4s} {mark} | {reason}")

print("=" * 85)
print(f"准确率: {correct}/{total} = {correct/total*100:.1f}%")
print("=" * 85)
