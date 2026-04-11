import os, re

print("3.10 比赛胜率核对:")
print("-" * 60)
for d in ['3.10', '3.11']:
    print(f"\n=== {d} ===")
    for f in sorted(os.listdir(d)):
        if f.endswith('_源数据.md'):
            content = open(f'{d}/{f}', encoding='utf-8').read()

            # 提取编号
            m = re.search(r'编号：(\w+\d+)', content)
            if not m:
                continue
            match_id = m.group(1)

            # 提取主客队
            teams = re.search(r'主队\s*\|\s*(\S+).*客队\s*\|\s*(\S+)', content, re.DOTALL)
            if not teams:
                continue
            home_team = teams.group(1).strip()
            away_team = teams.group(2).strip()

            # 提取胜率
            home_rate_match = re.search(r'主队近况.*?胜率(\d+)%', content)
            away_rate_match = re.search(r'客队近况.*?胜率(\d+)%', content)

            if not home_rate_match or not away_rate_match:
                continue

            home_rate = int(home_rate_match.group(1))
            away_rate = int(away_rate_match.group(1))
            rate_diff = home_rate - away_rate

            print(f"{match_id}: {home_team} vs {away_team}")
            print(f"  主队{home_rate}% vs 客队{away_rate}% → 胜率差: {rate_diff:+d}%")
