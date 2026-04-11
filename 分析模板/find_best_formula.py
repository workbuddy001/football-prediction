# 分析置信度>55%比赛的预测公式
# 核心变量：
# - C: 置信度 (0-100)
# - D: 胜率差 (-100到+100，正数表示主队更强)
# - 8变化: [H, Dr, A] (主胜、平局、客胜的变化)

# 读取分析结果
matches = []
with open('v7_8_full_analysis.md', encoding='utf-8') as f:
    lines = f.readlines()
    
for line in lines:
    if '|' not in line or '日期' in line or '---' in line or line.strip() == '':
        continue
    parts = [p.strip() for p in line.split('|')]
    if len(parts) < 15:
        continue
    try:
        conf_str = parts[5].replace('%', '')
        conf = int(conf_str)
        if conf <= 55:  # 只分析置信度>55%的
            continue
        
        # 解析胜率差
        diff_str = parts[6]
        diff = int(diff_str.replace('%', '').replace('+', ''))
        
        # 解析8变化
        home_8 = int(parts[7])
        draw_8 = int(parts[8])
        away_8 = int(parts[9])
        
        # 最终预测和实际结果
        final_pred = parts[11].strip()
        actual = parts[12].strip()
        
        matches.append({
            'date': parts[1],
            'num': parts[2],
            'teams': parts[3],
            'conf': conf,
            'diff': diff,
            'home_8': home_8,
            'draw_8': draw_8,
            'away_8': away_8,
            'final_pred': final_pred,
            'actual': actual,
        })
    except Exception as e:
        print(f"Error: {e}, parts: {parts}")
        pass

print(f"共 {len(matches)} 场比赛分析")

# 测试不同公式
def formula_v1(match, k=0.5):
    """公式1: 权重 = C + k*(C-D) + 8变化"""
    C = match['conf']
    D = match['diff']
    H, Dr, A = match['home_8'], match['draw_8'], match['away_8']
    
    # 高开程度
    overval = C - D
    
    # 计算各选项权重
    w_home = C + k * overval + H
    w_draw = 50 + k * (50 - abs(D)) + Dr
    w_away = (100 - C) + k * (-overval) + A
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    pred = max(weights, key=weights.get)
    return pred

def formula_v2(match, k=1.0):
    """公式2: 权重 = C + k*(C-D) + 8变化, 平局基础=C"""
    C = match['conf']
    D = match['diff']
    H, Dr, A = match['home_8'], match['draw_8'], match['away_8']
    
    overval = C - D
    
    w_home = C + k * overval + H
    w_draw = C + Dr
    w_away = (100 - C) + k * (-overval) + A
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    pred = max(weights, key=weights.get)
    return pred

def formula_v3(match, k=0.3):
    """公式3: 权重 = C + 8变化 + k*(C-D), 但8变化有上限"""
    C = match['conf']
    D = match['diff']
    H, Dr, A = match['home_8'], match['draw_8'], match['away_8']
    
    overval = C - D
    
    H_c = max(-3, min(3, H))
    Dr_c = max(-3, min(3, Dr))
    A_c = max(-3, min(3, A))
    
    w_home = C + H_c + k * overval
    w_draw = 50 + Dr_c
    w_away = (100 - C) + A_c - k * overval
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    pred = max(weights, key=weights.get)
    return pred

def formula_v4(match, k=0.5):
    """公式4: 权重 = C + 8变化 + k*(C-D)"""
    C = match['conf']
    D = match['diff']
    H, Dr, A = match['home_8'], match['draw_8'], match['away_8']
    
    overval = C - D
    
    w_home = C + H + k * overval
    w_draw = 50 + Dr + k * (50 - abs(D)) * 0.5
    w_away = (100 - C) + A - k * overval
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    pred = max(weights, key=weights.get)
    return pred

def formula_v5(match, k=0.3):
    """公式5: 核心思路 - 高开时容易出冷门"""
    C = match['conf']
    D = match['diff']
    H, Dr, A = match['home_8'], match['draw_8'], match['away_8']
    
    overval = C - D
    
    w_home = C + H
    w_draw = 50 + Dr
    w_away = (100 - C) + A
    
    w_home_adjusted = w_home - k * overval
    
    if H > 2:
        w_home_adjusted += 3
    if A > 2:
        w_away += 3
        
    weights = {'主胜': w_home_adjusted, '平局': w_draw, '客胜': w_away}
    pred = max(weights, key=weights.get)
    return pred

def formula_v6(match, k=0.4):
    """公式6: 简化版"""
    C = match['conf']
    D = match['diff']
    H, Dr, A = match['home_8'], match['draw_8'], match['away_8']
    
    overval = C - D
    
    w_home = C + H + k * overval
    w_draw = 50 + Dr + k * (50 - abs(D)) * 0.5
    w_away = (100 - C) + A - k * overval
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    pred = max(weights, key=weights.get)
    return pred

def formula_v7(match, k=0.5):
    """公式7: 考虑胜率差绝对值和方向"""
    C = match['conf']
    D = match['diff']
    H, Dr, A = match['home_8'], match['draw_8'], match['away_8']
    
    # 主胜高开程度
    overval = C - D  # 正=主胜高开，负=客胜高开
    
    # 主胜权重 = 置信度 + 8变化 + k * 高开程度
    w_home = C + H + k * overval
    
    # 平局权重：基础50 + 8变化 + 置信度偏离50的部分
    w_draw = 50 + Dr + abs(C - 50) * 0.3
    
    # 客胜权重
    w_away = (100 - C) + A - k * overval
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    pred = max(weights, key=weights.get)
    return pred

def formula_v8(match, k=0.6):
    """公式8: 高开大幅降低主胜权重"""
    C = match['conf']
    D = match['diff']
    H, Dr, A = match['home_8'], match['draw_8'], match['away_8']
    
    overval = C - D
    
    # 主胜权重
    w_home = C + H - k * max(0, overval)  # 高开时减少权重
    
    # 平局权重
    w_draw = 50 + Dr + abs(C - 50) * 0.4
    
    # 客胜权重
    w_away = (100 - C) + A + k * max(0, -overval)  # 低开时增加权重
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    pred = max(weights, key=weights.get)
    return pred

# 测试不同k值
print("\n测试不同公式和k值:")
print("="*60)

best_k = 0
best_hit = 0
best_formula = ""

formulas = [
    ("公式v1", formula_v1),
    ("公式v2", formula_v2),
    ("公式v3", formula_v3),
    ("公式v4", formula_v4),
    ("公式v5", formula_v5),
    ("公式v6", formula_v6),
    ("公式v7", formula_v7),
    ("公式v8", formula_v8),
]

for name, func in formulas:
    for k in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        hits = 0
        for m in matches:
            pred = func(m, k)
            if pred == m['actual']:
                hits += 1
        
        if hits > best_hit:
            best_hit = hits
            best_k = k
            best_formula = name
            
print(f"最佳: {best_formula}, k={best_k}, 命中 {best_hit}/{len(matches)} ({best_hit/len(matches)*100:.1f}%)")

# 打印最佳公式的详细结果
print("\n最佳公式详细结果:")
print("="*100)

formula_map = {
    "公式v1": formula_v1, "公式v2": formula_v2, "公式v3": formula_v3,
    "公式v4": formula_v4, "公式v5": formula_v5, "公式v6": formula_v6,
    "公式v7": formula_v7, "公式v8": formula_v8,
}
best_func = formula_map[best_formula]

correct = []
wrong = []
for m in matches:
    pred = best_func(m, best_k)
    is_correct = pred == m['actual']
    
    result = {
        'date': m['date'],
        'num': m['num'],
        'teams': m['teams'][:15],
        'conf': m['conf'],
        'diff': m['diff'],
        '8变化': '[' + str(m["home_8"]) + ',' + str(m["draw_8"]) + ',' + str(m["away_8"]) + ']',
        'pred': pred,
        'actual': m['actual'],
        'correct': is_correct
    }
    
    if is_correct:
        correct.append(result)
    else:
        wrong.append(result)

print(f"\n命中 {len(correct)} 场:")
for c in correct:
    print(f"  {c['date']} {c['num']} {c['teams']:<15} C={c['conf']}% D={c['diff']:+d}% 8={c['8变化']} 预{c['pred']} vs 实{c['actual']}")

print(f"\n错失 {len(wrong)} 场:")
for w in wrong:
    print(f"  {w['date']} {w['num']} {w['teams']:<15} C={w['conf']}% D={w['diff']:+d}% 8={w['8变化']} 预{w['pred']} vs 实{w['actual']}")
