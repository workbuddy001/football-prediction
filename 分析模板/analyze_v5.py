# V5优化版赔率分析算法
import os
import re
import numpy as np

def extract_odds_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    home_team = re.search(r'主队\s*\|\s*(.+)', content)
    away_team = re.search(r'客队\s*\|\s*(.+)', content)
    match_time = re.search(r'比赛时间\s*\|\s*(.+)', content)
    league = re.search(r'赛事\s*\|\s*(.+)', content)
    home_form = re.search(r'主队近况走势\s*\|\s*(.+)', content)
    away_form = re.search(r'客队近况走势\s*\|\s*(.+)', content)
    home_handicap = re.search(r'主队盘路走势\s*\|\s*(.+)', content)
    away_handicap = re.search(r'客队盘路走势\s*\|\s*(.+)', content)
    history = re.search(r'历史交锋\s*\|\s*(.+)', content)
    macao_tip = re.search(r'澳门推荐\s*\|\s*(.+)', content)
    
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
    
    return {
        'home_team': home_team.group(1).strip() if home_team else '',
        'away_team': away_team.group(1).strip() if away_team else '',
        'match_time': match_time.group(1).strip() if match_time else '',
        'league': league.group(1).strip() if league else '',
        'home_form': home_form.group(1).strip() if home_form else '',
        'away_form': away_form.group(1).strip() if away_form else '',
        'home_handicap': home_handicap.group(1).strip() if home_handicap else '',
        'away_handicap': away_handicap.group(1).strip() if away_handicap else '',
        'history': history.group(1).strip() if history else '',
        'macao_tip': macao_tip.group(1).strip() if macao_tip else '',
        'initial_odds': initial_odds,
        'realtime_odds': realtime_odds,
    }

def find_macao_odds(odds_list):
    for i, odds in enumerate(odds_list):
        home, draw, away = odds
        if 1.0 <= home <= 1.05 and 8 <= draw <= 20 and 15 <= away <= 30:
            return odds, i
    return odds_list[0] if odds_list else (0, 0, 0), 0

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

def analyze_match_v5(data):
    """V5优化版算法 - 改进平局判断和强队输球识别"""
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
    
    # ===== V5算法规则 =====
    
    # 规则0: 平局概率很高时直接选平局 (新增)
    if avg_draw_prob > 35 and avg_home_prob < 45 and avg_away_prob < 45:
        first_choice = "平局"
        first_prob = f"{avg_draw_prob:.0f}%"
        reason = "平局概率突出"
    
    # 规则1: 主胜<1.5 -> 主胜 (强队主场)
    elif avg_home < 1.5:
        first_choice = f"{data['home_team']}主胜"
        first_prob = f"{avg_home_prob:.0f}%"
        reason = "强队主场"
    
    # 规则2: 客胜<1.5 -> 客胜 (强队客场)
    elif avg_away < 1.5:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "强队客场"
    
    # 规则3: 平局概率>30% + 主客胜差距<15% + 任何一方近况多平局 -> 平局 (新增)
    elif avg_draw_prob > 30 and abs(avg_home_prob - avg_away_prob) < 15 and (home_draws >= 2 or away_draws >= 2):
        first_choice = "平局"
        first_prob = f"{avg_draw_prob:.0f}%"
        reason = "平局防范+近况多平"
    
    # 规则4: 平局升赔公司多(>85%) + 主胜被看衰(升>10%) -> 平局 (新增)
    elif draw_up_pct > 85 and np.mean(home_pct) > 10:
        first_choice = "平局"
        first_prob = f"{avg_draw_prob:.0f}%"
        reason = "平局受关注"
    
    # 规则5: 强队客场(1.5<客胜<2.0) + 客队近况好(W>=L) -> 客胜
    elif avg_away < 2.0 and away_wins >= away_losses:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "强队客场+近况好"
    
    # 规则6: 主胜被明显看衰 (升>15%) + 上升公司>80% -> 客胜
    elif np.mean(home_pct) > 15 and home_up_pct > 80:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "主胜被大幅看衰"
    
    # 规则7: 客胜被明显看衰 (升>15%) + 上升公司>70% -> 主胜
    elif np.mean(away_pct) > 15 and away_up_pct > 70:
        first_choice = f"{data['home_team']}主胜"
        first_prob = f"{avg_home_prob:.0f}%"
        reason = "客胜被大幅看衰"
    
    # 规则8: 澳门推荐主队 -> 主胜
    elif "主" in macao_tip and "客" not in macao_tip:
        first_choice = f"{data['home_team']}主胜"
        first_prob = f"{avg_home_prob:.0f}%"
        reason = "澳门推荐主胜"
    
    # 规则9: 澳门推荐客队 -> 客胜
    elif "客" in macao_tip:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "澳门推荐客胜"
    
    # 规则10: 主胜不稳+客胜受保护 -> 客胜
    elif home_up_pct > 60 and away_down_pct > 40:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "主胜不稳+客胜受保护"
    
    # 规则11: 强强对话(主胜2.5-4.0 且 客胜1.8-3.0) + 主队近况不佳(输多) -> 客胜
    elif 2.5 < avg_home < 4.0 and 1.8 < avg_away < 3.0 and home_losses > home_wins:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "强强对话主队近况差"
    
    # 规则12: 强强对话 + 平局概率接近主客胜 -> 平局
    elif 2.5 < avg_home < 5.0 and 2.0 < avg_away < 5.0 and abs(avg_draw_prob - avg_home_prob) < 12 and abs(avg_draw_prob - avg_away_prob) < 12:
        first_choice = "平局"
        first_prob = f"{avg_draw_prob:.0f}%"
        reason = "强强对话均势"
    
    # 规则13: 主队近况好(W>=3) + 主胜赔率<2.5 -> 主胜
    elif home_wins >= 3 and avg_home < 2.5:
        first_choice = f"{data['home_team']}主胜"
        first_prob = f"{avg_home_prob:.0f}%"
        reason = "主队近况好"
    
    # 规则14: 客队近况好(W>=3) + 客胜赔率<2.5 -> 客胜
    elif away_wins >= 3 and avg_away < 2.5:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "客队近况好"
    
    # 规则15: 主胜被升高 + 平局被降低 -> 防平局 (新增)
    elif home_up_pct > 50 and draw_down_pct > 50:
        # 判断哪一方更可能
        if avg_draw_prob > 28:
            first_choice = "平局"
            first_prob = f"{avg_draw_prob:.0f}%"
            reason = "平局防范"
        elif avg_home_prob > avg_away_prob:
            first_choice = f"{data['home_team']}主胜"
            first_prob = f"{avg_home_prob:.0f}%"
            reason = "概率较高"
        else:
            first_choice = f"{data['away_team']}客胜"
            first_prob = f"{avg_away_prob:.0f}%"
            reason = "概率较高"
    
    # 默认: 选概率最高的
    else:
        if avg_home_prob >= avg_away_prob and avg_home_prob >= avg_draw_prob:
            first_choice = f"{data['home_team']}主胜"
            first_prob = f"{avg_home_prob:.0f}%"
        elif avg_away_prob >= avg_home_prob and avg_away_prob >= avg_draw_prob:
            first_choice = f"{data['away_team']}客胜"
            first_prob = f"{avg_away_prob:.0f}%"
        else:
            first_choice = "平局"
            first_prob = f"{avg_draw_prob:.0f}%"
        reason = "概率最高"
    
    return {
        'home_team': data['home_team'],
        'away_team': data['away_team'],
        'league': data['league'],
        'macao_tip': data['macao_tip'],
        'first_choice': first_choice,
        'first_prob': first_prob,
        'reason': reason,
    }

def analyze_folder(folder_path):
    files = [f for f in os.listdir(folder_path) if f.endswith('_源数据.md')]
    
    results = []
    for f in sorted(files):
        filepath = os.path.join(folder_path, f)
        try:
            data = extract_odds_from_file(filepath)
            result = analyze_match_v5(data)
            if result:
                result['filename'] = f.replace('_源数据.md', '')
                results.append(result)
                print(f"{result['filename']}: {result['first_choice']} ({result['reason']})")
        except Exception as e:
            print(f"Error: {f} - {e}")
    
    return results

# 分析三个文件夹
print("=" * 60)
print("V5算法分析 3.13 文件夹 (周五)")
print("=" * 60)
results_313 = analyze_folder(r"d:\work\workbuddy\足球预测\分析模板\3.13")

print("\n" + "=" * 60)
print("V5算法分析 3.14 文件夹 (周六)")
print("=" * 60)
results_314 = analyze_folder(r"d:\work\workbuddy\足球预测\分析模板\3.14")

print("\n" + "=" * 60)
print("V5算法分析 3.15 文件夹 (周日)")
print("=" * 60)
results_315 = analyze_folder(r"d:\work\workbuddy\足球预测\分析模板\3.15")

print(f"\n总计: 3.13={len(results_313)}, 3.14={len(results_314)}, 3.15={len(results_315)}")
