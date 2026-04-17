import json
f=open('分析模板/matches_full_2026-03-24.json','r',encoding='utf-8')
d=json.load(f)
f.close()
m=d[0]
ep=m.get('欧赔数据',{}).get('欧赔列表',[])
print(f'共 {len(ep)} 家公司')
print()
for e in ep[:10]:
    print(f"{e.get('公司')}: 初盘胜={e.get('初盘胜')} 即时胜={e.get('即时胜')}")
