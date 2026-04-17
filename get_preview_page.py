#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import re
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
}

# 获取完整的竞彩对阵数据页面
url = 'https://m.sporttery.cn/zqlszl/bssj/index.html?mid=2039135'
r = requests.get(url, headers=headers, timeout=15)
r.encoding = 'utf-8'

print(f'页面大小: {len(r.text)} 字节')

# 保存完整页面
with open('bssj_full.html', 'w', encoding='utf-8') as f:
    f.write(r.text)

# 查找JS文件
js_files = re.findall(r'<script[^>]+src=["\'](.*?)["\']', r.text)
print('\nJS文件:')
for f in js_files:
    print(f'  {f}')

# 查找所有URL
urls = re.findall(r'["\']([^"\']*api[^"\']*)["\']', r.text)
print('\nAPI URL:')
for u in urls[:20]:
    print(f'  {u}')

# 查找前瞻相关
preview = re.findall(r'(?:前瞻|feature|analysis|伤停|injury|交锋|历史)[^<>"\']*', r.text[:10000])
print('\n前瞻相关内容:')
for p in preview[:10]:
    print(f'  {p[:100]}')
