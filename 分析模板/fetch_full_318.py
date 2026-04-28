"""
fetch_full_318.py
抓取 2026-04-12 的比赛数据
"""
import urllib.request
import re
import json
import time
import os

TARGET_DATE = "2026-04-28"
PAGE_URL    = f"https://trade.500.com/jczq/?playid=312&g=2&date={TARGET_DATE}"
OUT_DIR     = f"d:\\work\\workbuddy\\足球预测\\分析模板\\{TARGET_DATE.replace('-', '.')}"
RAW_HTML    = f"{OUT_DIR}\\page_raw_{TARGET_DATE}.html"
OUT_JSON    = f"{OUT_DIR}\\matches_full_{TARGET_DATE}.json"

# 确保输出目录存在
os.makedirs(OUT_DIR, exist_ok=True)

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

def parse_shuju(fixture_id):
    url = f'https://odds.500.com/fenxi/shuju-{fixture_id}.shtml'
    try:
        content = fetch(url)
    except Exception as e:
        return {'error': str(e)}

    result = {}

    his = re.search(r'<span class="his_info">(.*?)</span>\s*</div>', content, re.S)
    if his:
        his_text = strip_tags(his.group(1))
        result['交战历史摘要'] = his_text
        m_short = re.search(r'双方近\d+次交战，(.+)(\d+)胜(\d+)平(\d+)负', his_text)
        if m_short:
            team = m_short.group(1).strip('，, ')
            w, d, l = m_short.group(2), m_short.group(3), m_short.group(4)
            result['历史交锋'] = f'{team} {w}胜{d}和{l}负'

    records = re.findall(r'<p class="record_msg">(.*?)</p>', content, re.S)
    if len(records) >= 1:
        result['主队近况'] = strip_tags(records[0])
    if len(records) >= 2:
        result['客队近况'] = strip_tags(records[1])

    bottom = re.findall(r'<div class="bottom_info">\s*<p>(.*?)</p>', content, re.S)
    if len(bottom) >= 1:
        result['主队近10场'] = strip_tags(bottom[0])
    if len(bottom) >= 2:
        result['客队近10场'] = strip_tags(bottom[1])

    rows = re.findall(r'<tr class="tr[12]" ?>(.*?)</tr>', content, re.S)
    his_list = []
    for row in rows[:6]:
        texts = re.findall(r'>([^<>]{1,20})<', row)
        cleaned = [t.strip() for t in texts if t.strip()]
        if cleaned:
            his_list.append(' | '.join(cleaned[:8]))
    result['近期交战记录'] = his_list

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
        return {'error': str(e)}

    result = {}
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

        kelly_src  = realtime_vals if realtime_vals else opening_vals
        kelly_win  = kelly_src[0][0] if len(kelly_src) > 0 else ''
        kelly_draw = kelly_src[1][0] if len(kelly_src) > 1 else ''
        kelly_lose = kelly_src[2][0] if len(kelly_src) > 2 else ''

        pct_m = re.search(r'<td[^>]*>\s*([\d.]+%)\s*</td>', row)
        ret_rate = pct_m.group(1) if pct_m else ''

        if company and (win_r or win_o):
            companies.append({
                '公司': company,
                '即时胜': win_r, '即时平': draw_r, '即时负': lose_r,
                '初盘胜': win_o, '初盘平': draw_o, '初盘负': lose_o,
                '返还率': ret_rate,
                '凯利胜': kelly_win, '凯利平': kelly_draw, '凯利负': kelly_lose,
            })

    result['欧赔列表'] = companies
    return result


# ── 主程序 ──
print(f"抓取页面: {PAGE_URL}")
page_html = fetch(PAGE_URL)

with open(RAW_HTML, 'w', encoding='utf-8') as f:
    f.write(page_html)
print(f"原始页面已保存: {RAW_HTML}")

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

    print(f"\n[{i+1}/{len(match_rows)}] {match_num} {league}: {home} vs {away} (fixture={fixture_id})")

    print(f"  → 抓取析(数据分析)...")
    shuju = parse_shuju(fixture_id)
    time.sleep(0.5)

    print(f"  → 抓取欧(欧赔)...")
    ouzhi = parse_ouzhi(fixture_id)
    time.sleep(0.5)

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

    if '交战历史摘要' in shuju:
        print(f"  交战: {shuju['交战历史摘要'][:80]}")
    if '主队近况' in shuju:
        print(f"  主队: {shuju['主队近况'][:80]}")
    if '客队近况' in shuju:
        print(f"  客队: {shuju['客队近况'][:80]}")
    if '欧赔列表' in ouzhi and ouzhi['欧赔列表']:
        top3 = ouzhi['欧赔列表'][:3]
        for c in top3:
            print(f"  [{c['公司']}] 即时:{c['即时胜']}/{c['即时平']}/{c['即时负']}  初盘:{c['初盘胜']}/{c['初盘平']}/{c['初盘负']}")

with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)

print(f"\n完成！完整数据已保存到: {OUT_JSON}")
print(f"共 {len(all_data)} 场比赛")

# ════════════════════════════════════
# 生成 .md 源数据文件
# ════════════════════════════════════
print(f"\n开始生成 .md 源数据文件到 {OUT_DIR} ...")

def generate_md(entry):
    """生成源数据.md文件内容"""
    shuju = entry.get('数据分析', {})
    ouzhi = entry.get('欧赔数据', {})
    spf = entry.get('竞彩胜平负赔率', {})
    match_num = entry.get('编号', '')
    week_day = '周日' if '周日' in match_num else ('周一' if '周一' in match_num else match_num[:2])
    home = entry.get('主队', '')
    away = entry.get('客队', '')
    match_date = entry.get('日期', '')
    match_time = entry.get('时间', '')
    league = entry.get('联赛', '')
    rangqiu = entry.get('让球', '')
    
    # 文件名
    filename = f"{week_day}{match_num[-3:]}_{home}vs{away}_源数据.md"
    
    # 竞彩赔率
    spf_str = ""
    if spf:
        spf_str = f"| 竞彩胜 | {spf.get('胜', '-')} |\n| 竞彩平 | {spf.get('平', '-')} |\n| 竞彩负 | {spf.get('负', '-')} |"
    
    # 初盘赔率
    init_odds = ouzhi.get('欧赔列表', [])
    init_lines = []
    for i, c in enumerate(init_odds[:30]):
        company = c['公司']
        h = c.get('初盘胜', '') or c.get('即时胜', '')
        d = c.get('初盘平', '') or c.get('即时平', '')
        a = c.get('初盘负', '') or c.get('即时负', '')
        init_lines.append(f"    ({h}, {d}, {a}),  # {company}")
    
    # 即时赔率
    real_lines = []
    for i, c in enumerate(init_odds[:30]):
        company = c['公司']
        h = c.get('即时胜', '')
        d = c.get('即时平', '')
        a = c.get('即时负', '')
        real_lines.append(f"    ({h}, {d}, {a}),  # {company}")
    
    # 近况走势
    home_trend = shuju.get('主队近况走势', shuju.get('主队近况', ''))
    away_trend = shuju.get('客队近况走势', shuju.get('客队近况', ''))
    
    # 澳门推荐
    macao_tip = shuju.get('澳门推荐', '')
    macao_analysis = shuju.get('澳门分析', '')
    
    # 历史交锋
    history = shuju.get('历史交锋', shuju.get('交战历史摘要', ''))
    
    md_content = f"""# 赔率分析源数据

> 数据来源：500.com 竞彩足球 | 编号：{match_num} | 采集日期：{match_date}

---

## 一、比赛基本信息

| 字段 | 内容 |
|------|------|
| 主队 | {home} |
| 客队 | {away} |
| 比赛时间 | {match_date} {match_time} |
| 赛事 | {league} |
| 让球 | {rangqiu} |
| 主队近况 | {shuju.get('主队近况', '-')} |
| 客队近况 | {shuju.get('客队近况', '-')} |
| 主队近况走势 | {shuju.get('主队近况走势', '-')} |
| 主队盘路走势 | {shuju.get('主队盘路走势', '-')} |
| 客队近况走势 | {shuju.get('客队近况走势', '-')} |
| 客队盘路走势 | {shuju.get('客队盘路走势', '-')} |
| 历史交锋 | {history} |
| 澳门推荐 | {macao_tip} |
| 澳门分析 | {macao_analysis} |

---

## 二、初盘赔率（共{len(init_odds)}家公司）

```python
initial_odds = [
    # 格式: (主胜, 平局, 客胜)  # 公司名
{chr(10).join(init_lines[:30])}
]
```

---

## 三、即{'时' if False else '时'}赔率（共{len(init_odds)}家公司）

```python
realtime_odds = [
    # 格式: (主胜, 平局, 客胜)  # 公司名
{chr(10).join(real_lines[:30])}
]
```

---

## 四、竞彩官方赔率

```python
# 竞彩官方赔率
jc_odds = {{
    '胜': {spf.get('胜', '-')},
    '平': {spf.get('平', '-')},
    '负': {spf.get('负', '-')}
}}
```

---

## 五、快速复制数据块

```python
# ===== 竞彩赔率 =====
JC_WIN = {spf.get('胜', '0')}
JC_DRAW = {spf.get('平', '0')}
JC_AWAY = {spf.get('负', '0')}

# ===== 初盘赔率（澳门，第3家）=====
MAC_INIT = ({init_odds[2].get('初盘胜', '') or init_odds[2].get('即时胜', '')}, {init_odds[2].get('初盘平', '') or init_odds[2].get('即时平', '')}, {init_odds[2].get('初盘负', '') or init_odds[2].get('即时负', '')})

# ===== 即时赔率（澳门，第3家）=====
MAC_REAL = ({init_odds[2].get('即时胜', '')}, {init_odds[2].get('即时平', '')}, {init_odds[2].get('即时负', '')})

# ===== 变动 =====
MAC_CHG = (
    round(float(MAC_REAL[0]) - float(MAC_INIT[0]), 2),
    round(float(MAC_REAL[1]) - float(MAC_INIT[1]), 2),
    round(float(MAC_REAL[2]) - float(MAC_INIT[2]), 2)
)

# ===== 澳门推荐 =====
MACAO_TIP = "{macao_tip}"
```
"""
    return filename, md_content

# 生成所有 .md 文件
for entry in all_data:
    try:
        filename, md_content = generate_md(entry)
        filepath = os.path.join(OUT_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"  ✓ {filename}")
    except Exception as e:
        print(f"  ✗ 生成失败: {entry.get('编号', '未知')} - {e}")

print(f"\n.md 文件生成完成！")
