#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
500.com 比分赔率数据解析器
从WebFetch获取的HTML内容中解析比赛数据
"""

import re
import json
import os
from datetime import datetime

def parse_500_bifen_html(html_content):
    """解析500.com比分页面HTML"""
    matches = []

    # 匹配每场比赛的区块 - 简化版正则
    # 周五001, 周六023, 周日026 等编号
    match_blocks = re.split(r'\[(周\w+)\d+\]', html_content)

    current_day = ""
    for i, block in enumerate(match_blocks[1:], 1):  # 跳过第一个空块
        # 提取日期类型
        day_type = match_blocks[i] if i < len(match_blocks) else ""

        # 提取比赛ID (mid)
        mid_match = re.search(r'(?:shuju-|fenxi/shuju-)(\d+)\.shtml', block)
        if not mid_match:
            continue
        mid = mid_match.group(1)

        # 提取联赛名称
        league_match = re.search(r'\[([^\]]+)\]', block)
        league = league_match.group(1) if league_match else ""

        # 提取主队和客队
        team_match = re.search(r'\[?\d*\]?_\[([^\]]+)\]_?VS_?\[([^\]]+)\]_?\[?\d*\]?', block)
        if not team_match:
            # 尝试另一种格式
            team_match = re.search(r'([\u4e00-\u9fa5a-zA-Z]+)\s*VS\s*([\u4e00-\u9fa5a-zA-Z]+)', block)
        if not team_match:
            continue

        home_team = team_match.group(1).strip()
        away_team = team_match.group(2).strip()

        # 提取开赛时间
        time_match = re.search(r'(\d{2}-\d{2}\s+\d{2}:\d{2})', block)
        match_time = time_match.group(1) if time_match else ""

        # 解析比分赔率
        score_odds = {}

        # 主胜比分 (1:0, 2:0, 2:1, 3:0, ...)
        home_scores = re.findall(r'(\d):(\d)_(\d+\.?\d*)_', block)
        for score in home_scores:
            home_goals, away_goals, odds = score
            key = f"{home_goals}:{away_goals}"
            score_odds[key] = float(odds)

        # 提取胜其它、平其它、负其它
        other_match = re.search(r'胜其它_(\d+\.?\d*)_', block)
        if other_match:
            score_odds['胜其它'] = float(other_match.group(1))

        other_match = re.search(r'平其它_(\d+\.?\d*)_', block)
        if other_match:
            score_odds['平其它'] = float(other_match.group(1))

        other_match = re.search(r'负其它_(\d+\.?\d*)_', block)
        if other_match:
            score_odds['负其它'] = float(other_match.group(1))

        match_data = {
            "mid": mid,
            "day": day_type,
            "league": league,
            "home_team": home_team,
            "away_team": away_team,
            "match_time": match_time,
            "score_odds": score_odds,
            "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        matches.append(match_data)

    return matches


def extract_all_scores_from_text(text):
    """从原始文本提取所有比分赔率"""
    matches = []

    # 分割成单个比赛的块
    # 使用比赛ID来分割
    blocks = re.split(r'(?=shuju-\d+\.shtml)', text)

    current_day = "周五"
    for block in blocks:
        if 'shuju-' not in block:
            continue

        # 检测日期类型
        if '周六' in block[:200]:
            current_day = "周六"
        elif '周日' in block[:200]:
            current_day = "周日"

        # 提取mid
        mid_match = re.search(r'shuju-(\d+)\.shtml', block)
        if not mid_match:
            continue
        mid = mid_match.group(1)

        # 提取联赛
        league_match = re.search(r'\[([^\]]+联[赛甲乙丙丁]?)\]', block)
        league = league_match.group(1) if league_match else ""

        # 提取球队
        team_match = re.search(r'\[([^\]]+)\]\s*VS\s*\[([^\]]+)\]', block)
        if not team_match:
            continue
        home = team_match.group(1)
        away = team_match.group(2)

        # 提取时间
        time_match = re.search(r'(\d{2}-\d{2}\s+\d{2}:\d{2})', block)
        match_time = time_match.group(1) if time_match else ""

        # 解析比分赔率
        score_odds = {}

        # 匹配所有 "比分_赔率_" 格式
        all_scores = re.findall(r'(\d):(\d)_(\d+\.?\d*)_', block)
        for home_g, away_g, odds in all_scores:
            score_odds[f"{home_g}:{away_g}"] = float(odds)

        # 提取其他
        for t, key in [('胜其它', '胜其它'), ('平其它', '平其它'), ('负其它', '负其它')]:
            m = re.search(rf'{t}_(\d+\.?\d*)_', block)
            if m:
                score_odds[key] = float(m.group(1))

        if score_odds:
            matches.append({
                "mid": mid,
                "day": current_day,
                "league": league,
                "home_team": home,
                "away_team": away,
                "match_time": match_time,
                "score_odds": score_odds,
                "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    return matches


def save_matches_to_json(matches, output_dir):
    """保存比赛数据到JSON文件"""
    os.makedirs(output_dir, exist_ok=True)

    saved_files = []
    for match in matches:
        filename = f"{match['home_team']}vs{match['away_team']}_{match['mid']}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(match, f, ensure_ascii=False, indent=2)

        saved_files.append(filename)

    return saved_files


if __name__ == "__main__":
    # 这里可以手动粘贴HTML内容进行解析
    print("500.com 比分赔率解析器")
    print("使用方法：")
    print("1. 使用WebFetch获取 https://trade.500.com/jczq/?playid=271&g=2")
    print("2. 将返回的HTML内容保存到文件")
    print("3. 调用 parse_500_bifen_html() 或 extract_all_scores_from_text() 解析")
    print("4. 使用 save_matches_to_json() 保存到 sporttery_data 文件夹")
