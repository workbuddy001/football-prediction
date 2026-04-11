# V7 + 8探测 + 基本面 优化版回溯分析
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
    
    # 提取主客队近况（胜率等）
    home_form_str = re.search(r'\| 主队近况 \|\s*(.+)', content)
    if not home_form_str:
        home_form_str = re.search(r'主队近况\s*\|\s*(.+)', content)
    away_form_str = re.search(r'\| 客队近况 \|\s*(.+)', content)
    if not away_form_str:
        away_form_str = re.search(r'客队近况\s*\|\s*(.+)', content)
    
    # 让球
    handicap = re.search(r'\| 让球 \|\s*(.+)', content)
    if not handicap:
        handicap = re.search(r'让球\s*\|\s*(.+)', content)
    
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
        'handicap': clean_value(handicap.group(1)) if handicap else '',
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

def analyze_8_pattern(initial_odds, realtime_odds, choice_type):
    if not initial_odds or not realtime_odds:
        return {}
    
    idx = {'home': 0, 'draw': 1, 'away': 2}[choice_type]
    
    init_odds = [o[idx] for o in initial_odds]
    real_odds = [o[idx] for o in realtime_odds]
    
    init_8_count = count_ends_with_8(init_odds)
    real_8_count = count_ends_with_8(real_odds)
    
    diff_8 = real_8_count - init_8_count
    
    if real_8_count == 0 and init_8_count > 0:
        pattern = "真空避险"
        signal = "安全"
    elif diff_8 > 0:
        pattern = "补饵收割"
        signal = "危险"
    elif real_8_count >= 10:
        pattern = "超饱和"
        signal = "危险"
    else:
        pattern = "正常"
        signal = "正常"
    
    return {
        'init_8_count': init_8_count,
        'real_8_count': real_8_count,
        'diff_8': diff_8,
        'pattern': pattern,
        'signal': signal,
    }

def analyze_basic_factors(data):
    """基本面分析 - 判断基本面是否一边倒"""
    home_wins = count_wins(data['home_form'])
    away_wins = count_wins(data['away_form'])
    home_draws = count_draws(data['home_form'])
    away_draws = count_draws(data['away_form'])
    home_losses = count_losses(data['home_form'])
    away_losses = count_losses(data['away_form'])
    
    macao_tip = data['macao_tip'].upper() if data['macao_tip'] else ""
    
    # 从近况字符串中提取胜率
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
    
    # 判断基本面是否一边倒 (更宽松的条件)
    basic_clear = False
    basic_direction = None  # 'home' or 'away'
    
    # 条件1: 澳门推荐明确 + 胜率不差
    if "主" in macao_tip and "客" not in macao_tip:
        if home_win_rate >= away_win_rate:  # 主队胜率不低于客队
            basic_clear = True
            basic_direction = 'home'
    elif "客" in macao_tip:
        if away_win_rate >= home_win_rate:  # 客队胜率不低于主队
            basic_clear = True
            basic_direction = 'away'
    
    # 条件2: 主队近况很好 (W>=3) 且客队较差 (W<=2)
    if home_wins >= 3 and away_wins <= 2:
        basic_clear = True
        basic_direction = 'home'
    
    # 条件3: 客队近况很好 (W>=3) 且主队较差 (W<=2)
    if away_wins >= 3 and home_wins <= 2:
        basic_clear = True
        basic_direction = 'away'
    
    # 条件4: 澳门推荐 + 高胜率 (>=50%)
    if "主" in macao_tip and "客" not in macao_tip and home_win_rate >= 50:
        basic_clear = True
        basic_direction = 'home'
    if "客" in macao_tip and away_win_rate >= 50:
        basic_clear = True
        basic_direction = 'away'
    
    return {
        'basic_clear': basic_clear,
        'basic_direction': basic_direction,
        'home_win_rate': home_win_rate,
        'away_win_rate': away_win_rate,
        'home_wins': home_wins,
        'away_wins': away_wins,
        'macao_tip': macao_tip,
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
    
    # V7算法
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

def make_final_decision(v7_choice, v7_confidence, eight_analysis, basic_factors):
    """
    综合决策：V7 + 8探测 + 基本面
    
    逻辑：
    1. 置信度<50% -> 不推荐
    2. 8探测正常 -> 推荐V7预测
    3. 8探测危险 + 基本面一边倒 -> 仍推荐V7预测
    4. 8探测危险 + 基本面不明确 -> 不推荐/改选其他
    """
    
    if v7_confidence < 50:
        return {
            'final_choice': v7_choice,
            'recommendation': '不推荐',
            'reason': '置信度低于50%'
        }
    
    eight_signal = eight_analysis.get('signal', '正常')
    basic_clear = basic_factors['basic_clear']
    basic_direction = basic_factors['basic_direction']
    
    # V7预测的方向
    v7_direction = v7_choice
    
    if eight_signal == '正常':
        return {
            'final_choice': v7_choice,
            'recommendation': '推荐',
            'reason': '8探测正常'
        }
    elif eight_signal == '危险':
        if basic_clear and basic_direction == v7_direction:
            # 基本面明确指向V7预测方向，可以跟进
            return {
                'final_choice': v7_choice,
                'recommendation': '基本面确认可跟进',
                'reason': f'8探测危险但基本面一边倒({basic_direction})'
            }
        else:
            # 基本面不明确，避开
            return {
                'final_choice': v7_choice,
                'recommendation': '不推荐',
                'reason': '8探测危险+基本面不明确'
            }
    
    return {
        'final_choice': v7_choice,
        'recommendation': '待观察',
        'reason': '其他情况'
    }

def load_actual_results():
    """加载实际比赛结果"""
    results = {}
    
    # 3.13 结果
    results['周五001'] = '客胜'
    results['周五002'] = '主胜'
    results['周五003'] = '客胜'
    results['周五004'] = '客胜'
    results['周五005'] = '主胜'
    results['周五006'] = '客胜'
    results['周五007'] = '平局'
    results['周五008'] = '客胜'
    results['周五009'] = '主胜'
    results['周五010'] = '平局'
    results['周五011'] = '主胜'
    results['周五012'] = '主胜'
    
    # 3.14 结果
    results['周六001'] = '主胜'
    results['周六002'] = '客胜'
    results['周六003'] = '主胜'
    results['周六004'] = '客胜'
    results['周六005'] = '平局'
    results['周六006'] = '客胜'
    results['周六007'] = '客胜'
    results['周六008'] = '客胜'
    results['周六009'] = '主胜'
    results['周六010'] = '平局'
    results['周六011'] = '客胜'
    results['周六012'] = '主胜'
    results['周六013'] = '平局'
    results['周六014'] = '主胜'
    results['周六015'] = '客胜'
    results['周六016'] = '平局'
    
    # 3.15 结果
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
    results['周日011'] = '客胜'
    results['周日012'] = '客胜'
    results['周日013'] = '主胜'
    results['周日014'] = '平局'
    results['周日015'] = '主胜'
    results['周日016'] = '客胜'
    results['周日017'] = '主胜'
    results['周日018'] = '客胜'
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
                result['day'] = day_name
                
                # 8探测分析
                eight_analysis = analyze_8_pattern(
                    result['initial_odds'], 
                    result['realtime_odds'],
                    result['choice']
                )
                result['eight_analysis'] = eight_analysis
                
                # 基本面分析
                basic_factors = analyze_basic_factors(data)
                result['basic_factors'] = basic_factors
                
                # 最终决策
                final_decision = make_final_decision(
                    result['choice'],
                    result['confidence'],
                    eight_analysis,
                    basic_factors
                )
                result['final_decision'] = final_decision
                
                results.append(result)
        except Exception as e:
            print(f"Error: {f} - {e}")
    
    return results

# 加载实际结果
actual_results = load_actual_results()

# 分析三个文件夹
print("=" * 80)
print("V7 + 8探测 + 基本面 优化版回溯分析")
print("=" * 80)

all_results = []

folders = [
    (r"d:\work\workbuddy\足球预测\分析模板\3.13", "周五"),
    (r"d:\work\workbuddy\足球预测\分析模板\3.14", "周六"),
    (r"d:\work\workbuddy\足球预测\分析模板\3.15", "周日"),
]

for folder, day in folders:
    results = analyze_folder(folder, day)
    all_results.extend(results)

# 统计
print("\n" + "=" * 80)
print("回溯分析结果")
print("=" * 80)

# 1. V7原始命中率
v7_correct = 0
v7_total = 0

# 2. 优化版命中率
opt_correct = 0
opt_total = 0

# 3. 详细统计
details = []

for r in all_results:
    match_id = r['match_id']
    if match_id not in actual_results:
        continue
    
    actual = actual_results[match_id]
    v7_choice = r['choice']
    v7_pred = {'home': '主胜', 'draw': '平局', 'away': '客胜'}[v7_choice]
    v7_confidence = r['confidence']
    eight_signal = r['eight_analysis'].get('signal', '正常')
    basic_clear = r['basic_factors']['basic_clear']
    basic_direction = r['basic_factors']['basic_direction']
    recommendation = r['final_decision']['recommendation']
    
    # V7原始统计
    v7_total += 1
    if v7_pred == actual:
        v7_correct += 1
    
    # 优化版统计 (只统计推荐的比赛)
    if recommendation in ['推荐', '基本面确认可跟进']:
        opt_total += 1
        if v7_pred == actual:
            opt_correct += 1
    
    # 打印推荐比赛的详情
    if recommendation in ['推荐', '基本面确认可跟进']:
        is_correct = "正确" if v7_pred == actual else "错误"
        print(f"\n{r['filename']}:")
        print(f"  V7预测: {v7_pred}({v7_confidence:.0f}%), 实际: {actual} [{is_correct}]")
        print(f"  8探测: {eight_signal}, 基本面: {'一边倒(' + basic_direction + ')' if basic_clear else '不明确'}")
        print(f"  最终决策: {recommendation}")

# 计算命中率
v7_hit_rate = v7_correct / v7_total * 100 if v7_total > 0 else 0
opt_hit_rate = opt_correct / opt_total * 100 if opt_total > 0 else 0

print("\n" + "=" * 80)
print("统计结果")
print("=" * 80)
print(f"\n【V7原始算法】")
print(f"  总场次: {v7_total}")
print(f"  正确: {v7_correct}")
print(f"  命中率: {v7_hit_rate:.1f}%")

print(f"\n【优化版 V7+8探测+基本面】")
print(f"  推荐的场次: {opt_total}")
print(f"  正确: {opt_correct}")
print(f"  命中率: {opt_hit_rate:.1f}%")

print(f"\n【提升效果】")
if opt_total > 0:
    improvement = opt_hit_rate - v7_hit_rate
    print(f"  命中率提升: {improvement:+.1f}%")
    print(f"  过滤掉比赛: {v7_total - opt_total} 场")
