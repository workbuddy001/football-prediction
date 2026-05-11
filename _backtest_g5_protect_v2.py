#!/usr/bin/env python3
"""G5 保护方案对比: 无保护 vs 固定4球 vs 三维排除最强信号"""
import json, os, sys, re
for m in list(sys.modules):
    if 'v36_analyzer' in m: del sys.modules[m]
from v36_analyzer import analyze_match
from sporttery_web import _build_change_hitrate, _build_odds_hitrate
_odds_hr = _build_odds_hitrate(); _change_hr = _build_change_hitrate()

def _sf(v):
    try: return float(v)
    except: return 999.0

with open('分析模板/_scores.json','r',encoding='utf-8') as f:
    scores = json.load(f)

records_raw = []
records_fixed4 = []
records_signal = []

for mid, sr in scores.items():
    if '2026-05' not in str(sr.get('record_time','')): continue
    fp = f'sporttery_data/{mid}.json'
    if not os.path.exists(fp): continue
    with open(fp,'r',encoding='utf-8') as f: data = json.load(f)
    data['_odds_hitrate'] = _odds_hr; data['_change_hitrate'] = _change_hr
    try: analysis = analyze_match(data)
    except: continue
    tg = data.get('total_goals',{}) or {}
    g0 = _sf(tg.get('0球',0))
    if g0 < 12: continue
    
    exclusion = analysis.get('exclusion',{})
    st_map = {}; ch_map = {}
    for item in exclusion.get('kept',[]):
        try:
            gn = int(item.get('goal','').replace('球',''))
            st_map[gn] = item.get('status','?')
            mch = re.search(r'变(\d+)%', item.get('detail',''))
            ch_map[gn] = int(mch.group(1))/100 if mch else 0
        except: pass
    
    if st_map.get(5) != '⚠️警惕造热': continue
    
    total = sr['home_score'] + sr['away_score']
    g5_odds = _sf(tg.get('5球',0))
    g4_odds = _sf(tg.get('4球',0))
    home = sr.get('home_team','?')
    away = sr.get('away_team','?')
    score_str = f"{sr['home_score']}:{sr['away_score']}"
    
    # 无保护
    records_raw.append({
        'mid':mid,'home':home,'away':away,'score':score_str,'total':total,
        'hit5':total==5,'g5_odds':g5_odds
    })
    
    # 固定4球保护
    records_fixed4.append({
        'mid':mid,'home':home,'away':away,'score':score_str,'total':total,
        'hit5':total==5,'g5_odds':g5_odds,'hit4':total==4,'g4_odds':g4_odds
    })
    
    # 最强非5球信号保护
    best_goal = None; best_ch = -1; best_label = ''
    priority_st = ['⭐变高共振','✅观察保留','✅保留','🔄矛盾保留']
    for gn, st in st_map.items():
        if gn == 5: continue
        if st in priority_st:
            ch = ch_map.get(gn, 0) or 0
            if st == '⭐变高共振': ch += 0.5
            if ch > best_ch: best_ch = ch; best_goal = gn; best_label = st
    prot_odds = _sf(tg.get(f'{best_goal}球', 0)) if best_goal else 0
    records_signal.append({
        'mid':mid,'home':home,'away':away,'score':score_str,'total':total,
        'hit5':total==5,'g5_odds':g5_odds,
        'prot_goal':best_goal,'hit_prot':total==best_goal,
        'prot_odds':prot_odds,'prot_label':best_label
    })

print(f'G5触发 {len(records_raw)} 场\n')

# === 无保护 ===
n=len(records_raw); inv=n*30; ret=sum(30*r['g5_odds'] for r in records_raw if r['hit5'])
h=sum(1 for r in records_raw if r['hit5'])
print(f'=== 无保护 (30元/场) ===')
print(f'投入{inv}元 回报{ret:.0f}元 ROI={(ret-inv)/inv*100:+.1f}% (中{h}/{n})')
for r in records_raw:
    tag='✅' if r['hit5'] else '❌'
    print(f'  {tag} {r["home"]} {r["score"]} {r["away"]} (总{r["total"]}球, 赔{r["g5_odds"]})')

# === 固定4球 ===
n=len(records_fixed4); inv=n*40; ret=0
for r in records_fixed4:
    if r['hit5']: ret+=30*r['g5_odds']
    if r['hit4']: ret+=10*r['g4_odds']
h5=sum(1 for r in records_fixed4 if r['hit5'])
h4=sum(1 for r in records_fixed4 if r['hit4'])
print(f'\n=== 固定4球保护 (30+10=40元/场) ===')
print(f'投入{inv}元 回报{ret:.0f}元 ROI={(ret-inv)/inv*100:+.1f}% (主中{h5} 护中{h4}/{n})')
for r in records_fixed4:
    tags=[]
    if r['hit5']: tags.append('主中5球')
    if r['hit4']: tags.append('护中4球')
    tag='✅' if tags else '❌'
    print(f'  {tag} {r["home"]} {r["score"]} {r["away"]} (总{r["total"]}球) | 4球赔{r["g4_odds"]} | {" ".join(tags)}')

# === 最强信号 ===
n=len(records_signal); inv=n*40; ret=0
for r in records_signal:
    if r['hit5']: ret+=30*r['g5_odds']
    if r['hit_prot']: ret+=10*r['prot_odds']
h5=sum(1 for r in records_signal if r['hit5'])
hp=sum(1 for r in records_signal if r['hit_prot'] and not r['hit5'])
print(f'\n=== 最强信号保护 (30+10=40元/场) ===')
print(f'投入{inv}元 回报{ret:.0f}元 ROI={(ret-inv)/inv*100:+.1f}% (主中{h5} 护中{hp}/{n})')
for r in records_signal:
    tags=[]
    if r['hit5']: tags.append('主中5球')
    if r['hit_prot']: tags.append(f'护中{r["prot_goal"]}球')
    tag='✅' if tags else '❌'
    print(f'  {tag} {r["home"]} {r["score"]} {r["away"]} (总{r["total"]}球) → 保护={r["prot_goal"]}球({r["prot_label"]},赔{r["prot_odds"]}) | {" ".join(tags)}')
