# -*- coding: utf-8 -*-
"""
3球预测算法 v3 - 竞彩网 preview.recent 近况 + 赔率信号
数据来源: sporttery_data/*.json

核心规律:
  - Step 0: 竞彩网 preview.recent（双方近3场均值偏离3球区间则减分）
  - 规律⑨: 3球赔率<3.50关注，>3.50降低预期
  - 规律⑩: 0球赔率整数(X.0)+高赔(>15) = 3球加分信号(历史92.9%)

使用方法:
    python predict_3goals.py                         # 预测最新场次
    python predict_3goals.py <file.json>             # 预测指定文件
    python predict_3goals.py --backtest              # 运行回测
    python predict_3goals.py --all                   # 预测+回测所有场次，生成HTML报告
"""

import glob, json, os, re, math
from typing import Optional, Dict, Any, List, Tuple

# ============================================================
# 第一部分: 通用赔率解析
# ============================================================

def parse_goals_odds(data: dict) -> dict:
    """
    兼容两种格式解析总进球赔率
    Format A (40个文件): ttg: {'3球': '3.30', '0球': '13.00', ...}
    Format B (6个新文件): total_goals: {'3+球': 3.45, '0球': 22.0, ...}
    """
    raw = data.get('ttg') or data.get('total_goals') or {}
    result = {}
    for key, val in raw.items():
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        if '3球' in key:
            result[3] = v
        elif key == '0球':
            result[0] = v
        elif key == '1球':
            result[1] = v
        elif key == '2球':
            result[2] = v
        elif key == '4球':
            result[4] = v
        elif key == '5球':
            result[5] = v
        elif key == '6球':
            result[6] = v
        elif key == '7球':
            result[7] = v
    return result


def parse_had(data: dict) -> dict:
    """解析胜平负赔率"""
    had = data.get('had', {})
    result = {}
    for k, v in had.items():
        if k == '更新时间': continue
        try:
            result[k] = float(v)
        except (TypeError, ValueError):
            pass
    return result


def parse_score_odds(data: dict) -> dict:
    """解析精确比分赔率，返回 {比分: 赔率}"""
    raw = data.get('score_odds', {})
    return {str(k): float(v) for k, v in raw.items()
            if not isinstance(v, dict)}


# ============================================================
# 第二部分: 近况数据提取（从 sporttery_data 的 preview.recent）
# ============================================================

def _extract_recent_matches(data: dict) -> dict:
    """
    从 sporttery_data 的 preview.recent 提取两队近况
    返回: {
        'home': [{'date', 'opponent', 'total', 'result'}, ...],
        'away': [{'date', 'opponent', 'total', 'result'}, ...],
    }
    使用 homeTeamFullCourtGoalCnt / awayTeamFullCourtGoalCnt 精确获取两队得分
    """
    preview = data.get('preview', {}) or {}
    recent = preview.get('recent', {}) or {}

    result = {'home': [], 'away': []}

    for side in ['home', 'away']:
        match_list = recent.get(side, {}).get('matchList', [])
        matches = []
        for m in match_list[:5]:
            hg = m.get('homeTeamFullCourtGoalCnt')
            ag = m.get('awayTeamFullCourtGoalCnt')
            if hg is None or ag is None:
                continue
            total = int(hg) + int(ag)

            # 判断该队在这场是主队还是客队
            team_short = m.get('teamShortName', '')  # 查询队伍的简称
            home_short = m.get('homeTeamShortName', '')
            away_short = m.get('awayTeamShortName', '')
            is_home = (home_short == team_short)

            opponent = away_short if is_home else home_short
            team_score = hg if is_home else ag
            opp_score = ag if is_home else hg

            matches.append({
                'date': m.get('matchDate', ''),
                'opponent': opponent or '',
                'score': f'{team_score}:{opp_score}',
                'half': m.get('halfTimeGoal', ''),
                'total': total,
                'result': m.get('teamMatchResult', ''),  # W/D/L
            })
        result[side] = matches

    return result


def calc_recent_form(recent_data: dict) -> Optional[dict]:
    """
    根据 preview.recent 数据计算两队近况均值
    recent_data: _extract_recent_matches() 的返回值
    返回: {
        'home_avg': float, 'away_avg': float,
        'combined_avg': float,
        'home_matches': [...], 'away_matches': [...],
        'home_games': int, 'away_games': int,
    }
    或 None（数据不足时）
    """
    home_list = recent_data.get('home', [])
    away_list = recent_data.get('away', [])

    # 至少各2场才计算
    if len(home_list) < 2 or len(away_list) < 2:
        return None

    h_totals = [m['total'] for m in home_list]
    a_totals = [m['total'] for m in away_list]

    h_avg = sum(h_totals) / len(h_totals)
    a_avg = sum(a_totals) / len(a_totals)
    combined = (h_avg + a_avg) / 2

    return {
        'home_avg': round(h_avg, 2),
        'away_avg': round(a_avg, 2),
        'combined_avg': round(combined, 2),
        'home_matches': home_list,
        'away_matches': away_list,
        'home_games': len(home_list),
        'away_games': len(away_list),
    }


# ============================================================
# 第三部分: 特征提取
# ============================================================

def extract_features(data: dict) -> Dict[str, Any]:
    """从 sporttery_data 条目提取预测特征"""
    odds = parse_goals_odds(data)
    had = parse_had(data)
    scores = parse_score_odds(data)

    f = {}
    f['3球'] = odds.get(3)
    f['2球'] = odds.get(2)
    f['1球'] = odds.get(1)
    f['0球'] = odds.get(0)
    f['4球'] = odds.get(4)

    g3, g0, g1, g2 = f['3球'], f['0球'], f['1球'], f['2球']

    # ── 规律⑨: 3球赔率区间 ──
    if g3 is not None:
        f['区间'] = ('A' if g3 < 2.50 else 'B' if g3 < 3.00
                     else 'C' if g3 < 3.50 else 'D' if g3 < 4.00 else 'E')
        f['关注3球'] = g3 < 3.50
        f['排除3球'] = g3 > 5.00
    else:
        f['区间'] = None; f['关注3球'] = False; f['排除3球'] = False

    # ── 规律⑩: 0球整数尾数 ──
    if g0 is not None:
        frac = round(g0 % 1, 2)
        f['0球_是整数'] = frac < 0.01
        f['0球_小数'] = frac
        f['0球_赔率高'] = g0 > 15
        f['0球_赔率中'] = 8 <= g0 <= 15
        f['0球_整数高赔'] = f['0球_是整数'] and f['0球_赔率高']
        f['0球_整数中赔'] = f['0球_是整数'] and f['0球_赔率中']
    else:
        for k in ['0球_是整数','0球_赔率高','0球_赔率中','0球_整数高赔','0球_整数中赔']:
            f[k] = False

    # ── 1球/2球整数 ──
    f['1球_是整数'] = (g1 is not None and round(g1 % 1, 2) < 0.01)
    f['2球_是整数'] = (g2 is not None and round(g2 % 1, 2) < 0.01)

    # ── 诱导比分 ──
    special = [(s, v) for s, v in scores.items()
               if v % 1 not in (0.0, 0.25, 0.50, 0.75)]
    f['诱导比分_数量'] = sum(1 for s, v in special if 8 <= v <= 20)
    f['特殊比分_列表'] = [(s, round(v, 2)) for s, v in special[:5]]

    # ── 赔率变化 ──
    changes = data.get('ttg_change', {})
    g3c = changes.get('3球', {})
    f['3球_变化'] = g3c.get('change_pct')
    f['3球_降赔'] = f['3球_变化'] is not None and f['3球_变化'] < -3
    f['3球_升赔'] = f['3球_变化'] is not None and f['3球_变化'] > 5

    # ── 胜平负 ──
    if had:
        vals = list(had.values())
        f['胜平负_最低'] = min(vals)
        f['胜平负_差值'] = max(vals) - min(vals)
    else:
        f['胜平负_最低'] = None; f['胜平负_差值'] = None

    # ── 比赛信息 ──
    mi = data.get('match_info', {})
    f['主队'] = mi.get('home_team', '')
    f['客队'] = mi.get('away_team', '')
    f['联赛'] = mi.get('league', '')
    f['赛事类型'] = _detect_league_type(f['联赛'])

    # ── Step 0.5: 近况评分（从 preview.recent 提取） ──
    recent = _extract_recent_matches(data)
    form = calc_recent_form(recent)
    f['近况'] = form

    return f


def _detect_league_type(league: str) -> str:
    league_lower = league.lower()
    if any(x in league_lower for x in ['友谊', '朋友', 'friendly']):
        return '友谊赛'
    if any(x in league_lower for x in ['附加', '季后赛', 'relegation']):
        return '附加赛'
    if any(x in league_lower for x in ['杯', '淘汰', '淘汰']):
        return '淘汰赛'
    return '联赛正赛'


# ============================================================
# 第三部分: 预测核心
# ============================================================

def predict_3goals(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    3球预测主函数

    评分逻辑:
      >= 15 分 → 关注3球
      <= -10 分 → 排除3球
      中间     → 观望
    """
    signals, warnings, reasons = [], [], []
    g3, g0, g1, g2 = (features.get(k) for k in ['3球','0球','1球','2球'])
    league_type = features.get('赛事类型', '联赛正赛')
    is_friendly = league_type == '友谊赛'

    # Step 0: 近况评分（双方近3场均值判断）
    form = features.get('近况')
    if form:
        combined = form['combined_avg']
        home_avg = form['home_avg']
        away_avg = form['away_avg']
        detail = f"主{home_avg}/客{away_avg}({form['home_games']}/{form['away_games']}场)"

        if combined < 2.0:
            penalty = -8; label = '近况过小'
        elif combined < 2.5:
            penalty = -3; label = '近况偏低'
        elif combined > 4.0:
            penalty = -8; label = '近况过大'
        elif combined > 3.5:
            penalty = -3; label = '近况偏高'
        else:
            penalty = +3; label = '近况正常'  # 2.5~3.5 = 符合3球特征，加分

        sign = '+' if penalty > 0 else ''
        signals.append((label, f'{sign}{penalty}', detail))
        if penalty > 0:
            reasons.append(f'近况均值{combined}，符合3球特征({label})')
        else:
            reasons.append(f'近况均值{combined}，偏离3球区间({label})')

    # Step 1: 3球赔率值（A/B/C/D/E级）
    if g3 is not None:
        if g3 < 2.50:
            signals.append(('3球A级', '+20', f'{g3}<2.50'));
            reasons.append(f'3球{g3}，A级，历史打出率最高')
        elif g3 < 3.00:
            signals.append(('3球B级', '+12', f'{g3} 2.50-3.00'));
            reasons.append(f'3球{g3}，B级关注')
        elif g3 < 3.50:
            signals.append(('3球C级', '+5', f'{g3} 3.00-3.50'));
            reasons.append(f'3球{g3}，C级可关注')
        elif g3 < 4.00:
            signals.append(('3球D级', '0', f'{g3} 3.50-4.00'));
            reasons.append(f'3球{g3}，D级中性')
        elif g3 < 5.00:
            signals.append(('3球E级', '-8', f'{g3} 4.00-5.00'));
            reasons.append(f'3球{g3}，E级降低预期')
        else:
            signals.append(('3球F级', '-20', f'{g3}>5.00'));
            warnings.append('排除3球');
            reasons.append(f'3球{g3}，排除')

    # Step 2: 0球整数尾数（规律10核心）
    if features.get('0球_整数高赔'):
        signals.append(('0球整数高赔', '+10', f'0球={g0}，X.0整数+高赔'));
        reasons.append(f'0球{g0}整数，历史3球打出率92.9%')
    elif features.get('0球_整数中赔'):
        signals.append(('0球整数中赔', '-5', f'0球={g0}，可能陷阱'));
        warnings.append('0球整数中赔，可能是诱导陷阱');
        reasons.append(f'0球{g0}整数+中赔，谨慎')

    # Step 3: 2球 vs 1球关系
    if g2 and g1 and g1 > 0:
        ratio = g2 / g1
        if ratio > 1.4:
            signals.append(('2球>1球×1.4', '-6', f'{g2}/{g1}={ratio:.2f}'));
            reasons.append(f'2球({g2})显著>1球({g1})，倾向小比分')
        elif ratio < 0.85:
            signals.append(('2球<1球×0.85', '+5', f'{g2}/{g1}={ratio:.2f}'));
            reasons.append(f'2球({g2})<1球({g1})，市场不排斥2球以上')

    # Step 3.5: 3球 vs 4球赔率梯度（筹码流向判断）
    g4 = features.get('4球')
    if g3 is not None and g4 is not None:
        gap = g4 - g3  # 正=4球更贵，负=4球更便宜
        gap_pct = gap / g3 * 100
        # 0球赔率极高时，额外惩罚更重（球多可能溢出到4球）
        g0 = features.get('0球')
        g0_extreme = g0 is not None and g0 > 30
        if gap < -0.1:  # 4球比3球便宜 → 筹码流向4球，3球减分
            base_penalty = min(12, max(5, int(abs(gap_pct) * 0.8)))
            if g0_extreme:
                penalty = min(15, base_penalty + 5)
                signals.append(('4球<3球', f'-{penalty}', f'3={g3} 4={g4} 0球={g0}'));
                reasons.append(f'4球({g4})<3球({g3})，0球{g0}极高，额外溢出风险')
            else:
                penalty = base_penalty
                signals.append(('4球<3球', f'-{penalty}', f'3={g3} 4={g4} 差{gap:.2f}'));
                reasons.append(f'4球({g4})<3球({g3})，筹码流向4球，抵消3球加分')
        elif gap > 0.1:  # 3球比4球便宜 → 3球有吸引力，加分
            bonus = min(8, max(2, int(gap_pct * 0.6)))
            signals.append(('3球<4球', f'+{bonus}', f'3={g3} 4={g4} 差+{gap:.2f}'));
            reasons.append(f'3球({g3})<4球({g4})，3球相对便宜，有吸引力')
        # 差距<=0.3 → 无信号

    # Step 4: 诱导比分
    if features.get('诱导比分_数量', 0) >= 3:
        signals.append(('多诱导比分', '+3', f'{features["诱导比分_数量"]}个'));
        reasons.append(f'{features["诱导比分_数量"]}个诱导比分，庄家在特定比分做文章，3球方向相对安全')

    # Step 5: 赔率变化
    if features.get('3球_降赔'):
        ch = features['3球_变化']
        signals.append(('3球降赔', '+8', f'降{ch}%'));
        reasons.append(f'3球降赔{ch}%，引导筹码流向')
    elif features.get('3球_升赔'):
        ch = features['3球_变化']
        signals.append(('3球升赔', '-8', f'升{ch}%'));
        warnings.append('3球升赔，庄家推离');
        reasons.append(f'3球升赔{ch}%，庄家不想出')

    # Step 6: 赛事类型
    if is_friendly:
        warnings.append('友谊赛：信号全面降级');
        reasons.append('友谊赛，选3球不可靠')

    # 综合评分
    def ps(s):
        s = s.strip()
        return (1 if s[0] == '+' else -1) * int(s[1:])
    score = max(-30, min(100, sum(ps(s[1]) for s in signals if s[1][0] in '+-')))
    if is_friendly: score = int(score * 0.5)

    # ── 黄金3球筛选器（4条定律同时满足） ──
    # 定律①: 评分达标（≥15）
    # 定律②: 近况正常（合并均值2.5~3.5）
    # 定律③: 3球C级（3.00~3.50）
    # 定律④: 2球>3球<4球（完美梯度）
    golden = False
    golden_reason = []
    g4_val = features.get('4球')
    cond1 = score >= 15                                             # ①评分达标
    cond2 = (form is not None and 2.5 <= form['combined_avg'] <= 3.5)  # ②近况正常
    cond3 = (g3 is not None and 3.00 <= g3 < 3.50)                # ③3球C级
    cond4 = (g2 is not None and g3 is not None and g4_val is not None
             and g2 > g3 and g3 < g4_val)                         # ④2球>3球<4球
    if cond1 and cond2 and cond3 and cond4:
        golden = True
        golden_reason = [
            f'①评分{score}≥15',
            f'②近况均值{form["combined_avg"]}在[2.5,3.5]',
            f'③3球{g3}(C级)',
            f'④梯度:2球{g2}>3球{g3}<4球{g4_val}',
        ]
        signals.append(('⭐黄金3球', '+0', ' | '.join(golden_reason)))
        # 4球预警：黄金3球 + 4球赔率在4.95~6之间
        if g4_val is not None and 4.95 <= g4_val <= 6.0:
            warnings.append(f'⚠️ 4球预警：4球赔率{g4_val}在4.95~6区间，需预防4球打出')

    # 推荐
    if score >= 15:
        rec, conf = '关注3球', min(85, 55 + score)
    elif score <= -10:
        rec, conf = '排除3球', min(80, 55 + abs(score))
    else:
        rec, conf = '观望', None

    return {
        'recommendation': rec,
        'confidence': conf,
        'signal_score': score,
        'signals': signals,
        'warnings': warnings,
        'reasoning': reasons,
        'features': features,
        'golden_3goals': golden,
        'golden_reason': golden_reason,
    }


# ============================================================
# 第四部分: 比分缓存（模板+scores关联）
# ============================================================

def _build_cache(scores_file='分析模板/_scores.json', template_dir='分析模板'):
    """建立 team_pair -> [(date, label, score)] 缓存"""
    import re as re2

    scores_raw = json.load(open(scores_file, encoding='utf-8'))

    def norm_date(d):
        if not d: return None
        d = d.strip()
        m = re2.match(r'(\d{4})[._-]?(\d{1,2})[._-]?(\d{1,2})', d)
        if m:
            return f'{m.group(1)}.{int(m.group(2)):02d}.{int(m.group(3)):02d}'
        m = re2.match(r'^(\d{1,2})\.(\d{1,2})$', d)
        if m:
            return f'2026.{int(m.group(1)):02d}.{int(m.group(2)):02d}'
        return None

    # date -> {label -> score}
    date_to_label = {}
    for sk, sv in scores_raw.items():
        if sk.startswith('_'): continue
        parts = sk.rsplit('_', 1)
        if len(parts) < 2: continue
        nd = norm_date(parts[0])
        if not nd: continue
        if nd not in date_to_label: date_to_label[nd] = {}
        date_to_label[nd][parts[1]] = sv

    # team_pair -> list
    template_files = glob.glob(os.path.join(template_dir, '**', '*_源数据.md'), recursive=True)
    pair_map = {}
    for tf in template_files:
        bn = os.path.basename(tf)
        parent = os.path.dirname(tf)
        m_dir = re2.search(r'(\d{4})[._-]?(\d{1,2})[._-]?(\d{1,2})', parent)
        if not m_dir: continue
        nd = f'{m_dir.group(1)}.{int(m_dir.group(2)):02d}.{int(m_dir.group(3)):02d}'
        m_lbl = re2.match(r'^([周日月一二三四五六七八九十零]+(?:0?\d+)?)_', bn)
        if not m_lbl: continue
        label = m_lbl.group(1)
        rest = bn[len(m_lbl.group(0)):].replace('_源数据.md', '')
        if 'vs' not in rest: continue
        sp = rest.split('vs', 1)
        home, away = sp[0].strip(), sp[1].strip()
        score = date_to_label.get(nd, {}).get(label)
        key = (home[:2], away[:2])
        if key not in pair_map: pair_map[key] = []
        pair_map[key].append((nd, label, score))

    return pair_map, norm_date


# ============================================================
# 第五部分: 回测 + HTML报告
# ============================================================

def backtest(scores_file='分析模板/_scores.json', template_dir='分析模板',
             data_dir='sporttery_data') -> Dict[str, Any]:
    """
    回测 sporttery_data 赔率 vs _scores.json 实际结果
    """
    import re as re2
    scores_raw = json.load(open(scores_file, encoding='utf-8'))
    files = sorted(glob.glob(os.path.join(data_dir, '*.json')))
    pair_map, norm_date = _build_cache(scores_file, template_dir)

    def get_score(fp):
        d = json.load(open(fp, encoding='utf-8'))
        mi = d.get('match_info', {})
        home, away = mi.get('home_team', ''), mi.get('away_team', '')
        fetch = norm_date(d.get('fetch_time', '')[:10])
        if not home or not fetch: return None
        for td, _, score in pair_map.get((home[:2], away[:2]), []):
            if td == fetch: return score
        for td, _, score in pair_map.get((home[:1], away[:1]), []):
            if td == fetch: return score
        return None

    def parse_goals(sv):
        if isinstance(sv, dict):
            return (sv.get('home_score', 0) + sv.get('away_score', 0)
                    if sv.get('home_score') is not None else None)
        if isinstance(sv, str):
            parts = re2.split(r'[:\-— ]', sv)
            try:
                return int(parts[0]) + int(parts[1]) if len(parts) >= 2 else None
            except: return None
        return None

    total = hit = 0
    g3_low_hit = g3_low_tot = g3_high_hit = g3_high_tot = 0
    g0sig_hit = g0sig_tot = 0
    rows = []

    for fp in files:
        try:
            pred = predict_file(fp)
        except: continue

        sv = get_score(fp)
        tg = parse_goals(sv) if sv else None
        features = pred.get('features', {})
        g3 = features.get('3球')
        rec = pred.get('recommendation', '')
        actual_3 = (tg == 3) if tg is not None else None
        pred_3 = rec == '关注3球'
        hit_ok = (pred_3 == actual_3) if actual_3 is not None else None

        if hit_ok is not None:
            if hit_ok: hit += 1
            total += 1

        g3_low = g3 is not None and g3 < 3.50
        g0int = features.get('0球_整数高赔', False)

        # 计数（与actual_3无关）
        if g3_low:
            g3_low_tot += 1
        else:
            g3_high_tot += 1

        if actual_3 is not None:
            if actual_3 and g3_low: g3_low_hit += 1
            if actual_3 and not g3_low: g3_high_hit += 1
            if g0int: g0sig_tot += 1
            if actual_3 and g0int: g0sig_hit += 1

        actual_str = (f'{sv}({tg}球)' if sv and tg is not None
                      else ('未匹配' if sv is None else str(sv)))
        rows.append({
            **pred, 'actual': actual_str,
            'actual_3': actual_3, 'is_hit': hit_ok,
        })

    print(f'\n===== 回测结果 =====')
    print(f'总计: {total}场 命中 {hit} 准确率 {hit/total*100:.1f}%' if total else '')
    print(f'3球赔率<3.50: {g3_low_hit}/{g3_low_tot}={g3_low_hit/g3_low_tot*100:.1f}%' if g3_low_tot else '无')
    print(f'3球赔率>=3.50: {g3_high_hit}/{g3_high_tot}={g3_high_hit/g3_high_tot*100:.1f}%' if g3_high_tot else '无')
    print(f'0球整数高赔: {g0sig_hit}/{g0sig_tot}={g0sig_hit/g0sig_tot*100:.1f}%' if g0sig_tot else '无')

    return {
        'total': total, 'hit': hit,
        'accuracy': hit/total*100 if total else 0,
        'g3_low': {'hit': g3_low_hit, 'total': g3_low_tot, 'rate': g3_low_hit/g3_low_tot*100 if g3_low_tot else 0},
        'g3_high': {'hit': g3_high_hit, 'total': g3_high_tot, 'rate': g3_high_hit/g3_high_tot*100 if g3_high_tot else 0},
        'g0sig': {'hit': g0sig_hit, 'total': g0sig_tot, 'rate': g0sig_hit/g0sig_tot*100 if g0sig_tot else 0},
        'rows': rows,
    }


def generate_html(rows: List[Dict], bt: Dict) -> str:
    """生成HTML报告"""
    def sig_color(s):
        if s[1].startswith('+'): return '#27ae60'
        if s[1].startswith('-'): return '#e74c3c'
        return '#888'

    total = bt.get('total', 0)
    hit = bt.get('hit', 0)
    acc = bt.get('accuracy', 0)

    html = f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>3球预测算法 v2</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:1300px;margin:0 auto;padding:20px;background:#fafafa}}
h1{{color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px}}
h2{{color:#34495e;margin-top:32px;border-left:4px solid #3498db;padding-left:10px}}
.stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin:16px 0}}
.card{{background:white;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
.card .num{{font-size:2em;font-weight:bold;color:#3498db}}
.card .num.green{{color:#27ae60}}.card .num.red{{color:#e74c3c}}.card .num.purple{{color:#9b59b6}}
.card .label{{color:#888;font-size:.9em;margin-top:4px}}
table{{width:100%;border-collapse:collapse;background:white;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
th{{background:#34495e;color:white;padding:12px;text-align:left;font-size:.85em}}
td{{padding:9px 12px;border-bottom:1px solid #eee;font-size:.85em}}
tr:hover{{background:#f8f9fa}}
.sig{{display:inline-block;margin:1px 3px;font-size:.7em;padding:2px 6px;border-radius:4px}}
.badge{{display:inline-block;padding:3px 10px;border-radius:20px;font-size:.8em;font-weight:bold}}
.bg-green{{background:#d4edda;color:#155724}}
.bg-red{{background:#f8d7da;color:#721c24}}
.bg-gray{{background:#e9ecef;color:#495057}}
.bg-yellow{{background:#fff3cd;color:#856404}}
</style>
</head>
<body>
<h1>3球预测算法 v2</h1>
<p style="color:#888">规律⑨(赔率值) + 规律⑩(0球整数尾数) | 共 {total} 场验证</p>

<h2>回测统计</h2>
<div class="stats-grid">
  <div class="card"><div class="num">{hit}/{total}</div><div class="label">总体准确率 ({acc:.1f}%)</div></div>
  <div class="card"><div class="num green">{bt['g3_low']['rate']:.1f}%</div><div class="label">3球赔率&lt;3.50 ({bt['g3_low']['total']}场)</div></div>
  <div class="card"><div class="num red">{bt['g3_high']['rate']:.1f}%</div><div class="label">3球赔率≥3.50 ({bt['g3_high']['total']}场)</div></div>
  <div class="card"><div class="num purple">{bt['g0sig']['rate']:.1f}%</div><div class="label">0球整数高赔信号 ({bt['g0sig']['total']}场)</div></div>
</div>

<h2>预测明细</h2>
<table>
<thead><tr>
  <th>比赛</th><th>联赛</th><th>3球</th><th>0球</th><th>评分</th><th>推荐</th><th>置信</th>
  <th>触发信号</th><th>实际比分</th><th>命中</th>
</tr></thead>
<tbody>
'''
    for r in rows:
        f = r.get('features', {})
        rec = r.get('recommendation', '观望')
        rec_cls = ('bg-green' if '关注' in rec
                   else 'bg-red' if '排除' in rec else 'bg-gray')
        hit_ok = r.get('is_hit')
        hit_disp = ('<b style="color:#27ae60">OK</b>' if hit_ok == True
                    else '<b style="color:#e74c3c">NO</b>' if hit_ok == False else '—')

        sigs_html = ''.join(
            f'<span class="sig" style="background:{sig_color(s)}22;color:{sig_color(s)}">{s[0]}({s[1]})</span>'
            for s in r.get('signals', [])[:4]
        )

        conf = f'{r.get("confidence")}%' if r.get('confidence') else '—'
        html += f'''<tr>
  <td>{r.get('主队','?')} vs {r.get('客队','?')}</td>
  <td style="color:#888;font-size:.8em">{r.get('联赛','')}</td>
  <td><b>{f.get('3球','')}</b></td>
  <td>{f.get('0球','')}{'<span style="color:#9b59b6">整数</span>' if f.get('0球_是整数') else ''}</td>
  <td><b>{r.get('signal_score','')}</b></td>
  <td><span class="badge {rec_cls}">{rec}</span></td>
  <td>{conf}</td>
  <td>{sigs_html}</td>
  <td style="font-size:.8em">{r.get('actual','—')}</td>
  <td>{hit_disp}</td>
</tr>'''

    html += '</tbody></table>'

    # 信号说明表
    html += '''
<h2>评分算法说明</h2>
<table>
<tr style="background:#34495e;color:white"><th style="padding:10px">信号</th><th style="padding:10px">分值</th><th style="padding:10px">说明</th></tr>
<tr><td style="padding:8px">3球 &lt; 2.50 (A级)</td><td style="color:#27ae60;font-weight:bold">+20</td><td style="padding:8px">历史打出率最高区间</td></tr>
<tr><td style="padding:8px">3球 2.50-3.00 (B级)</td><td style="color:#27ae60;font-weight:bold">+12</td><td style="padding:8px">关注</td></tr>
<tr><td style="padding:8px">3球 3.00-3.50 (C级)</td><td style="color:#27ae60;font-weight:bold">+5</td><td style="padding:8px">可关注</td></tr>
<tr><td style="padding:8px">3球 4.00-5.00 (E级)</td><td style="color:#e74c3c;font-weight:bold">-8</td><td style="padding:8px">降低预期</td></tr>
<tr><td style="padding:8px">3球 &gt; 5.00 (F级)</td><td style="color:#e74c3c;font-weight:bold">-20</td><td style="padding:8px">排除3球</td></tr>
<tr><td style="padding:8px">0球整数+赔率&gt;15</td><td style="color:#9b59b6;font-weight:bold">+10</td><td style="padding:8px">规律10核心：历史3球打出率92.9%</td></tr>
<tr><td style="padding:8px">0球整数+赔率8-15</td><td style="color:#e74c3c;font-weight:bold">-5</td><td style="padding:8px">可能是庄家诱导陷阱</td></tr>
<tr><td style="padding:8px">2球显著高于1球(&gt;1.4x)</td><td style="color:#e74c3c;font-weight:bold">-6</td><td style="padding:8px">市场倾向小比分</td></tr>
<tr><td style="padding:8px">3球降赔(&lt;-3%)</td><td style="color:#27ae60;font-weight:bold">+8</td><td style="padding:8px">引导筹码流向</td></tr>
<tr><td style="padding:8px">3球升赔(&gt;5%)</td><td style="color:#e74c3c;font-weight:bold">-8</td><td style="padding:8px">庄家推离</td></tr>
<tr><td style="padding:8px">友谊赛</td><td style="color:#f39c12;font-weight:bold">×0.5</td><td style="padding:8px">所有分数减半，观望为主</td></tr>
<tr><td style="padding:8px">Step0: 近况均值&lt;2.0</td><td style="color:#e74c3c;font-weight:bold">-8</td><td style="padding:8px">双方近3场均值过小，偏离3球</td></tr>
<tr><td style="padding:8px">Step0: 近况均值2.0~2.5</td><td style="color:#e74c3c;font-weight:bold">-3</td><td style="padding:8px">近况偏低，不支持3球</td></tr>
<tr><td style="padding:8px">Step0: 近况均值3.5~4.0</td><td style="color:#e74c3c;font-weight:bold">-3</td><td style="padding:8px">近况偏高，大开大合，3球不稳</td></tr>
<tr><td style="padding:8px">Step0: 近况均值&gt;4.0</td><td style="color:#e74c3c;font-weight:bold">-8</td><td style="padding:8px">双方近况过大，小比分概率高</td></tr>
<tr><td style="padding:8px">Step0: 近况均值2.5~3.5</td><td style="color:#27ae60;font-weight:bold">+3</td><td style="padding:8px">符合3球特征，加分（均值≈3说明该队近期总进球接近3球/场）</td></tr>
</table>
<tr style="background:#2d1f00">
  <td style="padding:8px;color:#f1c40f;font-weight:bold">⭐黄金3球</td>
  <td style="color:#f1c40f;font-weight:bold">标记</td>
  <td style="padding:8px;color:#f1c40f">
    同时满足4条定律：①评分≥15 ②近况均值2.5~3.5 ③3球C级(3.00~3.50) ④2球&gt;3球&lt;4球梯度
  </td>
</tr>
<tr style="background:#3d2000">
  <td style="padding:8px;color:#e67e22;font-weight:bold">⚠️4球预警</td>
  <td style="color:#e67e22;font-weight:bold">提醒</td>
  <td style="padding:8px;color:#e67e22">
    黄金3球+4球赔率在4.95~6区间时，需预防4球打出（4球赔率适中，有一定打出概率）
  </td>
</tr>
</table>
<p style="color:#888;font-size:.85em;margin-top:8px">
  数据来源: preview.recent（竞彩网，每场比赛自带主客队近5场历史）
</p>
<p style="color:#666;margin-top:16px;font-size:.85em">
  评分 ≥ 15 → 关注3球 | 评分 ≤ -10 → 排除3球 | 中间 → 观望
</p>
</body></html>'''
    return html


# ============================================================
# 入口
# ============================================================

def predict_file(filepath: str) -> Dict[str, Any]:
    """对单个文件预测"""
    data = json.load(open(filepath, encoding='utf-8'))
    features = extract_features(data)
    prediction = predict_3goals(features)
    mi = data.get('match_info', {})
    for k, v in [('主队', 'home_team'), ('客队', 'away_team'), ('联赛', 'league')]:
        prediction[k] = mi.get(v, '')
    prediction['match_id'] = data.get('match_id', os.path.basename(filepath).replace('.json',''))
    prediction['file'] = os.path.basename(filepath)
    prediction['features'] = features  # ← 关键！backtest 需要取 g3 值
    return prediction


def run_all_predictions(data_dir='sporttery_data') -> List[Dict]:
    files = sorted(glob.glob(os.path.join(data_dir, '*.json')))
    return [predict_file(fp) for fp in files if os.path.exists(fp)]


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--backtest':
        bt = backtest()
        html = generate_html([], bt)
        with open('3球预测_回测报告.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print('报告: 3球预测_回测报告.html')
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        rows = run_all_predictions()
        bt = backtest()
        html = generate_html(rows, bt)
        with open('3球预测_全部场次.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'报告: 3球预测_全部场次.html ({len(rows)}场)')
        sys.exit(0)

    # 单场预测
    fp = sys.argv[1] if len(sys.argv) > 1 else None
    if not fp:
        files = sorted(glob.glob('sporttery_data/*.json'))
        fp = files[-1] if files else None

    if not fp or not os.path.exists(fp):
        print('用法:')
        print('  python predict_3goals.py                  # 预测最新场次')
        print('  python predict_3goals.py <file.json>     # 预测指定文件')
        print('  python predict_3goals.py --backtest     # 回测')
        print('  python predict_3goals.py --all            # 预测全部+回测+HTML')
        sys.exit(1)

    pred = predict_file(fp)
    f = pred.get('features', {})
    print(f'\n===== 3球预测 =====')
    print(f'比赛: {pred["主队"]} vs {pred["客队"]}')
    print(f'联赛: {pred["联赛"]}')
    print(f'3球: {f.get("3球")} | 0球: {f.get("0球")}{" (整数)" if f.get("0球_是整数") else ""}')
    print(f'推荐: {pred["recommendation"]}' + (f' (置信{pred["confidence"]}%)' if pred.get('confidence') else ''))
    print(f'评分: {pred["signal_score"]}分')
    print('触发信号:')
    for s in pred.get('signals', []):
        print(f'  {s[0]}: {s[1]} — {s[2]}')
    if pred.get('warnings'):
        print('警告:', ' '.join(pred['warnings']))
    print('理由:')
    for r in pred.get('reasoning', []):
        print(f'  * {r}')
