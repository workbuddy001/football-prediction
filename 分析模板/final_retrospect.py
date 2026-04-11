# V7 + 8探测 + 基本面 最终版 - 输出所有>=55%置信度比赛
import os
import re
import numpy as np
from collections import Counter

def extract_odds_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    home_team = re.search(r'\| 主队 \|\s*(.+)', content)
    if not home_team:
        home_team = re.search(r'主队\s*\|\s*(.+)', content)
    away_team = re.search(r'\| 客队 \|\s*(.+)', content)
    if not away_team:
        away_team = re.search(r'客队\s*\|\s*(.+)', content)
    league = re.search(r'\| 赛事 \|\s*(.+)', content)
    if not league:
        league = re.search(r'赛事\s*\|\s*(.+)', content)
    home_form = re.search(r'\| 主队近况走势 \|\s*(.+)', content)
    if not home_form:
        home_form = re.search(r'主队近况走势\s*\|\s*(.+)', content)
    away_form = re.search(r'\| 客队近况走势 \|\s*(.+)', content)
    if not away_form:
        away_form = re.search(r'客队近况走势\s*\|\s*(.+)', content)
    macao_tip = re.search(r'\| 澳门推荐 \|\s*(.+)', content)
    if not macao_tip:
        macao_tip = re.search(r'澳门推荐\s*\|\s*(.+)', content)
    
    home_form_str = re.search(r'\| 主队近况 \|\s*(.+)', content)
    if not home_form_str:
        home_form_str = re.search(r'主队近况\s*\|\s*(.+)', content)
    away_form_str = re.search(r'\| 客队近况 \|\s*(.+)', content)
    if not away_form_str:
        away_form_str = re.search(r'客队近况\s*\|\s*(.+)', content)
    
    init_match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if init_match:
        odds_str = init_match.group(1)
        initial_odds = eval('[' + odds_str + ']')
    else:
        initial_odds = []
    
    real_match = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if real_match:
        odds_str = real_match.group(1)
        realtime_odds = eval('[' + odds_str + ']')
    else:
        realtime_odds = []
    
    def clean_value(s):
        if s:
            return s.strip().replace('|', '').strip()
        return s
    
    return {
        'home_team': clean_value(home_team.group(1)) if home_team else '',
        'away_team': clean_value(away_team.group(1)) if away_team else '',
        'league': clean_value(league.group(1)) if league else '',
        'home_form': home_form.group(1).strip() if home_form else '',
        'away_form': away_form.group(1).strip() if away_form else '',
        'macao_tip': macao_tip.group(1).strip() if macao_tip else '',
        'home_form_str': home_form_str.group(1).strip() if home_form_str else '',
        'away_form_str': away_form_str.group(1).strip() if away_form_str else '',
        'initial_odds': initial_odds,
        'realtime_odds': realtime_odds,
    }

def count_wins(form):
    if not form:
        return 0
    return sum(1 for c in form.upper() if c == 'W')

def count_losses(form):
    if not form:
        return 0
    return sum(1 for c in form.upper() if c == 'L')

def count_draws(form):
    if not form:
        return 0
    return sum(1 for c in form.upper() if c == 'D')

def get_last_digit(odds):
    s = f"{odds:.2f}"
    return s[-1]

def count_ends_with_8(odds_list):
    return sum(1 for o in odds_list if get_last_digit(o) == '8')

def check_ends_with_88(odds):
    """检查赔率是否以88结尾（如1.88, 2.88, 3.88等）"""
    s = f"{odds:.2f}"
    return s[-2:] == '88'

def count_ends_with_88(odds_list):
    """统计末尾是88的赔率数量"""
    return sum(1 for o in odds_list if check_ends_with_88(o))

def analyze_8_pattern(initial_odds, realtime_odds, choice_type):
    if not initial_odds or not realtime_odds:
        return {}
    
    idx = {'home': 0, 'draw': 1, 'away': 2}[choice_type]
    
    init_odds = [o[idx] for o in initial_odds]
    real_odds = [o[idx] for o in realtime_odds]
    
    # 主胜赔率（检测主胜是否有88结尾）
    real_home = [o[0] for o in realtime_odds]
    # 客胜赔率（检测客胜是否有88结尾）
    real_away = [o[2] for o in realtime_odds]
    
    init_8_count = count_ends_with_8(init_odds)
    real_8_count = count_ends_with_8(real_odds)
    
    # 主胜选项的8变化
    init_home = [o[0] for o in initial_odds]
    init_away = [o[2] for o in initial_odds]
    init_home_8 = count_ends_with_8(init_home)
    init_away_8 = count_ends_with_8(init_away)
    real_home_8 = count_ends_with_8(real_home)
    real_away_8 = count_ends_with_8(real_away)
    diff_home_8 = real_home_8 - init_home_8  # 主胜8变化
    diff_away_8 = real_away_8 - init_away_8  # 客胜8变化
    
    # 检测主胜/客胜是否有88结尾
    home_has_88 = any(check_ends_with_88(o) for o in real_home)
    away_has_88 = any(check_ends_with_88(o) for o in real_away)
    
    # V7预测选项是否有88结尾
    real_88_count = count_ends_with_88(real_odds)
    choice_has_88 = real_88_count > 0
    
    diff_8 = real_8_count - init_8_count
    
    # 末尾88风险判断
    has_88_risk = choice_has_88
    
    if real_8_count == 0 and init_8_count > 0:
        pattern = "真空避险"
        signal = "安全"
    elif diff_8 > 0:
        pattern = "补饵收割"
        signal = "危险"
    elif real_8_count >= 10:
        pattern = "超饱和"
        signal = "危险"
    elif has_88_risk:
        pattern = "末尾88陷阱"
        signal = "危险"
    else:
        pattern = "正常"
        signal = "正常"
    
    return {
        'init_8_count': init_8_count,
        'real_8_count': real_8_count,
        'diff_8': diff_8,
        'diff_home_8': diff_home_8,  # 主胜8变化
        'diff_away_8': diff_away_8,  # 客胜8变化
        'real_88_count': real_88_count,
        'home_has_88': home_has_88,
        'away_has_88': away_has_88,
        'choice_has_88': choice_has_88,
        'pattern': pattern,
        'signal': signal,
    }

def analyze_match_v7(data):
    if not data['initial_odds'] or not data['realtime_odds']:
        return None
    
    real_home = [o[0] for o in data['realtime_odds']]
    real_draw = [o[1] for o in data['realtime_odds']]
    real_away = [o[2] for o in data['realtime_odds']]
    
    home_pct = [(data['realtime_odds'][i][0] - data['initial_odds'][i][0]) / data['initial_odds'][i][0] * 100 
                for i in range(len(data['initial_odds']))]
    draw_pct = [(data['realtime_odds'][i][1] - data['initial_odds'][i][1]) / data['initial_odds'][i][1] * 100 
                for i in range(len(data['initial_odds']))]
    away_pct = [(data['realtime_odds'][i][2] - data['initial_odds'][i][2]) / data['initial_odds'][i][2] * 100 
                for i in range(len(data['initial_odds']))]
    
    real_home_prob = [1/x*100 for x in real_home]
    real_draw_prob = [1/x*100 for x in real_draw]
    real_away_prob = [1/x*100 for x in real_away]
    
    home_up_pct = sum(1 for x in home_pct if x > 0) / len(home_pct) * 100
    draw_down_pct = sum(1 for x in draw_pct if x < 0) / len(draw_pct) * 100
    away_up_pct = sum(1 for x in away_pct if x > 0) / len(away_pct) * 100
    
    avg_home = np.mean(real_home)
    avg_draw = np.mean(real_draw)
    avg_away = np.mean(real_away)
    
    avg_home_prob = np.mean(real_home_prob)
    avg_draw_prob = np.mean(real_draw_prob)
    avg_away_prob = np.mean(real_away_prob)
    
    home_wins = count_wins(data['home_form'])
    away_wins = count_wins(data['away_form'])
    home_losses = count_losses(data['home_form'])
    away_losses = count_losses(data['away_form'])
    home_draws = count_draws(data['home_form'])
    away_draws = count_draws(data['away_form'])
    
    macao_tip = data['macao_tip'].upper() if data['macao_tip'] else ""
    
    if avg_home < 1.5:
        choice = 'home'
        reason = "强队主场"
    elif avg_away < 1.5:
        choice = 'away'
        reason = "强队客场"
    elif "主" in macao_tip and "客" not in macao_tip:
        choice = 'home'
        reason = "澳门推荐主胜"
    elif "客" in macao_tip:
        choice = 'away'
        reason = "澳门推荐客胜"
    elif home_draws >= 3 and away_draws >= 3 and abs(avg_home_prob - avg_away_prob) < 15:
        choice = 'draw'
        reason = "两队近况多平局"
    elif 2.5 < avg_home < 4.5 and 2.0 < avg_away < 4.0 and abs(home_wins - away_wins) <= 1:
        choice = 'draw'
        reason = "强强对话均势"
    elif avg_draw_prob > 28 and abs(avg_home_prob - avg_away_prob) < 10:
        choice = 'draw'
        reason = "平局概率突出"
    elif home_up_pct > 40 and away_up_pct > 40 and draw_down_pct > 40:
        choice = 'draw'
        reason = "胜赔上升平局降"
    elif home_wins >= 4 and avg_home < 2.5:
        choice = 'home'
        reason = "主队近况很好"
    elif away_wins >= 4 and avg_away < 2.5:
        choice = 'away'
        reason = "客队近况很好"
    elif avg_home_prob > avg_away_prob + 10 and avg_home_prob > avg_draw_prob + 8:
        choice = 'home'
        reason = "主胜概率优势明显"
    elif avg_away_prob > avg_home_prob + 10 and avg_away_prob > avg_draw_prob + 8:
        choice = 'away'
        reason = "客胜概率优势明显"
    elif avg_home_prob >= avg_away_prob and avg_home_prob >= avg_draw_prob:
        choice = 'home'
        reason = "主胜概率最高"
    elif avg_away_prob >= avg_home_prob and avg_away_prob >= avg_draw_prob:
        choice = 'away'
        reason = "客胜概率最高"
    else:
        choice = 'draw'
        reason = "默认平局"
    
    prob_map = {'home': avg_home_prob, 'draw': avg_draw_prob, 'away': avg_away_prob}
    confidence = prob_map.get(choice, 0)
    
    return {
        'choice': choice,
        'confidence': confidence,
        'reason': reason,
        'initial_odds': data['initial_odds'],
        'realtime_odds': data['realtime_odds'],
    }

def analyze_form_comparison(data):
    """分析双方状态对比
    
    返回:
    - dominance: 'home_strong'(主队强) / 'away_strong'(客队强) / 'balanced'(旗鼓相当)
    - diff: 主队胜场 - 客队胜场
    """
    home_wins = count_wins(data['home_form'])
    away_wins = count_wins(data['away_form'])
    
    home_win_rate = 0
    away_win_rate = 0
    try:
        if data['home_form_str']:
            match = re.search(r'(\d+)%', data['home_form_str'])
            if match:
                home_win_rate = int(match.group(1))
        if data['away_form_str']:
            match = re.search(r'(\d+)%', data['away_form_str'])
            if match:
                away_win_rate = int(match.group(1))
    except:
        pass
    
    # 状态对比：主队胜场比客队多4场以上，或胜率高25%以上，认为"远好于"
    diff = home_wins - away_wins
    rate_diff = home_win_rate - away_win_rate
    
    if diff >= 4 or rate_diff >= 25:
        return {'dominance': 'home_strong', 'diff': diff, 'home_wins': home_wins, 'away_wins': away_wins}
    elif diff <= -4 or rate_diff <= -25:
        return {'dominance': 'away_strong', 'diff': diff, 'home_wins': home_wins, 'away_wins': away_wins}
    else:
        return {'dominance': 'balanced', 'diff': diff, 'home_wins': home_wins, 'away_wins': away_wins}

def analyze_match_final(v7_choice, v7_confidence, eight_analysis, data):
    """最终决策"""
    home_wins = count_wins(data['home_form'])
    away_wins = count_wins(data['away_form'])
    macao_tip = data['macao_tip'] if data['macao_tip'] else ""
    home_team = data['home_team']
    away_team = data['away_team']
    
    home_win_rate = 0
    away_win_rate = 0
    try:
        if data['home_form_str']:
            match = re.search(r'(\d+)%', data['home_form_str'])
            if match:
                home_win_rate = int(match.group(1))
        if data['away_form_str']:
            match = re.search(r'(\d+)%', data['away_form_str'])
            if match:
                away_win_rate = int(match.group(1))
    except:
        pass
    
    v7_direction = v7_choice
    eight_signal = eight_analysis.get('signal', '正常')
    real_8_count = eight_analysis.get('real_8_count', 0)  # 即时盘末位8数量
    real_88_count = eight_analysis.get('real_88_count', 0)  # 即时盘末尾88数量
    diff_8 = eight_analysis.get('diff_8', 0)  # 末尾8变化
    
    # 主胜/客胜各自的8变化
    diff_home_8 = eight_analysis.get('diff_home_8', 0)
    diff_away_8 = eight_analysis.get('diff_away_8', 0)
    
    # 新增：V7预测选项是否有88结尾
    choice_has_88 = eight_analysis.get('choice_has_88', False)
    home_has_88 = eight_analysis.get('home_has_88', False)
    away_has_88 = eight_analysis.get('away_has_88', False)
    
    # 新增：即时盘8数量>=3的风险判断
    high_8_risk = real_8_count >= 3
    
    # 新增：末尾88风险判断 - 只看V7预测选项是否有88
    has_88_risk = choice_has_88
    
    # ===== 新增：状态对比分析 =====
    form_analysis = analyze_form_comparison(data)
    dominance = form_analysis['dominance']  # home_strong / away_strong / balanced
    
    # ===== 新增：末尾8趋势 =====
    eight_increasing = diff_8 > 0   # 末尾8增加
    eight_decreasing = diff_8 < 0  # 末尾8减少
    
    # 排除逻辑：主胜/客胜有88结尾就排除该选项
    excluded = False
    excluded_reason = ""
    if v7_direction == 'home' and home_has_88:
        excluded = True
        excluded_reason = "主胜有88陷阱"
    elif v7_direction == 'away' and away_has_88:
        excluded = True
        excluded_reason = "客胜有88陷阱"
    
    # 降权逻辑：V7预测选项没有88，但其他选项有88（特别是置信度高的比赛）
    demoted = False
    demoted_reason = ""
    if not excluded and v7_confidence >= 60:
        if v7_direction == 'home' and not home_has_88 and away_has_88:
            demoted = True
            demoted_reason = "客胜有88，但主胜无88"
        elif v7_direction == 'away' and not away_has_88 and home_has_88:
            demoted = True
            demoted_reason = "主胜有88，但客胜无88"
    
    # ===== 状态对比+末尾8趋势 诱盘陷阱判断 =====
    # 情况1：主队状态远好于客队 + 末尾8增加 + 预测主胜 = 诱盘风险 → 降权
    trap_risk = False
    trap_reason = ""
    if not excluded and not demoted and v7_confidence >= 60:
        if v7_direction == 'home' and dominance == 'home_strong' and eight_increasing:
            trap_risk = True
            trap_reason = "主队强+末尾8增加"
        elif v7_direction == 'away' and dominance == 'away_strong' and eight_increasing:
            trap_risk = True
            trap_reason = "客队强+末尾8增加"
    
    # ===== 状态焦灼+澳门推荐方向末尾8减少 = 强烈推荐 =====
    # 新逻辑：双方状态焦灼 + 澳门推荐方向的末尾8减少 → 推荐方打出
    strong_recommend = False
    strong_reason = ""
    
    # 解析澳门推荐：匹配主队或客队名称
    macao_direction = None
    if "和局" in macao_tip or "平局" in macao_tip:
        macao_direction = 'draw'
    elif home_team and home_team in macao_tip:
        macao_direction = 'home'
    elif away_team and away_team in macao_tip:
        macao_direction = 'away'
    
    # 调试输出（已删除）
    
    if not excluded and not demoted and not trap_risk and v7_confidence >= 55:
        # 澳门推荐主胜 + 状态焦灼 + 主胜方向8减少
        if macao_direction == 'home' and dominance == 'balanced' and diff_home_8 < 0:
            strong_recommend = True
            strong_reason = "状态焦灼+澳门推荐主胜+主胜8减少"
        # 澳门推荐客胜 + 状态焦灼 + 客胜方向8减少
        elif macao_direction == 'away' and dominance == 'balanced' and diff_away_8 < 0:
            strong_recommend = True
            strong_reason = "状态焦灼+澳门推荐客胜+客胜8减少"
    
    # 旧的safe_signal保留作为备用
    safe_signal = False
    safe_reason = ""
    if not excluded and not demoted and not trap_risk and not strong_recommend and v7_confidence >= 55:
        if v7_direction == 'home' and dominance == 'balanced' and eight_decreasing:
            safe_signal = True
            safe_reason = "状态相当+末尾8减少"
        elif v7_direction == 'away' and dominance == 'balanced' and eight_decreasing:
            safe_signal = True
            safe_reason = "状态相当+末尾8减少"
    
    # 基本面确认
    basic_confirmed = False
    if eight_signal == '危险':
        if v7_direction == 'home':
            if ("主" in macao_tip and "客" not in macao_tip) and home_win_rate > away_win_rate:
                basic_confirmed = True
        elif v7_direction == 'away':
            if "客" in macao_tip and away_win_rate > home_win_rate:
                basic_confirmed = True
    
    # 最终决策
    # 排除：有88陷阱的选项
    if excluded:
        return {
            'recommendation': '排除',
            'reason': f'{excluded_reason}，建议避开',
            'final_choice': None
        }
    # 降权：置信度>=60%但对方选项有88
    elif demoted:
        return {
            'recommendation': '降权',
            'reason': f'{demoted_reason}，有诱盘可能',
            'final_choice': v7_choice
        }
    
    # ===== 新规律1：8变化-5 + 状态极好 = 庄家挡不住，推荐主胜 =====
    # 规律：8减少到-5时，如果状态极好，主胜概率高
    minus_five_signal = False
    minus_five_reason = ""
    if not excluded and not demoted:
        # 主胜方向8减少-5 + 状态极好（home_strong）
        if v7_direction == 'home' and dominance == 'home_strong' and diff_home_8 <= -5:
            minus_five_signal = True
            minus_five_reason = "8减少-5+主队极好，庄家挡不住"
        # 客胜方向8减少-5 + 状态极好（away_strong）
        elif v7_direction == 'away' and dominance == 'away_strong' and diff_away_8 <= -5:
            minus_five_signal = True
            minus_five_reason = "8减少-5+客队极好，庄家挡不住"
    
    # ===== 新规律2：8变化-5 + 状态焦灼 = 平局是底限 =====
    # 规律：8减少到-5时，如果状态焦灼，平局概率高
    minus_five_draw = False
    minus_five_draw_reason = ""
    if not excluded and not demoted and not minus_five_signal:
        # 主胜方向8减少-5 + 状态焦灼（balanced）
        if v7_direction == 'home' and dominance == 'balanced' and diff_home_8 <= -5:
            minus_five_draw = True
            minus_five_draw_reason = "8减少-5+状态焦灼，平局是底限"
        # 客胜方向8减少-5 + 状态焦灼
        elif v7_direction == 'away' and dominance == 'balanced' and diff_away_8 <= -5:
            minus_five_draw = True
            minus_five_draw_reason = "8减少-5+状态焦灼，平局是底限"
    
    # ===== 原逻辑：高置信度+状态极好+末尾8减少 = 预测方打不出，推荐平局 =====
    predict_strong = False
    predict_strong_reason = ""
    if not excluded and not demoted and not minus_five_signal and not minus_five_draw and v7_confidence >= 55:
        # 主队状态极好 + 预测主胜 + 主胜8减少
        if v7_direction == 'home' and dominance == 'home_strong' and diff_home_8 < 0:
            predict_strong = True
            predict_strong_reason = "主队强+主胜8减少，平局是底限"
        # 客队状态极好 + 预测客胜 + 客胜8减少
        elif v7_direction == 'away' and dominance == 'away_strong' and diff_away_8 < 0:
            predict_strong = True
            predict_strong_reason = "客队强+客胜8减少，平局是底限"
    
    # 降权：主队强+末尾8增加 或 客队强+末尾8增加（诱盘陷阱）
    if trap_risk:
        return {
            'recommendation': '降权',
            'reason': f'{trap_reason}，诱盘风险高',
            'final_choice': v7_choice
        }
    # 新规律1：8变化-5 + 状态极好 → 推荐主胜
    elif minus_five_signal:
        return {
            'recommendation': '强烈推荐',
            'reason': f'{minus_five_reason}',
            'final_choice': v7_choice
        }
    # 新规律2：8变化-5 + 状态焦灼 → 推荐平局
    elif minus_five_draw:
        return {
            'recommendation': '推荐平局',
            'reason': f'{minus_five_draw_reason}',
            'final_choice': 'draw'
        }
    # 原逻辑：高置信度+状态极好+末尾8减少 → 推荐平局
    elif predict_strong:
        return {
            'recommendation': '推荐平局',
            'reason': f'{predict_strong_reason}',
            'final_choice': 'draw'
        }
    # 强烈推荐：状态焦灼+澳门推荐方向末尾8减少（新逻辑）
    elif strong_recommend:
        return {
            'recommendation': '强烈推荐',
            'reason': f'{strong_reason}',
            'final_choice': v7_choice
        }
    # 强烈推荐：置信度>=60% + 8正常 + 无末尾88 + 安全信号
    elif v7_confidence >= 60 and eight_signal == '正常' and not has_88_risk and safe_signal:
        return {
            'recommendation': '强烈推荐',
            'reason': f'高置信度({v7_confidence:.0f}%)+{safe_reason}+无末尾88',
            'final_choice': v7_choice
        }
    # 强烈推荐：置信度>=60% + 8正常 + 无末尾88（原逻辑保留）
    elif v7_confidence >= 60 and eight_signal == '正常' and not has_88_risk:
        return {
            'recommendation': '强烈推荐',
            'reason': f'高置信度({v7_confidence:.0f}%)+8正常+无末尾88',
            'final_choice': v7_choice
        }
    # 谨慎推荐：置信度>=60% + 8正常 + 即时8>=3
    elif v7_confidence >= 60 and eight_signal == '正常' and high_8_risk:
        return {
            'recommendation': '谨慎推荐',
            'reason': f'高置信度({v7_confidence:.0f}%)+但即时8>=3有风险',
            'final_choice': v7_choice
        }
    elif v7_confidence >= 60 and eight_signal == '危险' and basic_confirmed:
        return {
            'recommendation': '谨慎推荐',
            'reason': f'高置信度({v7_confidence:.0f}%)+基本面强确认',
            'final_choice': v7_choice
        }
    elif v7_confidence >= 55:
        return {
            'recommendation': '一般推荐',
            'reason': f'置信度{v7_confidence:.0f}%',
            'final_choice': v7_choice
        }
    else:
        return {
            'recommendation': '不推荐',
            'reason': f'置信度{v7_confidence:.0f}%不足',
            'final_choice': v7_choice
        }

def load_actual_results():
    results = {}
    results['周五001'] = '客胜'
    results['周五002'] = '主胜'
    results['周五003'] = '客胜'
    results['周五004'] = '客胜'
    results['周五005'] = '主胜'
    results['周五006'] = '客胜'
    results['周五007'] = '平局'
    results['周五008'] = '客胜'
    results['周五009'] = '主胜'
    results['周五010'] = '主胜'  # 马赛 vs 欧塞尔 1:0
    results['周五011'] = '主胜'
    results['周五012'] = '主胜'
    results['周六001'] = '平局'  # 中国女 vs 中国台女 0:0
    results['周六002'] = '客胜'
    results['周六003'] = '主胜'
    results['周六004'] = '客胜'
    results['周六005'] = '平局'
    results['周六006'] = '客胜'
    results['周六007'] = '客胜'
    results['周六008'] = '主胜'  # 韩国女 vs 乌兹别克斯坦女 6:0
    results['周六009'] = '主胜'
    results['周六010'] = '平局'
    results['周六011'] = '客胜'
    results['周六012'] = '平局'  # 国际米兰 vs 亚特兰大 1:1
    results['周六013'] = '平局'
    results['周六014'] = '主胜'
    results['周六015'] = '主胜'  # 法兰克福 vs 海登海姆 1:0
    results['周六016'] = '平局'
    results['周日001'] = '主胜'
    results['周日002'] = '平局'
    results['周日003'] = '客胜'
    results['周日004'] = '客胜'
    results['周日005'] = '主胜'
    results['周日006'] = '客胜'
    results['周日007'] = '主胜'
    results['周日008'] = '客胜'
    results['周日009'] = '平局'
    results['周日010'] = '主胜'  # 费耶诺德 vs SBV精英 2:1
    results['周日011'] = '主胜'  # 克里斯蒂 vs 布兰 3:2
    results['周日012'] = '客胜'
    results['周日013'] = '主胜'
    results['周日014'] = '主胜'  # 曼联 vs 维拉 3:1
    results['周日015'] = '主胜'
    results['周日016'] = '客胜'
    results['周日017'] = '主胜'
    results['周日018'] = '主胜'  # 巴萨 vs 塞维利亚 5:2
    results['周日019'] = '主胜'
    return results

def analyze_folder(folder_path, day_name):
    files = [f for f in os.listdir(folder_path) if f.endswith('_源数据.md')]
    
    results = []
    for f in sorted(files):
        filepath = os.path.join(folder_path, f)
        try:
            data = extract_odds_from_file(filepath)
            result = analyze_match_v7(data)
            if result:
                filename = f.replace('_源数据.md', '')
                match = re.search(r'(周[一二三五六日])(\d+)', filename)
                if match:
                    match_id = f"{match.group(1)}{int(match.group(2)):03d}"
                else:
                    continue
                
                result['filename'] = filename
                result['match_id'] = match_id
                result['data'] = data
                result['home_team'] = data['home_team']
                result['away_team'] = data['away_team']
                
                eight_analysis = analyze_8_pattern(
                    result['initial_odds'], 
                    result['realtime_odds'],
                    result['choice']
                )
                result['eight_analysis'] = eight_analysis
                
                final = analyze_match_final(
                    result['choice'],
                    result['confidence'],
                    eight_analysis,
                    data
                )
                result['final'] = final
                
                results.append(result)
        except Exception as e:
            print(f"Error: {f} - {e}")
    
    return results

actual_results = load_actual_results()

print("=" * 100)
print("V7 + 8探测 + 基本面 最终版回溯分析")
print("=" * 100)

all_results = []
folders = [
    (r"d:\work\workbuddy\足球预测\分析模板\3.13", "周五"),
    (r"d:\work\workbuddy\足球预测\分析模板\3.14", "周六"),
    (r"d:\work\workbuddy\足球预测\分析模板\3.15", "周日"),
]

for folder, day in folders:
    results = analyze_folder(folder, day)
    all_results.extend(results)

# 按置信度排序
all_results.sort(key=lambda x: x['confidence'], reverse=True)

# 统计
total_55 = 0
total_55_correct = 0
all_total = 0
all_correct = 0

print("\n" + "=" * 100)
print("【全部比赛详情】(按置信度排序)")
print("=" * 100)

for r in all_results:
    match_id = r['match_id']
    if match_id not in actual_results:
        continue
    
    actual = actual_results[match_id]
    v7_choice = r['choice']
    v7_pred = {'home': '主胜', 'draw': '平局', 'away': '客胜'}[v7_choice]
    v7_confidence = r['confidence']
    eight = r['eight_analysis']
    final = r['final']
    macao = r['data']['macao_tip']
    home_w = count_wins(r['data']['home_form'])
    away_w = count_wins(r['data']['away_form'])
    
    all_total += 1
    if v7_pred == actual:
        all_correct += 1
    
    is_correct = "对" if v7_pred == actual else "错"
    
    if v7_confidence >= 55:
        total_55 += 1
        if v7_pred == actual:
            total_55_correct += 1
        
        print(f"\n{'='*70}")
        print(f"[{r['filename']}]")
        print(f"V7预测: {v7_pred} ({v7_confidence:.0f}%)")
        print(f"实际: {actual} [{is_correct}]")
        print(f"澳门推荐: {macao}")
        print(f"主队近况: {r['data']['home_form']} ({home_w}胜)")
        print(f"客队近况: {r['data']['away_form']} ({away_w}胜)")
        print(f"8探测: 初盘{eight['init_8_count']} -> 即时{eight['real_8_count']} (变化{eight['diff_8']:+d})")
        print(f"模式: {eight['pattern']}")
        print(f"推荐: {final['recommendation']}")

# 统计结果
v7_hit_rate = all_correct / all_total * 100 if all_total > 0 else 0
hit_rate_55 = total_55_correct / total_55 * 100 if total_55 > 0 else 0

print("\n" + "=" * 100)
print("统计结果")
print("=" * 100)
print(f"\n【V7全部比赛】")
print(f"  总场次: {all_total}, 正确: {all_correct}, 命中率: {v7_hit_rate:.1f}%")

print(f"\n【置信度>=55%的比赛】")
print(f"  总场次: {total_55}, 正确: {total_55_correct}, 命中率: {hit_rate_55:.1f}%")

print(f"\n【优化版(强烈推荐)】")
strong_recall = [r for r in all_results if r['final']['recommendation'] == '强烈推荐']
strong_correct = sum(1 for r in strong_recall 
                     if {'home': '主胜', 'draw': '平局', 'away': '客胜'}[r['choice']] == actual_results.get(r['match_id'], ''))
if strong_recall:
    strong_hit = strong_correct / len(strong_recall) * 100
    print(f"  场次: {len(strong_recall)}, 正确: {strong_correct}, 命中率: {strong_hit:.1f}%")


