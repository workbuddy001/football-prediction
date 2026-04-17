#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
    'Referer': 'https://m.sporttery.cn/',
}

# 下载apis.js
url = 'https://static.sporttery.cn/res_1_0/jcwm/default/common/apis.js'
r = requests.get(url, headers=headers, timeout=10)
r.encoding = 'utf-8'

with open('apis.js', 'w', encoding='utf-8') as f:
    f.write(r.text)

print('apis.js 内容:')
print(r.text)
