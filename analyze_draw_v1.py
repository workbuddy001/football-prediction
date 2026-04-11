# -*- coding: utf-8 -*-
"""
平局判断逻辑 v1 - 基于用户思路
思路：
1. 澳门心水推荐平局
2. 8成以上公司平赔下降
3. 下降程度不超过10%
4. 平局打出
"""

import re
from pathlib import Path

def parse_team_form(content):
    """解析球队状态"""
    home_match = re.search(r'主队近况.*?近10场[，,]?(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    away_match = re.search(r'客队近况.*?近10场[，,]?(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    
    home_form = {}
    away_form = {}
    
    if home_match:
        home_form = {'win_rate': int(home_match.group(4))}
    if away_match:
        away_form = {'win_rate': int(away_match.group(4))}
    
    return home_form, away_form


def parse_macau_recommend(content):
    """解析澳门推荐 - 表格格式"""
    # 表格格式: | 澳门推荐 | 中国女足的赢 |
    match = re.search(r'澳门推荐\s*\|\s*(.+?)\s*\|', content)
    if match:
        recommend = match.group(1).strip()
        # 判断是否推荐平局
        if '和' in recommend or '平' in recommend.lower():
            return "平局"
        elif recommend and recommend != '待补充':
            return recommend
    return None


def parse_odds_change(content):
    """解析赔率变化"""
    initial_odds = []
    realtime_odds = []
    
    # 解析初盘
    initial_section = re.search(r'## 二、初盘赔率.*?```python(.*?)```', content, re.DOTALL)
    if initial_section:
        odds_text = initial_section.group(1)
        for match in re.finditer(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', odds_text):
            initial_odds.append({
                'home': float(match.group(1)),
                'draw': float(match.group(2)),
                'away': float(match.group(3))
            })
    
    # 解析即时赔率
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


def analyze_draw(content, initial_odds, realtime_odds):
    """
    分析平局可能性
    用户的思路：
    1. 澳门心水推荐平局
    2. 8成以上公司平赔下降
    3. 下降程度不超过10%
    """
    # 1. 检查澳门推荐
    macau_recommend = parse_macau_recommend(content)
    
    if not initial_odds or not realtime_odds:
        return None, "无赔率数据"
    
    # 2. 计算平赔变化和降赔公司占比
    company_count = len(initial_odds)
    draw_down_count = 0
    total_draw_change = 0
    
    for i, init in enumerate(initial_odds):
        if i < len(realtime_odds):
            rt = realtime_odds[i]
            # 变化百分比
            change = (init['draw'] - rt['draw']) / init['draw'] * 100
            total_draw_change += change
            if init['draw'] > rt['draw']:
                draw_down_count += 1
    
    draw_down_pct = draw_down_count / company_count * 100 if company_count > 0 else 0
    avg_draw_change = total_draw_change / company_count if company_count > 0 else 0
    
    # 3. 判断平局特征
    is_draw_signal = False
    reason = []
    
    # 条件1: 澳门推荐平局
    if macau_recommend and ('平' in macau_recommend or '和' in macau_recommend):
        reason.append(f"澳门推荐: {macau_recommend}")
        is_draw_signal = True
    
    # 条件2: 8成以上公司平赔下降
    if draw_down_pct >= 80:
        reason.append(f"降赔公司: {draw_down_pct:.0f}%")
        is_draw_signal = True
    
    # 条件3: 下降程度不超过10%
    if 0 < avg_draw_change <= 10:
        reason.append(f"平赔下降: {avg_draw_change:.1f}%")
        is_draw_signal = True
    elif avg_draw_change > 10:
        reason.append(f"平赔下降过多: {avg_draw_change:.1f}% (>10%)")
    elif avg_draw_change <= 0:
        reason.append(f"平赔未降: {avg_draw_change:.1f}%")
    
    # 综合判断
    draw_score = 0
    if macau_recommend and ('平' in macau_recommend or '和' in macau_recommend):
        draw_score += 1
    if draw_down_pct >= 80:
        draw_score += 1
    if 0 < avg_draw_change <= 10:
        draw_score += 1
    
    # 即时赔率
    avg_draw = sum(o['draw'] for o in realtime_odds) / len(realtime_odds)
    
    return {
        "澳门推荐": macau_recommend if macau_recommend else "无",
        "降赔公司": f"{draw_down_pct:.0f}%",
        "平赔变化": f"{avg_draw_change:+.1f}%",
        "即时平赔": f"{avg_draw:.2f}",
        "平局特征分": draw_score,
        "判断": "平局" if draw_score >= 2 else "非平局",
        "原因": "；".join(reason) if reason else "无明显特征"
    }


def analyze_match(filepath):
    """分析单场比赛"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    filename = Path(filepath).stem
    match = re.match(r'周六(\d+)_(.+?)vs(.+?)_源数据', filename)
    
    if match:
        match_id = f"周六{match.group(1)}"
        home = match.group(2)
        away = match.group(3)
    else:
        return None
    
    home_form, away_form = parse_team_form(content)
    initial_odds, realtime_odds = parse_odds_change(content)
    
    draw_result = analyze_draw(content, initial_odds, realtime_odds)
    
    return {
        "编号": match_id,
        "对阵": f"{home} vs {away}",
        **draw_result
    }


def main():
    folder = "分析模板/3.14"
    
    results = []
    
    for filepath in Path(folder).glob("周六*_源数据.md"):
        result = analyze_match(str(filepath))
        if result:
            results.append(result)
    
    results.sort(key=lambda x: x['编号'])
    
    print("=" * 100)
    print("平局判断分析 - 基于用户思路")
    print("条件: 澳门推荐平局 + 8成以上公司平赔下降 + 下降不超过10%")
    print("=" * 100)
    print()
    
    for r in results:
        print(f"{r['编号']} {r['对阵']}")
        print(f"  澳门推荐: {r['澳门推荐']} | 降赔公司: {r['降赔公司']} | 平赔变化: {r['平赔变化']} | 即时平赔: {r['即时平赔']}")
        print(f"  特征分: {r['平局特征分']}/3 → 判断: 【{r['判断']}】")
        print(f"  原因: {r['原因']}")
        print("-" * 80)
    
    # 统计
    print("\n" + "=" * 100)
    print("复盘验证")
    print("=" * 100)
    
    actual_results = {
        '周六001': '平', '周六002': '客', '周六003': '平', '周六004': '客',
        '周六005': '主', '周六006': '主', '周六007': '平', '周六008': '主',
        '周六009': '主', '周六010': '客', '周六011': '主', '周六012': '平',
        '周六013': '平', '周六014': '主', '周六015': '主', '周六016': '平',
        '周六017': '平', '周六018': '主', '周六019': '主', '周六020': '主',
        '周六021': '主', '周六022': '主', '周六023': '客', '周六024': '平',
        '周六025': '主', '周六026': '客', '周六027': '客', '周六028': '客',
        '周六029': '平', '周六030': '主', '周六031': '客', '周六032': '平',
    }
    
    # 按特征分统计
    for score in [0, 1, 2, 3]:
        matches = [r for r in results if r['平局特征分'] == score]
        if matches:
            correct = sum(1 for r in matches if actual_results.get(r['编号']) == '平')
            total = len(matches)
            acc = correct / total * 100 if total > 0 else 0
            print(f"特征分{score}: {correct}/{total} = {acc:.0f}% (平局率: {total/32*100:.0f}%)")
    
    # 判断为平局的统计
    draw_matches = [r for r in results if r['判断'] == '平局']
    if draw_matches:
        correct = sum(1 for r in draw_matches if actual_results.get(r['编号']) == '平')
        total = len(draw_matches)
        acc = correct / total * 100 if total > 0 else 0
        print(f"\n判断为平局: {correct}/{total} = {acc:.0f}%")
    
    # 高特征分(>=2)的统计
    high_matches = [r for r in results if r['平局特征分'] >= 2]
    if high_matches:
        correct = sum(1 for r in high_matches if actual_results.get(r['编号']) == '平')
        total = len(high_matches)
        acc = correct / total * 100 if total > 0 else 0
        print(f"高特征分(>=2): {correct}/{total} = {acc:.0f}%")
    
    return results


if __name__ == "__main__":
    results = main()
