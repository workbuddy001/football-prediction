import json
data = json.load(open(r'd:\work\workbuddy\足球预测\分析模板\matches_full_2026-03-15.json', encoding='utf-8'))
lfc = next(m for m in data if '利物浦' in m.get('主队',''))
shuju = lfc.get('数据分析', {})

keys = ['主队近况走势','主队盘路走势','客队近况走势','客队盘路走势','澳门推荐','澳门分析']
out = {k: shuju.get(k, '【未找到】') for k in keys}
with open(r'd:\work\workbuddy\足球预测\分析模板\verify_out.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print('done')
