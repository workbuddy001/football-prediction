#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量抓取竞彩网比赛数据
"""
import time
import json
import sys
import io
from sporttery_api import SportteryAPI

# Windows UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 从500.com获取的比赛ID列表（部分）
MATCH_IDS = [
    '1337830',  # 周五001 墨胜利vs纽喷气机
    '1223036',  # 周五002 埃沃斯堡vs卡斯鲁厄
    '1199675',  # 周五003 萨索洛vs科莫
    '1362624',  # 周五004 佐加顿斯vs马尔默
    '1212041',  # 周五005 勒芒vs克莱蒙
    '1390299',  # 周五006 阿尔梅勒vs多德勒支
    '1206143',  # 周五007 圣保利vs科隆
    '1199670',  # 周五008 国米vs卡利亚里
    '1205878',  # 周五009 朗斯vs图卢兹
    '1210472',  # 周五010 布莱克本vs考文垂
    '1216200',  # 周五011 里奥阿维vs阿维斯
    '1358267',  # 周五012 温哥华vs堪萨斯城
]

def main():
    api = SportteryAPI()
    
    print('='*60)
    print('竞彩网批量数据抓取')
    print('='*60)
    
    success_count = 0
    fail_count = 0
    
    for mid in MATCH_IDS:
        try:
            result = api.fetch_and_save(mid)
            if result:
                success_count += 1
                print(f"✓ {mid}: {result['match_info']['home_team']} vs {result['match_info']['away_team']}")
            else:
                fail_count += 1
                print(f"✗ {mid}: 获取失败")
            
            time.sleep(0.5)  # 避免请求过快
            
        except Exception as e:
            fail_count += 1
            print(f"✗ {mid}: 错误 - {e}")
    
    print('\n' + '='*60)
    print(f'抓取完成！成功: {success_count}, 失败: {fail_count}')
    print('='*60)


if __name__ == '__main__':
    main()
