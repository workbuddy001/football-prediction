# -*- coding: utf-8 -*-
import json

with open('分析模板/2026.04.17/matches_enhanced_2026-04-17.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

m = data[0]
print("完整数据结构:")
print("=" * 50)

def print_dict(d, indent=0):
    for k, v in d.items():
        if isinstance(v, dict):
            print("  " * indent + f"{k}:")
            print_dict(v, indent + 1)
        elif isinstance(v, list):
            if len(str(v)) < 100:
                print("  " * indent + f"{k}: {v}")
            else:
                print("  " * indent + f"{k}: [list with {len(v)} items]")
        else:
            print("  " * indent + f"{k}: {v}")

print_dict(m)
