"""
统计：澳门心水推荐主胜或客胜 + 赔率变化 + 队伍状态对比
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


def parse_team_status(content):
    """解析队伍状态信息"""
    result = {
        'home_record': '',  # 主队近况
        'away_record': '',  # 客队近况
        'home_trend': '',   # 主队走势
        'away_trend': '',   # 客队走势
        'head_to_head': '', # 历史交锋
        'home_win_rate': 0,
        'away_win_rate': 0,
    }
    
    # 主队近况 (支持表格格式 | 主队近况 | 近10场...)
    match = re.search(r'主队近况\s*\|\s*近10场[，,]\s*(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    if match:
        wins, draws, losses, win_rate = match.groups()
        result['home_record'] = f"{wins}胜{draws}平{losses}负"
        result['home_win_rate'] = int(win_rate)
    
    # 客队近况
    match = re.search(r'客队近况\s*\|\s*近10场[，,]\s*(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    if match:
        wins, draws, losses, win_rate = match.groups()
        result['away_record'] = f"{wins}胜{draws}平{losses}负"
        result['away_win_rate'] = int(win_rate)
    
    # 主队走势
    match = re.search(r'主队近况走势\s*\|\s*([WLWD]+)', content)
    if match:
        result['home_trend'] = match.group(1)
    
    # 客队走势
    match = re.search(r'客队近况走势\s*\|\s*([WLWD]+)', content)
    if match:
        result['away_trend'] = match.group(1)
    
    # 历史交锋
    match = re.search(r'历史交锋\s*\|\s*(.+)', content)
    if match:
        result['head_to_head'] = match.group(1).strip()
    
    return result


def analyze_odds_change(initial_odds, realtime_odds):
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
        
        # 澳门推荐
        macao_match = re.search(r'澳门推荐\s*\|\s*(\S+)', content)
        if not macao_match:
            macao_match = re.search(r'澳门推荐[:：]\s*(.+)', content)
        macao_tip = macao_match.group(1).strip() if macao_match else ""
        
        # 赔率
        rt_block = extract_odds_block(content, 'realtime_odds')
        odds_match = re.findall(r'\(\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*\)', rt_block)
        
        if not odds_match:
            continue
        
        home, draw, away = float(odds_match[0][0]), float(odds_match[0][1]), float(odds_match[0][2])
        
        init_block = extract_odds_block(content, 'initial_odds')
        init_odds = re.findall(r'\(\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*\)', init_block)
        initial_odds = [(float(h), float(d), float(a)) for h, d, a in init_odds] if init_odds else odds_match
        
        # 球队名
        teams = f.split('_')[1].split('vs')
        home_team = teams[0].strip()
        away_team = teams[1].replace('_源数据', '').strip()
        code = f.split('_')[0]
        
        # 队伍状态
        status = parse_team_status(content)
        
        matches.append({
            'code': code,
            'home_team': home_team,
            'away_team': away_team,
            'macao_tip': macao_tip,
            'home': home,
            'draw': draw,
            'away': away,
            'initial_odds': initial_odds,
            'realtime_odds': [(float(h), float(d), float(a)) for h, d, a in odds_match],
            'status': status
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


def get_status_compare(status):
    """比较两队状态"""
    diff = status['home_win_rate'] - status['away_win_rate']
    if diff >= 20:
        return "主队优势明显"
    elif diff >= 10:
        return "主队较好"
    elif diff <= -20:
        return "客队优势明显"
    elif diff <= -10:
        return "客队较好"
    else:
        return "势均力敌"


def run_analysis():
    days = ['3.12', '3.14', '3.15']
    
    all_matches = []
    for day in days:
        matches = load_match_data_from_folder(day)
        all_matches.extend(matches)
    
    print(f"共加载 {len(all_matches)} 场比赛\n")
    
    # 收集数据
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
        status = match['status']
        
        macao_dir = get_macao_direction(macao_tip, home_team, away_team)
        
        home_down_pct = stats['home_down'] / stats['total'] if stats['total'] > 0 else 0
        away_down_pct = stats['away_down'] / stats['total'] if stats['total'] > 0 else 0
        home_up_pct = stats['home_up'] / stats['total'] if stats['total'] > 0 else 0
        away_up_pct = stats['away_up'] / stats['total'] if stats['total'] > 0 else 0
        
        if macao_dir == "主胜":
            all_macao_home.append({
                'code': code,
                'home_team': home_team,
                'away_team': away_team,
                'home': match['home'],
                'home_down_pct': home_down_pct,
                'home_up_pct': home_up_pct,
                'status': status,
                'status_compare': get_status_compare(status),
                'actual': actual,
                'hit': actual == "主胜"
            })
        
        if macao_dir == "客胜":
            all_macao_away.append({
                'code': code,
                'home_team': home_team,
                'away_team': away_team,
                'away': match['away'],
                'away_down_pct': away_down_pct,
                'away_up_pct': away_up_pct,
                'status': status,
                'status_compare': get_status_compare(status),
                'actual': actual,
                'hit': actual == "客胜"
            })
    
    # 输出澳门推荐主胜 + 降水情况
    print("=" * 120)
    print("【澳门推荐主胜 + 主胜降水 + 队伍状态对比】")
    print("=" * 120)
    
    # 按状态分类
    for status_type in ["主队优势明显", "主队较好", "势均力敌", "客队较好", "客队优势明显"]:
        matches = [m for m in all_macao_home if m['status_compare'] == status_type]
        if not matches:
            continue
        
        print(f"\n--- {status_type} ({len(matches)}场) ---")
        print(f"{'编号':<8} {'对阵':<20} {'主胜':<5} {'降水%':<8} {'主队近况':<12} {'客队近况':<12} {'实际':<6} {'结果'}")
        
        for m in matches:
            home_rec = m['status']['home_record']
            away_rec = m['status']['away_record']
            print(f"{m['code']:<8} {m['home_team'][:6]}vs{m['away_team'][:6]:<10} {m['home']:<5.2f} {m['home_down_pct']:<8.0%} {home_rec:<12} {away_rec:<12} {m['actual']:<6} {'O' if m['hit'] else 'X'}")
    
    # 按降水幅度分段统计
    print("\n" + "=" * 120)
    print("【澳门主胜 + 降水幅度 vs 状态对比 命中率统计】")
    print("=" * 120)
    
    ranges = [(0, 0.3, "0-30%"), (0.3, 0.5, "30-50%"), (0.5, 0.7, "50-70%"), (0.7, 1.0, ">=70%")]
    
    for low, high, label in ranges:
        matches = [m for m in all_macao_home if low <= m['home_down_pct'] < high]
        if not matches:
            continue
        
        print(f"\n主胜降水{label} ({len(matches)}场):")
        for status_type in ["主队优势明显", "主队较好", "势均力敌", "客队较好", "客队优势明显"]:
            sub = [m for m in matches if m['status_compare'] == status_type]
            if sub:
                hits = sum(1 for m in sub if m['hit'])
                print(f"  {status_type}: {len(sub)}场, 打出{hits}场 ({hits/len(sub):.0%})")
    
    # 输出澳门推荐客胜 + 降水情况
    print("\n" + "=" * 120)
    print("【澳门推荐客胜 + 客胜降水 + 队伍状态对比】")
    print("=" * 120)
    
    for status_type in ["客队优势明显", "客队较好", "势均力敌", "主队较好", "主队优势明显"]:
        matches = [m for m in all_macao_away if m['status_compare'] == status_type]
        if not matches:
            continue
        
        print(f"\n--- {status_type} ({len(matches)}场) ---")
        print(f"{'编号':<8} {'对阵':<20} {'客胜':<5} {'降水%':<8} {'主队近况':<12} {'客队近况':<12} {'实际':<6} {'结果'}")
        
        for m in matches:
            home_rec = m['status']['home_record']
            away_rec = m['status']['away_record']
            print(f"{m['code']:<8} {m['home_team'][:6]}vs{m['away_team'][:6]:<10} {m['away']:<5.2f} {m['away_down_pct']:<8.0%} {home_rec:<12} {away_rec:<12} {m['actual']:<6} {'O' if m['hit'] else 'X'}")
    
    print("\n" + "=" * 120)
    print("【澳门客胜 + 降水幅度 vs 状态对比 命中率统计】")
    print("=" * 120)
    
    for low, high, label in ranges:
        matches = [m for m in all_macao_away if low <= m['away_down_pct'] < high]
        if not matches:
            continue
        
        print(f"\n客胜降水{label} ({len(matches)}场):")
        for status_type in ["客队优势明显", "客队较好", "势均力敌", "主队较好", "主队优势明显"]:
            sub = [m for m in matches if m['status_compare'] == status_type]
            if sub:
                hits = sum(1 for m in sub if m['hit'])
                print(f"  {status_type}: {len(sub)}场, 打出{hits}场 ({hits/len(sub):.0%})")


if __name__ == '__main__':
    run_analysis()
