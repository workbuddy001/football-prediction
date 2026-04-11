# 完整反向验证 - 所有强烈推荐场次
# 根据final_retrospect.py的输出，强烈推荐的场次：

strong_recommend_matches = [
    # 编号, 主队, 客队, V7预测, 置信度, 实际结果, 原因
    ("周日001", "日本女", "菲律宾女", "主胜", 99, "主胜", "高置信度+8正常+无末尾88"),
    ("周六001", "中国女", "中国台女", "主胜", 89, "平局", "状态焦灼+澳门推荐主胜+主胜8减少"),
    ("周五010", "马赛", "欧塞尔", "主胜", 70, "主胜", "高置信度(70%)+8正常+无末尾88"),
    ("周六013", "霍芬海姆", "沃夫斯堡", "主胜", 70, "平局", "高置信度(70%)+8正常+无末尾88"),
    ("周六012", "国际米兰", "亚特兰大", "主胜", 66, "平局", "状态焦灼+澳门推荐主胜+主胜8减少"),
    ("周六016", "勒沃库森", "拜仁", "客胜", 65, "平局", "高置信度(65%)+8正常+无末尾88"),
    ("周六015", "法兰克福", "海登海姆", "主胜", 62, "主胜", "高置信度(62%)+8正常+无末尾88"),
    ("周日006", "特温特", "乌德勒支", "主胜", 61, "客胜", "高置信度(61%)+8正常+无末尾88"),
]

print("=" * 80)
print("强烈推荐反向验证")
print("=" * 80)

total = len(strong_recommend_matches)
correct_original = 0
correct_reverse = 0

for match in strong_recommend_matches:
    match_id, home, away, v7_pred, conf, actual, reason = match
    
    # 正向预测
    if v7_pred == actual:
        original_ok = True
        correct_original += 1
    else:
        original_ok = False
    
    # 反向预测：主胜->客胜，客胜->主胜，平局->任选（跳过）
    if v7_pred == "主胜":
        reverse_pred = "客胜"
    elif v7_pred == "客胜":
        reverse_pred = "主胜"
    else:
        reverse_pred = "主胜"  # 默认
    
    if reverse_pred == actual:
        reverse_ok = True
        correct_reverse += 1
    else:
        reverse_ok = False
    
    print(f"\n{match_id} {home} vs {away}")
    print(f"  原因: {reason}")
    print(f"  原预测: {v7_pred} ({conf}%) -> 实际: {actual} -> {'OK' if original_ok else 'XX'}")
    print(f"  反向: {reverse_pred} -> 实际: {actual} -> {'OK' if reverse_ok else 'XX'}")

print("\n" + "=" * 80)
print("统计结果")
print("=" * 80)
print(f"\n正向（推荐方打出）: {correct_original}/{total} = {correct_original/total*100:.1f}%")
print(f"反向（不推荐方）: {correct_reverse}/{total} = {correct_reverse/total*100:.1f}%")
