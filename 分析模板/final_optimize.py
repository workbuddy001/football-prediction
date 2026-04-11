# 最终优化规则
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

# 加入更多规则变体测试
best_hit = 0
best_config = None

# 完整参数搜索
for t1 in [45, 50, 55, 60]:
    for t2 in [10, 15, 20, 25]:
        for t3 in [30, 35, 40, 45]:
            for t4 in range(-6, 0):
                for t5 in [2, 3, 4]:
                    for t6 in [40, 45, 50, 55]:  # 新增: 客胜8极端
                        hits = 0
                        for m in matches:
                            C, D = m['conf'], m['diff']
                            H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
                            over = C - D
                            
                            if D >= t1:
                                pred = '主胜'
                            elif D <= -t1:
                                pred = '客胜'
                            elif over > t2 and abs(D) < t3:
                                pred = '平局'
                            elif H >= t5:
                                pred = '主胜'
                            elif H <= t4:
                                pred = '平局'
                            elif A >= t6 - 35:  # 映射
                                pred = '客胜'
                            else:
                                pred = '主胜'
                            
                            if pred == m['actual']:
                                hits += 1
                        
                        if hits > best_hit:
                            best_hit = hits
                            best_config = (t1, t2, t3, t4, t5, t6)

print("最佳配置: " + str(best_config))
print("命中 " + str(best_hit) + "/" + str(len(matches)) + " (" + str(round(best_hit*100/len(matches),1)) + "%)")

# 验证配置
t1, t2, t3, t4, t5, t6 = best_config

correct = []
wrong = []
for m in matches:
    C, D = m['conf'], m['diff']
    H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
    over = C - D
    
    if D >= t1:
        pred = '主胜'
    elif D <= -t1:
        pred = '客胜'
    elif over > t2 and abs(D) < t3:
        pred = '平局'
    elif H >= t5:
        pred = '主胜'
    elif H <= t4:
        pred = '平局'
    elif A >= t6 - 35:
        pred = '客胜'
    else:
        pred = '主胜'
    
    is_correct = pred == m['actual']
    
    if is_correct:
        correct.append((m, pred))
    else:
        wrong.append((m, pred))

print("\n命中 " + str(len(correct)) + " 场:")
for m, pred in correct:
    print("  " + m['date'] + " " + m['num'] + " " + m['teams'][:12].ljust(12) + " C=" + str(m['conf']) + "% D=" + str(m['diff']) + "% 8=[" + str(m['home_8']) + "," + str(m['draw_8']) + "," + str(m['away_8']) + "] 预" + pred + " vs 实" + m['actual'])

print("\n错失 " + str(len(wrong)) + " 场:")
for m, pred in wrong:
    print("  " + m['date'] + " " + m['num'] + " " + m['teams'][:12].ljust(12) + " C=" + str(m['conf']) + "% D=" + str(m['diff']) + "% 8=[" + str(m['home_8']) + "," + str(m['draw_8']) + "," + str(m['away_8']) + "] 预" + pred + " vs 实" + m['actual'])
