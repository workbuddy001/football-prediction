import sys
sys.path.insert(0, 'd:\\work\\workbuddy\\足球预测\\分析模板')
from fetch_full import parse_shuju, parse_ouzhi
import json

print("验证利物浦 fixture=1373097 析数据...")
# 利物浦 fixture id 从之前 JSON 里确认
with open('d:/work/workbuddy/足球预测/分析模板/matches_full_2026-03-15.json', encoding='utf-8') as f:
    data = json.load(f)

# 找到 fixture_id 需要重新从 page_raw 拿
import re
with open('d:/work/workbuddy/足球预测/分析模板/page_raw.html', encoding='utf-8', errors='replace') as f:
    html = f.read()

rows = re.findall(r'<tr[^>]+class="bet-tb-tr[^"]*"([^>]+)>', html)
for attrs in rows:
    home = re.search(r'data-homesxname="([^"]*)"', attrs)
    fid  = re.search(r'data-fixtureid="([^"]*)"', attrs)
    if home and '利物浦' in home.group(1):
        fixture_id = fid.group(1)
        print(f"fixture_id = {fixture_id}")
        break

shuju = parse_shuju(fixture_id)
print(f"交战历史：{shuju.get('交战历史摘要', '未找到')}")
print(f"主队近况：{shuju.get('主队近况', '')}")
print(f"客队近况：{shuju.get('客队近况', '')}")
print("近期记录：")
for r in shuju.get('近期交战记录', []):
    print(f"  {r}")
