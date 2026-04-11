# -*- coding: utf-8 -*-
"""
实盘/诱盘分析 v2 - 最终版
"""

import re
from pathlib import Path

def parse_team_form(content):
    """解析球队状态"""
    # 主队近况 - 精确匹配
    home_match = re.search(r'主队近况.*?近10场[，,]?(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    # 客队近况
    away_match = re.search(r'客队近况.*?近10场[，,]?(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
    
    home_form = {}
    away_form = {}
    
    if home_match:
        home_form = {
            'wins': int(home_match.group(1)),
            'draws': int(home_match.group(2)),
            'losses': int(home_match.group(3)),
            'win_rate': int(home_match.group(4))
        }
    
    if away_match:
        away_form = {
            'wins': int(away_match.group(1)),
            'draws': int(away_match.group(2)),
            'losses': int(away_match.group(3)),
            'win_rate': int(away_match.group(4))
        }
    
    return home_form, away_form


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


def calculate_form_difference(home_form, away_form):
    """计算两队状态差距"""
    if not home_form or not away_form:
        return 0
    
    home_win_rate = home_form.get('win_rate', 0)
    away_win_rate = away_form.get('win_rate', 0)
    
    return home_win_rate - away_win_rate


def calculate_odds_change_pct(initial_odds, realtime_odds):
    """计算赔率变化百分比"""
    if not initial_odds or not realtime_odds:
        return 0, 0, 0, 0
    
    # 使用平均值
    init_home = sum(o['home'] for o in initial_odds) / len(initial_odds)
    init_away = sum(o['away'] for o in initial_odds) / len(initial_odds)
    rt_home = sum(o['home'] for o in realtime_odds) / len(realtime_odds)
    rt_away = sum(o['away'] for o in realtime_odds) / len(realtime_odds)
    
    home_change = (init_home - rt_home) / init_home * 100
    away_change = (init_away - rt_away) / init_away * 100
    
    # 计算降赔公司占比
    home_down = sum(1 for i, o in enumerate(initial_odds) 
                    if i < len(realtime_odds) and o['home'] > realtime_odds[i]['home'])
    away_down = sum(1 for i, o in enumerate(initial_odds) 
                    if i < len(realtime_odds) and o['away'] > realtime_odds[i]['away'])
    
    company_count = len(initial_odds)
    home_down_pct = home_down / company_count * 100 if company_count > 0 else 0
    away_down_pct = away_down / company_count * 100 if company_count > 0 else 0
    
    return home_change, away_change, max(home_down_pct, away_down_pct)


def analyze_panxing_v2(home_form, away_form, initial_odds, realtime_odds):
    """分析实盘/诱盘 v2"""
    
    form_diff = calculate_form_difference(home_form, away_form)
    home_change, away_change, draw_down_pct = calculate_odds_change_pct(initial_odds, realtime_odds)
    
    # 即时赔率
    avg_home = sum(o['home'] for o in realtime_odds) / len(realtime_odds) if realtime_odds else 0
    avg_away = sum(o['away'] for o in realtime_odds) / len(realtime_odds) if realtime_odds else 0
    
    # ====== 判断实盘/诱盘 ======
    # 核心逻辑：状态差距 + 赔率变化
    reason = []
    panxing = "未知"
    
    # 判断强队
    if form_diff > 20:
        strong = "主队"
        weak = "客队"
        strong_odds = avg_home
        strong_change = home_change
    elif form_diff < -20:
        strong = "客队"
        weak = "主队"
        strong_odds = avg_away
        strong_change = away_change
    else:
        strong = "相近"
        strong_odds = min(avg_home, avg_away)
        strong_change = home_change if avg_home < avg_away else away_change
    
    BIG_DROP = 10  # 大幅降水阈值
    
    # 情况1: 状态差距大 (>20%)
    if abs(form_diff) > 20:
        if strong_change > BIG_DROP:
            # 大幅降水
            if draw_down_pct > 60:
                panxing = "诱盘"
                reason.append(f"{strong}强队大幅降水{strong_change:.1f}%，降赔公司{draw_down_pct:.0f}%")
            else:
                panxing = "实盘"
                reason.append(f"{strong}强队降水{strong_change:.1f}%，降赔公司仅{draw_down_pct:.0f}%")
        elif strong_change > 0:
            panxing = "实盘"
            reason.append(f"{strong}强队轻微降水{strong_change:.1f}%")
        elif strong_change < -5:
            panxing = "诱盘"
            reason.append(f"{strong}强队升水{abs(strong_change):.1f}%")
        else:
            panxing = "实盘"
            reason.append(f"{strong}强队赔率稳定")
    
    # 情况2: 状态相近 (<20%)
    else:
        # 你的核心思路：状态相近 + 大幅降水 = 诱盘
        if strong_change > BIG_DROP:
            panxing = "诱盘"
            reason.append(f"状态相近({abs(form_diff):.0f}%)，强队大幅降水{strong_change:.1f}%")
        elif strong_change > 3:
            panxing = "实盘"
            reason.append(f"状态相近，强队轻微降水{strong_change:.1f}%")
        elif strong_change < -3:
            panxing = "诱盘"
            reason.append(f"状态相近，强队反而升水{abs(strong_change):.1f}%")
        else:
            panxing = "实盘"
            reason.append("状态相近，赔率稳定")
    
    return {
        "盘型": panxing,
        "原因": "；".join(reason),
        "状态差距": f"{form_diff:+.0f}%" if form_diff != 0 else "0%",
        "主胜变化": f"{home_change:+.1f}%",
        "客胜变化": f"{away_change:+.1f}%",
        "降赔公司": f"{draw_down_pct:.0f}%",
        "主胜赔率": f"{avg_home:.2f}",
        "客胜赔率": f"{avg_away:.2f}"
    }


def analyze_match_v2(filepath):
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
    
    panxing_result = analyze_panxing_v2(home_form, away_form, initial_odds, realtime_odds)
    
    return {
        "编号": match_id,
        "对阵": f"{home} vs {away}",
        "主队近况": f"{home_form.get('win_rate', 0)}%",
        "客队近况": f"{away_form.get('win_rate', 0)}%",
        **panxing_result
    }


def main():
    folder = "分析模板/3.14"
    
    results = []
    
    for filepath in Path(folder).glob("周六*_源数据.md"):
        result = analyze_match_v2(str(filepath))
        if result:
            results.append(result)
    
    results.sort(key=lambda x: x['编号'])
    
    print("=" * 95)
    print("实盘/诱盘分析 v2 - 基于状态差距 + 赔率变化")
    print("核心思路：状态相近 + 降水>10% = 诱盘 | 状态相近 + 降水<10% = 实盘")
    print("=" * 95)
    print()
    
    for r in results:
        print(f"{r['编号']} {r['对阵']}")
        print(f"  主队近况: {r['主队近况']:>3} | 客队近况: {r['客队近况']:>3} | 状态差距: {r['状态差距']}")
        print(f"  主胜变化: {r['主胜变化']:>6} | 客胜变化: {r['客胜变化']:>6} | 降赔公司: {r['降赔公司']}")
        print(f"  盘型: 【{r['盘型']}】 - {r['原因']}")
        print("-" * 70)
    
    # 统计
    panxing_count = {}
    for r in results:
        p = r['盘型']
        panxing_count[p] = panxing_count.get(p, 0) + 1
    
    print(f"\n盘型统计: {panxing_count}")
    
    # 复盘分析
    print("\n" + "=" * 95)
    print("复盘分析")
    print("=" * 95)
    
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
    
    # 按盘型分类统计
    panxing_results = {}
    for r in results:
        px = r['盘型']
        if px not in panxing_results:
            panxing_results[px] = {'correct': 0, 'total': 0}
        
        actual = actual_results.get(r['编号'], '')
        
        # 判断是否正确
        is_correct = False
        if px == '实盘':
            # 实盘：看好强队
            if r['状态差距'].startswith('+'):
                is_correct = actual == '主'
            elif r['状态差距'].startswith('-'):
                is_correct = actual == '客'
            else:
                # 相近状态，看赔率
                if '主胜变化' in r and float(r['主胜变化'].replace('%','').replace('+','')) > 3:
                    is_correct = actual == '主'
                elif '客胜变化' in r and float(r['客胜变化'].replace('%','').replace('+','')) > 3:
                    is_correct = actual == '客'
        elif px == '诱盘':
            # 诱盘：防冷，看好相反或平局
            if r['状态差距'].startswith('+'):
                is_correct = actual != '主'  # 主强但诱盘，防主胜
            elif r['状态差距'].startswith('-'):
                is_correct = actual != '客'
            else:
                is_correct = actual == '平' or actual != ''
        
        if is_correct:
            panxing_results[px]['correct'] += 1
        panxing_results[px]['total'] += 1
    
    for px, stats in panxing_results.items():
        acc = stats['correct'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"{px}: {stats['correct']}/{stats['total']} = {acc:.0f}%")
    
    return results


if __name__ == "__main__":
    results = main()
