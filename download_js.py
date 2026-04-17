#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import re

# 下载关键JS文件
js_urls = [
    'https://static.sporttery.cn/res_1_0/jcwm/default/jc/dzxx/dz_commonV1.js',
    'https://static.sporttery.cn/res_1_0/jcwm/default/jc/dzxx/jc_gdjjV1.js',
]

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
    'Referer': 'https://m.sporttery.cn/',
}

for url in js_urls:
    fname = url.split('/')[-1]
    print(f'下载: {fname}')
    r = requests.get(url, headers=headers, timeout=10)
    r.encoding = 'utf-8'
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(r.text)
    print(f'  大小: {len(r.text)} 字节')

    # 查找API调用
    apis = re.findall(r'["\']([^"\']*gateway[^"\']*)["\']', r.text)
    if apis:
        print(f'  找到API: {apis[:5]}')

    # 查找URL模式
    urls = re.findall(r'url\s*:\s*["\']([^"\']+)["\']', r.text)
    if urls:
        print(f'  URL模式: {urls[:10]}')

    # 查找其他域名
    domains = re.findall(r'["\']([^"\']*sporttery[^"\']*)["\']', r.text)
    print(f'  域名引用: {domains[:10]}')
    print()
