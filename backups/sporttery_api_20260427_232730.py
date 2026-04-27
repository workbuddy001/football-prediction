#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞彩网API数据抓取器 v3 - 包含前瞻数据
"""
import requests
import json
import os
from datetime import datetime

class SportteryAPI:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
            'Referer': 'https://m.sporttery.cn/',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://m.sporttery.cn',
        }
        self.client_code = '3001'
        self.base_api = 'https://webapi.sporttery.cn/gateway/uniform/football'

    def _call_api(self, api_name, match_id):
        """通用API调用"""
        url = f"{self.base_api}/{api_name}.qry"
        params = {
            'clientCode': self.client_code,
            'sportteryMatchId': str(match_id)
        }
        try:
            r = requests.get(url, params=params, headers=self.headers, timeout=15)
            r.encoding = 'utf-8'
            if r.status_code == 200:
                data = r.json()
                if data.get('success'):
                    return data.get('value', {})
        except:
            pass
        return None

    # ==================== 原始赔率数据 ====================
    def get_match_data(self, match_id):
        """获取比赛赔率数据"""
        url = f"{self.base_api}/getFixedBonusV1.qry"
        params = {'clientCode': self.client_code, 'matchId': str(match_id)}
        r = requests.get(url, params=params, headers=self.headers, timeout=15)
        r.encoding = 'utf-8'
        if r.status_code == 200 and 'json' in r.headers.get('Content-Type', ''):
            data = r.json()
            if data.get('success'):
                return data.get('value', {})
        return None

    def parse_score_odds(self, crs_list):
        """解析比分赔率"""
        import re
        score_odds = {}
        if not crs_list:
            return score_odds
        latest = crs_list[-1]
        for item in latest.get('hhadList', []):
            if item.get('v') and float(item.get('v', 0)) > 0:
                score_odds[item['h'] + '-' + item['a']] = item['v']
        return score_odds

    # ==================== 前瞻数据API ====================
    def get_preview_data(self, match_id):
        """获取前瞻数据（特征分析、历史交锋、伤停等）"""
        result = {
            'feature': {},
            'history': {},
            'injury': {},
            'recent': {},
            'tables': {},
            'player': {}
        }
        
        # 特征分析
        data = self._call_api('getMatchFeatureV1', match_id)
        if data:
            result['feature'] = data
        
        # 历史交锋
        data = self._call_api('getResultHistoryV1', match_id)
        if data:
            result['history'] = data
        
        # 伤停一览
        data = self._call_api('getInjurySuspensionV1', match_id)
        if data:
            result['injury'] = data
        
        # 比赛近况
        data = self._call_api('getMatchResultV1', match_id)
        if data:
            result['recent'] = data
        
        # 积分榜
        data = self._call_api('getMatchTablesV1', match_id)
        if data:
            result['tables'] = data
        
        # 射手信息
        data = self._call_api('getMatchPlayerV1', match_id)
        if data:
            result['player'] = data
        
        return result

    # ==================== 数据保存 ====================
    def fetch_and_save(self, match_id):
        """抓取并保存完整数据"""
        data = self.get_match_data(match_id)
        if not data:
            return None
        
        # 获取赔率数据（在 oddsHistory 里）
        odds_data = data.get('oddsHistory', {})
        match_data = data.get('match', odds_data)  # 兼容两种格式
        
        # 解析赔率数据
        match_info = self._parse_match_info(match_data)
        score_odds = self._parse_score_odds(odds_data)
        total_goals = self._parse_total_goals(odds_data)
        had = self._parse_had(odds_data)
        ttg = self._parse_ttg(odds_data)
        hafu = self._parse_hafu(odds_data)
        hhad = self._parse_hhad(odds_data)
        
        # 获取前瞻数据
        preview = self.get_preview_data(match_id)

        # 计算赔率变化统计
        ttg_change_stats = self._calc_ttg_change_stats(odds_data)
        hafu_change_stats = self._calc_hafu_change_stats(odds_data)

        # 计算进球数-比分联动排除列表
        exclusion_list = self._calc_exclusion_list(score_odds, total_goals)
        
        result = {
            'match_id': match_id,
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'match_info': match_info,
            'score_odds': score_odds,
            'total_goals': total_goals,
            'had': had,
            'ttg': ttg,
            'hafu': hafu,
            'hhad': hhad,
            'preview': preview,
            'ttg_change': ttg_change_stats,
            'hafu_change': hafu_change_stats,
            'exclusion_list': exclusion_list
        }
        
        # 保存
        os.makedirs('sporttery_data', exist_ok=True)
        filepath = os.path.join('sporttery_data', f'{match_id}.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return result

    def _parse_match_info(self, data):
        """解析比赛基本信息"""
        return {
            'home_team': data.get('homeTeamAllName', '') or data.get('homeTeamName', ''),
            'away_team': data.get('awayTeamAllName', '') or data.get('awayTeamName', ''),
            'league': data.get('leagueAllName', '') or data.get('leagueName', ''),
            'time': data.get('matchTime', '')[:16] if data.get('matchTime') else ''
        }

    def _parse_score_odds(self, data):
        """解析比分赔率 - 格式: s主队进球s客队进球"""
        score_odds = {}
        for item in data.get('crsList', []):
            if isinstance(item, dict):
                for key, val in item.items():
                    # 匹配格式: s02s01 (主2球-客1球)
                    import re
                    m = re.match(r'^s(\d+)s(\d+)$', key)
                    if m and val and float(val) > 0:
                        home_goals = m.group(1)
                        away_goals = m.group(2)
                        score_odds[f"{home_goals}:{away_goals}"] = val
        return score_odds

    def _parse_total_goals(self, data):
        """解析总进球 - 格式: [{"s0":"30.00","s1":"9.00","s2":"4.85",...}]"""
        total_goals = {}
        for item in data.get('ttgList', []):
            if isinstance(item, dict):
                for key, val in item.items():
                    # 匹配格式: s0, s1, s2, ... (总进球数)
                    if key.startswith('s') and key[1:].isdigit() and val and float(val) > 0:
                        goals = key[1:]
                        total_goals[f"{goals}球"] = val
        return total_goals

    def _parse_had(self, data):
        """解析胜平负 - 格式: [{"h":"胜","d":"3.90","a":"3.06"}]"""
        had = {}
        for item in data.get('hadList', []):
            if isinstance(item, dict):
                if item.get('h') and float(item['h']) > 0:
                    had['胜'] = item['h']
                if item.get('d') and float(item['d']) > 0:
                    had['平'] = item['d']
                if item.get('a') and float(item['a']) > 0:
                    had['负'] = item['a']
        return had

    def _parse_ttg(self, data):
        """解析总进球"""
        return self._parse_total_goals(data)

    def _parse_hafu(self, data):
        """解析半全场 - 格式: [{"hh":"2.85","dh":"5.40","ah":"18.00","hd":"13.00","dd":"7.25","ad":"13.00","ha":"24.00","da":"8.00","aa":"4.90"}]"""
        # hh=胜胜, dh=平胜, ah=负胜, hd=胜平, dd=平平, ad=负平, ha=胜负, da=平负, aa=负负
        hafu_names = {
            'hh': '胜胜', 'dh': '平胜', 'ah': '负胜',
            'hd': '胜平', 'dd': '平平', 'ad': '负平',
            'ha': '胜负', 'da': '平负', 'aa': '负负'
        }
        hafu = {}
        for item in data.get('hafuList', []):
            if isinstance(item, dict):
                for key, val in item.items():
                    if key in hafu_names and val and float(val) > 0:
                        hafu[hafu_names[key]] = val
        return hafu

    def _parse_hhad(self, data):
        """解析让球胜平负 - 格式: [{"goalLine":"-1","h":"3.25","d":"4.00","a":"1.75"}]"""
        hhad = {}
        for item in data.get('hhadList', []):
            if isinstance(item, dict):
                goal_line = item.get('goalLine', '')
                if goal_line:
                    hhad['让球'] = goal_line
                if item.get('h') and float(item['h']) > 0:
                    hhad['让胜'] = item['h']
                if item.get('d') and float(item['d']) > 0:
                    hhad['让平'] = item['d']
                if item.get('a') and float(item['a']) > 0:
                    hhad['让负'] = item['a']
        return hhad

    def _calc_ttg_change_stats(self, data):
        """计算总进球赔率变化统计
        返回格式: {赔率项: {"count": 变化次数, "change_pct": 变化百分比}}
        """
        ttg_list = data.get('ttgList', [])
        if len(ttg_list) < 2:
            return {}

        # 提取所有可能的赔率键 (s0, s1, s2, ...)
        all_keys = set()
        for item in ttg_list:
            if isinstance(item, dict):
                for key in item.keys():
                    if key.startswith('s') and key[1:].isdigit():
                        all_keys.add(key)

        stats = {}
        for key in all_keys:
            values = []
            for item in ttg_list:
                if isinstance(item, dict) and key in item:
                    try:
                        v = float(item[key])
                        if v > 0:
                            values.append(v)
                    except (ValueError, TypeError):
                        pass

            if len(values) < 2:
                continue

            # 计算变化次数（非连续相同值）
            changes = 0
            for i in range(1, len(values)):
                if abs(values[i] - values[i-1]) > 0.001:
                    changes += 1

            # 计算变化幅度：从第一个到最后一个
            first_val = values[0]
            last_val = values[-1]
            if first_val > 0:
                change_pct = ((last_val - first_val) / first_val) * 100
            else:
                change_pct = 0

            # 转换为显示名称
            goal_num = key[1:]
            display_name = f"{goal_num}球"
            stats[display_name] = {
                'count': changes,
                'change_pct': round(change_pct, 1)
            }

        return stats

    def _calc_hafu_change_stats(self, data):
        """计算半全场赔率变化统计
        返回格式: {赔率项: {"count": 变化次数, "change_pct": 变化百分比}}
        """
        hafu_list = data.get('hafuList', [])
        if len(hafu_list) < 2:
            return {}

        hafu_names = {
            'hh': '胜胜', 'dh': '平胜', 'ah': '负胜',
            'hd': '胜平', 'dd': '平平', 'ad': '负平',
            'ha': '胜负', 'da': '平负', 'aa': '负负'
        }

        all_keys = set(hafu_names.keys())

        stats = {}
        for key in all_keys:
            values = []
            for item in hafu_list:
                if isinstance(item, dict) and key in item:
                    try:
                        v = float(item[key])
                        if v > 0:
                            values.append(v)
                    except (ValueError, TypeError):
                        pass

            if len(values) < 2:
                continue

            # 计算变化次数（非连续相同值）
            changes = 0
            for i in range(1, len(values)):
                if abs(values[i] - values[i-1]) > 0.001:
                    changes += 1

            # 计算变化幅度：从第一个到最后一个
            first_val = values[0]
            last_val = values[-1]
            if first_val > 0:
                change_pct = ((last_val - first_val) / first_val) * 100
            else:
                change_pct = 0

            if key in hafu_names:
                stats[hafu_names[key]] = {
                    'count': changes,
                    'change_pct': round(change_pct, 1)
                }

        return stats

    def _is_special_tail(self, val_str):
        """判断赔率是否含特殊尾数（.25 / .75 / .15）"""
        try:
            v = float(val_str)
            # 取小数部分，保留2位精度
            frac = round(v % 1, 2)
            return frac in (0.25, 0.75, 0.15)
        except (ValueError, TypeError):
            return False

    def _calc_exclusion_list(self, score_odds, total_goals):
        """
        进球数-比分联动排除定律
        规则：
          A. 比分赔率尾数为 .25/.75/.15 → 该比分优先排除
          B. 进球数赔率尾数为 .25/.75/.15 → 该进球数优先排除
          C. 联动：若进球数被排除 + 对应比分也有特殊尾数 → 强排除
             若进球数被排除 + 对应比分尾数普通 → 普通排除
             若进球数未被排除 + 仅比分特殊尾数 → 比分单独排除

        返回:
          [
            {
              "goal": "3球",
              "ttg_odds": "3.90",
              "ttg_special": True/False,    # 进球数赔率含特殊尾数
              "scores": [
                { "score": "1:2", "odds": "10.50", "special": True/False }
              ],
              "level": "强排除" / "普通排除" / "仅比分排除",
              "reason": "说明文字"
            }
          ]
        """
        import re

        # 按进球总数分组比分
        # score_odds 格式: {"01:02": "10.50", ...}
        goals_to_scores = {}
        for score_key, odds_val in score_odds.items():
            # 解析 home:away 格式（可能是 01:02 或 1:2）
            m = re.match(r'^(\d+):(\d+)$', score_key)
            if not m:
                continue
            home = int(m.group(1))
            away = int(m.group(2))
            total = home + away
            if total not in goals_to_scores:
                goals_to_scores[total] = []
            goals_to_scores[total].append({
                'score': score_key,
                'odds': odds_val,
                'special': self._is_special_tail(odds_val)
            })

        result = []

        for total, scores in sorted(goals_to_scores.items()):
            ttg_key = f"{total}球"
            ttg_odds = total_goals.get(ttg_key, None)
            ttg_special = self._is_special_tail(ttg_odds) if ttg_odds else False

            # 检查该进球数下是否有比分含特殊尾数
            has_special_score = any(s['special'] for s in scores)

            # 只有至少一个方向（进球数或比分）命中特殊尾数才加入排除列表
            if not ttg_special and not has_special_score:
                continue

            # 判断级别
            if ttg_special and has_special_score:
                level = "强排除"
                reason = f"进球数赔率({ttg_odds})含特殊尾数，且对应比分中有特殊尾数赔率，联动双重排除信号"
            elif ttg_special and not has_special_score:
                level = "普通排除"
                reason = f"进球数赔率({ttg_odds})含特殊尾数，排除该进球数及其所有比分"
            else:
                # 仅比分含特殊尾数
                level = "仅比分排除"
                ttg_info = f"{ttg_odds}（普通）" if ttg_odds else "无数据"
                reason = f"进球数赔率{ttg_info}，但对应比分中存在特殊尾数赔率，可优先排除特殊尾数比分"

            result.append({
                'goal': ttg_key,
                'ttg_odds': ttg_odds or '-',
                'ttg_special': ttg_special,
                'scores': scores,
                'level': level,
                'reason': reason
            })

        # 按级别排序：强排除 > 普通排除 > 仅比分排除
        level_order = {'强排除': 0, '普通排除': 1, '仅比分排除': 2}
        result.sort(key=lambda x: level_order.get(x['level'], 9))

        return result
