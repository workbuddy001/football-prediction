import re

filepath = '3.14/周六010_考文垂vs南安普敦_源数据.md'
with open(filepath, encoding='utf-8') as f:
    content = f.read()

# 测试正则
num_match = re.search(r'编号：(\w+)\|', content)
print("num_match:", num_match.group(1) if num_match else None)

home_match = re.search(r'\| 主队 \|\s*(.+)', content)
print("home_match:", home_match.group(1).strip() if home_match else None)

home_rate_match = re.search(r'主队近况.*?胜率\s*(\d+)%', content)
print("home_rate_match:", home_rate_match.group(1) if home_rate_match else None)

# 初盘
init_match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
print("init_match:", bool(init_match))

if init_match:
    print("init content:", init_match.group(1)[:100])
