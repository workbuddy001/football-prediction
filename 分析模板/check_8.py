# V7 + 末位8探测准则分析 3.16 比赛
import os
import re
import numpy as np
from collections import Counter

def extract_odds_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    home_team = re.search(r'\| 主队 \|\s*(.+)', content)
    away_team = re.search(r'\| 客队 \|\s*(.+)', content)
    league = re.search(r'\| 赛事 \|\s*(.+)', content)
    home_form = re.search(r'\| 主队近况走势 \|\s*(.+)', content)
    away_form = re.search(r'\| 客队近况走势 \|\s*(.+)', content)
    macao_tip = re.search(r'\| 澳门推荐 \|\s*(.+)', content)
    
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
    """获取赔率的末位数字"""
    s = f"{odds:.2f}"
    # 取小数点后两位
    last = s[-1]
    return last

def count_ends_with_8(odds_list):
    """统计赔率中末位是8的数量"""
    return sum(1 for o in odds_list if get_last_digit(o) == '8')

def count_double_8(odds_list):
    """统计赔率中双8（如1.88, 3.88）的数量"""
    return sum(1 for o in odds_list if abs(o - round(o)) < 0.001 and str(o).endswith('88'))

def analyze_8_pattern(initial_odds, realtime_odds, choice_type):
    """
    末位8探测准则分析
    choice_type: 'home', 'draw', 'away'
    """
    if not initial_odds or not realtime_odds:
        return {}
    
    # 提取对应选项的赔率
    idx = {'home': 0, 'draw': 1, 'away': 2}[choice_type]
    
    init_odds = [o[idx] for o in initial_odds]
    real_odds = [o[idx] for o in realtime_odds]
    
    # 统计末位8的数量
    init_8_count = count_ends_with_8(init_odds)
    real_8_count = count_ends_with_8(real_odds)
    
    # 统计双88的数量
    init_88_count = count_double_8(init_odds)
    real_88_count = count_double_8(real_odds)
    
    # 变化分析
    diff_8 = real_8_count - init_8_count
    diff_88 = real_88_count - init_88_count
    
    # 判断模式
    if real_8_count == 0 and init_8_count > 0:
        pattern = "真空避险"  # 8消失，生门
        signal = "安全"
    elif diff_8 > 0 or diff_88 > 0:
        pattern = "补饵收割"  # 8增多，危险
        signal = "危险"
    elif real_8_count >= 10:  # 超过1/3的公司该选项末位是8
        pattern = "超饱和"
        signal = "危险"
    else:
        pattern = "正常"
        signal = "正常"
    
    return {
        'init_8_count': init_8_count,
        'real_8_count': real_8_count,
        'init_88_count': init_88_count,
        'real_88_count': real_88_count,
        'diff_8': diff_8,
        'diff_88': diff_88,
        'pattern': pattern,
        'signal': signal,
        'avg_odds': np.mean(real_odds)
    }

def analyze_match_v7(data):
    """V7优化版算法"""
    if not data['initial_odds'] or not data['realtime_odds']:
        return None
    
    real_home = [o[0] for o in data['realtime_odds']]
    real_draw = [o[1] for o in data['realtime_odds']]
    real_away = [o[2] for o in data['realtime_odds']]
    
    # 变化百分比
    home_pct = [(data['realtime_odds'][i][0] - data['initial_odds'][i][0]) / data['initial_odds'][i][0] * 100 
                for i in range(len(data['initial_odds']))]
    draw_pct = [(data['realtime_odds'][i][1] - data['initial_odds'][i][1]) / data['initial_odds'][i][1] * 100 
                for i in range(len(data['initial_odds']))]
    away_pct = [(data['realtime_odds'][i][2] - data['initial_odds'][i][2]) / data['initial_odds'][i][2] * 100 
                for i in range(len(data['initial_odds']))]
    
    # 概率
    real_home_prob = [1/x*100 for x in real_home]
    real_draw_prob = [1/x*100 for x in real_draw]
    real_away_prob = [1/x*100 for x in real_away]
    
    # 统计变化趋势
    home_up_pct = sum(1 for x in home_pct if x > 0) / len(home_pct) * 100
    home_down_pct = sum(1 for x in home_pct if x < 0) / len(home_pct) * 100
    draw_up_pct = sum(1 for x in draw_pct if x > 0) / len(draw_pct) * 100
    draw_down_pct = sum(1 for x in draw_pct if x < 0) / len(draw_pct) * 100
    away_up_pct = sum(1 for x in away_pct if x > 0) / len(away_pct) * 100
    away_down_pct = sum(1 for x in away_pct if x < 0) / len(away_pct) * 100
    
    # 平均值
    avg_home = np.mean(real_home)
    avg_draw = np.mean(real_draw)
    avg_away = np.mean(real_away)
    
    avg_home_prob = np.mean(real_home_prob)
    avg_draw_prob = np.mean(real_draw_prob)
    avg_away_prob = np.mean(real_away_prob)
    
    # 近况分析
    home_wins = count_wins(data['home_form'])
    away_wins = count_wins(data['away_form'])
    home_losses = count_losses(data['home_form'])
    away_losses = count_losses(data['away_form'])
    home_draws = count_draws(data['home_form'])
    away_draws = count_draws(data['away_form'])
    
    # 澳门推荐
    macao_tip = data['macao_tip'].upper() if data['macao_tip'] else ""
    
    # V7算法
    if avg_home < 1.5:
        choice = 'home'
        first_choice = f"{data['home_team']}主胜"
        reason = "强队主场"
    elif avg_away < 1.5:
        choice = 'away'
        first_choice = f"{data['away_team']}客胜"
        reason = "强队客场"
    elif "主" in macao_tip and "客" not in macao_tip:
        choice = 'home'
        first_choice = f"{data['home_team']}主胜"
        reason = "澳门推荐主胜"
    elif "客" in macao_tip:
        choice = 'away'
        first_choice = f"{data['away_team']}客胜"
        reason = "澳门推荐客胜"
    elif home_draws >= 3 and away_draws >= 3 and abs(avg_home_prob - avg_away_prob) < 15:
        choice = 'draw'
        first_choice = "平局"
        reason = "两队近况多平局"
    elif 2.5 < avg_home < 4.5 and 2.0 < avg_away < 4.0 and abs(home_wins - away_wins) <= 1:
        choice = 'draw'
        first_choice = "平局"
        reason = "强强对话均势"
    elif avg_draw_prob > 28 and abs(avg_home_prob - avg_away_prob) < 10:
        choice = 'draw'
        first_choice = "平局"
        reason = "平局概率突出"
    elif home_up_pct > 40 and away_up_pct > 40 and draw_down_pct > 40:
        choice = 'draw'
        first_choice = "平局"
        reason = "胜赔上升平局降"
    elif home_wins >= 4 and avg_home < 2.5:
        choice = 'home'
        first_choice = f"{data['home_team']}主胜"
        reason = "主队近况很好"
    elif away_wins >= 4 and avg_away < 2.5:
        choice = 'away'
        first_choice = f"{data['away_team']}客胜"
        reason = "客队近况很好"
    elif avg_home_prob > avg_away_prob + 10 and avg_home_prob > avg_draw_prob + 8:
        choice = 'home'
        first_choice = f"{data['home_team']}主胜"
        reason = "主胜概率优势明显"
    elif avg_away_prob > avg_home_prob + 10 and avg_away_prob > avg_draw_prob + 8:
        choice = 'away'
        first_choice = f"{data['away_team']}客胜"
        reason = "客胜概率优势明显"
    elif avg_home_prob >= avg_away_prob and avg_home_prob >= avg_draw_prob:
        choice = 'home'
        first_choice = f"{data['home_team']}主胜"
        reason = "主胜概率最高"
    elif avg_away_prob >= avg_home_prob and avg_away_prob >= avg_draw_prob:
        choice = 'away'
        first_choice = f"{data['away_team']}客胜"
        reason = "客胜概率最高"
    else:
        choice = 'draw'
        first_choice = "平局"
        reason = "默认平局"
    
    # 计算置信度
    prob_map = {'home': avg_home_prob, 'draw': avg_draw_prob, 'away': avg_away_prob}
    confidence = prob_map.get(choice, 0)
    
    return {
        'home_team': data['home_team'],
        'away_team': data['away_team'],
        'league': data['league'],
        'choice': choice,
        'first_choice': first_choice,
        'confidence': confidence,
        'reason': reason,
        'initial_odds': data['initial_odds'],
        'realtime_odds': data['realtime_odds'],
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
                result['filename'] = f.replace('_源数据.md', '')
                # 添加8探测分析
                eight_analysis = analyze_8_pattern(
                    result['initial_odds'], 
                    result['realtime_odds'],
                    result['choice']
                )
                result['eight_analysis'] = eight_analysis
                results.append(result)
        except Exception as e:
            print(f"Error: {f} - {e}")
    
    return results

# 分析3.16文件夹
print("=" * 80)
print("V7算法 + 末位8探测准则 3.16 比赛分析")
print("=" * 80)

results_316 = analyze_folder(r"d:\work\workbuddy\足球预测\分析模板\3.16")

print("\n" + "=" * 80)
print("预测结果及8探测分析 (置信度>=50%)")
print("=" * 80)

for r in results_316:
    conf = r['confidence']
    if conf >= 50:
        eight = r['eight_analysis']
        
        print(f"\n【{r['filename']}】{r['home_team']} vs {r['away_team']}")
        print(f"  预测: **{r['first_choice']}** (置信度: {conf:.0f}%)")
        print(f"  依据: {r['reason']}")
        
        if eight:
            print(f"  --- 末位8探测 ---")
            print(f"  初盘末位8数量: {eight['init_8_count']}/30")
            print(f"  即时盘末位8数量: {eight['real_8_count']}/30")
            print(f"  初盘双88数量: {eight['init_88_count']}/30")
            print(f"  即时盘双88数量: {eight['real_88_count']}/30")
            print(f"  模式: {eight['pattern']} -> {eight['signal']}")
            print(f"  平均赔率: {eight['avg_odds']:.2f}")
            
            # 给出建议
            if eight['signal'] == '危险':
                print(f"  警告: 该选项存在数字陷阱风险!")
            elif eight['signal'] == '安全':
                print(f"  安全: 该选项为真空避险区域")

print("\n" + "=" * 80)
print("置信度<50%的比赛 (参考)")
print("=" * 80)

for r in results_316:
    conf = r['confidence']
    if conf < 50:
        print(f"\n【{r['filename']}】{r['home_team']} vs {r['away_team']}")
        print(f"  预测: **{r['first_choice']}** (置信度: {conf:.0f}%)")
        print(f"  依据: {r['reason']}")

# 统计
print("\n" + "=" * 80)
print("统计汇总")
print("=" * 80)
high_conf = [r for r in results_316 if r['confidence'] >= 50]
low_conf = [r for r in results_316 if r['confidence'] < 50]
danger_count = sum(1 for r in high_conf if r['eight_analysis']['signal'] == '危险')
safe_count = sum(1 for r in high_conf if r['eight_analysis']['signal'] == '安全')
normal_count = sum(1 for r in high_conf if r['eight_analysis']['signal'] == '正常')

print(f"高置信度(>=50%): {len(high_conf)} 场")
print(f"  - 危险信号: {danger_count} 场")
print(f"  - 安全信号: {safe_count} 场")
print(f"  - 正常: {normal_count} 场")
print(f"低置信度(<50%): {len(low_conf)} 场")
