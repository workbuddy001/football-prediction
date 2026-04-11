# 生成V7+8分析完整报告
import os
import re
import json
import numpy as np

# ==================== 实际结果数据 ====================
actual_results = {
    "3.12_周四001": "平局", "3.12_周四002": "平局", "3.12_周四003": "主胜", "3.12_周四004": "客胜",
    "3.12_周四005": "主胜", "3.12_周四006": "平局", "3.12_周四007": "客胜", "3.12_周四008": "客胜",
    "3.12_周四009": "客胜", "3.12_周四010": "主胜", "3.12_周四011": "客胜", "3.12_周四012": "客胜",
    "3.13_周五001": "平局", "3.13_周五002": "主胜", "3.13_周五003": "平局", "3.13_周五004": "主胜",
    "3.13_周五005": "客胜", "3.13_周五006": "平局", "3.13_周五007": "平局", "3.13_周五008": "主胜",
    "3.13_周五009": "主胜", "3.13_周五010": "主胜", "3.13_周五011": "主胜", "3.13_周五012": "平局",
    "3.14_周六001": "平局", "3.14_周六002": "客胜", "3.14_周六003": "平局", "3.14_周六004": "客胜",
    "3.14_周六005": "主胜", "3.14_周六006": "主胜", "3.14_周六007": "平局", "3.14_周六008": "主胜",
    "3.14_周六009": "主胜", "3.14_周六010": "客胜", "3.14_周六011": "主胜", "3.14_周六012": "平局",
    "3.14_周六013": "平局", "3.14_周六014": "主胜", "3.14_周六015": "主胜", "3.14_周六016": "平局",
    "3.14_周六017": "平局", "3.14_周六018": "主胜", "3.14_周六019": "主胜", "3.14_周六020": "主胜",
    "3.14_周六021": "主胜", "3.14_周六022": "主胜", "3.14_周六023": "客胜", "3.14_周六024": "平局",
    "3.14_周六025": "主胜", "3.14_周六026": "客胜", "3.14_周六027": "客胜", "3.14_周六028": "客胜",
    "3.14_周六029": "平局", "3.14_周六030": "主胜", "3.14_周六031": "客胜", "3.14_周六032": "平局",
    "3.15_周日001": "主胜", "3.15_周日002": "主胜", "3.15_周日003": "客胜", "3.15_周日004": "平局",
    "3.15_周日005": "主胜", "3.15_周日006": "客胜", "3.15_周日007": "客胜", "3.15_周日008": "平局",
    "3.15_周日009": "主胜", "3.15_周日010": "主胜", "3.15_周日011": "主胜", "3.15_周日012": "平局",
    "3.15_周日013": "平局", "3.15_周日014": "主胜", "3.15_周日015": "主胜", "3.15_周日016": "客胜",
    "3.15_周日017": "客胜", "3.15_周日018": "主胜", "3.15_周日019": "主胜", "3.15_周日020": "平局",
    "3.15_周日021": "平局", "3.15_周日022": "客胜", "3.15_周日023": "主胜", "3.15_周日024": "平局",
    "3.15_周日025": "主胜", "3.15_周日026": "主胜", "3.15_周日027": "主胜", "3.15_周日028": "主胜",
    "3.15_周日029": "主胜",
    "3.16_周一001": "客胜", "3.16_周一002": "客胜", "3.16_周一003": "平局", "3.16_周一004": "平局",
    "3.16_周一005": "主胜", "3.16_周一006": "平局",
    "3.16_周二001": "主胜", "3.16_周二002": "主胜", "3.16_周二004": "平局", "3.16_周二006": "平局",
    "3.16_周二007": "客胜", "3.16_周二008": "客胜",
}

actual_scores = {
    "3.12_周四001": "1-1", "3.12_周四002": "1-1", "3.12_周四003": "2-1", "3.12_周四004": "1-2",
    "3.12_周四005": "2-1", "3.12_周四006": "1-1", "3.12_周四007": "0-1", "3.12_周四008": "1-2",
    "3.12_周四009": "0-1", "3.12_周四010": "2-0", "3.12_周四011": "0-1", "3.12_周四012": "2-0",
    "3.13_周五001": "0-0", "3.13_周五002": "1-0", "3.13_周五003": "1-1", "3.13_周五004": "2-1",
    "3.13_周五005": "1-2", "3.13_周五006": "1-1", "3.13_周五007": "1-1", "3.13_周五008": "2-1",
    "3.13_周五009": "3-1", "3.13_周五010": "2-1", "3.13_周五011": "2-0", "3.13_周五012": "1-1",
    "3.14_周六001": "1-1", "3.14_周六002": "0-1", "3.14_周六003": "0-0", "3.14_周六004": "1-2",
    "3.14_周六005": "3-0", "3.14_周六006": "1-0", "3.14_周六007": "1-1", "3.14_周六008": "2-1",
    "3.14_周六009": "3-1", "3.14_周六010": "1-2", "3.14_周六011": "2-0", "3.14_周六012": "1-1",
    "3.14_周六013": "1-1", "3.14_周六014": "2-1", "3.14_周六015": "2-1", "3.14_周六016": "1-1",
    "3.14_周六017": "1-1", "3.14_周六018": "3-1", "3.14_周六019": "3-0", "3.14_周六020": "3-1",
    "3.14_周六021": "2-0", "3.14_周六022": "2-1", "3.14_周六023": "0-1", "3.14_周六024": "1-1",
    "3.14_周六025": "2-1", "3.14_周六026": "1-2", "3.14_周六027": "0-3", "3.14_周六028": "1-2",
    "3.14_周六029": "1-1", "3.14_周六030": "2-1", "3.14_周六031": "1-2", "3.14_周六032": "0-0",
    "3.15_周日001": "2-0", "3.15_周日002": "3-1", "3.15_周日003": "1-2", "3.15_周日004": "1-1",
    "3.15_周日005": "2-1", "3.15_周日006": "0-1", "3.15_周日007": "0-1", "3.15_周日008": "1-1",
    "3.15_周日009": "3-1", "3.15_周日010": "2-0", "3.15_周日011": "3-1", "3.15_周日012": "1-1",
    "3.15_周日013": "0-0", "3.15_周日014": "2-1", "3.15_周日015": "0-1", "3.15_周日016": "1-2",
    "3.15_周日017": "0-2", "3.15_周日018": "3-0", "3.15_周日019": "3-0", "3.15_周日020": "1-1",
    "3.15_周日021": "2-2", "3.15_周日022": "0-1", "3.15_周日023": "3-1", "3.15_周日024": "1-1",
    "3.15_周日025": "3-2", "3.15_周日026": "2-1", "3.15_周日027": "2-1", "3.15_周日028": "2-0",
    "3.15_周日029": "2-1",
    "3.16_周一001": "0-2", "3.16_周一002": "0-2", "3.16_周一003": "1-1", "3.16_周一004": "0-0",
    "3.16_周一005": "2-1", "3.16_周一006": "1-1",
    "3.16_周二001": "3-1", "3.16_周二002": "2-1", "3.16_周二004": "1-1", "3.16_周二006": "1-1",
    "3.16_周二007": "1-2", "3.16_周二008": "1-2",
}

def count_8_in_decimal(value_str):
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
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    home_team = re.search(r'主队\s*\|\s*(.+)', content)
    away_team = re.search(r'客队\s*\|\s*(.+)', content)
    home_form = re.search(r'主队近况走势\s*\|\s*(.+)', content)
    away_form = re.search(r'客队近况走势\s*\|\s*(.+)', content)
    macao_tip = re.search(r'澳门推荐\s*\|\s*(.+)', content)
    
    init_match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    initial_odds = eval('[' + init_match.group(1) + ']') if init_match else []
    
    real_match = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    realtime_odds = eval('[' + real_match.group(1) + ']') if real_match else []
    
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

def count_draws(form):
    if not form:
        return 0
    return sum(1 for c in form.upper() if c == 'D')

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
    home_down_pct = sum(1 for x in home_pct if x < 0) / len(home_pct) * 100
    draw_up_pct = sum(1 for x in draw_pct if x > 0) / len(draw_pct) * 100
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
    home_draws = count_draws(data['home_form'])
    away_draws = count_draws(data['away_form'])
    
    macao_tip = data['macao_tip'].upper() if data['macao_tip'] else ""
    
    # V7规则
    if avg_home < 1.5:
        pred, prob, reason = "主胜", avg_home_prob, "强队主场"
    elif avg_away < 1.5:
        pred, prob, reason = "客胜", avg_away_prob, "强队客场"
    elif "主" in macao_tip and "客" not in macao_tip:
        pred, prob, reason = "主胜", avg_home_prob, "澳门推荐主胜"
    elif "客" in macao_tip:
        pred, prob, reason = "客胜", avg_away_prob, "澳门推荐客胜"
    elif home_draws >= 3 and away_draws >= 3 and abs(avg_home_prob - avg_away_prob) < 15:
        pred, prob, reason = "平局", avg_draw_prob, "两队近况多平局"
    elif 2.5 < avg_home < 4.5 and 2.0 < avg_away < 4.0 and abs(home_wins - away_wins) <= 1:
        pred, prob, reason = "平局", avg_draw_prob, "强强对话均势"
    elif avg_draw_prob > 28 and abs(avg_home_prob - avg_away_prob) < 10:
        pred, prob, reason = "平局", avg_draw_prob, "平局概率突出"
    elif home_up_pct > 40 and away_up_pct > 40 and draw_down_pct > 40:
        pred, prob, reason = "平局", avg_draw_prob, "胜赔上升平局降"
    elif home_wins >= 4 and avg_home < 2.5:
        pred, prob, reason = "主胜", avg_home_prob, "主队近况很好"
    elif away_wins >= 4 and avg_away < 2.5:
        pred, prob, reason = "客胜", avg_away_prob, "客队近况很好"
    elif avg_home_prob > avg_away_prob + 10 and avg_home_prob > avg_draw_prob + 8:
        pred, prob, reason = "主胜", avg_home_prob, "主胜概率优势明显"
    elif avg_away_prob > avg_home_prob + 10 and avg_away_prob > avg_draw_prob + 8:
        pred, prob, reason = "客胜", avg_away_prob, "客胜概率优势明显"
    elif avg_home_prob >= avg_away_prob and avg_home_prob >= avg_draw_prob:
        pred, prob, reason = "主胜", avg_home_prob, "主胜概率最高"
    elif avg_away_prob >= avg_home_prob and avg_away_prob >= avg_draw_prob:
        pred, prob, reason = "客胜", avg_away_prob, "客胜概率最高"
    else:
        pred, prob, reason = "平局", avg_draw_prob, "默认平局"
    
    init_home_prob = np.mean([1/o[0]*100 for o in data['initial_odds']])
    init_away_prob = np.mean([1/o[2]*100 for o in data['initial_odds']])
    diff = init_home_prob - init_away_prob
    
    return {
        'v7_pred': pred, 'v7_prob': prob, 'reason': reason, 'init_diff': diff,
        'init_home_prob': init_home_prob, 'init_draw_prob': np.mean([1/o[1]*100 for o in data['initial_odds']]),
        'init_away_prob': init_away_prob, 'changes': data['changes'],
    }

def analyze_with_8_weight(v7_result):
    changes = v7_result['changes']
    home_8, draw_8, away_8 = changes['home_8'], changes['draw_8'], changes['away_8']
    
    init_home = v7_result['init_home_prob']
    init_draw = v7_result['init_draw_prob']
    init_away = v7_result['init_away_prob']
    
    total = init_home + init_draw + init_away
    w_home = init_home / total * 100 + home_8 * 2
    w_draw = init_draw / total * 100 + draw_8 * 2
    w_away = init_away / total * 100 + away_8 * 2
    
    weights = {'主胜': w_home, '平局': w_draw, '客胜': w_away}
    final_pred = max(weights, key=weights.get)
    
    changes_list = [('主胜', home_8), ('平局', draw_8), ('客胜', away_8)]
    max_change = max(changes_list, key=lambda x: x[1])
    increase_info = f"{max_change[0]}+{max_change[1]}" if max_change[1] > 0 else "-"
    
    return final_pred, increase_info

# 处理比赛
dates = [('3.12', '周四', '03-12'), ('3.13', '周五', '03-13'), ('3.14', '周六', '03-14'),
         ('3.15', '周日', '03-15'), ('3.16', '周一', '03-16')]

all_results = []

for date, weekday, json_date in dates:
    folder = f"d:/work/workbuddy/足球预测/分析模板/{date}"
    if not os.path.exists(folder):
        continue
    
    files = [f for f in os.listdir(folder) if f.endswith('_源数据.md')]
    
    for f in sorted(files):
        filepath = os.path.join(folder, f)
        filename = f.replace('_源数据.md', '')
        
        num = ""; date_num = ""; teams = filename
        match = re.search(r'([周][\u4e00-\u9fa5]\d+)_(.+)', filename)
        if match:
            date_num = match.group(1)
            teams = match.group(2)
        else:
            match2 = re.search(r'([周]\d+)_(.+)', filename)
            if match2:
                date_num = match2.group(1)
                teams = match2.group(2)
        
        lookup_key = f"{date}_{date_num}" if date_num else f"{date}_{filename}"
        
        try:
            data = extract_odds_from_file(filepath)
            v7 = analyze_match_v7(data)
            if not v7:
                continue
            
            final_pred, increase_info = analyze_with_8_weight(v7)
            
            actual = actual_results.get(lookup_key, "-")
            score = actual_scores.get(lookup_key, "-")
            result = "对" if actual != "-" and final_pred == actual else ("错" if actual != "-" else "-")
            
            row = {
                'date': date, 'date_num': date_num or "-", 'teams': teams,
                'v7_pred': v7['v7_pred'], 'confidence': f"{v7['v7_prob']:.0f}%",
                'diff': f"{v7['init_diff']:+.0f}%",
                'home_8': v7['changes']['home_8'], 'draw_8': v7['changes']['draw_8'], 'away_8': v7['changes']['away_8'],
                'increase': increase_info, 'final_pred': final_pred,
                'actual': actual, 'score': score, 'result': result,
            }
            all_results.append(row)
        except Exception as e:
            print(f"Error: {filename} - {e}")

# 统计
has_increase = [r for r in all_results if r['increase'] != '-']
hit_8 = sum(1 for r in has_increase if r['result'] == '对')
total_8 = len(has_increase)

hit_all = sum(1 for r in all_results if r['result'] == '对')
total_all = len(all_results)

# 输出Markdown表格
md_lines = []
md_lines.append("# V7 + 8变化权重分析完整表格")
md_lines.append("")
md_lines.append("## 整体统计")
md_lines.append(f"- 总比赛数: {total_all}场")
md_lines.append(f"- 整体命中率: {hit_all/total_all*100:.1f}% ({hit_all}/{total_all})")
md_lines.append(f"- 有8变化: {total_8}场, 命中率: {hit_8/total_8*100:.1f}% ({hit_8}/{total_8})")
md_lines.append("")
md_lines.append("## 按日期统计")
md_lines.append("| 日期 | 总数 | 命中 | 命中率 | 有8变化 | 命中 | 命中率 |")
md_lines.append("|------|------|------|--------|---------|------|--------|")

for date in ['3.12', '3.13', '3.14', '3.15', '3.16']:
    date_results = [r for r in all_results if r['date'] == date]
    date_8 = [r for r in date_results if r['increase'] != '-']
    h = sum(1 for r in date_results if r['result'] == '对')
    h8 = sum(1 for r in date_8 if r['result'] == '对')
    md_lines.append(f"| {date} | {len(date_results)} | {h} | {h/len(date_results)*100:.0f}% | {len(date_8)} | {h8} | {h8/len(date_8)*100:.0f}% |" if date_8 else f"| {date} | {len(date_results)} | {h} | {h/len(date_results)*100:.0f}% | 0 | - | - |")

md_lines.append("")
md_lines.append("## 完整比赛表格")
md_lines.append("")
md_lines.append("| 日期 | 编号 | 对阵 | V7预测 | 置信度 | 胜率差 | 主胜8 | 平局8 | 客胜8 | 增加最多 | 最终预测 | 实际 | 比分 | 结果 |")
md_lines.append("|------|------|------|--------|--------|--------|-------|-------|-------|----------|----------|------|------|------|")

for r in all_results:
    md_lines.append(f"| {r['date']} | {r['date_num']} | {r['teams']} | {r['v7_pred']} | {r['confidence']} | {r['diff']} | {r['home_8']} | {r['draw_8']} | {r['away_8']} | {r['increase']} | {r['final_pred']} | {r['actual']} | {r['score']} | {r['result']} |")

# 保存
with open('v7_8_full_analysis.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(md_lines))

print("分析完成！结果已保存到 v7_8_full_analysis.md")
print(f"\n整体统计:")
print(f"  总比赛: {total_all}场")
print(f"  整体命中率: {hit_all/total_all*100:.1f}% ({hit_all}/{total_all})")
print(f"  有8变化: {total_8}场, 命中率: {hit_8/total_8*100:.1f}% ({hit_8}/{total_8})")
