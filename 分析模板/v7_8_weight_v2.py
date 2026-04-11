# V7 + 8变化权重分析完整版 (修正版)
import os
import re
import json
import numpy as np

def count_8_in_decimal(value_str):
    """统计尾数为8的赔率数量"""
    if not value_str:
        return 0
    try:
        value = float(value_str)
        decimal_str = f"{value:.2f}"
        last_digit = decimal_str[-1]
        return 1 if last_digit == '8' else 0
    except:
        return 0

def extract_odds_from_file(filepath):
    """从源数据md文件提取赔率"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    home_team = re.search(r'主队\s*\|\s*(.+)', content)
    away_team = re.search(r'客队\s*\|\s*(.+)', content)
    league = re.search(r'赛事\s*\|\s*(.+)', content)
    home_form = re.search(r'主队近况走势\s*\|\s*(.+)', content)
    away_form = re.search(r'客队近况走势\s*\|\s*(.+)', content)
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
    
    # 计算8变化
    init_home_8 = init_draw_8 = init_away_8 = 0
    real_home_8 = real_draw_8 = real_away_8 = 0
    
    for odds in initial_odds:
        init_home_8 += count_8_in_decimal(str(odds[0]))
        init_draw_8 += count_8_in_decimal(str(odds[1]))
        init_away_8 += count_8_in_decimal(str(odds[2]))
    
    for odds in realtime_odds:
        real_home_8 += count_8_in_decimal(str(odds[0]))
        real_draw_8 += count_8_in_decimal(str(odds[1]))
        real_away_8 += count_8_in_decimal(str(odds[2]))
    
    changes = {
        'home_8': real_home_8 - init_home_8,
        'draw_8': real_draw_8 - init_draw_8,
        'away_8': real_away_8 - init_away_8,
    }
    
    return {
        'home_team': home_team.group(1).strip() if home_team else '',
        'away_team': away_team.group(1).strip() if away_team else '',
        'league': league.group(1).strip() if league else '',
        'home_form': home_form.group(1).strip() if home_form else '',
        'away_form': away_form.group(1).strip() if away_form else '',
        'macao_tip': macao_tip.group(1).strip() if macao_tip else '',
        'initial_odds': initial_odds,
        'realtime_odds': realtime_odds,
        'changes': changes,
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
    """V7算法 - 返回预测和概率"""
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
    home_down_pct = sum(1 for x in home_pct if x < 0) / len(home_pct) * 100
    draw_up_pct = sum(1 for x in draw_pct if x > 0) / len(draw_pct) * 100
    draw_down_pct = sum(1 for x in draw_pct if x < 0) / len(draw_pct) * 100
    away_up_pct = sum(1 for x in away_pct if x > 0) / len(away_pct) * 100
    away_down_pct = sum(1 for x in away_pct if x < 0) / len(away_pct) * 100
    
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
    
    # ===== V7规则 =====
    if avg_home < 1.5:
        pred = "主胜"
        prob = avg_home_prob
        reason = "强队主场"
    elif avg_away < 1.5:
        pred = "客胜"
        prob = avg_away_prob
        reason = "强队客场"
    elif "主" in macao_tip and "客" not in macao_tip:
        pred = "主胜"
        prob = avg_home_prob
        reason = "澳门推荐主胜"
    elif "客" in macao_tip:
        pred = "客胜"
        prob = avg_away_prob
        reason = "澳门推荐客胜"
    elif home_draws >= 3 and away_draws >= 3 and abs(avg_home_prob - avg_away_prob) < 15:
        pred = "平局"
        prob = avg_draw_prob
        reason = "两队近况多平局"
    elif 2.5 < avg_home < 4.5 and 2.0 < avg_away < 4.0 and abs(home_wins - away_wins) <= 1:
        pred = "平局"
        prob = avg_draw_prob
        reason = "强强对话均势"
    elif avg_draw_prob > 28 and abs(avg_home_prob - avg_away_prob) < 10:
        pred = "平局"
        prob = avg_draw_prob
        reason = "平局概率突出"
    elif home_up_pct > 40 and away_up_pct > 40 and draw_down_pct > 40:
        pred = "平局"
        prob = avg_draw_prob
        reason = "胜赔上升平局降"
    elif home_wins >= 4 and avg_home < 2.5:
        pred = "主胜"
        prob = avg_home_prob
        reason = "主队近况很好"
    elif away_wins >= 4 and avg_away < 2.5:
        pred = "客胜"
        prob = avg_away_prob
        reason = "客队近况很好"
    elif avg_home_prob > avg_away_prob + 10 and avg_home_prob > avg_draw_prob + 8:
        pred = "主胜"
        prob = avg_home_prob
        reason = "主胜概率优势明显"
    elif avg_away_prob > avg_home_prob + 10 and avg_away_prob > avg_draw_prob + 8:
        pred = "客胜"
        prob = avg_away_prob
        reason = "客胜概率优势明显"
    elif avg_home_prob >= avg_away_prob and avg_home_prob >= avg_draw_prob:
        pred = "主胜"
        prob = avg_home_prob
        reason = "主胜概率最高"
    elif avg_away_prob >= avg_home_prob and avg_away_prob >= avg_draw_prob:
        pred = "客胜"
        prob = avg_away_prob
        reason = "客胜概率最高"
    else:
        pred = "平局"
        prob = avg_draw_prob
        reason = "默认平局"
    
    # 计算胜率差 (初始赔率)
    init_home_prob = np.mean([1/o[0]*100 for o in data['initial_odds']])
    init_draw_prob = np.mean([1/o[1]*100 for o in data['initial_odds']])
    init_away_prob = np.mean([1/o[2]*100 for o in data['initial_odds']])
    
    diff = init_home_prob - init_away_prob
    
    return {
        'home_team': data['home_team'],
        'away_team': data['away_team'],
        'v7_pred': pred,
        'v7_prob': prob,
        'reason': reason,
        'init_diff': diff,
        'init_home_prob': init_home_prob,
        'init_draw_prob': init_draw_prob,
        'init_away_prob': init_away_prob,
        'changes': data['changes'],
    }

def get_actual_result(date_str, match_key):
    """从JSON获取实际结果"""
    json_file = f"d:/work/workbuddy/足球预测/分析模板/matches_full_2026-{date_str}.json"
    if not os.path.exists(json_file):
        return None, None
    
    with open(json_file, encoding='utf-8') as f:
        data = json.load(f)
    
    for match in data:
        if match.get('编号', '') == match_key:
            result = match.get('实际结果', '')
            score = match.get('比分', '')
            return result, score
    return None, None

def analyze_with_8_weight(v7_result):
    """用末尾8变化调整权重"""
    changes = v7_result['changes']
    home_8 = changes['home_8']
    draw_8 = changes['draw_8']
    away_8 = changes['away_8']
    
    # 初始权重基于胜率差
    init_home = v7_result['init_home_prob']
    init_draw = v7_result['init_draw_prob']
    init_away = v7_result['init_away_prob']
    
    total = init_home + init_draw + init_away
    w_home = init_home / total * 100
    w_draw = init_draw / total * 100
    w_away = init_away / total * 100
    
    # 用8变化调整
    w_home += home_8 * 2
    w_draw += draw_8 * 2
    w_away += away_8 * 2
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    final_pred = max(weights, key=weights.get)
    
    # 增加最多的选项
    changes_list = [('主胜', home_8), ('平局', draw_8), ('客胜', away_8)]
    max_change = max(changes_list, key=lambda x: x[1])
    if max_change[1] > 0:
        increase_info = f"{max_change[0]}+{max_change[1]}"
    else:
        increase_info = "-"
    
    return final_pred, increase_info

# 处理3.12-3.16
dates = [
    ('3.12', '周四', '03-12'),
    ('3.13', '周五', '03-13'),
    ('3.14', '周六', '03-14'),
    ('3.15', '周日', '03-15'),
    ('3.16', '周一', '03-16'),
]

all_results = []

for date, weekday, json_date in dates:
    folder = f"d:/work/workbuddy/足球预测/分析模板/{date}"
    if not os.path.exists(folder):
        print(f"文件夹不存在: {folder}")
        continue
    
    files = [f for f in os.listdir(folder) if f.endswith('_源数据.md')]
    print(f"\n{'='*60}")
    print(f"{date} ({weekday}) - {len(files)}场比赛")
    print('='*60)
    
    for f in sorted(files):
        filepath = os.path.join(folder, f)
        filename = f.replace('_源数据.md', '')
        
        # 提取编号
        match = re.search(r'([周\d]+)(\d+)_(.+)', filename)
        if match:
            date_num = match.group(1)
            num = match.group(2)
            teams = match.group(3)
            match_key = f"{date_num}{num}"
        else:
            match_key = filename
            teams = filename
        
        try:
            data = extract_odds_from_file(filepath)
            v7 = analyze_match_v7(data)
            if not v7:
                continue
            
            changes = v7['changes']
            
            # 最终预测
            final_pred, increase_info = analyze_with_8_weight(v7)
            
            # 实际结果
            actual, score = get_actual_result(json_date, match_key)
            
            # 结果判定
            if actual and final_pred:
                if final_pred == actual:
                    result = "✅"
                else:
                    result = "❌"
            else:
                result = "-"
            
            v7_pred = v7['v7_pred']
            v7_prob = v7['v7_prob']
            diff = v7['init_diff']
            
            home_8 = changes['home_8']
            draw_8 = changes['draw_8']
            away_8 = changes['away_8']
            
            row = {
                'date': date,
                'weekday': weekday,
                'num': num,
                'teams': teams,
                'v7_pred': v7_pred,
                'confidence': f"{v7_prob:.0f}%",
                'diff': f"{diff:+.0f}%",
                'home_8': home_8,
                'draw_8': draw_8,
                'away_8': away_8,
                'increase': increase_info,
                'final_pred': final_pred,
                'actual': actual if actual else "-",
                'score': score if score else "-",
                'result': result,
            }
            all_results.append(row)
            
            print(f"{date} {num} {teams[:10]}: V7={v7_pred}({v7_prob:.0f}%) 8变化[{home_8},{draw_8},{away_8}] → 最终={final_pred} | 实际={actual} {score} {result}")
            
        except Exception as e:
            print(f"Error: {filename} - {e}")

# 统计
print("\n" + "="*60)
print("统计结果")
print("="*60)

has_increase = [r for r in all_results if r['increase'] != '-']
hit = sum(1 for r in has_increase if r['result'] == '✅')
total = len(has_increase)

if total > 0:
    print(f"有8变化: {total}场, 命中: {hit}场, 命中率: {hit/total*100:.1f}%")
else:
    print("没有8变化的比赛")

# 按日期统计
print("\n按日期:")
for date in ['3.12', '3.13', '3.14', '3.15', '3.16']:
    date_results = [r for r in has_increase if r['date'] == date]
    if date_results:
        h = sum(1 for r in date_results if r['result'] == '✅')
        print(f"  {date}: {len(date_results)}场, 命中{h}场 ({h/len(date_results)*100:.1f}%)")

# 输出表格
print("\n" + "="*60)
print("完整表格")
print("="*60)
print("日期\t编号\t对阵\t\tV7预测\t置信度\t胜率差\t主胜8\t平局8\t客胜8\t增加最多\t最终预测\t实际\t比分\t结果")
for r in all_results:
    teams = r['teams'][:10].ljust(10)
    print(f"{r['date']}\t{r['num']}\t{teams}\t{r['v7_pred']}\t{r['confidence']}\t{r['diff']}\t{r['home_8']}\t{r['draw_8']}\t{r['away_8']}\t{r['increase']}\t{r['final_pred']}\t{r['actual']}\t{r['score']}\t{r['result']}")
