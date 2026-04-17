#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞彩网API数据抓取器 v2
API: https://webapi.sporttery.cn/gateway/uniform/football/getFixedBonusV1.qry
"""
import requests
import json
import os
from datetime import datetime

class SportteryAPI:
    def __init__(self):
        self.base_url = 'https://webapi.sporttery.cn/gateway/uniform/football/getFixedBonusV1.qry'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
            'Referer': 'https://m.sporttery.cn/',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://m.sporttery.cn',
        }
        self.client_code = '3001'

    def get_match_data(self, match_id):
        """获取比赛数据"""
        params = {
            'clientCode': self.client_code,
            'matchId': str(match_id)
        }
        
        r = requests.get(self.base_url, params=params, headers=self.headers, timeout=15)
        r.encoding = 'utf-8'
        
        if r.status_code == 200 and 'json' in r.headers.get('Content-Type', ''):
            data = r.json()
            if data.get('success'):
                return data.get('value', {})
        
        return None

    def parse_score_odds(self, crs_list):
        """解析比分赔率 - 从最新的数据中提取"""
        import re
        score_odds = {}
        
        if not crs_list or len(crs_list) == 0:
            return score_odds
        
        # 使用最新的数据（最后一个元素）
        latest = crs_list[-1]
        
        # 比分格式: s01s00 = 主队1球:客队0球, s05s02 = 主5:客2
        # 正则: s(\d+)s(\d+) 匹配比分
        pattern = re.compile(r'^s(\d+)s(\d+)$')
        
        for key, value in latest.items():
            if not key.startswith('s'):
                continue
            
            # 跳过让球标记和变化标记
            if key.startswith('s-'):
                continue
            if 'f' in key:  # 包含f的是变化标记
                continue
            
            match = pattern.match(key)
            if match:
                try:
                    home_goals = str(int(match.group(1)))
                    away_goals = str(int(match.group(2)))
                    odds = float(value)
                    score_odds[f"{home_goals}:{away_goals}"] = odds
                except:
                    pass
        
        return score_odds

    def parse_total_goals(self, ttg_list):
        """解析总进球赔率"""
        total_goals = {}
        
        if not ttg_list or len(ttg_list) == 0:
            return total_goals
        
        # 使用最新的数据
        latest = ttg_list[-1]
        
        for key, value in latest.items():
            if not key.startswith('s'):
                continue
            
            # 解析总进球
            # s0=0球, s1=1球, s2=2球, s3+=3球或以上
            parts = key[1:]
            
            # 跳过变化标记
            if 'f' in parts:
                continue
            
            try:
                if parts.startswith('0'):
                    goals = '0'
                elif parts.startswith('1'):
                    goals = '1'
                elif parts.startswith('2'):
                    goals = '2'
                elif parts.startswith('3'):
                    goals = '3+'
                elif parts.startswith('4'):
                    goals = '4+'
                elif parts.startswith('5'):
                    goals = '5+'
                elif parts.startswith('6'):
                    goals = '6+'
                elif parts.startswith('7'):
                    goals = '7+'
                else:
                    continue
                
                odds = float(value)
                total_goals[f"{goals}球"] = odds
            except:
                pass
        
        return total_goals

    def parse_had(self, had_list):
        """解析胜平负赔率"""
        had = {}
        
        if not had_list or len(had_list) == 0:
            return had
        
        latest = had_list[-1]
        
        # had = 胜平负: h=主胜, d=平, a=客胜
        if isinstance(latest, dict):
            had = {
                '主胜': latest.get('h', 0),
                '平局': latest.get('d', 0),
                '主负': latest.get('a', 0),
                '更新时间': f"{latest.get('updateDate', '')} {latest.get('updateTime', '')}"
            }
        
        return had

    def parse_hhad(self, hhad_list):
        """解析让球胜平负"""
        hhad = {}
        
        if not hhad_list or len(hhad_list) == 0:
            return hhad
        
        latest = hhad_list[-1]
        
        # hhad: h=让胜, d=让平, a=让负, goalLine=让球数
        if isinstance(latest, dict):
            hhad = {
                '让胜': latest.get('h', 0),
                '让平': latest.get('d', 0),
                '让负': latest.get('a', 0),
                '让球数': latest.get('goalLine', ''),
                '更新时间': f"{latest.get('updateDate', '')} {latest.get('updateTime', '')}"
            }
        
        return hhad

    def parse_hafu(self, hafu_list):
        """解析半全场赔率"""
        hafu = {}
        
        if not hafu_list or len(hafu_list) == 0:
            return hafu
        
        latest = hafu_list[-1]
        
        if isinstance(latest, dict):
            # 半全场: 胜胜/胜平/胜负, 平胜/平平/平负, 负胜/负平/负负
            hafu = {
                '胜胜': latest.get('v0', 0),
                '胜平': latest.get('v1', 0),
                '胜负': latest.get('v3', 0),
                '平胜': latest.get('v4', 0),
                '平平': latest.get('v5', 0),
                '平负': latest.get('v7', 0),
                '负胜': latest.get('v8', 0),
                '负平': latest.get('v9', 0),
                '负负': latest.get('v10', 0),
                '更新时间': f"{latest.get('updateDate', '')} {latest.get('updateTime', '')}"
            }
        
        return hafu

    def format_match_data(self, data):
        """格式化比赛数据"""
        result = {
            'match_info': {},
            'score_odds': {},
            'total_goals': {},
            'had': {},
            'hhad': {},
            'hafu': {}
        }
        
        odds_history = data.get('oddsHistory', {})
        
        # 比赛信息
        result['match_info'] = {
            'home_team': odds_history.get('homeTeamAllName', ''),
            'away_team': odds_history.get('awayTeamAllName', ''),
            'home_abb': odds_history.get('homeTeamAbbName', ''),
            'away_abb': odds_history.get('awayTeamAbbName', ''),
            'isCancel': data.get('isCancel', 0)
        }
        
        # 各玩法赔率
        result['score_odds'] = self.parse_score_odds(odds_history.get('crsList', []))
        result['total_goals'] = self.parse_total_goals(odds_history.get('ttgList', []))
        result['had'] = self.parse_had(odds_history.get('hadList', []))
        result['hhad'] = self.parse_hhad(odds_history.get('hhadList', []))
        result['hafu'] = self.parse_hafu(odds_history.get('hafuList', []))
        
        return result

    def fetch_and_save(self, match_id, output_dir='sporttery_data'):
        """抓取并保存数据"""
        print(f'正在获取比赛 {match_id} 的数据...')
        
        data = self.get_match_data(match_id)
        if not data:
            print('获取数据失败')
            return None
        
        formatted = self.format_match_data(data)
        
        # 保存
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{formatted['match_info']['home_abb']}vs{formatted['match_info']['away_abb']}_{match_id}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'match_id': match_id,
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                **formatted
            }, f, ensure_ascii=False, indent=2)
        
        print(f'已保存到: {filepath}')
        return formatted


def main():
    api = SportteryAPI()
    
    # 测试
    match_id = '2039135'
    
    print('='*60)
    print(f'竞彩网数据抓取 - 比赛 {match_id}')
    print('='*60)
    
    result = api.fetch_and_save(match_id)
    
    if result:
        print('\n比赛信息:')
        print(f"  主队: {result['match_info']['home_team']}")
        print(f"  客队: {result['match_info']['away_team']}")
        
        print('\n比分赔率(部分):')
        for k, v in sorted(result['score_odds'].items(), key=lambda x: x[1])[:10]:
            print(f"  {k}: {v}")
        
        print('\n总进球:')
        for k, v in sorted(result['total_goals'].items(), key=lambda x: float(x[1] or 0))[:5]:
            print(f"  {k}: {v}")
        
        print('\n胜平负:')
        print(f"  {result['had']}")
        
        print('\n让球胜平负:')
        print(f"  {result['hhad']}")


if __name__ == '__main__':
    main()
