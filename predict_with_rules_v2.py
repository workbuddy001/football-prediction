"""
基于澳门心水 + 赔率变化 + 队伍状态的预测算法 v2

核心规律：
1. 澳门主胜 + 主胜降水30%-70% → 强推主胜
2. 澳门客胜 + 客胜降水0%-30% + 客队优势明显 → 强推客胜
3. 澳门客胜 + 客胜降水>=70% → 诱盘，反推主胜
4. 澳门主胜 + 主胜降水>=70% → 诱盘风险
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
    result = {'home_win_rate': 0, 'away_win_rate': 0}
    
    match = re.search(r'主队近况\s*\|\s*近10场[，,]\s*(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    if match:
        result['home_win_rate'] = int(match.group(4))
    
    match = re.search(r'客队近况\s*\|\s*近10场[，,]\s*(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    if match:
        result['away_win_rate'] = int(match.group(4))
    
    return result


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
    
    return {
        "home_up": home_up, "home_down": home_down,
        "away_up": away_up, "away_down": away_down,
        "total": total
    }


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


def get_status_type(status):
    diff = status['home_win_rate'] - status['away_win_rate']
    if diff >= 20:
        return "主优"
    elif diff >= 10:
        return "主较好"
    elif diff <= -20:
        return "客优"
    elif diff <= -10:
        return "客较好"
    else:
        return "均势"


def predict(match):
    home_team = match['home_team']
    away_team = match['away_team']
    macao_tip = match['macao_tip']
    status = match['status']
    stats = analyze_odds_change(match['initial_odds'], match['realtime_odds'])
    
    macao_dir = get_macao_direction(macao_tip, home_team, away_team)
    status_type = get_status_type(status)
    
    home_down_pct = stats['home_down'] / stats['total'] if stats['total'] > 0 else 0
    away_down_pct = stats['away_down'] / stats['total'] if stats['total'] > 0 else 0
    
    # 规则1: 澳门主胜 + 降水30%-70% → 强推主胜
    if macao_dir == "主胜" and 0.3 <= home_down_pct < 0.7:
        return "主胜", "强推", f"主降水{home_down_pct:.0%}"
    
    # 规则2: 澳门客胜 + 降水0%-30% + 客队优势明显 → 强推客胜
    if macao_dir == "客胜" and 0 <= away_down_pct < 0.3 and status_type in ["客较好", "客优"]:
        return "客胜", "强推", f"客降水{away_down_pct:.0%}+{status_type}"
    
    # 规则3: 澳门客胜 + 降水>=70% → 诱盘，反推主胜
    if macao_dir == "客胜" and away_down_pct >= 0.7:
        return "主胜", "诱盘反推", f"客降水{away_down_pct:.0%}"
    
    # 规则4: 澳门主胜 + 降水>=70% → 诱盘风险，防平
    if macao_dir == "主胜" and home_down_pct >= 0.7:
        return "防平", "诱盘风险", f"主降水{home_down_pct:.0%}"
    
    # 规则5: 澳门客胜 + 降水>=70% + 主队较好 → 反推主胜
    if macao_dir == "客胜" and away_down_pct >= 0.7 and status_type in ["主较好", "主优"]:
        return "主胜", "诱盘反推", f"客诱盘+主{status_type}"
    
    # 规则6: 澳门主胜 + 降水0%-30% + 主队优势 → 可推
    if macao_dir == "主胜" and 0 <= home_down_pct < 0.3 and status_type in ["主较好", "主优"]:
        return "主胜", "可推", f"主优{status_type}"
    
    # 规则7: 澳门客胜 + 降水30%-70% → 观望
    if macao_dir == "客胜" and 0.3 <= away_down_pct < 0.7:
        return "防平", "观望", f"客降水{away_down_pct:.0%}"
    
    # 规则8: 澳门主胜 + 降水0%-30% + 状态一般 → 观望
    if macao_dir == "主胜" and 0 <= home_down_pct < 0.3 and status_type in ["均势", "客较好", "客优"]:
        return "防平", "观望", f"主低水+{status_type}"
    
    return None


def run_prediction():
    days = ['3.12', '3.14', '3.15']
    
    all_matches = []
    for day in days:
        matches = load_match_data(day)
        all_matches.extend(matches)
    
    print("=" * 140)
    print("【基于澳门心水 + 赔率变化 + 队伍状态的预测结果 v2】")
    print("=" * 140)
    print(f"\n{'编号':<8} {'对阵':<20} {'澳门':<6} {'降水':<6} {'状态':<8} {'预测':<8} {'类型':<10} {'理由':<20} {'实际':<6} {'结果'}")
    print("-" * 140)
    
    results = {
        "强推": {"total": 0, "hit": 0},
        "诱盘反推": {"total": 0, "hit": 0},
        "可推": {"total": 0, "hit": 0},
        "观望": {"total": 0, "hit": 0},
    }
    
    valid_total = 0
    valid_hit = 0
    
    for match in all_matches:
        code = match['code']
        if code not in actual_results:
            continue
        
        actual = actual_results[code]
        macao_dir = get_macao_direction(match['macao_tip'], match['home_team'], match['away_team'])
        stats = analyze_odds_change(match['initial_odds'], match['realtime_odds'])
        status_type = get_status_type(match['status'])
        
        if macao_dir == "主胜":
            water = f"{stats['home_down']/stats['total']:.0%}"
        elif macao_dir == "客胜":
            water = f"{stats['away_down']/stats['total']:.0%}"
        else:
            water = "-"
        
        pred = predict(match)
        
        if pred is None:
            print(f"{code:<8} {match['home_team'][:5]}vs{match['away_team'][:6]:<8} {macao_dir:<6} {water:<6} {status_type:<8} {'待定':<8} {'--':<10} {'--':<20} {actual:<6} {'-'}")
            continue
        
        predict_result, predict_type, reason = pred
        
        if predict_result == "防平":
            hit = (actual == "和局")
        else:
            hit = (predict_result == actual)
        
        if predict_type in results:
            results[predict_type]["total"] += 1
            if hit:
                results[predict_type]["hit"] += 1
            valid_total += 1
            if hit:
                valid_hit += 1
        
        result_mark = "O" if hit else "X"
        
        print(f"{code:<8} {match['home_team'][:5]}vs{match['away_team'][:6]:<8} {macao_dir:<6} {water:<6} {status_type:<8} {predict_result:<8} {predict_type:<10} {reason:<20} {actual:<6} {result_mark}")
    
    print("=" * 140)
    print("\n【有效预测统计（排除待定）】")
    print("-" * 60)
    
    for ptype, data in results.items():
        if data["total"] > 0:
            rate = data["hit"] / data["total"]
            print(f"{ptype}: {data['total']}场, 打出{data['hit']}场, 命中率 {rate:.1%}")
    
    print("-" * 60)
    print(f"总计: {valid_total}场, 打出{valid_hit}场, 命中率 {valid_hit/valid_total:.1%}")


if __name__ == '__main__':
    run_prediction()
