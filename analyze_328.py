#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3月28日周六15场比赛自动分析脚本
基于源数据文件进行赔率分析和预测
"""

import os
import re
import glob
from datetime import datetime


def parse_form_score(form_str):
    """
    解析近况走势，计算近况评分
    规则：最近一场（字符串最左边）权重×2，其他4场×1
    得分：赢=3，平=1，输=0
    满分：3×2 + 3×4 = 18分
    """
    if not form_str or len(form_str) < 5:
        return 0
    
    # 取最近5场
    recent_5 = form_str[:5]
    
    score = 0
    for i, result in enumerate(recent_5):
        result_upper = result.upper()
        if result_upper == 'W':
            points = 3
        elif result_upper == 'D':
            points = 1
        else:  # L或其他
            points = 0
        
        # 权重：最近一场（索引0）×2，其他×1
        weight = 2 if i == 0 else 1
        score += points * weight
    
    return score


def extract_match_info(content):
    """从文件内容中提取比赛信息"""
    info = {}
    
    # 提取主队、客队
    home_match = re.search(r'home_team\s*=\s*"([^"]+)"', content)
    away_match = re.search(r'away_team\s*=\s*"([^"]+)"', content)
    time_match = re.search(r'match_time\s*=\s*"([^"]+)"', content)
    league_match = re.search(r'league\s*=\s*"([^"]+)"', content)
    home_form_match = re.search(r'home_form\s*=\s*"([^"]+)"', content)
    away_form_match = re.search(r'away_form\s*=\s*"([^"]+)"', content)
    history_match = re.search(r'history\s*=\s*"([^"]+)"', content)
    macao_match = re.search(r'macao_tip\s*=\s*"([^"]+)"', content)
    
    info['home_team'] = home_match.group(1) if home_match else "未知"
    info['away_team'] = away_match.group(1) if away_match else "未知"
    info['match_time'] = time_match.group(1) if time_match else "未知"
    info['league'] = league_match.group(1) if league_match else "未知"
    info['home_form'] = home_form_match.group(1) if home_form_match else ""
    info['away_form'] = away_form_match.group(1) if away_form_match else ""
    info['history'] = history_match.group(1) if history_match else ""
    info['macao_tip'] = macao_match.group(1) if macao_match else ""
    
    # 计算近况评分
    info['home_form_score'] = parse_form_score(info['home_form'])
    info['away_form_score'] = parse_form_score(info['away_form'])
    info['form_diff'] = info['home_form_score'] - info['away_form_score']
    
    return info


def extract_odds_weighted(content):
    """提取初盘和即时赔率数据（加权版：精选大公司）"""
    odds_data = {'initial': [], 'realtime': []}
    
    # 定义公司权重（根据可靠性和市场影响力）
    company_weights = {
        '竞*官*': 0.30,      # 竞彩官方 - 中国市场核心
        '威**尔': 0.15,      # 威廉希尔 - 国际权威
        '立*': 0.15,         # 立博 - 国际权威
        '**t3*5': 0.15,      # Bet365 - 国际权威
        'Pi****le平*': 0.10, # Pinnacle - 专业玩家参考
        'S**I': 0.05,        # SNAI - 欧洲老牌
        'B**n': 0.05,        # Bwin - 欧洲知名
        '伟*': 0.03,         # 伟德 - 亚洲知名
        '易*博': 0.02,       # 易胜博 - 亚洲
    }
    
    # 提取初盘赔率
    initial_pattern = r'initial_odds\s*=\s*\[(.*?)\]'
    initial_match = re.search(initial_pattern, content, re.DOTALL)
    if initial_match:
        odds_text = initial_match.group(1)
        # 提取带注释的赔率数据
        lines = odds_text.strip().split('\n')
        weighted_odds = []
        total_weight = 0
        
        for line in lines:
            # 提取元组和公司名
            tuple_match = re.search(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', line)
            if tuple_match:
                home, draw, away = float(tuple_match.group(1)), float(tuple_match.group(2)), float(tuple_match.group(3))
                
                # 查找公司权重
                weight = 0.01  # 默认小权重
                for company, w in company_weights.items():
                    if company in line:
                        weight = w
                        break
                
                weighted_odds.append((home, draw, away, weight))
                total_weight += weight
        
        # 计算加权平均
        if weighted_odds and total_weight > 0:
            home_avg = sum(o[0] * o[3] for o in weighted_odds) / total_weight
            draw_avg = sum(o[1] * o[3] for o in weighted_odds) / total_weight
            away_avg = sum(o[2] * o[3] for o in weighted_odds) / total_weight
            odds_data['initial'] = [(home_avg, draw_avg, away_avg)]
    
    # 提取即时赔率（同样加权）
    realtime_pattern = r'realtime_odds\s*=\s*\[(.*?)\]'
    realtime_match = re.search(realtime_pattern, content, re.DOTALL)
    if realtime_match:
        odds_text = realtime_match.group(1)
        lines = odds_text.strip().split('\n')
        weighted_odds = []
        total_weight = 0
        
        for line in lines:
            tuple_match = re.search(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', line)
            if tuple_match:
                home, draw, away = float(tuple_match.group(1)), float(tuple_match.group(2)), float(tuple_match.group(3))
                
                weight = 0.01
                for company, w in company_weights.items():
                    if company in line:
                        weight = w
                        break
                
                weighted_odds.append((home, draw, away, weight))
                total_weight += weight
        
        if weighted_odds and total_weight > 0:
            home_avg = sum(o[0] * o[3] for o in weighted_odds) / total_weight
            draw_avg = sum(o[1] * o[3] for o in weighted_odds) / total_weight
            away_avg = sum(o[2] * o[3] for o in weighted_odds) / total_weight
            odds_data['realtime'] = [(home_avg, draw_avg, away_avg)]
    
    return odds_data


def extract_odds(content):
    """提取初盘和即时赔率数据（兼容旧版：简单平均）"""
    odds_data = {'initial': [], 'realtime': []}
    
    # 提取初盘赔率
    initial_pattern = r'initial_odds\s*=\s*\[(.*?)\]'
    initial_match = re.search(initial_pattern, content, re.DOTALL)
    if initial_match:
        odds_text = initial_match.group(1)
        # 提取所有元组
        tuples = re.findall(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', odds_text)
        odds_data['initial'] = [(float(t[0]), float(t[1]), float(t[2])) for t in tuples]
    
    # 提取即时赔率
    realtime_pattern = r'realtime_odds\s*=\s*\[(.*?)\]'
    realtime_match = re.search(realtime_pattern, content, re.DOTALL)
    if realtime_match:
        odds_text = realtime_match.group(1)
        tuples = re.findall(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', odds_text)
        odds_data['realtime'] = [(float(t[0]), float(t[1]), float(t[2])) for t in tuples]
    
    return odds_data


def calculate_average_odds(odds_list):
    """计算平均赔率"""
    if not odds_list:
        return (0, 0, 0)
    
    home_sum = sum(o[0] for o in odds_list)
    draw_sum = sum(o[1] for o in odds_list)
    away_sum = sum(o[2] for o in odds_list)
    n = len(odds_list)
    
    return (home_sum/n, draw_sum/n, away_sum/n)


def calculate_odds_change(initial_avg, realtime_avg):
    """计算赔率变化百分比"""
    if initial_avg[0] == 0:
        return (0, 0, 0)
    
    home_change = ((realtime_avg[0] - initial_avg[0]) / initial_avg[0]) * 100
    draw_change = ((realtime_avg[1] - initial_avg[1]) / initial_avg[1]) * 100
    away_change = ((realtime_avg[2] - initial_avg[2]) / initial_avg[2]) * 100
    
    return (home_change, draw_change, away_change)


def calculate_probabilities(avg_odds):
    """根据赔率计算隐含概率"""
    home, draw, away = avg_odds
    total = (1/home) + (1/draw) + (1/away)
    
    home_prob = (1/home) / total * 100
    draw_prob = (1/draw) / total * 100
    away_prob = (1/away) / total * 100
    
    return (home_prob, draw_prob, away_prob)


def determine_macao_direction(macao_tip, home_team, away_team):
    """判断澳门推荐方向（V2优化版：增加繁体/别名映射）"""
    if not macao_tip:
        return "未知"
    
    # V2新增：繁体/别名映射表
    team_aliases = {
        '巴塞羅那': '巴塞罗那', '國際邁亞密': '迈阿密国际', '特羅素': '特罗姆瑟',
        '紐卡素': '纽卡斯尔', '熱刺': '热刺', '阿士東維拉': '阿斯顿维拉',
        '韋斯咸': '西汉姆联', '愛華頓': '埃弗顿', '水晶宮': '水晶宫',
        '諾定咸森林': '诺丁汉森林', '白禮頓': '布莱顿', '賓福特': '布伦特福德',
        '富咸': '富勒姆', '修咸頓': '南安普顿', '葉士域治': '伊普斯维奇',
        '李斯特城': '莱斯特城', '曼聯': '曼联', '車路士': '切尔西',
        '阿仙奴': '阿森纳', '皇家馬德里': '皇马', '馬德里體育會': '马竞',
        '西維爾': '塞维利亚', '華倫西亞': '瓦伦西亚', '畢爾包': '毕尔巴鄂',
        '貝迪斯': '贝蒂斯', '切爾達': '塞尔塔', '艾拉維斯': '阿拉维斯',
        '祖雲達斯': '尤文图斯', '國際米蘭': '国际米兰', 'AC米蘭': 'AC米兰',
        '阿特蘭大': '亚特兰大', '羅馬': '罗马', '拉素': '拉齐奥',
        '費倫天拿': '佛罗伦萨', '博洛尼亞': '博洛尼亚', '拖連奴': '都灵',
        '烏甸尼斯': '乌迪内斯', '維羅納': '维罗纳', '萊切': '莱切',
        '卡利亞里': '卡利亚里', '熱拿亞': '热那亚', '史帕爾': '斯帕尔',
        '克雷莫納': '克雷莫纳', '蒙扎': '蒙扎', '帕爾馬': '帕尔马',
        '恩波利': '恩波利', '比薩': '比萨', '雷吉納': '雷吉纳',
    }
    
    # 替换别名
    normalized_tip = macao_tip
    for alias, standard in team_aliases.items():
        if alias in normalized_tip:
            normalized_tip = normalized_tip.replace(alias, standard)
    
    tip = normalized_tip.lower()
    home_name = home_team.lower()
    away_name = away_team.lower()
    
    # 提取主客队名称关键词
    home_keywords = home_name.replace('fc', '').replace('联', '').strip()
    away_keywords = away_name.replace('fc', '').replace('联', '').strip()
    
    if '和' in normalized_tip or '平' in normalized_tip:
        return "平局"
    elif home_keywords in tip or any(kw in tip for kw in home_team.split() if len(kw) >= 2):
        return "主胜"
    elif away_keywords in tip or any(kw in tip for kw in away_team.split() if len(kw) >= 2):
        return "客胜"
    else:
        # 尝试模糊匹配
        if any(word in normalized_tip for word in ['贏', '胜', '赢']):
            if home_team.split()[0] in normalized_tip:
                return "主胜"
            elif away_team.split()[0] in normalized_tip:
                return "客胜"
    
    return "未知"


def is_derby_match(home_team, away_team, league):
    """V2新增：识别德比战/关键战"""
    derby_pairs = [
        ('热刺', '阿森纳', '北伦敦德比'), ('利物浦', '埃弗顿', '默西塞德德比'),
        ('曼联', '曼城', '曼彻斯特德比'), ('纽卡斯尔', '桑德兰', '东北德比'),
        ('皇马', '马竞', '马德里德比'), ('皇马', '巴萨', '国家德比'),
        ('巴萨', '西班牙人', '加泰德比'), ('国米', '米兰', '米兰德比'),
        ('罗马', '拉齐奥', '罗马德比'), ('尤文', '都灵', '都灵德比'),
        ('多特蒙德', '沙尔克', '鲁尔德比'), ('费耶诺德', '阿贾克斯', '荷兰德比'),
    ]
    
    for h, a, name in derby_pairs:
        if (h in home_team and a in away_team) or (a in home_team and h in away_team):
            return True, name
    
    return False, None


def analyze_match(match_info, odds_data):
    """分析单场比赛"""
    result = {}
    
    # 计算平均赔率
    initial_avg = calculate_average_odds(odds_data['initial'])
    realtime_avg = calculate_average_odds(odds_data['realtime'])
    
    # 计算赔率变化
    odds_change = calculate_odds_change(initial_avg, realtime_avg)
    
    # 计算概率
    probabilities = calculate_probabilities(realtime_avg)
    
    # 确定最高概率方向
    max_prob = max(probabilities)
    if probabilities[0] == max_prob:
        predicted = "主胜"
    elif probabilities[1] == max_prob:
        predicted = "平局"
    else:
        predicted = "客胜"
    
    # 澳门方向
    macao_direction = determine_macao_direction(
        match_info.get('macao_tip', ''), 
        match_info.get('home_team', ''), 
        match_info.get('away_team', '')
    )
    
    # V2新增：识别德比战
    is_derby, derby_name = is_derby_match(
        match_info.get('home_team', ''), 
        match_info.get('away_team', ''),
        match_info.get('league', '')
    )
    
    # 判断筹码状态
    home_change, draw_change, away_change = odds_change
    changes = [abs(home_change), abs(draw_change), abs(away_change)]
    max_change = max(changes)
    
    if max_change < 0.5:
        chip_status = "全锁定"
    elif sum(1 for c in changes if c > 2) == 1:
        chip_status = "单向锁定"
    elif all(0.5 <= c <= 2 for c in changes):
        chip_status = "均衡分流"
    elif max_change > 10:
        chip_status = "极端造热"
    elif max_change > 5:
        chip_status = "单向造热"
    else:
        chip_status = "正常波动"
    
    # 综合判断
    confidence = max_prob
    form_diff = match_info.get('form_diff', 0)
    
    result = {
        'match_info': match_info,
        'is_derby': is_derby,
        'derby_name': derby_name,
        'initial_avg': initial_avg,
        'realtime_avg': realtime_avg,
        'odds_change': odds_change,
        'probabilities': probabilities,
        'predicted': predicted,
        'confidence': confidence,
        'macao_direction': macao_direction,
        'chip_status': chip_status,
        'form_diff': form_diff
    }
    
    return result


def generate_prediction(analysis):
    """生成预测建议（V2优化版）"""
    pred = analysis['predicted']
    conf = analysis['confidence']
    macao = analysis['macao_direction']
    home_change, draw_change, away_change = analysis['odds_change']
    form_diff = analysis['form_diff']
    chip_status = analysis['chip_status']
    home_avg, draw_avg, away_avg = analysis['realtime_avg']
    is_derby = analysis.get('is_derby', False)
    derby_name = analysis.get('derby_name', '')
    
    predictions = []
    reasons = []
    triggered_rules = []  # 记录触发的所有规律
    
    # V2新增：德比战特殊处理
    if is_derby:
        predictions.append(("德比战", 50, f"德比战:{derby_name}"))
        reasons.append(f"【{derby_name}】德比战常规规律失效，建议观望或看临场")
        triggered_rules.append("德比战")
    
    # 规律五（V3.1修正版）：主胜升幅>5% 且 客胜变化>-5% 且 |近况差|>3 且 澳门推平 → 和局
    # V3.1修正：增加"澳门推平"条件
    # 修正依据：周五004澳门推主+主升=正常市场调整，不触发规律五
    if home_change > 5 and away_change > -5 and abs(form_diff) > 3 and macao == "平局":
        predictions.append(("平局", 85, "规律五V3.1：主升>5%+澳门推平+|差|>3"))
        reasons.append("主胜赔率大幅上升(>5%)+澳门推平局+近况有差距，和局概率高")
        triggered_rules.append("规律五V3.1")
    
    # 规律五（主客双造热版V3.1）：主胜升幅>5% 且 客胜降幅>5% 且 |近况差|>3 且 澳门推平 → 看客队
    # V3.1修正：增加"澳门推平"条件（澳门推主时不触发）
    if home_change > 5 and away_change < -5 and abs(form_diff) > 3 and macao == "平局":
        predictions.append(("客胜", 75, "规律五V3.1-双热：主客均造热+澳门推平看客胜"))
        reasons.append("主客均被造热+澳门推平局，客胜降幅更大，倾向客胜")
        triggered_rules.append("规律五V3.1-双热")
    
    # 规律S（V3.1修正版）：近况持平+赔率大幅变化 → 反向
    # V3.1修正：增加"澳门推方向≠造热方向"条件 + 赔率绝对值排除
    # V3.1补充：澳门推平时规律S不触发（平局方向本身有信号意义）
    # V3.1补充2：被反向方向赔率≥3.4时不触发（庄家赔付压力大=庄家无法完全诱导）
    # 修正依据：周五006澳门推客+客赔3.44高→实盘；周五012澳门推平+平赔2.76低→实盘
    # 条件：|近况差|≤2 且 任一方向赔率变化>5% 且 澳门推方向≠造热方向 且 澳门≠平局 且 反向方向赔率<3.4
    if abs(form_diff) <= 2 and max(abs(home_change), abs(draw_change), abs(away_change)) > 5:
        # 判断哪个方向被造热
        hot_direction = None  # 被造热的方向
        hot_change = 0
        if away_change < -5:
            hot_direction = "客胜"
            hot_change = away_change
        elif home_change < -5:
            hot_direction = "主胜"
            hot_change = home_change
        elif home_change > 5:
            hot_direction = "客胜"  # 主被推离 = 实际是客胜吸引筹码
            hot_change = home_change
        elif away_change > 5:
            hot_direction = "主胜"  # 客被推离 = 实际是主胜吸引筹码
            hot_change = away_change
        
        if hot_direction:
            # V3.1核心修正：澳门推方向 ≠ 造热方向 且 澳门≠平局 才触发
            if macao != hot_direction and macao != "平局":
                # 反向方向赔率≥3.4时不触发（庄家赔付压力大=真实概率高）
                if hot_direction == "客胜" and home_avg < 3.4:
                    predictions.append(("主胜", 80, "规律S：近况持平+客造热反向(澳门≠客)"))
                    reasons.append(f"近况差{form_diff}势均力敌，客胜造热({away_change:.1f}%)但澳门不推客，反向主胜")
                    triggered_rules.append("规律S")
                elif hot_direction == "主胜" and away_avg < 3.4:
                    predictions.append(("客胜", 80, "规律S：近况持平+主造热反向(澳门≠主)"))
                    reasons.append(f"近况差{form_diff}势均力敌，主胜造热({home_change:.1f}%)但澳门不推主，反向客胜")
                    triggered_rules.append("规律S")
                # 赔率≥3.4时：庄家赔付压力大，规律S信号弱化，不预测
    
    # 规律N（V3.1修正版）：规律五+澳门推客+客队极端造热+客赔≥2.5 → 反向主胜
    # V3.1修正：增加客胜赔率绝对值排除（<2.5=实盘确认，庄家能承受赔付）
    # 修正依据：周五001客赔2.57接近2.5，庄家能承受赔付，规律R假造热应优先
    if home_change > 5 and macao == "客胜" and away_change < -10 and away_avg >= 2.5:
        predictions.append(("主胜", 80, "规律N：规律五+极端造热客队"))
        reasons.append("主胜升幅>5%+澳门推客+客队极端造热，反向主胜")
        triggered_rules.append("规律N")
    
    # 规律O（V3修正版）：近况差+8以上+赔率微变<2% → 主队打出
    # 修正：明确区分"微变"和"造热"两种情况
    if form_diff >= 8 and max(abs(home_change), abs(draw_change), abs(away_change)) < 2:
        predictions.append(("主胜", 80, "规律O：近况差大+赔率微变"))
        reasons.append(f"近况差+{form_diff}，赔率微变<2%，主队打出信号")
        triggered_rules.append("规律O")
    
    # 规律U（V3.1修正版）：近况碾压+主胜造热 → 防平
    # V3.1修正：增加"澳门推方向≠造热方向"条件
    # 修正依据：如果澳门也推主+主造热=不是诱导而是实盘确认，不触发
    # 条件：近况差≥+8 + 主胜降幅>5% + 客胜升幅>5% + 澳门推方向≠主胜
    if form_diff >= 8 and home_change < -5 and away_change > 5 and macao != "主胜":
        predictions.append(("平局", 82, "规律U：近况碾压+主造热+澳门不推主→防平"))
        reasons.append(f"近况差+{form_diff}主队碾压，主胜造热({home_change:.1f}%)但澳门不推主，诱导信号，防平局")
        triggered_rules.append("规律U")
    
    # 规律V（V3.1修正版）：近况碾压客+客胜造热 → 防平
    # V3.1修正：增加"澳门推方向≠造热方向"条件
    # 修正依据：周五001澳门推客+客造热=实盘确认，规律V不应触发
    # 条件：近况差≤-8 + 客胜降幅>5% + 主胜升幅>5% + 澳门推方向≠客胜
    if form_diff <= -8 and away_change < -5 and home_change > 5 and macao != "客胜":
        predictions.append(("平局", 82, "规律V：近况碾压客+客造热+澳门不推客→防平"))
        reasons.append(f"近况差{form_diff}客队碾压，客胜造热({away_change:.1f}%)但澳门不推客，诱导信号，防平局")
        triggered_rules.append("规律V")
    
    # 规律P：平赔3.0-3.2+澳门推平局+变化<2% → 诱平，反向打出
    if 3.0 <= draw_avg <= 3.2 and macao == "平局" and abs(draw_change) < 2:
        if away_change > 0:  # 客胜赔率上升，被忽视
            predictions.append(("客胜", 75, "规律P：诱平陷阱"))
            reasons.append("平赔3.0-3.2诱平区间，筹码分散主/平，客队漏网")
            triggered_rules.append("规律P")
    
    # 规律Q：近况差极大+置信度<65%+赔率全变>2% → 防过热平局
    if form_diff >= 10 and conf < 65 and min(abs(home_change), abs(draw_change), abs(away_change)) > 2:
        predictions.append(("平局", 70, "规律Q：过热防平"))
        reasons.append("近况差极大但置信度不匹配，赔率变化有造热嫌疑，防平局")
        triggered_rules.append("规律Q")
    
    # 规律R：真假造热辨别
    # R1: 澳门推客 + 客造热
    if macao == "客胜" and away_change < -10:
        # 真造热：其他两向均升（无分流出口）
        if home_change > 0 and draw_change > 0:
            predictions.append(("主胜", 85, "规律R：真造热诱盘"))
            reasons.append("澳门推客+客造热>10%，主/平均升无分流，反向主胜")
            triggered_rules.append("规律R-真造热")
        # 假造热：至少一向同步降（有分流出口）
        elif draw_change < 0 or home_change < 0:
            predictions.append(("客胜", 75, "规律R：假造热实盘"))
            reasons.append("澳门推客+客降，但平/主同步降分流筹码，客胜实盘")
            triggered_rules.append("规律R-假造热")
    
    # R2: 澳门推主 + 主造热
    if macao == "主胜" and home_change < -10:
        # 真造热：其他两向均升（无分流出口）
        if away_change > 0 and draw_change > 0:
            predictions.append(("客胜", 85, "规律R：真造热诱盘"))
            reasons.append("澳门推主+主造热>10%，客/平均升无分流，反向客胜")
            triggered_rules.append("规律R-真造热")
        # 假造热：至少一向同步降（有分流出口）
        elif draw_change < 0 or away_change < 0:
            predictions.append(("主胜", 75, "规律R：假造热实盘"))
            reasons.append("澳门推主+主降，但平/客同步降分流筹码，主胜实盘")
            triggered_rules.append("规律R-假造热")
    
    # 规律H：置信度≥66%+赔率变化均<5%+澳门推非主方向 → 按置信度方向打出
    if conf >= 66 and max(abs(home_change), abs(draw_change), abs(away_change)) < 5:
        if macao != pred and pred == "主胜":
            predictions.append(("主胜", 78, "规律H：高置信度热度分散"))
            reasons.append("置信度≥66%，赔率变化<5%，热度分散≠结果不打出")
            triggered_rules.append("规律H")
    
    # 规律一：置信度≥66%+澳门同向 → 可信
    if conf >= 66:
        if (pred == "主胜" and macao == "主胜") or (pred == "客胜" and macao == "客胜"):
            predictions.append((pred, 82, "规律一：高置信度+澳门同向"))
            reasons.append(f"置信度{conf:.1f}%≥66%，澳门推荐一致，可信打出")
            triggered_rules.append("规律一")
    
    # 规律二：平局难出条件
    if draw_avg < 3.0 or draw_change < -5:
        if pred == "平局":
            # 平局难出，转向其他方向
            if home_change < away_change:
                predictions.append(("主胜", 65, "规律二：平局难出转主胜"))
                reasons.append("平赔<3.0或降幅>5%，平局难出，转向主胜")
                triggered_rules.append("规律二")
            else:
                predictions.append(("客胜", 65, "规律二：平局难出转客胜"))
                reasons.append("平赔<3.0或降幅>5%，平局难出，转向客胜")
                triggered_rules.append("规律二")
    
    # 规律G：置信度≥66%时，根据变化幅度判断
    if conf >= 66:
        if abs(home_change) < 2 and form_diff >= 5:
            predictions.append(("主胜", 75, "规律G：高置信度+小变化+近况优"))
            reasons.append("高置信度+赔率变化小+近况差大，可能大胜")
            triggered_rules.append("规律G")
        elif home_change < -4:
            predictions.append(("平局", 60, "规律G：主胜造热防冷"))
            reasons.append("主胜大幅造热(>4%)，需防平局")
            triggered_rules.append("规律G-防冷")
    
    # 规律I：极端造热+近况差≤-10+平赔不变 → 平局
    if home_change < -10 and away_change > 10 and form_diff <= -10 and abs(draw_change) < 1:
        predictions.append(("平局", 70, "规律I：极端造热平局"))
        reasons.append("极端造热客队+近况客优+平赔不变，平局")
        triggered_rules.append("规律I")
    
    # 规律J（V3.1修正版）：澳门推平+平赔<3.0+主升+客降+平赔不变或微升 → 客胜
    # V3.1修正：增加"平赔不降"条件（draw_change >= -2）
    # 修正依据：周五012平赔从2.99降到2.76(-7.9%)，平局也在承接筹码，客胜不是唯一方向
    if macao == "平局" and draw_avg < 3.0 and home_change > 0 and away_change < 0 and draw_change >= -2:
        predictions.append(("客胜", 72, "规律J：推平诱客"))
        reasons.append("澳门推平但平赔<3.0且不降，主升客降，客胜")
        triggered_rules.append("规律J")
    
    # 规律K：客队强造热+近况持平+平降>3% → 主队不败
    if away_change < -8 and abs(form_diff) <= 2 and draw_change < -3:
        predictions.append(("主胜/平局", 68, "规律K：客队过热主不败"))
        reasons.append("客队强造热但近况持平，平降分流，主队不败")
        triggered_rules.append("规律K")
    
    # 规律L：极端造热客队+近况差≤-10+平赔不降反升 → 主胜
    if away_change < -10 and form_diff <= -10 and draw_change > 0:
        predictions.append(("主胜", 75, "规律L：极端造热反向主胜"))
        reasons.append("极端造热客队+近况客优+平赔反升，主胜")
        triggered_rules.append("规律L")
    
    # 默认预测（V2改进版）
    if not predictions:
        if conf >= 66:
            predictions.append((pred, conf, "高置信度"))
            reasons.append(f"置信度{conf:.1f}%≥66%，按概率最高方向")
        elif conf >= 55:
            predictions.append((pred, conf, "中等置信度"))
            reasons.append(f"置信度{conf:.1f}%，结果可能被平局打断")
        else:
            # V2改进：低置信度不给出方向，统一观望
            predictions.append(("观望", conf, "低置信度V2：建议观望"))
            reasons.append(f"置信度{conf:.1f}%<55%，数据不足，建议观望不投注")
    
    # V2改进：多重规律投票机制
    if len(predictions) > 1:
        # 统计各方向的规律和置信度
        direction_votes = {}
        for pred, conf, rule in predictions:
            if pred not in direction_votes:
                direction_votes[pred] = {'count': 0, 'total_conf': 0, 'rules': []}
            direction_votes[pred]['count'] += 1
            direction_votes[pred]['total_conf'] += conf
            direction_votes[pred]['rules'].append(rule)
        
        # 选择票数最多且平均置信度最高的方向
        best_direction = None
        best_score = 0
        for direction, data in direction_votes.items():
            avg_conf = data['total_conf'] / data['count']
            # 票数权重60%，平均置信度权重40%
            score = data['count'] * 60 + avg_conf * 0.4
            if score > best_score:
                best_score = score
                best_direction = direction
        
        if best_direction:
            best_data = direction_votes[best_direction]
            best_conf = best_data['total_conf'] / best_data['count']
            best_rule = f"投票胜出({best_data['count']}条规律)"
            best_pred = (best_direction, best_conf, best_rule)
        else:
            best_pred = max(predictions, key=lambda x: x[1])
    else:
        best_pred = max(predictions, key=lambda x: x[1])
    
    return {
        'prediction': best_pred[0],
        'confidence': best_pred[1],
        'rule': best_pred[2],
        'reason': ' | '.join(reasons),
        'triggered_rules': triggered_rules,
        'all_predictions': predictions
    }


def format_match_output(match_id, analysis, prediction):
    """格式化单场比赛输出"""
    info = analysis['match_info']
    home_change, draw_change, away_change = analysis['odds_change']
    home_prob, draw_prob, away_prob = analysis['probabilities']
    home_avg, draw_avg, away_avg = analysis['realtime_avg']
    
    output = []
    output.append(f"\n{'='*60}")
    output.append(f"【{match_id}】{info['home_team']} vs {info['away_team']}")
    output.append(f"{'='*60}")
    output.append(f"联赛：{info['league']} | 时间：{info['match_time']}")
    output.append(f"澳门推荐：{info['macao_tip']} → 解析：{analysis['macao_direction']}")
    output.append(f"\n近况评分：")
    output.append(f"  主队({info['home_form']}): {info['home_form_score']}/18分")
    output.append(f"  客队({info['away_form']}): {info['away_form_score']}/18分")
    output.append(f"  近况差：{analysis['form_diff']:+.0f} (正值=主队优势)")
    output.append(f"\n赔率分析（平均）：")
    output.append(f"  初盘：主{analysis['initial_avg'][0]:.2f} 平{analysis['initial_avg'][1]:.2f} 客{analysis['initial_avg'][2]:.2f}")
    output.append(f"  即时：主{home_avg:.2f} 平{draw_avg:.2f} 客{away_avg:.2f}")
    output.append(f"  变化：主{home_change:+.1f}% 平{draw_change:+.1f}% 客{away_change:+.1f}%")
    output.append(f"  筹码状态：{analysis['chip_status']}")
    output.append(f"\n概率分布：")
    output.append(f"  主胜：{home_prob:.1f}% | 平局：{draw_prob:.1f}% | 客胜：{away_prob:.1f}%")
    output.append(f"  最高置信度：{analysis['confidence']:.1f}%")
    output.append(f"\n预测结果：")
    output.append(f"  ★ 推荐：{prediction['prediction']}")
    output.append(f"  ★ 信心：{prediction['confidence']:.0f}%")
    output.append(f"  ★ 依据：{prediction['rule']}")
    output.append(f"  ★ 理由：{prediction['reason']}")
    if prediction['triggered_rules']:
        output.append(f"  ★ 触发规律：{', '.join(prediction['triggered_rules'])}")
    output.append(f"{'='*60}")
    
    return '\n'.join(output)


def main():
    """主函数"""
    # 源数据目录
    source_dir = r"d:\work\workbuddy\足球预测\分析模板\3.28"
    
    # 获取所有源数据文件
    pattern = os.path.join(source_dir, "周六*_源数据.md")
    files = sorted(glob.glob(pattern))
    
    print(f"找到 {len(files)} 场比赛的源数据文件")
    
    if not files:
        print("未找到源数据文件，请检查路径！")
        return
    
    all_results = []
    stable_picks = []  # 最稳的比赛
    upset_picks = []   # 可能爆冷的比赛
    form_check = []    # 近况差复核
    
    for file_path in files:
        # 提取比赛编号
        filename = os.path.basename(file_path)
        match_id_match = re.search(r'(周六\d+)', filename)
        match_id = match_id_match.group(1) if match_id_match else filename
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取信息
            match_info = extract_match_info(content)
            # 使用加权版赔率提取（精选大公司）
            odds_data = extract_odds_weighted(content)
            
            if not odds_data['initial'] or not odds_data['realtime']:
                print(f"警告：{match_id} 赔率数据不完整，跳过")
                continue
            
            # 分析比赛
            analysis = analyze_match(match_info, odds_data)
            prediction = generate_prediction(analysis)
            
            # 格式化输出
            output = format_match_output(match_id, analysis, prediction)
            all_results.append(output)
            
            # 收集加权赔率信息用于报告
            initial_weighted = odds_data['initial'][0] if odds_data['initial'] else (0, 0, 0)
            realtime_weighted = odds_data['realtime'][0] if odds_data['realtime'] else (0, 0, 0)
            
            # 收集近况差复核数据
            form_check.append({
                'match_id': match_id,
                'home_team': match_info['home_team'],
                'away_team': match_info['away_team'],
                'home_form': match_info['home_form'],
                'away_form': match_info['away_form'],
                'home_score': match_info['home_form_score'],
                'away_score': match_info['away_form_score'],
                'form_diff': analysis['form_diff']
            })
            
            # 最稳的比赛：高置信度+规律一致
            if analysis['confidence'] >= 66 and len(prediction['triggered_rules']) >= 2:
                stable_picks.append({
                    'match_id': match_id,
                    'teams': f"{match_info['home_team']} vs {match_info['away_team']}",
                    'prediction': prediction['prediction'],
                    'confidence': analysis['confidence'],
                    'rules': prediction['triggered_rules'],
                    'form_diff': analysis['form_diff']
                })
            
            # 可能爆冷的比赛：造热信号+反向规律
            home_change, draw_change, away_change = analysis['odds_change']
            is_upset_candidate = False
            upset_reason = []
            
            # 规律R真造热
            if "规律R-真造热" in prediction['triggered_rules']:
                is_upset_candidate = True
                upset_reason.append("真造热诱盘")
            
            # 极端造热
            if max(abs(home_change), abs(draw_change), abs(away_change)) > 15:
                is_upset_candidate = True
                upset_reason.append("极端赔率变化")
            
            # 规律N反向
            if "规律N" in prediction['triggered_rules']:
                is_upset_candidate = True
                upset_reason.append("规律N反向信号")
            
            # 澳门与赔率反向
            if analysis['macao_direction'] != "未知":
                if (analysis['macao_direction'] == "主胜" and home_change > 5) or \
                   (analysis['macao_direction'] == "客胜" and away_change > 5):
                    is_upset_candidate = True
                    upset_reason.append("澳门与赔率反向")
            
            if is_upset_candidate:
                upset_picks.append({
                    'match_id': match_id,
                    'teams': f"{match_info['home_team']} vs {match_info['away_team']}",
                    'prediction': prediction['prediction'],
                    'confidence': analysis['confidence'],
                    'upset_reason': upset_reason,
                    'form_diff': analysis['form_diff'],
                    'macao': analysis['macao_direction']
                })
            
        except Exception as e:
            print(f"处理 {match_id} 时出错: {e}")
            continue
    
    # 生成完整报告
    report = []
    report.append("="*70)
    report.append("3月28日周六15场比赛分析报告")
    report.append("="*70)
    report.append("")
    
    # 添加所有比赛详细分析
    report.extend(all_results)
    
    # 添加近况差复核
    report.append("\n" + "="*70)
    report.append("【近况差计算复核】")
    report.append("="*70)
    report.append("计算规则：最近一场(左起第1个)×2，其他4场×1 | 赢=3分 平=1分 输=0分")
    report.append("-"*70)
    for item in form_check:
        report.append(f"{item['match_id']}: {item['home_team']} vs {item['away_team']}")
        report.append(f"  主队({item['home_form']}): {item['home_score']}/18分")
        report.append(f"  客队({item['away_form']}): {item['away_score']}/18分")
        report.append(f"  → 近况差: {item['form_diff']:+d}")
        report.append("")
    
    # 添加最稳比赛
    report.append("\n" + "="*70)
    report.append(f"【最稳的比赛】共{len(stable_picks)}场")
    report.append("="*70)
    report.append("筛选条件：置信度≥66% + 触发≥2条规律")
    report.append("-"*70)
    if stable_picks:
        for i, pick in enumerate(stable_picks, 1):
            report.append(f"{i}. {pick['match_id']} {pick['teams']}")
            report.append(f"   预测: {pick['prediction']} | 置信度: {pick['confidence']:.1f}%")
            report.append(f"   近况差: {pick['form_diff']:+d} | 触发规律: {', '.join(pick['rules'])}")
            report.append("")
    else:
        report.append("无满足条件的最稳比赛")
    
    # 添加可能爆冷比赛
    report.append("\n" + "="*70)
    report.append(f"【可能爆冷的比赛】共{len(upset_picks)}场")
    report.append("="*70)
    report.append("筛选条件：真造热/极端变化/反向信号")
    report.append("-"*70)
    if upset_picks:
        for i, pick in enumerate(upset_picks, 1):
            report.append(f"{i}. {pick['match_id']} {pick['teams']}")
            report.append(f"   预测: {pick['prediction']} | 置信度: {pick['confidence']:.1f}%")
            report.append(f"   澳门: {pick['macao']} | 近况差: {pick['form_diff']:+d}")
            report.append(f"   爆冷信号: {', '.join(pick['upset_reason'])}")
            report.append("")
    else:
        report.append("无明显的爆冷信号比赛")
    
    # 保存报告
    output_file = r"d:\work\workbuddy\足球预测\3.28_analysis_result.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    print(f"\n分析完成！结果已保存到: {output_file}")
    print(f"总计分析 {len(all_results)} 场比赛")
    print(f"最稳比赛: {len(stable_picks)} 场")
    print(f"可能爆冷: {len(upset_picks)} 场")


if __name__ == "__main__":
    main()
