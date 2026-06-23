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
    对当前比赛分类场景（旧版，粗粒度，确保高置信度场景有足够样本）
    
    Returns:
        场景字符串，如 "handicap_-1_let_neg_A_让负_67%_一致"
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
    
    # 场景3：历史期望分布（最高方向+命中率）
    directions = _map_scores_to_directions(historical_scores, handicap)
    max_dir = max(directions, key=directions.get)
    max_rate = directions[max_dir]
    # ✅ 修复：将场次转换为百分比
    total_games = len(historical_scores)
    max_rate_pct = (max_rate / total_games * 100) if total_games > 0 else 0
    situation += f"_{max_dir}_{max_rate_pct:.0f}%"
    
    # 场景4：是否有矛盾
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
        rate = score_data.get("rate", 1.0)  # ✅ 修复：默认值改为1.0（每个历史比分权重相等）
        
        try:
            home, away = map(int, score.split(":"))
        except:
            continue
        
        # 判断该比分属于哪个让球方向
        handicap_val = float(handicap)  # ✅ 修复：转换为浮点数
        adjusted_home = home + handicap_val
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
        # 1. 获取历史交锋比分（优先级高）
        history = data.get('preview', {}).get('history', {}).get('matchList', [])
        
        historical_scores = []
        if history and len(history) > 0:
            # 将历史交锋转换为标准格式
            for match in history:
                full_goal = match.get('fullCourtGoal', '') or match.get('fullCourtGoal', '')
                if not full_goal or ':' not in full_goal:
                    continue
                
                home_team = match.get('homeTeamShortName', '')
                away_team = match.get('awayTeamShortName', '')
                
                data_home = data.get('match_info', {}).get('home_team', '')
                data_away = data.get('match_info', {}).get('away_team', '')
                
                # 部分匹配
                home_match = (home_team in data_home or data_home in home_team)
                away_match = (away_team in data_away or data_away in away_team)
                home_reverse = (home_team in data_away or data_away in home_team)
                away_reverse = (away_team in data_home or data_home in away_team)
                
                if home_match and away_match:
                    score = full_goal
                elif home_reverse and away_reverse:
                    parts = full_goal.split(':')
                    score = f'{parts[1]}:{parts[0]}'
                else:
                    continue
                
                historical_scores.append({'score': score, 'rate': 1.0})
        
        # 2. 如果历史交锋不足3场，补充近期比赛数据
        recent_scores = []
        if not historical_scores or len(historical_scores) < 3:
            recent = data.get('preview', {}).get('recent', {})
            
            # 主队近期比赛
            home_recent = recent.get('home', {}).get('matchList', [])
            data_home = data.get('match_info', {}).get('home_team', '')
            
            for match in home_recent[:5]:  # 最近5场
                full_goal = match.get('fullCourtGoal', '')
                if not full_goal or ':' not in full_goal:
                    continue
                
                home_team = match.get('homeTeamShortName', '')
                if home_team in data_home or data_home in home_team:
                    # 主队主场比赛，比分格式正确
                    recent_scores.append({'score': full_goal, 'rate': 0.5})
            
            # 客队近期比赛
            away_recent = recent.get('away', {}).get('matchList', [])
            data_away = data.get('match_info', {}).get('away_team', '')
            
            for match in away_recent[:5]:  # 最近5场
                full_goal = match.get('fullCourtGoal', '')
                if not full_goal or ':' not in full_goal:
                    continue
                
                away_team = match.get('awayTeamShortName', '')
                if away_team in data_away or data_away in away_team:
                    # 客队客场比赛，比分格式正确（已经是"主队:客队"）
                    recent_scores.append({'score': full_goal, 'rate': 0.5})
        
        # 3. 合并历史交锋和近期比赛
        combined_scores = historical_scores.copy()
        
        if recent_scores:
            # 补充近期比赛，直到总数达到5场
            for score_data in recent_scores:
                if len(combined_scores) >= 5:
                    break
                combined_scores.append(score_data)
        
        if not combined_scores or len(combined_scores) < 3:
            # 合并后仍然不足3场，无法预测
            return None
        
        # 4. 分类场景（使用合并后的数据）
        situation = classify_situation(data, handicap, combined_scores)
        
        # 3. 检查是否属于高置信度场景
        high_conf_set = _load_high_conf_scenarios()
        is_high_conf = situation in high_conf_set
        
        # 4. 应用H9预测逻辑（无论是否高置信度，都计算预测结果）
        hhad_odds = data.get("hhad", {})
        hhad_change = data.get("hhad_change", {})
        
        directions = _map_scores_to_directions(combined_scores, handicap)
        if not directions or max(directions.values()) == 0:
            return None
        
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
        
        # 预测：H9核心逻辑
        # - 一致信号（历史期望=庄家保护）：庄家在防范 → 跟随历史期望
        # - 矛盾信号（历史期望≠庄家保护）：庄家在诱导 → 反向庄家 = 跟随历史期望
        if protected and max_dir != protected:
            # 矛盾 = 庄家诱导 = 反向庄家 = 跟随历史期望
            prediction = max_dir
            explanation = f"矛盾信号：历史期望{max_dir}({max_rate:.0f}%) ≠ 庄家保护{protected} → 庄家诱导 → 反向到{max_dir}"
        else:
            # 一致 = 庄家防范 = 跟随历史期望
            prediction = max_dir
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
        
        # 6. 设置置信度
        # 置信度 = 回测准确率（从高置信度列表读取），而不是历史期望占比
        # 历史期望占比（max_rate）通常很低（0%），没有参考价值
        # 回测准确率反映这个场景的历史命中率，更有意义
        if is_high_conf:
            confidence = _get_scenario_accuracy(situation)  # 回测准确率（0-100%）
        else:
            confidence = 0.0  # 低置信度，显示0%
        
        # 低置信度提示（不影响置信度显示）
        if not is_high_conf:
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
