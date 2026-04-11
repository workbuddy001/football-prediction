import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from 赔率分析工具 import analyze_match, generate_report

# ── 读取 JSON ──────────────────────────────────────────────────
with open('d:/work/workbuddy/足球预测/分析模板/matches_full_2026-03-15.json', encoding='utf-8') as f:
    data = json.load(f)

match = None
for m in data:
    if '利物浦' in m.get('主队', '') or '利物浦' in m.get('客队', ''):
        match = m
        break

if not match:
    print("未找到利物浦比赛！")
    sys.exit(1)

# ── 基本信息 ──────────────────────────────────────────────────
home_team   = match['主队']
away_team   = match['客队']
match_time  = match['日期'] + ' ' + match['时间']
league      = match['联赛']
sj          = match.get('数据分析', {})

home_form       = sj.get('主队近况走势', '')
away_form       = sj.get('客队近况走势', '')
home_handicap   = sj.get('主队盘路走势', '')
away_handicap   = sj.get('客队盘路走势', '')
history         = sj.get('历史交锋', sj.get('交战历史摘要', ''))
macao_tip       = sj.get('澳门推荐', '')
macao_analysis  = sj.get('澳门分析', '')

# ── 欧赔数据 ──────────────────────────────────────────────────
odds_list = match.get('欧赔数据', {}).get('欧赔列表', [])

initial_odds  = []
realtime_odds = []
companies     = []

for o in odds_list:
    try:
        io = (float(o['初盘胜']), float(o['初盘平']), float(o['初盘负']))
        ro = (float(o['即时胜']), float(o['即时平']), float(o['即时负']))
        initial_odds.append(io)
        realtime_odds.append(ro)
        companies.append(o['公司'])
    except (KeyError, ValueError):
        continue

print(f"比赛：{home_team} vs {away_team}")
print(f"有效公司数：{len(companies)}")
print(f"主队近况：{home_form}  盘路：{home_handicap}")
print(f"客队近况：{away_form}  盘路：{away_handicap}")
print(f"历史交锋：{history}")
print(f"澳门推荐：{macao_tip}")

# ── 分析 ──────────────────────────────────────────────────────
results = analyze_match(
    home_team, away_team, match_time, league,
    home_form, away_form, home_handicap, away_handicap,
    history, macao_tip,
    initial_odds, realtime_odds, companies
)

# 额外把澳门分析文字存进去，供报告使用
results['macao_analysis'] = macao_analysis

# ── 输出 JSON 供后续使用 ──────────────────────────────────────
with open('d:/work/workbuddy/足球预测/分析模板/verify_out.json', 'w', encoding='utf-8') as f:
    # results 中有些值是基础类型，直接序列化
    out = {k: v for k, v in results.items()}
    json.dump(out, f, ensure_ascii=False, indent=2)

print("\n=== 关键数值 ===")
print(f"初盘均值  主{results['init_home_avg']} 平{results['init_draw_avg']} 客{results['init_away_avg']}")
print(f"即时均值  主{results['real_home_avg']} 平{results['real_draw_avg']} 客{results['real_away_avg']}")
print(f"主胜变化  均{results['home_change_avg']} 升{results['home_up']}家 降{results['home_down']}家")
print(f"平局变化  均{results['draw_change_avg']} 升{results['draw_up']}家 降{results['draw_down']}家")
print(f"客胜变化  均{results['away_change_avg']} 升{results['away_up']}家 降{results['away_down']}家")
print(f"即时概率  主{results['real_home_prob']}% 平{results['real_draw_prob']}% 客{results['real_away_prob']}%")
print(f"澳门即时  主{results['macao_home_now']} 平{results['macao_draw_now']} 客{results['macao_away_now']}")
print("done")
