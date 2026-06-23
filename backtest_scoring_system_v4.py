#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测脚本 - 多因素打分系统 v4.0 (简化版)
直接测试打分系统的逻辑，使用模拟的分析数据
"""

import json
import os
import sys
import random

def get_handicap_direction(handicap, home_score, away_score):
    """
    根据实际比分和让球，判断让球方向
    返回: '让胜', '让平', '让负'
    """
    if handicap is None or home_score is None or away_score is None:
        return None

    # 计算让球后比分
    adjusted_home = home_score + abs(handicap) if handicap < 0 else home_score
    adjusted_away = away_score + abs(handicap) if handicap > 0 else away_score

    if adjusted_home - adjusted_away > 0:
        return '让胜'
    elif adjusted_home - adjusted_away == 0:
        return '让平'
    else:
        return '让负'

def generate_simulated_analysis(actual_direction):
    """
    生成模拟的分析结果
    根据实际方向生成一些有偏向的模拟数据，测试打分系统是否能纠正
    """
    # 随机生成H9分析结果（可能正确也可能错误）
    directions = ['让胜', '让平', '让负']

    # 70%概率H9预测正确，30%概率错误
    if random.random() < 0.7:
        h9_prediction = actual_direction
        h9_confidence = random.uniform(60, 90)
    else:
        h9_prediction = random.choice([d for d in directions if d != actual_direction])
        h9_confidence = random.uniform(30, 60)

    # 生成排除比分（模拟）
    excluded_scores = []
    if actual_direction == '让胜':
        # 实际是让胜，排除一些小球比分
        excluded_scores = ['0:0', '1:1', '0:1']
    elif actual_direction == '让负':
        excluded_scores = ['0:0', '1:1', '1:0']
    else:
        excluded_scores = ['2:0', '0:2', '3:0']

    # 生成画像规律（模拟）
    image_rules = []
    if random.random() < 0.6:  # 60%概率有🔥规则
        image_rules.append({
            'rule': f'模拟规则_{actual_direction}',
            'direction': actual_direction,
            'tag': '🔥'
        })

    # 生成历史高命中率比分（模拟）
    historical_scores = []
    if actual_direction == '让胜':
        historical_scores = ['2:1', '2:0', '3:1']
    elif actual_direction == '让负':
        historical_scores = ['1:2', '0:2', '1:3']
    else:
        historical_scores = ['1:1', '0:0', '2:2']

    return {
        'h9': {
            'prediction': h9_prediction,
            'confidence': h9_confidence
        },
        'excluded_scores': excluded_scores,
        'image_rules': image_rules,
        'historical_scores': historical_scores
    }

def score_direction(direction, h9_result, excluded_scores, image_rules, historical_scores):
    """
    对单个方向进行打分
    返回该方向的总分数
    """
    score = 0

    # 1. H9分析 (2分)
    if h9_result['prediction'] == direction:
        if h9_result['confidence'] >= 70:
            score += 2  # 高置信度
        else:
            score += 1  # 低置信度
    else:
        # H9预测不是这个方向 = 反向指标
        # 用户说：低置信度也=-2给相反方向
        score -= 2

    # 2. 排除比分 (2分)
    for excluded in excluded_scores:
        if ':' not in excluded:
            continue

        try:
            home_goals, away_goals = map(int, excluded.split(':'))
            goal_diff = home_goals - away_goals

            # 排除比分更有利于哪个方向，那个方向扣分
            if goal_diff > 0:  # 主队进球多，排除让胜
                if direction == '让胜':
                    score -= 2
            elif goal_diff < 0:  # 客队进球多，排除让负
                if direction == '让负':
                    score -= 2
            else:  # 平局，排除让平
                if direction == '让平':
                    score -= 2
        except:
            continue

    # 3. 画像规律 (1分每个，仅🔥标签)
    for rule in image_rules:
        if rule.get('direction') == direction and rule.get('tag') == '🔥':
            score += 1

    # 4. 历史高命中率比分 (1分每个)
    for hist_score in historical_scores:
        if ':' not in hist_score:
            continue

        try:
            home_goals, away_goals = map(int, hist_score.split(':'))
            goal_diff = home_goals - away_goals

            if goal_diff > 0 and direction == '让胜':
                score += 1
            elif goal_diff < 0 and direction == '让负':
                score += 1
            elif goal_diff == 0 and direction == '让平':
                score += 1
        except:
            continue

    return score

def backtest_random(sample_size=100):
    """
    随机模拟回测 - 测试打分系统逻辑
    """
    print(f"\n{'='*80}")
    print(f"随机模拟回测 (样本数: {sample_size})")
    print(f"目的: 测试打分系统逻辑是否合理")
    print(f"{'='*80}\n")

    results = {
        'total': 0,
        'correct': 0,
        'details': []
    }

    directions = ['让胜', '让平', '让负']

    for i in range(sample_size):
        # 随机生成实际方向
        actual_direction = random.choice(directions)

        # 生成模拟的分析结果
        analysis = generate_simulated_analysis(actual_direction)

        h9_result = analysis['h9']
        excluded_scores = analysis['excluded_scores']
        image_rules = analysis['image_rules']
        historical_scores = analysis['historical_scores']

        # 对三个方向打分
        scores = {}
        for direction in directions:
            scores[direction] = score_direction(
                direction, h9_result, excluded_scores,
                image_rules, historical_scores
            )

        # 预测方向（最高分）
        predicted_direction = max(scores, key=scores.get)

        # 判断是否正确
        is_correct = (predicted_direction == actual_direction)
        results['total'] += 1
        if is_correct:
            results['correct'] += 1

        # 记录详细信息
        results['details'].append({
            'match_idx': i,
            'actual_direction': actual_direction,
            'predicted_direction': predicted_direction,
            'is_correct': is_correct,
            'scores': scores,
            'h9_result': h9_result
        })

        # 打印进度
        if (i + 1) % 20 == 0:
            accuracy = results['correct'] / results['total'] * 100
            print(f"进度: {i+1}/{sample_size} | 当前准确率: {accuracy:.2f}%")

    # 计算结果
    final_accuracy = results['correct'] / results['total'] * 100

    print(f"\n{'='*80}")
    print(f"随机模拟回测完成")
    print(f"{'='*80}")
    print(f"总样本数: {results['total']}")
    print(f"正确数: {results['correct']}")
    print(f"准确率: {final_accuracy:.2f}%")
    print(f"随机基线: 33.33%")
    print(f"提升: {final_accuracy - 33.33:.2f}%")
    print(f"{'='*80}\n")

    # 打印一些示例
    print("\n示例预测 (前10个):")
    for detail in results['details'][:10]:
        print(f"  实际: {detail['actual_direction']} | 预测: {detail['predicted_direction']} | {'✅' if detail['is_correct'] else '❌'}")
        print(f"    分数: {detail['scores']} | H9: {detail['h9_result']['prediction']}({detail['h9_result']['confidence']:.0f}%)")

    return results

def backtest_on_historical_data(sample_size=50):
    """
    使用历史数据回测（简化版）
    直接从_scores.json读取历史比分，模拟让球和 analysis
    """
    print(f"\n{'='*80}")
    print(f"历史数据回测 (样本数: {sample_size})")
    print(f"{'='*80}\n")

    # 加载历史比分
    scores_file = "分析模板/_scores.json"
    if not os.path.exists(scores_file):
        print(f"❌ 历史比分文件不存在")
        return None

    with open(scores_file, 'r', encoding='utf-8') as f:
        scores_data = json.load(f)

    # 过滤有效比赛
    valid_matches = []
    for key, match in scores_data.items():
        if 'test' in key.lower():
            continue
        if match.get('home_score') is not None and match.get('away_score') is not None:
            valid_matches.append(match)

    print(f"✅ 加载历史比分: {len(valid_matches)} 场比赛")

    results = {
        'total': 0,
        'correct': 0,
        'details': []
    }

    random.seed(42)  # 固定随机种子，确保可重复

    for i, match in enumerate(valid_matches[:sample_size]):
        home_score = match.get('home_score')
        away_score = match.get('away_score')

        # 模拟让球（随机生成）
        handicap = random.choice([-2, -1, -0.5, 0, 0.5, 1, 2])

        # 实际方向
        actual_direction = get_handicap_direction(handicap, home_score, away_score)
        if actual_direction is None:
            continue

        # 生成模拟分析
        analysis = generate_simulated_analysis(actual_direction)

        # 打分
        directions = ['让胜', '让平', '让负']
        scores = {}
        for direction in directions:
            scores[direction] = score_direction(
                direction, analysis['h9'], analysis['excluded_scores'],
                analysis['image_rules'], analysis['historical_scores']
            )

        predicted_direction = max(scores, key=scores.get)
        is_correct = (predicted_direction == actual_direction)

        results['total'] += 1
        if is_correct:
            results['correct'] += 1

        results['details'].append({
            'match_idx': i,
            'home_team': match.get('home_team', ''),
            'away_team': match.get('away_team', ''),
            'handicap': handicap,
            'home_score': home_score,
            'away_score': away_score,
            'actual_direction': actual_direction,
            'predicted_direction': predicted_direction,
            'is_correct': is_correct,
            'scores': scores
        })

        if (i + 1) % 10 == 0:
            accuracy = results['correct'] / results['total'] * 100
            print(f"进度: {i+1}/{min(sample_size, len(valid_matches))} | 当前准确率: {accuracy:.2f}%")

    # 结果
    if results['total'] == 0:
        print("❌ 没有成功回测任何比赛")
        return None

    final_accuracy = results['correct'] / results['total'] * 100

    print(f"\n{'='*80}")
    print(f"历史数据回测完成")
    print(f"{'='*80}")
    print(f"总比赛数: {results['total']}")
    print(f"正确数: {results['correct']}")
    print(f"准确率: {final_accuracy:.2f}%")
    print(f"{'='*80}\n")

    return results

def main():
    """主函数"""
    print("="*80)
    print("多因素打分系统回测 v4.0 (简化版)")
    print("="*80)

    # 测试1: 随机模拟回测
    print("\n【测试1】随机模拟回测 (100样本)")
    results_random = backtest_random(sample_size=100)

    # 测试2: 历史数据回测
    print("\n【测试2】历史数据回测 (50样本)")
    results_historical = backtest_on_historical_data(sample_size=50)

    print("\n✅ 回测完成")
    print("\n注意: 当前使用模拟的分析数据")
    print("下一步: 集成真实的分析函数 (v36_analyze)")

if __name__ == "__main__":
    main()
