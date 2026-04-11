import urllib.request, re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://odds.500.com/',
}

content = open('d:\\work\\workbuddy\\足球预测\\分析模板\\preview_lfc.html', encoding='utf-8').read()

rows = re.findall(r'<tr[^>]+xls="row"[^>]*>(.*?)</tr>', content, re.S)
print(f"行数: {len(rows)}")

row = rows[0]
print(f"\n第1行长度: {len(row)}")
print("前500字符:")
print(row[:500])
print("\n---")

# 检查 quancheng 
co_m = re.search(r'<span class="quancheng"[^>]*>([^<]+)</span>', row)
print(f"公司: {co_m.group(1) if co_m else 'NOT FOUND'}")

# 检查 tr_bdb
bdb = re.search(r'tr_bdb', row)
print(f"tr_bdb 存在: {bool(bdb)}")

# 尝试找到赔率数字
tds_kl = re.findall(r'klfc="([\d.]+)"', row)
print(f"klfc值: {tds_kl}")

# 找 td 中的数字
all_nums = re.findall(r'<td[^>]*>\s*([\d.]+)\s*</td>', row)
print(f"所有数字td: {all_nums[:10]}")
