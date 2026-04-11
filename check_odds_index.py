# -*- coding: utf-8 -*-
import os, re, glob

folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '分析模板', '3.28')
files = sorted(glob.glob(os.path.join(folder, '*_源数据.md')))

for f in files:
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    
    # 找初盘赔率代码块
    init_match = re.search(r'##.*?初盘赔率.*?```python\n(.*?)```', content, re.DOTALL)
    # 找即时赔率代码块
    curr_match = re.search(r'##.*?即时赔率.*?```python\n(.*?)```', content, re.DOTALL)
    
    fname = os.path.basename(f)
    m_id = fname.split('_')[0]
    
    init_lines = []
    curr_lines = []
    
    if init_match:
        block = init_match.group(1)
        init_lines = [l.strip() for l in block.strip().split('\n') if l.strip().startswith('(')]
    
    if curr_match:
        block = curr_match.group(1)
        curr_lines = [l.strip() for l in block.strip().split('\n') if l.strip().startswith('(')]
    
    # 检查索引2是否是澳门
    init_idx2 = init_lines[2] if len(init_lines) > 2 else 'N/A'
    curr_idx2 = curr_lines[2] if len(curr_lines) > 2 else 'N/A'
    
    # 找澳门行（包含*门的）
    init_macau = [l for l in init_lines if '*门' in l]
    curr_macau = [l for l in curr_lines if '*门' in l]
    
    init_macau_idx = init_lines.index(init_macau[0]) if init_macau else -1
    curr_macau_idx = curr_lines.index(curr_macau[0]) if curr_macau else -1
    
    print(f'{m_id} | 初盘澳门索引={init_macau_idx} | 即时澳门索引={curr_macau_idx} | 初盘总行数={len(init_lines)} | 即时总行数={len(curr_lines)}')
