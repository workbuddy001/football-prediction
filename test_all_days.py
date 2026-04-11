# V6算法测试 - 3.12~3.15所有比赛
import os
import re

def get_distribution(home, draw, away):
    """判断分布类型"""
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
    """统计30家公司赔率变化"""
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
    """分析平局趋势"""
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
    """判断实盘/诱盘"""
    total = stats["total"]
    draw_trend, draw_tip = analyze_draw_trend(stats)
    
    macao_home = home_team in macao_tip and ("赢" in macao_tip or "贏" in macao_tip)
    macao_away = away_team in macao_tip and ("赢" in macao_tip or "贏" in macao_tip)
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


def load_match_data(folder):
    """从文件夹加载比赛数据"""
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
        
        # 提取比赛编号和球队
        match_name = f.split('_')[1].replace('vs', 'vs')
        
        # 提取澳门心水
        macao_match = re.search(r'澳门心水[:：]\s*(.+)', content)
        macao_tip = macao_match.group(1).strip() if macao_match else ""
        
        # 提取即时赔率
        realtime_match = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if not realtime_match:
            continue
        
        # 提取第一组赔率作为即时赔率
        odds_str = realtime_match.group(1)
        odds_match = re.findall(r'\((\d+\.\d+),(\d+\.\d+),(\d+\.\d+)\)', odds_str)
        if not odds_match:
            continue
        
        # 取第一家公司
        home, draw, away = map(float, odds_match[0])
        
        # 提取初始赔率
        initial_match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
        initial_odds = []
        if initial_match:
            odds_str = initial_match.group(1)
            odds_list = re.findall(r'\((\d+\.\d+),(\d+\.\d+),(\d+\.\d+)\)', odds_str)
            initial_odds = [(float(h), float(d), float(a)) for h, d, a in odds_list]
        
        # 提取即时赔率列表
        realtime_odds = [(float(h), float(d), float(a)) for h, d, a in odds_match]
        
        # 球队名
        teams = f.split('_')[1].split('vs')
        home_team = teams[0].strip()
        away_team = teams[1].replace('_源数据', '').strip()
        
        matches.append({
            'code': f.split('_')[0],
            'home_team': home_team,
            'away_team': away_team,
            'macao_tip': macao_tip,
            'home': home,
            'draw': draw,
            'away': away,
            'initial_odds': initial_odds,
            'realtime_odds': realtime_odds
        })
    
    return matches


def run_test():
    """运行测试"""
    days = ['3.12', '3.13', '3.14', '3.15']
    
    all_matches = []
    for day in days:
        matches = load_match_data(day)
        all_matches.extend(matches)
    
    print(f"加载了 {len(all_matches)} 场比赛")
    print()
    
    # 统计
    total = 0
    hit = 0
    
    macao_home_total = 0
    macao_home_hit = 0
    macao_away_total = 0
    macao_away_hit = 0
    macao_draw_total = 0
    macao_draw_hit = 0
    
    results = []
    
    for m in all_matches:
        stats = analyze_odds_change_30(m['initial_odds'], m['realtime_odds'])
        trap_type, prediction = judge_real_or_trap(
            m['macao_tip'], m['home_team'], m['away_team'],
            m['home'], m['draw'], m['away'], stats
        )
        
        # 需要有实际结果才能统计
        # 这里先只输出预测结果
        total += 1
        
        # 记录
        if '主胜' in m['macao_tip'] or '贏' in m['macao_tip']:
            macao_home_total += 1
        elif '客胜' in m['macao_tip'] and '和局' not in m['macao_tip']:
            macao_away_total += 1
        elif '和局' in m['macao_tip']:
            macao_draw_total += 1
        
        results.append({
            'code': m['code'],
            'home': m['home_team'][:6],
            'away': m['away_team'][:6],
            'macao': m['macao_tip'][:10],
            'prediction': prediction,
            'type': trap_type
        })
    
    print("=" * 80)
    print(f"{'编号':<8} {'主队':<6} {'客队':<6} {'澳门心水':<10} {'预测':<8} {'类型'}")
    print("-" * 80)
    
    for r in results:
        print(f"{r['code']:<8} {r['home']:<6} {r['away']:<6} {r['macao']:<10} {r['prediction']:<8} {r['type']}")
    
    print()
    print("=" * 80)
    print("统计:")
    print(f"总比赛数: {total}")
    print(f"澳门主胜推荐: {macao_home_total} 场")
    print(f"澳门客胜推荐: {macao_away_total} 场")
    print(f"澳门和局推荐: {macao_draw_total} 场")


if __name__ == '__main__':
    run_test()
