"""
V3优化版 v2 - 测试3.14和3.15
"""

import pandas as pd

# 威廉立博数据 - 3.14
WILLIAM_LADBROKES_314 = {
    '周六001': '2.30|3.20|2.80|2.35|3.20|2.80',  # 仁川联 vs 浦项制铁
    '周六002': '1.95|3.30|3.50|1.95|3.30|3.50',  # 悉尼FC vs 麦克阿瑟
    '周六003': '2.10|3.30|3.10|2.10|3.30|3.10',  # 横滨水手 vs 川崎前锋
    '周六004': '1.95|3.40|3.30|1.95|3.40|3.30',  # 神户胜利 vs 名古屋鲸
    '周六005': '2.50|3.00|2.75|2.50|3.00|2.75',  # 鸟栖沙岩 vs 鹿岛鹿角
    '周六006': '1.55|3.80|5.00|1.55|3.80|5.00',  # 广岛三箭 vs 东京FC
    '周六007': '2.05|3.25|3.25|2.05|3.25|3.25',  # 京都清水
    '周六008': '2.15|3.20|3.10|2.15|3.20|3.10',  # 东京绿茵 vs 大分三神
    '周六009': '2.30|3.15|2.90|2.30|3.15|2.90',  # 甲府风林 vs 山形山神
    '周六010': '2.20|3.20|3.00|2.20|3.20|3.00',  # 长崎航海 vs 藤枝
    '周六011': '2.40|3.10|2.80|2.40|3.10|2.80',  # 冈山绿雉 vs 清水鼓动
    '周六012': '1.75|3.40|4.00|1.75|3.40|4.00',  # 町田泽维亚 vs 磐田喜悦
    '周六013': '2.75|3.00|2.40|2.75|3.00|2.40',  # 德岛漩涡 vs 仙台七夕
    '周六014': '2.20|3.20|3.00|2.20|3.20|3.00',  # 柏太阳神 vs 大宫松鼠
    '周六015': '2.90|3.10|2.30|2.90|3.10|2.30',  # 千叶市原 vs 班尼菲奥
    '周六016': '1.85|3.30|3.80|1.85|3.30|3.80',  # 群马温泉 vs 琉球
    '周六017': '2.10|3.25|3.10|2.10|3.25|3.10',  # 金泽塞维 vs 松本山雅
    '周六018': '2.50|2.90|2.75|2.50|2.90|2.75',  # 磐城FC vs 山口雷诺
    '周六019': '1.75|3.40|4.20|1.75|3.40|4.20',  # 仙台七夕 vs 枥木SC
    '周六020': '1.55|3.60|5.50|1.55|3.60|5.50',  # 町田泽维亚 vs 磐田喜悦
    '周六021': '3.20|3.10|2.10|3.20|3.10|2.10',  # 冈山绿雉 vs 清水鼓动
    '周六022': '2.30|3.10|2.90|2.30|3.10|2.90',  # 甲府风林 vs 山形山神
    '周六023': '1.90|3.30|3.60|1.90|3.30|3.60',  # 柏太阳神 vs 大宫松鼠
    '周六024': '2.40|3.00|2.80|2.40|3.00|2.80',  # 东京绿茵 vs 大分三神
    '周六025': '1.80|3.30|4.00|1.80|3.30|4.00',  # 名古屋鲸 vs 神户胜利
}

# 威廉立博数据 - 3.15
WILLIAM_LADBROKES_315 = {
    '周日001': '2.10|3.20|3.20|2.10|3.20|3.20',  # 仁川联 vs 水原三星
    '周日002': '1.55|3.60|5.50|1.55|3.60|5.50',  # 广岛三箭 vs 东京FC
    '周日003': '1.75|3.40|4.20|1.75|3.40|4.20',  # 鹿岛鹿角 vs 川崎前锋
    '周日004': '2.30|3.10|2.90|2.30|3.10|2.90',  # 名古屋鲸 vs 磐田喜悦
    '周日005': '2.60|3.00|2.60|2.60|3.00|2.60',  # 鸟栖沙岩 vs 横滨水手
    '周日006': '1.85|3.30|3.80|1.85|3.30|3.80',  # 町田泽维亚 vs 京都清水
    '周日007': '2.20|3.20|2.90|2.20|3.20|2.90',  # 东京绿茵 vs 大分三神
    '周日008': '2.40|3.10|2.80|2.40|3.10|2.80',  # 甲府风林 vs 山形山神
    '周日009': '1.70|3.40|4.50|1.70|3.40|4.50',  # 柏太阳神 vs 磐田喜悦
    '周日010': '2.10|3.20|3.20|2.10|3.20|3.20',  # 德岛漩涡 vs 仙台七夕
    '周日011': '2.50|2.90|2.75|2.50|2.90|2.75',  # 千叶市原 vs 班尼菲奥
    '周日012': '1.80|3.30|4.00|1.80|3.30|4.00',  # 群马温泉 vs 琉球
    '周日013': '1.40|4.00|6.50|1.40|4.00|6.50',  # 拜仁 vs 法兰克福
    '周日014': '2.10|3.30|3.20|2.10|3.30|3.20',  # 波鸿 vs 霍芬海姆
    '周日015': '1.60|3.60|5.00|1.60|3.60|5.00',  # 勒沃库森 vs 云达不莱梅
    '周日016': '1.95|3.30|3.50|1.95|3.30|3.50',  # 门兴 vs 圣保利
    '周日017': '1.80|3.40|4.20|1.80|3.40|4.20',  # 狼堡 vs 弗赖堡
    '周日018': '2.40|3.20|2.70|2.40|3.20|2.70',  # 荷尔斯泰因 vs 纽伦堡
    '周日019': '2.20|3.20|3.00|2.20|3.20|3.00',  # 凯泽 vs 杜塞尔多夫
    '周日020': '2.00|3.30|3.40|2.00|3.30|3.40',  # 埃弗斯堡 vs 卡尔斯鲁厄
    '周日021': '1.85|3.30|3.80|1.85|3.30|3.80',  # 纽伦堡 vs 沙尔克
    '周日022': '2.10|3.25|3.10|2.10|3.25|3.10',  # 帕德博恩 vs 菲尔特
    '周日023': '2.30|3.10|2.90|2.30|3.10|2.90',  # 威廉二世上轮
    '周日024': '2.50|3.00|2.70|2.50|3.00|2.70',  # 布雷达 vs 格拉夫
    '周日025': '2.20|3.20|2.90|2.20|3.20|2.90',  # 阿尔梅勒 vs 埃门
    '周日026': '1.75|3.40|4.00|1.75|3.40|4.00',  # 兹沃勒 vs 格罗宁根
    '周日027': '1.55|3.60|5.50|1.55|3.60|5.50',  # 坎布尔 vs 罗达JC
    '周日028': '1.70|3.40|4.50|1.70|3.40|4.50',  # 海牙 vs 前进之鹰
    '周日029': '2.30|3.10|2.90|2.30|3.10|2.90',  # 奥斯 vs 芬洛
}


def analyze_william_ladbrokes(w_home, w_draw, w_away, l_home, l_draw, l_away):
    result = {"signal": None, "confidence": "D级", "reason": ""}
    home_diff = w_home - l_home
    away_diff = w_away - l_away
    
    if home_diff < -0.10:
        result["signal"] = "低开主胜(诱盘)"
        result["confidence"] = "B级"
        result["reason"] = f"威廉低开主胜{abs(home_diff):.2f}"
    elif home_diff > 0.10:
        result["signal"] = "主队占优"
        result["confidence"] = "B级"
        result["reason"] = f"威廉高开主胜{home_diff:.2f}"
    if away_diff < -0.10:
        result["signal"] = "客队占优"
        result["confidence"] = "B级"
        result["reason"] = f"威廉低开客胜{abs(away_diff):.2f}"
    elif away_diff > 0.10:
        result["signal"] = "低开客胜(诱盘)"
        result["confidence"] = "B级"
        result["reason"] = f"威廉高开客胜{away_diff:.2f}"
    if result["signal"] is None:
        result["reason"] = "威廉立博一致"
    return result


def get_distribution(w_home, w_draw, w_away, l_home, l_draw, l_away):
    avg_home = (w_home + l_home) / 2
    avg_draw = (w_draw + l_draw) / 2
    ratio = avg_home / avg_draw
    if ratio < 0.65:
        return "顺分布"
    elif ratio > 0.85:
        return "逆分布"
    elif abs(avg_home - ((w_away+l_away)/2)) < 0.3:
        return "缓冲分布"
    else:
        return "中庸分布"


def parse_state(state_str):
    try:
        return float(str(state_str).replace('%', ''))
    except:
        return 50.0


def v3_predict_v2(row, wl_data):
    code = row['编号']
    wl_str = wl_data.get(code, '')
    has_wl = bool(wl_str)
    
    if has_wl:
        try:
            parts = wl_str.split('|')
            w_home, w_draw, w_away = float(parts[0]), float(parts[1]), float(parts[2])
            l_home, l_draw, l_away = float(parts[3]), float(parts[4]), float(parts[5])
        except:
            has_wl = False
    
    home = row['主胜']
    draw = row['平局']
    away = row['客胜']
    home_state = parse_state(row.get('主队状态', '50%'))
    away_state = parse_state(row.get('客队状态', '50%'))
    state_diff = home_state - away_state
    
    prediction, confidence, reason = "", "D级", ""
    
    if home < 1.6 and state_diff > 20:
        prediction, confidence, reason = "主胜", "A级", "极低赔+状态差距大"
    elif away < 1.6 and state_diff < -20:
        prediction, confidence, reason = "客胜", "A级", "极低赔+状态差距大"
    elif has_wl:
        wl = analyze_william_ladbrokes(w_home, w_draw, w_away, l_home, l_draw, l_away)
        dist = get_distribution(w_home, w_draw, w_away, l_home, l_draw, l_away)
        if wl["signal"] == "低开主胜(诱盘)":
            prediction = "客胜" if away < 2.5 else "防平"
            confidence = "B级"
            reason = f"{dist}，{wl['reason']}"
        elif wl["signal"] == "低开客胜(诱盘)":
            prediction, confidence, reason = "主胜", "B级", f"{dist}，{wl['reason']}"
        elif wl["signal"] == "主队占优":
            prediction, confidence, reason = "主胜", wl["confidence"], f"{dist}，{wl['reason']}"
        elif wl["signal"] == "客队占优":
            prediction, confidence, reason = "客胜", wl["confidence"], f"{dist}，{wl['reason']}"
    
    if not prediction:
        if draw < 2.9 and abs(state_diff) < 15:
            prediction, confidence, reason = "防平", "B级", "低平赔+状态接近"
        elif state_diff > 30:
            prediction, confidence, reason = "主胜", "B级", "状态差距大"
        elif state_diff < -30:
            prediction, confidence, reason = "客胜", "B级", "状态差距大"
        else:
            if home < away:
                prediction, confidence, reason = "主胜", "C级", "概率最高"
            else:
                prediction, confidence, reason = "客胜", "C级", "概率最高"
    
    return {"预测": prediction, "信心度": confidence, "理由": reason}


def test_day(date_str, wl_data, actual_results):
    if '3.14' in date_str:
        df = pd.read_excel('3.14_比赛预测汇总.xlsx')
    else:
        df = pd.read_excel('3.15_V3预测.xlsx')
    print(f"\n{'='*75}")
    print(f"V3优化版 v2 - {date_str}")
    print(f"{'='*75}")
    
    correct, total = 0, 0
    for _, row in df.iterrows():
        code = row['编号']
        result = v3_predict_v2(row, wl_data)
        actual = actual_results.get(code, '')
        is_correct = result['预测'] == actual or ('防平' in result['预测'] and actual == '平')
        mark = "OK" if is_correct else "X"
        if is_correct:
            correct += 1
        total += 1
        wl_mark = "*" if code in wl_data else " "
        print(f"{wl_mark}{code}: {result['预测']:4s} {result['信心度']} {actual:4s} {mark}")
    
    print(f"{'='*75}")
    print(f"准确率: {correct}/{total} = {correct/total*100:.1f}%")
    print(f"{'='*75}")


# 实际结果
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
    '周日021': '平', '周日022': '平', '周日023': '客胜', '周日024': '客胜',
    '周日025': '平', '周日026': '平', '周日027': '主胜', '周日028': '主胜',
    '周日029': '主胜',
}


if __name__ == "__main__":
    # 3.14
    test_day("3.14", WILLIAM_LADBROKES_314, actual_314)
    # 3.15
    test_day("3.15", WILLIAM_LADBROKES_315, actual_315)
