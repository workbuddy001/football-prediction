#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
黑单残差分析器 — 2026-05-22
每周跑一次: python _residual_report.py
输出: 每条规则的黑单共性、翻车条件、修剪建议
"""
import json, os, sys
from collections import defaultdict

SCORES_FILE = '分析模板/_scores.json'
DATA_DIR = 'sporttery_data'

def run(weekly_only=True):
    """
    weekly_only=True: 仅最近7天（自动化任务）
    weekly_only=False: 全量历史（手动跑）
    """
    # 清缓存
    for m in list(sys.modules):
        if m in ('v36_analyzer', 'ai_reasoning', 'sporttery_web'):
            del sys.modules[m]
    from v36_analyzer import analyze_match
    from ai_reasoning import compute_betting
    import sporttery_web as _sw
    _sw._odds_hitrate_cache = None
    _sw._change_hitrate_cache = None
    from sporttery_web import _build_change_hitrate, _build_odds_hitrate
    _oh = _build_odds_hitrate()
    _ch = _build_change_hitrate()

    with open(SCORES_FILE, 'r', encoding='utf-8') as f:
        scores = json.load(f)

    # 按规则分组黑单
    black_by_rule = defaultdict(list)
    rule_stats = defaultdict(lambda: {'hit': 0, 'miss': 0})
    
    # 新增追踪
    weekly_all = {}  # {rule: {matches, hit, inv, ret, is_hit}}
    had_trap_count = 0
    shadow_count = 0
    protect_total = 0; protect_hit = 0; protect_skipped = 0
    protect_inv = 0; protect_ret = 0

    for k, v in scores.items():
        mid = v.get('match_id', '')
        hs = v.get('home_score')
        aws = v.get('away_score')
        if hs is None or aws is None:
            continue
        rt = str(v.get('record_time', ''))
        if '2026-04' not in rt and '2026-05' not in rt:
            continue
        # 每周报告: 仅分析最近7天的比赛
        if weekly_only:
            from datetime import datetime, timedelta
            try:
                match_date = datetime.strptime(rt[:10], '%Y-%m-%d')
                if match_date < datetime.now() - timedelta(days=7):
                    continue
            except:
                pass
        fp = os.path.join(DATA_DIR, f'{mid}.json')
        if not os.path.exists(fp):
            continue

        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['_odds_hitrate'] = _oh
        data['_change_hitrate'] = _ch

        try:
            analysis = analyze_match(data)
            bet = compute_betting(data, analysis)
        except:
            continue

        if bet.get('action') != 'bet':
            reason = bet.get('reason', '')
            if 'HAD陷阱' in reason:
                had_trap_count += 1
            continue

        rule = bet.get('rule', '').split('(')[0]
        actual = hs + aws
        goals = bet.get('goal_bet', {}).get('goals', [])
        is_hit = actual in goals if goals else False
        # 7球+特殊处理: 竞彩7球+=≥7球
        if not is_hit and goals and 7 in goals and actual >= 7:
            is_hit = True
        for sb in bet.get('score_bets', []):
            if sb.get('score') == f'{hs}:{aws}':
                is_hit = True
                break

        rule_stats[rule]['hit' if is_hit else 'miss'] += 1
        
        # 周报追踪
        full_rule = bet.get('rule', '')
        if '风控减半' in full_rule: shadow_count += 1
        if rule not in weekly_all:
            weekly_all[rule] = {'matches': 0, 'hit': 0, 'inv': 0, 'ret': 0, 'is_hit': False}
        weekly_all[rule]['matches'] += 1
        gb = bet.get('goal_bet', {})
        wk_gstake = gb.get('stake', 0)
        wk_sstake = sum(s.get('stake', 0) for s in bet.get('score_bets', []))
        wk_inv = wk_gstake + wk_sstake
        weekly_all[rule]['inv'] += wk_inv
        # 比分保护统计
        for sb in bet.get('score_bets', []):
            if sb.get('tag') == '比分保护':
                protect_total += 1
                protect_inv += sb.get('stake', 10)
                if sb.get('score') == f'{hs}:{aws}':
                    protect_hit += 1
                    protect_ret += sb.get('stake') * sb.get('odds', 1)
        # 收益
        profit = -wk_gstake
        if goals and actual in goals:
            godds = gb.get('odds', {})
            profit += wk_gstake * godds.get(str(actual), 0)
        for sb in bet.get('score_bets', []):
            profit -= sb.get('stake', 0)
            if sb.get('score') == f'{hs}:{aws}':
                profit += sb.get('stake') * sb.get('odds', 0)
        if profit > -wk_inv:
            weekly_all[rule]['hit'] += 1
            weekly_all[rule]['ret'] += profit + wk_inv
            weekly_all[rule]['is_hit'] = True
        # 同赔跳过计数: 对比比分保护应有的和实际的
        from collections import Counter
        so = data.get('score_odds', {})
        odds_counter = Counter()
        for vv in so.values():
            try: odds_counter[round(float(vv), 1)] += 1
            except: pass
        rec = analysis.get('recommended', {})
        fs = rec.get('filtered_scores', [])
        for g in goals:
            for f in fs:
                if f.get('goals') == g:
                    sc = f.get('score', '')
                    parts = sc.split('-')
                    odds_key = f'{int(parts[0]):02d}:{int(parts[1]):02d}'
                    odds_val = float(so.get(odds_key, 0) or 0)
                    if odds_val > 0 and odds_counter.get(round(odds_val, 1), 0) >= 2:
                        protect_skipped += 1
                    break
            break

        if not is_hit:
            tg = data.get('total_goals', {})
            had = data.get('had', {})
            hhad = data.get('hhad', {})
            hafu = data.get('hafu_change', {})
            pp = hafu.get('平平', {}) if isinstance(hafu, dict) else {}
            step0 = analysis.get('step0', {})
            rec_sum = analysis.get('recent_summary', {})

            black_by_rule[rule].append({
                'match': f"{v.get('home_team','?')}vs{v.get('away_team','?')}",
                'score': f'{hs}:{aws}',
                'actual': actual,
                'date': rt[:10],
                'g0': float(tg.get('0球', 0) or 0),
                'draw': float(had.get('平', 0) or 0),
                'hw': float(had.get('胜', 0) or 0),
                'aw': float(had.get('负', 0) or 0),
                'rs': float(hhad.get('让胜', 0) or 0),
                'rl': float(hhad.get('让负', 0) or 0),
                'pp_pct': float(pp.get('change_pct', 0) or 0),
                'direction': step0.get('direction', ''),
                'h_att': rec_sum.get('h_att', 0),
                'h_def': rec_sum.get('h_def', 0),
                'a_att': rec_sum.get('a_att', 0),
                'a_def': rec_sum.get('a_def', 0),
                'combined': rec_sum.get('combined_avg', 0),
            })

    # 生成报告
    lines = []
    lines.append("=" * 60)
    lines.append(f"  竞彩AI预测系统 — 每周复盘报告")
    lines.append(f"  生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 60)
    lines.append("")
    
    # ===== 本周盈亏总览 =====
    total_inv = sum(hstats['inv'] for _,hstats in weekly_all.items())
    total_ret = sum(hstats['ret'] for _,hstats in weekly_all.items())
    total_trig = len(weekly_all)
    total_hit_count = sum(1 for _,hstats in weekly_all.items() if hstats['is_hit'])
    lines.append(f"【本周盈亏总览】")
    if total_trig > 0:
        roi = (total_ret - total_inv) / total_inv * 100 if total_inv > 0 else 0
        lines.append(f"  触发: {total_trig}场 | 命中: {total_hit_count}场({total_hit_count/total_trig*100:.0f}%)")
        lines.append(f"  投入: {total_inv}元 | 回报: {total_ret:.0f}元 | ROI: {roi:+.1f}%")
    else:
        lines.append(f"  本周无规则触发")
    
    # ===== 拦截器战报 =====
    lines.append(f"\n【拦截器战报】")
    lines.append(f"  HAD陷阱拦截: {had_trap_count}场")
    lines.append(f"  Shadow风控减半: {shadow_count}场")
    
    # ===== 比分保护周报 =====
    lines.append(f"\n【比分保护周报】")
    lines.append(f"  保护投注: {protect_total}次 | 命中: {protect_hit}次({protect_hit/protect_total*100:.0f}%)" if protect_total > 0 else f"  保护投注: 0次")
    lines.append(f"  同赔跳过: {protect_skipped}次 (省{protect_skipped*10}元)")
    if protect_total > 0:
        proi = (protect_ret - protect_inv) / protect_inv * 100 if protect_inv > 0 else 0
        lines.append(f"  保护ROI: {proi:+.0f}%")
    
    lines.append("")
    
    # ===== 本周触发概览 =====
    lines.append(f"【本周触发概览】")
    sorted_weekly = sorted(weekly_all.items(), key=lambda x: x[1]['inv'], reverse=True)
    for rule, wstats in sorted_weekly[:10]:
        rpct = wstats['hit']/wstats['matches']*100 if wstats['matches']>0 else 0
        rroi = (wstats['ret']-wstats['inv'])/wstats['inv']*100 if wstats['inv']>0 else 0
        mark = '⭐红' if rpct >= 60 else ('🟡平' if rpct >= 40 else '🛑黑')
        lines.append(f"  {rule}: {wstats['matches']}场 {rpct:.0f}% ROI{rroi:+.0f}% {mark}")
    if not weekly_all:
        lines.append(f"  无")
    lines.append("")

    for rule in sorted(black_by_rule.keys(), key=lambda r: len(black_by_rule[r]), reverse=True):
        misses = black_by_rule[rule]
        hits = rule_stats[rule]['hit']
        n = len(misses)
        if n < 2:
            continue

        lines.append(f"## 规则 {rule} | {hits}红{n}黑 (命中率{hits/(hits+n)*100:.0f}%)")
        lines.append("")

        # 共性特征
        avg_g0 = sum(m['g0'] for m in misses) / n
        avg_draw = sum(m['draw'] for m in misses) / n
        avg_pp = sum(m['pp_pct'] for m in misses) / n
        avg_comb = sum(m['combined'] for m in misses) / n
        avg_h_att = sum(m['h_att'] for m in misses) / n
        avg_a_def = sum(m['a_def'] for m in misses) / n
        dir_counts = defaultdict(int)
        for m in misses:
            dir_counts[m['direction']] += 1

        lines.append(f"  共性: g0={avg_g0:.1f} draw={avg_draw:.2f} pp_pct={avg_pp:+.1f}%")
        lines.append(f"        近况={avg_comb:.1f} 主攻={avg_h_att:.1f} 客失={avg_a_def:.1f}")
        lines.append(f"        Step0方向: {dict(dir_counts)}")

        # 寻找翻车共性条件
        clues = []
        if avg_g0 > 15:
            clues.append(f"g0偏高({avg_g0:.0f}>15)——可能高估了进球预期")
        if avg_g0 < 9:
            clues.append(f"g0偏低({avg_g0:.0f}<9)——市场过度看小球")
        if abs(avg_pp) > 5:
            clues.append(f"平赔剧烈变化({avg_pp:+.0f}%)——变盘期不稳定")
        if avg_draw < 2.8:
            clues.append(f"平赔偏低({avg_draw:.2f}<2.8)——市场共识太强可能翻车")
        if avg_h_att > 2.5 and avg_a_def > 1.5:
            clues.append(f"双方攻防均强({avg_h_att:.1f}/{avg_a_def:.1f})——可能对攻超出预期")
        if avg_comb < 2.0:
            clues.append(f"近况极低({avg_comb:.1f}<2.0)——铁桶阵有时爆冷")

        if clues:
            lines.append(f"  ⚠️ 翻车共性: {' | '.join(clues)}")
        else:
            lines.append(f"  ⚠️ 无明显共性——属于随机波动（不修改规则）")

        lines.append(f"\n  黑单列表:")
        for m in misses[:5]:
            lines.append(f"    {m['date']} {m['match']} {m['score']}({m['actual']}球) "
                         f"g0={m['g0']:.0f} draw={m['draw']:.2f} dir={m['direction']}")

        lines.append("")
        lines.append("-" * 40)
        lines.append("")

    report = "\n".join(lines)

    # ===== 手动观察项 =====
    watch_items = [
        ('5.23 3:1比分偏见', 
         '30场3:1中V3.6候选含3:1占47%(14/30)但仅2次排第一',
         '当3-1在filtered_scores第2-3位+平赔>3.5+主胜<2.0时, 比分保护可优先选3-1',
         '等样本≥50场后评估落代码'),
        ('5.23 g0≥16→次选策略',
         'g0≥16时首选赔率重复→改选次选2/2=100%命中',
         '等≥5场后确认, 目前样本不足暂不落代码',
         '预计1-2个月后回测验证'),
        ('6.3 CAND030 → 1球候选',
         '条件: 3球赔升10-20% + 7球暴跌20%+ → 1球20元',
         '6场4/6=67% ROI+437%, 但未通过Bonferroni校正, 样本过小',
         '6月前向验证: 仅触发不实投, 等≥5场新触发后做统计再检验'),
        ('6.3 CAND038 → 5球候选',
         '条件: g3[3.0-3.3) + 1球升10-20% → 5球20元',
         '16场7/16=44% ROI+269%, 样本量最大候选中, 但ROI偏低',
         '6月前向验证: 仅触发不实投, 等≥5场新触发后做统计再检验'),
        ('6.13 CAND043 → 世界杯低赔比分',
         '条件: 世界杯/大赛 + 比分赔<5.0 + 该进球数赔率最低 → 投该比分',
         '3场2/3=67%(墨西哥2:0赔4.0x/加拿大1:1赔4.8x/韩国2:1赔7.0x未中)',
         '世界杯前向验证: 等≥10场后评估，联赛815场0触发说明大赛专有'),
    ]
    if watch_items:
        watch_section = []
        watch_section.append("")
        watch_section.append("=" * 60)
        watch_section.append(f"  📌 人工观察项 ({len(watch_items)}条)")
        watch_section.append("=" * 60)
        for title, finding, suggestion, status in watch_items:
            watch_section.append(f"  [{title}]")
            watch_section.append(f"    发现: {finding}")
            watch_section.append(f"    建议: {suggestion}")
            watch_section.append(f"    状态: {status}")
            watch_section.append("")
        lines.append("\n".join(watch_section))
        report = "\n".join(lines)

    # ===== 前向验证追踪: CAND030 & CAND038 =====
    cand030_triggers = []
    cand038_triggers = []
    cand031_triggers = []  # 3:1比分偏见
    cand032_triggers = []  # g0≥16次选策略
    for k, v in scores.items():
        mid = v.get('match_id', '')
        hs = v.get('home_score')
        aws = v.get('away_score')
        if hs is None or aws is None: continue
        rt = str(v.get('record_time', ''))
        if '2026-04' not in rt and '2026-05' not in rt: continue
        if weekly_only:
            from datetime import datetime, timedelta
            try:
                match_date = datetime.strptime(rt[:10], '%Y-%m-%d')
                if match_date < datetime.now() - timedelta(days=7): continue
            except: pass
        fp = os.path.join(DATA_DIR, f'{mid}.json')
        if not os.path.exists(fp): continue
        with open(fp, 'r', encoding='utf-8') as f: data = json.load(f)
        
        # CAND030: 3球升10-20% + 7球暴跌20%+
        try:
            ttg = data.get('ttg_change', {})
            g3_ch = float(ttg.get('3球', {}).get('change_pct', 0) or 0)
            g7_ch = float(ttg.get('7球', {}).get('change_pct', 0) or 0)
            if 10 <= g3_ch < 20 and g7_ch <= -20:
                tg = data.get('total_goals', {})
                g1_odds = float(tg.get('1球', 0) or 0)
                info = data.get('match_info', {})
                home = info.get('home_team', '?') if isinstance(info, dict) else '?'
                away = info.get('away_team', '?') if isinstance(info, dict) else '?'
                profit = (20 * g1_odds - 20) if (hs + aws) == 1 else -20
                cand030_triggers.append({
                    'date': rt[:10], 'team': f'{home}vs{away}',
                    'score': f'{hs}:{aws}', 'tg': hs + aws,
                    'odds': g1_odds, 'profit': profit, 'hit': (hs + aws) == 1
                })
        except: pass
        
        # CAND038: g3[3.0-3.3) + 1球升10-20%
        try:
            tg = data.get('total_goals', {})
            g3 = float(tg.get('3球', 0) or 0)
            ttg = data.get('ttg_change', {})
            g1_ch = float(ttg.get('1球', {}).get('change_pct', 0) or 0)
            if 3.0 <= g3 < 3.3 and 10 <= g1_ch < 20:
                g5_odds = float(tg.get('5球', 0) or 0)
                info = data.get('match_info', {})
                home = info.get('home_team', '?') if isinstance(info, dict) else '?'
                away = info.get('away_team', '?') if isinstance(info, dict) else '?'
                profit = (20 * g5_odds - 20) if (hs + aws) == 5 else -20
                cand038_triggers.append({
                    'date': rt[:10], 'team': f'{home}vs{away}',
                    'score': f'{hs}:{aws}', 'tg': hs + aws,
                    'odds': g5_odds, 'profit': profit, 'hit': (hs + aws) == 5
                })
        except: pass
        
        # CAND031: 3:1比分偏见 — 3-1在filtered_scores第2-3位+平赔>3.5+主胜<2.0
        try:
            a = analyze_match(data)
            fs = a.get('filtered_scores', [])
            scores_31 = [s for i, s in enumerate(fs) if '3-1' in str(s.get('score','')) and i >= 1]
            if scores_31:
                had = data.get('had', {})
                had_w_val = float(had.get('主胜', 0) or 0)
                had_d_val = float(had.get('平局', 0) or 0)
                if had_d_val > 3.5 and had_w_val < 2.0:
                    so = data.get('score_odds', {})
                    odds_31 = float(so.get('03:01', so.get('3:1', 0)) or 0)
                    info = data.get('match_info', {})
                    home = info.get('home_team', '?') if isinstance(info, dict) else '?'
                    away = info.get('away_team', '?') if isinstance(info, dict) else '?'
                    actual = f'{hs}:{aws}'
                    hit = (actual == '3:1')
                    profit = (20 * odds_31 - 20) if hit else -20
                    cand031_triggers.append({
                        'date': rt[:10], 'team': f'{home}vs{away}',
                        'score': actual, 'tg': hs + aws,
                        'odds': odds_31, 'profit': profit, 'hit': hit,
                        'had_d': had_d_val, 'had_w': had_w_val
                    })
        except: pass
        
        # CAND032: g0≥16次选策略
        try:
            tg2 = data.get('total_goals', {})
            g0_val = float(tg2.get('0球', 0) or 0)
            if g0_val >= 16:
                a2 = analyze_match(data)
                sc = a2.get('score_candidates', [])
                if len(sc) >= 2:
                    s0, s1 = sc[0], sc[1]
                    so0 = s0.get('scores', []) if isinstance(s0, dict) else []
                    so1 = s1.get('scores', []) if isinstance(s1, dict) else []
                    if so0 and so1:
                        try: od0 = float(so0[0].get('odds', 99))
                        except: od0 = 99
                        try: od1 = float(so1[0].get('odds', 99))
                        except: od1 = 99
                        if abs(od0 - od1) < 2 and od0 < 20:
                            ss_item = so1[0]
                            ss = ss_item.get('score', '?') if isinstance(ss_item, dict) else str(ss_item)
                            ss_key = ss.replace('-', ':') if '-' in ss else ss
                            parts = ss_key.split(':')
                            ss_key2 = f'{int(parts[0]):02d}:{int(parts[1]):02d}'
                            so = data.get('score_odds', {})
                            ss_odds = float(so.get(ss_key, so.get(ss_key2, 0)) or 0)
                            info = data.get('match_info', {})
                            home = info.get('home_team', '?') if isinstance(info, dict) else '?'
                            away = info.get('away_team', '?') if isinstance(info, dict) else '?'
                            actual = f'{hs}:{aws}'
                            hit = (actual == ss_key)
                            profit = (20 * ss_odds - 20) if hit else -20
                            cand032_triggers.append({
                                'date': rt[:10], 'team': f'{home}vs{away}',
                                'score': actual, 'tg': hs + aws,
                                'second_score': ss, 'odds': ss_odds,
                                'g0': g0_val, 'profit': profit, 'hit': hit
                            })
        except: pass
    
    # CAND042: 0:2观察 (C1盲区补位) — g0[25-35) + had_w[1.5-2.0) → 投0:2比分20元
    cand042_triggers = []
    cand042_cumul_n = 0  # 累计触发
    cand042_cumul_hit = 0
    for k, v in scores.items():
        mid = v.get('match_id', '')
        hs = v.get('home_score')
        aws = v.get('away_score')
        if hs is None or aws is None: continue
        rt = str(v.get('record_time', ''))
        if '2026-04' not in rt and '2026-05' not in rt: continue
        if weekly_only:
            from datetime import datetime, timedelta
            try:
                match_date = datetime.strptime(rt[:10], '%Y-%m-%d')
                if match_date < datetime.now() - timedelta(days=7): continue
            except: pass
        fp = os.path.join(DATA_DIR, f'{mid}.json')
        if not os.path.exists(fp): continue
        with open(fp, 'r', encoding='utf-8') as f: data = json.load(f)
        try:
            tg = data.get('total_goals', {})
            g0 = float(tg.get('0球', 0) or 0)
            had = data.get('had', {})
            had_w = float(had.get('主胜', 0) or 0)
            if 25 <= g0 < 35 and 1.5 <= had_w < 2.0:
                cand042_cumul_n += 1
                so = data.get('score_odds', {})
                k22 = '00:02'
                odds_02 = float(so.get(k22, 0) or 0)
                info = data.get('match_info', {})
                home = info.get('home_team', '?') if isinstance(info, dict) else '?'
                away = info.get('away_team', '?') if isinstance(info, dict) else '?'
                actual = f'{hs}:{aws}'
                hit = (actual == '0:2')
                profit = (20 * odds_02 - 20) if hit else -20
                if hit: cand042_cumul_hit += 1
                if weekly_only:
                    cand042_triggers.append({
                        'date': rt[:10], 'team': f'{home}vs{away}',
                        'score': actual, 'tg': hs + aws,
                        'odds': odds_02, 'profit': profit, 'hit': hit, 'g0': g0, 'had_w': had_w
                    })
        except: pass
    
    # 提前初始化所有cand变量, 避免UnboundLocalError
    cand043_triggers = []
    cand030_triggers = []
    cand038_triggers = []
    cand031_triggers = []
    cand032_triggers = []

    if cand030_triggers or cand038_triggers or cand042_triggers or cand031_triggers or cand032_triggers or cand043_triggers:
        lines.append("")
        lines.append("=" * 60)
        lines.append(f"  🔍 前向验证追踪 (CAND030 & CAND038)")
        lines.append("=" * 60)
    
    if cand030_triggers:
        c30_hit = sum(1 for t in cand030_triggers if t['hit'])
        c30_profit = sum(t['profit'] for t in cand030_triggers)
        c30_n = len(cand030_triggers)
        lines.append(f"  CAND030(3升+7暴跌→1球): 本周触发{c30_n}场 命中{c30_hit}/{c30_n} 盈亏{int(c30_profit):+d}元")
        for t in cand030_triggers:
            lines.append(f"    {t['date']} {t['team']} {t['score']}({t['tg']}球) 1球赔{t['odds']:.1f} {int(t['profit']):+d} {'HIT' if t['hit'] else 'MISS'}")
    
    if cand038_triggers:
        c38_hit = sum(1 for t in cand038_triggers if t['hit'])
        c38_profit = sum(t['profit'] for t in cand038_triggers)
        c38_n = len(cand038_triggers)
        lines.append(f"  CAND038(g3[3.0-3.3)+1球升→5球): 本周触发{c38_n}场 命中{c38_hit}/{c38_n} 盈亏{int(c38_profit):+d}元")
        for t in cand038_triggers:
            lines.append(f"    {t['date']} {t['team']} {t['score']}({t['tg']}球) 5球赔{t['odds']:.1f} {int(t['profit']):+d} {'HIT' if t['hit'] else 'MISS'}")
    
    if not cand030_triggers and not cand038_triggers and not cand042_triggers and not cand031_triggers and not cand032_triggers and not cand043_triggers:
        lines.append("")
        lines.append("  本周无候选规则触发")
    
    # CAND031 显示
    if cand031_triggers:
        lines.append("")
        c31_hit = sum(1 for t in cand031_triggers if t['hit'])
        c31_profit = sum(t['profit'] for t in cand031_triggers)
        c31_n = len(cand031_triggers)
        lines.append(f"  CAND031(3-1偏见): 本周触发{c31_n}场 命中{c31_hit}/{c31_n} 盈亏{int(c31_profit):+d}元")
        for t in cand031_triggers:
            lines.append(f"    {t['date']} {t['team']} {t['score']}({t['tg']}球) 3:1赔{t['odds']:.1f} had_d={t['had_d']:.1f} had_w={t['had_w']:.1f} {int(t['profit']):+d} {'HIT' if t['hit'] else 'MISS'}")
    
    # CAND032 显示
    if cand032_triggers:
        lines.append("")
        c32_hit = sum(1 for t in cand032_triggers if t['hit'])
        c32_profit = sum(t['profit'] for t in cand032_triggers)
        c32_n = len(cand032_triggers)
        lines.append(f"  CAND032(g0≥16次选): 本周触发{c32_n}场 命中{c32_hit}/{c32_n} 盈亏{int(c32_profit):+d}元")
        for t in cand032_triggers:
            lines.append(f"    {t['date']} {t['team']} {t['score']}({t['tg']}球) g0={t['g0']:.0f} 次选={t['second_score']} 赔{t['odds']:.1f} {int(t['profit']):+d} {'HIT' if t['hit'] else 'MISS'}")

    # CAND042 显示
    if cand042_triggers:
        lines.append("")
        c42_hit = sum(1 for t in cand042_triggers if t['hit'])
        c42_profit = sum(t['profit'] for t in cand042_triggers)
        c42_n = len(cand042_triggers)
        cumul_hitrate = f'{cand042_cumul_hit/cand042_cumul_n*100:.0f}%' if cand042_cumul_n > 0 else 'N/A'
        lines.append(f"  CAND042(g0[25-35)+had_w[1.5-2.0)→0:2): 本周触发{c42_n}场 命中{c42_hit}/{c42_n} 盈亏{int(c42_profit):+d}元 | 累计{cand042_cumul_n}场{cand042_cumul_hit}中({cumul_hitrate})")
        for t in cand042_triggers:
            lines.append(f"    {t['date']} {t['team']} {t['score']}({t['tg']}球) g0={t['g0']:.0f} 0:2赔{t['odds']:.1f} {int(t['profit']):+d} {'HIT' if t['hit'] else 'MISS'}")

    # CAND043 世界杯低赔比分追踪
    cand043_triggers = []
    cand043_cumul_n = 0; cand043_cumul_hit = 0
    for k, v in scores.items():
        mid = v.get('match_id', '')
        hs = v.get('home_score'); aws = v.get('away_score')
        if hs is None or aws is None: continue
        rt = str(v.get('record_time', ''))
        if '2026-04' not in rt and '2026-05' not in rt: continue
        if v.get('league', '') not in ('世界杯', '国际赛'): continue
        if weekly_only:
            from datetime import datetime, timedelta
            try:
                match_date = datetime.strptime(rt[:10], '%Y-%m-%d')
                if match_date < datetime.now() - timedelta(days=7): continue
            except: pass
        fp = os.path.join(DATA_DIR, f'{mid}.json')
        if not os.path.exists(fp): continue
        with open(fp, 'r', encoding='utf-8') as f: data = json.load(f)
        try:
            so = data.get('score_odds', {})
            tg = data.get('total_goals', {})
            # 找赔率最低的进球数
            goal_odds = {}
            for gk in ['0球','1球','2球','3球','4球','5球','6球','7球']:
                try: goal_odds[gk] = float(tg.get(gk, 0) or 0)
                except: goal_odds[gk] = 0
            min_goal = min((g for g in goal_odds if goal_odds[g] > 0), key=lambda g: goal_odds[g], default='')
            if not min_goal: continue
            min_goal_num = int(min_goal.replace('球', ''))
            
            # 找<5赔的比分
            best_score = ''
            best_odds = 99
            for sk, sv in so.items():
                try: svf = float(sv)
                except: continue
                if 0 < svf < 5 and svf < best_odds:
                    parts = sk.split(':')
                    try: sc_h, sc_a = int(parts[0]), int(parts[1])
                    except: continue
                    if sc_h + sc_a == min_goal_num:
                        best_score = sk; best_odds = svf
            
            if best_score:
                cand043_cumul_n += 1
                actual = f'{hs}:{aws}'
                info = data.get('match_info', {}) if isinstance(data.get('match_info'), dict) else {}
                home = info.get('home_team', v.get('home_team', '?'))
                away = info.get('away_team', v.get('away_team', '?'))
                # Normalize: score_odds uses '03:00', _scores uses '3:0'
                best_parts = best_score.split(':')
                best_norm = '{}:{}'.format(int(best_parts[0]), int(best_parts[1]))
                hit = (actual == best_norm)
                profit = (20 * best_odds - 20) if hit else -20
                if hit: cand043_cumul_hit += 1
                if weekly_only:
                    cand043_triggers.append({
                        'date': rt[:10], 'team': f'{home}vs{away}',
                        'score': actual, 'tg': hs + aws, 'bet_score': best_score,
                        'odds': best_odds, 'profit': profit, 'hit': hit,
                        'min_goal': min_goal_num
                    })
        except: pass
    
    if cand043_triggers:
        c43_hit = sum(1 for t in cand043_triggers if t['hit'])
        c43_profit = sum(t['profit'] for t in cand043_triggers)
        c43_n = len(cand043_triggers)
        cumul_hitrate = f'{cand043_cumul_hit/cand043_cumul_n*100:.0f}%' if cand043_cumul_n > 0 else 'N/A'
        lines.append(f"  CAND043(大赛低赔比分): 本周触发{c43_n}场 命中{c43_hit}/{c43_n} 盈亏{int(c43_profit):+d}元 | 累计{cand043_cumul_n}场{cand043_cumul_hit}中({cumul_hitrate})")
        for t in cand043_triggers:
            lines.append(f"    {t['date']} {t['team']} {t['score']}({t['tg']}球) 投{t['bet_score'].replace('0','',1).replace(':0',':',1) if t['bet_score'].startswith('0') else t['bet_score']}({t['min_goal']}球最低) 赔{t['odds']:.1f} {int(t['profit']):+d} {'HIT' if t['hit'] else 'MISS'}")

    if not cand030_triggers and not cand038_triggers and not cand043_triggers:
        lines.append("  (本周无触发)")
    total_triggers = sum(s['hit'] + s['miss'] for s in rule_stats.values())
    # 覆盖全量触发数（weekly模式时rule_stats只含本周，需补全）
    all_scores = {}
    with open(SCORES_FILE, 'r', encoding='utf-8') as f:
        all_scores = json.load(f)
    all_trig_count = 0
    for k, v in all_scores.items():
        if v.get('home_score') is not None and v.get('away_score') is not None:
            rt2 = str(v.get('record_time', ''))
            if '2026-04' in rt2 or '2026-05' in rt2:
                mid2 = v.get('match_id', '')
                fp2 = os.path.join(DATA_DIR, f'{mid2}.json')
                if os.path.exists(fp2):
                    all_trig_count += 1  # 简化: 有数据+有比分=潜在触发
    # 实际触发按比例估算（~84/1162=7.2%）
    estimated_triggers = int(all_trig_count * 0.072)
    # 历史回测基准: 4-5月=84场触发
    if estimated_triggers < 84:
        estimated_triggers = 84
    if total_triggers < estimated_triggers:
        total_triggers = estimated_triggers
    
    milestones = [('阶段一: 人工主导', 150, '残差报告+手动补丁',
                    ['数据≥150场触发 ~3-4个月', '人类专家主导,机器协助',
                     '每周残差报告→人工判断→加skip补丁',
                     '编码: 修改ai_reasoning.py的if-elif条件']),
                  ('阶段二: 二级弱盲测', 300, '解锁70/30切分+数据增强',
                    ['数据≥300场触发 ~7个月', '机器初步接入,不完全切分',
                     '数据增强: 赔率微动震荡×50生成合成样本',
                     '编码: 70/30切分→残差挖掘→auto_rules.json']),
                  ('阶段三: 完整自进化', 500, '60/20/20三级盲测',
                    ['数据≥500场触发 ~12个月', '机器全面自进化',
                     '严格60%训练/20%验证/20%盲测钢印切分',
                     '编码: 博费罗尼修正+交叉验证→自动写规则'])]
    
    tracker = []
    tracker.append("")
    tracker.append("=" * 60)
    tracker.append(f"  进化里程碑进度 (累计触发: {total_triggers}场)")
    tracker.append("=" * 60)
    
    for name, target, desc, details in milestones:
        pct = min(100, total_triggers / target * 100)
        bar_len = 20
        filled = int(pct / 100 * bar_len)
        bar = '█' * filled + '░' * (bar_len - filled)
        status = '✅ 已解锁' if total_triggers >= target else f'还需 {target - total_triggers} 场'
        tracker.append(f"  {name:<16} [{bar}] {pct:3.0f}%")
        tracker.append(f"    ╰ {desc} | {status}")
        for d in details:
            tracker.append(f"       · {d}")
    
    tracker.append("")
    # 预计解锁时间（按~42场/月计算）
    monthly_rate = max(1, total_triggers // 2)
    for name, target, desc, details in milestones:
        if total_triggers < target:
            months = (target - total_triggers) / monthly_rate
            tracker.append(f"    预计{name}解锁: {months:.0f}个月后")
            break
    
    lines.append("\n".join(tracker))
    report = "\n".join(lines)

    # 保存
    out_file = 'residual_blind_spot_report.txt'
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(report)
    print(f"\n✅ 报告已保存至: {out_file}")
    print(f"📊 可复制内容投喂给大模型做深度复盘")

    # 可选: 自动投喂LLM (需设置环境变量 DEEPSEEK_KEY)
    api_key = os.environ.get('DEEPSEEK_KEY', '')
    if api_key:
        print("\n🤖 检测到DEEPSEEK_KEY, 自动投喂LLM分析...")
        try:
            import urllib.request
            prompt = f"足彩量化分析师。以下是黑单残差报告。直接给出每条规则翻车原因+改进建议。\n格式:【规则名】原因:xxx|建议:yyy\n\n{report[:6000]}"
            req = urllib.request.Request(
                'https://api.deepseek.com/v1/chat/completions',
                data=json.dumps({
                    'model': 'deepseek-chat',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 2000
                }).encode(),
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                suggestions = result['choices'][0]['message']['content']
                print(f"\n{'='*60}\n  LLM深度分析建议\n{'='*60}")
                print(suggestions)
                with open('residual_llm_suggestions.txt', 'w', encoding='utf-8') as f:
                    f.write(suggestions)
                print(f"\n✅ LLM建议已保存至: residual_llm_suggestions.txt")
        except Exception as e:
            print(f"  ⚠️ LLM调用失败: {e}")

if __name__ == '__main__':
    import sys
    weekly = '--full' not in sys.argv
    if not weekly:
        print('🔍 全量历史模式..')
    else:
        print('📅 每周模式(最近7天)...')
    run(weekly_only=weekly)
