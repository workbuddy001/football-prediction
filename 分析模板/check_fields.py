import json

zhuDui = '\u4e3b\u961f'
keDui = '\u5ba2\u961f'
sj = '\u6570\u636e\u5206\u6790'
lj = '\u5386\u53f2\u4ea4\u950b'
zs = '\u4ea4\u6218\u5386\u53f2\u6458\u8981'

with open('d:/work/workbuddy/足球预测/分析模板/matches_full_2026-03-15.json', encoding='utf-8') as f:
    data = json.load(f)

out = []
for m in data:
    s = m.get(sj, {})
    home = m.get(zhuDui, '')
    away = m.get(keDui, '')
    out.append({
        'match': home + ' vs ' + away,
        'his_short': s.get(lj, 'MISSING'),
        'his_full': s.get(zs, '')
    })

with open('d:/work/workbuddy/足球预测/分析模板/verify_out.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print('done')
