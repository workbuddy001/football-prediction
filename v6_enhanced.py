# V6增强版算法 - 结合赔率变化+澳门心水实盘/诱盘

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


def analyze_odds_change(initial_odds, realtime_odds):
    """
    分析赔率变化
    返回: (主胜降赔数, 平局降赔数, 客胜降赔数)
    """
    home_down = 0
    draw_down = 0
    away_down = 0
    
    # 确保是列表
    if isinstance(realtime_odds, tuple):
        # realtime_odds是单个赔率tuple，不是list
        # 使用简化的统计方法
        ih, id, ia = initial_odds[0] if initial_odds else (0,0,0)
        rh, rd, ra = realtime_odds
        if rh < ih:
            home_down += 1
        if rd < id:
            draw_down += 1
        if ra < ia:
            away_down += 1
        return home_down, draw_down, away_down
    
    for i in range(len(initial_odds)):
        if i >= len(realtime_odds):
            break
        ih, id, ia = initial_odds[i]
        rh, rd, ra = realtime_odds[i]
        
        if rh < ih:
            home_down += 1
        if rd < id:
            draw_down += 1
        if ra < ia:
            away_down += 1
    
    return home_down, draw_down, away_down


def analyze_macao_real_trap(macao_tip, home_team, away_team, home, draw, away, home_change, draw_change, away_change):
    """
    澳门心水判断实盘/诱盘
    结合赔率变化
    """
    # 解析澳门推荐
    macao_home = home_team in macao_tip and "贏" in macao_tip
    macao_away = away_team in macao_tip and "贏" in macao_tip
    macao_draw = "和局" in macao_tip
    
    total = 30  # 假设30家公司
    
    if macao_home:
        # 玩家看法：主胜
        # 庄家根据这个看法应该高开主胜来分散
        # 如果主胜降赔，说明是真看好（实盘）
        # 如果主胜升赔，说明用主胜来分散（诱盘）
        
        if home_change > total * 0.4:  # 超过40%降赔
            # 主胜降赔多 → 庄家真实看好主胜 → 实盘
            return "实盘", "主胜", f"主胜降赔{home_change}家"
        else:
            # 主胜升赔多 → 诱盘分散主胜资金
            if away < home:  # 客胜赔率更低
                return "诱盘", "客胜", f"主胜升赔分散,客胜更低{away}"
            else:
                return "诱盘", "防平", f"主胜升赔分散,防平"
    
    elif macao_away:
        # 玩家看法：客胜
        if away_change > total * 0.4:
            return "实盘", "客胜", f"客胜降赔{away_change}家"
        else:
            if home < away:
                return "诱盘", "主胜", f"客胜升赔分散,主胜更低{home}"
            else:
                return "诱盘", "防平", f"客胜升赔分散,防平"
    
    elif macao_draw:
        # 澳门推荐和局时：直接相信澳门
        # 澳门推荐和局往往是庄家真实看法
        return "实盘", "和局", f"澳门推荐和局"
    
    return None, None, "无澳门"


def v6_enhanced_predict(code, home_team, away_team, macao_tip, home, draw, away, initial_odds, realtime_odds):
    """
    V6增强版预测
    """
    # 1. 分布判断
    distribution = get_distribution(home, draw, away)
    
    # 2. 赔率变化分析
    home_change, draw_change, away_change = analyze_odds_change(initial_odds, realtime_odds)
    
    # 3. 澳门心水实盘/诱盘判断
    macao_type, macao_result, reason = analyze_macao_real_trap(
        macao_tip, home_team, away_team, home, draw, away,
        home_change, draw_change, away_change
    )
    
    # 4. 如果澳门有判断，按澳门结果
    if macao_type:
        return macao_result, "A级", distribution, f"{macao_type}-{reason}"
    
    # 5. 无澳门时，用分布+赔率变化
    # 赔率变化作为辅助判断
    if distribution == "顺分布":
        if home < 1.8:
            return "主胜", "B级", distribution, "顺分布-主胜"
        else:
            # 赔率变化判断
            if away_change > home_change:
                return "客胜", "B级", distribution, "顺分布-客胜"
            return "防平", "B级", distribution, "顺分布-防平"
    
    elif distribution == "逆分布":
        if away < 1.8:
            return "客胜", "B级", distribution, "逆分布-客胜"
        else:
            if home_change > away_change:
                return "主胜", "B级", distribution, "逆分布-主胜"
            return "防平", "B级", distribution, "逆分布-防平"
    
    elif distribution == "缓冲分布":
        # 缓冲分布看赔率变化
        if draw_change > 15:
            return "和局", "B级", distribution, "缓冲-平局升"
        return "防平", "B级", distribution, "缓冲-防平"
    
    else:  # 中庸分布
        if draw < 3.3 and draw_change > 10:
            return "和局", "B级", distribution, "中庸-低平赔"
        elif home < draw and home < away:
            return "主胜", "B级", distribution, "中庸-主胜"
        elif away < draw and away < home:
            return "客胜", "B级", distribution, "中庸-客胜"
        else:
            return "防平", "B级", distribution, "中庸-防平"


# ===================== 3.12 比赛数据 =====================
matches = [
    {"code": "周四001", "home": "淡宾尼士", "away": "曼谷联", "macao": "曼谷联 贏",
     "initial": [(4.15,3.75,1.61),(3.75,3.40,1.75),(3.00,3.24,1.87)],
     "realtime": (2.75,3.26,2.18)},
    
    {"code": "周四002", "home": "博洛尼亚", "away": "罗马", "macao": "和局",
     "initial": [(2.80,2.87,2.36),(2.75,3.20,2.50),(2.87,2.97,2.28)],
     "realtime": (2.90,2.82,2.33)},
    
    {"code": "周四003", "home": "斯图加特", "away": "波尔图", "macao": "和局",
     "initial": [(1.94,3.30,3.22),(2.30,3.40,2.75),(1.99,3.35,3.11)],
     "realtime": (1.79,3.30,3.73)},
    
    {"code": "周四004", "home": "里尔", "away": "维拉", "macao": "和局",
     "initial": [(3.05,3.20,2.08),(3.25,3.40,2.05),(3.20,3.30,2.05)],
     "realtime": (3.05,3.12,2.08)},
    
    {"code": "周四005", "home": "帕纳辛纳", "away": "贝蒂斯", "macao": "贝蒂斯 贏",
     "initial": [(4.00,3.25,1.80),(4.00,3.40,1.80),(3.80,3.30,1.85)],
     "realtime": (3.92,3.20,1.78)},
    
    {"code": "周四006", "home": "阿尔克马", "away": "布斯巴达", "macao": "布斯巴达 贏",
     "initial": [(1.75,3.50,4.00),(1.80,3.50,4.00),(1.75,3.55,4.00)],
     "realtime": (1.74,3.47,3.75)},
    
    {"code": "周四007", "home": "新未来SC", "away": "布赖代合作", "macao": "和局",
     "initial": [(2.15,3.10,3.00),(2.20,3.10,3.00),(2.10,3.15,3.00)],
     "realtime": (2.15,3.11,2.92)},
    
    {"code": "周四008", "home": "费伦茨", "away": "布拉加", "macao": "布拉加 贏",
     "initial": [(3.10,3.00,2.10),(3.10,3.10,2.10),(3.05,3.05,2.15)],
     "realtime": (3.05,2.95,2.16)},
    
    {"code": "周四009", "home": "亨克", "away": "弗赖堡", "macao": "和局",
     "initial": [(2.55,3.15,2.40),(2.55,3.20,2.40),(2.55,3.15,2.42)],
     "realtime": (2.55,3.15,2.38)},
    
    {"code": "周四010", "home": "诺丁汉", "away": "中日德兰", "macao": "中日德兰 贏",
     "initial": [(1.40,4.25,5.50),(1.40,4.50,6.00),(1.42,4.30,5.50)],
     "realtime": (1.40,4.25,5.55)},
    
    {"code": "周四011", "home": "塞尔塔", "away": "里昂", "macao": "和局",
     "initial": [(1.90,3.20,3.50),(1.90,3.30,3.50),(1.88,3.25,3.60)],
     "realtime": (1.90,3.22,3.42)},
    
    {"code": "周四012", "home": "水晶宫", "away": "拉纳卡", "macao": "拉纳卡AEK 贏",
     "initial": [(1.22,5.00,12.00),(1.22,5.50,12.00),(1.25,5.00,10.00)],
     "realtime": (1.22,5.50,13.00)},
]

# 实际结果
results = {
    "周四001": "和局", "周四002": "和局", "周四003": "客胜", "周四004": "客胜",
    "周四005": "主胜", "周四006": "主胜", "周四007": "和局", "周四008": "主胜",
    "周四009": "主胜", "周四010": "客胜", "周四011": "和局", "周四012": "和局",
}

# 预测
print("="*70)
print("V6增强版算法 3.12 预测")
print("="*70)

buffer_dist = []
neutral_dist = []
reverse_dist = []
forward_dist = []

for match in matches:
    home, draw, away = match["realtime"]
    result = v6_enhanced_predict(
        match["code"], match["home"], match["away"], match["macao"],
        home, draw, away, match["initial"], match["realtime"]
    )
    
    match_info = {
        "code": match["code"],
        "home": match["home"],
        "away": match["away"],
        "prediction": result[0],
        "confidence": result[1],
        "dist_type": result[2],
        "reason": result[3],
        "odds": (home, draw, away)
    }
    
    if result[2] == "缓冲分布":
        buffer_dist.append(match_info)
    elif result[2] == "逆分布":
        reverse_dist.append(match_info)
    elif result[2] == "中庸分布":
        neutral_dist.append(match_info)
    else:
        forward_dist.append(match_info)

# 输出
def print_matches(matches, title):
    print(f"\n{'='*70}")
    print(title)
    print("="*70)
    for m in matches:
        print(f"{m['code']}: {m['home']} vs {m['away']}")
        print(f"  赔率: {m['odds'][0]:.2f} - {m['odds'][1]:.2f} - {m['odds'][2]:.2f}")
        print(f"  → 预测: {m['prediction']} ({m['confidence']})")
        print(f"  → 理由: {m['reason']}")
        
        # 显示命中结果
        actual = results[m["code"]]
        is_correct = (m["prediction"] == actual) or (m["prediction"] == "防平" and actual == "和局")
        mark = "OK" if is_correct else "X"
        print(f"  → 实际: {actual} {mark}")
        print()

print_matches(buffer_dist, "【缓冲分布】")
print_matches(neutral_dist, "【中庸分布】")
print_matches(reverse_dist, "【逆分布】")
print_matches(forward_dist, "【顺分布】")

# 统计
print("\n" + "="*70)
print("统计结果")
print("="*70)

total = 0
correct = 0
for dist_list in [buffer_dist, neutral_dist, reverse_dist, forward_dist]:
    for m in dist_list:
        total += 1
        actual = results[m["code"]]
        if m["prediction"] == actual:
            correct += 1
        elif m["prediction"] == "防平" and actual == "和局":
            correct += 0.5

print(f"\n总体准确率: {correct}/{total} = {correct/total*100:.1f}%")
