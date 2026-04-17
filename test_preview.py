#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import json

base = 'https://webapi.sporttery.cn'
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
    'Referer': 'https://m.sporttery.cn/',
}

# 详细测试前瞻API
preview_apis = [
    '/gateway/uniform/football/getMatchAnalysisV1.qry?matchId=2039135',
    '/gateway/uniform/football/getMatchPreviewV1.qry?matchId=2039135',
    '/gateway/uniform/football/getMatchStandingV1.qry?matchId=2039135',
    '/gateway/uniform/football/getTeamInfoV1.qry?matchId=2039135',
]

for api in preview_apis:
    url = base + api
    print(f'\n=== {api.split("?")[0].split("/")[-1]} ===')
    try:
        r = requests.get(url, headers=headers, timeout=8)
        print(f'状态: {r.status_code}')
        print(f'Content-Type: {r.headers.get("Content-Type", "")}')
        
        # 尝试解析JSON
        try:
            data = r.json()
            print(f'JSON: {json.dumps(data, ensure_ascii=False)[:800]}')
        except:
            print(f'文本: {r.text[:500]}')
    except Exception as e:
        print(f'错误: {e}')
