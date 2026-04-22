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
    f['5球'] = odds.get(5)
    f['6球'] = odds.get(6)
    f['7球'] = odds.get(7)

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

    # Step 0.5: 近况均衡度分析（2026-04-21 新规律）
    # 基于261场回测数据
    if form and form.get('home_avg') is not None and form.get('away_avg') is not None:
        home_avg = form['home_avg']
        away_avg = form['away_avg']
        diff = abs(home_avg - away_avg)

        # 规律1: 主强客弱 → 4+球概率高(39.1%)，降低3球预期
        if home_avg >= 3.5 and away_avg <= 2.0:
            signals.append(('主强客弱', '-3', f'主{home_avg}≥3.5且客{away_avg}≤2.0'));
            warnings.append(f'主强客弱({home_avg}/{away_avg})，4+球概率高');
            reasons.append(f'主强客弱，4+球概率39.1%，降低3球预期')

        # 规律2: 均衡偏弱 → 0-2球概率高，3球偏低(18.2%)
        elif diff < 0.5 and combined < 2.5:
            signals.append(('均衡偏弱', '-2', f'差{diff:.1f}<0.5且均{combined}<2.5'));
            warnings.append(f'均衡偏弱，双方偏弱倾向小比分');
            reasons.append(f'均衡偏弱，3球率18.2%，偏小比分')

        # 规律3: 客强主弱 → 4+球概率高
        elif away_avg >= 3.5 and home_avg <= 2.0:
            signals.append(('客强主弱', '-3', f'客{away_avg}≥3.5且主{home_avg}≤2.0'));
            warnings.append(f'客强主弱({away_avg}/{home_avg})，4+球概率高');
            reasons.append(f'客强主弱，4+球概率高，降低3球预期')

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

    # ══════════════════════════════════════════════════════════════
    # Step 7: 三条件排除3球（完整版）
    # 条件：近况正常(2.5~3.5) + 0球>13 + 初始3球>3.50
    # 排除情况：
    #   ① 初始>3.50 → 当前>3.50（升赔推离）
    #   ② 初始>3.50 → 当前<3.50（降赔诱导到黄金区间）
    # 不排除：初始<3.50（真正的黄金3球信号）
    # 原理：初始在3.50以上说明庄家从一开始就不想要3球
    # ══════════════════════════════════════════════════════════════
    if form is not None:
        combined_avg = form.get('combined_avg', 0)
        g0 = features.get('0球')
        g3_val = features.get('3球')
        g3_change = features.get('3球_变化', 0)
        
        # 计算初始3球赔率
        initial_g3 = g3_val
        if g3_val is not None and g3_change is not None and g3_change != 0:
            initial_g3 = g3_val / (1 + g3_change / 100)
        
        if (2.5 <= combined_avg <= 3.5 and 
            g0 is not None and g0 > 13 and
            initial_g3 is not None and initial_g3 > 3.50):
            
            # 初始3球>3.50，需要排除
            if g3_val > 3.50:
                # 升赔推离
                signals.append(('排除3球', '-15', f'初始3球{initial_g3:.2f}>3.50→当前升至{g3_val}↑+0球{g0}>13'));
                warnings.append(f'🚫 排除3球！初始{initial_g3:.2f}>3.50，当前升至{g3_val}（升赔推离）');
                reasons.append(f'排除3球：初始3球{initial_g3:.2f}>3.50，庄家不想要3球')
            else:
                # 降赔诱导到黄金区间
                signals.append(('排除3球', '-15', f'初始3球{initial_g3:.2f}>3.50→当前降至{g3_val}↓+0球{g0}>13'));
                warnings.append(f'🚫 排除3球！初始{initial_g3:.2f}>3.50，被降赔到{g3_val}（诱导降赔）');
                reasons.append(f'排除3球：初始3球{initial_g3:.2f}>3.50，被降赔诱导到{g3_val}，是诱导降赔陷阱')

    # ══════════════════════════════════════════════════════════════
    # Step 7.5: 近况正常 + 0球<10 + 3球<3.7 → 排除3球（历史3球率9.1%）
    # 原理：0球<10说明市场认为0球概率不低，但3球赔率也不高 → 庄家在两边都不想要3球
    # ══════════════════════════════════════════════════════════════
    if form is not None:
        combined_avg = form.get('combined_avg', 0)
        g0 = features.get('0球')
        g3_val = features.get('3球')
        
        if (2.5 <= combined_avg <= 3.5 and 
            g0 is not None and g0 < 10 and
            g3_val is not None and g3_val < 3.7):
            signals.append(('排除3球', '-15', f'近况正常+0球{g0}<10+3球{g3_val}<3.7，历史3球率9.1%'));
            warnings.append(f'🚫 排除3球！近况正常+0球{g0}<10+3球{g3_val}<3.7，历史3球率9.1%');
            reasons.append(f'排除3球：近况正常+0球{g0}<10+3球{g3_val}<3.7，历史3球率9.1%')

    # ══════════════════════════════════════════════════════════════
    # Step 8: 排除2球（新增）
    # 条件: 近况2.0~2.5 + 0球13~18 + 2球3.5~4.0
    # 历史准确率: 87.5%
    # ══════════════════════════════════════════════════════════════
    if form is not None:
        combined_avg = form.get('combined_avg', 0)
        g0 = features.get('0球')
        g2 = features.get('2球')
        g2_ch = features.get('2球变化')
        g4 = features.get('4球')
        g4_ch = features.get('4球变化')
        
        # 规则A: 近况2.0~2.5 + 0球13~18 + 2球3.5~4.0
        if (2.0 <= combined_avg < 2.5 and 
            g0 is not None and 13 <= g0 < 18 and
            g2 is not None and 3.5 <= g2 < 4.0):
            signals.append(('🚫排除2球', '-10', f'近况{combined_avg:.1f}+0球{g0:.0f}+2球{g2}，历史87.5%准确率'));
            warnings.append(f'🚫 排除2球！近况{combined_avg:.1f}+0球{g0:.0f}+2球{g2}，历史87.5%准确率');
            reasons.append(f'排除2球：近况{combined_avg:.1f}+0球{g0:.0f}+2球{g2}，历史87.5%准确率')
        
        # 规则B: 近况<2.5 + 0球<10 + 初始2球<3.3 + 初始4球>=6.5 → 排除2球
        if g0 is not None and g0 < 10 and g2 is not None and g4 is not None:
            # 计算初始2球和初始4球
            g2_ini = g2 / (1 + g2_ch / 100) if g2_ch else g2
            g4_ini = g4 / (1 + g4_ch / 100) if g4_ch else g4
            
            if (combined_avg < 2.5 and 
                g2_ini < 3.3 and 
                g4_ini >= 6.5):
                signals.append(('🚫排除2球', '-10', f'黄金2球+初始4球{g4_ini:.1f}≥6.5，近况{combined_avg:.1f}+0球{g0:.0f}+初始2球{g2_ini:.2f}，历史75%准确率'));
                warnings.append(f'🚫 排除2球！黄金2球+初始4球{g4_ini:.1f}≥6.5，历史75%准确率');
                reasons.append(f'排除2球：黄金2球+初始4球{g4_ini:.1f}≥6.5，历史75%准确率')

    # 综合评分
    def ps(s):
        s = s.strip()
        return (1 if s[0] == '+' else -1) * int(s[1:])
    score = max(-30, min(100, sum(ps(s[1]) for s in signals if s[1][0] in '+-')))
    if is_friendly: score = int(score * 0.5)

    # 三条件排除信号特殊处理：直接覆盖推荐为排除3球（不管最终分数）
    has_exclude_signal = any('排除3球' in str(s[0]) for s in signals)
    if has_exclude_signal:
        score = -15  # 确保分数为负，用于置信度显示

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
    super_golden = False    # 超级3球：黄金3球 + 0球=13
    super_golden_reason = []

    if cond1 and cond2 and cond3 and cond4:
        golden = True
        golden_reason = [
            f'①评分{score}≥15',
            f'②近况均值{form["combined_avg"]}在[2.5,3.5]',
            f'③3球{g3}(C级)',
            f'④梯度:2球{g2}>3球{g3}<4球{g4_val}',
        ]
        signals.append(('⭐黄金3球', '+0', ' | '.join(golden_reason)))

        # 超级3球检测：黄金3球 + 0球=13（历史75%命中率）
        g0 = features.get('0球')
        if g0 is not None and g0 == 13:
            super_golden = True
            super_golden_reason = [
                f'黄金3球 ✓',
                f'0球=13 ✓ ({g0})',
            ]
            # 进一步判断3球是否在3.25-3.5（历史83.3%命中率）
            if g3 is not None and 3.25 <= g3 <= 3.5:
                super_golden_reason.append(f'3球{g3}在3.25-3.5 ✓ (83.3%命中)')
            signals.append(('🌟超级3球', '+5', ' | '.join(super_golden_reason)))
            warnings.append('🌟超级3球信号！历史75%命中率')

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
        'super_golden': super_golden,              # 超级3球：黄金3球+0球=13
        'super_golden_reason': super_golden_reason,
    }


# ============================================================
# 第三部分: 双选推荐系统（近况 × 0球赔率 × 3球等级）
# ============================================================

# ============================================================
# 历史赔率命中率统计（基于 _scores.json 回测）
# ============================================================

# 每个进球数的整体命中率
ODDS_OVERALL_STATS = {
    0: (6.3, 221),  # 命中率14/221
    1: (14.5, 221),  # 命中率32/221
    2: (22.6, 221),  # 命中率50/221
    3: (26.4, 216),  # 命中率57/216
    4: (16.7, 216),  # 命中率36/216
    5: (8.8, 216),   # 命中率19/216
    6: (2.8, 216),   # 命中率6/216
    7: (1.9, 215),   # 命中率4/215
}

# 赔率区间统计（用于精确匹配）
# 格式: (进球数, 赔率区间) -> (命中率%, 样本数)
ODDS_BIN_STATS = {
    # 1球高命中率区间
    (1, 3.6): (100.0, 3),
    (1, 3.65): (33.3, 3),
    (1, 3.75): (50.0, 6),
    (1, 4.2): (33.3, 6),
    (1, 4.25): (33.3, 3),
    (1, 4.3): (20.0, 5),
    (1, 4.7): (33.3, 3),
    (1, 5.0): (30.0, 10),
    (1, 5.25): (37.5, 8),
    (1, 5.75): (33.3, 3),
    (1, 6.0): (28.6, 7),
    (1, 6.5): (33.3, 3),
    (1, 8.0): (33.3, 3),
    (1, 8.5): (33.3, 3),
    # 2球高命中率区间
    (2, 3.0): (33.3, 3),
    (2, 3.05): (50.0, 6),
    (2, 3.1): (23.1, 13),
    (2, 3.15): (26.3, 19),
    (2, 3.2): (40.0, 5),
    (2, 3.25): (22.2, 9),
    (2, 3.35): (36.4, 11),
    (2, 3.4): (23.1, 13),
    (2, 3.45): (28.6, 7),
    (2, 3.75): (50.0, 4),
    (2, 3.8): (40.0, 5),
    (2, 4.0): (50.0, 6),
    (2, 4.1): (50.0, 4),
    (2, 4.25): (33.3, 3),
    (2, 4.3): (62.5, 8),
    (2, 4.5): (20.0, 5),
    (2, 5.0): (50.0, 4),
    # 3球高命中率区间
    (3, 3.25): (44.4, 9),
    (3, 3.3): (30.0, 10),
    (3, 3.35): (25.0, 12),
    (3, 3.4): (40.0, 20),
    (3, 3.45): (39.1, 23),
    (3, 3.55): (23.1, 26),
    (3, 3.6): (28.6, 21),
    (3, 3.65): (20.0, 10),
    (3, 3.7): (27.3, 11),
    (3, 3.75): (33.3, 6),
    (3, 3.8): (28.6, 7),
    (3, 3.85): (25.0, 8),
    (3, 4.1): (33.3, 3),
    # 4球高命中率区间
    (4, 4.0): (25.0, 4),
    (4, 4.15): (25.0, 8),
    (4, 4.2): (36.4, 11),
    (4, 4.3): (25.0, 4),
    (4, 4.75): (33.3, 3),
    (4, 5.1): (50.0, 4),
    (4, 5.2): (25.0, 8),
    (4, 5.4): (50.0, 4),
    (4, 5.7): (40.0, 5),
    (4, 5.9): (33.3, 3),
    (4, 6.0): (23.1, 13),
    (4, 6.15): (33.3, 3),
    # 5球高命中率区间
    (5, 6.0): (25.0, 4),
    (5, 6.25): (20.0, 5),
    (5, 6.8): (75.0, 4),
    (5, 7.0): (28.6, 7),
    (5, 7.75): (75.0, 4),
    (5, 9.25): (25.0, 4),
}

# 命中率阈值：低于此值的赔率会被排除
ODDS_HIT_RATE_THRESHOLD = 20.0  # 20%

def get_odds_hit_rate(goals, odds):
    """
    获取某个赔率的历史命中率

    参数:
        goals: 进球数 (0-7)
        odds: 赔率值

    返回:
        (命中率%, 样本数) 或 None
    """
    # 尝试精确匹配
    bin_key = round(odds * 20) / 20  # 四舍五入到0.05
    key = (goals, bin_key)
    if key in ODDS_BIN_STATS:
        return ODDS_BIN_STATS[key]

    # 回退到整体统计
    if goals in ODDS_OVERALL_STATS:
        return ODDS_OVERALL_STATS[goals]
    return None


# ============================================================
# 双选命中率统计数据（基于214场回测结果）
# ============================================================

DOUBLE_PICK_STATS = {
    # (近况分类, 0球分类, 3球等级) -> (第二选项, 命中率, 样本数)
    ('高进攻', '高', 'C级'): ('2球', 85.7, 7),
    ('中进攻', '中', 'C级'): ('4球', 71.4, 21),
    ('高进攻', '中', 'C级'): ('4球', 60.0, 5),
    ('弱进攻', '高', 'D级'): ('1球', 60.0, 5),
    ('中进攻', '高', 'C级'): ('2球', 60.0, 20),
    ('弱进攻', '中', 'C级'): ('1球', 55.6, 9),
    ('高进攻', '高', 'D级'): ('4球', 53.8, 13),
    ('中进攻', '低', 'D级'): ('4球', 50.0, 30),
    ('弱进攻', '中', 'D级'): ('4球', 37.5, 8),
    ('中进攻', '中', 'D级'): ('4球', 31.2, 16),
    ('弱进攻', '低', 'D级'): ('4球', 25.8, 31),
    ('中进攻', '高', 'D级'): ('4球', 25.0, 16),
    ('弱进攻', '高', 'C级'): ('1球', 14.3, 7),
    ('高进攻', '中', 'D级'): ('4球', 0.0, 4),
}

def classify_near_form(avg):
    """近况分类"""
    if avg is None:
        return None
    if avg < 2.5:
        return '弱进攻'
    elif avg < 3.5:
        return '中进攻'
    else:
        return '高进攻'

def classify_zero_odds(odds):
    """0球赔率分类"""
    if odds is None:
        return None
    if odds < 12:
        return '低'
    elif odds < 16:
        return '中'
    else:
        return '高'

def classify_three_odds(odds):
    """3球赔率等级"""
    if odds is None:
        return None
    if odds < 2.5:
        return 'A级'
    elif odds < 3.0:
        return 'B级'
    elif odds < 3.5:
        return 'C级'
    elif odds < 4.0:
        return 'D级'
    else:
        return 'E级'

def recommend_double_pick(features):
    """
    双选推荐函数

    【新规律】基于221场回测的高命中率规律（2026-04-21）:
    - 规律A: 1+2组合 + 最低赔率<3.5 + 近况<2.5 -> 100% (6场)
    - 规律B: 近况<2.0 + 2+3组合 -> 81.8% (11场)
    - 规律C: 1+2组合 + 最低赔率<3.5 -> 76.5% (17场)

    【历史赔率命中率过滤】(2026-04-21 新增):
    - 检查最低赔率的历史命中率
    - 如果命中率<20%，排除该选项，选择下一个

    【旧规律】基于「近况 × 0球赔率 × 3球等级」查表

    返回: {
        'recommendation': '3+2球' / '1+2球' / '2+3球' / '单选3球' / None,
        'second_pick': '2球' / '1球' / '4球' / None,
        'confidence': 0-100,  # 信心指数
        'hit_rate': 实际历史命中率,
        'sample_size': 样本数,
        'reason': 理由,
        'signal': 信号描述,
    }
    """
    result = {
        'recommendation': None,
        'second_pick': None,
        'confidence': None,
        'hit_rate': None,
        'sample_size': None,
        'reason': None,
        'signal': None,
    }

    # === 新规律：基于赔率最低的两个进球数 ===
    g1 = features.get('1球')
    g2 = features.get('2球')
    g3 = features.get('3球')
    g4 = features.get('4球')
    form = features.get('近况')

    if form is None:
        return _recommend_double_pick_legacy(features)

    combined_avg = form.get('combined_avg')
    if combined_avg is None:
        return _recommend_double_pick_legacy(features)

    # 收集所有赔率
    all_odds = []
    for g in range(8):
        od = features.get(f'{g}球')
        if od is not None and od > 0:
            all_odds.append((g, od))

    if len(all_odds) < 2:
        return _recommend_double_pick_legacy(features)

    # 排序找最低赔率两个
    all_odds.sort(key=lambda x: x[1])
    min1_g, min1_od = all_odds[0]
    min2_g, min2_od = all_odds[1]
    min_odds = min1_od
    odds_ratio = min2_od / min1_od if min1_od > 0 else 0

    # === 新规律A: 1+2组合 + 最低赔率<3.5 + 近况<2.5 ===
    if min1_g == 1 and min2_g == 2 and min_odds < 3.5 and combined_avg < 2.5:
        result['recommendation'] = '1+2球'
        result['second_pick'] = '2球'
        result['hit_rate'] = 100
        result['sample_size'] = 6
        result['confidence'] = 95
        result['reason'] = '规律A: 1+2组合+低价赔+近况弱，100%命中率'
        result['signal'] = '新规律A'
        return result

    # === 新规律B: 近况<2.0 + 2+3组合 ===
    if min1_g == 2 and min2_g == 3 and combined_avg < 2.0:
        result['recommendation'] = '2+3球'
        result['second_pick'] = '3球'
        result['hit_rate'] = 81.8
        result['sample_size'] = 11
        result['confidence'] = 90
        result['reason'] = '规律B: 近况<2.0+2+3组合，81.8%命中率'
        result['signal'] = '新规律B'
        return result

    # === 新规律C: 1+2组合 + 最低赔率<3.5 + 赔率接近 ===
    if min1_g == 1 and min2_g == 2 and min_odds < 3.5:
        if odds_ratio <= 1.3:
            result['recommendation'] = '1+2球'
            result['second_pick'] = '2球'
            result['hit_rate'] = 76.5
            result['sample_size'] = 17
            result['confidence'] = 85
            result['reason'] = '规律C: 1+2组合+低价赔+赔率接近，76.5%命中率'
            result['signal'] = '新规律C'
            return result
        elif odds_ratio > 1.3:
            # 赔率差距大，谨慎
            result['recommendation'] = '1+2球'
            result['second_pick'] = '2球'
            result['hit_rate'] = 25
            result['sample_size'] = 4
            result['confidence'] = 30
            result['reason'] = '1+2组合+低价但赔率差距大，谨慎！'
            result['signal'] = '新规律C(危险)'
            return result

    # === 新规律D: 1+2组合全局 ===
    if min1_g == 1 and min2_g == 2:
        result['recommendation'] = '1+2球'
        result['second_pick'] = '2球'
        result['hit_rate'] = 68.2
        result['sample_size'] = 22
        result['confidence'] = 70
        result['reason'] = '规律D: 1+2组合全局，68.2%命中率'
        result['signal'] = '新规律D'
        return result

    # === 新规律E: 近况弱时的2+3组合 ===
    if min1_g == 2 and min2_g == 3 and combined_avg < 2.5:
        result['recommendation'] = '2+3球'
        result['second_pick'] = '3球'
        result['hit_rate'] = 50
        result['sample_size'] = 20
        result['confidence'] = 55
        result['reason'] = '近况弱+2+3组合'
        result['signal'] = '新规律E'
        return result

    # === 历史赔率命中率过滤（新增，2026-04-21）===
    # 检查最低赔率的历史命中率
    min1_hit = get_odds_hit_rate(min1_g, min1_od)
    min2_hit = get_odds_hit_rate(min2_g, min2_od)

    # 如果最低赔率命中率太低，检查是否需要换选项
    if min1_hit is not None:
        min1_hit_rate = min1_hit[0]
        min1_sample = min1_hit[1]

        # 如果最低赔率命中率<20%且有足够样本(>=3)
        if min1_hit_rate < ODDS_HIT_RATE_THRESHOLD and min1_sample >= 3:
            # 尝试使用下一个赔率
            if len(all_odds) >= 3:
                next_g, next_od = all_odds[2]
                next_hit = get_odds_hit_rate(next_g, next_od)

                if next_hit is not None:
                    next_hit_rate = next_hit[0]

                    # 如果第二个赔率命中率更高，选择第二个
                    if next_hit_rate >= min1_hit_rate + 10:  # 至少高10%才换
                        min2_g, min2_od = next_g, next_od
                        min2_hit = next_hit

    # === 使用过滤后的选项生成推荐 ===
    # 构建推荐理由
    if min1_hit is not None and min1_sample >= 3:
        min1_info = f'{min1_g}球={min1_od}(历史{min1_hit_rate:.0f}%)'
    else:
        min1_info = f'{min1_g}球={min1_od}'

    if min2_hit is not None and min2_hit[1] >= 3:
        min2_info = f'{min2_g}球={min2_od}(历史{min2_hit[0]:.0f}%)'
    else:
        min2_info = f'{min2_g}球={min2_od}'

    # 检查是否满足新规律E的条件（但上面没有返回）
    if min1_g == 2 and min2_g == 3:
        # 2+3组合但不满足新规律B/E的近况条件
        avg_hit = (min1_hit[0] + min2_hit[0]) / 2 if min1_hit and min2_hit else 50
        result['recommendation'] = '2+3球'
        result['second_pick'] = '3球'
        result['hit_rate'] = min(avg_hit, 60)
        result['sample_size'] = 0  # 无特定样本
        result['confidence'] = int(min(60, avg_hit * 0.8))
        result['reason'] = f'2+3组合，{min1_info} + {min2_info}'
        result['signal'] = f'2+3组合(赔率过滤)'
        return result

    # 默认：使用赔率最低的两个
    result['recommendation'] = f'{min1_g}+{min2_g}球'
    result['second_pick'] = f'{min2_g}球'
    avg_hit = (min1_hit[0] + min2_hit[0]) / 2 if min1_hit and min2_hit else 50
    result['hit_rate'] = min(avg_hit, 65)
    result['sample_size'] = 0
    result['confidence'] = int(min(65, avg_hit * 0.9))
    result['reason'] = f'赔率最低两个，{min1_info} + {min2_info}'
    result['signal'] = f'赔率组合({min1_g}+{min2_g})'
    return result


def _recommend_double_pick_legacy(features):
    """
    旧版双选推荐：基于「近况 × 0球赔率 × 3球等级」查表
    """
    result = {
        'recommendation': None,
        'second_pick': None,
        'confidence': None,
        'hit_rate': None,
        'sample_size': None,
        'reason': None,
        'signal': None,
    }
    
    g3 = features.get('3球')
    g0 = features.get('0球')
    form = features.get('近况')
    
    if g3 is None or g0 is None or form is None:
        return result
    
    combined_avg = form.get('combined_avg')
    near_key = classify_near_form(combined_avg)
    zero_key = classify_zero_odds(g0)
    three_key = classify_three_odds(g3)
    
    if near_key is None or zero_key is None or three_key is None:
        return result
    
    # 查表获取命中率
    key = (near_key, zero_key, three_key)
    if key in DOUBLE_PICK_STATS:
        second_pick, hit_rate, sample = DOUBLE_PICK_STATS[key]
        
        result['second_pick'] = second_pick
        result['hit_rate'] = hit_rate
        result['sample_size'] = sample
        
        # 信心指数计算
        sample_weight = min(1.0, max(0.5, sample / 20))
        base_confidence = hit_rate * 0.7
        sample_bonus = (hit_rate - 45) * 0.3 if hit_rate > 45 else 0
        result['confidence'] = min(95, max(25, int((base_confidence + sample_bonus) * sample_weight)))
        
        # 推荐选项
        if three_key in ['A级', 'B级']:
            result['recommendation'] = '单选3球'
            result['signal'] = f'3球{three_key}赔率极低，无需双选'
            result['reason'] = f'3球{g3}({three_key})，庄家明显支持'
        else:
            result['recommendation'] = f'3+{second_pick}'
            result['signal'] = f'{near_key} + 0球{zero_key} + 3球{three_key}'
            
            if near_key == '高进攻' and zero_key == '高' and three_key == 'C级':
                result['reason'] = '近况好但庄家不想要0球 -> 实际2-3球'
            elif near_key == '中进攻' and zero_key == '中':
                result['reason'] = '均衡比赛，进球分布均匀'
            elif near_key == '中进攻' and zero_key == '高':
                result['reason'] = '庄家认为0球概率低，实际2-3球'
            elif near_key == '弱进攻' and zero_key in ['中', '高']:
                result['reason'] = '弱进攻，进球数偏少'
            else:
                result['reason'] = '根据近况×赔率组合判断'
    else:
        # 无历史数据，使用逻辑推断
        g1 = features.get('1球')
        g2 = features.get('2球')
        g4 = features.get('4球')

        if three_key in ['A级', 'B级']:
            result['recommendation'] = '单选3球'
            result['second_pick'] = None
            result['confidence'] = 55
            result['hit_rate'] = None
            result['sample_size'] = 0
            result['reason'] = f'3球{three_key}赔率偏低，单选'
            result['signal'] = '3球赔率支持'
        elif three_key == 'C级':
            if g2 and g3 and g2 / g3 < 0.85:
                result['recommendation'] = '3+2球'
                result['second_pick'] = '2球'
                result['reason'] = '2球赔率接近3球，庄家分流'
            else:
                result['recommendation'] = '3+4球'
                result['second_pick'] = '4球'
                result['reason'] = '大球比赛，选3+4球'
            result['confidence'] = 40
            result['hit_rate'] = None
            result['sample_size'] = 0
            result['signal'] = f'{near_key} + 0球{zero_key} + 3球{three_key}(无样本)'
        elif three_key == 'D级':
            if near_key == '弱进攻':
                result['recommendation'] = '3+1球'
                result['second_pick'] = '1球'
                result['reason'] = '弱进攻，低比分'
            elif near_key == '中进攻':
                result['recommendation'] = '3+2球'
                result['second_pick'] = '2球'
                result['reason'] = '中进攻，均衡比赛'
            else:
                result['recommendation'] = '3+4球'
                result['second_pick'] = '4球'
                result['reason'] = '高进攻，大球'
            result['confidence'] = 35
            result['hit_rate'] = None
            result['sample_size'] = 0
            result['signal'] = f'{near_key} + 0球{zero_key} + 3球{three_key}(无样本)'
        else:
            if near_key == '弱进攻':
                result['recommendation'] = '3+1球'
                result['second_pick'] = '1球'
                result['reason'] = '弱进攻+高赔率，低比分'
            elif near_key == '中进攻':
                result['recommendation'] = '3+1球'
                result['second_pick'] = '1球'
                result['reason'] = '中进攻但3球赔率高，关注低比分'
            else:
                result['recommendation'] = '3+2球'
                result['second_pick'] = '2球'
                result['reason'] = '高进攻但3球赔率高，实际2-3球'
            result['confidence'] = 30
            result['hit_rate'] = None
            result['sample_size'] = 0
            result['signal'] = f'{near_key} + 0球{zero_key} + 3球{three_key}(无样本，E级高赔率)'

    return result


def recommend_exclude_double_pick(features, match_data=None):
    """
    排除法双选推荐函数

    【逻辑】:
    1. 收集所有进球数赔率和变化率
    2. 排除：赔率>3.5 且 升赔>=5% 的选项（0球不排除）
    3. 在剩余选项中，选择历史命中率最高的两个
    4. 如果只有一个选项，单选；否则双选命中率最高的两个

    【返回】: {
        'recommendation': '3+2球' / '单选X球' / None,
        'second_pick': '2球' / None,
        'hit_rate': 38.1,  # 单选命中率
        'double_hit_rate': 59.2,  # 双选命中率
        'excluded': ['1球', '4球'],  # 被排除的选项
        'remaining': ['2球', '3球'],  # 剩余可选项
        'reason': 理由,
        'signal': '排除法',
    }
    """
    result = {
        'recommendation': None,
        'second_pick': None,
        'hit_rate': None,
        'double_hit_rate': None,
        'excluded': [],
        'remaining': [],
        'reason': None,
        'signal': '排除法',
    }

    # 收集所有进球数赔率
    all_goals = []
    for g in range(8):
        od = features.get(f'{g}球')
        if od is not None and od > 0:
            all_goals.append({
                'goal': g,
                'name': f'{g}球',
                'odds': float(od)
            })

    if len(all_goals) < 2:
        return result

    # 如果有match_data，检查赔率变化
    if match_data:
        ttg_change = match_data.get('ttg_change') or {}
        for goal_info in all_goals:
            change = ttg_change.get(goal_info['name']) or {}
            if change:
                goal_info['change_pct'] = change.get('change_pct', 0)
            else:
                goal_info['change_pct'] = 0
    else:
        for goal_info in all_goals:
            goal_info['change_pct'] = 0

    # 排除逻辑（按优先级）：
    # 1. 0球不排除
    # 2. 赔率升>=5% → 强排除（赔率高被造热，不管命中率多高）
    # 3. 赔率>3.5 且 命中率<20% → 排除（低概率高赔率）
    # 4. 赔率>3.5 且 命中率>=20% 且 赔率没升 → 保留（高赔率高命中率但未被造热）
    excluded = []
    remaining = []
    for goal_info in all_goals:
        g = goal_info['goal']
        odds = goal_info['odds']
        change_pct = goal_info.get('change_pct', 0)
        
        # 0球永远不排除
        if g == 0:
            remaining.append(goal_info)
            continue
        
        # 赔率升>=5% → 强排除（不管命中率）
        if change_pct >= 5:
            excluded.append(goal_info)
            continue
        
        # 赔率没升，检查赔率绝对值和命中率
        if odds > 3.5:
            hit = get_odds_hit_rate(g, odds)
            hit_rate = hit[0] if hit else None
            # 赔率>3.5 且 命中率>=20% → 保留（高赔率但高命中率未被造热）
            if hit_rate is not None and hit_rate >= 20:
                remaining.append(goal_info)
            else:
                # 命中率<20%，排除
                excluded.append(goal_info)
        else:
            # 赔率<=3.5，保留
            remaining.append(goal_info)

    result['excluded'] = [g['name'] for g in excluded]
    result['remaining'] = [g['name'] for g in remaining]
    
    # 找出高赔率但高命中率保留的选项（显示用）
    high_odds_kept = []
    for g in remaining:
        odds = g['odds']
        hit = get_odds_hit_rate(g['goal'], odds)
        hit_rate = hit[0] if hit else None
        if odds > 3.5 and hit_rate is not None and hit_rate >= 20:
            high_odds_kept.append(g)

    if len(remaining) == 0:
        result['reason'] = '所有选项都被排除'
        return result

    if len(remaining) == 1:
        # 只有一个选项，单选
        goal_info = remaining[0]
        hit = get_odds_hit_rate(goal_info['goal'], goal_info['odds'])
        if hit:
            result['hit_rate'] = hit[0]
            result['double_hit_rate'] = hit[0]
            result['confidence'] = min(80, int(hit[0] * 0.9))
            result['reason'] = f"只剩{goal_info['name']}，单选 {goal_info['name']}={goal_info['odds']}(历史{hit[0]}%)"
        else:
            result['hit_rate'] = None
            result['double_hit_rate'] = None
            result['confidence'] = 30
            result['reason'] = f"只剩{goal_info['name']}，单选 {goal_info['name']}={goal_info['odds']}"
        result['recommendation'] = f"单选{goal_info['name']}"
        result['second_pick'] = None
        return result

    # 剩余>=2个选项，按历史命中率排序
    scored = []
    for goal_info in remaining:
        hit = get_odds_hit_rate(goal_info['goal'], goal_info['odds'])
        if hit:
            scored.append((goal_info, hit[0], hit[1]))
        else:
            # 无历史数据，使用赔率估算（赔率越低概率越高）
            # 赔率3.0 ≈ 33%，2.5 ≈ 40%，2.0 ≈ 50%
            est = max(10, min(40, 100 / (goal_info['odds'] * 3)))
            scored.append((goal_info, est, 0))

    # 按命中率降序排序
    scored.sort(key=lambda x: -x[1])

    top1, top1_rate, top1_sample = scored[0]
    top2, top2_rate, top2_sample = scored[1]

    # 单选命中率
    result['hit_rate'] = round(top1_rate, 1)
    # 双选命中率
    result['double_hit_rate'] = round((top1_rate + top2_rate) / 2, 1)
    result['confidence'] = min(80, int(result['double_hit_rate'] * 0.9))

    # 构建推荐
    excluded_names = [g['name'] for g in excluded]
    # 高赔率但命中率>=20%保留的选项（显示用）
    high_kept_names = [g['name'] for g in remaining 
                       if g['odds'] > 3.5 and get_odds_hit_rate(g['goal'], g['odds']) 
                       and get_odds_hit_rate(g['goal'], g['odds'])[0] >= 20]
    
    if top1_rate - top2_rate > 15:
        # 第一名比第二名高15%以上，单选
        result['recommendation'] = f"单选{top1['name']}"
        result['second_pick'] = None
        sample_hint = f"(样本{top1_sample}场)" if top1_sample >= 3 else "(无样本)"
        excl_str = '、'.join(excluded_names) if excluded_names else '无'
        kept_str = f'（{"、".join(high_kept_names)}赔率高但命中率≥20%保留）' if high_kept_names else ''
        result['reason'] = f"排除{excl_str}{kept_str}，单选 {top1['name']}={top1['odds']} {sample_hint}(历史{top1_rate}%)"
    else:
        # 差距不大，双选
        result['recommendation'] = f"{top1['name']}+{top2['name']}"
        result['second_pick'] = top2['name']
        hint1 = f"(历史{top1_rate}%)" if top1_sample >= 3 else "(无样本)"
        hint2 = f"(历史{top2_rate}%)" if top2_sample >= 3 else "(无样本)"
        excl_str = '、'.join(excluded_names) if excluded_names else '无'
        kept_str = f'（{"、".join(high_kept_names)}赔率高但命中率≥20%保留）' if high_kept_names else ''
        result['reason'] = f"排除{excl_str}{kept_str}，选命中率最高两个：{top1['name']}={top1['odds']}{hint1} + {top2['name']}={top2['odds']}{hint2}"

    return result


# ============================================================
# 黄金2球预测函数（基于0=10规律）
# 条件：0球=10 + 2球赔率区间 + 近况特征
# ============================================================

GOLDEN_2GOAL_STATS = {
    # 0球赔率 -> {2球区间: (命中率%, 样本数)}
    10: {
        (2.9, 3.3): (42.9, 21),  # 0=10 + 2球2.9-3.3 → 2球率43%
        (3.1, 3.3): (43.0, 9),    # 0=10 + 2球3.1-3.3 → 2球率43%
    },
    11: {
        (3.3, 3.5): (33.3, 12),   # 0=11 + 2球3.3-3.5 → 2球率33%（但3球率42%更高）
    },
    23: {
        (4.0, 4.4): (50.0, 4),    # 0=23 + 2球4.0-4.4 → 2球率50%
    },
}

def predict_2goals(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    黄金2球预测函数
    
    核心规律（基于262场回测）:
    - 0=10 + 2球3.1-3.3 → 2球率 43%（21场验证）
    - 0=23 + 2球4.0-4.4 → 2球率 50%（4场验证）
    
    近况特征:
    - 合并均值<1.5时2球命中率更高（67%）
    - 合并均值1.5-2.5时2球命中率中等（33%）
    - 近况>=2.5时2球命中率极低（0%）
    
    返回:
    {
        'is_golden_2': bool,
        'recommendation': '关注2球' / '观望' / '排除2球',
        'reason': 理由,
        'features': {0球, 2球, 近况},
        'hit_rate': 命中率%,
        'sample_size': 样本数,
    }
    """
    g0 = features.get('0球')
    g2 = features.get('2球')
    form = features.get('近况')
    
    result = {
        'is_golden_2': False,
        'recommendation': '观望',
        'reason': None,
        'features': {
            '0球': g0,
            '2球': g2,
            '近况': form.get('combined_avg') if form else None,
        },
        'hit_rate': None,
        'sample_size': None,
        'warnings': [],
        'signals': [],
    }
    
    # 近况分析
    combined_avg = form.get('combined_avg') if form else None
    
    # ── 黄金2球判断 ──
    golden_2 = False
    golden_reason = []
    
    # 条件1: 0球=10 或 0球=23
    if g0 == 10:
        # 0=10 + 2球3.1-3.3
        if g2 is not None and 3.1 <= g2 <= 3.3:
            golden_2 = True
            golden_reason.append(f'0球={g0} + 2球={g2}(3.1-3.3区间)')
            result['hit_rate'] = 43.0
            result['sample_size'] = 9
        elif g2 is not None and 2.9 <= g2 < 3.1:
            # 稍宽区间
            golden_2 = True
            golden_reason.append(f'0球={g0} + 2球={g2}(2.9-3.1区间)')
            result['hit_rate'] = 42.9
            result['sample_size'] = 21
    elif g0 == 23:
        # 0=23 + 2球4.0-4.4
        if g2 is not None and 4.0 <= g2 <= 4.4:
            golden_2 = True
            golden_reason.append(f'0球={g0} + 2球={g2}(4.0-4.4区间)')
            result['hit_rate'] = 50.0
            result['sample_size'] = 4
    
    # 条件2: 近况判断
    if combined_avg is not None:
        if combined_avg < 1.5:
            result['signals'].append(f'近况均值={combined_avg}<1.5，支持2球（历史67%命中）')
            golden_reason.append(f'近况{combined_avg}<1.5，加分')
        elif combined_avg < 2.5:
            result['signals'].append(f'近况均值={combined_avg}，2球中性')
        elif combined_avg >= 2.5:
            result['warnings'].append(f'近况均值={combined_avg}≥2.5，2球概率降低')
            golden_reason.append(f'近况{combined_avg}≥2.5，减分')
    
    if golden_2:
        result['is_golden_2'] = True
        result['recommendation'] = '关注2球'
        result['reason'] = ' | '.join(golden_reason)
        if combined_avg is not None and combined_avg >= 2.5:
            result['recommendation'] = '观望'
            result['warnings'].append('近况偏高，2球不可靠')
    else:
        # 非黄金2球，检查是否应排除
        if combined_avg is not None and combined_avg >= 2.5:
            result['recommendation'] = '排除2球'
            result['reason'] = f'近况均值{combined_avg}≥2.5，2球概率低'
    
    return result


# ============================================================
# 黄金4球预测函数（基于0=30规律）
# 条件：0球=30 + 4球赔率区间 + 近况特征
# ============================================================

GOLDEN_4GOAL_STATS = {
    # 0球赔率 -> {4球区间: (命中率%, 样本数)}
    30: {
        (3.4, 3.6): (100.0, 1),  # 0=30 + 4球3.4-3.6 → 100%（样本极小）
        (4.1, 4.5): (66.7, 3),    # 0=30 + 4球4.1-4.5 → 67%
        (3.7, 4.0): (50.0, 2),   # 0=30 + 4球3.7-4.0 → 50%
    },
}

def predict_4goals(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    黄金4球预测函数
    
    核心规律（基于262场回测）:
    - 0=30 + 4球4.1-4.5 → 4球率 67%（3场验证）
    - 0=30 + 4球3.4-3.6 → 4球率 100%（1场验证）
    
    近况特征:
    - 合并均值1.5-2.5区间 → 4球命中概率高（75%）
    - 近况<1.5 → 4球率25%
    - 近况>=2.5 → 4球率0%
    
    返回:
    {
        'is_golden_4': bool,
        'recommendation': '关注4球' / '观望' / '排除4球',
        'reason': 理由,
        'features': {0球, 4球, 近况},
        'hit_rate': 命中率%,
        'sample_size': 样本数,
    }
    """
    g0 = features.get('0球')
    g4 = features.get('4球')
    form = features.get('近况')
    
    result = {
        'is_golden_4': False,
        'recommendation': '观望',
        'reason': None,
        'features': {
            '0球': g0,
            '4球': g4,
            '近况': form.get('combined_avg') if form else None,
        },
        'hit_rate': None,
        'sample_size': None,
        'warnings': [],
        'signals': [],
    }
    
    # 近况分析
    combined_avg = form.get('combined_avg') if form else None
    
    # ── 黄金4球判断 ──
    golden_4 = False
    golden_reason = []
    
    # 条件1: 0球=30
    if g0 == 30:
        # 0=30 + 4球各区间
        if g4 is not None and 4.1 <= g4 <= 4.5:
            golden_4 = True
            golden_reason.append(f'0球={g0} + 4球={g4}(4.1-4.5区间)')
            result['hit_rate'] = 66.7
            result['sample_size'] = 3
        elif g4 is not None and 3.4 <= g4 < 4.1:
            golden_4 = True
            golden_reason.append(f'0球={g0} + 4球={g4}(3.4-4.1区间)')
            result['hit_rate'] = 66.7 if g4 >= 3.7 else 100.0
            result['sample_size'] = 1 if g4 < 3.7 else 3
        elif g4 is not None and 4.5 < g4 <= 5.0:
            golden_4 = True
            golden_reason.append(f'0球={g0} + 4球={g4}(4.5-5.0区间)')
            result['hit_rate'] = 50.0
            result['sample_size'] = 2
    
    # 条件2: 近况判断（关键！）
    if combined_avg is not None:
        if 1.5 <= combined_avg <= 2.5:
            result['signals'].append(f'近况均值={combined_avg}在[1.5,2.5]，支持4球（历史75%命中）')
            golden_reason.append(f'近况{combined_avg}在[1.5,2.5]，加分')
        elif combined_avg < 1.5:
            result['signals'].append(f'近况均值={combined_avg}<1.5，4球中性')
        elif combined_avg > 2.5:
            result['warnings'].append(f'近况均值={combined_avg}>2.5，4球概率降低')
            golden_reason.append(f'近况{combined_avg}>2.5，减分')
    
    if golden_4:
        result['is_golden_4'] = True
        result['recommendation'] = '关注4球'
        result['reason'] = ' | '.join(golden_reason)
        if combined_avg is not None and combined_avg > 2.5:
            result['recommendation'] = '观望'
            result['warnings'].append('近况偏高，4球不可靠')
    else:
        # 非黄金4球，检查是否应排除
        if combined_avg is not None and combined_avg > 2.5:
            result['recommendation'] = '排除4球'
            result['reason'] = f'近况均值{combined_avg}>2.5，4球概率低'
        elif g0 == 30:
            result['reason'] = f'0球=30但4球赔率不在合适区间'
    
    return result


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
