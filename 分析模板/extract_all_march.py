"""
提取3.12-3.17所有比赛数据
"""
import os
import re
import json

def extract_from_file(filepath):
    """从源数据文件提取信息"""
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
    except:
        return None
    
    # 提取编号
    num_match = re.search(r'编号：(\w+)\|', content)
    if not num_match:
        return None
    num = num_match.group(1)
    
    # 提取对阵
    match_match = re.search(r'对阵：([^\|]+)', content)
    if not match_match:
        return None
    match = match_match.group(1).strip()
    
    # 提取日期
    date_match = re.search(r'比赛时间：(\d+\.\d+\.\d+)', content)
    if not date_match:
        return None
    date = date_match.group(1).replace('2026.', '3.').replace('.', '-')
    
    # 提取V7预测
    v7_match = re.search(r'V7推荐[：:]\s*([主胜平局客胜]+)', content)
    v7 = v7_match.group(1) if v7_match else ""
    
    # 提取置信度
    conf_match = re.search(r'置信度[：:]\s*(\d+)%', content)
    conf = int(conf_match.group(1)) if conf_match else 0
    
    # 提取胜率差
    diff_match = re.search(r'主队胜率[-–]客队胜率[=：]\s*([+-]?\d+)%', content)
    diff = int(diff_match.group(1)) if diff_match else 0
    
    # 提取8变化
    # 主胜8变化
    h8_match = re.search(r'主胜8[：:]\s*(\d+)\s*→\s*(\d+)', content)
    h8_change = int(h8_match.group(2)) - int(h8_match.group(1)) if h8_match else 0
    
    # 平局8变化
    d8_match = re.search(r'平局8[：:]\s*(\d+)\s*→\s*(\d+)', content)
    d8_change = int(d8_match.group(2)) - int(d8_match.group(1)) if d8_match else 0
    
    # 客胜8变化
    a8_match = re.search(r'客胜8[：:]\s*(\d+)\s*→\s*(\d+)', content)
    a8_change = int(a8_match.group(2)) - int(a8_match.group(1)) if a8_match else 0
    
    # 提取实际结果
    actual_match = re.search(r'实际结果[：:]\s*([主胜平局客胜]+)', content)
    actual = actual_match.group(1) if actual_match else ""
    
    # 提取比分
    score_match = re.search(r'比分[：:]\s*(\d+[-:]\d+)', content)
    score = score_match.group(1) if score_match else ""
    
    return {
        'date': date,
        'num': num,
        'match': match,
        'v7': v7,
        'conf': conf,
        'diff': diff,
        'h8': h8_change,
        'd8': d8_change,
        'a8': a8_change,
        'actual': actual,
        'score': score
    }

# 收集所有比赛
all_matches = []

for day in ['3.12', '3.13', '3.14', '3.15', '3.16', '3.17']:
    day_dir = f'd:/work/workbuddy/足球预测/分析模板/{day}'
    if not os.path.exists(day_dir):
        continue
    
    for f in os.listdir(day_dir):
        if f.endswith('_源数据.md'):
            filepath = os.path.join(day_dir, f)
            data = extract_from_file(filepath)
            if data:
                all_matches.append(data)

# 按日期排序
all_matches.sort(key=lambda x: (x['date'], x['num']))

# 输出JSON
print(json.dumps(all_matches, ensure_ascii=False, indent=2))
