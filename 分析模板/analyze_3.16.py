# 分析3.16目录的比赛
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
    
    # 提取赔率数据 - 使用更简单的正则
    init_match = re.search(r'initial_odds = \[(.*?)\]', content, re.DOTALL)
    if init_match:
        odds_str = init_match.group(1)
        # 提取所有赔率tuple
        tuples = re.findall(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', odds_str)
        initial_odds = [(float(t[0]), float(t[1]), float(t[2])) for t in tuples]
    else:
        initial_odds = []
    
    real_match = re.search(r'realtime_odds = \[(.*?)\]', content, re.DOTALL)
    if real_match:
        odds_str = real_match.group(1)
        tuples = re.findall(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', odds_str)
        realtime_odds = [(float(t[0]), float(t[1]), float(t[2])) for t in tuples]
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
    s = f"{odds:.2f}"
    return s[-2:] == '88'

def count_ends_with_88(odds_list):
    return sum(1 for o in odds_list if check_ends_with_88(o))

def analyze_8_pattern(initial_odds, realtime_odds, choice_type):
    if not initial_odds or not realtime_odds:
        return {}
    
    idx = {'home': 0, 'draw': 1, 'away': 2}[choice_type]
    
    init_odds = [o[idx] for o in initial_odds]
    real_odds = [o[idx] for o in realtime_odds]
    
    real_home = [o[0] for o in realtime_odds]
    real_away = [o[2] for o in realtime_odds]
    
    init_8_count = count_ends_with_8(init_odds)
    real_8_count = count_ends_with_8(real_odds)
    
    init_home = [o[0] for o in initial_odds]
    init_away = [o[2] for o in initial_odds]
    init_home_8 = count_ends_with_8(init_home)
    init_away_8 = count_ends_with_8(init_away)
    real_home_8 = count_ends_with_8(real_home)
    real_away_8 = count_ends_with_8(real_away)
    diff_home_8 = real_home_8 - init_home_8
    diff_away_8 = real_away_8 - init_away_8
    
    home_has_88 = any(check_ends_with_88(o) for o in real_home)
    away_has_88 = any(check_ends_with_88(o) for o in real_away)
    
    real_88_count = count_ends_with_88(real_odds)
    choice_has_88 = real_88_count > 0
    
    diff_8 = real_8_count - init_8_count
    
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
        'diff_home_8': diff_home_8,
        'diff_away_8': diff_away_8,
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
    }

def analyze_form_comparison(data):
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
    
    diff = home_wins - away_wins
    rate_diff = home_win_rate - away_win_rate
    
    if diff >= 4 or rate_diff >= 25:
        return {'dominance': 'home_strong', 'diff': diff, 'home_wins': home_wins, 'away_wins': away_wins}
    elif diff <= -4 or rate_diff <= -25:
        return {'dominance': 'away_strong', 'diff': diff, 'home_wins': home_wins, 'away_wins': away_wins}
    else:
        return {'dominance': 'balanced', 'diff': diff, 'home_wins': home_wins, 'away_wins': away_wins}

def analyze_match_final(v7_choice, v7_confidence, eight_analysis, data):
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
    real_8_count = eight_analysis.get('real_8_count', 0)
    real_88_count = eight_analysis.get('real_88_count', 0)
    diff_8 = eight_analysis.get('diff_8', 0)
    
    diff_home_8 = eight_analysis.get('diff_home_8', 0)
    diff_away_8 = eight_analysis.get('diff_away_8', 0)
    
    choice_has_88 = eight_analysis.get('choice_has_88', False)
    home_has_88 = eight_analysis.get('home_has_88', False)
    away_has_88 = eight_analysis.get('away_has_88', False)
    
    high_8_risk = real_8_count >= 3
    
    has_88_risk = choice_has_88
    
    form_analysis = analyze_form_comparison(data)
    dominance = form_analysis['dominance']
    
    eight_increasing = diff_8 > 0
    eight_decreasing = diff_8 < 0
    
    excluded = False
    excluded_reason = ""
    if v7_direction == 'home' and home_has_88:
        excluded = True
        excluded_reason = "主胜有88陷阱"
    elif v7_direction == 'away' and away_has_88:
        excluded = True
        excluded_reason = "客胜有88陷阱"
    
    demoted = False
    demoted_reason = ""
    if not excluded and v7_confidence >= 60:
        if v7_direction == 'home' and not home_has_88 and away_has_88:
            demoted = True
            demoted_reason = "客胜有88，但主胜无88"
        elif v7_direction == 'away' and not away_has_88 and home_has_88:
            demoted = True
            demoted_reason = "主胜有88，但客胜无88"
    
    trap_risk = False
    trap_reason = ""
    if not excluded and not demoted and v7_confidence >= 60:
        if v7_direction == 'home' and dominance == 'home_strong' and eight_increasing:
            trap_risk = True
            trap_reason = "主队强+末尾8增加"
        elif v7_direction == 'away' and dominance == 'away_strong' and eight_increasing:
            trap_risk = True
            trap_reason = "客队强+末尾8增加"
    
    # 新规律1：8变化-5 + 状态极好 = 庄家挡不住，推荐主胜
    minus_five_signal = False
    minus_five_reason = ""
    if not excluded and not demoted:
        if v7_direction == 'home' and dominance == 'home_strong' and diff_home_8 <= -5:
            minus_five_signal = True
            minus_five_reason = "8减少-5+主队极好，庄家挡不住"
        elif v7_direction == 'away' and dominance == 'away_strong' and diff_away_8 <= -5:
            minus_five_signal = True
            minus_five_reason = "8减少-5+客队极好，庄家挡不住"
    
    # 新规律2：8变化-5 + 状态焦灼 = 平局是底限
    minus_five_draw = False
    minus_five_draw_reason = ""
    if not excluded and not demoted and not minus_five_signal:
        if v7_direction == 'home' and dominance == 'balanced' and diff_home_8 <= -5:
            minus_five_draw = True
            minus_five_draw_reason = "8减少-5+状态焦灼，平局是底限"
        elif v7_direction == 'away' and dominance == 'balanced' and diff_away_8 <= -5:
            minus_five_draw = True
            minus_five_draw_reason = "8减少-5+状态焦灼，平局是底限"
    
    # 原逻辑：高置信度+状态极好+末尾8减少 = 推荐平局
    predict_strong = False
    predict_strong_reason = ""
    if not excluded and not demoted and not minus_five_signal and not minus_five_draw and v7_confidence >= 55:
        if v7_direction == 'home' and dominance == 'home_strong' and diff_home_8 < 0:
            predict_strong = True
            predict_strong_reason = "主队强+主胜8减少，平局是底限"
        elif v7_direction == 'away' and dominance == 'away_strong' and diff_away_8 < 0:
            predict_strong = True
            predict_strong_reason = "客队强+客胜8减少，平局是底限"
    
    # 强烈推荐相关
    strong_recommend = False
    strong_reason = ""
    macao_direction = None
    if "和局" in macao_tip or "平局" in macao_tip:
        macao_direction = 'draw'
    elif home_team and home_team in macao_tip:
        macao_direction = 'home'
    elif away_team and away_team in macao_tip:
        macao_direction = 'away'
    
    safe_signal = False
    safe_reason = ""
    if not excluded and not demoted and not trap_risk and not strong_recommend and v7_confidence >= 55:
        if v7_direction == 'home' and dominance == 'balanced' and eight_decreasing:
            safe_signal = True
            safe_reason = "状态相当+末尾8减少"
        elif v7_direction == 'away' and dominance == 'balanced' and eight_decreasing:
            safe_signal = True
            safe_reason = "状态相当+末尾8减少"
    
    basic_confirmed = False
    if eight_signal == '危险':
        if v7_direction == 'home':
            if ("主" in macao_tip and "客" not in macao_tip) and home_win_rate > away_win_rate:
                basic_confirmed = True
        elif v7_direction == 'away':
            if "客" in macao_tip and away_win_rate > home_win_rate:
                basic_confirmed = True
    
    # 最终决策
    if excluded:
        return {
            'recommendation': '排除',
            'reason': f'{excluded_reason}，建议避开',
            'final_choice': None
        }
    elif demoted:
        return {
            'recommendation': '降权',
            'reason': f'{demoted_reason}，有诱盘可能',
            'final_choice': v7_choice
        }
    elif trap_risk:
        return {
            'recommendation': '降权',
            'reason': f'{trap_reason}，诱盘风险高',
            'final_choice': v7_choice
        }
    elif minus_five_signal:
        return {
            'recommendation': '强烈推荐',
            'reason': f'{minus_five_reason}',
            'final_choice': v7_choice
        }
    elif minus_five_draw:
        return {
            'recommendation': '推荐平局',
            'reason': f'{minus_five_draw_reason}',
            'final_choice': 'draw'
        }
    elif predict_strong:
        return {
            'recommendation': '推荐平局',
            'reason': f'{predict_strong_reason}',
            'final_choice': 'draw'
        }
    elif v7_confidence >= 60 and eight_signal == '正常' and not has_88_risk:
        return {
            'recommendation': '强烈推荐',
            'reason': f'高置信度({v7_confidence:.0f}%)+8正常+无末尾88',
            'final_choice': v7_choice
        }
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

def analyze_folder(folder_path):
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
                    data['initial_odds'],
                    data['realtime_odds'],
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
            import traceback
            print(f"Error: {f} - {e}")
            traceback.print_exc()
    
    return results

print("=" * 80)
print("V7 + 8探测 3.16比赛分析")
print("=" * 80)

all_results = analyze_folder(r"d:\work\workbuddy\足球预测\分析模板\3.16")

# 按置信度排序
all_results.sort(key=lambda x: x['confidence'], reverse=True)

print("\n【比赛分析结果】\n")

for r in all_results:
    match_id = r['match_id']
    v7_choice = r['choice']
    v7_pred = {'home': '主胜', 'draw': '平局', 'away': '客胜'}[v7_choice]
    v7_confidence = r['confidence']
    eight = r['eight_analysis']
    final = r['final']
    macao = r['data']['macao_tip']
    home_w = count_wins(r['data']['home_form'])
    away_w = count_wins(r['data']['away_form'])
    
    print(f"{'='*70}")
    print(f"[{r['filename']}]")
    print(f"V7预测: {v7_pred} ({v7_confidence:.0f}%)")
    print(f"澳门推荐: {macao}")
    print(f"主队近况: {r['data']['home_form']} ({home_w}胜)")
    print(f"客队近况: {r['data']['away_form']} ({away_w}胜)")
    print(f"8探测: 初盘{eight['init_8_count']} -> 即时{eight['real_8_count']} (变化{eight['diff_8']:+d})")
    print(f"  主胜8变化: {eight['diff_home_8']:+d}, 客胜8变化: {eight['diff_away_8']:+d}")
    print(f"模式: {eight['pattern']}")
    print(f"最终推荐: {final['recommendation']} - {final['reason']}")
