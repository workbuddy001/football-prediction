#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测脚本 - 多因素打分系统 v5.0 (真实数据版)
匹配历史比分与竞彩数据，调用真实分析函数
"""

import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_historical_scores():
    """加载历史比分数据"""
    scores_file = "分析模板/_scores.json"
    if not os.path.exists(scores_file):
        print(f"❌ 历史比分文件不存在: {scores_file}")
        return []

    with open(scores_file, 'r', encoding='utf-8') as f:
        scores_data = json.load(f)

    # 过滤有效比赛
    valid_matches = []
    for key, match in scores_data.items():
        if 'test' in key.lower():
            continue
        if match.get('home_score') is not None and match.get('away_score') is not None:
            match['key'] = key
            valid_matches.append(match)

    print(f"✅ 加载历史比分: {len(valid_matches)} 场比赛")
    return valid_matches

def find_sporttery_data(home_team, away_team):
    """
    根据主客队名称，在sporttery_data中查找对应的文件
    """
    sporttery_dir = "sporttery_data"
    if not os.path.exists(sporttery_dir):
        return None, None

    # 清理队名（去除特殊字符）
    def clean_name(name):
        if not name:
            return ''
        # 去除"_源数据"等后缀
        name = name.replace('_源数据', '').replace(' ', '')
        return name.strip()

    home_clean = clean_name(home_team)
    away_clean = clean_name(away_team)

    # 遍历所有文件
    for fname in os.listdir(sporttery_dir):
        if not fname.endswith('.json'):
            continue

        fpath = os.path.join(sporttery_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 从match_info中获取球队名
            match_info = data.get('match_info', {})
            data_home = match_info.get('home_team', '')
            data_away = match_info.get('away_team', '')

            # 清理数据中的队名
            data_home_clean = clean_name(data_home)
            data_away_clean = clean_name(data_away)

            # 检查是否匹配
            if home_clean in data_home_clean or data_home_clean in home_clean:
                if away_clean in data_away_clean or data_away_clean in away_clean:
                    match_id = fname.replace('.json', '')
                    return data, match_id

        except Exception as e:
            continue

    return None, None

def get_handicap_from_data(data):
    """从数据中提取让球"""
    hhad = data.get('hhad', {})
    if not hhad:
        return None

    # 获取初盘让球
    initial = hhad.get('initial', {})
    handicap_str = initial.get('handicap', '')

    if not handicap_str:
        # 尝试从实时盘获取
        realtime = hhad.get('realtime', {})
        handicap_str = realtime.get('handicap', '')

    if handicap_str:
        try:
            return float(handicap_str)
        except:
            pass

    return None

def get_handicap_direction(handicap, home_score, away_score):
    """判断让球方向"""
    if handicap is None or home_score is None or away_score is None:
        return None

    adjusted_home = home_score + abs(handicap) if handicap < 0 else home_score
    adjusted_away = away_score + abs(handicap) if handicap > 0 else away_score

    if adjusted_home - adjusted_away > 0:
        return '让胜'
    elif adjusted_home - adjusted_away == 0:
        return '让平'
    else:
        return '让负'

def analyze_match_simple(match_id):
    """
    简化版分析函数
    实际应该调用 ai_reasoning.py 中的 v36_analyze
    这里先返回模拟数据
    """
    # TODO: 集成真实的分析函数
    # from ai_reasoning import v36_analyze
    # result = v36_analyze(match_id)
    # return parse_result(result)

    # 模拟数据
    import random
    directions = ['让胜', '让平', '让负']
    prediction = random.choice(directions)
    confidence = random.uniform(30, 90)

    return {
        'h9': {
            'prediction': prediction,
            'confidence': confidence
        },
        'excluded_scores': ['0:0', '1:1'],
        'image_rules': [
            {'rule': '测试规则', 'direction': prediction, 'tag': '🔥' if confidence > 70 else ''}
        ],
        'historical_scores': ['2:1', '1:0'] if prediction == '让胜' else ['0:2', '1:2']
    }

def score_direction(direction, h9_result, excluded_scores, image_rules, historical_scores):
    """对单个方向打分"""
    score = 0

    # 1. H9分析 (2分)
    if h9_result['prediction'] == direction:
        if h9_result['confidence'] >= 70:
            score += 2
        else:
            score += 1
    else:
        # 低置信度也=-2
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

    # 3. 画像规律 (1分，仅🔥)
    for rule in image_rules:
        if rule.get('direction') == direction and rule.get('tag') == '🔥':
            score += 1

    # 4. 历史比分 (1分)
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

def backtest(sample_size=30):
    """回测"""
    print(f"\n{'='*80}")
    print(f"真实数据回测 (样本数: {sample_size})")
    print(f"{'='*80}\n")

    # 加载历史比分
    historical_matches = load_historical_scores()
    if not historical_matches:
        return None

    results = {
        'total': 0,
        'correct': 0,
        'details': [],
        'match_not_found': 0,
        'handicap_not_found': 0
    }

    matched_count = 0
    for match in historical_matches:
        if matched_count >= sample_size:
            break

        home_team = match.get('home_team', '')
        away_team = match.get('away_team', '')
        home_score = match.get('home_score')
        away_score = match.get('away_score')

        if not home_team or not away_team:
            continue

        # 查找对应的竞彩数据
        sporttery_data, match_id = find_sporttery_data(home_team, away_team)
        if sporttery_data is None:
            results['match_not_found'] += 1
            continue

        # 获取让球
        handicap = get_handicap_from_data(sporttery_data)
        if handicap is None:
            results['handicap_not_found'] += 1
            continue

        # 实际方向
        actual_direction = get_handicap_direction(handicap, home_score, away_score)
        if actual_direction is None:
            continue

        # 分析（当前使用模拟，TODO: 调用真实分析）
        analysis = analyze_match_simple(match_id)

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

        matched_count += 1

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

        if matched_count % 5 == 0:
            accuracy = results['correct'] / results['total'] * 100 if results['total'] > 0 else 0
            print(f"进度: {matched_count}/{sample_size} | 准确率: {accuracy:.2f}%")

    # 结果
    if results['total'] == 0:
        print("❌ 没有成功匹配任何比赛")
        print(f"   未找到竞彩数据: {results['match_not_found']}")
        print(f"   未找到让球: {results['handicap_not_found']}")
        return None

    final_accuracy = results['correct'] / results['total'] * 100

    print(f"\n{'='*80}")
    print(f"回测完成")
    print(f"{'='*80}")
    print(f"成功匹配: {results['total']}")
    print(f"正确: {results['correct']}")
    print(f"准确率: {final_accuracy:.2f}%")
    print(f"未找到竞彩数据: {results['match_not_found']}")
    print(f"未找到让球: {results['handicap_not_found']}")
    print(f"{'='*80}\n")

    # 保存结果
    output_file = "backtest_scoring_system_v5_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"✅ 结果已保存: {output_file}")

    return results

def main():
    print("="*80)
    print("多因素打分系统回测 v5.0")
    print("="*80)

    # 回测30场
    results = backtest(sample_size=30)

    if results:
        print("\n✅ 回测完成")
        print("\n⚠️  注意: 当前使用模拟的分析数据")
        print("   需要集成真实的分析函数 (v36_analyze) 才能获得真实准确率")
    else:
        print("\n❌ 回测失败")

if __name__ == "__main__":
    main()
