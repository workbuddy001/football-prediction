"""
3.10比赛分析脚本
基于工作记忆中的验证规律 + 赔率绝对值分析
"""

import os
import re

DATA_DIR = "d:/work/workbuddy/足球预测/分析模板/3.10"

# 比赛文件列表
MATCH_FILES = [
    "周二001_印度女vs中国台女_源数据.md",
    "周二002_日本女vs越南女_源数据.md",
    "周二003_町田泽维vs江原FC_源数据.md",
    "周二004_布里兰vs墨尔本城_源数据.md",
    "周二005_加拉塔萨vs利物浦_源数据.md",
    "周二006_朴次茅斯vs斯旺西_源数据.md",
    "周二007_亚特兰大vs拜仁_源数据.md",
    "周二008_马竞vs热刺_源数据.md",
    "周二009_纽卡斯尔vs巴萨_源数据.md",
]

def parse_match_file(filepath):
    """解析单个比赛源数据文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # 提取编号
    match_id = ""
    for line in lines:
        if '编号：' in line:
            m = re.search(r'编号：(.+?)\|', line)
            if m:
                match_id = m.group(1).strip()
                break
    
    # 提取主客队
    home_team = ""
    away_team = ""
    macao_tip = ""
    home_trend = ""
    away_trend = ""
    
    # 找到基本信息表结束位置
    table_end = 0
    for i, line in enumerate(lines):
        if line.strip() == "---" and i > 15:
            table_end = i
            break
        if "## 二、" in line:
            table_end = i
            break
    
    search_lines = lines[:table_end] if table_end > 0 else lines
    
    for line in search_lines:
        if '| 主队 |' in line and line.count('|') == 3:
            m = re.search(r'\| 主队 \|\s*(.+?)\s*\|', line)
            if m:
                home_team = m.group(1).strip()
        if '| 客队 |' in line and line.count('|') == 3:
            m = re.search(r'\| 客队 \|\s*(.+?)\s*\|', line)
            if m:
                away_team = m.group(1).strip()
        if '| 澳门推荐 |' in line and line.count('|') == 3:
            m = re.search(r'\| 澳门推荐 \|\s*(.+?)\s*\|', line)
            if m:
                macao_tip = m.group(1).strip()
        if '| 主队近况走势 |' in line and line.count('|') == 3:
            m = re.search(r'\| 主队近况走势 \|\s*(.+?)\s*\|', line)
            if m:
                home_trend = m.group(1).strip()
        if '| 客队近况走势 |' in line and line.count('|') == 3:
            m = re.search(r'\| 客队近况走势 \|\s*(.+?)\s*\|', line)
            if m:
                away_trend = m.group(1).strip()
    
    # 提取竞彩赔率
    jc_home = jc_draw = jc_away = 0
    in_jingcai_section = False
    for line in lines:
        if '竞彩胜平负赔率' in line:
            in_jingcai_section = True
            continue
        if in_jingcai_section and '| 主胜' in line:
            m = re.search(r'\| ([\d.]+)', line)
            if m:
                jc_home = float(m.group(1))
        if in_jingcai_section and '| 平局' in line:
            m = re.search(r'\| ([\d.]+)', line)
            if m:
                jc_draw = float(m.group(1))
        if in_jingcai_section and '| 客胜' in line:
            m = re.search(r'\| ([\d.]+)', line)
            if m:
                jc_away = float(m.group(1))
            in_jingcai_section = False
    
    # 提取赔率变化
    init_home = init_draw = init_away = 0
    rt_home = rt_draw = rt_away = 0
    
    in_change_section = False
    for line in lines:
        if '赔率变动对比' in line:
            in_change_section = True
            continue
        if in_change_section and '竞*官*' in line:
            parts = line.split('|')
            if len(parts) >= 11:
                try:
                    init_home = float(parts[2].strip())
                    rt_home = float(parts[3].strip())
                    init_draw = float(parts[5].strip())
                    rt_draw = float(parts[6].strip())
                    init_away = float(parts[8].strip())
                    rt_away = float(parts[9].strip())
                except:
                    pass
            in_change_section = False
    
    return {
        "id": match_id,
        "home": home_team,
        "away": away_team,
        "macao": macao_tip,
        "home_trend": home_trend,
        "away_trend": away_trend,
        "jc_home": jc_home,
        "jc_draw": jc_draw,
        "jc_away": jc_away,
        "init_home": init_home,
        "init_draw": init_draw,
        "init_away": init_away,
        "rt_home": rt_home,
        "rt_draw": rt_draw,
        "rt_away": rt_away,
    }

def calculate_form_score(trend):
    """计算近况评分"""
    if not trend:
        return None, None
    
    score_map = {'W': 3, 'D': 1, 'L': 0, '胜': 3, '平': 1, '负': 0}
    recent = trend[:5] if len(trend) >= 5 else trend
    
    scores = []
    for i, char in enumerate(recent):
        if char in score_map:
            weight = 2 if i == 0 else 1
            scores.append(score_map[char] * weight)
    
    if not scores:
        return None, None
    
    total = sum(scores)
    normalized = total / 15 * 100
    return total, normalized

def calculate_confidence(home, draw, away):
    """计算置信度"""
    if home + draw + away == 0:
        return 0, 0, 0, 0
    total = home + draw + away
    home_rate = (total / home) * 100 / 3
    draw_rate = (total / draw) * 100 / 3
    away_rate = (total / away) * 100 / 3
    total_rate = home_rate + draw_rate + away_rate
    home_rate = home_rate / total_rate * 100
    draw_rate = draw_rate / total_rate * 100
    away_rate = away_rate / total_rate * 100
    max_rate = max(home_rate, draw_rate, away_rate)
    return max_rate, home_rate, draw_rate, away_rate

def fmt_change(init_val, rt_val):
    """计算赔率变化百分比"""
    if not init_val or not rt_val:
        return 0
    return (rt_val - init_val) / init_val * 100

def analyze_odds_absolute(m, r):
    """
    赔率绝对值分析（新增2026-03-22）
    返回: (修正预测, 问题分析)
    
    核心原则：只在极端赔率值时进行修正，不覆盖正常判断
    """
    rt_home = m['rt_home']
    rt_draw = m['rt_draw']
    rt_away = m['rt_away']
    score_diff = r['score_diff']
    macao_dir = r['macao_dir']
    h_chg = r['h_chg']
    a_chg = r['a_chg']
    conf = r['conf']
    
    pred = None
    issue = ""
    
    # 规则1: 客胜赔率 >= 4.5 → 很难打出（极端高赔）
    if rt_away >= 4.5:
        if score_diff > 0 and macao_dir == "主队":
            pred = "主胜"
            issue = f"[!]客胜{rt_away:.2f}太高，状态+{score_diff}也撑不起"
        elif score_diff > 0:
            issue += f" [!]客胜{rt_away:.2f}偏高"
    
    # 规则2: 主胜赔率 >= 4.5 → 庄家极不信任
    if rt_home >= 4.5 and macao_dir == "客队":
        if rt_away < 1.55:
            pred = "防平"
            issue += f" [!]主胜{rt_home:.2f}太高，客胜{rt_away:.2f}太便宜需防冷"
    
    # 规则3: 豪门客胜 < 2.15 → 太舒服，需防冷
    if rt_away < 2.15 and macao_dir != "主队":
        if score_diff > 0:
            # 主队状态更好且被低看
            pred = "主队不败"
            issue += f" [!]客胜{rt_away:.2f}对客队太舒服，主队受让有望不败"
        else:
            issue += f" [!]客胜{rt_away:.2f}偏低"
    
    # 规则4: 赔率不变 + 状态差 >= -8 → 高压区
    if h_chg == 0 and a_chg == 0 and score_diff <= -8:
        issue += f" [!]赔率不变+状态差{score_diff}，高压区防冷"
        if macao_dir == "客队":
            pred = "主队不败"
    
    return pred, issue.strip()

# 解析所有比赛
print("="*100)
print("3.10比赛分析（加入赔率绝对值分析）")
print("="*100)

matches = []
for mf in MATCH_FILES:
    filepath = os.path.join(DATA_DIR, mf)
    if os.path.exists(filepath):
        m = parse_match_file(filepath)
        matches.append(m)
        print(f"解析: {m['id']} {m['home']} vs {m['away']}")

print(f"\n共解析 {len(matches)} 场比赛\n")

# 分析每场比赛
results = []
for m in matches:
    home = m['jc_home']
    draw = m['jc_draw']
    away = m['jc_away']
    
    conf, home_rate, draw_rate, away_rate = calculate_confidence(home, draw, away)
    
    if home_rate >= draw_rate and home_rate >= away_rate:
        raw_pred = "主胜"
    elif away_rate >= home_rate and away_rate >= draw_rate:
        raw_pred = "客胜"
    else:
        raw_pred = "平局"
    
    home_score, _ = calculate_form_score(m['home_trend'])
    away_score, _ = calculate_form_score(m['away_trend'])
    score_diff = home_score - away_score if (home_score and away_score) else 0
    
    h_chg = fmt_change(m['init_home'], m['rt_home'])
    d_chg = fmt_change(m['init_draw'], m['rt_draw'])
    a_chg = fmt_change(m['init_away'], m['rt_away'])
    
    macao = m['macao']
    if "和局" in macao or "平局" in macao:
        macao_dir = "和局"
    elif m['home'] in macao:
        macao_dir = "主队"
    elif m['away'] in macao:
        macao_dir = "客队"
    else:
        macao_dir = "未知"
    
    results.append({
        "id": m['id'],
        "home": m['home'],
        "away": m['away'],
        "macao": m['macao'],
        "macao_dir": macao_dir,
        "conf": conf,
        "raw_pred": raw_pred,
        "home_score": home_score,
        "away_score": away_score,
        "score_diff": score_diff,
        "h_chg": h_chg,
        "d_chg": d_chg,
        "a_chg": a_chg,
        "init_home": m['init_home'],
        "init_draw": m['init_draw'],
        "init_away": m['init_away'],
        "rt_home": m['rt_home'],
        "rt_draw": m['rt_draw'],
        "rt_away": m['rt_away'],
    })

# 打印完整数据列表（按模板格式）
print("\n" + "="*120)
print("【完整数据列表】")
print("="*120)
print(f"{'编号':<8} {'对阵':<22} {'置信度':<6} {'澳门':<6} {'近况差':<4} {'初盘(胜/平/负)':<22} {'即时(胜/平/负)':<22} {'变化(H/D/A)':<20}")
print("-"*120)

for r in results:
    match_name = f"{r['home'][:6]}vs{r['away'][:6]}"
    init_odds = f"{r['init_home']}/{r['init_draw']}/{r['init_away']}" if r['init_home'] else "-/-/-"
    rt_odds = f"{r['rt_home']}/{r['rt_draw']}/{r['rt_away']}" if r['rt_home'] else "-/-/-"
    change = f"H{r['h_chg']:+.1f}% D{r['d_chg']:+.1f}% A{r['a_chg']:+.1f}%"
    print(f"{r['id']:<8} {match_name:<22} {r['conf']:.1f}%  {r['macao_dir']:<6} {r['score_diff']:+d}   {init_odds:<22} {rt_odds:<22} {change:<20}")

# 应用验证规律 + 赔率绝对值分析
print("\n" + "="*120)
print("【最终预测 - 应用验证规律 + 赔率绝对值分析】")
print("="*120)
print(f"{'编号':<8} {'对阵':<22} {'澳门':<6} {'修正预测':<8} {'问题分析'}")
print("-"*120)

final_predictions = []

for i, r in enumerate(results):
    m = matches[i]
    conf = r['conf']
    macao_dir = r['macao_dir']
    score_diff = r['score_diff']
    h_chg = r['h_chg']
    a_chg = r['a_chg']
    d_chg = r['d_chg']
    raw_pred = r['raw_pred']
    
    pred = raw_pred
    reason = ""
    
    # ==================== 应用验证规律 ====================
    
    # 规律五：主胜升幅>5% → 平局概率大（优先级最高）
    if h_chg > 5:
        pred = "平局"
        reason = f"主胜升幅>{h_chg:.1f}%→防平"
    
    # 规律一：分胜负赛 + 置信度≥66%
    elif macao_dir != "和局" and conf >= 66:
        pred = raw_pred
        reason = f"置信度≥66%可信({conf:.0f}%)"
    
    # 规律三：置信度≤40%
    elif conf <= 40:
        if macao_dir == "主队":
            pred = "平局" if h_chg >= 0 else raw_pred
            reason = f"低置信度({conf:.0f}%)+澳门推主{'+应降不降' if h_chg >= 0 else ''}"
        elif macao_dir == "客队":
            pred = "平局" if a_chg >= 0 else raw_pred
            reason = f"低置信度({conf:.0f}%)+澳门推客{'+应降不降' if a_chg >= 0 else ''}"
        elif macao_dir == "和局":
            pred = "主胜" if "客" in r['away'] else "客胜"
            reason = f"低置信度({conf:.0f}%)+澳门推和局→反向"
        else:
            reason = f"低置信度({conf:.0f}%)按原预测"
    
    # 近况差≥5 + 赔率分散判断
    elif abs(score_diff) >= 5:
        if macao_dir == "主队" and score_diff >= 5:
            if h_chg < 0:
                pred = "主胜"
                reason = f"近况好(+{score_diff})+主降{h_chg:.1f}%→分散成功"
            else:
                pred = "客胜"
                reason = f"近况好(+{score_diff})+主升{h_chg:.1f}%→无法分散"
        elif macao_dir == "客队" and score_diff <= -5:
            if a_chg < 0:
                pred = "客胜"
                reason = f"近况客好({score_diff})+客降{a_chg:.1f}%→分散成功"
            else:
                pred = "主胜"
                reason = f"近况客好({score_diff})+客升{a_chg:.1f}%→无法分散"
        else:
            reason = f"近况差{score_diff}按原预测"
    
    # 规律A：澳门推和局 + 平赔上升
    elif macao_dir == "和局" and d_chg > 0:
        pred = "主胜" if h_chg < a_chg else "客胜"
        reason = f"澳门推和局+平升{d_chg:.1f}%→排除和局"
    
    # 规律二：澳门推和局 + 平降>5%
    elif macao_dir == "和局" and d_chg < -5:
        pred = "主胜" if h_chg < a_chg else "客胜"
        reason = f"澳门推和局+平降{d_chg:.1f}%→平局难出"
    
    else:
        reason = "维持原预测"
    
    # ==================== 赔率绝对值分析（作为补充）====================
    odds_pred, odds_issue = analyze_odds_absolute(m, r)
    
    # 只有当赔率绝对值分析给出明确修正，且原预测与修正不冲突时才覆盖
    if odds_pred and odds_issue:
        if odds_pred == "主队不败":
            pred = "主胜/平局"
            reason = odds_issue
        elif odds_pred == "防平":
            # 保持原预测，添加说明
            reason = reason + " " + odds_issue if reason else odds_issue
        elif odds_pred == "主胜" and pred != "主胜":
            # 只有当原预测不是主胜时才覆盖
            if pred in ["客胜", "平局"]:
                pred = odds_pred
                reason = odds_issue
            else:
                reason = reason + " " + odds_issue if reason else odds_issue
        else:
            # 其他情况只添加说明
            if reason and odds_issue not in reason:
                reason = reason + " " + odds_issue
            elif not reason:
                reason = odds_issue
    
    final_predictions.append({
        "id": r['id'],
        "home": r['home'],
        "away": r['away'],
        "macao_dir": macao_dir,
        "conf": conf,
        "score_diff": score_diff,
        "init_odds": f"{r['init_home']}/{r['init_draw']}/{r['init_away']}" if r['init_home'] else "-/-/-",
        "rt_odds": f"{r['rt_home']}/{r['rt_draw']}/{r['rt_away']}" if r['rt_home'] else "-/-/-",
        "h_chg": h_chg,
        "d_chg": d_chg,
        "a_chg": a_chg,
        "pred": pred,
        "reason": reason,
    })
    
    match_name = f"{r['home'][:6]}vs{r['away'][:6]}"
    print(f"{r['id']:<8} {match_name:<22} {macao_dir:<6} {pred:<8} {reason}")

# 汇总
print("\n" + "="*100)
print("【最终预测汇总】")
print("="*100)
for p in final_predictions:
    print(f"{p['id']}: {p['home']} vs {p['away']} → {p['pred']}")

# 保存结果
output_file = "d:/work/workbuddy/足球预测/3.10_analysis_result.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("3.10比赛分析结果\n")
    f.write("="*80 + "\n\n")
    for p in final_predictions:
        f.write(f"{p['id']} {p['home']} vs {p['away']}\n")
        f.write(f"  澳门推荐: {p['macao_dir']} | 置信度: {p['conf']:.1f}%\n")
        f.write(f"  近况差: {p['score_diff']:+d} | 赔率: {p['init_odds']} → {p['rt_odds']}\n")
        f.write(f"  变化: H{p['h_chg']:+.1f}% D{p['d_chg']:+.1f}% A{p['a_chg']:+.1f}%\n")
        f.write(f"  预测: {p['pred']} | 理由: {p['reason']}\n\n")

print(f"\n结果已保存到: {output_file}")
