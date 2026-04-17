# -*- coding: utf-8 -*-
"""
match_record.py - 预测记录数据结构和模板生成

数据结构定义 + TXT模板生成器
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional


class MatchRecord:
    """单场比赛预测记录"""

    def __init__(self, fixture_id: str, home: str, away: str,
                 league: str, match_time: str, handicap: str = ""):
        # === 基础信息 ===
        self.fixture_id = fixture_id
        self.home = home
        self.away = away
        self.league = league
        self.match_time = match_time
        self.handicap = handicap  # 让球数，如 "-1"
        self.record_date = datetime.now().strftime("%Y-%m-%d")

        # === 竞彩赔率 ===
        self.jc_odds = {
            'init': {'home': 0, 'draw': 0, 'away': 0},
            'realtime': {'home': 0, 'draw': 0, 'away': 0}
        }

        # === 澳门赔率 ===
        self.am_odds = {
            'init': {'home': 0, 'draw': 0, 'away': 0}
        }

        # === 澳门心水 ===
        self.macau_rec = ""       # 推荐方向
        self.macau_analysis = ""   # 分析理由
        self.history_h2h = ""      # 交锋记录

        # === 近况走势 ===
        self.home_form = ""        # 如 "WWLDW"
        self.away_form = ""
        self.home_panlu = ""       # 盘路
        self.away_panlu = ""

        # === 软件预测结果 ===
        self.software_pred = ""    # 主胜/平/客胜
        self.confidence = 0        # 置信度 0-100
        self.exclusion_stars = ""  # ★数量

        # === 排除法分析 ===
        self.exclusion_signals = []  # 排除信号列表
        self.final_odds = {"home": 0, "draw": 0, "away": 0}  # 最终赔率
        self.final_prob = {"home": 0, "draw": 0, "away": 0}  # 概率
        self.score_pred = ""       # 比分预测

        # === 附属赔率 ===
        self.half_full_odds = {}   # 半全场: {"胜胜": x.xx, ...}
        self.over_under_odds = {}  # 大小球: {"大球": x.xx, "小球": x.xx, "盘口": x}
        self.total_goals_odds = {} # 进球数: {"0": x, "1": x, ...}
        self.score_odds = {}       # 比分赔率: {"1:0": x, "2:0": x, ...}

        # === 亚洲盘口 ===
        self.yazhi = {
            'macau': {},
            '皇冠': {},
            '威尼斯人': {}
        }

        # === 比分分数（最终汇总） ===
        self.total_scores = {
            'home': 0,
            'draw': 0,
            'away': 0
        }

        # === 基本面分数（手填） ===
        self.basic_score = {
            'home': 0,
            'away': 0,
            'gap': 0
        }

        # === 大小球预测 ===
        self.over_under_pred = ""
        self.over_under_logic = ""

        # === 比分逻辑 ===
        self.score_logic = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'fixture_id': self.fixture_id,
            'home': self.home,
            'away': self.away,
            'league': self.league,
            'match_time': self.match_time,
            'handicap': self.handicap,
            'record_date': self.record_date,
            'jc_odds': self.jc_odds,
            'am_odds': self.am_odds,
            'macau_rec': self.macau_rec,
            'history_h2h': self.history_h2h,
            'home_form': self.home_form,
            'away_form': self.away_form,
            'software_pred': self.software_pred,
            'confidence': self.confidence,
            'exclusion_signals': self.exclusion_signals,
            'half_full_odds': self.half_full_odds,
            'over_under_odds': self.over_under_odds,
            'total_goals_odds': self.total_goals_odds,
            'score_odds': self.score_odds,
            'yazhi': self.yazhi,
            'total_scores': self.total_scores,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MatchRecord':
        """从字典创建"""
        record = cls(
            data.get('fixture_id', ''),
            data.get('home', ''),
            data.get('away', ''),
            data.get('league', ''),
            data.get('match_time', ''),
            data.get('handicap', '')
        )
        record.__dict__.update(data)
        return record


def calc_odds_change_str(init_val: float, rt_val: float) -> str:
    """计算赔率变化百分比，生成显示字符串"""
    if init_val == 0:
        return f"{rt_val} (无初赔)"
    chg = (rt_val - init_val) / init_val * 100
    sign = "+" if chg > 0 else ""
    return f"{init_val} → {rt_val} ({sign}{chg:.1f}%)"


def generate_txt(record: MatchRecord, template_path: str = None) -> str:
    """
    生成预测记录 TXT 文件内容

    对应模板: 分析模板/预测记录_塞尔塔 vs 弗赖堡_2026-04-17.txt
    """

    # 文件名
    filename = f"预测记录_{record.home}_vs_{record.away}_{record.record_date}.txt"

    # 计算赔率变化
    jc_h_chg = calc_odds_change_str(
        record.jc_odds['init']['home'],
        record.jc_odds['realtime']['home']
    )
    jc_d_chg = calc_odds_change_str(
        record.jc_odds['init']['draw'],
        record.jc_odds['realtime']['draw']
    )
    jc_a_chg = calc_odds_change_str(
        record.jc_odds['init']['away'],
        record.jc_odds['realtime']['away']
    )

    am_h_chg = calc_odds_change_str(
        record.am_odds['init']['home'],
        record.final_odds.get('home', record.am_odds['init']['home'])
    )
    am_d_chg = calc_odds_change_str(
        record.am_odds['init']['draw'],
        record.final_odds.get('draw', record.am_odds['init']['draw'])
    )
    am_a_chg = calc_odds_change_str(
        record.am_odds['init']['away'],
        record.final_odds.get('away', record.am_odds['init']['away'])
    )

    # 生成排除法信号文本
    exclusion_text = "\n".join([f"- {s}" for s in record.exclusion_signals]) if record.exclusion_signals else "（无）"

    # 半全场表格
    hf_lines = []
    hf_map = {
        '胜胜': '胜胜', '胜平': '胜平', '胜负': '胜负',
        '平胜': '平胜', '平平': '平平', '平负': '平负',
        '负胜': '负胜', '负平': '负平', '负负': '负负'
    }
    for key, label in hf_map.items():
        val = record.half_full_odds.get(key, '')
        hf_lines.append(f"{label}\n{val}")

    # 大小球表格
    ou_val = record.over_under_odds
    ou_text = f"大球\n{ou_val.get('大球', '')}\n\n小球\n{ou_val.get('小球', '')}"

    # 进球数表格
    goals_lines = []
    for i in range(7):
        key = str(i)
        val = record.total_goals_odds.get(key, '')
        goals_lines.append(f"{i}\n{val}")
    goals_lines.append("7+\n" + str(record.total_goals_odds.get('7+', '')))
    goals_text = "\n\n".join(goals_lines)

    # 比分表格
    score_map = [
        ('1:0', '2:0', '2:1', '3:0', '3:1', '3:2', '4:0', '4:1', '4:2', '5:0', '5:1', '5:2'),
        ('0:0', '0:1', '0:2', '0:3', '1:1', '1:2', '1:3', '2:2', '2:3', '0:4', '1:4', '2:4'),
        ('0:5', '1:5', '2:5', '负其它'),
    ]
    score_text_rows = []
    for row in score_map:
        for sc in row:
            val = record.score_odds.get(sc, '')
            score_text_rows.append(f"{sc}\n{val}")
        score_text_rows.append("")
    score_text = "\n".join(score_text_rows)

    # 亚盘表格
    yazhi_text = ""
    for company, data in record.yazhi.items():
        if data:
            init = data.get('init', {})
            rt = data.get('realtime', {})
            yazhi_text += f"\n{company}\n"
            yazhi_text += f"{init.get('home_odds', '')}\t{init.get('handicap', '')}\t{init.get('away_odds', '')}\n"
            yazhi_text += f"{rt.get('home_odds', '')}\t{rt.get('handicap', '')}\t{rt.get('away_odds', '')}"

    # 最终分数
    total_scores_text = (
        f"主胜={record.total_scores['home']} "
        f"平局={record.total_scores['draw']} "
        f"客胜={record.total_scores['away']}"
    )

    # 组装完整文本
    content = f"""名称：
{record.home} vs {record.away}
📌  |  ⚽ {record.league}  |  🕐 {record.match_time}  |  让球: {record.handicap}

1、软件预测：
{record.software_pred}
{record.exclusion_stars} 排除{len(record.exclusion_signals)}个方向
{record.software_pred.replace('胜', '胜分').replace('平', '平分').replace('客', '客胜分')}+1
2、历史参考：

（待接入历史数据库）
3、澳门心水：
澳门推荐 & 历史
心水
{record.macau_rec}
交锋
{record.history_h2h}
客胜分+1

4、基本面分数：（手填）
{record.home}：{record.basic_score.get('home', '？')}分
{record.away}：{record.basic_score.get('away', '？')}分
差距：{record.basic_score.get('gap', '？')}分
客胜分+1

6、赔率矩阵（标准1X2）:
🇨🇳 竞彩官方
主胜
{jc_h_chg}
平局
{jc_d_chg}
客胜
{jc_a_chg}
🇲🇴 澳门
主胜
{am_h_chg}
平局
{am_d_chg}
客胜
{am_a_chg}
客胜+1
7、排除法信号分析：
{exclusion_text}

8、赛果倾向：{record.software_pred}（稳胆）
胜 {record.final_prob.get('home', 0)}%、平 {record.final_prob.get('draw', 0)}%、{record.home}胜 {record.final_prob.get('away', 0)}%


9、大小球：{record.over_under_pred}
{record.over_under_logic}

比分参考：{record.score_pred}
大球+1

10、逻辑：
{record.score_logic}

11、亚洲盘口：（抓取）
{yazhi_text}

12、半全场：（抓取）
{chr(10).join(hf_lines[:18])}

13、大小球：
{ou_text}

13、进球数赔率：（抓取）
{goals_text}

14、比分赔率：（抓期）
比分
{score_text}



最终分数：（程序计算）
{total_scores_text}
比分预测：{record.score_pred}
"""

    return filename, content


# 测试
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    # 创建一个测试记录
    record = MatchRecord(
        fixture_id="001",
        home="塞尔塔",
        away="弗赖堡",
        league="欧罗巴",
        match_time="2026-04-17 00:45",
        handicap="-1"
    )

    record.software_pred = "客胜"
    record.confidence = 85
    record.exclusion_stars = "★★★★★"
    record.macau_rec = "弗赖堡 贏"
    record.history_h2h = "塞尔塔 0胜0和1负"
    record.exclusion_signals = [
        "主胜赔率8.35>5.0，排除主胜",
        "澳门造热客，排除主胜"
    ]
    record.final_odds = {'home': 1.80, 'draw': 3.65, 'away': 3.35}
    record.final_prob = {'home': 65, 'draw': 25, 'away': 10}
    record.score_pred = "1-3、1-2、0-2"
    record.over_under_pred = "大球（≥3）"
    record.over_under_logic = "主队狂攻易被反击打穿"
    record.score_logic = "塞尔塔残阵+绝境+防线崩盘；弗赖堡完整阵容+巨大优势+防守反击，客场稳晋级"

    record.jc_odds = {
        'init': {'home': 1.67, 'draw': 3.60, 'away': 3.95},
        'realtime': {'home': 1.80, 'draw': 3.65, 'away': 3.35}
    }
    record.am_odds = {
        'init': {'home': 1.95, 'draw': 3.35, 'away': 3.18}
    }

    record.basic_score = {'home': 49, 'away': 81, 'gap': 32}
    record.total_scores = {'home': 3, 'draw': 2, 'away': 7}

    # 生成文件
    filename, content = generate_txt(record)
    print(f"Generated: {filename}")
    print("=" * 50)
    print(content[:2000])
