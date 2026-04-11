#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3月27日周五12场比赛分析脚本 - 规律V3版
基于最新规律体系重新分析3.27比赛
"""

import os
import re
import glob
from datetime import datetime


def parse_form_score(form_str):
    """解析近况走势，计算近况评分"""
    if not form_str or len(form_str) < 5:
        return 0
    
    recent_5 = form_str[:5]
    score = 0
    for i, result in enumerate(recent_5):
        result_upper = result.upper()
        if result_upper == 'W':
            points = 3
        elif result_upper == 'D':
            points = 1
        else:
            points = 0
        weight = 2 if i == 0 else 1
        score += points * weight
    
    return score


def extract_match_info(content):
    """从文件内容中提取比赛信息"""
    info = {}
    
    home_match = re.search(r'home_team\s*=\s*"([^"]+)"', content)
    away_match = re.search(r'away_team\s*=\s*"([^"]+)"', content)
    time_match = re.search(r'match_time\s*=\s*"([^"]+)"', content)
    league_match = re.search(r'league\s*=\s*"([^"]+)"', content)
    home_form_match = re.search(r'home_form\s*=\s*"([^"]+)"', content)
    away_form_match = re.search(r'away_form\s*=\s*"([^"]+)"', content)
    macao_match = re.search(r'macao_tip\s*=\s*"([^"]+)"', content)
    
    info['home_team'] = home_match.group(1) if home_match else "未知"
    info['away_team'] = away_match.group(1) if away_match else "未知"
    info['match_time'] = time_match.group(1) if time_match else "未知"
    info['league'] = league_match.group(1) if league_match else "未知"
    info['home_form'] = home_form_match.group(1) if home_form_match else ""
    info['away_form'] = away_form_match.group(1) if away_form_match else ""
    info['macao_tip'] = macao_match.group(1) if macao_match else ""
    
    info['home_form_score'] = parse_form_score(info['home_form'])
    info['away_form_score'] = parse_form_score(info['away_form'])
    info['form_diff'] = info['home_form_score'] - info['away_form_score']
    
    return info


def extract_odds_weighted(content):
    """提取初盘和即时赔率数据（加权版）"""
    odds_data = {'initial': [], 'realtime': []}
    
    company_weights = {
        '竞*官*': 0.30, '威**尔': 0.15, '立*': 0.15, '**t3*5': 0.15,
        'Pi****le平*': 0.10, 'S**I': 0.05, 'B**n': 0.05, '伟*': 0.03, '易*博': 0.02,
    }
    
    initial_pattern = r'initial_odds\s*=\s*\[(.*?)\]'
    initial_match = re.search(initial_pattern, content, re.DOTALL)
    if initial_match:
        odds_text = initial_match.group(1)
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
            odds_data['initial'] = [(home_avg, draw_avg, away_avg)]
    
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


def calculate_odds_change(initial_avg, realtime_avg):
    """计算赔率变化百分比"""
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
    """判断澳门推荐方向"""
    if not macao_tip:
        return "未知"
    
    tip = macao_tip.lower()
    if '和' in macao_tip or '平' in macao_tip:
        return "平局"
    elif home_team.lower() in tip or home_team.split()[0].lower() in tip:
        return "主胜"
    elif away_team.lower() in tip or away_team.split()[0].lower() in tip:
        return "客胜"
    
    return "未知"


def generate_prediction_v3(analysis):
    """生成预测建议 - 规律V3版"""
    pred = analysis['predicted']
    conf = analysis['confidence']
    macao = analysis['macao_direction']
    home_change, draw_change, away_change = analysis['odds_change']
    form_diff = analysis['form_diff']
    home_avg, draw_avg, away_avg = analysis['realtime_avg']
    
    predictions = []
    reasons = []
    triggered_rules = []
    
    # ========== V3.1修正规律（优先级最高）==========
    
    # 规律S（V3.1修正版）：近况持平+赔率大幅变化+澳门推方向≠造热方向 → 反向
    # V3.1修正：增加澳门推方向≠造热方向条件 + 赔率绝对值排除
    # V3.1补充修正：澳门推平时不触发规律S（平局方向本身有信号意义）
    # V3.1补充2：被反向方向赔率≥3.4时不触发（庄家赔付压力大=庄家无法完全诱导）
    if abs(form_diff) <= 2 and max(abs(home_change), abs(draw_change), abs(away_change)) > 5:
        hot_direction = None
        if away_change < -5:
            hot_direction = "客胜"
        elif home_change < -5:
            hot_direction = "主胜"
        elif home_change > 5:
            hot_direction = "客胜"
        elif away_change > 5:
            hot_direction = "主胜"
        
        # V3.1补充：澳门推平时规律S不触发（平局本身有信号意义）
        if hot_direction and macao != hot_direction and macao != "平局":
            # 反向方向赔率≥3.4时不触发（庄家赔付压力大=真实概率高）
            # 周五006案例：澳门推客+主造热→反向看客胜，但客赔3.44≥3.4→不触发
            if hot_direction == "客胜" and home_avg < 3.4:
                predictions.append(("主胜", 80, "规律S：近况持平+客造热反向(澳门≠客)"))
                reasons.append(f"近况差{form_diff}势均力敌，客胜造热({away_change:.1f}%)但澳门不推客，反向主胜")
                triggered_rules.append("规律S")
            elif hot_direction == "主胜" and away_avg < 3.4:
                predictions.append(("客胜", 80, "规律S：近况持平+主造热反向(澳门≠主)"))
                reasons.append(f"近况差{form_diff}势均力敌，主胜造热({home_change:.1f}%)但澳门不推主，反向客胜")
                triggered_rules.append("规律S")
            # 赔率≥3.4时：庄家赔付压力大，规律S信号弱化
            # 周五006：客赔3.44→庄家赔付压力大，诱导可能失败，不预测
    
    # 规律U（V3.1修正版）：近况碾压+主胜造热+澳门不推主 → 防平
    if form_diff >= 8 and home_change < -5 and away_change > 5 and macao != "主胜":
        predictions.append(("平局", 82, "规律U：近况碾压+主造热+澳门不推主→防平"))
        reasons.append(f"近况差+{form_diff}主队碾压，主胜造热({home_change:.1f}%)但澳门不推主，诱导信号，防平局")
        triggered_rules.append("规律U")
    
    # 规律V（V3.1修正版）：近况碾压客+客胜造热+澳门不推客 → 防平
    if form_diff <= -8 and away_change < -5 and home_change > 5 and macao != "客胜":
        predictions.append(("平局", 82, "规律V：近况碾压客+客造热+澳门不推客→防平"))
        reasons.append(f"近况差{form_diff}客队碾压，客胜造热({away_change:.1f}%)但澳门不推客，诱导信号，防平局")
        triggered_rules.append("规律V")
    
    # ========== 规律五V3.1（修正版）==========
    
    # 规律五V3.1：主胜升幅>5% 且 客胜变化>-5% 且 |近况差|>3 且 澳门推平 → 和局
    if home_change > 5 and away_change > -5 and abs(form_diff) > 3 and macao == "平局":
        predictions.append(("平局", 85, "规律五V3.1：主升>5%+澳门推平+|差|>3"))
        reasons.append("主胜赔率大幅上升(>5%)+澳门推平局+近况有差距，和局概率高")
        triggered_rules.append("规律五V3.1")
    
    # 规律五V3.1-双热：主胜升幅>5% 且 客胜降幅>5% 且 |近况差|>3 且 澳门推平 → 看客队
    if home_change > 5 and away_change < -5 and abs(form_diff) > 3 and macao == "平局":
        predictions.append(("客胜", 75, "规律五V3.1-双热：主客均造热+澳门推平看客胜"))
        reasons.append("主客均被造热+澳门推平局，客胜降幅更大，倾向客胜")
        triggered_rules.append("规律五V3.1-双热")
    
    # ========== 其他规律 ==========
    
    # 规律O：近况差+8以上+赔率微变<2% → 主队打出
    if form_diff >= 8 and max(abs(home_change), abs(draw_change), abs(away_change)) < 2:
        predictions.append(("主胜", 80, "规律O：近况差大+赔率微变"))
        reasons.append(f"近况差+{form_diff}，赔率微变<2%，主队打出信号")
        triggered_rules.append("规律O")
    
    # 规律N（V3.1修正版）：规律五+澳门推客+客队极端造热 → 反向主胜
    # V3.1修正：增加客胜赔率绝对值排除（<2.5=实盘确认，不反向）
    # 修正依据：周五001客赔2.57接近2.5，庄家能承受赔付，实盘确认而非诱导
    if home_change > 5 and macao == "客胜" and away_change < -10 and away_avg >= 2.5:
        predictions.append(("主胜", 80, "规律N：规律五+极端造热客队"))
        reasons.append("主胜升幅>5%+澳门推客+客队极端造热，反向主胜")
        triggered_rules.append("规律N")
    
    # 规律R：真假造热辨别
    if macao == "客胜" and away_change < -10:
        if home_change > 0 and draw_change > 0:
            predictions.append(("主胜", 85, "规律R：真造热诱盘"))
            reasons.append("澳门推客+客造热>10%，主/平均升无分流，反向主胜")
            triggered_rules.append("规律R-真造热")
        elif draw_change < 0 or home_change < 0:
            predictions.append(("客胜", 75, "规律R：假造热实盘"))
            reasons.append("澳门推客+客降，但平/主同步降分流筹码，客胜实盘")
            triggered_rules.append("规律R-假造热")
    
    if macao == "主胜" and home_change < -10:
        if away_change > 0 and draw_change > 0:
            predictions.append(("客胜", 85, "规律R：真造热诱盘"))
            reasons.append("澳门推主+主造热>10%，客/平均升无分流，反向客胜")
            triggered_rules.append("规律R-真造热")
        elif draw_change < 0 or away_change < 0:
            predictions.append(("主胜", 75, "规律R：假造热实盘"))
            reasons.append("澳门推主+主降，但平/客同步降分流筹码，主胜实盘")
            triggered_rules.append("规律R-假造热")
    
    # 规律P：平赔3.0-3.2+澳门推平局+变化<2% → 诱平，反向打出
    if 3.0 <= draw_avg <= 3.2 and macao == "平局" and abs(draw_change) < 2:
        if away_change > 0:
            predictions.append(("客胜", 75, "规律P：诱平陷阱"))
            reasons.append("平赔3.0-3.2诱平区间，筹码分散主/平，客队漏网")
            triggered_rules.append("规律P")
    
    # 规律Q：近况差极大+置信度<65%+赔率全变>2% → 防过热平局
    if form_diff >= 10 and conf < 65 and min(abs(home_change), abs(draw_change), abs(away_change)) > 2:
        predictions.append(("平局", 70, "规律Q：过热防平"))
        reasons.append("近况差极大但置信度不匹配，赔率变化有造热嫌疑，防平局")
        triggered_rules.append("规律Q")
    
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
    
    # 规律J（V3.1修正版）：澳门推平+平赔<3.0+主升+客降+平赔不变或微升 → 客胜
    # V3.1修正：增加"平赔不降"条件
    # 修正依据：周五012平赔从2.99降到2.76(-7.9%)，平局也在承接筹码，客胜不是唯一方向
    if macao == "平局" and draw_avg < 3.0 and home_change > 0 and away_change < 0 and draw_change >= -2:
        predictions.append(("客胜", 72, "规律J：推平诱客"))
        reasons.append("澳门推平但平赔<3.0且不降，主升客降，客胜")
        triggered_rules.append("规律J")
    
    # 规律I：极端造热+近况差≤-10+平赔不变 → 平局
    if home_change < -10 and away_change > 10 and form_diff <= -10 and abs(draw_change) < 1:
        predictions.append(("平局", 70, "规律I：极端造热平局"))
        reasons.append("极端造热客队+近况客优+平赔不变，平局")
        triggered_rules.append("规律I")
    
    # 默认预测
    if not predictions:
        if conf >= 66:
            predictions.append((pred, conf, "高置信度默认"))
            reasons.append(f"置信度{conf:.1f}%≥66%，按最高概率方向")
        elif conf >= 55:
            predictions.append((pred, conf - 10, "中等置信度"))
            reasons.append(f"置信度{conf:.1f}%中等，存在不确定性")
        else:
            predictions.append(("观望", 50, "低置信度观望"))
            reasons.append(f"置信度{conf:.1f}%<55%，建议观望")
    
    # 选择最佳预测
    best_pred = max(predictions, key=lambda x: x[1])
    
    return {
        'prediction': best_pred[0],
        'confidence': best_pred[1],
        'rule': best_pred[2],
        'reason': reasons[0] if reasons else "",
        'all_rules': triggered_rules,
        'all_predictions': predictions
    }


def analyze_match(match_info, odds_data):
    """分析单场比赛"""
    if not odds_data['initial'] or not odds_data['realtime']:
        return None
    
    initial_avg = odds_data['initial'][0]
    realtime_avg = odds_data['realtime'][0]
    
    odds_change = calculate_odds_change(initial_avg, realtime_avg)
    probabilities = calculate_probabilities(realtime_avg)
    
    max_prob = max(probabilities)
    if probabilities[0] == max_prob:
        predicted = "主胜"
    elif probabilities[1] == max_prob:
        predicted = "平局"
    else:
        predicted = "客胜"
    
    macao_direction = determine_macao_direction(
        match_info.get('macao_tip', ''), 
        match_info.get('home_team', ''), 
        match_info.get('away_team', '')
    )
    
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
    
    form_diff = match_info.get('form_diff', 0)
    
    return {
        'match_info': match_info,
        'initial_avg': initial_avg,
        'realtime_avg': realtime_avg,
        'odds_change': odds_change,
        'probabilities': probabilities,
        'predicted': predicted,
        'confidence': max_prob,
        'macao_direction': macao_direction,
        'chip_status': chip_status,
        'form_diff': form_diff
    }


def format_output(match_id, analysis, prediction):
    """格式化输出"""
    info = analysis['match_info']
    home, draw, away = analysis['realtime_avg']
    home_c, draw_c, away_c = analysis['odds_change']
    home_p, draw_p, away_p = analysis['probabilities']
    
    output = f"""
{'='*60}
【{match_id}】{info['home_team']} vs {info['away_team']}
{'='*60}
联赛：{info['league']} | 时间：{info['match_time']}
澳门推荐：{analysis['macao_direction']}

【近况分析】
主队近况：{info['home_form']} ({info['home_form_score']}/18分)
客队近况：{info['away_form']} ({info['away_form_score']}/18分)
近况差：{analysis['form_diff']:+.0f} (主队{'优势' if analysis['form_diff'] > 0 else '劣势' if analysis['form_diff'] < 0 else '持平'})

【赔率分析】
初盘：主{analysis['initial_avg'][0]:.2f} / 平{analysis['initial_avg'][1]:.2f} / 客{analysis['initial_avg'][2]:.2f}
即时：主{home:.2f} / 平{draw:.2f} / 客{away:.2f}
变化：主{home_c:+.1f}% / 平{draw_c:+.1f}% / 客{away_c:+.1f}%

【概率分布】
主胜：{home_p:.1f}% | 平局：{draw_p:.1f}% | 客胜：{away_p:.1f}%
置信度：{analysis['confidence']:.1f}%

【筹码状态】{analysis['chip_status']}

【V3预测结果】
预测：{prediction['prediction']}
信心：{prediction['confidence']}%
触发规律：{prediction['rule']}
依据：{prediction['reason']}
"""
    return output


def main():
    """主函数"""
    data_dir = "d:/work/workbuddy/足球预测/分析模板/3.27"
    
    # 获取所有源数据文件
    data_files = glob.glob(os.path.join(data_dir, "*_源数据.md"))
    data_files.sort()
    
    print(f"找到 {len(data_files)} 场比赛数据")
    print("="*60)
    
    all_results = []
    
    for file_path in data_files:
        filename = os.path.basename(file_path)
        match_id = filename.split('_')[0]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            match_info = extract_match_info(content)
            odds_data = extract_odds_weighted(content)
            
            analysis = analyze_match(match_info, odds_data)
            if analysis:
                prediction = generate_prediction_v3(analysis)
                output = format_output(match_id, analysis, prediction)
                all_results.append({
                    'match_id': match_id,
                    'home': match_info['home_team'],
                    'away': match_info['away_team'],
                    'prediction': prediction['prediction'],
                    'confidence': prediction['confidence'],
                    'rule': prediction['rule'],
                    'form_diff': analysis['form_diff'],
                    'macao': analysis['macao_direction'],
                    'odds_change': analysis['odds_change'],
                    'output': output
                })
                print(output)
        except Exception as e:
            print(f"处理 {match_id} 时出错: {e}")
    
    # 生成汇总报告
    print("\n" + "="*60)
    print("【3.27比赛 V3规律预测汇总】")
    print("="*60)
    
    for r in all_results:
        home_c, draw_c, away_c = r['odds_change']
        print(f"{r['match_id']}: {r['home']} vs {r['away']}")
        print(f"  预测: {r['prediction']} | 信心: {r['confidence']}% | 规律: {r['rule']}")
        print(f"  近况差: {r['form_diff']:+.0f} | 赔率变化: 主{home_c:+.1f}% 平{draw_c:+.1f}% 客{away_c:+.1f}%")
        print()
    
    # 保存结果
    output_file = "d:/work/workbuddy/足球预测/3.27_V3分析结果.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("3月27日周五比赛 - 规律V3分析结果\n")
        f.write("="*60 + "\n\n")
        for r in all_results:
            f.write(r['output'])
            f.write("\n")
        
        f.write("\n" + "="*60 + "\n")
        f.write("【预测汇总】\n")
        f.write("="*60 + "\n")
        for r in all_results:
            f.write(f"{r['match_id']}: {r['prediction']} ({r['confidence']}%) - {r['rule']}\n")
    
    print(f"\n结果已保存到: {output_file}")


if __name__ == "__main__":
    main()
