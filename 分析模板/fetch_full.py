import urllib.request
import re
import json
import time

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
    """去除HTML标签，保留文本"""
    return re.sub(r'<[^>]+>', '', html).strip()

def parse_shuju(fixture_id):
    """解析析(数据分析)页面：交战历史、近期战绩、record_msg"""
    url = f'https://odds.500.com/fenxi/shuju-{fixture_id}.shtml'
    try:
        content = fetch(url)
    except Exception as e:
        return {'error': str(e)}

    result = {}

    # 1. 交战历史摘要 + 历史交锋简短格式
    his = re.search(r'<span class="his_info">(.*?)</span>\s*</div>', content, re.S)
    if his:
        his_text = strip_tags(his.group(1))
        result['交战历史摘要'] = his_text
        # 提取"X队 N胜N和N负"简短格式，例：维罗纳 2胜1和3负
        # 原文格式：双方近N次交战，XX队N胜N平N负，进...
        # 提取"XX队 N胜N和N负"格式
        # 用贪婪匹配队名（含数字如"沙尔克04"），再断开胜平负
        m_short = re.search(
            r'双方近\d+次交战，(.+)(\d+)胜(\d+)平(\d+)负',
            his_text
        )
        if m_short:
            team = m_short.group(1).strip('，, ')
            w, d, l = m_short.group(2), m_short.group(3), m_short.group(4)
            result['历史交锋'] = f'{team} {w}胜{d}和{l}负'

    # 2. 主队近期战绩文字 (record_msg)
    records = re.findall(r'<p class="record_msg">(.*?)</p>', content, re.S)
    if len(records) >= 1:
        result['主队近况'] = strip_tags(records[0])
    if len(records) >= 2:
        result['客队近况'] = strip_tags(records[1])

    # 3. bottom_info 近10场战绩
    bottom = re.findall(r'<div class="bottom_info">\s*<p>(.*?)</p>', content, re.S)
    if len(bottom) >= 1:
        result['主队近10场'] = strip_tags(bottom[0])
    if len(bottom) >= 2:
        result['客队近10场'] = strip_tags(bottom[1])

    # 4. 交战历史表格（最近几条）
    rows = re.findall(r'<tr class="tr[12]" ?>(.*?)</tr>', content, re.S)
    his_list = []
    for row in rows[:6]:
        # 联赛、日期、对阵、比分、胜平负
        texts = re.findall(r'>([^<>]{1,20})<', row)
        cleaned = [t.strip() for t in texts if t.strip() and t.strip() not in ('',)]
        cleaned = [c for c in cleaned if c]
        if cleaned:
            his_list.append(' | '.join(cleaned[:8]))
    result['近期交战记录'] = his_list

    # 5. 澳门心水推荐区块
    recommend_block = re.search(
        r'<div class="M_box recommend">(.*?)</table>',
        content, re.S
    )
    if recommend_block:
        rb = recommend_block.group(1)

        # 主队行、客队行（第1、2个 <tr>）
        tr_list = re.findall(r'<tr>(.*?)</tr>', rb, re.S)

        def parse_form(td_html):
            """把 <font color=...>W/L/D</font> 序列提取成字符串"""
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

        # 推介文字：从 <font> 标签直接取（含队名+胜/平/负）
        tip_m = re.search(r'推介\s*-\s*<font[^>]*>(.*?)</font>', rb, re.S)
        if tip_m:
            result['澳门推荐'] = strip_tags(tip_m.group(1)).strip()

        # 分析文字（td_no4 行）
        analysis_m = re.search(r'class="td_one td_no4"[^>]*>(.*?)</td>', rb, re.S)
        if analysis_m:
            result['澳门分析'] = strip_tags(analysis_m.group(1)).strip('　').strip()

    # 6. 若无澳门心水推荐，从近期比赛记录自动推算
    if '主队近况走势' not in result or '主队盘路走势' not in result:
        # 从析页面近期比赛 tr 中取胜负/盘路
        # 格式：<span class="ying/ping/shu">胜/平/负</span> 和 <span class="ying/ping/shu">赢/走/输</span>
        # 近期比赛表格行：class="tr3 bmatch" 开头的是本场，其他 tr3/tr4 是近期
        match_rows = re.findall(r'<tr[^>]+class="[^"]*tr[34][^"]*"[^>]*>(.*?)</tr>', content, re.S)

        def row_to_wld(row_html, is_home_side):
            """从一行比赛 tr 判断 W/L/D（近况）和 W/L/1（盘路）"""
            # 胜平负：第一个带颜色 span，ying=胜(W) ping=平(D) shu=负(L)
            wld_m = re.search(r'<span class="(ying|ping|shu)">[^<]*</span>', row_html)
            wld = ''
            if wld_m:
                cls = wld_m.group(1)
                wld = 'W' if cls == 'ying' else ('D' if cls == 'ping' else 'L')

            # 盘路：赢/输/走 → W/L/1
            pan_m = re.search(r'<span class="(ying|shu|ping)">(赢|输|走)</span>', row_html)
            pan = ''
            if pan_m:
                txt = pan_m.group(2)
                pan = 'W' if txt == '赢' else ('1' if txt == '走' else 'L')
            return wld, pan

        # 主队区块：id="team_zhanji_1" 里的 tr
        home_block = re.search(r'id="team_zhanji_1"(.*?)id="team_zhanji_2"', content, re.S)
        away_block = re.search(r'id="team_zhanji_2"(.*?)(?:id="team_zhanji_3"|</div>\s*</div>\s*</div>)', content, re.S)

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
                        continue  # 跳过本场
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
    """提取欧赔数据行：通过 xls=row 定位，用深度计数找到对应的关闭 </tr>"""
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
    """解析欧(欧赔)页面：各公司即时欧赔胜平负"""
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

        # ── 提取赔率内嵌表格中的两行 tr ──────────────────────────────────
        # 页面顺序：第一行（td_show_cp）= 初盘赔率；第二行 = 即时赔率
        # 用所有带 klfc 的 td 按顺序取，每3个为一组（胜/平/负）
        all_klfc_tds = re.findall(r'klfc="([\d.]+)"[^>]*>\s*([\d.]+)\s*</td>', row)
        # all_klfc_tds: [(klfc值, 赔率值), ...]
        # 初盘：前3个；即时：后3个（如果有）
        opening_vals  = all_klfc_tds[:3]
        realtime_vals = all_klfc_tds[3:6]

        win_o  = opening_vals[0][1] if len(opening_vals) > 0 else ''
        draw_o = opening_vals[1][1] if len(opening_vals) > 1 else ''
        lose_o = opening_vals[2][1] if len(opening_vals) > 2 else ''

        win_r  = realtime_vals[0][1] if len(realtime_vals) > 0 else ''
        draw_r = realtime_vals[1][1] if len(realtime_vals) > 1 else ''
        lose_r = realtime_vals[2][1] if len(realtime_vals) > 2 else ''

        # 凯利指数（即时，后3个 klfc 值；若无即时则用初盘）
        kelly_src = realtime_vals if realtime_vals else opening_vals
        kelly_win  = kelly_src[0][0] if len(kelly_src) > 0 else ''
        kelly_draw = kelly_src[1][0] if len(kelly_src) > 1 else ''
        kelly_lose = kelly_src[2][0] if len(kelly_src) > 2 else ''

        # 返还率（第一个百分比）
        pct_m = re.search(r'<td[^>]*>\s*([\d.]+%)\s*</td>', row)
        ret_rate = pct_m.group(1) if pct_m else ''

        if company and (win_r or win_o):
            companies.append({
                '公司': company,
                # 即时
                '即时胜': win_r,
                '即时平': draw_r,
                '即时负': lose_r,
                # 初盘
                '初盘胜': win_o,
                '初盘平': draw_o,
                '初盘负': lose_o,
                # 其他
                '返还率': ret_rate,
                '凯利胜': kelly_win,
                '凯利平': kelly_draw,
                '凯利负': kelly_lose,
            })

    result['欧赔列表'] = companies
    return result


def parse_yazhi(fixture_id):
    """解析亚(亚盘)页面：各公司亚盘盘口水位"""
    url = f'https://odds.500.com/fenxi/yazhi-{fixture_id}.shtml'
    try:
        content = fetch(url)
    except Exception as e:
        return {'error': str(e)}

    result = {}
    companies = []

    # 找亚盘数据行
    rows = re.findall(r'<tr[^>]+class="[^"]*tr[12][^"]*"[^>]*>(.*?)</tr>', content, re.S)
    for row in rows[:30]:
        co_m = re.search(r'title="([^"]{2,20})"', row)
        company = co_m.group(1) if co_m else ''
        # 盘口和水位
        tds = re.findall(r'<td[^>]*>\s*([^<\s][^<]{0,15}[^<\s]?)\s*</td>', row)
        cleaned = [strip_tags(t).strip() for t in tds if strip_tags(t).strip()]
        if company and cleaned:
            companies.append({'公司': company, '数据': cleaned[:8]})

    result['亚盘列表'] = companies
    return result


# ===================== 主程序 =====================
# 读取之前抓的比赛列表
with open('d:\\work\\workbuddy\\足球预测\\分析模板\\matches_2026-03-15.json', 'r', encoding='utf-8') as f:
    matches = json.load(f)

print(f"开始抓取 {len(matches)} 场比赛的析/欧/亚数据...")
print("=" * 60)

all_data = []

for i, m in enumerate(matches):
    fixture_id = None
    # 从原页面重新拿 fixture_id（我们之前没存），用编号找对应行
    # 直接从页面 raw HTML 里取
    pass

# 重新从 raw HTML 提取 fixture_id
with open('d:\\work\\workbuddy\\足球预测\\分析模板\\page_raw.html', 'r', encoding='utf-8') as f:
    page_html = f.read()

match_rows = re.findall(
    r'<tr[^>]+class="bet-tb-tr[^"]*"([^>]+)>(.*?)</tr>',
    page_html, re.S
)

def attr(attrs_str, name):
    m = re.search(rf'data-{name}="([^"]*)"', attrs_str)
    return m.group(1) if m else ''

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

    # 抓析数据
    print(f"  → 抓取析(数据分析)...")
    shuju = parse_shuju(fixture_id)
    time.sleep(0.5)

    # 抓欧赔
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

    # 打印摘要
    if '交战历史摘要' in shuju:
        print(f"  交战: {shuju['交战历史摘要'][:80]}")
    if '主队近况' in shuju:
        print(f"  主队: {shuju['主队近况'][:80]}")
    if '客队近况' in shuju:
        print(f"  客队: {shuju['客队近况'][:80]}")
    if '欧赔列表' in ouzhi and ouzhi['欧赔列表']:
        top3 = ouzhi['欧赔列表'][:3]
        for c in top3:
            print(f"  [{c['公司']}] 即时:{c['即时胜']}/{c['即时平']}/{c['即时负']}  初盘:{c['初盘胜']}/{c['初盘平']}/{c['初盘负']}  返还率:{c['返还率']}")

# 保存完整结果
out_path = 'd:\\work\\workbuddy\\足球预测\\分析模板\\matches_full_2026-03-15.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)

print(f"\n\n完成！完整数据已保存到: {out_path}")
