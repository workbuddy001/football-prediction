# 更细致的分段优化 - 尝试更多规则变体
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

# 更细的分段
segments = {
    '55-60%': [m for m in matches if 55 <= m['conf'] < 60],
    '60-65%': [m for m in matches if 60 <= m['conf'] < 65],
    '65-70%': [m for m in matches if 65 <= m['conf'] < 70],
    '70-75%': [m for m in matches if 70 <= m['conf'] < 75],
    '75-80%': [m for m in matches if 75 <= m['conf'] < 80],
    '80%+': [m for m in matches if m['conf'] >= 80],
}

print("各置信度分段:")
for seg_name, seg_matches in segments.items():
    print(f"  {seg_name}: {len(seg_matches)} 场")

# 简化规则测试 - 只用核心规则
def test_rules(segment_matches, t1, t2, t3, use_default='主胜'):
    hits = 0
    for m in segment_matches:
        C, D = m['conf'], m['diff']
        H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
        over = C - D
        
        if D >= t1:
            pred = '主胜'
        elif D <= -t1:
            pred = '客胜'
        elif over > t2 and abs(D) < t3:
            pred = '平局'
        elif H >= 2:
            pred = '主胜'
        elif H <= -3:
            pred = '平局'
        elif A >= 3:
            pred = '客胜'
        else:
            pred = use_default
        
        if pred == m['actual']:
            hits += 1
    return hits

# 对每个分段找最佳参数
print("\n" + "="*60)
print("每个分段的最佳配置")
print("="*60)

all_results = {}
total_hits = 0
total_matches = 0

for seg_name in ['55-60%', '60-65%', '65-70%', '70-75%', '75-80%', '80%+']:
    seg_matches = segments[seg_name]
    if len(seg_matches) == 0:
        continue
    
    best_hit = 0
    best_params = None
    
    for t1 in [25, 30, 35, 40, 45, 50, 55, 60, 65, 70]:
        for t2 in [0, 5, 10, 15, 20, 25]:
            for t3 in [15, 20, 25, 30, 35, 40, 45, 50]:
                for default in ['主胜', '平局', '客胜']:
                    hits = test_rules(seg_matches, t1, t2, t3, default)
                    if hits > best_hit:
                        best_hit = hits
                        best_params = (t1, t2, t3, default)
    
    all_results[seg_name] = {
        'params': best_params,
        'matches': seg_matches,
        'hits': best_hit,
        'total': len(seg_matches)
    }
    
    t1, t2, t3, default = best_params
    print(f"\n【{seg_name}】({len(seg_matches)}场)")
    print(f"  t1(胜率差)={t1}%, t2(高开阈值)={t2}%, t3(胜率差小)={t3}%, 默认={default}")
    print(f"  命中: {best_hit}/{len(seg_matches)} ({round(best_hit*100/len(seg_matches),1)}%)")
    
    total_hits += best_hit
    total_matches += len(seg_matches)

print(f"\n{'='*60}")
print(f"总计: {total_hits}/{total_matches} ({round(total_hits*100/total_matches,1)}%)")
print("="*60)

# 输出详细预测
print("\n详细预测结果:")
print("-"*90)

for seg_name in ['55-60%', '60-65%', '65-70%', '70-75%', '75-80%', '80%+']:
    res = all_results.get(seg_name)
    if not res:
        continue
    
    t1, t2, t3, default = res['params']
    print(f"\n=== {seg_name} ===")
    
    for m in res['matches']:
        C, D = m['conf'], m['diff']
        H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
        over = C - D
        
        if D >= t1:
            pred = '主胜'
        elif D <= -t1:
            pred = '客胜'
        elif over > t2 and abs(D) < t3:
            pred = '平局'
        elif H >= 2:
            pred = '主胜'
        elif H <= -3:
            pred = '平局'
        elif A >= 3:
            pred = '客胜'
        else:
            pred = default
        
        mark = "O" if pred == m['actual'] else "X"
        print(f"  {m['date']} {m['num']} {m['teams'][:12]:<12} C={C}% D={D}% 8=[{H},{Dr},{A}] 预{pred} vs 实{m['actual']} {mark}")
