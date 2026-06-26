#!/usr/bin/env python3
"""让平升赔>8% → 方向+近况加权+联赛过滤 ROI回测"""
import json, os, sys

def get_dir(hs, aw, hc):
    hv = float(hc)
    if hv + hs > aw: return '让胜'
    elif hv + hs == aw: return '让平'
    else: return '让负'

def estimate_goals(avg):
    if avg < 0.5: return (0, 2)
    if avg < 1.0: return (0, 2)
    if avg < 1.5: return (0, 3)
    if avg < 2.0: return (0, 3)
    if avg < 2.5: return (0, 4)
    return (1, 4)

def round_stake(amount):
    return max(2, round(amount / 2) * 2)

def get_form_avg(data):
    """获取双方近况场均进球"""
    preview = data.get('preview', {})
    recent = preview.get('recent', {})
    home_list = recent.get('home', {}).get('matchList', [])[:5] if isinstance(recent.get('home'), dict) else []
    away_list = recent.get('away', {}).get('matchList', [])[:5] if isinstance(recent.get('away'), dict) else []
    hg = [int(m.get('homeTeamFullCourtGoalCnt',0) or 0) for m in home_list]
    ag = [int(m.get('awayTeamFullCourtGoalCnt',0) or 0) for m in away_list]
    havg = sum(hg)/len(hg) if hg else 0
    aavg = sum(ag)/len(ag) if ag else 0
    return havg, aavg

with open('分析模板/_scores.json', 'r', encoding='utf-8') as f:
    scores = json.load(f)

all_results = []
for prefix, label in [('2026-05', '5月'), ('2026-06', '6月')]:
    for key, s in scores.items():
        if not key.isdigit(): continue
        hs, aw = s.get('home_score'), s.get('away_score')
        if hs is None or aw is None: continue
        fp = f'sporttery_data/{key}.json'
        if not os.path.exists(fp): continue
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not data.get('fetch_time', '').startswith(prefix): continue
        
        # 联赛过滤：跳过世界杯/国际赛
        league = data.get('match_info', {}).get('league', '')
        if any(kw in league for kw in ['世界杯', '国际赛']):
            continue
        
        hhad_ch = data.get('hhad_change', {})
        if not hhad_ch: continue
        hhad = data.get('hhad', {})
        hc = hhad.get('让球', '')
        if not hc: continue
        
        dp = hhad_ch.get('让平', {})
        if not isinstance(dp, dict): continue
        if float(dp.get('change_pct', 0)) <= 8: continue
        
        mi = data.get('match_info', {})
        ht = mi.get('home_team', '?')
        at = mi.get('away_team', '?')
        
        hw = float(hhad.get('让胜', 0))
        hl = float(hhad.get('让负', 0))
        hv = float(hc)
        
        actual = get_dir(hs, aw, hc)
        actual_score = (hs, aw)
        
        # 排除让平
        if actual == '让平':
            allow_dirs = ['让胜', '让负']
        else:
            pick_dir = '让胜' if hw <= hl else '让负'
            allow_dirs = [pick_dir]
        
        # 获取近况数据
        havg, aavg = get_form_avg(data)
        home_exp = estimate_goals(havg)
        away_exp = estimate_goals(aavg)
        
        # 从score_odds筛选
        so = data.get('score_odds', {})
        candidates = []
        for sk, sv in so.items():
            try:
                sh, sa = int(sk.split(':')[0]), int(sk.split(':')[1])
            except: continue
            if sh > 5 or sa > 5: continue
            odds = float(sv) if sv else 0
            if odds <= 0: continue
            
            d = '让胜' if hv + sh > sa else ('让平' if hv + sh == sa else '让负')
            if d not in allow_dirs: continue
            
            # 近况期望过滤
            if havg > 0 and not (home_exp[0] <= sh <= home_exp[1]): continue
            if aavg > 0 and not (away_exp[0] <= sa <= away_exp[1]): continue
            
            candidates.append((sh, sa, odds))
        
        if not candidates: continue
        
        # 近况匹配加权排序：deviation越小越匹配
        if havg > 0 and aavg > 0:
            def sort_key(x):
                h, a, o = x
                dev = ((h - havg)**2 + (a - aavg)**2) ** 0.5
                return o * (1 + 0.3 * dev)
            candidates.sort(key=sort_key)
        else:
            candidates.sort(key=lambda x: x[2])
        
        top3 = candidates[:3]
        
        # 权重分配
        inv = [1.0/max(o, 1.1) for _,_,o in top3]
        tw = sum(inv)
        raw = [(inv[i]/tw)*30 for i in range(len(top3))]
        stakes = [round_stake(s) for s in raw]
        if sum(stakes) % 2 != 0 and stakes:
            idx = stakes.index(max(stakes))
            stakes[idx] += 1
        
        match_inv = sum(stakes)
        match_ret = 0
        hit_score = None
        for (sh, sa, o), st in zip(top3, stakes):
            if (sh, sa) == actual_score:
                hit_score = f'{sh}:{sa}'
                match_ret = o * st
                break
        
        all_results.append({
            'month': label, 'match': f'{ht}vs{at}',
            'handicap': hc, 'act_score': f'{hs}:{aw}',
            'direction': pick_dir if actual != '让平' else f'排除(实{actual})',
            'havg': round(havg,1), 'aavg': round(aavg,1),
            'top3': [f'{sh}:{sa}({o})' for sh,sa,o in top3],
            'stakes': stakes, 'invest': round(match_inv, 1),
            'return': round(match_ret, 1),
            'correct': hit_score is not None,
        })

total_inv = sum(r['invest'] for r in all_results)
total_ret = sum(r['return'] for r in all_results)
hits = sum(1 for r in all_results if r['correct'])
roi = (total_ret - total_inv) / total_inv * 100 if total_inv else 0

print(f"{'='*80}")
print(f"让平升赔>8% → 方向+近况加权+跳过世界杯 ROI回测")
print(f"{'='*80}")
print(f"总场次：{len(all_results)}（跳过世界杯/国际赛后）")
print(f"命中场：{hits}（{hits/len(all_results)*100:.1f}%）")
print(f"总投注：{total_inv:.0f}元")
print(f"总回报：{total_ret:.0f}元")
print(f"💰 ROI：{roi:+.1f}%")
print()

for month in ['5月', '6月']:
    ms = [r for r in all_results if r['month'] == month]
    if not ms: continue
    m_inv = sum(r['invest'] for r in ms)
    m_ret = sum(r['return'] for r in ms)
    m_hit = sum(1 for r in ms if r['correct'])
    m_roi = (m_ret - m_inv) / m_inv * 100 if m_inv else 0
    print(f"{month}：{len(ms)}场 命中{m_hit}({m_hit/len(ms)*100:.0f}%) 投{m_inv:.0f} 回{m_ret:.0f} ROI{m_roi:+.1f}%")

print()
print("逐场详情：")
for i, r in enumerate(all_results, 1):
    ic = '✅' if r['correct'] else '❌'
    top3s = ' | '.join(f'{s}({st}元)' for s, st in zip(r['top3'], r['stakes']))
    print(f"{i:2d}. [{r['month']}] {r['match']} 实际{r['act_score']} "
          f"近况{r['havg']}:{r['aavg']} 方向{r['direction']} {ic} {top3s} | 投{r['invest']:.0f}回{r['return']:.0f}")
