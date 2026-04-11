import json

with open('d:\\work\\workbuddy\\足球预测\\分析模板\\matches_full_2026-03-15.json', encoding='utf-8') as f:
    d = json.load(f)

m = d[20]  # 利物浦 vs 热刺
print(f"=== {m['编号']} {m['主队']} vs {m['客队']} ===")
print(f"竞彩赔率: {m['竞彩胜平负赔率']}")
print(f"\n欧赔公司数: {len(m['欧赔数据'].get('欧赔列表', []))}")
for c in m['欧赔数据']['欧赔列表'][:8]:
    print(f"  [{c['公司']:10s}] 胜:{c['胜']:5s} 平:{c['平']:5s} 负:{c['负']:5s} 返还率:{c['返还率']}")

print(f"\n数据分析:")
for k, v in m['数据分析'].items():
    if k != '近期交战记录':
        print(f"  {k}: {v}")
print(f"  近期交战(前3条):")
for row in m['数据分析'].get('近期交战记录', [])[:3]:
    print(f"    {row}")
