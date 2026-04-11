# V7算法预测 3.16 比赛
import os
import re
import numpy as np

def extract_odds_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    home_team = re.search(r'\| 主队 \|\s*(.+)', content)
    away_team = re.search(r'\| 客队 \|\s*(.+)', content)
    league = re.search(r'\| 赛事 \|\s*(.+)', content)
    home_form = re.search(r'\| 主队近况走势 \|\s*(.+)', content)
    away_form = re.search(r'\| 客队近况走势 \|\s*(.+)', content)
    home_handicap = re.search(r'\| 主队盘路走势 \|\s*(.+)', content)
    away_handicap = re.search(r'\| 客队盘路走势 \|\s*(.+)', content)
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
        'home_handicap': home_handicap.group(1).strip() if home_handicap else '',
        'away_handicap': away_handicap.group(1).strip() if away_handicap else '',
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

def analyze_match_v7(data):
    """V7优化版算法 - 智能平局识别"""
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
    
    # ===== V7智能平局识别算法 =====
    
    # 规则1: 主胜<1.5 -> 主胜 (强队主场)
    if avg_home < 1.5:
        first_choice = f"{data['home_team']}主胜"
        first_prob = f"{avg_home_prob:.0f}%"
        reason = "强队主场"
    
    # 规则2: 客胜<1.5 -> 客胜 (强队客场)
    elif avg_away < 1.5:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "强队客场"
    
    # 规则3: 澳门推荐主队 -> 主胜
    elif "主" in macao_tip and "客" not in macao_tip:
        first_choice = f"{data['home_team']}主胜"
        first_prob = f"{avg_home_prob:.0f}%"
        reason = "澳门推荐主胜"
    
    # 规则4: 澳门推荐客队 -> 客胜
    elif "客" in macao_tip:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "澳门推荐客胜"
    
    # ===== 平局识别规则 =====
    
    # 平局规则1: 两队近况都多平局(D>=3) + 赔率接近
    elif home_draws >= 3 and away_draws >= 3 and abs(avg_home_prob - avg_away_prob) < 15:
        first_choice = "平局"
        first_prob = f"{avg_draw_prob:.0f}%"
        reason = "两队近况多平局"
    
    # 平局规则2: 强强对话(主胜2.5-4.5, 客胜2.0-4.0) + 近况相似
    elif 2.5 < avg_home < 4.5 and 2.0 < avg_away < 4.0 and abs(home_wins - away_wins) <= 1:
        first_choice = "平局"
        first_prob = f"{avg_draw_prob:.0f}%"
        reason = "强强对话均势"
    
    # 平局规则3: 平局概率突出(>28%) + 主客胜差距<10%
    elif avg_draw_prob > 28 and abs(avg_home_prob - avg_away_prob) < 10:
        first_choice = "平局"
        first_prob = f"{avg_draw_prob:.0f}%"
        reason = "平局概率突出"
    
    # 平局规则4: 主胜升高 + 客胜升高 + 平局降赔
    elif home_up_pct > 40 and away_up_pct > 40 and draw_down_pct > 40:
        first_choice = "平局"
        first_prob = f"{avg_draw_prob:.0f}%"
        reason = "胜赔上升平局降"
    
    # ===== 分胜负规则 =====
    
    # 规则5: 主队近况很好(W>=4) + 主胜<2.5 -> 主胜
    elif home_wins >= 4 and avg_home < 2.5:
        first_choice = f"{data['home_team']}主胜"
        first_prob = f"{avg_home_prob:.0f}%"
        reason = "主队近况很好"
    
    # 规则6: 客队近况很好(W>=4) + 客胜<2.5 -> 客胜
    elif away_wins >= 4 and avg_away < 2.5:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "客队近况很好"
    
    # 规则7: 主胜概率优势明显(>10%) -> 主胜
    elif avg_home_prob > avg_away_prob + 10 and avg_home_prob > avg_draw_prob + 8:
        first_choice = f"{data['home_team']}主胜"
        first_prob = f"{avg_home_prob:.0f}%"
        reason = "主胜概率优势明显"
    
    # 规则8: 客胜概率优势明显(>10%) -> 客胜
    elif avg_away_prob > avg_home_prob + 10 and avg_away_prob > avg_draw_prob + 8:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "客胜概率优势明显"
    
    # 规则9: 主胜概率最高 -> 主胜
    elif avg_home_prob >= avg_away_prob and avg_home_prob >= avg_draw_prob:
        first_choice = f"{data['home_team']}主胜"
        first_prob = f"{avg_home_prob:.0f}%"
        reason = "主胜概率最高"
    
    # 规则10: 客胜概率最高 -> 客胜
    elif avg_away_prob >= avg_home_prob and avg_away_prob >= avg_draw_prob:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "客胜概率最高"
    
    # 默认: 平局
    else:
        first_choice = "平局"
        first_prob = f"{avg_draw_prob:.0f}%"
        reason = "默认平局"
    
    return {
        'home_team': data['home_team'],
        'away_team': data['away_team'],
        'league': data['league'],
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
            result = analyze_match_v7(data)
            if result:
                result['filename'] = f.replace('_源数据.md', '')
                results.append(result)
        except Exception as e:
            print(f"Error: {f} - {e}")
    
    return results

# 分析3.16文件夹
print("=" * 70)
print("V7算法预测 3.16 比赛")
print("=" * 70)
results_316 = analyze_folder(r"d:\work\workbuddy\足球预测\分析模板\3.16")

print("\n" + "=" * 70)
print("预测结果汇总")
print("=" * 70)
for r in results_316:
    print(f"- {r['filename']} {r['home_team']} vs {r['away_team']}: **{r['first_choice']}** ({r['reason']}, {r['first_prob']})")

print(f"\n总计预测: {len(results_316)} 场比赛")

# 统计预测分布
pred_counts = {'主胜': 0, '客胜': 0, '平局': 0}
for r in results_316:
    if '主胜' in r['first_choice']:
        pred_counts['主胜'] += 1
    elif '客胜' in r['first_choice']:
        pred_counts['客胜'] += 1
    else:
        pred_counts['平局'] += 1

print(f"预测分布: 主胜={pred_counts['主胜']}, 平局={pred_counts['平局']}, 客胜={pred_counts['客胜']}")
