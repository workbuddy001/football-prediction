"""
3球历史统计引擎
基于历史比赛数据查询相似赔率组合的3球打出率
"""

import json
import os
from collections import defaultdict

class StatsEngine:
    def __init__(self):
        self.scores_file = '分析模板/_scores.json'
        self.data = []
        
    def load(self):
        """加载比分记录"""
        if os.path.exists(self.scores_file):
            try:
                with open(self.scores_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                print(f"StatsEngine: 加载 {len(self.data)} 条历史记录")
            except Exception as e:
                print(f"StatsEngine: 加载失败 {e}")
                self.data = []
        else:
            print(f"StatsEngine: 比分文件不存在 {self.scores_file}")
            self.data = []
    
    def query_similar(self, g3=None, g0=None, g0_is_int=False, 
                     league_type='联赛正赛', jc_pattern='', macao_pattern='',
                     g1=None, g2=None, min_records=2):
        """
        查询相似赔率组合的历史3球打出率
        
        参数:
            g3: 3球赔率
            g0: 0球赔率
            g0_is_int: 0球是否是整数
            league_type: 赛事类型
            jc_pattern: 竞彩模式 (e.g. "2>3<4")
            macao_pattern: 澳门模式
            g1: 1球赔率
            g2: 2球赔率
            min_records: 最少需要的历史记录数
        
        返回:
            dict: {
                'count': 匹配场次数量,
                'g3_rate': 3球打出率,
                'g4plus_rate': 4+球打出率,
                'avg_total': 平均总进球
            }
        """
        if not self.data:
            return None
        
        matches = []
        # se.data 是字典，遍历其值而非键
        for record in self.data.values():
            # 优先使用 home_score + away_score（历史记录格式）
            if 'home_score' in record and 'away_score' in record:
                total_goals = record.get('home_score', 0) + record.get('away_score', 0)
            else:
                # 兼容 score 字典或字符串的情况
                score = record.get('score', {})
                if isinstance(score, str):
                    try:
                        parts = score.replace(':', ' ').split()
                        total_goals = int(parts[0]) + int(parts[1]) if len(parts) >= 2 else 0
                    except:
                        total_goals = 0
                elif isinstance(score, dict):
                    total_goals = score.get('home_score', 0) + score.get('away_score', 0)
                else:
                    total_goals = 0
            
            # 赔率匹配（允许±0.5的误差）
            match = True
            reason = []
            
            if g3 is not None and abs(record.get('3球', 0) - g3) > 0.5:
                match = False
            if g0 is not None and abs(record.get('0球', 0) - g0) > 1.0:
                match = False
            if g2 is not None and abs(record.get('2球', 0) - g2) > 0.5:
                match = False
                
            if match:
                matches.append({
                    'total': total_goals,
                    'is_g3': total_goals == 3,
                    'is_g4plus': total_goals >= 4,
                    'record': record
                })
        
        if len(matches) < min_records:
            return {
                'count': len(matches),
                'g3_rate': None,
                'g4plus_rate': None,
                'avg_total': None,
                'min_records_needed': min_records
            }
        
        g3_count = sum(1 for m in matches if m['is_g3'])
        g4plus_count = sum(1 for m in matches if m['is_g4plus'])
        avg_total = sum(m['total'] for m in matches) / len(matches)
        
        return {
            'count': len(matches),
            'g3_rate': round(g3_count / len(matches) * 100, 1),
            'g4plus_rate': round(g4plus_count / len(matches) * 100, 1),
            'avg_total': round(avg_total, 2)
        }
