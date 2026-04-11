import json

with open('d:/work/workbuddy/足球预测/分析模板/matches_full_2026-03-15.json', encoding='utf-8') as f:
    data = json.load(f)

# 找利物浦那场
for m in data:
    if '利物浦' in m.get('主队', ''):
        match = m
        break

print("="*60)
print(f"【{match['编号']}】{match['联赛']}  {match['日期']} {match['时间']}")
print(f"  {match['主队']} vs {match['客队']}  让球：{match['让球']}")
print()

spf = match['竞彩胜平负赔率']
print(f"竞彩胜平负赔率：胜 {spf.get('胜','-')}  平 {spf.get('平','-')}  负 {spf.get('负','-')}")
print()

ana = match['数据分析']
print("【数据分析】")
print(f"  交战历史：{ana.get('交战历史摘要','')}")
print(f"  主队近况：{ana.get('主队近况','')}")
print(f"  客队近况：{ana.get('客队近况','')}")
print()
print("  近期交战记录：")
for r in ana.get('近期交战记录', []):
    print(f"    {r}")
print()

oz = match['欧赔数据']
companies = oz.get('欧赔列表', [])
print(f"【欧赔数据】共 {len(companies)} 家公司")
print(f"  {'公司':<22} {'初盘胜':>6} {'初盘平':>6} {'初盘负':>6}   {'即时胜':>6} {'即时平':>6} {'即时负':>6}   {'返还率':>7}  凯利(胜/平/负)")
print("  " + "-"*100)
for c in companies:
    print(f"  {c['公司']:<22} {c['初盘胜']:>6} {c['初盘平']:>6} {c['初盘负']:>6}   {c['即时胜']:>6} {c['即时平']:>6} {c['即时负']:>6}   {c['返还率']:>7}  {c['凯利胜']}/{c['凯利平']}/{c['凯利负']}")

print()
# 统计变动
up_win = sum(1 for c in companies if c['即时胜'] > c['初盘胜'])
dn_win = sum(1 for c in companies if c['即时胜'] < c['初盘胜'])
nc_win = sum(1 for c in companies if c['即时胜'] == c['初盘胜'])
up_lose = sum(1 for c in companies if c['即时负'] > c['初盘负'])
dn_lose = sum(1 for c in companies if c['即时负'] < c['初盘负'])
print(f"赔率变动统计（{len(companies)}家）：")
print(f"  主胜赔率：上升 {up_win} 家 / 下降 {dn_win} 家 / 不变 {nc_win} 家")
print(f"  客胜赔率：上升 {up_lose} 家 / 下降 {dn_lose} 家 / 不变 {len(companies)-up_lose-dn_lose} 家")
