"""
3.21 周六比赛分析
"""

import os
import re
import glob

DATA_DIR = "d:/work/workbuddy/足球预测/分析模板/3.21"

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

def fmt_change(init_val, real_val):
    """格式化赔率变化幅度"""
    if init_val is None or real_val is None or init_val == 0:
        return "—"
    pct = (real_val - init_val) / init_val * 100
    if abs(pct) < 0.1:
        return "—"
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"

def calc_confidence(real_home, real_draw, real_away):
    """计算置信度"""
    if not all([real_home, real_draw, real_away]):
        return None, None, None
    try:
        h = 1/real_home
        d = 1/real_draw
        a = 1/real_away
        total = h + d + a
        h_pct = h/total*100
        d_pct = d/total*100
        a_pct = a/total*100
        return h_pct, d_pct, a_pct
    except:
        return None, None, None

def extract_jingcai_odds(content):
    """提取竞彩赔率"""
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

def main():
    matches = []
    
    # 只处理周六比赛
    for f in sorted(glob.glob(f'{DATA_DIR}/周六*_源数据.md')):
        match_id = os.path.basename(f).split('_')[0]
        
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        
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
        ht_score = calc_form_score(ht_match.group(1).strip() if ht_match else '')
        at_score = calc_form_score(at_match.group(1).strip() if at_match else '')
        
        # 赔率
        odds = extract_jingcai_odds(content)
        
        # 计算置信度
        confidence = None
        max_conf = None
        if odds:
            h_pct, d_pct, a_pct = calc_confidence(odds[3], odds[4], odds[5])
            if h_pct:
                confidence = {'h': h_pct, 'd': d_pct, 'a': a_pct}
                max_conf = max(h_pct, d_pct, a_pct)
        
        matches.append({
            'id': match_id,
            'home': home,
            'away': away,
            'macao': macao,
            'ht_score': ht_score,
            'at_score': at_score,
            'form_diff': ht_score - at_score,
            'odds': odds,
            'confidence': confidence,
            'max_conf': max_conf
        })
    
    # 输出完整数据列表
    print(f"\n# 3.21 周六比赛完整分析报告\n")
    print(f"> 数据目录：{DATA_DIR}")
    print(f"> 比赛场次：{len(matches)}场\n")
    print("---\n")
    
    print("## 完整数据列表（标准格式）\n")
    print("| 编号 | 对阵 | 置信度 | 澳门心水 | 近况差 | 初盘(胜/平/负) | 即时(胜/平/负) | 变化(H/D/A) |")
    print("|------|------|--------|----------|--------|----------------|----------------|-------------|")
    
    for m in matches:
        odds = m['odds']
        if odds:
            init_str = f"{odds[0]:.2f}/{odds[1]:.2f}/{odds[2]:.2f}"
            real_str = f"{odds[3]:.2f}/{odds[4]:.2f}/{odds[5]:.2f}"
            h_ch = fmt_change(odds[0], odds[3])
            d_ch = fmt_change(odds[1], odds[4])
            a_ch = fmt_change(odds[2], odds[5])
            change_str = f"主{h_ch} 平{d_ch} 客{a_ch}"
            conf_str = f"{m['max_conf']:.1f}%" if m['max_conf'] else "—"
        else:
            init_str = "—"
            real_str = "—"
            change_str = "—"
            conf_str = "—"
        
        print(f"| {m['id']} | {m['home']} vs {m['away']} | {conf_str} | {m['macao']} | {m['form_diff']:+d} | {init_str} | {real_str} | {change_str} |")
    
    print("\n---\n")
    
    # 高置信度比赛（≥66%）
    print("## 偏离分析分类\n")
    print("### 【偏离过高】最可信（置信度≥66%）\n")
    high_conf = [m for m in matches if m['max_conf'] and m['max_conf'] >= 66]
    if high_conf:
        print("| 编号 | 对阵 | 置信度 | 澳门心水 | 近况差 | 变化(H/D/A) |")
        print("|------|------|--------|----------|--------|-------------|")
        for m in high_conf:
            odds = m['odds']
            h_ch = fmt_change(odds[0], odds[3])
            d_ch = fmt_change(odds[1], odds[4])
            a_ch = fmt_change(odds[2], odds[5])
            print(f"| {m['id']} | {m['home']} vs {m['away']} | {m['max_conf']:.1f}% | {m['macao']} | {m['form_diff']:+d} | 主{h_ch} 平{d_ch} 客{a_ch} |")
    else:
        print("无符合条件的比赛\n")
    
    print("\n---\n")
    
    # 过热提醒
    print("## 过热提醒 + 规律判断\n")
    print("| 编号 | 对阵 | 即时赔率 | 变化(H/D/A) | 置信度 | 澳门 | 预测 | 修正预测 | 类型 | 原因 |")
    print("|------|------|----------|-------------|--------|------|------|----------|------|------|")
    
    for m in matches:
        odds = m['odds']
        if not odds:
            continue
        
        # 计算变化幅度
        h_ch = (odds[3] - odds[0]) / odds[0] * 100 if odds[0] else 0
        d_ch = (odds[4] - odds[1]) / odds[1] * 100 if odds[1] else 0
        a_ch = (odds[5] - odds[2]) / odds[2] * 100 if odds[2] else 0
        
        # 基础预测
        if m['confidence']:
            max_dir = max(m['confidence'], key=m['confidence'].get)
            pred_map = {'h': '主胜', 'd': '和局', 'a': '客胜'}
            base_pred = pred_map[max_dir]
        else:
            base_pred = '—'
        
        # 过热判断
        alert_type = ""
        alert_reason = ""
        corrected = base_pred
        
        # 规律五：主升>5%
        if h_ch > 5:
            alert_type = "波动大"
            alert_reason = f"主胜升{h_ch:.1f}%"
            corrected = "和局"
        
        # 规律二：平赔<3.0
        if odds[4] < 3.0 and '和局' in m['macao']:
            alert_type = "平局难出"
            alert_reason = f"平赔{odds[4]:.2f}<3.0"
        
        # 实盘无变化
        if abs(h_ch) < 0.5 and abs(d_ch) < 0.5 and abs(a_ch) < 0.5:
            alert_type = "实盘"
            alert_reason = "实盘无变化"
        
        if alert_type:
            real_str = f"{odds[3]:.2f}/{odds[4]:.2f}/{odds[5]:.2f}"
            h_ch_str = fmt_change(odds[0], odds[3])
            d_ch_str = fmt_change(odds[1], odds[4])
            a_ch_str = fmt_change(odds[2], odds[5])
            conf_str = f"{m['max_conf']:.1f}%" if m['max_conf'] else "—"
            print(f"| {m['id']} | {m['home']} vs {m['away']} | {real_str} | 主{h_ch_str} 平{d_ch_str} 客{a_ch_str} | {conf_str} | {m['macao']} | {base_pred} | {corrected} | {alert_type} | {alert_reason} |")
    
    print(f"\n---\n")
    print(f"## 统计汇总\n")
    high_count = len(high_conf)
    print(f"| 类型 | 场数 |")
    print(f"|------|------|")
    print(f"| 偏离过高(≥66%) | {high_count} |")
    print(f"| 总计 | {len(matches)} |")

if __name__ == "__main__":
    main()
