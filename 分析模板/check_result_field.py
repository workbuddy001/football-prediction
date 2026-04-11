import json

json_file = "matches_full_2026-03-12.json"
with open(json_file, encoding='utf-8') as f:
    data = json.load(f)

print("第一场比赛的所有字段:")
for k, v in data[0].items():
    print(f"  {k}: {v}")
