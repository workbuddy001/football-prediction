# V6算法完整测试 - 3.12~3.15所有比赛
import os
import re

def get_distribution(home, draw, away):
    if home < away and home < 2.0:
        if away - home > 0.5:
            return "顺分布"
        elif away - home > 0.2:
            return "缓冲分布"
        else:
            return "中庸分布"
    elif away < home and away < 2.0:
        if home - away > 0.5:
            return "逆分布"
        elif home - away > 0.2:
            return "缓冲分布"
        else:
            return "中庸分布"
    else:
        return "中庸分布"


def analyze_odds_change_30(initial_odds, realtime_odds):
    home_up_10 = home_down_10 = 0
    draw_up_10 = draw_down_10 = 0
    away_up_10 = away_down_10 = 0
    home_up = home_down = 0
    draw_up = draw_down = 0
    away_up = away_down = 0
    
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
        
        if id > 0:
            pct = (rd - id) / id * 100
            if pct >= 10:
                draw_up_10 += 1
                draw_up += 1
            elif pct <= -10:
                draw_down_10 += 1
                draw_down += 1
            elif pct > 0:
                draw_up += 1
            else:
                draw_down += 1
        
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
        "draw_up_10": draw_up_10, "draw_down_10": draw_down_10,
        "away_up_10": away_up_10, "away_down_10": away_down_10,
        "home_up": home_up, "home_down": home_down,
        "draw_up": draw_up, "draw_down": draw_down,
        "away_up": away_up, "away_down": away_down,
        "total": total
    }


def analyze_draw_trend(stats):
    draw_up = stats["draw_up"]
    draw_down = stats["draw_down"]
    draw_up_10 = stats["draw_up_10"]
    total = stats["total"]
    
    up_ratio = draw_up / total if total > 0 else 0
    down_ratio = draw_down / total if total > 0 else 0
    up_10_ratio = draw_up_10 / total if total > 0 else 0
    
    if up_ratio >= 0.7 and up_10_ratio >= 0.5:
        return "up_high", "排除平局"
    if up_ratio >= 0.7:
        return "up_high", "排除平局"
    if up_10_ratio >= 0.6:
        return "up_high", "排除平局"
    if down_ratio >= 0.5:
        return "down", "防平"
    if draw_up > 0 and draw_down > 0 and abs(up_ratio - down_ratio) < 0.2:
        return "neutral", "排除平局"
    
    return "neutral", "可博平局"


def judge_real_or_trap(macao_tip, home_team, away_team, home, draw, away, stats):
    total = stats["total"]
    draw_trend, draw_tip = analyze_draw_trend(stats)
    
    # 澳门推荐：包含主队名=推荐主胜，包含客队名=推荐客胜，包含和局=推荐和局
    macao_home = home_team in macao_tip  # 直接用球队名匹配
    macao_away = away_team in macao_tip
    macao_draw = "和局" in macao_tip
    
    if macao_home:
        if draw_trend == "up_high":
            if away < home + 0.3:
                return "诱盘", "客胜"
            else:
                return "诱盘", "主胜"
        elif draw_trend == "down":
            if stats["home_up_10"] >= stats["total"] * 0.3:
                return "诱盘", "防平"
            elif stats["home_down_10"] >= stats["total"] * 0.3:
                return "实盘", "主胜"
            else:
                return "待定", "防平"
        
        if stats["home_up_10"] >= stats["total"] * 0.3:
            return "诱盘", "防平"
        elif stats["home_down_10"] >= stats["total"] * 0.3:
            return "实盘", "主胜"
        elif stats["home_up"] > stats["home_down"]:
            return "诱盘", "防平"
        else:
            return "实盘", "主胜"
    
    elif macao_away:
        if draw_trend == "up_high":
            if home < away + 0.3:
                return "诱盘", "主胜"
            else:
                return "诱盘", "客胜"
        elif draw_trend == "down":
            if stats["away_up_10"] >= stats["total"] * 0.3:
                return "诱盘", "防平"
            elif stats["away_down_10"] >= stats["total"] * 0.3:
                return "实盘", "客胜"
            else:
                return "待定", "防平"
        
        if stats["away_up_10"] >= stats["total"] * 0.3:
            return "诱盘", "防平"
        elif stats["away_down_10"] >= stats["total"] * 0.3:
            return "实盘", "客胜"
        elif stats["away_up"] > stats["away_down"]:
            return "诱盘", "防平"
        else:
            return "实盘", "客胜"
    
    elif macao_draw:
        if draw_trend == "up_high":
            return "待定", "防平"
        elif draw_trend == "down":
            return "待定", "防平"
        else:
            return "实盘", "和局"
    
    else:
        if draw_trend == "up_high":
            dist = get_distribution(home, draw, away)
            if dist == "顺分布":
                return "待定", "主胜"
            elif dist == "逆分布":
                return "待定", "客胜"
            else:
                return "待定", "主胜" if home < away else "待定", "客胜"
        
        elif draw_trend == "down":
            return "待定", "防平"
        
        else:
            dist = get_distribution(home, draw, away)
            if dist == "顺分布":
                if home < 1.8:
                    return "实盘", "主胜"
                else:
                    return "待定", "防平"
            elif dist == "逆分布":
                if away < 1.8:
                    return "实盘", "客胜"
                else:
                    return "待定", "防平"
            else:
                if draw < 3.3 and stats["draw_up"] > stats["draw_down"]:
                    return "实盘", "和局"
                return "待定", "防平"


def extract_odds_block(content, keyword):
    """提取赔率块"""
    start = content.find(keyword)
    if start < 0:
        return ""
    end = content.find('```', start)
    if end < 0:
        end = len(content)
    return content[start:end]


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
        
        # 提取澳门推荐
        macao_match = re.search(r'澳门推荐\s*\|\s*(\S+)', content)
        if not macao_match:
            macao_match = re.search(r'澳门推荐[:：]\s*(.+)', content)
        macao_tip = macao_match.group(1).strip() if macao_match else ""
        
        # 提取realtime_odds
        rt_block = extract_odds_block(content, 'realtime_odds')
        odds_match = re.findall(r'\(\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*\)', rt_block)
        
        if not odds_match:
            continue
        
        home, draw, away = float(odds_match[0][0]), float(odds_match[0][1]), float(odds_match[0][2])
        
        # 提取initial_odds
        init_block = extract_odds_block(content, 'initial_odds')
        init_odds = re.findall(r'\(\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*\)', init_block)
        initial_odds = [(float(h), float(d), float(a)) for h, d, a in init_odds] if init_odds else odds_match
        
        # 球队名
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


# 实际结果
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


def run_test():
    days = ['3.12', '3.14', '3.15']
    
    all_matches = []
    for day in days:
        matches = load_match_data_from_folder(day)
        all_matches.extend(matches)
        print(f"{day}: 加载 {len(matches)} 场")
    
    print(f"\n总共: {len(all_matches)} 场")
    
    results = []
    for m in all_matches:
        code = m['code']
        if code not in actual_results:
            continue
            
        stats = analyze_odds_change_30(m['initial_odds'], m['realtime_odds'])
        trap_type, prediction = judge_real_or_trap(
            m['macao_tip'], m['home_team'], m['away_team'],
            m['home'], m['draw'], m['away'], stats
        )
        
        actual = actual_results.get(code, "")
        hit = (prediction == actual)
        
        results.append({
            'code': code,
            'home': m['home_team'][:6],
            'away': m['away_team'][:6],
            'macao': m['macao_tip'][:10] if m['macao_tip'] else "无",
            'prediction': prediction,
            'actual': actual,
            'hit': hit,
            'type': trap_type
        })
    
    # 统计
    total = len(results)
    hit_count = sum(1 for r in results if r['hit'])
    
    print()
    print("=" * 90)
    print(f"{'编号':<8} {'主队':<6} {'客队':<6} {'澳门推荐':<10} {'预测':<8} {'实际':<8} {'结果'}")
    print("-" * 90)
    
    for r in results:
        status = "OK" if r['hit'] else "X"
        print(f"{r['code']:<8} {r['home']:<6} {r['away']:<6} {r['macao']:<10} {r['prediction']:<8} {r['actual']:<8} {status}")
    
    print()
    print("=" * 90)
    print("统计结果:")
    print("-" * 40)
    print(f"总比赛数: {total}")
    print(f"命中: {hit_count}")
    print(f"准确率: {hit_count/total*100:.1f}%")
    
    # 按澳门推荐分类
    print()
    print("按澳门推荐分类:")
    print("-" * 40)
    
    macao_types = {}
    for r in results:
        macao = r['macao']
        if macao not in macao_types:
            macao_types[macao] = {'total': 0, 'hit': 0}
        macao_types[macao]['total'] += 1
        if r['hit']:
            macao_types[macao]['hit'] += 1
    
    for macao, stat in sorted(macao_types.items(), key=lambda x: -x[1]['total'])[:10]:
        if stat['total'] >= 1:
            print(f"{macao}: {stat['hit']}/{stat['total']} = {stat['hit']/stat['total']*100:.1f}%")
    
    # 按预测类型分类
    print()
    print("按预测类型分类:")
    print("-" * 40)
    
    pred_types = {}
    for r in results:
        ptype = r['type']
        if ptype not in pred_types:
            pred_types[ptype] = {'total': 0, 'hit': 0}
        pred_types[ptype]['total'] += 1
        if r['hit']:
            pred_types[ptype]['hit'] += 1
    
    for ptype, stat in sorted(pred_types.items(), key=lambda x: -x[1]['total']):
        if stat['total'] >= 1:
            print(f"{ptype}: {stat['hit']}/{stat['total']} = {stat['hit']/stat['total']*100:.1f}%")


if __name__ == '__main__':
    run_test()
