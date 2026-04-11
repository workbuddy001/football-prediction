import json

with open('d:/work/workbuddy/足球预测/分析模板/matches_full_2026-03-15.json', encoding='utf-8') as f:
    data = json.load(f)

# 找利物浦那场
for m in data:
    if '利物浦' in m.get('主队', ''):
        print(json.dumps(m, ensure_ascii=False, indent=2))
        break
