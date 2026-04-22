import json
import os

# 模拟 _build_odds_hitrate 的统计逻辑
scores = {}
scores_file = '分析模板/_scores.json'
if os.path.exists(scores_file):
    with open(scores_file, encoding='utf-8') as f:
        scores = json.load(f)

overall = {}   # overall[goal] = [total, hits]
exact = {}     # exact[goal] = {赔率值: [total, hits]}

for key, record in scores.items():
    tg = record.get('total_goals')
    if tg is None:
        continue
    tg = int(tg)

    tg_odds = record.get('total_goals_odds', {})
    if not tg_odds:
        continue

    for goal in range(0, 8):
        od_val = tg_odds.get('%d球' % goal)
        if not od_val:
            continue
        try:
            val = round(float(od_val), 2)
        except:
            continue

        # overall
        if goal not in overall:
            overall[goal] = [0, 0]
        overall[goal][0] += 1
        if tg == goal:
            overall[goal][1] += 1

        # exact: 按精确赔率值统计
        if goal not in exact:
            exact[goal] = {}
        if val not in exact[goal]:
            exact[goal][val] = [0, 0]
        exact[goal][val][0] += 1
        if tg == goal:
            exact[goal][val][1] += 1

print("=== 1球的精确统计 ===")
if 1 in exact:
    print(f"1球赔率分布:")
    for val, stats in sorted(exact[1].items()):
        rate = round(stats[1] / stats[0] * 100, 1) if stats[0] > 0 else 0
        print(f"  {val}: {stats[1]}/{stats[0]} = {rate}%")
else:
    print("没有1球的统计")

print("\n=== 1球=5.25 的详细信息 ===")
if 1 in exact and 5.25 in exact[1]:
    stats = exact[1][5.25]
    rate = round(stats[1] / stats[0] * 100, 1) if stats[0] > 0 else 0
    print(f"总场次: {stats[0]}")
    print(f"命中次数: {stats[1]}")
    print(f"命中率: {rate}%")
else:
    print("没有 1球=5.25 的历史数据")

print("\n=== 3球的精确统计 ===")
if 3 in exact:
    print(f"3球赔率分布:")
    for val, stats in sorted(exact[3].items()):
        rate = round(stats[1] / stats[0] * 100, 1) if stats[0] > 0 else 0
        print(f"  {val}: {stats[1]}/{stats[0]} = {rate}%")
