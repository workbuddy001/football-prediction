#!/usr/bin/env python3
"""批量抓取+分析未赛比赛，输出投注建议"""
import json, os, sys, glob
from datetime import datetime, timedelta

# 清除模块缓存
for m in list(sys.modules):
    if m in ('v36_analyzer', 'ai_reasoning', 'sporttery_web', 'sporttery_api'):
        del sys.modules[m]

from sporttery_api import SportteryAPI

print('🔄 抓取比赛列表...')
api = SportteryAPI()
today = datetime.now().strftime('%Y-%m-%d')
tomorrow = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
list_data = api.get_match_list(today, tomorrow)

matches = []
if isinstance(list_data, dict):
    # API返回 {match_id: {...}, ...} 格式
    for k, v in list_data.items():
        if isinstance(v, dict):
            v['_mid'] = k
            matches.append(v)
print(f'✅ 获取 {len(matches)} 场未赛比赛\n')

# 抓取数据
DATA_DIR = 'sporttery_data'
os.makedirs(DATA_DIR, exist_ok=True)

for m in matches:
    mid = str(m.get('_mid', m.get('matchId', m.get('id', ''))))
    fp = os.path.join(DATA_DIR, f'{mid}.json')
    # 只抓取没有数据的
    if os.path.exists(fp):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                d = json.load(f)
            if d.get('match_info', {}).get('match_num_str'):
                print(f'  ⏭️  {mid} 已有数据')
                continue
        except:
            pass
    print(f'  📥 抓取 {mid}...')
    try:
        api.fetch_and_save(mid)
    except Exception as e:
        print(f'    ❌ 失败: {e}')

print(f'\n🔄 分析中...\n')

# 清除模块缓存重新加载
for m in list(sys.modules):
    if m in ('v36_analyzer', 'ai_reasoning', 'sporttery_web'):
        del sys.modules[m]

from v36_analyzer import analyze_match
from ai_reasoning import compute_betting
from sporttery_web import _build_change_hitrate, _build_odds_hitrate

_oh = _build_odds_hitrate()
_ch = _build_change_hitrate()

files = sorted(glob.glob(f'{DATA_DIR}/20*.json'), key=lambda x: int(os.path.basename(x).replace('.json','')), reverse=True)

# 读取已赛比分
try:
    with open('分析模板/_scores.json', 'r', encoding='utf-8') as f:
        scores = json.load(f)
except:
    scores = {}

signals = {}
for fp in files:
    mid = os.path.basename(fp).replace('.json', '')
    # 跳过已赛
    if mid in scores:
        sr = scores[mid]
        hs = sr.get('home_score')
        if hs is not None and isinstance(hs, (int, float)):
            continue
    
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        continue
    
    if not data.get('match_info', {}).get('match_num_str'):
        continue
    
    data['_odds_hitrate'] = _oh
    data['_change_hitrate'] = _ch
    try:
        analysis = analyze_match(data)
    except:
        continue
    betting = compute_betting(data, analysis)
    rule = betting.get('rule')
    if not rule:
        continue
    
    mi = data.get('match_info', {})
    mid_str = mi.get('match_num_str', mid)
    home = mi.get('home_team', '?')
    away = mi.get('away_team', '?')
    date = mi.get('match_date', '?')
    time = mi.get('match_time', '?')
    stake = betting.get('total_stake', 0)
    summary = betting.get('summary', '?')
    
    signals[mid] = {
        'rule': rule,
        'match': f'{mid_str} {home} vs {away}',
        'datetime': f'{date} {time}',
        'stake': stake,
        'summary': summary,
        'goal_bet': betting.get('goal_bet', {}),
        'score_bets': betting.get('score_bets', []),
    }

# 输出
print(f'{"="*80}')
print(f'扫描 {len(files)} 场，{len(signals)} 个未赛信号触发')
print(f'{"="*80}\n')

if not signals:
    print('当前无未赛信号触发')
    sys.exit(0)

order = ['R0','R1','F','G7','S4','S5','S3','G6','S2','H3','H2','H1','G5','S6','S1','G4','R3','R4']
rule_order = {r: i for i, r in enumerate(order)}

sorted_signals = sorted(signals.items(), key=lambda x: (rule_order.get(x[1]['rule'], 99), x[0]))

total_stake = 0
for mid, s in sorted_signals:
    total_stake += s['stake']
    print(f"[{s['rule']}] {s['match']}")
    print(f"      {s['datetime']} | 投{s['stake']}元 | {s['summary']}")
    gb = s['goal_bet']
    if gb.get('goals'):
        odds_str = str(gb.get('odds', {}))
        print(f"      进球: {gb.get('goals')} 赔{odds_str} 投{gb.get('stake')}元")
    for sb in s['score_bets']:
        print(f"      比分: {sb.get('score')} 赔{sb.get('odds')} 投{sb.get('stake')}元 [{sb.get('tag','')}]")
    print()

print(f'合计: {len(signals)}个信号, 总投入{total_stake}元')
