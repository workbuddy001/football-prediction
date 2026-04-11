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
    
    try:
        conf_str = parts[5]
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

print('置信度>55%的比赛共 %d 场' % len(results))
print()
print('='*130)
print("%-6s %-10s %-28s %-6s %-8s %-8s %-15s %-6s %-6s %-8s %-4s" % ('日期', '编号', '对阵', 'V7预测', '置信度', '胜率差', '8变化', '最终预测', '实际', '比分', '结果'))
print('='*130)

hit = 0
for r in results:
    changes = '[' + str(r['home_8']) + ',' + str(r['draw_8']) + ',' + str(r['away_8']) + ']'
    print("%-6s %-10s %-25s %-6s %-8s %-8s %-15s %-6s %-6s %-8s %-4s" % (
        r['date'], r['num'], r['teams'][:22], r['v7_pred'], r['confidence'], r['diff'],
        changes, r['final_pred'], r['actual'], r['score'], r['result']
    ))
    if r['result'] == '对':
        hit += 1

print('='*130)
if len(results) > 0:
    print("命中: %d/%d (%.1f%%)" % (hit, len(results), hit/len(results)*100))
