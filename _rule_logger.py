#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
运行时投注埋点模块
记录每次用户确认的投注决策（match_id 去重，每次覆盖），赛后回填比分。
"""

import json
import os
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), '分析模板', '_rule_trigger_log.json')


def _load():
    """加载埋点日志"""
    if not os.path.exists(LOG_FILE):
        return {}
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save(log):
    """保存埋点日志"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


# ── 核心操作 ──

def confirm_bet(match_id, data, betting_result):
    """
    用户确认投注：快照当前分析结果为最终决策。
    同一 match_id 重复确认会覆盖（保留最新的赔率状态）。
    
    Args:
        match_id: str, 比赛ID
        data: dict, sporttery_data/*.json 原始数据
        betting_result: dict, compute_betting() 的返回值
    
    Returns:
        dict, 写入的埋点条目
    """
    log = _load()
    mi = data.get('match_info', {}) or {}
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    entry = {
        'match_id': match_id,
        'match_num': mi.get('match_num_str', ''),
        'league': mi.get('league', ''),
        'home_team': mi.get('home_team', ''),
        'away_team': mi.get('away_team', ''),
        'match_time': mi.get('time', ''),
        'confirmed_at': now,
        'action': betting_result.get('action', 'unknown'),
        'rule': betting_result.get('rule', ''),
        'reason': betting_result.get('reason', ''),
        'goal_bet': betting_result.get('goal_bet', {}),
        'score_bets': betting_result.get('score_bets', []),
        'score_stake': betting_result.get('score_stake', 0),
        'total_stake': betting_result.get('total_stake', 0),
        'summary': betting_result.get('summary', ''),
        'bet_type': betting_result.get('bet_type', ''),
        'pp_boost': betting_result.get('pp_boost', False),
        's7_dual': betting_result.get('s7_dual', False),
        # 赛后回填字段（覆盖时保留已有比分数据）
        'actual_total': log.get(match_id, {}).get('actual_total'),
        'actual_score': log.get(match_id, {}).get('actual_score'),
        'hit': log.get(match_id, {}).get('hit'),
        # 首次确认时间（覆盖时保留）
        'first_confirmed_at': log.get(match_id, {}).get('first_confirmed_at', now),
    }
    log[match_id] = entry
    _save(log)
    return entry


def undo_bet(match_id):
    """
    撤销投注确认。删除埋点记录，比分不受影响（_scores.json 保持不变）。
    重新确认后下次回填会自动补回正确比分。
    """
    log = _load()
    if match_id in log:
        del log[match_id]
        _save(log)
    return True


def is_confirmed(match_id):
    """检查是否已确认投注"""
    log = _load()
    return match_id in log


def get_confirmed(match_id):
    """获取已确认的投注条目"""
    log = _load()
    return log.get(match_id)


def get_all_confirmed():
    """获取所有已确认条目"""
    log = _load()
    return {k: v for k, v in log.items()}


# ── 赛后回填 ──

def backfill_scores(scores_data):
    """
    用 _scores.json 数据回填所有已确认条目的实际比分。
    
    Args:
        scores_data: dict, _scores.json 的内容
    
    Returns:
        int, 回填的条目数
    """
    log = _load()
    updated = 0
    
    for match_id, entry in log.items():
        if entry.get('actual_total') is not None:
            continue  # 已回填，跳过
        
        # 用 match_id 直接匹配
        score_info = scores_data.get(match_id)
        if not score_info or not isinstance(score_info, dict):
            # 尝试 "4.17_周五001" 格式匹配
            for k, v in scores_data.items():
                if isinstance(v, dict) and str(v.get('match_id', '')) == str(match_id):
                    score_info = v
                    break
        
        if not score_info:
            continue
        
        hs = score_info.get('home_score')
        away_s = score_info.get('away_score')
        if hs is None or away_s is None:
            continue
        
        entry['actual_total'] = hs + away_s
        entry['actual_score'] = score_info.get('score_str') or f"{hs}:{away_s}"
        
        # 判断命中
        action = entry.get('action')
        if action == 'bet':
            goals = entry.get('goal_bet', {}).get('goals', [])
            if entry['actual_total'] in goals:
                entry['hit'] = True
            else:
                entry['hit'] = False
        elif action == 'skip':
            entry['hit'] = None  # 跳过的不计入
        
        updated += 1
        log[match_id] = entry
    
    if updated:
        _save(log)
    return updated


# ── 查询 ──

def query_stats(league=None, rule=None, league_group=None, date_from=None, date_to=None):
    """
    查询埋点统计。
    
    Returns:
        list[dict], 匹配的条目列表
    """
    log = _load()
    results = []
    
    for match_id, entry in log.items():
        if league and entry.get('league', '') != league:
            continue
        if rule and entry.get('rule', '') != rule:
            continue
        if date_from and entry.get('confirmed_at', '') < date_from:
            continue
        if date_to and entry.get('confirmed_at', '')[:10] > date_to:
            continue
        results.append(entry)
    
    return results


def query_summary(league=None, rule=None):
    """
    查询汇总统计。
    
    Returns:
        dict: {total_entries, total_hits, hit_rate, roi, ...} 或空dict
    """
    entries = query_stats(league=league, rule=rule)
    bets = [e for e in entries if e.get('action') == 'bet']
    hit_bets = [e for e in bets if e.get('hit') is True]
    
    if not bets:
        return {}
    
    total_stake = sum(e.get('total_stake', 0) for e in bets)
    total_return = 0
    for e in hit_bets:
        goals = e.get('goal_bet', {}).get('goals', [])
        actual = e.get('actual_total')
        odds_map = e.get('goal_bet', {}).get('odds', {})
        if actual is not None and str(actual) in odds_map:
            total_return += odds_map[str(actual)] * (e.get('goal_bet', {}).get('stake', 0) / len(goals) if goals else 0)
        # 比分回报
        for sb in e.get('score_bets', []):
            if sb.get('score') == e.get('actual_score'):
                total_return += sb.get('odds', 0) * sb.get('stake', 0)
    
    roi = (total_return - total_stake) / total_stake * 100 if total_stake > 0 else 0
    
    return {
        'total_entries': len(entries),
        'total_bets': len(bets),
        'total_hits': len(hit_bets),
        'hit_rate': len(hit_bets) / len(bets) * 100 if bets else 0,
        'total_stake': total_stake,
        'total_return': round(total_return, 1),
        'roi': round(roi, 1),
    }
