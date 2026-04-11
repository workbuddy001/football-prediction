# 按置信度分段优化公式
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

# 按置信度分段
segments = {
    '55-60%': [m for m in matches if 55 <= m['conf'] < 60],
    '60-70%': [m for m in matches if 60 <= m['conf'] < 70],
    '70-80%': [m for m in matches if 70 <= m['conf'] < 80],
    '80%+': [m for m in matches if m['conf'] >= 80],
}

print("各置信度分段:")
for seg_name, seg_matches in segments.items():
    print(f"  {seg_name}: {len(seg_matches)} 场")

# 对每个分段单独优化规则
def optimize_segment(segment_matches, segment_name):
    if len(segment_matches) < 3:
        return None, 0
    
    best_hit = 0
    best_config = None
    
    for t1 in [30, 35, 40, 45, 50, 55, 60]:
        for t2 in [5, 10, 15, 20]:
            for t3 in [20, 25, 30, 35, 40, 45]:
                for h8_neg in [-5, -4, -3, -2, -1]:
                    for h8_pos in [1, 2, 3, 4]:
                        for a8_pos in [1, 2, 3, 4, 5]:
                            hits = 0
                            for m in segment_matches:
                                C, D = m['conf'], m['diff']
                                H, Dr, A = m['home_8'], m['draw_8'], m['away_8']
                                over = C - D
                                
                                # 规则1: 强信号
                                if D >= t1:
                                    pred = '主胜'
                                elif D <= -t1:
                                    pred = '客胜'
                                # 规则2: 高开走冷
                                elif over > t2 and abs(D) < t3:
                                    if H <= h8_neg:
                                        pred = '平局'
                                    elif Dr > 0:
                                        pred = '平局'
                                    else:
                                        pred = '平局'
                                # 规则3: 8变化极端
                                elif H >= h8_pos:
                                    pred = '主胜'
                                elif A >= a8_pos:
                                    pred = '客胜'
                                elif H <= -3:
                                    pred = '平局'
                                # 规则4: 默认
                                else:
                                    pred = '主胜'
                                
                                if pred == m['actual']:
                                    hits += 1
                            
                            if hits > best_hit:
                                best_hit = hits
                                best_config = (t1, t2, t3, h8_neg, h8_pos, a8_pos)
    
    return best_config, best_hit, len(segment_matches)

# 优化每个分段
results = {}
for seg_name, seg_matches in segments.items():
    print(f"\n{'='*50}")
    print(f"优化分段: {seg_name} ({len(seg_matches)} 场)")
    print('='*50)
    
    config, hits, total = optimize_segment(seg_matches, seg_name)
    if config:
        results[seg_name] = {
            'config': config,
            'hits': hits,
            'total': total,
            'matches': seg_matches
        }
        print(f"最佳: t1={config[0]}, t2={config[1]}, t3={config[2]}, h8_neg={config[3]}, h8_pos={config[4]}, a8_pos={config[5]}")
        print(f"命中: {hits}/{total} ({round(hits*100/total,1)}%)")

# 输出汇总
print("\n" + "="*70)
print("分段公式汇总")
print("="*70)

total_hits = 0
total_matches = 0

for seg_name, res in results.items():
    config = res['config']
    t1, t2, t3, h8_neg, h8_pos, a8_pos = config
    print(f"\n【{seg_name}】")
    print(f"  规则1: 胜率差 >= {t1}% → 主胜; <= -{t1}% → 客胜")
    print(f"  规则2: 高开(over > {t2}%) 且 |胜率差| < {t3}% → 平局")
    print(f"  规则3: 主胜8 >= {h8_pos} → 主胜; <= {h8_neg} → 平局")
    print(f"  规则4: 客胜8 >= {a8_pos} → 客胜")
    print(f"  规则5: 默认主胜")
    print(f"  命中率: {res['hits']}/{res['total']} ({round(res['hits']*100/res['total'],1)}%)")
    total_hits += res['hits']
    total_matches += res['total']

print(f"\n总计: {total_hits}/{total_matches} ({round(total_hits*100/total_matches,1)}%)")
