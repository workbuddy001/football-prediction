import urllib.request, re, json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://odds.500.com/',
}

def fetch(url):
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=15)
    return resp.read().decode('gbk', errors='replace')

# 测试利物浦 (1202689) 的欧赔
content = fetch('https://odds.500.com/fenxi/ouzhi-1202689.shtml')

rows = re.findall(r'<tr[^>]+xls="row"[^>]*>(.*?)</tr>', content, re.S)
print(f"找到行数: {len(rows)}")

companies = []
for row in rows:
    co_m = re.search(r'<span class="quancheng"[^>]*>([^<]+)</span>', row)
    company = co_m.group(1).strip() if co_m else ''

    odds_block = re.search(r'<tr class="tr_bdb td_show_cp"[^>]*>(.*?)</tr>', row, re.S)
    win = draw = lose = ''
    if odds_block:
        tds = re.findall(r'<td[^>]*>\s*([\d.]+)\s*</td>', odds_block.group(1))
        if len(tds) >= 3:
            win, draw, lose = tds[0].strip(), tds[1].strip(), tds[2].strip()

    ret_rate = ''
    # 找百分比
    pct_m = re.search(r'<td[^>]*>\s*([\d.]+%)\s*</td>', row)
    if pct_m:
        ret_rate = pct_m.group(1)

    if company and (win or draw or lose):
        companies.append({'公司': company, '胜': win, '平': draw, '负': lose, '返还率': ret_rate})

print(f"解析到公司数: {len(companies)}")
for c in companies[:5]:
    print(c)

# 读取更新后的完整JSON
with open('d:\\work\\workbuddy\\足球预测\\分析模板\\matches_full_2026-03-15.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

m = d[20]
print(f"\n[JSON] 欧赔公司数: {len(m['欧赔数据'].get('欧赔列表', []))}")
if m['欧赔数据'].get('欧赔列表'):
    for c in m['欧赔数据']['欧赔列表'][:3]:
        print(c)
