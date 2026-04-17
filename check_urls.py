#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import json

# 测试竞彩网的多个可能API
base = 'https://webapi.sporttery.cn'
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
    'Referer': 'https://m.sporttery.cn/',
}

# 已知的API
known_apis = [
    '/gateway/uniform/football/getFixedBonusV1.qry?clientCode=3001&matchId=2039135',
    '/gateway/uniform/football/getMatchHeadV1.qry?source=m&sportteryMatchId=2039135',
    '/gateway/uniform/football/getMatchInfoAndVoteV1.qry?matchId=2039135',
]

# 尝试获取前瞻数据（伤停、交锋等）
preview_apis = [
    '/gateway/uniform/football/getMatchAnalysisV1.qry?matchId=2039135',
    '/gateway/uniform/football/getMatchPreviewV1.qry?matchId=2039135',
    '/gateway/uniform/football/getMatchStandingV1.qry?matchId=2039135',
    '/gateway/uniform/football/getTeamInfoV1.qry?matchId=2039135',
    '/gateway/football/getMatchAnalysis.qry?matchId=2039135',
    '/mjc/football/getMatchData?mid=2039135',
]

print('测试前瞻相关API:')
for api in preview_apis:
    url = base + api
    try:
        r = requests.get(url, headers=headers, timeout=8)
        print(f'{api[:50]}...: {r.status_code}')
        if r.status_code == 200:
            try:
                data = r.json()
                if data.get('errorCode') == 0 or data.get('success'):
                    print(f'  ✅ 成功! keys: {list(data.keys()) if isinstance(data, dict) else type(data)}')
                    print(f'  数据: {json.dumps(data, ensure_ascii=False)[:500]}')
            except:
                pass
    except Exception as e:
        print(f'{api[:40]}...: 错误 - {str(e)[:30]}')
    print()
