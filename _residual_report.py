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

    # ===== 进化里程碑追踪（从_scores.json统计全量触发） =====
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
