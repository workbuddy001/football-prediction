#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import json
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = 'https://webapi.sporttery.cn'
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
    'Referer': 'https://m.sporttery.cn/',
}

# 根据菜单关键词尝试API
apis = [
    '/gateway/uniform/football/getMatchAnalysisV1.qry?clientCode=3001&matchId=2039135',
    '/gateway/uniform/football/getMatchFeatureV1.qry?clientCode=3001&matchId=2039135',
    '/gateway/uniform/football/getMatchHistoryV1.qry?clientCode=3001&matchId=2039135',
    '/gateway/uniform/football/getMatchStandingV1.qry?clientCode=3001&matchId=2039135',
    '/gateway/uniform/football/getMatchRecentV1.qry?clientCode=3001&matchId=2039135',
    '/gateway/uniform/football/getMatchInjuryV1.qry?clientCode=3001&matchId=2039135',
    '/gateway/uniform/football/getMatchDetailV1.qry?clientCode=3001&matchId=2039135',
    # 尝试完整matchId格式
    '/gateway/uniform/football/getMatchAnalysisV1.qry?clientCode=3001&matchId=2039135&type=all',
]

for api in apis:
    url = base + api
    name = api.split('?')[0].split('/')[-1]
    try:
        r = requests.get(url, headers=headers, timeout=8)
        data = r.json()
        if data.get('errorCode') == '0':
            print('SUCCESS: ' + name)
            print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
        else:
            print('FAIL: ' + name + ' - ' + str(data.get('errorMessage', '')))
    except Exception as e:
        print('ERROR: ' + name + ' - ' + str(e)[:50])
    print()
