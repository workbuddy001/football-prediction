import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from v7_8_segment_analyze import parse_source_file
from pathlib import Path

files = list(Path('3.10').glob('*_源数据.md'))
print(f'找到 {len(files)} 个文件')

for f in files[:3]:
    print(f"\n文件: {f.name}")
    data = parse_source_file(f)
    if data:
        print(f"  home_team: {data.get('home_team')}")
        print(f"  away_team: {data.get('away_team')}")
    else:
        print("  解析失败!")
