# 筛选置信度>=55%的比赛
import re

content = open('result.txt', 'r', encoding='utf-8').read()

# 提取置信度>=55%的比赛
matches = re.findall(r'【([^】]+)】.*?V7预测: ([^\)]+).*?置信度: (\d+)%.*?实际结果: ([^\[]+)\[([^\]]+)\]', content, re.DOTALL)

print('=' * 80)
print('置信度>=55%的比赛（共15场）')
print('=' * 80)

count = 0
for m in matches:
    name, pred, conf, actual, result = m
    conf = int(conf)
    if conf >= 55:
        count += 1
        status = 'O' if result == '对' else 'X'
        print(f'{count}. {name}')
        print(f'   预测: {pred.strip()} ({conf}%)  实际: {actual.strip()}  [{status}]')
        print()
