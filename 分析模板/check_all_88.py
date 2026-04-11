import re, os

def get_last_2_digits(odds):
    s = f'{odds:.2f}'
    return s[-2:]

def count_ends_with_88(odds_list):
    return sum(1 for o in odds_list if get_last_2_digits(o) == '88')

def extract(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        c = f.read()
    m = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', c, re.DOTALL)
    if m:
        odds = eval('[' + m.group(1) + ']')
        all_o = []
        for o in odds:
            all_o.extend(o)
        return count_ends_with_88(all_o)
    return 0

# 检查所有比赛
folders = [
    (r'd:\work\workbuddy\足球预测\分析模板\3.13', '周五'),
    (r'd:\work\workbuddy\足球预测\分析模板\3.14', '周六'),
    (r'd:\work\workbuddy\足球预测\分析模板\3.15', '周日'),
]

results = []
for fld, day in folders:
    for f in os.listdir(fld):
        if not f.endswith('_源数据.md'): continue
        m = re.search(r'(周[一二三五六日])(\d+)', f)
        if not m: continue
        mid = f'{m.group(1)}{int(m.group(2)):03d}'
        cnt = extract(os.path.join(fld, f))
        if cnt > 0:
            results.append((mid, f, cnt))

print(f'47场比赛中共发现{len(results)}场有末尾88:')
for r in results[:10]:
    print(f'  {r[0]}: {r[1]} -> {r[2]}个')
if len(results) > 10:
    print(f'  ... 共{len(results)}场')
