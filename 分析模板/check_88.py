import re
import os

def get_last_2_digits(odds):
    s = f'{odds:.2f}'
    return s[-2:]

def extract_odds(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    init_match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if init_match:
        initial_odds = eval('[' + init_match.group(1) + ']')
    else:
        return None, None
    real_match = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if real_match:
        realtime_odds = eval('[' + real_match.group(1) + ']')
    else:
        return None, None
    return initial_odds, realtime_odds

# 检查所有3.13-3.15的比赛
found = []
for folder, day in [(r'd:\work\workbuddy\足球预测\分析模板\3.13', '周五'), 
                     (r'd:\work\workbuddy\足球预测\分析模板\3.14', '周六'),
                     (r'd:\work\workbuddy\足球预测\分析模板\3.15', '周日')]:
    files = [f for f in os.listdir(folder) if f.endswith('_源数据.md')]
    for f in sorted(files):
        filepath = os.path.join(folder, f)
        initial_odds, realtime_odds = extract_odds(filepath)
        if initial_odds and realtime_odds:
            # 检查即时盘三个选项
            for i, name in enumerate(['主胜', '平局', '客胜']):
                real = [o[i] for o in realtime_odds]
                for r in real:
                    if get_last_2_digits(r) == '88':
                        found.append(f'{f}: {name} = {r}')

print('找到末尾88的赔率:')
for x in found:
    print(x)
print(f'共找到 {len(found)} 个')
