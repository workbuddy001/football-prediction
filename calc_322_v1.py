#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3.22比赛数据分析脚本
使用规律体系：筹码分流 + 真假造热辨别
"""

import os
import re
from pathlib import Path

# 比赛数据定义
matches = [
    {
        "id": "周日001",
        "home": "首尔FC",
        "away": "光州FC",
        "macao_tip": "主",
        "home_form": "WWLLWD",
        "away_form": "DDWDDW",
        "initial_odds": [(1.44, 3.56, 6.50), (1.65, 3.40, 5.00), (1.53, 3.60, 5.25), (1.61, 3.40, 4.80), (1.65, 3.40, 5.25), (1.67, 3.40, 5.25), (1.60, 3.55, 5.00), (1.70, 3.60, 4.70), (1.60, 3.60, 5.40), (1.65, 3.60, 5.25), (1.66, 3.60, 5.25), (1.82, 3.44, 4.47), (1.65, 3.50, 5.00), (1.65, 3.40, 4.80), (1.63, 3.50, 4.96), (1.65, 3.50, 5.25), (1.68, 3.60, 5.25), (1.62, 3.60, 4.35), (1.62, 3.60, 4.35), (1.70, 3.60, 4.70), (1.43, 3.75, 6.00), (1.62, 3.60, 4.35), (1.66, 3.40, 5.00), (1.71, 3.70, 5.40), (1.65, 3.80, 6.40), (1.62, 3.50, 5.50), (1.64, 3.65, 5.50), (1.60, 3.40, 5.00), (1.60, 3.55, 5.25), (1.43, 4.15, 6.70)],
        "realtime_odds": [(1.34, 4.10, 7.20), (1.44, 4.00, 6.50), (1.45, 3.90, 5.70), (1.40, 4.00, 6.50), (1.42, 4.00, 7.00), (1.47, 4.00, 7.00), (1.57, 3.70, 5.50), (1.42, 4.30, 6.90), (1.42, 4.20, 6.90), (1.40, 4.20, 8.00), (1.44, 4.20, 7.00), (1.45, 4.49, 7.87), (1.46, 4.20, 6.80), (1.40, 4.00, 6.50), (1.41, 4.17, 7.30), (1.45, 4.20, 7.00), (1.44, 4.20, 7.00), (1.56, 3.75, 4.80), (1.44, 4.25, 6.70), (1.42, 4.30, 6.90), (1.34, 3.95, 7.25), (1.44, 4.25, 6.70), (1.66, 3.40, 5.00), (1.66, 3.85, 5.60), (1.48, 4.50, 8.60), (1.45, 4.20, 7.25), (1.50, 4.17, 6.95), (1.55, 3.50, 5.25), (1.57, 3.75, 5.50), (1.43, 4.15, 6.70)]
    },
    {
        "id": "周日002",
        "home": "大阪樱花",
        "away": "神户胜利",
        "macao_tip": "客",
        "home_form": "LWDLLW",
        "away_form": "DWWWWW",
        "initial_odds": [(2.97, 3.35, 2.03), (3.20, 3.25, 2.10), (2.98, 3.17, 2.17), (3.25, 3.25, 2.00), (3.10, 3.50, 2.05), (3.40, 3.35, 2.05), (3.20, 3.35, 2.00), (3.05, 3.60, 2.12), (2.90, 3.50, 2.19), (3.20, 3.50, 2.10), (3.40, 3.40, 2.05), (3.23, 3.41, 2.18), (3.20, 3.20, 2.04), (3.20, 3.30, 2.00), (3.14, 3.33, 2.07), (3.45, 3.40, 1.98), (3.30, 3.40, 2.05), (2.99, 3.50, 2.17), (2.99, 3.50, 2.17), (3.05, 3.60, 2.12), (3.00, 3.40, 1.98), (2.99, 3.50, 2.17), (3.20, 3.25, 2.10), (3.45, 3.55, 2.10), (3.10, 3.40, 2.15), (3.40, 3.35, 2.00), (3.41, 3.30, 1.92), (3.00, 3.40, 2.18), (3.00, 3.20, 2.10), (3.15, 3.40, 2.10)],
        "realtime_odds": [(2.55, 3.35, 2.28), (2.63, 3.10, 2.50), (2.55, 3.30, 2.40), (2.60, 3.10, 2.40), (2.70, 3.30, 2.60), (2.70, 3.30, 2.50), (3.00, 3.35, 2.15), (2.56, 3.40, 2.56), (2.60, 3.10, 2.60), (2.70, 3.30, 2.60), (2.70, 3.25, 2.50), (2.74, 3.42, 2.66), (2.60, 3.20, 2.46), (2.60, 3.10, 2.45), (2.72, 3.27, 2.58), (3.30, 3.35, 2.05), (2.70, 3.25, 2.50), (2.84, 3.45, 2.29), (2.81, 3.30, 2.56), (2.56, 3.45, 2.56), (2.52, 3.25, 2.33), (2.80, 3.30, 2.56), (3.00, 3.30, 2.15), (3.15, 3.55, 2.23), (2.84, 3.40, 2.70), (2.70, 3.35, 2.60), (2.86, 3.32, 2.50), (3.00, 3.40, 2.18), (2.90, 3.25, 2.15), (3.00, 3.35, 2.20)]
    },
    {
        "id": "周日003",
        "home": "浦和红钻",
        "away": "町田泽维",
        "macao_tip": "平",
        "home_form": "DLWLWD",
        "away_form": "LWWDWD",
        "initial_odds": [(2.60, 3.10, 2.38), (2.63, 3.00, 2.63), (2.60, 3.03, 2.52), (2.60, 3.10, 2.45), (2.57, 3.10, 2.55), (2.65, 3.10, 2.55), (2.65, 3.05, 2.50), (2.65, 3.30, 2.49), (2.60, 3.20, 2.50), (2.63, 3.20, 2.60), (2.65, 3.30, 2.50), (2.73, 3.10, 2.70), (2.60, 3.10, 2.45), (2.60, 3.00, 2.50), (2.62, 3.06, 2.54), (2.65, 3.20, 2.50), (2.65, 3.30, 2.50), (2.65, 3.15, 2.59), (2.65, 3.15, 2.59), (2.65, 3.30, 2.49), (2.59, 3.10, 2.35), (2.65, 3.15, 2.59), (2.54, 2.82, 2.46), (2.65, 3.00, 2.65), (2.69, 3.08, 2.66), (2.60, 2.95, 2.50), (2.70, 3.00, 2.60), (2.68, 3.05, 2.62), (2.62, 3.00, 2.70), (2.63, 3.10, 2.50)],
        "realtime_odds": [(2.54, 2.95, 2.52), (2.75, 2.90, 2.50), (2.60, 3.03, 2.52), (2.70, 3.00, 2.45), (3.00, 3.00, 2.55), (2.75, 3.05, 2.60), (2.65, 3.05, 2.50), (2.70, 3.10, 2.60), (2.70, 3.00, 2.60), (2.90, 3.13, 2.55), (2.75, 3.20, 2.50), (3.01, 3.11, 2.64), (2.70, 2.95, 2.55), (2.70, 3.00, 2.45), (2.86, 3.13, 2.55), (2.65, 3.20, 2.50), (2.75, 3.20, 2.50), (2.63, 3.20, 2.58), (3.00, 3.15, 2.52), (2.70, 3.10, 2.60), (2.63, 3.00, 2.38), (3.00, 3.15, 2.52), (2.62, 3.15, 2.58), (2.85, 3.10, 2.65), (3.18, 3.02, 2.46), (2.60, 2.90, 2.55), (2.70, 3.00, 2.60), (2.78, 3.05, 2.58), (2.75, 3.00, 2.60), (2.70, 3.00, 2.60)]
    },
    {
        "id": "周日004",
        "home": "珀斯",
        "away": "墨尔本城",
        "macao_tip": "平",
        "home_form": "LDDLLD",
        "away_form": "WDDLLD",
        "initial_odds": [(3.36, 3.40, 1.86), (3.30, 3.30, 2.05), (3.12, 3.35, 1.98), (3.30, 3.40, 2.10), (3.30, 3.40, 2.10), (3.40, 3.50, 2.10), (3.25, 3.40, 2.05), (3.25, 3.60, 2.16), (3.70, 3.50, 1.98), (3.20, 3.40, 2.15), (3.30, 3.40, 2.10), (3.67, 3.21, 2.09), (3.20, 3.35, 2.08), (3.40, 3.50, 2.10), (3.08, 3.27, 2.12), (3.30, 3.40, 2.05), (3.30, 3.40, 2.10), (3.35, 3.50, 2.02), (3.35, 3.50, 2.02), (3.25, 3.60, 2.16), (3.35, 3.40, 1.85), (3.30, 3.45, 2.04), (3.30, 3.30, 2.05), (3.50, 3.55, 2.13), (3.75, 3.45, 1.99), (3.30, 3.35, 2.05), (3.46, 3.57, 2.14), (3.25, 3.40, 2.05), (3.30, 3.40, 2.05), (3.70, 3.55, 1.92)],
        "realtime_odds": [(3.65, 3.45, 1.77), (3.90, 3.40, 1.85), (3.40, 3.35, 1.88), (3.90, 3.70, 1.85), (3.90, 3.60, 1.90), (3.95, 3.60, 1.90), (3.90, 3.40, 1.87), (3.75, 3.75, 1.93), (3.70, 3.60, 1.95), (3.80, 3.70, 1.87), (3.90, 3.70, 1.82), (4.10, 3.75, 1.93), (4.00, 3.60, 1.84), (4.00, 3.60, 1.91), (3.85, 3.51, 1.93), (4.00, 3.50, 1.88), (3.90, 3.50, 1.87), (3.55, 3.55, 1.93), (4.00, 3.65, 1.90), (3.70, 3.75, 1.95), (3.75, 3.50, 1.72), (4.00, 3.65, 1.90), (3.30, 3.30, 2.05), (3.80, 3.55, 2.02), (4.40, 3.75, 1.95), (3.90, 3.70, 1.90), (4.01, 3.70, 1.96), (4.00, 3.40, 1.91), (3.95, 3.35, 1.88), (3.95, 3.55, 1.85)]
    },
    {
        "id": "周日005",
        "home": "奈梅亨",
        "away": "海伦芬",
        "macao_tip": "主",
        "home_form": "WWWLDD",
        "away_form": "WWWLWW",
        "initial_odds": [(1.60, 4.10, 3.85), (1.85, 3.80, 3.40), (1.63, 4.05, 3.78), (1.75, 4.20, 3.90), (1.83, 4.00, 3.50), (1.75, 4.10, 3.95), (1.77, 4.00, 3.75), (1.75, 4.45, 3.95), (1.75, 4.20, 4.00), (1.70, 4.20, 4.10), (1.75, 4.20, 4.00), (1.91, 4.12, 3.73), (1.82, 3.95, 3.45), (1.75, 4.20, 4.00), (1.69, 3.98, 3.84), (1.82, 4.00, 3.45), (1.75, 4.20, 4.00), (1.74, 4.10, 3.85), (1.74, 4.10, 3.85), (1.75, 4.45, 3.95), (1.60, 4.10, 3.80), (1.74, 4.10, 3.85), (1.70, 3.90, 4.00), (1.75, 4.20, 4.00), (1.72, 4.40, 4.00), (1.86, 3.90, 3.40), (1.90, 4.16, 3.64), (1.73, 4.10, 3.85), (1.90, 4.20, 3.45), (1.72, 4.15, 3.90)],
        "realtime_odds": [(1.50, 4.40, 4.25), (1.67, 4.00, 4.00), (1.60, 4.05, 3.95), (1.67, 4.40, 4.20), (1.61, 4.50, 4.50), (1.65, 4.40, 4.30), (1.65, 4.25, 4.25), (1.63, 4.65, 4.55), (1.63, 4.50, 4.60), (1.62, 4.50, 4.75), (1.68, 4.40, 4.20), (1.65, 4.57, 4.68), (1.66, 4.40, 4.40), (1.67, 4.40, 4.20), (1.65, 4.40, 4.40), (1.70, 4.35, 4.20), (1.68, 4.40, 4.20), (1.67, 4.45, 4.40), (1.64, 4.60, 4.50), (1.63, 4.65, 4.55), (1.55, 4.20, 4.00), (1.71, 4.40, 4.20), (1.70, 4.00, 3.90), (1.75, 4.20, 4.00), (1.76, 4.60, 4.60), (1.65, 4.50, 4.40), (1.70, 4.64, 4.42), (1.67, 4.33, 4.20), (1.70, 4.30, 4.20), (1.65, 4.35, 4.25)]
    }
]

def calc_form_score(form_str):
    """计算近况得分 - 最近一场×2，其他4场×1"""
    if not form_str or len(form_str) < 5:
        return 0
    
    score_map = {'W': 3, 'D': 1, 'L': 0}
    total = 0
    
    # 取最近6场（如果不足6场，用现有的）
    recent_form = form_str[-6:] if len(form_str) >= 6 else form_str
    
    for i, result in enumerate(recent_form):
        if i == 0:  # 最近一场（序列最左边）
            total += score_map.get(result, 0) * 2
        else:
            total += score_map.get(result, 0)
    
    return total

def calc_odds_avg(odds_list):
    """计算30家公司赔率平均值"""
    h_sum = d_sum = a_sum = 0
    for h, d, a in odds_list:
        h_sum += h
        d_sum += d
        a_sum += a
    n = len(odds_list)
    return (h_sum/n, d_sum/n, a_sum/n)

def calc_odds_change(initial, realtime):
    """计算赔率变化百分比"""
    h_change = ((realtime[0] - initial[0]) / initial[0]) * 100
    d_change = ((realtime[1] - initial[1]) / initial[1]) * 100
    a_change = ((realtime[2] - initial[2]) / initial[2]) * 100
    return (h_change, d_change, a_change)

def calc_confidence(odds):
    """计算置信度 - 基于赔率倒数"""
    h_prob = 1 / odds[0]
    d_prob = 1 / odds[1]
    a_prob = 1 / odds[2]
    total = h_prob + d_prob + a_prob
    return (h_prob/total*100, d_prob/total*100, a_prob/total*100)

def analyze_match(match):
    """分析单场比赛"""
    # 计算近况差
    home_score = calc_form_score(match['home_form'])
    away_score = calc_form_score(match['away_form'])
    form_diff = home_score - away_score
    
    # 计算赔率平均值
    initial_avg = calc_odds_avg(match['initial_odds'])
    realtime_avg = calc_odds_avg(match['realtime_odds'])
    
    # 计算赔率变化
    change = calc_odds_change(initial_avg, realtime_avg)
    
    # 计算置信度（使用即时赔率）
    confidence = calc_confidence(realtime_avg)
    
    # 找出赔率最低方向
    min_odds = min(realtime_avg)
    if min_odds == realtime_avg[0]:
        lowest_dir = "主"
    elif min_odds == realtime_avg[1]:
        lowest_dir = "平"
    else:
        lowest_dir = "客"
    
    # 判断分歧
    macao_dir = match['macao_tip']
    is_divergence = (macao_dir != lowest_dir)
    
    # 判断筹码状态
    max_change = max(abs(c) for c in change)
    if max_change < 2:
        chip_status = "全锁定"
    elif max_change < 5:
        chip_status = "均衡分流"
    else:
        chip_status = "单向造热"
    
    # 真假造热辨别
    macao_idx = {"主": 0, "平": 1, "客": 2}.get(macao_dir, 0)
    macao_change = change[macao_idx]
    
    fake_hot = False
    real_hot = False
    if macao_change < -10:  # 澳门方向大幅降赔
        other_changes = [change[i] for i in range(3) if i != macao_idx]
        分流_count = sum(1 for c in other_changes if c < -2)
        if 分流_count >= 1:
            fake_hot = True  # 假造热，实盘
        else:
            real_hot = True  # 真造热，诱盘
    
    return {
        'id': match['id'],
        'home': match['home'],
        'away': match['away'],
        'macao_tip': macao_dir,
        'home_score': home_score,
        'away_score': away_score,
        'form_diff': form_diff,
        'initial': initial_avg,
        'realtime': realtime_avg,
        'change': change,
        'confidence': confidence,
        'lowest_dir': lowest_dir,
        'is_divergence': is_divergence,
        'chip_status': chip_status,
        'fake_hot': fake_hot,
        'real_hot': real_hot
    }

def get_prediction(result):
    """根据分析结果给出预测"""
    macao_dir = result['macao_tip']
    lowest_dir = result['lowest_dir']
    change = result['change']
    confidence = result['confidence']
    form_diff = result['form_diff']
    fake_hot = result['fake_hot']
    real_hot = result['real_hot']
    
    # 规律R：真假造热辨别
    if real_hot:
        # 真造热，反向
        if macao_dir == "主":
            return "平局或客胜"
        elif macao_dir == "客":
            return "平局或主胜"
        else:
            return "主胜或客胜"
    
    if fake_hot:
        # 假造热，顺向
        if macao_dir == "主":
            return "主胜"
        elif macao_dir == "客":
            return "客胜"
        else:
            return "平局"
    
    # 规律五：主胜升幅>5% → 和局
    if change[0] > 5:
        return "平局"
    
    # 规律H：高置信度+赔率稳定
    if max(confidence) >= 66 and max(abs(c) for c in change) < 5:
        if confidence[0] >= 66:
            return "主胜"
        elif confidence[1] >= 66:
            return "平局"
        elif confidence[2] >= 66:
            return "客胜"
    
    # 规律O：近况差+8以上+赔率微变
    if form_diff >= 8 and max(abs(c) for c in change) < 2:
        return "主胜"
    
    # 分歧场次
    if result['is_divergence']:
        if form_diff >= 5:
            return "主胜"
        elif form_diff <= -5:
            return "客胜"
        else:
            return "平局"
    
    # 同向场次
    if macao_dir == lowest_dir:
        if macao_dir == "主":
            return "主胜"
        elif macao_dir == "平":
            return "平局"
        else:
            return "客胜"
    
    return "需进一步分析"

def get_stability(result):
    """计算稳定性评分"""
    stability = 5
    
    # 同向加分
    if not result['is_divergence']:
        stability += 2
    
    # 高置信度加分
    if max(result['confidence']) >= 66:
        stability += 1
    
    # 赔率稳定加分
    if max(abs(c) for c in result['change']) < 2:
        stability += 1
    
    # 近况差支持加分
    if result['form_diff'] >= 5 and result['macao_tip'] == "主":
        stability += 1
    
    return min(stability, 10)

def main():
    print("=" * 80)
    print("3.22比赛数据分析报告")
    print("=" * 80)
    
    results = []
    for match in matches:
        result = analyze_match(match)
        result['prediction'] = get_prediction(result)
        result['stability'] = get_stability(result)
        results.append(result)
    
    # 打印完整数据列表
    print("\n## 完整数据列表（标准格式）\n")
    print("| 编号 | 对阵 | 置信度 | 澳门心水 | 近况差 | 初盘(胜/平/负) | 即时(胜/平/负) | 变化(H/D/A) | 最终预测 |")
    print("|------|------|--------|----------|--------|----------------|----------------|-------------|----------|")
    
    for r in results:
        conf_max = max(r['confidence'])
        conf_str = f"{conf_max:.1f}%"
        form_str = f"{r['form_diff']:+d}"
        initial_str = f"{r['initial'][0]:.2f}/{r['initial'][1]:.2f}/{r['initial'][2]:.2f}"
        realtime_str = f"{r['realtime'][0]:.2f}/{r['realtime'][1]:.2f}/{r['realtime'][2]:.2f}"
        change_str = f"主{r['change'][0]:+.1f}% 平{r['change'][1]:+.1f}% 客{r['change'][2]:+.1f}%"
        
        print(f"| {r['id']} | {r['home']} vs {r['away']} | {conf_str} | {r['macao_tip']} | {form_str} | {initial_str} | {realtime_str} | {change_str} | {r['prediction']} |")
    
    # 打印稳胆推荐
    print("\n## 最稳比赛推荐(稳胆)\n")
    stable_matches = [r for r in results if r['stability'] >= 7]
    stable_matches.sort(key=lambda x: x['stability'], reverse=True)
    
    if stable_matches:
        print("| 排名 | 编号 | 对阵 | 预测 | 稳定性 | 理由 |")
        print("|------|------|------|------|--------|------|")
        for i, r in enumerate(stable_matches[:5], 1):
            reason = []
            if not r['is_divergence']:
                reason.append("同向")
            if max(r['confidence']) >= 66:
                reason.append("高置信")
            if max(abs(c) for c in r['change']) < 2:
                reason.append("赔率稳")
            print(f"| {i} | {r['id']} | {r['home']} vs {r['away']} | {r['prediction']} | {r['stability']}/10 | {', '.join(reason)} |")
    else:
        print("暂无高稳定性推荐")
    
    # 打印爆冷警示
    print("\n## 最可能爆冷的比赛\n")
    upset_matches = []
    for r in results:
        if r['real_hot'] or (r['is_divergence'] and abs(r['form_diff']) <= 3):
            upset_matches.append(r)
    
    if upset_matches:
        print("| 排名 | 编号 | 对阵 | 预测 | 爆冷风险 | 理由 |")
        print("|------|------|------|------|----------|------|")
        for i, r in enumerate(upset_matches[:5], 1):
            reason = []
            if r['real_hot']:
                reason.append("真造热")
            if r['is_divergence']:
                reason.append("分歧")
            print(f"| {i} | {r['id']} | {r['home']} vs {r['away']} | {r['prediction']} | 高 | {', '.join(reason)} |")
    else:
        print("暂无高爆冷风险比赛")
    
    # 打印规律R应用
    print("\n## 规律R真假造热辨别应用\n")
    print("| 类型 | 编号 | 对阵 | 澳门方向 | 澳门变化 | 其他变化 | 判断 |")
    print("|------|------|------|----------|----------|----------|------|")
    
    for r in results:
        if r['fake_hot'] or r['real_hot']:
            macao_idx = {"主": 0, "平": 1, "客": 2}.get(r['macao_tip'], 0)
            macao_change = r['change'][macao_idx]
            other_changes = [r['change'][i] for i in range(3) if i != macao_idx]
            other_str = f"{other_changes[0]:+.1f}%, {other_changes[1]:+.1f}%"
            hot_type = "真造热(诱盘)" if r['real_hot'] else "假造热(实盘)"
            print(f"| {hot_type} | {r['id']} | {r['home']} vs {r['away']} | {r['macao_tip']} | {macao_change:+.1f}% | {other_str} | {r['prediction']} |")
    
    # 打印分歧场次
    print("\n## 分歧场次警示\n")
    div_matches = [r for r in results if r['is_divergence']]
    if div_matches:
        print("| 编号 | 对阵 | 澳门心水 | 赔率最低 | 近况差 | 建议 |")
        print("|------|------|----------|----------|--------|------|")
        for r in div_matches:
            print(f"| {r['id']} | {r['home']} vs {r['away']} | {r['macao_tip']} | {r['lowest_dir']} | {r['form_diff']:+d} | 谨慎对待 |")
    else:
        print("无分歧场次")

if __name__ == "__main__":
    main()
