# -*- coding: utf-8 -*-
"""
平局判断逻辑 v2 - 简化版
思路：
1. 8成以上公司平赔下降
2. 澳门心水推荐平局
3. 高度防平
"""

import re
from pathlib import Path

def parse_macau_recommend(content):
    """解析澳门推荐 - 表格格式"""
    match = re.search(r'澳门推荐\s*\|\s*(.+?)\s*\|', content)
    if match:
        recommend = match.group(1).strip()
        if '和' in recommend or ('平' in recommend.lower() and ' ' not in recommend.replace('和','')):
            return "平局"
    return None


def parse_odds_change(content):
    """解析赔率变化"""
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
    
    # 澳门推荐
    macau = parse_macau_recommend(content)
    
    # 赔率变化
    initial_odds, realtime_odds = parse_odds_change(content)
    
    if not initial_odds or not realtime_odds:
        return None
    
    # 计算降赔公司
    company_count = len(initial_odds)
    draw_down_count = 0
    
    for i, init in enumerate(initial_odds):
        if i < len(realtime_odds):
            if init['draw'] > realtime_odds[i]['draw']:
                draw_down_count += 1
    
    draw_down_pct = draw_down_count / company_count * 100 if company_count > 0 else 0
    
    # 判断：8成公司平赔下降
    is_80_pct = draw_down_pct >= 80
    
    # 判断：澳门推荐平局
    is_macau_draw = macau == "平局"
    
    # 综合判断
    if is_80_pct and is_macau_draw:
        signal = "高度防平"
    elif is_80_pct:
        signal = "关注平局"
    elif is_macau_draw:
        signal = "澳门看平"
    else:
        signal = "正常"
    
    # 即时平赔
    avg_draw = sum(o['draw'] for o in realtime_odds) / len(realtime_odds)
    
    return {
        "编号": match_id,
        "对阵": f"{home} vs {away}",
        "澳门推荐": macau if macau else "-",
        "降赔公司": f"{draw_down_pct:.0f}%",
        "即时平赔": f"{avg_draw:.2f}",
        "判断": signal
    }


def main():
    folder = "分析模板/3.14"
    
    results = []
    
    for filepath in Path(folder).glob("周六*_源数据.md"):
        result = analyze_match(str(filepath))
        if result:
            results.append(result)
    
    results.sort(key=lambda x: x['编号'])
    
    print("=" * 90)
    print("平局判断 v2 - 简化版")
    print("条件: 8成公司平赔下降 + 澳门推荐平局 = 高度防平")
    print("=" * 90)
    print()
    
    for r in results:
        flag = "*" if r['判断'] == "高度防平" else ""
        print(f"{r['编号']} {r['对阵']}")
        print(f"  澳门: {r['澳门推荐']:8} | 降赔: {r['降赔公司']:5} | 平赔: {r['即时平赔']:5} | {r['判断']} {flag}")
        print("-" * 70)
    
    # 复盘
    print("\n" + "=" * 90)
    print("复盘验证")
    print("=" * 90)
    
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
    
    # 按判断分类
    print("\n按判断分类：")
    for signal_type in ["高度防平", "关注平局", "澳门看平", "正常"]:
        matches = [r for r in results if r['判断'] == signal_type]
        if matches:
            correct = sum(1 for r in matches if actual.get(r['编号']) == '平')
            total = len(matches)
            pct = correct / total * 100 if total > 0 else 0
            print(f"  {signal_type}: {correct}/{total} = {pct:.0f}%")
            for r in matches:
                result = "[平]" if actual.get(r['编号']) == '平' else "[x]"
                print(f"    {r['编号']}: {result}")
    
    return results


if __name__ == "__main__":
    results = main()
