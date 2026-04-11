import urllib.request, re, json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://odds.500.com/',
}

def fetch(url):
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=15)
    return resp.read().decode('gbk', errors='replace')

def extract_oz_rows(content):
    """提取欧赔数据行：通过找 xls=row 开始，计数 <tr>/<\/tr> 深度来定位结束"""
    rows = []
    pos = 0
    while True:
        start = content.find('xls="row"', pos)
        if start == -1:
            break
        # 找到这个 <tr ...> 的起始 <
        tr_start = content.rfind('<tr', 0, start)
        if tr_start == -1:
            pos = start + 1
            continue
        # 从 tr_start 往后，计数 <tr 和 </tr>，找到匹配的 </tr>
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
                    end = i + 5  # 包含 </tr>
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

def parse_ouzhi_v2(fixture_id):
    """解析欧赔：正确处理嵌套 tr"""
    url = f'https://odds.500.com/fenxi/ouzhi-{fixture_id}.shtml'
    try:
        content = fetch(url)
    except Exception as e:
        return {'error': str(e)}

    result = {}
    companies = []

    rows = extract_oz_rows(content)

    for row in rows:
        # 公司名
        co_m = re.search(r'<span class="quancheng"[^>]*>([^<]+)</span>', row)
        company = co_m.group(1).strip() if co_m else ''

        # 即时赔率：找第一个包含3个 klfc 属性的 <tr> 行（即时行）
        klfc_vals = re.findall(r'klfc="([\d.]+)"', row)

        # 即时欧赔：前三个 klfc 对应赔率的 td 文本
        odds_tds = re.findall(r'klfc="[\d.]+"[^>]*>\s*([\d.]+)\s*</td>', row)
        win = odds_tds[0] if len(odds_tds) > 0 else ''
        draw = odds_tds[1] if len(odds_tds) > 1 else ''
        lose = odds_tds[2] if len(odds_tds) > 2 else ''

        # 返还率（百分比 td）
        pct_m = re.search(r'<td[^>]*>\s*([\d.]+%)\s*</td>', row)
        ret_rate = pct_m.group(1) if pct_m else ''

        # 凯利指数（即时）前3个
        kelly_win  = klfc_vals[0] if len(klfc_vals) > 0 else ''
        kelly_draw = klfc_vals[1] if len(klfc_vals) > 1 else ''
        kelly_lose = klfc_vals[2] if len(klfc_vals) > 2 else ''

        if company and (win or draw or lose):
            companies.append({
                '公司': company,
                '胜': win,
                '平': draw,
                '负': lose,
                '返还率': ret_rate,
                '凯利胜': kelly_win,
                '凯利平': kelly_draw,
                '凯利负': kelly_lose,
            })

    result['欧赔列表'] = companies
    return result

# 测试利物浦
r = parse_ouzhi_v2('1202689')
print(f"利物浦 欧赔公司数: {len(r.get('欧赔列表', []))}")
for c in r['欧赔列表'][:8]:
    print(f"  [{c['公司']:12s}] 胜:{c['胜']:5s} 平:{c['平']:5s} 负:{c['负']:5s}  返还率:{c['返还率']:7s}  凯利:{c['凯利胜']}/{c['凯利平']}/{c['凯利负']}")

# 测试日本女足
r2 = parse_ouzhi_v2('1318974')
print(f"\n日本女足 欧赔公司数: {len(r2.get('欧赔列表', []))}")
for c in r2['欧赔列表'][:5]:
    print(f"  [{c['公司']:12s}] 胜:{c['胜']:5s} 平:{c['平']:5s} 负:{c['负']:5s}  返还率:{c['返还率']}")
