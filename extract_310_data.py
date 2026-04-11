import os
import re

DATA_DIR = 'd:/work/workbuddy/足球预测/分析模板/3.10'
files = [
    '周二001_印度女vs中国台女_源数据.md',
    '周二002_日本女vs越南女_源数据.md',
    '周二003_町田泽维vs江原FC_源数据.md',
    '周二004_布里兰vs墨尔本城_源数据.md',
    '周二005_加拉塔萨vs利物浦_源数据.md',
    '周二006_朴次茅斯vs斯旺西_源数据.md',
    '周二007_亚特兰大vs拜仁_源数据.md',
    '周二008_马竞vs热刺_源数据.md',
    '周二009_纽卡斯尔vs巴萨_源数据.md',
]

print("="*120)
print("3.10比赛完整数据列表")
print("="*120)
print(f"{'编号':<8} {'对阵':<22} {'澳门心水':<10} {'近况差':<6} {'初盘(胜/平/负)':<22} {'即时(胜/平/负)':<22} {'变化(H/D/A)':<18}")
print("-"*120)

for f in files:
    path = os.path.join(DATA_DIR, f)
    with open(path, 'r', encoding='utf-8') as fp:
        content = fp.read()
    
    lines = content.split('\n')
    
    # 找编号
    mid = ''
    for line in lines:
        if '编号：' in line:
            m = re.search(r'编号：(.+?)\|', line)
            if m:
                mid = m.group(1).strip()
                break
    
    # 找主客队
    home = away = ''
    for line in lines:
        if '| 主队 |' in line and line.count('|') == 3:
            m = re.search(r'\| 主队 \|\s*(.+?)\s*\|', line)
            if m: home = m.group(1).strip()
        if '| 客队 |' in line and line.count('|') == 3:
            m = re.search(r'\| 客队 \|\s*(.+?)\s*\|', line)
            if m: away = m.group(1).strip()
    
    # 找澳门推荐
    macao = ''
    for line in lines:
        if '| 澳门推荐 |' in line and line.count('|') == 3:
            m = re.search(r'\| 澳门推荐 \|\s*(.+?)\s*\|', line)
            if m: macao = m.group(1).strip()
    
    # 澳门方向
    if home in macao:
        macao_dir = '主队'
    elif away in macao:
        macao_dir = '客队'
    elif '和局' in macao or '平局' in macao:
        macao_dir = '和局'
    else:
        macao_dir = '未知'
    
    # 找近况走势
    home_trend = away_trend = ''
    for line in lines:
        if '| 主队近况走势 |' in line and line.count('|') == 3:
            m = re.search(r'\| 主队近况走势 \|\s*(.+?)\s*\|', line)
            if m: home_trend = m.group(1).strip()
        if '| 客队近况走势 |' in line and line.count('|') == 3:
            m = re.search(r'\| 客队近况走势 \|\s*(.+?)\s*\|', line)
            if m: away_trend = m.group(1).strip()
    
    # 计算近况差
    score_map = {'W': 3, 'D': 1, 'L': 0}
    def calc_score(trend):
        if not trend: return 0
        recent = trend[:5]
        scores = []
        for i, c in enumerate(recent):
            if c in score_map:
                w = 2 if i == 0 else 1
                scores.append(score_map[c] * w)
        return sum(scores) if scores else 0
    
    home_score = calc_score(home_trend)
    away_score = calc_score(away_trend)
    score_diff = home_score - away_score
    
    # 找竞彩赔率（初盘和即时）
    init_h = init_d = init_a = 0
    rt_h = rt_d = rt_a = 0
    in_change = False
    for line in lines:
        if '赔率变动对比' in line:
            in_change = True
            continue
        if in_change and '竞*官*' in line:
            parts = line.split('|')
            if len(parts) >= 11:
                try:
                    init_h = float(parts[2].strip())
                    rt_h = float(parts[3].strip())
                    init_d = float(parts[5].strip())
                    rt_d = float(parts[6].strip())
                    init_a = float(parts[8].strip())
                    rt_a = float(parts[9].strip())
                except: pass
            in_change = False
    
    # 计算变化
    h_chg = (rt_h - init_h) / init_h * 100 if init_h else 0
    d_chg = (rt_d - init_d) / init_d * 100 if init_d else 0
    a_chg = (rt_a - init_a) / init_a * 100 if init_a else 0
    
    match_name = f"{home[:6]}vs{away[:6]}"
    init_str = f"{init_h:.2f}/{init_d:.2f}/{init_a:.2f}"
    rt_str = f"{rt_h:.2f}/{rt_d:.2f}/{rt_a:.2f}"
    chg_str = f"H{h_chg:+.1f}% D{d_chg:+.1f}% A{a_chg:+.1f}%"
    
    print(f"{mid:<8} {match_name:<22} {macao_dir:<10} {score_diff:+d}       {init_str:<22} {rt_str:<22} {chg_str:<18}")
