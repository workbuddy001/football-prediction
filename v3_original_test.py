"""
V3原版 - 命中率最高版本
直接使用原有V3算法预测
"""

import pandas as pd

def v3_predict_original(row):
    """V3原版预测逻辑"""
    home = row['主胜']
    draw = row['平局']
    away = row['客胜']
    
    # 解析状态
    try:
        home_state = float(str(row['主队状态']).replace('%', ''))
    except:
        home_state = 50
    try:
        away_state = float(str(row['客队状态']).replace('%', ''))
    except:
        away_state = 50
    
    state_diff = home_state - away_state
    
    # ===== V3原版核心逻辑 =====
    
    # A级信号：极低赔 + 状态差距大
    if home < 1.6 and state_diff > 20:
        return "主胜", "A级", "极低赔+状态差距大=实盘"
    if away < 1.6 and state_diff < -20:
        return "客胜", "A级", "极低赔+状态差距大=实盘"
    
    # B级信号：低平赔 + 状态接近 = 防平
    if draw < 2.9 and abs(state_diff) < 15:
        return "防平", "B级", "低平赔+状态接近=实盘防平"
    
    # 状态差距大 + 低赔
    if state_diff > 30 and home < 2.0:
        return "主胜", "B级", "状态差距大+低赔=实盘"
    if state_diff < -30 and away < 2.0:
        return "客胜", "B级", "状态差距大+低赔=实盘"
    
    # 诱盘检测：低赔方是诱盘
    if home > away and away < 2.0:
        return "防平", "C级", "主队低赔诱盘，防冷"
    if away > home and home < 2.0:
        return "防平", "C级", "客队低赔诱盘，防冷"
    
    # 默认：概率最高
    if home < away:
        return "主胜", "C级", "概率最高"
    else:
        return "客胜", "C级", "概率最高"


# 测试3.13
print("=" * 70)
print("V3原版 - 3.13比赛预测")
print("=" * 70)

df = pd.read_excel('3.13_V3预测.xlsx')

# 实际结果
actual_results = {
    '周五001': '平', '周五002': '主胜', '周五003': '平', '周五004': '主胜',
    '周五005': '客胜', '周五006': '平', '周五007': '平', '周五008': '主胜',
    '周五009': '主胜', '周五010': '主胜', '周五011': '主胜', '周五012': '平'
}

correct = 0
total = 0

for _, row in df.iterrows():
    code = row['编号']
    pred, conf, reason = v3_predict_original(row)
    actual = actual_results.get(code, '')
    
    is_correct = pred == actual or ('防平' in pred and actual == '平')
    if is_correct:
        correct += 1
        mark = "OK"
    else:
        mark = "X"
    total += 1
    
    print(f"{code}: {pred:4s} {conf} 实际={actual:4s} {mark}")

print("=" * 70)
print(f"准确率: {correct}/{total} = {correct/total*100:.1f}%")
print("=" * 70)
