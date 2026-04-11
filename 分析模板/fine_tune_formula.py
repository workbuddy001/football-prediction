# 更精细的公式测试
import sys
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
        actual = parts[12].strip()
        
        matches.append({
            'date': parts[1], 'num': parts[2], 'teams': parts[3],
            'conf': conf, 'diff': diff,
            'home_8': home_8, 'draw_8': draw_8, 'away_8': away_8,
            'actual': actual,
        })
    except:
        pass

print("共 " + str(len(matches)) + " 场比赛")

# 测试各种公式组合
best_hit = 0
best_params = None

# 尝试不同的k值范围
for k1 in range(0, 50, 5):  # 高开调整系数
    for k2 in range(0, 30, 5):  # 8变化系数
        for base_draw in range(45, 60, 5):  # 平局基础值
            for home_base in range(0, 2):  # 主胜是否用置信度
                hits = 0
                for m in matches:
                    C, D = m['conf'], m['diff']
                    H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
                    over = C - D  # 高开程度
                    
                    # 主胜权重
                    if home_base == 0:
                        w_home = C + H
                    else:
                        w_home = 50 + H + over * 0.5
                    
                    # 平局权重
                    w_draw = base_draw + Dr + abs(C - 50) * 0.1
                    
                    # 客胜权重
                    w_away = (100 - C) + A
                    
                    # 高开调整
                    if over > 10:
                        w_home -= k1 * over / 20.0
                        w_draw += k1 * over / 40.0
                    
                    # 8变化极端调整
                    if H <= -4:
                        w_home -= k2 / 10.0
                    if H >= 3:
                        w_home += k2 / 20.0
                    
                    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
                    pred = max(weights, key=weights.get)
                    if pred == m['actual']:
                        hits += 1
                
                if hits > best_hit:
                    best_hit = hits
                    best_params = (k1, k2, base_draw, home_base)

print("最佳: k1=" + str(best_params[0]) + ", k2=" + str(best_params[1]) + ", base_draw=" + str(best_params[2]) + ", home_base=" + str(best_params[3]))
print("命中 " + str(best_hit) + "/" + str(len(matches)) + " (" + str(best_hit*100/len(matches)) + "%)")

# 用最佳参数输出详细结果
k1, k2, base_draw, home_base = best_params
print("\n详细结果:")
print("-" * 100)
for m in matches:
    C, D = m['conf'], m['diff']
    H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
    over = C - D
    
    if home_base == 0:
        w_home = C + H
    else:
        w_home = 50 + H + over * 0.5
    
    w_draw = base_draw + Dr + abs(C - 50) * 0.1
    w_away = (100 - C) + A
    
    if over > 10:
        w_home -= k1 * over / 20.0
        w_draw += k1 * over / 40.0
    
    if H <= -4:
        w_home -= k2 / 10.0
    if H >= 3:
        w_home += k2 / 20.0
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    pred = max(weights, key=weights.get)
    is_correct = pred == m['actual']
    mark = "O" if is_correct else "X"
    
    print(m['date'] + " " + m['num'] + " " + m['teams'][:12].ljust(12) + " C=" + str(C) + "% D=" + str(D) + "% 8=[" + str(H) + "," + str(Dr) + "," + str(A) + "] 预" + pred + " vs 实" + m['actual'] + " " + mark)
