#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
连黑熔断引擎 — 2026-05-22
引入零依赖的防爆仓机制:
  4连黑 → 砍60%仓位 (强制偶数)
  6连黑 → 0元虚拟观察盘
自动复活: 命中1场后熔断解开
"""
import json
import os
import datetime

STREAK_FILE = '_streak.json'

def _load_streak():
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
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({
            'results': results[-10:],
            'updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        }, f, ensure_ascii=False, indent=2)

def record_streak(rule, hit, match_info=''):
    """
    手动录入单场结果，更新连黑记录。
    hit=1 命中, 0=黑单
    用法: python _meltdown.py R0 0 '弗拉门戈vs拉普拉塔'
    """
    results = _load_streak()
    results.append({
        'date': datetime.datetime.now().strftime('%m-%d %H:%M'),
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
    for r in results[-5:]:
        emoji = '✅' if r.get('hit') else '❌'
        print(f'  {r.get("date","?")} {emoji} {r.get("rule","?")} {r.get("match","")}')

if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 3:
        rule = sys.argv[1]
        hit = int(sys.argv[2])
        match = sys.argv[3] if len(sys.argv) > 3 else ''
        record_streak(rule, hit, match)
    elif len(sys.argv) == 2 and sys.argv[1] == 'show':
        show_streak()
    else:
        print('用法:')
        print('  python _meltdown.py <规则> <0/1> [比赛]  # 记录结果')
        print('  python _meltdown.py show                # 查看状态')
        print('  例: python _meltdown.py R0 0 \"弗拉门戈vs拉普拉塔\"')
