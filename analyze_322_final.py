import re
import glob

DATA_DIR = 'd:/work/workbuddy/足球预测/分析模板/3.22'

match_ids = [
    '周日001', '周日002', '周日003', '周日004', '周日005',
    '周日006', '周日007', '周日008', '周日010', '周日011',
    '周日012', '周日013', '周日014', '周日015', '周日016',
    '周日017', '周日018', '周日019', '周日020', '周日021',
    '周日022', '周日023', '周日024', '周日025', '周日026',
    '周日027', '周日028',
]

def calc_score(trend):
    if not trend:
        return 0
    score_map = {'W': 3, 'D': 1, 'L': 0, '胜': 3, '平': 1, '负': 0}
    recent = trend[:5] if len(trend) >= 5 else trend
    scores = []
    for i, char in enumerate(recent):
        if char in score_map:
            weight = 2 if i == 0 else 1
            scores.append(score_map[char] * weight)
    return sum(scores) if scores else 0

def extract_data(match_id):
    file_path = f'{DATA_DIR}/{match_id}_*_源数据.md'
    files = glob.glob(file_path)
    if not files:
        return None
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        home_match = re.search(r'主队\s*\|\s*([^\n|]+)', content)
        away_match = re.search(r'客队\s*\|\s*([^\n|]+)', content)
        home = home_match.group(1).strip() if home_match else '主队'
        away = away_match.group(1).strip() if away_match else '客队'
        
        macao_match = re.search(r'澳门推荐\s*\|\s*([^\n|]+)', content)
        macao = macao_match.group(1).strip() if macao_match else '未知'
        
        home_trend_match = re.search(r'主队近况走势\s*\|\s*([^\n|]+)', content)
        away_trend_match = re.search(r'客队近况走势\s*\|\s*([^\n|]+)', content)
        home_trend = home_trend_match.group(1).strip() if home_trend_match else ''
        away_trend = away_trend_match.group(1).strip() if away_trend_match else ''
        
        home_score = calc_score(home_trend)
        away_score = calc_score(away_trend)
        form_diff = home_score - away_score
        
        lines = content.split('\n')
        in_table = False
        for line in lines:
            if '初盘胜' in line and '即时胜' in line:
                in_table = True
                continue
            if in_table:
                if line.startswith('---') or line.startswith('## '):
                    break
                if '竞*官*' in line and '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 10:
                        init_home = float(parts[2])
                        real_home = float(parts[3])
                        init_draw = float(parts[5])
                        real_draw = float(parts[6])
                        init_away = float(parts[8])
                        real_away = float(parts[9])
                        
                        home_chg = (real_home - init_home) / init_home * 100
                        draw_chg = (real_draw - init_draw) / init_draw * 100
                        away_chg = (real_away - init_away) / init_away * 100
                        
                        return {
                            'id': match_id,
                            'match': home + ' vs ' + away,
                            'init_home': init_home, 'init_draw': init_draw, 'init_away': init_away,
                            'home': real_home, 'draw': real_draw, 'away': real_away,
                            'home_chg': home_chg, 'draw_chg': draw_chg, 'away_chg': away_chg,
                            'macao': macao,
                            'form_diff': form_diff
                        }
        return None
    except:
        return None

def calc_confidence(home, draw, away):
    total = home + draw + away
    home_rate = (total / home) * 100 / 3
    draw_rate = (total / draw) * 100 / 3
    away_rate = (total / away) * 100 / 3
    total_rate = home_rate + draw_rate + away_rate
    return max(home_rate/total_rate*100, draw_rate/total_rate*100, away_rate/total_rate*100)

def fmt_chg(v):
    if abs(v) < 0.1:
        return '—'
    return f"{v:+.1f}%"

# 输出标准格式表格
print('## 完整数据列表（标准格式）')
print()
print('| 编号 | 对阵 | 置信度 | 澳门心水 | 近况差 | 初盘(胜/平/负) | 即时(胜/平/负) | 变化(H/D/A) | 最终预测 |')
print('|------|------|--------|----------|--------|----------------|----------------|-------------|----------|')

results = []
for mid in match_ids:
    data = extract_data(mid)
    if data:
        confidence = calc_confidence(data['home'], data['draw'], data['away'])
        data['confidence'] = confidence
        
        # 最终预测
        if data['home'] <= data['draw'] and data['home'] <= data['away']:
            prediction = '主胜'
        elif data['away'] <= data['home'] and data['away'] <= data['draw']:
            prediction = '客胜'
        else:
            prediction = '平局'
        
        data['prediction'] = prediction
        results.append(data)
        
        # 输出表格行
        init_str = f"{data['init_home']}/{data['init_draw']}/{data['init_away']}"
        real_str = f"{data['home']}/{data['draw']}/{data['away']}"
        chg_str = f"主{fmt_chg(data['home_chg'])} 平{fmt_chg(data['draw_chg'])} 客{fmt_chg(data['away_chg'])}"
        macao = data['macao'] if data['macao'] else '未知'
        
        print(f"| {data['id']} | {data['match']} | {confidence:.1f}% | {macao} | {data['form_diff']:+d} | {init_str} | {real_str} | {chg_str} | {prediction} |")

print()
print('---')
print()
print('### 近况评分计算方法')
print()
print('- **权重**：最近一场×2，其他4场×1（共6场权重）')
print('- **得分**：赢=3分，平=1分，输=0分')
print('- **满分**：3×2 + 3×4 = 18分')
print('- **近况差** = 主队得分 - 客队得分')

# ====== 二次审核 ======
print()
print('='*80)
print('二次审核 - 最稳的比赛（经memory规律审核）')
print('='*80)

# 最稳的比赛：置信度>=66%
stable = [r for r in results if r['confidence'] >= 66]
stable.sort(key=lambda x: -x['confidence'])

if stable:
    print('| 编号 | 对阵 | 置信度 | 澳门心水 | 近况差 | 变化(H/D/A) | 修正预测 | 规律依据 |')
    print('|------|------|--------|----------|--------|-------------|----------|----------|')
    for r in stable:
        chg_str = f"主{fmt_chg(r['home_chg'])} 平{fmt_chg(r['draw_chg'])} 客{fmt_chg(r['away_chg'])}"
        reasons = []
        if r['confidence'] >= 66:
            if '赢' in r['macao']:
                reasons.append('规律一>=66%')
            elif '和局' in r['macao']:
                reasons.append('规律一>=66%')
        
        # 规律G：大胜条件
        if r['confidence'] >= 66:
            if abs(r['home_chg']) < 2 and abs(r['form_diff']) >= 5:
                reasons.append('规律G:大胜')
            elif 2 <= abs(r['home_chg']) <= 5:
                reasons.append('规律G:小胜')
        
        reason_str = ' / '.join(reasons) if reasons else '规律一'
        print(f"| {r['id']} | {r['match']} | {r['confidence']:.1f}% | {r['macao']} | {r['form_diff']:+d} | {chg_str} | {r['prediction']} | {reason_str} |")

print()
print('='*80)
print('二次审核 - 最可能爆冷的比赛（经memory规律审核）')
print('='*80)

# 可能爆冷
risky = []
for r in results:
    if r['confidence'] < 55:
        reasons = []
        # 规律二：澳门推平局 + 平赔<3.0
        if '和局' in r['macao'] and r['draw'] < 3.0:
            reasons.append('规律二:平<3.0')
        # 规律二：澳门推平局 + 平降>5%
        if '和局' in r['macao'] and r['draw_chg'] < -5:
            reasons.append('规律二:平降>5%')
        # 规律三：低置信度
        if r['confidence'] <= 40:
            reasons.append('规律三:低置信度')
        # 规律五：主胜升幅>5%
        if r['home_chg'] > 5:
            reasons.append(f'规律五:主升>{r["home_chg"]:.1f}%')
        # 规律五：客胜升幅>5%
        if r['away_chg'] > 5:
            reasons.append(f'规律五:客升>{r["away_chg"]:.1f}%')
        
        if reasons:
            r['reasons'] = reasons
            risky.append(r)
    elif r['confidence'] >= 55 and r['confidence'] < 66:
        # 55-66之间有问题的
        reasons = []
        if r['home_chg'] > 5:
            reasons.append(f'规律五:主升>{r["home_chg"]:.1f}%')
        if r['away_chg'] > 5:
            reasons.append(f'规律五:客升>{r["away_chg"]:.1f}%')
        if '和局' in r['macao'] and r['draw'] < 3.0:
            reasons.append('规律二:平<3.0')
        if reasons:
            r['reasons'] = reasons
            risky.append(r)

risky.sort(key=lambda x: x['confidence'])

if risky:
    print('| 编号 | 对阵 | 置信度 | 澳门心水 | 变化(H/D/A) | 问题 | 修正预测 |')
    print('|------|------|--------|----------|-------------|------|----------|')
    for r in risky:
        chg_str = f"主{fmt_chg(r['home_chg'])} 平{fmt_chg(r['draw_chg'])} 客{fmt_chg(r['away_chg'])}"
        reasons_str = ' / '.join(r.get('reasons', []))
        
        # 修正预测
        correction = r['prediction']
        if '规律二:平<3.0' in reasons_str or '规律二:平降>5%' in reasons_str:
            # 平局难出，按原始方向
            if r['home'] < r['away']:
                correction = '主胜'
            else:
                correction = '客胜'
        elif '规律五:主升' in reasons_str:
            correction = '和局'
        elif '规律三:低置信度' in reasons_str:
            # 顺赔率变动
            if r['home_chg'] < 0 and r['away_chg'] > 0:
                correction = '主胜'
            elif r['away_chg'] < 0 and r['home_chg'] > 0:
                correction = '客胜'
        
        print(f"| {r['id']} | {r['match']} | {r['confidence']:.1f}% | {r['macao']} | {chg_str} | {reasons_str} | {correction} |")
