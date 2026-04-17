#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import re

# 获取竞彩完整页面前瞻部分
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
}

# 尝试前瞻页面URL
urls = [
    'https://m.sporttery.cn/mjc/zqqzy/index.html?mid=2039135',  # 赛事摘要/前瞻
    'https://m.sporttery.cn/mjc/zqgz/index.html?mid=2039135',  # 比赛前瞻
    'https://m.sporttery.cn/zqlszl/qzyc/index.html?mid=2039135',  # 前瞻预测
    'https://m.sporttery.cn/mjc/zqtz/index.html?mid=2039135',  # 投注
]

for url in urls:
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'utf-8'
        print(f'\n=== {url} ===')
        print(f'状态: {r.status_code}')
        
        # 查找JS文件
        js = re.findall(r'src=["\'](.*?\.js)["\']', r.text)
        if js:
            print(f'JS文件: {js[:3]}')
        
        # 查找API
        apis = re.findall(r'gateway/[^"\'<>\s]+', r.text)
        if apis:
            print(f'API: {apis[:5]}')
        
        # 保存页面
        if r.status_code == 200 and '前瞻' in r.text:
            fname = url.split('/')[-1].split('?')[0] + '.html'
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(r.text)
            print(f'保存到 {fname}')
    except Exception as e:
        print(f'{url}: 错误 - {e}')
