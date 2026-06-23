#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H9 v2.0 回测脚本

目标：
1. 遍历数据集中的所有比赛
2. 用predict_h9_v2()预测
3. 对比实际结果
4. 计算准确率
5. 按不同场景分别计算准确率
"""

import json
import os
import sys
from datetime import datetime

# 添加h9_predictor_v2.py的路径
sys.path.insert(0, os.path.dirname(__file__))

def backtest_h9_v2(tolerance=0.5, league_level_filter=None, match_type_filter=None):
    """
    回测H9 v2.0预测器
    
    Args:
        tolerance: 相似度容忍度
        league_level_filter: 联赛级别过滤
        match_type_filter: 比赛性质过滤
    
    Returns:
        dict: 回测结果统计
    """
    print(f"=== H9 v2.0 回测开始 ===\n")
    print(f"参数：")
    print(f"  容忍度：±{tolerance}球")
    print(f"  联赛级别过滤：{league_level_filter or '无'}")
    print(f"  比赛性质过滤：{match_type_filter or '无'}\n")
    
    # 加载数据集
    try:
        with open('h9_dataset.json', 'r', encoding='utf-8') as f:
            dataset = json.load(f)
    except Exception as e:
        print(f"❌ 加载数据集失败：{e}")
        return None
    
    total = dataset['metadata']['total_matches']
    print(f"数据集总场数：{total}\n")
    
    # 回测统计
    stats = {
        'total': 0,           # 总预测场数
        'correct': 0,         # 正确预测场数
        'accuracy': 0.0,      # 总体准确率
        'by_consistency': {    # 按一致性分类
            '一致': {'total': 0, 'correct': 0, 'accuracy': 0.0},
            '轻微偏离': {'total': 0, 'correct': 0, 'accuracy': 0.0},
            '严重偏离': {'total': 0, 'correct': 0, 'accuracy': 0.0}
        },
        'by_confidence': {     # 按置信度分类
            '高(≥80%)': {'total': 0, 'correct': 0, 'accuracy': 0.0},
            '中(60-80%)': {'total': 0, 'correct': 0, 'accuracy': 0.0},
            '低(<60%)': {'total': 0, 'correct': 0, 'accuracy': 0.0}
        },
        'details': []          # 详细记录（用于调试）
    }
    
    # 导入预测函数
    try:
        from h9_predictor_v2 import predict_h9_v2
    except Exception as e:
        print(f"❌ 导入预测函数失败：{e}")
        return None
    
    # 遍历所有比赛
    for idx, match in enumerate(dataset['matches']):
        # 必须有实际结果
        if not match.get('result'):
            continue
        
        match_id = match['match_id']
        home_team = match['home_team']
        away_team = match['away_team']
        handicap = match['features']['handicap']
        actual_result = match['result']['handicap_result']
        
        # 加载比赛数据
        try:
            with open(f"sporttery_data/{match_id}.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            # 跳过无法加载的比赛
            continue
        
        # 预测
        result = predict_h9_v2(data, handicap, tolerance, 
                                league_level_filter, match_type_filter)
        
        if not result:
            continue
        
        prediction = result['prediction']
        confidence = result['confidence']
        consistency = result['consistency']
        
        # 判断预测是否正确
        correct = (prediction == actual_result)
        
        # 更新统计
        stats['total'] += 1
        if correct:
            stats['correct'] += 1
        
        # 按一致性分类
        if consistency in stats['by_consistency']:
            stats['by_consistency'][consistency]['total'] += 1
            if correct:
                stats['by_consistency'][consistency]['correct'] += 1
        
        # 按置信度分类
        if confidence >= 80.0:
            conf_key = '高(≥80%)'
        elif confidence >= 60.0:
            conf_key = '中(60-80%)'
        else:
            conf_key = '低(<60%)'
        
        stats['by_confidence'][conf_key]['total'] += 1
        if correct:
            stats['by_confidence'][conf_key]['correct'] += 1
        
        # 记录详细信息
        stats['details'].append({
            'match_id': match_id,
            'home_team': home_team,
            'away_team': away_team,
            'handicap': handicap,
            'prediction': prediction,
            'actual': actual_result,
            'correct': correct,
            'confidence': confidence,
            'consistency': consistency
        })
        
        # 进度提示
        if (idx + 1) % 100 == 0:
            print(f"已处理 {idx + 1}/{total} 场比赛...")
    
    # 计算准确率
    if stats['total'] > 0:
        stats['accuracy'] = stats['correct'] / stats['total'] * 100.0
    
    # 计算各分类的准确率
    for cons_key in stats['by_consistency']:
        s = stats['by_consistency'][cons_key]
        if s['total'] > 0:
            s['accuracy'] = s['correct'] / s['total'] * 100.0
    
    for conf_key in stats['by_confidence']:
        s = stats['by_confidence'][conf_key]
        if s['total'] > 0:
            s['accuracy'] = s['correct'] / s['total'] * 100.0
    
    return stats

def print_backtest_report(stats):
    """打印回测报告"""
    if not stats:
        print("❌ 无回测结果")
        return
    
    print("\n" + "="*60)
    print("H9 v2.0 回测报告")
    print("="*60 + "\n")
    
    # 总体准确率
    print(f"📊 总体准确率：")
    print(f"   总预测场数：{stats['total']}")
    print(f"   正确预测：{stats['correct']}")
    print(f"   准确率：{stats['accuracy']:.2f}%\n")
    
    # 按一致性分类
    print(f"📊 按一致性分类：")
    for cons_key in ['一致', '轻微偏离', '严重偏离']:
        s = stats['by_consistency'][cons_key]
        if s['total'] > 0:
            print(f"   {cons_key}：")
            print(f"      场数：{s['total']} ({s['total']/stats['total']*100:.1f}%)")
            print(f"      正确：{s['correct']}")
            print(f"      准确率：{s['accuracy']:.2f}%\n")
    
    # 按置信度分类
    print(f"📊 按置信度分类：")
    for conf_key in ['高(≥80%)', '中(60-80%)', '低(<60%)']:
        s = stats['by_confidence'][conf_key]
        if s['total'] > 0:
            print(f"   {conf_key}：")
            print(f"      场数：{s['total']} ({s['total']/stats['total']*100:.1f}%)")
            print(f"      正确：{s['correct']}")
            print(f"      准确率：{s['accuracy']:.2f}%\n")
    
    print("="*60)

def save_backtest_report(stats, filename='h9_v2_backtest_report.json'):
    """保存回测报告"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 回测报告已保存到：{filename}")
    except Exception as e:
        print(f"❌ 保存回测报告失败：{e}")

# 主程序
if __name__ == '__main__':
    print("=== H9 v2.0 回测程序 ===\n")
    
    # 回测参数
    tolerance = 0.5  # 相似度容忍度
    league_level_filter = None  # 不过滤
    match_type_filter = None  # 不过滤
    
    # 执行回测
    stats = backtest_h9_v2(tolerance, league_level_filter, match_type_filter)
    
    # 打印报告
    print_backtest_report(stats)
    
    # 保存报告
    if stats:
        save_backtest_report(stats)
