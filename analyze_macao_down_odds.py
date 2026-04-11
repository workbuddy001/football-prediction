"""
统计：澳门心水推荐主胜或客胜，各大公司主胜或客胜大幅下降时，澳门心水能否打出
"""
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


def analyze_odds_change(initial_odds, realtime_odds):
    """统计赔率变化"""
    home_up_10 = home_down_10 = home_up = home_down = 0
    away_up_10 = away_down_10 = away_up = away_down = 0
    
    total = min(len(initial_odds), len(realtime_odds))
    
    for i in range(total):
        ih, id, ia = initial_odds[i]
        rh, rd, ra = realtime_odds[i]
        
        if ih > 0:
            pct = (rh - ih) / ih * 100
            if pct >= 10:
                home_up_10 += 1
                home_up += 1
            elif pct <= -10:
                home_down_10 += 1
                home_down += 1
            elif pct > 0:
                home_up += 1
            else:
                home_down += 1
        
        if ia > 0:
            pct = (ra - ia) / ia * 100
            if pct >= 10:
                away_up_10 += 1
                away_up += 1
            elif pct <= -10:
                away_down_10 += 1
                away_down += 1
            elif pct > 0:
                away_up += 1
            else:
                away_down += 1
    
    return {
        "home_up_10": home_up_10, "home_down_10": home_down_10,
        "home_up": home_up, "home_down": home_down,
        "away_up_10": away_up_10, "away_down_10": away_down_10,
        "away_up": away_up, "away_down": away_down,
        "total": total
    }


def load_match_data_from_folder(folder):
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
        
        matches.append({
            'code': code,
            'home_team': home_team,
            'away_team': away_team,
            'macao_tip': macao_tip,
            'home': home,
            'draw': draw,
            'away': away,
            'initial_odds': initial_odds,
            'realtime_odds': [(float(h), float(d), float(a)) for h, d, a in odds_match]
        })
    
    return matches


actual_results = {
    "周四001": "和局", "周四002": "和局", "周四003": "客胜", "周四004": "客胜",
    "周四005": "主胜", "周四006": "主胜", "周四007": "和局", "周四008": "主胜",
    "周四009": "主胜", "周四010": "客胜", "周四011": "和局", "周四012": "和局",
    "周六001": "和局", "周六002": "客胜", "周六003": "和局", "周六004": "客胜",
    "周六005": "主胜", "周六006": "主胜", "周六007": "和局", "周六008": "主胜",
    "周六009": "主胜", "周六010": "客胜", "周六011": "主胜", "周六012": "和局",
    "周六013": "和局", "周六014": "主胜", "周六015": "主胜", "周六016": "和局",
    "周六017": "和局", "周六018": "主胜", "周六019": "主胜", "周六020": "主胜",
    "周六021": "主胜", "周六022": "客胜", "周六023": "客胜", "周六024": "和局",
    "周六025": "主胜", "周六026": "客胜", "周六027": "客胜", "周六028": "客胜",
    "周六029": "和局", "周六030": "主胜", "周六031": "客胜", "周六032": "和局",
    "周日001": "主胜", "周日002": "主胜", "周日003": "客胜", "周日004": "和局",
    "周日005": "主胜", "周日006": "客胜", "周日007": "客胜", "周日008": "和局",
    "周日009": "主胜", "周日010": "主胜", "周日011": "主胜", "周日012": "和局",
    "周日013": "和局", "周日014": "主胜", "周日015": "主胜", "周日016": "客胜",
    "周日017": "客胜", "周日018": "主胜", "周日019": "主胜", "周日020": "和局",
    "周日021": "和局", "周日022": "客胜", "周日023": "主胜", "周日024": "和局",
    "周日025": "主胜", "周日026": "主胜", "周日027": "主胜", "周日028": "主胜",
    "周日029": "主胜",
}


def get_macao_direction(macao_tip, home_team, away_team):
    if home_team in macao_tip:
        return "主胜"
    if away_team in macao_tip:
        return "客胜"
    if "和局" in macao_tip or "平局" in macao_tip:
        return "和局"
    return "未知"


def run_analysis():
    days = ['3.12', '3.14', '3.15']
    
    all_matches = []
    for day in days:
        matches = load_match_data_from_folder(day)
        all_matches.extend(matches)
    
    all_macao_home = []
    all_macao_away = []
    
    for match in all_matches:
        code = match['code']
        home_team = match['home_team']
        away_team = match['away_team']
        macao_tip = match['macao_tip']
        
        if code not in actual_results:
            continue
        
        actual = actual_results[code]
        stats = analyze_odds_change(match['initial_odds'], match['realtime_odds'])
        
        macao_dir = get_macao_direction(macao_tip, home_team, away_team)
        
        home_down_pct = stats['home_down'] / stats['total'] if stats['total'] > 0 else 0
        away_down_pct = stats['away_down'] / stats['total'] if stats['total'] > 0 else 0
        home_down_10_pct = stats['home_down_10'] / stats['total'] if stats['total'] > 0 else 0
        away_down_10_pct = stats['away_down_10'] / stats['total'] if stats['total'] > 0 else 0
        
        if macao_dir == "主胜":
            all_macao_home.append({
                'code': code,
                'home_team': home_team,
                'away_team': away_team,
                'home': match['home'],
                'macao_dir': macao_dir,
                'home_down_pct': home_down_pct,
                'home_down_10_pct': home_down_10_pct,
                'actual': actual,
                'hit': actual == "主胜"
            })
        
        if macao_dir == "客胜":
            all_macao_away.append({
                'code': code,
                'home_team': home_team,
                'away_team': away_team,
                'away': match['away'],
                'macao_dir': macao_dir,
                'away_down_pct': away_down_pct,
                'away_down_10_pct': away_down_10_pct,
                'actual': actual,
                'hit': actual == "客胜"
            })
    
    print("=" * 80)
    print("【澳门推荐主胜 + 赔率下降趋势分析】")
    print("=" * 80)
    
    ranges = [
        (0, 0.3, "降幅0-30%"),
        (0.3, 0.5, "降幅30-50%"),
        (0.5, 0.7, "降幅50-70%"),
        (0.7, 1.0, "降幅>=70%")
    ]
    
    print("\n按主胜降(任意幅度)占比分段:")
    for low, high, label in ranges:
        matches = [m for m in all_macao_home if low <= m['home_down_pct'] < high]
        if matches:
            hits = sum(1 for m in matches if m['hit'])
            print(f"  {label}: {len(matches)}场, 打出{hits}场 ({hits/len(matches):.1%})")
    
    print("\n按主胜大幅下降(>=10%)占比分段:")
    for low, high, label in ranges:
        matches = [m for m in all_macao_home if low <= m['home_down_10_pct'] < high]
        if matches:
            hits = sum(1 for m in matches if m['hit'])
            print(f"  {label}: {len(matches)}场, 打出{hits}场 ({hits/len(matches):.1%})")
    
    print("\n" + "=" * 80)
    print("【澳门推荐客胜 + 赔率下降趋势分析】")
    print("=" * 80)
    
    print("\n按客胜降(任意幅度)占比分段:")
    for low, high, label in ranges:
        matches = [m for m in all_macao_away if low <= m['away_down_pct'] < high]
        if matches:
            hits = sum(1 for m in matches if m['hit'])
            print(f"  {label}: {len(matches)}场, 打出{hits}场 ({hits/len(matches):.1%})")
    
    print("\n按客胜大幅下降(>=10%)占比分段:")
    for low, high, label in ranges:
        matches = [m for m in all_macao_away if low <= m['away_down_10_pct'] < high]
        if matches:
            hits = sum(1 for m in matches if m['hit'])
            print(f"  {label}: {len(matches)}场, 打出{hits}场 ({hits/len(matches):.1%})")
    
    # 打印符合条件的比赛详情
    print("\n" + "=" * 80)
    print("【详细比赛列表：澳门推荐主胜 + 主胜降>=30%公司】")
    print("=" * 80)
    
    for m in all_macao_home:
        if m['home_down_pct'] >= 0.3:
            print(f"{m['code']}: {m['home_team']} vs {m['away_team']}, 主胜{m['home']:.2f}, 降{m['home_down_pct']:.1%}, 实际{m['actual']}, {'O' if m['hit'] else 'X'}")
    
    print("\n【详细比赛列表：澳门推荐客胜 + 客胜降>=30%公司】")
    print("=" * 80)
    
    for m in all_macao_away:
        if m['away_down_pct'] >= 0.3:
            print(f"{m['code']}: {m['home_team']} vs {m['away_team']}, 客胜{m['away']:.2f}, 降{m['away_down_pct']:.1%}, 实际{m['actual']}, {'O' if m['hit'] else 'X'}")


if __name__ == '__main__':
    run_analysis()
