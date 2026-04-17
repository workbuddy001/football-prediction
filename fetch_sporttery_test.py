#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""竞彩网数据抓取测试"""
import requests
import re
import json
import time

def fetch_sporttery():
    url = 'https://m.sporttery.cn/mjc/zqgdjjv1/?mid=2039135'
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    r = requests.get(url, headers=headers, timeout=15)
    print(f'Status: {r.status_code}')
    print(f'Content length: {len(r.text)}')

    # 查找script标签
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)
    print(f'\n找到 {len(scripts)} 个script标签')

    # 查找所有URL
    urls = re.findall(r'https?://[^\s"\'<>]+', r.text)
    print(f'\n所有URL: {urls[:30]}')

    # 查找可能的接口
    apis = re.findall(r'(?:/api/|/interface/|/data/)[\w/.?=&]+', r.text)
    print(f'\nAPI路径: {apis[:20]}')

    # 保存完整页面
    with open('sporttery_page.html', 'w', encoding='utf-8') as f:
        f.write(r.text)
    print('\n页面已保存到 sporttery_page.html')

    # 尝试常见API
    print('\n尝试常见API...')
    common_apis = [
        'https://m.sporttery.cn/api/football/match_detail?mid=2039135',
        'https://m.sporttery.cn/api/v1/match/detail?mid=2039135',
        'https://www.sporttery.cn/api/match_detail?mid=2039135',
        'https://www.sporttery.cn/interface/football/match?mid=2039135',
        'https://m.sporttery.cn/mjc/api/matchInfo?mid=2039135',
    ]

    for api_url in common_apis:
        try:
            r2 = requests.get(api_url, headers=headers, timeout=5)
            print(f'{api_url}: {r2.status_code}')
            if r2.status_code == 200:
                print(f'  Response: {r2.text[:200]}')
        except Exception as e:
            print(f'{api_url}: Error - {e}')


def try_chrome_devtools_protocol():
    """尝试Chrome DevTools协议 (需要Chrome以调试模式运行)"""
    import socket

    # 尝试连接到Chrome调试端口
    ports = [9222, 9223, 9224, 9333]

    for port in ports:
        try:
            # 获取标签页列表
            r = requests.get(f'http://localhost:{port}/json/list', timeout=2)
            if r.status_code == 200:
                tabs = r.json()
                print(f'\nChrome DevTools - 端口 {port}: {len(tabs)} 个标签页')
                for tab in tabs:
                    print(f'  - {tab.get("title", "No title")}: {tab.get("url", "")}')
                return tabs
        except:
            pass

    print('\n未找到Chrome调试端口')
    return []


if __name__ == '__main__':
    print('='*50)
    print('竞彩网数据抓取测试')
    print('='*50)

    fetch_sporttery()

    print('\n' + '='*50)
    print('Chrome DevTools 检查')
    print('='*50)
    try_chrome_devtools_protocol()
