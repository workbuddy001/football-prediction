"""
竞彩比分进球预测系统 v3
数据放在 sporttery_data/ 文件夹中，网页自动读取显示
"""

import http.server
import json
import os
from datetime import datetime

PORT = 8891
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "sporttery_data")
os.makedirs(DATA_DIR, exist_ok=True)


def load_all_matches():
    """加载所有比赛数据"""
    matches = []
    for fname in sorted(os.listdir(DATA_DIR), reverse=True):
        if fname.endswith('.json'):
            mid = fname.replace('.json', '')
            try:
                with open(os.path.join(DATA_DIR, fname), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                matches.append({
                    'mid': mid,
                    'filename': fname,
                    'data': data
                })
            except:
                pass
    return matches


def analyze_data(data):
    """分析数据并生成结果"""
    result = {'recommendation': []}

    # 比分分析
    score_odds = data.get('score_odds', {})
    if score_odds:
        home = [(k, v) for k, v in score_odds.items() if int(k.split(':')[0]) > int(k.split(':')[1])]
        draw = [(k, v) for k, v in score_odds.items() if k.split(':')[0] == k.split(':')[1]]
        away = [(k, v) for k, v in score_odds.items() if int(k.split(':')[0]) < int(k.split(':')[1])]
        home.sort(key=lambda x: x[1])
        draw.sort(key=lambda x: x[1])
        away.sort(key=lambda x: x[1])

        result['score'] = {
            'home_best': home[0] if home else None,
            'draw_best': draw[0] if draw else None,
            'away_best': away[0] if away else None,
            'top5': sorted(score_odds.items(), key=lambda x: x[1])[:5]
        }

    # 总进球分析
    goals = data.get('total_goals', {})
    if goals:
        sorted_goals = sorted(goals.items(), key=lambda x: x[1])
        try:
            lowest = int(sorted_goals[0][0].replace('+', ''))
            if lowest <= 2: analysis = "倾向小球"
            elif lowest >= 4: analysis = "倾向大球"
            else: analysis = "中等进球"
        except:
            analysis = "无法判断"
        result['goals'] = {
            'most_likely': sorted_goals[:3],
            'analysis': analysis
        }

    # 胜平负
    wdl = data.get('win_draw_lose', {})
    if wdl:
        current = wdl.get('current', wdl) if isinstance(wdl, dict) else wdl
        if isinstance(current, dict) and 'home' in current:
            min_dir = min(current.items(), key=lambda x: x[1])
            names = {'home': '主胜', 'draw': '平局', 'away': '客胜'}
            result['wdl'] = {
                'current': current,
                'best': (names.get(min_dir[0], min_dir[0]), min_dir[1])
            }

    # 生成推荐
    if result.get('score', {}).get('home_best'):
        result['recommendation'].append({
            'type': '比分',
            'value': f"{result['score']['home_best'][0]} (赔率{result['score']['home_best'][1]})"
        })
    if result.get('goals', {}).get('most_likely'):
        result['recommendation'].append({
            'type': '总进球',
            'value': result['goals']['most_likely'][0][0] + '球'
        })
    if result.get('wdl', {}).get('best'):
        result['recommendation'].append({
            'type': '胜平负',
            'value': result['wdl']['best'][0]
        })

    return result


# ============= HTML模板 =============

HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>竞彩比分进球预测系统</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: system-ui; background: linear-gradient(135deg, #1a1a2e, #16213e); min-height: 100vh; color: #eee; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; }
        h1 { text-align: center; color: #00d4ff; margin-bottom: 20px; }
        .tip { text-align: center; color: #888; margin-bottom: 20px; font-size: 0.9rem; }
        .panel { background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.1); }
        .match-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; }
        .match-card { background: rgba(0,0,0,0.3); border-radius: 10px; padding: 15px; cursor: pointer; transition: all 0.2s; border: 1px solid transparent; }
        .match-card:hover { border-color: #00d4ff; transform: translateY(-3px); }
        .match-id { color: #00d4ff; font-weight: bold; font-size: 1.1rem; }
        .match-info { color: #888; font-size: 0.85rem; margin: 8px 0; }
        .match-result { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
        .badge { padding: 4px 10px; border-radius: 15px; font-size: 0.8rem; background: rgba(0,212,255,0.2); color: #00d4ff; }
        .empty { text-align: center; padding: 60px; color: #666; }
        .empty-icon { font-size: 3rem; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚽ 竞彩比分进球预测系统</h1>
        <p class="tip">💡 将JSON数据文件放入 <code>sporttery_data/</code> 文件夹，刷新页面即可查看</p>

        <div class="panel">
            <div class="match-grid" id="matchList">
                <div class="empty"><div class="empty-icon">📁</div>暂无数据文件<br>将比赛JSON放入 sporttery_data/ 文件夹</div>
            </div>
        </div>

        <!-- 详情弹窗 -->
        <div id="detailPanel" class="panel" style="display:none; position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); width:90%; max-width:600px; max-height:80vh; overflow-y:auto; z-index:1000;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                <span class="match-id" id="detailTitle">比赛详情</span>
                <button onclick="closeDetail()" style="padding:8px 16px; background:#ff6b6b; border:none; border-radius:6px; color:#fff; cursor:pointer;">关闭</button>
            </div>
            <div id="detailContent"></div>
        </div>
        <div id="overlay" onclick="closeDetail()" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.7); z-index:999;"></div>
    </div>

    <script>
        let matchesData = [];

        function loadMatches() {
            fetch('/api/matches').then(r => r.json()).then(data => {
                matchesData = data.matches || [];
                renderMatchList();
            });
        }

        function renderMatchList() {
            const list = document.getElementById('matchList');
            if (matchesData.length === 0) {
                list.innerHTML = '<div class="empty"><div class="empty-icon">📁</div>暂无数据文件<br>将比赛JSON放入 sporttery_data/ 文件夹</div>';
                return;
            }
            list.innerHTML = matchesData.map(m => `
                <div class="match-card" onclick="showDetail('${m.mid}')">
                    <div class="match-id">比赛 ${m.mid}</div>
                    <div class="match-info">${m.time || '未知时间'}</div>
                    <div class="match-result">
                        ${m.recs ? m.recs.slice(0,3).map(r => `<span class="badge">${r.type}: ${r.value}</span>`).join('') : ''}
                    </div>
                </div>
            `).join('');
        }

        function showDetail(mid) {
            const match = matchesData.find(m => m.mid === mid);
            if (!match) return;

            let html = '<div style="background:rgba(0,0,0,0.3); border-radius:8px; padding:15px; margin-bottom:15px;">';
            html += '<h3 style="color:#ffd93d; margin-bottom:10px;">🎯 预测推荐</h3>';
            if (match.recs) {
                match.recs.forEach(r => {
                    html += `<div style="display:flex; justify-content:space-between; padding:8px; background:rgba(0,212,255,0.1); border-radius:6px; margin:5px 0;">
                        <span style="color:#888;">${r.type}</span>
                        <span style="color:#51cf66; font-weight:bold;">${r.value}</span>
                    </div>`;
                });
            }
            html += '</div>';

            // 比分详情
            if (match.score) {
                html += '<div style="background:rgba(0,0,0,0.3); border-radius:8px; padding:15px; margin-bottom:15px;">';
                html += '<h3 style="color:#ffd93d; margin-bottom:10px;">🏆 比分赔率</h3>';
                html += '<table style="width:100%; border-collapse:collapse;">';
                html += '<tr style="background:rgba(0,212,255,0.2);"><th style="padding:10px; text-align:left;">类型</th><th style="padding:10px;">比分</th><th style="padding:10px;">赔率</th></tr>';
                if (match.score.home_best) html += `<tr style="border-bottom:1px solid rgba(255,255,255,0.1);"><td style="padding:10px;">🏠 主胜最低</td><td style="padding:10px; text-align:center; color:#51cf66; font-weight:bold;">${match.score.home_best[0]}</td><td style="padding:10px; text-align:center;">${match.score.home_best[1]}</td></tr>`;
                if (match.score.draw_best) html += `<tr style="border-bottom:1px solid rgba(255,255,255,0.1);"><td style="padding:10px;">⚖️ 平局最低</td><td style="padding:10px; text-align:center;">${match.score.draw_best[0]}</td><td style="padding:10px; text-align:center;">${match.score.draw_best[1]}</td></tr>`;
                if (match.score.away_best) html += `<tr><td style="padding:10px;">✈️ 客胜最低</td><td style="padding:10px; text-align:center;">${match.score.away_best[0]}</td><td style="padding:10px; text-align:center;">${match.score.away_best[1]}</td></tr>`;
                html += '</table></div>';

                // TOP5
                if (match.score.top5 && match.score.top5.length > 0) {
                    html += '<div style="background:rgba(0,0,0,0.3); border-radius:8px; padding:15px; margin-bottom:15px;">';
                    html += '<h3 style="color:#ffd93d; margin-bottom:10px;">📊 TOP5 最可能比分</h3>';
                    html += '<div style="display:grid; grid-template-columns:repeat(5,1fr); gap:10px;">';
                    match.score.top5.forEach((s, i) => {
                        html += `<div style="text-align:center; padding:12px; background:rgba(0,0,0,0.3); border-radius:8px; ${i===0?'border:2px solid #51cf66;':''}">
                            <div style="font-size:1.2rem; font-weight:bold;">${s[0]}</div>
                            <div style="color:#51cf66; font-size:0.9rem;">${s[1]}</div>
                        </div>`;
                    });
                    html += '</div></div>';
                }
            }

            // 总进球
            if (match.goals) {
                html += '<div style="background:rgba(0,0,0,0.3); border-radius:8px; padding:15px; margin-bottom:15px;">';
                html += '<h3 style="color:#ffd93d; margin-bottom:10px;">⚽ 总进球预测</h3>';
                html += '<div style="display:flex; gap:10px; flex-wrap:wrap;">';
                match.goals.most_likely.forEach((g, i) => {
                    html += `<div style="flex:1; min-width:60px; text-align:center; padding:12px; background:rgba(0,0,0,0.3); border-radius:8px; ${i===0?'border:2px solid #51cf66;':''}">
                        <div style="font-size:1.3rem; font-weight:bold;">${g[0]}</div>
                        <div style="color:#51cf66;">${g[1]}</div>
                    </div>`;
                });
                html += '</div>';
                if (match.goals.analysis) html += `<p style="margin-top:10px; color:#888;">📝 ${match.goals.analysis}</p>`;
                html += '</div>';
            }

            // 胜平负
            if (match.wdl && match.wdl.current) {
                html += '<div style="background:rgba(0,0,0,0.3); border-radius:8px; padding:15px;">';
                html += '<h3 style="color:#ffd93d; margin-bottom:10px;">📈 胜平负</h3>';
                html += '<div style="display:flex; gap:10px;">';
                const names = {home:'🏠 主胜', draw:'⚖️ 平局', away:'✈️ 客胜'};
                for (const [k, v] of Object.entries(match.wdl.current)) {
                    html += `<div style="flex:1; text-align:center; padding:12px; background:rgba(0,0,0,0.3); border-radius:8px;">
                        <div style="margin-bottom:5px;">${names[k]||k}</div>
                        <div style="font-size:1.2rem; color:#51cf66;">${v}</div>
                    </div>`;
                }
                html += '</div></div>';
            }

            document.getElementById('detailContent').innerHTML = html;
            document.getElementById('detailTitle').textContent = '比赛 ' + mid;
            document.getElementById('detailPanel').style.display = 'block';
            document.getElementById('overlay').style.display = 'block';
        }

        function closeDetail() {
            document.getElementById('detailPanel').style.display = 'none';
            document.getElementById('overlay').style.display = 'none';
        }

        loadMatches();
        setInterval(loadMatches, 5000); // 每5秒刷新
    </script>
</body>
</html>'''


# ============= Web服务 =============

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/' or path == '/index.html':
            self.send_html()
        elif path == '/api/matches':
            self.api_matches()
        else:
            self.send_error(404)

    def send_html(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(HTML.encode('utf-8'))

    def api_matches(self):
        """返回所有比赛列表"""
        matches = []
        for fname in sorted(os.listdir(DATA_DIR), reverse=True):
            if fname.endswith('.json'):
                mid = fname.replace('.json', '')
                try:
                    with open(os.path.join(DATA_DIR, fname), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    result = analyze_data(data)
                    recs = result.get('recommendation', [])
                    matches.append({
                        'mid': mid,
                        'time': data.get('time', data.get('fetched_at', '')),
                        'recs': recs,
                        **result
                    })
                except:
                    pass
        self.send_json({'matches': matches})

    def send_json(self, data):
        json_str = json.dumps(data, ensure_ascii=False)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json_str.encode('utf-8'))

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def main():
    # 创建示例文件
    example_file = os.path.join(DATA_DIR, "示例_2039135.json")
    if not os.path.exists(example_file):
        example = {
            "mid": "2039135",
            "time": "2026-04-17",
            "score_odds": {
                "1:0": 14.5, "2:0": 14.0, "2:1": 8.0, "3:0": 22.0, "3:1": 14.0, "3:2": 15.0, "4:0": 38.0,
                "0:0": 30.0, "1:1": 8.25, "2:2": 9.0, "3:3": 24.0,
                "0:1": 19.0, "0:2": 22.0, "1:2": 10.0, "0:3": 42.0, "1:3": 20.0, "2:3": 18.0
            },
            "total_goals": {"0": 30.0, "1": 9.75, "2": 5.25, "3": 3.80, "4": 4.20, "5": 5.25, "6": 8.0, "7+": 9.0},
            "win_draw_lose": {"current": {"home": 1.95, "draw": 3.73, "away": 2.81}}
        }
        with open(example_file, 'w', encoding='utf-8') as f:
            json.dump(example, f, ensure_ascii=False, indent=2)
        print(f"已创建示例文件: {example_file}")

    print(f"""
╔═══════════════════════════════════════════════╗
║     竞彩比分进球预测系统 v3                     ║
║     访问地址: http://localhost:{PORT}              ║
║     数据目录: {DATA_DIR}    ║
╚═══════════════════════════════════════════════╝
    """)
    server = http.server.HTTPServer(('0.0.0.0', PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == '__main__':
    main()
