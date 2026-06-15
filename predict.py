#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立预测脚本 — 不受Flask缓存影响，直接输出投注推荐
用法:
  python predict.py                          # 分析今天所有比赛
  python predict.py 2039856                  # 分析单场
  python predict.py --all                    # 分析所有未赛比赛(不限今天)
"""
import json, os, sys, glob

# 清空所有缓存模块
for m in list(sys.modules):
    if m in ('v36_analyzer', 'ai_reasoning', 'sporttery_web'):
        del sys.modules[m]

# 强制刷缓存
import sporttery_web as _sw
_sw._odds_hitrate_cache = None
_sw._change_hitrate_cache = None

# 自动同步过去战绩（仅处理新增的比赛）
from _meltdown import auto_sync_from_scores
auto_sync_from_scores()
_sw._score_hitrate_cache = None

from v36_analyzer import analyze_match
from ai_reasoning import compute_betting
from _meltdown import check_streak
from sporttery_web import _build_change_hitrate, _build_odds_hitrate, _build_score_hitrate_stats

# 埋点回填
try:
    from _rule_logger import backfill_scores, query_stats, query_summary
    _HAS_LOGGER = True
except:
    _HAS_LOGGER = False

_oh = _build_odds_hitrate()
_ch = _build_change_hitrate()
_build_score_hitrate_stats()

from datetime import datetime as dt, timedelta
from sporttery_api import SportteryAPI

DATA_DIR = 'sporttery_data'

def predict_match(mid, force_fetch=False):
    """预测单场比赛。force_fetch=True时始终从API拉最新数据"""
    fp = os.path.join(DATA_DIR, f'{mid}.json')
    
    if force_fetch or not os.path.exists(fp):
        try:
            api = SportteryAPI()
            api.fetch_and_save(mid)
        except:
            if not os.path.exists(fp):
                return None
    elif os.path.exists(fp):
        # 检查是否缺少score_change字段，有则重抓
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            if 'score_change' not in existing:
                api = SportteryAPI()
                api.fetch_and_save(mid)
        except:
            pass
    
    if not os.path.exists(fp):
        return None
    
    with open(fp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    data['_odds_hitrate'] = _oh
    data['_change_hitrate'] = _ch
    
    try:
        analysis = analyze_match(data)
        bet = compute_betting(data, analysis)
        # 连黑熔断检查
        if bet.get('action') == 'bet':
            bet = check_streak(bet)
    except Exception as e:
        return {'error': str(e)}
    
    mi = data.get('match_info', {}) or {}
    return {
        'match_id': mid,
        'match_num': mi.get('match_num_str', mid),
        'home': mi.get('home_team', '?'),
        'away': mi.get('away_team', '?'),
        'date': mi.get('match_date', ''),
        'time': mi.get('match_time', ''),
        'action': bet.get('action', ''),
        'rule': bet.get('rule', ''),
        'summary': bet.get('summary', ''),
        'total_stake': bet.get('total_stake', 0),
        'goal_bet': bet.get('goal_bet', {}),
        'score_bets': bet.get('score_bets', []),
    }

def print_result(r):
    """格式化输出"""
    print(f"\n{'='*60}")
    print(f"  {r['match_num']} {r['home']} vs {r['away']}")
    print(f"  {r['date']} {r['time']}")
    
    if r.get('error'):
        print(f"  ❌ 错误: {r['error']}")
        return
    
    if r['action'] == 'skip':
        print(f"  💤 无匹配规则")
        return
    
    print(f"  🎯 规则: {r['rule']}")
    print(f"  📋 {r['summary']}")
    
    gb = r['goal_bet']
    if gb and gb.get('goals'):
        stake = gb.get('stake', 0)
        print(f"  ⚽ 总进球: {gb['goals']}球 x{stake}元")
        for gk, odd in gb.get('odds', {}).items():
            print(f"      {gk}球 赔{odd}")
    
    for sb in r.get('score_bets', []):
        print(f"  🎯 比分: {sb['score']} 赔{sb['odds']} x{sb['stake']}元 ({sb.get('tag','')})")
    
    print(f"  💰 总投入: {r['total_stake']}元")

# ===== 主逻辑 =====
if __name__ == '__main__':
    args = sys.argv[1:]

    # ── 回填昨日战绩（埋点数据同步） ──
    if _HAS_LOGGER:
        scores_file = os.path.join(os.path.dirname(__file__), '分析模板', '_scores.json')
        if os.path.exists(scores_file):
            try:
                with open(scores_file, 'r', encoding='utf-8') as f:
                    scores_data = json.load(f)
                n = backfill_scores(scores_data)
                if n > 0:
                    print(f"📥 埋点回填: {n} 场比分已同步\n")
                
                # 汇总已投注战绩
                s = query_summary()
                if s.get('total_bets', 0) > 0:
                    print(f"{'='*60}")
                    print(f"  📊 真实投注战绩（已确认）")
                    print(f"{'='*60}")
                    print(f"  总投注: {s['total_bets']} 场 | 命中: {s['total_hits']} 场 | 命中率: {s['hit_rate']:.1f}%")
                    print(f"  总投入: {s['total_stake']} 元 | 总回报: {s['total_return']:.1f} 元 | ROI: {s['roi']:+.1f}%")
                    
                    # 按规则细分
                    from collections import Counter
                    confirmed = query_stats()
                    rule_counter = Counter(e.get('rule','?') for e in confirmed if e.get('action')=='bet')
                    if rule_counter:
                        print(f"\n  规则分布:")
                        for rule, cnt in rule_counter.most_common():
                            rs = query_summary(rule=rule)
                            print(f"    {rule}: {cnt}场, 命中率{rs.get('hit_rate',0):.0f}%, ROI{rs.get('roi',0):+.0f}%")
                    print()
            except Exception as e:
                print(f"⚠️ 埋点回填异常: {e}\n")
    
    if args and args[0].isdigit():
        # 单场预测 — 强制抓最新数据
        r = predict_match(args[0], force_fetch=True)
        if r:
            print_result(r)
        else:
            print(f"比赛 {args[0]} 无数据")
    
    elif '--all' in args:
        # 所有未赛
        scores_file = os.path.join(os.path.dirname(__file__), '分析模板', '_scores.json')
        try:
            with open(scores_file, 'r') as f:
                scores = json.load(f)
        except:
            scores = {}
        
        files = sorted(glob.glob(os.path.join(DATA_DIR, '20*.json')), reverse=True)
        count = 0
        total_stake = 0
        
        for fp in files:
            mid = os.path.basename(fp).replace('.json', '')
            if mid in scores:
                sr = scores[mid]
                if sr.get('home_score') is not None and isinstance(sr.get('home_score'), (int, float)):
                    continue
            
            r = predict_match(mid)
            if r and r['action'] == 'bet':
                print_result(r)
                count += 1
                total_stake += r['total_stake']
        
        if count == 0:
            print("\n💤 无投注信号")
        else:
            print(f"\n{'='*60}")
            print(f"  📊 共 {count} 场推荐，总投入 {total_stake} 元")
    
    else:
        # 今天比赛
        api = SportteryAPI()
        now = dt.now()
        today = now.strftime('%Y-%m-%d')
        end = (now + timedelta(days=2)).strftime('%Y-%m-%d')
        
        # 今天星期几(中文)
        WEEKDAY_CN = ['周一','周二','周三','周四','周五','周六','周日']
        today_weekday = WEEKDAY_CN[now.weekday()]
        
        print(f"📡 抓取 {today} ~ {end} 比赛数据...")
        list_data = api.get_match_list(today, end)
        
        all_matches = []
        if isinstance(list_data, dict):
            for k, v in list_data.items():
                if isinstance(v, dict):
                    v['_mid'] = k
                    all_matches.append(v)
        
        if not all_matches:
            print("无比赛")
            sys.exit(0)
        
        print(f"共抓取 {len(all_matches)} 场比赛\n")
        
        # 先抓所有数据
        for m in all_matches:
            mid = str(m.get('_mid', ''))
            try:
                api.fetch_and_save(mid)
                print(f"  ✅ {mid}")
            except:
                print(f"  ❌ {mid} 抓取失败")
        
        # 过滤: 只保留今天星期几的比赛(如周二001-周二00x)
        today_matches = [m for m in all_matches 
                         if str(m.get('matchNumStr', '')).startswith(today_weekday)]
        
        if not today_matches:
            print(f"\n💤 今日({today_weekday})无比赛")
            sys.exit(0)
        
        print(f"\n📅 {today_weekday} 共 {len(today_matches)} 场比赛，开始分析...")
        
        # 再分析
        all_results = []
        bet_count = 0
        total_stake = 0
        
        for m in today_matches:
            mid = str(m.get('_mid', ''))
            r = predict_match(mid, force_fetch=False)
            if not r:
                continue
            
            all_results.append(r)
            print_result(r)
            if r['action'] == 'bet':
                bet_count += 1
                total_stake += r['total_stake']
        
        # ===== 总结 =====
        print(f"\n{'='*60}")
        print(f"  📊 {today_weekday} 投注总结")
        print(f"{'='*60}")
        
        bet_results = [r for r in all_results if r['action'] == 'bet']
        skip_count = sum(1 for r in all_results if r['action'] == 'skip')
        
        if not bet_results:
            print(f"  💤 今日({today_weekday})无投注信号（{len(all_results)}场分析，{skip_count}场跳过）")
        else:
            print(f"  {'编号':<10s} {'对阵':<28s} {'规则':<12s} {'投注':<12s} {'金额':>5s}")
            print(f"  {'-'*10} {'-'*28} {'-'*12} {'-'*12} {'-'*5}")
            for r in bet_results:
                gb = r.get('goal_bet', {})
                goals = gb.get('goals', [])
                goal_str = '+'.join(str(g) for g in goals) + '球' if goals else ''
                if r.get('score_bets'):
                    scores = ','.join(sb['score'] for sb in r['score_bets'])
                    goal_str = (goal_str + ' ' + scores).strip()
                print(f"  {r['match_num']:<10s} {r['home']+'vs'+r['away']:<28s} {r['rule']:<12s} {goal_str:<12s} {r['total_stake']:>4d}元")
            print(f"  {'-'*10} {'-'*28} {'-'*12} {'-'*12} {'-'*5}")
            print(f"  {'':>10s} {'':>28s} {'':>12s} {'共'+str(bet_count)+'场':<12s} {total_stake:>4d}元")
        
        # 跳过明细
        skipped = [r for r in all_results if r['action'] == 'skip']
        if skipped:
            print(f"\n  ⏭️ 跳过 {len(skipped)} 场:")
            for r in skipped:
                print(f"     {r['match_num']} {r['home']}vs{r['away']} — 无匹配规则")
