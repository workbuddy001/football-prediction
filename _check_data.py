import json, glob

scores = json.load(open('分析模板/_scores.json', encoding='utf-8'))

cnt_total = 0
cnt_with_scores = 0
cnt_with_had = 0
cnt_with_recent = 0

for f in sorted(glob.glob('sporttery_data/*.json')):
    try:
        d = json.load(open(f, encoding='utf-8'))
        mid = d.get('match_id', '')
        if not mid: continue
        if mid not in scores: continue
        
        cnt_total += 1
        cnt_with_scores += 1
        
        had = d.get('had', {})
        if had and '主胜' in had:
            cnt_with_had += 1
        
        recent = d.get('preview', {}).get('recent', {})
        if recent and recent.get('home') and recent.get('away'):
            cnt_with_recent += 1
    except:
        pass

print('Total matches with scores:', cnt_total)
print('  + has had data:', cnt_with_had)
print('  + has recent data:', cnt_with_recent)
print('  + has both:', min(cnt_with_had, cnt_with_recent))
