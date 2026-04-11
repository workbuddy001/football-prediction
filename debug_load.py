# 调试加载函数
import os
import re

def load_match_data_from_folder(folder):
    """从文件夹加载比赛数据"""
    matches = []
    base = f'分析模板/{folder}'
    
    print(f"检查文件夹: {base}")
    if not os.path.exists(base):
        print(f"  文件夹不存在!")
        return matches
    
    files = [f for f in os.listdir(base) if '源数据' in f]
    print(f"  找到 {len(files)} 个源数据文件")
    
    for f in files[:2]:  # 只处理前2个
        filepath = f'{base}/{f}'
        print(f"  处理: {f}")
        
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # 提取澳门推荐
        macao_match = re.search(r'澳门推荐[:：]\s*(.+)', content)
        if not macao_match:
            macao_match = re.search(r'澳门心水[:：]\s*(.+)', content)
        
        if macao_match:
            print(f"    澳门推荐: {macao_match.group(1).strip()[:30]}")
        else:
            print(f"    澳门推荐: 未找到")
        
        # 提取即时赔率
        realtime_match = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if realtime_match:
            odds_str = realtime_match.group(1)
            odds_match = re.findall(r'\((\d+\.\d+),(\d+\.\d+),(\d+\.\d+)\)', odds_str)
            print(f"    即时赔率: {len(odds_match)} 组")
            if odds_match:
                print(f"    第一组: {odds_match[0]}")
        else:
            print(f"    即时赔率: 未找到")
    
    return matches

load_match_data_from_folder('3.14')
