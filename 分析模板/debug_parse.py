#!/usr/bin/env python3
from v7_8_segment_analyze import parse_source_file
from pathlib import Path

files = list(Path('3.10').glob('*_源数据.md'))
print(f'找到 {len(files)} 个文件')

if files:
    data = parse_source_file(files[0])
    print('解析结果:', data)
    if data:
        print('keys:', data.keys())
    else:
        print('解析失败')
