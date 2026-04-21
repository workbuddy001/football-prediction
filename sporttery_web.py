#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞彩比分预测系统 - 完整版
"""
from flask import Flask, jsonify, render_template_string, request
from markupsafe import Markup
import os
import json
import glob
from sporttery_api import SportteryAPI
from predict_3goals import extract_features, predict_3goals, calc_recent_form, _extract_recent_matches
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

def _build_odds_hitrate():
    """
    遍历所有有比分的历史记录，计算各进球数在各赔率区间的历史命中率。
    返回格式:
      overall[goal] = (total, hits)   # 该进球数全场命中率
      bucket[goal][bucket_key] = (total, hits)  # bucket_key 如 "3.0~3.5"
    """
    global _odds_hitrate_cache
    if _odds_hitrate_cache is not None:
        return _odds_hitrate_cache

    scores = load_scores()
    sporttery_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_DIR)

    overall = {}   # overall[goal] = [total, hits]
    buckets = {}  # buckets[goal][bucket_key] = [total, hits]

    def bucket_key(val, step=0.5):
        """0.5步长区间"""
        center = round(val / step) * step
        lo = round(center - step / 2, 2)
        hi = round(center + step / 2, 2)
        return '%.2f~%.2f' % (lo, hi)

    for key, record in scores.items():
        tg = record.get('total_goals')
        mid = record.get('match_id', key)
        if tg is None or not str(mid).isdigit():
            continue
        tg = int(tg)
        fp = os.path.join(sporttery_dir, '%s.json' % mid)
        if not os.path.exists(fp):
            continue
        try:
            d = json.load(open(fp, encoding='utf-8'))
            tg_odds = d.get('total_goals', {})
        except:
            continue

        for goal in range(0, 8):
            od_val = tg_odds.get('%d球' % goal)
            if not od_val:
                continue
            try:
                val = float(od_val)
            except:
                continue

            # overall
            if goal not in overall:
                overall[goal] = [0, 0]
            overall[goal][0] += 1
            if tg == goal:
                overall[goal][1] += 1

            # bucket
            bk = bucket_key(val)
            if goal not in buckets:
                buckets[goal] = {}
            if bk not in buckets[goal]:
                buckets[goal][bk] = [0, 0]
            buckets[goal][bk][0] += 1
            if tg == goal:
                buckets[goal][bk][1] += 1

    # 计算命中率
    def rate(total, hits):
        return round(hits / total * 100, 1) if total > 0 else None

    overall_stats = {g: {'total': v[0], 'hits': v[1], 'rate': rate(v[0], v[1])}
                     for g, v in overall.items() if v[0] > 0}
    bucket_stats = {}
    for g, bk_data in buckets.items():
        bucket_stats[g] = {
            bk: {'total': v[0], 'hits': v[1], 'rate': rate(v[0], v[1])}
            for bk, v in bk_data.items() if v[0] > 0
        }

    _odds_hitrate_cache = {'overall': overall_stats, 'bucket': bucket_stats}
    return _odds_hitrate_cache

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
    <title>竞彩比分预测系统</title>
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

        /* 进球数-比分联动排除列表 */
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
        .golden-badge { background: linear-gradient(90deg, #b8860b, #ffd700); color: #000; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 10px; margin-left: 8px; }
        .golden-reason { font-size: 11px; color: #f1c40f; background: rgba(241,196,15,0.08); border-left: 3px solid #f1c40f; padding: 6px 10px; border-radius: 0 6px 6px 0; margin: 4px 0 8px; }
        .g3-signal-item.signal-golden { background: rgba(241,196,15,0.1); border-left: 3px solid #f1c40f; }
        .signal-golden .g3-signal-tag { color: #f1c40f; }
        .signal-golden .g3-signal-score { color: #f1c40f; }
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
        .g3-signals { display: flex; flex-direction: column; gap: 4px; }
        .g3-signal-item { display: flex; align-items: center; gap: 8px; padding: 4px 8px; border-radius: 6px; font-size: 12px; }
        .g3-signal-item.signal-plus { background: rgba(34,197,94,0.08); border-left: 3px solid #22c55e; }
        .g3-signal-item.signal-minus { background: rgba(239,68,68,0.08); border-left: 3px solid #ef4444; }
        .g3-signal-item.signal-neutral { background: rgba(148,163,184,0.06); border-left: 3px solid #888; }
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
        /* 相似比赛面板 */
        .similar-panel { margin-top: 10px; background: #0d1b2a; border-radius: 8px; border: 1px solid #1e3a5f; overflow: hidden; }
        .similar-header { background: #0f3460; color: #a78bfa; font-size: 12px; font-weight: bold; padding: 8px 12px; }
        .similar-item { display: flex; align-items: center; padding: 8px 12px; border-bottom: 1px solid #1e3a5f; gap: 10px; font-size: 12px; }
        .similar-item:last-child { border-bottom: none; }
        .similar-rank { font-weight: bold; color: #a78bfa; min-width: 20px; }
        .similar-teams { flex: 1; color: #ccc; }
        .similar-score { font-weight: bold; min-width: 50px; text-align: center; }
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
        // 进球数赔率命中率统计
        const _ODDS_HITRATE = __ODDS_STATS_JSON__;
        const _HITRATE_COLORS = {green:'#4ade80', yellow:'#facc15', red:'#f87171', gray:'#888'};
        function _getHitRateLabel(goalNum, oddsVal) {
            const bk = _ODDS_HITRATE.bucket || {};
            const goalBuckets = bk[goalNum] || {};
            // 找精确bucket
            let found = null;
            for (const [bkStr, d] of Object.entries(goalBuckets)) {
                const [lo, hi] = bkStr.split('~').map(Number);
                if (oddsVal >= lo && oddsVal <= hi) { found = d; break; }
            }
            const rate = found ? found.rate : null;
            const total = found ? found.total : 0;
            const color = rate === null ? 'gray' : rate >= 35 ? 'green' : rate >= 20 ? 'yellow' : 'red';
            if (rate === null) return '';
            return `<span class="hitrate-badge" style="font-size:10px;padding:1px 5px;border-radius:4px;margin-left:3px;background:${_HITRATE_COLORS[color]}22;color:${_HITRATE_COLORS[color]};border:1px solid ${_HITRATE_COLORS[color]}55" title="${goalNum}球赔率${oddsVal}区间历史命中率">${rate}%</span>`;
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
                            ${m.g3_prediction.signals.map(s => `
                                <div class="g3-signal-item ${s[0].includes('黄金') ? 'signal-golden' : s[1].startsWith('+') ? 'signal-plus' : s[1].startsWith('-') ? 'signal-minus' : 'signal-neutral'}">
                                    <span class="g3-signal-tag">${s[0]}</span>
                                    <span class="g3-signal-score">${s[1]}</span>
                                    <span class="g3-signal-reason">${s[2]}</span>
                                </div>
                            `).join('')}
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
                        </div>
                        <div id="score-msg-${m.match_id}" class="score-msg"></div>
                        <div id="similar-panel-${m.match_id}" class="similar-panel" style="display:none"></div>
                    </div>
                    
                    <!-- 胜平负 -->
                    ${Object.keys(m.had || {}).filter(k => k !== '更新时间').length > 0 ? `
                    <div class="odds-section">
                        <div class="odds-title">胜平负</div>
                        <div class="odds-grid">
                            ${Object.entries(m.had || {}).filter(([k]) => k !== '更新时间').map(([k, v]) => 
                                `<div class="odds-item ${getOddsClass(v)}"><div class="label">${k}</div><div class="value">${v}</div></div>`
                            ).join('')}
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
                                const rateLabel = _getHitRateLabel(goalNum, parseFloat(v));
                                return `<div class="odds-item ${getOddsClass(v)}"><div class="label">${k}</div><div class="value">${v}${rateLabel}</div></div>`;
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

                    <!-- 进球数-比分联动排除列表 -->
                    ${m.exclusion_list && m.exclusion_list.length > 0 ? `
                    <div class="odds-section exclusion-section">
                        <div class="odds-title exclusion-title">
                            ⚡ 优先排除列表
                            <span class="exclusion-hint">赔率尾数含 .25 / .75 / .15 的进球数或比分</span>
                        </div>
                        <div class="exclusion-list">
                            ${m.exclusion_list.map(item => {
                                const levelCls = item.level === '强排除' ? 'excl-strong'
                                               : item.level === '普通排除' ? 'excl-normal'
                                               : 'excl-weak';
                                const levelIcon = item.level === '强排除' ? '🔴'
                                                : item.level === '普通排除' ? '🟠'
                                                : '🟡';
                                const specialScores = item.scores.filter(s => s.special);
                                const normalScores = item.scores.filter(s => !s.special);
                                return `<div class="excl-item ${levelCls}">
                                    <div class="excl-header">
                                        <span class="excl-level-badge">${levelIcon} ${item.level}</span>
                                        <span class="excl-goal ${item.ttg_special ? 'excl-goal-special' : ''}">${item.goal}</span>
                                        <span class="excl-ttg-odds">进球数赔率: ${item.ttg_odds}${item.ttg_special ? ' ★' : ''}</span>
                                    </div>
                                    <div class="excl-body">
                                        ${specialScores.length > 0 ? `
                                        <div class="excl-scores-row">
                                            <span class="excl-scores-label">★ 特殊尾数比分:</span>
                                            ${specialScores.map(s => `
                                                <span class="excl-score-badge special">${s.score} (${s.odds})</span>
                                            `).join('')}
                                        </div>` : ''}
                                        ${normalScores.length > 0 && item.level !== '仅比分排除' ? `
                                        <div class="excl-scores-row">
                                            <span class="excl-scores-label">普通比分:</span>
                                            ${normalScores.map(s => `
                                                <span class="excl-score-badge normal">${s.score} (${s.odds})</span>
                                            `).join('')}
                                        </div>` : ''}
                                        <div class="excl-reason">${item.reason}</div>
                                    </div>
                                </div>`;
                            }).join('')}
                        </div>
                    </div>
                    ` : ''}

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
            // 并行加载：精简比赛列表 + 已保存比分
            const [matchesRes, scoresRes] = await Promise.all([
                fetch('/api/matches?light=1'),
                fetch('/api/saved-scores')
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
            try {
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
            } catch(e) {}
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
                                return `<td style="padding:3px 6px;text-align:center;font-size:11px;${cls}">${g}球<br/><b>${val !== undefined ? val.toFixed(2) : '-'}</b>${rateLabel}</td>`;
                            }).join('');
                            html += `<div style="padding:4px 12px 4px 42px">
                                <table style="border-collapse:collapse;width:auto;background:#0a1628;border-radius:6px;" cellpadding="0">
                                    <tr style="color:#888;font-size:10px;text-align:center">${goalLabels.map(g => `<td style="padding:2px 6px;text-align:center">${g}球</td>`).join('')}</tr>
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
                            html += `<div style="padding:2px 12px 6px 42px;font-size:11px;color:#555">
                                <span style="color:#888">近况:</span> 主${rf.home_avg.toFixed(1)}/客${rf.away_avg.toFixed(1)}
                                <span style="color:#888">(${rf.home_games}/${rf.away_games}场)</span>
                                &nbsp;
                                <span style="color:${bonusColor};font-weight:bold">${bonus > 0 ? '+' : ''}${bonus}</span>
                                <span style="color:#888;font-size:10px">(${label})</span>
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
        ttg_change = data.get('ttg_change', {})
        hafu_change = data.get('hafu_change', {})
        exclusion_list = data.get('exclusion_list', [])

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
                    '区间': g3_pred.get('features', {}).get('区间'),
                },
                'hist_stats': g3_pred.get('hist_stats'),
            },
            # 让球：只保留数值
            'hhad': {
                '让球': hhad.get('让球'),
                '让胜': hhad.get('让胜'),
                '让平': hhad.get('让平'),
                '让负': hhad.get('让负'),
            } if hhad else {},
            # 变化数据：只保留数值
            'ttg_change': {k: v for k, v in ttg_change.items() if isinstance(v, (int, float))},
            'hafu_change': {k: v for k, v in hafu_change.items() if isinstance(v, (int, float))},
            'exclusion_list': exclusion_list,
        }
    else:
        # ── 完整版：返回全部字段 ──
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
                        data['g3_prediction'] = {
                            'recommendation': g3_pred.get('recommendation', '观望'),
                            'score': g3_pred.get('signal_score', 0),
                            'signals': g3_pred.get('signals', []),
                            'warnings': g3_pred.get('warnings', []),
                            'golden_3goals': g3_pred.get('golden_3goals', False),
                            'golden_reason': g3_pred.get('golden_reason', []),
                            'features': {
                                '3球': features.get('3球'),
                                '0球': features.get('0球'),
                                '1球': features.get('1球'),
                                '2球': features.get('2球'),
                                '区间': features.get('区间'),
                                '0球_整数高赔': features.get('0球_整数高赔'),
                                '3球_降赔': features.get('3球_降赔'),
                                '3球_升赔': features.get('3球_升赔'),
                            },
                            # 历史相似比赛统计
                            'hist_stats': g3_hist,
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
            result['g3_prediction'] = {
                                'recommendation': g3_pred.get('recommendation', '观望'),
                                'score': g3_pred.get('signal_score', 0),
                                'signals': g3_pred.get('signals', []),
                                'warnings': g3_pred.get('warnings', []),
                                'golden_3goals': g3_pred.get('golden_3goals', False),
                                'golden_reason': g3_pred.get('golden_reason', []),
                                'features': {
                                    '3球': features.get('3球'),
                    '0球': features.get('0球'),
                    '1球': features.get('1球'),
                    '2球': features.get('2球'),
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
