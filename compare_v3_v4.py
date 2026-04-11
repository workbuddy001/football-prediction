# -*- coding: utf-8 -*-
"""
比较V3和V4算法预测，找出相同的比赛
"""

import re
from pathlib import Path

# ===== V3算法 =====
def parse_team_form_v3(content):
    home_match = re.search(r'主队近况.*?近10场[，,]?(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    away_match = re.search(r'客队近况.*?近10场[，,]?(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    
    home_form = {}
    away_form = {}
    
    if home_match:
        home_form = {'win_rate': int(home_match.group(4))}
    if away_match:
        away_form = {'win_rate': int(away_match.group(4))}
    
    return home_form, away_form


def parse_odds_v3(content):
    initial_odds = []
    realtime_odds = []
    
    initial_section = re.search(r'## 二、初盘赔率.*?```python(.*?)```', content, re.DOTALL)
    if initial_section:
        odds_text = initial_section.group(1)
        for match in re.finditer(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', odds_text):
            initial_odds.append({
                'home': float(match.group(1)),
                'draw': float(match.group(2)),
                'away': float(match.group(3))
            })
    
    realtime_section = re.search(r'## 三、即时赔率.*?```python(.*?)```', content, re.DOTALL)
    if realtime_section:
        odds_text = realtime_section.group(1)
        for match in re.finditer(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', odds_text):
            realtime_odds.append({
                'home': float(match.group(1)),
                'draw': float(match.group(2)),
                'away': float(match.group(3))
            })
    
    return initial_odds, realtime_odds


def analyze_v3(filepath):
    """V3算法预测"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    filename = Path(filepath).stem
    match = re.match(r'周六(\d+)_(.+?)vs(.+?)_源数据', filename)
    if not match:
        return None
    
    match_id = f"周六{match.group(1)}"
    home = match.group(2)
    away = match.group(3)
    
    home_form, away_form = parse_team_form_v3(content)
    initial_odds, realtime_odds = parse_odds_v3(content)
    
    if not initial_odds or not realtime_odds:
        return None
    
    rt = realtime_odds[0]
    form_diff = home_form.get('win_rate', 0) - away_form.get('win_rate', 0)
    
    # V3预测逻辑（简化版）
    avg_home = sum(o['home'] for o in realtime_odds) / len(realtime_odds)
    avg_away = sum(o['away'] for o in realtime_odds) / len(realtime_odds)
    
    # 强胆判断
    if avg_home < 1.5:
        prediction = "主胜"
    elif avg_away < 1.5:
        prediction = "客胜"
    elif form_diff > 30 and avg_home < 2.0:
        prediction = "主胜"
    elif form_diff < -30 and avg_away < 2.0:
        prediction = "客胜"
    else:
        if avg_home < avg_away:
            prediction = "主胜"
        else:
            prediction = "客胜"
    
    return {"编号": match_id, "对阵": f"{home} vs {away}", "V3预测": prediction}


# ===== V4算法 =====
def analyze_v4(filepath):
    """V4算法预测"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    filename = Path(filepath).stem
    match = re.match(r'周六(\d+)_(.+?)vs(.+?)_源数据', filename)
    if not match:
        return None
    
    match_id = f"周六{match.group(1)}"
    home = match.group(2)
    away = match.group(3)
    
    # 解析赔率
    initial_odds, realtime_odds = parse_odds_v3(content)
    
    if not initial_odds or not realtime_odds:
        return None
    
    rt = realtime_odds[0]
    init = initial_odds[0]
    
    # V4核心逻辑
    home_win = rt['home']
    draw = rt['draw']
    away_win = rt['away']
    
    # 计算概率
    prob_home = 1 / home_win / (1/home_win + 1/draw + 1/away_win)
    prob_draw = 1 / draw / (1/home_win + 1/draw + 1/away_win)
    prob_away = 1 / away_win / (1/home_win + 1/draw + 1/away_win)
    
    # V4预测规则
    prediction = "未知"
    
    # 规则1: 强胆主胜 (赔率<1.5)
    if home_win < 1.5:
        prediction = f"{home}主胜"
    
    # 规则2: 强胆客胜
    elif away_win < 1.5:
        prediction = f"{away}客胜"
    
    # 规则3: 主胜升>15%
    elif (init['home'] - rt['home']) / init['home'] > 0.15:
        prediction = f"{home}主胜"
    
    # 规则4: 客胜升>15%
    elif (init['away'] - rt['away']) / init['away'] > 0.15:
        prediction = f"{away}客胜"
    
    # 规则5: 强队主场
    elif prob_home > 0.50:
        prediction = f"{home}主胜"
    
    # 规则6: 概率最高
    elif prob_home > prob_away and prob_home > prob_draw:
        prediction = f"{home}主胜"
    elif prob_away > prob_home and prob_away > prob_draw:
        prediction = f"{away}客胜"
    else:
        prediction = "平局"
    
    return {"编号": match_id, "对阵": f"{home} vs {away}", "V4预测": prediction}


def main():
    folder = "分析模板/3.14"
    
    results_v3 = {}
    results_v4 = {}
    
    for filepath in Path(folder).glob("周六*_源数据.md"):
        v3 = analyze_v3(str(filepath))
        v4 = analyze_v4(str(filepath))
        
        if v3:
            results_v3[v3['编号']] = v3
        if v4:
            results_v4[v4['编号']] = v4
    
    # 找出预测相同的比赛
    same_predictions = []
    diff_predictions = []
    
    for match_id in results_v3:
        if match_id in results_v4:
            v3_pred = results_v3[match_id]['V3预测']
            v4_pred = results_v4[match_id]['V4预测']
            
            # 简化预测结果
            v3_simple = "主" if "主胜" in v3_pred else ("客" if "客胜" in v3_pred else "平")
            v4_simple = "主" if "主胜" in v4_pred else ("客" if "客胜" in v4_pred else "平")
            
            if v3_simple == v4_simple:
                same_predictions.append({
                    "编号": match_id,
                    "对阵": results_v3[match_id]['对阵'],
                    "V3": v3_pred,
                    "V4": v4_pred,
                    "一致": v3_simple
                })
            else:
                diff_predictions.append({
                    "编号": match_id,
                    "对阵": results_v3[match_id]['对阵'],
                    "V3": v3_pred,
                    "V4": v4_pred
                })
    
    # 实际结果
    actual = {
        '周六001': '平', '周六002': '客', '周六003': '平', '周六004': '客',
        '周六005': '主', '周六006': '主', '周六007': '平', '周六008': '主',
        '周六009': '主', '周六010': '客', '周六011': '主', '周六012': '平',
        '周六013': '平', '周六014': '主', '周六015': '主', '周六016': '平',
        '周六017': '平', '周六018': '主', '周六019': '主', '周六020': '主',
        '周六021': '主', '周六022': '主', '周六023': '客', '周六024': '平',
        '周六025': '主', '周六026': '客', '周六027': '客', '周六028': '客',
        '周六029': '平', '周六030': '主', '周六031': '客', '周六032': '平',
    }
    
    # 输出结果
    print("=" * 90)
    print("V3 vs V4 预测对比 - 3.14")
    print("=" * 90)
    
    print(f"\n【预测相同的比赛】共 {len(same_predictions)} 场")
    print("-" * 90)
    
    correct = 0
    for r in same_predictions:
        actual_result = actual.get(r['编号'], '')
        is_correct = r['一致'] == actual_result
        status = "OK" if is_correct else "X"
        if is_correct:
            correct += 1
        print(f"{r['编号']} {r['对阵']:20} | V3:{r['V3']:10} V4:{r['V4']:15} | 一致:{r['一致']} | 实际:{actual_result} {status}")
    
    print(f"\n预测相同准确率: {correct}/{len(same_predictions)} = {correct/len(same_predictions)*100:.1f}%")
    
    print(f"\n\n【预测不同的比赛】共 {len(diff_predictions)} 场")
    print("-" * 90)
    
    correct_v3 = 0
    correct_v4 = 0
    for r in diff_predictions:
        actual_result = actual.get(r['编号'], '')
        
        v3 = r['V3']
        v4 = r['V4']
        
        v3_correct = ("主胜" in v3 and actual_result == "主") or ("客胜" in v3 and actual_result == "客") or (v3 == "平局" and actual_result == "平")
        v4_correct = ("主胜" in v4 and actual_result == "主") or ("客胜" in v4 and actual_result == "客") or (v4 == "平局" and actual_result == "平")
        
        if v3_correct:
            correct_v3 += 1
        if v4_correct:
            correct_v4 += 1
        
        v3_status = "OK" if v3_correct else "X"
        v4_status = "OK" if v4_correct else "X"
        
        print(f"{r['编号']} {r['对阵']:20} | V3:{v3:10}({v3_status}) V4:{v4:15}({v4_status}) | 实际:{actual_result}")
    
    print(f"\n不同预测中 V3正确: {correct_v3}/{len(diff_predictions)} = {correct_v3/len(diff_predictions)*100:.1f}%")
    print(f"不同预测中 V4正确: {correct_v4}/{len(diff_predictions)} = {correct_v4/len(diff_predictions)*100:.1f}%")
    
    return same_predictions, diff_predictions


if __name__ == "__main__":
    main()
