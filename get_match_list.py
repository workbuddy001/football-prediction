#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""获取竞彩网比赛列表"""
import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
    'Referer': 'https://m.sporttery.cn/',
    'Accept': 'application/json',
}

# 尝试获取比赛列表
urls = [
    'https://webapi.sporttery.cn/gateway/football/getMatchList.qry',
    'https://webapi.sporttery.cn/gateway/mJCfootball/getMatchList.qry',
]

for url in urls:
    print(f'\n尝试: {url}')
    try:
        params = {'clientCode': '3001', 'gameNo': '2001'}
        r = requests.get(url, params=params, headers=headers, timeout=10)
        print(f'状态: {r.status_code}')
        if r.status_code == 200:
            data = r.json()
            success = data.get('success')
            print(f'success: {success}')
            print(f'data: {json.dumps(data, ensure_ascii=False)[:800]}')
    except Exception as e:
        print(f'错误: {e}')
