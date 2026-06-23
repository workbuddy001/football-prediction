#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H9 多因子决策树规则库（v1.0）

使用说明：
1. 每条规则包含：name, condition, prediction, confidence, explanation_template
2. condition是函数，输入features，返回True/False
3. explanation_template是字符串模板，匹配后用features格式化
4. 规则按优先级排序（前面的优先匹配）
"""

# ============================================================
# 辅助函数：从数据集提取特征
# ============================================================

def extract_features_from_match(match):
    """
    从数据集的一场比赛记录中提取特征
    
    Args:
        match: dict, 数据集中的一场比赛记录
    
    Returns:
        dict: 特征字典
    """
    features = match.get('features', {})
    
    # 构造规则需要的所有字段
    return {
        'strength_gap': features.get('strength_gap', 0),
        'handicap': features.get('handicap', 0),
        'home_recent': features.get('home_recent', {}),
        'away_recent': features.get('away_recent', {}),
        'odds': features.get('odds', {}),
        'odds_change': features.get('odds_change', {}),
        'league_level': match.get('league_level', '其他'),
        'match_nature': match.get('match_nature', {})
    }


# ============================================================
# 规则库 v1.0
# ============================================================

RULES = [
    # --------------------------------------------------------
    # 规则类型1：实力差距极端（强信号）
    # --------------------------------------------------------
    {
        'name': '实力差距极端_主强',
        'priority': 10,  # 高优先级
        'condition': lambda f: f.get('strength_gap', 0) > 3.0,
        'prediction': '让胜',
        'confidence': 65.0,
        'explanation_template': '实力差距>{strength_gap:+.2f}球（主队远强于客队）→ 推荐让胜'
    },
    {
        'name': '实力差距极端_客强',
        'priority': 10,
        'condition': lambda f: f.get('strength_gap', 0) < -3.0,
        'prediction': '让负',
        'confidence': 65.0,
        'explanation_template': '实力差距>{strength_gap:+.2f}球（客队远强于主队）→ 推荐让负'
    },

    # --------------------------------------------------------
    # 规则类型2：实力接近 + 让球数极端（可能诱导）
    # --------------------------------------------------------
    {
        'name': '实力接近_让球极端_诱导让胜',
        'priority': 20,
        'condition': lambda f: abs(f.get('strength_gap', 0)) < 1.0 and f.get('handicap', 0) <= -2.0,
        'prediction': '让负',  # 反向
        'confidence': 55.0,
        'explanation_template': '实力接近({strength_gap:+.2f})但让球{f.get("handicap")}极端 → 可能诱导让胜 → 反向到让负'
    },
    {
        'name': '实力接近_让球极端_诱导让负',
        'priority': 20,
        'condition': lambda f: abs(f.get('strength_gap', 0)) < 1.0 and f.get('handicap', 0) >= 2.0,
        'prediction': '让胜',  # 反向
        'confidence': 55.0,
        'explanation_template': '实力接近({strength_gap:+.2f})但让球+{f.get("handicap")}极端 → 可能诱导让负 → 反向到让胜'
    },

    # --------------------------------------------------------
    # 规则类型3：主队状态差 + 让胜低赔（诱导）
    # --------------------------------------------------------
    {
        'name': '主队状态差_让胜低赔_诱导',
        'priority': 30,
        'condition': lambda f: f.get('home_recent', {}).get('win_rate', 0) < 0.3 and f.get('odds', {}).get('let_win', 10) < 1.60,
        'prediction': '让负',
        'confidence': 60.0,
        'explanation_template': '主队近期胜率{f.get("home_recent", {}).get("win_rate", 0):.0%}极低 + 让胜赔率{f.get("odds", {}).get("let_win", 10):.2f}超低 → 诱导让胜 → 推荐让负'
    },

    # --------------------------------------------------------
    # 规则类型4：客队状态差 + 让负低赔（诱导）
    # --------------------------------------------------------
    {
        'name': '客队状态差_让负低赔_诱导',
        'priority': 30,
        'condition': lambda f: f.get('away_recent', {}).get('win_rate', 0) < 0.3 and f.get('odds', {}).get('let_lose', 10) < 1.60,
        'prediction': '让胜',
        'confidence': 60.0,
        'explanation_template': '客队近期胜率{f.get("away_recent", {}).get("win_rate", 0):.0%}极低 + 让负赔率{f.get("odds", {}).get("let_lose", 10):.2f}超低 → 诱导让负 → 推荐让胜'
    },

    # --------------------------------------------------------
    # 规则类型5：让平超低赔（平局信号）
    # --------------------------------------------------------
    {
        'name': '让平超低赔_平局',
        'priority': 40,
        'condition': lambda f: f.get('odds', {}).get('let_draw', 10) < 3.0,
        'prediction': '让平',
        'confidence': 50.0,
        'explanation_template': '让平赔率{f.get("odds", {}).get("let_draw", 10):.2f}超低 → 庄家防范平局 → 推荐让平'
    },

    # --------------------------------------------------------
    # 规则类型6：友谊赛（降低置信度）
    # --------------------------------------------------------
    {
        'name': '友谊赛_降低置信度',
        'priority': 50,
        'condition': lambda f: f.get('league_level') == '友谊赛',
        'prediction': None,  # 不预测，只标记
        'confidence': 0.0,
        'explanation_template': '友谊赛结果不可预测 → 降低所有预测的置信度'
    },
]


# ============================================================
# 规则匹配函数
# ============================================================

def match_rules(features):
    """
    匹配规则，返回第一个匹配的规则
    
    Args:
        features: dict, 比赛特征
    
    Returns:
        dict: {
            'rule_name': str,
            'prediction': str,
            'confidence': float,
            'explanation': str
        } or None
    """
    # 按优先级排序
    sorted_rules = sorted(RULES, key=lambda r: r['priority'])
    
    for rule in sorted_rules:
        try:
            if rule['condition'](features):
                # 格式化explanation
                try:
                    explanation = rule['explanation_template'].format(**features)
                except Exception as e:
                    explanation = rule['explanation_template']
                
                return {
                    'rule_name': rule['name'],
                    'prediction': rule['prediction'],
                    'confidence': rule['confidence'],
                    'explanation': explanation
                }
        except Exception as e:
            # 如果规则求值失败（如缺少字段），跳过
            continue
    
    return None  # 无匹配规则


# ============================================================
# 回测函数
# ============================================================

def backtest_rules(dataset, tolerance=0.5):
    """
    回测所有规则，计算准确率
    
    Args:
        dataset: list, 数据集（h9_dataset.json中的matches）
        tolerance: float, 相似比赛容忍度（未使用，保留参数）
    
    Returns:
        dict: 回测结果
    """
    results = {}
    
    for rule in RULES:
        rule_name = rule['name']
        total = 0
        correct = 0
        samples = []
        
        for match in dataset:
            if not match.get('result'):
                continue  # 跳过无实际结果的比赛
            
            features = extract_features_from_match(match)
            actual_result = match['result']['handicap_result']
            
            try:
                if rule['condition'](features):
                    total += 1
                    
                    # 规则只给出预测方向，需要判断是否正确
                    if rule['prediction']:
                        if rule['prediction'] == actual_result:
                            correct += 1
                            samples.append({
                                'match_id': match['match_id'],
                                'correct': True
                            })
                        else:
                            samples.append({
                                'match_id': match['match_id'],
                                'correct': False,
                                'predicted': rule['prediction'],
                                'actual': actual_result
                            })
            except Exception as e:
                continue
        
        accuracy = correct / total if total > 0 else 0
        
        results[rule_name] = {
            'total': total,
            'correct': correct,
            'accuracy': accuracy,
            'samples': samples
        }
    
    return results


# ============================================================
# 主函数：预测单场比赛
# ============================================================

def predict_h9_multifactor(match, tolerance=0.5):
    """
    使用多因子决策树预测让球方向
    
    Args:
        match: dict, 比赛数据（从sporttery_data读取）
        tolerance: float, 相似比赛容忍度（未使用）
    
    Returns:
        dict: {
            'prediction': str,
            'confidence': float,
            'rule_name': str,
            'explanation': str
        } or None
    """
    # TODO: 从match中提取特征（需要解析sporttery_data结构）
    # 暂时返回None
    return None


if __name__ == '__main__':
    # 测试规则匹配
    test_features = {
        'strength_gap': 4.0,
        'handicap': -2.0,
        'home_recent': {'win_rate': 0.6},
        'away_recent': {'win_rate': 0.1},
        'odds': {'let_win': 1.85, 'let_draw': 4.00, 'let_lose': 2.95},
        'odds_change': {'let_win': -2.0, 'let_draw': 0.0, 'let_lose': 3.0},
        'league_level': '正赛'
    }
    
    result = match_rules(test_features)
    if result:
        print(f"匹配规则: {result['rule_name']}")
        print(f"预测方向: {result['prediction']}")
        print(f"置信度: {result['confidence']:.1f}%")
        print(f"解释: {result['explanation']}")
    else:
        print("无匹配规则")
