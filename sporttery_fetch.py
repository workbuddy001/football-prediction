"""
竞彩数据抓取脚本
抓取比赛数据并保存到 sporttery_data 文件夹
"""

import json
import os
import requests
from datetime import datetime
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "sporttery_data")
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://m.sporttery.cn/',
}


def fetch_match_detail(mid):
    """抓取指定比赛详情"""
    print(f"正在抓取比赛 {mid}...")

    apis = [
        f"https://i.sporttery.cn/api/fb_match_info/get_fb_match_info?mid={mid}",
        f"https://m.sporttery.cn/api/fb_match_info/get_fb_match_info?mid={mid}",
    ]

    for url in apis:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and data.get('result'):
                    print(f"成功从 API 获取")
                    return data
        except Exception as e:
            print(f"API失败: {e}")
            continue

    print(f"无法获取比赛 {mid}")
    return None


def fetch_match_list():
    """获取今日比赛列表"""
    print("正在获取比赛列表...")

    apis = [
        "https://i.sporttery.cn/api/fb_match_info/get_fb_match_schedule",
    ]

    for url in apis:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and data.get('result'):
                    print(f"成功获取比赛列表")
                    return data
        except Exception as e:
            print(f"获取列表失败: {e}")
            continue

    print("无法获取比赛列表")
    return None


def parse_match_data(raw_data):
    """解析原始数据"""
    result = raw_data.get('result', {})
    if not result:
        return None

    match_info = result.get('match_info', {})
    odds_info = result.get('odds_info', {})

    data = {
        "mid": match_info.get('mid', ''),
        "time": datetime.now().strftime('%Y-%m-%d'),
        "home_team": match_info.get('home_name', ''),
        "away_team": match_info.get('away_name', ''),
        "league": match_info.get('league_name', ''),
        "match_time": match_info.get('match_time', ''),
    }

    # 比分赔率
    score_odds = odds_info.get('score_odds', {})
    if score_odds:
        data['score_odds'] = score_odds

    # 总进球
    goals_odds = odds_info.get('total_goals_odds', odds_info.get('total_goals', {}))
    if goals_odds:
        data['total_goals'] = goals_odds

    # 胜平负
    wdl = odds_info.get('had_odds', odds_info.get('win_draw_lose', {}))
    if wdl:
        data['win_draw_lose'] = {'current': wdl}

    return data


def save_match(mid, data, filename=None):
    """保存比赛数据"""
    if not data:
        return False

    if not filename:
        teams = f"{data.get('home_team', '')}vs{data.get('away_team', '')}"
        filename = f"{teams}_{mid}.json"

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
    raw = fetch_match_detail(mid)
    if raw:
        data = parse_match_data(raw)
        if data:
            save_match(mid, data)
            return data
    return None


def fetch_all_today():
    """抓取今日所有比赛"""
    list_data = fetch_match_list()
    if not list_data:
        return []

    saved = []
    result = list_data.get('result', {})
    matches = result.get('match_list', result.get('matches', []))

    print(f"\n找到 {len(matches)} 场比赛\n")

    for match in matches:
        mid = match.get('mid')
        if mid:
            raw = fetch_match_detail(mid)
            if raw:
                data = parse_match_data(raw)
                if data:
                    save_match(mid, data)
                    saved.append(mid)
            time.sleep(0.5)

    return saved


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--mid', type=str, help='比赛ID')
    parser.add_argument('-a', '--all', action='store_true', help='抓取今日所有')
    args = parser.parse_args()

    print("竞彩数据抓取工具")
    print("="*50)

    if args.mid:
        fetch_single(args.mid)
    elif args.all:
        saved = fetch_all_today()
        print(f"\n完成! 共保存 {len(saved)} 场")
    else:
        print("\n用法:")
        print("  python sporttery_fetch.py -m 2039135")
        print("  python sporttery_fetch.py -a")
