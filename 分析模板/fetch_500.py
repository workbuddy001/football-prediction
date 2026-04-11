import urllib.request
import re
import json

url = 'https://trade.500.com/jczq/index.php?playid=312&g=2&date=2026-03-15'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

req = urllib.request.Request(url, headers=headers)
resp = urllib.request.urlopen(req, timeout=15)
raw = resp.read()
content = raw.decode('gbk', errors='replace')

# 找所有比赛行 (bet-tb-tr)
match_rows = re.findall(
    r'<tr[^>]+class="bet-tb-tr[^"]*"([^>]+)>(.*?)</tr>',
    content, re.S
)

print(f"共找到 {len(match_rows)} 场比赛\n")
print("=" * 80)

matches = []

for attrs_str, row_html in match_rows:
    # 提取 data-* 属性
    def attr(name):
        m = re.search(rf'data-{name}="([^"]*)"', attrs_str)
        return m.group(1) if m else ''

    match_num   = attr('matchnum')
    fixture_id  = attr('fixtureid')
    league      = attr('simpleleague')
    match_date  = attr('matchdate')
    match_time  = attr('matchtime')
    home        = attr('homesxname')
    away        = attr('awaysxname')
    rangqiu     = attr('rangqiu')  # 让球
    is_end      = attr('isend')    # 是否已结束

    # 从行内提取胜平负赔率
    spf = re.findall(r'data-type="spf"\s+data-value="(\d+)"\s+data-sp="([\d.]+)"', row_html)
    spf_map = {}
    for val, sp in spf:
        label = {'3': '胜', '1': '平', '0': '负'}.get(val, val)
        spf_map[label] = sp

    # 提取比分赔率
    bf_list = re.findall(r'data-type="bf"\s+data-value="([^"]+)"\s+data-sp="([\d.]+)"', row_html)
    # 提取进球数赔率
    jq_list = re.findall(r'data-type="jq"\s+data-value="(\d+)"\s+data-sp="([\d.]+)"', row_html)

    info = {
        '编号': match_num,
        '联赛': league,
        '日期': match_date,
        '时间': match_time,
        '主队': home,
        '客队': away,
        '让球': rangqiu,
        '状态': '已结束' if is_end == '1' else '进行中/未开始',
        '胜平负赔率': spf_map,
        '比分赔率(部分)': {bf[0]: bf[1] for bf in bf_list[:10]},
        '进球数赔率': {jq[0]: jq[1] for jq in jq_list},
    }
    matches.append(info)

    # 打印
    print(f"【{match_num}】{league}  {match_date} {match_time}")
    print(f"  {home} vs {away}  让球: {rangqiu}  状态: {info['状态']}")
    if spf_map:
        spf_str = '  '.join(f"{k}:{v}" for k, v in spf_map.items())
        print(f"  胜平负: {spf_str}")
    if jq_list:
        jq_str = '  '.join(f"{jq[0]}球:{jq[1]}" for jq in jq_list)
        print(f"  进球数: {jq_str}")
    print()

# 保存为 JSON
with open('d:\\work\\workbuddy\\足球预测\\分析模板\\matches_2026-03-15.json', 'w', encoding='utf-8') as f:
    json.dump(matches, f, ensure_ascii=False, indent=2)

print(f"\n数据已保存到 matches_2026-03-15.json")
