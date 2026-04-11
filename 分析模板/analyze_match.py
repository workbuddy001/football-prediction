#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
比赛分析工具 - 命令行版本
使用方法: python analyze_match.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from v7_8_segment_analyze_v3 import ComprehensiveEventAnalyzer


def interactive_analysis():
    """交互式分析"""
    print("="*70)
    print("V5 综合事件分析框架 - 交互式分析")
    print("="*70)
    print()
    
    analyzer = ComprehensiveEventAnalyzer()
    
    # 输入基本信息
    print("【基本信息】")
    home = input("主队名称: ").strip()
    away = input("客队名称: ").strip()
    league = input("赛事 (如: 欧冠/英超/西甲): ").strip()
    
    print()
    print("【赔率数据】")
    confidence = int(input("置信度 (%): ").strip())
    conf_option = input("置信度选项 (主胜/平局/客胜): ").strip()
    form_diff = int(input("状态差 (主队胜率% - 客队胜率%): ").strip())
    
    print()
    print("【8变化】")
    home_8 = int(input("主胜8变化: ").strip())
    draw_8 = int(input("平局8变化: ").strip())
    away_8 = int(input("客胜8变化: ").strip())
    
    print()
    print("【近期战绩 (可选)】")
    home_form = input("主队近况 (如: WWDLWW, 直接回车跳过): ").strip().upper()
    away_form = input("客队近况 (如: LLDWDL, 直接回车跳过): ").strip().upper()
    
    print()
    print("【首回合结果 (淘汰赛必填)】")
    first_leg = input("首回合结果 (如: 0-3惨败/1-1平/2-0胜, 直接回车跳过): ").strip()
    
    # 构建数据
    match_data = {
        'home_team': home,
        'away_team': away,
        'league': league,
        'confidence': confidence,
        'confidence_option': conf_option,
        'form_diff': form_diff,
        'home_8': home_8,
        'draw_8': draw_8,
        'away_8': away_8,
    }
    
    if home_form:
        match_data['home_form'] = home_form
    if away_form:
        match_data['away_form'] = away_form
    if first_leg:
        match_data['first_leg_result'] = first_leg
    
    print()
    print("="*70)
    print("分析结果")
    print("="*70)
    
    # 执行分析
    result = analyzer.analyze_moderate_distribution(match_data, verbose=True)
    
    print()
    print("="*70)
    print("预测结论")
    print("="*70)
    print(f"推荐: {result['prediction']}")
    print(f"方法: {result['method']}")
    print(f"理由: {result['reason']}")
    print("="*70)


def quick_analysis():
    """快速分析示例"""
    print("="*70)
    print("V5 综合事件分析框架 - 快速示例")
    print("="*70)
    print()
    
    analyzer = ComprehensiveEventAnalyzer()
    
    # 示例：里斯本 vs 博德闪耀
    print("示例：里斯本 vs 博德闪耀（欧冠次回合）")
    print("-"*70)
    
    match_data = {
        'home_team': '里斯本',
        'away_team': '博德闪耀',
        'league': '欧冠',
        'confidence': 59,
        'confidence_option': '主胜',
        'form_diff': -30,
        'home_8': -2,
        'draw_8': 2,
        'away_8': 1,
        'home_form': 'WDWDLW',
        'away_form': 'WWWDWW',
        'first_leg_result': '0-3惨败',
    }
    
    result = analyzer.analyze_moderate_distribution(match_data, verbose=True)
    
    print()
    print("="*70)
    print("预测结论")
    print("="*70)
    print(f"推荐: {result['prediction']}")
    print(f"方法: {result['method']}")
    print(f"理由: {result['reason']}")
    print(f"实际结果: 主胜 3-0 [正确]")
    print("="*70)


def main():
    """主函数"""
    print()
    print("="*70)
    print("V5 综合事件分析框架")
    print("="*70)
    print()
    print("1. 交互式分析（输入比赛数据）")
    print("2. 快速示例（查看里斯本vs博德闪耀案例）")
    print("3. 退出")
    print()
    
    choice = input("请选择 (1/2/3): ").strip()
    
    if choice == '1':
        interactive_analysis()
    elif choice == '2':
        quick_analysis()
    else:
        print("再见！")


if __name__ == "__main__":
    main()
