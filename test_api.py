#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试竞彩网API"""
import requests
import json

def test_api():
    base_url = 'https://webapi.sporttery.cn/gateway/uniform/football/getFixedBonusV1.qry'
    
    # 不同的clientCode
    client_codes = ['3001', 'HTML5', '3002', 'H5', 'MOBILE']
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Referer': 'https://m.sporttery.cn/',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Origin': 'https://m.sporttery.cn',
    }

    for code in client_codes:
        params = {
            'clientCode': code,
            'matchId': '2039135'
        }
        
        print(f'\n测试 clientCode={code}')
        try:
            r = requests.get(base_url, params=params, headers=headers, timeout=10)
            print(f'  状态: {r.status_code}')
            print(f'  Content-Type: {r.headers.get("Content-Type", "")}')
            
            if 'json' in r.headers.get('Content-Type', ''):
                try:
                    data = r.json()
                    print(f'  JSON: {json.dumps(data, ensure_ascii=False)[:500]}')
                except:
                    print(f'  响应: {r.text[:200]}')
            else:
                print(f'  响应(前200字): {r.text[:200]}')
        except Exception as e:
            print(f'  错误: {e}')

    # 尝试添加时间戳
    import time
    print('\n\n带时间戳测试...')
    params = {
        'clientCode': '3001',
        'matchId': '2039135',
        '_': str(int(time.time() * 1000))
    }
    r = requests.get(base_url, params=params, headers=headers, timeout=10)
    print(f'状态: {r.status_code}')
    if 'json' in r.headers.get('Content-Type', ''):
        try:
            data = r.json()
            print(f'JSON: {json.dumps(data, ensure_ascii=False)[:500]}')
        except:
            print(f'响应: {r.text[:200]}')
    else:
        print(f'响应: {r.text[:200]}')

if __name__ == '__main__':
    test_api()
