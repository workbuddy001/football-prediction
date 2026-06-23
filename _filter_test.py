#!/usr/bin/env python3
"""测试多种过滤方案对5月亏损场次的改善效果"""
import json, os, sys
sys.path.insert(0, '.')
from verify_handicap_method_v5 import load_match_data, get_handicap_direction, apply_7step_method

with open('分析模板/_scores.json', 'r', encoding='utf-8') as f:
    scores = json.load(f)

# 加载5月+1让球比赛
matches = []
for key, s in scores.items():
    if not key.isdigit(): continue
    hs, aw = s.get('home_score'), s.get('away_score')
    if hs is None or aw is None: continue
    fp = f'sporttery_data/{key}.json'
    if not os.path.exists(fp): continue
    with open(fp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    ft = data.get('fetch_time', '')
    if ft.startswith('2026-05'):
        hhad = data.get('hhad', {})
        if hhad.get('让球', '') == '+1':
            matches.append((key, int(hs), int(aw), data))

print(f"5月+1让球：{len(matches)}场")
print("="*80)

# 获取每场比赛的投注数据
match_data_list = []
for mid, hs, aw, raw in matches:
    hhad = raw.get('hhad', {})
    handicap = hhad.get('让球', '')
    ad = get_handicap_direction(hs, aw, handicap)
    pred, pred_score, top3_scores, reasons = apply_7step_method(raw)
    if not pred or not ad: continue
    
    # 基础赔率数据
    so = raw.get('score_odds', {})
    all_scores = [(int(k.split(':')[0]), int(k.split(':')[1]), float(v)) 
                  for k, v in so.items() if all(c.isdigit() or c==':' for c in k)]
    all_scores.sort(key=lambda x: x[2])
    
    # 前3赔率
    odds_list = [o for _,_,o in (top3_scores or all_scores[:3])][:3]
    
    # 让球赔率
    hw = float(hhad.get('让胜', 0))
    hd = float(hhad.get('让平', 0))
    hl = float(hhad.get('让负', 0))
    
    # 近况
    preview = raw.get('preview', {})
    recent = preview.get('recent', {})
    hg = [int(m.get('homeTeamFullCourtGoalCnt',0) or 0) for m in recent.get('home',{}).get('matchList',[])[:5]]
    ag = [int(m.get('awayTeamFullCourtGoalCnt',0) or 0) for m in recent.get('away',{}).get('matchList',[])[:5]]
    
    # 联赛
    league = raw.get('match_info', {}).get('league', '')
    
    top3_hit = False
    if top3_scores:
        inv_odds = [1.0/max(o, 1.1) for _,_,o in top3_scores[:3]]
        tw = sum(inv_odds)
        for idx, (h, a, o) in enumerate(top3_scores[:3]):
            stake = (inv_odds[idx] / tw) * 30
            if h == hs and a == aw:
                top3_hit = True
    
    match_data_list.append({
        'mid': mid, 'hs': hs, 'aw': aw,
        'odds1': odds_list[0] if len(odds_list)>0 else 99,
        'odds2': odds_list[1] if len(odds_list)>1 else 99,
        'odds3': odds_list[2] if len(odds_list)>2 else 99,
        'hw': hw, 'hd': hd, 'hl': hl,
        'top3_hit': top3_hit,
        'pred_is_11': (pred_score and pred_score == (1,1)) if pred_score else False,
        'hg_var': sum((x - sum(hg)/len(hg))**2 for x in hg)/len(hg) if hg else 0,
        'ag_var': sum((x - sum(ag)/len(ag))**2 for x in ag)/len(ag) if ag else 0,
        'league': league,
        'is_cup': any(kw in league for kw in ['解放者杯','国际赛','友谊赛','杯','欧冠','欧联']),
    })

# 测试过滤方案
def calc_roi(data_list, filter_fn):
    total_inv, total_ret, hits = 0, 0, 0
    skipped = 0
    for d in data_list:
        if not filter_fn(d):
            skipped += 1
            continue
        # 重新计算投注
        md = load_match_data(d['mid'])
        if not md: continue
        pred, pred_score, top3_scores, reasons = apply_7step_method(md)
        if not pred or not top3_scores: continue
        inv_odds = [1.0/max(o, 1.1) for _,_,o in top3_scores[:3]]
        tw = sum(inv_odds)
        for idx, (h, a, o) in enumerate(top3_scores[:3]):
            stake = (inv_odds[idx]/tw)*30
            total_inv += stake
            if h == d['hs'] and a == d['aw']:
                hits += 1
                total_ret += o * stake
                break
    roi = (total_ret - total_inv)/total_inv*100 if total_inv else 0
    return len(data_list) - skipped, hits, total_inv, total_ret, roi

# 方案1：赔率密集度 - 第3/第1差距<1.2时跳过
print("方案1：赔率密集度（第3候选/第1候选 < 阈值时跳过）")
for thresh in [1.1, 1.2, 1.3, 1.5]:
    n,hits,inv,ret,roi = calc_roi(match_data_list, 
        lambda d: d['odds3']/d['odds1'] >= thresh if d['odds3'] < 99 and d['odds1'] > 0 else True)
    if n > 0:
        print(f"  第3/第1 < {thresh:.1f}跳过: {n}场 命中{hits}({hits/n*100:.0f}%) 投{inv:.0f} 回{ret:.0f} ROI{roi:+.1f}%")

print()

# 方案2：1:1独家判断 - 1:1赔率/第2候选<0.85时才可信
print("方案2：1:1独家判断")
# 通过march_data_list中pred_is_11字段来判断
# 需要从reasons中提取1:1赔率
def check_11_confidence(d):
    md = load_match_data(d['mid'])
    if not md: return True
    so = md.get('score_odds', {})
    o11 = float(so.get('1:1', 99))
    o2 = d['odds2']
    if o2 and o2 < 99 and o2 > 0:
        return o11 / o2 <= 0.9
    return True

n,hits,inv,ret,roi = calc_roi(match_data_list, check_11_confidence)
if n > 0:
    print(f"  1:1赔率/第2>0.9跳过: {n}场 命中{hits}({hits/n*100:.0f}%) 投{inv:.0f} 回{ret:.0f} ROI{roi:+.1f}%")
else:
    print(f"  1:1过滤后无场次")

print()

# 方案3：近况方差
print("方案3：近况方差")
for var_thresh in [2.0, 3.0, 4.0]:
    n,hits,inv,ret,roi = calc_roi(match_data_list,
        lambda d: max(d['hg_var'], d['ag_var']) <= var_thresh)
    if n > 0:
        print(f"  方差>{var_thresh:.0f}跳过: {n}场 命中{hits}({hits/n*100:.0f}%) 投{inv:.0f} 回{ret:.0f} ROI{roi:+.1f}%")

print()

# 方案4：联赛特征
print("方案4：联赛特征（杯赛/国际赛跳过）")
n,hits,inv,ret,roi = calc_roi(match_data_list, lambda d: not d['is_cup'])
if n > 0:
    print(f"  杯赛跳过: {n}场 命中{hits}({hits/n*100:.0f}%) 投{inv:.0f} 回{ret:.0f} ROI{roi:+.1f}%")

print()

# 方案5：让负赔率过滤
print("方案5：让负赔率 < 让胜赔率 - 倾向大比分")
n,hits,inv,ret,roi = calc_roi(match_data_list, lambda d: d['hl'] >= d['hw'])
if n > 0:
    print(f"  让负<让胜跳过: {n}场 命中{hits}({hits/n*100:.0f}%) 投{inv:.0f} 回{ret:.0f} ROI{roi:+.1f}%")

print()

# 方案6：组合
print("方案6：组合（赔率密集1.2 + 方差<4）")
n,hits,inv,ret,roi = calc_roi(match_data_list,
    lambda d: (d['odds3']/d['odds1'] >= 1.2 if d['odds3']<99 and d['odds1']>0 else True) 
              and max(d['hg_var'], d['ag_var']) <= 4)
if n > 0:
    print(f"  组合: {n}场 命中{hits}({hits/n*100:.0f}%) 投{inv:.0f} 回{ret:.0f} ROI{roi:+.1f}%")

print()

# 基准
print("基准（无过滤）:")
n,hits,inv,ret,roi = calc_roi(match_data_list, lambda d: True)
if n > 0:
    print(f"  全部: {n}场 命中{hits}({hits/n*100:.0f}%) 投{inv:.0f} 回{ret:.0f} ROI{roi:+.1f}%")
