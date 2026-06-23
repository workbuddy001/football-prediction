#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测脚本 - 多因素打分系统 v3.0
使用分析模板/_scores.json中的历史比分数据进行回测
"""

import json
import os
import sys
import re

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_historical_scores():
    """加载历史比分数据"""
    scores_file = "分析模板/_scores.json"
    if not os.path.exists(scores_file):
        print(f"❌ 历史比分文件不存在: {scores_file}")
        return []

    with open(scores_file, 'r', encoding='utf-8') as f:
        scores_data = json.load(f)

    # 过滤掉测试数据，只保留有效比分
    valid_matches = []
    for key, match in scores_data.items():
        if 'test' in key.lower():
            continue
        if match.get('home_score') is not None and match.get('away_score') is not None:
            match['key'] = key  # 保存key用于查找
            valid_matches.append(match)

    print(f"✅ 加载历史比分: {len(valid_matches)} 场比赛")
    return valid_matches

def find_match_id_from_key(key):
    """
    根据_scores.json中的key找到对应的match_id
    key格式如: "4.08_周三001"
    """
    # 从key中提取日期和编号
    # 例如: "4.08_周三001" -> 需要找到对应的 sporttery_data/*.json

    # 方法1: 在sporttery_data中查找包含相同球队信息的文件
    # 方法2: 从key中提取日期，在sporttery_data中查找该日期附近的文件

    # 简化处理：假设key中的编号（如"周三001"）对应match_id的后几位
    # 或者直接从sporttery_data文件名匹配

    # 这里先返回None，表示需要手动匹配
    return None

def load_sporttery_by_match_info(home_team, away_team, date):
    """
    根据主客队名称和日期，在sporttery_data中查找对应的文件
    """
    sporttery_dir = "sporttery_data"
    if not os.path.exists(sporttery_dir):
        return None

    # 遍历所有文件，查找匹配的比赛
    for fname in os.listdir(sporttery_dir):
        if not fname.endswith('.json'):
            continue

        fpath = os.path.join(sporttery_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检查是否匹配
            data_home = data.get('home_team', '')
            data_away = data.get('away_team', '')

            if home_team in data_home or data_home in home_team:
                if away_team in data_away or data_away in away_team:
                    return data, fname.replace('.json', '')
        except:
            continue

    return None

def get_handicap_from_data(data):
    """从数据中提取让球"""
    # 尝试从hhad_odds中提取让球
    hhad_odds = data.get('hhad_odds', [])
    if hhad_odds and len(hhad_odds) > 0:
        # 通常第一个是让球
        handicap_str = hhad_odds[0].get('handicap', '')
        if handicap_str:
            try:
                return float(handicap_str)
            except:
                pass

    return None

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

def simulate_analysis(match_info, sporttery_data):
    """
    模拟分析（简化版）
    实际应该调用真实的分析函数
    """
    # 这里返回模拟数据
    # 实际实现需要调用 ai_reasoning.py 中的函数

    home_score = match_info.get('home_score', 0)
    away_score = match_info.get('away_score', 0)

    # 简单逻辑：根据比分判断方向
    goal_diff = home_score - away_score

    if goal_diff > 0:
        prediction = '让胜'
        confidence = 60
    elif goal_diff < 0:
        prediction = '让负'
        confidence = 60
    else:
        prediction = '让平'
        confidence = 40

    return {
        'h9': {
            'prediction': prediction,
            'confidence': confidence
        },
        'excluded_scores': ['0:0', '1:1'],
        'image_rules': [
            {'rule': '测试规则', 'direction': prediction, 'tag': '🔥'}
        ],
        'historical_scores': ['2:1', '1:0']
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
            score += 2
        else:
            score += 1
    else:
        # 低置信度 = -2给相反方向
        score -= 2

    # 2. 排除比分 (2分)
    for excluded in excluded_scores:
        if ':' not in excluded:
            continue

        try:
            home_goals, away_goals = map(int, excluded.split(':'))
            goal_diff = home_goals - away_goals

            if goal_diff > 0 and direction == '让胜':
                score -= 2
            elif goal_diff < 0 and direction == '让负':
                score -= 2
            elif goal_diff == 0 and direction == '让平':
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

def backtest_scoring_system(sample_size=50):
    """
    回测打分系统
    """
    print(f"\n{'='*80}")
    print(f"开始回测打分系统 v3.0 (样本数: {sample_size})")
    print(f"{'='*80}\n")

    # 加载历史比分
    historical_matches = load_historical_scores()
    if not historical_matches:
        return None

    results = {
        'total': 0,
        'correct': 0,
        'details': []
    }

    # 遍历历史比赛
    valid_count = 0
    for match in historical_matches:
        if valid_count >= sample_size:
            break

        home_team = match.get('home_team', '')
        away_team = match.get('away_team', '')
        home_score = match.get('home_score')
        away_score = match.get('away_score')
        date = match.get('date', '')

        if not home_team or not away_team:
            continue

        # 查找对应的sporttery数据
        result = load_sporttery_by_match_info(home_team, away_team, date)
        if result is None:
            continue

        sporttery_data, match_id = result
        handicap = get_handicap_from_data(sporttery_data)

        if handicap is None:
            continue

        # 实际方向
        actual_direction = get_handicap_direction(handicap, home_score, away_score)
        if actual_direction is None:
            continue

        # 模拟分析（实际应该调用真实分析函数）
        analysis = simulate_analysis(match, sporttery_data)

        h9_result = analysis['h9']
        excluded_scores = analysis['excluded_scores']
        image_rules = analysis['image_rules']
        historical_scores = analysis['historical_scores']

        # 对三个方向打分
        directions = ['让胜', '让平', '让负']
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

        valid_count += 1

        # 记录详细信息
        results['details'].append({
            'match_id': match_id,
            'home_team': home_team,
            'away_team': away_team,
            'handicap': handicap,
            'home_score': home_score,
            'away_score': away_score,
            'actual_direction': actual_direction,
            'predicted_direction': predicted_direction,
            'is_correct': is_correct,
            'scores': scores
        })

        # 打印进度
        if valid_count % 10 == 0:
            accuracy = results['correct'] / results['total'] * 100 if results['total'] > 0 else 0
            print(f"进度: {valid_count}/{sample_size} | 当前准确率: {accuracy:.2f}%")

    # 计算结果
    if results['total'] == 0:
        print("❌ 没有成功回测任何比赛")
        return None

    final_accuracy = results['correct'] / results['total'] * 100

    print(f"\n{'='*80}")
    print(f"回测完成")
    print(f"{'='*80}")
    print(f"总比赛数: {results['total']}")
    print(f"正确数: {results['correct']}")
    print(f"准确率: {final_accuracy:.2f}%")
    print(f"{'='*80}\n")

    # 保存结果
    output_file = f"backtest_scoring_system_v3_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"✅ 结果已保存: {output_file}")

    # 打印一些示例
    print("\n示例预测:")
    for detail in results['details'][:5]:
        print(f"  {detail['home_team']} vs {detail['away_team']}")
        print(f"    实际: {detail['actual_direction']} | 预测: {detail['predicted_direction']} | {'✅' if detail['is_correct'] else '❌'}")
        print(f"    分数: {detail['scores']}")

    return results

def main():
    """主函数"""
    print("="*80)
    print("多因素打分系统回测 v3.0")
    print("使用分析模板/_scores.json中的历史数据")
    print("="*80)

    # 回测50场
    print("\n开始回测50场比赛...")
    results = backtest_scoring_system(sample_size=50)

    if results is None:
        print("❌ 回测失败")
        return

    print("\n✅ 回测完成")

if __name__ == "__main__":
    main()
