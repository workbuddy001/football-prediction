import os, re

for d in ['3.10', '3.11']:
    for f in os.listdir(d):
        if f.endswith('_源数据.md'):
            content = open(f'{d}/{f}', encoding='utf-8').read()
            m = re.search(r'编号：(\w+\d+)\|', content)
            if m:
                print(f'{m.group(1)}')
