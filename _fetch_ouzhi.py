# -*- coding: utf-8 -*-
"""抓取欧赔详情页面数据"""
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
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=20)
    # 注意：500.com 使用 GBK 编码
    content = resp.read().decode('gbk', errors='replace')
    return content

def parse_ouzhi(content):
    """解析欧赔页面"""
    # 提取公司名称和赔率
    # 格式：初盘赔率 + 即时赔率
    # 例如: 1.83 3.90 3.06 1.91 3.92 2.85 (初盘胜平负 + 即时胜平负)
    
    results = []
    
    # 匹配赔率行
    # 格式：公司名 | 胜 平 负 | 胜 平 负 | ...
    rows = re.findall(
        r'<td[^>]*class="[^"]*brg[^"]*"[^>]*>(.*?)</td>\s*<td[^>]*class="[^"]*brg[^"]*"[^>]*>(.*?)</td>\s*<td[^>]*class="[^"]*brg[^"]*"[^>]*>(.*?)</td>\s*<td[^>]*class="[^"]*brg[^"]*"[^>]*>(.*?)</td>\s*<td[^>]*class="[^"]*brg[^"]*"[^>]*>(.*?)</td>',
        content, re.S
    )
    
    # 尝试另一种匹配
    # 匹配公司行
    company_pattern = re.compile(r'<td[^>]*>(.*?)</td>', re.S)
    
    # 先找到表格
    tables = re.findall(r'<table[^>]*class="[^"]*ouzhi-table[^"]*"[^>]*>(.*?)</table>', content, re.S)
    if not tables:
        tables = re.findall(r'<table[^>]*>(.*?)</table>', content, re.S)
    
    print(f"找到 {len(tables)} 个表格")
    
    # 打印一些关键内容用于调试
    # 搜索赔率数据
    odds_lines = re.findall(r'(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)', content)
    print(f"找到 {len(odds_lines)} 行赔率数据")
    
    if odds_lines:
        print("\n前5行赔率数据 (初盘胜平负 + 即时胜平负):")
        for i, line in enumerate(odds_lines[:5]):
            print(f"  {line}")
    
    return odds_lines

# 测试
url = "https://odds.500.com/fenxi/ouzhi-1337830.shtml"
content = fetch(url)
print(f"页面大小: {len(content)} 字符")

# 保存页面内容
with open('_ouzhi_page.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("页面已保存到 _ouzhi_page.html")

# 解析赔率
parse_ouzhi(content)
