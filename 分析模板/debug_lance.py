# 精确分析朗斯这场各赔率的8变化

# 初盘赔率
initial = [
    (3.82, 3.50, 1.72), (3.60, 3.40, 1.95), (4.00, 3.45, 1.75), (3.70, 3.60, 1.95),
    (3.80, 3.50, 1.91), (3.80, 3.60, 1.95), (3.60, 3.60, 1.95), (3.80, 3.60, 1.96),
    (4.20, 3.70, 1.84), (3.60, 3.50, 1.90), (3.70, 3.60, 1.95), (3.47, 3.46, 2.06),
    (3.85, 3.45, 1.92), (3.90, 3.60, 1.91), (3.44, 3.28, 1.98), (3.60, 3.40, 1.91),
    (3.70, 3.60, 1.95), (3.45, 3.55, 1.97), (3.45, 3.55, 1.97), (3.80, 3.60, 1.96),
    (3.60, 3.40, 1.78), (3.45, 3.55, 1.97), (3.90, 3.55, 1.91), (3.90, 3.50, 1.90),
    (4.06, 3.64, 2.02), (3.75, 3.40, 1.85), (3.75, 3.40, 1.90), (3.85, 3.45, 1.90),
    (4.15, 3.70, 1.85), (3.75, 3.40, 1.91)
]

# 即时赔率
realtime = [
    (5.00, 3.95, 1.48), (4.80, 3.75, 1.65), (4.40, 3.75, 1.62), (5.00, 3.75, 1.67),
    (4.75, 4.10, 1.67), (5.00, 3.95, 1.67), (5.25, 4.00, 1.65), (5.00, 4.00, 1.66),
    (5.00, 4.00, 1.67), (5.00, 3.90, 1.65), (5.00, 3.80, 1.68), (5.02, 3.98, 1.71),
    (5.00, 4.00, 1.66), (5.00, 3.80, 1.70), (4.87, 3.88, 1.67), (5.00, 4.00, 1.65),
    (5.00, 3.80, 1.68), (4.75, 3.90, 1.68), (4.75, 3.90, 1.68), (5.00, 3.90, 1.67),
    (4.75, 3.85, 1.67), (4.70, 3.90, 1.69), (5.00, 3.90, 1.68), (5.00, 3.80, 1.70),
    (5.05, 3.95, 1.70), (4.87, 3.85, 1.67), (4.75, 3.85, 1.70), (4.90, 3.90, 1.67),
    (5.00, 3.90, 1.68), (5.00, 3.90, 1.67)
]

def count_8_in_odds(odds_list):
    count = 0
    for odds in odds_list:
        for odd in odds:
            odd_str = f"{odd:.2f}"
            if odd_str.endswith('8'):
                count += 1
    return count

# 分别计算各赔率的8
initial_home = [o[0] for o in initial]
initial_draw = [o[1] for o in initial]
initial_away = [o[2] for o in initial]

realtime_home = [o[0] for o in realtime]
realtime_draw = [o[1] for o in realtime]
realtime_away = [o[2] for o in realtime]

print("=" * 60)
print("朗斯这场（洛里昂 vs 朗斯）各赔率的8变化分析")
print("=" * 60)

print("\n【主胜赔率】")
init_home_8 = count_8_in_odds([initial_home])
real_home_8 = count_8_in_odds([realtime_home])
print(f"  初盘8: {init_home_8}")
print(f"  即时8: {real_home_8}")
print(f"  变化: {real_home_8 - init_home_8:+d}")

print("\n【平局赔率】")
init_draw_8 = count_8_in_odds([initial_draw])
real_draw_8 = count_8_in_odds([realtime_draw])
print(f"  初盘8: {init_draw_8}")
print(f"  即时8: {real_draw_8}")
print(f"  变化: {real_draw_8 - init_draw_8:+d}")

print("\n【客胜赔率】")
init_away_8 = count_8_in_odds([initial_away])
real_away_8 = count_8_in_odds([realtime_away])
print(f"  初盘8: {init_away_8}")
print(f"  即时8: {real_away_8}")
print(f"  变化: {real_away_8 - init_away_8:+d}")

print("\n【总计】")
init_total = init_home_8 + init_draw_8 + init_away_8
real_total = real_home_8 + real_draw_8 + real_away_8
print(f"  初盘8总数: {init_total}")
print(f"  即时8总数: {real_total}")
print(f"  总变化: {real_total - init_total:+d}")

print("\n" + "=" * 60)
print("结论")
print("=" * 60)
print(f"客胜赔率的8变化: {real_away_8 - init_away_8:+d}")
print("（V7预测是客胜，所以应该看客胜赔率的8变化）")
