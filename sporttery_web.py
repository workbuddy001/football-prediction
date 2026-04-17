#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞彩比分预测系统 - 完整版
"""
from flask import Flask, jsonify, render_template_string
import os
import json
import glob
from sporttery_api import SportteryAPI

app = Flask(__name__)
DATA_DIR = 'sporttery_data'

# 比分预测分析函数
def analyze_match(data):
    """分析比赛，返回预测结果"""
    result = {
        'prediction': '未知',
        'confidence': 0,
        'reason': [],
        'recommended_odds': []
    }
    
    score_odds = data.get('score_odds', {})
    total_goals = data.get('total_goals', {})
    had = data.get('had', {})
    match_info = data.get('match_info', {})
    
    if not score_odds:
        return result
    
    # 1. 找出最低赔率的比分
    valid_scores = {k: v for k, v in score_odds.items() if v and v > 0 and k.count(':') == 1}
    if valid_scores:
        sorted_scores = sorted(valid_scores.items(), key=lambda x: float(x[1]))
        top3 = sorted_scores[:3]
        
        result['recommended_odds'] = [
            {'score': s, 'odds': o} for s, o in top3
        ]
        
        # 分析
        low_odds = float(top3[0][1])
        if low_odds < 5:
            result['confidence'] = 3
            result['reason'].append(f'最低赔率{top3[0][0]}={low_odds}，值得关注')
        elif low_odds < 8:
            result['confidence'] = 2
            result['reason'].append(f'最低赔率{top3[0][0]}={low_odds}')
        else:
            result['confidence'] = 1
            result['reason'].append('赔率较高，需谨慎')
    
    # 2. 分析总进球趋势
    if total_goals:
        valid_goals = {k: v for k, v in total_goals.items() if v and v > 0}
        if valid_goals:
            sorted_goals = sorted(valid_goals.items(), key=lambda x: float(x[1]))
            result['total_goals_prediction'] = sorted_goals[0][0]
            result['reason'].append(f'总进球推荐: {sorted_goals[0][0]}')
    
    # 3. 分析胜平负
    if had:
        valid_had = {k: v for k, v in had.items() if v and float(v) > 0 and k != '更新时间'}
        if valid_had:
            sorted_had = sorted(valid_had.items(), key=lambda x: float(x[1]))
            result['win_draw_lose'] = sorted_had[0][0]
            result['reason'].append(f'胜平负推荐: {sorted_had[0][0]} ({sorted_had[0][1]})')
    
    # 4. 综合判断
    if result['confidence'] >= 2 and result.get('win_draw_lose'):
        result['prediction'] = f"{result['win_draw_lose']}，比分关注 {top3[0][0] if top3 else '未知'}"
    elif result.get('total_goals_prediction'):
        result['prediction'] = f"总进球: {result['total_goals_prediction']}"
    
    return result


# HTML模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>竞彩比分预测系统</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #fff; min-height: 100vh; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { text-align: center; color: #00d4ff; margin-bottom: 30px; font-size: 28px; }
        .controls { display: flex; gap: 15px; justify-content: center; margin-bottom: 30px; flex-wrap: wrap; }
        .controls input { padding: 12px 20px; border: 2px solid #00d4ff; border-radius: 8px; background: #16213e; color: #fff; font-size: 16px; width: 200px; }
        .controls button { padding: 12px 30px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; transition: all 0.3s; }
        .btn-fetch { background: #00d4ff; color: #1a1a2e; }
        .btn-fetch:hover { background: #00b4d8; }
        .btn-refresh { background: #e94560; color: #fff; }
        .btn-refresh:hover { background: #c73e54; }
        .match-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; }
        .match-card { background: #16213e; border-radius: 12px; padding: 20px; border: 1px solid #0f3460; transition: all 0.3s; }
        .match-card:hover { transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0, 212, 255, 0.2); }
        .prediction-box { background: linear-gradient(135deg, #00d4ff 0%, #00b4d8 100%); border-radius: 10px; padding: 15px; margin: 15px 0; text-align: center; }
        .prediction-title { font-size: 14px; color: #1a1a2e; opacity: 0.8; }
        .prediction-value { font-size: 22px; font-weight: bold; color: #1a1a2e; margin-top: 5px; }
        .confidence { display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 12px; margin-left: 10px; }
        .conf-high { background: #1e5631; color: #fff; }
        .conf-medium { background: #4a4a00; color: #fff; }
        .conf-low { background: #563a3a; color: #fff; }
        .match-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #0f3460; }
        .match-id { color: #e94560; font-weight: bold; }
        .teams { font-size: 20px; font-weight: bold; text-align: center; margin: 15px 0; }
        .vs { color: #888; margin: 0 10px; }
        .odds-section { margin-top: 15px; }
        .odds-title { color: #00d4ff; font-size: 14px; margin-bottom: 10px; font-weight: bold; }
        .odds-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
        .odds-item { background: #0f3460; padding: 10px; border-radius: 6px; text-align: center; }
        .odds-item .label { color: #888; font-size: 12px; }
        .odds-item .value { color: #fff; font-weight: bold; font-size: 16px; margin-top: 5px; }
        .odds-item.low { background: #1e5631; }
        .odds-item.medium { background: #4a4a00; }
        .odds-item.high { background: #563a3a; }
        .odds-item.top { background: #006666; border: 2px solid #00d4ff; }
        .score-odds { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
        .score-odds .odds-item { padding: 8px 4px; }
        .no-data { text-align: center; color: #888; padding: 60px 20px; }
        .no-data h2 { margin-bottom: 20px; }
        .instructions { background: #16213e; border-radius: 10px; padding: 20px; margin-bottom: 30px; text-align: center; }
        .instructions p { color: #888; margin: 5px 0; }
        .instructions .tip { color: #00d4ff; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚽ 竞彩比分预测系统</h1>
        
        <div class="instructions">
            <p>输入比赛ID，点击"抓取分析"获取数据</p>
            <p class="tip">例如: 2039135 (从URL: sporttery.cn/?mid=2039135 获取)</p>
        </div>
        
        <div class="controls">
            <input type="text" id="matchInput" placeholder="输入比赛ID">
            <button class="btn-fetch" onclick="fetchMatch()">抓取分析</button>
            <button class="btn-refresh" onclick="loadMatches()">刷新列表</button>
        </div>
        
        <div id="matchList" class="match-grid"></div>
    </div>

    <script>
        async function loadMatches() {
            const res = await fetch('/api/matches');
            const matches = await res.json();
            const container = document.getElementById('matchList');
            
            if (matches.length === 0) {
                container.innerHTML = '<div class="no-data"><h2>暂无数据</h2><p>输入比赛ID，点击"抓取分析"按钮获取数据</p></div>';
                return;
            }
            
            container.innerHTML = matches.map(m => {
                // 分析推荐
                const analysis = analyzeMatch(m);
                const confClass = analysis.confidence >= 3 ? 'conf-high' : analysis.confidence >= 2 ? 'conf-medium' : 'conf-low';
                
                return `
                <div class="match-card">
                    <div class="match-header">
                        <span class="match-id">#${m.match_id}</span>
                        <span style="color:#666;font-size:12px">${m.fetch_time || ''}</span>
                    </div>
                    
                    <div class="teams">
                        ${m.match_info.home_team || '未知'} 
                        <span class="vs">VS</span> 
                        ${m.match_info.away_team || '未知'}
                    </div>
                    
                    ${analysis.prediction !== '未知' ? `
                    <div class="prediction-box">
                        <div class="prediction-title">预测推荐</div>
                        <div class="prediction-value">
                            ${analysis.prediction}
                            <span class="confidence ${confClass}">${analysis.confidence === 3 ? '高' : analysis.confidence === 2 ? '中' : '低'}置信</span>
                        </div>
                    </div>
                    ` : ''}
                    
                    <!-- 胜平负 -->
                    ${Object.keys(m.had || {}).filter(k => k !== '更新时间').length > 0 ? `
                    <div class="odds-section">
                        <div class="odds-title">胜平负</div>
                        <div class="odds-grid">
                            ${Object.entries(m.had || {}).filter(([k]) => k !== '更新时间').map(([k, v]) => 
                                `<div class="odds-item ${getOddsClass(v)}"><div class="label">${k}</div><div class="value">${v}</div></div>`
                            ).join('')}
                        </div>
                    </div>
                    ` : ''}
                    
                    <!-- 总进球 -->
                    ${Object.keys(m.total_goals || {}).length > 0 ? `
                    <div class="odds-section">
                        <div class="odds-title">总进球</div>
                        <div class="odds-grid">
                            ${Object.entries(m.total_goals || {}).map(([k, v]) => 
                                `<div class="odds-item ${getOddsClass(v)}"><div class="label">${k}</div><div class="value">${v}</div></div>`
                            ).join('')}
                        </div>
                    </div>
                    ` : ''}
                    
                    <!-- 让球胜平负 -->
                    ${m.hhad && m.hhad.让球数 ? `
                    <div class="odds-section">
                        <div class="odds-title">让球(${m.hhad.让球数})胜平负</div>
                        <div class="odds-grid">
                            <div class="odds-item ${getOddsClass(m.hhad.让胜)}"><div class="label">让胜</div><div class="value">${m.hhad.让胜 || '-'}</div></div>
                            <div class="odds-item ${getOddsClass(m.hhad.让平)}"><div class="label">让平</div><div class="value">${m.hhad.让平 || '-'}</div></div>
                            <div class="odds-item ${getOddsClass(m.hhad.让负)}"><div class="label">让负</div><div class="value">${m.hhad.让负 || '-'}</div></div>
                        </div>
                    </div>
                    ` : ''}
                    
                    <!-- 比分(最低赔率) -->
                    ${Object.keys(m.score_odds || {}).length > 0 ? `
                    <div class="odds-section">
                        <div class="odds-title">比分赔率 (最低)</div>
                        <div class="score-odds">
                            ${getLowestScores(m.score_odds)}
                        </div>
                    </div>
                    ` : ''}
                </div>
                `}).join('');
        }
        
        function analyzeMatch(m) {
            const scoreOdds = m.score_odds || {};
            const had = m.had || {};
            const totalGoals = m.total_goals || {};
            
            // 过滤有效数据
            const validScores = Object.entries(scoreOdds)
                .filter(([k, v]) => v && v > 0 && k.includes(':'));
            
            if (validScores.length === 0) {
                return { prediction: '未知', confidence: 0, reason: [] };
            }
            
            // 按赔率排序
            const sorted = validScores.sort((a, b) => parseFloat(a[1]) - parseFloat(b[1]));
            const lowest = sorted[0];
            const lowOdds = parseFloat(lowest[1]);
            
            // 胜平负
            const validHad = Object.entries(had)
                .filter(([k, v]) => k !== '更新时间' && v && parseFloat(v) > 0);
            const sortedHad = validHad.sort((a, b) => parseFloat(a[1]) - parseFloat(b[1]));
            
            // 总进球
            const validGoals = Object.entries(totalGoals)
                .filter(([k, v]) => v && parseFloat(v) > 0);
            const sortedGoals = validGoals.sort((a, b) => parseFloat(a[1]) - parseFloat(b[1]));
            
            // 构建预测
            let prediction = '未知';
            let confidence = 0;
            
            if (lowOdds < 5) confidence = 3;
            else if (lowOdds < 8) confidence = 2;
            else confidence = 1;
            
            const parts = [];
            if (sortedHad.length > 0) {
                parts.push(sortedHad[0][0]);
            }
            if (sorted.length > 0) {
                parts.push(`比分: ${lowest[0]}`);
            }
            if (sortedGoals.length > 0) {
                parts.push(`总进球: ${sortedGoals[0][0]}`);
            }
            
            prediction = parts.join(' | ');
            
            return { prediction, confidence, reason: parts };
        }
        
        function getOddsClass(val) {
            if (!val || val === 0) return '';
            const v = parseFloat(val);
            if (v < 3) return 'odds-item low';
            if (v < 6) return 'odds-item medium';
            return 'odds-item high';
        }
        
        function getLowestScores(odds) {
            if (!odds || Object.keys(odds).length === 0) return '';
            
            const entries = Object.entries(odds)
                .filter(([k, v]) => v && v > 0 && k.match(/^\\d+:\\d+$/))
                .sort((a, b) => parseFloat(a[1]) - parseFloat(b[1]))
                .slice(0, 8);
            
            return entries.map(([k, v], i) => {
                const cls = i === 0 ? 'odds-item top' : getOddsClass(v);
                return `<div class="${cls}"><div class="label">${k}</div><div class="value">${v}</div></div>`;
            }).join('');
        }
        
        async function fetchMatch() {
            const matchId = document.getElementById('matchInput').value.trim();
            if (!matchId) {
                alert('请输入比赛ID');
                return;
            }
            
            const res = await fetch('/api/fetch/' + matchId);
            const data = await res.json();
            
            if (data.success) {
                alert('抓取成功！');
                loadMatches();
            } else {
                alert('抓取失败: ' + (data.error || '未知错误'));
            }
        }
        
        // 初始加载
        loadMatches();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/matches')
def get_matches():
    """获取所有比赛数据"""
    matches = []
    
    for filepath in glob.glob(os.path.join(DATA_DIR, '*.json')):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 跳过原始数据
                if 'raw_' not in os.path.basename(filepath):
                    matches.append(data)
        except:
            pass
    
    matches.sort(key=lambda x: x.get('fetch_time', ''), reverse=True)
    return jsonify(matches)

@app.route('/api/fetch/<match_id>')
def fetch_match(match_id):
    """抓取单场比赛"""
    try:
        api = SportteryAPI()
        result = api.fetch_and_save(match_id)
        
        if result:
            return jsonify({'success': True, 'data': result})
        else:
            return jsonify({'success': False, 'error': '获取数据失败'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print('='*60)
    print('竞彩比分预测系统')
    print('='*60)
    print('访问地址: http://192.168.0.101:8899')
    print('='*60)
    
    app.run(host='0.0.0.0', port=8899, debug=False)
