import requests
headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)', 'Referer': 'https://m.sporttery.cn/'}
# 测试多个ID
for mid in ['2039135', '2039140', '2039150', '2039160']:
    url = f'https://webapi.sporttery.cn/gateway/uniform/football/getMatchFeatureV1.qry?clientCode=3001&matchId={mid}'
    r = requests.get(url, headers=headers, timeout=10)
    d = r.json()
    val = d.get('value', {})
    print(f'{mid}: success={d.get("success")}, hasData={bool(val)}, val={str(val)[:100]}')
