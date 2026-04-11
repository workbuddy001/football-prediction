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
        'prob_home': real_prob_home, 'prob_draw': real_prob_draw, 'prob_away': real_prob_away
    }

files = sorted(DATA_DIR.glob('*_源数据.md'))

print("="*120)
print("## 3.10 详细数据列表")
print("="*120)
print(f"{'编号':<8} {'对阵':<26} {'置信度':<8} {'胜率差':<8} {'8变化':<12} {'8中庸?':<10} {'类型':<20}")
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
    
    # 8中庸判断
    is_moderate = abs(h8) <= 2 and abs(d8) <= 2 and abs(a8) <= 2
    moderate_str = "是" if is_moderate else "否"
    
    # 判断类型
    judge_type = ""
    if is_moderate:
        if 55 <= conf < 65 and 10 <= abs_diff <= 20:
            judge_type = "实盘1"
        elif 65 <= conf < 75 and 30 <= abs_diff <= 40:
            judge_type = "实盘2"
        elif conf >= 75 and abs_diff >= 40:
            judge_type = "实盘3"
        else:
            # 计算偏离度
            ratio = abs_diff / conf if conf > 0 else 0
            expected_ratio_min = 0.15 if conf < 55 else 0.2
            expected_ratio_max = 0.35 if conf < 55 else (0.5 if conf < 65 else (0.6 if conf < 75 else 0.7))
            
            if ratio < expected_ratio_min:
                judge_type = f"8中庸-偏离过低({ratio:.2f})"
            elif ratio > expected_ratio_max:
                judge_type = f"8中庸-偏离过高({ratio:.2f})"
            else:
                judge_type = f"8中庸-匹配({ratio:.2f})"
    else:
        judge_type = "非8中庸"
    
    print(f"{mid:<8} {h} vs {a:<22} {conf:>5.1f}% {diff:>+6.1f}% [{h8:>+2},{d8:>+2},{a8:>+2}]   {moderate_str:<10} {judge_type:<20}")
    
    # 预测
    if conf < 45:
        pred = '平局'  # 低置信排除法
    elif abs(diff) >= 25:
        pred = '主胜' if diff > 0 else '客胜'
    else:
        if h8 - a8 >= 2:
            pred = '主胜'
        elif a8 - h8 >= 2:
            pred = '客胜'
        else:
            pred = '主胜' if v7v8['prob_home'] > v7v8['prob_away'] else '客胜'
    
    all_games.append({
        'mid': mid, 'home': h, 'away': a, 'conf': conf, 'diff': diff,
        'h8': h8, 'd8': d8, 'a8': a8,
        'is_moderate': is_moderate, 'judge_type': judge_type, 'pred': pred
    })

print()
print("="*100)
print("## 偏离度分析")
print("="*100)

# 分析所有8中庸比赛
moderate_games = [g for g in all_games if g['is_moderate']]

print(f"\n8中庸比赛数: {len(moderate_games)}")

for g in moderate_games:
    conf, diff = g['conf'], g['diff']
    abs_diff = abs(diff)
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
    
    print(f"{g['mid']} {g['home']} vs {g['away']}: 置信度{conf:.1f}% 胜率差{g['diff']:+.1f}% 比例{ratio:.2f} 期望{expected_ratio_min:.2f}-{expected_ratio_max:.2f} 偏离:{deviation_type}({deviation:.2f}) 预测:{g['pred']}")
