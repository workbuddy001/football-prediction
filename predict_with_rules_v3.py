"""
基于澳门心水 + 赔率变化 + 队伍状态的预测算法 v3

加入更细致的队伍状态判断：
1. 胜率差（优势程度）
2. 近期走势（连胜/连败/起伏）
3. 历史交锋
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
    result = {
        'home_win_rate': 0, 'away_win_rate': 0,
        'home_trend': '', 'away_trend': '',
        'head_to_head': ''
    }
    
    # 胜率
    match = re.search(r'主队近况\s*\|\s*近10场[，,]\s*(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    if match:
        result['home_win_rate'] = int(match.group(4))
    
    match = re.search(r'客队近况\s*\|\s*近10场[，,]\s*(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    if match:
        result['away_win_rate'] = int(match.group(4))
    
    # 走势
    match = re.search(r'主队近况走势\s*\|\s*([WLWD]+)', content)
    if match:
        result['home_trend'] = match.group(1)
    
    match = re.search(r'客队近况走势\s*\|\s*([WLWD]+)', content)
    if match:
        result['away_trend'] = match.group(1)
    
    # 交锋
    match = re.search(r'历史交锋\s*\|\s*(.+)', content)
    if match:
        result['head_to_head'] = match.group(1).strip()
    
    return result


def analyze_trend(trend):
    """分析走势：返回 (类型, 连胜/连败数)"""
    if not trend:
        return "未知", 0
    
    # 统计W和L的数量
    wins = trend.count('W')
    losses = trend.count('L')
    draws = trend.count('D')
    
    # 检查末尾连续相同结果
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
    """综合判断状态"""
    diff = status['home_win_rate'] - status['away_win_rate']
    home_trend_type, home_trend_val = analyze_trend(status['home_trend'])
    away_trend_type, away_trend_val = analyze_trend(status['away_trend'])
    
    # 优势判断
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
    
    # 走势判断
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


def predict(match):
    home_team = match['home_team']
    away_team = match['away_team']
    macao_tip = match['macao_tip']
    status = match['status']
    stats = analyze_odds_change(match['initial_odds'], match['realtime_odds'])
    
    macao_dir = get_macao_direction(macao_tip, home_team, away_team)
    adv, trend = get_status_type(status)
    
    home_down_pct = stats['home_down'] / stats['total'] if stats['total'] > 0 else 0
    away_down_pct = stats['away_down'] / stats['total'] if stats['total'] > 0 else 0
    
    # ===== 主胜推荐 =====
    if macao_dir == "主胜":
        # 规则1: 降水30%-70% + 主队优势 → 强推
        if 0.3 <= home_down_pct < 0.7 and adv in ["主优", "主较好"]:
            return "主胜", "强推", f"降水{home_down_pct:.0%}+{adv}"
        
        # 规则2: 降水30%-70% + 走势好 → 强推
        if 0.3 <= home_down_pct < 0.7 and "主走势好" in trend:
            return "主胜", "强推", f"降水{home_down_pct:.0%}+{trend}"
        
        # 规则3: 降水>=70% → 诱盘风险
        if home_down_pct >= 0.7:
            return "防平", "诱盘风险", f"降水{home_down_pct:.0%}"
        
        # 规则4: 降水<30% + 主队优势明显 → 可推
        if home_down_pct < 0.3 and adv == "主优":
            return "主胜", "可推", f"低水+{adv}"
        
        # 规则5: 降水<30% + 走势回升 → 可推
        if home_down_pct < 0.3 and "回升" in trend:
            return "主胜", "可推", f"低水+{trend}"
        
        # 规则6: 降水<30% + 客队优势 → 观望
        if home_down_pct < 0.3 and adv in ["客优", "客较好"]:
            return "防平", "观望", f"低水+客队{adv}"
        
        # 规则7: 降水<30% + 均势 → 观望
        if home_down_pct < 0.3 and adv == "均势":
            return "防平", "观望", f"低水+均势"
    
    # ===== 客胜推荐 =====
    elif macao_dir == "客胜":
        # 规则1: 客胜降水>=70% → 诱盘，反推主胜
        if away_down_pct >= 0.7:
            return "主胜", "诱盘反推", f"客降水{away_down_pct:.0%}"
        
        # 规则2: 降水0%-30% + 客队优势 → 强推
        if 0 <= away_down_pct < 0.3 and adv in ["客优", "客较好"]:
            return "客胜", "强推", f"客降水{away_down_pct:.0%}+{adv}"
        
        # 规则3: 降水0%-30% + 客走势好 → 强推
        if 0 <= away_down_pct < 0.3 and "客走势好" in trend:
            return "客胜", "强推", f"客降水{away_down_pct:.0%}+{trend}"
        
        # 规则4: 降水30%-70% → 观望
        if 0.3 <= away_down_pct < 0.7:
            return "防平", "观望", f"客降水{away_down_pct:.0%}"
        
        # 规则5: 降水<30% + 主队优势 → 反推
        if away_down_pct < 0.3 and adv in ["主优", "主较好"]:
            return "主胜", "反推", f"客低水+主队{adv}"
    
    return None


def run_prediction():
    days = ['3.12', '3.14', '3.15']
    
    all_matches = []
    for day in days:
        matches = load_match_data(day)
        all_matches.extend(matches)
    
    print("=" * 150)
    print("【基于澳门心水 + 赔率变化 + 队伍状态 v3】")
    print("=" * 150)
    print(f"\n{'编号':<8} {'对阵':<18} {'澳门':<4} {'降水':<6} {'优势':<8} {'走势':<14} {'预测':<8} {'类型':<10} {'理由':<20} {'实际':<6} {'结果'}")
    print("-" * 150)
    
    results = {
        "强推": {"total": 0, "hit": 0},
        "诱盘反推": {"total": 0, "hit": 0},
        "反推": {"total": 0, "hit": 0},
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
        adv, trend = get_status_type(match['status'])
        
        if macao_dir == "主胜":
            water = f"{stats['home_down']/stats['total']:.0%}"
        elif macao_dir == "客胜":
            water = f"{stats['away_down']/stats['total']:.0%}"
        else:
            water = "-"
        
        pred = predict(match)
        
        if pred is None:
            print(f"{code:<8} {match['home_team'][:5]}vs{match['away_team'][:5]:<8} {macao_dir:<4} {water:<6} {adv:<8} {trend:<14} {'待定':<8} {'--':<10} {'--':<20} {actual:<6} {'-'}")
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
        
        print(f"{code:<8} {match['home_team'][:5]}vs{match['away_team'][:5]:<8} {macao_dir:<4} {water:<6} {adv:<8} {trend:<14} {predict_result:<8} {predict_type:<10} {reason:<20} {actual:<6} {result_mark}")
    
    print("=" * 150)
    print("\n【预测统计】")
    print("-" * 70)
    
    for ptype, data in results.items():
        if data["total"] > 0:
            rate = data["hit"] / data["total"]
            print(f"{ptype}: {data['total']}场, 打出{data['hit']}场, 命中率 {rate:.1%}")
    
    print("-" * 70)
    print(f"总计: {valid_total}场, 打出{valid_hit}场, 命中率 {valid_hit/valid_total:.1%}")


if __name__ == '__main__':
    run_prediction()
