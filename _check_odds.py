import json
import glob

# 检查今天的原始JSON
files = sorted(glob.glob('分析模板/2026.04.17/*.json'))
print('JSON文件:', files)

# 检查是否有澳门字段
with open('分析模板/2026.04.17/matches_enhanced_2026-04-17.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f'共 {len(data)} 场比赛')
print()

# 检查第一场的赔率结构
m = data[0]
print(f"第一场: {m['match_num']}: {m['home']} vs {m['away']}")
print('赔率字段:', list(m.get('赔率', {}).keys()))

# 搜索所有包含澳门的字段
print('\n=== 搜索包含澳门的字段 ===')
has_macao = False
for m in data:
    odds = m.get('赔率', {})
    for k in odds.keys():
        if '澳门' in k or 'macao' in k.lower():
            print(f"{m['match_num']}: {k} = {odds[k]}")
            has_macao = True
            break

if not has_macao:
    print('没有找到澳门赔率字段！')
