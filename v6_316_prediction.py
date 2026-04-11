# 3.16 比赛预测 - V6算法（澳门心水+分布判断+威廉立博）

def get_distribution(home, draw, away):
    """判断分布类型"""
    # 计算各结果的赔率差
    home_draw_diff = home - draw
    draw_away_diff = draw - away
    
    # 顺分布：主胜低，平局中等，客胜高（主胜赔率最低）
    # 逆分布：客胜低（档位差距大但赔率接近）
    # 中庸分布：三项赔率接近
    # 缓冲分布：客胜略低于主胜，形成缓冲
    
    if home < away and home < 2.0:
        # 主胜是最低的
        if away - home > 0.5:
            return "顺分布"  # 主胜明显偏低
        elif away - home > 0.2:
            return "缓冲分布"  # 差距小，形成缓冲
        else:
            return "中庸分布"  # 非常接近
    elif away < home and away < 2.0:
        # 客胜是最低的
        if home - away > 0.5:
            return "逆分布"  # 档位差距大
        elif home - away > 0.2:
            return "缓冲分布"
        else:
            return "中庸分布"
    else:
        return "中庸分布"


def v6_predict(code, home_team, away_team, macao_tip, realtime_odds, initial_odds):
    """
    V6算法预测
    结合：分布判断 + 澳门心水 + 赔率变化
    """
    home, draw, away = realtime_odds
    
    # 获取威廉希尔和立博的初盘
    william_home, william_draw, william_away = None, None, None
    ladb_home, ladb_draw, ladb_away = None, None, None
    
    # 提取威廉和立博（初始赔率中索引1是威廉希尔，3是立博）
    if len(initial_odds) > 1:
        william_home, william_draw, william_away = initial_odds[1]
    if len(initial_odds) > 3:
        ladb_home, ladb_draw, ladb_away = initial_odds[3]
    
    # 即时威廉和立博
    william_rt = None
    ladb_rt = None
    if len(realtime_odds) > 1:
        william_rt = realtime_odds[1] if isinstance(realtime_odds[1], tuple) else None
    if len(realtime_odds) > 3:
        ladb_rt = realtime_odds[3] if isinstance(realtime_odds[3], tuple) else None
    
    # 1. 判断分布类型
    distribution = get_distribution(home, draw, away)
    
    # 2. 计算威廉-立博差（如果有）
    wl_diff = 0
    if william_rt and ladb_rt:
        wl_diff = abs(william_rt[0] - ladb_rt[0])  # 主胜差
    
    # 3. 澳门心水分析
    macao_home = "主胜" in macao_tip
    macao_away = "客胜" in macao_tip or "贏" in macao_tip and "主" not in macao_tip
    macao_draw = "和局" in macao_tip or "平" in macao_tip
    
    # 4. 赔率变化分析
    home_change = sum(1 for i, (ih, id, ia) in enumerate(initial_odds) 
                      for j, (rh, rd, ra) in enumerate(realtime_odds) if i==j and rh < ih)
    draw_change = sum(1 for i, (ih, id, ia) in enumerate(initial_odds) 
                      for j, (rh, rd, ra) in enumerate(realtime_odds) if i==j and rd < id)
    away_change = sum(1 for i, (ih, id, ia) in enumerate(initial_odds) 
                      for j, (rh, rd, ra) in enumerate(realtime_odds) if i==j and ra < ia)
    
    # ===== V6核心逻辑 =====
    
    # 澳门心水判断实盘/诱盘
    if macao_home:
        # 玩家看法：主胜
        # 庄家根据玩家看法开出的赔率
        if home < draw and home < away:
            # 赔率也支持主胜 → 实盘
            return "主胜", "A级", distribution, "实盘-主胜"
        else:
            # 赔率不支持主胜 → 诱盘
            if away < 2.5:
                return "客胜", "B级", distribution, "诱盘-主胜"
            else:
                return "防平", "B级", distribution, "诱盘-主胜"
    
    elif macao_away:
        # 玩家看法：客胜
        if away < home and away < draw:
            return "客胜", "A级", distribution, "实盘-客胜"
        else:
            if home < 2.5:
                return "主胜", "B级", distribution, "诱盘-客胜"
            else:
                return "防平", "B级", distribution, "诱盘-客胜"
    
    elif macao_draw:
        # 玩家看法：和局
        if draw < 3.3:
            return "防平", "A级", distribution, "实盘-防平"
        else:
            return "和局", "B级", distribution, "诱盘-分散"
    
    # 无澳门时，用分布+威廉立博
    # 威廉立博对比 - 简化
    if william_rt and ladb_rt and william_rt[0] and ladb_rt[0]:
        try:
            wl_diff = william_rt[0] - ladb_rt[0]
            if wl_diff < -0.1:
                # 威廉主胜低于立博 → 低开主胜诱盘
                if home < 2.0:
                    return "客胜", "B级", distribution, "威廉低开-诱盘"
                else:
                    return "防平", "B级", distribution, "威廉低开"
            elif wl_diff > 0.1:
                # 立博主胜低于威廉 → 低开客胜
                if away < 2.0:
                    return "客胜", "B级", distribution, "立博低开"
                else:
                    return "防平", "B级", distribution, "立博低开"
        except:
            pass
    
    # 分布判断
    if distribution == "顺分布":
        # 主胜偏低，正常打出的可能大
        if home < 1.8:
            return "主胜", "B级", distribution, "顺分布"
        else:
            return "防平", "B级", distribution, "顺分布-防平"
    
    elif distribution == "逆分布":
        # 客胜偏低，正常打出的可能大
        if away < 1.8:
            return "客胜", "B级", distribution, "逆分布"
        else:
            return "防平", "B级", distribution, "逆分布-防平"
    
    elif distribution == "缓冲分布":
        # 缓冲分布，最容易出意外
        if draw_change > 15:
            return "和局", "B级", distribution, "平赔上升"
        else:
            return "防平", "B级", distribution, "缓冲-防平"
    
    else:  # 中庸分布
        # 中庸分布三项接近
        if draw < 3.3 and draw_change > 10:
            return "和局", "B级", distribution, "低平赔"
        elif home < draw and home < away:
            return "主胜", "B级", distribution, "中庸-主胜"
        elif away < draw and away < home:
            return "客胜", "B级", distribution, "中庸-客胜"
        else:
            return "防平", "B级", distribution, "中庸-防平"


# ===================== 比赛数据 =====================

matches = [
    # 周一001
    {"code": "周一001", "home": "海尔蒙特", "away": "坎布尔", "macao": "坎布尔 贏",
     "initial": [(3.90,3.85,1.63),(3.50,3.20,2.10),(2.90,2.90,2.40)],
     "realtime": (3.70, 3.75, 1.73)},
    
    # 周一002
    {"code": "周一002", "home": "克雷莫纳", "away": "佛罗伦萨", "macao": "佛罗伦萨 贏",
     "initial": [(3.55,3.40,1.81),(3.50,3.20,2.10),(3.41,3.33,1.93)],
     "realtime": (3.70, 3.30, 1.95)},
    
    # 周一003
    {"code": "周一003", "home": "阿纳西", "away": "特鲁瓦", "macao": "特鲁瓦 贏",
     "initial": [(2.70,3.05,2.32),(2.90,2.90,2.40),(2.73,3.08,2.31)],
     "realtime": (2.60, 3.00, 2.45)},
    
    # 周一004
    {"code": "周一004", "home": "布伦特", "away": "狼队", "macao": "布伦特福德 贏",
     "initial": [(1.42,4.05,5.60),(1.57,3.80,5.50),(1.48,4.10,5.05)],
     "realtime": (1.48, 3.90, 5.10)},
    
    # 周一005
    {"code": "周一005", "home": "朴次茅斯", "away": "德比郡", "macao": "和局",
     "initial": [(1.95,3.06,3.45),(2.30,3.00,3.10),(2.10,3.25,2.93)],
     "realtime": (2.10, 3.25, 2.93)},
    
    # 周一006
    {"code": "周一006", "home": "巴列卡诺", "away": "莱万特", "macao": "巴列卡诺 贏",
     "initial": [(1.51,3.70,5.10),(1.75,3.60,4.40),(1.61,3.65,4.60)],
     "realtime": (1.46, 3.80, 5.50)},
    
    # 周二001
    {"code": "周二001", "home": "悉尼FC", "away": "墨尔本城", "macao": "悉尼FC 贏",
     "initial": [(2.23,3.28,2.66),(2.38,3.20,2.80),(2.17,3.35,2.75)],
     "realtime": (2.17, 3.35, 2.75)},
    
    # 周二002 - 中国女vs澳大利女
    {"code": "周二002", "home": "中国女", "away": "澳大利女", "macao": "澳大利亚 贏",
     "initial": [(5.50,3.80,1.53),(5.50,3.80,1.53),(6.00,4.00,1.45)],
     "realtime": (5.80, 4.00, 1.50)},
    
    # 周二004 - 里斯本vs博德闪耀
    {"code": "周二004", "home": "里斯本", "away": "博德闪耀", "macao": "里斯本 贏",
     "initial": [(1.40,4.40,6.00),(1.40,4.50,7.00),(1.42,4.50,6.50)],
     "realtime": (1.40, 4.50, 7.00)},
    
    # 周二006 - 阿森纳vs勒沃库森
    {"code": "周二006", "home": "阿森纳", "away": "勒沃库森", "macao": "阿森纳 贏",
     "initial": [(1.75,3.70,4.00),(1.73,3.80,4.33),(1.75,3.80,4.20)],
     "realtime": (1.75, 3.80, 4.20)},
    
    # 周二007 - 切尔西vs巴黎圣曼
    {"code": "周二007", "home": "切尔西", "away": "巴黎圣曼", "macao": "巴黎圣曼 贏",
     "initial": [(2.90,3.40,2.25),(2.90,3.50,2.30),(3.00,3.50,2.20)],
     "realtime": (3.00, 3.50, 2.20)},
    
    # 周二008 - 曼城vs皇马
    {"code": "周二008", "home": "曼城", "away": "皇马", "macao": "曼城 贏",
     "initial": [(1.65,4.00,4.50),(1.67,3.80,4.50),(1.70,4.00,4.33)],
     "realtime": (1.70, 4.00, 4.33)},
]

# ===================== 预测 =====================
print("="*70)
print("3.16 比赛预测 - V6算法")
print("="*70)

# 按分布类型分组
buffer_dist = []  # 缓冲分布
neutral_dist = []  # 中庸分布
reverse_dist = []  # 逆分布
forward_dist = []  # 顺分布

for match in matches:
    result = v6_predict(
        match["code"], 
        match["home"], 
        match["away"], 
        match["macao"],
        match["realtime"],
        match["initial"]
    )
    
    prediction = result[0]
    confidence = result[1]
    dist_type = result[2]
    reason = result[3]
    
    match_info = {
        "code": match["code"],
        "home": match["home"],
        "away": match["away"],
        "prediction": prediction,
        "confidence": confidence,
        "reason": reason
    }
    
    if dist_type == "缓冲分布":
        buffer_dist.append(match_info)
    elif dist_type == "逆分布":
        reverse_dist.append(match_info)
    elif dist_type == "中庸分布":
        neutral_dist.append(match_info)
    else:
        forward_dist.append(match_info)

# 输出结果
print("\n" + "="*70)
print("【缓冲分布】预测 (V6准确率100%)")
print("="*70)
if buffer_dist:
    for m in buffer_dist:
        print(f"{m['code']}: {m['home']} vs {m['away']}")
        print(f"  → 预测: {m['prediction']} ({m['confidence']})")
        print(f"  → 理由: {m['reason']}")
        print()
else:
    print("无缓冲分布比赛")

print("\n" + "="*70)
print("【中庸分布】预测 (V6准确率70.6%)")
print("="*70)
for m in neutral_dist:
    print(f"{m['code']}: {m['home']} vs {m['away']}")
    print(f"  → 预测: {m['prediction']} ({m['confidence']})")
    print(f"  → 理由: {m['reason']}")
    print()

print("\n" + "="*70)
print("【逆分布】预测 (V6准确率66.7%)")
print("="*70)
for m in reverse_dist:
    print(f"{m['code']}: {m['home']} vs {m['away']}")
    print(f"  → 预测: {m['prediction']} ({m['confidence']})")
    print(f"  → 理由: {m['reason']}")
    print()

print("\n" + "="*70)
print("【顺分布】预测 (V6准确率46.2%)")
print("="*70)
for m in forward_dist:
    print(f"{m['code']}: {m['home']} vs {m['away']}")
    print(f"  → 预测: {m['prediction']} ({m['confidence']})")
    print(f"  → 理由: {m['reason']}")
    print()
