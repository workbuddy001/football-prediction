#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V7+8分析脚本 V3 - 完整版近期关键事件框架
包含：近期战绩、交锋记录、首回合结果、伤停信息、主客场因素
"""

import os
import re
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入原脚本的核心函数
from v7_8_segment_analyze import (
    calculate_v7_from_odds, calculate_8_change, parse_form_win_rate,
    parse_source_file, get_expected_confidence_range,
    is_moderate_distribution
)


class ComprehensiveEventAnalyzer:
    """
    综合近期关键事件分析器
    包含：近期战绩、交锋记录、首回合结果、伤停信息、主客场因素
    """
    
    def __init__(self):
        # 事件权重体系（可根据验证结果调整）
        self.event_weights = {
            # ===== 首回合结果（淘汰赛）=====
            '首回合惨败': -0.40,      # 客场惨败3球以上
            '首回合大败': -0.30,      # 客场输2球
            '首回合失利': -0.25,      # 客场输1球
            '首回合不胜': -0.15,      # 客场平
            '首回合小胜': 0.10,       # 客场赢1球
            '首回合中胜': 0.20,       # 客场赢2球
            '首回合大胜': 0.35,       # 客场赢3球以上
            
            # ===== 近期战绩（最近3-5场）=====
            '近期3连败': -0.30,
            '近期2连败': -0.20,
            '近期3连胜': 0.30,
            '近期2连胜': 0.20,
            '近期5场不胜': -0.25,
            '近期5场不败': 0.25,
            '客队近期3连败': 0.30,      # 客队连败有利于主队
            '客队近期2连败': 0.20,
            '客队近期3连胜': -0.30,     # 客队连胜不利于主队
            '客队近期2连胜': -0.20,
            
            # ===== 交锋记录（最近3-5次）=====
            '交锋3连败': -0.25,
            '交锋2连败': -0.15,
            '交锋3连胜': 0.25,
            '交锋2连胜': 0.15,
            '交锋劣势明显': -0.20,
            '交锋优势明显': 0.20,
            
            # ===== 伤停信息 =====
            '核心伤停': -0.25,        # 主力射手/核心中场缺阵
            '多主力伤停': -0.35,      # 3+主力缺阵
            '防线伤停': -0.20,        # 后防核心缺阵
            '对手核心伤停': 0.20,     # 对方核心缺阵
            
            # ===== 主客场因素 =====
            '主场龙': 0.15,           # 主场战绩极好
            '主场虫': -0.15,          # 主场战绩极差
            '客场龙': 0.15,           # 客场战绩极好
            '客场虫': -0.15,          # 客场战绩极差
            
            # ===== 战意/赛程因素 =====
            '保级压力大': 0.15,       # 保级队主场
            '争冠关键战': 0.10,       # 争冠球队
            '多线作战疲劳': -0.15,    # 一周双赛
        }
    
    def extract_events_from_data(self, match_data):
        """
        从比赛数据中提取近期关键事件
        
        参数:
            match_data: 包含比赛信息的字典
        
        返回:
            events: 事件列表
            details: 事件详情说明
        """
        events = []
        details = []
        
        # 1. 提取近期战绩事件
        recent_events = self._extract_recent_form_events(match_data)
        events.extend(recent_events)
        if recent_events:
            details.append(f"近期战绩: {recent_events}")
        
        # 2. 提取交锋记录事件
        h2h_events = self._extract_h2h_events(match_data)
        events.extend(h2h_events)
        if h2h_events:
            details.append(f"交锋记录: {h2h_events}")
        
        # 3. 提取首回合结果（淘汰赛）
        first_leg_events = self._extract_first_leg_events(match_data)
        events.extend(first_leg_events)
        if first_leg_events:
            details.append(f"首回合: {first_leg_events}")
        
        # 4. 提取伤停信息（如果有）
        injury_events = self._extract_injury_events(match_data)
        events.extend(injury_events)
        if injury_events:
            details.append(f"伤停: {injury_events}")
        
        # 5. 提取主客场因素
        venue_events = self._extract_venue_events(match_data)
        events.extend(venue_events)
        if venue_events:
            details.append(f"主客场: {venue_events}")
        
        return events, details
    
    def _extract_recent_form_events(self, match_data):
        """提取近期战绩事件"""
        events = []
        
        # 从主队近况走势提取
        home_form = str(match_data.get('home_form', '')).upper()
        away_form = str(match_data.get('away_form', '')).upper()
        
        # 分析主队近期战绩
        if home_form:
            recent = home_form[-5:] if len(home_form) >= 5 else home_form  # 最近5场
            wins = recent.count('W')
            losses = recent.count('L')
            draws = recent.count('D')
            
            # 检查连败/连胜（最近的连续结果）
            if len(home_form) >= 3:
                last3 = home_form[-3:]
                if last3 == 'LLL':
                    events.append('近期3连败')
                elif last3 == 'WWW':
                    events.append('近期3连胜')
            
            if len(home_form) >= 2:
                last2 = home_form[-2:]
                if last2 == 'LL' and '近期3连败' not in events:
                    events.append('近期2连败')
                elif last2 == 'WW' and '近期3连胜' not in events:
                    events.append('近期2连胜')
            
            # 5场不胜/不败
            if len(recent) >= 5:
                if wins == 0 or wins + draws <= 1:
                    events.append('近期5场不胜')
                elif losses == 0 or losses + draws <= 1:
                    events.append('近期5场不败')
        
        # 分析客队近期战绩
        if away_form:
            recent = away_form[-5:] if len(away_form) >= 5 else away_form
            wins = recent.count('W')
            losses = recent.count('L')
            draws = recent.count('D')
            
            # 检查连败/连胜
            if len(away_form) >= 3:
                last3 = away_form[-3:]
                if last3 == 'LLL':
                    events.append('客队近期3连败')
                elif last3 == 'WWW':
                    events.append('客队近期3连胜')
            
            if len(away_form) >= 2:
                last2 = away_form[-2:]
                if last2 == 'LL' and '客队近期3连败' not in events:
                    events.append('客队近期2连败')
                elif last2 == 'WW' and '客队近期3连胜' not in events:
                    events.append('客队近期2连胜')
        
        return events
    
    def _extract_h2h_events(self, match_data):
        """提取交锋记录事件"""
        events = []
        h2h = match_data.get('h2h_record', '')
        
        if h2h:
            # 解析历史交锋字符串，如 "主队 2胜4和4负"
            # 这里简化处理，实际可以解析更详细
            pass
        
        return events
    
    def _extract_first_leg_events(self, match_data):
        """提取首回合结果事件"""
        events = []
        first_leg = match_data.get('first_leg_result', '')
        
        if first_leg:
            # 解析首回合结果，如 "0-3负", "1-1平", "2-0胜"
            if '惨败' in first_leg or any(score in first_leg for score in ['0-3', '0-4', '1-4']):
                events.append('首回合惨败')
            elif '大败' in first_leg or any(score in first_leg for score in ['0-2', '1-3']):
                events.append('首回合大败')
            elif '失利' in first_leg or '负' in first_leg:
                events.append('首回合失利')
            elif '平' in first_leg:
                events.append('首回合不胜')
            elif '大胜' in first_leg or any(score in first_leg for score in ['3-0', '4-0', '4-1']):
                events.append('首回合大胜')
            elif '胜' in first_leg:
                events.append('首回合小胜')
        
        return events
    
    def _extract_injury_events(self, match_data):
        """提取伤停信息事件"""
        events = []
        injuries = match_data.get('injuries', [])
        
        if injuries:
            core_injured = sum(1 for i in injuries if i.get('is_core', False))
            if core_injured >= 1:
                events.append('核心伤停')
            if len(injuries) >= 3:
                events.append('多主力伤停')
        
        return events
    
    def _extract_venue_events(self, match_data):
        """提取主客场因素事件（基于盘路走势）"""
        events = []
        
        # 从盘路走势提取主客场因素
        home_handicap = str(match_data.get('home_handicap', '')).upper()
        away_handicap = str(match_data.get('away_handicap', '')).upper()
        
        # 分析主队盘路（主场）
        if home_handicap:
            recent = home_handicap[-5:] if len(home_handicap) >= 5 else home_handicap
            wins = recent.count('W')
            losses = recent.count('L')
            
            # 主场龙：盘路好（赢多输少）
            if wins >= 4 or (wins >= 3 and losses <= 1):
                events.append('主场龙')
            # 主场虫：盘路差（输多赢少）
            elif losses >= 4 or (losses >= 3 and wins <= 1):
                events.append('主场虫')
        
        # 分析客队盘路（客场）
        if away_handicap:
            recent = away_handicap[-5:] if len(away_handicap) >= 5 else away_handicap
            wins = recent.count('W')
            losses = recent.count('L')
            
            # 客场龙：盘路好
            if wins >= 4 or (wins >= 3 and losses <= 1):
                events.append('客场龙')
            # 客场虫：盘路差
            elif losses >= 4 or (losses >= 3 and wins <= 1):
                events.append('客场虫')
        
        return events
    
    def calculate_adjustment(self, events, match_data=None):
        """
        计算事件调整值（不包含主客场因素）
        
        参数:
            events: 事件列表
            match_data: 比赛数据
        
        返回:
            adjustment: 事件调整值
            breakdown: 详细分解
        """
        total = 0
        breakdown_parts = []
        
        # 区分主客场事件和其他事件
        venue_events = ['主场龙', '主场虫', '客场龙', '客场虫']
        regular_events = [e for e in events if e not in venue_events]
        venue_events_found = [e for e in events if e in venue_events]
        
        # 客队不利事件（如连败）需要额外考虑客场因素
        away_negative_events = ['客队近期3连败', '客队近期2连败', '首回合惨败', '首回合大败', '首回合失利']
        # 客队有利事件（如连胜）客场会削弱其优势
        away_positive_events = ['客队近期3连胜', '客队近期2连胜', '首回合大胜', '首回合中胜', '首回合小胜']
        
        # 计算普通事件的调整值
        for event in regular_events:
            weight = self.event_weights.get(event, 0)
            
            # 客场放大器：客队的不利事件在客场会放大
            if match_data and event in away_negative_events:
                weight -= 0.10  # 客场额外不利
                breakdown_parts.append(f"{event}({weight:+.2f})")
            # 客场削弱器：客队的利好事件在客场会削弱
            elif match_data and event in away_positive_events:
                weight -= 0.10  # 客场削弱优势
                breakdown_parts.append(f"{event}({weight:+.2f})")
            else:
                breakdown_parts.append(f"{event}({weight:+.2f})")
            
            total += weight
        
        if not breakdown_parts:
            breakdown_parts = ["无特殊事件"]
        
        # 限制范围
        total = max(-1.0, min(1.0, total))
        
        breakdown = " + ".join(breakdown_parts) + f" = {total:+.2f}"
        
        # 返回：事件调整值 + 主客场事件列表
        return total, breakdown, venue_events_found
    
    def calculate_venue_correction(self, venue_events, match_data):
        """
        计算主客场修正值（作为最后修正项）
        
        参数:
            venue_events: 已识别的主客场事件
            match_data: 比赛数据
        
        返回:
            correction: 修正值
            venue_breakdown: 主客场分解
        """
        correction = 0
        venue_parts = []
        
        # 如果已有主场龙/虫或客场龙/虫事件
        for event in venue_events:
            weight = self.event_weights.get(event, 0)
            correction += weight
            venue_parts.append(f"{event}({weight:+.2f})")
        
        # 如果没有识别出主客场事件，才从胜率推断
        if not venue_events and match_data:
            home_win_rate = match_data.get('home_win_rate', 0)
            away_win_rate = match_data.get('away_win_rate', 0)
            
            # 主队胜率高
            if home_win_rate and home_win_rate >= 70:
                correction += 0.10
                venue_parts.append(f"主场强(+0.10)")
            elif home_win_rate and home_win_rate <= 40:
                correction -= 0.10
                venue_parts.append(f"主场弱(-0.10)")
            
            # 客队胜率低（客场劣势）
            if away_win_rate and away_win_rate < 50:
                correction -= 0.10
                venue_parts.append(f"客场弱(-0.10)")
        
        if not venue_parts:
            return 0, ""
        
        venue_breakdown = " + ".join(venue_parts) + f" = {correction:+.2f}"
        
        return correction, venue_breakdown
    
    def analyze_moderate_distribution(self, match_data, verbose=False):
        """
        分析中庸分布的含义
        
        参数:
            match_data: 比赛数据
            verbose: 是否打印详细信息
        
        返回:
            result: 分析结果字典
        """
        # 提取基础数据
        conf = match_data.get('confidence', 0)
        conf_option = match_data.get('confidence_option', '未知')
        form_diff = match_data.get('form_diff', 0) or 0
        home_8 = match_data.get('home_8', 0)
        draw_8 = match_data.get('draw_8', 0)
        away_8 = match_data.get('away_8', 0)
        
        # 提取近期事件
        events, event_details = self.extract_events_from_data(match_data)
        
        # 计算事件调整值（不含主客场）
        adjustment, breakdown, venue_events = self.calculate_adjustment(events, match_data)
        
        # 计算主客场修正值（作为最后修正项）
        venue_correction, venue_breakdown = self.calculate_venue_correction(venue_events, match_data)
        
        # 判断是否为中庸分布
        is_moderate, mod_type = is_moderate_distribution(home_8, draw_8, away_8)
        
        # 构建结果
        result = {
            'match': f"{match_data.get('home_team', '未知')} vs {match_data.get('away_team', '未知')}",
            'confidence': conf,
            'confidence_option': conf_option,
            'form_diff': form_diff,
            'eight_change': f"[{home_8:+d}{match_data.get('home_change', '')},{draw_8:+d}{match_data.get('draw_change', '')},{away_8:+d}{match_data.get('away_change', '')}]",
            'is_moderate': is_moderate,
            'moderate_type': mod_type,
            'events': events,
            'event_details': event_details,
            'adjustment': adjustment,           # 事件调整值
            'adjustment_breakdown': breakdown, # 事件分解
            'venue_correction': venue_correction,   # 主客场修正值
            'venue_breakdown': venue_breakdown,   # 主客场分解
        }
        
        # 判断预测
        if not is_moderate:
            result['prediction'] = conf_option
            result['method'] = '实盘'
            result['reason'] = '非中庸分布'
            result['is_trap'] = False
        else:
            # 中庸分布，进行深度分析
            prediction, method, reason, is_trap = self._judge_moderate_case(
                conf, conf_option, form_diff, adjustment, 
                home_8, draw_8, away_8, events
            )
            result['prediction'] = prediction
            result['method'] = method
            result['reason'] = reason
            result['is_trap'] = is_trap
        
        if verbose:
            self._print_analysis(result)
        
        return result
    
    def _judge_moderate_case(self, conf, conf_option, form_diff, adjustment,
                              home_8, draw_8, away_8, events):
        """
        判断中庸分布情况下的预测
        
        返回: (prediction, method, reason, is_trap)
        """
        # === 保护规则1：高置信度强队 ===
        if conf >= 70:
            return conf_option, '实盘', f'强队保护(置信度{conf}%)', False
        
        # === 保护规则2：状态极好 ===
        if abs(form_diff) >= 40:
            return conf_option, '实盘', f'状态极好保护({form_diff}%)', False
        
        # === 核心判断：市场预期是否已调整 ===
        
        # 情况A：有明显负面事件，市场预期已调整
        if adjustment <= -0.25:
            reason = f"市场预期已调整({adjustment:+.2f})，中庸分布合理"
            return conf_option, '实盘', reason, False
        
        # 情况B：有明显正面事件，市场预期已提升
        if adjustment >= 0.25:
            # 市场预期已经很高，如果还开中庸，可能是诱盘
            if form_diff >= 30 and draw_8 >= 3:
                return '平局', '中庸陷阱', f'市场预期已提升({adjustment:+.2f})但中庸+平8大，可能诱平', True
        
        # 情况C：市场预期正常，但中庸分布与状态不匹配
        if -0.25 < adjustment < 0.25:
            # 主队状态好，但中庸分布
            if form_diff >= 30:
                if draw_8 >= 4:
                    return '平局', '中庸陷阱', f'状态好({form_diff}%)但中庸+平8({draw_8})大+无负面事件', True
                elif draw_8 >= 2:
                    return '平局', '中庸陷阱-弱', f'状态好({form_diff}%)但中庸+平8({draw_8})，谨慎防平', True
            
            # 客队状态好，但中庸分布
            if form_diff <= -30:
                if draw_8 >= 4:
                    return '平局', '中庸陷阱', f'客状态好({form_diff}%)但中庸+平8({draw_8})大+无负面事件', True
        
        # 默认跟随实盘
        return conf_option, '实盘', '跟随实盘', False
    
    def _print_analysis(self, result):
        """打印分析结果"""
        print(f"\n{'='*70}")
        print(f"比赛: {result['match']}")
        print(f"{'='*70}")
        print(f"置信度: {result['confidence']}% ({result['confidence_option']})")
        print(f"状态差: {result['form_diff']:+d}%")
        print(f"8变化: {result['eight_change']}")
        if result['is_moderate']:
            print(f"分布类型: {result['moderate_type']}")
        print(f"{'-'*70}")
        print(f"近期事件: {result['events'] if result['events'] else '无'}")
        for detail in result['event_details']:
            print(f"  - {detail}")
        print(f"事件调整: {result['adjustment_breakdown']}")
        print(f"{'-'*70}")
        print(f"预测结果: {result['prediction']}")
        print(f"判断方法: {result['method']}")
        print(f"理由: {result['reason']}")
        print(f"{'='*70}")


def demo_comprehensive_analysis():
    """
    演示综合事件分析
    """
    print("="*80)
    print("V3 综合事件分析框架 - 演示")
    print("="*80)
    
    analyzer = ComprehensiveEventAnalyzer()
    
    # 案例1：里斯本 vs 博德闪耀（欧冠次回合）
    print("\n【案例1】里斯本 vs 博德闪耀（欧冠次回合）")
    match1 = {
        'home_team': '里斯本',
        'away_team': '博德闪耀',
        'league': '欧冠',
        'confidence': 59,
        'confidence_option': '主胜',
        'form_diff': -30,
        'home_8': -2, 'draw_8': 2, 'away_8': 1,
        'first_leg_result': '0-3惨败',
    }
    result1 = analyzer.analyze_moderate_distribution(match1, verbose=True)
    print(f"实际结果: 主胜 3-0 [正确]")
    
    # 案例2：假设的联赛比赛（近期连败+中庸分布）
    print("\n【案例2】某队 vs 对手（联赛，近期连败）")
    match2 = {
        'home_team': '状态差队',
        'away_team': '对手',
        'league': '英超',
        'confidence': 55,
        'confidence_option': '客胜',
        'form_diff': -35,
        'home_8': 1, 'draw_8': 3, 'away_8': -1,
        'home_form': 'LLLDL',  # 近期连败
    }
    result2 = analyzer.analyze_moderate_distribution(match2, verbose=True)
    print(f"分析: 近期连败导致市场预期已调整，中庸分布合理")
    
    # 案例3：无特殊事件+中庸分布
    print("\n【案例3】强队 vs 弱队（联赛，无特殊事件）")
    match3 = {
        'home_team': '强队',
        'away_team': '弱队',
        'league': '西甲',
        'confidence': 65,
        'confidence_option': '主胜',
        'form_diff': 35,
        'home_8': 0, 'draw_8': 4, 'away_8': 0,
        'home_form': 'WWDWD',  # 正常战绩
    }
    result3 = analyzer.analyze_moderate_distribution(match3, verbose=True)
    print(f"分析: 无负面事件+状态好+中庸分布+平8大 = 可能诱盘")


def analyze_directory_with_events(dir_path):
    """分析目录中的所有源数据文件，使用V3事件框架"""
    from pathlib import Path
    
    analyzer = ComprehensiveEventAnalyzer()
    results = []
    
    # 查找所有源数据文件
    source_files = list(Path(dir_path).glob('*_源数据.md'))
    if not source_files:
        source_files = list(Path(dir_path).glob('*_vs_*_源数据.md'))
    source_files.sort()
    
    print(f"找到 {len(source_files)} 个文件")
    
    for filepath in source_files:
        data = parse_source_file(filepath)
        if not data:
            print(f"  跳过: {filepath.name} (无法解析)")
            continue
        
        # 调试：打印解析结果
        # print(f"  解析: {data.get('home_team')} vs {data.get('away_team')}")
        
        # 构建V3分析所需的数据
        match_data = {
            'home_team': data.get('home_team', '未知'),
            'away_team': data.get('away_team', '未知'),
            'league': data.get('league', ''),
            'confidence': data['v7']['confidence'],
            'confidence_option': data['v7'].get('confidence_option', '主胜'),
            'form_diff': data.get('form_diff', 0) or 0,
            'home_8': data['eight_change']['home_8'],
            'draw_8': data['eight_change']['draw_8'],
            'away_8': data['eight_change']['away_8'],
            'home_change': data['eight_change'].get('home_change', ''),  # 赔率升降
            'draw_change': data['eight_change'].get('draw_change', ''),
            'away_change': data['eight_change'].get('away_change', ''),
            'home_form': data.get('home_form', ''),      # 主队近况走势
            'away_form': data.get('away_form', ''),      # 客队近况走势
            'home_handicap': data.get('home_handicap', ''),  # 主队盘路走势
            'away_handicap': data.get('away_handicap', ''),  # 客队盘路走势
            'macao_tip': data.get('macao_tip', ''),      # 澳门心水
            'home_win_rate': data.get('home_win_rate'),  # 主队胜率
            'away_win_rate': data.get('away_win_rate'),  # 客队胜率
        }
        
        # 使用V3框架分析
        result = analyzer.analyze_moderate_distribution(match_data)
        result['date_num'] = data.get('date_num', filepath.stem[:6])
        result['filename'] = data.get('filename', filepath.name)
        
        results.append(result)
    
    return results


def print_v3_results(results):
    """打印V3分析结果"""
    print("\n" + "="*140)
    print("V5 综合事件分析框架 预测结果")
    print("="*140)
    
    print("\n详细预测:")
    print("-"*140)
    print(f"{'日期':<8} {'对阵':<30} {'联赛':<8} {'置信度':>8} {'推荐':>4} {'状态差':>7} {'8变化':>16} {'事件':<20} {'调整':>12} {'预测':>6} {'方法':<10}")
    print("-"*140)
    
    for r in results:
        # 容错处理 - 支持多种字段名
        match = r.get('match', r.get('home_team', '未知') + ' vs ' + r.get('away_team', '未知'))
        conf = r.get('confidence', 0)
        conf_opt = r.get('confidence_option', '')
        form_diff = r.get('form_diff', 0)
        eight_chg = r.get('eight_change', '[--,--,--]')
        adj = r.get('adjustment', 0)
        pred = r.get('prediction', '')
        method = r.get('method', '')
        date = r.get('date_num', 'N/A')
        league = r.get('league', '')
        
        # 分别显示事件和主客场修正
        events_list = r.get('events', [])
        venue_correction = r.get('venue_correction', 0)
        
        # 过滤掉主场龙/虫/客场龙/虫，只显示普通事件
        venue_events = ['主场龙', '主场虫', '客场龙', '客场虫']
        regular_events = [e for e in events_list if e not in venue_events]
        
        events_str = ', '.join(regular_events[:2]) if regular_events else '-'
        if len(events_str) > 16:
            events_str = events_str[:13] + '...'
        
        # 如果有主客场修正，显示在调整值后面
        if venue_correction != 0:
            adj_str = f"{adj:+.2f}({venue_correction:+.2f})"
        else:
            adj_str = f"{adj:+.2f}"
        
        print(f"{date:<8} {match:<30} {league:<8} "
              f"{conf:>6}% {conf_opt:>4} "
              f"{form_diff:>+6}% "
              f"{str(eight_chg):>16} "
              f"{events_str:<20} "
              f"{adj_str:<12} "
              f"{pred:>6} {method:<10}")


def main():
    """主函数 - 支持命令行参数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='V5 综合事件分析框架')
    parser.add_argument('directory', nargs='?', default='.', help='源数据目录 (默认当前目录)')
    parser.add_argument('-o', '--output', help='输出结果到JSON文件')
    parser.add_argument('--demo', action='store_true', help='运行演示模式')
    
    args = parser.parse_args()
    
    if args.demo:
        demo_comprehensive_analysis()
        return
    
    # 解析目录
    dir_path = args.directory
    if not os.path.isdir(dir_path):
        dir_path = os.path.join(os.path.dirname(__file__), dir_path)
    
    if not os.path.isdir(dir_path):
        print(f"错误: 目录不存在 {dir_path}")
        print(f"使用演示模式: python v7_8_segment_analyze_v3.py --demo")
        return
    
    print(f"分析目录: {dir_path}")
    print(f"使用V5综合事件分析框架")
    
    # 分析
    results = analyze_directory_with_events(dir_path)
    
    # 打印结果
    print_v3_results(results)
    
    # 保存结果
    if args.output:
        output_data = []
        for r in results:
            output_data.append({
                'date_num': r.get('date_num', ''),
                'match': r['match'],
                'league': r['league'],
                'confidence': r['confidence'],
                'confidence_option': r['confidence_option'],
                'form_diff': r['form_diff'],
                'eight_change': r['eight_change'],
                'events': r['events'],
                'adjustment': r['adjustment'],
                'prediction': r['prediction'],
                'method': r['method'],
                'reason': r['reason'],
                'is_trap': r['is_trap'],
            })
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {args.output}")


if __name__ == "__main__":
    main()
