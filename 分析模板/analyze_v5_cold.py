# 足球比赛预测分析脚本 V5（冷门预警联动版）
import os
import re
import numpy as np

def extract_odds_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    def safe_regex(pattern, default=''):
        m = re.search(pattern, content)
        return m.group(1).strip() if m else default

    home_team   = safe_regex(r'主队\s*\|\s*(.+)')
    away_team   = safe_regex(r'客队\s*\|\s*(.+)')
    match_time  = safe_regex(r'比赛时间\s*\|\s*(.+)')
    league      = safe_regex(r'赛事\s*\|\s*(.+)')
    home_form   = safe_regex(r'主队近况走势\s*\|\s*(.+)')
    away_form   = safe_regex(r'客队近况走势\s*\|\s*(.+)')
    home_hand   = safe_regex(r'主队盘路走势\s*\|\s*(.+)')
    away_hand   = safe_regex(r'客队盘路走势\s*\|\s*(.+)')
    history     = safe_regex(r'历史交锋\s*\|\s*(.+)')
    macao_tip   = safe_regex(r'澳门推荐\s*\|\s*(.+)')

    def parse_odds(block_name):
        m = re.search(rf'{block_name}\s*=\s*\[(.*?)\]\s*```', content, re.DOTALL)
        if not m:
            return []
        raw = re.sub(r'#.*', '', m.group(1)).replace('\n', '').replace(' ', '')
        try:
            return eval('[' + raw + ']')
        except:
            return []

    initial_odds  = parse_odds('initial_odds')
    realtime_odds = parse_odds('realtime_odds')

    return {
        'home_team': home_team, 'away_team': away_team,
        'match_time': match_time, 'league': league,
        'home_form': home_form, 'away_form': away_form,
        'home_hand': home_hand, 'away_hand': away_hand,
        'history': history, 'macao_tip': macao_tip,
        'initial_odds': initial_odds, 'realtime_odds': realtime_odds,
    }


def count_wdl(form):
    if not form:
        return 0, 0, 0
    w = sum(1 for c in form.upper() if c == 'W')
    d = sum(1 for c in form.upper() if c == 'D')
    l = sum(1 for c in form.upper() if c == 'L')
    return w, d, l


def find_macao_idx(odds_list):
    """找澳门在列表中的索引（第3家，index=2）"""
    if len(odds_list) >= 3:
        return 2
    for i, odds in enumerate(odds_list):
        h, da, a = odds
        if 1.0 <= h <= 1.05 and 8 <= da <= 20 and 15 <= a <= 30:
            return i
    return 0


def analyze_match(data):
    """主分析函数"""
    if not data['initial_odds'] or not data['realtime_odds']:
        return None

    n = len(data['initial_odds'])
    real = data['realtime_odds']

    # 概率
    real_home_prob = [1/o[0]*100 for o in real]
    real_draw_prob = [1/o[1]*100 for o in real]
    real_away_prob = [1/o[2]*100 for o in real]

    avg_home_prob = np.mean(real_home_prob)
    avg_draw_prob = np.mean(real_draw_prob)
    avg_away_prob = np.mean(real_away_prob)

    # 变化百分比
    def pct_chg(i, idx):
        return (data['realtime_odds'][i][idx] - data['initial_odds'][i][idx]) \
               / data['initial_odds'][i][idx] * 100

    home_pct = [pct_chg(i, 0) for i in range(n)]
    draw_pct = [pct_chg(i, 1) for i in range(n)]
    away_pct = [pct_chg(i, 2) for i in range(n)]

    def ratio(chg_list):
        return sum(1 for x in chg_list if x > 0) / n * 100

    home_up = ratio(home_pct); home_down = ratio([x for x in home_pct if x < 0])
    draw_up = ratio(draw_pct); draw_down = ratio([x for x in draw_pct if x < 0])
    away_up = ratio(away_pct); away_down = ratio([x for x in away_pct if x < 0])

    avg_home = np.mean([o[0] for o in real])
    avg_draw = np.mean([o[1] for o in real])
    avg_away = np.mean([o[2] for o in real])

    macao_idx = find_macao_idx(real)
    macao_home, macao_draw, macao_away = real[macao_idx]

    hw, hd, hl = count_wdl(data['home_form'])
    aw, ad, al = count_wdl(data['away_form'])

    macao_tip = data['macao_tip'].upper()
    is_macao_draw = '和' in macao_tip or '平' in macao_tip
    is_macao_home = '主' in macao_tip and '客' not in macao_tip
    is_macao_away = '客' in macao_tip and '客' not in ' '.join(macao_tip.split('客')[1:]) or \
                    ('客' in macao_tip and '主' not in macao_tip and '和' not in macao_tip and '平' not in macao_tip)
    is_macao_away = '客' in macao_tip and '和' not in macao_tip and '平' not in macao_tip

    # ========== 冷门预警系统 ==========
    cold_signals = []
    cold_score = 0  # 0-10

    # 信号1：澳门推荐和局/客队，但算法得出主/客极端方向
    if is_macao_draw:
        if np.mean(home_pct) > 8 and avg_away_prob > 50:
            cold_signals.append(f"①澳门推荐和局，但主队赔率上升{np.mean(home_pct):.1f}%，客胜概率高达{avg_away_prob:.0f}%——方向分歧大")
            cold_score += 3
        if avg_draw_prob > 30 and avg_away_prob > 45:
            cold_signals.append(f"②澳门推荐和局，三项概率分布{avg_home_prob:.0f}%/{avg_draw_prob:.0f}%/{avg_away_prob:.0f}%，冷门空间充足")
            cold_score += 2

    # 信号2：双方近况都差（W<=L or W<=1）
    if hw <= hl and hw <= 1:
        cold_signals.append(f"③主队{hw}胜{hd}平{hl}负，近况极差，冷门温床")
        cold_score += 2
    if aw <= al and aw <= 1:
        cold_signals.append(f"④客队{aw}胜{ad}平{al}负，近况极差，冷门温床")
        cold_score += 2

    # 信号3：主队大热后被大幅看衰（主队赔率急升>10%的公司超过半数，且客队赔率下降）
    if home_up > 50 and np.mean([x for x in home_pct if x > 0]) > 10 and away_down > 30:
        cold_signals.append(f"⑤主队热度骤降：{home_up:.0f}%公司升主赔，客队受保护（{away_down:.0f}%公司降客赔）")
        cold_score += 3

    # 信号4：客队大热但基本面极差（客胜赔率下降，但客队近况W<=L）
    if away_down > 40 and aw <= al:
        cold_signals.append(f"⑥客队赔率下降但近况{aw}胜{al}负，基本面无法支撑大热")
        cold_score += 2

    # 信号5：赔率剧烈震荡（极端升降并存）
    if home_up > 60 and away_up > 30:
        cold_signals.append(f"⑦市场剧烈分歧：{home_up:.0f}%升主赔 + {away_up:.0f}%升客赔，同时存在双向资金")
        cold_score += 2

    # 信号6：主客同时被资金追逐（极端少见，信号强）
    if home_up > 70 and away_up > 70:
        cold_signals.append(f"⑧主客同时被大额资金——比赛热度极高，操控风险极大")
        cold_score += 4

    # 信号7：澳门客胜明显高于初盘（客队被高估）
    macao_init = data['initial_odds'][macao_idx]
    if macao_init[2] < macao_away - 0.10:
        cold_signals.append(f"⑨澳门客胜从{macao_init[2]}升至{macao_away}，客队被市场高估")
        cold_score += 2

    # 信号8：澳门推荐和局 + 主客近况差不大 → 和局高概率
    if is_macao_draw and abs(hw - aw) <= 1 and abs(hl - al) <= 2:
        cold_signals.append(f"⑩澳门推荐和局 + 主客近况接近{hw}vs{aw}，和局共振")
        cold_score += 2

    cold_level = '无' if cold_score == 0 else \
                 '⚠️ 低' if cold_score <= 3 else \
                 '⚠️⚠️ 中' if cold_score <= 6 else \
                 '⚠️⚠️⚠️ 高'

    # ========== 星级计算（冷门预警降级）==========
    def base_stars(prob):
        if prob >= 65: return 5
        elif prob >= 55: return 4
        elif prob >= 45: return 3
        elif prob >= 35: return 2
        else: return 1

    # ========== 推荐生成 ==========
    # 单选推荐（基础算法）
    reason = ''
    choice = ''

    if avg_home < 1.5:
        choice = '主胜'; reason = '强队主场'
    elif avg_away < 1.5:
        choice = '客胜'; reason = '强队客场'
    elif avg_home < 2.0 and hw >= hl:
        choice = '主胜'; reason = '强队主场+近况'
    elif avg_away < 2.0 and aw >= al:
        choice = '客胜'; reason = '强队客场+近况'
    elif np.mean(home_pct) > 15 and home_up > 80:
        choice = '客胜'; reason = '主胜被大幅看衰'
    elif np.mean(away_pct) > 15 and away_up > 70:
        choice = '主胜'; reason = '客胜被大幅看衰'
    elif hw >= 3 and avg_home < 2.5:
        choice = '主胜'; reason = '主队近况好'
    elif aw >= 3 and avg_away < 2.5:
        choice = '客胜'; reason = '客队近况好'
    elif macao_away < avg_away * 0.85:
        choice = '客胜'; reason = '澳门客胜偏低'
    elif macao_home < avg_home * 0.9:
        choice = '主胜'; reason = '澳门主胜偏低'
    elif is_macao_home:
        choice = '主胜'; reason = '澳门推荐主胜'
    elif is_macao_away:
        choice = '客胜'; reason = '澳门推荐客胜'
    elif draw_down > 60 and avg_draw_prob > 35:
        choice = '平局'; reason = '平局防范强'
    elif home_up > 60 and away_down > 40:
        choice = '客胜'; reason = '主胜不稳+客胜受保护'
    else:
        if avg_home_prob >= avg_away_prob + 5:
            choice = '主胜'; reason = '主胜概率最高'
        elif avg_away_prob >= avg_home_prob + 5:
            choice = '客胜'; reason = '客胜概率最高'
        elif avg_home_prob >= avg_draw_prob + 10:
            choice = '主胜'; reason = '主胜概率最高'
        elif avg_away_prob >= avg_draw_prob + 10:
            choice = '客胜'; reason = '客胜概率最高'
        else:
            choice = '主胜' if avg_home_prob >= avg_away_prob else '客胜'
            reason = '概率均衡偏向'

    # ========== 冷门联动：降级 & 双选 ==========
    final_choice = choice
    final_reason = reason
    star = base_stars(
        avg_home_prob if '主' in choice else
        avg_away_prob if '客' in choice else avg_draw_prob
    )
    cold_note = ''
    dual_pick = None  # 双选备选

    if cold_score >= 6:
        # 高危冷门：降1星，强制双选
        star = max(1, star - 1)
        # 判断双选方向
        if choice == '主胜':
            dual_pick = '主胜+平局'
        elif choice == '客胜':
            dual_pick = '主胜+客胜'
        else:
            # 已经是平局，降半星
            star = max(1, star - 1)
            dual_pick = None
        cold_note = f'【冷门高危，降星至{"★"*star}，建议双选{dual_pick}】'

    elif cold_score >= 3:
        # 中危冷门：降半星（取整），给出双选建议
        star = max(1, star - 1)
        if choice == '主胜':
            dual_pick = '主胜+平局'
        elif choice == '客胜':
            dual_pick = '主胜+客胜'
        else:
            dual_pick = '主胜+平局'
        cold_note = f'【冷门预警，降星至{"★"*star}，建议关注{dual_pick}】'

    elif cold_score > 0:
        cold_note = f'【冷门注意({cold_level})，维持{"★"*star}，星级不变】'

    return {
        'home_team': data['home_team'], 'away_team': data['away_team'],
        'league': data['league'], 'macao_tip': data['macao_tip'],
        'home_form': data['home_form'], 'away_form': data['away_form'],
        'home_hand': data['home_hand'], 'away_hand': data['away_hand'],
        'history': data['history'],
        'first_choice': final_choice,
        'dual_pick': dual_pick,
        'reason': final_reason,
        'cold_signals': cold_signals,
        'cold_level': cold_level,
        'cold_score': cold_score,
        'cold_note': cold_note,
        'star': star,
        'real_home_prob': f"{avg_home_prob:.1f}%",
        'real_draw_prob': f"{avg_draw_prob:.1f}%",
        'real_away_prob': f"{avg_away_prob:.1f}%",
        'avg_home': f"{avg_home:.2f}",
        'avg_draw': f"{avg_draw:.2f}",
        'avg_away': f"{avg_away:.2f}",
        'home_up_pct': f"{home_up:.0f}%",
        'draw_down_pct': f"{draw_down:.0f}%",
        'away_down_pct': f"{away_down:.0f}%",
        'macao_realtime': f"{macao_home:.2f}/{macao_draw:.2f}/{macao_away:.2f}",
    }


def format_result(r, filename=''):
    stars = "★" * r['star']
    dual_line = f"\n  🔀 双选建议: {r['dual_pick']}" if r['dual_pick'] else ""
    cold_line = ""
    if r['cold_signals']:
        cold_line = "\n  冷门预警:" + "".join([f"\n    {s}" for s in r['cold_signals']])

    return (
        f"\n{'='*60}\n"
        f"{filename or r['home_team']+' vs '+r['away_team']}\n"
        f"{'='*60}\n"
        f"  赛事: {r['league']}  |  澳门推荐: {r['macao_tip']}\n"
        f"  近况: 主队 {r['home_form']}({count_wdl(r['home_form'])[0]}胜)  客队 {r['away_form']}({count_wdl(r['away_form'])[0]}胜)\n"
        f"  盘路: 主队 {r['home_hand']}  客队 {r['away_hand']}\n"
        f"  交锋: {r['history']}\n"
        f"  概率: 主{r['real_home_prob']}  平{r['real_draw_prob']}  客{r['real_away_prob']}\n"
        f"  均值: 主{r['avg_home']}  平{r['avg_draw']}  客{r['avg_away']}\n"
        f"  澳门: {r['macao_realtime']}\n"
        f"  变化: 主升{r['home_up_pct']}公司  平降{r['draw_down_pct']}公司  客降{r['away_down_pct']}公司\n"
        f"  ── 投注建议 ──\n"
        f"  信心: {stars} {r['cold_level']}级\n"
        f"  推荐: {r['first_choice']}  ({r['reason']}){dual_line}\n"
        f"  {r['cold_note']}"
        f"{cold_line}"
    )


def analyze_folder(folder_path):
    files = [f for f in os.listdir(folder_path) if f.endswith('_源数据.md')]
    results = []
    for f in sorted(files):
        filepath = os.path.join(folder_path, f)
        try:
            data = extract_odds_from_file(filepath)
            result = analyze_match(data)
            if result:
                result['filename'] = f.replace('_源数据.md', '')
                results.append(result)
                print(format_result(result, result['filename']))
        except Exception as e:
            print(f"❌ Error: {f} - {e}")
    return results


if __name__ == '__main__':
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else r"d:\work\workbuddy\足球预测\分析模板\4.10"
    print(f"\n{'='*60}")
    print(f"  足球赔率分析 V5 — 冷门预警联动版")
    print(f"  分析目录: {folder}")
    print(f"{'='*60}")
    results = analyze_folder(folder)
    print(f"\n共分析 {len(results)} 场比赛")
