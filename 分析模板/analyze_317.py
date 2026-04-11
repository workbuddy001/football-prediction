# 3.17比赛分析脚本 - 使用新规律
import os
import re
import json

def count_8_in_odds(odds_list):
    """统计赔率中末尾为8的数量"""
    count = 0
    for odds in odds_list:
        for odd in odds:
            odd_str = f"{odd:.2f}"
            if odd_str.endswith('8'):
                count += 1
    return count

def analyze_match(file_path):
    """分析单场比赛"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取基本信息
    match_id = re.search(r'编号：(\w+)', content)
    match_id = match_id.group(1) if match_id else ""
    
    home_team = re.search(r'\| 主队 \| (.+) \|', content)
    away_team = re.search(r'\| 客队 \| (.+) \|', content)
    home_team = home_team.group(1) if home_team else ""
    away_team = away_team.group(1) if away_team else ""
    
    # 提取胜率
    home_rate_match = re.search(r'\| 主队近况 \|.*胜率(\d+)%', content)
    away_rate_match = re.search(r'\| 客队近况 \|.*胜率(\d+)%', content)
    home_rate = int(home_rate_match.group(1)) if home_rate_match else 0
    away_rate = int(away_rate_match.group(1)) if away_rate_match else 0
    rate_diff = home_rate - away_rate
    
    # 提取初盘和即时赔率
    initial_odds_match = re.findall(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', content.split('## 二、初盘赔率')[1].split('## 三、即时赔率')[0])
    realtime_odds_match = re.findall(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', content.split('## 三、即时赔率')[1].split('## 四、竞彩')[0])
    
    initial_odds = [(float(o[0]), float(o[1]), float(o[2])) for o in initial_odds_match]
    realtime_odds = [(float(o[0]), float(o[1]), float(o[2])) for o in realtime_odds_match]
    
    # 计算8变化
    initial_8 = count_8_in_odds(initial_odds)
    realtime_8 = count_8_in_odds(realtime_odds)
    diff_8 = realtime_8 - initial_8
    
    # 计算V7置信度
    if initial_odds:
        home_probs = [1/o[0] for o in initial_odds]
        draw_probs = [1/o[1] for o in initial_odds]
        away_probs = [1/o[2] for o in initial_odds]
        
        avg_home = sum(home_probs) / len(home_probs)
        avg_draw = sum(draw_probs) / len(draw_probs)
        avg_away = sum(away_probs) / len(away_probs)
        total = avg_home + avg_draw + avg_away
        
        home_conf = avg_home / total * 100
        draw_conf = avg_draw / total * 100
        away_conf = avg_away / total * 100
        
        v7_choice = max([(home_conf, '主胜'), (draw_conf, '平局'), (away_conf, '客胜')], key=lambda x: x[0])
        confidence = v7_choice[0]
        choice = v7_choice[1]
    else:
        confidence = 0
        choice = "未知"
    
    return {
        'id': match_id,
        'home': home_team,
        'away': away_team,
        'confidence': confidence,
        'choice': choice,
        'home_rate': home_rate,
        'away_rate': away_rate,
        'rate_diff': rate_diff,
        'initial_8': initial_8,
        'realtime_8': realtime_8,
        'diff_8': diff_8
    }

def apply_new_rules(match):
    """应用新规律判断"""
    conf = match['confidence']
    diff_8 = match['diff_8']
    rate_diff = match['rate_diff']
    choice = match['choice']
    
    # 置信度筛选
    if conf < 55:
        return {'recommend': '不推荐', 'reason': f'置信度{conf:.0f}%不足', 'priority': 0}
    
    # 新规律判断
    if diff_8 == -5:
        if abs(rate_diff) <= 20:
            # 状态焦灼 - 诱盘
            return {'recommend': '不推荐/防平', 'reason': '8变化-5+状态焦灼，诱盘风险', 'priority': 1}
        else:
            # 状态极好 - 实盘
            recommend = '主胜' if rate_diff > 0 else '客胜'
            return {'recommend': f'强烈推荐{recommend}', 'reason': f'8变化-5+状态极好，庄家挡不住', 'priority': 5}
    
    if -5 < diff_8 <= -2:
        return {'recommend': '推荐平局', 'reason': '8变化-2~-4，平局是底限', 'priority': 4}
    
    if diff_8 > 0:
        if abs(rate_diff) > 20:
            # 状态极好
            recommend = '主胜' if rate_diff > 0 else '客胜'
            return {'recommend': f'推荐{recommend}', 'reason': '8变化正数+状态极好', 'priority': 3}
        else:
            # 状态焦灼
            return {'recommend': '观察', 'reason': '8变化正数+状态焦灼，需观察', 'priority': 2}
    
    return {'recommend': '观察', 'reason': '无明显规律', 'priority': 1}

# 分析所有3.17比赛
print("=" * 80)
print("3.17 比赛分析 - V7 + 8探测新规律")
print("=" * 80)

results = []
for f in sorted(os.listdir('3.17')):
    if '源数据' in f:
        path = os.path.join('3.17', f)
        match = analyze_match(path)
        rule_result = apply_new_rules(match)
        
        results.append({
            'match': match,
            'rule': rule_result
        })

# 按优先级排序
results.sort(key=lambda x: x['rule']['priority'], reverse=True)

print("\n【高优先级推荐】\n")
for r in results:
    m = r['match']
    rule = r['rule']
    if rule['priority'] >= 3:
        print(f"{m['id']} {m['home']} vs {m['away']}")
        print(f"  V7预测: {m['choice']} ({m['confidence']:.0f}%)")
        print(f"  状态: 主{m['home_rate']}% vs 客{m['away_rate']}% (差{m['rate_diff']}%)")
        print(f"  8变化: {m['initial_8']} -> {m['realtime_8']} ({m['diff_8']:+d})")
        print(f"  推荐: {rule['recommend']} - {rule['reason']}")
        print()

print("\n【其他比赛】\n")
for r in results:
    m = r['match']
    rule = r['rule']
    if rule['priority'] < 3:
        print(f"{m['id']} {m['home']} vs {m['away']}: {rule['recommend']}")
