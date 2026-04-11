# 详细分析所有比赛的澳门盘变化
print('=' * 80)
print('澳门心水 vs 澳门盘赔率变化详细分析')
print('=' * 80)

# 从源数据中提取澳门盘变化
# 周四001: 澳门推荐客胜, 初始客胜1.61, 即时2.18 → 升
# 周四002: 澳门推荐和局
# 周四003: 澳门推荐和局
# 周四004: 澳门推荐和局
# 周四005: 澳门推荐客胜, 初始客胜1.65, 即时1.78 → 降
# 周四006: 澳门推荐主胜, 初始主胜1.68, 即时1.74 → 升
# 周四007: 澳门推荐和局
# 周四008: 澳门推荐客胜, 初始客胜2.08, 即时2.16 → 升(诱盘!)
# 周四009: 澳门推荐和局
# 周四010: 澳门推荐客胜, 初始客胜5.60, 即时5.55 → 降
# 周四011: 澳门推荐和局
# 周四012: 澳门推荐客胜, 初始客胜11.0, 即时13.0 → 升(诱盘!)

data = [
    ('周四001', '客胜', '主胜升', '客胜降', '和局', 1.61, 2.18),  # 澳门推荐客胜,客胜升
    ('周四002', '和局', '-', '-', '和局', 0, 0),
    ('周四003', '和局', '-', '-', '客胜', 0, 0),
    ('周四004', '和局', '-', '-', '客胜', 0, 0),
    ('周四005', '客胜', '主胜升', '客胜降', '主胜', 1.65, 1.78),  # 澳门推荐客胜,客胜降
    ('周四006', '主胜', '主胜升', '客胜升', '主胜', 1.68, 1.74),  # 澳门推荐主胜,主胜升(诱盘!)
    ('周四007', '和局', '-', '-', '和局', 0, 0),
    ('周四008', '客胜', '主胜升', '客胜升', '主胜', 2.08, 2.16),  # 澳门推荐客胜,客胜升(诱盘!)
    ('周四009', '和局', '-', '-', '主胜', 0, 0),
    ('周四010', '客胜', '主胜降', '客胜降', '客胜', 5.60, 5.55),  # 澳门推荐客胜,客胜降
    ('周四011', '和局', '-', '-', '和局', 0, 0),
    ('周四012', '客胜', '主胜降', '客胜升', '和局', 11.0, 13.0),  # 澳门推荐客胜,客胜升(诱盘!)
]

print()
print('所有比赛详细:')
print('-' * 80)
print(f"{'比赛':<8} {'澳门心水':<8} {'澳门盘变化':<15} {'初始→即时':<15} {'实际':<8} {'结果'}")
print('-' * 80)

for d in data:
    code = d[0]
    macao = d[1]
    home_ch = d[2]
    away_ch = d[3]
    actual = d[4]
    init = d[5]
    real = d[6]
    
    if init > 0:
        change_str = f"{init}→{real}"
    else:
        change_str = "-"
    
    # 判断结果
    if macao == '和局':
        result = '命中' if actual == '和局' else '错'
    else:
        result = '命中' if actual == macao else '错'
    
    print(f"{code:<8} {macao:<8} {home_ch}/{away_ch:<12} {change_str:<15} {actual:<8} {result}")

print()
print('=' * 80)
print('澳门推荐非和局时的分析:')
print('=' * 80)

# 筛选非和局推荐
non_draw = [d for d in data if d[1] != '和局']

# 分析
print()
print('按澳门推荐分类:')
print('-' * 60)

# 客胜推荐
away_rec = [d for d in non_draw if d[1] == '客胜']
away_hit = sum(1 for d in away_rec if d[4] == '客胜')
print(f'澳门推荐客胜: {len(away_rec)}场, 命中{away_hit}场, 准确率{away_hit/len(away_rec)*100:.0f}%' if away_rec else '0场')

# 主胜推荐
home_rec = [d for d in non_draw if d[1] == '主胜']
home_hit = sum(1 for d in home_rec if d[4] == '主胜')
print(f'澳门推荐主胜: {len(home_rec)}场, 命中{home_hit}场, 准确率{home_hit/len(home_rec)*100:.0f}%' if home_rec else '0场')

print()
print('按澳门盘变化分类:')
print('-' * 60)

# 一致：客胜推荐+客胜降 或 主胜推荐+主胜降
# 诱盘：客胜推荐+客胜升 或 主胜推荐+主胜升
away_down = [d for d in non_draw if d[1]=='客胜' and d[3]=='客胜降']  # 客胜降
away_up = [d for d in non_draw if d[1]=='客胜' and d[3]=='客胜升']    # 客胜升(诱盘)
home_down = [d for d in non_draw if d[1]=='主胜' and d[2]=='主胜降']  # 主胜降
home_up = [d for d in non_draw if d[1]=='主胜' and d[2]=='主胜升']    # 主胜升(诱盘)

print(f'客胜推荐+客胜降: {len(away_down)}场, 命中{sum(1 for d in away_down if d[4]=="客胜")}场')
for d in away_down:
    print(f'   {d[0]}: 客胜{d[5]}→{d[6]}, 实际{d[4]}')

print()
print(f'客胜推荐+客胜升(诱盘): {len(away_up)}场, 命中{sum(1 for d in away_up if d[4]=="客胜")}场')
for d in away_up:
    result = '主胜' if d[4] != '客胜' else '客胜'
    print(f'   {d[0]}: 客胜{d[5]}→{d[6]}, 实际{d[4]}({result})')

print()
print(f'主胜推荐+主胜降: {len(home_down)}场, 命中{sum(1 for d in home_down if d[4]=="主胜")}场')
for d in home_down:
    print(f'   {d[0]}: 主胜{d[5]}→{d[6]}, 实际{d[4]}')

print()
print(f'主胜推荐+主胜升(诱盘): {len(home_up)}场, 命中{sum(1 for d in home_up if d[4]=="主胜")}场')
for d in home_up:
    result = '主胜' if d[4] == '主胜' else '主胜'
    print(f'   {d[0]}: 主胜{d[5]}→{d[6]}, 实际{d[4]}({result})')

print()
print('=' * 80)
print('关键发现:')
print('=' * 80)
print('1. 澳门推荐客胜+客胜降 → 真实看好客胜 (2场中1场=50%)')
print('2. 澳门推荐客胜+客胜升 → 诱盘分散 (2场都出主胜/和局)')
print('3. 澳门推荐主胜+主胜升 → 诱盘 (1场出主胜)')
print('4. 样本量较小，需更多数据验证')
