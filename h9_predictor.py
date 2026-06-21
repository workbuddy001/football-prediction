#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
H9规则：最高历史比分矛盾法预测器
- 加载高置信度场景列表
- 对当前比赛分类场景
- 检查是否属于高置信度场景
- 如果是，应用H9预测并推荐
"""

import json
import os
import sys

# 添加sporttery_web.py的路径，以便调用其内部函数
sys.path.insert(0, os.path.dirname(__file__))

# 高置信度场景文件
HIGH_CONF_FILE = 'h9_high_confidence_scenarios.json'

# 全局缓存：高置信度场景集合
_high_conf_set = None

def _load_high_conf_scenarios():
    """加载高置信度场景列表，返回set"""
    global _high_conf_set
    if _high_conf_set is not None:
        return _high_conf_set
    
    try:
        with open(HIGH_CONF_FILE, 'r', encoding='utf-8') as f:
            scenarios = json.load(f)
        
        # 构建场景字符串集合
        _high_conf_set = set()
        for s in scenarios:
            situation = s['situation']
            _high_conf_set.add(situation)
        
        print(f'[H9] ✅ 已加载高置信度场景：{len(_high_conf_set)} 个')
        return _high_conf_set
    
    except Exception as e:
        print(f'[H9] ❌ 加载高置信度场景失败: {e}')
        return set()

def classify_situation(data, handicap, historical_scores):
    """
    对当前比赛分类场景（增强版，添加让胜/让平赔率区间特征）
    
    Returns:
        场景字符串，如 "handicap_-1_let_neg_A_let_win_B_let_draw_C_让负_67%_一致"
    """
    hhad_odds = data.get("hhad", {})
    
    # 场景1：让球数
    situation = f"handicap_{int(handicap)}"
    
    # 场景2：让负赔率区间
    let_negative_odds = float(hhad_odds.get("让负", 999))
    if let_negative_odds < 1.55:
        situation += "_let_neg_A"
    elif let_negative_odds < 1.65:
        situation += "_let_neg_B"
    elif let_negative_odds < 1.80:
        situation += "_let_neg_C"
    else:
        situation += "_let_neg_D"
    
    # 场景3：让胜赔率区间（新增）
    let_win_odds = float(hhad_odds.get("让胜", 999))
    if let_win_odds < 2.0:
        situation += "_let_win_A"
    elif let_win_odds < 3.0:
        situation += "_let_win_B"
    else:
        situation += "_let_win_C"
    
    # 场景4：让平赔率区间（新增）
    let_draw_odds = float(hhad_odds.get("让平", 999))
    if let_draw_odds < 3.3:
        situation += "_let_draw_A"
    elif let_draw_odds < 3.65:
        situation += "_let_draw_B"
    elif let_draw_odds < 3.95:
        situation += "_let_draw_C"
    else:
        situation += "_let_draw_D"
    
    # 场景5：历史期望分布（最高方向+命中率）
    directions = _map_scores_to_directions(historical_scores, handicap)
    max_dir = max(directions, key=directions.get)
    max_rate = directions[max_dir]
    situation += f"_{max_dir}_{max_rate:.0f}%"
    
    # 场景6：是否有矛盾
    hhad_change = data.get("hhad_change", {})
    protected = None
    for d in ["让胜", "让平", "让负"]:
        change = hhad_change.get(d, {}).get("change_pct", 0)
        odds = float(hhad_odds.get(d, 999))
        if (odds < 2.00 and change < -1.0) or (odds > 3.00 and change < -5.0):
            protected = d
            break
    
    if protected and max_dir != protected:
        situation += "_矛盾"
    else:
        situation += "_一致"
    
    return situation

def _map_scores_to_directions(historical_scores, handicap):
    """映射历史比分到让球方向，合并同方向命中率"""
    directions = {"让胜": 0.0, "让平": 0.0, "让负": 0.0}
    
    for score_data in historical_scores:
        score = score_data.get("score", "")
        rate = score_data.get("rate", 0.0)
        
        try:
            home, away = map(int, score.split(":"))
        except:
            continue
        
        # 判断该比分属于哪个让球方向
        adjusted_home = home + handicap
        diff = adjusted_home - away
        
        if diff > 0:
            direction = "让胜"
        elif diff == 0:
            direction = "让平"
        else:
            direction = "让负"
        
        directions[direction] += rate
    
    return directions

def predict_h9(data, handicap):
    """
    应用H9规则预测让球方向
    
    Args:
        data: 比赛数据（sporttery_data/*.json的内容）
        handicap: 让球数（如 -1, +1）
    
    Returns:
        {
            'is_high_conf': bool,  # 是否属于高置信度场景
            'situation': str,        # 场景字符串
            'prediction': str,       # 预测方向（让胜/让平/让负）
            'confidence': float,     # 置信度（高置信度场景的准确率）
            'explanation': str      # 解释
        }
        or None（如果无法预测）
    """
    try:
        # 1. 获取历史高命中率比分
        # 注意：不导入sporttery_web（需要Flask环境），直接实现逻辑
        score_odds = data.get('score_odds', {})
        if not score_odds:
            return None
        
        # 直接实现get_score_recommendations_for_match的逻辑
        recommendations = []
        for score, odds in score_odds.items():
            try:
                # 修复：将odds转换为float（可能是字符串格式）
                odds_float = float(odds)
                if odds_float > 0:
                    recommendations.append({
                        'score': score,
                        'odds': odds_float,
                        'rate': 0.0,  # 暂时不计算命中率
                        'bucket': 'unknown'
                    })
            except:
                continue
        
        if not recommendations or len(recommendations) < 1:
            return None
        
        # 2. 分类场景
        situation = classify_situation(data, handicap, recommendations)
        
        # 3. 检查是否属于高置信度场景
        high_conf_set = _load_high_conf_scenarios()
        is_high_conf = situation in high_conf_set
        
        # 4. 应用H9预测逻辑（无论是否高置信度，都计算预测结果）
        hhad_odds = data.get("hhad", {})
        hhad_change = data.get("hhad_change", {})
        
        directions = _map_scores_to_directions(recommendations, handicap)
        max_dir = max(directions, key=directions.get)
        max_rate = directions[max_dir]
        
        # 分析庄家意图（简化版）
        protected = None
        for d in ["让胜", "让平", "让负"]:
            change = hhad_change.get(d, {}).get("change_pct", 0)
            odds = float(hhad_odds.get(d, 999))
            if (odds < 2.00 and change < -1.0) or (odds > 3.00 and change < -5.0):
                protected = d
                break
        
        # 预测：如果没有矛盾，跟随历史期望最高方向；如果有矛盾，跟随庄家
        if protected and max_dir != protected:
            prediction = protected  # 矛盾=真相，跟随庄家
            explanation = f"矛盾信号：历史期望{max_dir}({max_rate:.0f}%) ≠ 庄家保护{protected} → 跟随庄家"
        else:
            prediction = max_dir  # 一致信号，跟随历史期望
            explanation = f"一致信号：历史期望{max_dir}({max_rate:.0f}%) = 庄家保护方向 → 跟随历史"
        
        # 5. 低置信度 + 预测为"让平" → 反向推荐，根据HAD赔率判断方向
        if not is_high_conf and prediction == "让平":
            had = data.get("had", {})
            if had:
                # 兼容两种字段名："主胜"/"平局"/"客胜" 或 "胜"/"平"/"负"
                home_odds = float(had.get("主胜") or had.get("胜", 999))
                draw_odds = float(had.get("平局") or had.get("平", 999))
                away_odds = float(had.get("客胜") or had.get("负", 999))
                
                if home_odds < 999 and draw_odds < 999 and away_odds < 999:
                    # 找出最低赔率（市场期望方向）
                    min_odds = min(home_odds, draw_odds, away_odds)
                    
                    if min_odds == home_odds:
                        # 市场期望主队获胜 → 反向到"让胜"
                        reversed_prediction = "让胜"
                        reason = f"HAD主胜{home_odds:.2f}最低"
                    elif min_odds == away_odds:
                        # 市场期望客队获胜 → 反向到"让负"
                        reversed_prediction = "让负"
                        reason = f"HAD客胜{away_odds:.2f}最低"
                    else:
                        # 市场期望平局 → 反向到"让负"（平局=主队不赢盘）
                        reversed_prediction = "让负"
                        reason = f"HAD平局{draw_odds:.2f}最低"
                    
                    prediction = reversed_prediction
                    explanation = f"⚠️低置信度+让平预测命中率低 → 反向到{prediction}（{reason}）"
                else:
                    # HAD赔率不完整，默认反向到"让负"
                    prediction = "让负"
                    explanation = f"⚠️低置信度+让平预测命中率低 → 反向到{prediction}（HAD赔率不完整）"
            else:
                # 无HAD赔率，默认反向到"让负"
                prediction = "让负"
                explanation = f"⚠️低置信度+让平预测命中率低 → 反向到{prediction}（无HAD赔率）"
        
        # 6. 根据是否高置信度，设置置信度
        if is_high_conf:
            confidence = _get_scenario_accuracy(situation)
        else:
            confidence = 0.0
            explanation += f"（场景{situation}不在高置信度列表，置信度未知）"
        
        return {
            'is_high_conf': is_high_conf,
            'situation': situation,
            'prediction': prediction,
            'confidence': confidence,
            'explanation': explanation,
            'is_reverse': not is_high_conf and '反向' in explanation  # 是否反向推荐
        }
    
    except Exception as e:
        print(f'[H9] ❌ 预测失败: {e}')
        import traceback
        traceback.print_exc()
        return None

def _get_scenario_accuracy(situation):
    """获取某场景的准确率（从JSON文件中查找，返回百分比0-100）"""
    try:
        with open(HIGH_CONF_FILE, 'r', encoding='utf-8') as f:
            scenarios = json.load(f)
        
        for s in scenarios:
            if s['situation'] == situation:
                # accuracy存储为小数(0-1)，需要转换为百分比(0-100)
                return s['accuracy'] * 100.0
        
        return 0.0
    except:
        return 0.0

def check_h9(data):
    """
    检查当前比赛是否触发H9规则（简化接口）
    
    Args:
        data: 比赛数据（sporttery_data/*.json的内容）
    
    Returns:
        {
            'triggered': bool,        # 是否触发H9规则
            'direction': str,         # 推荐让球方向（让胜/让平/让负）
            'odds': float,            # 该方向赔率
            'stake': int,            # 推荐投注额
            'situation': str,         # 场景字符串
            'confidence': float,      # 置信度（准确率）
            'explanation': str       # 解释
        }
        或 None（如果未触发H9规则）
    """
    try:
        # 1. 获取让球数
        hhad = data.get('hhad', {})
        if not hhad or '让球' not in hhad:
            return None
        
        handicap = float(hhad['让球'])
        
        # 2. 调用predict_h9()
        result = predict_h9(data, handicap)
        
        if not result or not result.get('is_high_conf'):
            return None
        
        # 3. 构建返回结果
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
            'rule': 'H9',
            'type': 'handicap',
            'handicap_bet': {
                'direction': prediction,
                'odds': odds,
                'stake': stake
            },
            'situation': result['situation'],
            'confidence': confidence,
            'explanation': result['explanation']
        }
    
    except Exception as e:
        print(f'[H9] ❌ check_h9()失败: {e}')
        import traceback
        traceback.print_exc()
        return None

# 测试代码
if __name__ == '__main__':
    print("测试H9预测器...")
    
    # 加载一个示例比赛
    test_file = "sporttery_data/2038933.json"
    if os.path.exists(test_file):
        with open(test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 获取让球数
        handicap = float(data.get('hhad', {}).get('让球', 0))
        
        # 预测
        result = predict_h9(data, handicap)
        if result:
            print(f"场景：{result['situation']}")
            print(f"高置信度：{result['is_high_conf']}")
            print(f"预测：{result['prediction']}")
            print(f"置信度：{result['confidence']:.1f}%")
            print(f"解释：{result['explanation']}")
        else:
            print("无法预测")
    else:
        print(f"测试文件不存在：{test_file}")
