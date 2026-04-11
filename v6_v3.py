# V6增强版算法 v3 - 精确统计每家公司赔率变化幅度

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


def analyze_odds_change_detailed(initial_odds, realtime_odds):
    """
    精确统计每家公司赔率变化
    返回详细统计：
    - home_up_10: 主胜升10%以上公司数
    - home_down_10: 主胜降10%以上公司数
    - draw_up_10, draw_down_10
    - away_up_10, away_down_10
    - total: 公司总数
    """
    home_up_10 = 0
    home_down_10 = 0
    draw_up_10 = 0
    draw_down_10 = 0
    away_up_10 = 0
    away_down_10 = 0
    
    # 如果realtime是单tuple，转为list
    if isinstance(realtime_odds, tuple) and not isinstance(realtime_odds, list):
        # realtime_odds是单公司的即时赔率，需要和initial对应
        # 假设initial有n家公司，realtime只有1个（可能是平均或中位数）
        # 这种情况下用简化判断
        return {
            "home_up_10": 0, "home_down_10": 0,
            "draw_up_10": 0, "draw_down_10": 0,
            "away_up_10": 0, "away_down_10": 0,
            "total": 1,
            "simple": True
        }
    
    # initial_odds 和 realtime_odds 都是list，一一对应
    total = min(len(initial_odds), len(realtime_odds))
    
    for i in range(total):
        ih, id, ia = initial_odds[i]
        rh, rd, ra = realtime_odds[i]
        
        # 主胜变化
        if ih > 0:
            home_pct = (rh - ih) / ih * 100
            if home_pct >= 10:
                home_up_10 += 1
            elif home_pct <= -10:
                home_down_10 += 1
        
        # 平局变化
        if id > 0:
            draw_pct = (rd - id) / id * 100
            if draw_pct >= 10:
                draw_up_10 += 1
            elif draw_pct <= -10:
                draw_down_10 += 1
        
        # 客胜变化
        if ia > 0:
            away_pct = (ra - ia) / ia * 100
            if away_pct >= 10:
                away_up_10 += 1
            elif away_pct <= -10:
                away_down_10 += 1
    
    return {
        "home_up_10": home_up_10, "home_down_10": home_down_10,
        "draw_up_10": draw_up_10, "draw_down_10": draw_down_10,
        "away_up_10": away_up_10, "away_down_10": away_down_10,
        "total": total,
        "simple": False
    }


def analyze_macao_real_trap_v3(macao_tip, home_team, away_team, home, draw, away, change_stats):
    """
    澳门心水判断实盘/诱盘 - v3精确版
    核心：统计变化幅度>=10%的公司占比
    - 澳门推荐方向：升10%以上占比>=50% → 诱盘
    - 澳门推荐方向：降10%以上占比>=50% → 实盘
    """
    # 解析澳门推荐
    macao_home = home_team in macao_tip and "赢" in macao_tip
    macao_away = away_team in macao_tip and "赢" in macao_tip
    macao_draw = "和局" in macao_tip
    
    total = change_stats["total"]
    if total == 0:
        total = 1
    
    if macao_home:
        # 澳门推荐主胜
        up_ratio = change_stats["home_up_10"] / total  # 升10%以上占比
        down_ratio = change_stats["home_down_10"] / total  # 降10%以上占比
        
        # 诱盘判断：升10%以上占比>=50%
        if up_ratio >= 0.5:
            # 诱盘！反向
            if away < home:
                return "诱盘", "客胜", f"主胜升10%以上{up_ratio*100:.0f}%→诱盘"
            else:
                return "诱盘", "防平", f"主胜升10%以上{up_ratio*100:.0f}%→诱盘"
        # 实盘判断：降10%以上占比>=50%
        elif down_ratio >= 0.5:
            return "实盘", "主胜", f"主胜降10%以上{down_ratio*100:.0f}%→实盘"
        else:
            # 变化分散，按澳门
            return "实盘", "主胜", f"主胜变化分散,跟澳门"
    
    elif macao_away:
        # 澳门推荐客胜
        up_ratio = change_stats["away_up_10"] / total
        down_ratio = change_stats["away_down_10"] / total
        
        if up_ratio >= 0.5:
            # 诱盘！
            if home < away:
                return "诱盘", "主胜", f"客胜升10%以上{up_ratio*100:.0f}%→诱盘"
            else:
                return "诱盘", "防平", f"客胜升10%以上{up_ratio*100:.0f}%→诱盘"
        elif down_ratio >= 0.5:
            return "实盘", "客胜", f"客胜降10%以上{down_ratio*100:.0f}%→实盘"
        else:
            return "实盘", "客胜", f"客胜变化分散,跟澳门"
    
    elif macao_draw:
        # 澳门推荐和局
        return "实盘", "和局", f"澳门推荐和局"
    
    return None, None, "无澳门"


def v6_predict_v3(code, home_team, away_team, macao_tip, home, draw, away, initial_odds, realtime_odds):
    """
    V6预测 v3 - 精确统计
    """
    # 1. 分布判断
    distribution = get_distribution(home, draw, away)
    
    # 2. 赔率变化分析
    change_stats = analyze_odds_change_detailed(initial_odds, realtime_odds)
    
    # 3. 澳门实盘/诱盘判断
    macao_type, macao_result, reason = analyze_macao_real_trap_v3(
        macao_tip, home_team, away_team, home, draw, away, change_stats
    )
    
    # 4. 澳门有判断时
    if macao_type:
        return macao_result, "A级", distribution, f"{macao_type}-{reason}"
    
    # 5. 无澳门时用分布
    if distribution == "顺分布":
        if home < 1.8:
            return "主胜", "B级", distribution, "顺分布-主胜"
        return "防平", "B级", distribution, "顺分布-防平"
    elif distribution == "逆分布":
        if away < 1.8:
            return "客胜", "B级", distribution, "逆分布-客胜"
        return "防平", "B级", distribution, "逆分布-防平"
    elif distribution == "缓冲分布":
        return "防平", "B级", distribution, "缓冲-防平"
    else:  # 中庸
        return "防平", "B级", distribution, "中庸-防平"


# ===================== 3.12 比赛数据 =====================
# 关键：initial_odds 和 realtime_odds 一一对应！
matches = [
    {"code": "周四001", "home": "淡宾尼士", "away": "曼谷联", "macao": "曼谷联 贏",
     "initial": [(4.15,3.75,1.61),(3.75,3.40,1.75),(3.00,3.24,1.87)],
     "realtime": [(2.75,3.26,2.18),(2.80,3.30,2.15),(2.70,3.20,2.20)]},
    
    {"code": "周四002", "home": "博洛尼亚", "away": "罗马", "macao": "和局",
     "initial": [(2.80,2.87,2.36),(2.75,3.20,2.50),(2.87,2.97,2.28)],
     "realtime": [(2.90,2.82,2.33),(2.85,2.85,2.35),(2.95,2.80,2.30)]},
    
    {"code": "周四003", "home": "斯图加特", "away": "波尔图", "macao": "和局",
     "initial": [(1.94,3.30,3.22),(2.30,3.40,2.75),(1.99,3.35,3.11)],
     "realtime": [(1.79,3.30,3.73),(1.80,3.35,3.70),(1.78,3.25,3.75)]},
    
    {"code": "周四004", "home": "里尔", "away": "维拉", "macao": "和局",
     "initial": [(3.05,3.20,2.08),(3.25,3.40,2.05),(3.20,3.30,2.05)],
     "realtime": [(3.05,3.12,2.08),(3.10,3.15,2.10),(3.00,3.10,2.05)]},
    
    {"code": "周四005", "home": "帕纳辛纳", "away": "贝蒂斯", "macao": "贝蒂斯 贏",
     "initial": [(4.00,3.25,1.80),(4.00,3.40,1.80),(3.80,3.30,1.85)],
     "realtime": [(3.92,3.20,1.78),(3.90,3.25,1.80),(3.95,3.15,1.75)]},
    
    {"code": "周四006", "home": "阿尔克马", "away": "布斯巴达", "macao": "布斯巴达 贏",
     "initial": [(1.75,3.50,4.00),(1.80,3.50,4.00),(1.75,3.55,4.00)],
     "realtime": [(1.74,3.47,3.75),(1.72,3.50,3.80),(1.76,3.45,3.70)]},
    
    {"code": "周四007", "home": "新未来SC", "away": "布赖代合作", "macao": "和局",
     "initial": [(2.15,3.10,3.00),(2.20,3.10,3.00),(2.10,3.15,3.00)],
     "realtime": [(2.15,3.11,2.92),(2.18,3.12,2.90),(2.12,3.10,2.95)]},
    
    {"code": "周四008", "home": "费伦茨", "away": "布拉加", "macao": "布拉加 贏",
     "initial": [(3.10,3.00,2.10),(3.10,3.10,2.10),(3.05,3.05,2.15)],
     "realtime": [(3.05,2.95,2.16),(3.08,3.00,2.12),(3.02,2.90,2.20)]},
    
    {"code": "周四009", "home": "亨克", "away": "弗赖堡", "macao": "和局",
     "initial": [(2.55,3.15,2.40),(2.55,3.20,2.40),(2.55,3.15,2.42)],
     "realtime": [(2.55,3.15,2.38),(2.58,3.18,2.35),(2.52,3.12,2.40)]},
    
    {"code": "周四010", "home": "诺丁汉", "away": "中日德兰", "macao": "中日德兰 贏",
     "initial": [(1.40,4.25,5.50),(1.40,4.50,6.00),(1.42,4.30,5.50)],
     "realtime": [(1.40,4.25,5.55),(1.42,4.30,5.40),(1.38,4.20,5.70)]},
    
    {"code": "周四011", "home": "塞尔塔", "away": "里昂", "macao": "和局",
     "initial": [(1.90,3.20,3.50),(1.90,3.30,3.50),(1.88,3.25,3.60)],
     "realtime": [(1.90,3.22,3.42),(1.92,3.25,3.40),(1.88,3.20,3.45)]},
    
    {"code": "周四012", "home": "水晶宫", "away": "拉纳卡", "macao": "拉纳卡AEK 贏",
     "initial": [(1.22,5.00,12.00),(1.22,5.50,12.00),(1.25,5.00,10.00)],
     "realtime": [(1.22,5.50,13.00),(1.24,5.30,12.50),(1.20,5.70,13.50)]},
]

# 实际结果
results = {
    "周四001": "和局", "周四002": "和局", "周四003": "客胜", "周四004": "客胜",
    "周四005": "主胜", "周四006": "主胜", "周四007": "和局", "周四008": "主胜",
    "周四009": "主胜", "周四010": "客胜", "周四011": "和局", "周四012": "和局",
}

# 预测
print("="*70)
print("V6算法 v3 - 精确统计每家公司变化幅度")
print("诱盘判断: 澳门推荐方向升10%以上公司>=50% = 诱盘")
print("实盘判断: 澳门推荐方向降10%以上公司>=50% = 实盘")
print("="*70)

all_matches = []

for match in matches:
    home, draw, away = match["realtime"][0]
    
    # 分析变化
    change_stats = analyze_odds_change_detailed(match["initial"], match["realtime"])
    
    result = v6_predict_v3(
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
        "odds": (home, draw, away),
        "change_stats": change_stats
    }
    all_matches.append(match_info)

# 输出
for m in all_matches:
    print(f"\n{m['code']}: {m['home']} vs {m['away']}")
    print(f"  赔率: {m['odds'][0]:.2f} - {m['odds'][1]:.2f} - {m['odds'][2]:.2f}")
    
    cs = m['change_stats']
    if not cs.get("simple", False):
        print(f"  变化统计(升10%↑/降10%↓): 主{cs['home_up_10']}/{cs['home_down_10']} 平{cs['draw_up_10']}/{cs['draw_down_10']} 客{cs['away_up_10']}/{cs['away_down_10']} (共{cs['total']}家)")
    
    print(f"  → 预测: {m['prediction']} ({m['confidence']}) - {m['reason']}")
    
    actual = results[m["code"]]
    is_correct = (m["prediction"] == actual) or (m["prediction"] == "防平" and actual == "和局")
    mark = "OK" if is_correct else "X"
    print(f"  → 实际: {actual} {mark}")

# 统计
print("\n" + "="*70)
print("统计结果")
print("="*70)

correct = sum(1 for m in all_matches 
              if m["prediction"] == results[m["code"]] or 
              (m["prediction"] == "防平" and results[m["code"]] == "和局"))

# 防平算0.5
for m in all_matches:
    if m["prediction"] == "防平" and results[m["code"]] == "和局":
        correct += 0.5

print(f"\n总体准确率: {correct}/12 = {correct/12*100:.1f}%")

# 分类
print("\n--- 分类统计 ---")
categories = {"和局推荐": [], "主胜推荐": [], "客胜推荐": []}
for m in all_matches:
    if "和局" in m["reason"]:
        categories["和局推荐"].append(m)
    elif "主胜" in m["prediction"]:
        categories["主胜推荐"].append(m)
    else:
        categories["客胜推荐"].append(m)

for cat, matches_list in categories.items():
    if not matches_list:
        continue
    cat_correct = sum(1 for m in matches_list 
                      if m["prediction"] == results[m["code"]] or
                      (m["prediction"] == "防平" and results[m["code"]] == "和局"))
    for m in matches_list:
        if m["prediction"] == "防平" and results[m["code"]] == "和局":
            cat_correct += 0.5
    print(f"{cat}: {cat_correct}/{len(matches_list)} = {cat_correct/len(matches_list)*100:.1f}%")
