import os
import re
import json

# 读取所有源数据文件
matches = []
for root, dirs, files in os.walk('.'):
    for f in files:
        if '源数据.md' in f:
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    
                    # 提取比赛编号
                    match_id = re.search(r'(\w+\d+_\w+vs\w+)', f)
                    if not match_id:
                        continue
                    match_name = match_id.group(1)
                    
                    # 提取8变化
                    eight_match = re.search(r'初盘(\d+) → 即时(\d+)', content)
                    if not eight_match:
                        continue
                    initial = int(eight_match.group(1))
                    realtime = int(eight_match.group(2))
                    diff = realtime - initial
                    
                    # 提取胜率
                    home_rate = re.search(r'\| 主队近况 \|.*胜率(\d+)%', content)
                    away_rate = re.search(r'\| 客队近况 \|.*胜率(\d+)%', content)
                    
                    if home_rate and away_rate:
                        h_rate = int(home_rate.group(1))
                        a_rate = int(away_rate.group(1))
                        rate_diff = h_rate - a_rate
                        
                        matches.append({
                            'match': match_name,
                            'diff': diff,
                            'rate_diff': rate_diff,
                            'home_rate': h_rate,
                            'away_rate': a_rate
                        })
            except:
                pass

# 筛选8变化正数 + 状态焦灼(胜率差<=20%)
print('=' * 70)
print('8变化正数 + 状态焦灼(胜率差<=20%)的比赛:')
print('=' * 70)

positive_diff = [m for m in matches if m['diff'] > 0]
print(f'\n总共 {len(positive_diff)} 场8变化正数的比赛\n')

# 按胜率差分类
close = [m for m in positive_diff if abs(m['rate_diff']) <= 20]  # 焦灼
not_close = [m for m in positive_diff if abs(m['rate_diff']) > 20]  # 不焦灼

print(f'状态焦灼(|胜率差|<=20%): {len(close)} 场')
for m in sorted(close, key=lambda x: x['diff'], reverse=True):
    print(f"  {m['match']}: 8变化+{m['diff']}, 胜率差{m['rate_diff']}% (主{m['home_rate']}% vs 客{m['away_rate']}%)")

print(f'\n状态不焦灼(|胜率差|>20%): {len(not_close)} 场')
for m in sorted(not_close, key=lambda x: x['diff'], reverse=True)[:10]:
    print(f"  {m['match']}: 8变化+{m['diff']}, 胜率差{m['rate_diff']}%")
