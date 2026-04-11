#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V7+8分析脚本 - 近期关键事件整合版
核心逻辑：赔率变化应该符合近期关键事件的市场反应
"""

import os
import re
import sys
import json
from datetime import datetime

# 添加原脚本路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入原脚本的核心函数
from v7_8_segment_analyze import (
    calculate_v7_from_odds, calculate_8_change, parse_form_win_rate,
    parse_source_file, get_expected_confidence_range,
    is_moderate_distribution, check_moderate_state_mismatch
)


class RecentEventAnalyzer:
    """
    近期关键事件分析器
    """
    
    def __init__(self):
        self.event_weights = {
            '首回合惨败': -0.35,
            '首回合失利': -0.25,
            '首回合不胜': -0.20,
            '首回合小胜': 0.10,
            '首回合大胜': 0.25,
            '近期连败': -0.25,
            '近期连胜': 0.25,
            '交锋劣势': -0.15,
            '交锋优势': 0.15,
            '核心伤停': -0.20,
            '主场龙': 0.15,
            '客场虫': -0.15,
        }
    
    def analyze_events(self, events):
        """分析事件，返回调整值和解释"""
        if not events:
            return 0, "无特殊事件"
        
        total = sum(self.event_weights.get(e, 0) for e in events)
        total = max(-1.0, min(1.0, total))
        details = [f"{e}({self.event_weights.get(e, 0):+.2f})" for e in events]
        return total, " + ".join(details) + f" = {total:+.2f}"
    
    def should_trigger_trap(self, events, form_diff, confidence, home_8, draw_8, away_8):
        """
        判断是否应触发中庸陷阱
        
        核心逻辑：
        - 有明显负面事件 → 市场预期已调整 → 中庸分布合理 → 不触发
        - 无负面事件 → 市场预期未调整 → 中庸分布异常 → 可能触发
        """
        adjustment, _ = self.analyze_events(events)
        is_moderate, _ = is_moderate_distribution(home_8, draw_8, away_8)
        
        if not is_moderate:
            return False, None, ""
        
        # 保护规则
        if confidence >= 70:
            return False, None, f"强队保护({confidence}%)"
        if abs(form_diff) >= 40:
            return False, None, f"状态极好保护({form_diff}%)"
        
        # 关键判断
        if adjustment <= -0.25:
            # 负面事件多，市场预期已调整
            return False, None, f"市场预期已调整({adjustment:+.2f})，中庸合理"
        
        if adjustment >= -0.1:
            # 市场信心正常，但中庸分布与状态不匹配
            if 30 <= form_diff < 40 and draw_8 >= 4:
                return True, "平局", f"状态好({form_diff}%)但中庸+无负面事件，可能诱盘"
            if 20 <= form_diff < 30 and draw_8 >= 5:
                return True, "平局", f"状态较好({form_diff}%)但中庸+无负面事件，可能诱盘"
        
        return False, None, ""


def extract_recent_events(match_info):
    """
    从比赛信息中提取近期关键事件
    这是一个简化版本，实际应用中可以从更多数据源提取
    """
    events = []
    
    # 这里可以根据比赛信息自动判断
    # 例如：从赛事名称判断是否为淘汰赛
    league = match_info.get('league', '')
    
    # 欧冠/欧联淘汰赛次回合
    if any(x in league for x in ['欧冠', '欧联', '欧罗巴']):
        # 需要首回合结果来判断
        # 这里简化处理，实际应该从数据中提取
        pass
    
    return events


def analyze_match_with_events(match_data, manual_events=None):
    """
    使用近期关键事件分析比赛
    
    参数:
        match_data: 比赛数据字典
        manual_events: 手动指定的事件列表（用于测试）
    """
    analyzer = RecentEventAnalyzer()
    
    # 获取基础数据
    conf = match_data['v7']['confidence']
    conf_option = match_data['v7']['confidence_option']
    form_diff = match_data.get('form_diff', 0) or 0
    home_8 = match_data['eight_change']['home_8']
    draw_8 = match_data['eight_change']['draw_8']
    away_8 = match_data['eight_change']['away_8']
    
    # 获取近期事件
    if manual_events is not None:
        events = manual_events
    else:
        events = extract_recent_events(match_data)
    
    # 分析事件影响
    adjustment, event_explanation = analyzer.analyze_events(events)
    
    # 判断是否触发陷阱
    is_trap, trap_pred, trap_reason = analyzer.should_trigger_trap(
        events, form_diff, conf, home_8, draw_8, away_8
    )
    
    result = {
        'match': f"{match_data['home_team']} vs {match_data['away_team']}",
        'league': match_data['league'],
        'confidence': conf,
        'confidence_option': conf_option,
        'form_diff': form_diff,
        'eight_change': f"[{home_8:+d},{draw_8:+d},{away_8:+d}]",
        'events': events,
        'event_adjustment': adjustment,
        'event_explanation': event_explanation,
        'is_moderate_trap': is_trap,
    }
    
    if is_trap:
        result['prediction'] = trap_pred
        result['reason'] = trap_reason
        result['method'] = '中庸陷阱-' + trap_pred
    else:
        result['prediction'] = conf_option
        result['reason'] = trap_reason if trap_reason else f"跟随实盘({conf_option})"
        result['method'] = '实盘-' + conf_option
    
    return result


def print_analysis_result(result):
    """打印分析结果"""
    print(f"\n{'='*60}")
    print(f"比赛: {result['match']}")
    print(f"赛事: {result['league']}")
    print(f"{'='*60}")
    print(f"置信度: {result['confidence']}% ({result['confidence_option']})")
    print(f"状态差: {result['form_diff']:+d}%")
    print(f"8变化: {result['eight_change']}")
    print(f"{'-'*60}")
    print(f"近期事件: {result['events'] if result['events'] else '无'}")
    print(f"事件调整: {result['event_explanation']}")
    print(f"{'-'*60}")
    print(f"预测结果: {result['prediction']}")
    print(f"判断方法: {result['method']}")
    print(f"理由: {result['reason']}")
    print(f"{'='*60}")


def demo_analysis():
    """
    演示分析：使用历史比赛数据
    """
    print("\n" + "="*70)
    print("近期关键事件分析框架 - 演示")
    print("="*70)
    
    # 案例1：里斯本 vs 博德闪耀（欧冠次回合）
    print("\n【案例1】里斯本 vs 博德闪耀（欧冠次回合）")
    print("背景：首回合客场0-3惨败")
    
    match1 = {
        'home_team': '里斯本',
        'away_team': '博德闪耀',
        'league': '欧冠',
        'v7': {'confidence': 59, 'confidence_option': '主胜'},
        'form_diff': -30,
        'eight_change': {'home_8': -2, 'draw_8': 2, 'away_8': 1}
    }
    events1 = ['首回合惨败']
    result1 = analyze_match_with_events(match1, events1)
    print_analysis_result(result1)
    print(f"实际结果: 主胜 3-0 [正确]")
    
    # 案例2：阿森纳 vs 勒沃库森（欧冠次回合）
    print("\n【案例2】阿森纳 vs 勒沃库森（欧冠次回合）")
    print("背景：首回合客场1-1平")
    
    match2 = {
        'home_team': '阿森纳',
        'away_team': '勒沃库森',
        'league': '欧冠',
        'v7': {'confidence': 74, 'confidence_option': '主胜'},
        'form_diff': 40,
        'eight_change': {'home_8': 2, 'draw_8': 1, 'away_8': -1}
    }
    events2 = ['首回合不胜']
    result2 = analyze_match_with_events(match2, events2)
    print_analysis_result(result2)
    print(f"实际结果: 主胜 2-0 [正确]")
    
    # 案例3：假设的联赛比赛（无特殊事件）
    print("\n【案例3】某联赛比赛（无特殊事件）")
    print("背景：主队状态好，但中庸分布")
    
    match3 = {
        'home_team': '强队A',
        'away_team': '弱队B',
        'league': '英超',
        'v7': {'confidence': 65, 'confidence_option': '主胜'},
        'form_diff': 35,
        'eight_change': {'home_8': 1, 'draw_8': 4, 'away_8': -1}
    }
    events3 = []  # 无特殊事件
    result3 = analyze_match_with_events(match3, events3)
    print_analysis_result(result3)
    print(f"分析: 状态好但中庸分布，且无负面事件解释 → 可能诱盘，防平")


if __name__ == "__main__":
    demo_analysis()
    
    print("\n" + "="*70)
    print("框架说明")
    print("="*70)
    print("""
核心洞察：
1. 赔率变化应该符合近期关键事件的市场反应
2. 有负面事件 + 中庸分布 = 市场预期已调整，不是陷阱
3. 无负面事件 + 中庸分布 = 市场预期未调整，可能是陷阱

使用方式：
1. 手动指定近期事件（如首回合结果、近期战绩等）
2. 系统自动计算事件影响权重
3. 结合中庸分布判断是否触发陷阱

扩展方向：
- 自动提取近期战绩（连胜/连败）
- 自动提取交锋记录
- 自动提取伤停信息
- 结合赔率变化方向进一步细化
    """)
