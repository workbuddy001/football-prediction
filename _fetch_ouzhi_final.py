# -*- coding: utf-8 -*-
"""
欧赔数据抓取函数
从 odds.500.com/fenxi/ouzhi-{fixture_id}.shtml 抓取30家公司的初盘+即时盘赔率
"""
import urllib.request
import re
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://odds.500.com/',
}

def fetch(url):
    """抓取页面"""
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=20)
    return resp.read().decode('gbk', errors='replace')

def parse_ouzhi(content):
    """解析欧赔页面，返回30家公司赔率列表"""
    results = []
    lines = content.split('\n')
    
    current_company = ""
    current_odds = []
    
    for line in lines:
        # 公司名行
        if 'tb_plgs' in line:
            m = re.search(r'<span[^>]*>([^<]+)</span>', line)
            if m:
                current_company = m.group(1).strip()
        
        # 赔率行（包含 klfc=）
        if 'klfc=' in line and current_company:
            odds = re.findall(r'<td[^>]*>\s*([\d.]+)\s*</td>', line)
            if odds:
                current_odds.extend(odds)
                # 当有6个赔率时，保存
                if len(current_odds) >= 6:
                    results.append({
                        '公司': current_company,
                        '初盘胜': current_odds[0], '初盘平': current_odds[1], '初盘负': current_odds[2],
                        '即时胜': current_odds[3], '即时平': current_odds[4], '即时负': current_odds[5],
                    })
                    current_company = ""
                    current_odds = []
    
    return results

def fetch_ouzhi_by_fixture(fixture_id):
    """根据fixture_id抓取欧赔数据"""
    url = f"https://odds.500.com/fenxi/ouzhi-{fixture_id}.shtml"
    content = fetch(url)
    return parse_ouzhi(content)

# 测试
if __name__ == '__main__':
    fixture_id = "1337830"
    results = fetch_ouzhi_by_fixture(fixture_id)
    print(f"抓取到 {len(results)} 家公司")
    for r in results[:5]:
        print(f"  {r['公司']}: 初盘({r['初盘胜']},{r['初盘平']},{r['初盘负']}) 即时({r['即时胜']},{r['即时平']},{r['即时负']})")
    
    # 保存
    with open('_test_ouzhi.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n已保存到 _test_ouzhi.json")
