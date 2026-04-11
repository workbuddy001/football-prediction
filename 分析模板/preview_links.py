import urllib.request, re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://trade.500.com/',
}

def fetch(url):
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=15)
    return resp.read().decode('gbk', errors='replace')

# 用第一场比赛 fixtureid=1318974 来探索三个链接
fixture_id = '1318974'

for name, url in [
    ('析(数据分析)', f'https://odds.500.com/fenxi/shuju-{fixture_id}.shtml'),
    ('亚(亚盘)',     f'https://odds.500.com/fenxi/yazhi-{fixture_id}.shtml'),
    ('欧(欧赔)',     f'https://odds.500.com/fenxi/ouzhi-{fixture_id}.shtml'),
]:
    print(f"\n{'='*60}")
    print(f"【{name}】 {url}")
    print('='*60)
    try:
        content = fetch(url)
        with open(f'd:\\work\\workbuddy\\足球预测\\分析模板\\preview_{name[0]}.html', 'w', encoding='utf-8') as f:
            f.write(content)
        # 打印前2000字符
        print(content[:2000])
    except Exception as e:
        print(f"ERROR: {e}")
