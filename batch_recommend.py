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
    date = mi.get('match_date', '')
    time = mi.get('match_time', '')
    # 从match数据补充时间
    if not date:
        mdata = data.get('match', data.get('match_data', {}))
        if isinstance(mdata, dict):
            date = mdata.get('matchDate', mdata.get('match_date', ''))
            time = mdata.get('matchTime', mdata.get('match_time', ''))
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
        '_date': date,
        '_time': time,
    }

# 输出 - 按时间规则过滤
from datetime import datetime as dt

# 1. 今天周几
weekday_cn = ['周一','周二','周三','周四','周五','周六','周日']
today_idx = dt.now().weekday()
today_wd = weekday_cn[today_idx]
now = dt.now()

print(f'{"="*80}')
print(f'📅 今天 {today_wd} | 当前 {now.strftime("%H:%M")} | 扫描 {len(files)} 场 → {len(signals)} 个信号')
print(f'{"="*80}\n')

# 2. 只保留今天的比赛
today_signals = {}
for mid, s in signals.items():
    match_str = s['match']
    if match_str.startswith(today_wd):
        today_signals[mid] = s

if not today_signals:
    print(f'今天({today_wd})无触发信号')
    sys.exit(0)

# 3. 分类：临场 / 今日 / 已过期
HOT_MINUTES = 60  # 1小时内=重点
CUTOFF_HOUR = 21   # 21点截止

hot_signals = {}   # 🔥临场
live_signals = {}  # 今天剩余
cutoff_signals = {} # 21点后剩余

for mid, s in today_signals.items():
    dt_str = f"{s.get('_date','')} {s.get('_time','')}"
    try:
        # 尝试多种格式
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
            try:
                match_dt = dt.strptime(dt_str.strip(), fmt)
                break
            except: continue
        else:
            match_dt = None
    except:
        match_dt = None
    
    if match_dt is None:
        live_signals[mid] = s
        continue
    
    diff_min = (match_dt - now).total_seconds() / 60
    
    if diff_min < 0:
        continue  # 已开赛，跳过
    
    if now.hour >= CUTOFF_HOUR:
        cutoff_signals[mid] = s
    elif diff_min <= HOT_MINUTES:
        hot_signals[mid] = s
    else:
        live_signals[mid] = s

# 4. 排序输出
order = ['R0','R1','F','G7','S4','S5','S3','G6','S2','H3','H2','H1','G5','S6','S1','G4','R3','R4']
rule_order = {r: i for i, r in enumerate(order)}

total_stake = 0

def print_section(title, signals_dict, emoji='📌'):
    global total_stake
    if not signals_dict:
        return
    sorted_s = sorted(signals_dict.items(), key=lambda x: (rule_order.get(x[1]['rule'], 99), x[0]))
    print(f'{emoji} {title} ({len(sorted_s)}场):')
    for mid, s in sorted_s:
        total_stake += s['stake']
        dt_display = s['datetime'] if s['datetime'].strip() else s['match']
        dt_short = dt_display.replace('2026-05-17 ','').replace(':00','')[:8]
        print(f"  [{s['rule']}] {s['match']}")
        print(f"        ⏰ {dt_short} | 投{s['stake']}元 | {s['summary']}")
        gb = s['goal_bet']
        if gb.get('goals'):
            print(f"        进球: {gb.get('goals')} 赔{gb.get('odds')} 投{gb.get('stake')}元")
        for sb in s['score_bets']:
            print(f"        比分: {sb.get('score')} 赔{sb.get('odds')} 投{sb.get('stake')}元 [{sb.get('tag','')}]")
    print()

if hot_signals:
    print_section('🔥 临场重点（1小时内开赛）', hot_signals, '🔥')
if live_signals:
    print_section('📌 今日推荐', live_signals)
if cutoff_signals:
    print(f'⏰ 当前已过21:00截止，剩余可投场次:')
    print_section('📌 今日剩余', cutoff_signals)

print(f'💰 今日总投入: {total_stake}元 (共{len(hot_signals)+len(live_signals)+len(cutoff_signals)}个信号)')
