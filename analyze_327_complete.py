"""
3.27 比赛 - 完整预测列表（从源数据自动提取"竞*官*"的初盘+即时赔率）
包含近况差计算复核和规律二次审核
"""

import os
import re
import glob

DATA_DIR = "d:/work/workbuddy/足球预测/分析模板/3.27"

def extract_jingcai_odds(match_id):
    """从源数据文件提取"竞*官*"的初盘和即时赔率（第五部分表格）
    返回: (初盘主, 初盘平, 初盘客, 即时主, 即时平, 即时客)
    注意：周五011没有竞*官*行，使用威**尔作为替代
    """
    file_path = f"{DATA_DIR}/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return None, None, None, None, None, None
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找第五部分"赔率变动对比"表格中的"竞*官*"行
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
                    # 实际parts: ['', '竞*官*', '初盘胜', '即时胜', '变动', '初盘平', '即时平', '变动', '初盘负', '即时负', '变动', '']
                    # 索引:        0     1          2         3        4      5         6        7      8         9        10      11
                    if len(parts) >= 10:
                        init_home = parts[2]  # 初盘胜
                        real_home = parts[3]  # 即时胜
                        init_draw = parts[5]  # 初盘平
                        real_draw = parts[6]  # 即时平
                        init_away = parts[8]  # 初盘负
                        real_away = parts[9]  # 即时负
                        try:
                            return (float(init_home), float(init_draw), float(init_away),
                                    float(real_home), float(real_draw), float(real_away))
                        except:
                            pass
                # 周五011没有竞*官*，使用威**尔作为替代
                elif '威**尔' in line and '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 10:
                        init_home = parts[2]
                        real_home = parts[3]
                        init_draw = parts[5]
                        real_draw = parts[6]
                        init_away = parts[8]
                        real_away = parts[9]
                        try:
                            return (float(init_home), float(init_draw), float(init_away),
                                    float(real_home), float(real_draw), float(real_away))
                        except:
                            pass
        
        return None, None, None, None, None, None
        
    except Exception as e:
        print(f"读取{match_id}竞彩赔率出错: {e}")
        return None, None, None, None, None, None


def fmt_change(init_val, real_val):
    """格式化赔率变化幅度，如 +3.5% 或 -8.2%"""
    if init_val is None or real_val is None or init_val == 0:
        return "—"
    pct = (real_val - init_val) / init_val * 100
    if abs(pct) < 0.1:
        return "—"
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"

def extract_macao_tip(match_id):
    """从源数据文件提取澳门推荐"""
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
    """从源数据文件提取比赛名称"""
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

def extract_form(match_id):
    """从源数据文件提取近况走势"""
    file_path = f"{DATA_DIR}/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return "", ""
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        home_form_match = re.search(r'主队近况走势\s*\|\s*([^\n|]+)', content)
        away_form_match = re.search(r'客队近况走势\s*\|\s*([^\n|]+)', content)
        
        home_form = home_form_match.group(1).strip() if home_form_match else ""
        away_form = away_form_match.group(1).strip() if away_form_match else ""
        
        return home_form, away_form
        
    except Exception as e:
        return "", ""

# 比赛ID列表（3.27周五+周六）
match_ids = [
    "周五001", "周五002", "周五003", "周五004", "周五005",
    "周五006", "周五007", "周五008", "周五009", "周五010",
    "周五011", "周五012", "周六001", "周六002", "周六012", "周六014"
]

# 自动提取所有比赛的竞彩赔率
matches_data = {}
for mid in match_ids:
    init_home, init_draw, init_away, real_home, real_draw, real_away = extract_jingcai_odds(mid)
    match_name = extract_match_name(mid)
    macao = extract_macao_tip(mid)
    home_form, away_form = extract_form(mid)
    
    if real_home is not None and real_draw is not None and real_away is not None:
        matches_data[mid] = {
            "match": match_name,
            "init_home": init_home, "init_draw": init_draw, "init_away": init_away,
            "home": real_home, "draw": real_draw, "away": real_away,
            "macao": macao,
            "home_form": home_form,
            "away_form": away_form
        }
        print(f"{mid}: 初盘{init_home}/{init_draw}/{init_away} → 即时{real_home}/{real_draw}/{real_away} | 澳门: {macao}")
    else:
        print(f"{mid}: 未找到竞彩数据!")

def calculate_form_score(form_str):
    """
    计算近况得分
    权重：最近一场×2，其他4场×1（共6场权重）
    得分：W=3, D=1, L=0
    满分：3×2 + 3×4 = 18分
    """
    if not form_str:
        return 0
    
    # 取最近6场比赛（左边第一个是最新最近）
    recent_games = form_str[:6] if len(form_str) >= 6 else form_str
    
    score = 0
    for i, result in enumerate(recent_games):
        # 最近一场（索引0）权重×2，其他权重×1
        weight = 2 if i == 0 else 1
        if result == 'W':
            score += 3 * weight
        elif result == 'D':
            score += 1 * weight
        # L = 0分
    
    return score

def calculate_form_difference(home_form, away_form):
    """
    计算近况差 = 主队得分 - 客队得分
    返回：主队分, 客队分, 近况差
    """
    home_score = calculate_form_score(home_form)
    away_score = calculate_form_score(away_form)
    difference = home_score - away_score
    return home_score, away_score, difference

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
        deviation_type = "偏离过低"
    else:
        deviation_type = "正常"
    
    # 澳门推荐
    macao = data.get('macao', '-')
    
    # 计算赔率变化百分比
    init_h_val = data.get('init_home') or 0
    init_d_val = data.get('init_draw') or 0
    init_a_val = data.get('init_away') or 0
    pct_h = (home - init_h_val) / init_h_val * 100 if init_h_val else 0
    pct_d = (draw - init_d_val) / init_d_val * 100 if init_d_val else 0
    pct_a = (away - init_a_val) / init_a_val * 100 if init_a_val else 0

    # 规律一标注：澳门推分胜负 + 置信度是否≥66%
    macao_str = macao or ''
    macao_is_draw = '和局' in macao_str
    rule1_tag = ""
    if not macao_is_draw:
        if confidence >= 66:
            rule1_tag = "[规律一:可信>=66%]"
        elif confidence >= 55:
            rule1_tag = "[规律一:慎55~65%]"
        else:
            rule1_tag = "[规律一:高危<55%]"
    
    # 计算近况差
    home_form = data.get('home_form', '')
    away_form = data.get('away_form', '')
    home_score, away_score, form_diff = calculate_form_difference(home_form, away_form)
    
    results.append({
        'id': mid,
        'match': data['match'],
        'init_home': data.get('init_home'), 'init_draw': data.get('init_draw'), 'init_away': data.get('init_away'),
        'home': home,
        'draw': draw,
        'away': away,
        'confidence': confidence,
        'home_rate': home_rate,
        'draw_rate': draw_rate,
        'away_rate': away_rate,
        'rate_diff': rate_diff,
        'deviation': deviation,
        'deviation_type': deviation_type,
        'prediction': odds_pred,
        'macao': macao,
        'pct_change': [pct_h, pct_d, pct_a],
        'rule1_tag': rule1_tag,
        'home_form_score': home_score,
        'away_form_score': away_score,
        'form_diff': form_diff,
    })

results.sort(key=lambda x: x['id'])

# 应用规律进行二次审核
def apply_rules(r):
    """应用memory中记录的规律进行二次审核（含3.28复盘新增规律N/O/P/Q）"""
    confidence = r['confidence']
    pct_h, pct_d, pct_a = r['pct_change']
    macao = r.get('macao', '')
    init_h = r.get('init_home') or 0
    init_d = r.get('init_draw') or 0
    init_a = r.get('init_away') or 0
    form_diff = r.get('form_diff', 0)
    
    tags = []
    stability = 0  # 稳定性评分，越高越稳
    upset_risk = 0  # 爆冷风险评分
    
    # 规律五（最高优先级）：主胜升幅>5% → 直接预测和局
    if pct_h > 5:
        tags.append("[规律五:主升>5%→和局]")
        # 规律N：规律五+造热客队 → 反向主胜
        if pct_a < -10:  # 客队极端造热(>10%)
            if '贏' in macao and macao.replace('贏','').strip() != '':  # 澳门推客队
                tags.append("[规律N:规律五+极端造热客+澳门推客→反向主胜]")
                upset_risk += 3
            else:
                tags.append("[规律N:规律五+极端造热客→反向主胜]")
                upset_risk += 2
        elif pct_a < -8:  # 客队中等造热(8-10%)
            if '贏' in macao and macao.replace('贏','').strip() != '':
                tags.append("[规律N:规律五+中等造热客+澳门推客→主胜概率高]")
                upset_risk += 2
        stability -= 2
        upset_risk += 2
    
    # 规律O：近况差+8以上+赔率微变(<2%) → 主队打出
    if form_diff >= 8 and abs(pct_h) < 2 and abs(pct_d) < 2 and abs(pct_a) < 2:
        tags.append("[规律O:近况差+8+赔率微变<2%→主队打出]")
        stability += 2
    
    # 规律P：平赔3.0-3.2+澳门推平局+变化<2% → 诱平反向
    if macao_is_draw and 3.0 <= init_d <= 3.2 and abs(pct_d) < 2:
        tags.append("[规律P:平赔3.0-3.2+澳门推平+变化<2%→诱平反向]")
        stability -= 1
        upset_risk += 2
    
    # 规律Q：近况差极大(+10)+置信度<65%+赔率全变>2% → 防过热平局
    if form_diff >= 10 and confidence < 65 and abs(pct_h) > 2 and abs(pct_d) > 2 and abs(pct_a) > 2:
        tags.append("[规律Q:近况差+10+置信度<65%+全变>2%→防过热平局]")
        stability -= 2
        upset_risk += 2
    
    # 规律I：极端造热（主降>10%+客升>10%）+近况差≤-10+平赔不变(3.3+) → 平局
    if pct_h < -10 and pct_a > 10 and form_diff <= -10 and init_d >= 3.3 and abs(pct_d) < 1:
        tags.append("[规律I:极端造热+近况差≤-10+平赔不变→平局]")
        stability -= 1
        upset_risk += 2
    
    # 规律J：澳门推平+平赔<3.0+主升+客降水进入低区 → 客胜
    if macao_is_draw and init_d < 3.0 and pct_h > 0 and pct_a < 0:
        tags.append("[规律J:澳门推平+平赔<3.0+主升+客降→客胜]")
        stability -= 1
        upset_risk += 2
    
    # 规律K：客队强造热(>8%)+近况持平(±2)+平降>3% → 主队不败
    if pct_a < -8 and abs(form_diff) <= 2 and pct_d < -3:
        tags.append("[规律K:客造热>8%+近况持平+平降>3%→主队不败]")
        stability += 1
        upset_risk += 1
    
    # 规律L：极端造热客队+近况差≤-10+平赔不降反升 → 主胜
    if pct_a < -10 and form_diff <= -10 and pct_d > 0:
        tags.append("[规律L:极端造热客+近况差≤-10+平赔反升→主胜]")
        stability -= 1
        upset_risk += 3
    
    # 规律一：置信度≥66% + 澳门同向 → 可信
    if confidence >= 66:
        tags.append("[规律一:高置信度≥66%]")
        stability += 3
        # 规律G：高置信度时，赔率变化幅度+近况差共同决定
        if abs(pct_h) < 2 and abs(pct_d) < 2 and abs(pct_a) < 2:
            if abs(form_diff) >= 5:
                tags.append("[规律G:变化小+近况差大→大胜可能]")
    
    # 规律二：平局难出条件
    if macao_is_draw:
        if init_d > 0 and init_d < 3.0:
            tags.append("[规律二:平初<3.0→平局难出]")
            stability -= 1
            upset_risk += 1
        elif pct_d < -5.0:
            tags.append("[规律二:平降>5%→平局难出]")
            stability -= 1
            upset_risk += 1
    
    # 规律四/A：1-3-3格式+澳门推和局+平赔上升 → 平难出，客队概率大
    # 1-3-3格式：主胜≈1，平局≈3，客胜≈3
    if macao_is_draw and 2.8 <= init_d <= 3.5 and pct_d > 0:
        tags.append("[规律四/A:1-3-3+澳门推平+平赔升→客胜概率大]")
        stability -= 1
        upset_risk += 2
    
    # 规律七/E：2-3-2格局+置信度44%+平赔<3.0+无变化 → 客队打出
    if 42 <= confidence <= 46 and 2.0 <= init_h <= 2.5 and 2.8 <= init_d <= 3.2 and 2.0 <= init_a <= 2.5:
        if init_d < 3.0 and abs(pct_h) < 1 and abs(pct_d) < 1 and abs(pct_a) < 1:
            tags.append("[规律七/E:2-3-2+置信度44%+平赔<3.0+无变化→客胜]")
            stability -= 1
            upset_risk += 2
    
    # 规律B：2-3-2格局+客队过热+主胜升>5% → 和局
    if 2.0 <= init_h <= 2.5 and 2.8 <= init_d <= 3.2 and 2.0 <= init_a <= 2.5:
        if pct_a < -5 and pct_h > 5:
            tags.append("[规律B:2-3-2+客过热+主升>5%→和局]")
            stability -= 1
            upset_risk += 2
    
    # 规律C：低置信度≤41%+澳门推主胜+赔率应降不降 → 平局概率大
    if confidence <= 41 and not macao_is_draw and '贏' in macao:
        # 澳门推主队但主胜赔率未降或反升
        if pct_h >= 0:
            tags.append("[规律C:低置信度+澳门推主+赔率不降→平局]")
            stability -= 1
            upset_risk += 2
    
    # 规律F：置信度41-55%+澳门推和局+平赔3.5-3.7小降(-1%~-2%) → 平局可出
    if 41 <= confidence <= 55 and macao_is_draw and 3.5 <= init_d <= 3.7 and -2 <= pct_d <= -1:
        tags.append("[规律F:41-55%+澳门推平+平赔3.5-3.7小降→平局可出]")
        stability += 1
    
    # 规律三：置信度≤40%
    if confidence <= 40:
        tags.append("[规律三:低置信度≤40%]")
        stability -= 2
        upset_risk += 2
    
    # 规律六：置信度64-65%场次防平
    if 64 <= confidence <= 65:
        if pct_h < 0 and (pct_d > 0 or pct_a > 0):
            tags.append("[规律六:64-65%+造热嫌疑→防平]")
            stability -= 1
            upset_risk += 1
    
    # 规律H：置信度≥66% + 赔率变化均<5% + 澳门推非主方向 → 直接按置信度方向打出
    if confidence >= 66 and abs(pct_h) < 5 and abs(pct_d) < 5 and abs(pct_a) < 5:
        tags.append("[规律H:高置信度+赔率稳定→稳胆]")
        stability += 2
    
    # 过热检测
    max_change = max(abs(pct_h), abs(pct_d), abs(pct_a))
    if max_change > 8:
        tags.append(f"[过热:最大变化{max_change:.1f}%]")
        stability -= 2
        upset_risk += 2
    
    return tags, stability, upset_risk

# 为所有比赛应用规律
for r in results:
    tags, stability, upset_risk = apply_rules(r)
    r['rule_tags'] = tags
    r['stability'] = stability
    r['upset_risk'] = upset_risk

# 输出完整数据列表（标准格式）
print("\n" + "=" * 180)
print("3.27 比赛 - 完整数据列表（标准格式）")
print("=" * 180)
print("\n| 编号 | 对阵 | 置信度 | 澳门心水 | 近况差 | 初盘(胜/平/负) | 即时(胜/平/负) | 变化(H/D/A) | 最终预测 | 规律标签 |")
print("|------|------|--------|----------|--------|----------------|----------------|-------------|----------|----------|")

for r in results:
    init_str = f"{r['init_home']:.2f}/{r['init_draw']:.2f}/{r['init_away']:.2f}" if r['init_home'] else "—"
    real_str = f"{r['home']:.2f}/{r['draw']:.2f}/{r['away']:.2f}"
    chg_h = fmt_change(r['init_home'], r['home'])
    chg_d = fmt_change(r['init_draw'], r['draw'])
    chg_a = fmt_change(r['init_away'], r['away'])
    chg_str = f"主{chg_h} 平{chg_d} 客{chg_a}"
    form_diff_str = f"{r['form_diff']:+d}"
    rule_tags_str = " ".join(r['rule_tags']) if r['rule_tags'] else "—"
    
    print(f"| {r['id']} | {r['match']} | {r['confidence']:.1f}% | {r['macao']} | {form_diff_str} | {init_str} | {real_str} | {chg_str} | {r['prediction']} | {rule_tags_str} |")

# 近况差计算复核
print("\n" + "=" * 180)
print("【近况差计算复核】")
print("=" * 180)
print("计算规则：最近一场×2权重，其他4场×1权重 | W=3分, D=1分, L=0分 | 满分18分")
print("\n| 编号 | 对阵 | 主队近况 | 主队分 | 客队近况 | 客队分 | 近况差 | 计算过程 |")
print("|------|------|----------|--------|----------|--------|--------|----------|")

for r in results:
    home_form = matches_data[r['id']]['home_form']
    away_form = matches_data[r['id']]['away_form']
    
    # 显示计算过程
    home_calc = []
    for i, result in enumerate(home_form[:6]):
        weight = 2 if i == 0 else 1
        score = 3 if result == 'W' else (1 if result == 'D' else 0)
        home_calc.append(f"{result}×{weight}={score*weight}")
    
    away_calc = []
    for i, result in enumerate(away_form[:6]):
        weight = 2 if i == 0 else 1
        score = 3 if result == 'W' else (1 if result == 'D' else 0)
        away_calc.append(f"{result}×{weight}={score*weight}")
    
    calc_str = f"主:{ '+'.join(home_calc) }={r['home_form_score']}, 客:{ '+'.join(away_calc) }={r['away_form_score']}"
    
    print(f"| {r['id']} | {r['match']} | {home_form[:6]} | {r['home_form_score']} | {away_form[:6]} | {r['away_form_score']} | {r['form_diff']:+d} | {calc_str} |")

# 稳胆和爆冷列表
print("\n" + "=" * 180)
print("【规律二次审核结果】")
print("=" * 180)

# 按稳定性排序
stable_matches = sorted([r for r in results if r['stability'] >= 2], key=lambda x: x['stability'], reverse=True)
upset_matches = sorted([r for r in results if r['upset_risk'] >= 2], key=lambda x: x['upset_risk'], reverse=True)

print("\n### [稳胆] 最稳的比赛推荐\n")
if stable_matches:
    print("| 编号 | 对阵 | 置信度 | 澳门心水 | 近况差 | 稳定性评分 | 规律标签 |")
    print("|------|------|--------|----------|--------|------------|----------|")
    for r in stable_matches[:5]:
        rule_tags_str = " ".join(r['rule_tags']) if r['rule_tags'] else "—"
        print(f"| {r['id']} | {r['match']} | {r['confidence']:.1f}% | {r['macao']} | {r['form_diff']:+d} | {r['stability']} | {rule_tags_str} |")
else:
    print("暂无高稳定性比赛")

print("\n### [爆冷] 最可能爆冷的比赛\n")
if upset_matches:
    print("| 编号 | 对阵 | 置信度 | 澳门心水 | 近况差 | 爆冷风险评分 | 规律标签 |")
    print("|------|------|--------|----------|--------|--------------|----------|")
    for r in upset_matches[:5]:
        rule_tags_str = " ".join(r['rule_tags']) if r['rule_tags'] else "—"
        print(f"| {r['id']} | {r['match']} | {r['confidence']:.1f}% | {r['macao']} | {r['form_diff']:+d} | {r['upset_risk']} | {rule_tags_str} |")
else:
    print("暂无高爆冷风险比赛")

# 统计
print("\n" + "=" * 180)
print("统计")
print("=" * 180)

high_conf = [r for r in results if r['confidence'] >= 66]
mid_conf = [r for r in results if 55 <= r['confidence'] < 66]
low_conf = [r for r in results if r['confidence'] < 55]

print(f"\n| 置信度范围 | 场数 | 主胜 | 客胜 | 平局 |")
print(f"|------------|------|------|------|------|")
print(f"| ≥66% (高) | {len(high_conf)} | {sum(1 for r in high_conf if r['prediction']=='主胜')} | {sum(1 for r in high_conf if r['prediction']=='客胜')} | {sum(1 for r in high_conf if r['prediction']=='平局')} |")
print(f"| 55-65% (中) | {len(mid_conf)} | {sum(1 for r in mid_conf if r['prediction']=='主胜')} | {sum(1 for r in mid_conf if r['prediction']=='客胜')} | {sum(1 for r in mid_conf if r['prediction']=='平局')} |")
print(f"| <55% (低) | {len(low_conf)} | {sum(1 for r in low_conf if r['prediction']=='主胜')} | {sum(1 for r in low_conf if r['prediction']=='客胜')} | {sum(1 for r in low_conf if r['prediction']=='平局')} |")
print(f"| 总计 | {len(results)} | {sum(1 for r in results if r['prediction']=='主胜')} | {sum(1 for r in results if r['prediction']=='客胜')} | {sum(1 for r in results if r['prediction']=='平局')} |")
