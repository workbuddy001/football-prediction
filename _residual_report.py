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
            continue

        rule = bet.get('rule', '').split('(')[0]
        actual = hs + aws
        goals = bet.get('goal_bet', {}).get('goals', [])
        is_hit = actual in goals if goals else False
        for sb in bet.get('score_bets', []):
            if sb.get('score') == f'{hs}:{aws}':
                is_hit = True
                break

        rule_stats[rule]['hit' if is_hit else 'miss'] += 1

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
    lines.append(f"  黑单残差盲区报告 ({len(black_by_rule)}条规则有黑单)")
    lines.append("=" * 60)
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
