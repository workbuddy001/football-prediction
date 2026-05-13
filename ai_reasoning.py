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


def compute_betting(data, analysis):
    """
    投注策略决策：
    R0: 推荐0:0 → 三层排除 + 双层保底 → 0球50元 + 1:1(10)+小胜(10)
    R1: 推荐3:0 + V36+Tree双确认 + 让胜<1.80 → 3:0比分20元
    R2: 推荐2:4 + 让胜<让负 + 让负>2.5 → 2:4比分20元
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
        a_win = float(had.get('负', 0))
    except: 
        h_win = None
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
    
    # 预计算信号F条件（避免elif阻断后续规则）
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
    
    # 预计算H1信号（大热必死+Top1比分+o0>=20→投Top1比分10元,回测ROI+171%）
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
                        # get odds for this score (inline, _get_score_odds defined later)
                        try:
                            parts = h1_score.replace('-',':').split(':')
                            key = f'{int(parts[0]):02d}:{int(parts[1]):02d}'
                            h1_odds = float(so.get(key, so.get(h1_score, 0)) or 0)
                        except: h1_odds = 0
    except:
        pass
    
    # 预计算H2信号（Top1=1:1+o0 11-13+平<3.5+2球铁保留/大热必死→投1:1 10元,回测ROI+231%）
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
                            # 也查excluded里大热必死
                            for e in excl.get('excluded', []):
                                if e.get('goal') == '2球' and '大热必死' in e.get('reason', ''):
                                    h2_11 = True; break
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
    
    if top_score_rec == '0:0':
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
            return {'action': 'skip', 'reason': f'R0跳过: g0={g0}≥10.5+平平降{pp_change:.0f}%(陷阱信号,回测0/6)'}
        
        # R0: 联赛过滤（西甲/欧联/瑞典超/日职/韩职0球率极低）
        SKIP_LEAGUES = ['西班牙甲级联赛', '欧罗巴联赛', '瑞典超级联赛', '日本职业联赛', '韩国职业联赛']
        try:
            info = data.get('match_info', {})
            league = info.get('league', '') if isinstance(info, dict) else ''
            if league in SKIP_LEAGUES:
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
        
        # R0: 置信度标记（仅供参考，投注额统一50元）
        rule = 'R0'
        bet_goals = [0]
        bet_type = 'single'
        goal_stake = 50
    elif top_score_rec == '3:0' and agree_count == 2:
        # R1: 推荐3:0 + 让胜<1.80 → 纯买3:0比分20元
        try:
            hhad = data.get('hhad', {})
            rs = float(hhad.get('让胜', 0)) if isinstance(hhad, dict) and hhad.get('让胜') else 0
            if rs >= 1.80:
                return {'action': 'skip', 'reason': f'R1跳过: 让胜{rs:.1f}≥1.80(回测仅10%命中)'}
        except:
            pass
        
        rule = 'R1'
        bet_goals = []
        bet_type = 'single'
        goal_stake = 0
    elif f_eligible:
        # 信号F: 近况>4 + 铁桶防守 + 0球25-35 + 0球不暴跌 → 投7球 (ROI+275%)
        rule = 'F'
        bet_goals = [7]
        bet_type = 'single'
        goal_stake = 30
    elif g7_signal and g0 and g0 >= 12:
        # 信号G7: 三维排除7球=保留/警惕 + o0>=12 → 投7球 (ROI+550%)
        rule = 'G7'
        bet_goals = [7]
        bet_type = 'single'
        goal_stake = 30
    elif g6_keep and g0 and g0 >= 12:
        # 信号G6: 三维排除6球=保留 + o0>=12 → 投6球 (ROI+298%)
        rule = 'G6'
        bet_goals = [6]
        bet_type = 'single'
        goal_stake = 30
    elif h2_11:
        # 信号H2: Top1=1:1+o0 11-13+平<3.5+2球铁保留/大热必死 → 投1:1 10元 (ROI+231%)
        rule = 'H2'
        bet_goals = []
        bet_type = 'single'
        goal_stake = 0
    elif h1_score and h1_odds > 0:
        # 信号H1: 大热必死+Top1比分+o0>=20 → 投Top1比分10元 (ROI+171%)
        rule = 'H1'
        bet_goals = []
        bet_type = 'single'
        goal_stake = 0
    elif g5_warn and g0 and g0 >= 12:
        # 信号G5: 三维排除5球=警惕造热 + o0>=12 → 投5球 (ROI+135%)
        rule = 'G5'
        bet_goals = [5]
        bet_type = 'single'
        goal_stake = 30
    elif g4_22:
        # 信号G4: 4球警惕造热 + 平<3.5 + 双方防守>1.0 → 投2:2比分10元 (ROI+122%)
        rule = 'G4'
        bet_goals = []
        bet_type = 'single'
        goal_stake = 0
    elif top_score_rec == '2:4':
        # R2: 推荐2:4 + 让胜<让负 + 让负>2.5 → 纯买2:4比分20元
        try:
            hhad = data.get('hhad', {})
            rs = float(hhad.get('让胜', 0)) if isinstance(hhad, dict) and hhad.get('让胜') else 0
            rf = float(hhad.get('让负', 0)) if isinstance(hhad, dict) and hhad.get('让负') else 0
            if not (rs < rf and rf > 2.5):
                return {'action': 'skip', 'reason': f'R2跳过: 让胜{rs:.1f}≥让负{rf:.1f}或让负≤2.5(不符合2:4规律)'}
        except:
            return {'action': 'skip', 'reason': 'R2跳过: 让球数据缺失'}
        
        rule = 'R2'
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
    
    if not rule:
        return {'action': 'skip', 'reason': '无匹配投注规则'}
    
    # 进球数投注
    goal_odds = {g: go.get(g) for g in bet_goals if go.get(g)}
    
    # 比分投注
    score_bets = []
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
        # R0保底比分: 1:1(10元) + 智能小胜(10元)
        home_fav = (h_win is not None and a_win is not None and h_win < a_win)
        fav_odds = h_win if home_fav else a_win
        
        if fav_odds and fav_odds < 2.0:
            close_score = '1:0' if home_fav else '0:1'
        else:
            close_score = '2:1' if home_fav else '1:2'
        
        odds_11 = _get_score_odds('1:1')
        odds_close = _get_score_odds(close_score)
        
        if odds_11 > 0:
            score_bets.append({'score': '1:1', 'odds': round(odds_11, 1), 'stake': 10, 'tag': '保底'})
        if odds_close > 0:
            score_bets.append({'score': close_score, 'odds': round(odds_close, 1), 'stake': 10, 'tag': '1球小胜保底'})
        
        conf_tag = ''
        if pp_boost:
            conf_tag = ' 🔥平平降>5%'
        elif had_boost:
            conf_tag = ' 💚HAD平赔降'
        elif had_weak:
            conf_tag = ' ⚠️HAD主胜升'
    elif rule in ('R1', 'R2'):
        # R1: 纯买3:0比分 20元 | R2: 纯买2:4比分 20元
        score_key = '3:0' if rule == 'R1' else '2:4'
        ho = _get_score_odds(score_key)
        if ho > 0:
            score_bets.append({'score': score_key, 'odds': round(ho, 1), 'stake': 20})
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
            score_bets.append({'score': '1:1', 'odds': round(ho, 1), 'stake': 10, 'tag': 'H2铁保留'})
        conf_tag = ''
    else:
        # 非R0: 每个目标球数取最低赔率2个比分
        for g in bet_goals:
            candidates = sorted(score_by_goals.get(g, []), key=lambda x: x[1])
            hot = candidates[:2]
            for sc, odds in hot:
                score_bets.append({'score': sc, 'odds': round(odds, 1), 'stake': 10})
        conf_tag = ''
    
    total_score_stake = sum(s['stake'] for s in score_bets)
    
    summary_text = ''
    if rule == 'G4':
        summary_text = '2:2比分10元'
    elif rule == 'H1':
        summary_text = f'{h1_score}比分10元'
    elif rule == 'H2':
        summary_text = '1:1比分10元'
    elif bet_goals:
        summary_text = f"{'单选' if bet_type=='single' else '双选'}{'+'.join(str(g) for g in bet_goals)}球 {goal_stake}元"
    if score_bets and rule not in ('G4', 'H1', 'H2'):
        if summary_text: summary_text += ' + '
        summary_text += f"{len(score_bets)}个比分{'保底' if rule=='R0' else '投注'}{total_score_stake}元"
    summary_text += conf_tag
    
    return {
        'action': 'bet',
        'rule': rule,
        'bet_type': bet_type,
        'goal_bet': {
            'goals': bet_goals,
            'stake': goal_stake,
            'odds': {str(g): round(o, 1) for g, o in goal_odds.items()},
        },
        'score_bets': score_bets,
        'score_stake': total_score_stake,
        'total_stake': goal_stake + total_score_stake,
        'summary': summary_text,
        'pp_boost': pp_boost if rule == 'R0' else False,
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
        
        # V3.6 fix: 独立加载命中率数据（优先使用，key保证是整数）
        try:
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
        from v36_analyzer import analyze_match
        result = analyze_match(data)
        
        # ===== 投注策略 =====
        result['betting'] = compute_betting(data, result)
        
        return jsonify({'success': True, 'analysis': result})
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()}), 500
