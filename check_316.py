"""检测3.16强推比赛"""
import os
import re


def extract_odds_block(content, keyword):
    start = content.find(keyword)
    if start < 0:
        return ""
    end = content.find('```', start)
    if end < 0:
        end = len(content)
    return content[start:end]


def parse_team_status(content):
    result = {'home_win_rate': 0, 'away_win_rate': 0, 'home_trend': '', 'away_trend': ''}
    
    match = re.search(r'主队近况\s*\|\s*近10场[，,]\s*(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    if match:
        result['home_win_rate'] = int(match.group(4))
    
    match = re.search(r'客队近况\s*\|\s*近10场[，,]\s*(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    if match:
        result['away_win_rate'] = int(match.group(4))
    
    match = re.search(r'主队近况走势\s*\|\s*([WLWD]+)', content)
    if match:
        result['home_trend'] = match.group(1)
    
    match = re.search(r'客队近况走势\s*\|\s*([WLWD]+)', content)
    if match:
        result['away_trend'] = match.group(1)
    
    return result


def analyze_trend(trend):
    if not trend:
        return "未知", 0
    wins = trend.count('W')
    losses = trend.count('L')
    last_char = trend[-1] if trend else ''
    streak = 0
    for c in reversed(trend):
        if c == last_char:
            streak += 1
        else:
            break
    
    if wins >= 7:
        return "连胜", wins
    elif losses >= 7:
        return "连败", losses
    elif wins >= 5 and wins > losses:
        return "较好", wins
    elif losses >= 5 and losses > wins:
        return "较差", losses
    elif last_char == 'W' and streak >= 3:
        return "回升", streak
    elif last_char == 'L' and streak >= 3:
        return "低迷", streak
    else:
        return "平稳", 0


def get_status_type(status):
    diff = status['home_win_rate'] - status['away_win_rate']
    home_trend_type, _ = analyze_trend(status['home_trend'])
    away_trend_type, _ = analyze_trend(status['away_trend'])
    
    if diff >= 20:
        adv = "主优"
    elif diff >= 10:
        adv = "主较好"
    elif diff <= -20:
        adv = "客优"
    elif diff <= -10:
        adv = "客较好"
    else:
        adv = "均势"
    
    if home_trend_type in ["连胜", "回升"] and away_trend_type in ["连败", "低迷"]:
        trend = "主回升客低迷"
    elif home_trend_type in ["连败", "低迷"] and away_trend_type in ["连胜", "回升"]:
        trend = "主低迷客回升"
    elif home_trend_type in ["连胜", "回升"]:
        trend = "主走势好"
    elif away_trend_type in ["连胜", "回升"]:
        trend = "客走势好"
    else:
        trend = "平稳"
    
    return adv, trend


def analyze_odds_change(initial_odds, realtime_odds):
    home_up = home_down = 0
    away_up = away_down = 0
    total = min(len(initial_odds), len(realtime_odds))
    
    for i in range(total):
        ih, id, ia = initial_odds[i]
        rh, rd, ra = realtime_odds[i]
        
        if ih > 0:
            if rh < ih:
                home_down += 1
            else:
                home_up += 1
        if ia > 0:
            if ra < ia:
                away_down += 1
            else:
                away_up += 1
    
    return {"home_up": home_up, "home_down": home_down, "away_up": away_up, "away_down": away_down, "total": total}


def load_match_data(folder):
    matches = []
    base = f'分析模板/{folder}'
    
    if not os.path.exists(base):
        return matches
    
    for f in sorted(os.listdir(base)):
        if '源数据' not in f:
            continue
        
        filepath = f'{base}/{f}'
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
        
        macao_match = re.search(r'澳门推荐\s*\|\s*(\S+)', content)
        if not macao_match:
            macao_match = re.search(r'澳门推荐[:：]\s*(.+)', content)
        macao_tip = macao_match.group(1).strip() if macao_match else ""
        
        rt_block = extract_odds_block(content, 'realtime_odds')
        odds_match = re.findall(r'\(\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*\)', rt_block)
        
        if not odds_match:
            continue
        
        home, draw, away = float(odds_match[0][0]), float(odds_match[0][1]), float(odds_match[0][2])
        
        init_block = extract_odds_block(content, 'initial_odds')
        init_odds = re.findall(r'\(\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*\)', init_block)
        initial_odds = [(float(h), float(d), float(a)) for h, d, a in init_odds] if init_odds else odds_match
        
        teams = f.split('_')[1].split('vs')
        home_team = teams[0].strip()
        away_team = teams[1].replace('_源数据', '').strip()
        code = f.split('_')[0]
        
        status = parse_team_status(content)
        
        matches.append({
            'code': code,
            'home_team': home_team,
            'away_team': away_team,
            'macao_tip': macao_tip,
            'home': home,
            'away': away,
            'initial_odds': initial_odds,
            'realtime_odds': [(float(h), float(d), float(a)) for h, d, a in odds_match],
            'status': status
        })
    
    return matches


def get_macao_direction(macao_tip, home_team, away_team):
    if home_team in macao_tip:
        return "主胜"
    if away_team in macao_tip:
        return "客胜"
    if "和局" in macao_tip or "平局" in macao_tip:
        return "和局"
    return "未知"


def check_strong_predict(match):
    """检测是否符合强推条件"""
    home_team = match['home_team']
    away_team = match['away_team']
    macao_tip = match['macao_tip']
    status = match['status']
    stats = analyze_odds_change(match['initial_odds'], match['realtime_odds'])
    
    macao_dir = get_macao_direction(macao_tip, home_team, away_team)
    adv, trend = get_status_type(status)
    
    home_down_pct = stats['home_down'] / stats['total'] if stats['total'] > 0 else 0
    away_down_pct = stats['away_down'] / stats['total'] if stats['total'] > 0 else 0
    
    reasons = []
    
    # 主胜强推条件
    if macao_dir == "主胜":
        if 0.3 <= home_down_pct < 0.7 and adv in ["主优", "主较好"]:
            reasons.append(f"强推: 主降水{home_down_pct:.0%}+{adv}")
        if 0.3 <= home_down_pct < 0.7 and "主走势好" in trend:
            reasons.append(f"强推: 主降水{home_down_pct:.0%}+{trend}")
    
    # 客胜强推条件
    elif macao_dir == "客胜":
        if 0 <= away_down_pct < 0.3 and adv in ["客优", "客较好"]:
            reasons.append(f"强推: 客降水{away_down_pct:.0%}+{adv}")
        if 0 <= away_down_pct < 0.3 and "客走势好" in trend:
            reasons.append(f"强推: 客降水{away_down_pct:.0%}+{trend}")
    
    return reasons


def check_other_predict(match):
    """检测其他可推条件"""
    home_team = match['home_team']
    away_team = match['away_team']
    macao_tip = match['macao_tip']
    status = match['status']
    stats = analyze_odds_change(match['initial_odds'], match['realtime_odds'])
    
    macao_dir = get_macao_direction(macao_tip, home_team, away_team)
    adv, trend = get_status_type(status)
    
    home_down_pct = stats['home_down'] / stats['total'] if stats['total'] > 0 else 0
    away_down_pct = stats['away_down'] / stats['total'] if stats['total'] > 0 else 0
    
    reasons = []
    
    if macao_dir == "主胜":
        if home_down_pct >= 0.7:
            reasons.append(f"诱盘风险: 主降水{home_down_pct:.0%}过高，防平")
        if home_down_pct < 0.3 and adv == "主优":
            reasons.append(f"可推: 低水+{adv}")
        if home_down_pct < 0.3 and "回升" in trend:
            reasons.append(f"可推: 低水+{trend}")
    
    elif macao_dir == "客胜":
        if away_down_pct >= 0.7:
            reasons.append(f"诱盘反推: 客降水{away_down_pct:.0%}，推主胜")
        if 0.3 <= away_down_pct < 0.7:
            reasons.append(f"观望: 客降水{away_down_pct:.0%}")
    
    return reasons


matches = load_match_data('3.16')

print("=" * 120)
print("【3.16 比赛分析】")
print("=" * 120)
print(f"\n{'编号':<8} {'对阵':<24} {'澳门':<6} {'主胜':<6} {'客胜':<6} {'主降水%':<8} {'客降水%':<8} {'优势':<8} {'走势':<12}")
print("-" * 120)

strong_count = 0
other_count = 0

for m in matches:
    code = m['code']
    home_team = m['home_team']
    away_team = m['away_team']
    macao_tip = m['macao_tip']
    macao_dir = get_macao_direction(macao_tip, home_team, away_team)
    stats = analyze_odds_change(m['initial_odds'], m['realtime_odds'])
    adv, trend = get_status_type(m['status'])
    
    home_water = f"{stats['home_down']/stats['total']:.0%}"
    away_water = f"{stats['away_down']/stats['total']:.0%}"
    
    print(f"{code:<8} {home_team[:6]}vs{away_team[:8]:<12} {macao_dir:<6} {m['home']:<6.2f} {m['away']:<6.2f} {home_water:<8} {away_water:<8} {adv:<8} {trend:<12}")

print("\n" + "=" * 120)
print("【强推检测结果】")
print("=" * 120)

for m in matches:
    code = m['code']
    home_team = m['home_team']
    away_team = m['away_team']
    macao_tip = m['macao_tip']
    macao_dir = get_macao_direction(macao_tip, home_team, away_team)
    stats = analyze_odds_change(m['initial_odds'], m['realtime_odds'])
    adv, trend = get_status_type(m['status'])
    
    home_water = stats['home_down']/stats['total']
    away_water = stats['away_down']/stats['total']
    
    strong_reasons = check_strong_predict(m)
    other_reasons = check_other_predict(m)
    
    if strong_reasons:
        strong_count += 1
        print(f"\n*** {code} {home_team} vs {away_team} ***")
        print(f"    澳门推荐: {macao_dir}")
        print(f"    主胜: {m['home']:.2f}, 客胜: {m['away']:.2f}")
        print(f"    主降水: {home_water:.0%}, 客降水: {away_water:.0%}")
        print(f"    状态: {adv}, {trend}")
        for r in strong_reasons:
            print(f"    >>> {r}")
    
    if other_reasons:
        other_count += 1

print("\n" + "=" * 120)
print(f"【总结】强推: {strong_count}场, 其他信号: {other_count}场")
print("=" * 120)
