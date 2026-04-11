import re

with open('3.16/周一001_海尔蒙特vs坎布尔_源数据.md', 'r', encoding='utf-8') as f:
    content = f.read()

# 尝试匹配
match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
print('Match 1:', match is not None)

match2 = re.search(r'```python\s*initial_odds\s*=\s*\[(.*?)\]```', content, re.DOTALL)
print('Match 2:', match2 is not None)

# 提取所有赔率tuple
match3 = re.findall(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', content)
print('Tuples found:', len(match3))
if match3:
    print('First:', match3[0])

# 找到initial_odds的位置
idx = content.find('initial_odds')
print('initial_odds at:', idx)
if idx > 0:
    print('Context:', content[idx:idx+100])
