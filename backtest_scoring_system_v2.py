#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测脚本 - 多因素打分系统 v2.0
实现用户的打分系统：H9(2pt) + 排除比分(2pt) + 画像规律(1pt) + 历史比分(1pt)
调用真实的分析函数获取数据
"""

import json
import os
import sys
from collections import defaultdict

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_dataset():
    """加载H9数据集"""
    dataset_path = "h9_dataset.json"
    if not os.path.exists(dataset_path):
        print(f"❌ 数据集文件不存在: {dataset_path}")
        return []

    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    matches = dataset.get('matches', [])
    print(f"✅ 加载数据集: {len(matches)} 场比赛")
    return matches

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

def parse_v36_analysis(analysis_text):
    """
    解析V3.6分析文本，提取关键信息
    返回: {
        'h9': {...},
        'excluded_scores': [...],
        'image_rules': [...],
        'historical_scores': [...]
    }
    """
    result = {
        'h9': {'prediction': None, 'confidence': 0},
        'excluded_scores': [],
        'image_rules': [],
        'historical_scores': []
    }

    if not analysis_text:
        return result

    lines = analysis_text.split('\n')

    # 解析H9分析
    for line in lines:
        if 'H9' in line or 'h9' in line:
            if '让胜' in line:
                result['h9']['prediction'] = '让胜'
            elif '让平' in line:
                result['h9']['prediction'] = '让平'
            elif '让负' in line:
                result['h9']['prediction'] = '让负'

            # 提取置信度
            if '置信度' in line:
                try:
                    conf_str = line.split('置信度')[1].split('%')[0].strip()
                    result['h9']['confidence'] = float(conf_str)
                except:
                    pass

        # 解析排除比分
        if '排除比分' in line or '排除:' in line:
            # 提取比分格式如 "0:0", "1:1"
            import re
            scores = re.findall(r'\d+:\d+', line)
            result['excluded_scores'].extend(scores)

        # 解析画像规律
        if '画像' in line or '规律' in line:
            rule = {'rule': line.strip(), 'direction': None, 'tag': ''}
            if '让胜' in line:
                rule['direction'] = '让胜'
            elif '让平' in line:
                rule['direction'] = '让平'
            elif '让负' in line:
                rule['direction'] = '让负'

            if '🔥' in line:
                rule['tag'] = '🔥'

            result['image_rules'].append(rule)

        # 解析历史高命中率比分
        if '历史' in line and ('命中率' in line or '高命中' in line):
            import re
            scores = re.findall(r'\d+:\d+', line)
            result['historical_scores'].extend(scores)

    return result

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
        if h9_result['confidence'] >= 70:
            score -= 2  # 高置信度预测其他方向，这个方向扣分
        else:
            score -= 2  # 用户说低置信度也=-2给相反方向

    # 2. 排除比分 (2分)
    for excluded in excluded_scores:
        if ':' not in excluded:
            continue

        home_goals, away_goals = map(int, excluded.split(':'))
        goal_diff = home_goals - away_goals

        # 排除比分更有利于哪个方向，那个方向扣分
        if goal_diff > 0:  # 主队进球多
            if direction == '让胜':
                score -= 2
            elif direction == '让负':
                score += 1
        elif goal_diff < 0:  # 客队进球多
            if direction == '让负':
                score -= 2
            elif direction == '让胜':
                score += 1
        else:  # 平局
            if direction == '让平':
                score -= 2
            else:
                score += 1

    # 3. 画像规律 (1分每个，仅🔥标签)
    for rule in image_rules:
        if rule.get('direction') == direction and rule.get('tag') == '🔥':
            score += 1

    # 4. 历史高命中率比分 (1分每个)
    for hist_score in historical_scores:
        if ':' not in hist_score:
            continue

        home_goals, away_goals = map(int, hist_score.split(':'))
        goal_diff = home_goals - away_goals

        if goal_diff > 0 and direction == '让胜':
            score += 1
        elif goal_diff < 0 and direction == '让负':
            score += 1
        elif goal_diff == 0 and direction == '让平':
            score += 1

    return score

def backtest_scoring_system(matches, sample_size=100):
    """
    回测打分系统
    """
    print(f"\n{'='*80}")
    print(f"开始回测打分系统 v2.0 (样本数: {min(sample_size, len(matches))})")
    print(f"{'='*80}\n")

    # 动态导入分析函数
    try:
        from ai_reasoning import v36_analyze
        print("✅ 已加载 v36_analyze 函数")
    except ImportError as e:
        print(f"❌ 无法导入分析函数: {e}")
        return None

    results = {
        'total': 0,
        'correct': 0,
        'details': []
    }

    # 只回测有实际比分的比赛
    valid_matches = []
    for match in matches[:sample_size * 2]:  # 多取一些，可能有部分没有比分
        match_id = match.get('match_id')
        if not match_id:
            continue

        # 检查是否有实际比分
        file_path = f"sporttery_data/{match_id}.json"
        if not os.path.exists(file_path):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                actual_data = json.load(f)

            if actual_data.get('home_score') is not None and actual_data.get('away_score') is not None:
                valid_matches.append((match, actual_data))
        except:
            continue

        if len(valid_matches) >= sample_size:
            break

    print(f"✅ 找到有效比赛数: {len(valid_matches)}")

    if len(valid_matches) == 0:
        print("❌ 没有找到有效比赛（需要有实际比分）")
        return None

    for idx, (match, actual_data) in enumerate(valid_matches):
        match_id = match.get('match_id')
        home_team = match.get('home_team', '')
        away_team = match.get('away_team', '')
        home_score = actual_data.get('home_score')
        away_score = actual_data.get('away_score')
        handicap = match.get('handicap')

        if handicap is None:
            continue

        # 实际方向
        actual_direction = get_handicap_direction(handicap, home_score, away_score)
        if actual_direction is None:
            continue

        # 调用真实分析函数
        try:
            analysis_result = v36_analyze(match_id)
            # 解析分析结果
            parsed = parse_v36_analysis(str(analysis_result))
        except Exception as e:
            print(f"⚠️  分析失败 {match_id}: {e}")
            continue

        h9_result = parsed['h9']
        excluded_scores = parsed['excluded_scores']
        image_rules = parsed['image_rules']
        historical_scores = parsed['historical_scores']

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
            'scores': scores,
            'h9_result': h9_result,
            'excluded_scores': excluded_scores,
            'image_rules': image_rules,
            'historical_scores': historical_scores
        })

        # 打印进度
        if (idx + 1) % 10 == 0:
            accuracy = results['correct'] / results['total'] * 100 if results['total'] > 0 else 0
            print(f"进度: {idx+1}/{len(valid_matches)} | 当前准确率: {accuracy:.2f}%")

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
    output_file = f"backtest_scoring_system_v2_result.json"
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
    print("多因素打分系统回测 v2.0")
    print("="*80)

    # 加载数据集
    matches = load_dataset()
    if not matches:
        return

    # 先回测50场（测试用）
    print("\n第一步: 回测50场比赛（测试）")
    results_50 = backtest_scoring_system(matches, sample_size=50)

    if results_50 is None:
        print("❌ 回测失败")
        return

    # 询问是否回测更多
    print(f"\n是否回测100场? (y/n)")
    choice = input().strip().lower()

    if choice == 'y':
        print("\n第二步: 回测100场")
        results_100 = backtest_scoring_system(matches, sample_size=100)

    print("\n✅ 回测完成")

if __name__ == "__main__":
    main()
