#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI推理Prompt生成器
读取推理流水框架.md + 比赛数据，生成供AI推理的Prompt
"""
from flask import Blueprint, jsonify, request
import json
import os

bp = Blueprint('ai_reasoning', __name__)

# 框架文档路径
FRAMEWORK_FILE = '推理流水框架.md'
# 比赛数据目录
DATA_DIR = 'sporttery_data'


DATA_DIR = 'sporttery_data'


def _get_stake_by_tier(rule_name):
    """凯利公式的硬编码平替：基于历史ROI甜区进行资金分级（2026-05-22）"""
    tier_1_heavy = ['R0', 'S7', 'S3', 'S2', 'X6', 'S9', 'H9']
    tier_2_medium = ['X3', 'X5', 'X4', 'X2', 'G6', 'H5', 'H3', 'H2']
    tier_3_light = ['G7', 'G5', 'F', 'H1', 'R1']
    if rule_name in tier_1_heavy: return 40
    elif rule_name in tier_2_medium: return 20
    return 10

def _trace_log(level, msg):
    """拦截日志跟踪（2026-05-22）：所有风控拦截统一打LOG，便于审计是否误伤"""
    import datetime
    ts = datetime.datetime.now().strftime('%m-%d %H:%M')
    import sys
    print(f'[{level}][{ts}] {msg}', file=sys.stderr, flush=True)

def _check_d1(analysis, data, v36_dir, g0, so):
    """D1条件检查: 方向冲突1:1信号"""
    try:
        fgp = analysis.get('final_goal_pick', {})
        d1_conflict = fgp.get('conflict', False)
        if not (v36_dir == '大球' and d1_conflict):
            return False
        exc_dict = analysis.get('exclusion', {})
        d1_excl = exc_dict.get('excluded', [])
        d1_excl_goals = [int(e['goal'].replace('球', '')) for e in d1_excl] if d1_excl else []
        if not (5 in d1_excl_goals and 6 in d1_excl_goals and 7 in d1_excl_goals):
            return False
        if g0 is None or g0 > 23:
            return False
        d1_form = analysis.get('step0', {}).get('combined_avg', 0)
        if not (2.5 <= d1_form <= 3.6):
            return False
        # 历史高命中率比分第一位是否为1:1
        # 优先用前端显示源(get_score_recommendations_for_match), v36内部作fallback
        display_ok = False
        try:
            from sporttery_web import get_score_recommendations_for_match
            recs = get_score_recommendations_for_match(so)
            display_top = recs[0]['score'] if recs else '?'
            display_ok = (display_top in ('1:1', '1-1'))
        except:
            pass
        if not display_ok:
            # fallback: v36内部score_candidates
            sc_list_fb = analysis.get('score_candidates', [])
            d1_top_fb = sc_list_fb[0]['scores'][0].get('score', '?') if sc_list_fb and sc_list_fb[0].get('scores') else '?'
            if d1_top_fb not in ('1-1', '1:1'):
                return False
        return True
    except:
        return False

def _build_d1_bet(so):
    """构建D1比分投注: 1:1 @ 10元"""
    import re as _re
    s11_odds = 7.0  # fallback
    if so:
        for sk, sv in so.items():
            try:
                p = _re.split('[:-]', sk)
                if int(p[0]) == 1 and int(p[1]) == 1:
                    s11_odds = float(sv)
                    break
            except:
                pass
    return {'score': '1:1', 'odds': round(s11_odds, 1), 'stake': 10, 'tag': 'D1方向冲突1:1'}

def _check_s9(data):
    """S9: 0球13-16+3球3.2-3.4+近况<2.5+主让1球 → 大球双投40元
    回测32场: 3球41%+4球16%+5球16% ROI+35.5% (2026-06-19)"""
    try:
        tg = data.get('total_goals', {})
        o0 = float(tg.get('0球', 0))
        o3 = float(tg.get('3球', 0))
        if not (13 <= o0 <= 16): return None
        if not (3.2 <= o3 <= 3.4): return None
        
        # 近况 < 2.5 (双方近5场场均总进球)
        preview = data.get('preview', {})
        recent = preview.get('recent', {})
        home_ml = recent.get('home', {}).get('matchList', []) or []
        away_ml = recent.get('away', {}).get('matchList', []) or []
        
        def _avg_goals(ml):
            gs = []
            for m in ml[:5]:
                try:
                    gs.append(float(str(m.get('homeTeamFullCourtGoalCnt', 0))) + float(str(m.get('awayTeamFullCourtGoalCnt', 0))))
                except: pass
            return sum(gs) / len(gs) if gs else 2.0  # 缺失数据用默认2.0
        
        ha = _avg_goals(home_ml)
        aa = _avg_goals(away_ml)
        if (ha + aa) / 2 >= 2.5: return None
        
        # 主让1球
        hhad = data.get('hhad', {})
        if float(hhad.get('让球', '0') or '0') != -1: return None
        
        o4 = float(tg.get('4球', 0))
        o5 = float(tg.get('5球', 0))
        
        if o5 < 8.5:
            second_goal = 5
            second_odds = o5
            pick_explain = 'o5<8.5→5球'
        else:
            second_goal = 4
            second_odds = o4
            pick_explain = 'o5>=8.5→4球'
        
        mi = data.get('match_info', {}) or {}
        mn = mi.get('match_num_str', '') if isinstance(mi, dict) else ''
        ht = mi.get('home_team', '?') if isinstance(mi, dict) else '?'
        at = mi.get('away_team', '?') if isinstance(mi, dict) else '?'
        _trace_log('S9', f'{mn} {ht}vs{at} o0={o0:.1f} o3={o3:.1f} form={((ha+aa)/2):.1f} {pick_explain}')
        
        return {
            'goals': [3, second_goal],
            'odds': {3: o3, second_goal: second_odds},
            'pick_explain': pick_explain,
        }
    except:
        return None

def _check_t_series(data):
    """T系列前置检查: 让胜降>10% + display=1:1 + rs/hw<1.6
    返回 (hw, rs, is_handicap_home_give, display_ok) 或 None"""
    try:
        hhad = data.get('hhad', {})
        rs = float(hhad.get('让胜', 0) or 0)
        rl = float(hhad.get('让负', 0) or 0)
        if rs <= 0 or rs >= 10:
            return None
        had = data.get('had', {})
        hw = float(had.get('胜', 0) or 0)
        if hw <= 0:
            return None
        if rs / hw >= 1.6:
            return None
        hhad_chg = data.get('hhad_change', {})
        rs_chg = hhad_chg.get('让胜', {})
        rs_pct = float(rs_chg.get('change_pct', 0)) if isinstance(rs_chg, dict) else 0
        if rs_pct > -10:
            return None
        so = data.get('score_odds', {})
        if not so:
            return None
        from sporttery_web import get_score_recommendations_for_match
        recs = get_score_recommendations_for_match(so)
        if not recs or recs[0]['score'] != '1:1':
            return None
        # 让球方向: rl < rs → 主让-1
        is_give = (rl < rs)
        return (hw, rs, is_give)
    except:
        return None

def _build_t_bet(t_rule, so):
    """构建T系列比分投注"""
    import re as _re2
    if t_rule == 'T1':
        odds = 7.0
        if so:
            for sk, sv in so.items():
                try:
                    p = _re2.split('[:-]', sk)
                    if int(p[0]) == 1 and int(p[1]) == 1:
                        odds = float(sv); break
                except: pass
        return {'score': '1:1', 'odds': round(odds, 1), 'stake': 10, 'tag': 'T1让胜陷阱1:1'}
    elif t_rule == 'T2':
        odds = 10.0
        if so:
            for sk, sv in so.items():
                try:
                    p = _re2.split('[:-]', sk)
                    if int(p[0]) == 0 and int(p[1]) == 2:
                        odds = float(sv); break
                except: pass
        return {'score': '0:2', 'odds': round(odds, 1), 'stake': 10, 'tag': 'T2让胜陷阱0:2'}
    elif t_rule == 'T3':
        odds00 = 10.0; odds22 = 15.0
        if so:
            for sk, sv in so.items():
                try:
                    p = _re2.split('[:-]', sk)
                    if int(p[0]) == 0 and int(p[1]) == 0:
                        odds00 = float(sv)
                    if int(p[0]) == 2 and int(p[1]) == 2:
                        odds22 = float(sv)
                except: pass
        return [
            {'score': '0:0', 'odds': round(odds00, 1), 'stake': 10, 'tag': 'T3让胜陷阱平局'},
            {'score': '2:2', 'odds': round(odds22, 1), 'stake': 10, 'tag': 'T3让胜陷阱平局'},
        ]
    return None

def _check_b1(data):
    """B1前置检查: 让胜降>10% + display=3:0 + rs/hw<1.6 + hw<1.5
    返回 hw 或 None"""
    try:
        hhad = data.get('hhad', {})
        rs = float(hhad.get('让胜', 0) or 0)
        if rs <= 0 or rs >= 10: return None
        had = data.get('had', {})
        hw = float(had.get('胜', 0) or 0)
        if hw <= 0 or hw >= 1.5: return None
        if rs / hw >= 1.6: return None
        hhad_chg = data.get('hhad_change', {})
        rs_chg = hhad_chg.get('让胜', {})
        rs_pct = float(rs_chg.get('change_pct', 0)) if isinstance(rs_chg, dict) else 0
        if rs_pct > -10: return None
        so = data.get('score_odds', {})
        if not so: return None
        from sporttery_web import get_score_recommendations_for_match
        recs = get_score_recommendations_for_match(so)
        if not recs or recs[0]['score'] != '3:0': return None
        return hw
    except:
        return None

def _build_b1_bet(so):
    """B1双选: 3:1+4:1 各10元"""
    import re as _re3
    odds31 = 10.0; odds41 = 20.0
    if so:
        for sk, sv in so.items():
            try:
                p = _re3.split('[:-]', sk)
                a, b = int(p[0]), int(p[1])
                if a == 3 and b == 1: odds31 = float(sv)
                if a == 4 and b == 1: odds41 = float(sv)
            except: pass
    return [
        {'score': '3:1', 'odds': round(odds31, 1), 'stake': 10, 'tag': 'B1让胜真信'},
        {'score': '4:1', 'odds': round(odds41, 1), 'stake': 10, 'tag': 'B1让胜真信'},
    ]

def _build_t_summary(t_rule):
    """T系列summary文本"""
    if t_rule == 'T1': return '1:1比分10元'
    elif t_rule == 'T2': return '0:2比分10元'
    elif t_rule == 'T3': return '0:0+2:2各10元 [T3覆盖: 让胜陷阱因果链更强(2/2)]'
    return ''

def _t_override_r0(data, reason):
    """R0拦截前检查T系列是否应覆盖"""
    t_info = _check_t_series(data)
    if t_info:
        hw_t, rs_t, is_give = t_info
        t_rule = None
        if hw_t < 3.0 and not is_give: t_rule = 'T1'
        elif hw_t >= 4.0 and not is_give: t_rule = 'T2'
        elif hw_t > 5.0 and is_give: t_rule = 'T3'
        if t_rule:
            t_sb = _build_t_bet(t_rule, data.get('score_odds', {}))
            t_list = t_sb if isinstance(t_sb, list) else [t_sb]
            return {
                'action': 'bet',
                'rule': t_rule,
                'bet_type': 'single',
                'goal_bet': {'goals': [], 'stake': 0, 'odds': {}},
                'score_bets': t_list,
                'score_stake': sum(s['stake'] for s in t_list),
                'total_stake': sum(s['stake'] for s in t_list),
                'summary': _build_t_summary(t_rule),
                'pp_boost': False, 's7_dual': False
            }
    return None

def compute_betting(data, analysis):
    """
    投注策略决策：
    R0: 推荐0:0 → 纯0球20元
    R1: 推荐3:0 + V36+Tree双确认 + 让胜<1.80 → 3:0比分20元
    R3: 不推荐1:1 + 主胜<1.3 + 0球20-35 → 双选3+4球120元
    R4: 不推荐1:1 + 0球<10 → 双选0+2球120元
    """
    tg = data.get('total_goals', {})
    go = {}
    for k in ['0球', '1球', '2球', '3球', '4球', '5球', '6球', '7球']:
        v = tg.get(k)
        if v:
            try: go[int(k[0])] = float(v)
            except: pass
    
    g0 = go.get(0)
    had = data.get('had', {})
    try: 
        h_win = float(had.get('胜', 0))
        draw = float(had.get('平', 0))
        a_win = float(had.get('负', 0))
    except: 
        h_win = None
        draw = None
        a_win = None
    
    step0 = analysis.get('step0', {})
    v36_dir = step0.get('direction', '')
    
    # 获取系统比分推荐 (从score_odds + hitrate计算)
    from sporttery_web import _build_score_hitrate_stats, get_score_recommendations_for_match
    so = data.get('score_odds', {})
    if so:
        try:
            recs = get_score_recommendations_for_match(so)
        except:
            _build_score_hitrate_stats()
            recs = get_score_recommendations_for_match(so)
    else:
        recs = []
    
    top_score_rec = recs[0]['score'] if recs else None
    not_11 = (top_score_rec != '1:1') if top_score_rec else None
    # R0放宽: 0:0从不当Top1, 放宽到Top2 (2026-05-27, Top2: 164场16%, Top3: 11场0%)
    r0_in_top2 = ('0:0' in [r['score'] for r in recs[:2]]) if recs else False
    
    # 决策树信号 (扩展: 主强队 + 客强队)
    strong_home = h_win and h_win < 1.3 and g0 and 20 <= g0 <= 35
    strong_over = strong_home  # 仅主强队
    # R4 temporarily disabled
    strong_under = False  # g0 and g0 < 10
    
    tree_dir = 'over_strong' if strong_over else 'under' if strong_under else None
    
    # 一致性
    score_goals = recs[0]['total_goals'] if recs else 0
    score_dir = 'over' if score_goals >= 3 else 'under'
    v36_is_over = ('大球' in v36_dir)
    
    agree_v36 = (v36_is_over == (score_dir == 'over'))
    agree_tree = ((tree_dir and tree_dir.startswith('over')) == (score_dir == 'over'))
    agree_count = (1 if agree_v36 else 0) + (1 if agree_tree else 0)
    
    # 规则判定
    rule = None
    bet_goals = []
    bet_type = None
    goal_stake = 0
    score_bets = []
    s7_dual = False
    f_eligible = False
    if g0 and 25 <= g0 < 35:
        try:
            preview = data.get('preview', {}) or {}
            recent = preview.get('recent', {}) or {}
            hf = -1; af = -1; hfc = -1; afc = -1
            for side, key in [('home', 'hf'), ('away', 'af')]:
                side_data = recent.get(side, {})
                ml = side_data.get('matchList', []) if isinstance(side_data, dict) else []
                if len(ml) >= 2:
                    n = min(len(ml), 5)
                    total_g = 0; concede_g = 0
                    for m in ml[:n]:
                        hg = float(m.get('homeTeamFullCourtGoalCnt', 0) or 0)
                        ag = float(m.get('awayTeamFullCourtGoalCnt', 0) or 0)
                        total_g += hg + ag
                        if side == 'home': concede_g += ag
                        else: concede_g += hg
                    if key == 'hf': hf = total_g / n; hfc = concede_g / n
                    else: af = total_g / n; afc = concede_g / n
            max_form = max(hf, af)
            weak_def = afc if hf >= af else hfc
            ttg_change = data.get('ttg_change', {})
            g0_chg_data = ttg_change.get('0球', {}) if isinstance(ttg_change, dict) else {}
            g0_chg = g0_chg_data.get('change_pct', 0) if isinstance(g0_chg_data, dict) else 0
            f_eligible = (max_form > 4 and weak_def >= 0 and weak_def < 1.5 and g0_chg > -5)
        except:
            pass
    
    # 预计算G4信号（4球警惕造热+平<3.5+双方防守>1.0→投2:2, 回测ROI+122%）
    g4_22 = False
    try:
        exclusion = analysis.get('exclusion', {})
        for e in exclusion.get('kept', []):
            g = e.get('goal', ''); st = e.get('status', '?')
            if g == '4球' and st == '⚠️警惕造热':
                had = data.get('had', {})
                try:
                    draw = float(had.get('平', had.get('D', 999)))
                    if draw < 3.5:
                        rec = analysis.get('recent_summary', {})
                        h_def = float(rec.get('h_def', 0) or 0)
                        a_def = float(rec.get('a_def', 0) or 0)
                        if min(h_def, a_def) > 1.0:  # 双方防守都不好
                            g4_22 = True
                except: pass
                break
    except:
        pass
    
    # 预计算H1信号（大热必死+Top1比分+o0>=20+尾数.25→投Top1比分10元,回测ROI+263%）
    h1_score = None; h1_odds = 0
    try:
        exclusion = analysis.get('exclusion', {})
        hot_goals = {}
        for e in exclusion.get('kept', []) + exclusion.get('excluded', []):
            st = e.get('status', '?'); reason = e.get('reason', '?')
            if '大热必死' in st or '大热必死' in reason:
                try: hot_goals[int(e.get('goal','').replace('球',''))] = True
                except: pass
        if hot_goals and g0 and g0 >= 20:
            so = data.get('score_odds', {})
            if so:
                from sporttery_web import get_score_recommendations_for_match
                top_recs = get_score_recommendations_for_match(so)
                if top_recs:
                    top1 = top_recs[0]
                    if int(top1.get('total_goals', 0)) in hot_goals:
                        h1_score = top1.get('score', '')
                        try:
                            parts = h1_score.replace('-',':').split(':')
                            key = f'{int(parts[0]):02d}:{int(parts[1]):02d}'
                            h1_odds = float(so.get(key, so.get(h1_score, 0)) or 0)
                            # 尾数必须.25
                            odd_str = str(h1_odds)
                            if not (len(odd_str) >= 3 and odd_str[-2:] == '25'):
                                h1_odds = 0; h1_score = None
                        except: h1_odds = 0
    except:
        pass
    
    # 预计算H2信号（Top1=1:1+o0 11-13+平<3.5+2球铁保留/大热必死+尾数.25→投1:1 10元,回测ROI+275%）
    h2_11 = False
    try:
        if g0 and 11 <= g0 < 13:
            had = data.get('had', {})
            draw = float(had.get('平', had.get('D', 999)) or 0)
            if draw < 3.5:
                so = data.get('score_odds', {})
                if so:
                    from sporttery_web import get_score_recommendations_for_match
                    top_recs = get_score_recommendations_for_match(so)
                    if top_recs and top_recs[0].get('score') == '1:1':
                        # 尾数必须.25
                        odds11 = top_recs[0].get('odds', 0)
                        odd_str = str(odds11)
                        if len(odd_str) >= 3 and odd_str[-2:] == '25':
                            # 检查2球状态: 铁保留 或 大热必死
                            excl = analysis.get('exclusion', {})
                            st2 = None
                            for e in excl.get('kept', []) + excl.get('excluded', []):
                                if e.get('goal') == '2球':
                                    st2 = e.get('status', '?')
                                    if '大热必死' in st2 or st2 == '🛡️铁保留':
                                        h2_11 = True
                                    break
                            if not h2_11:
                                for e in excl.get('excluded', []):
                                    if e.get('goal') == '2球' and '大热必死' in e.get('reason', ''):
                                        h2_11 = True; break
    except:
        pass
    
    # 预计算H3信号（平平↓+2球≥3.05+平<3.2+pp≤-8%+pp≤3次+Top1=1:1+o0≤14→投1:1 30元,回测ROI+405%）
    h3_11 = False
    try:
        if g0 and g0 <= 14:
            had = data.get('had', {})
            draw = float(had.get('平', had.get('D', 999)) or 0)
            if draw < 3.2:
                g2_val = go.get(2, 0)
                if g2_val and g2_val >= 3.05:
                    so = data.get('score_odds', {})
                    if so:
                        from sporttery_web import get_score_recommendations_for_match
                        top_recs = get_score_recommendations_for_match(so)
                        if top_recs and top_recs[0].get('score') == '1:1':
                            hafu_c = data.get('hafu_change', {}) or {}
                            pp = hafu_c.get('平平', {})
                            if isinstance(pp, dict):
                                pc = pp.get('count', 0)
                                pch = pp.get('change_pct', 0)
                                if 1 < pc <= 3 and pch <= -8:
                                    min_chg = min(v.get('change_pct', 0) for v in hafu_c.values() if isinstance(v, dict))
                                    if pch <= min_chg + 0.1:
                                        h3_11 = True
    except:
        pass
    
    # 预计算H4信号（平平3次↓>10% + Top1≠1:1 → 投1:1 20元, 旧版已停用）
    h4_11 = False
    # 预计算H5信号（新版H4替代: 平平↓≥10%+count≥3+0球<10+Top1≠1:1+draw∈[2.85,3.05] → 投1:1 20元, 回测7场4中57%）
    h5_11 = False
    try:
        hafu_c = data.get('hafu_change', {}) or {}
        pp = hafu_c.get('平平', {})
        if isinstance(pp, dict) and pp.get('count', 0) >= 3 and pp.get('change_pct', 0) <= -10:
            g0_val = float(tg.get('0球', 0) or 0)
            if g0_val < 10:
                draw_odds = float(had.get('平', had.get('D', 0)) or 0)
                if 2.85 <= draw_odds <= 3.05:
                    so = data.get('score_odds', {})
                    if so:
                        from sporttery_web import get_score_recommendations_for_match
                        top_recs = get_score_recommendations_for_match(so)
                        if top_recs and top_recs[0].get('score') != '1:1':
                            h5_11 = True
    except:
        pass
    
    # 预计算S1信号（近况>2.5+1球=⭐变高共振→投1球 30元,回测ROI+155%）
    s1_1ball = False
    try:
        rec = analysis.get('recent_summary', {})
        combined = float(rec.get('combined_avg', 0) or 0)
        if combined > 2.5:
            excl = analysis.get('exclusion', {})
            for e in excl.get('kept', []):
                if e.get('goal') == '1球' and '变高共振' in e.get('status', ''):
                    s1_1ball = True; break
    except:
        pass
    
    # 预计算S8信号（g0<10+平平降>17%→假0:0恐慌盘, 投HAD方向1:0/0:1 10元+1球20元, ROI+172%）
    s8_signal = False
    try:
        g0_val = float(data.get('total_goals', {}).get('0球', 0) or 0)
        if g0_val < 10:
            hf = data.get('hafu_change', {}) or {}
            pp = hf.get('平平', {})
            pp_chg = float(pp.get('change_pct', 0)) if isinstance(pp, dict) else 0
            if pp_chg < -17:
                s8_signal = True
    except:
        pass
    
    # P1信号: 黄金1球+通用3球+平平不动 → 1球 (10场8中80%, ROI+190%, 2026-05-30)
    p1_signal = False
    try:
        p1_g1 = float(data.get('total_goals', {}).get('1球', 0) or 0)
        p1_g0 = float(data.get('total_goals', {}).get('0球', 0) or 0)
        p1_rf = float(data.get('hhad', {}).get('让负', 0) or 0)
        p1_rq = int(data.get('hhad', {}).get('让球', '0') or '0')
        hf = data.get('hafu_change', {}) or {}
        pp = hf.get('平平', {})
        p1_pp_chg = float(pp.get('change_pct', 0)) if isinstance(pp, dict) else 0
        if (3.0 <= p1_g1 <= 4.0 and p1_g0 < 10 and p1_rq == -1 
            and 1.5 <= p1_rf <= 1.7 and p1_pp_chg == 0):
            p1_signal = True
    except:
        pass
    
    # 预计算N1信号：4球低价+平赔跌→6球 (2026-06-03, 10场4/10=40% ROI+405%)
    n1_signal = False
    try:
        g4_raw = data.get('total_goals', {}).get('4球')
        g4_val = float(g4_raw) if g4_raw else 99
        had_ch = data.get('had_change', {})
        draw_ch = had_ch.get('平', {})
        ch_pct = float(draw_ch.get('change_pct', 0)) if isinstance(draw_ch, dict) else 0
        if g4_val < 5.0 and -20 <= ch_pct <= -10:
            n1_signal = True
    except:
        pass
    
    # 预计算D2信号：让负1.50-1.70 + 3球3.3-3.5 + 变化次数=1 且 -5%≤变化幅度≤-2% → 69.2%命中率
    d2_signal = False
    try:
        hhad = data.get('hhad', {})
        rq = hhad.get('让球', '0')
        hh_l = float(hhad.get('让负', 0) or 0)
        tg = data.get('total_goals', {})
        g3 = float(tg.get('3球', 0) or 0)
        ttg_change = data.get('ttg_change', {})
        g3_change = ttg_change.get('3球', {})
        change_count = int(g3_change.get('count', 0)) if isinstance(g3_change, dict) else 0
        change_pct = float(g3_change.get('change_pct', 0)) if isinstance(g3_change, dict) else 0
        
        if (rq == '-1' and 1.50 <= hh_l < 1.70
            and 3.3 <= g3 < 3.5
            and change_count == 1
            and -5 <= change_pct <= -2):
            d2_signal = True
    except:
        pass
    
    # 预计算S2/S3/S4信号（近况<2.5 + 大球反常保留→反向投注）
    s2_5ball = False; s3_6ball = False; s4_7ball = False; s5_22 = False; s6_2ball = False
    try:
        rec = analysis.get('recent_summary', {})
        combined = float(rec.get('combined_avg', 0) or 0)
        if combined < 2.5:
            excl = analysis.get('exclusion', {})
            for e in excl.get('kept', []):
                g = e.get('goal', ''); st = e.get('status', '?')
                if g == '5球' and st == '⚠️警惕造热': s2_5ball = True
                if g == '6球' and st in ('✅保留', '✅观察保留'): s3_6ball = True
                if g == '7球' and st == '✅观察保留': s4_7ball = True
        # S5: Top1=3:0 + 3/4球双警惕 + 平>=5 + 近>=3.2 -> 投2:2 10元 (ROI+910%)
        if combined >= 3.2:
            so = data.get('score_odds', {})
            if so:
                from sporttery_web import get_score_recommendations_for_match
                top_recs = get_score_recommendations_for_match(so)
                if top_recs and top_recs[0].get('score') == '3:0':
                    excl = analysis.get('exclusion', {})
                    s3 = '?'; s4 = '?'
                    for e in excl.get('kept', []):
                        if e.get('goal') == '3球': s3 = e.get('status', '?')
                        if e.get('goal') == '4球': s4 = e.get('status', '?')
                    if '警惕造热' in s3 and '警惕造热' in s4:
                        had = data.get('had', {})
                        draw = float(had.get('平', had.get('D', 999)) or 0)
                        if draw and draw >= 5.0:
                            s5_22 = True
        # S6: 0球>=19 + 2球4.0-4.4 + 近况>=2.5 + 2球警惕 → 2球20+1:1 10元 (ROI+100%)
        if combined >= 2.5:
            tg = data.get('total_goals', {})
            g0 = float(tg.get('0球', 0) or 0)
            g2 = float(tg.get('2球', 0) or 0)
            if g0 >= 19 and 4.0 <= g2 <= 4.4:
                excl = analysis.get('exclusion', {})
                for e in excl.get('kept', []):
                    if e.get('goal') == '2球' and e.get('status') == '⚠️警惕造热':
                        s6_2ball = True; break
    except:
        pass
    
    # 预计算G5/G6/G7信号（三维排除标签驱动，2026-05-12新增，回测ROI+253%）
    g5_warn = False; g6_keep = False; g7_signal = False
    try:
        exclusion = analysis.get('exclusion', {})
        for e in exclusion.get('kept', []) + exclusion.get('excluded', []):
            g = e.get('goal', ''); st = e.get('status', '?')
            if g == '5球' and st == '⚠️警惕造热': g5_warn = True
            if g == '6球' and st == '✅保留': g6_keep = True
            if g == '7球' and st in ('✅观察保留', '⚠️警惕造热'): g7_signal = True
    except:
        pass
    
    # 预计算X2/X3/X4信号（三维排除陷阱, 2026-05-20新增）
    x2_35 = False; x3_123 = False; x4_34 = False
    try:
        exclusion = analysis.get('exclusion', {})
        kept = exclusion.get('kept', [])
        kept_goals = {e.get('goal', '') for e in kept}
        kept_statuses = {e.get('goal', ''): e.get('status', '') for e in kept}
        # X3: 1球+2球+3球保留 + 3球警惕 + 2球警惕 + 推荐含5球 → 投3球 (6场4中67%, ROI+129%)
        if kept_goals == {'1球', '2球', '3球'}:
            if '警惕' in kept_statuses.get('3球', '') and '警惕' in kept_statuses.get('2球', ''):
                rec = analysis.get('recommended', {})
                rec_goals = rec.get('goals', [])
                if rec_goals and 5 in rec_goals[:2]:
                    x3_123 = True
        if len(kept) == 2:
            # X2: 仅剩3球+5球 → 投2球 (4场3中75%)
            if kept_goals == {'3球', '5球'}:
                x2_35 = True
            # X4: 仅剩3球(警惕)+4球(保留) → 投4球 (4场3中75%)
            if kept_goals == {'3球', '4球'} and kept_statuses.get('3球') == '⚠️警惕造热':
                x4_34 = True
    except:
        pass
    
    # 预计算X5信号（建议投注+推荐4+5球+无规则 → 投4球, 5场4中80%, ROI+300%）
    # 2026-05-25: 5球变化>5%→跳过; 2026-05-26: 任一警惕造热→跳过(5场2中40%)
    x5_45 = False
    x5_5ball_surge = False
    x5_4ball_warn = False
    try:
        fgp = analysis.get('final_goal_pick', {})
        skip_reason = fgp.get('skip_reason', [])
        rec = analysis.get('recommended', {})
        rec_goals = rec.get('goals', [])
        if (not skip_reason or len(skip_reason) == 0) and rec_goals and rec_goals[:2] == [4, 5]:
            x5_45 = True
            # 检查5球赔率变化
            ttg2 = data.get('ttg_change', {})
            ch5 = float(ttg2.get('5球', {}).get('change_pct', 0) or 0)
            if ch5 > 5:
                x5_5ball_surge = True
            # 检查是否有警惕造热(任一警惕则跳过, 无警惕5场80% vs 有警惕5场40%)
            exc = analysis.get('exclusion', {})
            for e in exc.get('kept', []):
                if '警惕造热' in str(e.get('status', '')):
                    x5_4ball_warn = True
                    break
    except:
        pass
    
    # 预计算X6信号（客让+2:3候选+客攻>主防 → 投2:3比分, 13场4中31%, ROI+592%）
    x6_23 = False
    x6_23_odds = 0
    try:
        hhad = data.get('hhad', {})
        rs_val = float(hhad.get('让胜', 0)) if isinstance(hhad, dict) and hhad.get('让胜') else 99
        rl_val = float(hhad.get('让负', 0)) if isinstance(hhad, dict) and hhad.get('让负') else 99
        if rs_val < 99 and rl_val < 99 and rs_val > rl_val:
            rec_sum = analysis.get('recent_summary', {})
            a_att = rec_sum.get('a_att', 0)
            h_def = rec_sum.get('h_def', 0)
            if a_att - h_def >= 1.0:
                rec = analysis.get('recommended', {})
                fs = rec.get('filtered_scores', [])
                for f in fs:
                    if f.get('score') == '2-3':
                        so = data.get('score_odds', {})
                        odds_23 = float(so.get('02:03', so.get('2:3', 0)) or 0)
                        if odds_23 > 0:
                            x6_23 = True
                            x6_23_odds = odds_23
                        break
    except:
        pass
    
    # ⚠️ H系列上轮差距检查: 两队上轮进球与投注目标差≥2 → 0命中 (2026-05-24)
    h_gap_far = False
    try:
        preview = data.get('preview', {})
        recent_data = preview.get('recent', {})
        home_recent = recent_data.get('home', {}).get('matchList', []) if isinstance(recent_data.get('home'), dict) else []
        away_recent = recent_data.get('away', {}).get('matchList', []) if isinstance(recent_data.get('away'), dict) else []
        def _last_total(ml):
            if not ml: return None
            m = ml[0]
            return int(m.get('homeTeamFullCourtGoalCnt', 0) or 0) + int(m.get('awayTeamFullCourtGoalCnt', 0) or 0)
        hl = _last_total(home_recent); al = _last_total(away_recent)
        hl_prev = hl; al_prev = al
        # H系列只在0-1球区域, 检查是否全部差≥2
        h_far = hl is not None and hl >= 2
        a_far = al is not None and al >= 2
        h_gap_far = h_far and a_far  # 两队都≥2球 → 不可能突然闷平
    except:
        hl_prev = None; al_prev = None
        pass
    
    # ⚠️ H4/H5优先于R0: 平平↓信号直接触发(不给R0拦截机会)
    # ⚠️ HAD/HHAD诱盘检测：主胜极低但让胜极高=深盘无力陷阱
    # V6.6 CAND-HAD: 非让胜候选比分博冷10元 (回测5/5全中, 需让平>=3.85过滤)
    try:
        had = data.get('had', {})
        hhad = data.get('hhad', {})
        hw_chk = float(had.get('胜', 0)) if isinstance(had, dict) and had.get('胜') else 99
        rs_chk = float(hhad.get('让胜', 0)) if isinstance(hhad, dict) and hhad.get('让胜') else 0
        rp_chk = float(hhad.get('让平', 0)) if isinstance(hhad, dict) and hhad.get('让平') else 0
        hd_chk = float(had.get('平', 0)) if isinstance(had, dict) and had.get('平') else 0
        if 1.10 < hw_chk < 1.45 and rs_chk > 2.30 and rp_chk >= 3.85 and 5.0 < hd_chk <= 5.5:
            # CAND-HAD: 检查V3.6候选比分中3球/4球的非让胜选项
            cand_scores = []
            sc_list = (analysis or {}).get('score_candidates', [])
            so_data = data.get('score_odds', {}) if isinstance(data, dict) else {}
            for sc in sc_list:
                if sc.get('total_goals') not in (3, 4):
                    continue
                for s in sc.get('scores', []):
                    s_score = s.get('score', '')
                    parts = s_score.split('-')
                    if len(parts) != 2:
                        continue
                    try:
                        s_h, s_a = int(parts[0]), int(parts[1])
                    except:
                        continue
                    # 跳过让胜 (主胜)
                    if s_h > s_a:
                        continue
                    # 获取赔率
                    so_key = '{:02d}:{:02d}'.format(s_h, s_a)
                    s_odds = float(so_data.get(so_key, 0) or 0)
                    if s_odds > 0:
                        cand_scores.append({'score': '{}:{}'.format(s_h, s_a), 'odds': round(s_odds, 1),
                                            'stake': 10, 'tag': 'CAND-HAD'})
            if cand_scores:
                mi = data.get('match_info', {}) or {}
                mn = mi.get('match_num_str', '') if isinstance(mi, dict) else ''
                ht = mi.get('home_team', '?') if isinstance(mi, dict) else '?'
                at = mi.get('away_team', '?') if isinstance(mi, dict) else '?'
                _trace_log('HAD-TRAP', f'{mn} {ht}vs{at} 主胜{hw_chk:.2f}+让胜{rs_chk:.2f}→CAND-HAD({len(cand_scores)}个比分)')
                return {
                    'action': 'bet', 'rule': 'CAND-HAD',
                    'goal_stake': 0, 'goal_bet': {}, 'bet_goals': [],
                    'total_score_stake': sum(s['stake'] for s in cand_scores),
                    'score_bets': cand_scores, 'bet_type': '分数冷推',
                    'total_stake': sum(s['stake'] for s in cand_scores),
                    'summary': 'CAND-HAD: {}个比分{}元'.format(len(cand_scores), sum(s['stake'] for s in cand_scores)),
                    'pp_boost': False, 's7_dual': False
                }
            # 无候选比分 → 原skip逻辑
            mi = data.get('match_info', {}) or {}
            mn = mi.get('match_num_str', '') if isinstance(mi, dict) else ''
            ht = mi.get('home_team', '?') if isinstance(mi, dict) else '?'
            at = mi.get('away_team', '?') if isinstance(mi, dict) else '?'
            _trace_log('HAD-TRAP', f'{mn} {ht}vs{at} 主胜{hw_chk:.2f}+让胜{rs_chk:.2f}→SKIP(深盘无力)')
            return {'action': 'skip', 'reason': f'HAD陷阱: 主胜{hw_chk:.2f}<1.45+让胜{rs_chk:.2f}>2.30(深盘无力,无冷推比分)'}
    except:
        pass

    # ===== H9: 最高历史比分矛盾法 → 让球方向投注 (回测123场79.7%, 2026-06-21) =====
    if not rule:
        try:
            from h9_predictor import predict_h9
            hhad = data.get('hhad', {})
            handicap_str = hhad.get('让球', '')
            if handicap_str:
                handicap = float(handicap_str)
                h9_result = predict_h9(data, handicap)
                if h9_result and h9_result.get('prediction'):
                    # 存储H9分析结果，供前端显示
                    data['_h9_analysis'] = h9_result
                    
                    # 只在高置信度时触发投注
                    if h9_result.get('is_high_conf'):
                        prediction = h9_result['prediction']
                        confidence = h9_result['confidence']
                        explanation = h9_result['explanation']
                        
                        # 获取让球赔率
                        hhad_odds = hhad
                        bet_odds = float(hhad_odds.get(prediction, 0))
                        
                        if bet_odds > 0:
                            return {
                                'action': 'bet',
                                'rule': 'H9',
                                'bet_type': 'handicap',
                                'handicap_bet': {
                                    'direction': prediction,
                                    'odds': round(bet_odds, 2),
                                    'stake': _get_stake_by_tier('H9'),
                                    'confidence': confidence,
                                    'explanation': explanation,
                                    'situation': h9_result['situation'],
                                    'is_high_conf': True
                                },
                                'goal_bet': {'goals': [], 'stake': 0, 'odds': {}},
                                'score_bets': [],
                                'total_stake': _get_stake_by_tier('H9'),
                                'summary': f"H9: {prediction}{round(bet_odds, 2)}元 [{explanation}]",
                                'pp_boost': False,
                                's7_dual': False
                            }
                    # 非高置信度：只显示分析结果，不触发投注
        except Exception as e:
            import sys
            print(f'[H9] ❌ 规则检查失败: {e}', file=sys.stderr, flush=True)
    
    # ===== S9: 0球13-16+3球3.2-3.4+近况<2.5+主让1球 → 大球双投40元 (32场ROI+35.5%, 2026-06-19) =====
    if not rule:
        s9 = _check_s9(data)
        if s9:
            rule = 'S9'
            bet_goals = s9['goals']
            bet_type = 'double'
            goal_stake = 40
            goal_odds = s9['odds']
            
            # 运行H9调整置信度 (2026-06-21)
            h9_note = ''
            try:
                from h9_predictor import predict_h9
                hhad = data.get('hhad', {})
                handicap_str = hhad.get('让球', '')
                if handicap_str:
                    handicap = float(handicap_str)
                    h9_result = predict_h9(data, handicap)
                    if h9_result and isinstance(h9_result, dict):
                        # 存储H9分析结果，供前端显示
                        data['_h9_analysis'] = h9_result
                        
                        h9_pred = h9_result.get('prediction', '')
                        h9_conf = h9_result.get('confidence', 0)
                        
                        if h9_pred == '让胜':
                            goal_stake = 50  # 提升投注额
                            h9_note = f' [H9✅让胜{h9_conf:.0f}%→提置信]'
                        elif h9_pred == '让负':
                            goal_stake = 30  # 降低投注额
                            h9_note = f' [H9⚠️让负{h9_conf:.0f}%→降置信]'
                        else:
                            h9_note = f' [H9➖{h9_pred}{h9_conf:.0f}%]'
            except Exception as e:
                import sys
                print(f'[H9] ⚠️ 调整投注额失败: {e}', file=sys.stderr, flush=True)
            
            summary_text = f"S9: 3球+{s9['goals'][1]}球各{goal_stake//2}元 [{s9['pick_explain']}]{h9_note}"
            return {
                'action': 'bet', 'rule': rule,
                'bet_type': bet_type,
                'goal_bet': {'goals': bet_goals, 'stake': goal_stake, 'odds': {str(g): round(o, 1) for g, o in goal_odds.items()}},
                'score_bets': [], 'score_stake': 0,
                'total_stake': goal_stake, 'summary': summary_text,
                'pp_boost': False, 's7_dual': False
            }
    
    # ===== CAND043: 大赛低赔比分博冷10元 (世界杯/国际赛, 比分赔<5+该进球赔率最低, 回测4场3中75%) =====
    if not rule:
        try:
            mi = data.get('match_info', {}) or {}
            league = mi.get('league', '') if isinstance(mi, dict) else ''
            if league in ('世界杯', '国际赛', '世界杯预选赛'):
                so = data.get('score_odds', {})
                tg = data.get('total_goals', {})
                if so and tg:
                    goal_odds = {}
                    goal_map_c043 = {0:'0球',1:'1球',2:'2球',3:'3球',4:'4球',5:'5球',6:'6球',7:'7球'}
                    for gn, gk in goal_map_c043.items():
                        try: goal_odds[gn] = float(tg.get(gk, 0) or 0)
                        except: goal_odds[gn] = 0
                    min_goal = min((g for g in goal_odds if goal_odds[g] > 0), key=lambda g: goal_odds[g], default=-1)
                    if min_goal >= 0:
                        best_score = ''; best_od = 99
                        for sk, sv in so.items():
                            try: o = float(sv)
                            except: continue
                            if 0 < o < 5 and o < best_od:
                                parts = sk.split(':')
                                try: sh, sa = int(parts[0]), int(parts[1])
                                except: continue
                                if sh + sa == min_goal:
                                    best_score = '{}:{}'.format(sh, sa)
                                    best_od = o
                        if best_score:
                            mn_str = mi.get('match_num_str', '') if isinstance(mi, dict) else ''
                            ht = mi.get('home_team', '?') if isinstance(mi, dict) else '?'
                            at = mi.get('away_team', '?') if isinstance(mi, dict) else '?'
                            _trace_log('CAND043', f'{mn_str} {ht}vs{at} {best_score}({best_od:.1f}x,{min_goal}球)→大赛低赔')
                            return {
                                'action': 'bet', 'rule': 'CAND043',
                                'goal_stake': 0, 'goal_bet': {}, 'bet_goals': [],
                                'total_score_stake': 10,
                                'score_bets': [{'score': best_score, 'odds': round(best_od, 1), 'stake': 10, 'tag': '大赛低赔'}],
                                'bet_type': '分数冷推', 'total_stake': 10,
                                'summary': f'CAND043: {best_score}({best_od:.1f}x)',
                                'pp_boost': False, 's7_dual': False
                            }
        except:
            pass
    
    if h5_11 and not h_gap_far:
        # 信号H5: 平平↓≥10%+count≥3+0球<10+Top1≠1:1+draw∈[2.85,3.05] → 投1:1 20元
        rule = 'H5'
        bet_goals = []
        bet_type = 'single'
        goal_stake = 0
    elif h4_11:
        # 信号H4: 平平3次↓>10%+Top1≠1:1 → 投1:1 20元 (旧版已停用)
        rule = 'H4'
        bet_goals = []
        bet_type = 'single'
        goal_stake = 0
    elif x3_123:
        # 信号X3: 三维排除1球+2球+3球保留 + 3球警惕 + 2球警惕 → 投3球20元 (10场6中60%, ROI+109%)
        # ⚠️ 优先于R0: R0的0球命中率过滤会误拦X3(2039350皇家奥维1:2本应中3球)
        rule = 'X3'
        bet_goals = [3]
        bet_type = 'single'
        goal_stake = 20

    elif d2_signal:
        # 信号D2: 让负1.50-1.70 + 3球3.3-3.5 + 变化次数=1 且 -5%≤变化幅度≤-2% → 69.2%命中率 (2026-06-18新增)
        rule = 'D2'
        bet_goals = [3]
        bet_type = 'single'
        goal_stake = 40

    elif g0 == 10 and go.get(2) and 2.9 <= go[2] <= 3.1:
        # G2: g0=10+g2≈3.0 → 0或2球必选一 → 0球20元+2球10元=30元 (5场5中100%, 优化后ROI+240%)
        # ⚠️ 优先于R0: 此信号独立于R0的draw/联赛过滤, 0/2球二选一全覆盖
        # ⚠️ 近况过滤: 主+客近况和>3.0→跳过 (巴列卡诺3.2=0/1, 其余≤3.0全中)
        # ⚠️ 平赔过滤: draw>3.4→跳过 (16场中5场draw>3.4仅1中20%, 2026-06-03)
        try:
            preview_g2 = data.get('preview', {})
            recent_g2 = preview_g2.get('recent', {})
            home_g2 = recent_g2.get('home', {}).get('matchList', []) if isinstance(recent_g2.get('home'), dict) else []
            away_g2 = recent_g2.get('away', {}).get('matchList', []) if isinstance(recent_g2.get('away'), dict) else []
            if home_g2 and away_g2:
                h_m = sum(float(x.get('homeTeamFullCourtGoalCnt', 0) or 0) for x in home_g2) / len(home_g2)
                a_m = sum(float(x.get('awayTeamFullCourtGoalCnt', 0) or 0) for x in away_g2) / len(away_g2)
                if h_m + a_m > 3.0:
                    return {'action': 'skip', 'reason': f'G2跳过: 近况和{h_m+a_m:.1f}>3.0(主{h_m:.1f}+客{a_m:.1f})'}
        except:
            pass
        if draw is not None and draw > 3.4:
            return {'action': 'skip', 'reason': f'G2跳过: 平赔{draw:.2f}>3.4(仅20%命中)'}
        rule = 'G2'
        bet_goals = [0, 2]
        bet_type = 'dual'
        goal_stake = 30
        goal_odds = {0: go.get(0, 10), 2: go.get(2, 3)}
    elif r0_in_top2:
        # R0: 主攻<2.0过滤（强攻队不出0:0）
        h_att = None
        try:
            preview = data.get('preview', {})
            recent = preview.get('recent', {})
            hd = recent.get('home', {})
            hl = hd.get('matchList', []) if isinstance(hd, dict) else []
            if hl:
                h_att = sum([float(x.get('homeTeamFullCourtGoalCnt', 0) or 0) for x in hl]) / len(hl)
        except:
            pass
        if h_att is not None and h_att >= 2.0:
            t_ov1 = _t_override_r0(data, f'R0: 主攻{h_att:.1f}≥2.0')
            if t_ov1: return t_ov1
            return {'action': 'skip', 'reason': f'R0跳过: 主攻{h_att:.1f}≥2.0(强攻队不出0:0)'}
        
        # R0: 0球赔率命中率<10%过滤
        if g0:
            try:
                from sporttery_web import _build_odds_hitrate
                oh = _build_odds_hitrate()
                g0_exact = oh.get('exact', {}).get(0, {})
                key1 = f'{g0:.1f}'
                key2 = f'{g0:.2f}'
                g0_stat = g0_exact.get(key1, g0_exact.get(key2, {}))
                if isinstance(g0_stat, dict) and g0_stat.get('total', 0) >= 5:
                    g0_rate = g0_stat.get('rate', 0)
                    if g0_rate < 10:
                        g0_n = g0_stat['total']
                        t_ov2 = _t_override_r0(data, f'R0: 0球赔{g0}命中率低')
                        if t_ov2: return t_ov2
                        return {'action': 'skip', 'reason': f'R0跳过: 0球赔{g0}命中率{g0_rate:.0f}%<10%(n={g0_n})'}
            except:
                pass
        
        # R0: 半全场平平赔率变化信号
        pp_change = 0
        try:
            hafu_change = data.get('hafu_change', {})
            pp = hafu_change.get('平平', {}) if isinstance(hafu_change, dict) else {}
            pp_change = pp.get('change_pct', 0) if isinstance(pp, dict) else 0
        except:
            pass
        
        # R0: g0≥10.5 + 平平下降 → 陷阱信号，排除
        if g0 and g0 >= 10.5 and pp_change < -0.5:
            t_ov3 = _t_override_r0(data, f'R0: g0≥10.5+平平降')
            if t_ov3: return t_ov3
            return {'action': 'skip', 'reason': f'R0跳过: g0={g0}≥10.5+平平降{pp_change:.0f}%(陷阱信号,回测0/6)'}
        
        # R0: 联赛过滤（大球联赛天然不适合R0闷平）
        SKIP_LEAGUES = ['西班牙甲级联赛', '欧罗巴联赛', '瑞典超级联赛', '日本职业联赛', '韩国职业联赛',
                        '美国职业大联盟', '荷兰乙级联赛', '德国甲级联赛', '德国乙级联赛',
                        '沙特职业联赛', '荷兰甲级联赛', '法国甲级联赛', '葡萄牙超级联赛',
                        '挪威超级联赛']  # 均球>3.0的大球联赛 + 已有小球联赛(西甲/日职/韩职)
        try:
            info = data.get('match_info', {})
            league = info.get('league', '') if isinstance(info, dict) else ''
            if league in SKIP_LEAGUES:
                t_ov4 = _t_override_r0(data, f'R0: {league}联赛过滤')
                if t_ov4: return t_ov4
                return {'action': 'skip', 'reason': f'R0跳过: {league}(联赛0球率低,回测仅10%)'}
        except:
            pass
        
        # R0: 平平下降>5% → 高置信(+20)
        pp_boost = (pp_change < -5)
        
        # R0: HAD赔率变化信号（置信分层）
        had_weak = False  # 弱信号
        had_boost = False  # 强信号
        try:
            had_change = data.get('had_change', {})
            if isinstance(had_change, dict):
                hc_w = had_change.get('胜', {})
                hc_d = had_change.get('平', {})
                hw_ch = hc_w.get('change_pct', 0) if isinstance(hc_w, dict) else 0
                draw_ch = hc_d.get('change_pct', 0) if isinstance(hc_d, dict) else 0
                if draw_ch < -3:
                    had_boost = True  # HAD平赔降>3% → 庄家压平局,0球概率升
                elif hw_ch > 10:
                    had_weak = True  # HAD主胜升>10% → 资金涌向主胜,出球概率升
        except:
            pass
        
        # R0: 近况过滤已移除(2026-05-18)
        
        # R0: 0球甜区[9.5,10.5]过滤 (2026-05-19) — 甜区内10场7中70%, 甜区外12场1中8%
        if not (9.5 <= g0 <= 10.5):
            t_ov5 = _t_override_r0(data, 'R0: 0球甜区')
            if t_ov5: return t_ov5
            return {'action': 'skip', 'reason': f'R0跳过: 0球={g0}不在甜区[9.5-10.5](命中70%)'}
        
        # R0: 平赔≤3.0 (5月验证: ≤3.0=2/2红, >3.0=0/4全黑)
        if draw is not None and draw > 3.0:
            t_ov6 = _t_override_r0(data, f'R0: 平赔{draw:.2f}')
            if t_ov6: return t_ov6
            return {'action': 'skip', 'reason': f'R0跳过: 平赔{draw:.2f}>3.0(0/4全黑)'}
        
        # R0: 纯0球20元
        rule = 'R0'
        bet_goals = [0]
        bet_type = 'single'
        goal_stake = 20
    elif top_score_rec == '3:0':
        # B1: 让胜真信穿盘 (2026-06-17新增, 3/3 穿盘, 前置: 让胜降>10%+display=3:0+rs/hw<1.6+hw<1.5)
        # ⚠️ B1优先于R1: B1因果链说3:0不出, 直接触发, 不再走R1
        if _check_b1(data) is not None:
            rule = 'B1'
            b1_sb = _build_b1_bet(so)
            bet_goals = []
            bet_type = 'single'
            goal_stake = 0
            score_bets = b1_sb
            total_score_stake = sum(s['stake'] for s in b1_sb)
            rule = 'B1'
            # 直接返回, 不再走R1
            summary_text = '3:1+4:1各10元'
            return {
                'action': 'bet',
                'rule': rule,
                'bet_type': bet_type,
                'goal_bet': {'goals': bet_goals, 'stake': goal_stake, 'odds': {}},
                'score_bets': score_bets,
                'score_stake': total_score_stake,
                'total_stake': total_score_stake,
                'summary': summary_text,
                'pp_boost': False,
                's7_dual': False
            }
        
        # R1: Top1=3:0 + 让胜<1.80(当前或初盘) + sim3球<1 → 3:0比分20元 (7场4中 ROI+343%)
        # 2026-05-27: 移除agree_count==2和g0≤20, 新增sim3球过滤, 初盘让胜兼容
        try:
            hhad = data.get('hhad', {})
            rs = float(hhad.get('让胜', 0)) if isinstance(hhad, dict) and hhad.get('让胜') else 0
            rs_pass = (rs < 1.80)
            if not rs_pass:
                # 倒推初盘让胜 (2026-05-27)
                try:
                    hhad_chg = data.get('hhad_change', {})
                    rs_chg = hhad_chg.get('让胜', {})
                    chg_pct = float(rs_chg.get('change_pct', 0)) if isinstance(rs_chg, dict) else 0
                    if rs > 0 and chg_pct != 0:
                        rs_ini = rs / (1 + chg_pct / 100)
                        rs_pass = (rs_ini < 1.80)
                except:
                    pass
            if not rs_pass:
                return {'action': 'skip', 'reason': f'R1跳过: 让胜{rs:.1f}≥1.80(回测仅10%命中)'}
        except:
            pass
        
        # R1: sim3球≥1次→跳过 (甜区1/6=17%, 温区0/4=0%) (2026-05-27)
        try:
            from sporttery_web import find_similar_matches
            sims = find_similar_matches(data, top_n=8)
            if len(sims) >= 3:
                sim_tgs = [s.get('record',{}).get('home_score',0)+s.get('record',{}).get('away_score',0) for s in sims]
                cnt = sum(1 for g in sim_tgs if g == 3)
                if cnt >= 1:
                    return {'action': 'skip', 'reason': f'R1跳过: sim3球{cnt}次(≥1次仅10%命中)'}
        except:
            pass
        
        # R1: g0 15-25区间跳过 (0/4全黑, 2026-05-27)
        if g0 and 15 <= g0 <= 25:
            return {'action': 'skip', 'reason': f'R1跳过: g0={g0:.0f}在15-25区间(0/4全黑)'}
        
        rule = 'R1'
        bet_goals = []
        bet_type = 'single'
        goal_stake = 0
    elif g0 and g0 == 23 and go.get(2, 99) >= 4.0 and go.get(2, 99) <= 4.3:
        # 信号S7: 0球=23 + 2球[4.0-4.3] → 投2球20元 (回测5/5=100%)
        # S6+S7双确认: 两个独立逻辑(三维排除+赔率区间)同时指向2球 → 加注到40元 (4/4=100%)
        # ⚠️ S7近况过滤: 主+客近况和>3.0→跳过 (2026-05-30瓦勒伦加3:1,近况2.6+1.0=3.6唯一>3.0, 其他6场≤3.0全中)
        try:
            preview_s7 = data.get('preview', {})
            recent_s7 = preview_s7.get('recent', {})
            home_s7 = recent_s7.get('home', {}).get('matchList', []) if isinstance(recent_s7.get('home'), dict) else []
            away_s7 = recent_s7.get('away', {}).get('matchList', []) if isinstance(recent_s7.get('away'), dict) else []
            if home_s7 and away_s7:
                h_mean = sum(float(x.get('homeTeamFullCourtGoalCnt', 0) or 0) for x in home_s7) / len(home_s7)
                a_mean = sum(float(x.get('awayTeamFullCourtGoalCnt', 0) or 0) for x in away_s7) / len(away_s7)
                if h_mean + a_mean > 3.0:
                    return {'action': 'skip', 'reason': f'S7跳过: 近况和{h_mean+a_mean:.1f}>3.0(主{h_mean:.1f}+客{a_mean:.1f})'}
        except:
            pass
        rule = 'S7'
        bet_goals = [2]
        bet_type = 'single'
        goal_stake = 40 if s6_2ball else 20
        s7_dual = s6_2ball
    elif f_eligible:
        # 信号F: 近况>4 + 铁桶防守 + 0球25-35 + 0球不暴跌 → 投7球 (ROI+275%)
        # ⚠️ F过热过滤: 某队上轮≥5→跳过(2026-05-24, 3/3黑单全有上轮≥5, 红单0/2)
        if hl_prev is not None and al_prev is not None and (hl_prev >= 5 or al_prev >= 5):
            return {'action': 'skip', 'reason': f'F跳过: 上轮≥5(hl={hl_prev} al={al_prev})'}
        rule = 'F'
        bet_goals = [7]
        bet_type = 'single'
        goal_stake = 20
    elif g7_signal and g0 and g0 >= 12:
        # 信号G7: 三维排除7球=保留/警惕 + o0>=12 → 投7球 (ROI+550%)
        # ⚠️ G7过热过滤: dw<3→跳过(2026-05-24, 黑单dw均2.70 vs 红单4.30)
        # ⚠️ 2026-05-26: 警惕造热→跳过(有警惕0/2 vs 无警惕2/2=100%)
        try:
            exc_check = analysis.get('exclusion', {})
            if any('警惕' in str(e.get('status','')) for e in exc_check.get('kept',[])):
                return {'action': 'skip', 'reason': 'G7跳过: 警惕造热(0/2全黑)'}
        except: pass
        try:
            dw_chk = float(data.get('had', {}).get('平', 0) or 0)
            if dw_chk < 3.0:
                return {'action': 'skip', 'reason': f'G7跳过: dw={dw_chk:.2f}<3.0'}
        except: pass
        rule = 'G7'
        bet_goals = [7]
        bet_type = 'single'
        goal_stake = 20
    # 新规律信号(S2/S3/S4) - 近况小+大球反常,优先级高于G6
    elif s4_7ball:
        # 信号S4: 近况<2.5+7球=观察保留 → 投7球 (ROI+1700%)
        rule = 'S4'
        bet_goals = [7]
        bet_type = 'single'
        goal_stake = 20
    elif s5_22:
        # 信号S5: Top1=3:0+3/4球双警惕+平>=5+近>=3.2 → 投2:2 10元 (ROI+910%)
        rule = 'S5'
        bet_goals = []
        bet_type = 'single'
        goal_stake = 0
    elif s3_6ball and g0 and g0 >= 10 and go.get(6, 99) < 30 and (min(h_win, a_win) < 1.65 if (h_win and a_win) else True):
        # 国内杯赛排除: 足总杯等强队不全力进攻, S3杯赛全miss
        SKIP_CUPS = ['足总杯', '联赛杯', '意大利杯', '德国杯', '法国杯', '国王杯', '葡萄牙杯', '荷兰杯']
        league = ''
        try:
            info = data.get('match_info', {})
            league = info.get('league', '') if isinstance(info, dict) else ''
        except: pass
        if any(cup in league for cup in SKIP_CUPS):
            pass  # 跳过国内杯赛, 不设rule
        else:
            # 信号S3: 近<2.5+6球保留 + o0≥10 + 6球<30 + HAD<1.65(极端强队) → 投6球
            rule = 'S3'
            bet_goals = [6]
            bet_type = 'single'
            goal_stake = 20
    elif g6_keep and g0 and g0 >= 12 and go.get(6, 99) < 12:
        # 信号G6: 三维排除6球=保留 + o0>=12 + 6球<12 → 投6球 (ROI+298%)
        # 赔率过滤: 6球≥12区间0%(1场0中)
        # ⚠️ 2026-05-26: 警惕造热→跳过(有警惕0/2 vs 无警惕2/2=100%)
        try:
            exc_check = analysis.get('exclusion', {})
            if any('警惕' in str(e.get('status','')) for e in exc_check.get('kept',[])):
                return {'action': 'skip', 'reason': 'G6跳过: 警惕造热(0/2全黑)'}
        except: pass
        rule = 'G6'
        bet_goals = [6]
        bet_type = 'single'
        goal_stake = 20
    elif n1_signal:
        # N1: g4<5.0+平赔跌10-20%→6球 (10场4/10=40% ROI+405%, 2026-06-03)
        # ⚠️ 未来若加CAND041(g2≥4.0+平跌→6球)需做互斥, 当前独用
        rule = 'N1'
        bet_goals = [6]
        bet_type = 'single'
        goal_stake = 20
    elif s2_5ball and (min(h_win, a_win) >= 1.65 if (h_win and a_win) else True):
        # 信号S2: 近况<2.5+5球警惕 + HAD最低赔≥1.65(过滤极端强队) → 投5球 (ROI+462%)
        # HAD过滤: 一方极强(<1.65)→大球难出, 科莫1.13+拉瓦勒1.63两场全miss
        # ⚠️ 2026-05-26: 2球警惕→跳过(含2球警惕0/2 vs 不含3/4=75%)
        try:
            exc_check = analysis.get('exclusion', {})
            for e in exc_check.get('kept', []):
                if e.get('goal') == '2球' and '警惕' in str(e.get('status', '')):
                    return {'action': 'skip', 'reason': 'S2跳过: 2球警惕(0/2全黑)'}
        except: pass
        rule = 'S2'
        bet_goals = [5]
        bet_type = 'single'
        goal_stake = 20
    elif h3_11 and not h_gap_far:
        # 信号H3: 平平↓+2球≥3.05+平<3.2+Top1=1:1+o0≤14 → 投1:1 30元 (ROI+405%)
        # ⚠️ V3.6验证: 推荐范围含2球时命中率50%+163%ROI vs 不含时22%+26% (2026-05-25)
        rec_goals_chk = analysis.get('recommended', {}).get('goals', [])
        if 2 not in rec_goals_chk:
            return {'action': 'skip', 'reason': f'H3跳过: V3.6推荐不含2球({rec_goals_chk})'}
        rule = 'H3'
        bet_goals = []
        bet_type = 'single'
        goal_stake = 0
    elif h5_11 and not h_gap_far:
        # 信号H5: 平平↓≥10%+count≥3+0球<10+Top1≠1:1+draw∈[2.85,3.05] → 投1:1 20元 (回测7场4中57% ROI+90%)
        rule = 'H5'
        bet_goals = []
        bet_type = 'single'
        goal_stake = 0
    elif h4_11:
        # 信号H4: 平平3次↓>10%+Top1≠1:1 → 已在前面触发(优先于R0), 此处保留为安全网
        rule = 'H4'
        bet_goals = []
        bet_type = 'single'
        goal_stake = 0
    elif h2_11 and not h_gap_far:
        # 信号H2: Top1=1:1+o0 11-13+平<3.5+2球铁保留/大热必死 → 投1:1 10元 (ROI+231%)
        rule = 'H2'
        bet_goals = []
        bet_type = 'single'
        goal_stake = 0
    elif g5_warn and g0 and g0 >= 12 and go.get(5, 99) <= 7:
        # 信号G5: 三维排除5球=警惕造热 + o0>=12 + 5球≤7 → 投5球 (ROI+135%)
        # 赔率过滤: 5球=7.8区间9场仅1中(11%), ≤7区间4场2中(50%)
        rule = 'G5'
        bet_goals = [5]
        bet_type = 'single'
        goal_stake = 20
    elif s6_2ball:
        # 信号S6: 0球>=19+2球4.0-4.4+近>=2.5+2球警惕 → 2球20+1:1 10 (ROI+100%)
        rule = 'S6'
        bet_goals = [2]
        bet_type = 'single'
        goal_stake = 20
    elif p1_signal:
        # 信号P1: 黄金1球+通用3球+平平不动 → 1球30元+0:1比分10元=40元 (10场8中80%, ROI+190%, 2026-05-30)
        try:
            so_p1 = data.get('score_odds', {})
            o01 = float(so_p1.get('00:01', 0) or 0)
            if o01 <= 0:
                return {'action': 'skip', 'reason': 'P1跳过: 0:1赔率缺失'}
        except:
            return {'action': 'skip', 'reason': 'P1跳过: 数据异常'}
        rule = 'P1'
        bet_goals = [1]
        bet_type = 'single'
        goal_stake = 30
        score_bets = [{'score': '0:1', 'stake': 10, 'odds': round(o01, 1)}]
    elif s8_signal:
        # 信号S8: g0<10+平平降>17%→假0:0恐慌盘, 11场7中64% ROI+172% (2026-05-28)
        # 投HAD方向比分10元 + 1球总进球20元 = 30元
        try:
            had2 = data.get('had', {}) or {}
            hw2 = float(had2.get('胜', 0) or 0)
            aw2 = float(had2.get('负', 0) or 0)
            if hw2 < aw2:
                bet_score = '1:0'
                so_key = '01:00'
            else:
                bet_score = '0:1'
                so_key = '00:01'
            so2 = data.get('score_odds', {})
            score_odds = float(so2.get(so_key, 0) or 0)
            if score_odds <= 0:
                return {'action': 'skip', 'reason': 'S8跳过: 比分赔率缺失'}
        except:
            return {'action': 'skip', 'reason': 'S8跳过: 数据异常'}
        rule = 'S8'
        bet_goals = [1]
        bet_type = 'single'
        goal_stake = 20
        score_bets = [{'score': bet_score, 'stake': 10, 'odds': score_odds}]
    elif s1_1ball:
        # 信号S1: 已停用 (2026-05-27)
        # 近况>2.5+1球变高共振 → 方向冲突(V3.6大球vs投1球), 4+5月仅1黑
        pass
    elif g4_22:
        # 信号G4: 4球警惕造热 + 平<3.5 + 双方防守>1.0 → 投2:2比分10元 (ROI+122%)
        rule = 'G4'
        bet_goals = []
        bet_type = 'single'
        goal_stake = 0
    elif not_11 and strong_over:
        rule = 'R3'
        bet_goals = [3, 4]
        bet_type = 'dual'
        goal_stake = 120
    elif not_11 and strong_under:
        rule = 'R4'
        bet_goals = [0, 2]
        bet_type = 'dual'
        goal_stake = 120
    elif x4_34:
        # 信号X4: 三维排除仅剩3球(警惕)+4球(保留) → 投4球20元 (3场1中33%)
        # ⚠️ 2026-05-26: 仅3球警惕(不含4球警惕)→跳过(0/2全黑, 比赛被压在3球)
        try:
            exc_check = analysis.get('exclusion', {})
            kept_map = {e.get('goal',''): str(e.get('status','')) for e in exc_check.get('kept',[])}
            if '警惕' in kept_map.get('3球','') and '警惕' not in kept_map.get('4球',''):
                return {'action': 'skip', 'reason': 'X4跳过: 仅3球警惕(0/2全黑)'}
        except: pass
        rule = 'X4'
        bet_goals = [4]
        bet_type = 'single'
        goal_stake = 20
    elif x5_45:
        # 信号X5: 建议投注+推荐4+5球+无规则 → 投4球20元 (10场6中60%, ROI+175%)
        # 2026-05-25: 5球变化>5%→跳过; 2026-05-26: 任一警惕造热→跳过(5场2中40%)
        if x5_5ball_surge:
            return {'action': 'skip', 'reason': f'X5跳过: 5球异动>5%'}
        if x5_4ball_warn:
            return {'action': 'skip', 'reason': 'X5跳过: 警惕造热(5场2中40%)'}
        rule = 'X5'
        bet_goals = [4]
        bet_type = 'single'
        goal_stake = 20
    elif x6_23:
        # 信号X6: 客让+2:3候选+客攻>主防 → 投2:3比分20元 (13场4中31%, ROI+592%)
        rule = 'X6'
        bet_goals = []
        bet_type = 'single'
        goal_stake = 0
    elif x2_35:
        # 信号X2: 三维排除仅剩3球+5球 → 投2球20元 (4场3中75%, 辅助填充)
        rule = 'X2'
        bet_goals = [2]
        bet_type = 'single'
        goal_stake = 20
    
    elif h1_score and h1_odds > 0 and not h_gap_far:
        # 信号H1: 大热必死+Top1比分+o0>=20 → 投Top1比分10元 (ROI+171%)
        # 2026-05-27: 移到最后, 仅在其他规则都不触发时作为兜底
        rule = 'H1'
        bet_goals = []
        bet_type = 'single'
        goal_stake = 0
    
    # ===== C1冷推: 博冷比分40元 (V3过滤, 2026-06-07双过滤: 反向排除+去零封) =====
    cold_sb = None
    try:
        from v36_analyzer import analyze_match as v36_cold
        cold_analysis = v36_cold(data)
        csb = cold_analysis.get('score_bet')
        if csb and csb.get('strategy') == '无推荐博冷':
            c_odds = csb.get('odds', 0)
            c_bet_goals = csb['goals']
            c_score = csb['score']  # 格式: "1-2"
            c_g0 = float(data.get('total_goals', {}).get('0球', 99) or 99)
            c_ok = True
            if c_bet_goals >= 5 and c_g0 < 25 and c_odds <= 20: c_ok = False
            if c_bet_goals == 4 and 10 < c_g0 < 30 and c_odds <= 20: c_ok = False
            if c_bet_goals <= 2 and c_g0 >= 15 and c_odds <= 20: c_ok = False
            if c_odds > 100: c_ok = False
            if 15 < c_odds <= 30: c_ok = False
            # V6.5 反向排除过滤: 冷推比分在前2排除名单→跳过 (19场3全黑, ROI+106pp)
            if c_ok and c_score:
                sc_list = cold_analysis.get('score_candidates', [])
                all_sc = []
                for sc in sc_list:
                    for s in sc.get('scores', []):
                        all_sc.append(s.get('score', ''))
                if len(all_sc) >= 2 and c_score in set(all_sc[:2]):
                    c_ok = False
            # V6.5 去零封过滤: 4-0/0-4全黑 (6场0中)→跳过
            if c_ok and c_score in ('4-0', '0-4'):
                c_ok = False
            if c_ok:
                cold_sb = {'score': csb['score'], 'odds': round(c_odds, 1), 'stake': 40, 'tag': '冷推'}
    except:
        pass
    
    if not rule:
        if cold_sb:
            rule = 'C1'
            bet_goals = []
            bet_type = 'single'
            goal_stake = 0
            score_bets = [cold_sb]
            total_score_stake = cold_sb['stake']
        # D1: 方向冲突1:1信号 (2026-06-16新增, 3/3=100%)
        # 因果链: Step0方向大球 → 5/6/7球全排除 → 只剩2球 → top_sc=1:1
        # T系列: 让胜陷阱 (2026-06-17新增, 前置: 让胜降>10%+display=1:1+rs/hw<1.6)
        elif (t_info := _check_t_series(data)) is not None:
            hw_t, rs_t, is_give = t_info
            if hw_t < 3.0 and not is_give:
                rule = 'T1'
                t_sb = _build_t_bet('T1', so)
            elif hw_t >= 4.0 and not is_give:
                rule = 'T2'
                t_sb = _build_t_bet('T2', so)
            elif hw_t > 5.0 and is_give:
                rule = 'T3'
                t_sb = _build_t_bet('T3', so)
            else:
                rule = None
            if rule:
                bet_goals = []
                bet_type = 'single'
                goal_stake = 0
                if isinstance(t_sb, list):
                    score_bets = t_sb
                    total_score_stake = sum(s['stake'] for s in t_sb)
                else:
                    score_bets = [t_sb]
                    total_score_stake = t_sb['stake']
        # D1: 方向冲突1:1信号 (2026-06-16新增, 3/3=100%)
        elif _check_d1(analysis, data, v36_dir, g0, so):
            d1_sb = _build_d1_bet(so)
            rule = 'D1'
            bet_goals = []
            bet_type = 'single'
            goal_stake = 0
            score_bets = [d1_sb]
            total_score_stake = d1_sb['stake']
        # B1: 让胜真信穿盘 (2026-06-17新增, 3/3 穿盘, 前置: 让胜降>10%+display=3:0+rs/hw<1.6+hw<1.5)
        elif _check_b1(data) is not None:
            rule = 'B1'
            b1_sb = _build_b1_bet(so)
            bet_goals = []
            bet_type = 'single'
            goal_stake = 0
            score_bets = b1_sb
            total_score_stake = sum(s['stake'] for s in b1_sb)
        else:
            return {'action': 'skip', 'reason': '无匹配投注规则'}
    
    # 进球数投注
    goal_odds = {g: go.get(g) for g in bet_goals if go.get(g)}
    
    # 比分投注
    so_data = data.get('score_odds', {})
    score_by_goals = {}
    for sk, ov in so_data.items():
        try: ov = float(ov)
        except: continue
        if ov <= 0: continue
        parts = sk.split(':')
        if len(parts) != 2: continue
        try: sh, sa = int(parts[0]), int(parts[1])
        except: continue
        g = sh + sa
        if g not in score_by_goals: score_by_goals[g] = []
        score_by_goals[g].append((f'{sh}:{sa}', ov))
    
    def _get_score_odds(sc):
        """从score_odds获取格式化比分的赔率 1:1 -> 01:01"""
        key = f'{int(sc.split(":")[0]):02d}:{int(sc.split(":")[1]):02d}'
        v = so_data.get(key, 0)
        try: return float(v)
        except: return 0
    
    if rule == 'R0':
        # R0: 纯0球20元, 无比分保底 (2026-05-18简化)
        conf_tag = ''
        if pp_boost:
            conf_tag = ' 🔥平平降>5%'
        elif had_boost:
            conf_tag = ' 💚HAD平赔降'
        elif had_weak:
            conf_tag = ' ⚠️HAD主胜升'
    elif rule == 'R1':
        # R1: 纯买3:0比分 20元
        score_key = '3:0'
        ho = _get_score_odds(score_key)
        if ho > 0:
            score_bets.append({'score': score_key, 'odds': round(ho, 1), 'stake': 20, 'tag': 'R1'})
        conf_tag = ''
    elif rule == 'G4':
        # G4: 4球警惕造热+平<3.5+双方防守>1.0 → 纯买2:2比分 10元 (ROI+122%)
        ho = _get_score_odds('2:2')
        if ho > 0:
            score_bets.append({'score': '2:2', 'odds': round(ho, 1), 'stake': 10, 'tag': '4球警惕'})
        conf_tag = ''
    elif rule == 'H1':
        # H1: 大热必死+Top1比分+o0>=20 → 纯买Top1比分 10元 (ROI+171%)
        score_bets.append({'score': h1_score, 'odds': round(h1_odds, 1), 'stake': 10, 'tag': '大热必死'})
        conf_tag = ''
    elif rule == 'H2':
        # H2: Top1=1:1+o0 11-13+平<3.5+2球铁保留/大热 → 纯买1:1 10元 (ROI+231%)
        ho = _get_score_odds('1:1')
        if ho > 0:
            score_bets.append({'score': '1:1', 'odds': round(ho, 1), 'stake': 20, 'tag': 'H2铁保留'})
        conf_tag = ''
    elif rule == 'S5':
        # S5: Top1=3:0+3/4球双警惕+平>=5+近>=3.2 → 纯买2:2 10元 (ROI+910%)
        ho = _get_score_odds('2:2')
        if ho > 0:
            score_bets.append({'score': '2:2', 'odds': round(ho, 1), 'stake': 10, 'tag': '双警惕2:2'})
        conf_tag = ''
    elif rule == 'S6':
        # S6: 黄金2球+2球警惕 → 纯2球20元
        conf_tag = ''
    elif rule == 'H3':
        # H3: 平平↓+2球≥3.05+平<3.2+Top1=1:1+o0≤14 → 纯买1:1 30元 (ROI+405%)
        ho = _get_score_odds('1:1')
        if ho > 0:
            score_bets.append({'score': '1:1', 'odds': round(ho, 1), 'stake': 30, 'tag': '平平↓压盘'})
        conf_tag = ''
    elif rule == 'H4':
        # H4: 平平3次↓>10%+Top1≠1:1 → 纯买1:1 20元 (旧版, 已停用)
        ho = _get_score_odds('1:1')
        if ho > 0:
            score_bets.append({'score': '1:1', 'odds': round(ho, 1), 'stake': 20, 'tag': 'H4平淡↓'})
        conf_tag = ''
    elif rule == 'H5':
        # H5: 平平↓≥10%+count≥3+0球<10+Top1≠1:1+draw∈[2.85,3.05] → 纯买1:1 20元 (回测7场4中57%)
        ho = _get_score_odds('1:1')
        if ho > 0:
            score_bets.append({'score': '1:1', 'odds': round(ho, 1), 'stake': 20, 'tag': 'H5平赔甜区'})
        conf_tag = ''
    elif rule == 'S3':
        # S3: 近况<2.5+6球保留 → 纯6球20元 (ROI+330%)
        conf_tag = ''
    # S1已停用 (2026-05-27)
    elif rule == 'X6':
        # X6: 客让+2:3候选+客攻>主防 → 买2:3比分20元 + 5球对冲5元 (2026-05-22)
        if x6_23_odds > 0:
            score_bets.append({'score': '2:3', 'odds': round(x6_23_odds, 1), 'stake': 20, 'tag': '客让2:3'})
        # 比分防御伞: 6元买5球, 防爆冷(1:4/0:5/3:2)
        bet_goals = [5]
        bet_type = 'single'
        goal_stake = 6
        conf_tag = ''
    else:
        # 纯总进球投注(无比分保护), 2026-05-18改为纯20元
        conf_tag = ''
    
    # ===== 比分保护: 每个进球投注+10元买V3.6首选比分 =====
    if bet_goals and goal_stake > 0 and rule != 'P1':
        try:
            rec = analysis.get('recommended', {})
            fs = rec.get('filtered_scores', [])
            so = data.get('score_odds', {})
            # 预统计每个赔率出现次数(同赔比分=噪音,回测0%命中)
            from collections import Counter
            odds_counter = Counter()
            for vv in so.values():
                try: odds_counter[round(float(vv),1)] += 1
                except: pass
            for g in bet_goals:
                for f in fs:
                    if f.get('goals') == g:
                        sc = f.get('score', '')
                        parts = sc.split('-')
                        odds_key = f'{int(parts[0]):02d}:{int(parts[1]):02d}'
                        odds_val = float(so.get(odds_key, so.get(sc.replace('-',':'), 0)) or 0)
                        # 🔑 同赔比分跳过保护(赔率重复=市场无方向,0%命中)
                        if odds_val > 0 and odds_counter.get(round(odds_val,1), 0) >= 2:
                            break
                        if odds_val > 0:
                            score_bets.append({
                                'score': sc.replace('-', ':'),
                                'odds': round(odds_val, 1),
                                'stake': 10,
                                'tag': '比分保护'
                            })
                        break  # 每个进球只取首选
        except:
            pass
    
    total_score_stake = sum(s['stake'] for s in score_bets)
    
    summary_text = ''
    if rule == 'G4':
        summary_text = '2:2比分10元'
    elif rule == 'H1':
        summary_text = f'{h1_score}比分10元'
    elif rule == 'H2':
        summary_text = '1:1比分10元'
    elif rule == 'H3':
        summary_text = '1:1比分30元'
    elif rule == 'D1':
        summary_text = '1:1比分10元'
    elif rule == 'T1':
        summary_text = '1:1比分10元'
    elif rule == 'T2':
        summary_text = '0:2比分10元'
    elif rule == 'T3':
        summary_text = '0:0+2:2各10元 [T3覆盖大球规则: 让胜陷阱因果链更强(2/2)]'
    elif rule == 'B1':
        summary_text = '3:1+4:1各10元'
    elif rule and 'B1' in rule:
        # R1+B1等共存: B1覆盖R1的3:0
        summary_text = '3:1+4:1各10元 [B1覆盖R1: 让胜真信因果链更强(2/2)]'
    elif bet_goals:
        summary_text = f"{'单选' if bet_type=='single' else '双选'}{'+'.join(str(g) for g in bet_goals)}球 {goal_stake}元"
    SKIP_SCORE_SUMMARY = {'G4', 'H1', 'H2', 'H3', 'D1', 'T1', 'T2', 'T3', 'B1'}
    if score_bets and not any(x in str(rule) for x in SKIP_SCORE_SUMMARY):
        if summary_text: summary_text += ' + '
        summary_text += f"{len(score_bets)}个比分{'保底' if rule=='R0' else '投注'}{total_score_stake}元"
    summary_text += conf_tag
    if s7_dual:
        summary_text += ' 🔥双确认(S6+S7)'
    
    # 2026-05-18 停用低ROI信号
    DISABLED = {'S6', 'H4', 'G4', 'R3', 'R4', 'X2', 'X5', 'G5', 'H5', 'G7'}  # G7: 1场0/1 ROI-100%, F:0触发
    if rule in DISABLED:
        return {'action': 'skip', 'reason': f'{rule}已停用(低ROI)'}
    
    # ⚠️ Shadow Voting: 大球方向触发了小球/闷平信号→风控减半（2026-05-22）
    if '大球' in v36_dir and rule in ['H3']:
        goal_stake = goal_stake // 2
        if goal_stake % 2 == 1: goal_stake += 1  # 竞彩2元倍数对齐
        for sb in score_bets:
            sb['stake'] = sb['stake'] // 2
            if sb['stake'] % 2 == 1: sb['stake'] += 1
        total_score_stake = sum(s['stake'] for s in score_bets)
        orig_rule = rule
        rule = f'{rule}(风控减半)'
        # 拦截日志
        try:
            mi = data.get('match_info', {}) or {}
            mn = mi.get('match_num_str', '') if isinstance(mi, dict) else ''
            ht = mi.get('home_team', '?') if isinstance(mi, dict) else '?'
            at = mi.get('away_team', '?') if isinstance(mi, dict) else '?'
            _trace_log('SHADOW-LOCK', f'{mn} {ht}vs{at} 触发{orig_rule}但Step0={v36_dir}→资金减半')
        except:
            pass
    
    # ⚠️ 大球规则+V3.6不含+赔率异动→跳过 (2026-05-25)
    # V3.6不含+赔率↑>10%: 市场推离+共识一致→危险(6球>+10%仅4%命中)
    # V3.6不含+赔率↓: 市场拉客但V3.6不推→诱盘(8场38%ROI)→跳过
    BIG_RULES = {'S2','G5','G6','G7','F','S3','X4','X5','X6'}
    if rule in BIG_RULES and bet_goals:
        try:
            rec_goals = analysis.get('recommended', {}).get('goals', [])
            main_g = bet_goals[0]
            if main_g not in rec_goals:
                ttg = data.get('ttg_change', {})
                gk = f'{main_g}球'
                ch_pct = float(ttg.get(gk, {}).get('change_pct', 0) or 0)
                if ch_pct <= 0:
                    mi = data.get('match_info', {}) or {}
                    mn = mi.get('match_num_str', '') if isinstance(mi, dict) else ''
                    return {'action': 'skip', 'reason': f'{rule}跳过: V3.6不含+赔率↓({ch_pct:+.1f}%)'}
                if ch_pct > 10:
                    mi = data.get('match_info', {}) or {}
                    mn = mi.get('match_num_str', '') if isinstance(mi, dict) else ''
                    return {'action': 'skip', 'reason': f'{rule}跳过: V3.6不含+赔率暴涨({ch_pct:+.1f}%)'}
        except:
            pass
    
    # ⚠️ Staking Tier: 按历史ROI分级调整仓位（2026-05-22）
    # 排除X6(已有防御伞对冲，不升级)
    tier_goal_stake = _get_stake_by_tier(rule.replace('(风控减半)', '')) if 'X6' not in rule else 6
    # 保持规则内原设定为主，tier只调整纯进球投注
    if bet_goals and goal_stake > 0:
        if goal_stake < tier_goal_stake:  # 原设定比tier小，升级
            goal_stake = tier_goal_stake
    
    # ⚠️ 相似比赛甜区翻倍 (2026-05-26)
    # 投注目标在相似比赛中占比10-20%→92%命中→仓位翻倍
    if bet_goals and goal_stake > 0:
        try:
            cache_key = '_sim_sweet_cache'
            if cache_key not in data:
                from sporttery_web import find_similar_matches
                sims = find_similar_matches(data, top_n=8)
                sweet_map = {}
                if len(sims) >= 3:
                    from collections import Counter
                    gc = Counter()
                    for s in sims:
                        g = s.get('total_goals', 0)
                        if g is not None and g >= 0: gc[g] += 1
                    tp = sum(gc.values())
                    for goal in range(0, 8):
                        pct = gc.get(goal, 0) / tp if tp > 0 else 0
                        sweet_map[goal] = pct
                data[cache_key] = sweet_map
            else:
                sweet_map = data[cache_key]
            
            if sweet_map:
                bp = sweet_map.get(bet_goals[0], 0)
                if 0.1 < bp <= 0.2 and rule not in ('S8', 'G2', 'P1'):
                    goal_stake = goal_stake * 2
                    rule = f'{rule}(甜区翻倍)'
                    _trace_log('SWEET-X2', f'{rule} sim占比={bp:.0%}→仓位翻倍')
        except:
            pass
    
    # ⚠️ 相似温区跳过 (2026-05-26)
    # 投注目标在相似中出现≥2次(≥25%)=过热 → 跳过(除S7/S8/G2/P1/D2免疫)
    # 5月回测: 3场全黑零误伤, 命中68%→81%
    if rule not in ('S7','S8','G2','P1','D2') and bet_goals and goal_stake > 0:
        try:
            cache_key = '_sim_sweet_cache'
            sweet_map = data.get(cache_key, {})
            if sweet_map:
                bp = sweet_map.get(bet_goals[0], -1)
                if bp >= 0.25:  # ≥2次/8场
                    return {'action': 'skip', 'reason': f'{rule}跳过: 相似过热({bp:.0%}≥25%)'}
        except:
            pass
    
    # ⚠️ H类比分冷区跳过 (2026-05-26)
    # H2/H3/H5比分投注: 对应总进球在相似中出现<2次→跳过(0/3全黑 vs 2次+4/6=67%)
    if rule in ('H2','H3','H5') and score_bets:
        try:
            from sporttery_web import find_similar_matches
            sims = find_similar_matches(data, top_n=8)
            if len(sims) >= 3:
                sim_tgs = [s.get('record',{}).get('home_score',0)+s.get('record',{}).get('away_score',0) for s in sims]
                first_score = score_bets[0].get('score','')
                parts = first_score.split(':')
                if len(parts) == 2:
                    bet_tg = int(parts[0]) + int(parts[1])
                    cnt = sum(1 for g in sim_tgs if g == bet_tg)
                    if cnt < 2:
                        return {'action': 'skip', 'reason': f'{rule}跳过: 比分冷区({bet_tg}球出现{cnt}次<2次)'}
        except:
            pass
    
    # C1冷推与现有规则共存：追加冷推比分
    if cold_sb and rule != 'C1':
        score_bets.append(cold_sb)
        total_score_stake += cold_sb['stake']
        rule = f'{rule}+C1'
    
    # D1: 方向冲突1:1信号 — 与现有规则共存时追加1:1比分 (2026-06-16新增)
    if rule and 'D1' not in rule and _check_d1(analysis, data, v36_dir, g0, so):
        d1_sb = _build_d1_bet(so)
        score_bets.append(d1_sb)
        total_score_stake += d1_sb['stake']
        rule = f'{rule}+D1'
    
    # T系列: 让胜陷阱 — 与现有规则共存时追加比分 (2026-06-17新增)
    # ⚠️ T3优先: 当主规则推大球(>=3球)时, T3覆盖替代(因果链更强)
    t_info = _check_t_series(data)
    has_big_goal = bool(bet_goals) and any(g >= 3 for g in bet_goals)
    if rule and 'T1' not in rule and 'T2' not in rule and 'T3' not in rule and t_info is not None:
        hw_t, rs_t, is_give = t_info
        t_rule = None
        if hw_t < 3.0 and not is_give: t_rule = 'T1'
        elif hw_t >= 4.0 and not is_give: t_rule = 'T2'
        elif hw_t > 5.0 and is_give: t_rule = 'T3'
        if t_rule:
            if has_big_goal and t_rule == 'T3':
                # T3覆盖: 让胜陷阱因果链强于大球规则, 完全替代
                t_sb = _build_t_bet('T3', so)
                t_list = t_sb if isinstance(t_sb, list) else [t_sb]
                overridden = rule  # 记录被覆盖的规则
                bet_goals = []
                goal_stake = 0
                score_bets = t_list
                total_score_stake = sum(s['stake'] for s in t_list)
                rule = 'T3'
                # 在第一个bet的tag里记录覆盖决策
                if t_list:
                    t_list[0]['tag'] = f'T3覆盖{overridden}: 让胜陷阱因果链更强(2/2)'
            elif not has_big_goal:
                t_sb = _build_t_bet(t_rule, so)
                t_list = t_sb if isinstance(t_sb, list) else [t_sb]
                score_bets.extend(t_list)
                total_score_stake += sum(s['stake'] for s in t_list)
                rule = f'{rule}+{t_rule}'
    
    # B1: 让胜真信穿盘 — 与现有规则共存时追加3:1+4:1 (2026-06-17新增)
    # ⚠️ B1覆盖R1: R1推3:0但B1因果链说3:0不出, 移除3:0保留3:1+4:1
    if rule and 'B1' not in rule and _check_b1(data) is not None:
        b1_sb = _build_b1_bet(so)
        # 过滤掉R1的3:0比分投注(B1的因果链明确说3:0不会出)
        score_bets = [s for s in score_bets if not (s.get('score') == '3:0' and s.get('tag', '') == 'R1')]
        total_score_stake = sum(s['stake'] for s in score_bets)
        score_bets.extend(b1_sb)
        total_score_stake += sum(s['stake'] for s in b1_sb)
        rule = f'{rule}+B1'
        # B1覆盖R1: 重建summary
        if not bet_goals:
            summary_text = '3:1+4:1各10元 [B1覆盖R1: 让胜真信因果链更强(2/2)]'
    
    # 重建summary
    if bet_goals:
        base_summary = f"{'单选' if bet_type=='single' else '双选'}{'+'.join(str(g) for g in bet_goals)}球 {goal_stake}元"
        if score_bets:
            base_summary += f" + {len(score_bets)}个比分投注{total_score_stake}元"
        base_summary += conf_tag
        if s7_dual:
            base_summary += ' 🔥双确认(S6+S7)'
        summary_text = base_summary
    
    return {
        'action': 'bet',
        'rule': rule,
        'bet_type': bet_type,
        'goal_bet': {
            'goals': bet_goals,
            'stake': goal_stake,
            'odds': {str(g): round(o, 1) for g, o in goal_odds.items()},
            **({'stake_split': {0: 20, 2: 10}} if rule == 'G2' else {}),
        },
        'score_bets': score_bets,
        'score_stake': total_score_stake,
        'total_stake': goal_stake + total_score_stake,
        'summary': summary_text,
        'pp_boost': pp_boost if rule == 'R0' else False,
        's7_dual': s7_dual,
    }


def read_framework():
    """读取推理流水框架文档"""
    try:
        with open(FRAMEWORK_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f'读取框架文档失败：{str(e)}'


def calc_recent_form(data):
    """计算近况（从preview.recent计算主客队近5场平均进球）"""
    try:
        preview = data.get('preview', {})
        recent = preview.get('recent', {})
        
        home_recent = recent.get('home', {}).get('matchList', [])
        away_recent = recent.get('away', {}).get('matchList', [])
        
        if not home_recent or not away_recent:
            return None, None, None
        
        home_goals = []
        for m in home_recent:
            gh = m.get('homeTeamFullCourtGoalCnt')
            if gh is not None:
                home_goals.append(float(gh))
        
        away_goals = []
        for m in away_recent:
            gw = m.get('awayTeamFullCourtGoalCnt')
            if gw is not None:
                away_goals.append(float(gw))
        
        if not home_goals or not away_goals:
            return None, None, None
        
        home_avg = sum(home_goals) / len(home_goals)
        away_avg = sum(away_goals) / len(away_goals)
        combined = (home_avg + away_avg) / 2
        
        return round(home_avg, 1), round(away_avg, 1), round(combined, 1)
    except Exception as e:
        return None, None, None


def extract_odds(data):
    """提取总进球赔率"""
    try:
        # 尝试从 total_goals 字段读取
        tg = data.get('total_goals', {})
        if tg:
            return tg
        
        # 尝试从 odds 字段读取
        odds = data.get('odds', {}).get('total_goals', {})
        if odds:
            return odds
        
        return {}
    except:
        return {}


def extract_hhad_odds(data):
    """提取让球盘赔率"""
    try:
        hhad = data.get('hhad', {})
        if hhad:
            return hhad
        return {}
    except:
        return {}


def extract_had_odds(data):
    """提取胜平负赔率"""
    try:
        had = data.get('had', {})
        if had:
            return had
        return {}
    except:
        return {}


def analyze_odds_changes(data):
    """分析赔率变化（对比initial_odds和realtime_odds）"""
    try:
        # 尝试从 ttg_change 字段读取（已有变化统计）
        ttg_change = data.get('ttg_change', {})
        if ttg_change:
            changes = {}
            for goal in ['0球', '1球', '2球', '3球', '4球', '5球', '6球', '7球']:
                tc = ttg_change.get(goal, {})
                count = tc.get('count', 0)
                pct = tc.get('change_pct', 0)
                
                if count > 0 and pct != 0:
                    changes[goal] = {
                        'count': count,
                        'direction': '↓' if pct < 0 else '↑',
                        'pct': round(abs(pct), 1)
                    }
                else:
                    changes[goal] = {'count': 0, 'direction': '→', 'pct': 0}
            return changes
        
        # 如果没有 ttg_change，尝试对比 initial_odds 和 realtime_odds
        initial = data.get('initial_odds', {}).get('total_goals', {})
        realtime = data.get('realtime_odds', {}).get('total_goals', {})
        
        if not initial or not realtime:
            return {}
        
        changes = {}
        for goal in ['0球', '1球', '2球', '3球', '4球', '5球', '6球', '7球']:
            init_val = float(initial.get(goal, 0))
            real_val = float(realtime.get(goal, 0))
            
            if init_val == 0 or real_val == 0:
                changes[goal] = {'count': 0, 'direction': '→', 'pct': 0}
                continue
            
            # 计算变化次数（简化：只判断是否变化）
            if abs(real_val - init_val) > 0.01:
                changes[goal] = {
                    'count': 1,  # 简化：只记录是否变化
                    'direction': '↓' if real_val < init_val else '↑',
                    'pct': round((real_val - init_val) / init_val * 100, 1)
                }
            else:
                changes[goal] = {'count': 0, 'direction': '→', 'pct': 0}
        
        return changes
    except Exception as e:
        return {}


def generate_prompt(match_id):
    """生成AI推理Prompt"""
    # 1. 读取框架文档
    framework_text = read_framework()
    
    # 2. 读取比赛数据
    data_file = os.path.join(DATA_DIR, f'{match_id}.json')
    if not os.path.exists(data_file):
        return None, f'比赛数据不存在：{data_file}'
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return None, f'读取比赛数据失败：{str(e)}'
    
    # 3. 提取数据
    home_form, away_form, total_form = calc_recent_form(data)
    odds = extract_odds(data)
    hhad = extract_hhad_odds(data)
    had = extract_had_odds(data)
    changes = analyze_odds_changes(data)
    
    # 4. 组合Prompt
    prompt = "# 足球比分推理任务\n\n"
    prompt += "## 推理框架\n\n"
    prompt += "请严格按照以下框架进行推理：\n\n"
    prompt += framework_text + "\n\n---\n\n"
    prompt += "## 当前比赛数据\n\n"
    
    # 添加比赛信息
    match_info = data.get('match_info', {})
    if match_info:
        prompt += f"**比赛**：{match_info.get('home_team', '未知')} VS {match_info.get('away_team', '未知')}\n"
        prompt += f"**联赛**：{match_info.get('league', '未知')}\n"
        prompt += f"**时间**：{match_info.get('time', '未知')}\n\n"
    
    # 添加近况
    prompt += "### 近况数据\n"
    if home_form is not None:
        prompt += f"- 主队近况：{home_form} 球/场（近5场）\n"
        prompt += f"- 客队近况：{away_form} 球/场（近5场）\n"
        prompt += f"- 近况合计：{total_form} 球\n"
        prompt += "- 近况区间："
        
        if total_form < 2.0:
            prompt += "极低（预期0-1球）\n"
        elif total_form < 2.5:
            prompt += "偏低（预期1-2球）\n"
        elif total_form < 3.5:
            prompt += "正常（预期2-3球）\n"
        elif total_form < 4.0:
            prompt += "偏高（预期3-4球）\n"
        else:
            prompt += "极高（预期4+球）\n"
    else:
        prompt += "（数据不足）\n"
    
    # 添加赔率
    prompt += "\n### 总进球赔率\n"
    if odds:
        for goal in ['0球', '1球', '2球', '3球', '4球', '5球', '6球', '7球']:
            val = odds.get(goal, 'N/A')
            prompt += f"- **{goal}**：{val}\n"
    else:
        prompt += "（数据不足）\n"
    
    # 添加赔率变化
    prompt += "\n### 赔率变化统计\n"
    if changes:
        for goal in ['0球', '1球', '2球', '3球', '4球', '5球', '6球', '7球']:
            ch = changes.get(goal, {})
            count = ch.get('count', 0)
            direction = ch.get('direction', '→')
            pct = ch.get('pct', 0)
            
            if count > 0:
                prompt += f"- **{goal}**：变化{count}次 {direction}{pct}%\n"
            else:
                prompt += f"- **{goal}**：变化0次 →\n"
    else:
        prompt += "（数据不足，假设全部0次变化）\n"
        # 如果没有变化数据，假设全部0次
        for goal in ['0球', '1球', '2球', '3球', '4球', '5球', '6球', '7球']:
            prompt += f"- **{goal}**：变化0次 →\n"
    
    # 添加让球盘
    prompt += "\n### 让球盘（让球(+/-)胜平负）\n"
    if hhad:
        prompt += f"- 让球：{hhad.get('让球', 'N/A')}\n"
        prompt += f"- 让胜：{hhad.get('让胜', 'N/A')}\n"
        prompt += f"- 让平：{hhad.get('让平', 'N/A')}\n"
        prompt += f"- 让负：{hhad.get('让负', 'N/A')}\n"
    else:
        prompt += "（数据不足）\n"
    
    # 添加胜平负
    prompt += "\n### 胜平负\n"
    if had:
        prompt += f"- 主胜：{had.get('主胜', 'N/A')}\n"
        prompt += f"- 平局：{had.get('平', 'N/A')}\n"
        prompt += f"- 客胜：{had.get('客胜', 'N/A')}\n"
    else:
        prompt += "（数据不足）\n"
    
    # 添加任务说明
    prompt += """
---

## 任务要求

请严格按照"推理流水框架"的7个步骤进行推理，并输出：

1. **第一步**：判断近况区间
2. **第二步**：理论盘口 vs 实际盘口
3. **第三步**：赔率变化分析
4. **第四步**：排除法
5. **第五步**：聚焦推荐（总进球数 + 让球）
6. **第六步**：置信度评定
7. **第七步**：推荐比分

## 输出格式

请使用Markdown格式，每个步骤用 `### 第X步：...` 开头。

最后给出：
- **推荐总进球数**：X球（置信度）
- **推荐让球**：让胜/让平/让负（置信度）
- **推荐比分**：X-X（优先），X-X（备选）

---

**请开始推理！**
"""
    
    return prompt, None


# ── 路由定义 ──────────────────────────────────────

@bp.route('/api/ai/generate_prompt/<match_id>', methods=['GET'])
def generate_prompt_api(match_id):
    """生成AI推理Prompt的API"""
    prompt, error = generate_prompt(match_id)
    
    if error:
        return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({
        'success': True,
        'match_id': match_id,
        'prompt': prompt,
        'message': 'Prompt生成成功，请复制到AI对话框中'
    })


@bp.route('/api/ai/reasoning', methods=['POST'])
def ai_reasoning_api():
    """接收AI推理结果并保存（可选功能）"""
    try:
        body = request.get_json()
        match_id = body.get('match_id')
        reasoning = body.get('reasoning', '')
        
        if not match_id or not reasoning:
            return jsonify({'success': False, 'error': '参数错误'}), 400
        
        # 保存到文件（可选）
        output_file = f'ai_reasoning_result_{match_id}.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(reasoning)
        
        return jsonify({'success': True, 'file': output_file})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── V3.6 自动推理分析 ──
@bp.route('/v36/analyze/<match_id>', methods=['GET', 'POST'])
def v36_analyze(match_id):
    """执行V3.6完整推理流程。POST时优先使用请求体中的ttg_hitrates。"""
    try:
        data_file = os.path.join(DATA_DIR, f'{match_id}.json')
        if not os.path.exists(data_file):
            return jsonify({'success': False, 'error': f'比赛{match_id}数据不存在'}), 404
        
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # If POST, merge ttg_hitrates and odds hitrate from request body
        if request.method == 'POST' and request.is_json:
            body = request.get_json(silent=True) or {}
            if 'ttg_hitrates' in body:
                # 前端JSON key是字符串, 转为整数key (兼容_get_change_info查找)
                raw = body['ttg_hitrates']
                data['_change_hitrate'] = {int(k) if k.isdigit() else k: v for k, v in raw.items()} if isinstance(raw, dict) else raw
        
        # V3.6 fix: 独立加载命中率数据（强制刷新缓存，确保与_scores.json同步）
        try:
            import sporttery_web
            sporttery_web._odds_hitrate_cache = None
            sporttery_web._change_hitrate_cache = None
            sporttery_web._score_hitrate_cache = None
            from sporttery_web import _build_odds_hitrate, _build_change_hitrate
            if '_odds_hitrate' not in data:
                data['_odds_hitrate'] = _build_odds_hitrate()
            # 独立加载覆盖（确保key为整数，避免前端JSON序列化问题）
            data['_change_hitrate'] = _build_change_hitrate()
        except:
            pass
        
        import importlib, sys
        if 'v36_analyzer' in sys.modules:
            importlib.reload(sys.modules['v36_analyzer'])
        if 'ai_reasoning' in sys.modules:
            importlib.reload(sys.modules['ai_reasoning'])
        from v36_analyzer import analyze_match
        result = analyze_match(data)
        
        # ===== 投注策略 =====
        result['betting'] = compute_betting(data, result)
        
        # 包含H9预检测结果 (2026-06-21)
        h9_analysis = data.get('_h9_analysis')
        
        return jsonify({'success': True, 'analysis': result, 'h9_analysis': h9_analysis})
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()}), 500


# ── 批量推荐 ──
@bp.route('/v36/batch_recommend', methods=['GET'])
def v36_batch_recommend():
    """批量分析所有未赛比赛，返回投注建议"""
    try:
        import glob
        from datetime import datetime as dt
        import sporttery_web
        sporttery_web._odds_hitrate_cache = None
        sporttery_web._change_hitrate_cache = None
        sporttery_web._score_hitrate_cache = None
        from sporttery_web import _build_odds_hitrate, _build_change_hitrate
        _oh = _build_odds_hitrate()
        _ch = _build_change_hitrate()
        
        # 先抓取最新比赛数据
        from sporttery_api import SportteryAPI
        api = SportteryAPI()
        from datetime import timedelta
        today_str = dt.now().strftime('%Y-%m-%d')
        end_str = (dt.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        list_data = api.get_match_list(today_str, end_str)
        new_matches = []
        if isinstance(list_data, dict):
            for k, v in list_data.items():
                if isinstance(v, dict):
                    v['_mid'] = k
                    new_matches.append(v)
        
        os.makedirs(DATA_DIR, exist_ok=True)
        fetch_count = 0
        fetched_names = []
        for m in new_matches:
            mid = str(m.get('_mid', ''))
            fp = os.path.join(DATA_DIR, f'{mid}.json')
            try:
                api.fetch_and_save(mid)
                fetch_count += 1
                with open(fp, 'r', encoding='utf-8') as f:
                    new_data = json.load(f)
                mi = new_data.get('match_info', {})
                name = f"{mi.get('match_num_str','')} {mi.get('home_team','?')} vs {mi.get('away_team','?')}"
                fetched_names.append(name)
            except: pass
        
        # 读取已赛比分
        scores_file = os.path.join(os.path.dirname(DATA_DIR), '分析模板', '_scores.json')
        try:
            with open(scores_file, 'r', encoding='utf-8') as f:
                scores = json.load(f)
        except:
            scores = {}
        
        files = sorted(glob.glob(os.path.join(DATA_DIR, '20*.json')), reverse=True)
        
        signals = []
        weekday_cn = ['周一','周二','周三','周四','周五','周六','周日']
        today_idx = dt.now().weekday()
        today_wd = weekday_cn[today_idx]
        now = dt.now()
        
        for fp in files:
            mid = os.path.basename(fp).replace('.json', '')
            # 跳过已赛
            if mid in scores:
                sr = scores[mid]
                if sr.get('home_score') is not None and isinstance(sr.get('home_score'), (int, float)):
                    continue
            
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                continue
            
            if not data.get('match_info', {}).get('match_num_str'):
                continue
            
            data['_odds_hitrate'] = _oh
            data['_change_hitrate'] = _ch
            
            try:
                import importlib, sys
                if 'v36_analyzer' in sys.modules:
                    importlib.reload(sys.modules['v36_analyzer'])
                if 'ai_reasoning' in sys.modules:
                    importlib.reload(sys.modules['ai_reasoning'])
                from v36_analyzer import analyze_match
                analysis = analyze_match(data)
            except:
                continue
            
            bt = compute_betting(data, analysis)
            rule = bt.get('rule')
            if not rule:
                continue
            
            mi = data.get('match_info', {})
            mid_str = mi.get('match_num_str', mid)
            if not mid_str.startswith(today_wd):
                continue  # 只显示今天
            
            # 比赛时间
            date = mi.get('match_date', '')
            time = mi.get('match_time', '')
            dt_str = f'{date} {time}'.strip()
            match_dt = None
            if date and time:
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']:
                    try:
                        match_dt = dt.strptime(dt_str, fmt)
                        break
                    except: pass
            
            hot = False
            cutoff = False
            if match_dt:
                diff_min = (match_dt - now).total_seconds() / 60
                if diff_min < 0:
                    continue  # 已开赛
                if diff_min <= 60:
                    hot = True
                now_mins = now.hour * 60 + now.minute
                if now_mins >= 21 * 60 + 30:
                    cutoff = True
            
            signals.append({
                'rule': rule,
                'match_id': mid,
                'match_num': mid_str,
                'home': mi.get('home_team', '?'),
                'away': mi.get('away_team', '?'),
                'datetime': dt_str,
                'hot': hot,
                'cutoff': cutoff,
                'stake': bt.get('total_stake', 0),
                'summary': bt.get('summary', '?'),
                'goal_bet': {'goals': bt.get('goal_bet', {}).get('goals', []), 'odds': bt.get('goal_bet', {}).get('odds', {}), 'stake': bt.get('goal_bet', {}).get('stake', 0)},
                'score_bets': [{'score': s['score'], 'odds': s['odds'], 'stake': s['stake'], 'tag': s.get('tag', '')} for s in bt.get('score_bets', [])],
            })
        
        total_stake = sum(s['stake'] for s in signals)
        return jsonify({
            'success': True,
            'today': today_wd,
            'count': len(signals),
            'total_stake': total_stake,
            'fetched': fetch_count,
            'fetched_names': fetched_names,
            'signals': signals,
        })
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()}), 500


# ══════════════════════════════════════════
#  投注确认埋点 API
# ══════════════════════════════════════════

@bp.route('/v36/confirm_bet/<match_id>', methods=['POST'])
def v36_confirm_bet(match_id):
    """用户确认投注：优先使用前端传来的投注结果（避免重新计算导致赔率变动偏差）"""
    try:
        data_file = os.path.join(DATA_DIR, f'{match_id}.json')
        if not os.path.exists(data_file):
            return jsonify({'success': False, 'error': f'比赛{match_id}数据不存在'}), 404

        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 优先使用前端传来的已显示投注结果
        result = None
        if request.is_json:
            body = request.get_json(silent=True) or {}
            if body.get('betting'):
                result = body['betting']
        
        # 如果没有前端数据，重新计算
        if not result or not result.get('action'):
            try:
                import sporttery_web
                sporttery_web._odds_hitrate_cache = None
                sporttery_web._change_hitrate_cache = None
                from sporttery_web import _build_odds_hitrate, _build_change_hitrate
                if '_odds_hitrate' not in data:
                    data['_odds_hitrate'] = _build_odds_hitrate()
                data['_change_hitrate'] = _build_change_hitrate()
            except:
                pass
            from v36_analyzer import analyze_match
            analysis = analyze_match(data)
            result = compute_betting(data, analysis)

        # 写入埋点
        from _rule_logger import confirm_bet as _log_confirm
        entry = _log_confirm(str(match_id), data, result)

        return jsonify({'success': True, 'entry': entry})
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()}), 500


@bp.route('/v36/undo_bet/<match_id>', methods=['POST'])
def v36_undo_bet(match_id):
    """撤销投注确认。比分数据不受影响，重新确认后可自动回填。"""
    try:
        from _rule_logger import undo_bet as _log_undo
        _log_undo(str(match_id))
        return jsonify({'success': True})
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()}), 500


@bp.route('/v36/bet_status', methods=['GET'])
def v36_bet_status():
    """查询所有已确认的投注状态（批量，供前端初始化用）"""
    try:
        from _rule_logger import get_all_confirmed
        confirmed = get_all_confirmed()
        status = {}
        for mid, entry in confirmed.items():
            status[mid] = {
                'confirmed': True,
                'rule': entry.get('rule', ''),
                'confirmed_at': entry.get('confirmed_at', ''),
                'actual_total': entry.get('actual_total'),
                'hit': entry.get('hit'),
            }
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()}), 500


# ===== 回测接口函数（不依赖Flask上下文）=====
def get_recommendation_for_backtest(data):
    """
    获取比分推荐（用于回测，不依赖Flask上下文）
    
    Args:
        data: 比赛数据字典
    
    Returns:
        {
            'rule': str,           # 触发规则名
            'goals': list,          # 推荐总进球数列表
            'explanation': str     # 推荐解释
        }
        或 None（如果没有推荐）
    """
    try:
        # 加载命中率数据（如果不存在）
        if '_odds_hitrate' not in data:
            from sporttery_web import _build_odds_hitrate
            data['_odds_hitrate'] = _build_odds_hitrate()
        
        if '_change_hitrate' not in data:
            from sporttery_web import _build_change_hitrate
            data['_change_hitrate'] = _build_change_hitrate()
        
        # 调用分析函数
        from v36_analyzer import analyze_match
        analysis = analyze_match(data)
        
        if not analysis:
            return None
        
        # 直接从分析结果中提取推荐（不调用compute_betting）
        rule = analysis.get('rule')
        goals = analysis.get('goals', [])
        explanation = analysis.get('explanation', '')
        
        if not goals:
            return None
        
        return {
            'rule': rule if rule else '',
            'goals': goals,
            'explanation': explanation
        }
    
    except Exception as e:
        print(f'[回测接口] ❌ 获取推荐失败: {e}')
        import traceback
        traceback.print_exc()
        return None

# ===== 回测接口函数简易版（带调试）=====
def get_recommendation_simple(data, match_id=''):
    """
    简易版：只调用analyze_match，打印完整结果，用于调试
    """
    try:
        if '_odds_hitrate' not in data:
            from sporttery_web import _build_odds_hitrate
            data['_odds_hitrate'] = _build_odds_hitrate()
        if '_change_hitrate' not in data:
            from sporttery_web import _build_change_hitrate
            data['_change_hitrate'] = _build_change_hitrate()

        from v36_analyzer import analyze_match
        analysis = analyze_match(data)

        print(f'[回测-{match_id}] analysis类型={type(analysis)}, 内容={analysis}')
        
        if not analysis:
            return None
        
        # 尝试多种可能的字段名
        # 优先: recommended.goals (V3.6格式)
        recommended = analysis.get('recommended', {})
        if isinstance(recommended, dict):
            goals = recommended.get('goals')
        
        # 备选1: final_goal_pick.double
        if not goals:
            final_pick = analysis.get('final_goal_pick', {})
            if isinstance(final_pick, dict):
                goals = final_pick.get('double') or final_pick.get('single')
        
        # 备选2: 直接字段
        if not goals:
            goals = analysis.get('goals') or analysis.get('goal_list')
        
        if not goals:
            print(f'[回测-{match_id}] ⚠️ 无法从analysis提取goals, recommended={recommended}, final_pick={analysis.get("final_goal_pick")}')
            return None
        
        return {
            'rule': analysis.get('rule', ''),
            'goals': goals if isinstance(goals, list) else [],
            'explanation': analysis.get('explanation', '')
        }
    except Exception as e:
        print(f'[回测-{match_id}] ❌ 异常: {e}')
        import traceback
        traceback.print_exc()
        return None
