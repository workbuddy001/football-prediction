"""
fetch_325.py
抓取 2026-03-25 的竞彩足球数据，并生成 3.25/ 目录下的源数据 md 文件
基于 fetch_full_318.py 改造
"""
import urllib.request
import re
import json
import os
import time

TARGET_DATE = "2026-04-11"
PAGE_URL    = f"https://trade.500.com/jczq/?playid=312&g=2&date={TARGET_DATE}"
COLLECT_DATE = "2026-04-11"
OUT_DIR     = r"d:\work\workbuddy\足球预测\分析模板\4.11"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://odds.500.com/',
}

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=20)
    return resp.read().decode('gbk', errors='replace')

def strip_tags(html):
    return re.sub(r'<[^>]+>', '', html).strip()


# ─── 析页解析（数据分析页） ───────────────────────────────────────
def parse_shuju(fixture_id):
    url = f'https://odds.500.com/fenxi/shuju-{fixture_id}.shtml'
    try:
        content = fetch(url)
    except Exception as e:
        return {'error': str(e)}

    result = {}

    # 历史交锋
    his = re.search(r'<span class="his_info">(.*?)</span>\s*</div>', content, re.S)
    if his:
        his_text = strip_tags(his.group(1))
        result['交战历史摘要'] = his_text
        m_short = re.search(r'双方近\d+次交战[，,](.+?)(\d+)胜(\d+)平(\d+)负', his_text)
        if m_short:
            team = m_short.group(1).strip('，, ')
            w, d, l = m_short.group(2), m_short.group(3), m_short.group(4)
            result['历史交锋'] = f'{team} {w}胜{d}和{l}负'

    # 近况文字（record_msg）
    records = re.findall(r'<p class="record_msg">(.*?)</p>', content, re.S)
    if len(records) >= 1:
        result['主队近况'] = strip_tags(records[0])
    if len(records) >= 2:
        result['客队近况'] = strip_tags(records[1])

    # 近10场统计
    bottom = re.findall(r'<div class="bottom_info">\s*<p>(.*?)</p>', content, re.S)
    if len(bottom) >= 1:
        result['主队近10场'] = strip_tags(bottom[0])
    if len(bottom) >= 2:
        result['客队近10场'] = strip_tags(bottom[1])

    # 近期交战记录（tr1/tr2 行）
    rows = re.findall(r'<tr class="tr[12]" ?>(.*?)</tr>', content, re.S)
    his_list = []
    for row in rows[:6]:
        texts = re.findall(r'>([^<>]{1,30})<', row)
        cleaned = [t.strip() for t in texts if t.strip()]
        if cleaned:
            his_list.append(cleaned)
    result['近期交战记录'] = his_list

    # 澳门推荐区块
    recommend_block = re.search(r'<div class="M_box recommend">(.*?)</table>', content, re.S)
    if recommend_block:
        rb = recommend_block.group(1)
        tr_list = re.findall(r'<tr>(.*?)</tr>', rb, re.S)

        def parse_form(td_html):
            letters = re.findall(r'<font[^>]*>([WLD1])</font>', td_html, re.I)
            return ''.join(letters).upper()

        if len(tr_list) >= 1:
            home_tds = re.findall(r'<td[^>]*>(.*?)</td>', tr_list[0], re.S)
            if len(home_tds) >= 2:
                result['主队近况走势'] = parse_form(home_tds[1])
            if len(home_tds) >= 3:
                result['主队盘路走势'] = parse_form(home_tds[2])

        if len(tr_list) >= 2:
            away_tds = re.findall(r'<td[^>]*>(.*?)</td>', tr_list[1], re.S)
            if len(away_tds) >= 2:
                result['客队近况走势'] = parse_form(away_tds[1])
            if len(away_tds) >= 3:
                result['客队盘路走势'] = parse_form(away_tds[2])

        tip_m = re.search(r'推介\s*-\s*<font[^>]*>(.*?)</font>', rb, re.S)
        if tip_m:
            result['澳门推荐'] = strip_tags(tip_m.group(1)).strip()

        analysis_m = re.search(r'class="td_one td_no4"[^>]*>(.*?)</td>', rb, re.S)
        if analysis_m:
            result['澳门分析'] = strip_tags(analysis_m.group(1)).strip('\u3000').strip()

    # 备用走势解析
    if '主队近况走势' not in result or '主队盘路走势' not in result:
        home_block = re.search(r'id="team_zhanji_1"(.*?)id="team_zhanji_2"', content, re.S)
        away_block = re.search(r'id="team_zhanji_2"(.*?)(?:id="team_zhanji_3"|</div>\s*</div>\s*</div>)', content, re.S)

        def row_to_wld(row_html, is_home_side):
            wld_m = re.search(r'<span class="(ying|ping|shu)">[^<]*</span>', row_html)
            wld = ''
            if wld_m:
                cls = wld_m.group(1)
                wld = 'W' if cls == 'ying' else ('D' if cls == 'ping' else 'L')
            pan_m = re.search(r'<span class="(ying|shu|ping)">(赢|输|走)</span>', row_html)
            pan = ''
            if pan_m:
                txt = pan_m.group(2)
                pan = 'W' if txt == '赢' else ('1' if txt == '走' else 'L')
            return wld, pan

        for key_form, key_pan, block in [
            ('主队近况走势', '主队盘路走势', home_block),
            ('客队近况走势', '客队盘路走势', away_block),
        ]:
            if block and key_form not in result:
                b = block.group(1)
                trs = re.findall(r'<tr[^>]*>(.*?)</tr>', b, re.S)
                forms, pans = [], []
                for tr in trs:
                    if 'bmatch' in tr:
                        continue
                    w, p = row_to_wld(tr, True)
                    if w:
                        forms.append(w)
                    if p:
                        pans.append(p)
                if forms:
                    result[key_form] = ''.join(forms[:6])
                if pans:
                    result[key_pan] = ''.join(pans[:6])

    return result


# ─── 欧赔解析 ────────────────────────────────────────────────────
def extract_oz_rows(content):
    rows = []
    pos = 0
    while True:
        start = content.find('xls="row"', pos)
        if start == -1:
            break
        tr_start = content.rfind('<tr', 0, start)
        if tr_start == -1:
            pos = start + 1
            continue
        depth = 0
        i = tr_start
        end = -1
        while i < len(content):
            if content[i:i+3] == '<tr':
                depth += 1
                i += 3
            elif content[i:i+4] == '</tr':
                depth -= 1
                if depth == 0:
                    end = i + 5
                    break
                i += 4
            else:
                i += 1
        if end == -1:
            pos = start + 1
            continue
        rows.append(content[tr_start:end])
        pos = end
    return rows


def parse_ouzhi(fixture_id):
    url = f'https://odds.500.com/fenxi/ouzhi-{fixture_id}.shtml'
    try:
        content = fetch(url)
    except Exception as e:
        return {'欧赔列表': [], 'error': str(e)}

    companies = []
    rows = extract_oz_rows(content)

    for row in rows:
        co_m = re.search(r'<span class="quancheng"[^>]*>([^<]+)</span>', row)
        company = co_m.group(1).strip() if co_m else ''

        all_klfc_tds = re.findall(r'klfc="([\d.]+)"[^>]*>\s*([\d.]+)\s*</td>', row)
        opening_vals  = all_klfc_tds[:3]
        realtime_vals = all_klfc_tds[3:6]

        win_o  = opening_vals[0][1]  if len(opening_vals) > 0 else ''
        draw_o = opening_vals[1][1]  if len(opening_vals) > 1 else ''
        lose_o = opening_vals[2][1]  if len(opening_vals) > 2 else ''
        win_r  = realtime_vals[0][1] if len(realtime_vals) > 0 else ''
        draw_r = realtime_vals[1][1] if len(realtime_vals) > 1 else ''
        lose_r = realtime_vals[2][1] if len(realtime_vals) > 2 else ''

        if company and (win_r or win_o):
            companies.append({
                '公司': company,
                '即时胜': win_r or win_o, '即时平': draw_r or draw_o, '即时负': lose_r or lose_o,
                '初盘胜': win_o,  '初盘平': draw_o,  '初盘负': lose_o,
            })

    return {'欧赔列表': companies}


# ─── 生成 Markdown ────────────────────────────────────────────────
def arrow(a, b):
    try:
        fa, fb = float(a), float(b)
        if fb > fa: return '↑'
        if fb < fa: return '↓'
        return '—'
    except:
        return '—'


def generate_md(entry):
    shuju = entry.get('数据分析', {})
    ouzhi = entry.get('欧赔数据', {})
    companies = ouzhi.get('欧赔列表', [])
    spf = entry.get('竞彩胜平负赔率', {})

    home = entry['主队']
    away = entry['客队']
    match_id = entry['编号']
    n = len(companies)

    lines = []
    lines.append(f"# 赔率分析源数据")
    lines.append(f"")
    lines.append(f"> 数据来源：500.com 竞彩足球 | 编号：{match_id} | 采集日期：{COLLECT_DATE}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 一、比赛基本信息")
    lines.append(f"")
    lines.append(f"| 字段 | 内容 |")
    lines.append(f"|------|------|")
    lines.append(f"| 主队 | {home} |")
    lines.append(f"| 客队 | {away} |")
    lines.append(f"| 比赛时间 | {entry['日期']} {entry['时间']} |")
    lines.append(f"| 赛事 | {entry['联赛']} |")
    lines.append(f"| 让球 | {entry['让球']} |")
    lines.append(f"| 主队近况 | {shuju.get('主队近10场', shuju.get('主队近况', ''))} |")
    lines.append(f"| 客队近况 | {shuju.get('客队近10场', shuju.get('客队近况', ''))} |")
    lines.append(f"| 主队近况走势 | {shuju.get('主队近况走势', '')} |")
    lines.append(f"| 主队盘路走势 | {shuju.get('主队盘路走势', '')} |")
    lines.append(f"| 客队近况走势 | {shuju.get('客队近况走势', '')} |")
    lines.append(f"| 客队盘路走势 | {shuju.get('客队盘路走势', '')} |")
    lines.append(f"| 历史交锋 | {shuju.get('历史交锋', shuju.get('交战历史摘要', ''))} |")
    lines.append(f"| 澳门推荐 | {shuju.get('澳门推荐', '')} |")
    if shuju.get('澳门分析'):
        lines.append(f"| 澳门分析 | {shuju['澳门分析']} |")
    lines.append(f"")

    # 近期交战记录
    his_list = shuju.get('近期交战记录', [])
    if his_list:
        lines.append(f"### 近期交战记录（析页）")
        lines.append(f"")
        lines.append(f"| 赛事 | 日期 | 主队 | 比分 | 客队 | 让球线 | 盘口 |")
        lines.append(f"|------|------|------|------|------|--------|------|")
        for row in his_list:
            padded = row + [''] * max(0, 7 - len(row))
            lines.append(f"| {' | '.join(str(c) for c in padded[:7])} |")
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 二、初盘赔率（共{n}家公司）")
    lines.append(f"")
    lines.append(f"```python")
    lines.append(f"initial_odds = [")
    lines.append(f"    # 格式: (主胜, 平局, 客胜)  # 公司名")
    for c in companies:
        w = c['初盘胜'] or c['即时胜']
        d = c['初盘平'] or c['即时平']
        l = c['初盘负'] or c['即时负']
        lines.append(f"    ({w}, {d}, {l}),  # {c['公司']}")
    lines.append(f"]")
    lines.append(f"```")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 三、即时赔率（共{n}家公司）")
    lines.append(f"")
    lines.append(f"```python")
    lines.append(f"realtime_odds = [")
    lines.append(f"    # 格式: (主胜, 平局, 客胜)  # 公司名")
    for c in companies:
        lines.append(f"    ({c['即时胜']}, {c['即时平']}, {c['即时负']}),  # {c['公司']}")
    lines.append(f"]")
    lines.append(f"```")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 四、竞彩胜平负赔率（500.com官方）")
    lines.append(f"")
    lines.append(f"| 结果 | 赔率 |")
    lines.append(f"|------|------|")
    lines.append(f"| 主胜（{home}赢） | {spf.get('胜', '-')} |")
    lines.append(f"| 平局 | {spf.get('平', '-')} |")
    lines.append(f"| 客胜（{away}赢） | {spf.get('负', '-')} |")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 五、赔率变动对比（初盘 → 即时）")
    lines.append(f"")
    lines.append(f"| 公司 | 初盘胜 | 即时胜 | 变动 | 初盘平 | 即时平 | 变动 | 初盘负 | 即时负 | 变动 |")
    lines.append(f"|------|--------|--------|------|--------|--------|------|--------|--------|------|")

    w_down = d_up = l_up = 0
    for c in companies:
        iw, rw = c['初盘胜'], c['即时胜']
        id_, rd = c['初盘平'], c['即时平']
        il, rl = c['初盘负'], c['即时负']
        aw = arrow(iw, rw); ad = arrow(id_, rd); al = arrow(il, rl)
        if aw == '↓': w_down += 1
        if ad == '↑': d_up += 1
        if al == '↑': l_up += 1
        lines.append(f"| {c['公司']} | {iw} | {rw} | {aw} | {id_} | {rd} | {ad} | {il} | {rl} | {al} |")

    lines.append(f"")
    lines.append(f"> **趋势总结**：{w_down}/{n}家主胜降赔，{d_up}/{n}家平局升赔，{l_up}/{n}家客胜升赔。")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 六、快速复制到分析工具")
    lines.append(f"")
    lines.append(f"```python")
    lines.append(f"if __name__ == \"__main__\":")
    lines.append(f"")
    lines.append(f"    # 比赛信息")
    lines.append(f"    home_team     = \"{home}\"")
    lines.append(f"    away_team     = \"{away}\"")
    lines.append(f"    match_time    = \"{entry['日期']} {entry['时间']}\"")
    lines.append(f"    league        = \"{entry['联赛']}\"")
    lines.append(f"    home_form     = \"{shuju.get('主队近况走势', '')}\"")
    lines.append(f"    away_form     = \"{shuju.get('客队近况走势', '')}\"")
    lines.append(f"    home_handicap = \"{shuju.get('主队盘路走势', '')}\"")
    lines.append(f"    away_handicap = \"{shuju.get('客队盘路走势', '')}\"")
    lines.append(f"    history       = \"{shuju.get('历史交锋', shuju.get('交战历史摘要', ''))}\"")
    lines.append(f"    macao_tip     = \"{shuju.get('澳门推荐', '')}\"")
    lines.append(f"")
    lines.append(f"    initial_odds = [")
    for c in companies:
        w = c['初盘胜'] or c['即时胜']
        d = c['初盘平'] or c['即时平']
        l = c['初盘负'] or c['即时负']
        lines.append(f"        ({w}, {d}, {l}),  # {c['公司']}")
    lines.append(f"    ]")
    lines.append(f"")
    lines.append(f"    realtime_odds = [")
    for c in companies:
        lines.append(f"        ({c['即时胜']}, {c['即时平']}, {c['即时负']}),  # {c['公司']}")
    lines.append(f"    ]")
    lines.append(f"```")

    return '\n'.join(lines)


# ─── 主程序 ──────────────────────────────────────────────────────
os.makedirs(OUT_DIR, exist_ok=True)

print(f"抓取页面: {PAGE_URL}")
page_html = fetch(PAGE_URL)

match_rows = re.findall(
    r'<tr[^>]+class="bet-tb-tr[^"]*"([^>]+)>(.*?)</tr>',
    page_html, re.S
)
print(f"发现 {len(match_rows)} 场比赛")

def attr(attrs_str, name):
    m = re.search(rf'data-{name}="([^"]*)"', attrs_str)
    return m.group(1) if m else ''

all_data = []

for i, (attrs_str, row_html) in enumerate(match_rows):
    fixture_id  = attr(attrs_str, 'fixtureid')
    match_num   = attr(attrs_str, 'matchnum')
    league      = attr(attrs_str, 'simpleleague')
    match_date  = attr(attrs_str, 'matchdate')
    match_time  = attr(attrs_str, 'matchtime')
    home        = attr(attrs_str, 'homesxname')
    away        = attr(attrs_str, 'awaysxname')
    rangqiu     = attr(attrs_str, 'rangqiu')

    spf = re.findall(r'data-type="spf"\s+data-value="(\d+)"\s+data-sp="([\d.]+)"', row_html)
    spf_map = {}
    for val, sp in spf:
        label = {'3': '胜', '1': '平', '0': '负'}.get(val, val)
        spf_map[label] = sp

    print(f"\n[{i+1}/{len(match_rows)}] {match_num} {league}: {home} vs {away}  (fixture={fixture_id})")

    print(f"  → 抓取析页(数据分析)...")
    shuju = parse_shuju(fixture_id)
    time.sleep(0.8)

    print(f"  → 抓取欧赔页...")
    ouzhi = parse_ouzhi(fixture_id)
    time.sleep(0.8)

    entry = {
        '编号': match_num,
        '联赛': league,
        '日期': match_date,
        '时间': match_time,
        '主队': home,
        '客队': away,
        '让球': rangqiu,
        '竞彩胜平负赔率': spf_map,
        '数据分析': shuju,
        '欧赔数据': ouzhi,
    }
    all_data.append(entry)

    cos = ouzhi.get('欧赔列表', [])
    print(f"  欧赔: {len(cos)} 家公司")
    if cos:
        for c in cos[:3]:
            print(f"    [{c['公司']}] 初盘:{c['初盘胜']}/{c['初盘平']}/{c['初盘负']}  即时:{c['即时胜']}/{c['即时平']}/{c['即时负']}")
    print(f"  澳门推荐: {shuju.get('澳门推荐','未获取')}")
    print(f"  主队走势: {shuju.get('主队近况走势','未获取')}  盘路: {shuju.get('主队盘路走势','未获取')}")
    print(f"  客队走势: {shuju.get('客队近况走势','未获取')}  盘路: {shuju.get('客队盘路走势','未获取')}")

    # 生成 md 文件
    if cos:
        md_content = generate_md(entry)
        filename = f"{match_num}_{home}vs{away}_源数据.md"
        filepath = os.path.join(OUT_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"  [OK] 已保存: {filename}")
    else:
        print(f"  [SKIP] 无欧赔数据，跳过生成")

print(f"\n全部完成！共 {len(all_data)} 场比赛，文件保存至: {OUT_DIR}")
