# 回溯分析：置信度45%-55%区间的比赛
import os
import re

def count_8_in_odds(odds_list):
    """统计赔率中末尾为8的数量"""
    count = 0
    for odds in odds_list:
        for odd in odds:
            odd_str = f"{odd:.2f}"
            if odd_str.endswith('8'):
                count += 1
    return count

def analyze_match_from_file(file_path, actual_result=None):
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
    try:
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
        'initial_8': initial_8,
        'realtime_8': realtime_8,
        'diff_8': diff_8,
        'actual': actual_result
    }

# 实际结果（从之前的分析中收集）
actual_results = {
    "周五010": "主胜", "周五007": "平局", "周六012": "平局", 
    "周六013": "平局", "周六016": "平局", "周日014": "主胜",
    "周六008": "客胜", "周日018": "主胜", "周日010": "主胜", 
    "周六014": "主胜", "周一004": "平局", "周日011": "客胜",
}

# 分析所有历史比赛
print("=" * 80)
print("回溯分析：置信度45%-55%区间的比赛")
print("=" * 80)

all_matches = []
date_folders = ['3.12', '3.13', '3.14', '3.15', '3.16']

for date_folder in date_folders:
    folder_path = f'.\\{date_folder}'
    if not os.path.exists(folder_path):
        continue
        
    for f in os.listdir(folder_path):
        if '源数据' in f:
            path = os.path.join(folder_path, f)
            match = analyze_match_from_file(path, actual_results.get(f.split('_')[0]))
            if match and 45 <= match['confidence'] < 55:
                all_matches.append(match)

# 按8变化分类
print(f"\n找到 {len(all_matches)} 场置信度在45%-55%区间的比赛\n")

# 分类分析
categories = {
    'diff_minus_5': {'name': '8变化-5', 'matches': [], 'correct': 0},
    'diff_minus_2_to_4': {'name': '8变化-2~-4', 'matches': [], 'correct': 0},
    'diff_positive': {'name': '8变化正数+状态极好', 'matches': [], 'correct': 0},
    'diff_positive_close': {'name': '8变化正数+状态焦灼', 'matches': [], 'correct': 0},
    'diff_zero': {'name': '8变化0', 'matches': [], 'correct': 0},
    'diff_other': {'name': '其他', 'matches': [], 'correct': 0},
}

for m in all_matches:
    diff_8 = m['diff_8']
    rate_diff = m['rate_diff']
    
    if diff_8 == -5:
        cat = 'diff_minus_5'
    elif -5 < diff_8 <= -2:
        cat = 'diff_minus_2_to_4'
    elif diff_8 > 0:
        if abs(rate_diff) > 20:
            cat = 'diff_positive'
        else:
            cat = 'diff_positive_close'
    elif diff_8 == 0:
        cat = 'diff_zero'
    else:
        cat = 'diff_other'
    
    categories[cat]['matches'].append(m)
    
    # 检查是否正确
    if m['actual']:
        predicted = m['choice']
        actual = m['actual']
        if predicted == actual:
            categories[cat]['correct'] += 1

# 输出结果
for key, cat in categories.items():
    if cat['matches']:
        print(f"\n{'='*60}")
        print(f"【{cat['name']}】共 {len(cat['matches'])} 场")
        if cat['correct'] > 0 and len(cat['matches']) > 0:
            print(f"命中率: {cat['correct']}/{len(cat['matches'])} = {cat['correct']*100/len(cat['matches']):.1f}%")
        print("-" * 60)
        
        for m in cat['matches']:
            status = "状态极好" if abs(m['rate_diff']) > 20 else "状态焦灼"
            result = f" | 实际:{m['actual']}" if m['actual'] else ""
            print(f"{m['id']} {m['home']}vs{m['away']}: 预测{m['choice']}({m['confidence']:.0f}%) | 8变化{m['diff_8']:+d} | 胜率差{m['rate_diff']}%({status}){result}")
