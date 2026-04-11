# 更多公式变体测试
import itertools

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
        conf = int(parts[5].replace('%', ''))
        if conf <= 55:
            continue
        diff = int(parts[6].replace('%', '').replace('+', ''))
        home_8 = int(parts[7])
        draw_8 = int(parts[8])
        away_8 = int(parts[9])
        final_pred = parts[11].strip()
        actual = parts[12].strip()
        
        matches.append({
            'date': parts[1], 'num': parts[2], 'teams': parts[3],
            'conf': conf, 'diff': diff,
            'home_8': home_8, 'draw_8': draw_8, 'away_8': away_8,
            'final_pred': final_pred, 'actual': actual,
        })
    except:
        pass

print(f"共 {len(matches)} 场比赛")

# 测试更多公式
def test_formula(formula_func, params):
    hits = 0
    for m in matches:
        pred = formula_func(m, params)
        if pred == m['actual']:
            hits += 1
    return hits

# 公式9: 高开大幅降低主胜，小幅增加平局
def formula_v9(m, k):
    C, D = m['conf'], m['diff']
    H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
    over = C - D
    
    # 高开(over>0)时: 主胜-k*over, 平局+k*over*0.3
    w_home = C + H - k * max(0, over)
    w_draw = 50 + Dr + k * max(0, over) * 0.3
    w_away = (100 - C) + A + k * max(0, -over)
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    return max(weights, key=weights.get)

# 公式10: 高开时反向8变化
def formula_v10(m, k):
    C, D = m['conf'], m['diff']
    H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
    over = C - D
    
    # 高开时，8变化反向
    if over > 10:
        H_adj, Dr_adj, A_adj = H - k, Dr + k*0.5, A + k*0.5
    else:
        H_adj, Dr_adj, A_adj = H + k*0.5, Dr, A - k*0.5
    
    w_home = C + H_adj
    w_draw = 50 + Dr_adj
    w_away = (100 - C) + A_adj
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    return max(weights, key=weights.get)

# 公式11: 置信度高且高开 → 走冷
def formula_v11(m, k):
    C, D = m['conf'], m['diff']
    H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
    over = C - D
    
    # 基础权重
    w_home = C + H
    w_draw = 50 + Dr + abs(C-50)*0.2
    w_away = (100 - C) + A
    
    # 高开且高置信度 → 走冷
    if C > 70 and over > 20:
        w_home -= k * over
        w_draw += k * 0.5
        w_away += k * 0.5
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    return max(weights, key=weights.get)

# 公式12: 胜率差大但置信度一般 → 走冷
def formula_v12(m, k):
    C, D = m['conf'], m['diff']
    H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
    
    w_home = C + H
    w_draw = 50 + Dr
    w_away = (100 - C) + A
    
    # 胜率差大但置信度一般(胜率差 > 置信度+20)
    if D > 40 and C < 75:
        w_home -= k * (D - C)
        w_draw += k * 0.5
        w_away += k * 0.5
    elif D < -40 and C < 75:
        w_away -= k * (abs(D) - C)
        w_draw += k * 0.5
        w_home += k * 0.5
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    return max(weights, key=weights.get)

# 公式13: 8变化极端值判断
def formula_v13(m, k):
    C, D = m['conf'], m['diff']
    H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
    
    w_home = C + H
    w_draw = 50 + Dr
    w_away = (100 - C) + A
    
    # 主胜8极端负值(<= -3)且高开 → 走冷
    if H <= -3 and C > D:
        w_home -= k * 3
        w_draw += k
        w_away += k * 0.5
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    return max(weights, key=weights.get)

# 公式14: 综合公式
def formula_v14(m, k):
    C, D = m['conf'], m['diff']
    H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
    over = C - D
    
    # 基础权重
    w_home = C + H
    w_draw = 50 + Dr
    w_away = (100 - C) + A
    
    # 高开调整
    if over > 25:
        w_home -= k * 1.5
        w_draw += k * 0.5
    elif over > 15:
        w_home -= k * 1.0
        w_draw += k * 0.3
    
    # 8变化极端
    if H <= -4:
        w_home -= k * 2
    if H >= 4:
        w_home += k
        
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    return max(weights, key=weights.get)

# 公式15: 你的案例 - 置信度59 vs 胜率差37, 高开22, 8变化[2,1,0]
# 你的思路: 高开22 → 主胜被高估 → 权重降低 → 平局
def formula_v15(m, k):
    C, D = m['conf'], m['diff']
    H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
    over = C - D  # 高开程度
    
    # 基础权重
    w_home = C + H
    w_draw = 50 + Dr
    w_away = (100 - C) + A
    
    # 核心逻辑: 高开(over>0)时, 主胜权重下降, 平局权重上升
    # 下降幅度 = k * over
    if over > 0:
        w_home -= k * over
        w_draw += k * over * 0.4
    else:
        # 低开(客胜高开)
        w_away -= k * abs(over)
        w_home += k * abs(over) * 0.3
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    return max(weights, key=weights.get)

# 测试
formulas = [
    ("v9-高开降主胜", formula_v9),
    ("v10-反向8变化", formula_v10),
    ("v11-高开高置信", formula_v11),
    ("v12-胜率差大走冷", formula_v12),
    ("v13-8极端值", formula_v13),
    ("v14-综合", formula_v14),
    ("v15-高开降权", formula_v15),
]

print("\n测试新公式:")
best_hit = 0
best_k = 0
best_name = ""

for name, func in formulas:
    for k in [5, 10, 15, 20, 25, 30, 35, 40]:
        hits = test_formula(func, k)
        if hits > best_hit:
            best_hit = hits
            best_k = k
            best_name = name

print(f"最佳: {best_name}, k={best_k}, 命中 {best_hit}/{len(matches)} ({best_hit/len(matches)*100:.1f}%)")

# 用最佳公式重新计算
print("\n详细结果:")
best_func = formula_v15 if "v15" in best_name else formula_v9
if "v10" in best_name:
    best_func = formula_v10
elif "v11" in best_name:
    best_func = formula_v11
elif "v12" in best_name:
    best_func = formula_v12
elif "v13" in best_name:
    best_func = formula_v13
elif "v14" in best_name:
    best_func = formula_v14

for m in matches:
    pred = best_func(m, best_k)
    is_correct = pred == m['actual']
    mark = "O" if is_correct else "X"
    print(m['date'] + " " + m['num'] + " " + m['teams'][:12].ljust(12) + " C=" + str(m['conf']) + "% D=" + str(m['diff']) + "% 8=[" + str(m['home_8']) + "," + str(m['draw_8']) + "," + str(m['away_8']) + "] 预" + pred + " vs 实" + m['actual'] + " " + mark)
