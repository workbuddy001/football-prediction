#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞彩网前瞻数据抓取器
获取：特征分析、历史交锋、积分榜、比赛近况、未来赛事、射手信息、伤停一览
"""
import requests
import json
import sys
import io
import time
from datetime import datetime

# Windows UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class SportteryPreviewAPI:
    """竞彩网前瞻数据API"""
    
    BASE_URL = 'https://webapi.sporttery.cn'
    
    # API路径
    APIS = {
        'fixed_bonus': '/gateway/uniform/football/getFixedBonusV1.qry',  # 固定奖金
        'match_feature': '/gateway/uniform/football/getMatchFeatureV1.qry',  # 特征分析
        'result_history': '/gateway/uniform/football/getResultHistoryV1.qry',  # 历史交锋
        'match_tables': '/gateway/uniform/football/getMatchTablesV1.qry',  # 积分榜
        'injury': '/gateway/uniform/football/getInjurySuspensionV1.qry',  # 伤停一览
        'future_matches': '/gateway/uniform/football/getFutureMatchesV1.qry',  # 未来赛事
        'match_result': '/gateway/uniform/football/getMatchResultV1.qry',  # 比赛近况
        'match_player': '/gateway/uniform/football/getMatchPlayerV1.qry',  # 射手信息
        'match_head': '/gateway/uniform/football/getMatchHeadV1.qry',  # 比赛头部信息
    }
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
        'Referer': 'https://m.sporttery.cn/',
        'Accept': 'application/json',
    }
    
    def __init__(self, match_id):
        self.match_id = str(match_id)
        self.client_code = '3001'
        
    def _get(self, api_name, params=None):
        """发送GET请求"""
        url = self.BASE_URL + self.APIS[api_name]
        
        # 添加基础参数
        query = f'clientCode={self.client_code}&sportteryMatchId={self.match_id}'
        if params:
            query += '&' + params
        
        full_url = url + '?' + query
        
        try:
            r = requests.get(full_url, headers=self.HEADERS, timeout=10)
            return r.json()
        except Exception as e:
            print(f'请求错误: {e}')
            return None
    
    def get_match_info(self):
        """获取比赛基本信息"""
        data = self._get('match_head', 'source=m')
        if data and data.get('errorCode') == '0':
            return data.get('value', {})
        return None
    
    def get_fixed_bonus(self):
        """获取固定奖金（赔率）"""
        data = self._get('fixed_bonus')
        if data and data.get('errorCode') == '0':
            return data.get('value', {})
        return None
    
    def get_match_feature(self):
        """获取特征分析"""
        data = self._get('match_feature', 'termLimits=10')
        if data and data.get('errorCode') == '0':
            return data.get('value', {})
        return None
    
    def get_result_history(self, limit=5, tournament_flag=0, home_away_flag=0):
        """获取历史交锋"""
        params = f'termLimits={limit}&tournamentFlag={tournament_flag}&homeAwayFlag={home_away_flag}'
        data = self._get('result_history', params)
        if data and data.get('errorCode') == '0':
            return data.get('value', {})
        return None
    
    def get_match_tables(self):
        """获取积分榜"""
        data = self._get('match_tables')
        if data and data.get('errorCode') == '0':
            return data.get('value', {})
        return None
    
    def get_injury(self):
        """获取伤停信息"""
        data = self._get('injury')
        if data and data.get('errorCode') == '0':
            return data.get('value', {})
        return None
    
    def get_future_matches(self, limit=4):
        """获取未来赛事"""
        params = f'termLimits={limit}'
        data = self._get('future_matches', params)
        if data and data.get('errorCode') == '0':
            return data.get('value', {})
        return None
    
    def get_match_result(self, limit=5, tournament_flag=0, home_away_flag=0):
        """获取比赛近况"""
        params = f'termLimits={limit}&tournamentFlag={tournament_flag}&homeAwayFlag={home_away_flag}'
        data = self._get('match_result', params)
        if data and data.get('errorCode') == '0':
            return data.get('value', {})
        return None
    
    def get_match_player(self, limit=3):
        """获取射手信息"""
        params = f'termLimits={limit}'
        data = self._get('match_player', params)
        if data and data.get('errorCode') == '0':
            return data.get('value', {})
        return None
    
    def get_all_preview(self):
        """获取所有前瞻数据"""
        result = {
            'match_id': self.match_id,
            'fetch_time': datetime.now().isoformat(),
            'match_info': self.get_match_info(),
            'fixed_bonus': self.get_fixed_bonus(),
            'match_feature': self.get_match_feature(),
            'result_history': self.get_result_history(),
            'match_tables': self.get_match_tables(),
            'injury': self.get_injury(),
            'future_matches': self.get_future_matches(),
            'match_result': self.get_match_result(),
            'match_player': self.get_match_player(),
        }
        return result
    
    def print_preview(self):
        """打印前瞻数据"""
        data = self.get_all_preview()
        
        print('\n' + '='*60)
        print(f'比赛ID: {self.match_id}')
        print('='*60)
        
        # 比赛信息
        info = data.get('match_info', {})
        if info:
            print(f"\n📋 比赛信息")
            print(f"  主队: {info.get('homeTeamShortName', 'N/A')}")
            print(f"  客队: {info.get('awayTeamShortName', 'N/A')}")
            print(f"  赛事: {info.get('tournamentCnShortName', 'N/A')}")
            print(f"  时间: {info.get('matchDateTime', 'N/A')}")
        
        # 特征分析
        feature = data.get('match_feature', {})
        if feature:
            print(f"\n📊 特征分析（近10场）")
            last = feature.get('last', {})
            if last:
                print(f"  主队胜/平/负: {last.get('homeWinGoalMatchCnt', 0)}/{last.get('homeDrawMatchCnt', 0)}/{last.get('homeLossGoalMatchCnt', 0)}")
                print(f"  客队胜/平/负: {last.get('awayWinGoalMatchCnt', 0)}/{last.get('awayDrawMatchCnt', 0)}/{last.get('awayLossGoalMatchCnt', 0)}")
            
            goal_avg = feature.get('goalAvg', {})
            if goal_avg:
                print(f"  主队场均进球: {goal_avg.get('homeGoalAvgCnt', 'N/A')}")
                print(f"  客队场均进球: {goal_avg.get('awayGoalAvgCnt', 'N/A')}")
        
        # 伤停信息
        injury = data.get('injury', {})
        if injury:
            print(f"\n🏥 伤停一览")
            
            home = injury.get('home', {})
            if home:
                injuries = home.get('injuriesAndSuspensionsList', [])
                print(f"  主队({home.get('teamShortName', '')})伤停: {len(injuries)}人")
                for p in injuries[:3]:
                    name = p.get('personName', '')
                    pos = p.get('playerPositionDesc', '')
                    print(f"    - {name}({pos}) 出场{p.get('appearanceCnt', 0)}次")
            
            away = injury.get('away', {})
            if away:
                injuries = away.get('injuriesAndSuspensionsList', [])
                print(f"  客队({away.get('teamShortName', '')})伤停: {len(injuries)}人")
                for p in injuries[:3]:
                    name = p.get('personName', '')
                    pos = p.get('playerPositionDesc', '')
                    print(f"    - {name}({pos}) 出场{p.get('appearanceCnt', 0)}次")
        
        # 历史交锋
        history = data.get('result_history', {})
        if history:
            matches = history.get('matchList', [])
            print(f"\n⚔️ 历史交锋 (共{len(matches)}场)")
            for m in matches[:3]:
                home = m.get('homeTeamShortName', '')
                away = m.get('awayTeamShortName', '')
                score = m.get('fullCourtGoal', '')
                date = m.get('matchDate', '')[:10]
                print(f"    {date} {home} {score} {away}")
        
        # 射手信息
        player = data.get('match_player', {})
        if player:
            print(f"\n⚽ 射手信息")
            home = player.get('home', {})
            if isinstance(home, dict):
                home_list = home.get('playerList', [])
                print(f"  主队射手:")
                for p in home_list[:3]:
                    print(f"    - {p.get('personName', '')} {p.get('goalCnt', 0)}球")
            
            away = player.get('away', {})
            if isinstance(away, dict):
                away_list = away.get('playerList', [])
                print(f"  客队射手:")
                for p in away_list[:3]:
                    print(f"    - {p.get('personName', '')} {p.get('goalCnt', 0)}球")
        
        print('\n' + '='*60)
        return data


def main():
    if len(sys.argv) > 1:
        match_id = sys.argv[1]
    else:
        match_id = '2039135'  # 默认比赛
    
    api = SportteryPreviewAPI(match_id)
    data = api.print_preview()
    
    # 保存JSON
    fname = f'sporttery_preview_{match_id}.json'
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'\n数据已保存到: {fname}')


if __name__ == '__main__':
    main()
