#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
    'Referer': 'https://m.sporttery.cn/',
}

# 下载导航JS
url = 'https://static.sporttery.cn/res_1_0/jcwm/default/jc/dzxx/jc_fbnavV1.js'
r = requests.get(url, headers=headers, timeout=10)
r.encoding = 'utf-8'
print(f'jc_fbnavV1.js 大小: {len(r.text)} 字节')

with open('jc_fbnavV1.js', 'w', encoding='utf-8') as f:
    f.write(r.text)

# 查找API和URL
apis = re.findall(r'["\']([^"\']*gateway[^"\']*)["\']', r.text)
print('\nAPI URL:')
for a in apis:
    print(f'  {a}')

# 查找函数调用
funcs = re.findall(r'function\s+(\w+)', r.text)
print(f'\n函数: {funcs[:20]}')

# 查找ajax调用
ajax = re.findall(r'ajaxFun\([^)]+\)', r.text)
print(f'\nAjax调用: {ajax[:10]}')
