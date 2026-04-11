# 筛选置信度>55%的比赛

with open('v7_8_full_analysis.md', encoding='utf-8') as f:
    lines = f.readlines()

results = []
for line in lines[19:]:
    if '|' not in line or line.startswith('|---'):
        continue
    parts = [p.strip() for p in line.split('|')]
    if len(parts) < 14:
        continue
    
    # 列位置: 1=日期,2=编号,3=对阵,4=V7预测,5=置信度,6=胜率差,...
    try:
        conf_str = parts[5]  # 置信度在第5列
        conf = int(conf_str.replace('%', ''))
        if conf > 55:
            results.append({
                'date': parts[1],
                'num': parts[2],
                'teams': parts[3],
                'v7_pred': parts[4],
                'confidence': parts[5],
                'diff': parts[6],
                'home_8': parts[7],
                'draw_8': parts[8],
                'away_8': parts[9],
                'increase': parts[10],
                'final_pred': parts[11],
                'actual': parts[12],
                'score': parts[13],
                'result': parts[14],
            })
    except Exception as e:
        pass

print(f'置信度>55%的比赛共 {len(results)} 场')
print()
print('='*130)
print(f"{'日期':<6} {'编号':<10} {'对阵':<28} {'V7预测':<6} {'置信度':<8} {'胜率差':<8} {'8变化':<15} {'最终预测':<6} {'实际':<6} {'比分':<8} {'结果':<4}")
print('='*130)

hit = 0
for r in results:
    changes = f'[{r[\"home_8\"]},{r[\"draw_8\"]},{r[\"away_8\"]}]'
    print(f"{r['date']:<6} {r['num']:<10} {r['teams'][:25]:<25} {r['v7_pred']:<6} {r['confidence']:<8} {r['diff']:<8} {changes:<15} {r['final_pred']:<6} {r['actual']:<6} {r['score']:<8} {r['result']:<4}")
    if r['result'] == '对':
        hit += 1

print('='*130)
if len(results) > 0:
    print(f"命中: {hit}/{len(results)} ({hit/len(results)*100:.1f}%)")
