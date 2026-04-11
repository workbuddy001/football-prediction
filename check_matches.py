# -*- coding: utf-8 -*-
import json
from pathlib import Path

# 检查最新的比赛数据
for f in Path('.').rglob('*.json'):
    if '2026' in f.name:
        print(f.name)
        # 尝试读取内容
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                if isinstance(data, list) and len(data) > 0:
                    print(f"  比赛数: {len(data)}")
                    if 'match_time' in data[0]:
                        print(f"  时间: {data[0]['match_time']}")
        except:
            pass
