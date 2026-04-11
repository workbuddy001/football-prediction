# V7 + 8探测 + 基本面 优化版V2 - 更精准的过滤策略
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

def make_decision_v2(v7_choice, v7_confidence, eight_analysis, data):
    """
    优化版决策逻辑 V2 - 只保留置信度55%以上，更严格的基本面要求
    
    策略：
    1. 置信度>=55% + 8探测正常 + 澳门推荐 -> 强烈推荐
    2. 置信度>=60% + 8探测危险 + 基本面非常强 -> 谨慎推荐
    3. 置信度>=70% + 8探测正常 -> 也可推荐
    4. 其他 -> 不推荐
    """
    
    home_wins = count_wins(data['home_form'])
    away_wins = count_wins(data['away_form'])
    macao_tip = data['macao_tip'].upper() if data['macao_tip'] else ""
    
    # 提取胜率
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
    
    # 基本面确认 - 更严格
    basic_confirmed = False
    if eight_signal == '危险':
        # 检查基本面是否强支持V7预测
        if v7_direction == 'home':
            # 主胜预测：澳门推荐主队 + 胜率明显更高
            if ("主" in macao_tip and "客" not in macao_tip) and home_win_rate > away_win_rate:
                basic_confirmed = True
        elif v7_direction == 'away':
            # 客胜预测：澳门推荐客队 + 胜率明显更高
            if "客" in macao_tip and away_win_rate > home_win_rate:
                basic_confirmed = True
    
    # 决策
    if v7_confidence >= 55 and eight_signal == '正常' and ("主" in macao_tip or "客" in macao_tip):
        # 8正常 + 有澳门推荐
        return {
            'recommendation': '强烈推荐',
            'reason': f'高置信度({v7_confidence:.0f}%)+8正常+澳门推荐'
        }
    elif v7_confidence >= 70 and eight_signal == '正常':
        # 超高置信度
        return {
            'recommendation': '强烈推荐',
            'reason': f'超高置信度({v7_confidence:.0f}%)+8正常'
        }
    elif v7_confidence >= 60 and eight_signal == '危险' and basic_confirmed:
        return {
            'recommendation': '谨慎推荐',
            'reason': f'高置信度({v7_confidence:.0f}%)+基本面强确认'
        }
    else:
        return {
            'recommendation': '不推荐',
            'reason': f'条件不满足(8:{eight_signal}, 置信度:{v7_confidence:.0f}%)'
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
    results['周五010'] = '平局'
    results['周五011'] = '主胜'
    results['周五012'] = '主胜'
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
                result['data'] = data
                
                eight_analysis = analyze_8_pattern(
                    result['initial_odds'], 
                    result['realtime_odds'],
                    result['choice']
                )
                result['eight_analysis'] = eight_analysis
                
                decision = make_decision_v2(
                    result['choice'],
                    result['confidence'],
                    eight_analysis,
                    data
                )
                result['decision'] = decision
                
                results.append(result)
        except Exception as e:
            print(f"Error: {f} - {e}")
    
    return results

actual_results = load_actual_results()

print("=" * 80)
print("V7 + 8探测 + 基本面 优化版V2")
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
v7_correct = 0
v7_total = 0
opt_correct = 0
opt_total = 0
strong_correct = 0
strong_total = 0
cautious_correct = 0
cautious_total = 0

print("\n--- 推荐比赛详情 ---\n")

for r in all_results:
    match_id = r['match_id']
    if match_id not in actual_results:
        continue
    
    actual = actual_results[match_id]
    v7_choice = r['choice']
    v7_pred = {'home': '主胜', 'draw': '平局', 'away': '客胜'}[v7_choice]
    v7_confidence = r['confidence']
    recommendation = r['decision']['recommendation']
    eight_signal = r['eight_analysis'].get('signal', '正常')
    
    v7_total += 1
    if v7_pred == actual:
        v7_correct += 1
    
    if recommendation in ['强烈推荐', '谨慎推荐']:
        opt_total += 1
        if v7_pred == actual:
            opt_correct += 1
        
        is_correct = "正确" if v7_pred == actual else "错误"
        print(f"{r['filename']}:")
        print(f"  预测: {v7_pred}({v7_confidence:.0f}%), 实际: {actual} [{is_correct}]")
        print(f"  8探测: {eight_signal}, 决策: {recommendation}")
        print(f"  原因: {r['decision']['reason']}")
        print()
        
        if recommendation == '强烈推荐':
            strong_total += 1
            if v7_pred == actual:
                strong_correct += 1
        elif recommendation == '谨慎推荐':
            cautious_total += 1
            if v7_pred == actual:
                cautious_correct += 1

v7_hit_rate = v7_correct / v7_total * 100 if v7_total > 0 else 0
opt_hit_rate = opt_correct / opt_total * 100 if opt_total > 0 else 0
strong_hit_rate = strong_correct / strong_total * 100 if strong_total > 0 else 0
cautious_hit_rate = cautious_correct / cautious_total * 100 if cautious_total > 0 else 0

print("=" * 80)
print("统计结果")
print("=" * 80)
print(f"\n【V7原始算法】")
print(f"  总场次: {v7_total}, 正确: {v7_correct}, 命中率: {v7_hit_rate:.1f}%")

print(f"\n【优化版总体】")
print(f"  推荐场次: {opt_total}, 正确: {opt_correct}, 命中率: {opt_hit_rate:.1f}%")

if strong_total > 0:
    print(f"\n【强烈推荐】(置信度>=50% + 8正常)")
    print(f"  场次: {strong_total}, 正确: {strong_correct}, 命中率: {strong_hit_rate:.1f}%")

if cautious_total > 0:
    print(f"\n【谨慎推荐】(置信度>=60% + 8危险 + 基本面确认)")
    print(f"  场次: {cautious_total}, 正确: {cautious_correct}, 命中率: {cautious_hit_rate:.1f}%")

improvement = opt_hit_rate - v7_hit_rate
print(f"\n【提升效果】")
print(f"  命中率提升: {improvement:+.1f}%")
print(f"  过滤掉比赛: {v7_total - opt_total} 场")
