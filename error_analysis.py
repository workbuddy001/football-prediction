# 错误案例分析 - 找出规律
import openpyxl
from pathlib import Path
import re
import ast

def parse_all_source(folder, date_prefix):
    """解析源数据"""
    files = sorted(Path(folder).glob(f"{date_prefix}*_源数据.md"))
    
    results = []
    for f in files:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # 解析文件名
        match = re.match(r'.+?_(\d+)_(.+?)vs(.+?)_源数据', f.stem)
        if not match:
            continue
        
        id_ = f"{date_prefix[:2]}{match.group(1)}"
        home = match.group(2)
        away = match.group(3)
        
        # 近况
        home_w = home_l = away_w = away_l = 0
        m = re.search(r'主队近况.*?(\d+)胜(\d+)平(\d+)负', content)
        if m:
            home_w, home_l = int(m.group(1)), int(m.group(3))
        m = re.search(r'客队近况.*?(\d+)胜(\d+)平(\d+)负', content)
        if m:
            away_w, away_l = int(m.group(1)), int(m.group(3))
        
        # 赔率
        initial = []
        m = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if m:
            try:
                initial = ast.literal_eval(re.sub(r'#.*', '', '[' + m.group(1) + ']'))
            except:
                pass
        
        realtime = []
        m = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if m:
            try:
                realtime = ast.literal_eval(re.sub(r'#.*', '', '[' + m.group(1) + ']'))
            except:
                pass
        
        if not initial or not realtime:
            continue
        
        results.append({
            'id': id_,
            'home': home,
            'away': away,
            'home_w': home_w,
            'home_l': home_l,
            'away_w': away_w,
            'away_l': away_l,
            'initial': initial,
            'realtime': realtime
        })
    
    return results

# 实际结果
actual_14 = {
    '周六001': '平局', '周六002': '客胜', '周六003': '平局', '周六004': '客胜',
    '周六005': '主胜', '周六006': '主胜', '周六007': '平局', '周六008': '主胜',
    '周六009': '主胜', '周六010': '客胜', '周六011': '主胜', '周六012': '平局',
    '周六013': '平局', '周六014': '主胜', '周六015': '主胜', '周六016': '平局',
    '周六017': '平局', '周六018': '主胜', '周六019': '主胜', '周六020': '主胜',
    '周六021': '主胜', '周六022': '主胜', '周六023': '客胜', '周六024': '平局',
    '周六025': '主胜', '周六026': '客胜', '周六027': '客胜', '周六028': '客胜',
    '周六029': '平局', '周六030': '主胜', '周六031': '客胜', '周六032': '平局',
}

actual_15 = {
    '周日001': '主胜', '周日003': '客胜', '周日004': '平局', '周日006': '客胜',
    '周日007': '客胜', '周日008': '平局', '周日009': '主胜', '周日010': '主胜',
    '周日011': '主胜', '周日012': '平局', '周日013': '平局', '周日014': '主胜',
    '周日015': '主胜', '周日016': '客胜', '周日017': '客胜', '周日018': '主胜',
    '周日019': '主胜', '周日020': '平局', '周日021': '平局', '周日022': '客胜',
    '周日023': '主胜', '周日024': '平局', '周日025': '主胜', '周日026': '主胜',
    '周日027': '主胜', '周日028': '客胜', '周日029': '主胜',
}

# 分析错误案例
print("=" * 70)
print("错误案例分析")
print("=" * 70)

# 分析1: 强队客场错误
print("\n【分析1: 强队客场 (客胜赔率1.5-2.0) 错误分析】")
print("-" * 50)

all_matches = parse_all_source("分析模板/3.14", "周六")
all_matches += parse_all_source("分析模板/3.15", "周日")

# 统计强队客场
strong_away_errors = []
for m in all_matches:
    id_ = m['id']
    actual = actual_14.get(id_) or actual_15.get(id_)
    
    if not actual:
        continue
    
    realtime = m['realtime']
    avg_away = sum(x[2] for x in realtime) / len(realtime)
    
    # 强队客场: 1.5 < 客胜 < 2.0
    if 1.5 < avg_away < 2.0:
        # 预测客胜
        pred = "客胜"
        is_correct = pred == actual
        
        if not is_correct:
            strong_away_errors.append({
                'id': id_,
                'home': m['home'],
                'away': m['away'],
                'away_odds': avg_away,
                'home_w': m['home_w'],
                'home_l': m['home_l'],
                'away_w': m['away_w'],
                'away_l': m['away_l'],
                'actual': actual
            })

print(f"强队客场共{len(strong_away_errors)}场错误:")
for e in strong_away_errors:
    print(f"  {e['id']}: {e['away']}(客胜{e['away_odds']:.2f}) vs {e['home']}, 实际{e['actual']}")

# 分析2: 高概率主胜错误
print("\n【分析2: 高概率主胜(>50%)错误分析】")
print("-" * 50)

high_prob_errors = []
for m in all_matches:
    id_ = m['id']
    actual = actual_14.get(id_) or actual_15.get(id_)
    
    if not actual:
        continue
    
    realtime = m['realtime']
    avg_home = sum(x[0] for x in realtime) / len(realtime)
    avg_draw = sum(x[1] for x in realtime) / len(realtime)
    avg_away = sum(x[2] for x in realtime) / len(realtime)
    
    prob_home = (1/avg_home) / (1/avg_home + 1/avg_draw + 1/avg_away)
    
    if prob_home > 0.50:
        pred = "主胜"
        is_correct = pred == actual
        
        if not is_correct:
            high_prob_errors.append({
                'id': id_,
                'home': m['home'],
                'away': m['away'],
                'prob': prob_home,
                'actual': actual
            })

print(f"高概率主胜共{len(high_prob_errors)}场错误:")
for e in high_prob_errors[:10]:
    print(f"  {e['id']}: {e['home']}(主胜概率{e['prob']*100:.0f}%) vs {e['away']}, 实际{e['actual']}")

# 分析3: 平局未识别
print("\n【分析3: 实际平局但未预测平局】")
print("-" * 50)

draw_missed = []
for m in all_matches:
    id_ = m['id']
    actual = actual_14.get(id_) or actual_15.get(id_)
    
    if actual != "平局":
        continue
    
    realtime = m['realtime']
    avg_home = sum(x[0] for x in realtime) / len(realtime)
    avg_draw = sum(x[1] for x in realtime) / len(realtime)
    avg_away = sum(x[2] for x in realtime) / len(realtime)
    
    prob_home = (1/avg_home) / (1/avg_home + 1/avg_draw + 1/avg_away)
    prob_draw = (1/avg_draw) / (1/avg_home + 1/avg_draw + 1/avg_away)
    prob_away = (1/avg_away) / (1/avg_home + 1/avg_draw + 1/avg_away)
    
    initial = m['initial']
    init_draw = sum(x[1] for x in initial) / len(initial)
    draw_change = (avg_draw - init_draw) / init_draw * 100
    
    draw_up = sum(1 for i in range(len(initial)) if realtime[i][1] > initial[i][1])
    draw_down_pct = (len(initial) - draw_up) / len(initial) * 100
    
    draw_missed.append({
        'id': id_,
        'home': m['home'],
        'away': m['away'],
        'draw_odds': avg_draw,
        'prob': prob_draw * 100,
        'change': draw_change,
        'down_pct': draw_down_pct
    })

print(f"实际平局{len(draw_missed)}场，识别情况:")
for e in draw_missed:
    print(f"  {e['id']}: {e['home']} vs {e['away']}, 平赔{e['draw_odds']:.2f}, 概率{e['prob']:.0f}%, 变化{e['change']:.1f}%, 降赔{e['down_pct']:.0f}%")

# 分析4: 联赛特性
print("\n【分析4: 联赛错误率】")
print("-" * 50)

league_errors = {}
for m in all_matches:
    id_ = m['id']
    actual = actual_14.get(id_) or actual_15.get(id_)
    
    if not actual:
        continue
    
    # 简化判断联赛
    league = "未知"
    if '日职' in m['home'] or '日职' in m['away'] or 'J联赛' in str(m):
        league = "日职"
    elif '韩职' in m['home'] or '韩职' in str(m):
        league = "韩职"
    elif '英超' in m['home'] or '英超' in str(m):
        league = "英超"
    elif '意甲' in m['home'] or '意甲' in str(m):
        league = "意甲"
    elif '德甲' in m['home'] or '德甲' in str(m):
        league = "德甲"
    elif '西甲' in m['home'] or '西甲' in str(m):
        league = "西甲"
    elif '法甲' in m['home'] or '法甲' in str(m):
        league = "法甲"
    
    if league not in league_errors:
        league_errors[league] = {'total': 0, 'errors': 0}
    
    league_errors[league]['total'] += 1
    
    # 判断是否错误(简化)
    realtime = m['realtime']
    avg_home = sum(x[0] for x in realtime) / len(realtime)
    avg_draw = sum(x[1] for x in realtime) / len(realtime)
    avg_away = sum(x[2] for x in realtime) / len(realtime)
    
    prob_home = (1/avg_home) / (1/avg_home + 1/avg_draw + 1/avg_away)
    prob_draw = (1/avg_draw) / (1/avg_home + 1/avg_draw + 1/avg_away)
    prob_away = (1/avg_away) / (1/avg_home + 1/avg_draw + 1/avg_away)
    
    if prob_home > prob_away and prob_home > prob_draw:
        pred = "主胜"
    elif prob_away > prob_home and prob_away > prob_draw:
        pred = "客胜"
    else:
        pred = "平局"
    
    if pred != actual:
        league_errors[league]['errors'] += 1

for league, stats in sorted(league_errors.items(), key=lambda x: x[1]['errors']/x[1]['total'], reverse=True):
    if stats['total'] > 0:
        err_rate = stats['errors'] / stats['total'] * 100
        print(f"  {league}: 错误{stats['errors']}/{stats['total']} = {err_rate:.0f}%")
