# 3.12 比赛预测 - V6算法

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
    """V6算法预测"""
    distribution = get_distribution(home, draw, away)
    
    # 澳门心水分析
    macao_home = home_team in macao_tip and "贏" in macao_tip
    macao_away = away_team in macao_tip and "贏" in macao_tip
    macao_draw = "和局" in macao_tip
    
    # V6核心逻辑
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


# 比赛数据 (即时赔率)
matches = [
    {"code": "周四001", "home": "淡宾尼士", "away": "曼谷联", "macao": "曼谷联 贏", "odds": (2.75, 3.26, 2.18)},
    {"code": "周四002", "home": "博洛尼亚", "away": "罗马", "macao": "和局", "odds": (2.90, 2.82, 2.33)},
    {"code": "周四003", "home": "斯图加特", "away": "波尔图", "macao": "和局", "odds": (1.79, 3.30, 3.73)},
    {"code": "周四004", "home": "里尔", "away": "维拉", "macao": "和局", "odds": (3.05, 3.12, 2.08)},
    {"code": "周四005", "home": "帕纳辛纳", "away": "贝蒂斯", "macao": "贝蒂斯 贏", "odds": (3.92, 3.20, 1.78)},
    {"code": "周四006", "home": "阿尔克马", "away": "布斯巴达", "macao": "布斯巴达 贏", "odds": (1.74, 3.47, 3.75)},
    {"code": "周四007", "home": "新未来SC", "away": "布赖代合作", "macao": "和局", "odds": (2.15, 3.11, 2.92)},
    {"code": "周四008", "home": "费伦茨", "away": "布拉加", "macao": "布拉加 贏", "odds": (3.05, 2.95, 2.16)},
    {"code": "周四009", "home": "亨克", "away": "弗赖堡", "macao": "和局", "odds": (2.55, 3.15, 2.38)},
    {"code": "周四010", "home": "诺丁汉", "away": "中日德兰", "macao": "中日德兰 贏", "odds": (1.40, 4.25, 5.55)},
    {"code": "周四011", "home": "塞尔塔", "away": "里昂", "macao": "和局", "odds": (1.90, 3.22, 3.42)},
    {"code": "周四012", "home": "水晶宫", "away": "拉纳卡", "macao": "拉纳卡AEK 贏", "odds": (1.22, 5.50, 13.00)},
]

# 预测
print("="*70)
print("3.12 比赛预测 - V6算法")
print("="*70)

buffer_dist = []
neutral_dist = []
reverse_dist = []
forward_dist = []

for match in matches:
    home, draw, away = match["odds"]
    result = v6_predict(match["code"], match["home"], match["away"], match["macao"], home, draw, away)
    
    match_info = {
        "code": match["code"],
        "home": match["home"],
        "away": match["away"],
        "prediction": result[0],
        "confidence": result[1],
        "dist_type": result[2],
        "reason": result[3],
        "odds": match["odds"]
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
print("\n" + "="*70)
print("【缓冲分布】预测 (V6历史准确率100%，样本3场)")
print("="*70)
for m in buffer_dist:
    print(f"{m['code']}: {m['home']} vs {m['away']}")
    print(f"  赔率: {m['odds'][0]:.2f} - {m['odds'][1]:.2f} - {m['odds'][2]:.2f}")
    print(f"  → 预测: {m['prediction']} ({m['confidence']})")
    print(f"  → 理由: {m['reason']}")
    print()

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
