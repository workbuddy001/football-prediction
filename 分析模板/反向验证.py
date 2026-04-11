# 强烈推荐反向验证 - 3.13-3.15数据
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

def get_last_digit(odds):
    s = f"{odds:.2f}"
    return s[-1]

def count_ends_with_8(odds_list):
    return sum(1 for o in odds_list if get_last_digit(o) == '8')

def check_ends_with_88(odds):
    s = f"{odds:.2f}"
    return s[-2:] == '88'

def analyze_8_pattern(initial_odds, realtime_odds, choice_type):
    if not initial_odds or not realtime_odds:
        return {}
    
    idx = {'home': 0, 'draw': 1, 'away': 2}[choice_type]
    
    real_home = [o[0] for o in realtime_odds]
    real_away = [o[2] for o in realtime_odds]
    
    init_home = [o[0] for o in initial_odds]
    init_away = [o[2] for o in initial_odds]
    init_home_8 = count_ends_with_8(init_home)
    init_away_8 = count_ends_with_8(init_away)
    real_home_8 = count_ends_with_8(real_home)
    real_away_8 = count_ends_with_8(real_away)
    diff_home_8 = real_home_8 - init_home_8
    diff_away_8 = real_away_8 - init_away_8
    
    return {
        'diff_home_8': diff_home_8,
        'diff_away_8': diff_away_8,
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
        return {'dominance': 'home_strong', 'diff': diff}
    elif diff <= -4 or rate_diff <= -25:
        return {'dominance': 'away_strong', 'diff': diff}
    else:
        return {'dominance': 'balanced', 'diff': diff}

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
    home_draws = sum(1 for c in data['home_form'].upper() if c == 'D')
    away_draws = sum(1 for c in data['away_form'].upper() if c == 'D')
    
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
    results['周五010'] = '主胜'
    results['周五011'] = '主胜'
    results['周五012'] = '主胜'
    results['周六001'] = '平局'
    results['周六002'] = '客胜'
    results['周六003'] = '主胜'
    results['周六004'] = '客胜'
    results['周六005'] = '平局'
    results['周六006'] = '客胜'
    results['周六007'] = '客胜'
    results['周六008'] = '主胜'
    results['周六009'] = '主胜'
    results['周六010'] = '平局'
    results['周六011'] = '客胜'
    results['周六012'] = '平局'
    results['周六013'] = '平局'
    results['周六014'] = '主胜'
    results['周六015'] = '主胜'
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
    results['周日010'] = '主胜'
    results['周日011'] = '主胜'
    results['周日012'] = '客胜'
    results['周日013'] = '主胜'
    results['周日014'] = '主胜'
    results['周日015'] = '主胜'
    results['周日016'] = '客胜'
    results['周日017'] = '主胜'
    results['周日018'] = '主胜'
    results['周日019'] = '主胜'
    return results

def analyze_folder(folder_path):
    files = [f for f in os.listdir(folder_path) if f.endswith('_源数据.md')]
    
    results = []
    for f in sorted(files):
        filepath = os.path.join(folder_path, f)
        try:
            data = extract_odds_from_file(filepath)
            v7 = analyze_match_v7(data)
            if v7:
                filename = f.replace('_源数据.md', '')
                match = re.search(r'(周[一二三五六日])(\d+)', filename)
                if match:
                    match_id = f"{match.group(1)}{int(match.group(2)):03d}"
                else:
                    continue
                
                eight = analyze_8_pattern(data['initial_odds'], data['realtime_odds'], v7['choice'])
                form = analyze_form_comparison(data)
                
                # 解析澳门推荐
                macao_tip = data['macao_tip'] if data['macao_tip'] else ""
                home_team = data['home_team']
                away_team = data['away_team']
                
                macao_direction = None
                if "和局" in macao_tip or "平局" in macao_tip:
                    macao_direction = 'draw'
                elif home_team and home_team in macao_tip:
                    macao_direction = 'home'
                elif away_team and away_team in macao_tip:
                    macao_direction = 'away'
                
                results.append({
                    'filename': filename,
                    'match_id': match_id,
                    'home_team': data['home_team'],
                    'away_team': data['away_team'],
                    'v7_choice': v7['choice'],
                    'v7_confidence': v7['confidence'],
                    'macao_direction': macao_direction,
                    'dominance': form['dominance'],
                    'diff_home_8': eight.get('diff_home_8', 0),
                    'diff_away_8': eight.get('diff_away_8', 0),
                    'data': data,
                })
        except Exception as e:
            print(f"Error: {f} - {e}")
    
    return results

actual_results = load_actual_results()

print("=" * 100)
print("反向验证：强烈推荐信号出现时，打反向！")
print("=" * 100)

all_results = []
folders = [
    (r"d:\work\workbuddy\足球预测\分析模板\3.13", "周五"),
    (r"d:\work\workbuddy\足球预测\分析模板\3.14", "周六"),
    (r"d:\work\workbuddy\足球预测\分析模板\3.15", "周日"),
]

for folder, day in folders:
    results = analyze_folder(folder)
    all_results.extend(results)

# 找出满足"强烈推荐"信号的比赛（状态焦灼+澳门推荐方向末尾8减少）
print("\n" + "=" * 100)
print("【强烈推荐信号】= 状态焦灼 + 澳门推荐方向末尾8减少")
print("=" * 100)

reverse_signal_matches = []
for r in all_results:
    match_id = r['match_id']
    if match_id not in actual_results:
        continue
    
    actual = actual_results[match_id]
    v7_choice = r['v7_choice']
    dominance = r['dominance']
    macao_dir = r['macao_direction']
    
    # 强烈推荐信号条件：状态焦灼 + 澳门推荐方向末尾8减少
    is_strong_signal = False
    signal_desc = ""
    
    if dominance == 'balanced':
        if macao_dir == 'home' and r['diff_home_8'] < 0:
            is_strong_signal = True
            signal_desc = "状态焦灼+澳门推荐主胜+主胜8减少"
        elif macao_dir == 'away' and r['diff_away_8'] < 0:
            is_strong_signal = True
            signal_desc = "状态焦灼+澳门推荐客胜+客胜8减少"
    
    if is_strong_signal:
        # 正向预测（按原逻辑推荐方）
        v7_pred = {'home': '主胜', 'draw': '平局', 'away': '客胜'}[v7_choice]
        
        # 反向预测：主胜->客胜，客胜->主胜
        if v7_choice == 'home':
            reverse_pred = '客胜'
        elif v7_choice == 'away':
            reverse_pred = '主胜'
        else:
            reverse_pred = '主胜' if actual != '客胜' else '客胜'
        
        reverse_signal_matches.append({
            'filename': r['filename'],
            'home_team': r['home_team'],
            'away_team': r['away_team'],
            'signal': signal_desc,
            'v7_pred': v7_pred,
            'v7_confidence': r['v7_confidence'],
            'actual': actual,
            'reverse_pred': reverse_pred,
            'v7_correct': v7_pred == actual,
            'reverse_correct': reverse_pred == actual,
        })

# 统计
if reverse_signal_matches:
    v7_total = len(reverse_signal_matches)
    v7_correct = sum(1 for m in reverse_signal_matches if m['v7_correct'])
    reverse_total = len(reverse_signal_matches)
    reverse_correct = sum(1 for m in reverse_signal_matches if m['reverse_correct'])
    
    print(f"\n满足【强烈推荐信号】的比赛共 {v7_total} 场：\n")
    for m in reverse_signal_matches:
        v7_result = "对" if m['v7_correct'] else "错"
        reverse_result = "对" if m['reverse_correct'] else "错"
        print(f"  {m['filename']}: {m['home_team']} vs {m['away_team']}")
        print(f"    信号: {m['signal']}")
        print(f"    原预测: {m['v7_pred']} ({v7_result})  实际: {m['actual']}")
        print(f"    反向预测: {m['reverse_pred']} ({reverse_result})")
        print()
    
    print("=" * 80)
    print("【验证结果】")
    print("=" * 80)
    v7_hit = v7_correct / v7_total * 100 if v7_total > 0 else 0
    reverse_hit = reverse_correct / reverse_total * 100 if reverse_total > 0 else 0
    print(f"按原逻辑（推荐方打出）: {v7_correct}/{v7_total} = {v7_hit:.1f}%")
    print(f"按反向逻辑（不推荐方）: {reverse_correct}/{reverse_total} = {reverse_hit:.1f}%")
    print(f"\n反向打命中率提升: {reverse_hit - v7_hit:+.1f}%")
else:
    print("没有找到满足强烈推荐信号的比赛")
