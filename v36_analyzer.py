#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V3.6 自动推理分析引擎
实现完整推理流程: Step0 → 5.24 → 2.5 → 4 → 7.8 → 7.9 → 7.10
集成四条比分规律
"""
import json, os, math
from collections import Counter

# ============================================================
# 工具函数
# ============================================================

def _safe_float(v, default=999.0):
    try: return float(v)
    except: return default

def _extract_recent_matches(data):
    """提取近5场数据, 返回每场{scored, conceded, total, venue}"""
    preview = data.get('preview', {}) or {}
    recent = preview.get('recent', {}) or {}
    mi = data.get('match_info', {})
    home_name = mi.get('home_team', '')
    away_name = mi.get('away_team', '')
    
    result = {'home': [], 'away': []}
    for side, target_name in [('home', home_name), ('away', away_name)]:
        ml = recent.get(side, {}).get('matchList', [])
        for m in ml[:5]:
            hg = m.get('homeTeamFullCourtGoalCnt')
            ag = m.get('awayTeamFullCourtGoalCnt')
            if hg is None or ag is None:
                continue
            home_short = m.get('homeTeamShortName', '') or ''
            away_short = m.get('awayTeamShortName', '') or ''
            team_short = m.get('teamShortName', '') or ''
            
            is_home = False
            if team_short:
                is_home = (home_short == team_short)
            elif target_name:
                # Fuzzy match: contains OR partial match >= 2 chars
                def _fuzzy(a, b):
                    if a in b or b in a: return True
                    shared = sum(1 for c in a if c in b)
                    if shared < 1: return False
                    if shared >= 2: return True
                    la, lb = len(a), len(b)
                    return max(la, lb) >= 4 and shared / max(la, 1) >= 0.25
                def _fz_score(a, b):
                    if a in b or b in a: return max(len(a), len(b)) + 10
                    return sum(1 for c in a if c in b)
                hs = _fz_score(target_name, home_short)
                aws = _fz_score(target_name, away_short)
                if hs == 0 and aws == 0:
                    continue
                is_home = (hs >= aws)
            else:
                continue
            
            team_scored = int(hg) if is_home else int(ag)
            opp_scored = int(ag) if is_home else int(hg)
            result[side].append({
                'scored': team_scored,
                'conceded': opp_scored,
                'total': int(hg) + int(ag),
                'venue': '主' if is_home else '客',
                'result': m.get('teamMatchResult', ''),
            })
    return result

def _calc_att_def(recent):
    """计算攻击力(场均进球)和防守力(场均失球)"""
    home = recent.get('home', [])
    away = recent.get('away', [])
    
    h_att = sum(r['scored'] for r in home) / max(len(home), 1)
    h_def = sum(r['conceded'] for r in home) / max(len(home), 1)
    a_att = sum(r['scored'] for r in away) / max(len(away), 1)
    a_def = sum(r['conceded'] for r in away) / max(len(away), 1)
    
    return h_att, h_def, a_att, a_def

def _get_change_info(data, goal_key):
    """获取进球数的变化信息（从预加载命中率数据提取）"""
    tc = data.get('ttg_change', {}) or {}
    info = tc.get(goal_key, {})
    pct = float(info.get('change_pct', 0) or 0)
    changes = info.get('count', info.get('changes', 0)) or 0
    
    # Try pre-loaded change hit rate data
    hr_data = data.get('_change_hitrate', {})
    hit_rate = 0.0
    sample = 0
    
    if hr_data:
        goal_buckets = hr_data.get(goal_key, {})
        if goal_buckets:
            # Find the matching bucket for this change
            abs_pct = abs(pct)
            if abs_pct == 0:
                bucket = '0%不变'
            elif abs_pct <= 2:
                direction = '涨' if pct > 0 else '降'
                bucket = f'0-2%{direction}'
            elif abs_pct <= 5:
                direction = '涨' if pct > 0 else '降'
                bucket = f'2-5%{direction}'
            elif abs_pct <= 10:
                direction = '涨' if pct > 0 else '降'
                bucket = f'5-10%{direction}'
            else:
                direction = '涨' if pct > 0 else '降'
                bucket = f'>20%{direction}'
            
            bd = goal_buckets.get(bucket, {})
            if bd:
                total = bd.get('total', 0)
                hits = bd.get('hits', 0)
                hit_rate = (hits / total) if total > 0 else 0
                sample = total
    else:
        # Fallback: extract from change count
        sample = changes or 0
    
    # V3.7: Extract odds hit rate from pre-loaded data
    odds_hit_rate = 0.0
    odds_sample = 0
    od_data = data.get('_odds_hitrate', {})
    if od_data:
        tg = data.get('total_goals', {}) or {}
        odds_val = tg.get(goal_key, '')
        if isinstance(odds_val, str):
            try: odds_val = round(float(odds_val), 2)
            except: odds_val = 0
        elif isinstance(odds_val, (int, float)):
            odds_val = round(float(odds_val), 2)
        
        if odds_val and odds_val > 0:
            exact_data = od_data.get('exact', {})
            g_num = int(goal_key.replace('球', ''))
            goal_exact = exact_data.get(g_num, {})
            val_data = goal_exact.get(str(odds_val), {})
            if val_data:
                odds_hit_rate = (val_data.get('rate', 0) or 0) / 100.0
                odds_sample = val_data.get('total', 0)
    
    return {
        'pct': pct,
        'hit_rate': hit_rate,
        'sample': sample,
        'changes': changes,
        'odds_hit_rate': odds_hit_rate,
        'odds_sample': odds_sample,
    }

def _get_odds_hit(data, goal_key):
    """获取赔率命中率"""
    tg = data.get('total_goals', {}) or {}
    # The UI data embeds hit rate in the value: "3.30 25.9% ↑6.5%"
    raw = tg.get(goal_key, '')
    if isinstance(raw, (int, float)):
        return float(raw)
    # Try to extract hit rate from string format
    # Actually, let's use the data attribute  
    return _safe_float(raw, 0)

# ============================================================
# 核心分析函数
# ============================================================

def analyze_match(data):
    """
    完整的V3.6分析
    返回: dict with analysis results
    """
    mi = data.get('match_info', {})
    had = data.get('had', {}) or {}
    hhad = data.get('hhad', {}) or {}
    tg = data.get('total_goals', {}) or {}
    score_odds = data.get('score_odds', {}) or {}
    ou = data.get('over_under', {}) or {}
    tc = data.get('ttg_change', {}) or {}
    
    recent = _extract_recent_matches(data)
    h_att, h_def, a_att, a_def = _calc_att_def(recent)
    
    # 近况组合
    home_recent_goals = [r['total'] for r in recent.get('home', [])]
    away_recent_goals = [r['total'] for r in recent.get('away', [])]
    all_goals = home_recent_goals + away_recent_goals
    combined_avg = sum(all_goals) / max(len(all_goals), 1) if all_goals else 0
    
    # 赔率数据
    g0_val = _safe_float(tg.get('0球', 0))
    g1_val = _safe_float(tg.get('1球', 0))
    g2_val = _safe_float(tg.get('2球', 0))
    g3_val = _safe_float(tg.get('3球', 0))
    g4_val = _safe_float(tg.get('4球', 0))
    g5_val = _safe_float(tg.get('5球', 0))
    g6_val = _safe_float(tg.get('6球', 0))
    g7_val = _safe_float(tg.get('7球', 0))
    
    ou_line = _safe_float(ou.get('ou_line', 0)) if ou else 0
    ou_over = _safe_float(ou.get('over_odds', 0)) if ou else 0
    ou_under = _safe_float(ou.get('under_odds', 0)) if ou else 0
    
    had_win = _safe_float(had.get('胜', had.get('W', 0)))
    had_draw = _safe_float(had.get('平', had.get('D', 0)))
    had_lose = _safe_float(had.get('负', had.get('L', 0)))
    
    hhad_handicap = hhad.get('让球', '0')
    hhad_win = _safe_float(hhad.get('让胜', 0))
    hhad_draw = _safe_float(hhad.get('让平', 0))
    hhad_lose = _safe_float(hhad.get('让负', 0))
    
    # ============== Step 0: 大小球方向 ==============
    theo_g0_lo = h_att + 10
    theo_g0_hi = a_att + 10
    g0_deviation = g0_val - max(theo_g0_lo, theo_g0_hi)
    
    # 理论标准线(简化版)
    if combined_avg < 2.0: std_line = 2.0
    elif combined_avg < 2.5: std_line = 2.25
    elif combined_avg < 3.0: std_line = 2.5
    elif combined_avg < 3.5: std_line = 2.75
    elif combined_avg < 4.0: std_line = 3.0
    elif combined_avg < 5.0: std_line = 3.25
    else: std_line = 3.5
    
    line_deviation = (ou_line - std_line) if ou_line > 0 else 0
    
    g0_dir = '大球' if g0_deviation > 2 else ('小球' if g0_deviation < -2 else '中性')
    line_dir = '大球' if line_deviation > 0.5 else ('小球' if line_deviation < -0.5 else '中性')
    water_dir = '大球' if ou_over < 0.85 else ('小球' if ou_under < 0.85 else '中性')
    
    # V3.7: HAD赔率方向信号
    had_dir = '中性'
    had_strength = 0  # 0=不用, 1=弱, 2=强
    if had_win > 0 and had_win < 1.50:
        had_signal = f'主胜{had_win}极低→大球'
        had_dir = '大球'
        had_strength = 2
    elif had_lose > 0 and had_lose < 2.00:
        had_signal = f'客胜{had_lose}低→大球'
        had_dir = '大球'
        had_strength = 1
    elif had_draw > 0 and had_draw < 3.00:
        had_signal = f'平局{had_draw}低→小球'
        had_dir = '小球'
        had_strength = 2
    
    # ===== V3.7: 0球区间铁律（历史回测验证的方向增强） =====
    g0_rule_dir = None
    g0_rule_name = ''
    if 10 <= g0_val <= 12 and combined_avg <= 3.0:
        g0_rule_dir = '小球'
        g0_rule_name = f'0球={g0_val:.0f}(区间10-12)+近{combined_avg:.1f}→小球倾向'
    elif 13 <= g0_val <= 14 and combined_avg <= 3.0:
        g0_rule_dir = '大球'
        g0_rule_name = f'0球={g0_val:.0f}(区间13-14)+近{combined_avg:.1f}→大球信号'
    elif g0_val >= 19:
        g0_rule_dir = '大球'
        g0_rule_name = f'0球={g0_val:.0f}(≥19)→极端大球信号'
    elif g0_val < 10:
        g0_rule_dir = '小球'
        g0_rule_name = f'0球={g0_val:.0f}(<10)→小球信号'
    
    # V3.7: 半全场辅助信号 (5.19节)
    hafu = data.get('hafu_change', {}) or {}
    hafu_signal = None
    hafu_name = ''
    if hafu:
        pp_ch = hafu.get('平平', {}).get('change_pct', 0) or 0
        np_ch = hafu.get('负平', {}).get('change_pct', 0) or 0
        sp_ch = hafu.get('胜平', {}).get('change_pct', 0) or 0
        # 3条路径都降 → 平局信号 → 小球
        if pp_ch < -3 and np_ch < -3 and sp_ch < -3:
            hafu_signal = '小球'
            hafu_name = '半全场3路径全降→平局→小球'
        elif pp_ch < -5:  # 平平大降 → 庄家怕半场平
            hafu_signal = '小球'
            hafu_name = f'平平↓{abs(pp_ch):.0f}%→小球倾向'
    
    step0_signals = []
    if g0_dir != '中性': step0_signals.append(f'0球→{g0_dir}')
    if line_dir != '中性': step0_signals.append(f'线位→{line_dir}')
    if water_dir != '中性': step0_signals.append(f'水位→{water_dir}')
    if had_dir != '中性' and had_strength >= 1: step0_signals.append(had_signal)
    if hafu_signal: step0_signals.append(hafu_name)
    
    # 信号计数（HAD强信号计1票，弱信号不计）
    all_dirs = [g0_dir, line_dir, water_dir]
    if had_strength >= 1:
        all_dirs.append(had_dir)
    big_signals = sum(1 for d in all_dirs if d == '大球')
    small_signals = sum(1 for d in all_dirs if d == '小球')
    
    # ===== V3.7: 方向判定（含0球区间铁律+近况矛盾修正） =====
    direction = '模糊'
    direction_conf = '弱'
    
    # 优先级1: 近况-0球矛盾（70%大球，20场验证）
    if combined_avg < 2.5 and g0_val > 15:
        direction = '大球'
        direction_conf = '近小球+0球过高→大球'
        step0_signals.append(f'🚨近况{combined_avg:.1f}小球+0球{g0_val:.0f}过高→反转大球')
    # 优先级2: 信号计数
    elif big_signals >= 2:
        direction = '大球'
        direction_conf = '强' if big_signals >= 3 else '中'
    elif small_signals >= 2:
        direction = '小球'
        direction_conf = '强' if small_signals >= 3 else '中'
    elif big_signals == 1 and small_signals == 0:
        direction = '大球'; direction_conf = '弱'
    elif small_signals == 1 and big_signals == 0:
        direction = '小球'; direction_conf = '弱'
    
    # 优先级3: 0球区间铁律（模糊时打破僵局/中方向矛盾时留自救空间）
    if direction == '模糊' and g0_rule_dir:
        direction = g0_rule_dir
        direction_conf = '0球区间铁律'
        step0_signals.append(g0_rule_name)
    elif g0_rule_dir and g0_rule_dir != direction:
        step0_signals.append(f'⚠️{g0_rule_name}(与方向矛盾)')
        # V3.7: 中方向+0球矛盾 → 降为弱方向留自救
        if direction_conf == '中':
            direction_conf = '弱(矛盾留空)'
    elif g0_rule_dir and g0_rule_dir == direction:
        step0_signals.append(g0_rule_name)
    
    step0 = {
        'combined_avg': combined_avg,
        'std_line': std_line,
        'g0_val': g0_val,
        'g0_theo': f'[{theo_g0_lo:.1f},{theo_g0_hi:.1f}]',
        'g0_deviation': g0_deviation,
        'ou_line': ou_line,
        'line_deviation': line_deviation,
        'ou_over': ou_over,
        'ou_under': ou_under,
        'signals': step0_signals,
        'direction': direction,
        'direction_conf': direction_conf,
        'analysis_range': '≤2球' if direction == '小球' else ('≥3球' if direction == '大球' else '全范围'),
    }
    
    # ============== V3.5: 变化命中率否决 ==============
    goal_data = {}
    for gk, gv in [('0球', g0_val), ('1球', g1_val), ('2球', g2_val), 
                    ('3球', g3_val), ('4球', g4_val), ('5球', g5_val),
                    ('6球', g6_val), ('7球', g7_val)]:
        if gv == 0: continue
        ci = _get_change_info(data, gk)
        goal_data[gk] = {
            'odds': gv,
            'change_pct': ci['pct'],
            'change_hit': ci['hit_rate'],
            'change_sample': int(ci['sample']),
            'odds_hit': ci['odds_hit_rate'],
            'odds_sample': ci['odds_sample'],
        }
    
    # ============== V3.7: H/I 模式检测（优先级高于信号计数） ==============
    # H模式: 线位偏浅+大球低水+0球↓ → 实际小球
    # I模式: 线位偏浅+小球低水+0球→0% → 实际大球
    
    g0_ch_pct = _get_change_info(data, '0球').get('pct', 0)
    line_is_shallow = line_deviation < -0.3  # 线位明显偏浅
    g0_is_defending = g0_ch_pct < -2  # 0球下降>2% = 防范小球
    g0_is_static = abs(g0_ch_pct) < 0.5  # 0球不动 = 不防
    
    hi_override = False
    if line_is_shallow and ou_over < 0.85 and g0_is_defending:
        # H模式: 盘口大球+0球↓→实际小球
        direction = '小球'
        direction_conf = 'H模式(线偏浅+0球↓)'
        hi_override = True
    elif line_is_shallow and ou_under < 0.85 and g0_is_static:
        # I模式: 盘口小球+0球不动→实际大球  
        direction = '大球'
        direction_conf = 'I模式(线偏浅+0球不动)'
        hi_override = True
    
    # ============== 5.24 veto（V3.7收紧：双条件确认防误杀） ==============
    veto_triggered = False
    veto_reason = ''
    
    if not hi_override:
        high_ball_all_static = all(
            _get_change_info(data, g).get('pct', 1) == 0 
            for g in ['5球', '6球', '7球']
        )
        
        if direction == '大球' and high_ball_all_static:
            if line_deviation < -0.2:
                veto_triggered = True
                veto_reason = f'高球不动+线偏浅({line_deviation:.1f})→反转小球'
            else:
                direction_conf = '弱(高球不动降权)'
                veto_reason_warn = '高球不动→降权但不反转'
        elif direction == '小球' and g0_is_static:
            if line_deviation < -0.3 or abs(line_deviation) < 0.1:
                veto_triggered = True
                veto_reason = '0球不动+线偏浅→反转大球'
            else:
                direction_conf = '弱(0球不动降权)'
                veto_reason_warn = '0球不动→降权但不反转'
    
    if veto_triggered:
        direction = '小球' if direction == '大球' else '大球'
        direction_conf = '修正(否决)'
        step0['direction'] = direction
        step0['direction_conf'] = direction_conf
        step0['analysis_range'] = '≤2球' if direction == '小球' else '≥3球'
        step0['vetoed'] = True
    
    # ============== Step 2.5: 造热检查 ==============
    # Check if system recommends 3球
    g3_pred = data.get('g3_prediction', {}) or {}
    golden_3 = g3_pred.get('golden_3goals', False)
    big3_pred = g3_pred.get('big3_prediction', False)
    
    ci_3 = _get_change_info(data, '3球')
    heat_triggered = False
    if g3_val > 0 and 3.2 <= g3_val <= 3.5:
        signals = 0
        if combined_avg > 3.0: signals += 1  # A2: 近况支持
        if ci_3['hit_rate'] >= 0.2: signals += 1  # A3: 变化命中率
        if golden_3 or big3_pred: signals += 1  # A4: 系统推荐
        if ci_3['pct'] < 0: signals += 1  # A5: 赔率↓
        if g3_val <= 3.5: signals += 1  # A1: 舒适区间
        if signals >= 5:
            heat_triggered = True
    
    # ============== Step 4: 三维排除 ==============
    exclusion_results = []
    for gk, gd in goal_data.items():
        g_num = int(gk.replace('球', ''))
        odds = gd['odds']
        ch = gd['change_hit']
        cs = gd['change_sample']
        pc = gd['change_pct']
        oh = gd['odds_hit']  # V3.7: 赔率命中率
        os = gd['odds_sample']  # V3.7: 赔率样本量
        
        status = '保留'
        reason = ''
        
        # System exclusions
        exc_list = data.get('exclusion_list', []) or []
        sys_exclude = any(gk in str(e) for e in exc_list)
        
        # ===== V3.7 精细化排除 =====
        # 0球: 赔率>18 or 变化↑>8% → 强排除
        if g_num == 0 and odds > 18:
            status = '排除'
            reason = f'0球极高({odds})'
        elif g_num == 0 and pc > 8 and cs >= 5:
            status = '排除'
            reason = f'0球推离{pc:.0f}%'
        elif g_num == 0 and cs >= 5 and ch < 0.1:
            status = '排除'
            reason = '变化命中率<10%'
        
        # 1球: 系统排除 or 赔率>5+推离 → 排除
        elif g_num == 1 and sys_exclude and odds > 4.5:
            status = '排除'
            reason = '系统排除+高赔'
        elif g_num == 1 and ch < 0.1 and cs >= 10:
            status = '排除'
            reason = f'变化命中率{ch:.0%}<10%'
        
        # 2球: 双低(<10%)+↑推离 → 排除
        elif g_num == 2 and ch < 0.1 and cs >= 10 and pc > 0:
            status = '排除'
            reason = '双低+推离'
        
        # 5-7球
        elif g_num >= 5 and cs < 5:
            status = '排除'
            reason = '样本不足'
        elif g_num >= 5 and ch < 0.1 and cs >= 5:
            status = '排除'
            reason = '双低'
        
        # ===== 保留条件 =====
        if '排除' not in status:
            # V3.7: 双命中率铁保留 (变化≥15% + 赔率≥15% + 各自样本≥10)
            if ch >= 0.15 and cs >= 10 and oh >= 0.15 and os >= 10:
                status = '🛡️双高铁保留'
                reason = f'变{ch:.0%}+赔{oh:.0%}双高'
            elif ch >= 0.15 and cs >= 10:
                status = '🛡️铁保留'
                reason = f'变化命中率{ch:.0%}≥15%'
            elif oh >= 0.15 and os >= 10:
                status = '🛡️铁保留'
                reason = f'赔率命中率{oh:.0%}≥15%'
            # V3.7: 双低排除 (变化<10%+赔率<10%, 均有样本)
            elif ch < 0.1 and cs >= 10 and oh < 0.1 and os >= 10:
                status = '排除'
                reason = f'双低(变{ch:.0%}+赔{oh:.0%})'
            # 赔率命中率0%+大样本(≥10) = 强排除
            elif oh == 0 and os >= 10:
                status = '排除'
                reason = f'赔率命中率0%({os}场)'
            elif ch >= 0.2 and cs >= 10 and pc < 0 and sys_exclude:
                status = '🔥大热排除'
                reason = '双高+↓+系统排除'
            elif sys_exclude and ch < 0.1 and cs >= 5:
                if g_num != 2:
                    status = '排除'
                    reason = '系统排除+低命中率'
        
        exclusion_results.append({
            'goal': gk,
            'odds': odds,
            'change_pct': pc,
            'change_hit': ch,
            'change_sample': cs,
            'status': status,
            'reason': reason,
        })
    
    kept = [e for e in exclusion_results if '保留' in e['status'] or '铁保留' in e['status']]
    excluded = [e for e in exclusion_results if '排除' in e['status']]
    
    # ============== 新规律: 近况锚定 ==============
    if combined_avg < 2.0:
        anchor_rule = '近况<2.0→2球50%大概率'
    elif combined_avg > 3.5:
        anchor_rule = f'近况>{3.5}→>2.5率86.7%'
    else:
        anchor_rule = f'近况{combined_avg:.1f}中性区间'
    
    # ============== 新规律: 主攻击力阈值 ==============
    att_threshold = '通过' if h_att >= 1.5 else f'不通过(主攻{h_att:.1f}<1.5)'
    
    # ============== Step 7.8: 比分反推 ==============
    # 找出候选进球数
    candidate_goals = []
    # V3.7: 弱方向不盲猜，全范围分析
    effective_dir = '模糊' if ('弱' in direction_conf) else direction
    
    for e in kept:
        g = int(e['goal'].replace('球', ''))
        if effective_dir == '小球' and g > 2: continue
        if effective_dir == '大球' and g < 3: continue
        if effective_dir == '模糊':
            candidate_goals.append(g)
        elif (effective_dir == '小球' and g <= 2) or (effective_dir == '大球' and g >= 3):
            candidate_goals.append(g)
    
    if not candidate_goals:
        candidate_goals = [int(e['goal'].replace('球', '')) for e in kept]
    
    candidate_goals.sort()
    
    # ============== V3.7: 攻防匹配分析 ==============
    score_analysis = []
    if h_att >= 2.0:
        score_analysis.append(f'主攻强({h_att:.1f}),能撕破客防({a_def:.1f})')
    elif h_att >= 1.5:
        score_analysis.append(f'主攻一般({h_att:.1f}),尚能威胁客防({a_def:.1f})')
    else:
        if a_def < 1.0:
            score_analysis.append(f'主攻弱({h_att:.1f})难破客防强盾({a_def:.1f})→主队进球期望低')
        else:
            score_analysis.append(f'主攻弱({h_att:.1f})但客防也松({a_def:.1f})→主队有机会')
    if a_att >= 2.0:
        if h_def < 1.0:
            score_analysis.append(f'客攻强({a_att:.1f})vs主防铁壁({h_def:.1f})→矛盾之争')
        else:
            score_analysis.append(f'客攻强({a_att:.1f})能击穿主防({h_def:.1f})→客队进球概率高')
    else:
        if h_def < 1.0:
            score_analysis.append(f'客攻弱({a_att:.1f})vs主防强({h_def:.1f})→客队难进球')
        else:
            score_analysis.append(f'客攻弱({a_att:.1f})但主防也松({h_def:.1f})→双方都可能丢球')
    
    # V3.7: BTS信号 — 需防范一方防守铁壁导致零封
    bts_weak_def = (h_att < 2.0 and a_def >= 1.0) or (a_att < 2.0 and h_def >= 1.0)
    bts_blocked = (a_def < 1.0 or h_def < 1.0)  # 任何一方防守铁壁都能阻挡BTS
    if bts_weak_def and not bts_blocked:
        score_analysis.append('⚠️双方都可能丢球→大概率双方进球(75%/164场,失败全因主队遭零封)')
    elif bts_weak_def and bts_blocked:
        score_analysis.append('⚠️双方防守均有漏洞但一方防线铁壁→BTS信号不可靠')
    
    # 比分推导（增强版）
    score_candidates = []
    for total in candidate_goals[:3]:  # Max 3 goal totals
        scores = []
        for h in range(total + 1):
            a = total - h
            # Basic HAD filter
            if had_win < 2.0 and a > h: continue  # Strong home → away win unlikely
            if had_lose < 2.0 and h > a: continue  # Strong away → home win unlikely
            
            # Venue tag
            if h > a: tag = '主胜'
            elif a > h: tag = '客胜'
            else: tag = '平局'
            
            # V3.7: plausibility by attack-defense match
            h_dev = abs(h - h_att) / max(h_att, 0.5)
            a_dev = abs(a - a_att) / max(a_att, 0.5)
            dev = max(h_dev, a_dev)
            plausibility = '🔥' if dev <= 1.5 else ('✅' if dev <= 3.0 else '⚠️')
            
            # Score odds
            so_key = f'{h:02d}:{a:02d}'
            so_val = score_odds.get(so_key, None)
            
            scores.append({
                'score': f'{h}-{a}',
                'tag': tag,
                'h_capable': plausibility,
                'a_capable': '',
                'score_odds': so_val,
            })
        
        # Filter: keep only "plausible" scores
        plausible = [s for s in scores if '✅' in s['h_capable'] or '✅' in s['a_capable']]
        if not plausible:
            plausible = scores  # all if none clearly capable
        
        score_candidates.append({
            'total_goals': total,
            'scores': plausible,
        })
    
    # If all scores excluded, fallback
    if not score_candidates or not any(s['scores'] for s in score_candidates):
        score_candidates = [{'total_goals': candidate_goals[0], 'scores': [
            {'score': f'{candidate_goals[0]}-{0}', 'tag': '主胜', 'h_capable': '⚠️', 'a_capable': '⚠️', 'note': '兜底'},
        ]}]
    
    # ============== Step 7.9: 终审（V3.7增强） ==============
    handicap_num = 0
    try: handicap_num = abs(int(hhad_handicap))
    except: pass
    
    final_review = {'triggered': False, 'upset': [], 'blowout': False}
    # 标准触发: 让球深(>=2) + 主胜极低(<1.30)
    if handicap_num >= 2 and had_win > 0 and had_win < 1.30:
        final_review['triggered'] = True
        opponent_fragile = a_def >= 1.5 or any(r['conceded'] >= 3 for r in recent.get('away', []))
        if opponent_fragile:
            final_review['upset'].append(f"让{handicap_num}+主胜{had_win}→大胜场景")
            final_review['upset'].append(f"对手脆弱(失球均{a_def:.1f})→意外大胜备选")
    # V3.7增强: 主胜<1.50 + 客队脆弱 → 即使让球不深也可能大胜
    elif had_win > 0 and had_win < 1.50:
        opponent_fragile = a_def >= 1.5 or any(r['conceded'] >= 3 for r in recent.get('away', []))
        if opponent_fragile:
            final_review['triggered'] = True
            final_review['upset'].append(f"主胜{had_win}极低+对手脆弱(客失{a_def:.1f})→大胜备选")
    
    # V3.7: 大球方向+5-7全排除 → 爆冷兜底
    if direction == '大球' and candidate_goals and max(candidate_goals) <= 4:
        final_review['blowout'] = True
        if 5 not in candidate_goals:
            candidate_goals.append(5)
            score_candidates.append({
                'total_goals': 5,
                'scores': [
                    {'score': '3-2', 'tag': '主胜', 'h_capable': '⚠️', 'a_capable': '⚠️', 'note': '大球兜底'},
                    {'score': '4-1', 'tag': '主胜', 'h_capable': '⚠️', 'a_capable': '⚠️', 'note': '大球兜底'},
                ],
            })
            final_review['upset'].append('大球方向+5-7被排除→5球兜底')
    
    # ============== Step 7.10: 反审 ==============
    # Check if recommended goal aligns with expectation
    review_warnings = []
    if kept:
        # Get best candidate
        best_goals = sorted(kept, key=lambda x: x['change_hit'], reverse=True)
        best_goal = int(best_goals[0]['goal'].replace('球', '')) if best_goals else None
        
        if best_goal:
            # 迎合检查
            align_count = 0
            if (best_goal >= 3 and direction == '大球') or (best_goal <= 2 and direction == '小球'):
                align_count += 1
            if (best_goal >= 3 and water_dir == '大球') or (best_goal <= 2 and water_dir == '小球'):
                align_count += 1
            
            # 赔付压力
            odds_val = _safe_float(tg.get(f'{best_goal}球', 0))
            if align_count >= 2 and odds_val < 4.0:
                best_hit = best_goals[0]['change_hit']
                if best_hit >= 0.2:
                    review_warnings.append(f'⚠️ {best_goal}球迎合+压力→陷阱可能')
    
    # ============== V3.7: 防守漏洞检测 ==============
    h_conc_vals = [r.get('conceded', 0) for r in recent.get('home', [])]
    a_conc_vals = [r.get('conceded', 0) for r in recent.get('away', [])]
    has_def_leak = any(c >= 4 for c in h_conc_vals) or (len(a_conc_vals)>0 and sum(a_conc_vals)/max(len(a_conc_vals),1) >= 2.0)
    
    # ============== V3.7: 攻防画像规律 ==============
    profile_rules = []
    # ============== V3.7: 新排除规律（赔率+攻防组合） ==============
    # 排除1球: 客队防守强(失<1.0) + 1球赔率>5.0 → 0%命中(33场)
    if a_def < 1.0 and g1_val > 5.0:
        profile_rules.append('🚫排除1球:客防强(失'+str(round(a_def,1))+')+1球'+str(round(g1_val,1))+'>5→95%(34场仅1翻车)')
    # 排除4球: 0球<10 + 双方攻弱(<1.5) + 4球>4.0 → 0%命中(20场)
    if g0_val < 10 and h_att < 1.5 and a_att < 1.5 and g4_val > 4.0:
        profile_rules.append('🚫排除4球:0球<10+攻弱+4球>4→0%(20场)')
    # 排除4球强化: 原有规律(0球<10+4球>6.0) + 双方攻弱 → 4球率0%(19场)
    if g0_val < 10 and g4_val > 6.0 and h_att < 1.5 and a_att < 1.5:
        profile_rules.append('🚫排除4球强化:旧规律+双方攻弱→0%(19场)')
    # 排除1球强化: 原有规律(1球>5.0) + 主失>=1.5 → 1球率2.9%(70场)
    if g1_val > 5.0 and h_def >= 1.5:
        profile_rules.append('🚫排除1球强化:1球>5+主失≥1.5→仅2.9%(70场)')
    # 排除6球: 主攻>=2 + 客失>=2 + 6球>5.0 → 0%命中(14场)
    if h_att >= 2.0 and a_def >= 2.0 and g6_val > 5.0:
        profile_rules.append('🚫排除6球:主攻强+客漏+6球>5→0%(14场)')
    # 排除2球: 双方攻>=2.0 + 2球>3.5 → 2球率5.9%(17场)
    if h_att >= 2.0 and a_att >= 2.0 and g2_val > 3.5:
        profile_rules.append('🚫排除2球:双方攻强+2球>3.5→仅5.9%(17场)')
    # 排除2球: 客攻>=2.0 + 2球>4.0 → 2球率7.7%(26场)
    if a_att >= 2.0 and g2_val > 4.0:
        profile_rules.append('🚫排除2球:客攻强+2球>4→仅7.7%(26场)')
    if h_def >= 2.0 and a_def >= 2.0:
        profile_rules.append('🔥双方漏勺→大球91%/3-4球55%/0-1球=0%')
    elif h_att >= 2.0 and a_def >= 2.0:
        profile_rules.append('🔥主攻vs客漏→大球91%/3球41%')
    if h_att >= 2.0 and a_att >= 2.0:
        profile_rules.append('🔥双方攻击火爆→大球80%/3球40%')
    if h_def < 1.0 and a_def < 1.0:
        profile_rules.append('🛡️双方铁壁→小球58%/2球50%')
    if h_att < 1.5 and a_att < 1.5 and h_def < 1.5 and a_def < 1.5:
        if has_def_leak:
            profile_rules.append('⚠️双方沉闷但防守有漏洞→小球不可靠(65%大球)')
        else:
            profile_rules.append('😴双方沉闷→小球46%/2球43%')
    try: hcap = int(hhad_handicap)
    except: hcap = 0
    if a_att >= 2.0 and hcap > 0:
        profile_rules.append('🛡️客火爆+主受让→主队不败81%')
    
    # ============== V3.7: 让球盘+近况联合规律 ==============
    # 计算主/客近5场胜场数
    h_win_count = sum(1 for r in recent.get('home', []) if r.get('result', '') in ('home', 'win'))
    a_win_count = sum(1 for r in recent.get('away', []) if r.get('result', '') in ('home', 'win'))
    hhad_lose_odds = _safe_float(hhad.get('让负', 0))
    hhad_win_odds = _safe_float(hhad.get('让胜', 0))
    
    # 规律1: 让负2.50-3.00 + 主队不胜 → 让胜80%/0%让负
    if 2.50 <= hhad_lose_odds <= 3.00 and h_win_count <= 1:
        profile_rules.append('🔥让负'+str(round(hhad_lose_odds,2))+'且主不胜→反弹让胜80%')
    # 规律1b: 让负2.50-3.00 + 主受让 → 双层细分(攻力差+防守差)
    if 2.50 <= hhad_lose_odds <= 3.00 and hcap >= 1:
        if h_att >= a_att and h_def >= 1.5 and a_def < 1.0:
            profile_rules.append('⚠️让负'+str(round(hhad_lose_odds,2))+'且主受让但主防弱客防强→观望(1/14翻车)')
        else:
            profile_rules.append('🔥让负'+str(round(hhad_lose_odds,2))+'且主受让→推荐让胜/让平(14场仅1翻)')
    
    # 规律2: 让胜1.50-1.70 + 主队1-2胜 → 让胜89-100%
    if 1.50 <= hhad_win_odds <= 1.70:
        if 1 <= h_win_count <= 2:
            profile_rules.append('🔥让胜'+str(round(hhad_win_odds,2))+'且主1-2胜→让胜89%+')
        elif h_win_count >= 3:
            profile_rules.append('⚠️让胜'+str(round(hhad_win_odds,2))+'但主3+胜→陷阱!让胜仅30-50%')
    
    # 规律3: 让胜/让负>=4.0 → 高赔几乎不打出的0%规律
    if hhad_win_odds >= 4.0:
        if h_win_count >= 3:
            profile_rules.append('🚫让胜'+str(round(hhad_win_odds,2))+'且主3+胜→让胜0%(21场)')
        if h_win_count >= 3 and a_att < 2.0:
            profile_rules.append('🚫让胜'+str(round(hhad_win_odds,2))+'且主3+胜+客攻弱→让负70%(20场)')
        elif a_win_count <= 1:
            profile_rules.append('🚫让胜'+str(round(hhad_win_odds,2))+'且客不胜→让负59%(22场)')
        else:
            profile_rules.append('🚫让胜'+str(round(hhad_win_odds,2))+'≥4.0→让胜仅17%,选让负/让平')
    if hhad_lose_odds >= 4.0:
        if a_win_count >= 3:
            profile_rules.append('🚫让负'+str(round(hhad_lose_odds,2))+'且客3+胜→让负0%(11场)')
        if h_att < 1.5:
            profile_rules.append('🔥让负≥4.0且主攻弱→让胜80%(20场)')
        else:
            profile_rules.append('🚫让负'+str(round(hhad_lose_odds,2))+'≥4.0→让负仅9%,选让胜')
    
    # ============== V3.7: 盘口偏差规律（攻防预期 vs OU线） ==============
    # 预期 = 主攻 + 客失
    ou_expected = h_att + a_def
    ou_deviation = (ou_line - ou_expected) if ou_line > 0 else 0
    if abs(ou_deviation) >= 0.2:
        if -0.5 <= ou_deviation <= -0.2:
            # 轻度低开 → 大球 (suppressed when attack+defense mismatch)
            if ou_over >= 0.85:
                if h_att < 1.5 and a_att < 1.5:
                    profile_rules.append(f'⚠️轻度低开{ou_deviation:+.1f}+中高水但双方攻弱→降权')
                elif h_def < 1.0 and h_att < 1.5:
                    profile_rules.append(f'⚠️轻度低开{ou_deviation:+.1f}但主防强攻弱→降权(阿森纳1-0翻车)')
                else:
                    profile_rules.append(f'📉轻度低开{ou_deviation:+.1f}+中高水→大球91%')
            else:
                if h_att < 1.5 and a_att < 1.5:
                    profile_rules.append(f'⚠️轻度低开{ou_deviation:+.1f}但双方攻弱→降权')
                elif h_def < 1.0 and h_att < 1.5:
                    profile_rules.append(f'⚠️轻度低开{ou_deviation:+.1f}但主防强攻弱→降权')
                else:
                    profile_rules.append(f'📉轻度低开{ou_deviation:+.1f}→大球88%')
        elif ou_deviation < -0.8:
            # 深度低开
            if ou_over >= 0.9:
                profile_rules.append(f'📉深度低开{ou_deviation:+.1f}+高水→大球75%')
            else:
                profile_rules.append(f'📉深度低开{ou_deviation:+.1f}+低水→小球67%')
        elif ou_deviation > 0.2 and (h_att + a_def) < 2.5:
            if h_att < 1.5 and a_att < 1.5:
                if has_def_leak:
                    profile_rules.append(f'⚠️高开{ou_deviation:+.1f}+双方攻弱但有防守漏洞→大球风险')
                else:
                    profile_rules.append(f'📈高开{ou_deviation:+.1f}+双方攻弱→小球70%(10场)')
            else:
                profile_rules.append(f'📈高开{ou_deviation:+.1f}+预期低→小球仅37%,观望')
    
    # ============== 组装结果 ==============
    # Pick best non-0-0 score
    top_score = '?'
    for sc in score_candidates:
        for s in sc['scores']:
            if s['score'] != '0-0':
                top_score = s['score']
                break
        if top_score != '?': break
    if top_score == '?' and score_candidates and score_candidates[0]['scores']:
        top_score = score_candidates[0]['scores'][0]['score']
    
    return {
        'match_id': data.get('match_id', ''),
        'match_info': mi,
        'recent_summary': {
            'h_att': round(h_att, 2),
            'h_def': round(h_def, 2),
            'a_att': round(a_att, 2),
            'a_def': round(a_def, 2),
            'combined_avg': round(combined_avg, 2),
            'home_recent': [f"{r['venue']} {r['scored']}-{r['conceded']}" for r in recent.get('home', [])],
            'away_recent': [f"{r['venue']} {r['scored']}-{r['conceded']}" for r in recent.get('away', [])],
        },
        'step0': step0,
        'veto': {'triggered': veto_triggered, 'reason': veto_reason} if veto_triggered else None,
        'heat_check': {'triggered': heat_triggered, 'goal': '3球'} if heat_triggered else None,
        'exclusion': {
            'kept': [{'goal': e['goal'], 'hit': f"{e['change_hit']:.0%}", 'status': e['status']} for e in kept],
            'excluded': [{'goal': e['goal'], 'reason': e['reason']} for e in excluded if '排除' in e['status']],
        },
        'new_rules': {
            'anchor': anchor_rule,
            'attack_threshold': f'主攻{h_att:.1f}(\'≥1.5\'→{att_threshold})',
            'attack_vs_defense': f'主攻{h_att:.1f}+客失{a_def:.1f}',
            'profiles': profile_rules,
        },
        'score_candidates': score_candidates,
        'score_analysis': score_analysis,
        'final_review': final_review,
        'review_warnings': review_warnings,
        'recommended': {
            'direction': direction,
            'confidence': direction_conf,
            'goals': candidate_goals[:3],
            'top_score': top_score,
        } if candidate_goals else None,
    }
# V3.6 FIX v2 - Tue May  5 17:00:32     2026
