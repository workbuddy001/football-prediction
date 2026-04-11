# 基于直觉的简单规则
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

# 简单规则测试
def rule_based(m):
    C, D = m['conf'], m['diff']
    H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
    over = C - D
    
    # 规则1: 胜率差绝对值 >= 60 → 强信号
    if D >= 60:
        return '主胜'
    if D <= -60:
        return '客胜'
    
    # 规则2: 高开(over>20) 且 胜率差小(|D|<40) → 走冷
    if over > 20 and abs(D) < 40:
        # 8变化判断
        if H <= -3:
            return '平局'
        if Dr > 0:
            return '平局'
        return '平局'
    
    # 规则3: 8变化极端
    if H >= 4:
        return '主胜'
    if A >= 4:
        return '客胜'
    if H <= -4:
        return '平局'
    
    # 规则4: 默认用置信度
    return '主胜' if C > 50 else '客胜'

# 测试规则
hits = 0
for m in matches:
    pred = rule_based(m)
    if pred == m['actual']:
        hits += 1
        
print("规则法命中: " + str(hits) + "/" + str(len(matches)) + " (" + str(round(hits*100/len(matches),1)) + "%)")

# 打印结果
for m in matches:
    pred = rule_based(m)
    mark = "O" if pred == m['actual'] else "X"
    print(m['date'] + " " + m['num'] + " " + m['teams'][:12].ljust(12) + " C=" + str(m['conf']) + "% D=" + str(m['diff']) + "% 8=[" + str(m['home_8']) + "," + str(m['draw_8']) + "," + str(m['away_8']) + "] 预" + pred + " vs 实" + m['actual'] + " " + mark)
