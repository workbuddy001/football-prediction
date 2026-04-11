"""
3.21 比赛 - 完整预测列表（从源数据自动提取"竞*官*"的初盘+即时赔率）
新增：近况评分分析
"""

import os
import re
import glob

DATA_DIR = "d:/work/workbuddy/足球预测/分析模板/3.21"

def extract_jingcai_odds(match_id):
    """从源数据文件提取"竞*官*"的初盘和即时赔率"""
    file_path = f"{DATA_DIR}/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return None, None, None, None, None, None
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        in_table = False
        for i, line in enumerate(lines):
            if '初盘胜' in line and '即时胜' in line:
                in_table = True
                continue
            if in_table:
                if line.startswith('---') or line.startswith('## '):
                    break
                if '竞*官*' in line and '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 10:
                        try:
                            return (float(parts[2]), float(parts[5]), float(parts[8]),
                                    float(parts[3]), float(parts[6]), float(parts[9]))
                        except:
                            pass
        
        return None, None, None, None, None, None
        
    except Exception as e:
        print(f"读取{match_id}竞彩赔率出错: {e}")
        return None, None, None, None, None, None


def extract_form_trend(match_id):
    """提取主客队近况走势"""
    file_path = f"{DATA_DIR}/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return "", ""
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找主队近况走势 - 使用表格格式匹配
        home_trend = ""
        away_trend = ""
        
        # 匹配表格中的走势: | 主队近况走势 | LWWLDW |
        match = re.search(r'主队近况走势\s*\|\s*([WDLwdl]+)', content)
        if match:
            home_trend = match.group(1).upper()
        
        match = re.search(r'客队近况走势\s*\|\s*([WDLwdl]+)', content)
        if match:
            away_trend = match.group(1).upper()
        
        return home_trend, away_trend
        
    except Exception as e:
        print(f"提取走势出错 {match_id}: {e}")
        return "", ""


def calculate_form_score(trend):
    """
    计算近况评分
    评分规则：最近一场权重2，其他权重1
    得分：赢=3分，平=1分，输=0分
    """
    if not trend:
        return None
    
    # 映射: W=胜(3分), D=平(1分), L=负(0分)
    score_map = {'W': 3, 'D': 1, 'L': 0}
    
    # 只取最近5场
    recent = trend[:5] if len(trend) >= 5 else trend
    
    scores = []
    for i, char in enumerate(recent):
        if char in score_map:
            weight = 2 if i == 0 else 1
            scores.append(score_map[char] * weight)
    
    return sum(scores) if scores else None


def analyze_form_vs_odds(home_trend, away_trend, odds_change):
    """
    分析近况与赔率变化的关系
    返回: (分析结果, 近况差值)
    """
    home_score = calculate_form_score(home_trend)
    away_score = calculate_form_score(away_trend)
    
    if home_score is None or away_score is None:
        return "无近况数据", 0
    
    score_diff = home_score - away_score
    
    # 分析近况与赔率关系
    if score_diff >= 6:  # 主队近况明显更好
        if odds_change.get("home", 0) < -2:
            return "[OK]近况支持+赔率降水", score_diff
        elif odds_change.get("home", 0) > 2:
            return "[!]近况支持但赔上升-防冷", score_diff
        else:
            return "[!]近况支持+赔不变", score_diff
    elif score_diff <= -6:  # 客队近况明显更好
        if odds_change.get("away", 0) < -2:
            return "[OK]近况支持+赔率降水", score_diff
        elif odds_change.get("away", 0) > 2:
            return "[!]近况支持但赔上升-防冷", score_diff
        else:
            return "[!]近况支持+赔不变", score_diff
    else:
        return "双方近况接近", score_diff


def fmt_change(init_val, real_val):
    """格式化赔率变化幅度"""
    if init_val is None or real_val is None or init_val == 0:
        return "—"
    pct = (real_val - init_val) / init_val * 100
    if abs(pct) < 0.1:
        return "—"
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"


def extract_macao_tip(match_id):
    """提取澳门推荐"""
    file_path = f"{DATA_DIR}/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return None
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        match = re.search(r'澳门推荐\s*\|\s*([^\n|]+)', content)
        if match:
            return match.group(1).strip()
        
        return None
        
    except Exception as e:
        return None


def extract_match_name(match_id):
    """提取比赛名称"""
    file_path = f"{DATA_DIR}/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return match_id
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        home_match = re.search(r'主队\s*\|\s*([^\n|]+)', content)
        away_match = re.search(r'客队\s*\|\s*([^\n|]+)', content)
        
        home = home_match.group(1).strip() if home_match else "主队"
        away = away_match.group(1).strip() if away_match else "客队"
        
        return f"{home} vs {away}"
        
    except Exception as e:
        return match_id


# 比赛ID列表（3.21）
match_ids = [
    "周六001", "周六002", "周六003", "周六004", "周六005",
    "周六006", "周六007", "周六008", "周六009", "周六010",
    "周六011", "周六012", "周六013", "周六014", "周六015",
    "周六016", "周六017", "周六018", "周六019", "周六020",
    "周六021", "周六022", "周六023", "周六024", "周六025",
    "周六026", "周六027", "周六028", "周六029", "周六030",
    "周日001", "周日002", "周日003", "周日004", "周日005",
    "周日006", "周日007", "周日008", "周日009", "周日010",
    "周日011", "周日012", "周日013", "周日014", "周日015",
    "周日016", "周日017", "周日018", "周日019", "周日020",
    "周日021", "周日022", "周日023", "周日024", "周日025",
    "周日026", "周日027", "周日028",
]

# 自动提取所有比赛的竞彩赔率
matches_data = {}
for mid in match_ids:
    init_home, init_draw, init_away, real_home, real_draw, real_away = extract_jingcai_odds(mid)
    match_name = extract_match_name(mid)
    macao = extract_macao_tip(mid)
    home_trend, away_trend = extract_form_trend(mid)
    
    if real_home is not None and real_draw is not None and real_away is not None:
        matches_data[mid] = {
            "match": match_name,
            "init_home": init_home, "init_draw": init_draw, "init_away": init_away,
            "home": real_home, "draw": real_draw, "away": real_away,
            "macao": macao,
            "home_trend": home_trend,
            "away_trend": away_trend,
        }
        print(f"{mid}: 初盘{init_home}/{init_draw}/{init_away} -> 即时{real_home}/{real_draw}/{real_away} | 澳门: {macao}")
    else:
        print(f"{mid}: 未找到竞彩数据!")


def calculate_confidence(home, draw, away):
    """计算置信度和各选项概率"""
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


# 生成预测结果
results = []

for mid, data in matches_data.items():
    home = data['home']
    draw = data['draw']
    away = data['away']
    init_home = data['init_home']
    init_draw = data['init_draw']
    init_away = data['init_away']
    macao = data['macao']
    home_trend = data['home_trend']
    away_trend = data['away_trend']
    
    confidence, home_rate, draw_rate, away_rate = calculate_confidence(home, draw, away)
    
    # 根据概率确定预测
    if home_rate >= draw_rate and home_rate >= away_rate:
        odds_pred = "主胜"
    elif away_rate >= home_rate and away_rate >= draw_rate:
        odds_pred = "客胜"
    else:
        odds_pred = "平局"
    
    rate_diff = home_rate - away_rate
    
    if confidence > 0:
        deviation = abs(rate_diff) / confidence
    else:
        deviation = 0
    
    # 偏离类型
    if deviation > 0.7:
        deviation_type = "偏离过高"
    elif deviation < 0.3:
        deviation_type = "实盘"
    else:
        deviation_type = "中庸"
    
    # 澳门推荐方向
    macao_dir = "和局"
    if macao:
        if "和局" in macao:
            macao_dir = "和局"
        elif "主" in macao:
            macao_dir = "主胜"
        elif "客" in macao or "贏" in macao:
            macao_dir = "客胜"
    
    # 赔率变化
    odds_change = {
        "home": (home - init_home) / init_home * 100 if init_home else 0,
        "draw": (draw - init_draw) / init_draw * 100 if init_draw else 0,
        "away": (away - init_away) / init_away * 100 if init_away else 0,
    }
    
    # 近况分析
    form_analysis, score_diff = analyze_form_vs_odds(home_trend, away_trend, odds_change)
    home_form = calculate_form_score(home_trend)
    away_form = calculate_form_score(away_trend)
    
    results.append({
        "id": mid,
        "match": data['match'],
        "odds": f"{home}/{draw}/{away}",
        "init_odds": f"{init_home}/{init_draw}/{init_away}",
        "confidence": confidence,
        "home_rate": home_rate,
        "draw_rate": draw_rate,
        "away_rate": away_rate,
        "macao": macao,
        "macao_dir": macao_dir,
        "prediction": odds_pred,
        "deviation": deviation_type,
        "odds_change": odds_change,
        "home_trend": home_trend,
        "away_trend": away_trend,
        "home_form": home_form,
        "away_form": away_form,
        "form_diff": score_diff,
        "form_analysis": form_analysis,
    })


# 输出详细分析
print("\n" + "="*150)
print("3.21比赛 - 完整预测列表（含近况评分分析）")
print("="*150)
print(f"{'编号':<8} {'对阵':<22} {'竞彩即时':<14} {'置信度':<6} {'澳门':<14} {'预测':<4} {'赔率变化':<22} {'主队走势':<6} {'客队走势':<6} {'近况差':<5} {'近况分析'}")
print("-"*150)

single_picks = []

for r in results:
    home_trend = r["home_trend"][:5] if r["home_trend"] else "-"
    away_trend = r["away_trend"][:5] if r["away_trend"] else "-"
    home_form = r["home_form"] if r["home_form"] else "-"
    away_form = r["away_form"] if r["away_form"] else "-"
    form_diff = r["form_diff"] if r["form_diff"] else 0
    
    # 赔率变化
    odds_change = r["odds_change"]
    pct_h = odds_change.get("home", 0)
    pct_d = odds_change.get("draw", 0)
    pct_a = odds_change.get("away", 0)
    chg_str = f"H{pct_h:+.1f}% D{pct_d:+.1f}% A{pct_a:+.1f}%"
    
    print(f"{r['id']:<8} {r['match']:<22} {r['odds']:<14} {r['confidence']:.1f}%  {r['macao']:<14} {r['prediction']:<4} {chg_str:<22} {home_trend:<6} {away_trend:<6} {form_diff:+4.0f}   {r['form_analysis']}")
    
    # 单选条件
    is_single = False
    if r["macao_dir"] != "和局" and r["confidence"] >= 66:
        is_single = True
    
    if is_single:
        single_picks.append(r)


# 单选列表
print("\n" + "="*150)
print("[单选列表] 澳门分胜负 + 置信度>=66%")
print("="*150)
print(f"{'编号':<8} {'对阵':<22} {'竞彩即时':<14} {'置信度':<6} {'澳门':<14} {'预测':<4} {'赔率变化':<22} {'主队分':<5} {'客队分':<5} {'近况差':<5} {'近况验证'}")
print("-"*150)

for r in single_picks:
    home_form = r["home_form"] if r["home_form"] else "-"
    away_form = r["away_form"] if r["away_form"] else "-"
    form_diff = r["form_diff"] if r["form_diff"] else 0
    
    # 近况验证
    verify = r["form_analysis"]
    
    # 赔率变化
    odds_change = r["odds_change"]
    pct_h = odds_change.get("home", 0)
    pct_d = odds_change.get("draw", 0)
    pct_a = odds_change.get("away", 0)
    chg_str = f"H{pct_h:+.1f}% D{pct_d:+.1f}% A{pct_a:+.1f}%"
    
    print(f"{r['id']:<8} {r['match']:<22} {r['odds']:<14} {r['confidence']:.1f}%  {r['macao']:<14} {r['prediction']:<4} {chg_str:<22} {str(home_form):<5} {str(away_form):<5} {form_diff:+4.0f}   {verify}")

print(f"\n共 {len(single_picks)} 场可单选")


# 保存结果
output_file = "d:/work/workbuddy/足球预测/3.21_result.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("3.21比赛 - 完整预测列表（含近况评分分析）\n")
    f.write("="*120 + "\n\n")
    f.write("评分规则：最近一场权重2，其他权重1 | 赢=3分，平=1分，输=0分\n")
    f.write("近况差：正值表示主队近况更好，负值表示客队近况更好\n\n")
    
    f.write("[详细分析列表]\n")
    f.write("-"*150 + "\n")
    f.write(f"{'编号':<8} {'对阵':<22} {'竞彩即时':<14} {'置信度':<6} {'澳门':<14} {'预测':<4} {'赔率变化':<22} {'主队走势':<6} {'客队走势':<6} {'近况差':<5} {'近况分析'}\n")
    f.write("-"*150 + "\n")
    
    for r in results:
        home_trend = r["home_trend"][:5] if r["home_trend"] else "-"
        away_trend = r["away_trend"][:5] if r["away_trend"] else "-"
        form_diff = r["form_diff"] if r["form_diff"] else 0
        
        # 赔率变化
        odds_change = r["odds_change"]
        pct_h = odds_change.get("home", 0)
        pct_d = odds_change.get("draw", 0)
        pct_a = odds_change.get("away", 0)
        chg_str = f"H{pct_h:+.1f}% D{pct_d:+.1f}% A{pct_a:+.1f}%"
        
        f.write(f"{r['id']:<8} {r['match']:<22} {r['odds']:<14} {r['confidence']:.1f}%  {r['macao']:<14} {r['prediction']:<4} {chg_str:<22} {home_trend:<6} {away_trend:<6} {form_diff:+4.0f}   {r['form_analysis']}\n")
    
    f.write("\n" + "="*150 + "\n")
    f.write("[单选列表] 澳门分胜负 + 置信度>=66%\n")
    f.write("="*150 + "\n")
    f.write(f"{'编号':<8} {'对阵':<22} {'竞彩即时':<14} {'置信度':<6} {'澳门':<14} {'预测':<4} {'赔率变化':<22} {'主队分':<5} {'客队分':<5} {'近况差':<5} {'近况验证'}\n")
    f.write("-"*150 + "\n")
    
    for r in single_picks:
        home_form = r["home_form"] if r["home_form"] else "-"
        away_form = r["away_form"] if r["away_form"] else "-"
        form_diff = r["form_diff"] if r["form_diff"] else 0
        verify = r["form_analysis"]
        
        # 赔率变化
        odds_change = r["odds_change"]
        pct_h = odds_change.get("home", 0)
        pct_d = odds_change.get("draw", 0)
        pct_a = odds_change.get("away", 0)
        chg_str = f"H{pct_h:+.1f}% D{pct_d:+.1f}% A{pct_a:+.1f}%"
        
        f.write(f"{r['id']:<8} {r['match']:<22} {r['odds']:<14} {r['confidence']:.1f}%  {r['macao']:<14} {r['prediction']:<4} {chg_str:<22} {str(home_form):<5} {str(away_form):<5} {form_diff:+4.0f}   {verify}\n")
    
    f.write(f"\n共 {len(single_picks)} 场可单选\n")

# ====== 过热分析 ======
print("\n" + "="*150)
print("【过热提醒 + 近况分析】")
print("="*150)

overheated = []
for r in results:
    pred = r["prediction"]
    macao = r["macao"] or ""
    odds_change = r["odds_change"]
    pct_h = odds_change.get("home", 0)
    pct_d = odds_change.get("draw", 0)
    pct_a = odds_change.get("away", 0)
    conf = r["confidence"]
    macao_dir = r["macao_dir"]
    form_diff = r["form_diff"]
    form_analysis = r["form_analysis"]
    
    warn_type = ""
    reason = ""
    
    # 大幅变化阈值
    big_threshold = 5.0
    
    # 过热检测
    if pred == "主胜" and macao_dir == "主胜":
        if abs(pct_h) > big_threshold:
            warn_type = "过热" if pct_h < 0 else "反向"
            reason = f"主胜{'降' if pct_h < 0 else '升'}{abs(pct_h):.1f}%"
        elif abs(pct_d) > big_threshold:
            warn_type = "警惕"
            reason = f"平局{'升' if pct_d > 0 else '降'}{abs(pct_d):.1f}%"
        elif abs(pct_a) > big_threshold:
            warn_type = "警惕"
            reason = f"客胜{'升' if pct_a > 0 else '降'}{abs(pct_a):.1f}%"
    elif pred == "客胜" and macao_dir == "客胜":
        if abs(pct_a) > big_threshold:
            warn_type = "过热" if pct_a < 0 else "反向"
            reason = f"客胜{'降' if pct_a < 0 else '升'}{abs(pct_a):.1f}%"
        elif abs(pct_d) > big_threshold:
            warn_type = "警惕"
            reason = f"平局{'升' if pct_d > 0 else '降'}{abs(pct_d):.1f}%"
        elif abs(pct_h) > big_threshold:
            warn_type = "警惕"
            reason = f"主胜{'升' if pct_h > 0 else '降'}{abs(pct_h):.1f}%"
    elif pred == "平局" and macao_dir == "和局":
        if abs(pct_d) > big_threshold:
            warn_type = "过热" if pct_d < 0 else "反向"
            reason = f"平局{'降' if pct_d < 0 else '升'}{abs(pct_d):.1f}%"
        elif abs(pct_h) > big_threshold:
            warn_type = "警惕"
            reason = f"主胜{'升' if pct_h > 0 else '降'}{abs(pct_h):.1f}%"
        elif abs(pct_a) > big_threshold:
            warn_type = "警惕"
            reason = f"客胜{'升' if pct_a > 0 else '降'}{abs(pct_a):.1f}%"
    
    # 主胜升幅>5% → 平局概率大
    if pct_h > 5:
        warn_type = "主胜升"
        reason = f"主胜升幅{pct_h:.1f}% → 防平"
    
    # 近况与赔率矛盾检测
    if form_diff >= 6 and pct_h > 2:
        warn_type = "近况矛盾"
        reason = f"主队近况更好(+{form_diff})但主胜升"
    elif form_diff <= -6 and pct_a > 2:
        warn_type = "近况矛盾"
        reason = f"客队近况更好({form_diff})但客胜升"
    
    if warn_type:
        r["overheat_type"] = warn_type
        r["overheat_reason"] = reason
        overheated.append(r)

if overheated:
    print(f"\n| 编号 | 对阵 | 竞彩即时 | 赔率变化 | 置信度 | 澳门 | 预测 | 近况差 | 类型 | 原因 |")
    print(f"|------|------|----------|---------|--------|------|------|--------|------|---------|")
    for r in overheated:
        odds = r["odds"]
        chg = r["odds_change"]
        chg_str = f"H{chg.get('home',0):+.1f}% D{chg.get('draw',0):+.1f}% A{chg.get('away',0):+.1f}%"
        print(f"| {r['id']} | {r['match']} | {odds} | {chg_str} | {r['confidence']:.1f}% | {r['macao']} | {r['prediction']} | {r['form_diff']:+4} | {r['overheat_type']} | {r['overheat_reason']} |")
else:
    print("\n无过热比赛")

# 保存完整结果
output_file = "d:/work/workbuddy/足球预测/3.21_result.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("3.21比赛 - 完整预测列表（含近况评分+过热分析）\n")
    f.write("="*150 + "\n\n")
    f.write("评分规则：最近一场权重2，其他权重1 | 赢=3分，平=1分，输=0分\n")
    f.write("近况差：正值表示主队近况更好，负值表示客队近况更好\n\n")
    
    f.write("[详细分析列表]\n")
    f.write("-"*150 + "\n")
    f.write(f"{'编号':<8} {'对阵':<24} {'竞彩即时':<14} {'置信度':<6} {'澳门':<14} {'预测':<4} {'赔率变化':<22} {'主队走势':<6} {'客队走势':<6} {'近况差':<5} {'近况分析'}\n")
    f.write("-"*150 + "\n")
    
    for r in results:
        home_trend = r["home_trend"][:5] if r["home_trend"] else "-"
        away_trend = r["away_trend"][:5] if r["away_trend"] else "-"
        form_diff = r["form_diff"] if r["form_diff"] else 0
        
        # 赔率变化
        odds_change = r["odds_change"]
        pct_h = odds_change.get("home", 0)
        pct_d = odds_change.get("draw", 0)
        pct_a = odds_change.get("away", 0)
        chg_str = f"H{pct_h:+.1f}% D{pct_d:+.1f}% A{pct_a:+.1f}%"
        
        f.write(f"{r['id']:<8} {r['match']:<24} {r['odds']:<14} {r['confidence']:.1f}%  {r['macao']:<14} {r['prediction']:<4} {chg_str:<22} {home_trend:<6} {away_trend:<6} {form_diff:+4.0f}   {r['form_analysis']}\n")
    
    f.write("\n" + "="*150 + "\n")
    f.write("[单选列表] 澳门分胜负 + 置信度>=66%\n")
    f.write("="*150 + "\n")
    
    for r in single_picks:
        home_form = r["home_form"] if r["home_form"] else "-"
        away_form = r["away_form"] if r["away_form"] else "-"
        form_diff = r["form_diff"] if r["form_diff"] else 0
        verify = r["form_analysis"]
        
        f.write(f"{r['id']:<8} {r['match']:<24} {r['odds']:<14} {r['confidence']:.1f}%  {r['macao']:<14} {r['prediction']:<4} {str(home_form):<5} {str(away_form):<5} {form_diff:+4.0f}   {verify}\n")
    
    f.write(f"\n共 {len(single_picks)} 场可单选\n")
    
    # 过热列表
    f.write("\n" + "="*150 + "\n")
    f.write("[过热提醒列表]\n")
    f.write("="*150 + "\n")
    if overheated:
        f.write(f"| 编号 | 对阵 | 竞彩即时 | 赔率变化 | 置信度 | 澳门 | 预测 | 近况差 | 类型 | 原因 |\n")
        f.write(f"|------|------|----------|---------|--------|------|------|--------|------|---------||\n")
        for r in overheated:
            odds = r["odds"]
            chg = r["odds_change"]
            chg_str = f"H{chg.get('home',0):+.1f}% D{chg.get('draw',0):+.1f}% A{chg.get('away',0):+.1f}%"
            f.write(f"| {r['id']} | {r['match']} | {odds} | {chg_str} | {r['confidence']:.1f}% | {r['macao']} | {r['prediction']} | {r['form_diff']:+4} | {r['overheat_type']} | {r['overheat_reason']} |\n")
    else:
        f.write("无过热比赛\n")
    
    # ====== 近况差>=4的比赛分析 ======
    
    # 分类
    form_high_risk = []  # 高压区：澳门推荐+近况好+赔率不变
    form_contradict = []  # 矛盾：近况与赔率矛盾
    form_support_ok = []  # 正常：近况支持+赔率降水
    form_macao_draw = []  # 澳门推荐和局
    form_other = []       # 其他近况差>=4的比赛
    
    for r in results:
        form_diff = r["form_diff"] if r["form_diff"] else 0
        if abs(form_diff) < 4:
            continue
        
        macao = r["macao"] or ""
        macao_dir = r["macao_dir"]
        pct_h = r["odds_change"].get("home", 0)
        pct_a = r["odds_change"].get("away", 0)
        pred = r["prediction"]
        conf = r["confidence"]
        
        # 澳门推荐和局
        if macao_dir == "和局":
            form_macao_draw.append(r)
            continue
        
        # 判断澳门推荐方向与近况是否一致
        is_macao_home = macao_dir == "主胜"
        is_macao_away = macao_dir == "客胜"
        
        # 近况支持澳门
        form_support_macao = (is_macao_home and form_diff > 0) or (is_macao_away and form_diff < 0)
        
        # 矛盾检测：近况好但赔率不利
        is_contradict = False
        if is_macao_home and form_diff >= 4 and pct_h > 2:
            is_contradict = True
        elif is_macao_away and form_diff <= -4 and pct_a > 2:
            is_contradict = True
        
        # 高压区：澳门推荐+近况支持+赔率不变
        is_high_pressure = form_support_macao and pct_h == 0 and pct_a == 0
        
        if is_contradict:
            form_contradict.append(r)
        elif is_high_pressure:
            form_high_risk.append(r)
        elif form_support_macao and ((is_macao_home and pct_h < 0) or (is_macao_away and pct_a < 0)):
            form_support_ok.append(r)
        else:
            form_other.append(r)
    
    # 写入文件
    f.write("\n" + "="*150 + "\n")
    f.write("[近况差>=4的比赛分析]\n")
    f.write("="*150 + "\n\n")
    
    # 类型一
    f.write("【类型一】高压区：澳门推荐+近况好+赔率不变 -> 防冷\n")
    f.write("-"*150 + "\n")
    if form_high_risk:
        f.write("| 编号 | 对阵 | 竞彩即时 | 置信度 | 澳门 | 预测 | 赔率变化 | 近况差 | 分析 |\n")
        f.write("|------|------|----------|--------|------|------|----------|--------|------|\n")
        for r in form_high_risk:
            chg = r["odds_change"]
            chg_str = "H{}% D{}% A{}%".format(
                int(chg.get('home',0)), 
                int(chg.get('draw',0)), 
                int(chg.get('away',0))
            )
            if abs(r["form_diff"]) >= 10:
                danger = "极危"
            elif abs(r["form_diff"]) >= 7:
                danger = "高危"
            else:
                danger = "中危"
            f.write("| {} | {} | {} | {}% | {} | {} | {} | {:+d} | {} |\n".format(
                r['id'], r['match'], r['odds'], r['confidence'], 
                r['macao'], r['prediction'], chg_str, r['form_diff'], danger
            ))
    else:
        f.write("无\n")
    
    # 类型二
    f.write("\n【类型二】矛盾：近况与赔率变动矛盾 -> 防反向\n")
    f.write("-"*150 + "\n")
    if form_contradict:
        f.write("| 编号 | 对阵 | 竞彩即时 | 置信度 | 澳门 | 预测 | 赔率变化 | 近况差 | 分析 |\n")
        f.write("|------|------|----------|--------|------|------|----------|--------|------|\n")
        for r in form_contradict:
            chg = r["odds_change"]
            chg_str = "H{:.0f}% D{:.0f}% A{:.0f}%".format(
                chg.get('home',0), chg.get('draw',0), chg.get('away',0)
            )
            f.write("| {} | {} | {} | {}% | {} | {} | {} | {:+d} | 近况矛盾 |\n".format(
                r['id'], r['match'], r['odds'], r['confidence'],
                r['macao'], r['prediction'], chg_str, r['form_diff']
            ))
    else:
        f.write("无\n")
    
    # 类型三
    f.write("\n【类型三】正常：近况支持+赔率降水\n")
    f.write("-"*150 + "\n")
    if form_support_ok:
        f.write("| 编号 | 对阵 | 竞彩即时 | 置信度 | 澳门 | 预测 | 赔率变化 | 近况差 |\n")
        f.write("|------|------|----------|--------|------|------|----------|--------|\n")
        for r in form_support_ok:
            chg = r["odds_change"]
            chg_str = "H{:.0f}% D{:.0f}% A{:.0f}%".format(
                chg.get('home',0), chg.get('draw',0), chg.get('away',0)
            )
            f.write("| {} | {} | {} | {}% | {} | {} | {} | {:+d} |\n".format(
                r['id'], r['match'], r['odds'], r['confidence'],
                r['macao'], r['prediction'], chg_str, r['form_diff']
            ))
    else:
        f.write("无\n")
    
    # 类型四
    f.write("\n【类型四】澳门推荐和局 + 近况差>=4\n")
    f.write("-"*150 + "\n")
    if form_macao_draw:
        f.write("| 编号 | 对阵 | 竞彩即时 | 置信度 | 澳门 | 预测 | 赔率变化 | 近况差 |\n")
        f.write("|------|------|----------|--------|------|------|----------|--------|\n")
        for r in form_macao_draw:
            chg = r["odds_change"]
            chg_str = "H{}% D{}% A{}%".format(
                int(chg.get('home',0)), 
                int(chg.get('draw',0)), 
                int(chg.get('away',0))
            )
            f.write("| {} | {} | {} | {}% | {} | {} | {} | {:+d} |\n".format(
                r['id'], r['match'], r['odds'], r['confidence'],
                r['macao'], r['prediction'], chg_str, r['form_diff']
            ))
    else:
        f.write("无\n")
    
    # 类型五
    f.write("\n【类型五】其他：澳门推荐与近况不一致\n")
    f.write("-"*150 + "\n")
    if form_other:
        f.write("| 编号 | 对阵 | 竞彩即时 | 置信度 | 澳门 | 预测 | 赔率变化 | 近况差 |\n")
        f.write("|------|------|----------|--------|------|------|----------|--------|\n")
        for r in form_other:
            chg = r["odds_change"]
            chg_str = "H{:.0f}% D{:.0f}% A{:.0f}%".format(
                chg.get('home',0), chg.get('draw',0), chg.get('away',0)
            )
            f.write("| {} | {} | {} | {}% | {} | {} | {} | {:+d} |\n".format(
                r['id'], r['match'], r['odds'], r['confidence'],
                r['macao'], r['prediction'], chg_str, r['form_diff']
            ))
    else:
        f.write("无\n")

print(f"\n结果已保存到: {output_file}")
