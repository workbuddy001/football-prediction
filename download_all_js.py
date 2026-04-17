#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import re
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
    'Referer': 'https://m.sporttery.cn/',
}

# 下载commonV1.js找API模式
url = 'https://static.sporttery.cn/res_1_0/common/js/commonV1.js'
r = requests.get(url, headers=headers, timeout=10)
r.encoding = 'utf-8'

print('commonV1.js 中的API:')
apis = re.findall(r'["\']([^"\']*gateway[^"\']*)["\']', r.text)
for a in set(apis):
    print(f'  {a}')

# 查找所有uniform相关的URL模式
uniform = re.findall(r'["\']([^"\']*uniform[^"\']*)["\']', r.text)
print('\nuniform相关:')
for u in set(uniform):
    print(f'  {u}')

# 查找可能的参数模式
params = re.findall(r'(?:clientCode|clientCode|gameNo|matchId|sportteryMatchId)[^&=]*', r.text)
print('\n参数:')
for p in set(params):
    print(f'  {p}')
