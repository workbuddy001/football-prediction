#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动事件提取器
从现有的比赛数据文件中自动提取近期关键事件
"""

import os
import re
import sys
import json
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from v7_8_segment_analyze_v3 import ComprehensiveEventAnalyzer


class AutoEventExtractor:
    """
    自动从比赛数据文件中提取关键事件
    """
    
    def __init__(self):
        self.analyzer = ComprehensiveEventAnalyzer()
    
    def extract_from_file(self, filepath):
        """
        从单个比赛数据文件中提取事件
        
        参数:
            filepath: 比赛数据文件路径
        
        返回:
            match_data: 包含提取事件的完整比赛数据
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"读取文件失败 {filepath}: {e}")
            return None
        
        # 提取基本信息
        filename = os.path.basename(filepath)
        match_info = self._parse_filename(filename)
        
        # 提取近期战绩
        home_form, away_form = self._extract_form_from_content(content)
        
        # 提取交锋记录
        h2h_record = self._extract_h2h_from_content(content)
        
        # 提取赛事类型（判断是否淘汰赛）
        league = self._extract_league_from_content(content)
        
        # 提取赔率数据
        odds_data = self._extract_odds_from_content(content)
        
        # 构建完整数据
        match_data = {
            'filename': filename,
            'home_team': match_info.get('home', '未知'),
            'away_team': match_info.get('away', '未知'),
            'date_num': match_info.get('date_num', ''),
            'league': league,
            'home_form': home_form,
            'away_form': away_form,
            'h2h_record': h2h_record,
        }
        
        if odds_data:
            match_data.update(odds_data)
        
        # 自动提取事件
        events, details = self.analyzer.extract_events_from_data(match_data)
        match_data['auto_events'] = events
        match_data['event_details'] = details
        
        return match_data
    
    def _parse_filename(self, filename):
        """从文件名解析比赛信息"""
        # 格式: 3.14_周_六_013_霍芬海姆vs沃夫斯堡.py
        pattern = r'([\d.]+)_[^\d]*(\d+)_(.+?)vs(.+?)\.py'
        match = re.search(pattern, filename)
        
        if match:
            return {
                'date_num': match.group(1),
                'match_num': match.group(2),
                'home': match.group(3).strip(),
                'away': match.group(4).strip(),
            }
        
        return {'home': '未知', 'away': '未知', 'date_num': ''}
    
    def _extract_form_from_content(self, content):
        """从内容中提取近期战绩"""
        # 主队近况走势 | WWDLWW
        home_form = ''
        away_form = ''
        
        home_match = re.search(r'主队近况走势\s*\|\s*([WDLX]+)', content)
        if home_match:
            home_form = home_match.group(1).strip()
        
        away_match = re.search(r'客队近况走势\s*\|\s*([WDLX]+)', content)
        if away_match:
            away_form = away_match.group(1).strip()
        
        return home_form, away_form
    
    def _extract_h2h_from_content(self, content):
        """从内容中提取交锋记录"""
        # 历史交锋 | 主队 2胜4和4负
        h2h = ''
        match = re.search(r'历史交锋\s*\|\s*(.+?)(?:\n|$)', content)
        if match:
            h2h = match.group(1).strip()
        return h2h
    
    def _extract_league_from_content(self, content):
        """从内容中提取赛事类型"""
        league = ''
        match = re.search(r'赛事\s*\|\s*(.+?)(?:\n|$)', content)
        if match:
            league = match.group(1).strip()
        return league
    
    def _extract_odds_from_content(self, content):
        """从内容中提取赔率数据"""
        # 提取初盘和即时赔率
        init_odds = []
        real_odds = []
        
        # 查找初盘赔率
        init_section = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if init_section:
            odds_text = init_section.group(1)
            for line in odds_text.split('\n'):
                match = re.search(r'\((\d+\.?\d*),\s*(\d+\.?\d*),\s*(\d+\.?\d*)\)', line)
                if match:
                    init_odds.append((float(match.group(1)), float(match.group(2)), float(match.group(3))))
        
        # 查找即时赔率
        real_section = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if real_section:
            odds_text = real_section.group(1)
            for line in odds_text.split('\n'):
                match = re.search(r'\((\d+\.?\d*),\s*(\d+\.?\d*),\s*(\d+\.?\d*)\)', line)
                if match:
                    real_odds.append((float(match.group(1)), float(match.group(2)), float(match.group(3))))
        
        if init_odds and real_odds:
            # 计算V7数据
            from v7_8_segment_analyze import calculate_v7_from_odds, calculate_8_change
            
            v7_data = calculate_v7_from_odds(init_odds, real_odds)
            eight_change = calculate_8_change(init_odds, real_odds)
            
            if v7_data and eight_change:
                return {
                    'confidence': v7_data['confidence'],
                    'confidence_option': v7_data['confidence_option'],
                    'home_8': eight_change['home_8'],
                    'draw_8': eight_change['draw_8'],
                    'away_8': eight_change['away_8'],
                }
        
        return None
    
    def batch_extract(self, date_pattern='3.*', target_dir=None):
        """
        批量提取事件
        
        参数:
            date_pattern: 日期匹配模式，如 '3.14', '3.*'
            target_dir: 目标目录，默认为当前目录
        
        返回:
            results: 提取结果列表
        """
        if target_dir is None:
            target_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 查找匹配的文件
        pattern = os.path.join(target_dir, f'{date_pattern}_*.py')
        files = glob.glob(pattern)
        
        results = []
        print(f"找到 {len(files)} 个文件")
        
        for filepath in sorted(files):
            print(f"\n处理: {os.path.basename(filepath)}")
            match_data = self.extract_from_file(filepath)
            if match_data:
                results.append(match_data)
                self._print_extraction_result(match_data)
        
        return results
    
    def _print_extraction_result(self, match_data):
        """打印提取结果"""
        print(f"  比赛: {match_data['home_team']} vs {match_data['away_team']}")
        print(f"  赛事: {match_data['league']}")
        print(f"  主队近况: {match_data.get('home_form', 'N/A')}")
        print(f"  客队近况: {match_data.get('away_form', 'N/A')}")
        print(f"  自动提取事件: {match_data.get('auto_events', [])}")
        
        if 'confidence' in match_data:
            print(f"  置信度: {match_data['confidence']}%")
            print(f"  8变化: [{match_data.get('home_8', 0):+d},{match_data.get('draw_8', 0):+d},{match_data.get('away_8', 0):+d}]")


def demo_auto_extraction():
    """演示自动提取"""
    print("="*80)
    print("自动事件提取器 - 演示")
    print("="*80)
    
    extractor = AutoEventExtractor()
    
    # 演示从单个文件提取
    # 注意：这里需要一个示例文件路径
    print("\n功能说明:")
    print("1. 从比赛数据文件中自动提取近期战绩(WDL)")
    print("2. 自动提取交锋记录")
    print("3. 自动识别赛事类型")
    print("4. 自动计算赔率数据")
    print("5. 使用V3框架自动识别关键事件")
    
    print("\n使用方法:")
    print("  extractor = AutoEventExtractor()")
    print("  # 单个文件")
    print("  data = extractor.extract_from_file('3.14_xxx.py')")
    print("  # 批量处理")
    print("  results = extractor.batch_extract('3.14')")
    
    print("\n提取的事件类型:")
    print("  - 近期3连胜/连败")
    print("  - 近期5场不败/不胜")
    print("  - 交锋优势/劣势")
    print("  - 首回合结果（需手动输入或从数据库获取）")
    print("  - 主客场因素")


if __name__ == "__main__":
    demo_auto_extraction()
