#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H9预测器 v2.0 - 基于数据集的实力差距相似度匹配

核心思路：
1. 加载h9_dataset.json（预计算的数据集）
2. 计算当前比赛的实力差距
3. 从数据集中找相似比赛（实力差距±tolerance）
4. 统计相似比赛的让球数分布
5. 对比实际让球数，推理让球方向
6. 计算置信度

新增功能：
- 可按联赛级别、比赛性质过滤
- 支持可配置的相似度容忍度
"""

import json
import os
import sys
from datetime import datetime

# 数据集文件
DATASET_FILE = 'h9_dataset.json'

# 全局缓存：数据集
_dataset = None
_dataset_loaded = False

def _load_dataset(force_reload=False):
    """
    加载数据集（带缓存）
    
    Args:
        force_reload: 是否强制重新加载
    
    Returns:
        dataset dict 或 None
    """
    global _dataset, _dataset_loaded
    
    if _dataset_loaded and not force_reload:
        return _dataset
    
    try:
        if not os.path.exists(DATASET_FILE):
            print(f'[H9 v2] ❌ 数据集文件不存在: {DATASET_FILE}')
            _dataset = None
            _dataset_loaded = True
            return None
        
        with open(DATASET_FILE, 'r', encoding='utf-8') as f:
            _dataset = json.load(f)
        
        total = _dataset['metadata']['total_matches']
        print(f'[H9 v2] ✅ 已加载数据集: {total} 场比赛 (v{_dataset["metadata"]["version"]})')
        _dataset_loaded = True
        return _dataset
    
    except Exception as e:
        print(f'[H9 v2] ❌ 加载数据集失败: {e}')
        _dataset = None
        _dataset_loaded = True
        return None

def calculate_strength_gap_from_data(data):
    """
    从比赛数据中计算实力差距
    
    Args:
        data: sporttery_data/*.json的内容
    
    Returns:
        float: 实力差距（主队avg_net - 客队avg_net）
    """
    try:
        preview = data.get('preview', {})
        recent = preview.get('recent', {})
        
        # 主队近期主场
        home_recent_list = recent.get('home', {}).get('matchList', [])
        home_stats = _calculate_recent_stats(home_recent_list, 'home')
        
        # 客队近期客场
        away_recent_list = recent.get('away', {}).get('matchList', [])
        away_stats = _calculate_recent_stats(away_recent_list, 'away')
        
        if home_stats['matches'] == 0 or away_stats['matches'] == 0:
            return None
        
        strength_gap = round(home_stats['avg_net'] - away_stats['avg_net'], 2)
        return strength_gap
    
    except Exception as e:
        print(f'[H9 v2] ❌ 计算实力差距失败: {e}')
        return None

def _calculate_recent_stats(match_list, team_type='home'):
    """
    计算近期比赛统计（简化版，与create_h9_dataset.py保持一致）
    """
    if not match_list or len(match_list) == 0:
        return {
            'matches': 0,
            'avg_net': 0.0
        }
    
    nets = []
    
    for match in match_list[:5]:  # 最近5场
        full_goal = match.get('fullCourtGoal', '')
        if not full_goal or ':' not in full_goal:
            continue
        
        try:
            home_score, away_score = map(int, full_goal.split(':'))
            
            if team_type == 'home':
                gf = home_score
                ga = away_score
            else:
                gf = away_score
                ga = home_score
            
            nets.append(gf - ga)
        
        except:
            continue
    
    if not nets:
        return {
            'matches': 0,
            'avg_net': 0.0
        }
    
    return {
        'matches': len(nets),
        'avg_net': round(sum(nets) / len(nets), 2)
    }

def find_similar_matches(dataset, current_gap, tolerance=0.5, 
                         league_level_filter=None, match_type_filter=None):
    """
    从数据集中找相似比赛
    
    Args:
        dataset: 数据集dict
        current_gap: 当前比赛的实力差距
        tolerance: 容忍度（±0.5球）
        league_level_filter: 联赛级别过滤（如["联赛", "杯赛"]）
        match_type_filter: 比赛性质过滤（如["联赛", "正赛"]）
    
    Returns:
        list: 相似比赛列表
    """
    similar = []
    
    for match in dataset['matches']:
        # 必须有实际结果
        if not match.get('result'):
            continue
        
        # 计算实力差距差异
        gap = match['features']['strength_gap']
        if abs(gap - current_gap) > tolerance:
            continue
        
        # 联赛级别过滤
        if league_level_filter:
            if match.get('league_level') not in league_level_filter:
                continue
        
        # 比赛性质过滤
        if match_type_filter:
            nature_type = match.get('match_nature', {}).get('type', '')
            if nature_type not in match_type_filter:
                continue
        
        similar.append(match)
    
    return similar

def analyze_handicap_distribution(similar_matches):
    """
    统计相似比赛的让球数分布
    
    Args:
        similar_matches: 相似比赛列表
    
    Returns:
        dict: {
            'avg_handicap': float,  # 平均让球数
            'distribution': dict,    # 让球数分布
            'total': int            # 总场数
        }
    """
    if not similar_matches:
        return None
    
    handicaps = [m['features']['handicap'] for m in similar_matches]
    
    avg_handicap = sum(handicaps) / len(handicaps)
    
    # 分布统计
    dist = {}
    for h in handicaps:
        key = f"handicap_{int(h)}" if h == int(h) else f"handicap_{h}"
        dist[key] = dist.get(key, 0) + 1
    
    return {
        'avg_handicap': round(avg_handicap, 2),
        'distribution': dist,
        'total': len(similar_matches)
    }

def compare_handicap_and_predict(analysis, actual_handicap, strength_gap):
    """
    对比实际让球数与预期，推理让球方向
    
    新逻辑（A1简化版）：
    - 总是跟随实力差距方向
    - 让球数差异只影响置信度，不影响预测方向
    
    Args:
        analysis: 让球数分布分析结果
        actual_handicap: 实际让球数
        strength_gap: 实力差距
    
    Returns:
        dict: {
            'avg_handicap': float,      # 预期让球数（相似比赛平均）
            'actual_handicap': float,    # 实际让球数
            'handicap_diff': float,     # 差异（实际-预期）
            'consistency': str,          # 一致性评价
            'prediction': str,           # 预测方向
            'confidence': float,         # 置信度
            'explanation': str          # 解释
        }
    """
    expected = analysis['avg_handicap']
    diff = actual_handicap - expected
    
    # 判断一致性（只用于置信度，不用于预测方向）
    if abs(diff) <= 0.5:
        consistency = "一致"
    elif abs(diff) <= 1.0:
        consistency = "轻微偏离"
    else:
        consistency = "严重偏离"
    
    # 新逻辑：总是跟随实力差距方向
    if strength_gap > 0:
        prediction = "让胜"  # 主队实力强 → 推荐让胜
        explanation = f"实力差距{strength_gap:+.2f}球（主队强）→ 推荐让胜"
    elif strength_gap < 0:
        prediction = "让负"  # 客队实力强 → 推荐让负
        explanation = f"实力差距{strength_gap:+.2f}球（客队强）→ 推荐让负"
    else:
        # 实力差距=0 → 无法判断
        prediction = None
        explanation = "实力差距为0，无法判断方向"
        return {
            'avg_handicap': expected,
            'actual_handicap': actual_handicap,
            'handicap_diff': round(diff, 2),
            'consistency': consistency,
            'prediction': None,
            'confidence': 0.0,
            'explanation': explanation
        }
    
    # 置信度：基于一致性（暂时用固定值，后续改为回测准确率）
    if consistency == "一致":
        confidence = 60.0  # 降低，因为算法简化了
    elif consistency == "轻微偏离":
        confidence = 50.0
    else:
        confidence = 40.0
    
    explanation += f"\n（让球{actual_handicap} vs 预期{expected:+.2f}，{consistency}）"
    
    return {
        'avg_handicap': expected,
        'actual_handicap': actual_handicap,
        'handicap_diff': round(diff, 2),
        'consistency': consistency,
        'prediction': prediction,
        'confidence': confidence,
        'explanation': explanation
    }

def predict_h9_v2(data, handicap, tolerance=0.5, 
                   league_level_filter=None, match_type_filter=None):
    """
    使用数据集进行H9预测（新算法v2.0）
    
    Args:
        data: 比赛数据（sporttery_data/*.json的内容）
        handicap: 让球数（如 -1, +1）
        tolerance: 相似度容忍度（±0.5球）
        league_level_filter: 联赛级别过滤（如["联赛", "杯赛"]）
        match_type_filter: 比赛性质过滤（如["联赛", "正赛"]）
    
    Returns:
        {
            'prediction': str,       # 预测方向（让胜/让平/让负）
            'confidence': float,     # 置信度（0-100%）
            'similar_matches': int,  # 相似比赛场数
            'avg_handicap': float,  # 相似比赛平均让球数
            'handicap_diff': float, # 实际让球数 - 预期让球数
            'explanation': str      # 解释
        }
        或 None（如果无法预测）
    """
    try:
        # 1. 加载数据集
        dataset = _load_dataset()
        if not dataset:
            return None
        
        # 2. 计算当前比赛的实力差距
        strength_gap = calculate_strength_gap_from_data(data)
        if strength_gap is None:
            print(f'[H9 v2] ⚠️ 无法计算实力差距（近期数据不足）')
            return None
        
        # 3. 从数据集中找相似比赛
        similar = find_similar_matches(
            dataset, strength_gap, tolerance,
            league_level_filter, match_type_filter
        )
        
        if len(similar) < 5:
            print(f'[H9 v2] ⚠️ 相似比赛不足（{len(similar)}场，需要≥5场）')
            return None
        
        # 4. 统计相似比赛的让球数分布
        analysis = analyze_handicap_distribution(similar)
        
        # 5. 对比实际让球数，推理让球方向
        result = compare_handicap_and_predict(analysis, handicap, strength_gap)
        
        # 6. 添加相似比赛信息
        result['similar_matches'] = len(similar)
        result['explanation'] += f'\n（基于{len(similar)}场相似比赛：实力差距{strength_gap:+.2f}±{tolerance}球）'
        
        return result
    
    except Exception as e:
        print(f'[H9 v2] ❌ 预测失败: {e}')
        import traceback
        traceback.print_exc()
        return None

def check_h9_v2(data, tolerance=0.5, 
                 league_level_filter=None, match_type_filter=None):
    """
    检查当前比赛是否触发H9规则（新算法v2.0）
    
    Args:
        data: 比赛数据（sporttery_data/*.json的内容）
        tolerance: 相似度容忍度
        league_level_filter: 联赛级别过滤
        match_type_filter: 比赛性质过滤
    
    Returns:
        {
            'triggered': bool,        # 是否触发H9规则
            'direction': str,         # 推荐让球方向
            'odds': float,            # 该方向赔率
            'stake': int,            # 推荐投注额
            'confidence': float,      # 置信度
            'explanation': str       # 解释
        }
        或 None（如果未触发）
    """
    try:
        # 1. 获取让球数
        hhad = data.get('hhad', {})
        if not hhad or '让球' not in hhad:
            return None
        
        handicap = float(hhad['让球'])
        
        # 2. 调用predict_h9_v2()
        result = predict_h9_v2(data, handicap, tolerance, 
                              league_level_filter, match_type_filter)
        
        if not result:
            return None
        
        # 3. 检查置信度（只推荐高置信度场景）
        if result['confidence'] < 60.0:
            print(f'[H9 v2] ⚠️ 置信度过低（{result["confidence"]:.1f}%），不推荐')
            return None
        
        # 4. 构建返回结果
        prediction = result['prediction']
        odds = float(hhad.get(prediction, 0))
        
        # 推荐投注额（基于置信度）
        confidence = result['confidence']
        if confidence >= 80.0:
            stake = 40  # tier_1_heavy
        elif confidence >= 70.0:
            stake = 20  # tier_2_medium
        else:
            stake = 10  # tier_3_light
        
        return {
            'action': 'bet',
            'rule': 'H9_v2',
            'type': 'handicap',
            'handicap_bet': {
                'direction': prediction,
                'odds': odds,
                'stake': stake
            },
            'confidence': confidence,
            'explanation': result['explanation']
        }
    
    except Exception as e:
        print(f'[H9 v2] ❌ check_h9_v2()失败: {e}')
        import traceback
        traceback.print_exc()
        return None

# 测试代码
if __name__ == '__main__':
    print("=== H9预测器 v2.0 测试 ===\n")
    
    # 加载数据集
    dataset = _load_dataset()
    
    if not dataset:
        print("❌ 无法加载数据集，测试终止")
        sys.exit(1)
    
    # 测试：厄瓜多尔 vs 库拉索（实力差距4.8球）
    test_file = "sporttery_data/2040245.json"
    if os.path.exists(test_file):
        with open(test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"测试比赛：厄瓜多尔 vs 库拉索\n")
        
        # 计算实力差距
        gap = calculate_strength_gap_from_data(data)
        print(f"实力差距：{gap:+.2f}球\n")
        
        # 预测
        result = predict_h9_v2(data, -2.0, tolerance=0.5)
        if result:
            print(f"预测方向：{result['prediction']}")
            print(f"置信度：{result['confidence']:.1f}%")
            print(f"相似比赛：{result['similar_matches']}场")
            print(f"预期让球：{result['avg_handicap']:+.2f}")
            print(f"实际让球：{result['actual_handicap']}")
            print(f"差异：{result['handicap_diff']:+.2f}球")
            print(f"解释：{result['explanation']}")
        else:
            print("无法预测")
    else:
        print(f"测试文件不存在：{test_file}")
