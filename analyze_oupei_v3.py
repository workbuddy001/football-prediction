# -*- coding: utf-8 -*-
"""
基于《欧赔核心思维》的优化算法

核心思路提取：
1. 实盘 vs 韬盘（诱盘）
   - 实盘：降低赔付思维，信心强
   - 韬盘：降低信心思维，诱盘
   
2. 平赔的核心作用
   - 拉低平赔分散胜赔（拉胜分平）
   - 抬高平赔分散胜赔（抬胜分平）
   - 平赔是最有效的分散工具

3. 判断方法
   - 胜赔位置分析：实盘/韬盘/中庸
   - 平赔分散作用分析
   - 受注分布分析
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


def parse_macau(content):
    """解析澳门推荐"""
    match = re.search(r'澳门推荐\s*\|\s*(.+?)\s*\|', content)
    if match:
        recommend = match.group(1).strip()
        if '和' in recommend or '平' in recommend.lower():
            return "平局"
    return None


def parse_odds(content):
    """解析赔率"""
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


def analyze_oupei_v3(content):
    """
    基于《欧赔核心思维》的分析 v3
    
    核心方法：
    1. 分析胜赔位置：实盘/韬盘/中庸
    2. 分析平赔分散作用
    3. 结合澳门推荐
    """
    
    home_form, away_form = parse_team_form(content)
    macau = parse_macau(content)
    initial_odds, realtime_odds = parse_odds(content)
    
    if not initial_odds or not realtime_odds:
        return None
    
    # 计算平均赔率变化
    init = initial_odds[0]
    rt = realtime_odds[0]
    
    # 赔率变化百分比
    home_change = (init['home'] - rt['home']) / init['home'] * 100
    draw_change = (init['draw'] - rt['draw']) / init['draw'] * 100
    away_change = (init['away'] - rt['away']) / init['away'] * 100
    
    # 即时赔率
    avg_home = sum(o['home'] for o in realtime_odds) / len(realtime_odds)
    avg_draw = sum(o['draw'] for o in realtime_odds) / len(realtime_odds)
    avg_away = sum(o['away'] for o in realtime_odds) / len(realtime_odds)
    
    # 状态差距
    form_diff = home_form.get('win_rate', 0) - away_form.get('win_rate', 0)
    
    # ====== 《欧赔核心思维》分析方法 ======
    
    reason = []
    prediction = "待分析"
    confidence = "D"
    
    # 1. 判断胜赔位置（实盘/韬盘/中庸）
    # 核心：根据状态差距判断赔率是否合理
    
    if abs(form_diff) > 30:
        # 状态差距大
        if form_diff > 0:
            # 主队更强
            expected_home = 1.5  # 预期主胜赔率
            if avg_home < expected_home:
                # 强队低赔 - 实盘
                pan_type = "实盘"
                reason.append(f"主队强({home_form.get('win_rate',0)}%)，低赔实盘")
            else:
                pan_type = "韬盘"
                reason.append(f"主队强但高赔，诱盘")
        else:
            # 客队更强
            expected_away = 1.5
            if avg_away < expected_away:
                pan_type = "实盘"
                reason.append(f"客队强({away_form.get('win_rate',0)}%)，低赔实盘")
            else:
                pan_type = "韬盘"
                reason.append(f"客队强但高赔，诱盘")
    else:
        # 状态相近 - 分析平赔分散
        if draw_change > 0 and draw_change < 15:
            # 平赔下降但不过分 - 《欧赔》说这是"拉低平分散胜赔"
            pan_type = "实盘"
            reason.append(f"状态相近，平赔下降{draw_change:.1f}%分散")
        elif draw_change > 15:
            # 平赔大幅下降 - 可能诱盘
            pan_type = "诱盘"
            reason.append(f"状态相近，平赔大降{draw_change:.1f}%异常")
        elif away_change > 10 and home_change < 0:
            # 客胜降水，主胜升水 - "拉胜分平"
            pan_type = "诱盘"
            reason.append(f"胜负反向，分散平局")
        else:
            pan_type = "中庸"
            reason.append("状态相近，中庸盘")
    
    # 2. 结合澳门推荐
    if macau == "平局":
        reason.append("澳门推荐平局")
        # 《欧赔》思维：澳门推荐平局时，要防平
        if "诱盘" in reason or "异常" in str(reason):
            prediction = "防平局"
            confidence = "B"
        else:
            prediction = "关注平局"
            confidence = "C"
    elif macau:
        reason.append(f"澳门推荐:{macau}")
    
    # 3. 最终预测
    if confidence == "D":
        # 默认判断
        if "实盘" in str(reason) and form_diff > 20:
            if form_diff > 0:
                prediction = f"主胜"
                confidence = "B"
            else:
                prediction = f"客胜"
                confidence = "B"
        elif "诱盘" in str(reason):
            # 《欧赔》诱盘思维：防冷
            if form_diff > 0:
                prediction = "防平/客胜"
                confidence = "C"
            else:
                prediction = "防平/主胜"
                confidence = "C"
        else:
            # 中庸盘，看概率
            if avg_home < avg_away and avg_home < 1.8:
                prediction = "主胜"
                confidence = "C"
            elif avg_away < avg_home and avg_away < 1.8:
                prediction = "客胜"
                confidence = "C"
            else:
                prediction = "防平"
                confidence = "C"
    
    return {
        "主队近况": f"{home_form.get('win_rate', 0)}%",
        "客队近况": f"{away_form.get('win_rate', 0)}%",
        "状态差距": f"{form_diff:+.0f}%",
        "即时赔率": f"{avg_home:.2f} / {avg_draw:.2f} / {avg_away:.2f}",
        "赔率变化": f"H:{home_change:+.1f}% D:{draw_change:+.1f}% A:{away_change:+.1f}%",
        "盘型": pan_type,
        "澳门": macau if macau else "-",
        "预测": prediction,
        "把握度": confidence,
        "分析": " | ".join(reason)
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
    
    result = analyze_oupei_v3(content)
    if result:
        return {"编号": match_id, "对阵": f"{home} vs {away}", **result}
    return None


def main():
    folder = "分析模板/3.14"
    
    results = []
    
    for filepath in Path(folder).glob("周六*_源数据.md"):
        result = analyze_match(str(filepath))
        if result:
            results.append(result)
    
    results.sort(key=lambda x: x['编号'])
    
    print("=" * 100)
    print("基于《欧赔核心思维》的分析 v3")
    print("=" * 100)
    
    for r in results:
        print(f"\n{r['编号']} {r['对阵']}")
        print(f"  主队:{r['主队近况']:>4} 客队:{r['客队近况']:>4} 状态差距:{r['状态差距']}")
        print(f"  赔率:{r['即时赔率']}")
        print(f"  变化:{r['赔率变化']}")
        print(f"  盘型:{r['盘型']:>4} 澳门:{r['澳门']:>4} → 预测:{r['预测']:>10} (把握度:{r['把握度']})")
        print(f"  分析:{r['分析']}")
    
    # 复盘
    print("\n" + "=" * 100)
    print("复盘验证")
    print("=" * 100)
    
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
    
    # 按把握度统计
    print("\n按把握度分类：")
    for conf in ["A", "B", "C", "D"]:
        matches = [r for r in results if r['把握度'] == conf]
        if matches:
            correct = 0
            for r in matches:
                actual_result = actual.get(r['编号'], '')
                pred = r['预测']
                
                is_correct = False
                if '主胜' in pred and actual_result == '主':
                    is_correct = True
                elif '客胜' in pred and actual_result == '客':
                    is_correct = True
                elif '平' in pred and actual_result == '平':
                    is_correct = True
                
                if is_correct:
                    correct += 1
            
            total = len(matches)
            pct = correct / total * 100 if total > 0 else 0
            print(f"  把握度{conf}: {correct}/{total} = {pct:.0f}%")
    
    # 总准确率
    correct_total = 0
    for r in results:
        actual_result = actual.get(r['编号'], '')
        pred = r['预测']
        
        is_correct = False
        if '主胜' in pred and actual_result == '主':
            is_correct = True
        elif '客胜' in pred and actual_result == '客':
            is_correct = True
        elif '平' in pred and actual_result == '平':
            is_correct = True
        
        if is_correct:
            correct_total += 1
    
    total = len(results)
    print(f"\n总体准确率: {correct_total}/{total} = {correct_total/total*100:.1f}%")
    
    return results


if __name__ == "__main__":
    results = main()
