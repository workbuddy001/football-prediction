# 3.17比赛分析 - 更科学的方法：分别计算各赔率的8变化
import os
import re

def count_8_in_odds(odds_list):
    """统计赔率中末尾为8的数量"""
    count = 0
    for odd in odds_list:
        odd_str = f"{odd:.2f}"
        if odd_str.endswith('8'):
            count += 1
    return count

def analyze_match_from_file(file_path):
    """分析单场比赛"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    match_id = re.search(r'编号：(\w+)', content)
    match_id = match_id.group(1) if match_id else ""
    
    home_team = re.search(r'\| 主队 \| (.+) \|', content)
    away_team = re.search(r'\| 客队 \| (.+) \|', content)
    home_team = home_team.group(1) if home_team else ""
    away_team = away_team.group(1) if away_team else ""
    
    home_rate_match = re.search(r'\| 主队近况 \|.*胜率(\d+)%', content)
    away_rate_match = re.search(r'\| 客队近况 \|.*胜率(\d+)%', content)
    home_rate = int(home_rate_match.group(1)) if home_rate_match else 0
    away_rate = int(away_rate_match.group(1)) if away_rate_match else 0
    rate_diff = home_rate - away_rate
    
    try:
        # 提取初盘和即时赔率
        initial_odds_match = re.findall(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', content.split('## 二、初盘赔率')[1].split('## 三、即时赔率')[0])
        realtime_odds_match = re.findall(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', content.split('## 三、即时赔率')[1].split('## 四、竞彩')[0])
        
        initial_odds = [(float(o[0]), float(o[1]), float(o[2])) for o in initial_odds_match]
        realtime_odds = [(float(o[0]), float(o[1]), float(o[2])) for o in realtime_odds_match]
        
        # 分别计算各赔率的8数量
        init_home = [o[0] for o in initial_odds]
        init_draw = [o[1] for o in initial_odds]
        init_away = [o[2] for o in initial_odds]
        
        real_home = [o[0] for o in realtime_odds]
        real_draw = [o[1] for o in realtime_odds]
        real_away = [o[2] for o in realtime_odds]
        
        # 各赔率的8变化
        diff_home_8 = count_8_in_odds(real_home) - count_8_in_odds(init_home)
        diff_draw_8 = count_8_in_odds(real_draw) - count_8_in_odds(init_draw)
        diff_away_8 = count_8_in_odds(real_away) - count_8_in_odds(init_away)
        
        # 计算V7置信度
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
        
        # 根据V7预测方向选择对应的8变化
        if choice == '主胜':
            diff_8 = diff_home_8
        elif choice == '客胜':
            diff_8 = diff_away_8
        else:
            diff_8 = diff_draw_8
            
    except:
        return None
    
    return {
        'id': match_id,
        'home': home_team,
        'away': away_team,
        'confidence': confidence,
        'choice': choice,
        'home_rate': home_rate,
        'away_rate': away_rate,
        'rate_diff': rate_diff,
        'diff_8': diff_8,
        'diff_home_8': diff_home_8,
        'diff_draw_8': diff_draw_8,
        'diff_away_8': diff_away_8,
    }

def get_rule_and_recommend(m):
    diff_8 = m['diff_8']
    rate_diff = m['rate_diff']
    choice = m['choice']
    confidence = m['confidence']
    
    if confidence < 55:
        return '不推荐', f'置信度{confidence:.0f}%不足'
    
    if diff_8 == -5:
        if abs(rate_diff) <= 20:
            return "规律2", "不推荐/防平"
        else:
            recommend = "主胜" if rate_diff > 0 else "客胜"
            return "规律1", f"强烈推荐{recommend}"
    elif -5 < diff_8 <= -2:
        return "规律3", "推荐平局"
    elif diff_8 > 0:
        if abs(rate_diff) > 20:
            recommend = "主胜" if rate_diff > 0 else "客胜"
            return "规律4", f"推荐{recommend}"
        else:
            return "规律5", "预测方打不出/观察"
    elif diff_8 == 0:
        return "无规律", "观察"
    else:
        return "其他", "观察"

# 分析3.17比赛
print("=" * 100)
print("3.17比赛分析 - 更科学的方法：分别计算各赔率的8变化")
print("=" * 100)

results = []
for f in sorted(os.listdir('3.17')):
    if '源数据' in f:
        path = os.path.join('3.17', f)
        match = analyze_match_from_file(path)
        if match:
            results.append(match)

# 按优先级排序
def sort_key(m):
    rule, _ = get_rule_and_recommend(m)
    priority = {
        "规律1": 1, "规律2": 2, "规律3": 3, "规律4": 4, "规律5": 5, "无规律": 6, "其他": 7, "不推荐": 99
    }
    return priority.get(rule, 99)

results.sort(key=sort_key)

print(f"\n{'比赛':<20} {'置信度':<8} {'V7预测':<6} {'8变化':<8} {'状态':<12} {'规律':<12} {'推荐':<15}")
print("-" * 100)

for m in results:
    match_name = f"{m['home'][:4]}vs{m['away'][:4]}"
    confidence = f"{m['confidence']:.0f}%"
    choice = m['choice']
    diff_8 = f"{m['diff_8']:+d}"
    
    if abs(m['rate_diff']) > 20:
        status = "状态极好" if m['rate_diff'] > 0 else "客队极好"
    else:
        status = "焦灼"
    
    rule, recommend = get_rule_and_recommend(m)
    
    print(f"{match_name:<20} {confidence:<8} {choice:<6} {diff_8:<8} {status:<12} {rule:<12} {recommend:<15}")

print("\n" + "=" * 100)
print("详细分析 - 高优先级比赛")
print("=" * 100)

for m in results:
    rule, recommend = get_rule_and_recommend(m)
    if rule in ['规律1', '规律2', '规律3', '规律4']:
        print(f"\n【{m['id']} {m['home']} vs {m['away']}】")
        print(f"  V7预测: {m['choice']} ({m['confidence']:.0f}%)")
        print(f"  状态: 主{m['home_rate']}% vs 客{m['away_rate']}% (差{m['rate_diff']}%)")
        print(f"  8变化: 主胜{m['diff_home_8']:+d}, 平局{m['diff_draw_8']:+d}, 客胜{m['diff_away_8']:+d}")
        print(f"  → V7预测方向的8变化: {m['diff_8']:+d}")
        print(f"  推荐: {recommend}")
