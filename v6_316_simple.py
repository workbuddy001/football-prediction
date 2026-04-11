# 3.16 比赛预测 - V6算法（简化版）

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


def v6_predict(code, home_team, away_team, macao_tip, home, draw, away):
    """
    V6算法预测 - 简化版
    """
    distribution = get_distribution(home, draw, away)
    
    # 澳门心水分析
    macao_home = "主胜" in macao_tip or (home_team in macao_tip and "贏" in macao_tip)
    macao_away = "客胜" in macao_tip or ("贏" in macao_tip and home_team not in macao_tip and "和" not in macao_tip)
    macao_draw = "和局" in macao_tip or "平" in macao_tip
    
    # ===== V6核心逻辑 =====
    
    # 澳门心水判断实盘/诱盘
    if macao_home:
        if home < draw and home < away:
            return "主胜", "A级", distribution, "实盘-主胜"
        else:
            if away < 2.5:
                return "客胜", "B级", distribution, "诱盘-主胜"
            else:
                return "防平", "B级", distribution, "诱盘-主胜"
    
    elif macao_away:
        if away < home and away < draw:
            return "客胜", "A级", distribution, "实盘-客胜"
        else:
            if home < 2.5:
                return "主胜", "B级", distribution, "诱盘-客胜"
            else:
                return "防平", "B级", distribution, "诱盘-客胜"
    
    elif macao_draw:
        if draw < 3.3:
            return "防平", "A级", distribution, "实盘-防平"
        else:
            return "和局", "B级", distribution, "诱盘-分散"
    
    # 分布判断
    if distribution == "顺分布":
        if home < 1.8:
            return "主胜", "B级", distribution, "顺分布"
        else:
            return "防平", "B级", distribution, "顺分布-防平"
    
    elif distribution == "逆分布":
        if away < 1.8:
            return "客胜", "B级", distribution, "逆分布"
        else:
            return "防平", "B级", distribution, "逆分布-防平"
    
    elif distribution == "缓冲分布":
        return "防平", "B级", distribution, "缓冲-防平"
    
    else:  # 中庸分布
        if draw < 3.3 and home < draw and home < away:
            return "和局", "B级", distribution, "低平赔"
        elif home < draw and home < away:
            return "主胜", "B级", distribution, "中庸-主胜"
        elif away < draw and away < home:
            return "客胜", "B级", distribution, "中庸-客胜"
        else:
            return "防平", "B级", distribution, "中庸-防平"


# ===================== 比赛数据 (即时赔率) =====================

matches = [
    # 周一001 - 海尔蒙特vs坎布尔
    {"code": "周一001", "home": "海尔蒙特", "away": "坎布尔", "macao": "坎布尔 贏",
     "odds": (3.70, 3.75, 1.73)},
    
    # 周一002 - 克雷莫纳vs佛罗伦萨
    {"code": "周一002", "home": "克雷莫纳", "away": "佛罗伦萨", "macao": "佛罗伦萨 贏",
     "odds": (3.70, 3.30, 1.95)},
    
    # 周一003 - 阿纳西vs特鲁瓦
    {"code": "周一003", "home": "阿纳西", "away": "特鲁瓦", "macao": "特鲁瓦 贏",
     "odds": (2.60, 3.00, 2.45)},
    
    # 周一004 - 布伦特vs狼队
    {"code": "周一004", "home": "布伦特", "away": "狼队", "macao": "布伦特福德 贏",
     "odds": (1.48, 3.90, 5.10)},
    
    # 周一005 - 朴次茅斯vs德比郡
    {"code": "周一005", "home": "朴次茅斯", "away": "德比郡", "macao": "和局",
     "odds": (2.10, 3.25, 2.93)},
    
    # 周一006 - 巴列卡诺vs莱万特
    {"code": "周一006", "home": "巴列卡诺", "away": "莱万特", "macao": "巴列卡诺 贏",
     "odds": (1.46, 3.80, 5.50)},
    
    # 周二001 - 悉尼FCvs墨尔本城
    {"code": "周二001", "home": "悉尼FC", "away": "墨尔本城", "macao": "悉尼FC 贏",
     "odds": (2.17, 3.35, 2.75)},
    
    # 周二002 - 中国女vs澳大利女
    {"code": "周二002", "home": "中国女", "away": "澳大利女", "macao": "澳大利亚 贏",
     "odds": (5.80, 4.00, 1.50)},
    
    # 周二004 - 里斯本vs博德闪耀
    {"code": "周二004", "home": "里斯本", "away": "博德闪耀", "macao": "里斯本 贏",
     "odds": (1.40, 4.50, 7.00)},
    
    # 周二006 - 阿森纳vs勒沃库森
    {"code": "周二006", "home": "阿森纳", "away": "勒沃库森", "macao": "阿森纳 贏",
     "odds": (1.75, 3.80, 4.20)},
    
    # 周二007 - 切尔西vs巴黎圣曼
    {"code": "周二007", "home": "切尔西", "away": "巴黎圣曼", "macao": "巴黎圣曼 贏",
     "odds": (3.00, 3.50, 2.20)},
    
    # 周二008 - 曼城vs皇马
    {"code": "周二008", "home": "曼城", "away": "皇马", "macao": "曼城 贏",
     "odds": (1.70, 4.00, 4.33)},
]

# ===================== 预测 =====================
print("="*70)
print("3.16 比赛预测 - V6算法")
print("="*70)

# 按分布类型分组
buffer_dist = []
neutral_dist = []
reverse_dist = []
forward_dist = []

for match in matches:
    home, draw, away = match["odds"]
    
    result = v6_predict(
        match["code"], 
        match["home"], 
        match["away"], 
        match["macao"],
        home, draw, away
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
        "reason": reason,
        "odds": match["odds"]
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
print("【缓冲分布】预测 (V6历史准确率100%，样本3场)")
print("="*70)
if buffer_dist:
    for m in buffer_dist:
        print(f"{m['code']}: {m['home']} vs {m['away']}")
        print(f"  赔率: {m['odds'][0]:.2f} - {m['odds'][1]:.2f} - {m['odds'][2]:.2f}")
        print(f"  → 预测: {m['prediction']} ({m['confidence']})")
        print(f"  → 理由: {m['reason']}")
        print()
else:
    print("无缓冲分布比赛")

print("\n" + "="*70)
print("【中庸分布】预测 (V6历史准确率70.6%，样本17场)")
print("="*70)
for m in neutral_dist:
    print(f"{m['code']}: {m['home']} vs {m['away']}")
    print(f"  赔率: {m['odds'][0]:.2f} - {m['odds'][1]:.2f} - {m['odds'][2]:.2f}")
    print(f"  → 预测: {m['prediction']} ({m['confidence']})")
    print(f"  → 理由: {m['reason']}")
    print()

print("\n" + "="*70)
print("【逆分布】预测 (V6历史准确率66.7%，样本6场)")
print("="*70)
for m in reverse_dist:
    print(f"{m['code']}: {m['home']} vs {m['away']}")
    print(f"  赔率: {m['odds'][0]:.2f} - {m['odds'][1]:.2f} - {m['odds'][2]:.2f}")
    print(f"  → 预测: {m['prediction']} ({m['confidence']})")
    print(f"  → 理由: {m['reason']}")
    print()

print("\n" + "="*70)
print("【顺分布】预测 (V6历史准确率46.2%，样本26场)")
print("="*70)
for m in forward_dist:
    print(f"{m['code']}: {m['home']} vs {m['away']}")
    print(f"  赔率: {m['odds'][0]:.2f} - {m['odds'][1]:.2f} - {m['odds'][2]:.2f}")
    print(f"  → 预测: {m['prediction']} ({m['confidence']})")
    print(f"  → 理由: {m['reason']}")
    print()
