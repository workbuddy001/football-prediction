# 澳门推荐和局 vs 平赔变化不一致分析
print('=' * 60)
print('澳门心水推荐和局 vs 澳门赔率变化不一致分析')
print('=' * 60)

# 数据：(比赛, 澳门心水, 平升比例, 平降比例, 实际结果)
data = [
    ('周四002', '和局', 0.20, 0.80, '和局'),  # 降多，一致
    ('周四003', '和局', 0.93, 0.07, '客胜'),  # 升多，不一致
    ('周四004', '和局', 0.97, 0.03, '客胜'),  # 升多，不一致
    ('周四007', '和局', 1.00, 0.00, '和局'),  # 升多，不一致(防平)
    ('周四009', '和局', 0.87, 0.13, '主胜'),  # 升多，不一致
    ('周四011', '和局', 1.00, 0.00, '和局'),  # 升多，不一致(防平)
]

print()
print('澳门推荐和局 + 平赔变化统计:')
print('-' * 60)

# 一致：澳门推荐和局 + 平降多(>=50%)
consistent = [d for d in data if d[3] >= 0.5]  # 平降>=50%
consistent_hit = sum(1 for d in consistent if d[4] == '和局')

# 不一致：澳门推荐和局 + 平升多(>=50%)
inconsistent = [d for d in data if d[2] >= 0.5]  # 平升>=50%
inconsistent_hit_draw = sum(1 for d in inconsistent if d[4] == '和局')
inconsistent_hit_not = sum(1 for d in inconsistent if d[4] != '和局')

print(f'1. 一致情况 (澳门和局 + 平降>=50%):')
for d in consistent:
    status = '一致' if d[3] >= 0.5 else '不一致'
    result = '命中' if d[4] == '和局' else '错'
    print(f'   {d[0]}: 平升{d[2]*100:.0f}%/降{d[3]*100:.0f}%, 实际{d[4]} {result}')
if consistent:
    print(f'   统计: {len(consistent)}场, 命中{consistent_hit}场, 准确率{consistent_hit/len(consistent)*100:.0f}%')
else:
    print(f'   统计: 0场')

print()
print(f'2. 不一致情况 (澳门和局 + 平升>=50%):')
for d in inconsistent:
    trend = '排除和局' if d[2] >= 0.7 else '防平'
    result = '命中' if d[4] == '和局' else '错'
    print(f'   {d[0]}: 平升{d[2]*100:.0f}%/降{d[3]*100:.0f}%, {trend}, 实际{d[4]} {result}')
if inconsistent:
    print(f'   统计: {len(inconsistent)}场, 命中{len(inconsistent)-inconsistent_hit_not}场, 准确率{(len(inconsistent)-inconsistent_hit_not)/len(inconsistent)*100:.0f}%')

print()
print('=' * 60)
print('结论:')
print('=' * 60)
if consistent:
    print(f'- 一致时(澳门和局+平降): {consistent_hit}/{len(consistent)} = {consistent_hit/len(consistent)*100:.0f}%')
if inconsistent:
    print(f'- 不一致时(澳门和局+平升): {len(inconsistent)-inconsistent_hit_not}/{len(inconsistent)} = {(len(inconsistent)-inconsistent_hit_not)/len(inconsistent)*100:.0f}%')
