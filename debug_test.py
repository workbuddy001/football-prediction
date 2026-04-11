# 调试测试
import os
import re

def extract_odds_block(content, keyword):
    start = content.find(keyword)
    if start < 0:
        return ""
    end = content.find('```', start)
    if end < 0:
        end = len(content)
    return content[start:end]

filepath = '分析模板/3.14/周六001_中国女vs中国台女_源数据.md'
with open(filepath, 'r', encoding='utf-8') as file:
    content = file.read()

# 澳门推荐
macao_match = re.search(r'澳门推荐\s*\|\s*(\S+)', content)
macao_tip = macao_match.group(1).strip() if macao_match else ""
print(f"澳门推荐: {macao_tip}")

# realtime_odds
rt_block = extract_odds_block(content, 'realtime_odds')
odds_match = re.findall(r'\(\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*\)', rt_block)
print(f"realtime_odds: {len(odds_match)} 组")
if odds_match:
    print(f"第一组: {odds_match[0]}")

# initial_odds
init_block = extract_odds_block(content, 'initial_odds')
init_odds = re.findall(r'\(\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*\)', init_block)
print(f"initial_odds: {len(init_odds)} 组")
if init_odds:
    print(f"第一组: {init_odds[0]}")

# 球队名
f = "周六001_中国女vs中国台女_源数据.md"
teams = f.split('_')[1].split('vs')
home_team = teams[0].strip()
away_team = teams[1].replace('_源数据', '').strip()
code = f.split('_')[0]

print(f"\n主队: {home_team}")
print(f"客队: {away_team}")
print(f"编号: {code}")

# 检查macao_tip是否匹配
print(f"\n澳门推荐包含主队? {home_team in macao_tip}")
print(f"澳门推荐包含'赢'? {'赢' in macao_tip or '贏' in macao_tip}")
