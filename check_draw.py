# 检查各场平赔变化
import os
import re

base = '分析模板/3.12'
for f in sorted(os.listdir(base)):
    if '源数据' in f:
        with open(f'{base}/{f}', 'r', encoding='utf-8') as file:
            content = file.read()
        
        # 找澳门心水
        macao = ''
        if '澳门心水' in content:
            macao_match = re.search(r'澳门心水[:：]\s*(.+)', content)
            if macao_match:
                macao = macao_match.group(1).strip()[:30]
        
        # 提取初始和即时平赔
        initial_match = re.search(r'initial_odds.*?\[(.*?)\]', content)
        realtime_match = re.search(r'realtime_odds.*?\[(.*?)\]', content)
        
        if initial_match and realtime_match:
            # 提取所有平赔
            initial_draw = re.findall(r'\d+\.\d+', initial_match.group(1))
            realtime_draw = re.findall(r'\d+\.\d+', realtime_match.group(1))
            
            up = sum(1 for i in range(len(initial_draw)) if i < len(realtime_draw) and float(realtime_draw[i]) > float(initial_draw[i]))
            down = sum(1 for i in range(len(initial_draw)) if i < len(realtime_draw) and float(realtime_draw[i]) < float(initial_draw[i]))
            
            print(f"{f[:6]} | 平:升{up}/降{down}/共{len(initial_draw)}家 | {macao}")
