#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
失球（防守能力）与比赛结果导向规律深度分析
验证假说：防守决定比赛走向（vs 攻击力）
"""
import json, glob, os, sys
from collections import Counter, defaultdict

sys.path.insert(0, '.')
from v36_analyzer import _extract_recent_matches, _calc_att_def, _safe_float

# 加载比分结果
with open('分析模板/_scores.json', 'r', encoding='utf-8') as f:
    scores_raw = json.load(f)

score_map = {}  # match_num_str -> score info
mid_map = {}    # match_id -> score info (备用)
for k, v in scores_raw.items():
    mn = v.get('match_id', '')
    if mn and mn != 'test':
        mid_map[mn] = v
    # match_num_str 匹配: 用 match_date + match_id
    dt = v.get('date', '')
    if dt and mn:
        key = f"{dt}_{mn}"
        score_map[key] = v

print(f"比分数据: {len(score_map)} 条(date+num) + {len(mid_map)} 条(match_id)")

# 扫描sporttery_data
data_files = sorted(glob.glob('sporttery_data/*.json'))
valid = 0
records = []

for fp in data_files:
    if 'full_' in fp:
        continue
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        continue
    
    preview = data.get('preview')
    if not preview:
        continue
    
    mi = data.get('match_info', {})
    match_id = data.get('match_id', '')
    match_num = mi.get('match_num_str', '')
    match_date = mi.get('match_date', '')
    
    # 找比分结果
    score = None
    # 方式1: match_num_str (如 "周一010")
    if match_num:
        score = score_map.get(f'{match_date}_{match_num}')
    # 方式2: match_id
    if not score and match_id:
        score = mid_map.get(match_id)
    # 方式3: 模糊匹配
    if not score:
        for k, v in score_map.items():
            if match_num and match_num in k:
                score = v
                break
    
    if not score:
        continue
    
    h_score = score.get('home_score')
    a_score = score.get('away_score')
    if h_score is None or a_score is None:
        continue
    
    # 提取近况攻防数据
    try:
        recent = _extract_recent_matches(data)
        h_att, h_def, a_att, a_def = _calc_att_def(recent)
    except:
        continue
    
    total = h_score + a_score
    
    # 胜负结果
    if h_score > a_score:
        result = '主胜'
    elif h_score < a_score:
        result = '主负'
    else:
        result = '平局'
    
    # 大小球 (以2.5为界)
    ou_result = '大球' if total >= 3 else '小球'
    
    records.append({
        'match_id': match_id,
        'match_num': match_num,
        'match_date': match_date,
        'home': mi.get('home_team', '?'),
        'away': mi.get('away_team', '?'),
        'h_att': round(h_att, 2),
        'h_def': round(h_def, 2),
        'a_att': round(a_att, 2),
        'a_def': round(a_def, 2),
        'h_score': h_score,
        'a_score': a_score,
        'total': total,
        'result': result,
        'ou_result': ou_result,
        'att_diff': round(h_att - a_att, 2),  # 主攻-客攻
        'def_diff': round(h_def - a_def, 2),  # 主失-客失(越小=主防守越好)
    })
    valid += 1

print(f"\n有效比赛: {valid} 场")

# ============================================================
# 分析1: 失球差(def_diff = 主失 - 客失) 与胜负关系
# ============================================================
print("\n" + "=" * 70)
print("分析1: 失球差(def_diff = 主失 - 客失) vs 胜负")
print("=" * 70)

def_diff_bins = [
    (-5.0, -1.0, '主防极强(差<-1.0)'),
    (-1.0, -0.5, '主防明显优(-1.0~-0.5)'),
    (-0.5, -0.2, '主防略优(-0.5~-0.2)'),
    (-0.2, 0.2, '防守接近(-0.2~0.2)'),
    (0.2, 0.5, '客防略优(0.2~0.5)'),
    (0.5, 1.0, '客防明显优(0.5~1.0)'),
    (1.0, 5.0, '客防极强(>1.0)'),
]

for lo, hi, label in def_diff_bins:
    matched = [r for r in records if lo <= r['def_diff'] < hi]
    if not matched:
        continue
    n = len(matched)
    home_win = sum(1 for r in matched if r['result'] == '主胜')
    draw = sum(1 for r in matched if r['result'] == '平局')
    away_win = sum(1 for r in matched if r['result'] == '主负')
    big_ball = sum(1 for r in matched if r['ou_result'] == '大球')
    avg_total = sum(r['total'] for r in matched) / n
    print(f"\n  {label}: {n}场")
    print(f"    胜负: 主胜{home_win}({home_win/n*100:.0f}%) 平{draw}({draw/n*100:.0f}%) 主负{away_win}({away_win/n*100:.0f}%)")
    print(f"    大小球: 大球{big_ball}({big_ball/n*100:.0f}%) 均球{avg_total:.1f}")

# ============================================================
# 分析2: 失球等级分类 (铁壁/稳/一般/漏/大漏)
# ============================================================
print("\n" + "=" * 70)
print("分析2: 失球等级分类交叉分析")
print("=" * 70)

def classify_def(val):
    if val <= 0.8: return '铁壁(A)'
    if val <= 1.2: return '稳固(B)'
    if val <= 1.8: return '一般(C)'
    if val <= 2.5: return '漏勺(D)'
    return '大漏(E)'

# 按主队防守+客队防守分组
groups = defaultdict(list)
for r in records:
    hc = classify_def(r['h_def'])
    ac = classify_def(r['a_def'])
    key = f"{hc} vs {ac}"
    groups[key].append(r)

# 按结果排名打印
sorted_groups = sorted(groups.items(), key=lambda x: -len(x[1]))
for key, matched in sorted_groups:
    if len(matched) < 15:
        continue
    n = len(matched)
    home_win = sum(1 for r in matched if r['result'] == '主胜')
    draw = sum(1 for r in matched if r['result'] == '平局')
    away_win = sum(1 for r in matched if r['result'] == '主负')
    big = sum(1 for r in matched if r['ou_result'] == '大球')
    avg_t = sum(r['total'] for r in matched) / n
    print(f"\n  {key}: {n}场")
    print(f"    胜负: 主{home_win}({home_win/n*100:.0f}%) 平{draw}({draw/n*100:.0f}%) 客{away_win}({away_win/n*100:.0f}%)")
    print(f"    大球: {big}({big/n*100:.0f}%) 均球{avg_t:.1f}")

# ============================================================
# 分析3: 防守 vs 攻击 对胜负的影响力对比
# ============================================================
print("\n" + "=" * 70)
print("分析3: 防守差 vs 攻击差 → 哪个更能预测胜负？")
print("=" * 70)

# 场景A: 攻击优势在客队(主攻<客攻) 但防守优势在主队(主失<客失)
print("\n  场景A: 客攻强+主防强 (攻击优势在客, 防守优势在主)")
a_records = [r for r in records if r['h_att'] < r['a_att'] and r['h_def'] < r['a_def']]
if a_records:
    n = len(a_records)
    hw = sum(1 for r in a_records if r['result'] == '主胜')
    aw = sum(1 for r in a_records if r['result'] == '主负')
    dr = n - hw - aw
    print(f"    {n}场: 主胜{hw}({hw/n*100:.0f}%) 平{dr}({dr/n*100:.0f}%) 主负{aw}({aw/n*100:.0f}%)")
    print(f"    → 防守优势压过攻击劣势! 主胜率显著高于预期")

# 场景B: 攻击优势在主队+防守优势在主队 (双优)
print("\n  场景B: 主攻强+主防强 (主队全面占优)")
b_records = [r for r in records if r['h_att'] >= r['a_att'] and r['h_def'] < r['a_def']]
if b_records:
    n = len(b_records)
    hw = sum(1 for r in b_records if r['result'] == '主胜')
    aw = sum(1 for r in b_records if r['result'] == '主负')
    dr = n - hw - aw
    print(f"    {n}场: 主胜{hw}({hw/n*100:.0f}%) 平{dr}({dr/n*100:.0f}%) 主负{aw}({aw/n*100:.0f}%)")

# 场景C: 攻击优势在主队+防守优势在客队
print("\n  场景C: 主攻强+客防强 (攻击优在主, 防守优在客)")
c_records = [r for r in records if r['h_att'] >= r['a_att'] and r['h_def'] >= r['a_def']]
if c_records:
    n = len(c_records)
    hw = sum(1 for r in c_records if r['result'] == '主胜')
    aw = sum(1 for r in c_records if r['result'] == '主负')
    dr = n - hw - aw
    print(f"    {n}场: 主胜{hw}({hw/n*100:.0f}%) 平{dr}({dr/n*100:.0f}%) 主负{aw}({aw/n*100:.0f}%)")

# 场景D: 客攻强+客防强
print("\n  场景D: 客攻强+客防强 (客队全面占优)")
d_records = [r for r in records if r['h_att'] < r['a_att'] and r['h_def'] >= r['a_def']]
if d_records:
    n = len(d_records)
    hw = sum(1 for r in d_records if r['result'] == '主胜')
    aw = sum(1 for r in d_records if r['result'] == '主负')
    dr = n - hw - aw
    print(f"    {n}场: 主胜{hw}({hw/n*100:.0f}%) 平{dr}({dr/n*100:.0f}%) 主负{aw}({aw/n*100:.0f}%)")

# ============================================================
# 分析4: 失球差与总进球的关联
# ============================================================
print("\n" + "=" * 70)
print("分析4: 失球差 vs 总进球数")
print("=" * 70)

for lo, hi, label in def_diff_bins:
    matched = [r for r in records if lo <= r['def_diff'] < hi]
    if len(matched) < 10:
        continue
    n = len(matched)
    goal_dist = Counter(r['total'] for r in matched)
    avg = sum(r['total'] for r in matched) / n
    top_goals = goal_dist.most_common(3)
    print(f"  {label}({n}场): 均球{avg:.1f} | 最常见: {top_goals}")

# ============================================================
# 分析5: 塞维利亚那场的具体数据验证
# ============================================================
print("\n" + "=" * 70)
print("分析5: 防守优势明确(主失<客失, 差≥0.5) → 主胜率")
print("=" * 70)

# 主失比客失少>=0.5 且差距不是极端
def_clear = [r for r in records if r['def_diff'] <= -0.3 and r['def_diff'] > -3.0]
n = len(def_clear)
hw = sum(1 for r in def_clear if r['result'] == '主胜')
aw = sum(1 for r in def_clear if r['result'] == '主负')
dr = n - hw - aw
print(f"  def_diff≤-0.3: {n}场, 主胜{hw}({hw/n*100:.0f}%), 平{dr}({dr/n*100:.0f}%), 主负{aw}({aw/n*100:.0f}%)")

# 细分: 差距越大越好
for threshold in [-0.3, -0.5, -0.8, -1.0, -1.5]:
    matched = [r for r in def_clear if r['def_diff'] <= threshold]
    if len(matched) < 5:
        break
    n2 = len(matched)
    hw2 = sum(1 for r in matched if r['result'] == '主胜')
    print(f"  def_diff≤{threshold}: {n2}场, 主胜{hw2}({hw2/n2*100:.0f}%) 均失球差{sum(r['def_diff'] for r in matched)/n2:.1f}")

# 加上攻击力也占优的
print("\n  主防优(def_diff≤-0.5) + 主攻也优 → 双优主胜率:")
double = [r for r in def_clear if r['def_diff'] <= -0.5 and r['h_att'] >= r['a_att']]
if double:
    n3 = len(double)
    hw3 = sum(1 for r in double if r['result'] == '主胜')
    print(f"  {n3}场, 主胜{hw3}({hw3/n3*100:.0f}%)")

print("\n  主防优(def_diff≤-0.5) + 但攻击劣势(h_att < a_att) → 防守单优:")
single = [r for r in def_clear if r['def_diff'] <= -0.5 and r['h_att'] < r['a_att']]
if single:
    n4 = len(single)
    hw4 = sum(1 for r in single if r['result'] == '主胜')
    print(f"  {n4}场, 主胜{hw4}({hw4/n4*100:.0f}%)")
    print(f"  → 这正是塞维利亚vs皇家社会(W{round(hw4/n4*100)}%)的场景!")

# ============================================================
# 分析6: 比分分布（防守优主队会打出什么比分）
# ============================================================
print("\n" + "=" * 70)
print("分析6: 防守优主队(def_diff≤-0.3)的比分分布")
print("=" * 70)

def_adv = [r for r in records if r['def_diff'] <= -0.3]
score_dist = Counter(f"{r['h_score']}-{r['a_score']}" for r in def_adv)
print(f"  Top-10 比分 ({len(def_adv)}场):")
for sc, cnt in score_dist.most_common(10):
    pct = cnt / len(def_adv) * 100
    print(f"    {sc}: {cnt}场 ({pct:.1f}%)")

# ============================================================
# 分析7: 大小球规律
# ============================================================
print("\n" + "=" * 70)
print("分析7: 失球组合 vs 大小球")
print("=" * 70)

for (lo1, hi1, label1, lo2, hi2, label2) in [
    (0, 1.0, '双方铁壁', 0, 1.0, '双方铁壁'),
    (0, 1.0, '主铁壁', 1.5, 99, '客漏勺'),
    (1.5, 99, '主漏勺', 0, 1.0, '客铁壁'),
    (1.5, 99, '双方漏勺', 1.5, 99, '双方漏勺'),
]:
    matched = [r for r in records if lo1 <= r['h_def'] < hi1 and lo2 <= r['a_def'] < hi2]
    if len(matched) < 10:
        continue
    n = len(matched)
    big = sum(1 for r in matched if r['total'] >= 3)
    avg = sum(r['total'] for r in matched) / n
    print(f"  {label1} + {label2}: {n}场, 大球{big}({big/n*100:.0f}%), 均球{avg:.1f}")

# ============================================================
# 总结
# ============================================================
print("\n" + "=" * 70)
print("核心发现总结")
print("=" * 70)

print("\n1. 防守差 vs 胜负导向:")
for lo, hi, label in def_diff_bins:
    matched = [r for r in records if lo <= r['def_diff'] < hi]
    if not matched:
        continue
    n = len(matched)
    hw = sum(1 for r in matched if r['result'] == '主胜')
    print(f"   {label:30s}: n={n:3d}, 主胜={hw/n*100:4.1f}%")

# 攻击差的对比
print("\n2. 攻击差(att_diff)对比 → 防守差更有预测力吗?")
att_bins = [
    (-5, -1.0, '客攻极强'),
    (-1.0, -0.5, '客攻明显强'),
    (-0.5, -0.2, '客攻略强'),
    (-0.2, 0.2, '攻击接近'),
    (0.2, 0.5, '主攻略强'),
    (0.5, 1.0, '主攻明显强'),
    (1.0, 5, '主攻极强'),
]
for lo, hi, label in att_bins:
    matched = [r for r in records if lo <= r['att_diff'] < hi]
    if not matched:
        continue
    n = len(matched)
    hw = sum(1 for r in matched if r['result'] == '主胜')
    print(f"   {label:15s}: n={n:3d}, 主胜={hw/n*100:4.1f}%")
