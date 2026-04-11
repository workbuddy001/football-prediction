# 优化规则
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

# 尝试不同的规则组合
best_hit = 0
best_rules = None

# 参数搜索
for thresh_diff in [50, 55, 60, 65, 70]:  # 强信号胜率差阈值
    for over_thresh in [15, 20, 25, 30]:  # 高开阈值
        for abs_diff_thresh in [35, 40, 45, 50]:  # 胜率差小时判断
            for h8_neg in [-5, -4, -3, -2]:  # 主胜8变化极端负值
                for h8_pos in [3, 4, 5]:  # 主胜8变化极端正值
                    hits = 0
                    for m in matches:
                        C, D = m['conf'], m['diff']
                        H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
                        over = C - D
                        
                        # 规则1: 强信号
                        if D >= thresh_diff:
                            pred = '主胜'
                        elif D <= -thresh_diff:
                            pred = '客胜'
                        # 规则2: 高开走冷
                        elif over > over_thresh and abs(D) < abs_diff_thresh:
                            if H <= h8_neg:
                                pred = '平局'
                            elif Dr > 0:
                                pred = '平局'
                            else:
                                pred = '平局'
                        # 规则3: 8变化极端
                        elif H >= h8_pos:
                            pred = '主胜'
                        elif A >= 3:
                            pred = '客胜'
                        elif H <= -4:
                            pred = '平局'
                        # 规则4: 默认
                        else:
                            pred = '主胜'
                        
                        if pred == m['actual']:
                            hits += 1
                    
                    if hits > best_hit:
                        best_hit = hits
                        best_rules = (thresh_diff, over_thresh, abs_diff_thresh, h8_neg, h8_pos)

print("最佳规则: thresh_diff=" + str(best_rules[0]) + ", over=" + str(best_rules[1]) + ", abs_diff=" + str(best_rules[2]) + ", h8_neg=" + str(best_rules[3]) + ", h8_pos=" + str(best_rules[4]))
print("命中 " + str(best_hit) + "/" + str(len(matches)) + " (" + str(round(best_hit*100/len(matches),1)) + "%)")

# 用最佳规则输出详细结果
thresh_diff, over_thresh, abs_diff_thresh, h8_neg, h8_pos = best_rules
print("\n" + "="*90)
print("公式说明:")
print("  规则1: 胜率差 >= " + str(thresh_diff) + "% → 主胜; 胜率差 <= -" + str(thresh_diff) + "% → 客胜")
print("  规则2: 高开(置信度-胜率差 > " + str(over_thresh) + "%) 且 |胜率差| < " + str(abs_diff_thresh) + "% → 平局")
print("  规则3: 主胜8变化 >= " + str(h8_pos) + " → 主胜; 主胜8变化 <= " + str(h8_neg) + " → 平局")
print("  规则4: 默认主胜")
print("="*90)

correct = []
wrong = []
for m in matches:
    C, D = m['conf'], m['diff']
    H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
    over = C - D
    
    if D >= thresh_diff:
        pred = '主胜'
    elif D <= -thresh_diff:
        pred = '客胜'
    elif over > over_thresh and abs(D) < abs_diff_thresh:
        if H <= h8_neg:
            pred = '平局'
        elif Dr > 0:
            pred = '平局'
        else:
            pred = '平局'
    elif H >= h8_pos:
        pred = '主胜'
    elif A >= 3:
        pred = '客胜'
    elif H <= -4:
        pred = '平局'
    else:
        pred = '主胜'
    
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
