"""
竞彩数据抓取工具 v2
通过HTML页面解析获取数据
"""

import json
import os
import re
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "sporttery_data")
os.makedirs(DATA_DIR, exist_ok=True)


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}


def fetch_match_page(mid):
    """抓取比赛页面HTML"""
    url = f"https://m.sporttery.cn/mjc/zqgdjjv1/?mid={mid}"
    print(f"正在抓取: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = 'utf-8'
        return resp.text
    except Exception as e:
        print(f"抓取失败: {e}")
        return None


def parse_match_page(html, mid):
    """解析比赛页面HTML"""
    if not html:
        return None

    data = {
        "mid": mid,
        "time": datetime.now().strftime('%Y-%m-%d'),
        "score_odds": {},
        "total_goals": {},
        "win_draw_lose": {"current": {}},
    }

    # 解析比分赔率 - 查找 "数字:数字" 格式
    score_pattern = r'(\d+):(\d+)[^>]*?(\d+\.?\d*)'
    for m in re.finditer(score_pattern, html):
        home, away, odds = m.group(1), m.group(2), m.group(3)
        try:
            odds = float(odds)
            if 1 <= odds <= 300:  # 合理的赔率范围
                key = f"{home}:{away}"
                if key not in data['score_odds']:
                    data['score_odds'][key] = odds
        except:
            continue

    # 解析总进球
    goals_pattern = r'(\d+\+?)[进球\s]+(\d+\.?\d*)'
    for m in re.finditer(goals_pattern, html):
        goals, odds = m.group(1), m.group(2)
        try:
            data['total_goals'][goals] = float(odds)
        except:
            continue

    # 解析胜平负
    wdl_pattern = r'[\u80DC\u5E73\u8D1F][\u80DC\u5E73\u8D1F]?\s*[>:：]\s*(\d+\.?\d*)'
    matches = re.findall(wdl_pattern, html)
    if len(matches) >= 3:
        try:
            data['win_draw_lose']['current'] = {
                'home': float(matches[0]),
                'draw': float(matches[1]),
                'away': float(matches[2])
            }
        except:
            pass

    # 尝试提取球队名
    team_pattern = r'([\u4e00-\u9fff]+)\s*vs\s*([\u4e00-\u9fff]+)'
    team_match = re.search(team_pattern, html)
    if team_match:
        data['home_team'] = team_match.group(1)
        data['away_team'] = team_match.group(2)

    return data if data['score_odds'] else None


def save_match(data, filename=None):
    """保存比赛数据"""
    if not data:
        return False

    if not filename:
        teams = f"{data.get('home_team', '')}vs{data.get('away_team', '')}"
        filename = f"{teams}_{data.get('mid', '')}.json"

    filename = "".join(c for c in filename if c.isalnum() or c in '._-()' or '\u4e00' <= c <= '\u9fff')
    if not filename.endswith('.json'):
        filename += '.json'

    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已保存: {filepath}")
    return True


def fetch_single(mid):
    """抓取单场比赛"""
    html = fetch_match_page(mid)
    if html:
        data = parse_match_page(html, mid)
        if data:
            save_match(data)
            return data
    return None


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='竞彩数据抓取')
    parser.add_argument('-m', '--mid', type=str, required=True, help='比赛ID')
    args = parser.parse_args()

    print("竞彩数据抓取工具 v2")
    print("="*50)

    result = fetch_single(args.mid)
    if result:
        print(f"\n成功! 提取到 {len(result['score_odds'])} 个比分赔率")
    else:
        print("\n抓取失败，页面可能需要登录或JavaScript渲染")
