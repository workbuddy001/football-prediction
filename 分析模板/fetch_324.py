#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
抓取500.com指定日期的比赛数据
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import os

def fetch_matches(date_str):
    """抓取指定日期的比赛"""
    url = f"https://trade.500.com/jczq/?playid=312&g=2&date={date_str}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"抓取页面: {url}")
    resp = requests.get(url, headers=headers)
    
    if resp.status_code != 200:
        print(f"请求失败: {resp.status_code}")
        return []
    
    html = resp.text
    
    # 保存原始HTML
    output_dir = "d:\\work\\workbuddy\\足球预测\\分析模板\\page_raw_2026-03-24.html"
    with open(output_dir, 'w', encoding='utf-8') as f:
        f.write(html)
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 解析比赛数据...
    # (这里省略详细的解析逻辑)
    
    return []

if __name__ == '__main__':
    fetch_matches('2026-03-24')
