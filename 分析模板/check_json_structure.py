import json

with open('matches_full_2026-03-16.json', encoding='utf-8') as f:
    data = json.load(f)

print("类型:", type(data))
if isinstance(data, dict):
    print("Keys:", list(data.keys()))
    print("Match count:", len(data.get('matches', [])))
    if data.get('matches'):
        print("First match keys:", list(data['matches'][0].keys()))
        print("First match:", json.dumps(data['matches'][0], ensure_ascii=False, indent=2)[:1000])
else:
    print("List length:", len(data))
    if data:
        print("First item:", json.dumps(data[0], ensure_ascii=False, indent=2)[:1000])
