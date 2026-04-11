"""
batch_predict.py
────────────────
读取 matches_full_2026-03-15.json，对每场比赛调用 analyze_match 得到预测首选，
再与实际赛果对比，输出复盘对照表（Markdown + 控制台）。
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from 赔率分析工具 import analyze_match, predict_result

# ── 实际赛果（从500.com页面核对，格式：主队视角 H/D/A） ──────────────
ACTUAL_RESULTS = {
    "周日001": ("7:0", "H"),   # 日本女 7-0 菲律宾女足
    "周日002": ("1:0", "H"),   # 长崎航海 1-0 福冈黄蜂
    "周日003": ("1:2", "A"),   # 济州SK 1-2 首尔FC
    "周日004": ("1:1", "D"),   # 浦项制铁 1-1 仁川联
    "周日005": ("4:1", "H"),   # 墨胜利 4-1 麦克阿瑟
    "周日006": ("0:2", "A"),   # 特温特 0-2 乌德勒支
    "周日007": ("0:2", "A"),   # 维罗纳 0-2 热那亚
    "周日008": ("2:2", "D"),   # 沙尔克04 2-2 汉诺威96
    "周日009": ("2:1", "H"),   # 马洛卡 2-1 西班牙人
    "周日010": ("2:1", "H"),   # 费耶诺德 2-1 SBV精英
    "周日011": ("3:2", "H"),   # 克里斯蒂 3-2 布兰
    "周日012": ("0:0", "D"),   # 水晶宫 0-0 利兹联
    "周日013": ("0:0", "D"),   # 诺丁汉 0-0 富勒姆
    "周日014": ("3:1", "H"),   # 曼联 3-1 维拉
    "周日015": ("3:1", "H"),   # 比萨 3-1 卡利亚里
    "周日016": ("0:1", "A"),   # 萨索洛 0-1 博洛尼亚
    "周日017": ("0:2", "A"),   # 不来梅 0-2 美因茨
    "周日018": ("5:2", "H"),   # 巴萨 5-2 塞维利亚
    "周日019": ("1:0", "H"),   # 瓦勒伦加 1-0 桑纳菲
    "周日020": ("0:0", "D"),   # 勒阿弗尔 0-0 里昂
    "周日021": ("1:1", "D"),   # 利物浦 1-1 热刺
    "周日022": ("0:1", "A"),   # 弗赖堡 0-1 柏林联合
    "周日023": ("2:1", "H"),   # 科莫 2-1 罗马
    "周日024": ("1:1", "D"),   # 贝蒂斯 1-1 塞尔塔
    "周日025": ("1:0", "H"),   # 斯图加特 1-0 莱红牛
    "周日026": ("1:0", "H"),   # 拉齐奥 1-0 AC米兰
    "周日027": ("3:1", "H"),   # 皇家社会 3-1 奥萨苏纳
    "周日028": ("3:0", "H"),   # 波尔图 3-0 摩雷伦斯
    "周日029": ("6:0", "H"),   # 温哥华 6-0 明尼苏达
}

# ── 读取JSON ──────────────────────────────────────────────────────────
json_path = os.path.join(os.path.dirname(__file__), 'matches_full_2026-03-15.json')
with open(json_path, encoding='utf-8') as f:
    data = json.load(f)

# ── 对每场比赛跑预测 ──────────────────────────────────────────────────
def predict(results):
    """
    从analyze_match返回的results中提取预测首选（H/D/A）。
    逻辑和generate_report保持一致。
    """
    home_up_pct   = float(results['home_pct_up'].replace('%',''))
    draw_down_pct = float(results['draw_pct_down'].replace('%',''))
    away_down_pct = float(results['away_pct_down'].replace('%',''))
    draw_prob     = float(results['real_draw_prob_val'])

    macao_draw_now = float(results['macao_draw_now'])
    macao_away_now = float(results['macao_away_now'])
    real_draw_avg  = float(results['real_draw_avg'])
    real_away_avg  = float(results['real_away_avg'])
    macao_tip      = results['macao_tip']

    # 澳门推荐解析
    macao_vote = 'H'
    tip_lower = macao_tip.lower()
    if '和局' in macao_tip or 'draw' in tip_lower:
        macao_vote = 'D'
    elif any(x in macao_tip for x in ['负','客','away']):
        macao_vote = 'A'
    elif '贏' in macao_tip or '赢' in macao_tip or '胜' in macao_tip or 'win' in tip_lower:
        # 判断是主队还是客队
        home = results['home_team']
        away = results['away_team']
        if home in macao_tip:
            macao_vote = 'H'
        elif away in macao_tip:
            macao_vote = 'A'
        else:
            macao_vote = 'H'  # 默认主胜
    
    # 首选逻辑（与generate_report一致）
    if macao_draw_now < real_draw_avg:
        first = 'D'
    elif macao_away_now < real_away_avg:
        first = 'A'
    else:
        first = 'A'

    return first, macao_vote

rows = []
hit_main = 0    # 首选命中
hit_macao = 0   # 澳门推荐命中

for m in data:
    num = m.get('编号', '')
    home = m.get('主队', '')
    away = m.get('客队', '')
    sj   = m.get('数据分析', {})

    odds_list = m.get('欧赔数据', {}).get('欧赔列表', [])
    initial_odds, realtime_odds, companies = [], [], []
    for o in odds_list:
        try:
            io = (float(o['初盘胜']), float(o['初盘平']), float(o['初盘负']))
            ro = (float(o['即时胜']), float(o['即时平']), float(o['即时负']))
            initial_odds.append(io)
            realtime_odds.append(ro)
            companies.append(o['公司'])
        except (KeyError, ValueError):
            continue

    if len(initial_odds) < 5:
        rows.append({
            'num': num, 'home': home, 'away': away,
            'pred': '数据不足', 'macao': '-',
            'actual_score': '-', 'actual': '-',
            'hit_main': '-', 'hit_macao': '-',
            'real_home_avg': '-', 'real_draw_avg': '-', 'real_away_avg': '-',
            'draw_pct': '-', 'home_down': '-',
        })
        continue

    res = analyze_match(
        home, away,
        m.get('日期','') + ' ' + m.get('时间',''),
        m.get('联赛',''),
        sj.get('主队近况走势',''), sj.get('客队近况走势',''),
        sj.get('主队盘路走势',''), sj.get('客队盘路走势',''),
        sj.get('历史交锋', sj.get('交战历史摘要','')),
        sj.get('澳门推荐',''),
        initial_odds, realtime_odds, companies
    )

    pred_label, macao_vote = predict(res)
    actual_score, actual_hda = ACTUAL_RESULTS.get(num, ('-', '-'))

    label_map = {'H': '主胜', 'D': '平局', 'A': '客胜'}
    h_main  = 'OK' if pred_label  == actual_hda else 'NO'
    h_macao = 'OK' if macao_vote  == actual_hda else 'NO'

    if pred_label  == actual_hda: hit_main  += 1
    if macao_vote  == actual_hda: hit_macao += 1

    rows.append({
        'num': num,
        'home': home, 'away': away,
        'pred': label_map.get(pred_label, pred_label),
        'macao': sj.get('澳门推荐',''),
        'macao_vote': label_map.get(macao_vote, macao_vote),
        'actual_score': actual_score,
        'actual': label_map.get(actual_hda, actual_hda),
        'hit_main': h_main,
        'hit_macao': h_macao,
        # 额外数据，供复盘分析
        'real_home_avg': res['real_home_avg'],
        'real_draw_avg': res['real_draw_avg'],
        'real_away_avg': res['real_away_avg'],
        'draw_pct': res['draw_pct_avg'],
        'home_down': res['home_down'],
        'away_down': res['away_down'],
        'macao_tip_raw': sj.get('澳门推荐',''),
    })

total = len([r for r in rows if r['hit_main'] != '-'])

# ── 控制台输出 ─────────────────────────────────────────────────────────
print(f"\n{'='*90}")
print(f"{'编号':<10} {'主队':<12} {'客队':<12} {'工具预测':<8} {'澳门推荐':<8} {'实际':<6} {'比分':<8} {'工具':<4} {'澳门':<4}")
print(f"{'-'*90}")
for r in rows:
    macao_show = r.get('macao_vote', r['macao'])
    print(f"{r['num']:<10} {r['home']:<12} {r['away']:<12} {r['pred']:<8} {macao_show:<8} {r['actual']:<6} {r['actual_score']:<8} {r['hit_main']:<4} {r['hit_macao']:<4}")

print(f"{'='*90}")
print(f"工具预测命中: {hit_main}/{total} = {hit_main/total*100:.1f}%")
print(f"澳门推荐命中: {hit_macao}/{total} = {hit_macao/total*100:.1f}%")

# ── 输出Markdown复盘报告 ──────────────────────────────────────────────
md_lines = [
    "# 2026-03-15 赛果复盘报告\n",
    f"> 数据来源：500.com | 复盘日期：2026-03-16\n",
    "---\n",
    "## 一、全场预测 vs 实际赛果对照\n",
    "| 编号 | 主队 | 客队 | 工具预测 | 澳门推荐 | 实际结果 | 比分 | 工具 | 澳门 |",
    "|------|------|------|----------|----------|----------|------|------|------|",
]
for r in rows:
    macao_show = r.get('macao_vote', r['macao'])
    md_lines.append(
        f"| {r['num']} | {r['home']} | {r['away']} | {r['pred']} | {macao_show} | {r['actual']} | {r['actual_score']} | {'V' if r['hit_main']=='OK' else 'X'} | {'V' if r['hit_macao']=='OK' else 'X'} |"
    )

md_lines += [
    "",
    f"**工具预测命中率：{hit_main}/{total} = {hit_main/total*100:.1f}%**",
    f"**澳门推荐命中率：{hit_macao}/{total} = {hit_macao/total*100:.1f}%**",
    "",
    "---\n",
    "## 二、失误场次详细分析\n",
    "| 编号 | 主队 | 客队 | 工具预测 | 实际 | 即时赔率(主/平/客) | 平局变化% | 主胜降幅(家) |",
    "|------|------|------|----------|------|-------------------|-----------|------------|",
]
for r in rows:
    if r['hit_main'] == '❌':
        md_lines.append(
            f"| {r['num']} | {r['home']} | {r['away']} | {r['pred']} | {r['actual']} "
            f"| {r['real_home_avg']}/{r['real_draw_avg']}/{r['real_away_avg']} "
            f"| {r['draw_pct']} | {r['home_down']} |"
        )

out_path = os.path.join(os.path.dirname(__file__), '复盘报告_2026-03-15.md')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(md_lines))
print(f"\n复盘报告已生成: {out_path}")
