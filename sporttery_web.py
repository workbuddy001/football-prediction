#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞彩比分预测系统 - 完整版 v2.5.0 (2026-04-24)
"""
VERSION = "2.5.0"
from flask import Flask, jsonify, render_template_string, request
from markupsafe import Markup
import os
import json
import glob
from sporttery_api import SportteryAPI
from predict_3goals import extract_features, predict_3goals, predict_2goals, predict_4goals, predict_big3_vs_small3, calc_recent_form, _extract_recent_matches, get_final_recommendation
from _3goals_stats import StatsEngine

app = Flask(__name__)

# 3球历史统计引擎（延迟加载）
_stats_engine = None

def get_stats_engine():
    global _stats_engine
    if _stats_engine is None:
        _stats_engine = StatsEngine()
        _stats_engine.load()
    return _stats_engine
DATA_DIR = 'sporttery_data'
SCORES_FILE = '分析模板/_scores.json'

# ─────────────────────────────────────────────────────────────
#  比分记录文件读写
# ─────────────────────────────────────────────────────────────
def load_scores():
    """加载所有已记录比分"""
    try:
        with open(SCORES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_score_record(record):
    """保存一条比分记录"""
    scores = load_scores()
    key = record.get('match_id', record.get('key'))
    scores[key] = record
    with open(SCORES_FILE, 'w', encoding='utf-8') as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)

def get_score_record(match_id):
    """获取某比赛的比分记录"""
    scores = load_scores()
    return scores.get(match_id)

# ─────────────────────────────────────────────────────────────
#  相似比赛算法
# ─────────────────────────────────────────────────────────────
def compute_similarity(current_data, past_record, past_data):
    """
    比较两场比赛的相似度：
    - 3球赔率（精确匹配）：必须完全相等才算同维度
    - 让球赔率差异（权重50%）：让球线必须相同，再比较让胜/让平/让负三方向平均
    优先用 past_record 中已存储的赔率（复盘附带），次选用 past_data（从文件加载）
    返回 0-100 的相似度分数，和各维度明细
    """
    score = 0
    details = {}

    # ── 1. 3球赔率（精确匹配）───────────────────────────
    tg_cur = current_data.get('total_goals', {})
    tg_pst = past_record.get('total_goals_odds') or past_data.get('total_goals', {})

    g3_cur = tg_cur.get('3球')
    g3_pst = tg_pst.get('3球')
    details['g3_cur'] = g3_cur
    details['g3_pst'] = g3_pst

    if g3_cur and g3_pst:
        try:
            if float(g3_cur) == float(g3_pst):
                details['g3_exact'] = True
                details['g3_score'] = 100   # 精确相等 → 满分
                score += 100 * 0.5
            else:
                details['g3_exact'] = False
                details['g3_score'] = 0      # 不相等 → 直接返回0，不显示
                return 0, details
        except:
            pass
    elif not g3_cur or not g3_pst:
        # 任一方缺少3球赔率，无法匹配，直接排除
        details['g3_exact'] = None
        return 0, details

    # ── 1.5 0球赔率差异（辅助排序用，不影响相似度过滤）────────
    g0_cur = tg_cur.get('0球')
    g0_pst = tg_pst.get('0球')
    if g0_cur and g0_pst:
        try:
            details['g0_diff'] = round(abs(float(g0_cur) - float(g0_pst)), 2)
        except:
            details['g0_diff'] = None
    else:
        details['g0_diff'] = None

    # ── 2. 让球赔率相似度 ────────────────────────────
    hhad_cur = current_data.get('hhad', {})
    hhad_pst = past_record.get('hhad_odds') or past_data.get('hhad', {})

    # 先比较让球线，必须相同才算可比
    line_cur = str(hhad_cur.get('让球', '')).strip()
    line_pst = str(hhad_pst.get('让球', '')).strip()
    details['line_cur'] = line_cur
    details['line_pst'] = line_pst
    details['line_match'] = (line_cur != '' and line_cur == line_pst)

    if not details['line_match']:
        # 让球线不同，不可比，该维度不记分
        details['hhad_score'] = 0
        details['hhad_diff'] = None
    else:
        # 让球线相同，比较让胜/让平/让负三方向
        hhad_keys = ['让胜', '让平', '让负']
        hhad_valid = [k for k in hhad_keys if hhad_cur.get(k) and hhad_pst.get(k)]
        if hhad_valid:
            diffs = []
            for k in hhad_valid:
                try:
                    diffs.append(abs(float(hhad_cur[k]) - float(hhad_pst[k])) / float(hhad_pst[k]))
                except:
                    pass
            if diffs:
                avg_diff = sum(diffs) / len(diffs)
                details['hhad_diff'] = round(avg_diff * 100, 1)
                if avg_diff < 0.05:    hhad_score = 100
                elif avg_diff < 0.10:  hhad_score = 80
                elif avg_diff < 0.15:  hhad_score = 60
                elif avg_diff < 0.20:  hhad_score = 40
                else:                  hhad_score = 20
                details['hhad_score'] = hhad_score
                score += hhad_score * 0.5

    return round(score, 1), details

# ─────────────────────────────────────────────────────────────────
# 进球数赔率命中率统计（带缓存）
# ─────────────────────────────────────────────────────────────────
_odds_hitrate_cache = None
_pattern_hitrate_cache = None

def _build_odds_hitrate():
    """
    遍历所有有比分的历史记录，计算各进球数在各赔率区间的历史命中率。
    
    统计方法：
    1. 直接从 _scores.json 的 total_goals_odds 读取赔率（无需读sporttery_data）
    2. 按精确赔率值统计：有多少场比赛该进球数赔率=X，其中打出该进球数的比例
    
    返回格式:
      overall[goal] = {total, hits, rate}          # 该进球数全场命中率
      exact[goal][赔率值] = {total, hits, rate}     # 该赔率值的历史命中率
    """
    global _odds_hitrate_cache
    if _odds_hitrate_cache is not None:
        return _odds_hitrate_cache

    scores = load_scores()

    overall = {}   # overall[goal] = [total, hits]
    exact = {}     # exact[goal] = {赔率值: [total, hits]}

    for key, record in scores.items():
        tg = record.get('total_goals')
        if tg is None:
            continue
        tg = int(tg)
        
        # 直接从 _scores.json 读取赔率（已有保存的赔率数据）
        tg_odds = record.get('total_goals_odds', {})
        if not tg_odds:
            continue

        for goal in range(0, 8):
            od_val = tg_odds.get('%d球' % goal)
            if not od_val:
                continue
            try:
                val = round(float(od_val), 2)
            except:
                continue

            # overall
            if goal not in overall:
                overall[goal] = [0, 0]
            overall[goal][0] += 1
            if tg == goal:
                overall[goal][1] += 1

            # exact: 按精确赔率值统计
            if goal not in exact:
                exact[goal] = {}
            if val not in exact[goal]:
                exact[goal][val] = [0, 0]
            exact[goal][val][0] += 1
            if tg == goal:
                exact[goal][val][1] += 1

    # 计算命中率
    def rate(total, hits):
        return round(hits / total * 100, 1) if total > 0 else None

    overall_stats = {g: {'total': v[0], 'hits': v[1], 'rate': rate(v[0], v[1])}
                     for g, v in overall.items() if v[0] > 0}
    
    exact_stats = {}
    for g, val_data in exact.items():
        exact_stats[g] = {
            str(k): {'total': v[0], 'hits': v[1], 'rate': rate(v[0], v[1])}
            for k, v in val_data.items() if v[0] > 0
        }

    _odds_hitrate_cache = {'overall': overall_stats, 'exact': exact_stats}
    return _odds_hitrate_cache

# ────────────────────────────────────────────────────────────
# 规律命中率统计（带缓存）
# ────────────────────────────────────────────────────────────
def _build_pattern_hitrate():
    """
    遍历所有有 big3_signal_type 的历史记录，计算各前置条件的命中率。

    返回格式:
      stats[signal_type] = {total, hits, misses, rate, prediction}
    """
    global _pattern_hitrate_cache
    if _pattern_hitrate_cache is not None:
        return _pattern_hitrate_cache

    scores = load_scores()
    # pattern_stats[signal_type] = [total, hits, prediction]
    pattern_stats = {}

    for key, record in scores.items():
        signal_type = record.get('big3_signal_type')
        prediction = record.get('big3_prediction')
        result = record.get('big3_result')

        if not signal_type or not result or result == 'unknown':
            continue

        if signal_type not in pattern_stats:
            pattern_stats[signal_type] = [0, 0, prediction]

        pattern_stats[signal_type][0] += 1
        if result == 'hit':
            pattern_stats[signal_type][1] += 1

    # 计算命中率
    result = {}
    for signal_type, (total, hits, prediction) in pattern_stats.items():
        result[signal_type] = {
            'total': total,
            'hits': hits,
            'misses': total - hits,
            'rate': round(hits / total * 100, 1) if total > 0 else 0,
            'prediction': prediction
        }

    _pattern_hitrate_cache = result
    return _pattern_hitrate_cache

def get_hitrate_for_odds(goal, odds_val):
    """
    返回指定进球数和赔率对应的命中率信息。
    返回: {'overall_rate': 31.2, 'bucket_rate': 45.0, 'bucket_total': 13, 'color': 'green'}
    """
    stats = _build_odds_hitrate()
    ov = stats['overall'].get(goal, {})
    overall_rate = ov.get('rate')

    bucket_rate = None
    bucket_total = 0
    if odds_val is not None:
        try:
            val = float(odds_val)
            # 找精确匹配bucket
            bk_key = '%.2f~%.2f' % (round(val - 0.25, 2), round(val + 0.25, 2))
            bk_data = stats['bucket'].get(goal, {}).get(bk_key)
            if bk_data:
                bucket_rate = bk_data['rate']
                bucket_total = bk_data['total']
            else:
                # 找最近的bucket
                bk = stats['bucket'].get(goal, {})
                for bk_str, d in bk.items():
                    lo, hi = bk_str.split('~')
                    if float(lo) <= val <= float(hi):
                        bucket_rate = d['rate']
                        bucket_total = d['total']
                        break
        except:
            pass

    # 颜色：bucket_rate > 0 时使用bucket，否则用overall
    ref_rate = bucket_rate if bucket_rate is not None else overall_rate
    if ref_rate is None:
        color = 'gray'
    elif ref_rate >= 35:
        color = 'green'
    elif ref_rate >= 20:
        color = 'yellow'
    else:
        color = 'red'

    return {
        'overall_rate': overall_rate,
        'bucket_rate': bucket_rate,
        'bucket_total': bucket_total,
        'color': color,
    }


# ─────────────────────────────────────────────────────────────────
# 比分赔率命中率统计（新版，基于实际比分赔率区间）
# ─────────────────────────────────────────────────────────────────
_score_hitrate_cache = None

SCORE_ODDS_BUCKETS = [
    (5,   8,   '5-8'),
    (8,   11,  '8-11'),
    (11,  15,  '11-15'),
    (15,  20,  '15-20'),
    (20,  30,  '20-30'),
    (30,  50,  '30-50'),
    (50,  100, '50-100'),
    (100, 9999,'100+'),
]

def _get_score_odds_bucket(odds):
    for lo, hi, label in SCORE_ODDS_BUCKETS:
        if lo <= odds < hi:
            return label
    return '100+'

def _build_score_hitrate_stats():
    """
    遍历所有有比分的历史记录，统计每个 (比分, 赔率区间) 的历史命中率。
    返回格式: {
        'score_bucket': {
            '1:0': {
                '5-8':  {'total': 131, 'hits': 19, 'rate': 14.5},
                '8-11': {'total': 107, 'hits': 5,  'rate': 4.7},
                ...
            },
            '2:1': {...},
        },
        'total_records': 325
    }
    """
    global _score_hitrate_cache
    if _score_hitrate_cache is not None:
        return _score_hitrate_cache

    scores_data = load_scores()
    from collections import defaultdict

    score_bucket = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # [total, hits]
    total_records = 0

    for key, record in scores_data.items():
        mid = record.get('match_id')
        if not mid:
            continue
        hs = record.get('home_score')
        aws = record.get('away_score')
        if hs is None or aws is None:
            continue
        actual_key = '%d:%d' % (int(hs), int(aws))

        fpath = os.path.join(DATA_DIR, '%s.json' % mid)
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            continue
        so = data.get('score_odds', {})
        if not so:
            continue

        total_records += 1
        for score_key, odds_val in so.items():
            try:
                odds_val = float(odds_val)
            except:
                continue
            if odds_val <= 0:
                continue
            parts = score_key.split(':')
            if len(parts) != 2:
                continue
            try:
                norm_key = '%d:%d' % (int(parts[0]), int(parts[1]))
            except:
                continue
            bucket = _get_score_odds_bucket(odds_val)
            score_bucket[norm_key][bucket][0] += 1
            if norm_key == actual_key:
                score_bucket[norm_key][bucket][1] += 1

    # 转换为命中率格式
    result = {}
    for score, buckets in score_bucket.items():
        result[score] = {}
        for bucket, (total, hits) in buckets.items():
            rate = round(hits / total * 100, 1) if total > 0 else 0.0
            result[score][bucket] = {'total': total, 'hits': hits, 'rate': rate}

    _score_hitrate_cache = {'score_bucket': result, 'total_records': total_records}
    return _score_hitrate_cache


def get_score_recommendations_for_match(score_odds, min_rate=9.0, min_sample=5):
    """
    为当前比赛返回历史命中率较高的比分提示。
    根据当前赔率查找对应赔率区间的历史命中率。

    返回: [
        {
            'score': '1:0',
            'odds': 7.5,
            'total_goals': 1,
            'bucket': '5-8',
            'rate': 14.5,
            'total': 131,
            'hits': 19,
            'level': 'high'/'mid'/'normal',
        },
        ...
    ]
    按命中率从高到低排序
    """
    stats = _build_score_hitrate_stats()
    score_bucket = stats.get('score_bucket', {})

    recs = []
    for score_key, odds_val in score_odds.items():
        try:
            odds_val = float(odds_val)
        except:
            continue
        if odds_val <= 0:
            continue
        parts = score_key.split(':')
        if len(parts) != 2:
            continue
        try:
            sh, sa = int(parts[0]), int(parts[1])
        except:
            continue
        norm_key = '%d:%d' % (sh, sa)
        tg = sh + sa
        bucket = _get_score_odds_bucket(odds_val)
        bucket_data = score_bucket.get(norm_key, {}).get(bucket, {})
        total = bucket_data.get('total', 0)
        hits = bucket_data.get('hits', 0)
        rate = bucket_data.get('rate', 0.0)

        if total < min_sample or rate < min_rate:
            continue

        if rate >= 15:
            level = 'high'
        elif rate >= 11:
            level = 'mid'
        else:
            level = 'normal'

        recs.append({
            'score': norm_key,
            'odds': round(odds_val, 2),
            'total_goals': tg,
            'bucket': bucket,
            'rate': rate,
            'total': total,
            'hits': hits,
            'level': level,
        })

    recs.sort(key=lambda x: -x['rate'])
    return recs


def find_similar_matches(current_data, top_n=5):
    """
    在已记录比分的比赛中找相似场次
    只处理有赔率数据的记录（复盘附带 or 有源文件），避免全量遍历。
    """
    scores = load_scores()
    results = []

    # 第一步：预过滤，只保留有赔率数据的记录（无需逐文件I/O）
    candidates = []
    for key, record in scores.items():
        if record.get('match_id') == current_data.get('match_id'):
            continue  # 跳过当前比赛
        if record.get('total_goals_odds') or record.get('hhad_odds'):
            # 已有赔率（复盘附带），无需读文件
            candidates.append((record, None))
        else:
            mid = record.get('match_id', key)
            if not str(mid).isdigit():
                continue  # 旧格式key无赔率文件，跳过
            filepath = os.path.join(DATA_DIR, f'{mid}.json')
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        past_data = json.load(f)
                    candidates.append((record, past_data))
                except:
                    pass

    # 第二步：计算相似度（只处理有数据的候选）
    for record, past_data in candidates:
        sim, details = compute_similarity(current_data, record, past_data or {})
        # 3球必须精确相等（得分=100），否则 g3_score=0 → sim<50，直接过滤
        if sim >= 50:   # 3球精确匹配贡献50，让球贡献0-50
            mid = record.get('match_id', '')
            pd = past_data  # 已有历史源文件数据

            # 若复盘附带但无源文件，尝试读源文件（为获取近况数据）
            if not pd:
                mid = record.get('match_id', key)
                if str(mid).isdigit():
                    fp = os.path.join(DATA_DIR, f'{mid}.json')
                    if os.path.exists(fp):
                        try:
                            with open(fp, 'r', encoding='utf-8') as f:
                                pd = json.load(f)
                        except:
                            pass

            # 赔率来源：复盘附带 > 历史文件
            odds_source = record.get('total_goals_odds') or (pd.get('ttg') or pd.get('total_goals') or {}) if pd else record.get('total_goals_odds', {})
            # 统一格式为 {0: 13.0, 1: 5.2, ...} 方便前端直接用
            odds_normalized = {}
            if isinstance(odds_source, dict):
                for k, v in odds_source.items():
                    try:
                        odds_normalized[int(k.replace('球', ''))] = float(v)
                    except:
                        pass

            # 近况数据：从历史源文件提取
            recent_form = None
            if pd:
                try:
                    rd = _extract_recent_matches(pd)
                    recent_form = calc_recent_form(rd)
                except Exception:
                    pass

            results.append({
                'record': record,
                'similarity': sim,
                'details': details,
                'match_id': mid,
                'home_team': (pd.get('match_info') or {}).get('home_team') or record.get('home_team', '未知'),
                'away_team': (pd.get('match_info') or {}).get('away_team') or record.get('away_team', '未知'),
                'total_goals': record.get('total_goals', record.get('home_score', 0) + record.get('away_score', 0)),
                'goal_odds': odds_normalized,
                'recent_form': recent_form,
                'g0_diff': details.get('g0_diff'),   # 0球赔率与历史的差值，排序用
            })

    # 排序：相似度高的排前；相似度相同时，0球赔率差值小的排前
    results.sort(key=lambda x: (-x['similarity'], x['g0_diff'] if x['g0_diff'] is not None else 9999))
    return results[:top_n]

# 比分预测分析函数
def analyze_match(data):
    """分析比赛，返回预测结果"""
    result = {
        'prediction': '未知',
        'confidence': 0,
        'reason': [],
        'recommended_odds': []
    }
    
    score_odds = data.get('score_odds', {})
    total_goals = data.get('total_goals', {})
    had = data.get('had', {})
    match_info = data.get('match_info', {})
    
    if not score_odds:
        return result
    
    # 1. 找出最低赔率的比分
    valid_scores = {k: v for k, v in score_odds.items() if v and v > 0 and k.count(':') == 1}
    if valid_scores:
        sorted_scores = sorted(valid_scores.items(), key=lambda x: float(x[1]))
        top3 = sorted_scores[:3]
        
        result['recommended_odds'] = [
            {'score': s, 'odds': o} for s, o in top3
        ]
        
        # 分析
        low_odds = float(top3[0][1])
        if low_odds < 5:
            result['confidence'] = 3
            result['reason'].append(f'最低赔率{top3[0][0]}={low_odds}，值得关注')
        elif low_odds < 8:
            result['confidence'] = 2
            result['reason'].append(f'最低赔率{top3[0][0]}={low_odds}')
        else:
            result['confidence'] = 1
            result['reason'].append('赔率较高，需谨慎')
    
    # 2. 分析总进球趋势
    if total_goals:
        valid_goals = {k: v for k, v in total_goals.items() if v and v > 0}
        if valid_goals:
            sorted_goals = sorted(valid_goals.items(), key=lambda x: float(x[1]))
            result['total_goals_prediction'] = sorted_goals[0][0]
            result['reason'].append(f'总进球推荐: {sorted_goals[0][0]}')
    
    # 3. 分析胜平负
    if had:
        valid_had = {k: v for k, v in had.items() if v and float(v) > 0 and k != '更新时间'}
        if valid_had:
            sorted_had = sorted(valid_had.items(), key=lambda x: float(x[1]))
            result['win_draw_lose'] = sorted_had[0][0]
            result['reason'].append(f'胜平负推荐: {sorted_had[0][0]} ({sorted_had[0][1]})')
    
    # 4. 综合判断
    if result['confidence'] >= 2 and result.get('win_draw_lose'):
        result['prediction'] = f"{result['win_draw_lose']}，比分关注 {top3[0][0] if top3 else '未知'}"
    elif result.get('total_goals_prediction'):
        result['prediction'] = f"总进球: {result['total_goals_prediction']}"
    
    return result


# HTML模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>竞彩比分预测系统 v2.5.0</title>
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #fff; min-height: 100vh; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { text-align: center; color: #00d4ff; margin-bottom: 30px; font-size: 28px; }
        .controls { display: flex; gap: 15px; justify-content: center; margin-bottom: 30px; flex-wrap: wrap; }
        .controls input { padding: 12px 20px; border: 2px solid #00d4ff; border-radius: 8px; background: #16213e; color: #fff; font-size: 16px; width: 200px; }
        .controls button { padding: 12px 30px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; transition: all 0.3s; }
        .btn-fetch { background: #00d4ff; color: #1a1a2e; }
        .btn-fetch:hover { background: #00b4d8; }
        .btn-refresh { background: #e94560; color: #fff; }
        .btn-refresh:hover { background: #c73e54; }
        .match-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; }
        .match-card { background: #16213e; border-radius: 12px; padding: 20px; border: 1px solid #0f3460; transition: all 0.3s; }
        .match-card:hover { transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0, 212, 255, 0.2); }
        .prediction-box { background: linear-gradient(135deg, #00d4ff 0%, #00b4d8 100%); border-radius: 10px; padding: 15px; margin: 15px 0; text-align: center; }
        .prediction-title { font-size: 14px; color: #1a1a2e; opacity: 0.8; }
        .prediction-value { font-size: 22px; font-weight: bold; color: #1a1a2e; margin-top: 5px; }
        .confidence { display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 12px; margin-left: 10px; }
        .conf-high { background: #1e5631; color: #fff; }
        .conf-medium { background: #4a4a00; color: #fff; }
        .conf-low { background: #563a3a; color: #fff; }
        .match-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #0f3460; }
        .match-id { color: #e94560; font-weight: bold; }
        .teams { font-size: 20px; font-weight: bold; text-align: center; margin: 15px 0; }
        .vs { color: #888; margin: 0 10px; }
        .odds-section { margin-top: 15px; }
        .odds-title { color: #00d4ff; font-size: 14px; margin-bottom: 10px; font-weight: bold; }
        .odds-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
        .odds-item { background: #0f3460; padding: 10px; border-radius: 6px; text-align: center; }
        .odds-item .label { color: #888; font-size: 12px; }
        .odds-item .value { color: #fff; font-weight: bold; font-size: 16px; margin-top: 5px; }
        .odds-item.low { background: #1e5631; }
        .odds-item.medium { background: #4a4a00; }
        .odds-item.high { background: #563a3a; }
        .odds-item.top { background: #006666; border: 2px solid #00d4ff; }
        .odds-change-tag { font-size: 11px; margin-left: 4px; font-weight: normal; }
        .odds-tags { display: flex; gap: 4px; margin-top: 4px; justify-content: center; }
        .odds-tag { font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: bold; }
        .odds-tag.exclude { background: #dc2626; color: #fff; }
        .odds-tag.focus { background: #16a34a; color: #fff; }
        .odds-tag.gold { background: linear-gradient(135deg, #f59e0b, #fbbf24); color: #000; font-weight: bold; box-shadow: 0 0 8px rgba(251, 191, 36, 0.6); }
        .odds-tag.alert { background: #f97316; color: #fff; font-weight: bold; }
        .odds-item.exclude { border: 2px solid #dc2626; }
        .odds-item.focus { border: 2px solid #16a34a; box-shadow: 0 0 8px rgba(22, 163, 74, 0.5); }
        .odds-item.gold-highlight { border: 2px solid #f59e0b; box-shadow: 0 0 12px rgba(251, 191, 36, 0.7); background: linear-gradient(135deg, rgba(251, 191, 36, 0.1), transparent); }
        .score-odds { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
        .score-odds .odds-item { padding: 8px 4px; }

        /* 赔率变化统计 */
        .change-stats { background: #0a1929; border-radius: 8px; padding: 12px; }
        .change-category { margin-bottom: 12px; }
        .change-category:last-child { margin-bottom: 0; }
        .change-subtitle { color: #ffd700; font-size: 12px; margin-bottom: 8px; font-weight: bold; }
        .change-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 6px; }
        .change-item { background: #0f3460; padding: 8px 6px; border-radius: 6px; text-align: center; }
        .change-item .change-label { color: #888; font-size: 11px; margin-bottom: 4px; }
        .change-item .change-value { font-size: 12px; font-weight: bold; }
        .change-up { border-left: 3px solid #ef4444; }
        .change-up .change-value { color: #ef4444; }
        .change-down { border-left: 3px solid #22c55e; }
        .change-down .change-value { color: #22c55e; }
        .change-neutral { border-left: 3px solid #888; }
        .change-neutral .change-value { color: #888; }

        /* 进球数-比分联动排除列表（保留用于兼容） */
        .exclusion-section { margin-top: 12px; }
        .exclusion-title { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
        .exclusion-hint { font-size: 11px; color: #888; font-weight: normal; margin-left: 4px; }
        .exclusion-list { display: flex; flex-direction: column; gap: 8px; }
        .excl-item { border-radius: 8px; overflow: hidden; border: 1px solid transparent; }
        .excl-strong { border-color: #ef4444; background: rgba(239,68,68,0.08); }
        .excl-normal  { border-color: #f97316; background: rgba(249,115,22,0.08); }
        .excl-weak    { border-color: #eab308; background: rgba(234,179,8,0.08); }
        .excl-header { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: rgba(0,0,0,0.2); flex-wrap: wrap; }
        .excl-level-badge { font-size: 12px; font-weight: bold; color: #fff; }
        .excl-goal { font-size: 15px; font-weight: bold; color: #ffd700; }
        .excl-goal-special { text-decoration: underline wavy #ef4444; }

        /* 比分历史命中率推荐（新） */
        .score-rec-section { margin-top: 12px; }
        .score-rec-title { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
        .score-rec-hint { font-size: 11px; color: #888; font-weight: normal; margin-left: 4px; }
        .score-rec-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
        .score-rec-item { display: flex; flex-direction: column; align-items: center; gap: 2px;
            border-radius: 10px; padding: 8px 14px; border: 1px solid transparent; min-width: 80px; }
        .score-rec-item.level-high { border-color: #22c55e; background: rgba(34,197,94,0.12); }
        .score-rec-item.level-mid  { border-color: #facc15; background: rgba(250,204,21,0.10); }
        .score-rec-item.level-normal { border-color: #60a5fa; background: rgba(96,165,250,0.08); }
        .score-rec-score { font-size: 18px; font-weight: bold; letter-spacing: 1px; }
        .level-high .score-rec-score { color: #4ade80; }
        .level-mid  .score-rec-score { color: #facc15; }
        .level-normal .score-rec-score { color: #93c5fd; }
        .score-rec-odds { font-size: 11px; color: #888; }
        .score-rec-rate { font-size: 12px; font-weight: bold; padding: 1px 6px; border-radius: 6px; }
        .level-high .score-rec-rate { background: rgba(34,197,94,0.2); color: #4ade80; }
        .level-mid  .score-rec-rate { background: rgba(250,204,21,0.2); color: #facc15; }
        .level-normal .score-rec-rate { background: rgba(96,165,250,0.15); color: #93c5fd; }
        .score-rec-sample { font-size: 10px; color: #555; }
        .excl-ttg-odds { font-size: 12px; color: #aaa; margin-left: auto; }
        .excl-body { padding: 8px 12px; }
        .excl-scores-row { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; margin-bottom: 6px; }
        .excl-scores-label { font-size: 11px; color: #888; flex-shrink: 0; }
        .excl-score-badge { padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .excl-score-badge.special { background: #7f1d1d; color: #fca5a5; border: 1px solid #ef4444; }
        .excl-score-badge.normal  { background: #1e3a5f; color: #93c5fd; border: 1px solid #3b82f6; }
        .excl-reason { font-size: 11px; color: #888; line-height: 1.5; margin-top: 4px; }

        .no-data { text-align: center; color: #888; padding: 60px 20px; }
        .no-data h2 { margin-bottom: 20px; }
        .instructions { background: #16213e; border-radius: 10px; padding: 20px; margin-bottom: 30px; text-align: center; }
        .instructions p { color: #888; margin: 5px 0; }
        .instructions .tip { color: #00d4ff; }
        
        /* 前瞻数据标签页 */
        .preview-tabs { display: flex; gap: 5px; margin-top: 15px; border-bottom: 2px solid #0f3460; }
        .preview-tab { padding: 8px 12px; background: #0f3460; border: none; border-radius: 6px 6px 0 0; color: #888; cursor: pointer; font-size: 12px; transition: all 0.2s; }
        .preview-tab:hover { background: #1a4a7a; }
        .preview-tab.active { background: #00d4ff; color: #1a1a2e; font-weight: bold; }
        .preview-content { display: none; padding: 15px 0; }
        .preview-content.active { display: block; }
        
        /* 前瞻数据样式 */
        .preview-section { margin-bottom: 15px; }
        .preview-section-title { color: #00d4ff; font-size: 14px; font-weight: bold; margin-bottom: 10px; padding-bottom: 5px; border-bottom: 1px solid #0f3460; }
        .team-form { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .team-stats { background: #0f3460; padding: 12px; border-radius: 8px; }
        .team-stats h4 { color: #00d4ff; margin-bottom: 8px; font-size: 14px; }
        .form-list { display: flex; gap: 4px; margin-bottom: 8px; }
        .form-item { width: 24px; height: 24px; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: bold; }
        .form-win { background: #1e5631; color: #4ade80; }
        .form-draw { background: #4a4a00; color: #facc15; }
        .form-loss { background: #563a3a; color: #f87171; }
        .stat-row { display: flex; justify-content: space-between; color: #aaa; font-size: 12px; margin: 4px 0; }
        .stat-row span:last-child { color: #fff; }
        
        /* 历史交锋 */
        .history-list { display: flex; flex-direction: column; gap: 10px; }
        .history-item { background: #0f3460; padding: 12px; border-radius: 8px; }
        .history-item .match-info { display: flex; justify-content: space-between; color: #888; font-size: 12px; margin-bottom: 8px; }
        .history-item .score { font-size: 18px; font-weight: bold; text-align: center; margin: 5px 0; }
        .history-item .teams { display: flex; justify-content: space-between; color: #aaa; font-size: 13px; }
        
        /* 伤停列表 */
        .injury-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .injury-team { background: #0f3460; padding: 12px; border-radius: 8px; }
        .injury-team h4 { color: #00d4ff; margin-bottom: 10px; }
        .player-item { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #16213e; font-size: 12px; }
        .player-item:last-child { border-bottom: none; }
        .player-name { color: #fff; }
        .player-pos { color: #888; }
        .player-status { padding: 2px 6px; border-radius: 4px; font-size: 10px; }
        .status-injury { background: #563a3a; color: #f87171; }
        .status-suspend { background: #4a4a00; color: #facc15; }
        
        /* 射手榜 */
        .scorer-list { display: flex; flex-direction: column; gap: 8px; }
        .scorer-item { display: flex; align-items: center; gap: 10px; background: #0f3460; padding: 8px 12px; border-radius: 6px; }
        .scorer-rank { width: 20px; height: 20px; background: #00d4ff; color: #1a1a2e; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: bold; }
        .scorer-name { flex: 1; color: #fff; font-size: 13px; }
        .scorer-goals { color: #4ade80; font-weight: bold; font-size: 14px; }
        .scorer-ratio { color: #888; font-size: 11px; }
        
        /* 积分榜 */
        .standing-table { width: 100%; border-collapse: collapse; font-size: 12px; }
        .standing-table th { background: #0f3460; color: #00d4ff; padding: 8px 4px; text-align: center; }
        .standing-table td { padding: 8px 4px; text-align: center; color: #aaa; border-bottom: 1px solid #16213e; }
        .standing-table tr:first-child td { color: #4ade80; font-weight: bold; }

        /* 3球预测 */
        .g3-prediction-box { background: linear-gradient(135deg, #1a1a3e 0%, #16213e 100%); border-radius: 10px; padding: 15px; margin: 10px 0; border: 1px solid #0f3460; }
        .g3-prediction-box.golden-box { background: linear-gradient(135deg, #2d1f00 0%, #1a1200 100%); border: 1px solid #b8860b; box-shadow: 0 0 12px rgba(255,215,0,0.15); }

        /* 最终推荐样式 - 基于最严谨的方法 */
        .final-rec-box { background: linear-gradient(135deg, #1a1a2e 0%, #0d0d1a 100%); border-radius: 10px; padding: 15px; margin: 10px 0; }
        .final-rec-bet { border: 2px solid #22c55e; box-shadow: 0 0 15px rgba(34,197,94,0.2); }
        .final-rec-no-bet { border: 2px solid #ef4444; box-shadow: 0 0 15px rgba(239,68,68,0.2); }
        .final-rec-watch { border: 2px solid #f59e0b; box-shadow: 0 0 15px rgba(245,158,11,0.2); }
        .final-rec-title { font-size: 15px; font-weight: bold; margin-bottom: 10px; display: flex; align-items: center; gap: 10px; }
        .final-rec-bet .final-rec-title { color: #22c55e; }
        .final-rec-no-bet .final-rec-title { color: #ef4444; }
        .final-rec-watch .final-rec-title { color: #f59e0b; }
        .signal-type-tag { font-size: 11px; background: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 10px; color: #fff; }
        .final-rec-content { background: rgba(0,0,0,0.3); border-radius: 8px; padding: 12px; }
        .final-rec-main { font-size: 20px; margin-bottom: 8px; }
        .final-rec-main strong { font-size: 24px; }
        .final-rec-bet .final-rec-main { color: #4ade80; }
        .final-rec-bet .final-rec-main strong { color: #22c55e; }
        .final-rec-no-bet .final-rec-main { color: #f87171; }
        .final-rec-no-bet .final-rec-main strong { color: #ef4444; }
        .final-rec-watch .final-rec-main { color: #fbbf24; }
        .final-rec-watch .final-rec-main strong { color: #f59e0b; }
        .final-rec-reason { font-size: 12px; color: #94a3b8; margin-bottom: 8px; line-height: 1.5; }
        .final-rec-stats { font-size: 13px; margin-bottom: 6px; }
        .final-rec-confidence { font-size: 12px; color: #64748b; }
        .hit-rate-high { color: #22c55e; font-weight: bold; }
        .hit-rate-mid { color: #f59e0b; font-weight: bold; }
        .hit-rate-low { color: #ef4444; font-weight: bold; }

        /* 大球规则强信号提示 */
        .big-ball-rule-alert {
            background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
            border-radius: 10px;
            padding: 12px 16px;
            margin: 10px 0;
            animation: pulse-red 2s ease-in-out infinite;
            border: 2px solid #fca5a5;
        }
        @keyframes pulse-red {
            0%, 100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.4); }
            50% { box-shadow: 0 0 20px 5px rgba(220, 38, 38, 0.6); }
        }
        .big-ball-rule-alert .alert-title {
            font-size: 14px;
            font-weight: bold;
            color: #fff;
            margin-bottom: 8px;
        }
        .big-ball-rule-alert .alert-detail {
            font-size: 12px;
            color: #fecaca;
            line-height: 1.5;
        }

        /* 大3球 vs 小3球 预判 */
        .big3-small3-box { background: linear-gradient(135deg, #1a1a2e 0%, #0d0d1a 100%); border-radius: 10px; padding: 12px; margin: 10px 0; }
        .big3-box { border: 1px solid #22c55e; }
        .small3-box { border: 1px solid #f59e0b; }
        .big3-small3-title { font-size: 14px; font-weight: bold; margin-bottom: 10px; display: flex; align-items: center; gap: 10px; }
        .big3-box .big3-small3-title { color: #22c55e; }
        .small3-box .big3-small3-title { color: #f59e0b; }
        .big3-confidence { font-size: 11px; background: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 10px; color: #fff; }
        .big3-small3-content { background: rgba(0,0,0,0.3); border-radius: 8px; padding: 10px; }
        .big3-prob-bar, .small3-prob-bar { margin-bottom: 8px; }
        .prob-label { font-size: 12px; color: #94a3b8; margin-bottom: 4px; }
        .prob-bar { height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden; }
        .prob-fill { height: 100%; border-radius: 4px; transition: width 0.3s ease; }
        .big3-fill { background: linear-gradient(90deg, #22c55e, #4ade80); }
        .small3-fill { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
        .big3-factors { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
        .factor-tag { font-size: 10px; background: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 10px; color: #94a3b8; }
        /* 2026-04-24 新规律高亮样式 */
        .factor-tag-new {
            font-size: 13px !important;
            font-weight: bold;
            background: linear-gradient(135deg, rgba(251,191,36,0.25), rgba(251,191,36,0.1));
            border: 1.5px solid #f59e0b;
            color: #fbbf24;
            padding: 4px 12px;
            border-radius: 12px;
            animation: pulse-glow 2s ease-in-out infinite;
            box-shadow: 0 0 8px rgba(251,191,36,0.3);
        }
        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 0 8px rgba(251,191,36,0.3); }
            50% { box-shadow: 0 0 16px rgba(251,191,36,0.6); }
        }

        /* 黄金2球/4球样式 */
        .golden-2-box { background: linear-gradient(135deg, #1a2a1a 0%, #0d1a0d 100%); border: 1px solid #22c55e; border-radius: 8px; padding: 10px; margin: 6px 0; }
        .golden-4-box { background: linear-gradient(135deg, #1a1a2a 0%, #0d0d1a 100%); border: 1px solid #6366f1; border-radius: 8px; padding: 10px; margin: 6px 0; }
        .golden-recommendation { font-size: 14px; font-weight: bold; margin-bottom: 6px; }
        .golden-2-box .golden-recommendation { color: #22c55e; }
        .golden-4-box .golden-recommendation { color: #818cf8; }
        .golden-stats { font-size: 12px; margin-top: 6px; }
        .hit-rate-high { color: #22c55e; font-weight: bold; }
        .golden-2-box .golden-reason { font-size: 11px; color: #4ade80; background: rgba(34,197,94,0.08); border-left: 3px solid #22c55e; padding: 5px 8px; border-radius: 0 6px 6px 0; }
        .golden-4-box .golden-reason { font-size: 11px; color: #818cf8; background: rgba(99,102,241,0.08); border-left: 3px solid #6366f1; padding: 5px 8px; border-radius: 0 6px 6px 0; }

        /* 信心指数徽章 */
        .confidence-badge { padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: bold; }
        .confidence-high { background: #27ae60; color: #fff; }
        .confidence-mid { background: #f39c12; color: #fff; }
        .confidence-low { background: #e74c3c; color: #fff; }
        .golden-badge { background: linear-gradient(90deg, #b8860b, #ffd700); color: #000; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 10px; margin-left: 8px; }
        .golden-reason { font-size: 11px; color: #f1c40f; background: rgba(241,196,15,0.08); border-left: 3px solid #f1c40f; padding: 6px 10px; border-radius: 0 6px 6px 0; margin: 4px 0 8px; }
        .g3-signal-item.signal-golden { background: rgba(241,196,15,0.1); border-left: 3px solid #f1c40f; }
        .signal-golden .g3-signal-tag { color: #f1c40f; }
        .signal-golden .g3-signal-score { color: #f1c40f; }
        /* 超级3球 - 最高优先级信号 */
        .g3-signal-item.signal-super { 
            background: linear-gradient(135deg, rgba(168,85,247,0.2), rgba(236,72,153,0.15)); 
            border-left: 4px solid #a855f7; 
            animation: super-pulse 2s infinite;
        }
        @keyframes super-pulse {
            0%, 100% { box-shadow: 0 0 8px rgba(168,85,247,0.3); }
            50% { box-shadow: 0 0 16px rgba(168,85,247,0.5); }
        }
        .signal-super .g3-signal-tag { color: #a855f7; font-weight: bold; font-size: 12px; }
        .signal-super .g3-signal-score { color: #a855f7; }
        .g3-warnings { margin-top: 8px; }
        .g3-warning-item { font-size: 12px; color: #e67e22; background: rgba(230,126,34,0.1); border-left: 3px solid #e67e22; padding: 5px 10px; border-radius: 0 6px 6px 0; margin-bottom: 4px; }
        .g3-prediction-title { font-size: 13px; color: #ffd700; font-weight: bold; margin-bottom: 8px; }
        .g3-prediction-value { font-size: 20px; font-weight: bold; padding: 8px 12px; border-radius: 8px; text-align: center; margin-bottom: 8px; }
        .g3-prediction-value.rec-focus { background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); }
        .g3-prediction-value.rec-exclude { background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }
        .g3-prediction-value.rec-watch { background: rgba(148,163,184,0.1); color: #94a3b8; border: 1px solid rgba(148,163,184,0.2); }
        .g3-score { font-size: 12px; font-weight: normal; margin-left: 10px; background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 10px; }
        .g3-odds-info { font-size: 12px; color: #888; text-align: center; margin-bottom: 6px; }
        .g3-odds-info strong { color: #ffd700; font-size: 14px; }
        .g3-tier { background: #0f3460; color: #00d4ff; padding: 1px 6px; border-radius: 4px; font-size: 11px; margin-left: 4px; }
        /* 排除3球时在赔率上方高亮显示 */
        .g3-exclude-banner { background: linear-gradient(135deg, rgba(239,68,68,0.25), rgba(220,38,38,0.15)); border: 2px solid #ef4444; border-radius: 8px; padding: 8px 12px; margin-bottom: 8px; text-align: center; animation: pulse-red 1.5s ease-in-out infinite; }
        .g3-exclude-banner-text { color: #fca5a5; font-size: 13px; font-weight: bold; }
        @keyframes pulse-red { 0%, 100% { box-shadow: 0 0 8px rgba(239,68,68,0.3); } 50% { box-shadow: 0 0 16px rgba(239,68,68,0.5); } }
        .g3-signals { display: flex; flex-direction: column; gap: 4px; }
        .g3-signal-item { display: flex; align-items: center; gap: 8px; padding: 4px 8px; border-radius: 6px; font-size: 12px; }
        .g3-signal-item.signal-plus { background: rgba(34,197,94,0.08); border-left: 3px solid #22c55e; }
        .g3-signal-item.signal-minus { background: rgba(239,68,68,0.08); border-left: 3px solid #ef4444; }
        .g3-signal-item.signal-neutral { background: rgba(148,163,184,0.06); border-left: 3px solid #888; }
        .g3-signal-item.signal-warning { background: rgba(245,158,11,0.1); border-left: 3px solid #f59e0b; }
        .signal-warning .g3-signal-tag { color: #f59e0b; }
        .signal-warning .g3-signal-score { color: #f59e0b; }
        /* 高近况+高球降信号 */
        .g3-signal-item.signal-high-form { background: rgba(139,92,246,0.12); border-left: 3px solid #8b5cf6; }
        .signal-high-form .g3-signal-tag { color: #c4b5fd; }
        .signal-high-form .g3-signal-score { color: #a78bfa; }
        /* 低近况+高球降信号 */
        .g3-signal-item.signal-low-form { background: rgba(6,182,212,0.12); border-left: 3px solid #06b6d4; }
        .signal-low-form .g3-signal-tag { color: #67e8f9; }
        .signal-low-form .g3-signal-score { color: #22d3ee; }
        .g3-signal-tag { font-weight: bold; color: #fff; min-width: 90px; }
        .g3-signal-score { font-weight: bold; min-width: 30px; }
        .signal-plus .g3-signal-score { color: #4ade80; }
        .signal-minus .g3-signal-score { color: #f87171; }
        .signal-neutral .g3-signal-score { color: #94a3b8; }
        .g3-signal-reason { color: #888; }

        /* 历史相似比赛统计 */
        .g3-hist-stats { margin-top: 8px; padding: 8px 10px; background: rgba(99,102,241,0.06); border-radius: 8px; border: 1px solid rgba(99,102,241,0.15); }
        .hist-stats-header { display: flex; align-items: center; gap: 8px; font-size: 12px; margin-bottom: 4px; }
        .hist-level { color: #6366f1; font-weight: bold; }
        .hist-count { color: #888; }
        .hist-rate { font-weight: bold; }
        .hist-rate.rate-high { color: #22c55e; }
        .hist-rate.rate-mid { color: #f59e0b; }
        .hist-rate.rate-low { color: #ef4444; }
        .hist-hits { color: #888; font-size: 11px; }
        .hist-matches { display: flex; flex-direction: column; gap: 2px; }
        .hist-match-item { display: flex; align-items: center; gap: 6px; font-size: 11px; padding: 2px 6px; border-radius: 4px; }
        .hist-match-item.hit { background: rgba(34,197,94,0.08); }
        .hist-match-item.miss { background: rgba(239,68,68,0.06); }
        .hist-match-tag { font-weight: bold; min-width: 14px; }
        .hist-match-item.hit .hist-match-tag { color: #22c55e; }
        .hist-match-item.miss .hist-match-tag { color: #ef4444; }
        .hist-match-info { color: #64748b; flex: 1; }
        .hist-match-g3 { color: #888; }
        .hist-match-actual { color: #94a3b8; }

        /* 比分记录 & 相似比赛 */
        .score-review-section { padding: 10px 0 5px; border-top: 1px dashed #1e3a5f; margin-top: 8px; }
        .score-input-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
        .score-label { font-size: 13px; color: #888; font-weight: bold; }
        .score-input { width: 52px; padding: 4px 6px; border: 1px solid #1e3a5f; border-radius: 6px; background: #0d1b2a; color: #fff; font-size: 14px; text-align: center; }
        .score-input:focus { border-color: #00d4ff; outline: none; }
        .score-sep { font-size: 16px; font-weight: bold; color: #888; }
        .btn-save-score { background: #0f3460; color: #4ade80; border: 1px solid #22c55e; border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; }
        .btn-save-score:hover { background: #1a4a2e; }
        .btn-review { background: #0f3460; color: #fbbf24; border: 1px solid #f59e0b; border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; }
        .btn-review:hover { background: #3a2a0a; }
        .btn-similar { background: #0f3460; color: #a78bfa; border: 1px solid #8b5cf6; border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; }
        .btn-similar:hover { background: #2a1a4a; }
        .score-msg { font-size: 12px; margin-top: 6px; min-height: 18px; }
        .score-msg.saved { color: #4ade80; }
        .score-msg.error { color: #f87171; }
        .score-msg.review-hit { color: #fbbf24; font-weight: bold; }
        .score-msg.review-miss { color: #f87171; }
        /* 大3球预判命中率标签 */
        .hit-rate-badge { margin-left: 8px; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
        .hit-rate-high { background: rgba(74,222,128,0.15); color: #4ade80; }
        .hit-rate-mid { background: rgba(251,191,36,0.15); color: #fbbf24; }
        .hit-rate-low { background: rgba(248,113,113,0.15); color: #f87171; }
        /* 命中率按钮 */
        .btn-pattern { background: #0f3460; color: #a78bfa; border: 1px solid #8b5cf6; border-radius: 6px; padding: 2px 8px; font-size: 11px; cursor: pointer; margin-left: 4px; }
        .btn-pattern:hover { background: #1a4a2e; }
        /* 单个前置条件命中率显示 */
        .pattern-single-stats { margin-top: 8px; padding: 8px 12px; background: #0a1628; border-radius: 6px; }
        .pattern-single-title { color: #fbbf24; font-weight: bold; font-size: 12px; margin-bottom: 4px; }
        .pattern-single-content { display: flex; gap: 12px; flex-wrap: wrap; font-size: 12px; }
        .pattern-single-content span { color: #e0e0e0; }
        .pattern-single-content strong { margin-left: 4px; }
        .pattern-no-stats { color: #888; font-size: 12px; padding: 8px; }
        /* 相似比赛面板 */
        .similar-panel { margin-top: 10px; background: #0d1b2a; border-radius: 8px; border: 1px solid #1e3a5f; overflow: hidden; }
        .similar-header { background: #0f3460; color: #a78bfa; font-size: 12px; font-weight: bold; padding: 8px 12px; }
        .similar-item { display: flex; align-items: center; padding: 8px 12px; border-bottom: 1px solid #1e3a5f; gap: 10px; font-size: 12px; }
        .similar-item:last-child { border-bottom: none; }
        .similar-rank { font-weight: bold; color: #a78bfa; min-width: 20px; }
        .similar-teams { flex: 1; color: #ccc; }
        .similar-score { font-weight: bold; min-width: 50px; text-align: center; }
        /* 规律命中率统计 */
        .pattern-stats { margin-top: 8px; padding: 8px 12px; background: #0a1628; border-radius: 6px; font-size: 12px; }
        .pattern-stats-title { color: #fbbf24; font-weight: bold; margin-bottom: 6px; }
        .pattern-stats-table { width: 100%; border-collapse: collapse; }
        .pattern-stats-table th { color: #888; font-size: 11px; text-align: left; padding: 2px 6px; border-bottom: 1px solid #0f3460; }
        .pattern-stats-table td { padding: 2px 6px; color: #e0e0e0; }
        .pattern-stats-table tr:hover { background: #0f3460; }
        .pattern-rate-high { color: #4ade80; font-weight: bold; }
        .pattern-rate-mid { color: #fbbf24; }
        .pattern-rate-low { color: #f87171; }
        .similar-score.tg-3 { color: #4ade80; }
        .similar-score.tg-other { color: #f87171; }
        .similar-score.tg-0 { color: #888; }
        .similar-similarity { font-size: 11px; background: #1e3a5f; color: #a78bfa; padding: 2px 6px; border-radius: 10px; white-space: nowrap; }
        .similar-tg-label { font-size: 11px; color: #666; min-width: 40px; text-align: right; }
        .similar-detail { font-size: 11px; color: #555; }
        .similar-empty { color: #555; padding: 10px; text-align: center; font-size: 12px; }
        .score-badge { display: inline-block; background: rgba(74,222,128,0.15); color: #4ade80; border: 1px solid rgba(74,222,128,0.3); border-radius: 4px; padding: 1px 6px; font-size: 11px; margin-left: 4px; }
        .saved-score-display { font-weight: bold; color: #4ade80; font-size: 14px; }
        /* ── 分页 ── */
        .pagination { display: flex; align-items: center; justify-content: center; gap: 6px; margin: 20px 0 10px; flex-wrap: wrap; }
        .pagination button { background: #0f3460; color: #a78bfa; border: 1px solid #1e3a5f; border-radius: 6px; padding: 6px 14px; font-size: 13px; cursor: pointer; }
        .pagination button:hover:not([disabled]) { background: #2a1a4a; }
        .pagination button[disabled] { opacity: 0.4; cursor: not-allowed; }
        .pagination button.active { background: #4c1d95; color: #fff; border-color: #7c3aed; font-weight: bold; }
        .pagination .page-ellipsis { color: #555; padding: 0 4px; }
        .pagination .page-info { color: #666; font-size: 12px; margin-left: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚽ 竞彩比分预测系统</h1>
        
        <div class="instructions">
            <p>输入比赛ID，点击"抓取分析"获取数据</p>
            <p class="tip">例如: 2039135 (从URL: sporttery.cn/?mid=2039135 获取)</p>
        </div>
        
        <div class="controls">
            <input type="text" id="matchInput" placeholder="输入比赛ID">
            <button class="btn-fetch" onclick="fetchMatch()">抓取分析</button>
            <button class="btn-refresh" onclick="loadMatches()">刷新列表</button>
        </div>
        
        <div id="matchList" class="match-grid"></div>
        <div id="pagination"></div>
    </div>

        <script>
        // 全局比赛数据缓存（供 doReview 获取 g3_prediction 用）
        window._matchData = {};
        // 全局已保存比分缓存 { match_id: {home_score, away_score, total_goals, ...} }
        window._savedScores = {};
        // 前置条件命中率统计（全局存储）
        let _patternStats = {};
        // 进球数赔率命中率统计
        const _ODDS_HITRATE = __ODDS_STATS_JSON__;
        const _HITRATE_COLORS = {green:'#4ade80', yellow:'#facc15', red:'#f87171', gray:'#888'};
        function _getHitRateLabel(goalNum, oddsVal) {
            // 直接精确匹配：找历史上有相同赔率的比赛
            const exact = _ODDS_HITRATE.exact || {};
            const goalExact = exact[goalNum] || {};

            // 精确匹配：找赔率完全相同的历史记录
            let found = null;
            for (const [ekStr, d] of Object.entries(goalExact)) {
                const ek = parseFloat(ekStr);
                if (Math.abs(oddsVal - ek) < 0.01) {  // 赔率完全相同
                    found = d;
                    break;
                }
            }

            const rate = found ? found.rate : null;
            const total = found ? found.total : 0;
            // 样本太少(<3场)显示灰色，表示参考价值低
            const color = rate === null ? 'gray' : total < 3 ? 'gray' : rate >= 35 ? 'green' : rate >= 20 ? 'yellow' : 'red';
            const tagTitle = rate === null ? '无历史数据'
                : `${goalNum}球赔率${oddsVal}，历史${total}场中${found.hits}场打出`;
            if (rate === null) return '';
            const sampleHint = total < 3 ? `(${total}场)` : '';
            return `<span class="hitrate-badge" style="font-size:10px;padding:1px 5px;border-radius:4px;margin-left:3px;background:${_HITRATE_COLORS[color]}22;color:${_HITRATE_COLORS[color]};border:1px solid ${_HITRATE_COLORS[color]}55" title="${tagTitle}">${rate}%${sampleHint}</span>`;
        }
        // 获取命中率数值（供其他逻辑使用）
        function _getHitRateValue(goalNum, oddsVal) {
            const exact = _ODDS_HITRATE.exact || {};
            const goalExact = exact[goalNum] || {};
            for (const [ekStr, d] of Object.entries(goalExact)) {
                const ek = parseFloat(ekStr);
                if (Math.abs(oddsVal - ek) < 0.01) {
                    return d.rate;
                }
            }
            return null;
        }

        // ── 分页配置 ──────────────────────────────────────
        window._PAGE_SIZE = 6;
        window._currentPage = 1;
        window._allMatches = [];

        function renderPage(page) {
            const matches = window._allMatches;
            const PAGE_SIZE = window._PAGE_SIZE;
            const total = matches.length;
            const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
            if (page < 1) page = 1;
            if (page > totalPages) page = totalPages;
            window._currentPage = page;

            const start = (page - 1) * PAGE_SIZE;
            const pageMatches = matches.slice(start, start + PAGE_SIZE);

            const container = document.getElementById('matchList');
            if (matches.length === 0) {
                container.innerHTML = '<div class="no-data"><h2>暂无数据</h2><p>输入比赛ID，点击"抓取分析"按钮获取数据</p></div>';
                document.getElementById('pagination').innerHTML = '';
                return;
            }

            container.innerHTML = pageMatches.map(m => {
                const analysis = analyzeMatch(m);
                const confClass = analysis.confidence >= 3 ? 'conf-high' : analysis.confidence >= 2 ? 'conf-medium' : 'conf-low';
                return `
                <div class="match-card">
                    <div class="match-header">
                        <span class="match-id">#${m.match_id}</span>
                        <span style="color:#666;font-size:12px">${m.fetch_time || ''}</span>
                    </div>
                    
                    <div class="teams">
                        ${m.match_info.home_team || '未知'} 
                        <span class="vs">VS</span> 
                        ${m.match_info.away_team || '未知'}
                    </div>
                    
                    ${analysis.prediction !== '未知' ? `
                    <div class="prediction-box">
                        <div class="prediction-title">预测推荐</div>
                        <div class="prediction-value">
                            ${analysis.prediction}
                            <span class="confidence ${confClass}">${analysis.confidence === 3 ? '高' : analysis.confidence === 2 ? '中' : '低'}置信</span>
                        </div>
                    </div>
                    ` : ''}

                    <!-- 3球预测 -->
                    ${m.g3_prediction ? `
                    <div class="g3-prediction-box${m.g3_prediction.golden_3goals ? ' golden-box' : ''}">
                        <div class="g3-prediction-title">⚽ 总进球预测${m.g3_prediction.golden_3goals ? ' <span class="golden-badge">⭐ 黄金3球</span>' : ''}</div>
                        <div class="g3-prediction-value ${m.g3_prediction.recommendation === '关注3球' ? 'rec-focus' : m.g3_prediction.recommendation === '排除3球' ? 'rec-exclude' : 'rec-watch'}">
                            ${m.g3_prediction.recommendation}
                            <span class="g3-score">评分: ${m.g3_prediction.score > 0 ? '+' : ''}${m.g3_prediction.score}</span>
                        </div>
                        ${m.g3_prediction.golden_3goals && m.g3_prediction.golden_reason ? `
                        <div class="golden-reason">
                            ${m.g3_prediction.golden_reason.join(' &nbsp;·&nbsp; ')}
                        </div>` : ''}
                        ${m.g3_prediction.warnings && m.g3_prediction.warnings.length > 0 ? `
                        <div class="g3-warnings">
                            ${m.g3_prediction.warnings.map(w => `
                                <div class="g3-warning-item">${w}</div>
                            `).join('')}
                        </div>` : ''}
                        ${m.g3_prediction.signals && m.g3_prediction.signals.some(s => s[0].includes('排除3球') && s[2].includes('历史3球率9.1%')) ? `
                        <div class="g3-exclude-banner" style="border-color:#a855f7;background:linear-gradient(135deg,rgba(168,85,247,0.25),rgba(147,51,234,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#d8b4fe;">🚫 排除3球 - 近况正常+0球<10+3球<3.7</div>
                        </div>` : ''}
                        ${m.g3_prediction.signals && m.g3_prediction.signals.some(s => s[0].includes('排除3球') && !s[2].includes('历史3球率9.1%')) ? `
                        <div class="g3-exclude-banner">
                            <div class="g3-exclude-banner-text">🚫 排除3球 - 三条件全满足</div>
                        </div>` : ''}
                        ${m.g3_prediction.signals && m.g3_prediction.signals.some(s => s[0].includes('排除2球') && s[2].includes('初始4球')) ? `
                        <div class="g3-exclude-banner" style="border-color:#f59e0b;background:linear-gradient(135deg,rgba(245,158,11,0.25),rgba(234,88,12,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#fcd34d;">🚫 排除2球 - 黄金2球+初始4球≥6.5</div>
                        </div>` : ''}
                        ${m.g3_prediction.signals && m.g3_prediction.signals.some(s => s[0].includes('排除2球') && s[2].includes('87.5%')) ? `
                        <div class="g3-exclude-banner" style="border-color:#22c55e;background:linear-gradient(135deg,rgba(34,197,94,0.25),rgba(22,163,74,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#86efac;">🚫 排除2球 - 近况2.0~2.5+0球13~18</div>
                        </div>` : ''}
                        ${m.g3_prediction.signals && m.g3_prediction.signals.some(s => s[0].includes('关注3球') && s[2].includes('50%')) ? `
                        <div class="g3-exclude-banner" style="border-color:#8b5cf6;background:linear-gradient(135deg,rgba(139,92,246,0.25),rgba(109,40,217,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#c4b5fd;">⭐ 关注3球 - 近况偏高+高球多降，历史50%命中率</div>
                        </div>` : ''}
                        ${m.g3_prediction.signals && m.g3_prediction.signals.some(s => s[0].includes('关注3球') && !s[2].includes('50%') && s[2].includes('历史28%')) ? `
                        <div class="g3-exclude-banner" style="border-color:#6366f1;background:linear-gradient(135deg,rgba(99,102,241,0.25),rgba(79,70,229,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#a5b4fc;">⭐ 关注3球 - 近况偏高+高球多降，3球率偏高</div>
                        </div>` : ''}
                        ${m.g3_prediction.signals && m.g3_prediction.signals.some(s => s[0].includes('观望3球')) ? `
                        <div class="g3-exclude-banner" style="border-color:#f59e0b;background:linear-gradient(135deg,rgba(245,158,11,0.20),rgba(234,88,12,0.10));">
                            <div class="g3-exclude-banner-text" style="color:#fcd34d;">⚠️ 观望3球 - 近况偏高+高球降，但3球赔率偏高</div>
                        </div>` : ''}
                        ${m.g3_prediction.signals && m.g3_prediction.signals.some(s => s[0].includes('关注2球') && s[2].includes('37.9%')) ? `
                        <div class="g3-exclude-banner" style="border-color:#06b6d4;background:linear-gradient(135deg,rgba(6,182,212,0.25),rgba(14,116,144,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#67e8f9;">⭐ 关注2球 - 近况偏低+高球多降为诱导，历史2球37.9%最高</div>
                        </div>` : ''}
                        ${m.g3_prediction.signals && m.g3_prediction.signals.some(s => s[0].includes('考虑0球')) ? `
                        <div class="g3-exclude-banner" style="border-color:#64748b;background:linear-gradient(135deg,rgba(100,116,139,0.20),rgba(71,85,105,0.10));">
                            <div class="g3-exclude-banner-text" style="color:#cbd5e1;">⚠️ 考虑0球 - 近况偏低+高球多降+0球≥13</div>
                        </div>` : ''}
                        ${m.g3_prediction.features['3球'] ? `
                        <div class="g3-odds-info">
                            3球赔率: <strong>${m.g3_prediction.features['3球']}</strong>
                            ${m.g3_prediction.features['区间'] ? `<span class="g3-tier">区间${m.g3_prediction.features['区间']}</span>` : ''}
                            &nbsp;|&nbsp;
                            0球: ${m.g3_prediction.features['0球'] || '-'}
                            &nbsp;|&nbsp;
                            1球: ${m.g3_prediction.features['1球'] || '-'}
                            &nbsp;|&nbsp;
                            2球: ${m.g3_prediction.features['2球'] || '-'}
                        </div>
                        ` : ''}
                        ${m.g3_prediction.signals && m.g3_prediction.signals.length > 0 ? `
                        <div class="g3-signals">
                            ${m.g3_prediction.signals.map(s => {
                                let cls = 'signal-neutral';
                                if (s[0].includes('超级3球')) cls = 'signal-super';
                                else if (s[0].includes('黄金3球')) cls = 'signal-golden';
                                else if (s[0].includes('主强客弱') || s[0].includes('客强主弱') || s[0].includes('均衡偏弱')) cls = 'signal-warning';
                                else if (s[0].includes('关注3球') && s[2].includes('50%')) cls = 'signal-high-form';
                                else if (s[0].includes('关注3球')) cls = 'signal-high-form';
                                else if (s[0].includes('关注2球') || s[0].includes('考虑0球')) cls = 'signal-low-form';
                                else if (s[1].startsWith('+')) cls = 'signal-plus';
                                else if (s[1].startsWith('-')) cls = 'signal-minus';
                                return `<div class="g3-signal-item ${cls}">
                                    <span class="g3-signal-tag">${s[0]}</span>
                                    <span class="g3-signal-score">${s[1]}</span>
                                    <span class="g3-signal-reason">${s[2]}</span>
                                </div>`;
                            }).join('')}
                        </div>
                        ` : ''}
                        ${m.g3_prediction.hist_stats && m.g3_prediction.hist_stats.matched_count >= 2 ? `
                        <div class="g3-hist-stats">
                            <div class="hist-stats-header">
                                <span class="hist-level">${m.g3_prediction.hist_stats.level === 'L1' ? '[精确]' : m.g3_prediction.hist_stats.level === 'L2' ? '[模糊]' : m.g3_prediction.hist_stats.level === 'L3' ? '[指纹]' : '[宽松]'}历史</span>
                                <span class="hist-count">${m.g3_prediction.hist_stats.matched_count}场</span>
                                <span class="hist-rate ${m.g3_prediction.hist_stats.g3_hit_rate >= 50 ? 'rate-high' : m.g3_prediction.hist_stats.g3_hit_rate >= 30 ? 'rate-mid' : 'rate-low'}">3球${m.g3_prediction.hist_stats.g3_hit_rate.toFixed(1)}%</span>
                                <span class="hist-hits">(${m.g3_prediction.hist_stats.g3_hit_count}打${m.g3_prediction.hist_stats.matched_count})</span>
                            </div>
                            ${m.g3_prediction.hist_stats.similar_matches && m.g3_prediction.hist_stats.similar_matches.length > 0 ? `
                            <div class="hist-matches">
                                ${m.g3_prediction.hist_stats.similar_matches.slice(0, 3).map(sm => `
                                    <div class="hist-match-item ${sm.is_3 ? 'hit' : 'miss'}">
                                        <span class="hist-match-tag">${sm.is_3 ? 'O' : 'X'}</span>
                                        <span class="hist-match-info">${sm.date} ${sm.match}</span>
                                        <span class="hist-match-g3">3球=${sm.g3}</span>
                                        <span class="hist-match-actual">${sm.actual}(${sm.total}球)</span>
                                    </div>
                                `).join('')}
                            </div>
                            ` : ''}
                        </div>
                        ` : m.g3_prediction.hist_stats && m.g3_prediction.hist_stats.total_historical > 0 ? `
                        <div class="g3-hist-stats">
                            <div class="hist-stats-header">
                                <span class="hist-level">[无匹配]</span>
                                <span class="hist-rate rate-mid">历史3球${m.g3_prediction.hist_stats.g3_hit_rate.toFixed(1)}%</span>
                                <span class="hist-hits">(${m.g3_prediction.hist_stats.total_historical}场参考)</span>
                            </div>
                        </div>
                        ` : ''}
                    </div>
                    ` : ''}

                    <!-- 最终推荐 -->
                    ${m.g3_prediction && m.g3_prediction.final_rec ? `
                    <div class="final-rec-box ${m.g3_prediction.final_rec.is_bet ? 'final-rec-bet' : m.g3_prediction.final_rec.recommendation === '不投注' ? 'final-rec-no-bet' : 'final-rec-watch'}">
                        <div class="final-rec-title">
                            ${m.g3_prediction.final_rec.recommendation === '不投注' ? '❌ 建议不投注' :
                              m.g3_prediction.final_rec.is_bet ? '✅ 建议投注' : '👁️ 观望'}
                            ${m.g3_prediction.final_rec.signal_type ? `<span class="signal-type-tag">${m.g3_prediction.final_rec.signal_type}</span>` : ''}
                        </div>
                        <div class="final-rec-content">
                            <div class="final-rec-main ${m.g3_prediction.final_rec.is_bet ? 'bet' : 'no-bet'}">
                                <strong>${m.g3_prediction.final_rec.recommendation}</strong>
                            </div>
                            <div class="final-rec-reason">
                                ${m.g3_prediction.final_rec.reason || ''}
                            </div>
                            ${m.g3_prediction.final_rec.hit_rate !== null ? `
                            <div class="final-rec-stats">
                                历史命中率: <span class="${m.g3_prediction.final_rec.hit_rate >= 50 ? 'hit-rate-high' : m.g3_prediction.final_rec.hit_rate >= 35 ? 'hit-rate-mid' : 'hit-rate-low'}">${m.g3_prediction.final_rec.hit_rate}%</span>
                                ${m.g3_prediction.final_rec.sample_size ? `(样本${m.g3_prediction.final_rec.sample_size}场)` : '(基于历史统计)'}
                            </div>
                            ` : ''}
                            ${m.g3_prediction.final_rec.confidence ? `
                            <div class="final-rec-confidence">
                                信心指数: ${m.g3_prediction.final_rec.confidence}%
                            </div>
                            ` : ''}
                        </div>
                    </div>
                    ` : ''}

                    <!-- 2026-04-24 新规律说明 -->
                    <div style="background: linear-gradient(135deg, rgba(251,191,36,0.15), rgba(251,191,36,0.05)); border: 1px solid #f59e0b; border-radius: 10px; padding: 12px; margin: 10px 0; font-size: 12px; line-height: 1.6;">
                        <div style="color: #f59e0b; font-weight: bold; margin-bottom: 6px;">📌 2026-04-24 新规律已生效</div>
                        <div style="color: #d1d5db;">
                            <div style="margin-bottom: 4px;"><b style="color: #22c55e;">大3球信号：</b>关注3球+0球=14 → 73.3%大3球 | 0球=14+近况2.5-3.0 → 85.7%大3球</div>
                            <div style="margin-bottom: 4px;"><b style="color: #22c55e;">排除大3球：</b>关注3球+0球10-12+近况2.5-3.0 → 100%无大3球</div>
                            <div><b style="color: #f59e0b;">小3球信号：</b>0球=16+近况3.0-3.5 → 66.7%小3球（样本小）</div>
                        </div>
                    </div>

                    <!-- 大球规则强信号提示（2026-04-23新增） -->
                    ${m.g3_prediction && m.g3_prediction.final_rec && m.g3_prediction.final_rec.big3_vs_small3 && m.g3_prediction.final_rec.big3_vs_small3.prediction && m.g3_prediction.final_rec.big3_vs_small3.prediction !== '不确定' && m.g3_prediction.final_rec.big3_vs_small3.reasons && m.g3_prediction.final_rec.big3_vs_small3.reasons.some(r => r.includes('🎯')) ? `
                    <div class="big-ball-rule-alert">
                        <div class="alert-title">🎯 大球规则强信号！历史命中率大幅提升</div>
                        <div class="alert-detail">
                            ${m.g3_prediction.final_rec.big3_vs_small3.reasons.filter(r => r.includes('🎯')).map(r => r).join('<br>')}
                        </div>
                    </div>
                    ` : ''}

                    <!-- 大3球 vs 小3球 预判 -->
                    ${m.g3_prediction && m.g3_prediction.final_rec && m.g3_prediction.final_rec.big3_vs_small3 && m.g3_prediction.final_rec.big3_vs_small3.prediction !== '不确定' ? `
                    <div class="big3-small3-box ${m.g3_prediction.final_rec.big3_vs_small3.prediction === '大3球' ? 'big3-box' : 'small3-box'}">
                        <div class="big3-small3-title">
                            ${m.g3_prediction.final_rec.big3_vs_small3.prediction === '大3球' ? '📈 大3球' : '📉 小3球'}预判
                            <span class="big3-confidence">置信度 ${m.g3_prediction.final_rec.big3_vs_small3.confidence}%</span>
                        </div>
                        <div class="big3-small3-content">
                            <div class="big3-prob-bar">
                                <div class="prob-label">大3球(4+): ${m.g3_prediction.final_rec.big3_vs_small3.big3_probability}%</div>
                                <div class="prob-bar">
                                    <div class="prob-fill big3-fill" style="width: ${m.g3_prediction.final_rec.big3_vs_small3.big3_probability}%"></div>
                                </div>
                            </div>
                            <div class="small3-prob-bar">
                                <div class="prob-label">小3球(恰好3): ${m.g3_prediction.final_rec.big3_vs_small3.small3_probability}%</div>
                                <div class="prob-bar">
                                    <div class="prob-fill small3-fill" style="width: ${m.g3_prediction.final_rec.big3_vs_small3.small3_probability}%"></div>
                                </div>
                            </div>
                            ${m.g3_prediction.final_rec.big3_vs_small3.reasons && m.g3_prediction.final_rec.big3_vs_small3.reasons.length > 0 ? `
                            <div class="big3-factors">
                                ${m.g3_prediction.final_rec.big3_vs_small3.reasons.map(r => `<span class="factor-tag ${r.includes('⭐') ? 'factor-tag-new' : ''}">${r}</span>`).join('')}
                            </div>
                            ` : ''}
                        </div>
                    </div>
                    ` : ''}

                    <!-- 黄金2球/4球 -->
                    ${(m.g3_prediction.golden_2goals && m.g3_prediction.golden_2goals.is_golden_2) || (m.g3_prediction.golden_4goals && m.g3_prediction.golden_4goals.is_golden_4) ? `
                    <div class="g3-prediction-box">
                        <div class="g3-prediction-title">🎯 黄金进球信号</div>
                        ${m.g3_prediction.golden_2goals && m.g3_prediction.golden_2goals.is_golden_2 ? `
                        <div class="golden-2-box">
                            <div class="golden-recommendation">⭐ 黄金2球信号</div>
                            <div class="golden-reason">
                                ${m.g3_prediction.golden_2goals.reason || ''}
                            </div>
                            ${m.g3_prediction.golden_2goals.hit_rate !== null ? `
                            <div class="golden-stats">
                                <span class="hit-rate-high">历史命中率: ${m.g3_prediction.golden_2goals.hit_rate}%</span>
                                ${m.g3_prediction.golden_2goals.sample_size ? `(样本${m.g3_prediction.golden_2goals.sample_size}场)` : ''}
                            </div>
                            ` : ''}
                        </div>
                        ` : ''}
                        ${m.g3_prediction.golden_4goals && m.g3_prediction.golden_4goals.is_golden_4 ? `
                        <div class="golden-4-box">
                            <div class="golden-recommendation">⭐ 黄金4球信号</div>
                            <div class="golden-reason">
                                ${m.g3_prediction.golden_4goals.reason || ''}
                            </div>
                            ${m.g3_prediction.golden_4goals.hit_rate !== null ? `
                            <div class="golden-stats">
                                <span class="hit-rate-high">历史命中率: ${m.g3_prediction.golden_4goals.hit_rate}%</span>
                                ${m.g3_prediction.golden_4goals.sample_size ? `(样本${m.g3_prediction.golden_4goals.sample_size}场)` : ''}
                            </div>
                            ` : ''}
                        </div>
                        ` : ''}
                    </div>
                    ` : ''}

                    <!-- 比分记录 & 相似比赛 -->
                    <div class="score-review-section">
                        <div class="score-input-row">
                            <span class="score-label">比分:</span>
                            <input type="number" class="score-input" id="home-${m.match_id}" min="0" max="15" placeholder="主" value="${window._savedScores && window._savedScores[m.match_id] ? window._savedScores[m.match_id].home_score : ''}">
                            <span class="score-sep">:</span>
                            <input type="number" class="score-input" id="away-${m.match_id}" min="0" max="15" placeholder="客" value="${window._savedScores && window._savedScores[m.match_id] ? window._savedScores[m.match_id].away_score : ''}">
                            <button class="btn-save-score" onclick="saveScore('${m.match_id}')">💾 保存</button>
                            <button class="btn-review" onclick="doReview('${m.match_id}')">📋 复盘</button>
                            <button class="btn-similar" onclick="showSimilar('${m.match_id}')">🔍 相似</button>
                            ${m.g3_prediction && m.g3_prediction.final_rec && m.g3_prediction.final_rec.big3_vs_small3 && m.g3_prediction.final_rec.big3_vs_small3.signal_type ? `
                            <button class="btn-pattern" onclick="togglePatternStats('${m.match_id}', '${m.g3_prediction.final_rec.big3_vs_small3.signal_type}')">📊 命中率</button>
                            ` : ''}
                        </div>
                    <div id="score-msg-${m.match_id}" class="score-msg"></div>
                    <div id="pattern-stats-${m.match_id}" class="pattern-stats" style="display:none"></div>
                    <div id="similar-panel-${m.match_id}" class="similar-panel" style="display:none"></div>
                    </div>
                    
                    <!-- 胜平负 -->
                    ${m.had && (m.had['胜'] !== undefined || m.had['平'] !== undefined || m.had['负'] !== undefined) ? `
                    <div class="odds-section">
                        <div class="odds-title">胜平负</div>
                        <div class="odds-grid">
                            <div class="odds-item ${getOddsClass(m.had['胜'])}"><div class="label">主胜</div><div class="value">${m.had['胜'] || '-'}</div></div>
                            <div class="odds-item ${getOddsClass(m.had['平'])}"><div class="label">平局</div><div class="value">${m.had['平'] || '-'}</div></div>
                            <div class="odds-item ${getOddsClass(m.had['负'])}"><div class="label">客胜</div><div class="value">${m.had['负'] || '-'}</div></div>
                        </div>
                    </div>
                    ` : ''}
                    
                    <!-- 总进球 -->
                    ${Object.keys(m.total_goals || {}).length > 0 ? `
                    <div class="odds-section">
                        <div class="odds-title">总进球</div>
                        <div class="odds-grid">
                            ${Object.entries(m.total_goals || {}).map(([k, v]) => {
                                const goalNum = parseInt(k.replace('球',''));
                                const odds = parseFloat(v);
                                const rateLabel = _getHitRateLabel(goalNum, odds);
                                const hitRate = _getHitRateValue(goalNum, odds);  // 获取命中率数值
                                const change = m.ttg_change && m.ttg_change[k];
                                let changeTag = '';
                                let excludeTag = '';
                                let focusTag = '';
                                let goldTag = '';
                                if (change && change.count > 0) {
                                    const pct = change.change_pct;
                                    const isUp = pct > 0;
                                    const color = isUp ? '#ef4444' : '#22c55e';
                                    const arrow = isUp ? '↑' : '↓';
                                    changeTag = `<span class="odds-change-tag" style="color:${color}">${arrow}${Math.abs(pct)}%</span>`;
                                }
                                // 排除/关注判断
                                // 排除：赔率>3.5 且 升赔>=5%（0球不排除，升赔显示警惕）
                                const isExclude = goalNum !== 0 && odds > 3.5 && change && change.change_pct >= 5;
                                const isFocus = odds >= 2.5 && odds <= 3.5 && change && change.change_pct < 0;
                                // 0球升赔警惕：显示"警惕"而不是排除
                                const isAlert0 = goalNum === 0 && change && change.change_pct > 0;
                                // 黄金信号：命中率>=50%
                                if (hitRate !== null && hitRate >= 50) {
                                    goldTag = '<span class="odds-tag gold">&#9733;黄金</span>';
                                }
                                if (isExclude) {
                                    excludeTag = '<span class="odds-tag exclude">&#10005;排除</span>';
                                } else if (isFocus) {
                                    focusTag = '<span class="odds-tag focus">&#9733;关注</span>';
                                } else if (isAlert0) {
                                    excludeTag = '<span class="odds-tag alert">&#9888;警惕</span>';
                                }
                                const tagClass = isExclude ? 'exclude' : (isFocus ? 'focus' : '') + (goldTag ? ' gold-highlight' : '');
                                return `<div class="odds-item ${getOddsClass(v)} ${tagClass}"><div class="label">${k}</div><div class="value">${v}${rateLabel}${changeTag}</div><div class="odds-tags">${goldTag}${excludeTag}${focusTag}</div></div>`;
                            }).join('')}
                        </div>
                    </div>
                    ` : ''}

                    <!-- 让球胜平负 -->
                    ${m.hhad && m.hhad.让球 ? `
                    <div class="odds-section">
                        <div class="odds-title">让球(${m.hhad.让球})胜平负</div>
                        <div class="odds-grid">
                            <div class="odds-item ${getOddsClass(m.hhad.让胜)}"><div class="label">让胜</div><div class="value">${m.hhad.让胜 || '-'}</div></div>
                            <div class="odds-item ${getOddsClass(m.hhad.让平)}"><div class="label">让平</div><div class="value">${m.hhad.让平 || '-'}</div></div>
                            <div class="odds-item ${getOddsClass(m.hhad.让负)}"><div class="label">让负</div><div class="value">${m.hhad.让负 || '-'}</div></div>
                        </div>
                        ${m.hhad_hint && m.hhad_hint.active ? (() => {
                            const h = m.hhad_hint;
                            const isHighDraw = h.draw_signal && h.draw_pct >= 60;
                            const bgStyle = isHighDraw
                                ? 'background:linear-gradient(135deg,rgba(234,179,8,0.20),rgba(245,158,11,0.15));border:1px solid rgba(234,179,8,0.5);'
                                : 'background:rgba(100,116,139,0.15);border:1px solid rgba(100,116,139,0.3);';
                            const tagColor = isHighDraw ? '#fbbf24' : '#94a3b8';
                            const tagBg = isHighDraw ? 'rgba(234,179,8,0.25)' : 'rgba(100,116,139,0.2)';
                            return `
                            <div class="hhad-hint-box" style="${bgStyle}border-radius:8px;padding:10px 12px;margin-top:10px;font-size:12px;">
                                ${h.is_midlow
                                    ? `<div style="color:#fbbf24;font-weight:bold;font-size:13px;margin-bottom:6px;">让球平中低赔3.3-3.64规律触发！</div>`
                                    : h.is_high
                                        ? `<div style="color:#fbbf24;font-weight:bold;font-size:13px;margin-bottom:6px;">让球平高赔4.0-4.5规律触发！</div>`
                                        : h.is_mid
                                            ? `<div style="color:#fbbf24;font-weight:bold;font-size:13px;margin-bottom:6px;">⚠️ 让球平中赔3.65-3.95规律触发！</div>`
                                            : (h.draw_signal && h.draw_pct >= 60
                                                ? `<div style="color:#fbbf24;font-weight:bold;font-size:13px;margin-bottom:6px;">🎯 让球平低赔规律触发！</div>`
                                                : `<div style="color:${tagColor};font-weight:bold;font-size:13px;margin-bottom:6px;">💡 让球平低赔规律</div>`)}
                                <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                                    <span style="background:${tagBg};color:${tagColor};padding:2px 8px;border-radius:4px;font-weight:bold;font-size:11px;">推荐${h.hhad_pick}</span>
                                    <span style="color:#94a3b8;">置信度 ${h.hhad_confidence}%</span>
                                </div>
                                ${h.hints.map(tip => `<div style="color:#cbd5e1;margin:2px 0 2px 4px;">• ${tip}</div>`).join('')}
                                ${h.mid_hints && h.mid_hints.length > 0 ? `
                                <div style="margin-top:6px;padding:4px 8px;background:rgba(251,191,36,0.12);border:1px solid rgba(251,191,36,0.3);border-radius:4px;">
                                    ${h.mid_hints.map(tip => `<div style="color:#fbbf24;font-size:11px;margin:2px 0;">• ${tip}</div>`).join('')}
                                </div>` : ''}
                                ${h.midlow_hints && h.midlow_hints.length > 0 ? `
                                <div style="margin-top:6px;padding:4px 8px;background:rgba(251,191,36,0.12);border:1px solid rgba(251,191,36,0.3);border-radius:4px;">
                                    ${h.midlow_hints.map(tip => `<div style="color:#fbbf24;font-size:11px;margin:2px 0;">• ${tip}</div>`).join('')}
                                </div>` : ''}
                                ${h.high_hints && h.high_hints.length > 0 ? `
                                <div style="margin-top:6px;padding:4px 8px;background:rgba(251,191,36,0.12);border:1px solid rgba(251,191,36,0.3);border-radius:4px;">
                                    ${h.high_hints.map(tip => `<div style="color:#fbbf24;font-size:11px;margin:2px 0;">• ${tip}</div>`).join('')}
                                </div>` : ''}
                                ${h.draw_signal ? `
                                <div style="margin-top:8px;padding:6px 8px;background:rgba(234,179,8,0.10);border:1px solid rgba(234,179,8,0.25);border-radius:6px;">
                                    <div style="display:flex;align-items:center;gap:6px;">
                                        <span style="background:rgba(234,179,8,0.25);color:#fbbf24;padding:2px 8px;border-radius:4px;font-weight:bold;font-size:12px;">⚠️ 高平局信号</span>
                                        <span style="color:#fbbf24;font-weight:bold;font-size:13px;">90分钟平局率约${h.draw_pct}%</span>
                                    </div>
                                    <div style="color:#fcd34d;margin-top:4px;font-size:11px;">${h.draw_reason}</div>
                                </div>
                                ` : ''}
                            </div>`;
                        })() : ''}
                    </div>
                    ` : ''}

                    <!-- 平局信号（所有had.平区间） -->
                    ${m.draw_hint && m.draw_hint.active ? `
                    <div class="odds-section">
                        ${drawHintHtml(m.draw_hint)}
                    </div>
                    ` : ''}

                    <!-- 半全场 -->
                    ${Object.keys(m.hafu || {}).length > 0 ? `
                    <div class="odds-section">
                        <div class="odds-title">半全场</div>
                        <div class="odds-grid">
                            ${Object.entries(m.hafu || {}).map(([k, v]) =>
                                `<div class="odds-item ${getOddsClass(v)}"><div class="label">${k}</div><div class="value">${v}</div></div>`
                            ).join('')}
                        </div>
                    </div>
                    ` : ''}
                    
                    <!-- 比分(最低赔率) -->
                    ${Object.keys(m.score_odds || {}).length > 0 ? `
                    <div class="odds-section">
                        <div class="odds-title">比分赔率 (最低)</div>
                        <div class="score-odds">
                            ${getLowestScores(m.score_odds)}
                        </div>
                    </div>
                    ` : ''}

                    <!-- 赔率变化统计 -->
                    ${(m.ttg_change && Object.keys(m.ttg_change).length > 0) || (m.hafu_change && Object.keys(m.hafu_change).length > 0) ? `
                    <div class="odds-section">
                        <div class="odds-title">赔率变化统计</div>
                        <div class="change-stats">
                            ${m.ttg_change && Object.keys(m.ttg_change).length > 0 ? `
                            <div class="change-category">
                                <div class="change-subtitle">总进球变化</div>
                                <div class="change-grid">
                                    ${Object.entries(m.ttg_change || {}).map(([k, v]) => {
                                        const up = v.change_pct > 0;
                                        const down = v.change_pct < 0;
                                        const cls = up ? 'change-up' : (down ? 'change-down' : 'change-neutral');
                                        const arrow = up ? '↑' : (down ? '↓' : '→');
                                        return `<div class="change-item ${cls}">
                                            <div class="change-label">${k}</div>
                                            <div class="change-value">${v.count}次 ${arrow}${Math.abs(v.change_pct)}%</div>
                                        </div>`;
                                    }).join('')}
                                </div>
                            </div>
                            ` : ''}
                            ${m.hafu_change && Object.keys(m.hafu_change).length > 0 ? `
                            <div class="change-category">
                                <div class="change-subtitle">半全场变化</div>
                                <div class="change-grid">
                                    ${Object.entries(m.hafu_change || {}).map(([k, v]) => {
                                        const up = v.change_pct > 0;
                                        const down = v.change_pct < 0;
                                        const cls = up ? 'change-up' : (down ? 'change-down' : 'change-neutral');
                                        const arrow = up ? '↑' : (down ? '↓' : '→');
                                        return `<div class="change-item ${cls}">
                                            <div class="change-label">${k}</div>
                                            <div class="change-value">${v.count}次 ${arrow}${Math.abs(v.change_pct)}%</div>
                                        </div>`;
                                    }).join('')}
                                </div>
                            </div>
                            ` : ''}
                        </div>
                    </div>
                    ` : ''}


                    <!-- 比分历史命中率推荐（新算法） -->
                    ${m.score_recommendations && m.score_recommendations.length > 0 ? `
                    <div class="odds-section score-rec-section" id="score-rec-section-${m.match_id}">
                        <div class="odds-title score-rec-title">
                            📊 历史高命中率比分
                            <span class="score-rec-hint" id="score-rec-hint-${m.match_id}">基于历史${Math.max(...m.score_recommendations.map(r=>r.total))}场同赔率区间统计</span>
                        </div>
                        <div class="score-rec-list" id="score-rec-list-${m.match_id}">
                            ${m.score_recommendations.map(rec => `
                                <div class="score-rec-item level-${rec.level}" title="赔率${rec.odds}（${rec.bucket}区间），历史${rec.total}场中${rec.hits}次命中">
                                    <span class="score-rec-score">${rec.score}</span>
                                    <span class="score-rec-odds">赔率 ${rec.odds}</span>
                                    <span class="score-rec-rate">${rec.rate}%</span>
                                    <span class="score-rec-sample">${rec.hits}/${rec.total}场</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    ` : `<div class="odds-section score-rec-section" id="score-rec-section-${m.match_id}" style="display:none">
                        <div class="odds-title score-rec-title">
                            📊 历史高命中率比分
                            <span class="score-rec-hint" id="score-rec-hint-${m.match_id}"></span>
                        </div>
                        <div class="score-rec-list" id="score-rec-list-${m.match_id}"></div>
                    </div>`}

                    <!-- 前瞻数据标签页 -->
                    <div class="preview-tabs">
                        <button class="preview-tab active" onclick="switchPreviewTab(this, 'tab-feature-${m.match_id}')">特征</button>
                        <button class="preview-tab" onclick="switchPreviewTab(this, 'tab-history-${m.match_id}')">交锋</button>
                        <button class="preview-tab" onclick="switchPreviewTab(this, 'tab-injury-${m.match_id}')">伤停</button>
                        <button class="preview-tab" onclick="switchPreviewTab(this, 'tab-player-${m.match_id}')">射手</button>
                        <button class="preview-tab" onclick="switchPreviewTab(this, 'tab-standing-${m.match_id}')">积分</button>
                    </div>
                    
                    <!-- 特征分析 -->
                    <div id="tab-feature-${m.match_id}" class="preview-content active">
                        ${renderFeature(m.preview)}
                    </div>
                    
                    <!-- 历史交锋 -->
                    <div id="tab-history-${m.match_id}" class="preview-content">
                        ${renderHistory(m.preview)}
                    </div>
                    
                    <!-- 伤停一览 -->
                    <div id="tab-injury-${m.match_id}" class="preview-content">
                        ${renderInjury(m.preview)}
                    </div>
                    
                    <!-- 射手信息 -->
                    <div id="tab-player-${m.match_id}" class="preview-content">
                        ${renderPlayer(m.preview)}
                    </div>
                    
                    <!-- 积分榜 -->
                    <div id="tab-standing-${m.match_id}" class="preview-content">
                        ${renderStanding(m.preview)}
                    </div>
                </div>
                `}).join('');

            // ── 分页导航 ───────────────────────────────
            let pageHtml = '<div class="pagination">';
            if (totalPages > 1) {
                pageHtml += `<button ${page <= 1 ? 'disabled' : ''} onclick="goPage(${page - 1})">‹ 上一页</button>`;
                for (let p = 1; p <= totalPages; p++) {
                    if (p === 1 || p === totalPages || (p >= page - 1 && p <= page + 1)) {
                        pageHtml += `<button class="${p === page ? 'active' : ''}" onclick="goPage(${p})">${p}</button>`;
                    } else if (p === page - 2 || p === page + 2) {
                        pageHtml += '<span class="page-ellipsis">…</span>';
                    }
                }
                pageHtml += `<button ${page >= totalPages ? 'disabled' : ''} onclick="goPage(${page + 1})">下一页 ›</button>`;
            }
            pageHtml += `<span class="page-info">第${page}/${totalPages}页，共${total}场</span>`;
            pageHtml += '</div>';
            document.getElementById('pagination').innerHTML = pageHtml;
        }

        function goPage(p) { renderPage(p); window.scrollTo({ top: 0, behavior: 'smooth' }); }

        async function loadMatches() {
            // 并行加载：精简比赛列表 + 已保存比分（加时间戳防缓存）
            const ts = Date.now();
            const [matchesRes, scoresRes] = await Promise.all([
                fetch('/api/matches?light=1&t=' + ts),
                fetch('/api/saved-scores?t=' + ts)
            ]);
            window._allMatches = await matchesRes.json();
            const scoresData = scoresRes.ok ? (await scoresRes.json()) : {};
            window._savedScores = (scoresData && scoresData.success && scoresData.scores) ? scoresData.scores : {};
            // 缓存数据，供复盘时取 g3_prediction
            window._matchData = {};
            window._allMatches.forEach(m => { window._matchData[m.match_id] = m; });
            renderPage(1);
        }
        
        function analyzeMatch(m) {
            // 轻量API使用 g3_prediction 作为预测和置信度来源
            const g3 = m.g3_prediction || {};
            const rec = g3.recommendation || '观望';
            const score = g3.score || 0;

            // 置信度基于 g3 评分
            let confidence = 0;
            if (score >= 15) confidence = 3;      // 高置信：强烈推荐/排除3球
            else if (score >= 5) confidence = 2;  // 中置信
            else confidence = 1;                  // 低置信

            const parts = [];
            const features = g3.features || {};
            if (rec !== '观望') {
                parts.push(rec);
                if (features['3球']) parts.push(`3球赔率: ${features['3球']}`);
            }

            return { prediction: parts.join(' | ') || '未知', confidence, reason: parts };
        }
        
        function getOddsClass(val) {
            if (!val || val === 0) return '';
            const v = parseFloat(val);
            if (v < 3) return 'odds-item low';
            if (v < 6) return 'odds-item medium';
            return 'odds-item high';
        }
        
        function getLowestScores(odds) {
            if (!odds || Object.keys(odds).length === 0) return '';
            
            const entries = Object.entries(odds)
                .filter(([k, v]) => v && v > 0 && k.match(/^\\d+:\\d+$/))
                .sort((a, b) => parseFloat(a[1]) - parseFloat(b[1]))
                .slice(0, 8);
            
            return entries.map(([k, v], i) => {
                const cls = i === 0 ? 'odds-item top' : getOddsClass(v);
                return `<div class="${cls}"><div class="label">${k}</div><div class="value">${v}</div></div>`;
            }).join('');
        }
        
        function switchPreviewTab(btn, tabId) {
            // 隐藏所有tab content
            btn.parentElement.parentElement.querySelectorAll('.preview-content').forEach(el => el.classList.remove('active'));
            // 取消所有tab激活状态
            btn.parentElement.querySelectorAll('.preview-tab').forEach(el => el.classList.remove('active'));
            // 激活当前tab
            btn.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        }
        
        // 前瞻数据渲染函数
        function renderFeature(preview) {
            if (!preview || !preview.feature) return '<div class="no-data"><p>暂无特征数据</p></div>';
            const f = preview.feature;
            
            // 使用 last (近况) 数据
            const last = f.last || {};
            const home = f.homeTeamShortName || '主队';
            const away = f.awayTeamShortName || '客队';
            
            let html = '<div class="team-form">';
            
            // 主队
            html += '<div class="team-stats">';
            html += '<h4>🟢 ' + home + '</h4>';
            html += '<div class="stat-row"><span>近' + (last.totalLegCnt||0) + '场</span><span>' + (last.homeWinMatchCnt||0) + '胜 ' + (last.homeDrawMatchCnt||0) + '平 ' + (last.homeLossMatchCnt||0) + '负</span></div>';
            html += '<div class="stat-row"><span>场均进球</span><span>' + (f.goalAvg?.homeGoalAvgCnt||'0') + '</span></div>';
            html += '<div class="stat-row"><span>场均失球</span><span>' + (f.lossGoalAvg?.homeLossGoalAvgCnt||'0') + '</span></div>';
            html += '<div class="stat-row"><span>主场胜率</span><span>' + (f.eachHomeAway?.homeScoreRatio||'0') + '%</span></div>';
            html += '</div>';
            
            // 客队
            html += '<div class="team-stats">';
            html += '<h4>🔴 ' + away + '</h4>';
            html += '<div class="stat-row"><span>近' + (last.totalLegCnt||0) + '场</span><span>' + (last.awayWinMatchCnt||0) + '胜 ' + (last.awayDrawMatchCnt||0) + '平 ' + (last.awayLossMatchCnt||0) + '负</span></div>';
            html += '<div class="stat-row"><span>场均进球</span><span>' + (f.goalAvg?.awayGoalAvgCnt||'0') + '</span></div>';
            html += '<div class="stat-row"><span>场均失球</span><span>' + (f.lossGoalAvg?.awayLossGoalAvgCnt||'0') + '</span></div>';
            html += '<div class="stat-row"><span>客场胜率</span><span>' + (f.eachHomeAway?.awayScoreRatio||'0') + '%</span></div>';
            html += '</div>';
            
            html += '</div>';
            return html;
        }
        
        function renderHistory(preview) {
            if (!preview || !preview.history) return '<div class="no-data"><p>暂无交锋数据</p></div>';
            const list = preview.history.matchList || [];
            
            if (!list || list.length === 0) return '<div class="no-data"><p>暂无交锋数据</p></div>';
            
            let html = '<div class="history-list">';
            list.slice(0, 5).forEach(m => {
                html += '<div class="history-item">';
                html += '<div class="match-info"><span>' + (m.matchDate||'') + '</span><span>' + (m.tournamentShortName||'') + '</span></div>';
                html += '<div class="score">' + (m.homeTeamFullCourtGoalCnt||'') + ' - ' + (m.awayTeamFullCourtGoalCnt||'') + '</div>';
                html += '<div class="teams"><span>' + (m.homeTeamShortName||'') + '</span><span>' + (m.awayTeamShortName||'') + '</span></div>';
                html += '</div>';
            });
            html += '</div>';
            return html;
        }
        
        function renderInjury(preview) {
            if (!preview || !preview.injury) return '<div class="no-data"><p>暂无伤停数据</p></div>';
            const home = preview.injury.home || {};
            const away = preview.injury.away || {};
            const homeList = home.injuriesAndSuspensionsList || [];
            const awayList = away.injuriesAndSuspensionsList || [];
            
            let html = '<div class="injury-grid">';
            
            // 主队
            html += '<div class="injury-team">';
            html += '<h4>🟢 ' + (home.teamShortName||'主队') + ' 伤停</h4>';
            if (homeList.length === 0) {
                html += '<p style="color:#888;font-size:12px">无伤停</p>';
            } else {
                homeList.forEach(p => {
                    const statusCls = 'status-injury';
                    html += '<div class="player-item"><span class="player-name">' + (p.personName||'') + '</span><span class="player-pos">' + (p.playerPositionDesc||'') + '</span><span class="player-status ' + statusCls + '">伤停</span></div>';
                });
            }
            html += '</div>';
            
            // 客队
            html += '<div class="injury-team">';
            html += '<h4>🔴 ' + (away.teamShortName||'客队') + ' 伤停</h4>';
            if (awayList.length === 0) {
                html += '<p style="color:#888;font-size:12px">无伤停</p>';
            } else {
                awayList.forEach(p => {
                    const statusCls = 'status-injury';
                    html += '<div class="player-item"><span class="player-name">' + (p.personName||'') + '</span><span class="player-pos">' + (p.playerPositionDesc||'') + '</span><span class="player-status ' + statusCls + '">伤停</span></div>';
                });
            }
            html += '</div>';
            
            html += '</div>';
            return html;
        }
        
        function renderPlayer(preview) {
            if (!preview || !preview.player) return '<div class="no-data"><p>暂无射手数据</p></div>';
            const home = preview.player.home || {};
            const away = preview.player.away || {};
            const homeList = home.playerList || [];
            const awayList = away.playerList || [];
            
            let html = '<div class="team-form">';
            
            // 主队射手
            html += '<div class="team-stats">';
            html += '<h4>🟢 ' + (home.teamShortName||'主队') + '</h4>';
            if (homeList.length === 0) {
                html += '<p style="color:#888;font-size:12px">暂无数据</p>';
            } else {
                html += '<div class="scorer-list">';
                homeList.slice(0, 5).forEach((p, i) => {
                    html += '<div class="scorer-item"><span class="scorer-rank">' + (i+1) + '</span><span class="scorer-name">' + (p.personName||'') + '</span><span class="scorer-goals">' + (p.goalCnt||0) + '球</span><span class="scorer-ratio">' + (p.goalAvgCnt||'') + '</span></div>';
                });
                html += '</div>';
            }
            html += '</div>';
            
            // 客队射手
            html += '<div class="team-stats">';
            html += '<h4>🔴 ' + (away.teamShortName||'客队') + '</h4>';
            if (awayList.length === 0) {
                html += '<p style="color:#888;font-size:12px">暂无数据</p>';
            } else {
                html += '<div class="scorer-list">';
                awayList.slice(0, 5).forEach((p, i) => {
                    html += '<div class="scorer-item"><span class="scorer-rank">' + (i+1) + '</span><span class="scorer-name">' + (p.personName||'') + '</span><span class="scorer-goals">' + (p.goalCnt||0) + '球</span><span class="scorer-ratio">' + (p.goalAvgCnt||'') + '</span></div>';
                });
                html += '</div>';
            }
            html += '</div>';
            
            html += '</div>';
            return html;
        }
        
        function renderStanding(preview) {
            if (!preview || !preview.tables) return '<div class="no-data"><p>暂无积分榜数据</p></div>';
            const tables = preview.tables;
            const tableList = tables.tables || [];
            
            if (!tableList || tableList.length === 0) {
                return '<div class="no-data"><p>暂无积分榜数据</p></div>';
            }
            
            let html = '<div class="preview-section"><div class="preview-section-title">' + (tables.tournamentShortName||'') + ' 积分榜</div>';
            html += '<table class="standing-table"><tr><th>排名</th><th>球队</th><th>场次</th><th>胜</th><th>平</th><th>负</th><th>积分</th></tr>';
            
            // 找到主客队
            const homeTeam = tables.tables?.find(t => t.sportteryTeamId === tables.sportteryHomeTeamId);
            const awayTeam = tables.tables?.find(t => t.sportteryTeamId === tables.sportteryAwayTeamId);
            
            tableList.forEach(t => {
                const isHome = homeTeam && t.ranking === homeTeam.ranking;
                const isAway = awayTeam && t.ranking === awayTeam.ranking;
                const rowStyle = isHome || isAway ? 'style="color:#00d4ff;font-weight:bold"' : '';
                html += '<tr ' + rowStyle + '><td>' + (t.ranking||'') + '</td><td>' + (t.teamShortName||'') + '</td><td>' + (t.totalLegCnt||'') + '</td><td>' + (t.winGoalMatchCnt||'') + '</td><td>' + (t.drawMatchCnt||'') + '</td><td>' + (t.lossGoalMatchCnt||'') + '</td><td>' + (t.points||'') + '</td></tr>';
            });
            html += '</table></div>';
            
            return html;
        }
        
        async function fetchMatch() {
            const matchId = document.getElementById('matchInput').value.trim();
            if (!matchId) {
                alert('请输入比赛ID');
                return;
            }
            
            const res = await fetch('/api/fetch/' + matchId);
            const data = await res.json();
            
            if (data.success) {
                alert('抓取成功！');
                loadMatches();
            } else {
                alert('抓取失败: ' + (data.error || '未知错误'));
            }
        }

        // ── 比分保存 ──────────────────────────────────────────
        async function saveScore(matchId) {
            const homeInput = document.getElementById('home-' + matchId);
            const awayInput = document.getElementById('away-' + matchId);
            const msgEl = document.getElementById('score-msg-' + matchId);
            const home = parseInt(homeInput.value);
            const away = parseInt(awayInput.value);
            if (isNaN(home) || isNaN(away) || home < 0 || away < 0) {
                msgEl.className = 'score-msg error';
                msgEl.textContent = '请输入有效的比分（0-15）';
                return;
            }
            try {
                const res = await fetch('/api/score/' + matchId, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({home_score: home, away_score: away})
                });
                const data = await res.json();
                if (data.success) {
                    const r = data.record;
                    const tg = r.total_goals;
                    // 立即更新本地缓存，避免切换分页后丢失显示
                    if (!window._savedScores) window._savedScores = {};
                    window._savedScores[matchId] = r;
                    // 比分保留在输入框，下方消息区醒目展示保存结果
                    msgEl.className = 'score-msg saved';
                    const teamLabel = `${r.home_team || '主队'} vs ${r.away_team || '客队'}`;
                    const badge = tg === 3 ? '<span class="score-badge">🎯3球!</span>' : tg === 0 ? '<span class="score-badge">0球!</span>' : '';
                    msgEl.innerHTML = `<span class="saved-score-display">已保存: <b>${home}:${away}</b></span> <span style="color:#888">${teamLabel}</span>，总进球 <b>${tg}球</b> ${badge}`;
                } else {
                    msgEl.className = 'score-msg error';
                    msgEl.textContent = '保存失败: ' + (data.error || '');
                }
            } catch(e) {
                msgEl.className = 'score-msg error';
                msgEl.textContent = '请求失败: ' + e.message;
            }
        }

        // ── 复盘：检验3球预测 ──────────────────────────────────
        async function doReview(matchId) {
            const homeInput = document.getElementById('home-' + matchId);
            const awayInput = document.getElementById('away-' + matchId);
            const msgEl = document.getElementById('score-msg-' + matchId);
            const home = parseInt(homeInput.value);
            const away = parseInt(awayInput.value);
            if (isNaN(home) || isNaN(away) || home < 0 || away < 0) {
                msgEl.className = 'score-msg error';
                msgEl.textContent = '请先输入比分再点击复盘';
                return;
            }
            const total = home + away;
            const tgLabel = total === 3 ? '3球' : total + '球';
            const matchData = window._matchData && window._matchData[matchId];
            const g3rec = matchData ? (matchData.g3_prediction || {}).recommendation : null;
            const g3score = matchData ? (matchData.g3_prediction || {}).score : null;
            // 保存比分（同时附带赔率数据，供后续相似比赛匹配）
            await fetch('/api/score/' + matchId, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    home_score: home,
                    away_score: away,
                    // 复盘时附带赔率，确保相似比赛匹配有效
                    total_goals: matchData ? matchData.total_goals : null,
                    hhad: matchData ? matchData.hhad : null,
                })
            });
            // 复盘后刷新赔率命中率统计（独立，不影响比分保存）
            try {
                const r2 = await fetch('/api/odds_hitrate');
                const data = await r2.json();
                window._ODDS_HITRATE = data;
                // 如果相似面板已打开，自动刷新赔率显示
                const panelEl = document.getElementById('similar-panel-' + matchId);
                if (panelEl && panelEl.style.display !== 'none') {
                    showSimilar(matchId);
                }
            } catch(e2) {
                console.warn('命中率刷新失败:', e2);
            }
            // 复盘后刷新规律命中率统计
            try {
                const rPattern = await fetch('/api/pattern_hitrate');
                const patternData = await rPattern.json();
                if (patternData.success && patternData.stats) {
                    _patternStats = patternData.stats;  // 存储到全局变量
                    displayPatternStats(matchId, patternData.stats);
                }
            } catch(e3) {
                console.warn('规律命中率刷新失败:', e3);
            }
            // 复盘后同步刷新当前比赛的"历史高命中率比分"模块
            try {
                const r3 = await fetch('/api/score_recommendations/' + matchId);
                const recData = await r3.json();
                if (recData.success && recData.recommendations) {
                    const recListEl = document.getElementById('score-rec-list-' + matchId);
                    const recSectionEl = document.getElementById('score-rec-section-' + matchId);
                    if (recSectionEl) {
                        const recs = recData.recommendations;
                        if (recs.length > 0) {
                            recSectionEl.style.display = '';
                            if (recListEl) {
                                var htmlParts = [];
                                for (var i = 0; i < recs.length; i++) {
                                    var rec = recs[i];
                                    var title = '赔率' + rec.odds + '（' + rec.bucket + '区间），历史' + rec.total + '场中' + rec.hits + '次命中';
                                    htmlParts.push(
                                        '<div class="score-rec-item level-' + rec.level + '" title="' + title + '">' +
                                        '<span class="score-rec-score">' + rec.score + '</span>' +
                                        '<span class="score-rec-odds">赔率 ' + rec.odds + '</span>' +
                                        '<span class="score-rec-rate">' + rec.rate + '%</span>' +
                                        '<span class="score-rec-sample">' + rec.hits + '/' + rec.total + '场</span>' +
                                        '</div>'
                                    );
                                }
                                recListEl.innerHTML = htmlParts.join('');
                            }
                            // 更新标题里的样本数
                            var hintEl = recSectionEl.querySelector('.score-rec-hint');
                            if (hintEl) hintEl.textContent = '基于历史' + recData.total_records + '场同赔率区间统计（已更新）';
                        } else {
                            recSectionEl.style.display = 'none';
                        }
                    }
                }
            } catch(e3) {
                console.warn('比分推荐刷新失败:', e3);
            }
            // 显示复盘结果
            let reviewText = `📋 复盘结果: 实际 ${home}:${away}，总进球 ${tgLabel}`;
            if (g3rec) {
                reviewText += ` | 赛前预测: ${g3rec} (评分${g3score > 0 ? '+' : ''}${g3score || 0})`;
                const hit = (tgLabel === '3球' && (g3rec === '关注3球' || g3rec === '关注3球机会'))
                         || (tgLabel !== '3球' && g3rec === '排除3球');
                const partial = (tgLabel === '3球' && g3rec === '观望') || (tgLabel !== '3球' && g3rec === '观望');
                if (hit) {
                    reviewText += ` <span style="color:#4ade80;font-weight:bold">✅ 预测正确!</span>`;
                    msgEl.className = 'score-msg review-hit';
                } else if (partial) {
                    reviewText += ` <span style="color:#fbbf24">⚠️ 预测观望，${tgLabel}</span>`;
                    msgEl.className = 'score-msg';
                } else {
                    reviewText += ` <span style="color:#f87171">❌ 预测错误</span>`;
                    msgEl.className = 'score-msg review-miss';
                }
            } else {
                reviewText += ` (无3球预测数据)`;
                msgEl.className = 'score-msg';
            }
            msgEl.innerHTML = reviewText;
        }

        // ── 大3球预判命中率统计展示 ──────────────────────────
        function displayPatternStats(matchId, stats) {
            const container = document.getElementById('pattern-stats-' + matchId);
            if (!container) return;
            container.style.display = '';

            let html = '<div class="pattern-stats-title">📊 前置条件命中率统计</div>';
            html += '<table class="pattern-stats-table">';
            html += '<tr><th>前置条件</th><th>预判</th><th>样本</th><th>命中</th><th>命中率</th></tr>';

            for (const [signalType, data] of Object.entries(stats)) {
                const rateClass = data.rate >= 70 ? 'pattern-rate-high' : 
                              data.rate >= 50 ? 'pattern-rate-mid' : 'pattern-rate-low';
                html += '<tr>' +
                    '<td>' + signalType + '</td>' +
                    '<td>' + data.prediction + '</td>' +
                    '<td>' + data.total + '场</td>' +
                    '<td>' + data.hits + '场</td>' +
                    '<td class="' + rateClass + '">' + data.rate + '%</td>' +
                '</tr>';
            }

            html += '</table>';
            container.innerHTML = html;
        }


        // ── 相似比赛查找 ───────────────────────────────────────
        async function showSimilar(matchId) {
            const panelEl = document.getElementById('similar-panel-' + matchId);
            if (panelEl.style.display === 'none') {
                panelEl.style.display = 'block';
                panelEl.innerHTML = '<div class="similar-header">🔍 查找相似比赛...</div>';
                try {
                    const res = await fetch('/api/similar/' + matchId);
                    const data = await res.json();
                    if (!data.success || !data.similar || data.similar.length === 0) {
                        panelEl.innerHTML = '<div class="similar-header">🔍 相似比赛</div><div class="similar-empty">暂无已记录比分的相似比赛<br><small>（需先保存比分才能匹配）</small></div>';
                        return;
                    }
                    let html = '<div class="similar-header">🔍 相似比赛（3球赔率相同，0球赔率相近优先，最多5场）</div>';
                    data.similar.forEach((item, idx) => {
                        const tg = item.record.total_goals;
                        const tgClass = tg === 3 ? 'tg-3' : tg === 0 ? 'tg-0' : 'tg-other';
                        const tgDisplay = tg + '球';
                        const det = item.details || {};
                        html += `<div class="similar-item">
                            <span class="similar-rank">#${idx + 1}</span>
                            <div class="similar-teams">${item.record.home_team || item.home_team} vs ${item.record.away_team || item.away_team}</div>
                            <div class="similar-score ${tgClass}">${item.record.score_str || (item.record.home_score + ':' + item.record.away_score)}</div>
                            <div class="similar-tg-label">${tgDisplay}</div>
                            <div class="similar-similarity">相似 ${item.similarity}%${item.g0_diff != null ? ' | 0球差' + item.g0_diff : ''}</div>
                        </div>`;
                        // 0-7球赔率表格
                        const odds = item.goal_odds || {};
                        const goalLabels = [0,1,2,3,4,5,6,7];
                        if (Object.keys(odds).length > 0) {
                            let oddsCells = goalLabels.map(g => {
                                const val = odds[g];
                                const isTg = g === tg;
                                const rateLabel = val !== undefined ? _getHitRateLabel(g, val) : '';
                                const cls = isTg ? 'background:#1a4a2e;color:#4ade80;font-weight:bold' : 'color:#ccc';
                                return `<td style="padding:3px 4px;text-align:center;font-size:11px;${cls}"><div>${g}球</div><b>${val !== undefined ? val.toFixed(2) : '-'}</b><div>${rateLabel}</div></td>`;
                            }).join('');
                            html += `<div style="padding:4px 12px 4px 42px">
                                <table style="border-collapse:collapse;width:auto;background:#0a1628;border-radius:6px;" cellpadding="0">
                                    <tr>${oddsCells}</tr>
                                </table>
                            </div>`;
                        }
                        // 近况展示
                        const rf = item.recent_form;
                        if (rf && rf.home_avg !== undefined) {
                            // 计算近况评分（与 predict_3goals.py 规则一致）
                            const comb = rf.combined_avg;
                            let bonus = 0, label = '';
                            if      (comb < 2.0)  { bonus = -8; label = '近况偏小'; }
                            else if (comb < 2.5)  { bonus = -3; label = '近况偏低'; }
                            else if (comb < 3.5)  { bonus = +3; label = '近况正常'; }
                            else if (comb < 4.0)  { bonus = -3; label = '近况偏高'; }
                            else                  { bonus = -8; label = '近况偏大'; }
                            const bonusColor = bonus > 0 ? '#4ade80' : bonus < 0 ? '#f87171' : '#888';
                            
                            // 近况均衡度判断（2026-04-21 新规律）
                            const diff = Math.abs(rf.home_avg - rf.away_avg);
                            let balanceLabel = '';
                            if (rf.home_avg >= 3.5 && rf.away_avg <= 2.0) {
                                balanceLabel = '<span style="background:#ef444420;color:#f87171;padding:1px 4px;border-radius:3px;margin-left:4px;font-size:10px">主强客弱</span>';
                            } else if (rf.away_avg >= 3.5 && rf.home_avg <= 2.0) {
                                balanceLabel = '<span style="background:#ef444420;color:#f87171;padding:1px 4px;border-radius:3px;margin-left:4px;font-size:10px">客强主弱</span>';
                            } else if (diff < 0.5 && comb < 2.5) {
                                balanceLabel = '<span style="background:#f59e0b20;color:#f59e0b;padding:1px 4px;border-radius:3px;margin-left:4px;font-size:10px">均衡偏弱</span>';
                            }
                            
                            html += `<div style="padding:2px 12px 6px 42px;font-size:11px;color:#555">
                                <span style="color:#888">近况:</span> 主${rf.home_avg.toFixed(1)}/客${rf.away_avg.toFixed(1)}
                                <span style="color:#888">(${rf.home_games}/${rf.away_games}场)</span>
                                &nbsp;
                                <span style="color:${bonusColor};font-weight:bold">${bonus > 0 ? '+' : ''}${bonus}</span>
                                <span style="color:#888;font-size:10px">(${label})</span>
                                ${balanceLabel}
                            </div>`;
                        }
                        // 明细
                        if (det.g3_exact !== undefined || det.hhad_score) {
                            let detailParts = [];
                            if (det.g3_exact !== undefined) detailParts.push(`3球赔率${det.g3_exact ? '✓相同' : '✗不同'} (${det.g3_pst})`);
                            if (det.line_match && det.hhad_diff !== undefined) detailParts.push(`让球(${det.line_cur})差异${det.hhad_diff}%`);
                            if (!det.line_match && det.line_pst) detailParts.push(`让球线不同(${det.line_cur} vs ${det.line_pst})`);
                            html += `<div class="similar-detail" style="padding:2px 12px 8px 42px;color:#555;font-size:11px">${detailParts.join(' | ')}</div>`;
                        }
                    });
                    panelEl.innerHTML = html;
                } catch(e) {
                    panelEl.innerHTML = '<div class="similar-header">🔍 相似比赛</div><div class="similar-empty">查询失败: ' + e.message + '</div>';
                }
            } else {
                panelEl.style.display = 'none';
            }
        }



        // 初始加载
        loadMatches();

        // 加载前置条件命中率统计（页面加载时立即获取）
        fetch('/api/pattern_hitrate')
            .then(r => r.json())
            .then(data => {
                if (data.success && data.stats) {
                    _patternStats = data.stats;
                }
            })
            .catch(e => console.error('前置条件命中率加载失败:', e));

        function togglePatternStats(matchId, signalType) {
            const container = document.getElementById('pattern-stats-' + matchId);
            if (!container) return;

            if (container.style.display === 'none') {
                const stats = _patternStats[signalType];
                if (!stats) {
                    container.innerHTML = '<div class="pattern-no-stats">无统计</div>';
                } else {
                    const rateClass = stats.rate >= 70 ? 'pattern-rate-high' :
                                 stats.rate >= 50 ? 'pattern-rate-mid' : 'pattern-rate-low';
                    container.innerHTML = `
                        <div class="pattern-single-stats">
                            <div class="pattern-single-title">📊 ${signalType} 命中率统计</div>
                            <div class="pattern-single-content">
                                <span>预判: <strong>${stats.prediction}</strong></span>
                                <span>样本: <strong>${stats.total}场</strong></span>
                                <span class="${rateClass}">命中率: <strong>${stats.rate}%</strong></span>
                            </div>
                        </div>
                    `;
                }
                container.style.display = '';
            } else {
                container.style.display = 'none';
            }
        }

        // 平局信号HTML生成（基于draw_level分色）
        function drawHintHtml(d) {
            if (!d || !d.active) return '';
            const isSuper = d.draw_level === 'super_high';
            const isHigh = d.draw_level === 'high';
            const isMed = d.draw_level === 'medium';
            const isLow = d.draw_level === 'low';
            const isVLow = d.draw_level === 'very_low';
            const bg = isSuper ? 'rgba(239,68,68,0.20)' : isHigh ? 'rgba(234,179,8,0.20)' : isMed ? 'rgba(59,130,246,0.15)' : isLow ? 'rgba(100,116,139,0.12)' : 'rgba(34,197,94,0.12)';
            const border = isSuper ? 'rgba(239,68,68,0.5)' : isHigh ? 'rgba(234,179,8,0.5)' : isMed ? 'rgba(59,130,246,0.4)' : isLow ? 'rgba(100,116,139,0.3)' : 'rgba(34,197,94,0.3)';
            const tagBg = isSuper ? 'rgba(239,68,68,0.30)' : isHigh ? 'rgba(234,179,8,0.25)' : isMed ? 'rgba(59,130,246,0.20)' : isLow ? 'rgba(100,116,139,0.18)' : 'rgba(34,197,94,0.20)';
            const tagColor = isSuper ? '#fca5a5' : isHigh ? '#fbbf24' : isMed ? '#93c5fd' : isLow ? '#94a3b8' : '#4ade80';
            const textColor = isSuper ? '#fca5a5' : isHigh ? '#fbbf24' : isMed ? '#93c5fd' : isLow ? '#94a3b8' : '#4ade80';
            const label = isSuper ? '⚠️ 超高平局' : isHigh ? '⚠️ 高平局' : isMed ? '平局信号' : isLow ? '平局概率偏低' : '💚 平局概率低';
            return '<div style="background:' + bg + ';border:1px solid ' + border + ';border-radius:8px;padding:10px 12px;margin-top:10px;font-size:12px;">' +
                '<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">' +
                    '<span style="background:' + tagBg + ';color:' + tagColor + ';padding:2px 8px;border-radius:4px;font-weight:bold;font-size:11px;">' + label + '</span>' +
                    '<span style="color:' + textColor + ';font-weight:bold;font-size:13px;">90分钟平局率 ' + d.draw_pct + '%</span>' +
                '</div>' +
                '<div style="color:' + textColor + ';margin-top:4px;font-size:11px;">' + d.draw_reason + '</div>' +
            '</div>';
        }

    </script>
</body>
</html>
'''

@app.route('/')
def index():
    # 注入命中率统计到 JS 全局变量
    stats = _build_odds_hitrate()
    # 序列化成 JS 字面量嵌入页面（用字符串替换避免 Jinja2 转义）
    stats_js = json.dumps(stats, ensure_ascii=False)
    html = HTML_TEMPLATE.replace('__ODDS_STATS_JSON__', stats_js)
    return html

def _analyze_hhad_low_draw(hhad, recent_form, data=None):
    """
    让球平低赔规律分析（基于341场历史回测）

    参数:
        hhad: {'让球': str, '让胜': float, '让平': float, '让负': float}
        recent_form: {'home_avg': float, 'away_avg': float, 'combined_avg': float} 或 None

    返回:
        {
            'active': bool,       # 是否触发让平低赔条件
            'hhad_draw': float,   # 让平赔率
            'handicap': float,    # 让球数(正=主让球, 负=主受让)
            'direction': str,     # '主让球' 或 '主受让'
            'hhad_pick': str,     # '让胜' / '让负'
            'hhad_confidence': int, # 让胜让负置信度
            'draw_signal': bool,  # 是否有高平局信号
            'draw_pct': int,      # 预估平局率
            'draw_reason': str,   # 平局信号原因
            'hints': list,        # 提示列表
        } 或 None
    """
    if not hhad or not hhad.get('让平'):
        return None

    try:
        hhad_draw = float(hhad['让平'])
        hhad_win = float(hhad['让胜'])
        hhad_lose = float(hhad['让负'])
    except (ValueError, TypeError):
        return None

    if hhad_draw <= 0:
        return None

    # 解析让球数（提前，中赔需要判断让球方向）
    h_str = str(hhad.get('让球', ''))
    try:
        raw = float(h_str)
        handicap = -raw
    except:
        return None

    is_home_let = handicap > 0
    direction = '主让球' if is_home_let else '主受让'

    # 计算近况差（提前，中赔需要判断客队近况是否更好）
    form_diff = None
    combined_avg = None
    if recent_form and recent_form.get('home_avg') is not None:
        form_diff = recent_form['home_avg'] - recent_form['away_avg']
        combined_avg = recent_form['combined_avg']

    # 触发条件 — 各区间
    is_low = hhad_draw < 3.3                       # 极低/低区间
    is_midlow = (hhad_draw >= 3.3 and hhad_draw <= 3.64)   # 中低区间(3.3~3.64)
    is_mid = (hhad_draw >= 3.65 and hhad_draw <= 3.95)      # 中区间(3.65~3.95)
    is_high = (hhad_draw >= 4.0 and hhad_draw <= 4.5)       # 高区间(4.0~4.5)
    # 中赔前置条件: 主受让 + 客队近况好(form_diff < -0.3)
    is_mid_match = is_mid and (not is_home_let) and form_diff is not None and form_diff < -0.3
    # 中低区间前置条件: 客队近况好(form_diff < -0.3) + 让胜赔更低
    is_midlow_match = is_midlow and form_diff is not None and form_diff < -0.3 and hhad_win < hhad_lose - 0.05
    # 高区间前置条件: 主让球 + 客队近况好(form_diff < -0.5) + 让负赔更低
    is_high_match = is_high and is_home_let and form_diff is not None and form_diff < -0.5 and hhad_lose < hhad_win - 0.05

    if not is_low and not is_mid_match and not is_midlow_match and not is_high_match:
        return None

    hints = []

    # ── Step 1: 让球方向判断 ──
    if is_home_let:
        hints.append(f'主让球(让球-1), 让负率55.8%(113场)')
        hhad_pick = '让负'
        hhad_confidence = 56
    else:
        hints.append(f'主受让(让球+1), 让胜率68.3%(63场)')
        hhad_pick = '让胜'
        hhad_confidence = 68


    # ── Step 3: 平局概率分析（基于had.平回测, 2026-04-26修正）──
    # 逻辑：不让球平局赔率(had.平)在高危区间时，90分钟平局概率显著上升
    # 高危区间：[3.0,3.2) 或 [3.4,3.7)  → 平局率约45%
    # 前置条件：任意hhad分析触发后均可作为风险提示
    draw_signal = False
    draw_pct = 27   # 基准27.3%（所有比赛）
    draw_reason = ''

    had_draw_val = 0
    try:
        had = data.get('had', {}) if data is not None else {}
        if had and '平' in had:
            had_draw_val = float(had['平'])
    except:
        pass 

    # 高危区间判断（回测：+had.平高危 → 平局率45%左右）
    is_high_draw = (3.0 <= had_draw_val < 3.2) or (3.4 <= had_draw_val < 3.7)

    if is_high_draw:
        draw_signal = True
        draw_pct = 45   # 回测均值约45%
        draw_reason = f'had.平={had_draw_val:.2f}高危区间, 90分钟平局率约45%'

    # ── Step 4: 让胜/让负低赔信号（341场回测）──
    # 中低/中/高区间已有专属强信号，跳过通用低赔信号（避免提示混乱）
    if not is_mid_match and not is_midlow_match and not is_high_match:
        # 让胜<1.60 → 让胜57.1%(35场)
        if hhad_win < 1.60:
            hhad_pick = '让胜'
            hhad_confidence = 57
            hints.append(f'让胜<1.60超低热, 让胜率57.1%(35场)')
        # 让负<1.60 → 让负59.2%(76场)
        elif hhad_lose < 1.60:
            hhad_pick = '让负'
            hhad_confidence = 59
            hints.append(f'让负<1.60超低热, 让负率59.2%(76场)')
        # 让胜>3.00 → 让负53.8%(145场) 反向信号
        elif hhad_win > 3.00:
            hhad_pick = '让负'
            hhad_confidence = 54
            hints.append(f'让胜>3.00高赔, 让负率53.8%(145场)')
        # 让负>3.00 → 让胜56.8%(88场) 反向信号
        elif hhad_lose > 3.00:
            hhad_pick = '让胜'
            hhad_confidence = 57
            hints.append(f'让负>3.00高赔, 让胜率56.8%(88场)')

    # ── Step 5: 中赔细分提醒（前置条件: 主受让+客队近况好+让平3.65~3.95）──
    mid_hints = []
    if is_mid_match:
        # 优先级1: 让胜赔更低 → 让胜88.2%(17场) ⭐⭐⭐
        if hhad_win < hhad_lose - 0.05:
            hhad_pick = '让胜'
            hhad_confidence = 88
            mid_hints.append(f'⭐⭐⭐ 中赔区间+让胜赔更低, 让胜率88.2%(17场)')
        # 优先级2: 让负赔 > 3.0 → 让胜100%(10场) ⭐⭐⭐
        elif hhad_lose > 3.0:
            hhad_pick = '让胜'
            hhad_confidence = 100
            mid_hints.append(f'⭐⭐⭐ 中赔区间+让负赔>3.0, 让胜率100%(10场)')
        # 让负赔 < 2.5 → 让胜50%(4场), 谨慎
        elif hhad_lose < 2.5:
            mid_hints.append(f'⚠️ 中赔区间+让负赔<2.5, 让胜率仅50%(4场), 谨慎')

        # 差值 > -1.0（客队近况略好）→ 让胜91%(11场) ⭐⭐
        if form_diff > -1.0:
            mid_hints.append(f'⭐⭐ 客队近况略好(form_diff={form_diff:.1f}), 让胜率91%(11场)')
        # 差值 ≤ -1.0（客队近况远好）→ 让胜62.5%(8场), 谨慎
        else:
            mid_hints.append(f'⚠️ 客队近况远好(form_diff={form_diff:.1f}), 让胜率62.5%(8场), 谨慎')

    # ── Step 6: 中低区间细分提醒（前置条件: 客近况好+让胜赔更低, 3.3~3.64）──
    midlow_hints = []
    if is_midlow_match:
        # 让胜赔率 1.60~1.80 → 让胜83%(6场) ⭐⭐⭐
        if 1.60 <= hhad_win < 1.80:
            hhad_pick = '让胜'
            hhad_confidence = 83
            midlow_hints.append(f'⭐⭐⭐ 中低区间+让胜1.60~1.80, 让胜率83%(6场)')
        # 让胜赔率 < 1.60 → 仅50%, 反向信号!
        elif hhad_win < 1.60:
            midlow_hints.append(f'⚠️ 中低区间+让胜赔<1.60, 让胜率仅50%, 可能是诱盘!')
        else:
            hhad_pick = '让胜'
            hhad_confidence = 79
            midlow_hints.append(f'⭐⭐ 中低区间+让胜赔更低, 让胜率79%(19场)')

    # ── Step 7: 高区间细分提醒（前置条件: 主让球+客近况好+让负赔更低, 4.0~4.5）──
    high_hints = []
    if is_high_match:
        hhad_pick = '让负'
        hhad_confidence = 90
        high_hints.append(f'⭐⭐⭐ 高区间+客近况好+让负赔更低, 让负率90%(10场)')

    return {
        'active': True,
        'is_mid': is_mid,              # 是否中赔区间(3.65~3.95)
        'is_midlow': is_midlow_match,  # 是否中低区间(3.3~3.64)
        'is_high': is_high_match,       # 是否高区间(4.0~4.5)
        'hhad_draw': round(hhad_draw, 2),
        'handicap': handicap,
        'direction': direction,
        'hhad_pick': hhad_pick,
        'hhad_confidence': hhad_confidence,
        'draw_signal': draw_signal,
        'draw_pct': draw_pct,
        'draw_reason': draw_reason,
        'hints': hints,
        'mid_hints': mid_hints,        # 中赔区间细分提醒
        'midlow_hints': midlow_hints,  # 中低区间细分提醒
        'high_hints': high_hints,      # 高区间细分提醒
    }


def _analyze_draw_signal(had, hhad):
    """
    平局信号分析（所有had.平区间均显示，基于344场回测）
    返回:
        {
            'active': bool,        # 是否有had数据
            'had_draw': float,     # had.平赔率
            'draw_level': str,     # 'super_high'/'high'/'medium'/'low'/'very_low'
            'draw_pct': int,       # 预估平局率
            'draw_reason': str,    # 原因说明
            'special_combo': bool, # 触发超高组合(100%, 7场)
            'combo_778': bool,     # 触发77.8%组合(9场)
        }
    """
    if not had or '平' not in had:
        return {'active': False}

    try:
        had_draw = float(had['平'])
    except (ValueError, TypeError):
        return {'active': False}

    if had_draw <= 0:
        return {'active': False}

    result = {
        'active': True,
        'had_draw': had_draw,
        'special_combo': False,
        'combo_778': False,
        'draw_level': 'medium',
        'draw_pct': 27,
        'draw_reason': '',
    }

    # ── 区间判断 + 平局率（基于344场回测）──
    if 3.0 <= had_draw < 3.2:
        result['draw_pct'] = 43
        result['draw_level'] = 'high'
        result['draw_reason'] = 'had.平=%.2f 高危区间[3.0,3.2), 平局率42.6%%(%d场)' % (had_draw, 47)
    elif 3.4 <= had_draw < 3.6:
        result['draw_pct'] = 36
        result['draw_level'] = 'high'
        result['draw_reason'] = 'had.平=%.2f 高危区间[3.4,3.6), 平局率35.7%%(%d场)' % (had_draw, 42)
    elif 3.6 <= had_draw < 3.8:
        result['draw_pct'] = 34
        result['draw_level'] = 'medium'
        result['draw_reason'] = 'had.平=%.2f [3.6,3.8), 平局率34.1%%(%d场)' % (had_draw, 41)
    elif 2.8 <= had_draw < 3.0:
        result['draw_pct'] = 26
        result['draw_level'] = 'medium'
        result['draw_reason'] = 'had.平=%.2f [2.8,3.0), 平局率25.6%%(%d场)' % (had_draw, 39)
    elif 3.2 <= had_draw < 3.4:
        result['draw_pct'] = 21
        result['draw_level'] = 'low'
        result['draw_reason'] = 'had.平=%.2f [3.2,3.4), 平局率21.1%%(%d场)' % (had_draw, 57)
    elif 3.8 <= had_draw < 4.0:
        result['draw_pct'] = 22
        result['draw_level'] = 'low'
        result['draw_reason'] = 'had.平=%.2f [3.8,4.0), 平局率21.9%%(%d场)' % (had_draw, 32)
    elif 4.0 <= had_draw < 4.5:
        result['draw_pct'] = 24
        result['draw_level'] = 'low'
        result['draw_reason'] = 'had.平=%.2f [4.0,4.5), 平局率23.5%%(%d场)' % (had_draw, 34)
    elif had_draw < 2.8:
        result['draw_pct'] = 33
        result['draw_level'] = 'medium'
        result['draw_reason'] = 'had.平=%.2f (<2.8), 平局率33.3%%(%d场,小样本)' % (had_draw, 6)
    else:  # >= 4.5
        result['draw_pct'] = 13
        result['draw_level'] = 'very_low'
        result['draw_reason'] = 'had.平=%.2f (>=4.5), 平局率13.0%%(%d场) [低平局区间]' % (had_draw, 46)

    # ── 特殊组合：had[3.4,3.6) + hhd<3.3 ──
    if 3.4 <= had_draw < 3.6 and hhad and '让平' in hhad and '让胜' in hhad:
        try:
            hhd = float(hhad['让平'])
            hhd_win = float(hhad['让胜'])
            if hhd < 3.3:
                # 77.8%组合（9场7平）
                result['combo_778'] = True
                result['draw_pct'] = 78
                result['draw_level'] = 'high'
                result['draw_reason'] = 'had.平=%.2f + 让平%.2f<3.3, 平局率77.8%%(9场)' % (had_draw, hhd)
                # 差值过滤：100%(7/7)
                if abs(hhd - hhd_win) >= 0.3:
                    result['special_combo'] = True
                    result['draw_level'] = 'super_high'
                    result['draw_pct'] = 100
                    result['draw_reason'] = '⚠️ 超高平局信号: had.平=%.2f+让平%.2f+|让平-让胜|>=0.3, 平局率100%%(7/7)' % (had_draw, hhd)
        except (ValueError, TypeError, KeyError):
            pass

    return result


def _build_match_card(data, api):
    """
    提取比赛数据中卡片展示所需的字段，构建轻量化对象。
    完整版返回全部字段（兼容旧逻辑），精简版只返回卡片需要的内容。
    """
    is_light = request.args.get('light') == '1'

    if is_light:
        # ── 精简版：只包含卡片和分页需要的数据 ──
        match_info = data.get('match_info', {})
        g3_pred = data.get('g3_prediction', {})
        hhad = data.get('hhad', {})
        had = data.get('had', {})
        ttg_change = data.get('ttg_change', {})
        hafu_change = data.get('hafu_change', {})
        exclusion_list = data.get('exclusion_list', [])

        # 计算近况数据
        recent_form = None
        try:
            rd = _extract_recent_matches(data)
            recent_form = calc_recent_form(rd)
        except Exception:
            pass

        # 让球平低赔规律分析
        hhad_hint = _analyze_hhad_low_draw(hhad, recent_form, data)

        # 平局信号分析（所有had.平区间均显示）
        draw_hint = _analyze_draw_signal(had, hhad)

        return {
            'match_id': data.get('match_id'),
            'fetch_time': data.get('fetch_time'),
            'match_info': {
                'home_team': match_info.get('home_team', '未知'),
                'away_team': match_info.get('away_team', '未知'),
                'league': match_info.get('league', ''),
                'time': match_info.get('time', ''),
            },
            # 进球数赔率（列表展示用）
            'total_goals': data.get('total_goals', {}),
            'g3_prediction': {
                'recommendation': g3_pred.get('recommendation', '观望'),
                'score': g3_pred.get('score', 0),
                'signals': g3_pred.get('signals', []),
                'warnings': g3_pred.get('warnings', []),
                'golden_3goals': g3_pred.get('golden_3goals', False),
                'golden_reason': g3_pred.get('golden_reason', []),
                'features': {
                    '3球': g3_pred.get('features', {}).get('3球'),
                    '0球': g3_pred.get('features', {}).get('0球'),
                    '1球': g3_pred.get('features', {}).get('1球'),
                    '2球': g3_pred.get('features', {}).get('2球'),
                    '4球': g3_pred.get('features', {}).get('4球'),
                    '区间': g3_pred.get('features', {}).get('区间'),
                },
                'hist_stats': g3_pred.get('hist_stats'),
                'double_pick': g3_pred.get('double_pick'),
                'exclude_pick': g3_pred.get('exclude_pick'),
                'golden_2goals': g3_pred.get('golden_2goals'),
                'golden_4goals': g3_pred.get('golden_4goals'),
                # 最终推荐（基于最严谨的方法）
                'final_rec': g3_pred.get('final_rec'),
                # 大3球 vs 小3球预判
                'big3_vs_small3': g3_pred.get('big3_vs_small3'),
            },
            # 不让球胜平负
            'had': {
                '胜': had.get('胜'),
                '平': had.get('平'),
                '负': had.get('负'),
            } if had else {},
            # 让球：只保留数值
            'hhad': {
                '让球': hhad.get('让球'),
                '让胜': hhad.get('让胜'),
                '让平': hhad.get('让平'),
                '让负': hhad.get('让负'),
            } if hhad else {},
            # 变化数据
            'ttg_change': ttg_change,
            'hafu_change': {k: v for k, v in hafu_change.items() if isinstance(v, (int, float))},
            'exclusion_list': exclusion_list,
            # 比分历史命中率推荐（新）
            'score_recommendations': data.get('score_recommendations', []),
            # 近况数据（让球平规律用）
            'recent_form': {
                'home_avg': recent_form['home_avg'],
                'away_avg': recent_form['away_avg'],
                'combined_avg': recent_form['combined_avg'],
            } if recent_form else None,
            # 让球平低赔规律提示
            'hhad_hint': hhad_hint,
            # 平局信号（所有had.平区间）
            'draw_hint': draw_hint,
        }
    else:
        # ── 完整版：返回全部字段 ──
        # 平局信号分析（所有had.平区间均显示）
        _full_had = data.get('had', {})
        _full_hhad = data.get('hhad', {})
        data['draw_hint'] = _analyze_draw_signal(_full_had, _full_hhad)
        return data


@app.route('/api/matches')
def get_matches():
    """获取所有比赛数据，?light=1 返回精简版（用于卡片列表）"""
    matches = []
    api = SportteryAPI()
    is_light = api is not None  # always True, just for readability

    for filepath in glob.glob(os.path.join(DATA_DIR, '*.json')):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'raw_' not in os.path.basename(filepath):
                    # 动态补充 exclusion_list（兼容旧缓存文件）
                    if 'exclusion_list' not in data:
                        data['exclusion_list'] = api._calc_exclusion_list(
                            data.get('score_odds', {}),
                            data.get('total_goals', {})
                        )
                    # 动态计算比分历史命中率推荐（每次都重新计算，确保最新）
                    data['score_recommendations'] = get_score_recommendations_for_match(
                        data.get('score_odds', {})
                    )
                    # 动态补充/更新3球预测（强制重新计算，确保 signal_score 最新）
                    try:
                        features = extract_features(data)
                        g3_pred = predict_3goals(features)
                        # 历史相似比赛3球打出率
                        se = get_stats_engine()
                        g3_hist = se.query_similar(
                            g3=features.get('3球'),
                            g0=features.get('0球'),
                            g0_is_int=features.get('0球_是整数', False),
                            g1=features.get('1球'),
                            g2=features.get('2球'),
                            league_type=features.get('赛事类型', '联赛正赛'),
                            jc_pattern=features.get('jc_pattern', ''),
                            macao_pattern=features.get('macao_pattern', ''),
                            min_records=2,
                        )
                        # 黄金2球预测
                        g2_pred = predict_2goals(features)
                        # 黄金4球预测
                        g4_pred = predict_4goals(features)
                        # 大球涨降判断（综合4/5/6/7球整体趋势）
                        high_changes = features.get('高球数变化', {})
                        rising_count = sum(1 for k, v in high_changes.items() if v is not None and v > 0)
                        dropping_count = sum(1 for k, v in high_changes.items() if v is not None and v < 0)
                        big_ball_rising = rising_count > dropping_count
                        big_ball_dropping = dropping_count > rising_count
                        # 最终推荐（基于最严谨的方法）
                        final_rec = get_final_recommendation(features, g3_pred, g2_pred, g4_pred)
                        # 大3球 vs 小3球预判（结合排除法和大球涨降规则）
                        big3_small3 = predict_big3_vs_small3(features, g3_pred=g3_pred, g2_pred=g2_pred, 
                                                             big_ball_rising=big_ball_rising, 
                                                             big_ball_dropping=big_ball_dropping)
                        data['g3_prediction'] = {
                            'recommendation': g3_pred.get('recommendation', '观望'),
                            'score': g3_pred.get('signal_score', 0),
                            'signals': g3_pred.get('signals', []),
                            'warnings': g3_pred.get('warnings', []),
                            'golden_3goals': g3_pred.get('golden_3goals', False),
                            'golden_reason': g3_pred.get('golden_reason', []),
                            'super_golden': g3_pred.get('super_golden', False),
                            'super_golden_reason': g3_pred.get('super_golden_reason', []),
                            'features': {
                                '3球': features.get('3球'),
                                '0球': features.get('0球'),
                                '1球': features.get('1球'),
                                '2球': features.get('2球'),
                                '4球': features.get('4球'),
                                '区间': features.get('区间'),
                                '0球_整数高赔': features.get('0球_整数高赔'),
                                '3球_降赔': features.get('3球_降赔'),
                                '3球_升赔': features.get('3球_升赔'),
                            },
                            # 历史相似比赛统计
                            'hist_stats': g3_hist,
                            # 黄金2球/4球
                            'golden_2goals': g2_pred,
                            'golden_4goals': g4_pred,
                            # 最终推荐（基于最严谨的方法）
                            'final_rec': final_rec,
                            # 大3球 vs 小3球预判
                            'big3_vs_small3': big3_small3,
                        }
                    except Exception as ex:
                        pass
                    matches.append(_build_match_card(data, api))
        except:
            pass

    matches.sort(key=lambda x: x.get('fetch_time', ''), reverse=True)
    return jsonify(matches)

@app.route('/api/fetch/<match_id>')
def fetch_match(match_id):
    """抓取单场比赛"""
    try:
        api = SportteryAPI()
        result = api.fetch_and_save(match_id)
        
        if result:
            # ── 3球预测 ──
            features = extract_features(result)
            g3_pred = predict_3goals(features)

            # ── 让球平低赔规律分析（含Step 3高平局信号）──
            _hhad = result.get('hhad', {})
            _recent_form = None
            try:
                _rd = _extract_recent_matches(result)
                _recent_form = calc_recent_form(_rd)
            except Exception:
                pass
            hhad_hint = _analyze_hhad_low_draw(_hhad, _recent_form, result)
            result['had_hint'] = hhad_hint
            # 黄金2球预测
            g2_pred = predict_2goals(features)
            # 黄金4球预测
            g4_pred = predict_4goals(features)
            # 大球涨降判断（综合4/5/6/7球整体趋势）
            high_changes = features.get('高球数变化', {})
            rising_count = sum(1 for k, v in high_changes.items() if v is not None and v > 0)
            dropping_count = sum(1 for k, v in high_changes.items() if v is not None and v < 0)
            big_ball_rising = rising_count > dropping_count
            big_ball_dropping = dropping_count > rising_count
            # 最终推荐（基于最严谨的方法）
            final_rec = get_final_recommendation(features, g3_pred, g2_pred, g4_pred)
            # 大3球 vs 小3球预判（结合排除法和大球涨降规则）
            big3_small3 = predict_big3_vs_small3(features, g3_pred=g3_pred, g2_pred=g2_pred,
                                                 big_ball_rising=big_ball_rising,
                                                 big_ball_dropping=big_ball_dropping)
            result['g3_prediction'] = {
                'recommendation': g3_pred.get('recommendation', '观望'),
                'score': g3_pred.get('signal_score', 0),
                'signals': g3_pred.get('signals', []),
                'warnings': g3_pred.get('warnings', []),
                'golden_3goals': g3_pred.get('golden_3goals', False),
                'golden_reason': g3_pred.get('golden_reason', []),
                'super_golden': g3_pred.get('super_golden', False),
                'super_golden_reason': g3_pred.get('super_golden_reason', []),
                'features': {
                    '3球': features.get('3球'),
                    '0球': features.get('0球'),
                    '1球': features.get('1球'),
                    '2球': features.get('2球'),
                    '4球': features.get('4球'),
                    '区间': features.get('区间'),
                    '0球_整数高赔': features.get('0球_整数高赔'),
                    '3球_降赔': features.get('3球_降赔'),
                    '3球_升赔': features.get('3球_升赔'),
                },
                # 历史相似比赛统计
                'hist_stats': get_stats_engine().query_similar(
                    g3=features.get('3球'),
                    g0=features.get('0球'),
                    g0_is_int=features.get('0球_是整数', False),
                    league_type=features.get('赛事类型', '联赛正赛'),
                    min_records=2,
                ) if features.get('3球') else None,
                # 黄金2球/4球
                'golden_2goals': g2_pred,
                'golden_4goals': g4_pred,
                # 最终推荐（基于最严谨的方法）
                'final_rec': final_rec,
                # 大3球 vs 小3球预判
                'big3_vs_small3': big3_small3,
                # 前置条件命中率统计（用于前端显示）
                'pattern_hitrate': _build_pattern_hitrate(),
            }
            return jsonify({'success': True, 'data': result})
        else:
            return jsonify({'success': False, 'error': '获取数据失败'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ─────────────────────────────────────────────────────────────
#  比分保存 & 复盘
# ─────────────────────────────────────────────────────────────
@app.route('/api/score/<match_id>', methods=['POST'])
def save_score(match_id):
    """保存比赛比分 / 复盘
    Body: { "home_score": 2, "away_score": 1, "total_goals": {...}, "hhad": {...} }
    """
    try:
        from flask import request
        body = request.get_json() or {}
        home = int(body.get('home_score', -1))
        away = int(body.get('away_score', -1))
        if home < 0 or away < 0:
            return jsonify({'success': False, 'error': '比分格式错误'}), 400

        total = home + away
        # 判断总进球区间
        if total == 0:    tg_result = '0球'
        elif total == 1:  tg_result = '1球'
        elif total == 2:  tg_result = '2球'
        elif total == 3:  tg_result = '3球'
        elif total == 4:  tg_result = '4球'
        elif total >= 5:  tg_result = '5+球'
        else:             tg_result = f'{total}球'

        record = {
            'match_id': match_id,
            'home_score': home,
            'away_score': away,
            'score_str': f'{home}:{away}',
            'total_goals': total,
            'tg_result': tg_result,
            'record_time': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M'),
        }

        # 优先使用前端传入的赔率数据（复盘时附带）
        if body.get('total_goals'):
            record['total_goals_odds'] = body['total_goals']
        if body.get('hhad'):
            record['hhad_odds'] = body['hhad']

        # 加载文件补全基本信息（球队名、联赛）
        filepath = os.path.join(DATA_DIR, f'{match_id}.json')
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                record['home_team'] = data.get('match_info', {}).get('home_team', '')
                record['away_team'] = data.get('match_info', {}).get('away_team', '')
                record['league'] = data.get('match_info', {}).get('league', '')
                # 文件没有赔率时才从文件补充
                if not record.get('total_goals_odds') and data.get('total_goals'):
                    record['total_goals_odds'] = data['total_goals']
                if not record.get('hhad_odds') and data.get('hhad'):
                    record['hhad_odds'] = data['hhad']
            except:
                pass

        # ── 复盘：计算大3球/小3球规律命中情况 ──────────────────
        try:
            filepath = os.path.join(DATA_DIR, f'{match_id}.json')
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                features = extract_features(data)
                g3_pred = predict_3goals(features)
                big3_pred = predict_big3_vs_small3(features, g3_pred=g3_pred)

                # 判断实际结果
                # 小3球 = 总进球<3 (0/1/2球) | 恰好3球 = 总进球=3 | 大3球 = 总进球>3 (4+球)
                if total >= 4:
                    big3_actual = '大3球'
                elif total <= 2:
                    big3_actual = '小3球'
                else:
                    big3_actual = '恰好3球'  # total == 3

                # 判断命中
                prediction = big3_pred.get('prediction', '不确定')
                signal_type = big3_pred.get('signal_type')  # 前置条件/规律名称

                if prediction == '不确定':
                    big3_result = 'unknown'
                elif prediction == '大3球' and big3_actual == '大3球':
                    big3_result = 'hit'
                elif prediction == '小3球' and big3_actual == '小3球':
                    big3_result = 'hit'
                else:
                    big3_result = 'miss'

                # 保存到记录
                record['big3_signal_type'] = signal_type  # 前置条件/规律名称
                record['big3_prediction'] = prediction
                record['big3_confidence'] = big3_pred.get('confidence', 0)
                record['big3_actual'] = big3_actual
                record['big3_result'] = big3_result
                record['big3_reasons'] = big3_pred.get('reasons', [])
        except Exception as e:
            print(f'big3_vs_small3 计算失败: {e}')
            import traceback; traceback.print_exc()

        save_score_record(record)
        return jsonify({'success': True, 'record': record})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/saved-scores')
def get_all_saved_scores():
    """返回所有已保存的比分，格式 {match_id: record}"""
    try:
        scores = load_scores()
        # 只保留有 home_score 的记录（过滤空数据）
        filtered = {k: v for k, v in scores.items() if v.get('home_score', -1) >= 0}
        return jsonify({'success': True, 'scores': filtered})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/odds_hitrate')
def get_odds_hitrate():
    """返回赔率命中率统计（供复盘后动态刷新）"""
    global _odds_hitrate_cache, _score_hitrate_cache
    _odds_hitrate_cache = None   # 清除进球数赔率缓存
    _score_hitrate_cache = None  # 同时清除比分赔率缓存
    stats = _build_odds_hitrate()
    return jsonify(stats)

@app.route('/api/pattern_hitrate')
def get_pattern_hitrate():
    """返回规律命中率统计（供复盘后动态刷新）"""
    global _pattern_hitrate_cache
    _pattern_hitrate_cache = None  # 清除缓存
    stats = _build_pattern_hitrate()
    return jsonify({'success': True, 'stats': stats})

@app.route('/api/score_recommendations/<match_id>')
def get_score_recommendations(match_id):
    """复盘后重新计算并返回某场比赛的历史高命中率比分推荐"""
    global _score_hitrate_cache
    _score_hitrate_cache = None  # 强制清除缓存，重新统计
    try:
        filepath = os.path.join(DATA_DIR, f'{match_id}.json')
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': '比赛数据不存在'}), 404
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        recs = get_score_recommendations_for_match(data.get('score_odds', {}))
        total_records = _build_score_hitrate_stats().get('total_records', 0)
        return jsonify({'success': True, 'recommendations': recs, 'total_records': total_records})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/similar/<match_id>')
def get_similar(match_id):
    """查找与指定比赛赔率相似的历史已记录比分"""
    try:
        filepath = os.path.join(DATA_DIR, f'{match_id}.json')
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': '比赛数据不存在，请先抓取'}), 404
        with open(filepath, 'r', encoding='utf-8') as f:
            current_data = json.load(f)
        similar = find_similar_matches(current_data, top_n=5)
        return jsonify({'success': True, 'match_id': match_id, 'similar': similar})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/similar-odds', methods=['POST'])
def get_similar_by_odds():
    """
    根据传入的赔率数据找相似比赛（用于抓取前预览）
    Body: { "total_goals": {...}, "hhad": {...} }
    """
    try:
        from flask import request
        body = request.get_json() or {}
        current_data = {
            'match_id': 'preview',
            'total_goals': body.get('total_goals', {}),
            'hhad': body.get('hhad', {}),
        }
        similar = find_similar_matches(current_data, top_n=5)
        return jsonify({'success': True, 'similar': similar})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print('='*60)
    print('竞彩比分预测系统')
    print('='*60)
    print('访问地址: http://192.168.0.101:8899')
    print('='*60)
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8899)), debug=False, threaded=True)
