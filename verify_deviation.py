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
    
    # 赔率
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
    
    # 8变化: 末尾为8的赔率数量变化
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

# 实际结果 (从复盘分析)
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

# 预测结果 (按策略)
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

print('='*150)
print(f"{'编号':<8} {'对阵':<22} {'置信度':<8} {'胜率差':<8} {'8变化':<12} {'实盘类型':<12} {'偏差':<6} {'预测':<6} {'实际':<6} {'结果':<4}")
print('='*150)

# 收集所有实盘类型比赛
real_market_games = []

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
    
    # 实盘判断和偏差计算
    real_type = "非实盘"
    deviation = 0
    
    if is_moderate:
        if 55 <= conf < 65 and 10 <= abs_diff <= 20:
            real_type = "实盘1"
            deviation = abs_diff - 15  # 中心值15
        elif 65 <= conf < 75 and 30 <= abs_diff <= 40:
            real_type = "实盘2"
            deviation = abs_diff - 35  # 中心值35
        elif conf >= 75 and abs_diff >= 40:
            real_type = "实盘3"
            deviation = abs_diff - 40  # 最小值40
    
    pred = predictions.get(mid, '')
    act = actual_results.get(mid, '')
    result = 'O' if pred == act else 'X'
    
    print(f'{mid:<8} {home} vs {away:<18} {conf:>5.1f}% {diff:>+6.1f}% [{h8:>+2},{d8:>+2},{a8:>+2}]   {real_type:<12} {deviation:>+5} {pred:<6} {act:<6} {result}')
    
    if real_type != "非实盘":
        real_market_games.append({
            'mid': mid,
            'home': home,
            'away': away,
            'conf': conf,
            'diff': diff,
            'deviation': deviation,
            'real_type': real_type,
            'pred': pred,
            'actual': act,
            'result': result,
        })

print()
print('='*100)
print('## 实盘比赛偏差与结果对照')
print('='*100)

for g in real_market_games:
    status = "OK" if g['result'] == 'O' else "X"
    print(f"{g['mid']} {g['home']} vs {g['away']}")
    print(f"   类型:{g['real_type']} 偏差:{g['deviation']:>+5} 预测:{g['pred']} 实际:{g['actual']} {status}")
    print()

# 统计偏差与准确率
print('='*80)
print('## 偏差与准确率统计')
print('='*80)

deviations = [g['deviation'] for g in real_market_games]
correct = sum(1 for g in real_market_games if g['result'] == 'O')

if deviations:
    print(f"实盘比赛数: {len(real_market_games)}")
    print(f"正确数: {correct}")
    print(f"准确率: {correct/len(real_market_games)*100:.1f}%")
    print(f"平均偏差: {sum(deviations)/len(deviations):.1f}")
    print(f"偏差范围: {min(deviations)} ~ {max(deviations)}")
    
    # 按偏差分组
    low_dev = [g for g in real_market_games if g['deviation'] <= 5]
    mid_dev = [g for g in real_market_games if 5 < g['deviation'] <= 15]
    high_dev = [g for g in real_market_games if g['deviation'] > 15]
    
    print()
    print("按偏差分组:")
    print(f"  低偏差(≤5): {len(low_dev)}场, 正确:{sum(1 for g in low_dev if g['result']=='O')}, 准确率:{len(low_dev) and sum(1 for g in low_dev if g['result']=='O')/len(low_dev)*100:.0f}%")
    print(f"  中偏差(6-15): {len(mid_dev)}场, 正确:{sum(1 for g in mid_dev if g['result']=='O')}, 准确率:{len(mid_dev) and sum(1 for g in mid_dev if g['result']=='O')/len(mid_dev)*100:.0f}%")
    print(f"  高偏差(>15): {len(high_dev)}场, 正确:{sum(1 for g in high_dev if g['result']=='O')}, 准确率:{len(high_dev) and sum(1 for g in high_dev if g['result']=='O')/len(high_dev)*100:.0f}%")
