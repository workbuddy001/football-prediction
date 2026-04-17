#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import json

base = 'https://webapi.sporttery.cn'
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
    'Referer': 'https://m.sporttery.cn/',
}

# 带clientCode的前瞻API
preview_apis = [
    '/gateway/uniform/football/getMatchAnalysisV1.qry?clientCode=3001&matchId=2039135',
    '/gateway/uniform/football/getMatchPreviewV1.qry?clientCode=3001&matchId=2039135',
    '/gateway/uniform/football/getMatchStandingV1.qry?clientCode=3001&matchId=2039135',
    '/gateway/uniform/football/getTeamInfoV1.qry?clientCode=3001&matchId=2039135',
    # 尝试不同的ID格式
    '/gateway/uniform/football/getMatchAnalysisV1.qry?clientCode=3001&sportteryMatchId=2039135',
    '/gateway/uniform/football/getMatchAnalysisV1.qry?clientCode=3001&mid=2039135',
]

for api in preview_apis:
    url = base + api
    name = api.split('?')[0].split("/")[-1]
    print(f'\n=== {name} ===')
    try:
        r = requests.get(url, headers=headers, timeout=8)
        data = r.json()
        if data.get('errorCode') == '0' or data.get('success'):
            print(f'✅ 成功!')
            print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
        else:
            print(f'❌ {data.get("errorMessage", "错误")}')
    except Exception as e:
        print(f'错误: {e}')
