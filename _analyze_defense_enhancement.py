#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
防守维度对让球盘 + 大小球的命中率提升验证
"""
import json, glob, sys
from collections import Counter, defaultdict

sys.path.insert(0, '.')
from v36_analyzer import _extract_recent_matches, _calc_att_def, _safe_float

# ---- 加载比分 ----
with open('分析模板/_scores.json', 'r', encoding='utf-8') as f:
    scores_raw = json.load(f)

mid_map = {}
for k, v in scores_raw.items():
    mn = v.get('match_id', '')
    if mn and mn != 'test':
        mid_map[mn] = v
    dt = v.get('date', '')
    if dt and mn:
        mid_map[f'{dt}_{mn}'] = v

# ---- 扫描数据 ----
records = []
for fp in sorted(glob.glob('sporttery_data/*.json')):
    if 'full_' in fp:
        continue
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        continue
    preview = data.get('preview')
    if not preview: continue
    
    mi = data.get('match_info', {})
    match_id = data.get('match_id', '')
    match_num = mi.get('match_num_str', '')
    match_date = mi.get('match_date', '')
    
    # 找比分
    score = mid_map.get(match_id) or mid_map.get(f'{match_date}_{match_num}')
    if not score:
        for k, v in mid_map.items():
            if match_num and match_num in k:
                score = v; break
    if not score: continue
    
    hs = score.get('home_score')
    ag = score.get('away_score')
    if hs is None or ag is None: continue
    
    # 近况攻防
    try:
        recent = _extract_recent_matches(data)
        h_att, h_def, a_att, a_def = _calc_att_def(recent)
    except:
        continue
    
    # 让球盘数据
    hhad = data.get('hhad', {})
    if not hhad: continue
    hhad_win = _safe_float(hhad.get('让胜', 0))
    hhad_draw = _safe_float(hhad.get('让平', 0))
    hhad_lose = _safe_float(hhad.get('让负', 0))
    if hhad_win >= 900: continue
    
    # 解析让球方向
    hcap_str = str(hhad.get('让球', '0'))
    try: hcap = -float(hcap_str)
    except: hcap = 0
    is_home_give = hcap < 0   # 主让球 (让球=-1)
    is_home_recv = hcap > 0   # 主受让 (让球=+1)
    
    # 让球盘实际结果
    adj_h = hs + hcap  # 调整后主队得分
    if adj_h > ag: hhad_result = '让胜'
    elif adj_h == ag: hhad_result = '让平'
    else: hhad_result = '让负'
    
    total = hs + ag
    ou_result = '大球' if total >= 3 else '小球'
    
    # 大小球赔率
    ou = data.get('over_under', {}) or {}
    ou_line = _safe_float(ou.get('ou_line', 2.5))
    ou_over = _safe_float(ou.get('over_odds', 0))
    ou_under = _safe_float(ou.get('under_odds', 0))
    
    # 进球数赔率
    tg = data.get('total_goals', {}) or {}
    g0 = _safe_float(tg.get('0球', 0))
    
    # 胜负
    if hs > ag: result = '主胜'
    elif hs < ag: result = '主负'
    else: result = '平局'
    
    records.append({
        'match_id': match_id,
        'home': mi.get('home_team', '?'),
        'away': mi.get('away_team', '?'),
        'hs': hs, 'ag': ag, 'total': total,
        'result': result,
        'hhad_result': hhad_result,
        'ou_result': ou_result,
        'h_att': h_att, 'h_def': h_def, 'a_att': a_att, 'a_def': a_def,
        'def_diff': h_def - a_def,
        'att_diff': h_att - a_att,
        'hhad_win': hhad_win, 'hhad_draw': hhad_draw, 'hhad_lose': hhad_lose,
        'is_home_give': is_home_give, 'is_home_recv': is_home_recv, 'hcap': hcap,
        'ou_line': ou_line, 'ou_over': ou_over, 'ou_under': ou_under,
        'g0': g0,
        'combined_avg': (h_att + a_att + h_def + a_def) / 4 * 2,  # rough combined_avg
    })

print(f"有效比赛: {len(records)} 场")

def classify_def(val):
    if val <= 0.8: return '铁壁'
    if val <= 1.2: return '稳固'
    if val <= 1.8: return '一般'
    if val <= 2.5: return '漏勺'
    return '大漏'

# ============================================================
# Part 1: 让球盘 + 防守维度
# ============================================================
print("\n" + "=" * 70)
print("Part 1: 让球盘规律 × 防守维度 → 命中率提升")
print("=" * 70)

# 1A: 主让球 → 让胜75% (原始规律)
home_give = [r for r in records if r['is_home_give']]
n = len(home_give)
base = sum(1 for r in home_give if r['hhad_result'] == '让胜')
print(f"\n1A. 主让球 → 让胜: {n}场, 让胜{base}({base/n*100:.1f}%) [无防守过滤]")

# 加上防守维度: 主防优于客防
for lo, hi, label in [(-5, -0.5, '主防明显优(def<-0.5)'), (-5, -0.3, '主防略优(def<-0.3)'),
                       (-5, 0.0, '主防不劣(def<0)'), (0.0, 0.5, '主防劣(0<def<0.5)'),
                       (0.5, 5, '主防极劣(def>0.5)')]:
    matched = [r for r in home_give if lo <= r['def_diff'] < hi]
    if len(matched) < 10: continue
    n2 = len(matched)
    hit = sum(1 for r in matched if r['hhad_result'] == '让胜')
    print(f"    +{label}: {n2}场, 让胜{hit}({hit/n2*100:.1f}%) {'⬆' if hit/n2 > base/n else '⬇'}")

# 1B: 主受让 → 让负54% (原始规律)
home_recv = [r for r in records if r['is_home_recv']]
n = len(home_recv)
base = sum(1 for r in home_recv if r['hhad_result'] == '让负')
print(f"\n1B. 主受让 → 让负: {n}场, 让负{base}({base/n*100:.1f}%) [无防守过滤]")

for lo, hi, label in [(-5, -0.5, '主防优(def<-0.5)'), (-5, 0.0, '主防不劣(def<0)'),
                       (0.0, 0.5, '主防劣(def>0)'), (0.5, 5, '主防极劣(def>0.5)')]:
    matched = [r for r in home_recv if lo <= r['def_diff'] < hi]
    if len(matched) < 10: continue
    n2 = len(matched)
    hit = sum(1 for r in matched if r['hhad_result'] == '让负')
    print(f"    +{label}: {n2}场, 让负{hit}({hit/n2*100:.1f}%) {'⬆' if hit/n2 > base/n else '⬇'}")

# 1C: 主受让 + 让胜赔<1.60 → 让胜 (防守维度增强)
print(f"\n1C. 主受让 + 让胜<1.60 → 让胜:")
h_recv_low_win = [r for r in home_recv if r['hhad_win'] < 1.60]
n = len(h_recv_low_win)
if n >= 5:
    hit = sum(1 for r in h_recv_low_win if r['hhad_result'] == '让胜')
    print(f"  全部: {n}场, 让胜{hit}({hit/n*100:.1f}%)")
    for lo, hi, label in [(-5, -0.3, '主防优'), (-0.3, 0.3, '防接近'), (0.3, 5, '主防劣')]:
        matched = [r for r in h_recv_low_win if lo <= r['def_diff'] < hi]
        if len(matched) < 5: continue
        n2 = len(matched)
        hit2 = sum(1 for r in matched if r['hhad_result'] == '让胜')
        print(f"    +{label}: {n2}场, 让胜{hit2}({hit2/n2*100:.1f}%)")

# 1D: 详细：不同让球深度 + 防守组合
print(f"\n1D. 让球盘结论 × 防守差 完整矩阵:")
conditions = [
    ('主让深(>1)', lambda r: r['is_home_give'] and abs(r['hcap']) > 1),
    ('主让1球', lambda r: r['is_home_give'] and abs(r['hcap']) == 1),
    ('平手', lambda r: abs(r['hcap']) < 0.5),
    ('主受1球', lambda r: r['is_home_recv'] and abs(r['hcap']) == 1),
    ('主受深(>1)', lambda r: r['is_home_recv'] and abs(r['hcap']) > 1),
]
for cname, cond in conditions:
    subset = [r for r in records if cond(r)]
    if len(subset) < 10: continue
    n = len(subset)
    # 默认推荐
    if '主让' in cname:
        default_pick = '让胜'
    elif '主受' in cname:
        default_pick = '让负'
    else:
        default_pick = None
    
    base_hit = sum(1 for r in subset if r['hhad_result'] == default_pick) if default_pick else 0
    print(f"\n  {cname}({n}场) 默认推荐{default_pick or '无'}: {base_hit}({base_hit/n*100:.1f}%)")
    
    for lo, hi, label in [(-5, -0.5, '主防优'), (-0.5, 0.5, '防接近'), (0.5, 5, '主防劣')]:
        matched = [r for r in subset if lo <= r['def_diff'] < hi]
        if len(matched) < 10: continue
        n2 = len(matched)
        hw = sum(1 for r in matched if r['hhad_result'] == '让胜')
        hd = sum(1 for r in matched if r['hhad_result'] == '让平')
        hl = sum(1 for r in matched if r['hhad_result'] == '让负')
        # 最佳推荐方向
        best = max([('让胜', hw), ('让平', hd), ('让负', hl)], key=lambda x: x[1])
        print(f"    +{label}({n2}场): 让胜{hw}({hw/n2*100:.0f}%) 让平{hd}({hd/n2*100:.0f}%) 让负{hl}({hl/n2*100:.0f}%) → 推荐{best[0]}({best[1]/n2*100:.0f}%)")

# ============================================================
# Part 2: 大小球 + 防守维度
# ============================================================
print("\n" + "=" * 70)
print("Part 2: 大小球方向判断 × 防守维度 → 命中率提升")
print("=" * 70)

# 2A: 基础大小球方向判断 (用近况做方向判断)
print("\n2A. 基础方向判断: 近况高→大球, 近况低→小球")
for lo, hi, label in [(0, 2.0, '近况<2.0→小球'), (2.0, 2.5, '近况2.0-2.5→小球倾向'),
                       (2.5, 3.0, '近况2.5-3.0→大球倾向'), (3.0, 3.5, '近况3.0-3.5→大球'),
                       (3.5, 99, '近况>3.5→强大大球')]:
    matched = [r for r in records if lo <= r['combined_avg'] < hi]
    if len(matched) < 10: continue
    n = len(matched)
    predict = '大球' if (lo + hi) / 2 >= 2.5 else '小球'
    hit = sum(1 for r in matched if r['ou_result'] == predict)
    print(f"  {label}: {n}场, {predict}命中{hit}({hit/n*100:.1f}%)")

# 2B: 加入防守维度的方向判断
print("\n2B. 防守维度修正 → 方向判断命中率变化:")

# 按近况+防守组合
for form_lo, form_hi, form_label in [(0, 2.0, '近况低'), (2.0, 2.5, '近况中低'), 
                                       (2.5, 3.5, '近况中高'), (3.5, 99, '近况高')]:
    for def_lo, def_hi, def_label in [(-5, -0.3, '主防优'), (-0.3, 0.3, '防接近'), (0.3, 5, '主防劣')]:
        matched = [r for r in records if form_lo <= r['combined_avg'] < form_hi and def_lo <= r['def_diff'] < def_hi]
        if len(matched) < 10: continue
        n = len(matched)
        big = sum(1 for r in matched if r['total'] >= 3)
        small = n - big
        base_dir = '大球' if (form_lo + form_hi) / 2 >= 2.5 else '小球'
        base_hit = big if base_dir == '大球' else small
        
        # 考虑防守后: 主防劣→偏向大球, 主防优→偏向小球
        if def_label == '主防劣':
            adj_dir = '大球'  # 防守差→容易出大球
        elif def_label == '主防优':
            adj_dir = '小球' if base_dir == '小球' else base_dir  # 防守好→小球, 但近况高时不反转
        else:
            adj_dir = base_dir
        
        adj_hit = big if adj_dir == '大球' else small
        
        if adj_dir != base_dir:
            delta = adj_hit / n * 100 - base_hit / n * 100
            sign = '⬆' if delta > 0 else '⬇'
            print(f"  {form_label}+{def_label}({n}场): 原{base_dir}{base_hit}({base_hit/n*100:.0f}%) → 修正{adj_dir}{adj_hit}({adj_hit/n*100:.0f}%) {sign}{abs(delta):.1f}pp")

# 2C: 具体大小球铁律 + 防守
print("\n2C. 现有画像规律 + 防守维度增强:")

# 铁壁 + 铁壁 → 小球58%/2球50%
iron = [r for r in records if r['h_def'] < 1.0 and r['a_def'] < 1.0]
if iron:
    n = len(iron)
    small = sum(1 for r in iron if r['total'] <= 2)
    two = sum(1 for r in iron if r['total'] == 2)
    print(f"  双方铁壁(h_def<1,a_def<1): {n}场, 小球{small}({small/n*100:.0f}%), 2球{two}({two/n*100:.0f}%)")

# 漏勺 + 漏勺 → 大球
leak = [r for r in records if r['h_def'] >= 2.0 and r['a_def'] >= 2.0]
if leak:
    n = len(leak)
    big = sum(1 for r in leak if r['total'] >= 3)
    print(f"  双方漏勺(h_def≥2,a_def≥2): {n}场, 大球{big}({big/n*100:.0f}%)")

# 细化: 攻防混合
print("\n2D. 攻防四象限大小球精度:")
# 高攻+高防 → ?
hh = [r for r in records if r['h_att'] >= 2.0 and r['h_def'] < 1.0 and r['a_att'] >= 2.0 and r['a_def'] < 1.0]
# 高攻+低防 → 漏勺大战
hl = [r for r in records if r['h_att'] >= 2.0 and r['a_def'] >= 2.0]
# 低攻+高防 → 沉闷
lh = [r for r in records if r['h_att'] < 1.5 and r['a_att'] < 1.5 and r['h_def'] < 1.0 and r['a_def'] < 1.0]
# 低攻+低防 → 
ll = [r for r in records if r['h_att'] < 1.5 and r['a_att'] < 1.5 and r['h_def'] >= 1.5 and r['a_def'] >= 1.5]

for label, matched in [('高攻高防(矛盾)', hh), ('主攻强+客漏勺', hl), 
                        ('双方沉闷铁壁', lh), ('双方低攻漏勺', ll)]:
    if len(matched) < 8: continue
    n = len(matched)
    big = sum(1 for r in matched if r['total'] >= 3)
    avg_t = sum(r['total'] for r in matched) / n
    print(f"  {label}({n}场): 大球{big}({big/n*100:.0f}%), 均球{avg_t:.1f}")

# 2E: 水位 + 防守组合 (核心：庄家做盘的方向是否被防守支撑?)
print("\n2E. 水位信号 + 防守一致性验证:")
# 大球低水 + 主防劣 → 信号一致, 高命中
big_low = [r for r in records if r['ou_over'] < 0.85 and r['ou_line'] >= 2.5]
for lo, hi, label in [(-5, -0.3, '主防优'), (-0.3, 0.3, '防接近'), (0.3, 5, '主防劣')]:
    matched = [r for r in big_low if lo <= r['def_diff'] < hi]
    if len(matched) < 8: continue
    n = len(matched)
    big = sum(1 for r in matched if r['total'] >= 3)
    avg = sum(r['total'] for r in matched) / n
    print(f"  大球低水+{label}: {n}场, 吹大{big}({big/n*100:.0f}%), 均球{avg:.1f}")

# 小球低水 + 主防优 → 信号一致
small_low = [r for r in records if r['ou_under'] < 0.85 and r['ou_line'] >= 2.5]
for lo, hi, label in [(-5, -0.3, '主防优'), (-0.3, 0.3, '防接近'), (0.3, 5, '主防劣')]:
    matched = [r for r in small_low if lo <= r['def_diff'] < hi]
    if len(matched) < 8: continue
    n = len(matched)
    small = sum(1 for r in matched if r['total'] <= 2)
    avg = sum(r['total'] for r in matched) / n
    print(f"  小球低水+{label}: {n}场, 小球{small}({small/n*100:.0f}%), 均球{avg:.1f}")

# ============================================================
# 总结
# ============================================================
print("\n" + "=" * 70)
print("总结: 防守维度的增量价值")
print("=" * 70)

# 让球盘最佳提升
home_give_best = [r for r in home_give if r['def_diff'] <= -0.3]
hgb = sum(1 for r in home_give_best if r['hhad_result'] == '让胜') / max(len(home_give_best), 1) * 100
print(f"\n让球盘: 主让+主防优(def<-0.3) → 让胜{hgb:.1f}% (vs 基准{base/n*100:.1f}%)")

# 大小球最佳提升
form_high_def_bad = [r for r in records if r['combined_avg'] >= 2.5 and r['def_diff'] > 0.3]
if form_high_def_bad:
    big_hit = sum(1 for r in form_high_def_bad if r['total'] >= 3) / len(form_high_def_bad) * 100
    form_high_all = [r for r in records if r['combined_avg'] >= 2.5]
    base_big = sum(1 for r in form_high_all if r['total'] >= 3) / max(len(form_high_all), 1) * 100
    print(f"大小球: 近况高+主防劣(def>0.3) → 大球{big_hit:.1f}% (vs 基准近况高{base_big:.1f}%)")

form_low_def_good = [r for r in records if r['combined_avg'] < 2.5 and r['def_diff'] < -0.3]
if form_low_def_good:
    small_hit = sum(1 for r in form_low_def_good if r['total'] <= 2) / len(form_low_def_good) * 100
    form_low_all = [r for r in records if r['combined_avg'] < 2.5]
    base_small = sum(1 for r in form_low_all if r['total'] <= 2) / max(len(form_low_all), 1) * 100
    print(f"大小球: 近况低+主防优(def<-0.3) → 小球{small_hit:.1f}% (vs 基准近况低{base_small:.1f}%)")
