#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
回测H9预测器：比较高置信度 vs 低置信度场景的命中率
"""

import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))

def calc_actual_direction(home_score, away_score, handicap):
    """
    计算实际让球方向
    
    Args:
        home_score: 主队实际进球
        away_score: 客队实际进球
        handicap: 让球数（如 -1, +1）
    
    Returns:
        "让胜" / "让平" / "让负"
    """
    adjusted_home = home_score + handicap
    diff = adjusted_home - away_score
    
    if diff > 0:
        return "让胜"
    elif diff == 0:
        return "让平"
    else:
        return "让负"

def backtest_h9_confidence():
    """回测H9预测器：比较高 vs 低置信度命中率"""
    
    print("=== H9预测器回测：高置信度 vs 低置信度 ===\n")
    
    # 1. 加载所有比赛
    sporttery_dir = "sporttery_data"
    all_files = [f for f in os.listdir(sporttery_dir) if f.endswith(".json")]
    all_matches = [f.replace(".json", "") for f in all_files]
    
    print(f"扫描到 {len(all_matches)} 场比赛\n")
    
    # 2. 加载实际比分
    scores_file = os.path.join("分析模板", "_scores.json")
    try:
        with open(scores_file, "r", encoding="utf-8") as f:
            scores_data = json.load(f)
    except Exception as e:
        print(f"❌ 无法加载实际比分: {e}")
        return
    
    # 3. 统计
    high_conf_correct = 0
    high_conf_total = 0
    low_conf_correct = 0
    low_conf_total = 0
    
    # 详细统计：低置信度场景中，各预测方向的命中率
    low_conf_by_direction = defaultdict(lambda: {"correct": 0, "total": 0})
    
    # 调试：收集低置信度场景的分布
    low_conf_situations = defaultdict(int)
    high_conf_situations = defaultdict(int)
    
    for idx, match_id in enumerate(all_matches):
        # 加载比赛数据
        try:
            with open(f"{sporttery_dir}/{match_id}.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            continue
        
        # 获取实际比分
        actual = scores_data.get(match_id) or scores_data.get(str(match_id))
        if not actual or "home_score" not in actual:
            continue
        
        home_score = int(actual["home_score"])
        away_score = int(actual["away_score"])
        
        # 获取让球数
        hhad = data.get("hhad", {})
        if not hhad or "让球" not in hhad:
            continue
        
        try:
            handicap = float(hhad["让球"])
        except:
            continue
        
        # 调用H9预测
        try:
            from h9_predictor import predict_h9
            result = predict_h9(data, handicap)
        except Exception as e:
            continue
        
        if not result or not result.get("prediction"):
            continue
        
        # 判断预测是否正确
        prediction = result["prediction"]
        actual_direction = calc_actual_direction(home_score, away_score, handicap)
        is_correct = (prediction == actual_direction)
        
        # 根据置信度分类统计
        is_high_conf = result["is_high_conf"]
        situation = result["situation"]
        
        if is_high_conf:
            high_conf_total += 1
            high_conf_situations[situation] += 1
            if is_correct:
                high_conf_correct += 1
        else:
            low_conf_total += 1
            low_conf_situations[situation] += 1
            low_conf_by_direction[prediction]["total"] += 1
            if is_correct:
                low_conf_correct += 1
                low_conf_by_direction[prediction]["correct"] += 1
    
    # 4. 计算命中率
    high_conf_hit_rate = (high_conf_correct / high_conf_total * 100) if high_conf_total > 0 else 0
    low_conf_hit_rate = (low_conf_correct / low_conf_total * 100) if low_conf_total > 0 else 0
    
    # 5. 输出结果
    print("=" * 60)
    print("回测结果")
    print("=" * 60)
    print(f"\n高置信度场景: {high_conf_total}场, 命中{high_conf_correct}场, 命中率{high_conf_hit_rate:.1f}%")
    print(f"低置信度场景: {low_conf_total}场, 命中{low_conf_correct}场, 命中率{low_conf_hit_rate:.1f}%")
    
    # 6. 分析低置信度场景
    print(f"\n{'=' * 60}")
    print("低置信度场景详细分析")
    print(f"{'=' * 60}")
    
    if low_conf_total > 0:
        print(f"\n低置信度场景各预测方向的命中率:")
        for direction, stats in sorted(low_conf_by_direction.items()):
            total = stats["total"]
            correct = stats["correct"]
            hit_rate = (correct / total * 100) if total > 0 else 0
            print(f"  {direction}: {total}场, 命中{correct}场, 命中率{hit_rate:.1f}%")
        
        # 判断低置信度是否应该反向
        if low_conf_hit_rate < 45:
            print(f"\n⚠️ 低置信度场景命中率{low_conf_hit_rate:.1f}%，可能应该反向投注！")
            print(f"   建议：低置信度场景推荐的方向，实际应该投注相反方向")
        elif low_conf_hit_rate > 55:
            print(f"\n✅ 低置信度场景命中率{low_conf_hit_rate:.1f}%，仍有参考价值")
        else:
            print(f"\n➖ 低置信度场景命中率{low_conf_hit_rate:.1f}%，接近随机")
    
    # 7. 输出高频低置信度场景
    print(f"\n{'=' * 60}")
    print("高频低置信度场景 (top 10)")
    print(f"{'=' * 60}")
    
    if low_conf_situations:
        sorted_low = sorted(low_conf_situations.items(), key=lambda x: x[1], reverse=True)[:10]
        for situation, count in sorted_low:
            print(f"  {situation}: {count}场")
    
    # 8. 结论
    print(f"\n{'=' * 60}")
    print("结论")
    print(f"{'=' * 60}")
    
    if high_conf_hit_rate > low_conf_hit_rate + 10:
        print(f"\n✅ 高置信度场景命中率明显高于低置信度场景（+{high_conf_hit_rate - low_conf_hit_rate:.1f}%）")
        print(f"   建议：只在高置信度场景下使用H9推荐")
    elif high_conf_hit_rate < low_conf_hit_rate - 10:
        print(f"\n⚠️ 低置信度场景命中率反而高于高置信度场景（反常！）")
        print(f"   建议：检查高置信度场景的定义是否合理")
    else:
        print(f"\n➖ 高置信度场景与低置信度场景命中率接近（差{abs(high_conf_hit_rate - low_conf_hit_rate):.1f}%）")
        print(f"   建议：重新评估H9预测器的价值")

if __name__ == "__main__":
    backtest_h9_confidence()
