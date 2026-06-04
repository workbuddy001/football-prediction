#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
连黑熔断引擎 — 2026-05-22 / 2026-06-04 接入埋点数据
引入零依赖的防爆仓机制:
  4连黑 → 砍60%仓位 (强制偶数)
  6连黑 → 0元虚拟观察盘
自动复活: 命中1场后熔断解开
"""
import json
import os
import datetime

STREAK_FILE = '_streak.json'
RULES_LOG = os.path.join(os.path.dirname(__file__), '分析模板', '_rule_trigger_log.json')


def _load_streak():
    """
    加载连黑数据。优先从埋点日志读取（真实投注记录），
    若不存在则回退到旧 _streak.json。
    """
    # 优先从埋点日志读取
    if os.path.exists(RULES_LOG):
        try:
            with open(RULES_LOG, 'r', encoding='utf-8') as f:
                log = json.load(f)
            results = []
            for mid, e in log.items():
                if e.get('action') != 'bet':
                    continue
                if e.get('hit') is None:
                    continue  # 未出比分，不计入连黑
                results.append({
                    'hit': 1 if e['hit'] else 0,
                    'date': (e.get('confirmed_at', '') or '')[:10],
                    'rule': e.get('rule', ''),
                    'match': f"{e.get('match_num','')}{e.get('home_team','')}vs{e.get('away_team','')}",
                })
            # 按日期排序
            results.sort(key=lambda r: r.get('date', ''))
            return results
        except:
            pass

    # 回退到旧文件
    if not os.path.exists(STREAK_FILE):
        return []
    try:
        with open(STREAK_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get('results', [])
    except:
        return []

def _save_streak(results):
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, STREAK_FILE)
    # 按日期排序(升序), 保留最近30场
    sorted_results = sorted(results, key=lambda r: r.get('date', ''))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({
            'results': sorted_results[-30:],
            'updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        }, f, ensure_ascii=False, indent=2)

def record_streak(rule, hit, match_info='', match_date=None):
    """
    手动录入单场结果，更新连黑记录。
    hit=1 命中, 0=黑单 / match_date='2026-05-19' 或 None(用当前日期)
    用法: python _meltdown.py R0 0 '弗拉门戈vs拉普拉塔'
    """
    results = _load_streak()
    date_str = match_date if match_date else datetime.datetime.now().strftime('%m-%d')
    results.append({
        'date': date_str,
        'rule': rule,
        'hit': int(hit),
        'match': match_info,
    })
    _save_streak(results)
    consecutive = 0
    for r in reversed(results):
        if r.get('hit') == 0: consecutive += 1
        else: break
    emoji = '✅' if hit else '❌'
    print(f'[STREAK] {emoji} {rule} {match_info} (累计{len(results)}场, 连黑{consecutive}场)')
    return consecutive

def check_streak(bet_result):
    """
    检查连黑状态, 自动降级。
    返回: modified bet_result
    """
    results = _load_streak()
    if not results:
        return bet_result

    consecutive = 0
    for r in reversed(results):
        if r.get('hit') == 0: consecutive += 1
        else: break

    if consecutive >= 6:
        bet_result['action'] = 'paper_observe'
        bet_result['total_stake'] = 0
        bet_result['rule'] = f"{bet_result.get('rule','')}(熔断:{consecutive}连黑→虚拟盘)"
        print(f'[MELTDOWN-1] 连续{consecutive}场不中→一级熔断, 转虚拟观察盘')

    elif consecutive >= 4:
        ts = bet_result.get('total_stake', 0)
        reduced = max(2, int(ts * 0.4) // 2 * 2)
        bet_result['total_stake'] = reduced
        bet_result['rule'] = f"{bet_result.get('rule','')}(熔断:{consecutive}连黑→{reduced}元)"
        print(f'[MELTDOWN-2] 连续{consecutive}场不中→二级熔断, {ts}→{reduced}元')

    return bet_result

def show_streak():
    """显示当前连黑状态"""
    results = _load_streak()
    if not results:
        print('暂无战绩记录')
        return
    consecutive = 0
    for r in reversed(results):
        if r.get('hit') == 0: consecutive += 1
        else: break
    hits = sum(1 for r in results if r.get('hit') == 1)
    print(f'最近{len(results)}场: {hits}红/{len(results)-hits}黑 | 当前连黑{consecutive}场')
    # 最近10场, 按日期倒序
    display = sorted(results, key=lambda r: r.get('date', ''))[-10:][::-1]
    for r in display:
        emoji = '✅' if r.get('hit') else '❌'
        d = r.get("date", "?")
        ru = r.get("rule", "?")
        ma = r.get("match", "")
        print(f'  {d} {emoji} {ru} {ma}')

def auto_sync_from_scores(scores_file='分析模板/_scores.json'):
    """
    从_scores.json自动同步最近未录入的战绩。
    每天跑predict.py之前调用一次即可。
    """
    if not os.path.exists(scores_file):
        print(f'_scores.json 不存在')
        return
    
    with open(scores_file, 'r', encoding='utf-8') as f:
        scores = json.load(f)
    
    results = _load_streak()
    recorded_matches = {r.get('match','') for r in results}
    new_count = 0
    
    # 只同步最近30天的比赛
    from datetime import timedelta
    cutoff = datetime.datetime.now() - timedelta(days=30)
    
    for k, v in scores.items():
        # 时间过滤
        rt = str(v.get('record_time', ''))
        try:
            md = datetime.datetime.strptime(rt[:10], '%Y-%m-%d')
            if md < cutoff: continue
        except: pass
        hs = v.get('home_score')
        aws = v.get('away_score')
        if hs is None or aws is None:
            continue
        
        # 重建投注结果：需要知道这场比赛触发了哪个规则
        # 通过sporttery_data回查
        mid = v.get('match_id', '')
        h = v.get('home_team', '')
        a = v.get('away_team', '')
        match_name = f'{h}vs{a}'
        
        if match_name in recorded_matches:
            continue  # 已录入
        
        # 读取sporttery_data分析投注
        fp = f'sporttery_data/{mid}.json' if mid else ''
        if not fp or not os.path.exists(fp):
            continue
        
        try:
            # 延迟导入避免循环
            import sys
            sys_mods = list(sys.modules.keys())
            for m in sys_mods:
                if 'v36_analyzer' in m: del sys.modules[m]
            from v36_analyzer import analyze_match
            for m in list(sys.modules.keys()):
                if 'ai_reasoning' in m: del sys.modules[m]
            from ai_reasoning import compute_betting
            from sporttery_web import _build_change_hitrate, _build_odds_hitrate
            
            _oh = _build_odds_hitrate()
            _ch = _build_change_hitrate()
            
            with open(fp, 'r', encoding='utf-8') as f_data:
                data = json.load(f_data)
            data['_odds_hitrate'] = _oh
            data['_change_hitrate'] = _ch
            
            analysis = analyze_match(data)
            bet = compute_betting(data, analysis)
            
            if bet.get('action') != 'bet':
                continue
            
            rule = bet.get('rule', '').split('(')[0]
            gb = bet.get('goal_bet', {})
            goals = gb.get('goals', [])
            actual = hs + aws
            
            is_hit = actual in goals if goals else False
            # 7球+特殊处理: 竞彩7球+=≥7球
            if not is_hit and goals and 7 in goals and actual >= 7:
                is_hit = True
            # 比分投注命中检查
            for sb in bet.get('score_bets', []):
                if sb.get('score') == f'{hs}:{aws}':
                    is_hit = True
                    break
            
            # 用比赛日期而非同步时间
            rt = str(v.get('record_time', ''))
            match_date = rt[:10] if rt else None
            
            record_streak(rule, 1 if is_hit else 0, match_name, match_date=match_date)
            new_count += 1
            
        except Exception as e:
            print(f'  跳过 {match_name}: {e}')
            continue
    
    if new_count == 0:
        print('没有新比赛需要同步')
    else:
        print(f'✅ 自动同步 {new_count} 场战绩')
        show_streak()

if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == 'sync':
        auto_sync_from_scores()
    elif len(sys.argv) == 2 and sys.argv[1] == 'show':
        show_streak()
    elif len(sys.argv) >= 3:
        rule = sys.argv[1]
        hit = int(sys.argv[2])
        match = sys.argv[3] if len(sys.argv) > 3 else ''
        record_streak(rule, hit, match)
    else:
        print('用法:')
        print('  python _meltdown.py sync              # 自动同步最近的战绩')
        print('  python _meltdown.py show              # 查看连黑状态')
        print('  python _meltdown.py <规则> <0/1> [比赛] # 手动录入')
