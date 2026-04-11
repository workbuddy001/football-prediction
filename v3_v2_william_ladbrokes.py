"""
V3优化版 v2 - 增加威廉立博对比判断
基于欧赔核心思维，增加关键公司赔率对比
"""

import pandas as pd
import json

# ===== 威廉立博对比判断核心函数 =====
def analyze_william_ladbrokes(w_home, w_draw, w_away, l_home, l_draw, l_away):
    """
    威廉希尔 vs 立博 赔率对比分析
    返回: (判断结果, 信心度, 理由)
    """
    result = {
        "signal": None,  # 主队占优/客队占优/诱盘/无明显信号
        "confidence": "D级",
        "reason": ""
    }
    
    # 计算差异
    home_diff = w_home - l_home  # 威廉-立博
    away_diff = w_away - l_away
    draw_diff = w_draw - l_draw
    
    # 主胜差异分析
    if home_diff < -0.10:
        # 威廉主胜明显低于立博 → 低开主胜（诱盘）
        result["signal"] = "低开主胜(诱盘)"
        result["confidence"] = "B级"
        result["reason"] = f"威廉主胜{w_home}低于立博{l_home}，差{abs(home_diff):.2f}，典型低开诱盘"
    elif home_diff > 0.10:
        # 威廉主胜高于立博 → 真实看好主队
        result["signal"] = "主队占优"
        result["confidence"] = "B级"
        result["reason"] = f"威廉主胜{w_home}高于立博{l_home}，差{home_diff:.2f}，真实看好主队"
    
    # 客胜差异分析
    if away_diff < -0.10:
        result["signal"] = "客队占优"
        result["confidence"] = "B级"
        result["reason"] = f"威廉客胜{w_away}低于立博{l_away}，差{abs(away_diff):.2f}，真实看好客队"
    elif away_diff > 0.10:
        result["signal"] = "低开客胜(诱盘)"
        result["confidence"] = "B级"
        result["reason"] = f"威廉客胜{w_away}高于立博{l_away}，差{away_diff:.2f}，低开客胜诱盘"
    
    # 平局差异
    if abs(draw_diff) < 0.05:
        result["reason"] += "，平赔一致无分散"
    
    # 无明显信号
    if result["signal"] is None:
        result["reason"] = "威廉立博赔率接近，无明显信号"
    
    return result


def get_distribution_type(w_home, w_draw, w_away, l_home, l_draw, l_away):
    """
    判断分布类型（威廉+立博平均）
    """
    avg_home = (w_home + l_home) / 2
    avg_draw = (w_draw + l_draw) / 2
    avg_away = (w_away + l_away) / 2
    
    # 胜/平比率
    ratio = avg_home / avg_draw
    
    # 判断分布
    if ratio < 0.65:
        return "顺分布"  # 主胜信心强
    elif ratio > 0.85:
        return "逆分布"  # 主胜信心弱
    else:
        # 中庸/缓冲分布
        if abs(avg_home - avg_away) < 0.3:
            return "缓冲分布"
        else:
            return "中庸分布"


def v3_predict_v2(row):
    """
    V3优化版 v2 预测
    增加了威廉-立博对比
    """
    # 提取赔率（如果有威廉立博数据）
    # 格式: 威廉主胜|威廉平局|威廉客胜|立博主胜|立博平局|立博客胜
    odds_parts = str(row.get('威廉立博', '')).split('|')
    
    has_wl = len(odds_parts) >= 6
    
    if has_wl:
        try:
            w_home = float(odds_parts[0])
            w_draw = float(odds_parts[1])
            w_away = float(odds_parts[2])
            l_home = float(odds_parts[3])
            l_draw = float(odds_parts[4])
            l_away = float(odds_parts[5])
        except:
            has_wl = False
    
    # 普通赔率
    home = row['主胜']
    draw = row['平局']
    away = row['客胜']
    
    # 状态
    try:
        home_state = float(str(row.get('主队状态', '50%')).replace('%', ''))
        away_state = float(str(row.get('客队状态', '50%')).replace('%', ''))
    except:
        home_state = 50
        away_state = 50
    state_diff = home_state - away_state
    
    # 预测
    prediction = ""
    confidence = "D级"
    reason = ""
    
    # ===== 核心判断逻辑 =====
    
    # 1. A级信号：极低赔 + 状态差距大
    if home < 1.6 and state_diff > 20:
        prediction = "主胜"
        confidence = "A级"
        reason = "极低赔+状态差距大，实盘"
    elif away < 1.6 and state_diff < -20:
        prediction = "客胜"
        confidence = "A级"
        reason = "极低赔+状态差距大，实盘"
    
    # 2. 威廉立博对比判断
    elif has_wl:
        wl_result = analyze_william_ladbrokes(w_home, w_draw, w_away, l_home, l_draw, l_away)
        distribution = get_distribution_type(w_home, w_draw, w_away, l_home, l_draw, l_away)
        
        reason = f"分布:{distribution}，{wl_result['reason']}"
        
        # 根据威廉立博信号判断
        if wl_result["signal"] in ["低开主胜(诱盘)", "低开客胜(诱盘)"]:
            # 诱盘：反向选择
            if wl_result["signal"] == "低开主胜(诱盘)":
                prediction = "客胜" if away < 3.0 else "防平"
            else:
                prediction = "主胜"
            confidence = "B级"
        elif wl_result["signal"] == "主队占优":
            prediction = "主胜"
            confidence = wl_result["confidence"]
        elif wl_result["signal"] == "客队占优":
            prediction = "客胜"
            confidence = wl_result["confidence"]
        else:
            # 无明显信号，用原有逻辑
            pass
    
    # 3. 原有V3逻辑
    if not prediction:
        # 平赔分析
        if draw < 2.9 and abs(state_diff) < 15:
            # 低平赔 + 状态接近 = 防平
            if home < away:
                prediction = "防平"
                confidence = "B级"
                reason = "低平赔+状态接近=实盘防平"
            else:
                prediction = "防平"
                confidence = "C级"
                reason = "低平赔+状态接近=实盘防平"
        
        # 状态差距大
        elif state_diff > 30:
            prediction = "主胜"
            confidence = "B级"
            reason = "状态差距大+低赔=实盘"
        elif state_diff < -30:
            prediction = "客胜"
            confidence = "B级"
            reason = "状态差距大+低赔=实盘"
        
        # 诱盘检测
        elif home > away and away < 2.0:
            prediction = "防平"
            confidence = "C级"
            reason = "主队低赔诱盘，防冷"
        elif away > home and home < 2.0:
            prediction = "防平"
            confidence = "C级"
            reason = "客队低赔诱盘，防冷"
        
        # 默认
        else:
            if home < away:
                prediction = "主胜"
                confidence = "C级"
                reason = "概率最高"
            else:
                prediction = "客胜"
                confidence = "C级"
                reason = "概率最高"
    
    return {
        "预测": prediction,
        "信心度": confidence,
        "理由": reason
    }


# ===== 测试3.13比赛 =====
def test_v3_v2():
    # 读取数据
    df = pd.read_excel('3.13_V3预测.xlsx')
    
    print("=" * 70)
    print("V3优化版 v2 - 威廉立博对比测试 (3.13)")
    print("=" * 70)
    
    # 模拟威廉立博数据（从源数据提取）
    # 周五004 胡巴尔 vs 吉达国民
    wl_data = {
        '周五004': '2.20|3.10|2.80|2.37|3.40|2.80',  # 威廉|立博
        '周五007': '1.85|3.60|3.65|1.85|3.60|3.65',  # 坎布尔 vs 罗达JC
        '周五010': '1.55|3.80|5.50|1.53|3.80|5.50',  # 马赛 vs 欧塞尔
    }
    
    results = []
    correct = 0
    total = 0
    
    for idx, row in df.iterrows():
        code = row['编号']
        
        # 添加威廉立博数据
        if code in wl_data:
            row['威廉立博'] = wl_data[code]
        else:
            row['威廉立博'] = ''
        
        # 预测
        result = v3_predict_v2(row)
        
        # 实际结果（从3.13复盘获取）
        actual = ""
        if code == '周五001':
            actual = "平"
        elif code == '周五002':
            actual = "主胜"
        elif code == '周五003':
            actual = "平"
        elif code == '周五004':
            actual = "主胜"
        elif code == '周五005':
            actual = "客胜"
        elif code == '周五006':
            actual = "平"
        elif code == '周五007':
            actual = "平"
        elif code == '周五008':
            actual = "主胜"
        elif code == '周五009':
            actual = "主胜"
        elif code == '周五010':
            actual = "主胜"
        elif code == '周五011':
            actual = "主胜"
        elif code == '周五012':
            actual = "平"
        
        # 判断对错
        is_correct = False
        if result['预测'] == actual:
            is_correct = True
            correct += 1
        elif '防平' in result['预测'] and actual == '平':
            is_correct = True
            correct += 1
        
        total += 1
        
        # 显示
        mark = "OK" if is_correct else "X"
        print(f"{code}: 预测={result['预测']:4s} 信心={result['信心度']} 实际={actual:4s} {mark}")
        print(f"     理由: {result['理由']}")
        print()
        
        results.append({
            '编号': code,
            '对阵': row['对阵'],
            '预测': result['预测'],
            '信心度': result['信心度'],
            '理由': result['理由'],
            '实际': actual,
            '结果': '✓' if is_correct else '✗'
        })
    
    print("=" * 70)
    accuracy = correct / total * 100
    print(f"准确率: {correct}/{total} = {accuracy:.1f}%")
    print("=" * 70)
    
    return results


if __name__ == "__main__":
    test_v3_v2()
