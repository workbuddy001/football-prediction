"""
3.19 周四比赛分析脚本
"""

import os
import re
import glob

DATA_DIR = "d:/work/workbuddy/足球预测/分析模板/3.19"

def extract_jingcai_odds(match_id):
    """从源数据文件提取竞彩初盘和即时赔率"""
    file_path = f"{DATA_DIR}/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return None
    
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
                            init_home = float(parts[2])
                            real_home = float(parts[3])
                            init_draw = float(parts[5])
                            real_draw = float(parts[6])
                            init_away = float(parts[8])
                            real_away = float(parts[9])
                            return (init_home, init_draw, init_away, real_home, real_draw, real_away)
                        except:
                            pass
        return None
    except:
        return None

def calc_form_score(trend):
    """计算近况评分"""
    if not trend:
        return 0
    score_map = {'W':3,'D':1,'L':0,'胜':3,'平':1,'负':0}
    recent = trend[:5] if len(trend)>=5 else trend
    total = 0
    for i, ch in enumerate(recent):
        if ch in score_map:
            w = 2 if i==0 else 1
            total += score_map[ch]*w
    return total

def extract_match_info(match_id):
    """提取比赛信息"""
    file_path = f"{DATA_DIR}/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return None
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取比赛名称
        name_match = re.search(r'主队\s*\|\s*([^\n|]+)', content)
        home = name_match.group(1).strip() if name_match else ''
        away_match = re.search(r'客队\s*\|\s*([^\n|]+)', content)
        away = away_match.group(1).strip() if away_match else ''
        
        # 澳门推荐
        macao_match = re.search(r'澳门推荐\s*\|\s*([^\n|]+)', content)
        macao = macao_match.group(1).strip() if macao_match else ''
        
        # 近况
        ht_match = re.search(r'主队近况走势\s*\|\s*([^\n|]+)', content)
        at_match = re.search(r'客队近况走势\s*\|\s*([^\n|]+)', content)
        ht_trend = ht_match.group(1).strip() if ht_match else ''
        at_trend = at_match.group(1).strip() if at_match else ''
        
        ht_score = calc_form_score(ht_trend)
        at_score = calc_form_score(at_trend)
        
        return {
            'home': home,
            'away': away,
            'macao': macao,
            'ht_trend': ht_trend,
            'at_trend': at_trend,
            'ht_score': ht_score,
            'at_score': at_score,
            'form_diff': ht_score - at_score
        }
    except:
        return None

def calc_confidence(odds):
    """计算置信度"""
    if not odds:
        return None
    h, d, a = odds[3], odds[4], odds[5]
    total = 1/h + 1/d + 1/a
    h_prob = (1/h) / total * 100
    d_prob = (1/d) / total * 100
    a_prob = (1/a) / total * 100
    return max(h_prob, d_prob, a_prob), h_prob, d_prob, a_prob

def calc_change_pct(init, real):
    """计算变化百分比"""
    if init == 0:
        return 0
    return round((real - init) / init * 100, 1)

def apply_rules(match):
    """应用记忆体规律进行预测"""
    odds = match['odds']
    macao = match['macao']
    form_diff = match['form_diff']
    confidence = match['confidence']
    h_pct = match['h_pct']
    d_pct = match['d_pct']
    a_pct = match['a_pct']
    
    if not odds:
        return "待定", ""
    
    init_h, init_d, init_a, real_h, real_d, real_a = odds
    h_change = calc_change_pct(init_h, real_h)
    d_change = calc_change_pct(init_d, real_d)
    a_change = calc_change_pct(init_a, real_a)
    
    prediction = ""
    rule = ""
    
    # 规律五：主胜升幅>5% → 和局
    if h_change > 5:
        prediction = "和局"
        rule = "规律五:主升>5%"
        return prediction, rule
    
    # 规律二：平局难出条件
    if '和局' in macao or '平' in macao:
        if init_d < 3.0 or d_change < -5:
            # 平局难出
            if h_change < 0:
                prediction = "主胜"
                rule = f"规律二:平初{init_d:.2f}<3.0"
            else:
                prediction = "客胜"
                rule = f"规律二:平初{init_d:.2f}<3.0"
            return prediction, rule
    
    # 规律一：置信度≥66% + 澳门同向
    if confidence >= 66:
        # 判断澳门方向
        if '主' in macao or '贏' in macao:
            if h_change <= 0:  # 主降
                prediction = "主胜"
                rule = f"规律一:≥66%同向"
                return prediction, rule
        if '客' in macao:
            if a_change <= 0:  # 客降
                prediction = "客胜"
                rule = f"规律一:≥66%同向"
                return prediction, rule
    
    # 规律H：高置信度 + 澳门推平 + 近况均衡 + 无大波动
    if confidence >= 66 and ('和局' in macao or '平' in macao):
        if abs(form_diff) <= 2 and abs(h_change) < 5 and abs(d_change) < 5 and abs(a_change) < 5:
            # 热度分散，按置信度方向
            if h_pct >= d_pct and h_pct >= a_pct:
                prediction = "主胜"
                rule = "规律H:热度分散"
                return prediction, rule
            elif a_pct >= d_pct and a_pct >= h_pct:
                prediction = "客胜"
                rule = "规律H:热度分散"
                return prediction, rule
    
    # 规律I：极端造热 + 近况差极大 → 平局
    if form_diff <= -10:  # 客队碾压
        if h_change < -10 and a_change > 10 and abs(d_change) < 2:
            prediction = "和局"
            rule = "规律I:极端造热平局"
            return prediction, rule
    
    # 规律L：极端造热 + 平赔不降反升 → 主胜
    if form_diff <= -10:  # 客队碾压但极端造热
        if h_change > 10 and a_change < -10 and d_change > 0:
            prediction = "主胜"
            rule = "规律L:极端造热平升→主胜"
            return prediction, rule
    
    # 默认：按置信度方向
    if confidence >= 50:
        if h_pct >= d_pct and h_pct >= a_pct:
            prediction = "主胜"
        elif a_pct >= d_pct and a_pct >= h_pct:
            prediction = "客胜"
        else:
            prediction = "和局"
        rule = f"置信度{confidence:.1f}%"
    else:
        # 低置信度，按赔率变化
        if h_change < a_change:
            prediction = "主胜"
        elif a_change < h_change:
            prediction = "客胜"
        else:
            prediction = "和局"
        rule = f"低置信度顺变化"
    
    return prediction, rule

def main():
    # 查找所有周四比赛
    thursday_files = sorted(glob.glob(f"{DATA_DIR}/周四*_源数据.md"))
    
    matches = []
    for f in thursday_files:
        match_id = os.path.basename(f).split('_')[0]
        
        info = extract_match_info(match_id)
        odds = extract_jingcai_odds(match_id)
        
        if info:
            match = {
                'id': match_id,
                **info,
                'odds': odds
            }
            
            if odds:
                conf_data = calc_confidence(odds)
                if conf_data:
                    match['confidence'] = conf_data[0]
                    match['h_pct'] = conf_data[1]
                    match['d_pct'] = conf_data[2]
                    match['a_pct'] = conf_data[3]
                else:
                    match['confidence'] = 0
                    match['h_pct'] = 0
                    match['d_pct'] = 0
                    match['a_pct'] = 0
            else:
                match['confidence'] = 0
                match['h_pct'] = 0
                match['d_pct'] = 0
                match['a_pct'] = 0
                match['odds'] = None
            
            matches.append(match)
    
    # 输出
    print(f"\n{'='*80}")
    print(f"3.19 周四比赛分析（共{len(matches)}场）")
    print(f"{'='*80}\n")
    
    for m in matches:
        odds = m['odds']
        if odds:
            init_h, init_d, init_a, real_h, real_d, real_a = odds
            h_change = calc_change_pct(init_h, real_h)
            d_change = calc_change_pct(init_d, real_d)
            a_change = calc_change_pct(init_a, real_a)
            
            prediction, rule = apply_rules(m)
            
            print(f"{m['id']}: {m['home']} vs {m['away']}")
            print(f"  置信度: {m['confidence']:.1f}% | 澳门: {m['macao']} | 近况差: {m['form_diff']}")
            print(f"  初盘: {init_h:.2f}/{init_d:.2f}/{init_a:.2f} → 即时: {real_h:.2f}/{real_d:.2f}/{real_a:.2f}")
            print(f"  变化: 主{h_change:+.1f}% 平{d_change:+.1f}% 客{a_change:+.1f}%")
            print(f"  预测: {prediction} | 规律: {rule}")
            print()
        else:
            print(f"{m['id']}: {m['home']} vs {m['away']} | 无竞彩数据")
            print()

if __name__ == "__main__":
    main()
