import re
import ast
from pathlib import Path

DATA_DIR = Path('d:/work/workbuddy/足球预测/分析模板/3.14')

def parse_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    info = {}
    filename = filepath.stem
    match = re.match(r'(周六|周日|周一|周二|周三|周四|周五)(\d+)_([^vs]+)vs(.+?)_源数据', filename)
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

# 实际比分
actual_scores = {
    '周六001': '1-1', '周六002': '0-1', '周六003': '0-0', '周六004': '1-2',
    '周六005': '3-0', '周六006': '1-0', '周六007': '1-1', '周六008': '2-1',
    '周六009': '3-1', '周六010': '1-2', '周六011': '2-0', '周六012': '1-1',
    '周六013': '1-1', '周六014': '2-1', '周六015': '2-1', '周六016': '1-1',
    '周六017': '1-1', '周六018': '3-1', '周六019': '3-0', '周六020': '3-1',
    '周六021': '2-0', '周六022': '2-1', '周六023': '0-1', '周六024': '1-1',
    '周六025': '2-1', '周六026': '1-2', '周六027': '0-3', '周六028': '1-2',
    '周六029': '1-1', '周六030': '2-1', '周六031': '1-2', '周六032': '0-0',
}

# 实际结果
actual_results = {
    '周六001': '平局', '周六002': '客胜', '周六003': '平局', '周六004': '客胜',
    '周六005': '主胜', '周六006': '主胜', '周六007': '平局', '周六008': '主胜',
    '周六009': '主胜', '周六010': '客胜', '周六011': '主胜', '周六012': '平局',
    '周六013': '平局', '周六014': '主胜', '周六015': '主胜', '周六016': '平局',
    '周六017': '平局', '周六018': '主胜', '周六019': '主胜', '周六020': '主胜',
    '周六021': '主胜', '周六022': '主胜', '周六023': '客胜', '周六024': '平局',
    '周六025': '主胜', '周六026': '客胜', '周六027': '客胜', '周六028': '客胜',
    '周六029': '平局', '周六030': '主胜', '周六031': '客胜', '周六032': '平局',
}

predictions = {
    '周六001': '主胜', '周六002': '平局', '周六003': '客胜', '周六004': '平局',
    '周六005': '主胜', '周六006': '主胜', '周六007': '平局', '周六008': '主胜',
    '周六009': '平局', '周六010': '客胜', '周六011': '平局', '周六012': '主胜',
    '周六013': '主胜', '周六014': '主胜', '周六015': '主胜', '周六016': '客胜',
    '周六017': '客胜', '周六018': '主胜', '周六019': '客胜', '周六020': '主胜',
    '周六021': '主胜', '周六022': '主胜', '周六023': '主胜', '周六024': '平局',
    '周六025': '平局', '周六026': '主胜', '周六027': '客胜', '周六028': '客胜',
    '周六029': '客胜', '周六030': '主胜', '周六031': '客胜', '周六032': '平局',
}

files = sorted(DATA_DIR.glob('*_源数据.md'))

# 分析8中庸但非实盘的比赛
print("="*140)
print("## 8中庸(|8|≤2)但非实盘的比赛 - 比分详情")
print("="*140)

moderate_not_real = []

for f in files:
    info = parse_file(f)
    v7v8 = calc_v7v8(info)
    if not v7v8: continue
    
    mid = info.get('match_id', '')
    h, a = info.get('home_team', ''), info.get('away_team', '')
    
    conf, diff = v7v8['confidence'], v7v8['diff']
    abs_diff, h8 = v7v8['abs_diff'], v7v8['home_8']
    d8, a8 = v7v8['draw_8'], v7v8['away_8']
    
    is_moderate = abs(h8) <= 2 and abs(d8) <= 2 and abs(a8) <= 2
    
    is_real = False
    if is_moderate:
        if 55 <= conf < 65 and 10 <= abs_diff <= 20:
            is_real = True
        elif 65 <= conf < 75 and 30 <= abs_diff <= 40:
            is_real = True
        elif conf >= 75 and abs_diff >= 40:
            is_real = True
    
    if is_moderate and not is_real:
        ratio = abs_diff / conf if conf > 0 else 0
        expected_ratio_min = 0.15 if conf < 55 else 0.2
        expected_ratio_max = 0.35 if conf < 55 else (0.5 if conf < 65 else (0.6 if conf < 75 else 0.7))
        
        if ratio < expected_ratio_min:
            deviation = expected_ratio_min - ratio
            deviation_type = "过低"
        elif ratio > expected_ratio_max:
            deviation = ratio - expected_ratio_max
            deviation_type = "过高"
        else:
            deviation = 0
            deviation_type = "匹配"
        
        pred = predictions.get(mid, '')
        act = actual_results.get(mid, '')
        score = actual_scores.get(mid, '')
        result = 'O' if pred == act else 'X'
        
        moderate_not_real.append({
            'mid': mid, 'home': h, 'away': a, 'conf': conf, 'diff': diff,
            'ratio': ratio, 'deviation': deviation, 'deviation_type': deviation_type,
            'pred': pred, 'actual': act, 'score': score, 'result': result
        })

print(f"\n8中庸但非实盘比赛数: {len(moderate_not_real)}")
print()

# 按偏离类型分组
match = [g for g in moderate_not_real if g['deviation_type'] == '匹配']
low_dev = [g for g in moderate_not_real if g['deviation_type'] != '匹配' and g['deviation'] <= 0.15]
high_dev = [g for g in moderate_not_real if g['deviation_type'] != '匹配' and g['deviation'] > 0.15]

print("="*80)
print("## 1. 匹配期望比例的比赛 (准确率100%)")
print("="*80)
for g in match:
    status = "O" if g['result'] == 'O' else "X"
    print(f"{g['mid']} {g['home']} vs {g['away']}")
    print(f"   置信度:{g['conf']:.1f}% 胜率差:{g['diff']:+.1f}% 比例:{g['ratio']:.2f}")
    print(f"   预测:{g['pred']} 实际:{g['actual']} 比分:{g['score']} [{status}]")
    print()

print("="*80)
print("## 2. 低偏离(≤0.15)的比赛 (准确率0%)")
print("="*80)
for g in low_dev:
    status = "O" if g['result'] == 'O' else "X"
    print(f"{g['mid']} {g['home']} vs {g['away']}")
    print(f"   置信度:{g['conf']:.1f}% 胜率差:{g['diff']:+.1f}% 比例:{g['ratio']:.2f} 偏离:{g['deviation_type']}({g['deviation']:.2f})")
    print(f"   预测:{g['pred']} 实际:{g['actual']} 比分:{g['score']} [{status}]")
    print()

print("="*80)
print("## 3. 高偏离(>0.15)的比赛 (准确率40%)")
print("="*80)
for g in high_dev:
    status = "O" if g['result'] == 'O' else "X"
    print(f"{g['mid']} {g['home']} vs {g['away']}")
    print(f"   置信度:{g['conf']:.1f}% 胜率差:{g['diff']:+.1f}% 比例:{g['ratio']:.2f} 偏离:{g['deviation_type']}({g['deviation']:.2f})")
    print(f"   预测:{g['pred']} 实际:{g['actual']} 比分:{g['score']} [{status}]")
    print()

print("="*80)
print("## 统计汇总")
print("="*80)
print(f"匹配期望比例: {len(match)}场, 正确:{sum(1 for g in match if g['result']=='O')}, 准确率:{len(match) and sum(1 for g in match if g['result']=='O')/len(match)*100:.0f}%")
print(f"低偏离(≤0.15): {len(low_dev)}场, 正确:{sum(1 for g in low_dev if g['result']=='O')}, 准确率:{len(low_dev) and sum(1 for g in low_dev if g['result']=='O')/len(low_dev)*100:.0f}%")
print(f"高偏离(>0.15): {len(high_dev)}场, 正确:{sum(1 for g in high_dev if g['result']=='O')}, 准确率:{len(high_dev) and sum(1 for g in high_dev if g['result']=='O')/len(high_dev)*100:.0f}%")
