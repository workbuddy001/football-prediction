"""
fetch_full_319_v2.py
抓取 2026-03-19 的比赛数据 - 改进版，增加延迟和更好的请求头
"""
import urllib.request
import re
import json
import time
import random

TARGET_DATE = "2026-03-19"
PAGE_URL    = f"https://trade.500.com/jczq/?playid=312&g=2&date={TARGET_DATE}"
RAW_HTML    = f"d:\\work\\workbuddy\\足球预测\\分析模板\\page_raw_2026-03-19_v2.html"
OUT_JSON    = f"d:\\work\\workbuddy\\足球预测\\分析模板\\matches_full_2026-03-19_v2.json"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://trade.500.com/jczq/',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Cache-Control': 'max-age=0',
}

def fetch(url, headers=None):
    """抓取URL内容"""
    if headers is None:
        headers = HEADERS
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=30)
    return resp.read().decode('gbk', errors='replace')

def strip_tags(html):
    return re.sub(r'<[^>]+>', '', html).strip()

def parse_shuju(fixture_id):
    """抓取数据分析页(shuju)"""
    url = f"https://odds.500.com/fenxi/shuju-{fixture_id}.shtml"
    try:
        time.sleep(random.uniform(1.0, 2.0))  # 增加随机延迟
        html = fetch(url)
    except Exception as e:
        print(f"    [WARN] shuju fetch error: {e}")
        return {}
    
    data = {}
    
    # 检查是否是登录页面
    if '免费注册' in html or '用户名' in html:
        print(f"    [WARN] 遇到登录页面，跳过")
        return data
    
    # 近期战绩走势
    m = re.search(r'<span class="spf">\s*近10场[^<]*</span>', html)
    if m:
        data['近期战绩'] = strip_tags(m.group(0))
    
    # 主客队走势
    home_form = re.findall(r'<span class="[^"]*">([胜平负])</span>\s*<span class="date">', html)
    if home_form:
        data['主队走势'] = ''.join(home_form[:5])
        data['客队走势'] = ''.join(home_form[5:10])
    
    # 历史交锋
    m = re.search(r'<div class="jiaozhan[^"]*">\s*<p>(.*?)</p>', html, re.S)
    if m:
        data['历史交锋'] = strip_tags(m.group(1)).replace('\n', ' ').strip()
    
    # 澳门推荐
    m = re.search(r'<div class="tuijian"[^>]*>.*?<span[^>]*>(.*?)</span>', html, re.S)
    if m:
        data['澳门推荐'] = strip_tags(m.group(1)).strip()
    
    # 澳门分析
    m = re.search(r'<div class="fenxi"[^>]*>.*?<p>(.*?)</p>', html, re.S)
    if m:
        data['澳门分析'] = strip_tags(m.group(1)).strip()
    
    # 近期交战记录表
    his_table = []
    tbl = re.findall(r'<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>', html, re.S)
    for row in tbl[:10]:
        his_table.append([strip_tags(c) for c in row])
    data['交战记录表'] = his_table
    
    return data

def parse_ouzhi(fixture_id):
    """抓取欧赔页(ouzhi)"""
    url = f"https://odds.500.com/fenxi/ouzhi-{fixture_id}.shtml"
    try:
        time.sleep(random.uniform(1.0, 2.0))  # 增加随机延迟
        html = fetch(url)
    except Exception as e:
        print(f"    [WARN] ouzhi fetch error: {e}")
        return []
    
    # 检查是否是登录页面
    if '免费注册' in html or '用户名' in html:
        print(f"    [WARN] 遇到登录页面，跳过")
        return []
    
    companies = []
    # 提取表格数据 - 更精确的正则
    rows = re.findall(r'<tr[^>]*>\s*<td[^>]*>.*?</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>', html, re.S)
    for row in rows:
        name = strip_tags(row[0])
        if not name or '公司' in name or len(name) > 20:
            continue
        # 验证数据是否为数字
        init_w = strip_tags(row[1])
        if not re.match(r'^\d+\.?\d*$', init_w):
            continue
        companies.append({
            '公司': name,
            '初盘胜': init_w,
            '初盘平': strip_tags(row[2]),
            '初盘负': strip_tags(row[3]),
            '即时胜': strip_tags(row[4]),
            '即时平': strip_tags(row[5]),
            '即时负': strip_tags(row[6]),
        })
    return companies

def parse_page(html):
    """解析主页面，提取比赛列表 - 使用data属性"""
    matches = []
    # 查找所有比赛行的data属性
    pattern = r'<tr[^>]*data-fixtureid="(\d+)"[^>]*data-homesxname="([^"]*)"[^>]*data-awaysxname="([^"]*)"[^>]*data-matchdate="([^"]*)"[^>]*data-matchtime="([^"]*)"[^>]*data-rangqiu="([^"]*)"[^>]*data-simpleleague="([^"]*)"[^>]*data-matchnum="([^"]*)"[^>]*>'
    rows = re.findall(pattern, html)
    
    for row in rows:
        fixture_id, home, away, match_date, match_time, rq, league, match_num = row
        matches.append({
            'fixture_id': fixture_id,
            '编号': match_num,
            '联赛': league,
            '比赛时间': f"{match_date} {match_time}",
            '主队': home,
            '客队': away,
            '让球': rq,
        })
    return matches

def main():
    print(f"抓取页面: {PAGE_URL}")
    html = fetch(PAGE_URL)
    
    # 保存原始页面
    with open(RAW_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"原始页面已保存: {RAW_HTML}")
    
    matches = parse_page(html)
    print(f"发现 {len(matches)} 场比赛\n")
    
    full_data = []
    for idx, m in enumerate(matches, 1):
        print(f"[{idx}/{len(matches)}] {m['编号']} {m['联赛']}: {m['主队']} vs {m['客队']} (fixture={m['fixture_id']})")
        
        # 抓取数据分析
        print("  → 抓取析(数据分析)...")
        shuju = parse_shuju(m['fixture_id'])
        if shuju.get('历史交锋'):
            print(f"    交战: {shuju['历史交锋'][:60]}...")
        elif shuju:
            print(f"    析页数据已获取")
        
        # 抓取欧赔
        print("  → 抓取欧(欧赔)...")
        ouzhi = parse_ouzhi(m['fixture_id'])
        if ouzhi:
            jc = next((o for o in ouzhi if '竞' in o['公司']), ouzhi[0] if ouzhi else None)
            if jc:
                print(f"    [{jc['公司']}] 即时:{jc['即时胜']}/{jc['即时平']}/{jc['即时负']}  初盘:{jc['初盘胜']}/{jc['初盘平']}/{jc['初盘负']}")
        
        full_match = {
            **m,
            '析页数据': shuju,
            '欧赔': ouzhi,
        }
        full_data.append(full_match)
        time.sleep(random.uniform(0.5, 1.0))
    
    # 保存
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n完成！完整数据已保存到: {OUT_JSON}")
    print(f"共 {len(full_data)} 场比赛")

if __name__ == "__main__":
    main()
