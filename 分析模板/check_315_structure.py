import json

# Check 3.15 data structure
with open('matches_full_2026-03-15.json', encoding='utf-8') as f:
    data = json.load(f)

first_item = data[0]
print('编号:', first_item['编号'])
print('主队 vs 客队:', first_item['主队'], 'vs', first_item['客队'])
print()

# Check 欧赔数据
if '欧赔数据' in first_item:
    print('欧赔数据 fields:', list(first_item['欧赔数据'].keys())[:10])
    print('Sample:', first_item['欧赔数据'])

print()

# Check 数据分析
if '数据分析' in first_item:
    print('数据分析 fields:', list(first_item['数据分析'].keys())[:15])
    print('Sample:', first_item['数据分析'])
