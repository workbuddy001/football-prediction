#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V7+8分段分析脚本 V2 - 扩展版
新增：近期关键事件分析框架
核心逻辑：赔率变化应该符合近期关键事件的市场反应
"""

import os
import re
import sys
import json
from datetime import datetime

# ========== 近期关键事件分析框架 ==========

class RecentEventAnalyzer:
    """
    近期关键事件分析器
    分析近期比赛结果、交锋记录等对赔率的影响
    """
    
    def __init__(self):
        # 定义关键事件类型及其对赔率的影响权重
        self.event_weights = {
            '首回合惨败': -0.3,      # 客场惨败，市场信心大降
            '首回合不胜': -0.2,      # 客场平或负
            '首回合小胜': 0.1,       # 客场小胜
            '首回合大胜': 0.2,       # 客场大胜
            '近期连败': -0.25,       # 最近2-3场连败
            '近期连胜': 0.25,        # 最近2-3场连胜
            '交锋劣势': -0.15,       # 近期交锋不占优
            '交锋优势': 0.15,        # 近期交锋占优
            '核心伤停': -0.2,        # 关键球员缺阵
            '主场龙': 0.15,          # 主场战绩极好
            '客场虫': -0.15,         # 客场战绩极差
        }
    
    def analyze_events(self, events):
        """
        分析一系列近期事件，计算市场预期调整值
        
        参数:
            events: 事件列表，如 ['首回合惨败', '近期连败', '核心伤停']
        
        返回:
            adjustment: 市场预期调整值 (-1.0 到 1.0)
            explanation: 解释说明
        """
        if not events:
            return 0, "无特殊事件"
        
        total_adjustment = 0
        event_details = []
        
        for event in events:
            weight = self.event_weights.get(event, 0)
            total_adjustment += weight
            event_details.append(f"{event}({weight:+.2f})")
        
        # 限制调整值范围
        total_adjustment = max(-1.0, min(1.0, total_adjustment))
        
        explanation = " + ".join(event_details) + f" = {total_adjustment:+.2f}"
        
        return total_adjustment, explanation
    
    def interpret_moderate_distribution(self, events, form_diff, confidence, home_8, draw_8, away_8):
        """
        解读中庸分布的含义
        
        核心逻辑：
        - 如果近期有负面事件 → 市场信心下降 → 中庸分布合理 → 可能是真实看好反弹
        - 如果近期无负面事件 → 市场信心正常 → 中庸分布异常 → 可能是诱盘
        
        返回:
            (是否陷阱, 推荐预测, 理由)
        """
        adjustment, explanation = self.analyze_events(events)
        
        # 判断是否为中庸分布
        is_moderate = abs(home_8) <= 2 and abs(draw_8) <= 2 and abs(away_8) <= 2
        if not is_moderate:
            return False, None, ""
        
        # === 保护规则 ===
        if confidence >= 70:
            return False, None, f"强队保护(置信度{confidence}%)"
        
        if abs(form_diff) >= 40:
            return False, None, f"状态极好保护({form_diff}%)"
        
        # === 关键判断：近期事件 vs 中庸分布 ===
        
        # 情况1：有明显负面事件 + 中庸分布 = 真实看好反弹，不是陷阱
        if adjustment <= -0.3:
            # 负面事件较多，市场信心已下降，中庸分布是合理的
            if form_diff >= 30 and draw_8 >= 3:
                # 即使状态好，但有负面事件，中庸分布可以理解
                return False, None, f"负面事件调整({adjustment:+.2f})，中庸分布合理"
        
        # 情况2：无明显负面事件 + 中庸分布 = 可能是诱盘
        if adjustment >= -0.1:
            # 市场信心正常，但8变化中庸，与状态不匹配
            if form_diff >= 30 and draw_8 >= 4:
                return True, "平局", f"状态好({form_diff}%)但中庸分布+无负面事件，可能诱盘"
            if form_diff >= 20 and draw_8 >= 5:
                return True, "平局", f"状态较好({form_diff}%)但中庸分布+无负面事件，可能诱盘"
        
        return False, None, ""


# ========== 示例：如何使用新框架 ==========

def example_usage():
    """
    示例：如何使用近期关键事件分析框架
    """
    analyzer = RecentEventAnalyzer()
    
    # 示例1：里斯本 vs 博德闪耀（欧冠次回合）
    events_1 = ['首回合惨败']  # 首回合客场0-3惨败
    adj_1, exp_1 = analyzer.analyze_events(events_1)
    print(f"里斯本案例: {exp_1}")
    # 结果：首回合惨败(-0.30) = -0.30
    
    is_trap_1, pred_1, reason_1 = analyzer.interpret_moderate_distribution(
        events=events_1,
        form_diff=-30,  # 状态差
        confidence=59,   # 置信度
        home_8=-2, draw_8=2, away_8=1  # 中庸分布
    )
    print(f"是否陷阱: {is_trap_1}, 预测: {pred_1}, 理由: {reason_1}")
    # 预期：不是陷阱，因为首回合惨败已经调整了市场预期
    
    print("\n" + "="*50 + "\n")
    
    # 示例2：某联赛比赛，无特殊事件
    events_2 = []  # 无特殊事件
    adj_2, exp_2 = analyzer.analyze_events(events_2)
    print(f"联赛案例: {exp_2}")
    
    is_trap_2, pred_2, reason_2 = analyzer.interpret_moderate_distribution(
        events=events_2,
        form_diff=35,   # 主队状态好
        confidence=65,  # 中等置信度
        home_8=1, draw_8=4, away_8=-1  # 中庸分布+平局8变化大
    )
    print(f"是否陷阱: {is_trap_2}, 预测: {pred_2}, 理由: {reason_2}")
    # 预期：可能是陷阱，因为状态好但中庸分布，且无负面事件解释


if __name__ == "__main__":
    print("="*60)
    print("近期关键事件分析框架 V2")
    print("="*60)
    print()
    
    example_usage()
    
    print()
    print("="*60)
    print("框架说明：")
    print("="*60)
    print("""
核心逻辑：赔率变化应该符合近期关键事件的市场反应

使用步骤：
1. 收集近期关键事件（首回合结果、近期战绩、交锋记录等）
2. 使用 RecentEventAnalyzer 分析事件影响
3. 结合中庸分布判断是否为陷阱

关键洞察：
- 有负面事件 + 中庸分布 = 市场预期已调整，不是陷阱
- 无负面事件 + 中庸分布 = 市场预期未调整，可能是陷阱

下一步：
将此框架整合到主分析脚本中，自动提取比赛的关键事件
    """)
