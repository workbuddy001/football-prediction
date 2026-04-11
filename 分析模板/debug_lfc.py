import urllib.request, re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://trade.500.com/',
}

url = 'https://odds.500.com/fenxi/ouzhi-1202689.shtml'
req = urllib.request.Request(url, headers=headers)
resp = urllib.request.urlopen(req, timeout=15)
content = resp.read().decode('gbk', errors='replace')

with open('d:\\work\\workbuddy\\足球预测\\分析模板\\preview_lfc.html', 'w', encoding='utf-8') as f:
    f.write(content)

# 查找 ttl 属性行
rows = re.findall(r'<tr[^>]+ttl="zy"[^>]*>(.*?)</tr>', content, re.S)
print(f"ttl='zy' 行数: {len(rows)}")

# 尝试其他模式
rows2 = re.findall(r'<tr[^>]+ttl[^>]*xls="row"[^>]*>(.*?)</tr>', content, re.S)
print(f"含 xls='row' 行数: {len(rows2)}")

rows3 = re.findall(r'<tr[^>]+xls="row"[^>]*>(.*?)</tr>', content, re.S)
print(f"xls='row' 行数: {len(rows3)}")

# 打印前几行结构
for i, row in enumerate(rows3[:2]):
    print(f"\n--- 行{i+1} ---")
    print(row[:800])
