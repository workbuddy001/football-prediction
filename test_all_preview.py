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

# 前瞻API列表
apis = [
    ('getMatchFeatureV1', '/gateway/uniform/football/getMatchFeatureV1.qry', '特征分析'),
    ('getResultHistoryV1', '/gateway/uniform/football/getResultHistoryV1.qry', '历史交锋'),
    ('getMatchTablesV1', '/gateway/uniform/football/getMatchTablesV1.qry', '积分榜'),
    ('getInjurySuspensionV1', '/gateway/uniform/football/getInjurySuspensionV1.qry', '伤停一览'),
    ('getFutureMatchesV1', '/gateway/uniform/football/getFutureMatchesV1.qry', '未来赛事'),
    ('getMatchResultV1', '/gateway/uniform/football/getMatchResultV1.qry', '比赛近况'),
    ('getMatchPlayerV1', '/gateway/uniform/football/getMatchPlayerV1.qry', '射手信息'),
]

# 尝试两种ID格式
id_formats = [
    'sportteryMatchId=2039135',
    'matchId=2039135',
]

for api_name, api_path, desc in apis:
    print('\n=== ' + desc + ' (' + api_name + ') ===')
    
    for id_format in id_formats:
        url = base + api_path + '?' + id_format
        try:
            r = requests.get(url, headers=headers, timeout=10)
            data = r.json()
            
            if data.get('errorCode') == '0' and data.get('value'):
                value = data.get('value', {})
                is_valid = False
                if isinstance(value, dict) and len(value) > 0:
                    is_valid = True
                    keys_info = 'dict, keys=' + str(list(value.keys()))
                elif isinstance(value, list) and len(value) > 0:
                    is_valid = True
                    keys_info = 'list, length=' + str(len(value))
                
                if is_valid:
                    print('  SUCCESS with ' + id_format + '!')
                    print('  ' + keys_info)
                    fname = 'preview_' + api_name + '.json'
                    with open(fname, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print('  已保存到 ' + fname)
                    break
                else:
                    print('  FAIL: ' + id_format + ' - 空数据')
            else:
                print('  FAIL: ' + id_format + ' - ' + str(data.get('errorMessage', '错误')))
        except Exception as e:
            print('  ERROR: ' + str(e))
