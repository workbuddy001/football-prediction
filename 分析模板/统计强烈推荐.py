# 统计强烈推荐的场次
import re
content = open('final_retrospect.py', 'r', encoding='utf-8').read()

# 找到所有强烈推荐的原因
matches = re.findall(r'推荐: 强烈推荐.*?原因: ([^\n]+)', content, re.DOTALL)
print("强烈推荐原因分布：")
for m in set(matches):
    count = matches.count(m)
    print(f"  {m}: {count}场")
