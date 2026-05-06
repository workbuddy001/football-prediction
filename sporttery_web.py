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
from predict_3goals import extract_features, predict_3goals, predict_1goals, predict_2goals, predict_4goals, predict_big3_vs_small3, calc_recent_form, _extract_recent_matches, get_final_recommendation
from _3goals_stats import StatsEngine
from ai_reasoning import bp as ai_reasoning_bp

app = Flask(__name__)
app.register_blueprint(ai_reasoning_bp)

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
REC_STATS_FILE = '分析模板/_rec_stats.json'

def load_rec_stats():
    try:
        with open(REC_STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_rec_stats(stats):
    with open(REC_STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def get_accumulated_stats():
    """从_rec_stats.json计算各规则的实盘验证数据（仅统计按钮点击的场次）"""
    stats = load_rec_stats()
    acc = {}
    for mid, entry in stats.items():
        tg = entry.get('total_goals', -1)
        for rule in entry.get('rules', []):
            t = rule['type']
            target = rule.get('target_goals', -1) if 'target_goals' in rule else 0
            is_hit = (tg == target)
            if t not in acc:
                acc[t] = {'hits': 0, 'total': 0}
            acc[t]['total'] += 1
            if is_hit:
                acc[t]['hits'] += 1
    return acc

def apply_accumulated_stats(match_data):
    """在match数据中追加推荐统计摘要（不覆盖现有命中率）"""
    acc_stats = get_accumulated_stats()
    pd = match_data.get('g3_prediction', {})
    
    summaries = {}
    for key, rt in [('golden_1goals', 'golden_1goals'), ('golden_2goals', 'golden_2goals'), ('golden_4goals', 'golden_4goals')]:
        gold = pd.get(key)
        if gold and isinstance(gold, dict):
            # golden_1goals支持增强/基础两个子类型
            if key == 'golden_1goals':
                is_enh = (gold.get('reason', '') or '').find('增强') >= 0
                rt_key = 'golden_1goals_enhanced' if is_enh else 'golden_1goals_base'
                if rt_key in acc_stats:
                    s = acc_stats[rt_key]
                    pct = round(s['hits']/s['total']*100, 1) if s['total'] else 0
                    summaries[key] = f'实盘验证: {s["hits"]}/{s["total"]} ({pct}%)'
            # golden_2goals支持多个子类型
            elif key == 'golden_2goals':
                reason = gold.get('reason', '') or ''
                g2type = 'golden_2goals'
                if reason.find('2.9') >= 0: g2type = 'golden_2goals_29'
                elif reason.find('0球=23') >= 0: g2type = 'golden_2goals_g023'
                elif reason.find('3.1') >= 0: g2type = 'golden_2goals_31'
                if g2type in acc_stats:
                    s = acc_stats[g2type]
                    pct = round(s['hits']/s['total']*100, 1) if s['total'] else 0
                    summaries[key] = f'实盘验证: {s["hits"]}/{s["total"]} ({pct}%)'
            elif rt in acc_stats:
                s = acc_stats[rt]
                pct = round(s['hits']/s['total']*100, 1) if s['total'] else 0
                summaries[key] = f'实盘验证: {s["hits"]}/{s["total"]} ({pct}%)'

    def _fmt_stats(s, name=''):
        pct = round(s['hits']/s['total']*100, 1) if s['total'] else 0
        label = f'({name})' if name else ''
        return f'实盘验证{label}: {s["hits"]}/{s["total"]} ({pct}%)'
    
    # 排除规则统计 - 固定规则 + 动态final_*规则
    exclude_map = {
        'exclude_2ball_A': 'exclude_2ball_A', 'exclude_2ball_B': 'exclude_2ball_B', 'exclude_2ball_C': 'exclude_2ball_C',
        'exclude_3ball_A': 'exclude_3ball_A',
        'exclude_4ball_A': 'exclude_4ball_A', 'exclude_4ball_B': 'exclude_4ball_B', 'exclude_4ball_C': 'exclude_4ball_C',
        'exclude_1ball_A': 'exclude_1ball_A', 'exclude_1ball_B': 'exclude_1ball_B',
    }
    for k in acc_stats:
        if k.startswith('final_'):
            exclude_map[k] = k
    exclude_summaries = {}
    for ek, rt in exclude_map.items():
        if rt in acc_stats:
            s = acc_stats[rt]
            exclude_summaries[ek] = _fmt_stats(s)
    
    # 实操规律统计（2026-05-02新增）
    practical_map = {
        'practical_exclude_3': 'practical_exclude_3',
        'practical_recommend_3': 'practical_recommend_3',
        'practical_exclude_2': 'practical_exclude_2',
        'practical_recommend_2': 'practical_recommend_2',
    }
    practical_summaries = {}
    for pk, rt in practical_map.items():
        if rt in acc_stats:
            s = acc_stats[rt]
            practical_summaries[pk] = _fmt_stats(s)
    
    if summaries or exclude_summaries or practical_summaries:
        pd['_rec_stats'] = {'golden': summaries, 'exclude': exclude_summaries, 'practical': practical_summaries}

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
            if tg == goal or (goal == 7 and tg >= 7):
                overall[goal][1] += 1

            # exact: 按精确赔率值统计
            if goal not in exact:
                exact[goal] = {}
            if val not in exact[goal]:
                exact[goal][val] = [0, 0]
            exact[goal][val][0] += 1
            if tg == goal or (goal == 7 and tg >= 7):
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

# ─────────────────────────────────────────────────────────────────
# 进球数赔率变化命中率统计（带缓存）
# 统计每个进球数在各"幅度+方向"组合下的历史命中率
# ─────────────────────────────────────────────────────────────────
_change_hitrate_cache = None

def _build_change_hitrate():
    """
    遍历所有有比分+ttg_change的历史记录，计算各进球数在各幅度+方向组合的历史命中率。
    返回格式: change[goal][bucket_label] = {total, hits, rate}
    bucket_label = "0%不变", "1-2%涨", "1-2%降", ">20%涨", ...
    """
    global _change_hitrate_cache
    if _change_hitrate_cache is not None:
        return _change_hitrate_cache

    scores = load_scores()
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sporttery_data')

    def pct_bucket(a):
        if a == 0:
            return "0%"
        lo = int(a)
        if a == lo:
            lo = lo - 1  # 整数如20.0 → 19-20%
        return f"{lo}-{lo+1}%"

    def make_label(change_pct):
        if change_pct == 0:
            return "0%不变"
        a = abs(change_pct)
        d = "涨" if change_pct > 0 else "降"
        return f"{pct_bucket(a)}{d}"

    change = {}  # change[goal][label] = [total, hits]

    for key, record in scores.items():
        mid = record.get('match_id', '')
        hs = record.get('home_score')
        as_ = record.get('away_score')
        if hs is None or as_ is None or mid == 'test':
            continue
        if not (mid.isdigit() or (mid.startswith('2') and len(mid) == 7)):
            continue
        total_goals = hs + as_
        fp = os.path.join(data_dir, f'{mid}.json')
        if not os.path.exists(fp):
            continue
        try:
            data = json.load(open(fp, encoding='utf-8'))
        except:
            continue
        ttg_chg = data.get('ttg_change')
        if not ttg_chg:
            continue

        for goal in range(0, 8):
            gl = f"{goal}球"
            actual = ttg_chg.get(gl)
            if not actual:
                continue
            bl = make_label(actual.get('change_pct', 0))
            if goal not in change:
                change[goal] = {}
            if bl not in change[goal]:
                change[goal][bl] = [0, 0]
            change[goal][bl][0] += 1
            if total_goals == goal or (goal == 7 and total_goals >= 7):
                change[goal][bl][1] += 1

    def rate(total, hits):
        return round(hits / total * 100, 1) if total > 0 else None

    change_stats = {}
    for g, bl_data in change.items():
        change_stats[g] = {
            bl: {'total': v[0], 'hits': v[1], 'rate': rate(v[0], v[1])}
            for bl, v in bl_data.items() if v[0] > 0
        }

    _change_hitrate_cache = change_stats
    
    # 保存变化命中率排名（供predict_3goals.py使用）
    try:
        # 计算每个进球数的最高命中率
        goal_max_rate = {}
        for g, bl_data in change_stats.items():
            max_rate = 0
            for bl, stats in bl_data.items():
                if stats.get('rate'):
                    max_rate = max(max_rate, stats['rate'])
            goal_max_rate[g] = max_rate
        
        # 按命中率排序，第1名是命中率最高的进球数
        sorted_goals = sorted(goal_max_rate.items(), key=lambda x: x[1], reverse=True)
        ranking = {g: {'rank': idx+1, 'rate': rate} for idx, (g, rate) in enumerate(sorted_goals)}
        
        ranking_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'change_hit_rate_ranking.json')
        with open(ranking_file, 'w', encoding='utf-8') as f:
            json.dump(ranking, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'保存变化命中率排名失败: {e}')
    
    return _change_hitrate_cache

# ────────────────────────────────────────────────────────────
# 规律命中率统计（带缓存）
# ────────────────────────────────────────────────────────────
def _build_pattern_hitrate():
    """
    遍历所有有 big3_signal_type 的历史记录，计算各前置条件的命中率。
    按"小3球/恰好3球/大3球"三个维度分别统计。

    返回格式:
      stats[signal_type] = {
        'total': total,
        'prediction': prediction,
        '小3球': {'hits': h, 'total': t, 'rate': r},
        '恰好3球': {'hits': h, 'total': t, 'rate': r},
        '大3球': {'hits': h, 'total': t, 'rate': r},
      }
    """
    global _pattern_hitrate_cache
    if _pattern_hitrate_cache is not None:
        return _pattern_hitrate_cache

    scores = load_scores()
    # pattern_stats[signal_type] = {'prediction': p, '小3球': [hits, total], ...}
    pattern_stats = {}

    for key, record in scores.items():
        # 处理 big3_signal_type（原有逻辑）
        signal_type = record.get('big3_signal_type')
        prediction = record.get('big3_prediction')
        result = record.get('big3_result')
        actual = record.get('big3_actual', '')

        if not result or result == 'unknown' or not actual:
            continue

        # 统计 big3_signal_type
        if signal_type:
            if signal_type not in pattern_stats:
                pattern_stats[signal_type] = {
                    'prediction': prediction,
                    '小3球': [0, 0],
                    '恰好3球': [0, 0],
                    '大3球': [0, 0],
                }
            if actual in ['小3球', '恰好3球', '大3球']:
                pattern_stats[signal_type][actual][1] += 1
                if result == 'hit':
                    pattern_stats[signal_type][actual][0] += 1

        # 也处理 final_signal_type（最终推荐的signal_type）
        final_signal_type = record.get('final_signal_type')
        final_prediction = record.get('final_prediction')
        if final_signal_type and final_prediction:
            if final_signal_type not in pattern_stats:
                pattern_stats[final_signal_type] = {
                    'prediction': final_prediction,
                    '小3球': [0, 0],
                    '恰好3球': [0, 0],
                    '大3球': [0, 0],
                }
            if actual in ['小3球', '恰好3球', '大3球']:
                pattern_stats[final_signal_type][actual][1] += 1
                if result == 'hit':
                    pattern_stats[final_signal_type][actual][0] += 1

    # 计算命中率
    result = {}
    for signal_type, data in pattern_stats.items():
        pred = data['prediction']
        entry = {'prediction': pred, 'total': 0}

        for key in ['小3球', '恰好3球', '大3球']:
            hd = data[key]
            hits = hd[0]
            total = hd[1]
            rate = round(hits / total * 100, 1) if total > 0 else 0
            entry[key] = {'hits': hits, 'total': total, 'rate': rate}
            entry['total'] += total

        result[signal_type] = entry

    _pattern_hitrate_cache = result
    return result
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


def find_similar_matches(current_data, top_n=8):
    """
    在已记录比分的比赛中找相似场次
    只处理有赔率数据的记录（复盘附带 or 有源文件），避免全量遍历。
    排序优先级：近况之和接近 > 0球赔率差值小 > 0球变化涨跌一致 > 相似度高
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

            # 0球赔率变化数据（从历史源文件的ttg_change提取）
            g0_change = None
            if pd:
                tc = pd.get('ttg_change', {})
                if tc and '0球' in tc:
                    g0_change = tc['0球']

            # 当前比赛的0球赔率变化（用于计算变化幅度差异）
            cur_g0_change = None
            cur_tc = current_data.get('ttg_change', {})
            if cur_tc and '0球' in cur_tc:
                cur_g0_change = cur_tc['0球']

            # 计算排序用的0球变化幅度差异
            g0_change_diff = None
            if g0_change and cur_g0_change:
                try:
                    g0_change_diff = round(abs(g0_change.get('change_pct', 0) - cur_g0_change.get('change_pct', 0)), 1)
                except:
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
                'g0_change': g0_change,               # 历史0球赔率变化 {count, change_pct}
                'g0_change_diff': g0_change_diff,     # 0球变化幅度差异（与当前比赛）
            })

    # 计算当前比赛的近况之和（combined_avg）
    cur_combined_avg = None
    try:
        cur_rd = _extract_recent_matches(current_data)
        cur_rf = calc_recent_form(cur_rd)
        if cur_rf:
            cur_combined_avg = cur_rf.get('combined_avg')
    except Exception:
        pass

    # 提取当前比赛的0球变化供排序闭包使用
    cur_g0_change_ref = None
    cur_tc_tmp = current_data.get('ttg_change', {})
    if cur_tc_tmp and '0球' in cur_tc_tmp:
        cur_g0_change_ref = cur_tc_tmp['0球']

        # 排序：近况之和接近 > 0球赔率差值小 > 0球变化涨跌一致 > 相似度高
    def _sort_key(x):
        sim = x['similarity']
        g0_diff = x['g0_diff'] if x['g0_diff'] is not None else 9999

        # 维度1：近况之和差异（越小越优先，无数据排后面）
        his_rf = x.get('recent_form')
        his_avg = his_rf.get('combined_avg') if his_rf else None
        if cur_combined_avg is not None and his_avg is not None:
            form_diff = abs(cur_combined_avg - his_avg)
        else:
            form_diff = 9999

        # 维度3：赔率变化方向匹配
        g0_cur_chg = cur_g0_change_ref
        g0_his_chg = x.get('g0_change')
        cur_count = g0_cur_chg.get('count', 0) if g0_cur_chg else 0
        his_count = g0_his_chg.get('count', 0) if g0_his_chg else 0
        if cur_count == 0 and his_count == 0:
            dir_match = 0  # 双方都无变化，最一致
        elif cur_count == 0 or his_count == 0:
            dir_match = 1  # 一方有变化一方无，不一致
        else:
            cur_dir = (g0_cur_chg.get('change_pct', 0) > 0) - (g0_cur_chg.get('change_pct', 0) < 0)
            his_dir = (g0_his_chg.get('change_pct', 0) > 0) - (g0_his_chg.get('change_pct', 0) < 0)
            dir_match = 0 if cur_dir == his_dir else 1

        return (form_diff, g0_diff, dir_match, -sim)

    results.sort(key=_sort_key)
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
    <title>竞彩比分预测系统 v2.6.0</title>
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
        .btn-ai { background: #8b5cf6; color: #fff; border: 1px solid #7c3aed; border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; }
        .btn-ai:hover { background: #7c3aed; }
        .btn-ai.loading { background: #6d28d9; cursor: wait; }
        .btn-rec-stats { background: #059669; color: #fff; border: 1px solid #047857; border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; }
        .btn-rec-stats:hover { background: #047857; }
        .btn-rec-stats.done { background: #166534; border-color: #15803d; cursor: default; }
        /* V3.6 Analysis Modal */
        .v36-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 9999; display: flex; align-items: center; justify-content: center; }
        .v36-modal { background: #1a1a2e; border: 1px solid #4fc3f7; border-radius: 12px; max-width: 700px; width: 90%; max-height: 85vh; overflow-y: auto; padding: 0; color: #e0e0e0; font-size: 13px; }
        .v36-header { background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 16px 20px; border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 1; }
        .v36-header h3 { margin: 0; color: #4fc3f7; font-size: 16px; }
        .v36-close { background: #333; color: #fff; border: none; border-radius: 4px; padding: 4px 12px; cursor: pointer; font-size: 14px; }
        .v36-section { padding: 12px 20px; border-bottom: 1px solid #2a2a4a; }
        .v36-section h4 { color: #ff9800; margin: 0 0 8px 0; font-size: 14px; }
        .v36-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin: 2px; }
        .v36-big { background: #e65100; color: #fff; }
        .v36-small { background: #1565c0; color: #fff; }
        .v36-fuzzy { background: #666; color: #fff; }
        .v36-keep { background: #1b5e20; color: #fff; }
        .v36-exclude { background: #b71c1c; color: #fff; }
        .v36-iron { background: #0d47a1; color: #4fc3f7; }
        .v36-table { width: 100%; border-collapse: collapse; font-size: 12px; margin: 8px 0; }
        .v36-table th { background: #2a2a4a; color: #ccc; padding: 4px 8px; text-align: left; }
        .v36-table td { padding: 4px 8px; border-bottom: 1px solid #333; }
        .v36-warn { background: #4a1a1a; border-left: 3px solid #f44336; padding: 8px 12px; margin: 8px 0; border-radius: 4px; }
        .v36-info { background: #1a2a4a; border-left: 3px solid #4fc3f7; padding: 8px 12px; margin: 8px 0; border-radius: 4px; }
        .v36-rec { background: #1a3a1a; border: 2px solid #4caf50; padding: 12px; border-radius: 8px; text-align: center; margin-top: 8px; }
        .v36-rec strong { color: #4caf50; font-size: 18px; }
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
        /* 3个高置信度3球规律 - 醒目显示 */
        .final-rec-golden-3-20-21 { border: 3px solid #ffd700; box-shadow: 0 0 20px rgba(255,215,0,0.3); background: linear-gradient(135deg, #2d1f00 0%, #1a1200 100%); }
        .final-rec-super-3 { border: 3px solid #ff6b6b; box-shadow: 0 0 20px rgba(255,107,107,0.3); background: linear-gradient(135deg, #2d0000 0%, #1a0000 100%); }
        .final-rec-0-20-21-form { border: 3px solid #4ade80; box-shadow: 0 0 20px rgba(74,222,128,0.3); background: linear-gradient(135deg, #0d1a0d 0%, #0d1a0d 100%); }
        .final-rec-golden-3-20-21 .final-rec-title { color: #ffd700; font-size: 17px; }
        .final-rec-super-3 .final-rec-title { color: #ff6b6b; font-size: 17px; }
        .final-rec-0-20-21-form .final-rec-title { color: #4ade80; font-size: 17px; }
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
            background: linear-gradient(135deg, rgba(250,204,21,0.4), rgba(234,179,8,0.25));
            border: 2px solid #fde047;
            color: #fef08a !important;
            padding: 4px 12px;
            border-radius: 12px;
            animation: pulse-glow 2s ease-in-out infinite;
            box-shadow: 0 0 12px rgba(250,204,21,0.5);
            text-shadow: 0 0 6px rgba(250,204,21,0.8);
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
        .g3-warning-item { font-size: 12px; color: #ef4444; background: rgba(239,68,68,0.1); border-left: 3px solid #ef4444; padding: 5px 10px; border-radius: 0 6px 6px 0; margin-bottom: 4px; }
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
        let _CHANGE_HITRATE = __CHANGE_HITRATE_JSON__;
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
            return `<span class="hitrate-badge" style="font-size:10px;padding:1px 5px;border-radius:4px;margin-left:3px;background:${_HITRATE_COLORS[color]}22;color:${_HITRATE_COLORS[color]};border:1px solid ${_HITRATE_COLORS[color]}55" title="${tagTitle}">${rate}%</span>`;
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
        // 获取精确赔率匹配的场次数（供总进球区域显示"xx场"）
        function _getHitRateTotal(goalNum, oddsVal) {
            const exact = _ODDS_HITRATE.exact || {};
            const goalExact = exact[goalNum] || {};
            for (const [ekStr, d] of Object.entries(goalExact)) {
                const ek = parseFloat(ekStr);
                if (Math.abs(oddsVal - ek) < 0.01) {
                    return d.total;
                }
            }
            return null;
        }
        // 获取变化命中率标签（赔率变化统计区域用）
        function _getChangeHitRateLabel(goalNum, changePct) {
            if (!_CHANGE_HITRATE) return '';
            const goalData = _CHANGE_HITRATE[goalNum];
            if (!goalData) return '';
            // 计算bucket label
            let bl;
            if (changePct === 0) {
                bl = '0%不变';
            } else {
                const a = Math.abs(changePct);
                let lo = Math.floor(a);
                if (a === lo && lo > 0) lo -= 1; // 整数如25.0 → 24-25%
                const bucket = lo + '-' + (lo+1) + '%';
                bl = bucket + (changePct > 0 ? '涨' : '降');
            }
            const d = goalData[bl];
            if (!d || d.total < 1) return '';
            const rate = d.rate;
            const total = d.total;
            const hits = d.hits;
            let color;
            if (rate >= 40) color = 'green';
            else if (rate >= 25) color = 'yellow';
            else if (rate >= 15) color = 'gray';
            else color = 'red';
            return `<span class="change-hitrate-badge" style="font-size:10px;padding:1px 4px;border-radius:3px;display:block;margin-top:2px;background:${_HITRATE_COLORS[color]}22;color:${_HITRATE_COLORS[color]};border:1px solid ${_HITRATE_COLORS[color]}55;cursor:help" title="历史${total}场: ${goalNum}球命中${hits}次">${rate}%(${total}场)</span>`;
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
                const _missingHeader = !m.match_info.match_num_str;
                return `
                <div class="match-card">
                    <div class="match-header">
                        <span class="match-id">${m.match_info.match_num_str || ''}${m.match_info.match_num_str ? ' <span style="color:#666;font-size:11px;font-weight:normal">#' + m.match_id + '</span>' : '#' + m.match_id}</span>
                        <span style="color:#666;font-size:12px">${m.match_info.match_date ? m.match_info.match_date + ' ' : ''}${m.match_info.match_time || ''} ${m.match_info.match_status === 'Selling' ? '<span style="color:#22c55e;font-size:11px">●在售</span>' : ''}</span>
                        ${_missingHeader ? `<span onclick="openEditHeader(${m.match_id})" style="cursor:pointer;font-size:11px;color:#f59e0b;margin-left:6px;border:1px solid #f59e0b;border-radius:3px;padding:1px 5px">✏️补全</span>` : `<span onclick="openEditHeader(${m.match_id})" style="cursor:pointer;font-size:11px;color:#555;margin-left:6px;border:1px solid #333;border-radius:3px;padding:1px 5px" title="编辑抬头">✏️</span>`}
                    </div>
                    
                    <div style="text-align:center;margin-bottom:8px;font-size:13px;color:#aaa">
                        <span style="background:#1a1a3e;padding:2px 8px;border-radius:3px;margin-right:8px">${m.match_info.league_abbr || m.match_info.league || ''}</span>
                        ${m.match_info.home_rank ? '<span style="color:#f59e0b">' + m.match_info.home_rank + '</span>' : ''}
                        <span style="margin:0 6px;color:#555">vs</span>
                        ${m.match_info.away_rank ? '<span style="color:#f59e0b">' + m.match_info.away_rank + '</span>' : ''}
                    </div>
                    
                    <div class="teams">
                        ${m.match_info.home_team || '未知'} 
                        <span class="vs">VS</span> 
                        ${m.match_info.away_team || '未知'}
                    </div>
                    
                    <!-- 3球预测 -->
                    ${m.g3_prediction ? `
                    <div class="g3-prediction-box${m.g3_prediction.golden_3goals ? ' golden-box' : ''}">
                        ${m.near_form && m.near_form.home !== null ? `
                        <div style="font-size:13px;color:#e0e0e0;margin-bottom:6px;text-align:center;font-weight:bold">📊 近况: 主${m.near_form.home.toFixed(1)}/客${m.near_form.away.toFixed(1)}球 (近5场)</div>
                        ` : ''}
                        ${m.recent_matches ? `
                        <details style="font-size:11px;color:#aaa;margin-bottom:6px">
                          <summary style="cursor:pointer;color:#ccc;font-weight:bold">📋 近5场赛果</summary>
                          <div style="display:flex;gap:10px;margin-top:4px">
                            <!-- 主队 -->
                            <div style="flex:1;min-width:0">
                              <div style="color:#4fc3f7;margin-bottom:2px">▲ ${m.match_info.home_team}</div>
                              ${m.recent_matches.home.map(r => {
                                const cls = r.result === 'home' ? 'color:#4caf50' : r.result === 'away' ? 'color:#f44336' : 'color:#ff9800';
                                const lbl = r.result === 'home' ? 'W' : r.result === 'away' ? 'L' : 'D';
                                const venueTag = r.venue === '主' ? '<span style=\"color:#4fc3f7\">主</span>' : '<span style=\"color:#888\">客</span>';
                                return '<div style=\"white-space:nowrap;font-size:10px\">'+venueTag+' <span style=\"'+cls+'\">'+lbl+'</span> '+r.date.slice(5)+' '+r.score+' vs'+r.opponent+'</div>';
                              }).join('')}
                            </div>
                            <!-- 客队 -->
                            <div style="flex:1;min-width:0">
                              <div style="color:#ff9800;margin-bottom:2px">▼ ${m.match_info.away_team}</div>
                              ${m.recent_matches.away.map(r => {
                                const cls = r.result === 'home' ? 'color:#4caf50' : r.result === 'away' ? 'color:#f44336' : 'color:#ff9800';
                                const lbl = r.result === 'home' ? 'W' : r.result === 'away' ? 'L' : 'D';
                                const venueTag = r.venue === '主' ? '<span style=\"color:#4fc3f7\">主</span>' : '<span style=\"color:#888\">客</span>';
                                return '<div style=\"white-space:nowrap;font-size:10px\">'+venueTag+' <span style=\"'+cls+'\">'+lbl+'</span> '+r.date.slice(5)+' '+r.score+' vs'+r.opponent+'</div>';
                              }).join('')}
                            </div>
                          </div>
                        </details>
                        ` : ''}
                        <div class="g3-odds-info">
                            3球赔率: <strong>${m.g3_prediction.features['3球'] || '-'}</strong>
                            ${m.g3_prediction.features['区间'] ? `<span class="g3-tier">区间${m.g3_prediction.features['区间']}</span>` : ''}
                            &nbsp;|&nbsp;
                            0球: ${m.g3_prediction.features['0球'] || '-'}
                            &nbsp;|&nbsp;
                            1球: ${m.g3_prediction.features['1球'] || '-'}
                            &nbsp;|&nbsp;
                            2球: ${m.g3_prediction.features['2球'] || '-'}
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
                        ${m.g3_prediction.signals && m.g3_prediction.signals.some(s => s[0].includes('排除3球')) ? `
                        <div class="g3-exclude-banner">
                            <div class="g3-exclude-banner-text">🚫 排除3球 - 三条件全满足，历史3球率18.9%(7/37)</div>
                        </div>` : ''}
                        ${m.g3_prediction.signals && m.g3_prediction.signals.some(s => s[0].includes('排除2球') && s[2].includes('初始4球') && !s[2].includes('初始2球')) ? `
                        <div class="g3-exclude-banner" style="border-color:#f59e0b;background:linear-gradient(135deg,rgba(245,158,11,0.25),rgba(234,88,12,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#fcd34d;">🚫 排除2球 - 初始4球>=6.5（黄金2球排除B）</div>
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
                        ${m.g3_prediction.signals && m.g3_prediction.signals.some(s => s[0].includes('排除2球') && s[2].includes('100%准确')) ? `
                        <div class="g3-exclude-banner" style="border-color:#22c55e;background:linear-gradient(135deg,rgba(34,197,94,0.25),rgba(22,163,74,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#86efac;">🚫 排除2球 - 近况2.0-2.5+0球13-18，历史100%准确(0/11)</div>
                        </div>` : ''}
                        ${m.g3_prediction.warnings && m.g3_prediction.warnings.some(w => w.includes('排除2球') && w.includes('2球') && w.includes('4球') && w.includes('主让-1')) ? `
                        <div class="g3-exclude-banner" style="border-color:#f59e0b;background:linear-gradient(135deg,rgba(245,158,11,0.25),rgba(234,88,12,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#fcd34d;">🚫 排除2球 - 2球<3.3+4球>=6.5+主让-1，历史2球率8.3%</div>
                        </div>` : ''}
                        ${m.g3_prediction.signals && m.g3_prediction.signals.some(s => s[0].includes('排除2球') && s[2].includes('主让-1+让负')) ? `
                        <div class="g3-exclude-banner" style="border-color:#a855f7;background:linear-gradient(135deg,rgba(168,85,247,0.25),rgba(147,51,234,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#d8b4fe;">🚫 排除2球 - 主让-1+让负>=2.0+0球10-15，历史2球率10%(3/30)</div>
                        </div>` : ''}
                        ${m.g3_prediction.warnings && m.g3_prediction.warnings.some(w => w.includes('排除2球') && w.includes('HAD主胜')) ? `
                        <div class="g3-exclude-banner" style="border-color:#ef4444;background:linear-gradient(135deg,rgba(239,68,68,0.25),rgba(220,38,38,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#fca5a5;">🚫 排除2球 - 黄金2球+HAD主胜<2.0，主队过强，历史0%(0/3)</div>
                        </div>` : ''}
                        ${m.g3_prediction.warnings && m.g3_prediction.warnings.some(w => w.includes('排除2球') && w.includes('客近况')) ? `
                        <div class="g3-exclude-banner" style="border-color:#ef4444;background:linear-gradient(135deg,rgba(239,68,68,0.25),rgba(220,38,38,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#fca5a5;">🚫 排除2球 - 黄金2球+客近况>3.0，历史0%(0/3)</div>
                        </div>` : ''}
                        ${m.g3_prediction.warnings && m.g3_prediction.warnings.some(w => w.includes('排除2球') && w.includes('0球=23+2球=4.4')) ? `
                        <div class="g3-exclude-banner" style="border-color:#ef4444;background:linear-gradient(135deg,rgba(239,68,68,0.25),rgba(220,38,38,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#fca5a5;">🚫 排除2球 - 0球=23+2球=4.4+受让+1，历史0%(0/2)</div>
                        </div>` : ''}
                        ${m.g3_prediction.warnings && m.g3_prediction.warnings.some(w => w.includes('实操规律') && w.includes('排除3球')) ? `
                        <div class="g3-exclude-banner" style="border-color:#f59e0b;background:linear-gradient(135deg,rgba(245,158,11,0.25),rgba(234,88,12,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#fcd34d;">🔥 实操规律 - 排除3球 (让负1.7-2 + HAD<2 + 3球<2球)</div>
                            ${m.g3_prediction._rec_stats && m.g3_prediction._rec_stats.practical && m.g3_prediction._rec_stats.practical.practical_exclude_3 ? `
                            <div style="font-size:11px;color:#4ade80;margin-top:2px">📊 ${m.g3_prediction._rec_stats.practical.practical_exclude_3}</div>` : ''}
                        </div>` : ''}
                        ${m.g3_prediction.warnings && m.g3_prediction.warnings.some(w => w.includes('实操规律') && w.includes('推荐3球')) ? `
                        <div class="g3-exclude-banner" style="border-color:#8b5cf6;background:linear-gradient(135deg,rgba(139,92,246,0.25),rgba(109,40,217,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#c4b5fd;">👍 实操规律 - 推荐3球 (让负<1.7 + 3球3.3-3.5 + 3球<2球)</div>
                            ${m.g3_prediction._rec_stats && m.g3_prediction._rec_stats.practical && m.g3_prediction._rec_stats.practical.practical_recommend_3 ? `
                            <div style="font-size:11px;color:#4ade80;margin-top:2px">📊 ${m.g3_prediction._rec_stats.practical.practical_recommend_3}</div>` : ''}
                        </div>` : ''}
                        ${m.g3_prediction.warnings && m.g3_prediction.warnings.some(w => w.includes('实操规律') && w.includes('排除2球')) ? `
                        <div class="g3-exclude-banner" style="border-color:#ef4444;background:linear-gradient(135deg,rgba(239,68,68,0.25),rgba(220,38,38,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#fca5a5;">🔥 实操规律 - 排除2球 (HAD<1.8 + 2球<3.3)</div>
                            ${m.g3_prediction._rec_stats && m.g3_prediction._rec_stats.practical && m.g3_prediction._rec_stats.practical.practical_exclude_2 ? `
                            <div style="font-size:11px;color:#4ade80;margin-top:2px">📊 ${m.g3_prediction._rec_stats.practical.practical_exclude_2}</div>` : ''}
                        </div>` : ''}
                        ${m.g3_prediction.warnings && m.g3_prediction.warnings.some(w => w.includes('实操规律') && w.includes('推荐2球')) ? `
                        <div class="g3-exclude-banner" style="border-color:#22c55e;background:linear-gradient(135deg,rgba(34,197,94,0.25),rgba(22,163,74,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#86efac;">👍 实操规律 - 推荐2球 (0球<12 + HAD>=2.8 + 3球>=3.8)</div>
                            ${m.g3_prediction._rec_stats && m.g3_prediction._rec_stats.practical && m.g3_prediction._rec_stats.practical.practical_recommend_2 ? `
                            <div style="font-size:11px;color:#4ade80;margin-top:2px">📊 ${m.g3_prediction._rec_stats.practical.practical_recommend_2}</div>` : ''}
                        </div>` : ''}
                        ${m.g3_prediction.warnings && m.g3_prediction.warnings.some(w => w.includes('实操规律') && w.includes('排除1球')) ? `
                        <div class="g3-exclude-banner" style="border-color:#ef4444;background:linear-gradient(135deg,rgba(239,68,68,0.25),rgba(220,38,38,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#fca5a5;">🔥 实操规律 - 排除1球 (3球<3.5 + 1球>5.0)</div>
                        </div>` : ''}
                        ${m.g3_prediction.warnings && m.g3_prediction.warnings.some(w => w.includes('实操规律') && w.includes('排除4球')) ? `
                        <div class="g3-exclude-banner" style="border-color:#ef4444;background:linear-gradient(135deg,rgba(239,68,68,0.25),rgba(220,38,38,0.15));">
                            <div class="g3-exclude-banner-text" style="color:#fca5a5;">🔥 实操规律 - 排除4球 (0球<10 + 4球>6.0)</div>
                        </div>` : ''}
                        ${m.g3_prediction.signals && m.g3_prediction.signals.some(s => s[0].includes('考虑0球')) ? `
                        <div class="g3-exclude-banner" style="border-color:#64748b;background:linear-gradient(135deg,rgba(100,116,139,0.20),rgba(71,85,105,0.10));">
                            <div class="g3-exclude-banner-text" style="color:#cbd5e1;">⚠️ 考虑0球 - 近况偏低+高球多降+0球≥13</div>
                        </div>` : ''}
                        ${m.g3_prediction.warnings && m.g3_prediction.warnings.some(w => w.includes('排除4球') && w.includes('近况')) ? `
                        <div class="g3-exclude-banner" style="border-color:#ef4444;background:linear-gradient(135deg,rgba(239,68,68,0.22),rgba(220,38,38,0.12));">
                            <div class="g3-exclude-banner-text" style="color:#fca5a5;">🚫 排除4球 - 近况<2.0，历史4球率0%(0/12)</div>
                        </div>` : ''}
                        ${m.g3_prediction.warnings && m.g3_prediction.warnings.some(w => w.includes('排除4球') && w.includes('0球=')) ? `
                        <div class="g3-exclude-banner" style="border-color:#ef4444;background:linear-gradient(135deg,rgba(239,68,68,0.22),rgba(220,38,38,0.12));">
                            <div class="g3-exclude-banner-text" style="color:#fca5a5;">🚫 排除4球 - 0球>30极高，历史4球率5.3%(1/19)</div>
                        </div>` : ''}
                        ${m.g3_prediction.warnings && m.g3_prediction.warnings.some(w => w.includes('排除4球') && w.includes('4球赔率')) ? `
                        <div class="g3-exclude-banner" style="border-color:#ef4444;background:linear-gradient(135deg,rgba(239,68,68,0.22),rgba(220,38,38,0.12));">
                            <div class="g3-exclude-banner-text" style="color:#fca5a5;">🚫 排除4球 - 4球赔率>6.0，历史4球率6.7%(5/75)</div>
                        </div>` : ''}
                        ${m.g3_prediction.warnings && m.g3_prediction.warnings.some(w => w.includes('排除1球') && w.includes('近况均值')) ? `
                        <div class="g3-exclude-banner" style="border-color:#ef4444;background:linear-gradient(135deg,rgba(239,68,68,0.22),rgba(220,38,38,0.12));">
                            <div class="g3-exclude-banner-text" style="color:#fca5a5;">🚫 排除1球 - 近况均值>=3.5，历史1球率7.6%(79场)</div>
                        </div>` : ''}
                        ${m.g3_prediction.warnings && m.g3_prediction.warnings.some(w => w.includes('排除1球') && w.includes('1球赔率=')) ? `
                        <div class="g3-exclude-banner" style="border-color:#ef4444;background:linear-gradient(135deg,rgba(239,68,68,0.22),rgba(220,38,38,0.12));">
                            <div class="g3-exclude-banner-text" style="color:#fca5a5;">🚫 排除1球 - 1球赔率>8.0，历史1球率8.9%(45场)</div>
                        </div>` : ''}
                        ${m.g3_prediction.final_rec && m.g3_prediction.final_rec.signal_type === '让负+3球黄金' ? `
                        <div class="g3-exclude-banner" style="border-color:#ffd700;background:linear-gradient(135deg,rgba(255,215,0,0.22),rgba(184,134,11,0.12));">
                            <div class="g3-exclude-banner-text" style="color:#ffd700;">🎯 让负1.50-1.70+3球3.3-3.5 → 历史55.6%(10/18) | 比分:2:1/1:2/3:0</div>
                            ${m.g3_prediction._rec_stats && m.g3_prediction._rec_stats.exclude && m.g3_prediction._rec_stats.exclude.final_3gold ? `
                            <div style="font-size:11px;color:#4ade80;margin-top:2px">📊 ${m.g3_prediction._rec_stats.exclude.final_3gold}</div>` : ''}
                        </div>` : ''}
                        ${m.g3_prediction.final_rec && m.g3_prediction.final_rec.signal_type === '让负区间3球' ? `
                        <div class="g3-exclude-banner" style="border-color:#fbbf24;background:linear-gradient(135deg,rgba(251,191,36,0.18),rgba(217,119,6,0.1));">
                            <div class="g3-exclude-banner-text" style="color:#fde68a;">🎯 让负1.50-1.70+主让-1 → 通用3球信号 历史35.7%(25/70)</div>
                            ${m.g3_prediction._rec_stats && m.g3_prediction._rec_stats.exclude && m.g3_prediction._rec_stats.exclude.final_3gen ? `
                            <div style="font-size:11px;color:#4ade80;margin-top:2px">📊 ${m.g3_prediction._rec_stats.exclude.final_3gen}</div>` : ''}
                            ${m.g3_prediction._rec_stats && m.g3_prediction._rec_stats.exclude && m.g3_prediction._rec_stats.exclude.final_0_20_21 && m.g3_prediction.final_rec && m.g3_prediction.final_rec.signal_type === '0球20-21+近况2.5-3.5' ? `
                            <div style="font-size:11px;color:#4ade80;margin-top:2px">📊 ${m.g3_prediction._rec_stats.exclude.final_0_20_21}</div>` : ''}
                            ${m.g3_prediction._rec_stats && m.g3_prediction._rec_stats.exclude && m.g3_prediction._rec_stats.exclude.final_golden_3_20_21 && m.g3_prediction.final_rec && m.g3_prediction.final_rec.signal_type === '黄金3球+0球20-21' ? `
                            <div style="font-size:11px;color:#4ade80;margin-top:2px">📊 ${m.g3_prediction._rec_stats.exclude.final_golden_3_20_21}</div>` : ''}
                            ${m.g3_prediction._rec_stats && m.g3_prediction._rec_stats.exclude && m.g3_prediction._rec_stats.exclude.final_form_high_drop && m.g3_prediction.final_rec && m.g3_prediction.final_rec.signal_type === '近况+高球降' ? `
                            <div style="font-size:11px;color:#4ade80;margin-top:2px">📊 ${m.g3_prediction._rec_stats.exclude.final_form_high_drop}</div>` : ''}
                        </div>` : ''}
                        ${m.g3_prediction.final_rec && m.g3_prediction.final_rec.signal_type === '排除3球(客近况极低)' ? `
                        <div class="g3-exclude-banner">
                            <div class="g3-exclude-banner-text">🚫 排除3球 - 客近况<2.0 历史3球率仅6.2%(1/16)</div>
                        </div>` : ''}
                        ${m.g3_prediction.final_rec && m.g3_prediction.final_rec.signal_type === '排除3球(平赔降)' ? `
                        <div class="g3-exclude-banner">
                            <div class="g3-exclude-banner-text">🚫 排除3球 - HAD平赔降>3% 历史3球率9.1%(1/11)</div>
                        </div>` : ''}
                        ${m.g3_prediction.final_rec && m.g3_prediction.final_rec.signal_type === '排除3球(0球高+客近况低)' ? `
                        <div class="g3-exclude-banner">
                            <div class="g3-exclude-banner-text">🚫 排除3球 - 0球>=15+客近况<2.5 历史3球率11.1%(2/18)</div>
                        </div>` : ''}
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
                    ${m.g3_prediction && m.g3_prediction.final_rec && (m.g3_prediction.final_rec.is_bet || (m.g3_prediction.final_rec.signal_type && m.g3_prediction.final_rec.signal_type !== '关注3球(观望)' && !m.g3_prediction.final_rec.signal_type.includes('观望'))) ? `
                    <div class="final-rec-box ${m.g3_prediction.final_rec.signal_type === '黄金3球+0球20-21' ? 'final-rec-golden-3-20-21' :
                      m.g3_prediction.final_rec.signal_type === '超级3球' ? 'final-rec-super-3' :
                      m.g3_prediction.final_rec.signal_type === '0球20-21+近况2.5-3.5' ? 'final-rec-0-20-21-form' :
                      (m.g3_prediction.final_rec.is_bet ? 'final-rec-bet' : m.g3_prediction.final_rec.recommendation === '不投注' ? 'final-rec-no-bet' : 'final-rec-watch')}">
                        <div class="final-rec-title">
                            ${m.g3_prediction.final_rec.signal_type === '黄金3球+0球20-21' ? '⭐⭐⭐ 黄金3球+0球20-21 (70.0%)' :
                              m.g3_prediction.final_rec.signal_type === '超级3球' ? '⭐⭐ 超级3球 (60.0%)' :
                              m.g3_prediction.final_rec.signal_type === '0球20-21+近况2.5-3.5' ? '⭐ 0球20-21+近况2.5-3.5 (53.3%)' :
                              (m.g3_prediction.final_rec.recommendation === '不投注' ? '❌ 建议不投注' :
                               m.g3_prediction.final_rec.is_bet ? '✅ 建议投注' : '👁️ 观望')}
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
                                ${(m.g3_prediction.final_rec.recommendation || '').includes('排除') ? '历史3球率' : '回测命中率'}: <span class="${m.g3_prediction.final_rec.hit_rate >= 50 ? 'hit-rate-high' : m.g3_prediction.final_rec.hit_rate >= 35 ? 'hit-rate-mid' : 'hit-rate-low'}">${m.g3_prediction.final_rec.hit_rate}%</span>
                                ${m.g3_prediction.final_rec.sample_size ? `(${Math.round(m.g3_prediction.final_rec.hit_rate/100*m.g3_prediction.final_rec.sample_size)}/${m.g3_prediction.final_rec.sample_size}场)` : ''}
                            </div>
                            ` : ''}
                            ${(() => {
                                if (!m.g3_prediction._rec_stats || !m.g3_prediction._rec_stats.exclude || !m.g3_prediction.final_rec) return '';
                                const st = m.g3_prediction.final_rec.signal_type || '';
                                const key = 'final_' + (st || 'x').replace(/[^\w\u4e00-\u9fff+\-]/g, '_').replace(/_+/g, '_');
                                const val = m.g3_prediction._rec_stats.exclude[key];
                                return val ? `<div style="font-size:11px;color:#4ade80;margin-top:2px">📊 ${val}</div>` : '';
                            })()}
                        </div>
                    </div>
                    ` : ''}

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
                    ${(m.g3_prediction.golden_1goals && m.g3_prediction.golden_1goals.is_golden_1) || (m.g3_prediction.golden_2goals && m.g3_prediction.golden_2goals.is_golden_2) || (m.g3_prediction.golden_4goals && m.g3_prediction.golden_4goals.is_golden_4) ? `
                    <div class="g3-prediction-box">
                        <div class="g3-prediction-title">🎯 黄金进球信号</div>
                        ${m.g3_prediction.golden_1goals && m.g3_prediction.golden_1goals.is_golden_1 ? `
                        <div class="golden-recommendation">⭐ 黄金1球信号</div>
                        <div class="golden-detail">
                            ${m.g3_prediction.golden_1goals.reason || ''}
                        </div>
                        ${m.g3_prediction.golden_1goals.hit_rate !== null ? `
                        <div class="golden-hitrate">
                            <span class="hit-rate-high">历史命中率: ${m.g3_prediction.golden_1goals.hit_rate}%</span>
                            ${m.g3_prediction.golden_1goals.sample_size ? `(样本${m.g3_prediction.golden_1goals.sample_size}场)` : ''}
                        </div>` : ''}
                        ${m.g3_prediction._rec_stats && m.g3_prediction._rec_stats.golden && m.g3_prediction._rec_stats.golden.golden_1goals ? `
                        <div style="font-size:11px;color:#4ade80;margin-top:2px">📊 ${m.g3_prediction._rec_stats.golden.golden_1goals}</div>` : ''}
                        <div style="font-size:11px;color:#94a3b8;margin-top:4px">比分: 1:0 / 0:1</div>
                        ` : ''}
                        ${m.g3_prediction.golden_2goals && m.g3_prediction.golden_2goals.is_golden_2 ? `
                        <div class="golden-2-box">
                            <div class="golden-recommendation" style="color:#94a3b8;">📋 参考2球信号</div>
                            <div class="golden-reason">
                                ${m.g3_prediction.golden_2goals.reason || ''}
                            </div>
                            ${m.g3_prediction.golden_2goals.hit_rate !== null ? `
                            <div class="golden-stats">
                                <span class="hit-rate-high">历史命中率: ${m.g3_prediction.golden_2goals.hit_rate}%</span>
                                ${m.g3_prediction.golden_2goals.sample_size ? `(样本${m.g3_prediction.golden_2goals.sample_size}场)` : ''}
                            </div>
                            ` : ''}
                            ${m.g3_prediction._rec_stats && m.g3_prediction._rec_stats.golden && m.g3_prediction._rec_stats.golden.golden_2goals ? `
                            <div style="font-size:11px;color:#4ade80;margin-top:2px">📊 ${m.g3_prediction._rec_stats.golden.golden_2goals}</div>` : ''}
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
                            ${m.g3_prediction._rec_stats && m.g3_prediction._rec_stats.golden && m.g3_prediction._rec_stats.golden.golden_4goals ? `
                            <div style="font-size:11px;color:#4ade80;margin-top:2px">📊 ${m.g3_prediction._rec_stats.golden.golden_4goals}</div>` : ''}
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
                            <button class="btn-ai" onclick="runV36Analysis('${m.match_id}')">🧠 AI推理</button>
                            <button class="btn-rec-stats" id="btn-stats-${m.match_id}" onclick="updateRecStats('${m.match_id}')">📊 推荐统计</button>
                            ${m.g3_prediction && m.g3_prediction.final_rec && m.g3_prediction.final_rec.big3_vs_small3 && m.g3_prediction.final_rec.big3_vs_small3.signal_type ? `
                            <button class="btn-pattern" onclick="togglePatternStats('${m.match_id}', '${m.g3_prediction.final_rec.big3_vs_small3.signal_type}')">📊 命中率</button>
                            ` : ''}
                        </div>
                        <!-- 大小球输入行 -->
                        <div class="score-input-row" style="margin-top:8px">
                            <span class="score-label">大小球:</span>
                            <input type="number" class="score-input" id="over-odds-${m.match_id}" min="0" max="10" step="0.01" placeholder="大球水位" value="${m.over_under && m.over_under.over_odds ? m.over_under.over_odds : ''}" style="width:90px;padding:4px;border:1px solid #ccc;border-radius:3px">
                            <input type="number" class="score-input" id="ou-line-${m.match_id}" min="0" max="10" step="0.1" placeholder="大小球数值" value="${m.over_under && m.over_under.ou_line ? m.over_under.ou_line : ''}" style="width:90px;padding:4px;border:1px solid #ccc;border-radius:3px;margin-left:5px">
                            <input type="number" class="score-input" id="under-odds-${m.match_id}" min="0" max="10" step="0.01" placeholder="小球水位" value="${m.over_under && m.over_under.under_odds ? m.over_under.under_odds : ''}" style="width:90px;padding:4px;border:1px solid #ccc;border-radius:3px;margin-left:5px">
                            <button class="btn-save-score" onclick="saveOverUnder('${m.match_id}')" style="margin-left:5px">💾 保存</button>
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
                            <div class="odds-item ${getOddsClass(m.had['胜'])}"><div class="label">主胜</div><div class="value">${m.had['胜'] || '-'}${_getHADChangeTag(m, '胜')}</div></div>
                            <div class="odds-item ${getOddsClass(m.had['平'])}"><div class="label">平局</div><div class="value">${m.had['平'] || '-'}${_getHADChangeTag(m, '平')}</div></div>
                            <div class="odds-item ${getOddsClass(m.had['负'])}"><div class="label">客胜</div><div class="value">${m.had['负'] || '-'}${_getHADChangeTag(m, '负')}</div></div>
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
                                const hitTotal = _getHitRateTotal(goalNum, odds); // 获取精确赔率匹配的场次数
                                const change = m.ttg_change && m.ttg_change[k];
                                let changeTag = '';
                                let sampleTag = '';
                                let goldTag = '';
                                // 变化方向+幅度
                                if (change && change.count > 0) {
                                    const pct = change.change_pct;
                                    const isUp = pct > 0;
                                    const color = isUp ? '#ef4444' : '#22c55e';
                                    const arrow = isUp ? '↑' : '↓';
                                    changeTag = `<span class="odds-change-tag" style="color:${color}">${arrow}${Math.abs(pct)}%</span>`;
                                }
                                // 样本场次数（精确赔率匹配：该进球数在此赔率下的历史比赛数）
                                if (hitTotal !== null && hitTotal > 0) {
                                    // 颜色分级：≥10场醒目，3-9场中等，<3场灰色
                                    let sColor, sBg, sBorder;
                                    if (hitTotal >= 10) {
                                        sColor = '#4ade80'; sBg = '#4ade8022'; sBorder = '#4ade8055';
                                    } else if (hitTotal >= 3) {
                                        sColor = '#facc15'; sBg = '#facc1522'; sBorder = '#facc1555';
                                    } else {
                                        sColor = '#888'; sBg = '#88822222'; sBorder = '#88855555';
                                    }
                                    sampleTag = `<span class="change-hitrate-badge" style="font-size:10px;padding:1px 4px;border-radius:3px;display:block;margin-top:2px;background:${sBg};color:${sColor};border:1px solid ${sBorder};cursor:help" title="历史${hitTotal}场比赛中，${goalNum}球赔率为${odds}">(${hitTotal}场)</span>`;
                                }
                                // 黄金信号：命中率>=50%
                                if (hitRate !== null && hitRate >= 50) {
                                    goldTag = '<span class="odds-tag gold">&#9733;黄金</span>';
                                }
                                const tagClass = (goldTag ? ' gold-highlight' : '');
                                return `<div class="odds-item ${getOddsClass(v)} ${tagClass}"><div class="label">${k}</div><div class="value">${v}${rateLabel}${changeTag}</div><div class="odds-tags">${goldTag}${sampleTag}</div></div>`;
                            }).join('')}
                        </div>
                    </div>
                    ` : ''}

                    <!-- 让球胜平负 -->
                    ${m.hhad && m.hhad.让球 ? `
                    <div class="odds-section">
                        <div class="odds-title">让球(${m.hhad.让球})胜平负</div>
                        <div class="odds-grid">
                            <div class="odds-item ${getOddsClass(m.hhad.让胜)}"><div class="label">让胜</div><div class="value">${m.hhad.让胜 || '-'}${_getHHADChangeTag(m, '让胜')}</div></div>
                            <div class="odds-item ${getOddsClass(m.hhad.让平)}"><div class="label">让平</div><div class="value">${m.hhad.让平 || '-'}${_getHHADChangeTag(m, '让平')}</div></div>
                            <div class="odds-item ${getOddsClass(m.hhad.让负)}"><div class="label">让负</div><div class="value">${m.hhad.让负 || '-'}${_getHHADChangeTag(m, '让负')}</div></div>
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
                                ${h.hints.map(tip => `<div style="color:${tip.includes('⚠️') ? '#ef4444' : '#cbd5e1'};margin:2px 0 2px 4px;">• ${tip}</div>`).join('')}
                                ${h.mid_hints && h.mid_hints.length > 0 ? `
                                <div style="margin-top:6px;padding:4px 8px;background:rgba(251,191,36,0.12);border:1px solid rgba(251,191,36,0.3);border-radius:4px;">
                                    ${h.mid_hints.map(tip => `<div style="color:${tip.includes('⚠️') ? '#ef4444' : '#fbbf24'};font-size:11px;margin:2px 0;">• ${tip}</div>`).join('')}
                                </div>` : ''}
                                ${h.midlow_hints && h.midlow_hints.length > 0 ? `
                                <div style="margin-top:6px;padding:4px 8px;background:rgba(251,191,36,0.12);border:1px solid rgba(251,191,36,0.3);border-radius:4px;">
                                    ${h.midlow_hints.map(tip => `<div style="color:${tip.includes('⚠️') ? '#ef4444' : '#fbbf24'};font-size:11px;margin:2px 0;">• ${tip}</div>`).join('')}
                                </div>` : ''}
                                ${h.high_hints && h.high_hints.length > 0 ? `
                                <div style="margin-top:6px;padding:4px 8px;background:rgba(251,191,36,0.12);border:1px solid rgba(251,191,36,0.3);border-radius:4px;">
                                    ${h.high_hints.map(tip => `<div style="color:${tip.includes('⚠️') ? '#ef4444' : '#fbbf24'};font-size:11px;margin:2px 0;">• ${tip}</div>`).join('')}
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

                    <!-- 主让+让负低赔规律（217场回测） -->
                    ${m.hhad_lose_hint && m.hhad_lose_hint.active ? (() => {
                        const h = m.hhad_lose_hint;
                        const isExclude = h.pick === '排除让负';
                        const isRecommend = h.pick === '让负';
                        const isWatch = h.pick === '观望';
                        const tierColors = {
                            'S': { bg: 'rgba(239,68,68,0.15)', border: 'rgba(239,68,68,0.5)', title: '#ef4444' },
                            'A': { bg: 'rgba(249,115,22,0.15)', border: 'rgba(249,115,22,0.5)', title: '#f97316' },
                            'B': { bg: 'rgba(234,179,8,0.12)', border: 'rgba(234,179,8,0.4)', title: '#eab308' },
                            'C': { bg: 'rgba(100,116,139,0.12)', border: 'rgba(100,116,139,0.3)', title: '#94a3b8' },
                            'D': { bg: 'rgba(100,116,139,0.10)', border: 'rgba(100,116,139,0.25)', title: '#64748b' },
                            'E': { bg: 'rgba(168,85,247,0.12)', border: 'rgba(168,85,247,0.4)', title: '#a855f7' },
                        };
                        const tc = tierColors[h.tier] || tierColors['D'];
                        const pickBg = isExclude ? 'rgba(168,85,247,0.25)' : isRecommend ? 'rgba(34,197,94,0.25)' : 'rgba(100,116,139,0.2)';
                        const pickColor = isExclude ? '#a855f7' : isRecommend ? '#22c55e' : '#94a3b8';
                        const pickIcon = isExclude ? '🚫' : isRecommend ? '✅' : '👀';
                        return `
                    <div class="odds-section">
                        <div style="background:${tc.bg};border:1px solid ${tc.border};border-radius:8px;padding:10px 12px;font-size:12px;">
                            <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
                                <span style="background:${tc.bg};color:${tc.title};padding:2px 6px;border-radius:4px;font-weight:bold;font-size:11px;border:1px solid ${tc.border};">${h.tier}级</span>
                                <span style="color:${tc.title};font-weight:bold;font-size:13px;">让负低赔规律</span>
                                <span style="color:#64748b;font-size:11px;">让负${h.lose_odds}</span>
                            </div>
                            <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
                                <span style="background:${pickBg};color:${pickColor};padding:2px 8px;border-radius:4px;font-weight:bold;font-size:12px;">${pickIcon} ${h.pick}</span>
                                <span style="color:#94a3b8;">置信度 ${h.confidence}%</span>
                            </div>
                            ${h.reasons.map(r => {
                                const isWarn = r.includes('✖');
                                const isUp = r.includes('★') || r.includes('↑');
                                const clr = isWarn ? '#f43f5e' : isUp ? '#22c55e' : '#cbd5e1';
                                return `<div style="color:${clr};margin:2px 0 2px 4px;font-size:11px;line-height:1.5;">${r}</div>`;
                            }).join('')}
                            <div style="color:#475569;font-size:10px;margin-top:6px;border-top:1px solid rgba(100,116,139,0.15);padding-top:4px;">
                                主让+让负<2.0 | 217场回测 | 近况细分决策树
                            </div>
                        </div>
                    </div>`;
                    })() : ''}

                    <!-- 平局信号（所有had.平区间） -->
                    ${m.draw_hint && m.draw_hint.active ? `
                    <div class="odds-section">
                        ${drawHintHtml(m.draw_hint)}
                    </div>
                    ` : ''}

                    <!-- 排除平局分析（football_web逻辑） -->
                    ${m.draw_exclusion && m.draw_exclusion.active ? `
                    <div class="odds-section">
                        ${drawExclusionHtml(m.draw_exclusion)}
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
                    ${(m.ttg_change && Object.keys(m.ttg_change).length > 0) || (m.hafu_change && Object.keys(m.hafu_change).length > 0) || (m.had_change && Object.keys(m.had_change).length > 0) || (m.hhad_change && Object.keys(m.hhad_change).length > 0) ? `
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
                                        const goalNum = parseInt(k.replace('球',''));
                                        const chgRateLabel = _getChangeHitRateLabel(goalNum, v.change_pct);
                                        return `<div class="change-item ${cls}">
                                            <div class="change-label">${k}</div>
                                            <div class="change-value">${v.count}次 ${arrow}${Math.abs(v.change_pct)}%${chgRateLabel}</div>
                                        </div>`;
                                    }).join('')}
                                </div>
                            </div>
                            ` : ''}
                            ${m.had_change && Object.keys(m.had_change).length > 0 ? `
                            <div class="change-category">
                                <div class="change-subtitle">胜平负变化</div>
                                <div class="change-grid">
                                    ${Object.entries(m.had_change || {}).map(([k, v]) => {
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
                            ${m.hhad_change && Object.keys(m.hhad_change).length > 0 ? `
                            <div class="change-category">
                                <div class="change-subtitle">让球胜平负变化</div>
                                <div class="change-grid">
                                    ${Object.entries(m.hhad_change || {}).map(([k, v]) => {
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

        // ── 生成AI推理Prompt ─────────────────────────────
        async function generateAIPrompt(matchId) {
            const btn = event.target;
            const originalText = btn.innerHTML;
            btn.innerHTML = '⏳ 生成中...';
            btn.disabled = true;

            try {
                const res = await fetch(`/api/ai/generate_prompt/${matchId}`);
                const data = await res.json();

                if (!data.success) {
                    alert('生成失败：' + (data.error || '未知错误'));
                    return;
                }

                // 创建模态框显示Prompt
                const overlay = document.createElement('div');
                overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center;';
                overlay.onclick = (e) => { if (e.target === overlay) document.body.removeChild(overlay); };

                const modal = document.createElement('div');
                modal.style.cssText = 'background:#1a1a2e;color:#e0e0e0;width:90%;max-width:800px;max-height:85vh;overflow:auto;padding:24px;border-radius:12px;border:1px solid #0f3460;';

                modal.innerHTML = `
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                        <h3 style="margin:0;color:#00d4ff;">🧠 AI推理 Prompt</h3>
                        <button onclick="document.body.removeChild(this.closest('div').parentElement)" style="background:none;border:none;color:#888;font-size:20px;cursor:pointer;">✕</button>
                    </div>
                    <p style="color:#888;font-size:12px;margin-bottom:12px;">复制下方内容，粘贴到AI对话框（如WorkBuddy），AI会按照"推理流水框架"进行推理。</p>
                    <textarea id="ai-prompt-text" style="width:100%;height:400px;background:#0a0a1a;color:#4ade80;border:1px solid #0f3460;border-radius:8px;padding:12px;font-family:monospace;font-size:12px;resize:vertical;white-space:pre-wrap;">${data.prompt}</textarea>
                    <div style="margin-top:12px;display:flex;gap:10px;">
                        <button onclick="copyAIPrompt()" style="background:#00d4ff;color:#1a1a2e;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;font-weight:bold;">📋 一键复制</button>
                        <button onclick="downloadAIPrompt()" style="background:#0f3460;color:#00d4ff;border:1px solid #00d4ff;padding:8px 20px;border-radius:6px;cursor:pointer;">💾 下载为文件</button>
                        <button onclick="document.body.removeChild(this.closest('div').parentElement.parentElement)" style="background:#333;color:#888;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">关闭</button>
                    </div>
                `;

                overlay.appendChild(modal);
                document.body.appendChild(overlay);

                // 全局函数：复制Prompt
                window.copyAIPrompt = function() {
                    const textarea = document.getElementById('ai-prompt-text');
                    textarea.select();
                    document.execCommand('copy');
                    const btn = document.querySelector('button[onclick="copyAIPrompt()"');
                    const original = btn.innerHTML;
                    btn.innerHTML = '✅ 已复制！';
                    setTimeout(() => btn.innerHTML = original, 2000);
                };

                // 全局函数：下载Prompt为文件
                window.downloadAIPrompt = function() {
                    const text = document.getElementById('ai-prompt-text').value;
                    const blob = new Blob([text], { type: 'text/plain' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `AI推理Prompt_${matchId}.txt`;
                    a.click();
                    URL.revokeObjectURL(url);
                };

            } catch (err) {
                alert('生成失败：' + err.message);
            } finally {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        }

        // ── V3.6 自动推理分析 ─────────────────────────────
        async function runV36Analysis(matchId) {
            const btn = event.target;
            const orig = btn.innerHTML;
            btn.innerHTML = '⏳ V3.6分析中...';
            btn.classList.add('loading');
            btn.disabled = true;

            try {
                // Get match card data from API
                const mRes = await fetch('/api/matches?light=1');
                const matches = await mRes.json();
                const match = matches.find(m => String(m.match_id) === String(matchId));
                if (!match) { alert('未找到比赛数据'); return; }
                
                // POST to V3.6 endpoint
                const res = await fetch('/v36/analyze/' + matchId, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(match)
                });
                const data = await res.json();
                if (!data.success) { alert('分析失败: ' + data.error); return; }

                const a = data.analysis;
                const dirTag = a.step0.direction === '大球' ? 'v36-big' : (a.step0.direction === '小球' ? 'v36-small' : 'v36-fuzzy');
                
                let vetoHtml = '';
                if (a.veto) {
                    vetoHtml = '<div class="v36-warn"><strong>🚨 方向否决!</strong> ' + a.veto.reason + '</div>';
                }
                
                let heatHtml = '';
                if (a.heat_check && a.heat_check.triggered) {
                    heatHtml = '<div class="v36-warn"><strong>🔥 造热排除!</strong> ' + a.heat_check.goal + '五信号全指向→排除</div>';
                }

                let exclRows = '';
                for (let e of a.exclusion.kept) {
                    const cls = e.status.includes('铁保留') ? 'v36-iron' : 'v36-keep';
                    exclRows += '<tr><td>' + e.goal + '</td><td><span class="v36-badge ' + cls + '">' + e.status + '</span></td><td>' + e.hit + '</td></tr>';
                }
                for (let e of a.exclusion.excluded) {
                    exclRows += '<tr><td>' + e.goal + '</td><td><span class="v36-badge v36-exclude">排除</span></td><td>' + e.reason + '</td></tr>';
                }

                let scoreHtml = '';
                for (let sc of a.score_candidates) {
                    scoreHtml += '<div style="margin:4px 0"><strong>' + sc.total_goals + '球</strong>: ';
                    scoreHtml += sc.scores.map(s => s.score + ' ' + s.tag + ' [' + s.h_capable + s.a_capable + ']').join(' | ');
                    scoreHtml += '</div>';
                }

                let reviewHtml = '';
                if (a.final_review.triggered) {
                    reviewHtml = '<div class="v36-warn"><strong>⚠️ 终审触发!</strong> ' + a.final_review.upset.join('; ') + '</div>';
                }

                let warnHtml = a.review_warnings.map(w => '<div class="v36-warn">' + w + '</div>').join('');

                const rec = a.recommended;
                const overlay = document.createElement('div');
                overlay.className = 'v36-overlay';
                overlay.onclick = function(e) { if (e.target === this) document.body.removeChild(this); };

                overlay.innerHTML = '<div class="v36-modal">'
                    + '<div class="v36-header">'
                    + '<h3>🧠 V3.6 推理分析 — ' + a.match_info.home_team + ' vs ' + a.match_info.away_team + '</h3>'
                    + '<button class="v36-close" id="v36-close-btn">✕</button>'
                    + '</div>'
                    + '<div class="v36-section">'
                    + '<h4>📊 近况摘要</h4>'
                    + '近况均球: ' + a.recent_summary.combined_avg.toFixed(1) + ' | 主攻' + a.recent_summary.h_att.toFixed(1) + '|主失' + a.recent_summary.h_def.toFixed(1) + ' | 客攻' + a.recent_summary.a_att.toFixed(1) + '|客失' + a.recent_summary.a_def.toFixed(1)
                    + '</div>'
                    + '<div class="v36-section">'
                    + '<h4>Step0 方向判断 <span class="v36-badge ' + dirTag + '">' + a.step0.direction + '(' + a.step0.direction_conf + ')</span></h4>'
                    + '0球=' + a.step0.g0_val.toFixed(0) + ' 理论[' + a.step0.g0_theo + '] 偏差=' + (a.step0.g0_deviation>0?'+':'') + a.step0.g0_deviation.toFixed(1) + '<br>'
                    + '线位=' + a.step0.ou_line + ' vs 标准=' + a.step0.std_line + ' 偏差=' + (a.step0.line_deviation>0?'+':'') + a.step0.line_deviation.toFixed(2) + '<br>'
                    + '信号: ' + (a.step0.signals.length ? a.step0.signals.join(' | ') : '无明确信号') + '<br>'
                    + '分析范围: <strong>' + a.step0.analysis_range + '</strong>'
                    + vetoHtml
                    + '</div>'
                    + '<div class="v36-section">'
                    + '<h4>Step4 三维排除</h4>'
                    + '<table class="v36-table"><tr><th>进球</th><th>状态</th><th>命中率/原因</th></tr>' + exclRows + '</table>'
                    + heatHtml
                    + '</div>'
                    + '<div class="v36-section">'
                    + '<h4>📈 新规律辅助</h4>'
                    + '近况锚定: ' + a.new_rules.anchor + '<br>'
                    + '攻击力阈值: ' + a.new_rules.attack_threshold + '<br>'
                    + '大胜评估: ' + a.new_rules.attack_vs_defense
                    + (a.new_rules.profiles && a.new_rules.profiles.length > 0 ? '<br><br><strong>🎯 画像规律触发:</strong><br>' + a.new_rules.profiles.map(p => '&nbsp;&nbsp;' + (typeof p === 'object' ? (p.active ? '<span style="color:#4caf50">✅</span> ' : '<span style="color:#9e9e9e;font-size:11px">[仅参考]</span> ') + p.text : p)).join('<br>') : '')
                    + '</div>'
                    + '<div class="v36-section">'
                    + '<h4>7.8 比分反推</h4>'
                    + (a.score_analysis ? '<div style=\"margin-bottom:8px;color:#b0b0b0;font-size:12px\">' + a.score_analysis.map(s => '• ' + s).join('<br>') + '</div>' : '')
                    + scoreHtml
                    + '</div>'
                    + (function() {
                        let allScores = [];
                        for (let sc of a.score_candidates) {
                            for (let s of sc.scores) {
                                allScores.push({score: s.score, tag: s.tag, goals: sc.total_goals});
                            }
                        }
                        let excludeScores = allScores.slice(0, 2);
                        let altScores = allScores.slice(2, 5);
                        let h = '<div class="v36-section"><h4>🎯 反向排除 (81%准确)</h4>';
                        if (excludeScores.length > 0) {
                            h += '<div class="v36-warn"><strong>⚠️建议排除:</strong><br>';
                            h += excludeScores.map(s => '&nbsp;&nbsp;🚫 ' + s.score + ' ' + s.tag + ' (' + s.goals + '球)').join('<br>');
                            h += '</div>';
                        }
                        if (altScores.length > 0) {
                            h += '<div class="v36-info"><strong>✅ 备选:</strong> ';
                            h += altScores.map(s => s.score).join(' | ');
                            h += '</div>';
                        }
                        h += '<div style="font-size:10px;color:#888;margin-top:4px">回测355场:首选命中7%,前2排除准确率81%</div></div>';
                        return h;
                    })()
                    + (function() {
                        // ── V3.8: 让球盘总结 ──
                        try {
                        const hc = a.handicap_conclusion;
                        if (!hc) return '';
                        let h = '<div class="v36-section" style="border:2px solid #ff9800;background:#1a1a0a;border-radius:8px">';
                        h += '<h4 style="color:#ff9800">🎯 让球盘总结</h4>';
                        
                        let excl = [];
                        if (hc.p0_win === true) excl.push('让胜');
                        if (hc.p0_lose === true) excl.push('让负');
                        if (hc.p0_draw === true) excl.push('让平');
                        
                        let recs = [];
                        if (hc.p1_win === true && hc.p0_win !== true) recs.push('让胜');
                        if (hc.p1_lose === true && hc.p0_lose !== true) recs.push('让负');
                        
                        let contra = [];
                        if (hc.p1_win === true && hc.p0_win === true) contra.push('让胜');
                        if (hc.p1_lose === true && hc.p0_lose === true) contra.push('让负');
                        
                        if (hc.contra) {
                            h += '<div style="color:#f44336;font-size:14px"><strong>⚠️ 矛盾信号→放弃，观望</strong></div>';
                        } else if (recs.length > 0) {
                            h += '<div style="color:#4caf50;font-size:16px"><strong>✅ 推荐: ' + recs.join(' / ') + '</strong></div>';
                            if (excl.length > 0) h += '<div style="color:#f44336;font-size:13px;margin-top:4px">🚫 排除: ' + excl.join('、') + '</div>';
                        } else {
                            h += '<div style="color:#888;font-size:14px">❌ 无明确信号 → 观望</div>';
                        }
                        h += '<div style="font-size:10px;color:#888;margin-top:4px">基于120场回测:让胜66%/让负67%(不矛盾时)</div>';
                        h += '</div>';
                        return h;
                        } catch(e) { return '<div class="v36-section v36-warn">让球盘总结错误: ' + e.message + '</div>'; }
                    })()
                    + '<div class="v36-section">'
                    + '<h4>7.9/7.10 终审 & 反审</h4>'
                    + reviewHtml + warnHtml
                    + '</div>'
                    + (rec ? '<div class="v36-rec"><strong>' + a.step0.direction + '</strong> | 总进球: ' + rec.goals.join('/') + '球 | 首选比分: ' + rec.top_score + '</div>' : '')
                    + '</div>';

                document.body.appendChild(overlay);
                document.getElementById('v36-close-btn').onclick = function() { overlay.remove(); };
            } catch (err) {
                alert('分析失败: ' + err.message);
            } finally {
                btn.innerHTML = orig;
                btn.classList.remove('loading');
                btn.disabled = false;
            }
        }

        // ── 推荐统计（v2.6新增）─────────────────────────────
        async function updateRecStats(matchId) {
            const btn = document.getElementById('btn-stats-' + matchId);
            const homeEl = document.getElementById('home-' + matchId);
            const awayEl = document.getElementById('away-' + matchId);
            const homeScore = parseInt(homeEl.value);
            const awayScore = parseInt(awayEl.value);
            
            if (isNaN(homeScore) || isNaN(awayScore)) {
                alert('请先输入比分再点击推荐统计');
                return;
            }

            // 找到对应的match对象
            const m = window._allMatches ? window._allMatches.find(x => x.match_id == matchId) : null;
            if (!m || !m.g3_prediction) {
                alert('数据未加载');
                return;
            }

            // 收集触发的规则
            const rules = [];
            const pred = m.g3_prediction;

            // 黄金信号 - 区分增强版和基础版
            if (pred.golden_1goals && pred.golden_1goals.is_golden_1) {
                const isEnh = (pred.golden_1goals.reason || '').includes('增强');
                const type = isEnh ? 'golden_1goals_enhanced' : 'golden_1goals_base';
                rules.push({type: type, target_goals: 1, hit_rate: pred.golden_1goals.hit_rate || (isEnh ? 44.8 : 37.2), sample: pred.golden_1goals.sample_size || (isEnh ? 29 : 43)});
            }
            if (pred.golden_2goals && pred.golden_2goals.is_golden_2) {
                const reason = pred.golden_2goals.reason || '';
                let g2type = 'golden_2goals'; // default
                if (reason.includes('2.9')) g2type = 'golden_2goals_29';
                else if (reason.includes('0球=23')) g2type = 'golden_2goals_g023';
                else if (reason.includes('3.1')) g2type = 'golden_2goals_31';
                rules.push({type: g2type, target_goals: 2, hit_rate: pred.golden_2goals.hit_rate || 40, sample: pred.golden_2goals.sample_size || 20});
            }
            if (pred.golden_4goals && pred.golden_4goals.is_golden_4) {
                rules.push({type: 'golden_4goals', target_goals: 4, hit_rate: pred.golden_4goals.hit_rate || 66.7, sample: pred.golden_4goals.sample_size || 6});
            }

            // 最终推荐信号（建议投注板块）- 通用收集所有is_bet信号
            if (pred.final_rec) {
                const st = pred.final_rec.signal_type || '';
                if (pred.final_rec.is_bet) {
                    // 保留中文、字母、数字、+、-，其余替换为_
                    const typeKey = 'final_' + (st || 'unknown').replace(/[^\w\u4e00-\u9fff+\-]/g, '_').replace(/_+/g, '_');
                    rules.push({type: typeKey, target_goals: 3, hit_rate: pred.final_rec.hit_rate || 50, sample: pred.final_rec.sample_size || 10});
                }
            }

            // 收集实操规律（2026-05-02新增）
            if (pred.signals && Array.isArray(pred.signals)) {
                for (const sig of pred.signals) {
                    const sigName = Array.isArray(sig) ? sig[0] : sig;
                    if (typeof sigName === 'string' && sigName.includes('实操规律')) {
                        let pType = '';
                        let targetGoals = 0;
                        let hitRate = 50;
                        let sampleSize = 10;
                        
                        if (sigName.includes('排除3球')) {
                            pType = 'practical_exclude_3';
                            targetGoals = 3;
                            hitRate = 0;  // 0%（0/13）
                            sampleSize = 13;
                        } else if (sigName.includes('推荐3球')) {
                            pType = 'practical_recommend_3';
                            targetGoals = 3;
                            hitRate = 50;  // 50%
                            sampleSize = 10;
                        } else if (sigName.includes('排除2球')) {
                            pType = 'practical_exclude_2';
                            targetGoals = 2;
                            hitRate = 0;  // 0%（0/9）
                            sampleSize = 9;
                        } else if (sigName.includes('推荐2球')) {
                            pType = 'practical_recommend_2';
                            targetGoals = 2;
                            hitRate = 100;  // 100%
                            sampleSize = 5;
                        }
                        
                        if (pType && !rules.some(r => r.type === pType)) {
                            rules.push({
                                type: pType,
                                target_goals: targetGoals,
                                hit_rate: hitRate,
                                sample_size: sampleSize
                            });
                        }
                    }
                }
            }

            if (rules.length === 0) {
                alert('未检测到触发的推荐规律');
                return;
            }

            // 去重
            const seen = new Set();
            const uniqueRules = rules.filter(r => {
                const k = r.type;
                if (seen.has(k)) return false;
                seen.add(k);
                return true;
            });

            btn.innerHTML = '⏳ 统计中...';
            btn.disabled = true;

            try {
                const res = await fetch('/api/update-rec-stats/' + encodeURIComponent(matchId), {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({home_score: homeScore, away_score: awayScore, rules: uniqueRules})
                });
                const data = await res.json();
                
                if (!data.success) {
                    if (data.error && data.error.includes('重复')) {
                        btn.innerHTML = '✅ 已统计';
                        btn.classList.add('done');
                        btn.disabled = true;
                    } else {
                        alert('统计失败：' + (data.error || '未知错误'));
                        btn.innerHTML = '📊 推荐统计';
                        btn.disabled = false;
                    }
                    return;
                }

                // 显示更新结果
                let msg = '推荐统计结果:\\n\\n';
                for (const r of data.updated_rules) {
                    const typeName = r.type.replace(/_/g, ' ').replace(/([A-D])$/, '');
                    const dir = r.is_hit ? '✅命中' : '❌不中';
                    msg += typeName + ': ' + r.old_hit_rate + '%→' + r.new_hit_rate + '% (' + r.old_sample + '→' + r.new_sample + ') ' + dir + '\\n';
                }
                msg += '\\n实际比分: ' + homeScore + ':' + awayScore + ' (总' + (homeScore+awayScore) + '球)';
                alert(msg);

                btn.innerHTML = '✅ 已统计';
                btn.classList.add('done');
                btn.disabled = true;
                // 重新加载比赛列表以更新实盘验证显示
                const ts2 = Date.now();
                const fres = await fetch('/api/matches?light=1&t=' + ts2);
                const fdata = await fres.json();
                window._allMatches = fdata;
                renderPage(window._currentPage || 1);
            } catch (err) {
                alert('统计失败：' + err.message);
                btn.innerHTML = '📊 推荐统计';
                btn.disabled = false;
            }
        }

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

        function _getHADChangeTag(m, key) {
            if (!m.had_change || !m.had_change[key] || m.had_change[key].count === 0) return '';
            const c = m.had_change[key];
            const up = c.change_pct > 0;
            const color = up ? '#ef4444' : '#22c55e';
            const arrow = up ? '↑' : '↓';
            return '<span class="odds-change-tag" style="color:' + color + '">' + arrow + Math.abs(c.change_pct) + '%</span>';
        }

        function _getHHADChangeTag(m, key) {
            if (!m.hhad_change || !m.hhad_change[key] || m.hhad_change[key].count === 0) return '';
            const c = m.hhad_change[key];
            const up = c.change_pct > 0;
            const color = up ? '#ef4444' : '#22c55e';
            const arrow = up ? '↑' : '↓';
            return '<span class="odds-change-tag" style="color:' + color + '">' + arrow + Math.abs(c.change_pct) + '%</span>';
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

        // ── 大小球保存 ──────────────────────────────
        async function saveOverUnder(matchId) {
            const overOddsInput = document.getElementById('over-odds-' + matchId);
            const ouLineInput = document.getElementById('ou-line-' + matchId);
            const underOddsInput = document.getElementById('under-odds-' + matchId);
            const msgEl = document.getElementById('score-msg-' + matchId);
            
            const overOdds = parseFloat(overOddsInput.value);
            const ouLine = parseFloat(ouLineInput.value);
            const underOdds = parseFloat(underOddsInput.value);
            
            if (isNaN(overOdds) || isNaN(ouLine) || isNaN(underOdds) || overOdds <= 0 || ouLine < 0 || underOdds <= 0) {
                msgEl.className = 'score-msg error';
                msgEl.textContent = '请输入有效的大小球数据';
                return;
            }
            
            try {
                const res = await fetch('/api/over_under/' + matchId, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        over_odds: overOdds,
                        ou_line: ouLine,
                        under_odds: underOdds
                    })
                });
                const data = await res.json();
                if (data.success) {
                    msgEl.className = 'score-msg saved';
                    msgEl.innerHTML = `<span class="saved-score-display">已保存大小球: 大${overOdds} / ${ouLine} / 小${underOdds}</span>`;
                } else {
                    msgEl.className = 'score-msg error';
                    msgEl.textContent = '保存失败: ' + (data.error || '');
                }
            } catch(e) {
                msgEl.className = 'score-msg error';
                msgEl.textContent = '请求失败: ' + e.message;
            }
        }

        // ── 手动补全比赛抬头 ──────────────────────────────────
        function openEditHeader(matchId) {
            // 取当前数据
            const m = (window._allMatches || []).find(x => x.match_id == matchId);
            const mi = (m && m.match_info) || {};
            document.getElementById('edit-header-mid').value = matchId;
            document.getElementById('edit-header-num').value = mi.match_num_str || '';
            document.getElementById('edit-header-date').value = mi.match_date || '';
            document.getElementById('edit-header-time').value = mi.match_time || '';
            document.getElementById('edit-header-league').value = mi.league_abbr || mi.league || '';
            document.getElementById('edit-header-home-rank').value = mi.home_rank || '';
            document.getElementById('edit-header-away-rank').value = mi.away_rank || '';
            document.getElementById('edit-header-msg').textContent = '';
            document.getElementById('edit-header-modal').style.display = 'flex';
        }

        function closeEditHeader() {
            document.getElementById('edit-header-modal').style.display = 'none';
        }

        async function saveEditHeader() {
            const matchId = document.getElementById('edit-header-mid').value;
            const body = {
                match_num_str: document.getElementById('edit-header-num').value.trim(),
                match_date:    document.getElementById('edit-header-date').value.trim(),
                match_time:    document.getElementById('edit-header-time').value.trim(),
                league_abbr:   document.getElementById('edit-header-league').value.trim(),
                home_rank:     document.getElementById('edit-header-home-rank').value.trim(),
                away_rank:     document.getElementById('edit-header-away-rank').value.trim(),
            };
            const msgEl = document.getElementById('edit-header-msg');
            msgEl.textContent = '保存中...';
            try {
                const res = await fetch('/api/match-info/' + matchId, {
                    method: 'PATCH',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(body)
                });
                const data = await res.json();
                if (data.success) {
                    msgEl.style.color = '#22c55e';
                    msgEl.textContent = '✅ 保存成功，页面将刷新...';
                    setTimeout(() => { closeEditHeader(); loadMatches(); }, 800);
                } else {
                    msgEl.style.color = '#ef4444';
                    msgEl.textContent = '❌ ' + (data.error || '保存失败');
                }
            } catch(e) {
                msgEl.style.color = '#ef4444';
                msgEl.textContent = '❌ 请求失败: ' + e.message;
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
                // 同时刷新变化命中率统计
                const r3 = await fetch('/api/change_hitrate');
                const chgData = await r3.json();
                window._CHANGE_HITRATE = chgData;
                // 重新渲染当前展开的比赛详情（更新变化命中率标签）
                const detailEl = document.getElementById('match-detail-' + matchId);
                if (detailEl && detailEl.style.display !== 'none') {
                    renderMatchDetail(matchId);
                }
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
            html += '<tr><th>前置条件</th><th>预判</th><th>样本</th><th>小3球(0-2)</th><th>恰好3球</th><th>大3球(4+)</th></tr>';

            for (const [signalType, data] of Object.entries(stats)) {
                // 小3球：显示 实际小3球场次/总样本数
                const s = data['小3球'] || {};
                const sActual = s.total || 0;
                const sRate = data.total > 0 ? (sActual / data.total * 100).toFixed(1) : 0;
                const sClass = sRate >= 70 ? 'pattern-rate-high' :
                              sRate >= 50 ? 'pattern-rate-mid' : 'pattern-rate-low';
                const sText = data.total > 0 ? `${sActual}场/${data.total}场(${sRate}%)` : '-';

                // 恰好3球：显示 实际恰好3球场次/总样本数
                const m = data['恰好3球'] || {};
                const mActual = m.total || 0;
                const mRate = data.total > 0 ? (mActual / data.total * 100).toFixed(1) : 0;
                const mClass = mRate >= 70 ? 'pattern-rate-high' :
                              mRate >= 50 ? 'pattern-rate-mid' : 'pattern-rate-low';
                const mText = data.total > 0 ? `${mActual}场/${data.total}场(${mRate}%)` : '-';

                // 大3球：显示 实际大3球场次/总样本数
                const b = data['大3球'] || {};
                const bActual = b.total || 0;
                const bRate = data.total > 0 ? (bActual / data.total * 100).toFixed(1) : 0;
                const bClass = bRate >= 70 ? 'pattern-rate-high' :
                              bRate >= 50 ? 'pattern-rate-mid' : 'pattern-rate-low';
                const bText = data.total > 0 ? `${bActual}场/${data.total}场(${bRate}%)` : '-';

                html += '<tr>' +
                    '<td>' + signalType + '</td>' +
                    '<td>' + data.prediction + '</td>' +
                    '<td>' + data.total + '场</td>' +
                    '<td class="' + sClass + '">' + sText + '</td>' +
                    '<td class="' + mClass + '">' + mText + '</td>' +
                    '<td class="' + bClass + '">' + bText + '</td>' +
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
                    let html = '<div class="similar-header">🔍 相似比赛（3球赔率相同，按近况接近>0球赔率接近>变化方向一致排序，最多8场）</div>';
                    data.similar.forEach((item, idx) => {
                        const tg = item.record.total_goals;
                        const tgClass = tg === 3 ? 'tg-3' : tg === 0 ? 'tg-0' : 'tg-other';
                        const tgDisplay = tg + '球';
                        const det = item.details || {};
                        // 0球赔率变化信息
                        const g0ch = item.g0_change || {};
                        const g0chCount = g0ch.count;
                        const g0chPct = g0ch.change_pct;
                        let g0chTag = '';
                        if (g0chCount > 0 && g0chPct !== undefined) {
                            const chDir = g0chPct > 0 ? '↑' : (g0chPct < 0 ? '↓' : '→');
                            const chColor = g0chPct > 0 ? '#ef4444' : (g0chPct < 0 ? '#22c55e' : '#888');
                            g0chTag = '<span style="color:' + chColor + '">' + chDir + Math.abs(g0chPct) + '%</span><span style="color:#555">(' + g0chCount + '次)</span>';
                        } else {
                            g0chTag = '<span style="color:#555">无变化</span>';
                        }
                        html += `<div class="similar-item">
                            <span class="similar-rank">#${idx + 1}</span>
                            <div class="similar-teams">${item.record.home_team || item.home_team} vs ${item.record.away_team || item.away_team}</div>
                            <div class="similar-score ${tgClass}">${item.record.score_str || (item.record.home_score + ':' + item.record.away_score)}</div>
                            <div class="similar-tg-label">${tgDisplay}</div>
                            <div class="similar-similarity">相似 ${item.similarity}%${item.g0_diff != null ? ' | 0球差' + item.g0_diff : ''}</div>
                        </div>`;
                        // 0球变化信息单独一行
                        html += `<div style="padding:1px 12px 1px 42px;font-size:11px"><span style="color:#888">0球变化:</span>${g0chTag}</div>`;
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
                    // 小3球：显示 实际小3球场次/总样本数
                    const s = stats['小3球'] || {};
                    const sActual = s.total || 0;  // 实际小3球的场次
                    const sRate = stats.total > 0 ? (sActual / stats.total * 100).toFixed(1) : 0;
                    const sClass = sRate >= 70 ? 'pattern-rate-high' :
                                  sRate >= 50 ? 'pattern-rate-mid' : 'pattern-rate-low';
                    const sText = stats.total > 0 ? `${sActual}场/${stats.total}场(${sRate}%)` : '-';

                    // 恰好3球：显示 实际恰好3球场次/总样本数
                    const m = stats['恰好3球'] || {};
                    const mActual = m.total || 0;  // 实际恰好3球的场次
                    const mRate = stats.total > 0 ? (mActual / stats.total * 100).toFixed(1) : 0;
                    const mClass = mRate >= 70 ? 'pattern-rate-high' :
                                  mRate >= 50 ? 'pattern-rate-mid' : 'pattern-rate-low';
                    const mText = stats.total > 0 ? `${mActual}场/${stats.total}场(${mRate}%)` : '-';

                    // 大3球：显示 实际大3球场次/总样本数
                    const b = stats['大3球'] || {};
                    const bActual = b.total || 0;  // 实际大3球的场次
                    const bRate = stats.total > 0 ? (bActual / stats.total * 100).toFixed(1) : 0;
                    const bClass = bRate >= 70 ? 'pattern-rate-high' :
                                  bRate >= 50 ? 'pattern-rate-mid' : 'pattern-rate-low';
                    const bText = stats.total > 0 ? `${bActual}场/${stats.total}场(${bRate}%)` : '-';

                    container.innerHTML = `
                        <div class="pattern-single-stats">
                            <div class="pattern-single-title">📊 ${signalType} 命中率统计</div>
                            <table class="pattern-stats-table">
                                <tr><th>预判</th><th>样本</th><th>小3球(0-2)</th><th>恰好3球</th><th>大3球(4+)</th></tr>
                                <tr>
                                    <td><strong>${stats.prediction}</strong></td>
                                    <td><strong>${stats.total}场</strong></td>
                                    <td class="${sClass}">${sText}</td>
                                    <td class="${mClass}">${mText}</td>
                                    <td class="${bClass}">${bText}</td>
                                </tr>
                            </table>
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

        function drawExclusionHtml(d) {
            if (!d || !d.active) return '';
            const signals = d.signals || [];
            const excl = d.exclusions || [];
            const warns = d.warnings || [];
            const pred = d.prediction || '';
            const conf = d.confidence || 1;
            const confText = d.confidence_text || '';

            // 信号按strength排序
            const activeSignals = signals.filter(s => s.action).sort((a, b) => b.strength - a.strength);
            const dirMap = {'home': '主胜', 'draw': '平局', 'away': '客胜'};
            const exclNames = excl.map(e => dirMap[e] || e);

            // 检测特殊状态
            const hasColdAlert = warns.some(w => w && (w.indexOf('R8') >= 0 || w.indexOf('冷门') >= 0));
            const hasHeatTrap = warns.some(w => w && (w.indexOf('造热陷阱') >= 0 || w.indexOf('R5a') >= 0));
            const hasCoverMode = warns.some(w => w && (w.indexOf('掩护') >= 0 || w.indexOf('R6') >= 0));

            // 背景色 - 冷门/陷阱时用警告色
            let bgColor, borderColor, tagBg, tagColor, label;
            if (hasColdAlert) {
                bgColor = 'rgba(239,68,68,0.15)'; borderColor = 'rgba(239,68,68,0.5)';
                tagBg = 'rgba(239,68,68,0.25)'; tagColor = '#fca5a5';
                label = '🧊 冷门预警';
            } else if (hasHeatTrap) {
                bgColor = 'rgba(249,115,22,0.12)'; borderColor = 'rgba(249,115,22,0.4)';
                tagBg = 'rgba(249,115,22,0.20)'; tagColor = '#fb923c';
                label = '🔴 造热陷阱';
            } else if (conf >= 5) {
                bgColor = 'rgba(239,68,68,0.12)'; borderColor = 'rgba(239,68,68,0.4)';
                tagBg = 'rgba(239,68,68,0.20)'; tagColor = '#fca5a5';
                label = '🔥 强排除';
            } else if (conf >= 4) {
                bgColor = 'rgba(234,179,8,0.10)'; borderColor = 'rgba(234,179,8,0.35)';
                tagBg = 'rgba(234,179,8,0.18)'; tagColor = '#fbbf24';
                label = '⚡ 排除信号';
            } else if (conf >= 3) {
                bgColor = 'rgba(59,130,246,0.08)'; borderColor = 'rgba(59,130,246,0.25)';
                tagBg = 'rgba(59,130,246,0.12)'; tagColor = '#93c5fd';
                label = '📊 排除参考';
            } else {
                bgColor = 'rgba(100,116,139,0.06)'; borderColor = 'rgba(100,116,139,0.18)';
                tagBg = 'rgba(100,116,139,0.10)'; tagColor = '#94a3b8';
                label = '📋 30家统计';
            }

            let html = '<div style="background:' + bgColor + ';border:1px solid ' + borderColor + ';border-radius:8px;padding:10px 12px;margin-top:8px;font-size:12px;">';

            // 标题行
            html += '<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;flex-wrap:wrap;">';
            html += '<span style="background:' + tagBg + ';color:' + tagColor + ';padding:2px 8px;border-radius:4px;font-weight:bold;font-size:11px;">' + label + '</span>';
            if (pred && conf >= 3) {
                html += '<span style="color:' + tagColor + ';font-weight:bold;font-size:13px;">预测: ' + pred + '</span>';
                if (confText) html += '<span style="color:#94a3b8;font-size:11px;">' + confText + '</span>';
            }
            if (d.macao_tip && d.macao_tip.length > 1 && !['|', '-', '—', '/'].includes(d.macao_tip)) {
                html += '<span style="color:#94a3b8;font-size:11px;margin-left:auto;">澳门推荐: ' + d.macao_tip + '</span>';
            }
            html += '</div>';

            // 排除方向
            if (exclNames.length > 0) {
                html += '<div style="margin-bottom:4px;color:#fca5a5;font-weight:bold;font-size:11px;">';
                html += '✗ 排除: ' + exclNames.join('、');
                html += '</div>';
            }

            // 分歧警告单独检测（strength=0 但需显示）
            const hasConflict = signals.some(s => s.rule && s.rule.indexOf('分歧') >= 0);

            // 冷门/陷阱/掩护/分歧 警告区域
            if (hasColdAlert || hasHeatTrap || hasCoverMode || hasConflict) {
                html += '<div style="background:rgba(239,68,68,0.08);border-left:3px solid #f87171;padding:6px 8px;margin:4px 0;border-radius:0 4px 4px 0;">';
                // 特殊信号：从全量 signals 中取（不受 activeSignals 的 action 过滤限制）
                const warnSignals = signals.filter(s =>
                    s.rule && (s.rule.indexOf('R8') >= 0 || s.rule.indexOf('R6') >= 0 || s.rule.indexOf('R5a') >= 0 || s.rule.indexOf('分歧') >= 0)
                );
                warnSignals.forEach(s => {
                    const wColor = s.strength >= 6 ? '#f87171' : s.strength >= 5 ? '#fb923c' : s.strength >= 1 ? '#fbbf24' : '#f97316';
                    html += '<div style="color:' + wColor + ';font-size:11px;line-height:1.6;">';
                    html += s.rule + ' ' + s.detail;
                    if (s.action) html += ' → <b>' + s.action + '</b>';
                    html += '</div>';
                });
                html += '</div>';
            }

            // 常规信号列表（排除特殊信号后最多显示8条）
            // 注意：30家公司共识 action=''，单独渲染避免丢失
            const specialRules = ['R8-冷门', 'R8-预警', 'R6-掩护', 'R5a-造热陷阱', '分歧警告'];
            // 先渲染有 action 的常规信号
            const normalSignals = activeSignals.filter(s =>
                !specialRules.some(r => s.rule && s.rule.indexOf(r) >= 0)
            ).slice(0, 8);
            normalSignals.forEach(s => {
                const sColor = s.strength >= 5 ? '#fca5a5' : s.strength >= 4 ? '#fbbf24' : s.strength >= 3 ? '#93c5fd' : '#94a3b8';
                const sIcon = s.strength >= 5 ? '▸' : s.strength >= 4 ? '▸' : '·';
                html += '<div style="color:' + sColor + ';font-size:11px;line-height:1.6;margin-top:2px;">';
                html += sIcon + ' [' + s.rule + '] ' + s.detail;
                if (s.action && s.strength < 6) html += ' → <b>' + s.action + '</b>';
                html += '</div>';
            });
            // 单独渲染 30家公司共识（无 action，但有价值）
            const consensus = signals.find(s => s.rule && s.rule.indexOf('30家') >= 0);
            if (consensus) {
                html += '<div style="color:#6b7280;font-size:11px;line-height:1.6;margin-top:3px;border-top:1px solid rgba(255,255,255,0.06);padding-top:3px;">';
                html += '· [' + consensus.rule + '] ' + consensus.detail;
                html += '</div>';
            }

            const totalNormal = activeSignals.filter(s => !specialRules.some(r => s.rule && s.rule.indexOf(r) >= 0)).length;
            if (totalNormal > 8) {
                html += '<div style="color:#94a3b8;font-size:10px;margin-top:2px;">...还有' + (totalNormal - 8) + '条信号</div>';
            }

            html += '</div>';
            return html;
        }

    </script>

<!-- ── 手动补全比赛抬头 弹窗 ─────────────────────────────── -->
<div id="edit-header-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:9999;justify-content:center;align-items:center">
  <div style="background:#1a1a2e;border:1px solid #333;border-radius:10px;padding:20px;width:320px;max-width:92vw">
    <div style="font-size:15px;font-weight:bold;color:#f59e0b;margin-bottom:14px">✏️ 补全比赛抬头信息</div>
    <input type="hidden" id="edit-header-mid">
    <table style="width:100%;border-collapse:collapse;font-size:13px;color:#ccc">
      <tr>
        <td style="padding:5px 6px;white-space:nowrap;color:#888">竞彩编号</td>
        <td><input id="edit-header-num" placeholder="如：周一004" style="width:100%;background:#0d0d1a;border:1px solid #333;color:#fff;padding:5px 8px;border-radius:4px;font-size:13px"></td>
      </tr>
      <tr>
        <td style="padding:5px 6px;white-space:nowrap;color:#888">比赛日期</td>
        <td><input id="edit-header-date" placeholder="2026-04-28" style="width:100%;background:#0d0d1a;border:1px solid #333;color:#fff;padding:5px 8px;border-radius:4px;font-size:13px"></td>
      </tr>
      <tr>
        <td style="padding:5px 6px;white-space:nowrap;color:#888">比赛时间</td>
        <td><input id="edit-header-time" placeholder="01:00:00" style="width:100%;background:#0d0d1a;border:1px solid #333;color:#fff;padding:5px 8px;border-radius:4px;font-size:13px"></td>
      </tr>
      <tr>
        <td style="padding:5px 6px;white-space:nowrap;color:#888">联赛简称</td>
        <td><input id="edit-header-league" placeholder="如：瑞超" style="width:100%;background:#0d0d1a;border:1px solid #333;color:#fff;padding:5px 8px;border-radius:4px;font-size:13px"></td>
      </tr>
      <tr>
        <td style="padding:5px 6px;white-space:nowrap;color:#888">主队排名</td>
        <td><input id="edit-header-home-rank" placeholder="如：[瑞超7]" style="width:100%;background:#0d0d1a;border:1px solid #333;color:#fff;padding:5px 8px;border-radius:4px;font-size:13px"></td>
      </tr>
      <tr>
        <td style="padding:5px 6px;white-space:nowrap;color:#888">客队排名</td>
        <td><input id="edit-header-away-rank" placeholder="如：[瑞超6]" style="width:100%;background:#0d0d1a;border:1px solid #333;color:#fff;padding:5px 8px;border-radius:4px;font-size:13px"></td>
      </tr>
    </table>
    <div id="edit-header-msg" style="font-size:12px;margin-top:8px;min-height:16px"></div>
    <div style="display:flex;gap:10px;margin-top:14px">
      <button onclick="saveEditHeader()" style="flex:1;background:#f59e0b;color:#000;border:none;padding:8px;border-radius:5px;font-size:14px;font-weight:bold;cursor:pointer">💾 保存</button>
      <button onclick="closeEditHeader()" style="flex:1;background:#333;color:#ccc;border:none;padding:8px;border-radius:5px;font-size:14px;cursor:pointer">取消</button>
    </div>
  </div>
</div>

</body>
</html>
'''

@app.route('/')
def index():
    import time
    print(f'=== INDEX() CALLED: {time.strftime("%H:%M:%S")} ===')
    # 注入命中率统计到 JS 全局变量
    stats = _build_odds_hitrate()
    # 序列化成 JS 字面量嵌入页面（用字符串替换避免 Jinja2 转义）
    stats_js = json.dumps(stats, ensure_ascii=False)
    html = HTML_TEMPLATE.replace('__ODDS_STATS_JSON__', stats_js)
    # 注入变化命中率统计
    chg_stats = _build_change_hitrate()
    chg_js = json.dumps(chg_stats, ensure_ascii=False)
    html = html.replace('__CHANGE_HITRATE_JSON__', chg_js)
    
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
    form_away = None  # 客近况（用于条件2判断）
    is_cond2 = False  # 初始化条件2标志（避免引用前未赋值）
    if recent_form and recent_form.get('home_avg') is not None:
        form_diff = recent_form['home_avg'] - recent_form['away_avg']
        combined_avg = recent_form['combined_avg']
        form_away = recent_form.get('away_avg')  # 获取客近况

    # 触发条件 — 各区间
    is_low = hhad_draw < 3.3                       # 极低/低区间
    is_midlow = (hhad_draw >= 3.3 and hhad_draw <= 3.64)   # 中低区间(3.3~3.64)
    is_mid = (hhad_draw >= 3.65 and hhad_draw <= 3.95)      # 中区间(3.65~3.95)
    is_high = (hhad_draw >= 4.0 and hhad_draw <= 4.5)       # 高区间(4.0~4.5)

    # 新增规律1: 让胜<1.7 + 让平>=3.7 + 客队近况好(form_diff<0) → 让胜84.6%
    is_law1 = hhad_win < 1.7 and hhad_draw >= 3.7 and form_diff is not None and form_diff < 0

    # 新增规律2: 让胜1.7-2.0 + 让平3.3-3.7 + 客远好(form_diff<-0.3) → 让胜77.8%
    is_law2 = (1.7 <= hhad_win < 2.0) and (3.3 <= hhad_draw < 3.7) and form_diff is not None and form_diff < -0.3

    # 新增规律3: 让胜<2.2 + 让平>=3.7 + 主近况好(form_diff>0) + had_win<1.5 → 让胜87.5%
    had_win = 0
    try:
        # 注意：函数参数是data（第三个参数），不是d！
        if data is not None:
            had_data = data.get('had', {})
        else:
            had_data = {}
        if had_data:
            if '胜' in had_data:
                had_win = float(had_data['胜'])  # 直接用[]访问，如果key不存在会抛异常（方便调试）
            elif '主胜' in had_data:
                had_win = float(had_data['主胜'])
            else:
                # 打印had的所有keys，方便调试
                print(f'[DEBUG] had_data keys: {list(had_data.keys())}, cannot find had_win')
    except Exception as e:
        print(f'[DEBUG] Error reading had_win: {e}')
        pass
    is_law3 = hhad_win < 2.2 and hhad_draw >= 3.7 and form_diff is not None and form_diff > 0 and 0 < had_win < 1.5
    print(f'[DEBUG] is_law3 calculation: hhad_win={hhad_win}<2.2, hhad_draw={hhad_draw}>=3.7, form_diff={form_diff}>0, had_win={had_win} in (0,1.5) → {is_law3}')

    # 中赔前置条件: 主受让 + 客队近况好(form_diff < -0.3)
    is_mid_match = is_mid and (not is_home_let) and form_diff is not None and form_diff < -0.3
    # 中低区间前置条件: 客队近况好(form_diff < -0.3) + 让胜赔更低
    is_midlow_match = is_midlow and form_diff is not None and form_diff < -0.3 and hhad_win < hhad_lose - 0.05
    # 高区间前置条件: 主让球 + 客队近况好(form_diff < -0.5) + 让负赔更低
    is_high_match = is_high and is_home_let and form_diff is not None and form_diff < -0.5 and hhad_lose < hhad_win - 0.05

    # 移除debug输出，改用/test_law3路由查看
    # 条件2: 让平3.6-3.9 + 客近况<2.5 → 激活hhad_hint
    if not is_low and not is_mid_match and not is_midlow_match and not is_high_match and not is_law1 and not is_law2 and not is_law3 and not is_cond2:
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

    # ── Step 1.5: 新规律判断（覆盖默认方向）──
    # 规律1: 让胜<1.7 + 让平>=3.7 + 客队近况好 → 让胜84.6%
    if is_law1:
        hhad_pick = '让胜'
        hhad_confidence = 85
        hints.append(f'⚡新规律1: 让胜<1.7+让平≥3.7+客近况好, 让胜率84.6%(13场)')
        # 低赔率警告
        if hhad_win < 1.50:
            hints.append(f'⚠️ 让胜赔率过低({hhad_win:.2f}<1.50)，可能存在诱盘风险，请谨慎')
    # 规律2: 让胜1.7-2.0 + 让平3.3-3.7 + 客远好 → 让胜77.8%
    elif is_law2:
        hhad_pick = '让胜'
        hhad_confidence = 78
        hints.append(f'⚡新规律2: 让胜1.7-2.0+让平3.3-3.7+客远好, 让胜率77.8%(9场)')
        # 1.75-1.79范围警告（回测显示此范围0%命中）
        if 1.75 <= hhad_win < 1.80:
            hints.append(f'⚠️ 让胜赔率({hhad_win:.2f})在1.75-1.79范围，回测0%命中，建议谨慎或排除')
        # 低赔率警告
        if hhad_win < 1.50:
            hints.append(f'⚠️ 让胜赔率过低({hhad_win:.2f}<1.50)，可能存在诱盘风险，请谨慎')
    # 规律3: 让胜<2.2 + 让平>=3.7 + 主近况好 + had_win<1.5 → 让胜87.5%
    elif is_law3:
        hhad_pick = '让胜'
        hhad_confidence = 88
        hints.append(f'⚡新规律3: 让胜<2.2+让平≥3.7+主近况好+普通主胜<1.5, 让胜率87.5%(8场)')
        # 爆冷提醒：had_win极低(<1.3)时，主队可能爆冷输球
        if had_win > 0 and had_win < 1.3:
            hints.append(f'⚠️爆冷提醒: 普通主胜={had_win}<1.3, 主队可能爆冷输球, 谨慎投注')


    # ── Step 3: 平局概率分析（基于had.平回测, 2026-04-26修正）──
    # 逻辑：不让球平局赔率(had.平)在高危区间时，90分钟平局概率显著上升
    # 高危区间：[3.0,3.2) 或 [3.4,3.7)  → 平局率约45%
    # 前置条件：任意hhad分析触发后均可作为风险提示
    draw_signal = False
    draw_pct = 27   # 基准27.3%（所有比赛）
    draw_reason = ''

    had_draw_val = 0
    try:
        had = d.get('had', {}) if d is not None else {}
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
    
    # 条件2: 让平3.6-3.9(中赔区间) + 客近况<2.5 → 推荐让胜(60.5%) 反向信号
    is_cond2 = is_mid and form_away is not None and form_away < 2.5
    
    if is_cond2:
        hhad_pick = '让胜'
        hhad_confidence = 61
        mid_hints.append(f'⭐⭐ 条件2反向信号: 让平3.6-3.9+客近况<2.5, 让胜率60.5%(23/38场)')
        mid_hints.append(f'  推荐策略: 买让胜(60.5%), 可考虑小2.5球(平均2.35球), 主队零封(60.9%)')
    elif is_mid_match:
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

    # 低赔率警告：推荐方赔率<1.50时可能存在诱盘风险
    if hhad_pick == '让胜' and hhad_win < 1.50:
        hints.append(f'⚠️ 让胜赔率过低({hhad_win:.2f}<1.50)，可能存在诱盘风险，请谨慎')
    elif hhad_pick == '让负' and hhad_lose < 1.50:
        hints.append(f'⚠️ 让负赔率过低({hhad_lose:.2f}<1.50)，可能存在诱盘风险，请谨慎')

    return {
        'active': True,
        'is_mid': is_mid,              # 是否中赔区间(3.65~3.95)
        'is_midlow': is_midlow_match,  # 是否中低区间(3.3~3.64)
        'is_high': is_high_match,       # 是否高区间(4.0~4.5)
        'is_cond2': is_cond2,          # 是否条件2触发(让平3.6-3.9+客近况<2.5)
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
        'is_law1': is_law1,          # 新规律1触发
        'is_law2': is_law2,          # 新规律2触发
        'is_law3': is_law3,          # 新规律3触发
    }







def _analyze_hhad_lose_low(hhad, recent_form):
    """
    主让+让负低赔规律分析（基于217场回测，含近况细分决策树）

    触发条件: 主让球 + 让负赔率 < 2.0
    核心规律: 让负低赔 = 庄家防范让负方向（真实方向）

    参数:
        hhad: {"让球": str, "让胜": float, "让平": float, "让负": float}
        recent_form: {"home_avg": float, "away_avg": float, "combined_avg": float} 或 None

    返回:
        {
            "active": bool,
            "lose_odds": float,
            "handicap": float,
            "pick": str,        # "让负" / "观望" / "排除让负"
            "confidence": int,
            "tier": str,        # "S/A/B/C/D/E"
            "reasons": list,
        } 或 None
    """
    if not hhad or not hhad.get("让负"):
        return None

    try:
        hhad_win = float(hhad["让胜"])
        hhad_lose = float(hhad["让负"])
    except (ValueError, TypeError):
        return None

    # 解析让球方向
    h_str = str(hhad.get("让球", ""))
    try:
        raw = float(h_str)
        handicap = -raw  # "-1" -> handicap=1 (主让1球)
    except:
        return None

    is_home_let = handicap > 0
    if not is_home_let or hhad_lose >= 2.0:
        return None

    # 近况数据
    home_avg = None
    away_avg = None
    combined_avg = None
    if recent_form and recent_form.get("home_avg") is not None:
        home_avg = recent_form["home_avg"]
        away_avg = recent_form.get("away_avg")
        combined_avg = recent_form.get("combined_avg")

    reasons = []
    pick = "观望"
    confidence = 0
    tier = "D"

    if hhad_lose < 1.45:
        tier = "S"
        pick = "让负"
        confidence = 83
        reasons.append(f"S级: 让负赔率<1.45(当前{hhad_lose:.2f}), 24场回测让负率83.3%, 让胜率0%")
        if home_avg is not None:
            if home_avg < 1.5:
                reasons.append(f"  主队近况{home_avg:.1f}(低迷)→让负78.6%(14场)")
            elif home_avg < 2.0:
                reasons.append(f"  主队近况{home_avg:.1f}(一般)→让负83.3%(6场)")
            else:
                reasons.append(f"  主队近况{home_avg:.1f}(较好)→让负80.0%(10场)")
            reasons.append("  近况不敏感，无论近况好坏均强推让负")

    elif hhad_lose < 1.50:
        tier = "A"
        pick = "让负"
        confidence = 62
        reasons.append(f"A级: 让负赔率1.45-1.50(当前{hhad_lose:.2f}), 34场回测让负率61.8%")
        if home_avg is not None:
            if home_avg < 1.5:
                confidence = 67
                reasons.append(f"  主队近况{home_avg:.1f}(<1.5)→让负66.7%(12场)↑升级")
            elif home_avg < 2.0:
                confidence = 64
                reasons.append(f"  主队近况{home_avg:.1f}(1.5-2.0)→让负63.6%(11场)")
            else:
                reasons.append(f"  主队近况{home_avg:.1f}(≥2.0)→让负50%(6场), 信号减弱")

    elif hhad_lose < 1.55:
        tier = "B"
        reasons.append(f"B级: 让负赔率1.50-1.55(当前{hhad_lose:.2f}), 基础让负率55.0%, 需近况确认")
        if home_avg is not None:
            if home_avg < 1.5:
                pick = "让负"
                confidence = 67
                reasons.append(f"  主队近况{home_avg:.1f}(<1.5)→让负66.7%(9场)★升级")
            elif home_avg < 2.0:
                pick = "排除让负"
                confidence = 67
                reasons.append(f"  主队近况{home_avg:.1f}(1.5-2.0)→让负仅33.3%(6场)✖排除让负")
            else:
                reasons.append(f"  主队近况{home_avg:.1f}(≥2.0), 样本不足, 观望")
        if away_avg is not None and 1.0 <= away_avg < 1.5:
            if pick != "排除让负":
                pick = "让负"
                confidence = max(confidence, 67)
                reasons.append(f"  客队近况{away_avg:.1f}(1.0-1.5)→让负66.7%(9场)★升级")
        if combined_avg is not None and 1.5 <= combined_avg < 2.0:
            if pick != "排除让负":
                pick = "让负"
                confidence = max(confidence, 83)
                reasons.append(f"  双方平均近况{combined_avg:.1f}(1.5-2.0)→让负83.3%(6场)★★强升级")

    elif hhad_lose < 1.65:
        tier = "C"
        reasons.append(f"C级: 让负赔率1.55-1.65(当前{hhad_lose:.2f}), 基础让负率56.5%, 强依赖近况")
        if home_avg is not None and 2.0 <= home_avg < 2.5:
            pick = "让负"
            confidence = 70
            reasons.append(f"  主队近况{home_avg:.1f}(2.0-2.5)→让负70.0%(10场)★升级")
        elif away_avg is not None and away_avg < 1.0:
            pick = "让负"
            confidence = 75
            reasons.append(f"  客队近况{away_avg:.1f}(<1.0)→让负75.0%(12场)★升级")
        else:
            reasons.append(f"  近况条件不满足, 保持观望(让负率47-54%)")

    elif hhad_lose < 1.80:
        tier = "D"
        reasons.append(f"D级: 让负赔率1.65-1.80(当前{hhad_lose:.2f}), 基础让负率49.6%, 中性")
        if home_avg is not None:
            if 1.5 <= home_avg < 2.0:
                pick = "让负"
                confidence = 63
                reasons.append(f"  主队近况{home_avg:.1f}(1.5-2.0)→让负63.2%(19场)★升级")
            elif home_avg < 1.5:
                pick = "让负"
                confidence = 62
                reasons.append(f"  双方低迷区间(主{home_avg:.1f})→让负61.5%(26场)★升级")
            elif home_avg >= 2.0:
                pick = "排除让负"
                confidence = 70
                reasons.append(f"  主队近况{home_avg:.1f}(≥2.0)→让负仅30.4%(13场)✖排除让负")
        else:
            reasons.append(f"  无近况数据, 观望")

    else:
        tier = "E"
        pick = "排除让负"
        confidence = 62
        reasons.append(f"E级(排除): 让负赔率≥1.80(当前{hhad_lose:.2f}), 19场回测让负率仅31.6%")
        if home_avg is not None and 1.5 <= home_avg < 2.0:
            confidence = 67
            reasons.append(f"  主队近况{home_avg:.1f}(1.5-2.0)→让负仅33.3%(9场)✖确认排除")
        if combined_avg is not None and 1.5 <= combined_avg < 2.0:
            confidence = 77
            reasons.append(f"  双方平均近况{combined_avg:.1f}(1.5-2.0)→让负仅23.1%(13场)✖✖强排除")
        reasons.append("  建议: 让负方向是陷阱，庄家引导性开盘")

    return {
        "active": True,
        "lose_odds": round(hhad_lose, 2),
        "handicap": handicap,
        "pick": pick,
        "confidence": confidence,
        "tier": tier,
        "reasons": reasons,
    }

# ==================== 排除平局分析（基于分析模板源数据） ====================

_ANALYSIS_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '分析模板')


def _find_source_md(match_num_str, match_date):
    """
    根据竞彩编号和比赛日期查找分析模板源数据文件。
    match_date: "2026-04-28" → 先找 "2026.04.28"，再找 "2026.04.27"
    match_num_str: "周一001" → 文件前缀 "周一001_*_源数据.md"
    返回文件路径或 None。
    """
    if not match_num_str or not match_date:
        return None
    try:
        from datetime import datetime, timedelta
        dt = datetime.strptime(match_date, '%Y-%m-%d')
        # 竞彩match_date可能是比赛日，分析模板按采集日（可能是前一天）组织
        date_dirs = [
            dt.strftime('%Y.%m.%d'),
            (dt - timedelta(days=1)).strftime('%Y.%m.%d'),
        ]
    except (ValueError, TypeError):
        return None

    prefix = match_num_str + '_'
    for dir_name in date_dirs:
        date_dir = os.path.join(_ANALYSIS_TEMPLATE_DIR, dir_name)
        if not os.path.isdir(date_dir):
            continue
        pattern = os.path.join(date_dir, prefix + '*_源数据.md')
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return None


def _parse_source_md(filepath):
    """
    解析分析模板源数据md文件，提取：
    - initial_odds: list of (主胜, 平局, 客胜) 30家
    - realtime_odds: list of (主胜, 平局, 客胜) 30家
    - macao_tip: 澳门推荐方向字符串
    - home_team, away_team: 队名
    返回dict或None（解析失败时）
    """
    if not filepath or not os.path.isfile(filepath):
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return None

    import re

    result = {
        'initial_odds': [],
        'realtime_odds': [],
        'macao_tip': '',
        'home_team': '',
        'away_team': '',
    }

    # 提取主客队名
    m_home = re.search(r'\|\s*主队\s*\|\s*(.+?)\s*\|', content)
    m_away = re.search(r'\|\s*客队\s*\|\s*(.+?)\s*\|', content)
    if m_home:
        result['home_team'] = m_home.group(1).strip()
    if m_away:
        result['away_team'] = m_away.group(1).strip()

    # 提取澳门推荐
    m_tip = re.search(r'\|\s*澳门推荐\s*\|\s*(.+?)\s*\|', content)
    if m_tip:
        result['macao_tip'] = m_tip.group(1).strip()

    # 提取 initial_odds
    m_init = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if m_init:
        result['initial_odds'] = _parse_odds_block(m_init.group(1))

    # 提取 realtime_odds
    m_real = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if m_real:
        result['realtime_odds'] = _parse_odds_block(m_real.group(1))

    if not result['initial_odds'] or not result['realtime_odds']:
        return None

    return result


def _parse_odds_block(block_text):
    """
    解析赔率数组文本，提取每行的 (主胜, 平局, 客胜) 元组。
    格式: (4.22, 3.45, 1.66),  # 公司名
    """
    import re
    odds_list = []
    # 匹配每一行的元组 (x.xx, y.yy, z.zz)
    for m in re.finditer(r'\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)', block_text):
        try:
            odds_list.append((float(m.group(1)), float(m.group(2)), float(m.group(3))))
        except ValueError:
            continue
    return odds_list


def _calc_pct(init_val, real_val):
    """计算变化百分比"""
    if init_val is None or real_val is None or init_val == 0:
        return 0.0
    return (real_val - init_val) / init_val * 100


def _run_draw_exclusion(source_data):
    """
    基于分析模板源数据运行排除平局分析（同步football_web.py最新逻辑）。
    包含：心水排除、绝对值检查、不怕/不跟标签、推离排除、30家共识、
    分歧检测、低赔排除、冷门预警(R8)、掩护模式(R6)、造热陷阱(R5a)。
    返回dict。
    """
    if not source_data:
        return {'active': False}

    init_odds = source_data.get('initial_odds', [])
    real_odds = source_data.get('realtime_odds', [])
    macao_tip = source_data.get('macao_tip', '').strip()
    # 过滤无效的澳门推荐
    if macao_tip and macao_tip not in ('|', '-', '—', '/', '\\') and len(macao_tip) > 1:
        pass
    else:
        macao_tip = ''

    if not init_odds or not real_odds:
        return {'active': False}

    # 竞彩=idx0, 澳门=idx2
    jc_init = init_odds[0] if len(init_odds) > 0 else None
    jc_real = real_odds[0] if len(real_odds) > 0 else None
    macao_init = init_odds[2] if len(init_odds) > 2 else None
    macao_real = real_odds[2] if len(real_odds) > 2 else None

    if not jc_init or not jc_real:
        return {'active': False}

    # 计算竞彩赔率变化
    jc_h_chg = _calc_pct(jc_init[0], jc_real[0])
    jc_d_chg = _calc_pct(jc_init[1], jc_real[1])
    jc_a_chg = _calc_pct(jc_init[2], jc_real[2])

    # 澳门赔率变化
    macao_h_chg = _calc_pct(macao_init[0], macao_real[0]) if macao_init and macao_real else 0
    macao_d_chg = _calc_pct(macao_init[1], macao_real[1]) if macao_init and macao_real else 0
    macao_a_chg = _calc_pct(macao_init[2], macao_real[2]) if macao_init and macao_real else 0

    current_h = jc_real[0]
    current_d = jc_real[1]
    current_a = jc_real[2]

    excluded = set()
    signals = []
    warnings = []  # 冷门预警/警告

    def _dir_name(d):
        return {'home': '主胜', 'draw': '平局', 'away': '客胜'}.get(d, d)

    def _parse_macao_dir(tip):
        if not tip:
            return 'unknown'
        if '主' in tip or '胜' in tip:
            return 'home'
        elif '客' in tip:
            return 'away'
        elif '和' in tip or '平' in tip or '局' in tip:
            return 'draw'
        return 'unknown'

    def _get_tip_odds(tip_dir):
        if tip_dir == 'home': return current_h
        elif tip_dir == 'draw': return current_d
        elif tip_dir == 'away': return current_a
        return 0

    def _get_tip_jc_chg(tip_dir):
        if tip_dir == 'home': return jc_h_chg
        elif tip_dir == 'draw': return jc_d_chg
        elif tip_dir == 'away': return jc_a_chg
        return 0

    # ========== Step 1: 心水排除法（最高优先级） ==========
    if macao_tip:
        tip_dir = _parse_macao_dir(macao_tip)
        if tip_dir and tip_dir != 'unknown':
            tip_odds = _get_tip_odds(tip_dir)

            if tip_odds >= 5.0:
                excluded.add(tip_dir)
                signals.append({'rule': '心水排除①', 'detail': f"澳门推荐'{macao_tip}'，方向赔率{tip_odds:.2f}≥5.0",
                                'action': f"排除{_dir_name(tip_dir)}", 'strength': 5})
            elif tip_odds >= 3.5:
                excluded.add(tip_dir)
                signals.append({'rule': '心水排除②', 'detail': f"澳门推荐'{macao_tip}'，方向赔率{tip_odds:.2f}≥3.5",
                                'action': f"排除{_dir_name(tip_dir)}", 'strength': 4})
            elif tip_odds >= 3.0:
                tip_jc_chg = _get_tip_jc_chg(tip_dir)
                if tip_jc_chg > 3:
                    excluded.add(tip_dir)
                    signals.append({'rule': '规则B', 'detail': f"澳门推{_dir_name(tip_dir)}+竞彩推离{tip_jc_chg:.1f}%>3%",
                                    'action': f"排除{_dir_name(tip_dir)}", 'strength': 5})
                elif abs(tip_jc_chg) <= 2:
                    signals.append({'rule': '规则A（降级）', 'detail': f"澳门推{_dir_name(tip_dir)}赔率{tip_odds:.2f}，竞彩无明显信号",
                                    'action': f"可能排除{_dir_name(tip_dir)}（50%命中率）", 'strength': 2})
                elif tip_jc_chg < -2:
                    signals.append({'rule': '实盘信号', 'detail': f"澳门推{_dir_name(tip_dir)}+竞彩造热{abs(tip_jc_chg):.1f}%",
                                    'action': f"不排除{_dir_name(tip_dir)}（实盘）", 'strength': 3})

    # ========== Step 2: 赔率绝对值检查 ==========
    if current_h > 5.0:
        excluded.add('home')
        signals.append({'rule': '绝对值排除', 'detail': f"主胜赔率{current_h:.2f}>5.0",
                        'action': '排除主胜', 'strength': 4})
    elif current_h > 3.5:
        signals.append({'rule': '绝对值参考', 'detail': f"主胜赔率{current_h:.2f}>3.5（大概率排除，友谊赛除外）",
                        'action': '倾向排除主胜', 'strength': 3})

    if current_d > 5.0:
        excluded.add('draw')
        signals.append({'rule': '绝对值排除', 'detail': f"平局赔率{current_d:.2f}>5.0",
                        'action': '排除平局', 'strength': 4})
    elif current_d > 3.5:
        signals.append({'rule': '绝对值参考', 'detail': f"平局赔率{current_d:.2f}>3.5（大概率排除，友谊赛除外）",
                        'action': '倾向排除平局', 'strength': 3})

    if current_a > 5.0:
        excluded.add('away')
        signals.append({'rule': '绝对值排除', 'detail': f"客胜赔率{current_a:.2f}>5.0",
                        'action': '排除客胜', 'strength': 4})
    elif current_a > 3.5:
        signals.append({'rule': '绝对值参考', 'detail': f"客胜赔率{current_a:.2f}>3.5（大概率排除，友谊赛除外）",
                        'action': '倾向排除客胜', 'strength': 3})

    # 低赔排除：主胜<1.5时庄家高度自信
    if current_h < 1.5:
        signals.append({'rule': '低赔排除', 'detail': f"主胜赔率{current_h:.2f}<1.5，庄家高度自信",
                        'action': '排除另外两方向可能性高', 'strength': 4})

    # ========== Step 3: 竞彩×澳门互动检查 ==========
    if macao_init and macao_real:
        # [不怕]标签 / [不可靠的不怕]标签
        for dn, di, jcc, mcc in [('home', 0, jc_h_chg, macao_h_chg),
                                  ('draw', 1, jc_d_chg, macao_d_chg),
                                  ('away', 2, jc_a_chg, macao_a_chg)]:
            dir_odds = [current_h, current_d, current_a][di]

            if jcc > 1.0 and abs(mcc) < 0.5:
                if dir_odds >= 3.5:
                    excluded.add(dn)
                    signals.append({'rule': '[不怕]标签',
                                    'detail': f"竞彩升{_dir_name(dn)}{jcc:+.1f}%+澳门不动，{_dir_name(dn)}赔率≥3.5",
                                    'action': f"排除{_dir_name(dn)}", 'strength': 4})
                else:
                    signals.append({'rule': '[不可靠的不怕]',
                                    'detail': f"竞彩升{_dir_name(dn)}+澳门不动，但{_dir_name(dn)}赔率<3.5",
                                    'action': f"不可靠排除{_dir_name(dn)}", 'strength': 1})

            # [不跟]标签：竞彩降+澳门不动=造热假象
            if jcc < -1.0 and abs(mcc) < 0.5:
                signals.append({'rule': '[不跟]标签',
                                'detail': f"竞彩降{_dir_name(dn)}{jcc:+.1f}%+澳门不动",
                                'action': f"{_dir_name(dn)}造热是假象", 'strength': 4})

        # 推离排除：竞彩升>5%
        for dn, jcc in [('home', jc_h_chg), ('draw', jc_d_chg), ('away', jc_a_chg)]:
            if jcc > 5:
                excluded.add(dn)
                signals.append({'rule': '推离排除',
                                'detail': f"竞彩{_dir_name(dn)}升{jcc:+.1f}%>5%",
                                'action': f"排除{_dir_name(dn)}", 'strength': 4})

    # ========== Step 4: 30家公司共识检查 ==========
    total = len(init_odds)
    h_down = h_up = d_down = d_up = a_down = a_up = 0
    for ini, real in zip(init_odds, real_odds):
        for i, (iv, rv) in enumerate(zip(ini, real)):
            pct = (rv - iv) / iv * 100 if iv != 0 else 0
            if i == 0:
                if pct < -0.5: h_down += 1
                elif pct > 0.5: h_up += 1
            elif i == 1:
                if pct < -0.5: d_down += 1
                elif pct > 0.5: d_up += 1
            else:
                if pct < -0.5: a_down += 1
                elif pct > 0.5: a_up += 1

    signals.append({'rule': '30家公司共识',
                    'detail': f"主降{h_down}升{h_up} / 平降{d_down}升{d_up} / 客降{a_down}升{a_up}",
                    'action': '', 'strength': 3})

    if a_up >= total * 0.85:
        signals.append({'rule': '强共识推离客', 'detail': f"{a_up}/{total}家公司升客胜（>{int(total*0.85)}家阈值）",
                        'action': '强烈推离客胜', 'strength': 4})
    if h_up >= total * 0.85:
        signals.append({'rule': '强共识推离主', 'detail': f"{h_up}/{total}家公司升主胜（>{int(total*0.85)}家阈值）",
                        'action': '强烈推离主胜', 'strength': 4})
    if a_down >= total * 0.85:
        signals.append({'rule': '强共识造热客', 'detail': f"{a_down}/{total}家公司降客胜（>{int(total*0.85)}家阈值）",
                        'action': '全面造热客（需判断出口结构）', 'strength': 4})
    if h_down >= total * 0.85:
        signals.append({'rule': '强共识造热主', 'detail': f"{h_down}/{total}家公司降主胜（>{int(total*0.85)}家阈值）",
                        'action': '全面造热主（需判断出口结构）', 'strength': 4})

    # ========== Step 5: 竞彩×澳门分歧检测 ==========
    if macao_init and macao_real:
        conflicts = []
        for dir_label, jcc, mcc in [("主", jc_h_chg, macao_h_chg), ("平", jc_d_chg, macao_d_chg), ("客", jc_a_chg, macao_a_chg)]:
            if abs(jcc) > 2 and abs(mcc) > 2 and ((jcc > 0) != (mcc > 0)):
                conflicts.append(dir_label)
        if conflicts:
            signals.append({'rule': '⚠️ 分歧警告',
                            'detail': f"竞彩与澳门在{'/'.join(conflicts)}方向相反",
                            'action': '信号降级', 'strength': 0})
            warnings.append(f"竞彩×澳门在{','.join(conflicts)}方向分歧")

    # ========== Step 6: R8 冷门检测器 ==========
    # 核心逻辑：当"赔率变化信号"足够强时，可以覆盖"赔率绝对值排除"
    # 适用场景：庄家主动引导筹码去低赔方向，掩护高赔方向打出
    if len(real_odds) >= 20:
        cold_exclusions_to_remove = set()  # R8覆盖的排除
        for dn, di, jcc in [('home', 0, jc_h_chg), ('draw', 1, jc_d_chg), ('away', 2, jc_a_chg)]:
            dir_odds = [current_h, current_d, current_a][di]
            if dir_odds < 3.5:
                continue  # 只检测被绝对值排除的高赔方向

            if dn not in excluded:
                continue  # 没被排除的不需要R8覆盖

            # 计算竞彩变化
            chg_pct = jcc
            jc_dropping = chg_pct < -2
            jc_strong_drop = chg_pct < -5

            # 计算30家公司降赔数量
            dir_down_count = 0
            dir_up_count = 0
            for ini, real in zip(init_odds, real_odds):
                pct = _calc_pct(ini[di], real[di])
                if pct < -0.5:
                    dir_down_count += 1
                elif pct > 0.5:
                    dir_up_count += 1

            consensus_drop = dir_down_count >= total * 0.7
            strong_consensus = dir_down_count >= total * 0.85

            # 澳门同向
            macao_chg = [macao_h_chg, macao_d_chg, macao_a_chg][di]
            macao_agrees = macao_chg < -1.0 if macao_init and macao_real else False

            # 心水同向
            tip_match = False
            if macao_tip:
                tip_dir = _parse_macao_dir(macao_tip)
                if tip_dir == dn:
                    tip_match = True

            # R8评分
            r8_score = 0
            r8_reasons = []
            if jc_strong_drop:
                r8_score += 40
                r8_reasons.append(f'竞彩强降{chg_pct:.1f}%')
            elif jc_dropping:
                r8_score += 25
                r8_reasons.append(f'竞彩降{chg_pct:.1f}%')
            if strong_consensus:
                r8_score += 30
                r8_reasons.append(f'{dir_down_count}/30家强共识')
            elif consensus_drop:
                r8_score += 18
                r8_reasons.append(f'{dir_down_count}/30家同向降')
            if macao_agrees:
                r8_score += 15
                r8_reasons.append('澳门同向降')
            if tip_match:
                r8_score += 10
                r8_reasons.append(f'心水同向({macao_tip})')

            if r8_score >= 65:
                bonus = min(r8_score, 90)
                cold_exclusions_to_remove.add(dn)
                signals.append({'rule': '🧊 R8-冷门检测⚡',
                                'detail': f"{_dir_name(dn)}: {'+'.join(r8_reasons)}, 极端变化信号强力覆盖绝对值",
                                'action': f"⚠️ 取消排除{_dir_name(dn)}! 冷门风险极高",
                                'strength': 6})
                warnings.append(f"R8-极端冷门: {_dir_name(dn)}被绝对值排除但{'+'.join(r8_reasons)}")
            elif r8_score >= 50:
                cold_exclusions_to_remove.add(dn)
                signals.append({'rule': '🧊 R8-冷门检测',
                                'detail': f"{_dir_name(dn)}: {'+'.join(r8_reasons)}, 变化信号覆盖绝对值",
                                'action': f"⚠️ 取消排除{_dir_name(dn)}! 可能冷门",
                                'strength': 5})
                warnings.append(f"R8-冷门: {_dir_name(dn)}被排除但{'+'.join(r8_reasons)}")
            elif r8_score >= 30:
                signals.append({'rule': '🧊 R8-冷门预警',
                                'detail': f"{_dir_name(dn)}: {'+'.join(r8_reasons)}, 存在冷门可能",
                                'action': f"降低排除{_dir_name(dn)}置信度",
                                'strength': 4})
                warnings.append(f"R8-预警: {_dir_name(dn)}有冷门风险({'+'.join(r8_reasons)})")

        # 移除被R8覆盖的排除
        for dn in cold_exclusions_to_remove:
            excluded.discard(dn)

    # ========== Step 7: R6 掩护模式检测 ==========
    # 平赔不动（竞彩降平+澳门不动）可能掩护平局
    quiet_draw = False
    if macao_init and macao_real:
        if jc_d_chg < -1.0 and abs(macao_d_chg) < 0.5:
            quiet_draw = True
    if quiet_draw:
        signals.append({'rule': '🛡️ R6-掩护模式',
                        'detail': f"竞彩降平{jc_d_chg:+.1f}%+澳门平不动，庄家掩护平局",
                        'action': '⚠️ 平局被掩护，排除平局需谨慎',
                        'strength': 4})
        warnings.append("R6-掩护模式: 平赔不动，庄家可能在掩护平局")

    # ========== Step 8: R5a 造热陷阱检测 ==========
    # 单出口全面造热：三方向同向≠可靠，可能是陷阱
    has_dual_heat = False
    if macao_init and macao_real:
        for dn, jcc, mcc in [('home', jc_h_chg, macao_h_chg), ('away', jc_a_chg, macao_a_chg)]:
            if jcc < -2 and mcc < -2:  # 竞彩和澳门同时降赔某方向
                has_dual_heat = True
                break
    if has_dual_heat:
        signals.append({'rule': '🔴 R5a-造热陷阱',
                        'detail': '竞彩×澳门同向造热某方向，三方向同向≠可靠',
                        'action': '当前预测可能是陷阱，建议降低置信度',
                        'strength': 4})
        warnings.append("R5a-造热陷阱: 竞彩×澳门同向造热")

    # ========== 综合结果 ==========
    signals.sort(key=lambda s: s.get('strength', 0), reverse=True)

    n_excluded = len(excluded)
    remaining = set(['home', 'draw', 'away']) - excluded
    prediction = ''
    confidence = 1
    confidence_text = ''
    has_cold = any('冷门' in w or 'R8' in w for w in warnings)
    has_heat_trap = any('造热陷阱' in w or 'R5a' in w for w in warnings)

    if n_excluded >= 2 and remaining:
        final = remaining.pop()
        prediction = _dir_name(final)
        if has_cold:
            confidence = 3
            confidence_text = '★★★ 排除2个，但有冷门预警⚠️'
            warnings.append('存在冷门预警信号，排除2方向的置信度降为★★★')
        else:
            confidence = 5
            confidence_text = '★★★★★ 排除2个方向'
    elif n_excluded == 1:
        remaining_dirs = list(remaining)
        if len(remaining_dirs) == 2:
            odds_r = {d: [current_h, current_d, current_a][['home', 'draw', 'away'].index(d)] for d in remaining_dirs}
            low_dir = min(odds_r.keys(), key=lambda x: odds_r[x])
            high_dir = max(odds_r.keys(), key=lambda x: odds_r[x])
            diff = abs(odds_r[low_dir] - odds_r[high_dir])

            if has_cold:
                confidence = 3
                confidence_text = f"★★★ 排除1个+冷门预警⚠️"
            elif has_heat_trap:
                confidence = 3
                confidence_text = f"★★★ 排除1个+造热陷阱⚠️"
            elif diff > 0.5:
                prediction = _dir_name(low_dir)
                confidence = 4
                confidence_text = f"★★★★ 排除1个，选低赔({odds_r[low_dir]:.2f})"
            else:
                prediction = '平局'
                confidence = 3
                confidence_text = f"★★★ 排除1个，赔率接近优先考虑平局"
        else:
            prediction = _dir_name(remaining_dirs[0]) if remaining_dirs else '无法判断'
            confidence = 3
    else:
        prediction = '观望'
        confidence_text = '★ 无法有效排除'

    return {
        'active': True,
        'draw_excluded': 'draw' in excluded,
        'exclusions': list(excluded),
        'signals': signals,
        'warnings': warnings,
        'prediction': prediction,
        'confidence': confidence,
        'confidence_text': confidence_text,
        'source': f"{source_data.get('home_team', '')} vs {source_data.get('away_team', '')}",
        'macao_tip': macao_tip,
    }


def _get_draw_exclusion(match_num_str, match_date):
    """
    便捷函数：查找分析模板 → 解析 → 运行排除平局分析。
    任何一步失败都返回 {'active': False}。
    """
    filepath = _find_source_md(match_num_str, match_date)
    if not filepath:
        return {'active': False}
    source_data = _parse_source_md(filepath)
    if not source_data:
        return {'active': False}
    return _run_draw_exclusion(source_data)


def _analyze_draw_signal(had, hhad):
    """
    平局信号分析（结合HAD平局赔率 + HHD让平赔率，基于361场回测）
    返回:
        {
            'active': bool,        # 是否有had数据
            'had_draw': float,     # had.平赔率
            'hhd_draw': float,     # hhd.让平赔率（若有）
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

    # 提取让平赔率（HHD）
    hhd_draw = 0
    if hhad and '让平' in hhad:
        try:
            hhd_draw = float(hhad['让平'])
        except (ValueError, TypeError):
            hhd_draw = 0

    result = {
        'active': True,
        'had_draw': had_draw,
        'hhd_draw': hhd_draw,
        'special_combo': False,
        'combo_778': False,
        'draw_level': 'medium',
        'draw_pct': 27,
        'draw_reason': '',
    }

    # ── 规则1：高平局概率（>40%）──
    # HAD平局[3.0,3.2) → 42.6%  OR  HHD让平<3.3 → 41.0%
    is_high_had = (3.0 <= had_draw < 3.2)
    is_high_hhd = (hhd_draw > 0 and hhd_draw < 3.3)
    if is_high_had or is_high_hhd:
        if is_high_had and is_high_hhd:
            # 双高信号叠加
            result['draw_pct'] = 43
            result['draw_level'] = 'high'
            result['draw_reason'] = 'had.平=%.2f[3.0,3.2) + 让平=%.2f<3.3, 平局率约43%%' % (had_draw, hhd_draw)
        elif is_high_had:
            result['draw_pct'] = 43
            result['draw_level'] = 'high'
            result['draw_reason'] = 'had.平=%.2f 高危区间[3.0,3.2), 平局率42.6%%(%d场)' % (had_draw, 47)
        else:
            result['draw_pct'] = 41
            result['draw_level'] = 'high'
            result['draw_reason'] = '让平=%.2f<3.3, 平局率41.0%%(%d场)' % (hhd_draw, 61)

    # ── 规则2：低平局概率（<20%）──
    # HHD让平[3.3,3.5) → 20.7%  ← 最强单独信号
    # HAD平局≥3.7 → 19.5%
    is_low_hhd = (hhd_draw > 0 and 3.3 <= hhd_draw < 3.5)
    is_low_had = (had_draw >= 3.7)
    # HAD≤3.0 + HHD≥3.3 → ~20%  ← 新增（优先级更高）
    is_low_combo = (had_draw <= 3.0 and hhd_draw >= 3.3)
    
    if is_low_combo:
        result['draw_level'] = 'low'
        result['draw_pct'] = 20
        result['draw_reason'] = 'had.平=%.2f<=3.0 + 让平=%.2f>=3.3, 平局率约20%%' % (had_draw, hhd_draw)
    elif is_low_hhd or is_low_had:
        result['draw_level'] = 'low'
        pct = 21
        reasons = []
        if is_low_hhd:
            pct = min(pct, 21)
            reasons.append('让平=%.2f[3.3,3.5)' % hhd_draw)
        if is_low_had:
            pct = min(pct, 20)
            reasons.append('had.平=%.2f>=3.7' % had_draw)
        result['draw_pct'] = pct
        result['draw_reason'] = ' + '.join(reasons) + ', 平局率约%d%%' % pct

    # ── 规则3：最强排除信号（平局率<15%）──
    # HHD让平[3.3,3.5) + HAD平局≥3.7 → 平局率<15%
    if is_low_hhd and is_low_had:
        result['draw_level'] = 'very_low'
        result['draw_pct'] = 15
        result['draw_reason'] = '⚠️ 最强排除: 让平=%.2f[3.3,3.5) + had.平=%.2f>=3.7, 平局率<15%%' % (hhd_draw, had_draw)

    # ── 原有区间判断（作为补充，当上述规则未触发时）──
    if result['draw_reason'] == '':
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
    if 3.4 <= had_draw < 3.6 and hhd_draw > 0 and hhd_draw < 3.3:
        try:
            hhd_win = float(hhad['让胜'])
            # 77.8%组合（9场7平）
            result['combo_778'] = True
            result['draw_pct'] = 78
            result['draw_level'] = 'high'
            result['draw_reason'] = 'had.平=%.2f + 让平%.2f<3.3, 平局率77.8%%(9场)' % (had_draw, hhd_draw)
            # 差值过滤：100%(7/7)
            if abs(hhd_draw - hhd_win) >= 0.3:
                result['special_combo'] = True
                result['draw_level'] = 'super_high'
                result['draw_pct'] = 100
                result['draw_reason'] = '⚠️ 超高平局信号: had.平=%.2f+让平%.2f+|让平-让胜|>=0.3, 平局率100%%(7/7)' % (had_draw, hhd_draw)
        except (ValueError, TypeError, KeyError):
            pass

    return result


def _build_match_card(data, api, match_list_cache=None):
    """
    提取比赛数据中卡片展示所需的字段，构建轻量化对象。
    完整版返回全部字段（兼容旧逻辑），精简版只返回卡片需要的内容。
    match_list_cache: 预加载的比赛列表缓存，避免重复调用API。
    """
    is_light = request.args.get('light') == '1'

    # ── 自动补充旧数据缺失的 match_info 字段（使用缓存）──
    match_info = data.get('match_info', {})
    if not match_info.get('match_num_str') and api:
        try:
            list_data = match_list_cache or api.get_match_list()
            mid_str = str(data.get('match_id', ''))
            if mid_str in list_data:
                extra = list_data[mid_str]
                for k, v in [('match_num_str', 'matchNumStr'), ('match_week', 'matchWeek'),
                             ('match_date', 'matchDate'), ('match_time', 'matchTime'),
                             ('match_status', 'matchStatus'), ('home_rank', 'homeRank'),
                             ('away_rank', 'awayRank'), ('league_abbr', 'leagueAbbName')]:
                    if not match_info.get(k) and extra.get(v):
                        match_info[k] = extra[v]
                if not match_info.get('time') and extra.get('matchDate'):
                    t = extra.get('matchTime', '00:00:00')[:5]
                    match_info['time'] = extra['matchDate'] + ' ' + t
                data['match_info'] = match_info  # 回写到 data，后续完整版也能用
        except Exception:
            pass

    # 计算近况数据（精简版和完整版共用）
    recent_form = None
    rd = None
    try:
        team_names = {
            'home': match_info.get('home_team', ''),
            'away': match_info.get('away_team', ''),
        }
        rd = _extract_recent_matches(data, team_names)
        recent_form = calc_recent_form(rd)
    except Exception:
        pass

    if is_light:
        # ── 精简版：只包含卡片和分页需要的数据 ──
        g3_pred = data.get('g3_prediction', {})
        hhad = data.get('hhad', {})
        had = data.get('had', {})
        ttg_change = data.get('ttg_change', {})
        hafu_change = data.get('hafu_change', {})
        exclusion_list = data.get('exclusion_list', [])

        # 让球平低赔规律分析
        hhad_hint = _analyze_hhad_low_draw(hhad, recent_form, data)

        # 主让+让负低赔规律分析（217场回测，含近况决策树）
        hhad_lose_hint = _analyze_hhad_lose_low(hhad, recent_form)

        # 平局信号分析（所有had.平区间均显示）
        draw_hint = _analyze_draw_signal(had, hhad)

        # 排除平局分析（基于分析模板源数据，football_web逻辑）
        draw_exclusion = _get_draw_exclusion(
            match_info.get('match_num_str', ''),
            match_info.get('match_date', '')
        )

        return {
            'match_id': data.get('match_id'),
            'fetch_time': data.get('fetch_time'),
            'match_info': {
                'home_team': match_info.get('home_team', '未知'),
                'away_team': match_info.get('away_team', '未知'),
                'league': match_info.get('league', ''),
                'league_abbr': match_info.get('league_abbr', ''),
                'time': match_info.get('time', ''),
                'match_num_str': match_info.get('match_num_str', ''),
                'match_week': match_info.get('match_week', ''),
                'match_date': match_info.get('match_date', ''),
                'match_time': match_info.get('match_time', ''),
                'match_status': match_info.get('match_status', ''),
                'home_rank': match_info.get('home_rank', ''),
                'away_rank': match_info.get('away_rank', ''),
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
                'golden_1goals': g3_pred.get('golden_1goals'),
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
            'hafu_change': hafu_change,
            'had_change': data.get('had_change', {}),
            'hhad_change': data.get('hhad_change', {}),
            'exclusion_list': exclusion_list,
            # 比分历史命中率推荐（新）
            'score_recommendations': data.get('score_recommendations', []),
            # 大小球数据（用户手动保存）
            'over_under': data.get('over_under', {}),
            # 近况数据（让球平规律用）
            'recent_form': {
                'home_avg': recent_form['home_avg'],
                'away_avg': recent_form['away_avg'],
                'combined_avg': recent_form['combined_avg'],
            } if recent_form else None,
            # 近况简显
            'near_form': {
                'home': recent_form['home_avg'] if recent_form else None,
                'away': recent_form['away_avg'] if recent_form else None,
            } if recent_form else None,
            # 近5场赛果（比分反推验证用）
            'recent_matches': rd if recent_form else {'home': [], 'away': []},
            # V3.6: 变化命中率数据（用于AI推理）
            'ttg_hitrates': _build_change_hitrate() if recent_form else {},
            # 让球平低赔规律提示
            'hhad_hint': hhad_hint,
            # 主让+让负低赔规律（217场回测）
            'hhad_lose_hint': hhad_lose_hint,
            # 平局信号（所有had.平区间）
            'draw_hint': draw_hint,
            # 排除平局分析（football_web逻辑）
            'draw_exclusion': draw_exclusion,
        }
    else:
        # ── 完整版：返回全部字段 ──
        # 近况简显
        _full_rf = None
        try:
            _full_rd = _extract_recent_matches(data)
            _full_rf = calc_recent_form(_full_rd)
        except Exception:
            pass
        data['near_form'] = {
            'home': _full_rf['home_avg'] if _full_rf else None,
            'away': _full_rf['away_avg'] if _full_rf else None,
        } if _full_rf else None
        # 平局信号分析
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

    # ── 预加载比赛列表（一次请求，供所有旧数据补充字段）──
    _match_list_cache = None

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
                        # 黄金1球预测
                        g1_pred = predict_1goals(features)
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
                            'golden_1goals': g1_pred,
                            'golden_2goals': g2_pred,
                            'golden_4goals': g4_pred,
                            # 最终推荐（基于最严谨的方法）
                            'final_rec': final_rec,
                            # 大3球 vs 小3球预判
                            'big3_vs_small3': big3_small3,
                        }
                    except Exception as ex:
                        pass
                    # 懒加载：只有旧数据才触发一次 get_match_list
                    if not data.get('match_info', {}).get('match_num_str') and _match_list_cache is None:
                        try:
                            _match_list_cache = api.get_match_list()
                        except Exception:
                            pass
                    matches.append(_build_match_card(data, api, match_list_cache=_match_list_cache))
        except:
            pass

    matches.sort(key=lambda x: x.get('fetch_time', ''), reverse=True)
    # 应用累积统计数据覆盖硬编码命中率
    for m in matches:
        apply_accumulated_stats(m)
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
            # 主让+让负低赔规律（217场回测）
            hhad_lose_hint = _analyze_hhad_lose_low(_hhad, _recent_form)
            result['hhad_lose_hint'] = hhad_lose_hint
            # 黄金1球预测
            g1_pred = predict_1goals(features)
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
                signal_type = big3_pred.get('signal_type')  # 前置条件/规律名称（来自big3_vs_small3）

                if prediction == '不确定':
                    big3_result = 'unknown'
                elif prediction == '大3球' and big3_actual == '大3球':
                    big3_result = 'hit'
                elif prediction == '小3球' and big3_actual == '小3球':
                    big3_result = 'hit'
                else:
                    big3_result = 'miss'

                # 获取最终推荐的signal_type
                final_rec = data.get('g3_prediction', {}).get('final_rec', {})
                final_signal_type = final_rec.get('signal_type', '')  # 最终推荐的signal_type

                # 保存到记录
                record['big3_signal_type'] = signal_type  # 前置条件/规律名称（来自big3_vs_small3）
                record['final_signal_type'] = final_signal_type  # 最终推荐的signal_type
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

@app.route('/api/update-rec-stats/<match_id>', methods=['POST'])
def update_rec_stats(match_id):
    """更新推荐统计数据（v2.6新增）
    Body: {
        "home_score": 1, "away_score": 0,
        "rules": [
            {"type": "golden_1goals", "target_goals": 1, "hit_rate": 44.8, "sample": 29},
            {"type": "exclude_2ball_B", "target_goals": 2, "hit_rate": 17.6, "sample": 17},
            {"type": "exclude_4ball_A", "target_goals": 4, "hit_rate": 0.0, "sample": 12}
        ]
    }
    返回: updated rules with new hit_rate and sample
    """
    try:
        body = request.get_json() or {}
        home = int(body.get('home_score', -1))
        away = int(body.get('away_score', -1))
        rules = body.get('rules', [])
        if home < 0 or away < 0:
            return jsonify({'success': False, 'error': '比分格式错误'}), 400

        total_goals = home + away
        stats = load_rec_stats()

        # 防止重复统计
        if match_id in stats:
            return jsonify({'success': False, 'error': '该比赛已统计过，不能重复提交'}), 400

        updated_rules = []
        for rule in rules:
            rule_type = rule.get('type', '')
            target_goals = rule.get('target_goals', 0)
            old_hit_rate = rule.get('hit_rate', 0)
            old_sample = rule.get('sample', 0)

            # 判断：实际总进球是否等于目标进球数（统一逻辑）
            is_hit = (total_goals == target_goals)
            
            new_hit_rate = round((old_hit_rate * old_sample / 100 + (1 if is_hit else 0)) / (old_sample + 1) * 100, 1)
            new_sample = old_sample + 1

            updated_rules.append({
                'type': rule_type,
                'old_hit_rate': old_hit_rate,
                'new_hit_rate': new_hit_rate,
                'old_sample': old_sample,
                'new_sample': new_sample,
                'is_hit': is_hit,
                'target_goals': target_goals,  # 用于后续实盘统计
            })

        # 保存记录
        stats[match_id] = {
            'home_score': home,
            'away_score': away,
            'total_goals': total_goals,
            'rules': updated_rules,
            'time': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M'),
        }
        save_rec_stats(stats)

        return jsonify({'success': True, 'updated_rules': updated_rules})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ────────────────────────────────────────────────────────────
#  大小球保存
# ────────────────────────────────────────────────────────────
@app.route('/api/over_under/<match_id>', methods=['POST'])
def save_over_under(match_id):
    """保存大小球赔率数据
    Body: { "over_odds": 1.85, "ou_line": 2.5, "under_odds": 2.05 }
    """
    try:
        from flask import request
        body = request.get_json() or {}
        over_odds = float(body.get('over_odds', 0))
        ou_line = float(body.get('ou_line', -1))
        under_odds = float(body.get('under_odds', 0))
        
        if over_odds <= 0 or ou_line < 0 or under_odds <= 0:
            return jsonify({'success': False, 'error': '大小球数据格式错误'}), 400
        
        # 保存到比赛的JSON文件
        filepath = os.path.join(DATA_DIR, f'{match_id}.json')
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': '比赛数据不存在'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 添加/更新大小球数据
        if 'over_under' not in data:
            data['over_under'] = {}
        data['over_under'] = {
            'over_odds': over_odds,
            'ou_line': ou_line,
            'under_odds': under_odds,
            'save_time': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'data': data['over_under']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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

@app.route('/api/match-info/<match_id>', methods=['PATCH'])
def patch_match_info(match_id):
    """
    手动补全 / 修正比赛抬头信息（对旧数据缺失 match_num_str 等字段时使用）
    Body JSON 支持字段：match_num_str, match_date, match_time, home_rank, away_rank, league_abbr
    直接写回 sporttery_data/<match_id>.json 的 match_info 段。
    """
    try:
        filepath = os.path.join(DATA_DIR, f'{match_id}.json')
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': '文件不存在'})
        body = request.get_json(force=True, silent=True) or {}
        allowed = {'match_num_str', 'match_date', 'match_time', 'home_rank', 'away_rank', 'league_abbr', 'match_status', 'match_week'}
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        mi = data.setdefault('match_info', {})
        for k, v in body.items():
            if k in allowed:
                mi[k] = v
        # 同步 time 字段（给旧数据兼容）
        if mi.get('match_date') and mi.get('match_time'):
            mi['time'] = mi['match_date'] + ' ' + mi['match_time']
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({'success': True, 'match_info': mi})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/odds_hitrate')
def get_odds_hitrate():
    """返回赔率命中率统计（供复盘后动态刷新）"""
    global _odds_hitrate_cache, _score_hitrate_cache, _change_hitrate_cache
    _odds_hitrate_cache = None   # 清除进球数赔率缓存
    _score_hitrate_cache = None  # 同时清除比分赔率缓存
    _change_hitrate_cache = None # 同时清除变化命中率缓存
    stats = _build_odds_hitrate()
    return jsonify(stats)

@app.route('/api/change_hitrate')
def get_change_hitrate():
    """返回进球数变化命中率统计（供复盘后动态刷新）"""
    global _change_hitrate_cache
    _change_hitrate_cache = None
    return jsonify(_build_change_hitrate())

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
        similar = find_similar_matches(current_data, top_n=8)
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
        similar = find_similar_matches(current_data, top_n=8)
        return jsonify({'success': True, 'similar': similar})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/test_law3')
def test_law3():
    """测试规律3是否触发（用于调试）"""
    try:
        import json as json_mod
        
        # 读取利物浦比赛数据
        with open('sporttery_data/2039323.json', 'r', encoding='utf-8') as f:
            d = json_mod.load(f, strict=False)
        
        # 手动计算近况差
        recent_form = None
        preview = d.get('preview', {})
        recent = preview.get('recent', {})
        if recent:
            home_data = recent.get('home', {})
            away_data = recent.get('away', {})
            home_list = home_data.get('matchList', []) if isinstance(home_data, dict) else []
            away_list = away_data.get('matchList', []) if isinstance(away_data, dict) else []
            
            if home_list and away_list:
                try:
                    home_avg = sum([float(x.get('homeTeamFullCourtGoalCnt', 0)) for x in home_list]) / len(home_list)
                    away_avg = sum([float(x.get('awayTeamFullCourtGoalCnt', 0)) for x in away_list]) / len(away_list)
                    combined_avg = (home_avg + away_avg) / 2
                    recent_form = {
                        'home_avg': home_avg,
                        'away_avg': away_avg,
                        'combined_avg': combined_avg
                    }
                except: pass
        
        # 调用分析函数，并捕获内部变量
        import inspect
        source_lines = inspect.getsource(_analyze_hhad_low_draw)
        
        # 修改函数，添加debug输出
        debug_info = {
            'match_id': '2039323',
            'recent_form_passed': recent_form,
            'recent_form_valid': recent_form is not None and recent_form.get('home_avg') is not None
        }
        
        # 手动计算所有中间变量
        hhad = d.get('hhad', {})
        had = d.get('had', {})
        
        hhad_win = float(hhad.get('让胜', 0))
        hhad_draw = float(hhad.get('让平', 0))
        
        had_win = 0
        if had:
            if '胜' in had:
                had_win = float(had.get('胜', 0))
            elif '主胜' in had:
                had_win = float(had.get('主胜', 0))
        
        form_diff = None
        if recent_form and recent_form.get('home_avg') is not None:
            form_diff = recent_form['home_avg'] - recent_form['away_avg']
        
        debug_info['hhad_win'] = hhad_win
        debug_info['hhad_draw'] = hhad_draw
        debug_info['had_win'] = had_win
        debug_info['form_diff'] = form_diff
        debug_info['condition_1_hhad_win_lt_2.2'] = hhad_win < 2.2
        debug_info['condition_2_hhad_draw_ge_3.7'] = hhad_draw >= 3.7
        debug_info['condition_3_form_diff_gt_0'] = form_diff is not None and form_diff > 0
        debug_info['condition_4_had_win_in_0_1.5'] = 0 < had_win < 1.5
        debug_info['is_law3_calculated'] = hhad_win < 2.2 and hhad_draw >= 3.7 and form_diff is not None and form_diff > 0 and 0 < had_win < 1.5
        
        # 调用原函数（注意：第三个参数是完整比赛数据d）
        result = _analyze_hhad_low_draw(d, recent_form, d)
        debug_info['function_result'] = result
        
        return jsonify(debug_info)
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()})

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print('='*60)
    print('竞彩比分预测系统')
    print('='*60)
    print('访问地址: http://192.168.0.101:8899')
    print('='*60)
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8899)), debug=False, threaded=True)
