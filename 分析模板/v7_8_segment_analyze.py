# -*- coding: utf-8 -*-
"""
V7+8变化 分段权重分析法
从源数据文件中提取赔率数据，计算V7预测，然后使用分段公式进行预测

使用方法:
  python v7_8_segment_analyze.py                    # 分析当天数据
  python v7_8_segment_analyze.py 3.17               # 分析指定日期文件夹
  python v7_8_segment_analyze.py 3.17 -o result.md  # 输出到文件
"""

import os
import re
import json
import argparse
from pathlib import Path

# ============== 分段配置 ==============
SEGMENT_CONFIG = {
    '55-60%': {'t1': 30, 't2': 0, 't3': 15, 'default': '客胜'},
    '60-65%': {'t1': 45, 't2': 0, 't3': 15, 'default': '主胜'},
    '65-70%': {'t1': 60, 't2': 0, 't3': 15, 'default': '客胜'},
    '70-75%': {'t1': 50, 't2': 0, 't3': 15, 'default': '平局'},
    '75-80%': {'t1': 60, 't2': 0, 't3': 15, 'default': '主胜'},
    '80%+':   {'t1': 25, 't2': 0, 't3': 15, 'default': '主胜'},
}

def get_segment(conf):
    """根据置信度获取分段"""
    if 55 <= conf < 60:
        return '55-60%'
    elif 60 <= conf < 65:
        return '60-65%'
    elif 65 <= conf < 70:
        return '65-70%'
    elif 70 <= conf < 75:
        return '70-75%'
    elif 75 <= conf < 80:
        return '75-80%'
    elif conf >= 80:
        return '80%+'
    else:
        return '低于55%'

def calculate_v7_from_odds(initial_odds, realtime_odds):
    """
    从赔率数据计算V7预测
    - 置信度: 基于赔率计算的胜率
    - 胜率差: 主队胜率 - 客队胜率
    """
    if not initial_odds or not realtime_odds:
        return None
    
    # 计算平均赔率
    init_home = sum(o[0] for o in initial_odds) / len(initial_odds)
    init_draw = sum(o[1] for o in initial_odds) / len(initial_odds)
    init_away = sum(o[2] for o in initial_odds) / len(initial_odds)
    
    real_home = sum(o[0] for o in realtime_odds) / len(realtime_odds)
    real_draw = sum(o[1] for o in realtime_odds) / len(realtime_odds)
    real_away = sum(o[2] for o in realtime_odds) / len(realtime_odds)
    
    # 计算概率 (1/赔率)
    init_total = 1/init_home + 1/init_draw + 1/init_away
    real_total = 1/real_home + 1/real_draw + 1/real_away
    
    init_home_prob = (1/init_home) / init_total * 100
    init_draw_prob = (1/init_draw) / init_total * 100
    init_away_prob = (1/init_away) / init_total * 100
    
    real_home_prob = (1/real_home) / real_total * 100
    real_draw_prob = (1/real_draw) / real_total * 100
    real_away_prob = (1/real_away) / real_total * 100
    
    # 置信度: 即时概率的最大值及其对应选项
    probs = {'主胜': real_home_prob, '平局': real_draw_prob, '客胜': real_away_prob}
    max_option = max(probs, key=probs.get)
    max_prob = probs[max_option]
    confidence = int(max_prob)
    
    # 胜率差: 主队胜率 - 客队胜率
    win_rate_diff = int(real_home_prob - real_away_prob)
    
    return {
        'confidence': confidence,
        'confidence_option': max_option,  # 置信度对应的选项
        'win_rate_diff': win_rate_diff,
        'home_prob': int(real_home_prob),
        'draw_prob': int(real_draw_prob),
        'away_prob': int(real_away_prob),
        'init_probs': (init_home_prob, init_draw_prob, init_away_prob),
        'real_probs': (real_home_prob, real_draw_prob, real_away_prob),
    }

def count_ending_8(odds_list):
    """统计赔率中末尾为8的数量"""
    count = 0
    for odds in odds_list:
        # 主胜
        if int(odds[0] * 10) % 10 == 8 or int(odds[0]) % 10 == 8:
            count += 1
        # 平局
        if int(odds[1] * 10) % 10 == 8 or int(odds[1]) % 10 == 8:
            count += 1
        # 客胜
        if int(odds[2] * 10) % 10 == 8 or int(odds[2]) % 10 == 8:
            count += 1
    return count

def calculate_8_change(initial_odds, realtime_odds):
    """
    计算8变化，并说明赔率升降
    - 赔率下降 = 被看好 (更多8出现表示热度下降)
    - 赔率上升 = 不被看好
    """
    # 统计初盘末尾8数量
    init_8_home = sum(1 for o in initial_odds if str(o[0]).replace('.','').endswith('8'))
    init_8_draw = sum(1 for o in initial_odds if str(o[1]).replace('.','').endswith('8'))
    init_8_away = sum(1 for o in initial_odds if str(o[2]).replace('.','').endswith('8'))
    
    # 统计即时末尾8数量
    real_8_home = sum(1 for o in realtime_odds if str(o[0]).replace('.','').endswith('8'))
    real_8_draw = sum(1 for o in realtime_odds if str(o[1]).replace('.','').endswith('8'))
    real_8_away = sum(1 for o in realtime_odds if str(o[2]).replace('.','').endswith('8'))
    
    # 计算变化
    home_8 = real_8_home - init_8_home
    draw_8 = real_8_draw - init_8_draw
    away_8 = real_8_away - init_8_away
    
    # 计算赔率变化方向 (比较初盘和即时赔率)
    # 赔率下降=被看好(用↓表示)，赔率上升=不被看好(用↑表示)
    def get_odds_change(init_o, real_o):
        """返回赔率变化: 下降(被看好)=↓, 上升(不被看好)=↑, 相等=-"""
        init_avg = sum(o[init_o] for o in initial_odds) / len(initial_odds)
        real_avg = sum(o[real_o] for o in realtime_odds) / len(realtime_odds)
        if real_avg < init_avg - 0.05:
            return '↓'  # 赔率下降，被看好
        elif real_avg > init_avg + 0.05:
            return '↑'  # 赔率上升，不被看好
        else:
            return '-'  # 基本不变
    
    # 计算每个选项的赔率变化
    # 使用第一个赔率公司的数据
    if initial_odds and realtime_odds:
        home_change = get_odds_change(0, 0)
        draw_change = get_odds_change(1, 1)
        away_change = get_odds_change(2, 2)
    else:
        home_change = draw_change = away_change = '-'
    
    return {
        'home_8': home_8,
        'draw_8': draw_8,
        'away_8': away_8,
        'home_change': home_change,
        'draw_change': draw_change,
        'away_change': away_change,
    }

def parse_form_win_rate(content, team_type='主'):
    """
    从近况文字中提取胜率
    优先读取"胜率XX%"，次选从走势字符串WDLWW计算
    team_type: '主' 或 '客'
    """
    # 优先：从"主队近况 | 近10场，7胜2平1负 胜率70%"中提取
    pattern = rf'{team_type}队近况\s*\|\s*[^|]*胜率(\d+)%'
    m = re.search(pattern, content)
    if m:
        return int(m.group(1))
    
    # 次选：从"主队近况走势 | WWDLWW"计算
    form_pattern = rf'{team_type}队近况走势\s*\|\s*([WDLX]+)'
    m = re.search(form_pattern, content)
    if m:
        form = m.group(1).upper()
        if form:
            wins = sum(1 for c in form if c == 'W')
            return round(wins / len(form) * 100)
    
    return None

def parse_source_file(filepath):
    """解析源数据文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取基本信息
    filename = os.path.basename(filepath)
    match = re.search(r'([周][\u4e00-\u9fa5]\d+)_([^_]+)vs([^_]+)_', filename)
    if match:
        date_num = match.group(1)
        home_team = match.group(2)
        away_team = match.group(3)
    else:
        date_num = filename[:6]
        home_team = "未知"
        away_team = "未知"
    
    # 提取比赛信息
    league_match = re.search(r'赛事\s*\|\s*([^|]+)', content)
    league = league_match.group(1).strip() if league_match else "未知"

    # 提取球队状态胜率差
    home_win_rate = parse_form_win_rate(content, '主')
    away_win_rate = parse_form_win_rate(content, '客')
    if home_win_rate is not None and away_win_rate is not None:
        form_diff = home_win_rate - away_win_rate
    else:
        form_diff = None
    
    # 提取近况走势 (WDL)
    home_form_match = re.search(r'主队近况走势\s*\|\s*([WDL]+)', content)
    away_form_match = re.search(r'客队近况走势\s*\|\s*([WDL]+)', content)
    home_form = home_form_match.group(1).strip() if home_form_match else ''
    away_form = away_form_match.group(1).strip() if away_form_match else ''
    
    # 提取盘路走势 (WDL)
    home_handicap_match = re.search(r'主队盘路走势\s*\|\s*([WDL]+)', content)
    away_handicap_match = re.search(r'客队盘路走势\s*\|\s*([WDL]+)', content)
    home_handicap = home_handicap_match.group(1).strip() if home_handicap_match else ''
    away_handicap = away_handicap_match.group(1).strip() if away_handicap_match else ''
    
    # 提取澳门心水
    macao_tip_match = re.search(r'澳门推荐\s*\|\s*([^|]+)', content)
    macao_tip = macao_tip_match.group(1).strip() if macao_tip_match else ''
    
    # 提取初盘赔率
    init_odds = []
    init_section = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if init_section:
        odds_text = init_section.group(1)
        for line in odds_text.split('\n'):
            match = re.search(r'\((\d+\.?\d*),\s*(\d+\.?\d*),\s*(\d+\.?\d*)\)', line)
            if match:
                init_odds.append((float(match.group(1)), float(match.group(2)), float(match.group(3))))
    
    # 提取即时赔率
    real_odds = []
    real_section = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if real_section:
        odds_text = real_section.group(1)
        for line in odds_text.split('\n'):
            match = re.search(r'\((\d+\.?\d*),\s*(\d+\.?\d*),\s*(\d+\.?\d*)\)', line)
            if match:
                real_odds.append((float(match.group(1)), float(match.group(2)), float(match.group(3))))
    
    if not init_odds or not real_odds:
        return None
    
    # 计算V7数据
    v7_data = calculate_v7_from_odds(init_odds, real_odds)
    if not v7_data:
        return None
    
    # 计算8变化
    eight_change = calculate_8_change(init_odds, real_odds)
    
    return {
        'filename': filename,
        'date_num': date_num,
        'home_team': home_team,
        'away_team': away_team,
        'league': league,
        'v7': v7_data,
        'eight_change': eight_change,
        'form_diff': form_diff,          # 球队状态差 (主队胜率% - 客队胜率%)
        'home_win_rate': home_win_rate,
        'away_win_rate': away_win_rate,
        'home_form': home_form,           # 主队近况走势 (如 "WWWLLW")
        'away_form': away_form,           # 客队近况走势 (如 "WLWWWW")
        'home_handicap': home_handicap,   # 主队盘路走势
        'away_handicap': away_handicap,   # 客队盘路走势
        'macao_tip': macao_tip,           # 澳门心水推荐
    }

def get_expected_confidence_range(form_diff):
    """
    根据状态差获取合理的置信度区间
    状态差越大，合理置信度越高
    """
    if form_diff is None:
        return None, None
    
    abs_form_diff = abs(form_diff)
    if 10 <= abs_form_diff < 20:
        return 55, 65
    elif 20 <= abs_form_diff < 30:
        return 60, 70
    elif 30 <= abs_form_diff < 40:
        return 65, 75
    elif abs_form_diff >= 40:
        return 70, 100
    else:
        # 状态差<10%，置信度应该在55%以下或非常谨慎
        return 0, 55

def is_moderate_distribution(home_8, draw_8, away_8):
    """
    判断是否为中庸8变化分布
    中庸定义：各方向8变化绝对值都较小，没有明显倾向
    """
    # 严格中庸：所有方向|8变化|<=2
    if abs(home_8) <= 2 and abs(draw_8) <= 2 and abs(away_8) <= 2:
        return True, "严格中庸"
    # 宽松中庸：最大|8变化|<=4且总和绝对值<=3
    if max(abs(home_8), abs(draw_8), abs(away_8)) <= 4 and abs(home_8 + draw_8 + away_8) <= 3:
        return True, "宽松中庸"
    return False, ""

def check_moderate_state_mismatch(conf_option, form_diff, home_8, draw_8, away_8, confidence=None, first_leg_result=None):
    """
    检查中庸分布与状态不匹配的情况（3.17欧冠教训优化版）
    
    核心逻辑：中庸分布应该符合两队状态中庸
    - 如果主队状态极好（form_diff >= 30%），但8变化呈中庸分布 → 异常，可能诱盘
    - 如果客队状态极好（form_diff <= -30%），但8变化呈中庸分布 → 异常，可能诱盘
    - 平局8变化较大时，优先考虑平局
    
    【3.17欧冠重要教训】
    - 里斯本vs博德闪耀：首回合客场0-3惨败，次回合主场中庸分布 → 实际主胜3-0
    - 阿森纳vs勒沃库森：首回合客场1-1平，次回合主场中庸分布 → 实际主胜2-0
    - 结论：淘汰赛次回合，首回合不利+中庸分布 = 真实看好主队反弹，不是陷阱！
    
    【修正后规则】
    1. 置信度>=70%：不触发陷阱（强队保护）
    2. 状态差>=40%：不触发陷阱（状态极好保护）
    3. 【新增】首回合客场不胜/惨败 + 次回合中庸分布：不触发陷阱（反弹信号）
    4. 只有联赛/首回合有利时，状态差30-40% + 平局8变化明显，才触发防平
    
    参数:
        first_leg_result: 首回合结果，如 '0-3负', '1-1平', '2-0胜' 等，None表示无首回合或联赛
    
    返回: (是否不匹配, 推荐预测, 理由)
    """
    is_moderate, moderate_type = is_moderate_distribution(home_8, draw_8, away_8)
    
    if not is_moderate:
        return False, None, ""
    
    # === 保护规则1：高置信度强队不触发陷阱 ===
    if confidence is not None and confidence >= 70:
        return False, None, "强队保护(置信度>=70%)"
    
    # === 保护规则2：状态极好（>=40%）不触发陷阱 ===
    if form_diff is not None and abs(form_diff) >= 40:
        return False, None, "状态极好保护(>=40%)"
    
    # === 保护规则3：【新增】淘汰赛次回合反弹信号 ===
    # 首回合客场不利 + 次回合中庸分布 = 庄家真实看好但不引导
    if first_leg_result:
        result_lower = str(first_leg_result).lower()
        # 首回合客场不胜（平或负）
        if any(x in result_lower for x in ['负', '平', '输', 'draw', 'loss']):
            return False, None, "次回合反弹信号(首回合不利)"
    
    # === 触发条件：联赛/首回合有利时，状态差30-40% + 平局8变化明显 ===
    if form_diff is not None and 30 <= form_diff < 40:
        if draw_8 >= 4:
            return True, "平局", f"状态好({form_diff}%)但{moderate_type}分布+平8({draw_8})较大"
        return False, None, ""
    
    if form_diff is not None and -40 < form_diff <= -30:
        if draw_8 >= 4:
            return True, "平局", f"客状态好({form_diff}%)但{moderate_type}分布+平8({draw_8})较大"
        return False, None, ""
    
    # 状态差20-30%，平局8变化极大时才触发
    if form_diff is not None and 20 <= form_diff < 30:
        if draw_8 >= 5:
            return True, "平局", f"状态较好({form_diff}%)但{moderate_type}分布+平8({draw_8})极大"
    
    if form_diff is not None and -30 < form_diff <= -20:
        if draw_8 >= 5:
            return True, "平局", f"客状态较好({form_diff}%)但{moderate_type}分布+平8({draw_8})极大"
    
    return False, None, ""

def predict_match(conf, diff, home_8, draw_8, away_8, conf_option='主胜', form_diff=None, 
                  home_change='-', draw_change='-', away_change='-'):
    """
    使用分段公式预测
    conf_option: 置信度对应的选项（主胜/平局/客胜）
    form_diff: 球队状态差（主队胜率% - 客队胜率%），用于检测状态陷阱
    home_change/draw_change/away_change: 赔率变化方向 ↓下降被看好 ↑上升不被看好
    """
    segment = get_segment(conf)
    if segment == '低于55%':
        return '不使用', segment, '置信度低于55%', '低置信度'
    
    config = SEGMENT_CONFIG[segment]
    t1 = config['t1']
    t2 = config['t2']
    t3 = config['t3']
    default = config['default']
    
    over = conf - diff
    
    # === 第零优先级：中庸分布与状态匹配检查 ===
    # 新思路：中庸分布应该符合两队状态中庸
    # 如果主队状态极好，但8变化呈中庸分布 → 异常，可能诱盘
    is_moderate_mismatch, moderate_pred, moderate_reason = check_moderate_state_mismatch(
        conf_option, form_diff, home_8, draw_8, away_8, conf
    )
    if is_moderate_mismatch:
        return moderate_pred, segment, moderate_reason, '中庸陷阱-' + moderate_pred
    
    # === 第一优先级：8变化中庸检查 ===
    # 如果8变化中庸，直接跟随实盘，不再进行后续复杂判断
    # 中庸定义1：所有方向8变化绝对值≤2
    # 中庸定义2：整体平衡，正负相互抵消（总和绝对值≤2）且最大变化≤4
    total_8 = home_8 + draw_8 + away_8
    is_balanced = abs(home_8) <= 2 and abs(draw_8) <= 2 and abs(away_8) <= 2
    is_mutual_cancel = abs(total_8) <= 2 and max(abs(home_8), abs(draw_8), abs(away_8)) <= 4
    
    if is_balanced or is_mutual_cancel:
        # 8变化中庸或微妙平衡，市场没有明显倾向，跟随实盘（置信度选项）
        return conf_option, segment, f'中庸8变化[{home_8:+d},{draw_8:+d},{away_8:+d}]→跟随实盘', '实盘-' + conf_option
    
    # === 第一优先级：置信度合理性检查 ===
    # 8变化非中庸时，检查置信度是否与状态差匹配
    if form_diff is not None:
        min_conf, max_conf = get_expected_confidence_range(form_diff)
        if min_conf is not None:
            if conf < min_conf or conf > max_conf:
                # 置信度与状态差不匹配，可能是诱盘
                if conf > max_conf:
                    # 置信度过高，状态差不足支撑 → 大热诱盘
                    if conf_option == '主胜' and form_diff > 0:
                        return '平局', segment, f'置信度异常:状态差{form_diff}%但置信度{conf}%过高', '大热诱盘-平局'
                    elif conf_option == '客胜' and form_diff < 0:
                        return '平局', segment, f'置信度异常:状态差{form_diff}%但置信度{conf}%过高', '大热诱盘-平局'
                    else:
                        return '不使用', segment, f'置信度{conf}%与状态差{form_diff}%不匹配', '数据异常'
                else:
                    # 置信度过低，状态差足够但开盘保守
                    return '不使用', segment, f'置信度{conf}%低于状态差{form_diff}%应有区间', '开盘保守'
    
    # === 第二优先级：8变化极端警报（变化≥5或≤-5）===
    # 当某方向8变化绝对值≥5时，说明市场变化过大，需要警惕
    max_8_change = max(abs(home_8), abs(draw_8), abs(away_8))
    if max_8_change >= 5:
        # 极端变化：某方向8变化过大，可能是变盘信号
        # 优先检查诱反信号（8↓+赔率↑），这是强信号
        if home_8 <= -5 and home_change == '↑':
            return '主胜', segment, f'极端诱反:主8({home_8})↓+赔率↑', '极端诱反-主胜'
        if away_8 <= -5 and away_change == '↑':
            return '客胜', segment, f'极端诱反:客8({away_8})↓+赔率↑', '极端诱反-客胜'
        # 正常极端看好信号（8↑+赔率↓）
        if home_8 >= 5 and home_change == '↓':
            return '主胜', segment, f'极端8变化:主8({home_8})↑+赔率↓', '极端看好主胜'
        if away_8 >= 5 and away_change == '↓':
            return '客胜', segment, f'极端8变化:客8({away_8})↑+赔率↓', '极端看好客胜'
        if draw_8 >= 5 and draw_change == '↓':
            return '平局', segment, f'极端8变化:平8({draw_8})↑+赔率↓', '极端看好平局'
        # 8变化大但赔率反向（8↑+赔率↑），可能是诱盘
        if home_8 >= 5 and home_change == '↑':
            return '客胜', segment, f'极端诱盘:主8({home_8})↑但赔率↑', '极端诱盘-客胜'
        if away_8 >= 5 and away_change == '↑':
            return '主胜', segment, f'极端诱盘:客8({away_8})↑但赔率↑', '极端诱盘-主胜'
        # 其他极端情况，谨慎处理
        return '不使用', segment, f'极端8变化[{home_8:+d},{draw_8:+d},{away_8:+d}]需警惕', '极端变化'
    
    # === 第三优先级：超级强队保护（置信度≥70%且状态差≥40%）===
    # 超级强队区间，8变化只能微调，不能逆转
    if conf >= 70 and form_diff is not None and abs(form_diff) >= 40:
        # 只有大热陷阱才能改平局，其他8变化不逆转
        if (conf_option == '主胜' and form_diff >= 40 and 
            home_8 <= -5 and home_change == '↓'):
            return '平局', segment, f'超级强队大热:置信度{conf}%+状态差{form_diff}%+主8{home_8}↓', '大热诱盘-平局'
        if (conf_option == '客胜' and form_diff <= -40 and 
            away_8 <= -5 and away_change == '↓'):
            return '平局', segment, f'超级强队大热:置信度{conf}%+状态差{form_diff}%+客8{away_8}↓', '大热诱盘-平局'
        # 超级强队维持原预测
        return conf_option, segment, f'超级强队保护:置信度{conf}%+状态差{form_diff}%', '超级强队-' + conf_option
    
    # === 第四优先级：8变化与赔率变化组合判断（非极端情况）===
    # 组合1: 8增加 + 赔率下降 = 看好（但非极端）
    if home_8 >= 3 and home_change == '↓':
        return '主胜', segment, f'8组合:主8({home_8})↑+赔率↓', '8组合主胜'
    if away_8 >= 3 and away_change == '↓':
        return '客胜', segment, f'8组合:客8({away_8})↑+赔率↓', '8组合客胜'
    
    # 组合2: 8减少 + 赔率上升 = 诱盘反向（庄家故意引导，实际该方向打出）
    # 切尔西案例：客8-6↑+赔率↑，实际客胜
    if home_8 <= -3 and home_change == '↑':
        return '主胜', segment, f'8诱反:主8({home_8})↓+赔率↑', '8诱反-主胜'
    if away_8 <= -3 and away_change == '↑':
        return '客胜', segment, f'8诱反:客8({away_8})↓+赔率↑', '8诱反-客胜'
    
    # 组合3: 8增加但赔率上升 = 诱盘（热度高但庄家不看好）
    if home_8 >= 3 and home_change == '↑':
        return '平局', segment, f'8诱盘:主8({home_8})↑但赔率↑', '8诱盘-平局'
    if away_8 >= 3 and away_change == '↑':
        return '平局', segment, f'8诱盘:客8({away_8})↑但赔率↑', '8诱盘-平局'
    
    # 组合4: 平局8变化 + 赔率变化（阈值提高到4）
    if draw_8 >= 4 and draw_change == '↓':
        return '平局', segment, f'8组合:平8({draw_8})↑+赔率↓', '8组合平局'
    if draw_8 <= -4 and draw_change == '↑':
        # 平8大幅减少+赔率上升，可能是诱反
        return '不使用', segment, f'平8诱反:平8({draw_8})↓+赔率↑，建议观望', '平8诱反-观望'
    
    # === 第五优先级：中高置信度区间（60-70%）的8变化覆盖 ===
    # 置信度60-70%且状态差20-40%时，强逆分布可以覆盖
    if 60 <= conf < 70 and form_diff is not None and 20 <= abs(form_diff) < 40:
        # 主胜预测时的强逆分布
        if conf_option == '主胜' and form_diff >= 20:
            if away_8 >= 4 and away_change == '↓':
                return '客胜', segment, f'中高强度逆:客8({away_8})↑+赔率↓+状态差{form_diff}%', '中强逆-客胜'
            if away_8 >= 2 and away_change == '↓' and home_8 <= -2:
                return '客胜', segment, f'中强度逆:客8↑+主8↓+状态差{form_diff}%', '中逆-客胜'
        # 客胜预测时的强逆分布
        if conf_option == '客胜' and form_diff <= -20:
            if home_8 >= 4 and home_change == '↓':
                return '主胜', segment, f'中高强度逆:主8({home_8})↑+赔率↓+状态差{abs(form_diff)}%', '中强逆-主胜'
            if home_8 >= 2 and home_change == '↓' and away_8 <= -2:
                return '主胜', segment, f'中强度逆:主8↑+客8↓+状态差{abs(form_diff)}%', '中逆-主胜'
    
    # === 新增：低状态差 + 中庸8变化 = 优先平局 ===
    # 当两队状态接近（状态差<20%）且8变化呈中庸分布时，市场没有明确倾向，优先走平局
    if form_diff is not None and abs(form_diff) < 20:
        # 中庸8变化定义：各方向8变化绝对值都<=1，即没有明显市场倾向
        if abs(home_8) <= 1 and abs(draw_8) <= 1 and abs(away_8) <= 1:
            return '平局', segment, f'低状态差({form_diff}%)+中庸8变化[{home_8:+d},{draw_8:+d},{away_8:+d}]', '中庸平局'
    
    # === 新增：中低置信度区间（55-60%）的8变化敏感 ===
    # 置信度55-60%且状态差<30%时，8变化更敏感
    if 55 <= conf < 60 and form_diff is not None and abs(form_diff) < 30:
        # 主胜预测时
        if conf_option == '主胜':
            if away_8 >= 3 and away_change == '↓':
                return '客胜', segment, f'中低敏感逆:客8({away_8})↑+赔率↓+状态差{form_diff}%', '敏感逆-客胜'
            if home_8 <= -3 and home_change == '↑':
                return '平局', segment, f'中低敏感弱:主8({home_8})↓+赔率↑', '敏感弱-平局'
        # 客胜预测时
        if conf_option == '客胜':
            if home_8 >= 3 and home_change == '↓':
                return '主胜', segment, f'中低敏感逆:主8({home_8})↑+赔率↓+状态差{abs(form_diff)}%', '敏感逆-主胜'
            if away_8 <= -3 and away_change == '↑':
                return '平局', segment, f'中低敏感弱:客8({away_8})↓+赔率↑', '敏感弱-平局'
    
    # === 新增：完美一致陷阱检测（大热必死）===
    # 当赔率、状态、8变化三方极度一致看好一方时，往往是诱盘
    # 主胜完美一致陷阱（只在非超级强队时触发）
    if (conf_option == '主胜' and 60 <= conf < 70 and diff >= 50 and 
        form_diff is not None and form_diff >= 40 and 
        home_8 <= -5 and home_change == '↓'):
        return '平局', segment, f'大热陷阱:置信度{conf}%+胜率差{diff}%+状态差{form_diff}%+主8{home_8}↓', '大热诱盘-平局'
    
    # 客胜完美一致陷阱
    if (conf_option == '客胜' and 60 <= conf < 70 and diff <= -50 and 
        form_diff is not None and form_diff <= -40 and 
        away_8 <= -5 and away_change == '↓'):
        return '平局', segment, f'大热陷阱:置信度{conf}%+胜率差{diff}%+状态差{form_diff}%+客8{away_8}↓', '大热诱盘-平局'
    
    # 状态陷阱检测：状态差为负但赔率看好主队（诱盘）
    # 当状态差 <= -10% 且赔率胜率差 > 30% 时，降低主胜置信度
    if form_diff is not None and form_diff <= -10 and diff > 30:
        # 状态陷阱：客队状态更好，但赔率强开主队
        # 优先看8变化和胜率差绝对值
        if away_8 >= 2:
            return '客胜', segment, f'状态陷阱(状态差{form_diff}%)+客胜8变化({away_8})', '状态诱盘-客胜'
        if abs(diff) >= t1:
            # 即使胜率差大，也因状态差而谨慎
            if form_diff <= -20:  # 状态差很大时，直接反客胜
                return '客胜', segment, f'状态陷阱(状态差{form_diff}%)>=20%', '强状态诱盘-客胜'
        # 状态陷阱但不够强，走平局
        return '平局', segment, f'状态陷阱(状态差{form_diff}%)', '状态诱盘-平局'
    
    # 规则1: 强信号 - 胜率差超过阈值
    if diff >= t1:
        return '主胜', segment, f'胜率差({diff}%)>=阈值({t1}%)', '强主胜'
    if diff <= -t1:
        return '客胜', segment, f'胜率差({diff}%)<=-阈值({t1}%)', '强客胜'
    
    # 规则2: 高开走冷 - 置信度高开但胜率差不大
    if over > t2 and abs(diff) < t3:
        return '平局', segment, f'高开({over}%)>{t2}% 且 |胜率差({diff}%)|<{t3}%', '高开走冷'
    
    # 规则3: 8变化极端（基础判断，不含赔率组合）
    if home_8 >= 2:
        return '主胜', segment, f'主胜8变化({home_8})>=2', '8强化主胜'
    if home_8 <= -3:
        return '平局', segment, f'主胜8变化({home_8})<=-3', '8倾向平局'
    if away_8 >= 3:
        return '客胜', segment, f'客胜8变化({away_8})>=3', '8强化客胜'
    
    # 规则4: 根据置信度选项和胜率差方向综合判断
    # 如果置信度选项和胜率差方向一致，优先选择该方向
    # 但需考虑状态差修正
    if conf_option == '主胜' and diff > 0:
        # 状态差为负时，降低主胜倾向
        if form_diff is not None and form_diff < 0:
            if form_diff <= -20:
                return '平局', segment, f'置信度主胜但状态差大负({form_diff}%)', '状态修正-平局'
            # 轻度状态劣势，仍主胜但标记
            return '主胜', segment, f'置信度主胜但状态劣势({form_diff}%)', '状态警告-主胜'
        return '主胜', segment, f'置信度主胜且胜率差为正({diff}%)', '主胜倾向'
    if conf_option == '客胜' and diff < 0:
        return '客胜', segment, f'置信度客胜且胜率差为负({diff}%)', '客胜倾向'
    if conf_option == '平局':
        return '平局', segment, f'置信度平局', '平局倾向'
    
    # 规则5: 分段默认值（当置信度选项和胜率差方向不一致时）
    reason_detail = f'默认({default})'
    if default == '主胜':
        reason_brief = '默认主胜'
    elif default == '客胜':
        reason_brief = '默认客胜'
    else:
        reason_brief = '默认平局'
    return default, segment, reason_detail, reason_brief

def analyze_directory(dir_path):
    """分析目录中的所有源数据文件"""
    results = []
    
    # 查找所有源数据文件
    source_files = list(Path(dir_path).glob('*_源数据.md'))
    source_files.sort()
    
    print(f"找到 {len(source_files)} 个源数据文件")
    
    for filepath in source_files:
        data = parse_source_file(filepath)
        if not data:
            print(f"  跳过: {filepath.name} (无法解析)")
            continue
        
        # 预测
        conf = data['v7']['confidence']
        diff = data['v7']['win_rate_diff']
        home_8 = data['eight_change']['home_8']
        draw_8 = data['eight_change']['draw_8']
        away_8 = data['eight_change']['away_8']
        conf_option = data['v7'].get('confidence_option', '主胜')  # 获取置信度对应的选项
        form_diff = data.get('form_diff')  # 球队状态差
        home_change = data['eight_change'].get('home_change', '-')
        draw_change = data['eight_change'].get('draw_change', '-')
        away_change = data['eight_change'].get('away_change', '-')
        
        prediction, segment, reason, reason_brief = predict_match(
            conf, diff, home_8, draw_8, away_8, conf_option, form_diff,
            home_change, draw_change, away_change
        )
        
        data['prediction'] = prediction
        data['segment'] = segment
        data['reason'] = reason
        data['reason_brief'] = reason_brief
        
        results.append(data)
    
    return results

def print_results(results):
    """打印预测结果"""
    print("\n" + "="*120)
    print("V7+8变化 分段权重分析法 预测结果")
    print("="*120)
    
    # 按分段统计
    segment_stats = {}
    for r in results:
        seg = r.get('segment', 'N/A')
        if seg not in segment_stats:
            segment_stats[seg] = {'total': 0, 'high_conf': 0}
        segment_stats[seg]['total'] += 1
        if r.get('prediction') != '不使用':
            segment_stats[seg]['high_conf'] += 1
    
    print("\n分段统计:")
    for seg in ['55-60%', '60-65%', '65-70%', '70-75%', '75-80%', '80%+', '低于55%']:
        if seg in segment_stats:
            stats = segment_stats[seg]
            print(f"  {seg}: {stats['high_conf']} 场")
    
    # 打印详细结果
    print("\n详细预测:")
    print("-"*165)
    print(f"{'日期':<8} {'对阵':<25} {'联赛':<6} {'置信度':>6} {'选项':>4} {'胜率差':>8} {'状态差':>7} {'8变化':>14} {'分段':>8} {'预测':>6} {'理由':<12}")
    print("-"*165)
    
    for r in results:
        match = f"{r['home_team']} vs {r['away_team']}"
        conf = r['v7']['confidence']
        conf_option = r['v7'].get('confidence_option', '')
        diff = r['v7']['win_rate_diff']
        form_diff = r.get('form_diff')
        form_diff_str = f"{form_diff:+d}%" if form_diff is not None else "  N/A"
        h8 = r['eight_change']['home_8']
        d8 = r['eight_change']['draw_8']
        a8 = r['eight_change']['away_8']
        h8_odds = r['eight_change'].get('home_change', '-')
        d8_odds = r['eight_change'].get('draw_change', '-')
        a8_odds = r['eight_change'].get('away_change', '-')
        seg = r.get('segment', '')
        pred = r.get('prediction', '')
        reason_brief = r.get('reason_brief', '')
        
        # 8变化格式: [+2↓,+1-,+0↑] 数字表示8的数量变化，符号表示赔率变化
        print(f"{r['date_num']:<8} {match:<25} {r['league']:<6} {conf:>5}% {conf_option:>4} {diff:>+7}% {form_diff_str:>7} [{h8:+2}{h8_odds},{d8:+2}{d8_odds},{a8:+2}{a8_odds}] {seg:>8} {pred:>6} {reason_brief:<12}")

def main():
    parser = argparse.ArgumentParser(description='V7+8变化 分段权重分析法')
    parser.add_argument('directory', nargs='?', default='.', help='源数据目录 (默认当前目录)')
    parser.add_argument('-o', '--output', help='输出结果到文件')
    
    args = parser.parse_args()
    
    # 解析目录
    dir_path = args.directory
    if not os.path.isdir(dir_path):
        # 可能是日期编号如 3.17
        dir_path = os.path.join(os.path.dirname(__file__), dir_path)
    
    print(f"分析目录: {dir_path}")
    
    # 分析
    results = analyze_directory(dir_path)
    
    # 打印结果
    print_results(results)
    
    # 保存结果
    if args.output:
        output_data = []
        for r in results:
            ec = r['eight_change']
            v7 = r['v7']
            form_diff = r.get('form_diff')
            output_data.append({
                'date_num': r['date_num'],
                'match': f"{r['home_team']} vs {r['away_team']}",
                'league': r['league'],
                'confidence': v7['confidence'],
                'confidence_option': v7.get('confidence_option', ''),
                'probs': f"{v7.get('home_prob',0)}/{v7.get('draw_prob',0)}/{v7.get('away_prob',0)}",
                'win_rate_diff': v7['win_rate_diff'],
                'form_diff': f"{form_diff:+d}%" if form_diff is not None else "N/A",  # 球队状态差
                'home_win_rate': r.get('home_win_rate'),
                'away_win_rate': r.get('away_win_rate'),
                'eight_change': f"[{ec['home_8']:+d}{ec.get('home_change','')},{ec['draw_8']:+d}{ec.get('draw_change','')},{ec['away_8']:+d}{ec.get('away_change','')}]",
                'segment': r.get('segment', ''),
                'prediction': r.get('prediction', ''),
                'reason': r.get('reason', ''),
                'reason_brief': r.get('reason_brief', ''),
            })
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {args.output}")

if __name__ == '__main__':
    main()
