# 回溯分析 - 更科学的方法：分别计算各赔率的8变化
import os
import re

def count_8_in_odds(odds_list):
    count = 0
    for odd in odds_list:
        odd_str = f"{odd:.2f}"
        if odd_str.endswith('8'):
            count += 1
    return count

def analyze_match_from_file(file_path, actual_result=None):
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
        
        diff_home_8 = count_8_in_odds(real_home) - count_8_in_odds(init_home)
        diff_draw_8 = count_8_in_odds(real_draw) - count_8_in_odds(init_draw)
        diff_away_8 = count_8_in_odds(real_away) - count_8_in_odds(init_away)

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
            
            # 根据V7预测方向选择对应的8变化
            if choice == '主胜':
                diff_8 = diff_home_8
            elif choice == '客胜':
                diff_8 = diff_away_8
            else:
                diff_8 = diff_draw_8
        else:
            confidence = 0
            choice = "未知"
            diff_8 = 0
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
        'actual': actual_result
    }

# 实际结果
actual_results = {
    "周五010": "主胜", "周五007": "平局", "周六012": "平局", 
    "周六013": "平局", "周六016": "平局", "周日014": "主胜",
    "周六008": "客胜", "周日018": "主胜", "周日010": "主胜", 
    "周六014": "主胜", "周一004": "平局", "周日011": "客胜",
    "周五008": "主胜", "周六023": "客胜", "周六005": "主胜",
    "周日026": "主胜", "周四001": "平局", "周六010": "客胜",
    "周六017": "平局", "周六019": "主胜", "周六021": "主胜",
    "周六024": "平局", "周日027": "主胜", "周一006": "平局",
    "周日019": "主胜", "周五002": "平局", "周日005": "主胜",
    "周日020": "平局", "周一002": "客胜",
}

print("=" * 100)
print("回溯分析 - 更科学的方法：分别计算各赔率的8变化")
print("=" * 100)

all_matches = []
date_folders = ['3.12', '3.13', '3.14', '3.15', '3.16']

for date_folder in date_folders:
    folder_path = f'.\\{date_folder}'
    if not os.path.exists(folder_path):
        continue
    for f in os.listdir(folder_path):
        if '源数据' in f:
            path = os.path.join(folder_path, f)
            match_id = f.split('_')[0]
            match = analyze_match_from_file(path, actual_results.get(match_id))
            if match and match['confidence'] >= 55:
                all_matches.append(match)

print(f"\n找到 {len(all_matches)} 场置信度>=55%的比赛\n")

# 按8变化分类
categories = {}

for m in all_matches:
    diff_8 = m['diff_8']
    rate_diff = m['rate_diff']
    
    # 分类
    if diff_8 == -5:
        cat_key = 'diff_minus_5'
    elif -5 < diff_8 <= -2:
        cat_key = 'diff_minus_2_to_4'
    elif diff_8 > 0:
        if abs(rate_diff) > 20:
            cat_key = 'diff_positive_strong'
        else:
            cat_key = 'diff_positive_close'
    elif diff_8 == 0:
        cat_key = 'diff_zero'
    else:
        cat_key = 'diff_other'
    
    if cat_key not in categories:
        categories[cat_key] = {'name': '', 'matches': [], 'correct': 0, 'total': 0}
    
    categories[cat_key]['matches'].append(m)
    categories[cat_key]['total'] += 1
    
    if m['actual']:
        if m['choice'] == m['actual']:
            categories[cat_key]['correct'] += 1

# 设置分类名称
cat_names = {
    'diff_minus_5': '8变化-5',
    'diff_minus_2_to_4': '8变化-2~-4',
    'diff_positive_strong': '8变化正数+状态极好',
    'diff_positive_close': '8变化正数+状态焦灼',
    'diff_zero': '8变化0',
    'diff_other': '其他',
}

# 输出结果
for key in ['diff_minus_5', 'diff_minus_2_to_4', 'diff_positive_strong', 'diff_positive_close', 'diff_zero', 'diff_other']:
    if key not in categories:
        continue
    cat = categories[key]
    cat['name'] = cat_names.get(key, key)
    
    if cat['matches']:
        print(f"\n{'='*80}")
        hit_rate = f"{cat['correct']*100/max(cat['total'],1):.1f}%" if cat['total'] > 0 else "N/A"
        print(f"【{cat['name']}】共 {cat['total']} 场 | 命中: {cat['correct']} | 命中率: {hit_rate}")
        print("-" * 80)
        
        for m in cat['matches']:
            status = "极好" if abs(m['rate_diff']) > 20 else "焦灼"
            result = f" | 实际:{m['actual']}" if m['actual'] else ""
            is_correct = "对" if m['actual'] and m['choice'] == m['actual'] else ""
            print(f"{m['id']:<6} {m['home'][:4]}vs{m['away'][:4]}: 预测{m['choice']}({m['confidence']:.0f}%) 8变化{m['diff_8']:+d} 胜差{m['rate_diff']:+.0f}%({status}){result} {is_correct}")

print("\n" + "=" * 80)
print("统计汇总")
print("=" * 80)
total = sum(c['total'] for c in categories.values())
correct = sum(c['correct'] for c in categories.values())
print(f"总场次: {total}")
print(f"命中场次: {correct}")
print(f"总命中率: {correct*100/total:.1f}%")
