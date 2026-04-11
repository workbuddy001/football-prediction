"""
V3优化版 v2 - 完整版威廉立博对比
增加更多比赛的威廉立博数据
"""

import pandas as pd

# 威廉立博数据（从源数据提取）
WILLIAM_LADBROKES = {
    # 格式: 威廉主胜|威廉平局|威廉客胜|立博主胜|立博平局|立博客胜
    '周五001': '2.50|2.90|2.50|2.60|3.50|2.50',  # 布里斯班 vs 西悉尼
    '周五002': '1.75|3.45|4.00|1.73|3.45|4.00',  # 澳大利亚女 vs 朝鲜女
    '周五003': '2.35|3.25|2.85|2.30|3.25|2.90',  # 马格德堡 vs 达姆施塔
    '周五004': '2.20|3.10|2.80|2.37|3.40|2.80',  # 胡巴尔 vs 吉达国民
    '周五005': '2.10|2.95|3.40|2.10|3.00|3.40',  # 克莱蒙 vs 波城FC
    '周五006': '2.50|3.30|2.50|2.50|3.30|2.55',  # 兹沃勒 vs 格罗宁根
    '周五007': '1.85|3.60|3.65|1.85|3.60|3.65',  # 坎布尔 vs 罗达JC
    '周五008': '1.75|3.55|4.20|1.75|3.55|4.20',  # 门兴 vs 圣保利
    '周五009': '1.80|3.40|4.30|1.80|3.40|4.30',  # 都灵 vs 帕尔马
    '周五010': '1.55|3.80|5.50|1.53|3.80|5.50',  # 马赛 vs 欧塞尔
    '周五011': '2.25|3.20|3.00|2.25|3.20|3.00',  # 雷克斯 vs 斯旺西
    '周五012': '3.20|3.15|2.15|3.20|3.15|2.15',  # 阿拉维斯 vs 比利亚雷
}


def analyze_william_ladbrokes(w_home, w_draw, w_away, l_home, l_draw, l_away):
    """威廉希尔 vs 立博 赔率对比分析"""
    result = {"signal": None, "confidence": "D级", "reason": ""}
    
    home_diff = w_home - l_home
    away_diff = w_away - l_away
    draw_diff = w_draw - l_draw
    
    # 威廉主胜明显低于立博 → 低开主胜（诱盘）
    if home_diff < -0.10:
        result["signal"] = "低开主胜(诱盘)"
        result["confidence"] = "B级"
        result["reason"] = f"威廉低开主胜{abs(home_diff):.2f}"
    # 威廉主胜高于立博 → 真实看好主队
    elif home_diff > 0.10:
        result["signal"] = "主队占优"
        result["confidence"] = "B级"
        result["reason"] = f"威廉高开主胜{home_diff:.2f}"
    
    # 威廉客胜明显低于立博 → 真实看好客队
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
    """判断分布类型"""
    avg_home = (w_home + l_home) / 2
    avg_draw = (w_draw + l_draw) / 2
    avg_away = (w_away + l_away) / 2
    ratio = avg_home / avg_draw
    
    if ratio < 0.65:
        return "顺分布"
    elif ratio > 0.85:
        return "逆分布"
    elif abs(avg_home - avg_away) < 0.3:
        return "缓冲分布"
    else:
        return "中庸分布"


def parse_state(state_str):
    """解析状态值"""
    try:
        return float(str(state_str).replace('%', ''))
    except:
        return 50.0


def v3_predict_v2(row):
    """V3优化版 v2 预测"""
    code = row['编号']
    
    # 威廉立博数据
    wl_str = WILLIAM_LADBROKES.get(code, '')
    has_wl = bool(wl_str)
    
    if has_wl:
        try:
            parts = wl_str.split('|')
            w_home, w_draw, w_away = float(parts[0]), float(parts[1]), float(parts[2])
            l_home, l_draw, l_away = float(parts[3]), float(parts[4]), float(parts[5])
        except:
            has_wl = False
    
    # 普通赔率
    home = row['主胜']
    draw = row['平局']
    away = row['客胜']
    
    # 状态
    home_state = parse_state(row.get('主队状态', '50%'))
    away_state = parse_state(row.get('客队状态', '50%'))
    state_diff = home_state - away_state
    
    # ===== 预测逻辑 =====
    prediction = ""
    confidence = "D级"
    reason = ""
    
    # 1. A级：极低赔 + 状态差距大
    if home < 1.6 and state_diff > 20:
        prediction = "主胜"
        confidence = "A级"
        reason = "极低赔+状态差距大"
    elif away < 1.6 and state_diff < -20:
        prediction = "客胜"
        confidence = "A级"
        reason = "极低赔+状态差距大"
    
    # 2. 威廉立博对比
    elif has_wl:
        wl = analyze_william_ladbrokes(w_home, w_draw, w_away, l_home, l_draw, l_away)
        dist = get_distribution(w_home, w_draw, w_away, l_home, l_draw, l_away)
        
        # 诱盘判断
        if wl["signal"] == "低开主胜(诱盘)":
            # 客队强于主队，但赔率显示主队有机会
            if away < 2.5:
                prediction = "客胜"
            else:
                prediction = "防平"
            confidence = "B级"
            reason = f"{dist}，{wl['reason']}"
        elif wl["signal"] == "低开客胜(诱盘)":
            prediction = "主胜"
            confidence = "B级"
            reason = f"{dist}，{wl['reason']}"
        elif wl["signal"] == "主队占优":
            prediction = "主胜"
            confidence = wl["confidence"]
            reason = f"{dist}，{wl['reason']}"
        elif wl["signal"] == "客队占优":
            prediction = "客胜"
            confidence = wl["confidence"]
            reason = f"{dist}，{wl['reason']}"
        else:
            # 威廉立博一致，无明显信号
            pass
    
    # 3. 原有逻辑
    if not prediction:
        if draw < 2.9 and abs(state_diff) < 15:
            prediction = "防平"
            confidence = "B级"
            reason = "低平赔+状态接近"
        elif state_diff > 30:
            prediction = "主胜"
            confidence = "B级"
            reason = "状态差距大"
        elif state_diff < -30:
            prediction = "客胜"
            confidence = "B级"
            reason = "状态差距大"
        else:
            if home < away:
                prediction = "主胜"
                confidence = "C级"
                reason = "概率最高"
            else:
                prediction = "客胜"
                confidence = "C级"
                reason = "概率最高"
    
    return {"预测": prediction, "信心度": confidence, "理由": reason}


# ===== 测试 =====
def test():
    df = pd.read_excel('3.13_V3预测.xlsx')
    
    print("=" * 75)
    print("V3优化版 v2 - 威廉立博对比 (3.13)")
    print("=" * 75)
    
    # 实际结果
    actual_results = {
        '周五001': '平', '周五002': '主胜', '周五003': '平', '周五004': '主胜',
        '周五005': '客胜', '周五006': '平', '周五007': '平', '周五008': '主胜',
        '周五009': '主胜', '周五010': '主胜', '周五011': '主胜', '周五012': '平'
    }
    
    results = []
    correct = 0
    total = 0
    
    for _, row in df.iterrows():
        code = row['编号']
        result = v3_predict_v2(row)
        actual = actual_results.get(code, '')
        
        is_correct = result['预测'] == actual or ('防平' in result['预测'] and actual == '平')
        
        if is_correct:
            correct += 1
            mark = "OK"
        else:
            mark = "X"
        total += 1
        
        wl_mark = "*" if code in WILLIAM_LADBROKES else " "
        print(f"{wl_mark}{code}: 预测={result['预测']:4s} {result['信心度']} 实际={actual:4s} {mark} | {result['理由']}")
        
        results.append({'编号': code, '预测': result['预测'], '实际': actual, '结果': mark})
    
    print("=" * 75)
    print(f"准确率: {correct}/{total} = {correct/total*100:.1f}%")
    print("=" * 75)
    
    return results


if __name__ == "__main__":
    test()
