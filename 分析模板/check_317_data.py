import re

with open('analyze_317_detailed.py', encoding='utf-8') as f:
    content = f.read()

# 提取所有比赛
matches = re.findall(r'"id":\s*"([^"]+)".*?"match":\s*"([^"]+)"', content)
for m in matches[:15]:
    print(m[0], m[1])
print('...')
print('Total:', len(matches))
