# -*- coding: utf-8 -*-
import os, re, glob

folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '分析模板', '3.28')
files = sorted(glob.glob(os.path.join(folder, '*_源数据.md')))

def calc_form_score(form_str):
    if not form_str or len(form_str) < 2:
        return 0
    score = 0
    for i, ch in enumerate(form_str[:5]):
        mult = 2 if i == 0 else 1
        if ch == 'W': score += 3 * mult
        elif ch == 'D': score += 1 * mult
    return score

def parse_section(content, section_name):
    pattern = r'##\s*.*?' + re.escape(section_name) + r'.*?\n```python\n(.*?)```'
    m = re.search(pattern, content, re.DOTALL)
    if m:
        return m.group(1)
    return ''

def get_odds_from_code_block(text, target_index=0):
    m = re.findall(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', text)
    if m and len(m) > target_index:
        return m[target_index]
    elif m:
        return m[-1]
    return None

def calc_changes(init, curr):
    """计算赔率变化百分比"""
    if not init or not curr:
        return 0, 0, 0, 0
    ih, id_, ia = float(init[0]), float(init[1]), float(init[2])
    ch, cd, ca = float(curr[0]), float(curr[1]), float(curr[2])
    h_chg = (ch - ih) / ih * 100
    d_chg = (cd - id_) / id_ * 100
    a_chg = (ca - ia) / ia * 100
    total_chg = abs(h_chg) + abs(d_chg) + abs(a_chg)
    return h_chg, d_chg, a_chg, total_chg

def calc_dispersion(jc_odds, am_odds):
    """计算竞彩vs澳门赔率离散度（百分比差值）"""
    if not jc_odds or not am_odds:
        return None
    jc_h, jc_d, jc_a = float(jc_odds[0]), float(jc_odds[1]), float(jc_odds[2])
    am_h, am_d, am_a = float(am_odds[0]), float(am_odds[1]), float(am_odds[2])
    # 用澳门赔率作为基准计算差值百分比
    disp_h = (jc_h - am_h) / am_h * 100
    disp_d = (jc_d - am_d) / am_d * 100
    disp_a = (jc_a - am_a) / am_a * 100
    return disp_h, disp_d, disp_a

def judge_dispersion(disp):
    """根据离散度判断两家一致性"""
    if disp is None:
        return '?', '?'
    disp_h, disp_d, disp_a = disp
    # 取三向绝对差值的平均值作为总体离散度
    avg_disp = (abs(disp_h) + abs(disp_d) + abs(disp_a)) / 3
    if avg_disp < 2:
        return f'{avg_disp:.1f}%', '高度一致'
    elif avg_disp < 5:
        return f'{avg_disp:.1f}%', '基本一致'
    elif avg_disp < 10:
        return f'{avg_disp:.1f}%', '轻度分歧'
    elif avg_disp < 15:
        return f'{avg_disp:.1f}%', '明显分歧'
    else:
        return f'{avg_disp:.1f}%', '严重分歧'

def compare_jingcai_macau(jc_h, jc_d, jc_a, am_h, am_d, am_a):
    """竞彩vs澳门赔率变化方向对比（含盘口硬度分析）"""
    jc_total = abs(jc_h) + abs(jc_d) + abs(jc_a)
    am_total = abs(am_h) + abs(am_d) + abs(am_a)
    
    threshold = 0.5  # 小于0.5%视为不变
    
    if am_total < threshold and jc_total < threshold:
        return '全不动', ''
    elif am_total < threshold:
        # 澳门不动 — 分析盘口硬度
        tags = []
        if jc_total > 10:
            tags.append('硬')  # 盘口极硬
        
        # 检查竞彩往高水走的方向（澳门不怕）
        high_water_dirs = []
        if jc_h > 5:
            high_water_dirs.append('H')
        if jc_d > 5:
            high_water_dirs.append('D')
        if jc_a > 5:
            high_water_dirs.append('A')
        for d in high_water_dirs:
            tags.append(f'不怕{d}')
        
        # 检查竞彩往低水走的方向（澳门不跟）
        low_water_dirs = []
        if jc_h < -5:
            low_water_dirs.append('H')
        if jc_d < -5:
            low_water_dirs.append('D')
        if jc_a < -5:
            low_water_dirs.append('A')
        for d in low_water_dirs:
            tags.append(f'不跟{d}')
        
        tag_str = '[' + ','.join(tags) + ']' if tags else ''
        return '澳门不动', tag_str
    elif jc_total < threshold:
        return '竞彩不动', ''
    
    # 检查方向一致性：三向变化方向是否一致
    same_h = (jc_h > threshold and am_h > threshold) or (jc_h < -threshold and am_h < -threshold) or (abs(jc_h) <= threshold and abs(am_h) <= threshold)
    same_d = (jc_d > threshold and am_d > threshold) or (jc_d < -threshold and am_d < -threshold) or (abs(jc_d) <= threshold and abs(am_d) <= threshold)
    same_a = (jc_a > threshold and am_a > threshold) or (jc_a < -threshold and am_a < -threshold) or (abs(jc_a) <= threshold and abs(am_a) <= threshold)
    
    same_count = same_h + same_d + same_a
    diff_count = 3 - same_count
    
    if same_count >= 3:
        return '同向', ''
    elif diff_count >= 2:
        return '分歧', ''
    elif same_count >= 2:
        return '大致同向', ''
    else:
        return '分歧', ''

league_map = {
    '町田泽维': '日职', '川崎前锋': '日职',
    '浦项制铁': '韩K联', '江原FC': '韩K联',
    '韩国': '友谊赛', '科特迪瓦': '友谊赛',
    '威科姆': '英乙', '维尔港': '英乙',
    '雷丁': '英冠', '维冈': '英冠',
    '斯托克港': '英乙', '温布尔登': '英乙',
    '埃克塞特': '英甲', '莱顿东方': '英甲',
    '布莱克浦': '英甲', '伯顿': '英甲',
    '苏格兰': '友谊赛', '日本': '友谊赛',
    '加拿大': '友谊赛', '冰岛': '友谊赛',
    '匈牙利': '欧国联', '斯洛文尼': '欧国联',
    '威廉二世': '荷甲', '格拉夫': '荷甲',
    '美国': '友谊赛', '比利时': '友谊赛',
    '埃因FC': '荷乙', '埃门': '荷乙',
    '墨西哥': '友谊赛', '葡萄牙': '友谊赛',
}

macau_dir_map = {
    '周六001': 'H', '周六002': 'D', '周六003': 'H', '周六004': 'D',
    '周六005': 'H', '周六006': 'H', '周六007': 'A', '周六008': 'A',
    '周六009': 'A', '周六010': 'H', '周六011': 'D', '周六012': 'H',
    '周六013': 'D', '周六014': 'H', '周六015': 'D',
}

# ===== 输出1：主数据表 =====
header = f"{'编号':<8} | {'对阵':<26} | {'澳门':<3} | {'近况差':<5} | {'初盘竞彩':<16} | {'初盘澳门':<16} | {'离散度':<24} | {'一致性':<6} | {'变化(竞彩)':<30} | {'变化(澳门)':<30} | {'方向对比':<12} | {'竞彩总和':<7} | {'澳门总和':<7}"
print(header)
print('=' * len(header))

for fpath in files:
    fname = os.path.basename(fpath)
    with open(fpath, 'r', encoding='utf-8') as fh:
        content = fh.read()
        lines = content.split('\n')
    
    m_id = fname.split('_')[0]
    home, away, league, macau, hf, af = '?', '?', '?', '?', '?', '?'
    
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith('|') and i < 30:
            cells = [c.strip() for c in s.split('|')]
            if len(cells) >= 3:
                field = cells[1]
                value = cells[2]
                if field == '主队': home = value
                elif field == '客队': away = value
                elif field == '赛事': league = value
                elif field == '澳门推荐': macau = value
                elif field == '主队近况走势': hf = value
                elif field == '客队近况走势': af = value
    
    if league in ['日期', '?', '']:
        league = league_map.get(home, league_map.get(away, '?'))
    
    # 赔率提取
    init_text = parse_section(content, '初盘赔率')
    curr_text = parse_section(content, '即时赔率')
    jc_init = get_odds_from_code_block(init_text, 0)
    jc_curr = get_odds_from_code_block(curr_text, 0)
    am_init = get_odds_from_code_block(init_text, 2)
    am_curr = get_odds_from_code_block(curr_text, 2)
    
    h_score = calc_form_score(hf)
    a_score = calc_form_score(af)
    form_diff = h_score - a_score
    
    # 变化计算
    jc_h, jc_d, jc_a, jc_total = calc_changes(jc_init, jc_curr)
    am_h, am_d, am_a, am_total = calc_changes(am_init, am_curr)
    
    # 离散度计算（初盘+即时都算）
    init_disp = calc_dispersion(jc_init, am_init)
    curr_disp = calc_dispersion(jc_curr, am_curr)
    
    # 方向对比（含盘口硬度标签）
    comparison, hardness_tag = compare_jingcai_macau(jc_h, jc_d, jc_a, am_h, am_d, am_a)
    
    # 格式化
    jc_init_str = '/'.join(jc_init) if jc_init else '?/?/?'
    am_init_str = '/'.join(am_init) if am_init else '?/?/?'
    jc_chg_str = f'H{jc_h:+.1f} D{jc_d:+.1f} A{jc_a:+.1f}' if jc_init and jc_curr else '全0'
    am_chg_str = f'H{am_h:+.1f} D{am_d:+.1f} A{am_a:+.1f}' if am_init and am_curr else '全0'
    jc_total_str = f'{jc_total:.1f}%' if jc_init and jc_curr else '0%'
    am_total_str = f'{am_total:.1f}%' if am_init and am_curr else '0%'
    
    # 离散度格式化：显示初盘→即时
    if init_disp and curr_disp:
        init_str = f'H{init_disp[0]:+.1f} D{init_disp[1]:+.1f} A{init_disp[2]:+.1f}'
        curr_str = f'H{curr_disp[0]:+.1f} D{curr_disp[1]:+.1f} A{curr_disp[2]:+.1f}'
        disp_str = f'{init_str} -> {curr_str}'
        # 用即时离散度判断一致性（最新状态）
        _, consistency = judge_dispersion(curr_disp)
    else:
        disp_str = '?'
        consistency = '?'
    
    macau_dir = macau_dir_map.get(m_id, '?')
    vs_str = f'{home} vs {away}'
    
    # 方向对比列：包含硬度标签
    compare_str = f'{comparison}{hardness_tag}'
    
    print(f'{m_id:<8} | {vs_str:<26} | {macau_dir:<3} | {form_diff:>+4d}  | {jc_init_str:<16} | {am_init_str:<16} | {disp_str:<24} | {consistency:<6} | {jc_chg_str:<30} | {am_chg_str:<30} | {compare_str:<12} | {jc_total_str:<7} | {am_total_str:<7}')

# ===== 输出2：离散度汇总排序 =====
print()
print('=' * 80)
print(f"{'离散度排名（按即时离散度从小到大=一致性从高到低）':<80}")
print(f"{'编号':<8} | {'初盘离散度':<20} | {'即时离散度':<20} | {'一致性':<6} | {'变化趋势':<10}")
print('-' * 75)

disp_list = []
for fpath in files:
    fname = os.path.basename(fpath)
    m_id = fname.split('_')[0]
    with open(fpath, 'r', encoding='utf-8') as fh:
        content = fh.read()
    
    init_text = parse_section(content, '初盘赔率')
    curr_text = parse_section(content, '即时赔率')
    jc_init = get_odds_from_code_block(init_text, 0)
    jc_curr = get_odds_from_code_block(curr_text, 0)
    am_init = get_odds_from_code_block(init_text, 2)
    am_curr = get_odds_from_code_block(curr_text, 2)
    
    init_disp = calc_dispersion(jc_init, am_init)
    curr_disp = calc_dispersion(jc_curr, am_curr)
    
    if init_disp and curr_disp:
        init_avg = (abs(init_disp[0]) + abs(init_disp[1]) + abs(init_disp[2])) / 3
        curr_avg = (abs(curr_disp[0]) + abs(curr_disp[1]) + abs(curr_disp[2])) / 3
        _, consistency = judge_dispersion(curr_disp)
        # 变化趋势：离散度是扩大还是缩小
        diff = curr_avg - init_avg
        if diff > 1:
            trend = '扩大'
        elif diff < -1:
            trend = '缩小'
        else:
            trend = '不变'
        disp_list.append((m_id, init_avg, curr_avg, consistency, trend, init_disp, curr_disp))

disp_list.sort(key=lambda x: x[2])  # 按即时离散度排序

for m_id, init_avg, curr_avg, consistency, trend, init_disp, curr_disp in disp_list:
    init_str = f'H{init_disp[0]:+.1f} D{init_disp[1]:+.1f} A{init_disp[2]:+.1f}'
    curr_str = f'H{curr_disp[0]:+.1f} D{curr_disp[1]:+.1f} A{curr_disp[2]:+.1f}'
    print(f'{m_id:<8} | {init_str:<20} | {curr_str:<20} | {consistency:<6} | {trend:<10}')
