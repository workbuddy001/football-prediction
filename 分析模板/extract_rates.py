"""
从源数据中提取所有比赛的胜率信息
"""
import os
import re

def extract_rates_from_file(filepath):
    """从源数据文件中提取胜率"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取比赛编号
    match_id = re.search(r'编号：(\w+\d+)\|', content)
    if not match_id:
        return None
    match_id = match_id.group(1)

    # 提取主客队
    teams = re.search(r'主队\s*\|\s*(\S+).*客队\s*\|\s*(\S+)', content, re.DOTALL)
    if not teams:
        return None
    home_team = teams.group(1).strip()
    away_team = teams.group(2).strip()

    # 提取主客队胜率
    home_rate_match = re.search(r'主队近况.*?胜率(\d+)%', content)
    away_rate_match = re.search(r'客队近况.*?胜率(\d+)%', content)

    if not home_rate_match or not away_rate_match:
        return None

    home_rate = int(home_rate_match.group(1))
    away_rate = int(away_rate_match.group(1))

    return {
        'id': match_id,
        'match': f"{home_team} vs {away_team}",
        'home_rate': home_rate,
        'away_rate': away_rate,
        'rate_diff': home_rate - away_rate
    }

# 处理3.10目录
print("3.10 比赛胜率核对:")
print("-" * 60)
for filename in sorted(os.listdir('3.10')):
    if filename.endswith('_源数据.md'):
        result = extract_rates_from_file(f'3.10/{filename}')
        if result:
            print(f"{result['id']}: {result['match']}")
            print(f"  主队{result['home_rate']}% vs 客队{result['away_rate']}%")
            print(f"  胜率差: {result['rate_diff']:+d}%")

print("\n" + "=" * 60)
print("3.11 比赛胜率核对:")
print("-" * 60)
for filename in sorted(os.listdir('3.11')):
    if filename.endswith('_源数据.md'):
        result = extract_rates_from_file(f'3.11/{filename}')
        if result:
            print(f"{result['id']}: {result['match']}")
            print(f"  主队{result['home_rate']}% vs 客队{result['away_rate']}%")
            print(f"  胜率差: {result['rate_diff']:+d}%")
