#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞彩足球分析系统 - 完整版
包含：赔率数据 + 前瞻数据（特征分析、历史交锋、积分榜、伤停、射手等）
"""
from flask import Flask, jsonify, request
import os
import json
import sys
import io
import requests
from datetime import datetime

# Windows UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

app = Flask(__name__)
DATA_DIR = 'sporttery_data'
os.makedirs(DATA_DIR, exist_ok=True)

# API配置
API_BASE = 'https://webapi.sporttery.cn'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
    'Referer': 'https://m.sporttery.cn/',
}

# ============ 前瞻API ============
PREVIEW_APIS = {
    'match_info': '/gateway/uniform/football/getMatchHeadV1.qry?source=m',
    'fixed_bonus': '/gateway/uniform/football/getFixedBonusV1.qry',
    'match_feature': '/gateway/uniform/football/getMatchFeatureV1.qry',
    'result_history': '/gateway/uniform/football/getResultHistoryV1.qry',
    'match_tables': '/gateway/uniform/football/getMatchTablesV1.qry',
    'injury': '/gateway/uniform/football/getInjurySuspensionV1.qry',
    'match_result': '/gateway/uniform/football/getMatchResultV1.qry',
    'match_player': '/gateway/uniform/football/getMatchPlayerV1.qry',
}

def fetch_preview(match_id):
    """获取前瞻数据"""
    result = {}
    match_id = str(match_id)
    
    for name, api_path in PREVIEW_APIS.items():
        url = f"{API_BASE}{api_path}?clientCode=3001&sportteryMatchId={match_id}"
        
        # 特殊参数
        if name == 'match_feature':
            url += '&termLimits=10'
        elif name == 'result_history':
            url += '&termLimits=5'
        elif name == 'match_result':
            url += '&termLimits=5'
        elif name == 'match_player':
            url += '&termLimits=3'
        
        try:
            r = requests.get(url, headers=HEADERS, timeout=8)
            data = r.json()
            if data.get('errorCode') == '0' and data.get('value'):
                result[name] = data['value']
            else:
                result[name] = {}
        except:
            result[name] = {}
    
    return result

def fetch_fixed_bonus(match_id):
    """获取固定奖金赔率"""
    url = f"{API_BASE}/gateway/uniform/football/getFixedBonusV1.qry?clientCode=3001&matchId={match_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        data = r.json()
        if data.get('errorCode') == '0':
            return data.get('value', {})
    except:
        pass
    return {}

def parse_fixed_bonus(odds_data):
    """解析赔率数据"""
    result = {
        'had': {},
        'hhad': {},
        'ttg': {},
        'hafu': {},
        'score_odds': {},
        'total_goals': {}
    }
    
    odds = odds_data.get('oddsHistory', {})
    
    # 胜平负 had: h=主胜, d=平, a=客胜
    had_list = odds.get('hadList', [])
    if had_list:
        latest = had_list[-1]
        result['had'] = {
            '主胜': latest.get('h', 0),
            '平局': latest.get('d', 0),
            '主负': latest.get('a', 0),
        }
    
    # 让球胜平负
    hhad_list = odds.get('hhadList', [])
    if hhad_list:
        latest = hhad_list[-1]
        result['hhad'] = {
            '让球数': latest.get('goalLine', ''),
            '让胜': latest.get('h', 0),
            '让平': latest.get('d', 0),
            '让负': latest.get('a', 0),
        }
    
    # 总进球 ttg
    ttg_list = odds.get('ttgList', [])
    if ttg_list:
        latest = ttg_list[-1]
        for i in range(8):
            key = 's' + str(i)
            if i < 7:
                result['total_goals'][str(i) + '球'] = latest.get(key, 0)
            else:
                result['total_goals']['7+球'] = latest.get(key, 0)
    
    # 比分 crs
    crs_list = odds.get('crsList', [])
    if crs_list:
        import re
        latest = crs_list[-1]
        pattern = re.compile(r'^s(\d+)s(\d+)$')
        for key, value in latest.items():
            if key.startswith('s') and 'f' not in key and not key.startswith('s-'):
                match = pattern.match(key)
                if match:
                    home = str(int(match.group(1)))
                    away = str(int(match.group(2)))
                    result['score_odds'][f"{home}:{away}"] = float(value)
    
    return result

# ============ Flask路由 ============

@app.route('/')
def index():
    return open('sporttery_full.html', 'r', encoding='utf-8').read()

@app.route('/api/analyze/<match_id>')
def analyze(match_id):
    """分析指定比赛"""
    match_id = str(match_id)
    
    # 1. 获取前瞻数据
    preview = fetch_preview(match_id)
    
    # 2. 获取赔率数据
    bonus = fetch_fixed_bonus(match_id)
    odds = parse_fixed_bonus(bonus)
    
    # 3. 整合数据
    match_info = preview.get('match_info', {})
    
    data = {
        'match_id': match_id,
        'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'match_info': {
            'home_team': match_info.get('homeTeamShortName', ''),
            'away_team': match_info.get('awayTeamShortName', ''),
            'league': match_info.get('tournamentCnShortName', ''),
            'time': match_info.get('matchDateTime', ''),
        },
        **odds,
        'preview': {
            'feature': preview.get('match_feature', {}),
            'history': preview.get('result_history', {}),
            'tables': preview.get('match_tables', {}),
            'injury': preview.get('injury', {}),
            'recent': preview.get('match_result', {}),
            'player': preview.get('match_player', {}),
        }
    }
    
    # 保存
    save_path = os.path.join(DATA_DIR, f'full_{match_id}.json')
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return jsonify(data)

@app.route('/api/matches')
def matches():
    """获取已保存的比赛列表"""
    files = glob.glob(os.path.join(DATA_DIR, 'full_*.json'))
    result = []
    for f in sorted(files, key=os.path.getmtime, reverse=True):
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                result.append({
                    'match_id': data.get('match_id'),
                    'fetch_time': data.get('fetch_time'),
                    'home': data.get('match_info', {}).get('home_team'),
                    'away': data.get('match_info', {}).get('away_team'),
                    'league': data.get('match_info', {}).get('league'),
                })
        except:
            pass
    return jsonify(result)

if __name__ == '__main__':
    print("启动竞彩足球分析系统...")
    print("访问 http://localhost:8899")
    app.run(host='0.0.0.0', port=8899, debug=False)
