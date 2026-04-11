# 最终公式优化
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

# 根据你的案例分析:
# 巴列卡诺vs莱万特: C=59, D=37, 高开=22, 8=[2,1,0]
# 结果: 平局
# 你的思路:
# 1. 高开程度 = C - D = 22 (主胜被高估)
# 2. 8变化: 主胜+2, 平局+1, 客胜+0
# 3. 胜率差只有37% → 实力差距不大 → 平局权重上升

# 核心公式:
# W_home = C + H8 - k1 * max(0, C-D)  # 高开时降低权重
# W_draw = 50 + D8 + k2 * max(0, 30-abs(D))  # 胜率差小时增加平局权重
# W_away = (100-C) + A8 - k1 * max(0, D-C)  # 低开时降低权重

best_hit = 0
best_params = None

# 搜索最优参数
for k1 in range(0, 60, 2):  # 高开调整系数
    for k2 in range(0, 30, 2):  # 平局系数
        for draw_base in range(40, 55, 2):  # 平局基础
            for draw_threshold in range(20, 50, 5):  # 胜率差阈值
                hits = 0
                for m in matches:
                    C, D = m['conf'], m['diff']
                    H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
                    over = C - D  # 高开程度
                    
                    # 主胜权重 = 置信度 + 8变化 - k1 * 高开程度
                    w_home = C + H - k1 * max(0, over) / 10.0
                    
                    # 平局权重 = 基础 + 8变化 + 胜率差小时加成
                    diff_factor = max(0, draw_threshold - abs(D)) / 10.0
                    w_draw = draw_base + Dr + k2 * diff_factor
                    
                    # 客胜权重 = (100-置信度) + 8变化 - k1 * 低开程度
                    w_away = (100 - C) + A - k1 * max(0, -over) / 10.0
                    
                    # 8变化极端值加权
                    if H >= 3:
                        w_home += k1 * 0.3
                    if H <= -4:
                        w_home -= k1 * 0.3
                    
                    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
                    pred = max(weights, key=weights.get)
                    if pred == m['actual']:
                        hits += 1
                
                if hits > best_hit:
                    best_hit = hits
                    best_params = (k1, k2, draw_base, draw_threshold)

print("最佳参数: k1=" + str(best_params[0]) + ", k2=" + str(best_params[1]) + ", draw_base=" + str(best_params[2]) + ", threshold=" + str(best_params[3]))
print("命中 " + str(best_hit) + "/" + str(len(matches)) + " (" + str(round(best_hit*100/len(matches),1)) + "%)")

# 用最佳参数输出详细结果
k1, k2, draw_base, threshold = best_params
print("\n" + "="*100)
print("公式说明:")
print("  主胜权重 = 置信度 + 主胜8变化 - k1 * max(0, 置信度-胜率差) / 10")
print("  平局权重 = " + str(draw_base) + " + 平局8变化 + k2 * max(0, " + str(threshold) + "-abs(胜率差)) / 10")
print("  客胜权重 = (100-置信度) + 客胜8变化 - k1 * max(0, 胜率差-置信度) / 10")
print("="*100)

correct = []
wrong = []
for m in matches:
    C, D = m['conf'], m['diff']
    H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
    over = C - D
    
    w_home = C + H - k1 * max(0, over) / 10.0
    diff_factor = max(0, threshold - abs(D)) / 10.0
    w_draw = draw_base + Dr + k2 * diff_factor
    w_away = (100 - C) + A - k1 * max(0, -over) / 10.0
    
    if H >= 3:
        w_home += k1 * 0.3
    if H <= -4:
        w_home -= k1 * 0.3
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    pred = max(weights, key=weights.get)
    is_correct = pred == m['actual']
    
    result = {
        'date': m['date'], 'num': m['num'], 'teams': m['teams'],
        'conf': C, 'diff': D, '8': '['+str(H)+','+str(Dr)+','+str(A)+']',
        'pred': pred, 'actual': m['actual'], 'correct': is_correct
    }
    
    if is_correct:
        correct.append(result)
    else:
        wrong.append(result)

print("\n命中 " + str(len(correct)) + " 场:")
for c in correct:
    print("  " + c['date'] + " " + c['num'] + " " + c['teams'][:12].ljust(12) + " C=" + str(c['conf']) + "% D=" + str(c['diff']) + "% 8=" + c['8'] + " 预" + c['pred'] + " vs 实" + c['actual'])

print("\n错失 " + str(len(wrong)) + " 场:")
for w in wrong:
    print("  " + w['date'] + " " + w['num'] + " " + w['teams'][:12].ljust(12) + " C=" + str(w['conf']) + "% D=" + str(w['diff']) + "% 8=" + w['8'] + " 预" + w['pred'] + " vs 实" + w['actual'])
