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
    
    initial_odds = []
    match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if match:
        try:
            odds_str = '[' + re.sub(r'#.*', '', match.group(1)) + ']'
            initial_odds = ast.literal_eval(odds_str)
        except: pass
    
    realtime_odds = []
    match = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if match:
        try:
            odds_str = '[' + re.sub(r'#.*', '', match.group(1)) + ']'
            realtime_odds = ast.literal_eval(odds_str)
        except: pass
    
    info['initial_odds'] = initial_odds
    info['realtime_odds'] = realtime_odds
    
    return info

def calc_v7v8(info):
    initial = info.get('initial_odds', [])
    realtime = info.get('realtime_odds', [])
    
    if not initial or not realtime:
        return None
    
    real_home = sum(x[0] for x in realtime) / len(realtime)
    real_draw = sum(x[1] for x in realtime) / len(realtime)
    real_away = sum(x[2] for x in realtime) / len(realtime)
    
    real_prob_home = 1/real_home / (1/real_home + 1/real_draw + 1/real_away)
    real_prob_draw = 1/real_draw / (1/real_home + 1/real_draw + 1/real_away)
    real_prob_away = 1/real_away / (1/real_home + 1/real_draw + 1/real_away)
    
    confidence = max(real_prob_home, real_prob_draw, real_prob_away) * 100
    diff = (real_prob_home - real_prob_away) * 100
    
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
        'confidence': confidence,
        'diff': diff,
        'home_8': home_8,
        'draw_8': draw_8,
        'away_8': away_8,
    }

# 实际结果
actual_results = {
    '周六001': '平局', '周六002': '客胜', '周六003': '平局', '周六004': '客胜',
    '周六005': '主胜', '周六006': '主胜', '周六007': '平局', '周六008': '主胜',
    '周六009': '主胜', '周六010': '客胜', '周六011': '主胜', '周六012': '平局',
    '周六013': '平局', '周六014': '主胜', '周六015': '主胜', '周六016': '平局',
    '周六017': '平局', '周六018': '主胜', '周六019': '主胜', '周六020': '主胜',
    '周六021': '主胜', '周六022': '主胜', '周六023': '客胜', '周六024': '平局',
    '周六025': '主胜', '周六026': '客胜', '周六027': '客胜', '周六028': '主胜',
    '周六029': '平局', '周六030': '主胜', '周六031': '客胜', '周六032': '平局',
}

# 预测
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

print("="*160)
print(f"{'编号':<8} {'对阵':<22} {'置信度':<8} {'胜率差':<8} {'8变化':<12} {'实盘判定':<20} {'预测':<6} {'实际':<6} {'结果'}")
print("="*160)

all_games = []

for f in files:
    info = parse_file(f)
    v7v8 = calc_v7v8(info)
    if not v7v8:
        continue
    
    mid = info.get('match_id', '')
    home = info.get('home_team', '')
    away = info.get('away_team', '')
    
    conf = v7v8['confidence']
    diff = v7v8['diff']
    abs_diff = abs(diff)
    h8 = v7v8['home_8']
    d8 = v7v8['draw_8']
    a8 = v7v8['away_8']
    
    # 8中庸判断
    is_moderate = abs(h8) <= 2 and abs(d8) <= 2 and abs(a8) <= 2
    
    # 实盘判断 - 严格按照用户定义
    real_judge = ""
    if is_moderate:
        if 55 <= conf < 65 and 10 <= abs_diff <= 20:
            # 实盘1: 偏差 = 偏离15（中值）的距离
            deviation = abs(abs_diff - 15)
            real_judge = f"实盘1(55-65%,10-20%)偏差{deviation:.0f}"
        elif 65 <= conf < 75 and 30 <= abs_diff <= 40:
            deviation = abs(abs_diff - 35)
            real_judge = f"实盘2(65-75%,30-40%)偏差{deviation:.0f}"
        elif conf >= 75 and abs_diff >= 40:
            deviation = abs(abs_diff - 40)
            real_judge = f"实盘3(75%+,40%+)偏差{deviation:.0f}"
        else:
            real_judge = f"8中庸但非实盘(conf{conf:.0f}%,差{abs_diff:.0f}%)"
            deviation = None
    else:
        real_judge = f"非实盘(8:[{h8},{d8},{a8}])"
        deviation = None
    
    pred = predictions.get(mid, '')
    act = actual_results.get(mid, '')
    result = 'O' if pred == act else 'X'
    
    print(f"{mid:<8} {home} vs {away:<18} {conf:>5.1f}% {diff:>+6.1f}% [{h8:>+2},{d8:>+2},{a8:>+2}]   {real_judge:<20} {pred:<6} {act:<6} {result}")
    
    all_games.append({
        'mid': mid, 'home': home, 'away': away, 'conf': conf, 'diff': diff,
        'deviation': deviation, 'real_judge': real_judge, 'pred': pred, 'actual': act, 'result': result
    })

# 分析偏差与准确率的关系
print()
print("="*100)
print("## 偏差与准确率关系分析")
print("="*100)

# 只分析8中庸的比赛
moderate_games = [g for g in all_games if '8中庸' in g['real_judge'] or '实盘' in g['real_judge']]

if moderate_games:
    # 有偏差的比赛
    with_deviation = [g for g in moderate_games if g['deviation'] is not None]
    without_deviation = [g for g in moderate_games if g['deviation'] is None]
    
    print(f"\n8中庸比赛总数: {len(moderate_games)}")
    print(f"  - 满足实盘条件: {len(with_deviation)}")
    print(f"  - 不满足实盘条件: {len(without_deviation)}")
    
    if with_deviation:
        print("\n### 满足实盘条件的比赛:")
        for g in with_deviation:
            status = "O" if g['result'] == 'O' else "X"
            print(f"  {g['mid']} {g['home']} vs {g['away']}: 偏差={g['deviation']:.0f}, 预测={g['pred']}, 实际={g['actual']} [{status}]")
        
        # 按偏差分组
        low = [g for g in with_deviation if g['deviation'] <= 5]
        mid = [g for g in with_deviation if 5 < g['deviation'] <= 10]
        high = [g for g in with_deviation if g['deviation'] > 10]
        
        print("\n### 按偏差分组准确率:")
        print(f"  低偏差(<=5): {len(low)}场, 正确:{sum(1 for g in low if g['result']=='O')}, 准确率:{len(low) and sum(1 for g in low if g['result']=='O')/len(low)*100:.0f}%")
        print(f"  中偏差(6-10): {len(mid)}场, 正确:{sum(1 for g in mid if g['result']=='O')}, 准确率:{len(mid) and sum(1 for g in mid if g['result']=='O')/len(mid)*100:.0f}%")
        print(f"  高偏差(>10): {len(high)}场, 正确:{sum(1 for g in high if g['result']=='O')}, 准确率:{len(high) and sum(1 for g in high if g['result']=='O')/len(high)*100:.0f}%")

print()
print("="*100)
print("## 结论")
print("="*100)

# 分析非8中庸但满足"实盘比例"的比赛（胜率差/置信度 ≈ 0.5-0.7）
print("\n### 分析：胜率差与置信度比例关系")
ratio_games = []
for g in all_games:
    if g['conf'] >= 50 and abs(g['diff']) >= 10:
        ratio = abs(g['diff']) / g['conf']
        if 0.4 <= ratio <= 0.9:
            ratio_games.append({**g, 'ratio': ratio})

if ratio_games:
    # 按比例分组
    perfect = [g for g in ratio_games if 0.5 <= g['ratio'] <= 0.7]
    near = [g for g in ratio_games if 0.4 <= g['ratio'] < 0.5 or 0.7 < g['ratio'] <= 0.9]
    far = [g for g in ratio_games if g['ratio'] < 0.4 or g['ratio'] > 0.9]
    
    print(f"比例实盘(0.4-0.9)比赛: {len(ratio_games)}场")
    print(f"  - 完美比例(0.5-0.7): {len(perfect)}场, 正确:{sum(1 for g in perfect if g['result']=='O')}, 准确率:{len(perfect) and sum(1 for g in perfect if g['result']=='O')/len(perfect)*100:.0f}%")
    print(f"  - 接近(0.4-0.5或0.7-0.9): {len(near)}场, 正确:{sum(1 for g in near if g['result']=='O')}, 准确率:{len(near) and sum(1 for g in near if g['result']=='O')/len(near)*100:.0f}%")
    print(f"  - 偏离(>0.9或<0.4): {len(far)}场, 正确:{sum(1 for g in far if g['result']=='O')}, 准确率:{len(far) and sum(1 for g in far if g['result']=='O')/len(far)*100:.0f}%")
