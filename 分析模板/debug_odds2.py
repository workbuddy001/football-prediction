import re

with open('3.16/周一001_海尔蒙特vs坎布尔_源数据.md', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查提取
init_match = re.search(r'initial_odds = \[(.*?)\]', content, re.DOTALL)
print('Match found:', init_match is not None)
if init_match:
    odds_str = init_match.group(1)[:100]
    print('First 100 chars:', odds_str)

# 提取所有赔率tuple
tuples = re.findall(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', content)
print('Tuples count:', len(tuples))
if tuples:
    print('First tuple:', tuples[0])
