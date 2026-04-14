import json, glob

t = 0
h = 0
hs = []
for f in glob.glob('分析模板/_reviews/*.json'):
    t += 1
    try:
        d = json.load(open(f, 'r', encoding='utf-8'))
        fp = d.get('odds_fingerprint') or {}
        if fp.get('handicap'):
            h += 1
            mid = d.get('match_id', '?')
            df = d.get('date_folder', '?')
            hc = fp['handicap']
            hs.append(f"{mid} | {df} | hc={hc}")
    except Exception as e:
        pass

print(f"Total reviews: {t}")
print(f"With handicap data: {h}")
print()
print("=== Sample with handicap ===")
for x in hs[:20]:
    print(x)
