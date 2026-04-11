# 分析各规则的准确率
import os
import re
import ast
from pathlib import Path

def parse_source_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    match_info = {}
    
    filename = Path(filepath).stem
    match = re.match(r'周六(\d+)_(.+?)vs(.+?)_源数据', filename)
    if match:
        match_info['match_id'] = f"周六{match.group(1)}"
        match_info['home_team'] = match.group(2)
        match_info['away_team'] = match.group(3)
    
    match = re.search(r'主队近况.*?(\d+)胜(\d+)平(\d+)负', content)
    if match:
        match_info['home_w'] = int(match.group(1))
        match_info['home_l'] = int(match.group(3))
    
    match = re.search(r'客队近况.*?(\d+)胜(\d+)平(\d+)负', content)
    if match:
        match_info['away_w'] = int(match.group(1))
        match_info['away_l'] = int(match.group(3))
    
    initial_odds = []
    realtime_odds = []
    
    match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if match:
        try:
            tuple_str = '[' + match.group(1) + ']'
            tuple_str = re.sub(r'#.*', '', tuple_str)
            initial_odds = ast.literal_eval(tuple_str)
        except:
            pass
    
    match = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if match:
        try:
            tuple_str = '[' + match.group(1) + ']'
            tuple_str = re.sub(r'#.*', '', tuple_str)
            realtime_odds = ast.literal_eval(tuple_str)
        except:
            pass
    
    match_info['initial_odds'] = initial_odds
    match_info['realtime_odds'] = realtime_odds
    
    return match_info

# 实际结果
actual_14 = {
    "周六001": "平局", "周六002": "客胜", "周六003": "平局", "周六004": "客胜",
    "周六005": "主胜", "周六006": "主胜", "周六007": "平局", "周六008": "主胜",
    "周六009": "主胜", "周六010": "客胜", "周六011": "主胜", "周六012": "平局",
    "周六013": "平局", "周六014": "主胜", "周六015": "主胜", "周六016": "平局",
    "周六017": "平局", "周六018": "主胜", "周六019": "主胜", "周六020": "主胜",
    "周六021": "主胜", "周六022": "主胜", "周六023": "客胜", "周六024": "平局",
    "周六025": "主胜", "周六026": "客胜", "周六027": "客胜", "周六028": "客胜",
    "周六029": "平局", "周六030": "主胜", "周六031": "客胜", "周六032": "平局",
}

# 分析各规则
folder = "分析模板/3.14"
files = sorted(Path(folder).glob("*.md"))

rule_stats = {}
matches_data = []

for f in files:
    info = parse_source_file(f)
    if not info.get('home_team') or not info.get('initial_odds'):
        continue
    
    initial = info.get('initial_odds', [])
    realtime = info.get('realtime_odds', [])
    
    if not initial or not realtime:
        continue
    
    initial_home = [x[0] for x in initial]
    initial_draw = [x[1] for x in initial]
    initial_away = [x[2] for x in initial]
    
    realtime_home = [x[0] for x in realtime]
    realtime_draw = [x[1] for x in realtime]
    realtime_away = [x[2] for x in realtime]
    
    avg_realtime_home = sum(realtime_home) / len(realtime_home)
    avg_realtime_draw = sum(realtime_draw) / len(realtime_draw)
    avg_realtime_away = sum(realtime_away) / len(realtime_away)
    
    prob_home = 1 / avg_realtime_home / (1/avg_realtime_home + 1/avg_realtime_draw + 1/avg_realtime_away)
    prob_draw = 1 / avg_realtime_draw / (1/avg_realtime_home + 1/avg_realtime_draw + 1/avg_realtime_away)
    prob_away = 1 / avg_realtime_away / (1/avg_realtime_home + 1/avg_realtime_draw + 1/avg_realtime_away)
    
    home_pct_change = (avg_realtime_home - sum(initial_home)/len(initial_home)) / (sum(initial_home)/len(initial_home)) * 100
    away_pct_change = (avg_realtime_away - sum(initial_away)/len(initial_away)) / (sum(initial_away)/len(initial_away)) * 100
    draw_pct_change = (avg_realtime_draw - sum(initial_draw)/len(initial_draw)) / (sum(initial_draw)/len(initial_draw)) * 100
    
    home_up = sum(1 for i in range(len(initial)) if realtime[i][0] > initial[i][0])
    draw_up = sum(1 for i in range(len(initial)) if realtime[i][1] > initial[i][1])
    away_up = sum(1 for i in range(len(initial)) if realtime[i][2] > initial[i][2])
    
    home_w = info.get('home_w', 0)
    home_l = info.get('home_l', 0)
    away_w = info.get('away_w', 0)
    away_l = info.get('away_l', 0)
    
    id_ = info.get('match_id')
    actual = actual_14.get(id_, "")
    
    # 计算各规则的预测
    rules_pred = {}
    
    # 规则1: 强胆主胜
    rules_pred['强胆主'] = "主胜" if avg_realtime_home < 1.5 else None
    # 规则2: 强胆客胜
    rules_pred['强胆客'] = "客胜" if avg_realtime_away < 1.5 else None
    # 规则3: 强队主场
    rules_pred['强主场'] = "主胜" if 1.5 < avg_realtime_home < 2.0 and home_w >= home_l else None
    # 规则4: 强队客场
    rules_pred['强客场'] = "客胜" if 1.5 < avg_realtime_away < 2.0 and away_w >= away_l else None
    # 规则5: 主胜大升
    rules_pred['主升15'] = "客胜" if home_pct_change > 15 and home_up/len(initial) > 0.8 else None
    # 规则6: 客胜大升
    rules_pred['客升15'] = "主胜" if away_pct_change > 15 and away_up/len(initial) > 0.7 else None
    # 规则7: 主队近况好
    rules_pred['主W3'] = "主胜" if home_w >= 3 and avg_realtime_home < 2.5 else None
    # 规则8: 客队近况好
    rules_pred['客W3'] = "客胜" if away_w >= 3 and avg_realtime_away < 2.5 else None
    # 规则9: 平局防范
    rules_pred['平局防'] = "平局" if draw_up/len(initial) < 0.5 and draw_pct_change < -2 and prob_draw > 0.28 else None
    # 规则10: 主胜概率最高
    rules_pred['主概率'] = "主胜" if prob_home > prob_away and prob_home > prob_draw else None
    # 规则11: 客胜概率最高
    rules_pred['客概率'] = "客胜" if prob_away > prob_home and prob_away > prob_draw else None
    # 规则12: 平局概率最高
    rules_pred['平概率'] = "平局" if prob_draw > prob_home and prob_draw > prob_away else None
    # 规则13: 主胜不稳
    rules_pred['主不稳'] = "客胜" if home_pct_change > 5 and away_pct_change < 0 else None
    
    matches_data.append({
        'id': id_,
        'actual': actual,
        'rules': rules_pred
    })

# 统计各规则准确率
print("各规则准确率分析 (3.14):")
print("=" * 60)

for rule_name in ['强胆主', '强胆客', '强主场', '强客场', '主升15', '客升15', '主W3', '客W3', '平局防', '主概率', '客概率', '平概率', '主不稳']:
    correct = 0
    total = 0
    for m in matches_data:
        pred = m['rules'].get(rule_name)
        if pred:
            total += 1
            if pred == m['actual']:
                correct += 1
    
    if total > 0:
        acc = correct / total * 100
        print(f"{rule_name}: {acc:.1f}% ({correct}/{total})")

# 尝试组合规则
print("\n" + "=" * 60)
print("组合规则测试:")

# 策略1: 优先强胆
correct1 = 0
for m in matches_data:
    pred = None
    if m['rules']['强胆主']:
        pred = m['rules']['强胆主']
    elif m['rules']['强胆客']:
        pred = m['rules']['强胆客']
    elif m['rules']['强主场']:
        pred = m['rules']['强主场']
    elif m['rules']['强客场']:
        pred = m['rules']['强客场']
    elif m['rules']['主升15']:
        pred = m['rules']['主升15']
    elif m['rules']['客升15']:
        pred = m['rules']['客升15']
    elif m['rules']['平局防']:
        pred = m['rules']['平局防']
    elif m['rules']['主W3']:
        pred = m['rules']['主W3']
    elif m['rules']['客W3']:
        pred = m['rules']['客W3']
    elif m['rules']['主概率']:
        pred = m['rules']['主概率']
    elif m['rules']['客概率']:
        pred = m['rules']['客概率']
    else:
        pred = m['rules']['平概率']
    
    if pred == m['actual']:
        correct1 += 1

print(f"策略1 (V4逻辑): {correct1/32*100:.1f}% ({correct1}/32)")

# 策略2: 增加平局权重
correct2 = 0
for m in matches_data:
    pred = None
    # 强胆优先
    if m['rules']['强胆主']:
        pred = m['rules']['强胆主']
    elif m['rules']['强胆客']:
        pred = m['rules']['强胆客']
    # 平局防范
    elif m['rules']['平局防']:
        pred = m['rules']['平局防']
    # 强队
    elif m['rules']['强主场']:
        pred = m['rules']['强主场']
    elif m['rules']['强客场']:
        pred = m['rules']['强客场']
    # 变化
    elif m['rules']['主升15']:
        pred = m['rules']['主升15']
    elif m['rules']['客升15']:
        pred = m['rules']['客升15']
    elif m['rules']['主W3']:
        pred = m['rules']['主W3']
    elif m['rules']['客W3']:
        pred = m['rules']['客W3']
    elif m['rules']['主不稳']:
        pred = m['rules']['主不稳']
    # 概率
    elif m['rules']['主概率']:
        pred = m['rules']['主概率']
    elif m['rules']['客概率']:
        pred = m['rules']['客概率']
    else:
        pred = m['rules']['平概率']
    
    if pred == m['actual']:
        correct2 += 1

print(f"策略2 (增加平局): {correct2/32*100:.1f}% ({correct2}/32)")

# 策略3: 概率优先
correct3 = 0
for m in matches_data:
    pred = None
    # 强胆
    if m['rules']['强胆主']:
        pred = m['rules']['强胆主']
    elif m['rules']['强胆客']:
        pred = m['rules']['强胆客']
    # 概率
    elif m['rules']['主概率']:
        pred = m['rules']['主概率']
    elif m['rules']['客概率']:
        pred = m['rules']['客概率']
    elif m['rules']['平概率']:
        pred = m['rules']['平概率']
    # 变化
    elif m['rules']['主升15']:
        pred = m['rules']['主升15']
    elif m['rules']['客升15']:
        pred = m['rules']['客升15']
    else:
        pred = m['rules']['平局防'] if m['rules']['平局防'] else None
    
    if pred == m['actual']:
        correct3 += 1

print(f"策略3 (概率优先): {correct3/32*100:.1f}% ({correct3}/32)")
