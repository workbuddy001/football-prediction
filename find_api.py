#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""获取竞彩网API的clientCode"""
import requests
import re

# 获取commonV1.js
js_url = 'https://static.sporttery.cn/res_1_0/common/js/commonV1.js'
r = requests.get(js_url, timeout=10)
r.encoding = 'utf-8'

print(f'JS长度: {len(r.text)}')

# 查找clientCode
patterns = [
    r'clientCode.*?=.*?["\']([^"\']+)["\']',
    r'comClientCode.*?=.*?["\']([^"\']+)["\']',
    r'"clientCode"\s*:\s*["\']([^"\']+)["\']',
]

for p in patterns:
    match = re.search(p, r.text)
    if match:
        print(f'找到 clientCode: {match.group(1)}')
        client_code = match.group(1)
        break

# 打印相关代码
for line in r.text.split('\n'):
    if 'clientCode' in line or 'comClient' in line:
        print(f'相关行: {line}')

# 测试API
api_url = 'https://webapi.sporttery.cn/gateway/uniform/football/getFixedBonusV1.qry'
params = {
    'clientCode': 'HTML5',
    'matchId': '2039135'
}

print('\n测试API...')
r2 = requests.get(api_url, params=params, timeout=10)
print(f'状态: {r2.status_code}')
print(f'响应: {r2.text[:1000]}')
