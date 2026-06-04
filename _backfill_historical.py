#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
历史比赛批量回填——将所有 _scores.json 中的比赛标记为"已确认投注"（推断决策）并回填比分。
只执行一次，生成初始埋点日志。
"""

import json
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(__file__))

# Mock flask before importing ai_reasoning (which imports flask for Blueprint)
import types

class _MockBlueprint:
    """模拟 Flask Blueprint，支持 @bp.route(...) 装饰器"""
    def route(self, *args, **kwargs):
        return lambda f: f
    def add_url_rule(self, *args, **kwargs):
        pass

class _MockApp:
    """模拟 Flask app，支持 @app.route(...) 和 register_blueprint"""
    def route(self, *a, **kw):
        return lambda f: f
    def register_blueprint(self, *a, **kw):
        pass

_mock_flask = types.ModuleType('flask')
_mock_flask.Flask = lambda *a, **kw: _MockApp()
_mock_flask.Blueprint = lambda *a, **kw: _MockBlueprint()
_mock_flask.jsonify = lambda *a, **kw: {}
_mock_flask.request = types.SimpleNamespace(method='GET', is_json=False)
_mock_flask.render_template_string = lambda *a, **kw: ''
sys.modules['flask'] = _mock_flask

SCORES_FILE = os.path.join(os.path.dirname(__file__), '分析模板', '_scores.json')
LOG_FILE = os.path.join(os.path.dirname(__file__), '分析模板', '_rule_trigger_log.json')
DATA_DIR = os.path.join(os.path.dirname(__file__), 'sporttery_data')


def main():
    # 1. 加载比分
    if not os.path.exists(SCORES_FILE):
        print(f'[错误] 未找到 _scores.json: {SCORES_FILE}')
        return
    
    with open(SCORES_FILE, 'r', encoding='utf-8') as f:
        scores = json.load(f)
    
    print(f'比分总数: {len(scores)}')
    
    # 2. 加载已有埋点（如果有，跳过已存在的）
    existing = {}
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    print(f'已有埋点: {len(existing)}')
    
    # 3. 遍历所有 sporttery_data/*.json
    files = glob.glob(os.path.join(DATA_DIR, '*.json'))
    print(f'sporttery_data 文件数: {len(files)}')
    
    # 建立 match_id → file path 映射
    id_to_file = {}
    for fp in files:
        basename = os.path.basename(fp).replace('.json', '')
        if basename.isdigit():
            id_to_file[basename] = fp
    
    print(f'有效 match_id 文件: {len(id_to_file)}')
    
    # 4. 遍历比分，只处理今天之前的（有比分结果的）
    import time
    today = time.strftime('%Y-%m-%d')
    
    new_count = 0
    skip_no_data = 0
    skip_existing = 0
    
    for match_id_key, score_info in scores.items():
        if not isinstance(score_info, dict):
            continue
        
        hs = score_info.get('home_score')
        away_s = score_info.get('away_score')
        if hs is None or away_s is None:
            continue  # 没有比分结果，跳过
        
        mid = str(score_info.get('match_id', match_id_key))
        
        # 跳过已存在的
        if mid in existing:
            skip_existing += 1
            continue
        
        # 检查是否有对应数据文件
        if mid not in id_to_file:
            skip_no_data += 1
            continue
        
        # 读取原始数据
        try:
            with open(id_to_file[mid], 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            skip_no_data += 1
            continue
        
        mi = data.get('match_info', {}) or {}
        if not mi.get('match_num_str'):
            skip_no_data += 1
            continue
        
        # 模拟 compute_betting（需要导入并运行）
        try:
            from v36_analyzer import analyze_match
            from ai_reasoning import compute_betting
            analysis = analyze_match(data)
            result = compute_betting(data, analysis)
        except Exception as e:
            print(f'  [{mid}] 分析失败: {e}')
            continue
        
        # 构建埋点条目
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        entry = {
            'match_id': mid,
            'match_num': mi.get('match_num_str', ''),
            'league': mi.get('league', ''),
            'home_team': mi.get('home_team', ''),
            'away_team': mi.get('away_team', ''),
            'match_time': mi.get('time', ''),
            'confirmed_at': now,
            'first_confirmed_at': now,
            'action': result.get('action', 'unknown'),
            'rule': result.get('rule', ''),
            'reason': result.get('reason', ''),
            'goal_bet': result.get('goal_bet', {}),
            'score_bets': result.get('score_bets', []),
            'score_stake': result.get('score_stake', 0),
            'total_stake': result.get('total_stake', 0),
            'summary': result.get('summary', ''),
            'bet_type': result.get('bet_type', ''),
            'pp_boost': result.get('pp_boost', False),
            's7_dual': result.get('s7_dual', False),
            'actual_total': hs + away_s,
            'actual_score': score_info.get('score_str') or f"{hs}:{away_s}",
            'hit': None,
        }
        
        # 判断命中
        if entry['action'] == 'bet':
            goals = entry.get('goal_bet', {}).get('goals', [])
            entry['hit'] = entry['actual_total'] in goals
        # 比分投注命中判断
        if entry['action'] == 'bet' and entry.get('score_bets'):
            any_score_hit = False
            for sb in entry['score_bets']:
                if sb.get('score') == entry['actual_score']:
                    any_score_hit = True
                    break
            if any_score_hit:
                entry['hit'] = True
        
        existing[mid] = entry
        new_count += 1
        
        if new_count % 50 == 0:
            print(f'  已处理 {new_count}...')
    
    # 5. 保存
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    print(f'\n===== 完成 =====')
    print(f'新回填: {new_count}')
    print(f'已存在跳过: {skip_existing}')
    print(f'无数据跳过: {skip_no_data}')
    print(f'总埋点条目: {len(existing)}')
    print(f'输出文件: {LOG_FILE}')


if __name__ == '__main__':
    main()
