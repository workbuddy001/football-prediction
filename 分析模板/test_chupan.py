import sys, re
sys.path.insert(0, 'd:\\work\\workbuddy\\足球预测\\分析模板')
from fetch_full import parse_ouzhi

# 利物浦 vs 热刺
data = parse_ouzhi('1318974')
print(f"共 {len(data['欧赔列表'])} 家公司")
for c in data['欧赔列表'][:5]:
    print(f"  {c['公司']:<20} 即时: {c['即时胜']:>5}/{c['即时平']:>5}/{c['即时负']:>5}   初盘: {c['初盘胜']:>5}/{c['初盘平']:>5}/{c['初盘负']:>5}   返还率:{c['返还率']}")
