# V6算法 3.12 预测结果统计

# 实际比赛结果
results = {
    "周四001": "主胜",  # 淡宾尼士 2:2 曼谷联 → 平
    "周四002": "和局",  # 博洛尼亚 1:1 罗马 → 和局
    "周四003": "客胜",  # 斯图加特 1:2 波尔图 → 客胜
    "周四004": "客胜",  # 里尔 0:1 维拉 → 客胜
    "周四005": "主胜",  # 帕纳辛纳 1:0 贝蒂斯 → 主胜
    "周四006": "主胜",  # 阿尔克马 2:1 布斯巴达 → 主胜
    "周四007": "和局",  # 新未来SC 2:2 布赖代合作 → 和局
    "周四008": "主胜",  # 费伦茨 2:0 布拉加 → 主胜
    "周四009": "主胜",  # 亨克 1:0 弗赖堡 → 主胜
    "周四010": "客胜",  # 诺丁汉 0:1 中日德兰 → 客胜
    "周四011": "和局",  # 塞尔塔 1:1 里昂 → 和局
    "周四012": "和局",  # 水晶宫 0:0 拉纳卡 → 和局
}

# V6预测结果
predictions = {
    "周四001": {"预测": "客胜", "分布": "中庸分布", "信心": "A级"},
    "周四002": {"预测": "防平", "分布": "中庸分布", "信心": "A级"},
    "周四003": {"预测": "和局", "分布": "顺分布", "信心": "B级"},
    "周四004": {"预测": "防平", "分布": "中庸分布", "信心": "A级"},
    "周四005": {"预测": "客胜", "分布": "逆分布", "信心": "A级"},
    "周四006": {"预测": "主胜", "分布": "顺分布", "信心": "B级"},
    "周四007": {"预测": "防平", "分布": "中庸分布", "信心": "A级"},
    "周四008": {"预测": "客胜", "分布": "中庸分布", "信心": "A级"},
    "周四009": {"预测": "防平", "分布": "中庸分布", "信心": "A级"},
    "周四010": {"预测": "主胜", "分布": "顺分布", "信心": "B级"},
    "周四011": {"预测": "防平", "分布": "顺分布", "信心": "A级"},
    "周四012": {"预测": "主胜", "分布": "顺分布", "信心": "B级"},
}

def check_prediction(code, predicted, actual):
    """检查预测是否正确"""
    # 防平预测：命中平局或主胜客胜的一半
    if predicted == "防平":
        if actual == "和局":
            return 0.5  # 半对
        else:
            return 0  # 错
    # 预测和局
    elif predicted == "和局":
        if actual == "和局":
            return 1
        else:
            return 0
    # 预测主胜
    elif predicted == "主胜":
        if actual == "主胜":
            return 1
        else:
            return 0
    # 预测客胜
    elif predicted == "客胜":
        if actual == "客胜":
            return 1
        else:
            return 0
    return 0

# 统计
print("="*70)
print("V6算法 3.12 预测结果统计")
print("="*70)

total = 0
correct = 0

# 按分布统计
dist_stats = {
    "中庸分布": {"total": 0, "correct": 0},
    "逆分布": {"total": 0, "correct": 0},
    "顺分布": {"total": 0, "correct": 0},
    "缓冲分布": {"total": 0, "correct": 0},
}

print("\n详细结果：")
print("-"*70)

for code in predictions:
    pred = predictions[code]["预测"]
    actual = results[code]
    dist = predictions[code]["分布"]
    confidence = predictions[code]["信心"]
    
    score = check_prediction(code, pred, actual)
    total += 1
    correct += score
    
    dist_stats[dist]["total"] += 1
    dist_stats[dist]["correct"] += score
    
    mark = "OK" if score == 1 else ("Half" if score == 0.5 else "X")
    print(f"{code}: 预测={pred:4s} 实际={actual:4s} {mark} ({dist})")

print("-"*70)

# 总体准确率
print(f"\n【总体准确率】{correct}/{total} = {correct/total*100:.1f}%")

# 按分布准确率
print("\n【按分布类型准确率】")
for dist, stats in dist_stats.items():
    if stats["total"] > 0:
        rate = stats["correct"] / stats["total"] * 100
        print(f"  {dist}: {stats['correct']}/{stats['total']} = {rate:.1f}%")
