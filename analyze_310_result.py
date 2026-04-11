import re
import ast
from pathlib import Path

DATA_DIR = Path('d:/work/workbuddy/足球预测/分析模板/3.10')

def parse_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    info = {}
    filename = filepath.stem
    match = re.match(r'(周二|周一|周三|周四|周五|周六|周日)(\d+)_([^vs]+)vs(.+?)_源数据', filename)
    if match:
        info['match_id'] = f'{match.group(1)}{match.group(2)}'
        info['home_team'] = match.group(3).strip()
        info['away_team'] = match.group(4).strip()
    
    initial_odds, realtime_odds = [], []
    for pattern in [r'initial_odds\s*=\s*\[(.*?)\]', r'realtime_odds\s*=\s*\[(.*?)\]']:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                odds_str = '[' + re.sub(r'#.*', '', match.group(1)) + ']'
                odds_list = ast.literal_eval(odds_str)
                if 'initial' in pattern:
                    initial_odds = odds_list
                else:
                    realtime_odds = odds_list
            except: pass
    
    info['initial_odds'] = initial_odds
    info['realtime_odds'] = realtime_odds
    return info

def calc_v7v8(info):
    initial, realtime = info.get('initial_odds', []), info.get('realtime_odds', [])
    if not initial or not realtime: return None
    
    real_home = sum(x[0] for x in realtime) / len(realtime)
    real_draw = sum(x[1] for x in realtime) / len(realtime)
    real_away = sum(x[2] for x in realtime) / len(realtime)
    
    total = 1/real_home + 1/real_draw + 1/real_away
    real_prob_home = (1/real_home) / total * 100
    real_prob_draw = (1/real_draw) / total * 100
    real_prob_away = (1/real_away) / total * 100
    
    confidence = max(real_prob_home, real_prob_draw, real_prob_away)
    diff = real_prob_home - real_prob_away
    
    initial_home_8 = sum(1 for o in initial if str(o[0]).endswith('8'))
    initial_draw_8 = sum(1 for o in initial if str(o[1]).endswith('8'))
    initial_away_8 = sum(1 for o in initial if str(o[2]).endswith('8'))
    realtime_home_8 = sum(1 for o in realtime if str(o[0]).endswith('8'))
    realtime_draw_8 = sum(1 for o in realtime if str(o[1]).endswith('8'))
    realtime_away_8 = sum(1 for o in realtime if str(o[2]).endswith('8'))
    
    home_8 = realtime_home_8 - initial_home_8
    draw_8 = realtime_draw_8 - initial_draw_8
    away_8 = realtime_away_8 - initial_away_8
    
    return {
        'confidence': confidence, 'diff': diff, 'abs_diff': abs(diff),
        'home_8': home_8, 'draw_8': draw_8, 'away_8': away_8,
    }

# 实际结果和比分
actual_results = {
    '周二001': '客胜', '周二002': '主胜', '周二003': '主胜', '周二004': '平局',
    '周二005': '主胜', '周二006': '客胜', '周二007': '客胜', '周二008': '主胜', '周二009': '平局'
}

actual_scores = {
    '周二001': '1-3', '周二002': '4-0', '周二003': '1-0', '周二004': '0-0',
    '周二005': '1-0', '周二006': '1-2', '周二007': '1-6', '周二008': '5-2', '周二009': '1-1'
}

# 预测结果
predictions = {
    '周二001': '客胜', '周二002': '主胜', '周二003': '主胜', '周二004': '主胜',
    '周二005': '客胜', '周二006': '平局', '周二007': '客胜', '周二008': '主胜', '周二009': '平局'
}

files = sorted(DATA_DIR.glob('*_源数据.md'))

print("="*120)
print("## 3.10 预测 vs 实际 结果")
print("="*120)

all_games = []

for f in files:
    info = parse_file(f)
    v7v8 = calc_v7v8(info)
    if not v7v8:
        continue
    
    mid = info.get('match_id', '')
    h, a = info.get('home_team', ''), info.get('away_team', '')
    
    conf, diff = v7v8['confidence'], v7v8['diff']
    abs_diff = v7v8['abs_diff']
    h8, d8, a8 = v7v8['home_8'], v7v8['draw_8'], v7v8['away_8']
    
    is_moderate = abs(h8) <= 2 and abs(d8) <= 2 and abs(a8) <= 2
    
    # 偏离度计算
    ratio = abs_diff / conf if conf > 0 else 0
    expected_ratio_min = 0.15 if conf < 55 else 0.2
    expected_ratio_max = 0.35 if conf < 55 else (0.5 if conf < 65 else (0.6 if conf < 75 else 0.7))
    
    if ratio < expected_ratio_min:
        deviation_type = "过低"
        deviation = expected_ratio_min - ratio
    elif ratio > expected_ratio_max:
        deviation_type = "过高"
        deviation = ratio - expected_ratio_max
    else:
        deviation_type = "匹配"
        deviation = 0
    
    pred = predictions.get(mid, '')
    act = actual_results.get(mid, '')
    score = actual_scores.get(mid, '')
    result = 'O' if pred == act else 'X'
    
    # 净胜球
    try:
        goals = score.split('-')
        goal_diff = abs(int(goals[0]) - int(goals[1]))
    except:
        goal_diff = 0
    
    print(f"{mid} {h} vs {a}")
    print(f"   置信度:{conf:.1f}% 胜率差:{diff:+.1f}% 8:[{h8},{d8},{a8}] 8中庸:{is_moderate}")
    print(f"   比例:{ratio:.2f} 偏离:{deviation_type}({deviation:.2f}) 预测:{pred} 实际:{act} 比分:{score} 净胜球:{goal_diff} [{result}]")
    print()
    
    all_games.append({
        'mid': mid, 'home': h, 'away': a, 'conf': conf, 'diff': diff,
        'h8': h8, 'd8': d8, 'a8': a8, 'is_moderate': is_moderate,
        'ratio': ratio, 'deviation_type': deviation_type, 'deviation': deviation,
        'pred': pred, 'actual': act, 'score': score, 'goal_diff': goal_diff, 'result': result
    })

# 统计准确率
correct = sum(1 for g in all_games if g['result'] == 'O')
print("="*80)
print(f"## 总体准确率: {correct}/{len(all_games)} = {correct/len(all_games)*100:.1f}%")
print("="*80)

# 按偏离度分组分析
print()
print("="*80)
print("## 偏离度与比分关系分析")
print("="*80)

moderate_games = [g for g in all_games if g['is_moderate']]
non_moderate = [g for g in all_games if not g['is_moderate']]

print(f"\n8中庸比赛: {len(moderate_games)}场")
print(f"非8中庸比赛: {len(non_moderate)}场")

# 8中庸比赛详情
print("\n### 8中庸比赛:")
for g in moderate_games:
    status = "O" if g['result'] == 'O' else "X"
    print(f"  {g['mid']} {g['home']} vs {g['away']}: 比例{g['ratio']:.2f} 偏离:{g['deviation_type']} 比分:{g['score']} 净胜球:{g['goal_diff']} [{status}]")

# 统计比分差距
if moderate_games:
    avg_moderate = sum(g['goal_diff'] for g in moderate_games) / len(moderate_games)
    print(f"  平均净胜球: {avg_moderate:.1f}")

if non_moderate:
    avg_non_moderate = sum(g['goal_diff'] for g in non_moderate) / len(non_moderate)
    print(f"非8中庸平均净胜球: {avg_non_moderate:.1f}")

# 按偏离类型分组
match = [g for g in all_games if g['deviation_type'] == '匹配']
low_dev = [g for g in all_games if g['deviation_type'] == '过低']
high_dev = [g for g in all_games if g['deviation_type'] == '过高']

print("\n### 按偏离类型分组:")
print(f"  匹配: {len(match)}场, 正确:{sum(1 for g in match if g['result']=='O')}")
print(f"  偏离过低: {len(low_dev)}场, 正确:{sum(1 for g in low_dev if g['result']=='O')}")
print(f"  偏离过高: {len(high_dev)}场, 正确:{sum(1 for g in high_dev if g['result']=='O')}")

if high_dev:
    print(f"  偏离过高平均净胜球: {sum(g['goal_diff'] for g in high_dev)/len(high_dev):.1f}")
