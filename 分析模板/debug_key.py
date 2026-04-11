# 调试lookup_key

# 来自actual_results的key格式
actual_results = {
    "3.12_周四001": "平局", "3.12_周四002": "平局",
}

# 从文件名提取的key
import re

files = [
    "周四001_淡宾尼士vs曼谷联_源数据.md",
    "周四002_博洛尼亚vs罗马_源数据.md",
]

for f in files:
    filename = f.replace('_源数据.md', '')
    match = re.search(r'([周\d]+)(\d+)_(.+)', filename)
    if match:
        date_num = match.group(1)  # 周四001
        num = match.group(2)
        print(f"filename: {filename}")
        print(f"  date_num: {date_num}, num: {num}")
        print(f"  lookup: 3.12_{date_num}")
