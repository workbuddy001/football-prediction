# 置信度45%-55%区间比赛 - 按格式输出
import os
import re

def count_8_in_odds(odds_list):
    count = 0
    for odds in odds_list:
        for odd in odds:
            odd_str = f"{odd:.2f}"
            if odd_str.endswith('8'):
                count += 1
    return count

def analyze_match_from_file(file_path, actual_result=None, score=None):
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

        initial_8 = count_8_in_odds(initial_odds)
        realtime_8 = count_8_in_odds(realtime_odds)
        diff_8 = realtime_8 - initial_8

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
        'diff_8': diff_8,
        'actual': actual_result,
        'score': score
    }

# 实际结果和比分
results_data = {
    "周五008": {"result": "主胜", "score": "2-0"},
    "周六023": {"result": "客胜", "score": "0-1"},
    "周六005": {"result": "主胜", "score": "1-0"},
    "周日026": {"result": "主胜", "score": "1-0"},
    "周四001": {"result": "平局", "score": "2-2"},
    "周六010": {"result": "客胜", "score": "1-2"},
    "周六017": {"result": "平局", "score": "0-0"},
    "周六019": {"result": "主胜", "score": "2-1"},
    "周六021": {"result": "主胜", "score": "2-0"},
    "周六024": {"result": "平局", "score": "1-1"},
    "周日027": {"result": "主胜", "score": "3-1"},
    "周一006": {"result": "平局", "score": "1-1"},
    "周日014": {"result": "主胜", "score": "3-1"},
    "周一001": {"result": "客胜", "score": "0-2"},
    "周日019": {"result": "主胜", "score": "1-0"},
    "周五002": {"result": "平局", "score": "1-1"},
    "周日005": {"result": "主胜", "score": "2-1"},
    "周日020": {"result": "平局", "score": "0-0"},
    "周一002": {"result": "客胜", "score": "0-2"},
}

# 规律判断函数
def get_rule_and_recommend(m):
    diff_8 = m['diff_8']
    rate_diff = m['rate_diff']
    choice = m['choice']
    confidence = m['confidence']

    if diff_8 == -5:
        if abs(rate_diff) <= 20:
            return "规律2", "不推荐/防平"
        else:
            recommend = "主胜" if rate_diff > 0 else "客胜"
            return "规律1", recommend
    elif -5 < diff_8 <= -2:
        return "规律3", "平局"
    elif diff_8 > 0:
        if abs(rate_diff) > 20:
            recommend = "主胜" if rate_diff > 0 else "客胜"
            return "规律4", recommend
        else:
            return "规律5", "预测方打不出/观察"
    elif diff_8 == 0:
        return "无规律", "观察"
    else:  # diff_8 < -5 or diff_8 == -1
        return "其他", "观察"

print("=" * 100)
print("置信度45%-55%区间比赛 - 完整列表")
print("=" * 100)
print(f"{'比赛':<20} {'置信度':<8} {'8变化':<8} {'状态':<12} {'新规律判断':<12} {'推荐':<10} {'实际':<10} {'比分':<8}")
print("-" * 100)

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
            data = results_data.get(match_id, {})
            match = analyze_match_from_file(path, data.get('result'), data.get('score'))
            if match and 45 <= match['confidence'] < 55:
                all_matches.append(match)

# 排序：按规律优先级
def sort_key(m):
    rule, _ = get_rule_and_recommend(m)
    priority = {
        "规律1": 1,
        "规律2": 2,
        "规律3": 3,
        "规律4": 4,
        "规律5": 5,
        "无规律": 6,
        "其他": 7,
    }
    return priority.get(rule, 99)

all_matches.sort(key=sort_key)

for m in all_matches:
    match_name = f"{m['home'][:4]}vs{m['away'][:4]}"
    confidence = f"{m['confidence']:.0f}%"
    diff_8 = f"{m['diff_8']:+d}"

    # 状态判断
    if abs(m['rate_diff']) > 20:
        if m['rate_diff'] > 0:
            status = "主队极好"
        else:
            status = "客队极好"
    else:
        status = "焦灼"

    rule, recommend = get_rule_and_recommend(m)
    actual = m['actual'] if m['actual'] else "-"
    score = m['score'] if m['score'] else "-"

    # 预测是否正确
    is_correct = "对" if m['actual'] and m['choice'] == m['actual'] else ""

    print(f"{match_name:<20} {confidence:<8} {diff_8:<8} {status:<12} {rule:<12} {m['choice']:<10} {actual:<10} {score:<8} {is_correct}")

print("=" * 100)

# 统计
print("\n统计：")
print("-" * 60)
total = len(all_matches)
correct = sum(1 for m in all_matches if m['actual'] and m['choice'] == m['actual'])
print(f"总场次: {total}")
print(f"命中场次: {correct}")
print(f"总命中率: {correct*100/total:.1f}%")
