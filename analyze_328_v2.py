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

def get_odds_from_code_block(text, target_index=2):
    m = re.findall(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', text)
    if m and len(m) > target_index:
        return m[target_index]
    elif m:
        return m[-1]
    return None

def parse_section(content, section_name):
    pattern = r'##\s*.*?' + re.escape(section_name) + r'.*?\n```python\n(.*?)```'
    m = re.search(pattern, content, re.DOTALL)
    if m:
        return m.group(1)
    return ''

# Known leagues from filenames
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

results = []
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
    
    # Fix league
    if league in ['日期', '?', '']:
        league = league_map.get(home, league_map.get(away, '?'))
    
    # Parse odds
    init_text = parse_section(content, '初盘赔率')
    curr_text = parse_section(content, '即时赔率')
    init = get_odds_from_code_block(init_text, 2)
    curr = get_odds_from_code_block(curr_text, 2)
    
    init_str = f'{init[0]}/{init[1]}/{init[2]}' if init else '?/?/?'
    curr_str = f'{curr[0]}/{curr[1]}/{curr[2]}' if curr else '?/?/?'
    
    # Form diff
    h_score = calc_form_score(hf)
    a_score = calc_form_score(af)
    form_diff = h_score - a_score
    
    # Odds change
    if init and curr:
        ih, id_, ia = float(init[0]), float(init[1]), float(init[2])
        ch, cd, ca = float(curr[0]), float(curr[1]), float(curr[2])
        h_chg = (ch - ih) / ih * 100
        d_chg = (cd - id_) / id_ * 100
        a_chg = (ca - ia) / ia * 100
        total_chg = abs(h_chg) + abs(d_chg) + abs(a_chg)
        chg_str = f'H{h_chg:+.1f}% D{d_chg:+.1f}% A{a_chg:+.1f}%'
        total_str = f'{total_chg:.1f}%'
    else:
        chg_str = '?'
        total_str = '?'
        h_chg = d_chg = a_chg = 0
    
    # Macau direction
    macau_dir = '?'
    if macau != '?':
        if '赢' in macau:
            if home in macau or macau.startswith(home[:2]):
                macau_dir = 'H'
            elif away in macau or macau.startswith(away[:2]):
                macau_dir = 'A'
            else:
                # fuzzy match
                for part in macau.split():
                    if home in part or part in home:
                        macau_dir = 'H'
                        break
                    elif away in part or part in away:
                        macau_dir = 'A'
                        break
        elif '和局' in macau or '平局' in macau:
            macau_dir = 'D'
    
    print(f'{m_id}|{home} vs {away}|{league}|{macau_dir}|{hf}|{af}|{form_diff:+d}|{init_str}|{curr_str}|{chg_str}|{total_str}')
