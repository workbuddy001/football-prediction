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
        g_num_key = int(goal_key.replace('球', ''))
        goal_buckets = hr_data.get(goal_key, hr_data.get(g_num_key, hr_data.get(str(g_num_key), {})))
        if goal_buckets:
            # Build same bucket label as _build_change_hitrate
            abs_pct = abs(pct)
            if abs_pct == 0:
                bucket = '0%不变'
            else:
                direction = '涨' if pct > 0 else '降'
                lo = int(abs_pct)
                if abs_pct == lo:
                    lo = lo - 1
                bucket = f'{lo}-{lo+1}%{direction}'
            
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
    
    # ===== V3.8: 防守维度方向信号 =====
    def_diff = h_def - a_def  # <0=主防好, >0=主防差
    def_dir = '中性'
    def_strength = 0
    if def_diff > 0.3:
        def_dir = '大球'
        def_strength = 1  # 主防劣→倾向大球
    elif def_diff < -0.3:
        def_dir = '小球'
        def_strength = 1  # 主防优→倾向小球
    
    # 水位-防守一致性检查 (V3.8: 525场回测验证)
    def_consistency = '中性'
    def_trap = False
    if water_dir == '大球' and def_dir == '大球':
        def_consistency = '一致强化'  # 大球低水+主防劣→60%(+8pp)
    elif water_dir == '小球' and def_dir == '小球':
        def_consistency = '一致强化'  # 小球低水+主防优→48%(+5pp)
    elif water_dir == '大球' and def_dir == '小球':
        def_consistency = '矛盾'       # 低水吹大但防守好→庄家可能在诱盘
        def_trap = True
    elif water_dir == '小球' and def_dir == '大球':
        def_consistency = '矛盾'       # 低水吹小但防守差→庄家可能在诱盘
        def_trap = True
    
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
    # V3.8: 防守维度信号
    if def_dir != '中性': step0_signals.append(f'防守→{def_dir}(主失{round(h_def,1)}vs客失{round(a_def,1)})')
    if def_consistency == '一致强化':
        step0_signals.append(f'🛡️水位+防守同向→强化信号')
    elif def_trap:
        step0_signals.append(f'⚠️水位{water_dir}但防守{def_dir}→诱盘嫌疑')
    
    # 信号计数（HAD强信号计1票，V3.8防御信号计1票）
    all_dirs = [g0_dir, line_dir, water_dir]
    if had_strength >= 1:
        all_dirs.append(had_dir)
    if def_strength >= 1:
        all_dirs.append(def_dir)
    
    # ===== V3.9: 盘口偏差方向信号（攻防预期 vs 亚盘线位） =====
    ou_expected = h_att + a_def
    ou_deviation = (ou_line - ou_expected) if ou_line > 0 else 0
    ou_rule_dir = '中性'
    ou_rule_name = ''
    ou_rule_strength = 0
    # V3.9: 防守漏洞预检(供盘口偏差规律使用, 后续在Step7.10完善)
    _def_leak_home = any(r.get('conceded', 0) >= 4 for r in recent.get('home', []))
    _def_leak_away = any(r.get('conceded', 0) >= 4 for r in recent.get('away', []))
    _has_def_leak_early = _def_leak_home or _def_leak_away
    
    if abs(ou_deviation) >= 0.2:
        if -0.5 <= ou_deviation <= -0.2:
            # 轻度低开 → 大球倾向
            if ou_over >= 0.85:
                if h_att < 1.5 and a_att < 1.5:
                    ou_rule_dir = '中性'; ou_rule_name = f'低开{ou_deviation:+.1f}+双方攻弱→降权'
                elif h_def < 1.0 and h_att < 1.5:
                    ou_rule_dir = '中性'; ou_rule_name = f'低开{ou_deviation:+.1f}+主防强攻弱→降权'
                else:
                    ou_rule_dir = '大球'; ou_rule_strength = 1
                    ou_rule_name = f'低开{ou_deviation:+.1f}+中高水→大球91%'
            else:
                if h_att < 1.5 and a_att < 1.5:
                    ou_rule_dir = '中性'; ou_rule_name = f'低开{ou_deviation:+.1f}+双方攻弱→降权'
                elif h_def < 1.0 and h_att < 1.5:
                    ou_rule_dir = '中性'; ou_rule_name = f'低开{ou_deviation:+.1f}+主防强攻弱→降权'
                else:
                    ou_rule_dir = '大球'; ou_rule_strength = 1
                    ou_rule_name = f'低开{ou_deviation:+.1f}→大球88%'
        elif ou_deviation < -0.8:
            # 深度低开
            if ou_over >= 0.9:
                ou_rule_dir = '大球'; ou_rule_strength = 1
                ou_rule_name = f'深度低开{ou_deviation:+.1f}+高水→大球75%'
            else:
                ou_rule_dir = '小球'; ou_rule_strength = 1
                ou_rule_name = f'深度低开{ou_deviation:+.1f}+低水→小球67%'
        elif ou_deviation > 0.2:
            # 高开 → 小球倾向 (但防线漏洞→大球风险优先)
            if _has_def_leak_early:
                ou_rule_dir = '大球'; ou_rule_strength = 1
                ou_rule_name = f'高开{ou_deviation:+.1f}+防线漏洞→大球风险'
            elif h_att < 1.5 and a_att < 1.5:
                ou_rule_dir = '小球'; ou_rule_strength = 1
                ou_rule_name = f'高开{ou_deviation:+.1f}+双方攻弱→小球77%'
            elif h_def < 1.0:
                ou_rule_dir = '小球'; ou_rule_strength = 1
                ou_rule_name = f'高开{ou_deviation:+.1f}+主防强→小球77%'
            elif (h_att + a_def) < 2.5:
                ou_rule_dir = '小球'; ou_rule_strength = 1
                ou_rule_name = f'高开{ou_deviation:+.1f}+预期低→小球仅37%'
    
    if ou_rule_dir != '中性':
        all_dirs.append(ou_rule_dir)
    big_signals = sum(1 for d in all_dirs if d == '大球')
    small_signals = sum(1 for d in all_dirs if d == '小球')
    
    # V3.9: 盘口偏差规律信号(在方向判定后显示)
    if ou_rule_dir != '中性' and ou_rule_name:
        step0_signals.append(f'盘口→{ou_rule_name}')
    
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
    
    # V3.8: 防守一致性修正（水位+防守同向→升置信，矛盾→降置信）
    if def_consistency == '一致强化' and direction == water_dir:
        if direction_conf == '弱': direction_conf = '中(防守强化)'
        elif direction_conf == '中': direction_conf = '强(防守强化)'
        elif direction_conf == '强': direction_conf = '强(防守一致)'
    elif def_trap and direction == water_dir and direction_conf in ('弱', '中'):
        direction_conf = f'{direction_conf}(防守矛盾⚠️)'
    
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
    
    # V3.9: 盘口偏差 vs 方向矛盾检测
    if ou_rule_dir != '中性' and direction != '模糊' and ou_rule_dir != direction:
        step0_signals.append(f'⚠️盘口偏差→{ou_rule_dir}(与方向{direction}矛盾)')
        if direction_conf == '强':
            direction_conf = '中(盘口矛盾)'
        elif direction_conf == '中':
            direction_conf = '弱(盘口矛盾)'
        elif direction_conf == '弱':
            direction_conf = '弱(盘口矛盾⚠️)'
    elif ou_rule_dir != '中性' and direction != '模糊' and ou_rule_dir == direction:
        step0_signals.append(f'✅盘口偏差→{ou_rule_dir}(与方向一致)')
        if direction_conf in ('弱', '弱(矛盾留空)', '弱(盘口矛盾)'):
            direction_conf = '中(盘口支持)'
    
    step0 = {
        'combined_avg': combined_avg,
        'h_def': round(h_def, 2),
        'a_def': round(a_def, 2),
        'def_diff': round(def_diff, 2),
        'def_dir': def_dir,
        'def_consistency': def_consistency,
        'def_trap': def_trap,
        'ou_deviation': round(ou_deviation, 2),
        'ou_rule_dir': ou_rule_dir,
        'ou_rule_name': ou_rule_name,
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
    
    # ============== Step 4: 三维排除（V3.6完整版 = 文档4.7节） ==============
    # 三维 = 热度(系统排除信号) × 变化命中率(ch) × 赔率命中率(oh)
    # 决策矩阵（9格）→ 黄金法则覆盖 → 特殊规则(0球/5-7球) → 数据缺失降级
    exclusion_results = []
    for gk, gd in goal_data.items():
        g_num = int(gk.replace('球', ''))
        odds = gd['odds']
        ch = gd['change_hit']       # 变化命中率
        cs = gd['change_sample']    # 变化样本量
        pc = gd['change_pct']       # 变化幅度%
        oh = gd['odds_hit']         # 赔率命中率
        os = gd['odds_sample']      # 赔率样本量

        status = '保留'
        reason = ''

        # System exclusions
        exc_list = data.get('exclusion_list', []) or []
        sys_exclude = any(gk in str(e) for e in exc_list)

        # ===== 第一步: 分类命中率档位 =====
        # 变化命中率档位 (文档: 高≥25% / 中10-25% / 低<10%)
        if cs < 5:
            ch_tier = 'N/A'    # 样本不足，不参与判断(文档4.7节)
        elif ch >= 0.25:
            ch_tier = '高'
        elif ch >= 0.10:
            ch_tier = '中'
        else:
            ch_tier = '低'

        # 赔率命中率档位 (文档: 高≥20% / 中10-20% / 低<10%)
        if os < 10:
            oh_tier = 'N/A'    # 样本<10，标记不可用(文档数据完整性规则)
        elif oh >= 0.20:
            oh_tier = '高'
        elif oh >= 0.10:
            oh_tier = '中'
        else:
            oh_tier = '低'

        # ===== 第二步: 三维决策矩阵 (文档4.7节) =====
        # 仅在双维度都可用时应用矩阵
        if ch_tier != 'N/A' and oh_tier != 'N/A':
            # ── 9格矩阵 ──
            if oh_tier == '高' and ch_tier == '高':
                # 🔥大热+双高 → 有排除信号=排除，无=警惕造热
                if sys_exclude:
                    if pc < 0:
                        status = '排除'
                        reason = f'🔥大热必死:双高(变{ch:.0%}+赔{oh:.0%})+↓+系统排除'
                    else:
                        status = '排除'
                        reason = f'🔥大热+双高+系统排除→排除'
                else:
                    status = '⚠️警惕造热'
                    reason = f'双高(变{ch:.0%}+赔{oh:.0%})但无排除→警惕诱盘'

            elif oh_tier == '高' and ch_tier == '中':
                # 🔥热+变中 → 警惕造热
                status = '⚠️警惕造热'
                reason = f'赔高({oh:.0%})+变中({ch:.0%})→可能造热'

            elif oh_tier == '高' and ch_tier == '低':
                # ⚡矛盾 → 排除
                status = '排除'
                reason = f'⚡矛盾:赔高({oh:.0%})+变低({ch:.0%})→排除'

            elif oh_tier == '中' and ch_tier == '高':
                # ⭐变高共振 → 强保留
                status = '⭐变高共振'
                reason = f'变高({ch:.0%})+赔中({oh:.0%})→强保留'

            elif oh_tier == '中' and ch_tier == '中':
                # ✅保留
                status = '✅观察保留'
                reason = f'双中(变{ch:.0%}+赔{oh:.0%})→保留'

            elif oh_tier == '中' and ch_tier == '低':
                # → 弱排除
                status = '弱排除'
                reason = f'变低({ch:.0%})+赔中({oh:.0%})→弱排除'
                if sys_exclude or ch < 0.05:
                    status = '排除'
                    reason = f'变低({ch:.0%})<5%+赔中→排除'

            elif oh_tier == '低' and ch_tier == '高':
                # 🔄矛盾保留 → 保留
                status = '🔄矛盾保留'
                reason = f'变高({ch:.0%})+赔低({oh:.0%})→矛盾但保留(变尊)'

            elif oh_tier == '低' and ch_tier == '中':
                # ✅保留
                status = '✅观察保留'
                reason = f'双中偏低(变{ch:.0%}+赔{oh:.0%})→保留'

            elif oh_tier == '低' and ch_tier == '低':
                # 🚫 双低 → 排除
                status = '排除'
                reason = f'🚫双低(变{ch:.0%}+赔{oh:.0%})→强排除'

        elif ch_tier != 'N/A' and oh_tier == 'N/A':
            # 单维度: 变化命中率可用，赔率不可用
            if ch_tier == '高':
                status = '⭐变高共振'
                reason = f'变化高({ch:.0%},n={cs})→强保留(赔率数据不足)'
            elif ch_tier == '中':
                status = '✅保留'
                reason = f'变化中({ch:.0%},n={cs})→保留(赔率数据不足)'
            elif ch_tier == '低' and cs >= 10:
                if ch == 0:
                    status = '排除'
                    reason = f'变化0%({cs}场)→绝对排除'
                else:
                    status = '弱排除'
                    reason = f'变化低({ch:.0%},n={cs})→弱排除(赔率数据不足)'

        elif ch_tier == 'N/A' and oh_tier != 'N/A':
            # 单维度: 赔率命中率可用，变化不可用
            if oh_tier == '高':
                status = '⚠️警惕造热'
                reason = f'赔率高({oh:.0%},n={os})→警惕造热(变化数据不足)'
            elif oh_tier == '中':
                status = '✅保留'
                reason = f'赔率中({oh:.0%},n={os})→保留(变化数据不足)'
            elif oh_tier == '低':
                if oh == 0 and os >= 10:
                    status = '排除'
                    reason = f'赔率0%({os}场)→绝对排除'
                else:
                    status = '弱排除'
                    reason = f'赔率低({oh:.0%},n={os})→弱排除(变化数据不足)'

        else:
            # 双维度都不可用 → 回退到赔率位置+推离判断(文档数据完整性规则)
            status = '⚠️数据不足'
            reason = f'变n={cs}赔n={os}→双维度不可用'
            # 大球(5-7)在数据不足时保留，小球(0-2)看赔率极值
            if g_num >= 5 and ch_tier == 'N/A' and oh_tier == 'N/A':
                if oh == 0 and os >= 5:
                    status = '排除'
                    reason = f'赔率0%({os}场)+无变化数据→排除'
                elif oh > 0 and oh <= 0.05 and os >= 5:
                    status = '弱排除'
                    reason = f'赔率≤5%({oh:.0%})+无变化→弱排除(文档收紧阈值)'
                else:
                    status = '⚠️样本不足'
                    reason = f'无足够数据(n={max(cs,os)})→保守保留'

        # ===== 第三步: 黄金法则覆盖 (文档4.7节排除黄金法则) =====
        # 法则1: 变化命中率≥15%+样本≥10 → 🚫绝对不可排除
        if cs >= 10 and ch >= 0.15 and '排除' in status:
            status = '🛡️铁保留'
            reason = f'黄金法则1:变化{ch:.0%}≥15%(n={cs})→🚫绝对不可排除'

        # 法则2: 双高(都≥20%)+↓+系统排除 → 🔥大热必死
        if cs >= 5 and os >= 5 and ch >= 0.20 and oh >= 0.20 and pc < 0 and sys_exclude:
            if '排除' not in status:
                status = '排除'
                reason = f'🔥大热必死:双高(变{ch:.0%}+赔{oh:.0%})+↓+系统排除'

        # 法则3: 双低(都<10%)且都有样本(≥5) → 排除
        if cs >= 5 and os >= 5 and ch < 0.10 and oh < 0.10:
            if '排除' not in status:
                status = '排除'
                reason = f'🚫双低(变{ch:.0%}+赔{oh:.0%})→强排除'

        # 法则4: 任一命中率=0%+样本≥5 → 绝对排除
        if (cs >= 5 and ch == 0) or (os >= 5 and oh == 0):
            if '排除' not in status and '保留' in status:
                status = '排除'
                reason = f'⛔1率0%:变{ch:.0%}(n={cs})赔{oh:.0%}(n={os})→绝对排除'

        # ===== 第四步: 特殊规则 =====
        # 0球特殊: 赔率>18 or 高赔推离
        if g_num == 0:
            if odds > 18:
                status = '排除'
                reason = f'0球赔率极高({odds})→排除'
            elif pc > 8 and cs >= 5:
                if '排除' not in status:
                    status = '排除'
                    reason = f'0球↑推离{pc:.0f}%(n={cs})'

        # 5-7球特殊: 文档收紧阈值
        if g_num >= 5 and ch_tier == 'N/A' and oh_tier == 'N/A' and '排除' not in status:
            if cs < 3 and os < 3:
                status = '排除'
                reason = f'大球({g_num}球)双维度无数据→保守排除'

        # 1球特殊: 系统排除+高赔
        if g_num == 1 and sys_exclude and odds > 4.5 and '排除' not in status:
            status = '排除'
            reason = '系统排除+高赔'

        # ===== 最终fallback: 无数据全部保留 =====
        if '排除' not in status and ch_tier == 'N/A' and oh_tier == 'N/A':
            if g_num <= 4:
                status = '保留'
                reason = f'无变化数据(n={max(cs,os)})→保守保留'

        exclusion_results.append({
            'goal': gk,
            'odds': odds,
            'change_pct': pc,
            'change_hit': ch,
            'change_sample': cs,
            'odds_hit': oh,
            'odds_sample': os,
            'status': status,
            'reason': reason,
        })

    kept = [e for e in exclusion_results if '排除' not in e['status']]
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
    if h_def < 1.0 and a_att < 1.0:
        score_analysis.append('🟢主铁壁+客攻弱→小球78%(9场)→强小球信号')
    elif a_def < 1.0 and h_att >= 2.0:
        score_analysis.append('🔴客铁壁+主攻强→大球87%(15场)→强大球信号')

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
        
        # V3.8: 按合理性+赔率排序(🔥>✅>⚠️, 同档内赔率低优先)
        def _score_sort_key(s):
            cap = s.get('h_capable', '⚠️')
            tier = 0 if '🔥' in cap else (1 if '✅' in cap else 2)
            odds = s.get('score_odds', 999) or 999
            if isinstance(odds, str):
                try: odds = float(odds)
                except: odds = 999
            return (tier, odds)
        plausible.sort(key=_score_sort_key)
        
        score_candidates.append({
            'total_goals': total,
            'scores': plausible,
        })
    
    # If all scores excluded, fallback
    if not candidate_goals:
        candidate_goals = [1, 2, 3]  # 绝对兜底
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
    
    # ============== V3.8: 最终进球数推荐（在profile_items完成后填充） ==============
    final_goal_pick = {'single': None, 'double': [], 'reason': [], 'all_kept': []}
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
    # 排除7球: 双方攻<1.5 + 7球>3.5 → 0%命中(94场)
    if h_att < 1.5 and a_att < 1.5 and g7_val > 3.5:
        profile_rules.append('🚫排除7球:双方攻弱+7球>3.5→0%(94场)')
    # 排除7球: 主攻<1.5 + 客防<1.0 + 7球>3.0 → 0%命中(41场)
    if h_att < 1.5 and a_def < 1.0 and g7_val > 3.0:
        profile_rules.append('🚫排除7球:主攻弱+客防强+7球>3→0%(41场)')
    # 排除5球: 双方攻<1.0 + 5球>4.0 → 0%命中(9场)
    if h_att < 1.0 and a_att < 1.0 and g5_val > 4.0:
        profile_rules.append('🚫排除5球:双方攻极弱+5球>4→0%(9场)')
    # 扩大4球排除: 4球>4.0 + 主防<1.0 → 4球率11.6%(69场)
    if g4_val > 4.0 and h_def < 1.0:
        profile_rules.append('🚫排除4球扩大:4球>4+主防强→仅11.6%(69场)')
    if h_def >= 2.0 and a_def >= 2.0:
        profile_rules.append('🔥双方漏勺→大球91%/3-4球55%/0-1球=0%')
    elif h_att >= 2.0 and a_def >= 2.0:
        profile_rules.append('🔥主攻vs客漏→大球91%/3球41%')
    if h_att >= 2.0 and a_att >= 2.0:
        profile_rules.append('🔥双方攻击火爆→大球80%/3球40%')
    # ============== V3.8: 高命中比分实时信号 ==============
    # 0:0信号: 庄家推离0球(高赔+大球线+升水) → 反向出0:0
    g0_change = tc.get('0球', {}).get('change_pct', 0) if tc else 0
    if g0_val > 14 and ou_line > 2.5 and g0_change > 1 and h_def >= 1.0 and a_def >= 1.0:
        profile_rules.append('🎯0:0强:0球>14+大球线+升水+双方防≥1→庄家全面推离反向')
    elif g0_val > 14 and ou_line > 2.5:
        profile_rules.append('👁️0:0候选:0球>14+大球线→庄家看大球,警惕0:0')
    # 1:1信号: 主防好+近况温和+庄家不极端看大球
    g2_change = tc.get('2球', {}).get('change_pct', 0) if tc else 0
    if h_def < 1.0 and 10 <= g0_val <= 18 and combined_avg < 3.5 and h_att >= 0.8 and a_att >= 0.8:
        profile_rules.append('👁️1:1候选:主铁壁(失'+str(round(h_def,1))+')+0球适中+近况温和→关注1:1')
    
    if h_def < 1.0 and a_def < 1.0:
        profile_rules.append('🛡️双方铁壁→小球58%/2球50%')
    if h_att < 1.5 and a_att < 1.5 and h_def < 1.5 and a_def < 1.5:
        if has_def_leak:
            profile_rules.append('⚠️双方沉闷但防守有漏洞→小球不可靠(65%大球)')
        else:
            profile_rules.append('😴双方沉闷→小球46%/2球43%')
    try: hcap = int(hhad_handicap)
    except: hcap = 0
    is_home_give = hcap < 0   # 主让球 (让球=-1)
    is_home_recv = hcap > 0   # 主受让 (让球=+1)
    if a_att >= 2.0 and is_home_recv:
        profile_rules.append('🛡️客火爆+主受让→主队不败81%')
    
    # ============== V3.8: 让球盘系统推荐 (120场回测) ==============
    # 计算主/客近5场胜场数
    h_win_count = sum(1 for r in recent.get('home', []) if r.get('result', '') in ('home', 'win'))
    a_win_count = sum(1 for r in recent.get('away', []) if r.get('result', '') in ('home', 'win'))
    hhad_lose_odds = _safe_float(hhad.get('让负', 0))
    hhad_win_odds = _safe_float(hhad.get('让胜', 0))
    hhad_draw_odds = _safe_float(hhad.get('让平', 0))
    
    # 数据: 主让(-1)85场 让胜75%/让平19%/让负6% | 主受让(+1)35场 让胜17%/让平29%/让负54%
    
    # P0 排除层 (命中率≤10% → 直接排除)
    # 注1: "主让+让负<2.0"已由 _analyze_hhad_lose_low() 决策树(S/A/B/C/D/E)完全接管
    # 注2: "让胜≥3.0→排除让负"已由 _analyze_hhad_low_draw() Step4覆盖(让胜>3.0→让负53.8%), 旧数据(0%/8%)与新数据矛盾, 删除

    # 调用 _analyze_hhad_lose_low() 决策树（主让+让负<2.0）
    _hhad_lose_low_result = None
    try:
        from sporttery_web import _analyze_hhad_lose_low
        home_avg = sum(r['total'] for r in recent.get('home', [])) / max(len(recent.get('home', [])), 1) if recent.get('home') else None
        away_avg = sum(r['total'] for r in recent.get('away', [])) / max(len(recent.get('away', [])), 1) if recent.get('away') else None
        recent_form = {'home_avg': home_avg, 'away_avg': away_avg, 'combined_avg': combined_avg}
        _hhad_lose_low_result = _analyze_hhad_lose_low(hhad, recent_form)
    except ImportError:
        pass

    if _hhad_lose_low_result and _hhad_lose_low_result.get('active'):
        tier = _hhad_lose_low_result.get('tier', '?')
        pick = _hhad_lose_low_result.get('pick', '')
        confidence = _hhad_lose_low_result.get('confidence', 0)
        reasons = _hhad_lose_low_result.get('reasons', [])
        # 将决策树结果作为ACTIVE画像规律写入
        for reason in reasons:
            profile_rules.append(f'🔍决策树{tier}级: {reason}')
        # 标记决策树结论用于active判定
        if pick == '排除让负':
            profile_rules.append(f'🚫决策树→排除让负({tier}级,{confidence}%)')

    if 2.0 <= hhad_lose_odds < 3.0:
        profile_rules.append('🚫排除让平:让负2.0-3.0→让平仅10%(40场)')
    if 2.0 <= hhad_win_odds < 3.0:
        profile_rules.append('🚫排除让平:让胜2.0-3.0→让平仅10%(39场)')
    if hhad_lose_odds >= 5.0:
        if is_home_give:
            profile_rules.append(f'🚫排除让胜:主让+让负{round(hhad_lose_odds,2)}≥5→让胜仅12%(8场)')
        else:
            profile_rules.append(f'👁️让负{round(hhad_lose_odds,2)}极高→客大胜概率极低,让胜可能性增大')
    
    # P1 强推层 (命中率≥70% → 直接推荐)
    # 让胜规律 (主让方向, 让胜赔率<4.0才适用)
    if is_home_give and hhad_win_odds < 4.0:
        profile_rules.append('🔥主让球→让胜75%(85场)')
        if 2.5 <= hhad_draw_odds < 3.3 and h_att > a_att:
            profile_rules.append(f'🔥主让+让平{round(hhad_draw_odds,2)}+主攻>客攻→让胜92%(12场)')
        if 2.0 <= hhad_lose_odds < 3.0 and h_att > a_att:
            profile_rules.append(f'🔥主让+让负{round(hhad_lose_odds,2)}+主攻>客攻→让胜85%(20场)')
        if 2.0 <= hhad_lose_odds < 3.0:
            profile_rules.append(f'🔥主让+让负{round(hhad_lose_odds,2)}→让胜80%(30场)')
        if 4.0 <= hhad_draw_odds < 5.0:
            profile_rules.append(f'🔥主让+让平{round(hhad_draw_odds,2)}→让胜80%(20场)')
    
    # 让负规律 (主受让方向)
    if is_home_recv and 2.0 <= hhad_win_odds < 3.0:
        profile_rules.append(f'🔥主受让+让胜{round(hhad_win_odds,2)}→让负69%(13场)')
    # 让负极高 → 反向推荐让胜 (主受让时客队大胜概率极低)
    if is_home_recv and hhad_lose_odds >= 5.0:
        profile_rules.append(f'🔥主受让+让负{round(hhad_lose_odds,2)}极高→让胜75%(8场仅1翻)')
    
    # 让平: 无≥65%规律, 仅当让胜+让负都被排除时推荐
    
    # 让胜≥4.0 高赔规则 (保持原有)
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
        if h_att < 1.5 and hhad_lose_odds < 5.0:
            profile_rules.append('🔥让负≥4.0且主攻弱→让胜80%(20场)')
        elif hhad_lose_odds >= 5.0:
            if is_home_give:
                profile_rules.append('🚫让负'+str(round(hhad_lose_odds,2))+'≥5→让胜仅12%(8场)')
            # 主受让时已在P0/P1处理
        else:
            profile_rules.append('🚫让负'+str(round(hhad_lose_odds,2))+'≥4.0→让负仅9%,选让胜')
    
    # V3.8: 矛盾检测 (P0排除X + P1推荐X → X大概率打不出)
    p0_win = any('🚫排除让胜' in p or '🚫让胜' in p for p in profile_rules)
    p0_lose = any('🚫排除让负' in p or '🚫让负' in p for p in profile_rules)
    p1_win = any('🔥' in p and '→让胜' in p for p in profile_rules)
    p1_lose = any('🔥' in p and '→让负' in p for p in profile_rules)
    if p0_win and p1_win:
        profile_rules.append('⚠️矛盾:推荐让胜但P0排除→仅20%命中(5场仅1中),选让平/让负')
    if p0_lose and p1_lose:
        profile_rules.append('⚠️矛盾:推荐让负但P0排除→仅50%命中,观望')
    # 跨框架矛盾: 让球盘推荐 vs 攻防画像
    has_home_unbeaten = any('主队不败' in p for p in profile_rules)
    # 陷阱信号直接判断(在profile_rules之前,因为陷阱规则在后面)
    has_trap_win = (1.50 <= hhad_win_odds <= 1.70 and h_win_count >= 3)
    if p1_lose and has_home_unbeaten:
        profile_rules.append('⚠️矛盾:让球盘推荐让负,但攻防画像提示主队不败81%→观望')
    if p1_win and has_trap_win:
        profile_rules.append('⚠️矛盾:推荐让胜但触发陷阱信号(让胜低赔+主3+胜)→让胜仅30-50%,观望')
    
    # 特殊: 让胜1.50-1.70
    if 1.50 <= hhad_win_odds <= 1.70:
        if 1 <= h_win_count <= 2:
            profile_rules.append('🔥让胜'+str(round(hhad_win_odds,2))+'且主1-2胜→让胜89%+')
        elif h_win_count >= 3:
            profile_rules.append('⚠️让胜'+str(round(hhad_win_odds,2))+'但主3+胜→陷阱!让胜仅30-50%')
    
    # 特殊: 客火爆+主受让
    if a_att >= 2.0 and is_home_recv:
        profile_rules.append('🛡️客火爆+主受让→主队不败81%')
    
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
    
    # ============== 标注画像规律: 已生效 vs 仅参考 ==============
    # 排除规则: 检查对应球数是否在三维排除中真正被排除
    excluded_goals = {e['goal'] for e in excluded if '排除' in e['status']}
    profile_items = []
    for rule in profile_rules:
        active = False
        # 检查 🚫排除X球 规则是否在三维排除中被执行
        import re
        m = re.search(r'排除(\d+)球', rule)
        if m:
            goal_key = m.group(1) + '球'
            if goal_key in excluded_goals:
                active = True
        # 🔥让胜/让负推荐 → 已被handicap_conclusion引用
        if ('→让胜' in rule or '→让负' in rule) and '🚫' not in rule:
            if ('→让胜' in rule and (p1_win or (not p0_win))) or \
               ('→让负' in rule and (p1_lose or (not p0_lose))):
                active = True
        # 盘口偏差方向规律（高开/低开→大小球）: 仅参考
        profile_items.append({'text': rule, 'active': active})

    # ===== V3.8: 填充最终进球数推荐（在profile_items完成后） =====
    if kept:
        kept_goals = [int(e['goal'].replace('球', '')) for e in kept]
        final_goal_pick['all_kept'] = kept_goals
        
        # ACTIVE画像排除规则
        profile_excluded = set()
        for item in profile_items:
            if item.get('active') and '排除' in item.get('text', ''):
                m = re.search(r'排除(\d+)球', item['text'])
                if m:
                    g = int(m.group(1))
                    if g in kept_goals:
                        profile_excluded.add(g)
                        final_goal_pick['reason'].append(f'画像规律→排除{g}球')
        
        # 候选: kept中排除画像排除的
        cand = [g for g in kept_goals if g not in profile_excluded]
        if not cand:
            cand = kept_goals
        
        # 按change_hit排序(警惕造热状态降权)
        goal_scores = []
        for e in kept:
            g = int(e['goal'].replace('球', ''))
            if g in cand:
                wt = 0.5 if '警惕造热' in e['status'] else 1.0
                # 样本门槛: n<5不计入单选竞争
                valid_single = e.get('change_sample', 0) >= 5
                goal_scores.append((g, e['change_hit'] * wt, e['status'], valid_single, e.get('change_sample',0)))
        goal_scores.sort(key=lambda x: -x[1])
        
        # 方向约束: 单选必须匹配Step0方向
        dir_filtered = [gs for gs in goal_scores if 
            (direction == '大球' and gs[0] >= 3 and gs[3]) or
            (direction == '小球' and gs[0] <= 2 and gs[3]) or
            (direction == '模糊' and gs[3])]
        
        if not dir_filtered:
            # 无合格单选 → 降级：只要n≥5不分方向
            dir_filtered = [gs for gs in goal_scores if gs[3]]
        if not dir_filtered:
            # 再降级：全部候选
            dir_filtered = goal_scores
        
        # 单选 = 方向内最高分
        sp = dir_filtered[0][0]
        final_goal_pick['single'] = sp
        final_goal_pick['reason'].append(f'首选{sp}球(变{int(dir_filtered[0][1]*100)}%,n={dir_filtered[0][4]})')
        
        # V3.8: 方向冲突检测（Step0方向 vs 单选进球是否跨2.5边界）
        is_big = sp >= 3
        dir_conflict = (direction == '小球' and is_big) or (direction == '大球' and not is_big)
        final_goal_pick['conflict'] = dir_conflict
        if dir_conflict:
            # 检查是否方向内所有进球都被排除
            small_kept = [g for g in kept_goals if g <= 2]
            big_kept = [g for g in kept_goals if g >= 3]
            if direction == '小球' and not small_kept:
                final_goal_pick['reason'].append('⚠️单侧空空: 方向小球但0/1/2球全被排除, 只剩大球→方向存疑')
            elif direction == '大球' and not big_kept:
                final_goal_pick['reason'].append('⚠️单侧空空: 方向大球但3+球全被排除, 只剩小球→方向存疑')
            else:
                final_goal_pick['reason'].append(f'⚠️方向冲突: Step0={direction}但推荐{sp}球(反方向)→谨慎')
        
        # 双选 = 单选 + 次优（允许跨方向但优先同方向）
        if len(dir_filtered) >= 2:
            g2 = dir_filtered[1][0]
            final_goal_pick['double'] = [sp, g2]
            final_goal_pick['reason'].append(f'双选{sp}球+{g2}球')
        elif len(goal_scores) >= 2:
            # 方向内只有1个，从全候选取第二个
            remaining = [gs for gs in goal_scores if gs[0] != sp]
            if remaining:
                g2 = remaining[0][0]
                final_goal_pick['double'] = [sp, g2]
                final_goal_pick['reason'].append(f'双选{sp}球+{g2}球(跨方向取次优)')
            else:
                final_goal_pick['double'] = [sp]
        else:
            final_goal_pick['double'] = [sp]

    # ===== V3.8: 观望建议 =====
    skip_direction = final_goal_pick.get('conflict', False) or \
                     direction_conf.startswith('弱') or \
                     direction == '模糊'
    skip_3ball = (final_goal_pick.get('single') == 3)
    # V3.8 新增: 防守诱盘 → 强制观望 (周五001/010反例)
    def_trap_signal = step0.get('def_trap', False)
    # V3.8 新增: 低近况+高0球 → 信号矛盾, 观望
    low_form_high_g0 = (combined_avg < 2.5 and g0_val > 12)
    # V3.9 新增: 盘口偏差与方向矛盾 + 有诱盘信号 → 强制观望
    ou_dir_contra = (ou_rule_dir != '中性' and direction != '模糊' and ou_rule_dir != direction)
    # V3.8 新增: 单选6球 → 历史0%命中, 观望
    skip_6ball = (final_goal_pick.get('single') == 6)
    
    final_goal_pick['skip_reason'] = []
    if skip_direction:
        reason_parts = []
        if final_goal_pick.get('conflict'): reason_parts.append('方向冲突')
        if direction_conf.startswith('弱'): reason_parts.append('方向弱信号')
        if direction == '模糊': reason_parts.append('方向模糊')
        sep = '+'
        final_goal_pick['skip_reason'].append(f'💡建议观望: {sep.join(reason_parts)}(历史ROI -4%)')
    if def_trap_signal:
        final_goal_pick['skip_reason'].append('💡建议观望: 防守诱盘信号(水位+防守反向, 回测ROI -9%)')
    if low_form_high_g0:
        final_goal_pick['skip_reason'].append(f'💡建议观望: 近况{combined_avg:.1f}<2.5+0球{g0_val}偏高→信号矛盾')
    if skip_3ball:
        final_goal_pick['skip_reason'].append('💡建议观望: 单选3球历史ROI -19%(517场回测)')
    if skip_6ball:
        final_goal_pick['skip_reason'].append('💡建议观望: 单选6球历史ROI 0%(13场回测)')
    if ou_dir_contra and def_trap_signal:
        final_goal_pick['skip_reason'].append(f'💡建议观望: 盘口偏差+防守诱盘双矛盾(周五010/012反例)')
    elif ou_dir_contra and direction_conf.startswith('弱'):
        final_goal_pick['skip_reason'].append(f'💡建议观望: 盘口偏差→{ou_rule_dir}与方向{direction}矛盾, 方向弱')
    # V3.9: 极端0球+水位防守反向 → 信号内部矛盾 (周五004反例)
    if g0_val >= 19 and def_consistency == '一致强化' and def_dir != direction:
        final_goal_pick['skip_reason'].append(f'💡建议观望: 0球={g0_val}极端大球+水位防守一致{def_dir}→矛盾')

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
    
    # ===== V3.8: 根据让球盘结论过滤比分 =====
    hhad_pick = None
    # 不矛盾时取P1推荐方向
    has_contra = (p0_win and p1_win) or (p0_lose and p1_lose) or (p1_lose and has_home_unbeaten) or (p1_win and has_trap_win)
    if not has_contra:
        if p1_win and not p0_win:
            hhad_pick = '让胜'
        elif p1_lose and not p0_lose:
            hhad_pick = '让负'
    
    # 过滤比分: 只保留让球盘推荐方向的比分
    # V3.8 fix: 用实际比分差 vs 让球数判断, 而非仅凭tag标签
    abs_handicap = abs(hcap_number) if 'hcap_number' in dir() else 0
    try: abs_handicap = abs(int(hhad_handicap))
    except: abs_handicap = 0
    
    filtered_scores = []
    for sc_group in score_candidates:
        for s in sc_group['scores']:
            tag = s['tag']
            score_parts = s['score'].split('-')
            try:
                s_h = int(score_parts[0])
                s_a = int(score_parts[1])
            except:
                s_h = s_a = 0
            
            keep = True
            if hhad_pick == '让胜':
                # 让胜: 主队净胜球 > 让球绝对值
                keep = (s_h - s_a) > abs_handicap
            elif hhad_pick == '让负':
                # 让负: 客队净胜球 > 让球绝对值 (主受让时) 或 主队+让球仍输
                if abs_handicap > 0:
                    keep = (s_a - s_h) > abs_handicap
            elif hhad_pick == '让平':
                keep = (s_h - s_a) == abs_handicap
            if keep:
                filtered_scores.append({
                    'goals': sc_group['total_goals'],
                    'score': s['score'],
                    'tag': tag
                })
    # 过滤后首选比分
    filtered_top = filtered_scores[0]['score'] if filtered_scores else top_score
    
    # ===== V3.8: 单选比分投注推荐 =====
    score_bet = None
    # 观望时不推荐比分
    skip_reasons = final_goal_pick.get('skip_reason', []) if isinstance(final_goal_pick, dict) else []
    if filtered_scores and candidate_goals and not skip_reasons:
        # 取单选进球数的第一个比分（已排序: 让胜过滤后/无推荐🔥+低赔排序）
        fg = final_goal_pick.get('single') if isinstance(final_goal_pick, dict) else None
        if fg:
            match_scores = [s for s in filtered_scores if s['goals'] == fg]
            if match_scores:
                best = match_scores[0]
                strategy = '让胜推荐' if hhad_pick == '让胜' else ('让负推荐' if hhad_pick == '让负' else '无推荐博冷')
                # 让负7场全亏，不推荐(样本太小且无一命中)
                if strategy == '让负推荐':
                    strategy = None
                if strategy:
                    # 获取赔率
                    parts = best['score'].split('-')
                    so_key = best['score'].replace('-', ':')
                    so_key_fmt = f'{int(parts[0]):02d}:{int(parts[1]):02d}'
                    odds_val = _safe_float(score_odds.get(so_key, score_odds.get(so_key_fmt, 0)))
                    score_bet = {
                        'score': best['score'],
                        'goals': fg,
                        'tag': best.get('tag', ''),
                        'strategy': strategy,
                        'odds': round(odds_val, 1) if odds_val < 900 else None,
                    }
    
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
            'kept': [{
                'goal': e['goal'], 
                'hit': f"{e['change_hit']:.0%}" if e['change_hit'] > 0 else '-',
                'status': e['status'],
                'detail': f'变{e["change_hit"]:.0%}(n={e["change_sample"]}) 赔{e["odds_hit"]:.0%}(n={e["odds_sample"]})' if (e.get('change_sample',0)+e.get('odds_sample',0)) > 0 else '无变化数据',
            } for e in kept],
            'excluded': [{
                'goal': e['goal'], 
                'reason': e['reason'],
                'detail': f'变{e["change_hit"]:.0%}(n={e["change_sample"]}) 赔{e["odds_hit"]:.0%}(n={e["odds_sample"]})' if (e.get('change_sample',0)+e.get('odds_sample',0)) > 0 else '无变化数据',
            } for e in excluded if '排除' in e['status']],
        },
        'new_rules': {
            'anchor': anchor_rule,
            'attack_threshold': f'主攻{h_att:.1f}(\'≥1.5\'→{att_threshold})',
            'attack_vs_defense': f'主攻{h_att:.1f}+客失{a_def:.1f}',
            'profiles': profile_items,
        },
        'handicap_conclusion': {
            'p1_win': p1_win, 'p1_lose': p1_lose, 'p1_draw': False,
            'p0_win': p0_win, 'p0_lose': p0_lose, 'p0_draw': False,
            'contra': (p0_win and p1_win) or (p0_lose and p1_lose) or (p1_lose and has_home_unbeaten) or (p1_win and has_trap_win),
        },
        'score_candidates': score_candidates,
        'score_analysis': score_analysis,
        'final_review': final_review,
        'review_warnings': review_warnings,
        'final_goal_pick': final_goal_pick,
        'score_bet': score_bet,
        'recommended': {
            'direction': direction,
            'confidence': direction_conf,
            'goals': candidate_goals[:3],
            'top_score': top_score,
            'hhad_pick': hhad_pick,
            'filtered_scores': filtered_scores[:6],
        } if candidate_goals else None,
    }
# V3.6 FIX v2 - Tue May  5 17:00:32     2026
