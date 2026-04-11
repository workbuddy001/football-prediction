# 澳门推荐非和局 vs 澳门盘赔率变化不一致分析
print('=' * 70)
print('澳门心水推荐(主胜/客胜) vs 澳门盘赔率变化不一致分析')
print('=' * 70)

# 数据：(比赛, 澳门心水, 澳门主胜变化, 澳门客胜变化, 实际结果)
# 正数表示升赔，负数表示降赔
data = [
    ('周四001', '客胜', '升', '降', '和局'),  # 澳门推荐客胜，客胜升，主胜降，不一致
    ('周四002', '和局', '升', '降', '和局'),  # 澳门推荐和局，跳过
    ('周四003', '和局', '降', '升', '客胜'),  # 澳门推荐和局，跳过
    ('周四004', '和局', '升', '降', '客胜'),  # 澳门推荐和局，跳过
    ('周四005', '客胜', '升', '降', '主胜'),  # 澳门推荐客胜，客胜降，主胜升，不一致
    ('周四006', '主胜', '降', '升', '主胜'),  # 澳门推荐主胜，主胜降，一致
    ('周四007', '和局', '升', '升', '和局'),  # 澳门推荐和局，跳过
    ('周四008', '客胜', '升', '降', '主胜'),  # 澳门推荐客胜，客胜降，一致(诱盘指向)
    ('周四009', '和局', '降', '升', '主胜'),  # 澳门推荐和局，跳过
    ('周四010', '客胜', '降', '降', '客胜'),  # 澳门推荐客胜，客胜降，一致
    ('周四011', '和局', '降', '升', '和局'),  # 澳门推荐和局，跳过
    ('周四012', '客胜', '降', '升', '和局'),  # 澳门推荐客胜，客胜升，不一致
]

print()
print('详细分析:')
print('-' * 70)

# 筛选非和局推荐
non_draw = [d for d in data if d[1] != '和局']

consistent = []  # 一致：推荐主胜+主胜降 或 推荐客胜+客胜降
inconsistent = []  # 不一致：推荐主胜+主胜升 或 推荐客胜+客胜升

for d in non_draw:
    macao = d[1]
    home_change = d[2]
    away_change = d[3]
    actual = d[4]
    
    if macao == '主胜':
        if home_change == '降':
            consistent.append(d)
        else:  # home_change == '升'
            inconsistent.append(d)
    elif macao == '客胜':
        if away_change == '降':
            consistent.append(d)
        else:  # away_change == '升'
            inconsistent.append(d)

print(f'1. 一致情况 (推荐主胜+主胜降 或 推荐客胜+客胜降):')
consistent_hit = 0
for d in consistent:
    macao = d[1]
    actual = d[4]
    hit = (macao == actual)
    if hit:
        consistent_hit += 1
    status = '命中' if hit else '错'
    print(f'   {d[0]}: 澳门推荐{macao}, 主胜{d[2]}, 客胜{d[3]}, 实际{actual} {status}')
print(f'   统计: {len(consistent)}场, 命中{consistent_hit}场, 准确率{consistent_hit/len(consistent)*100:.0f}%' if consistent else '   统计: 0场')

print()
print(f'2. 不一致情况 (推荐主胜+主胜升 或 推荐客胜+客胜升):')
inconsistent_hit = 0
for d in inconsistent:
    macao = d[1]
    actual = d[4]
    hit = (macao == actual)
    if hit:
        inconsistent_hit += 1
    status = '命中' if hit else '错'
    print(f'   {d[0]}: 澳门推荐{macao}, 主胜{d[2]}, 客胜{d[3]}, 实际{actual} {status}')
if inconsistent:
    print(f'   统计: {len(inconsistent)}场, 命中{inconsistent_hit}场, 准确率{inconsistent_hit/len(inconsistent)*100:.0f}%')
else:
    print(f'   统计: 0场')

print()
print('=' * 70)
print('结论:')
print('=' * 70)
if consistent:
    print(f'- 一致时: {consistent_hit}/{len(consistent)} = {consistent_hit/len(consistent)*100:.0f}%')
if inconsistent:
    print(f'- 不一致时: {inconsistent_hit}/{len(inconsistent)} = {inconsistent_hit/len(inconsistent)*100:.0f}%')
