import re
import glob

DATA_DIR = 'd:/work/workbuddy/足球预测/分析模板/3.21'

match_ids = [
    '周六001', '周六002', '周六003', '周六004', '周六005',
    '周六006', '周六007', '周六008', '周六009', '周六010',
    '周六011', '周六012', '周六014', '周六015', '周六016',
    '周六017', '周六018', '周六019', '周六020', '周六021',
    '周六022', '周六023', '周六024', '周六025', '周六026',
    '周六027', '周六028', '周六029', '周六030',
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
        
        # 提取近况走势
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
                            'match': f'{home} vs {away}',
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

print('='*100)
print('周六比赛 - 造热嫌疑分析')
print('='*100)

results = []
for mid in match_ids:
    data = extract_data(mid)
    if data:
        confidence = calc_confidence(data['home'], data['draw'], data['away'])
        data['confidence'] = confidence
        
        # 分析造热嫌疑
        reasons = []
        
        # 规律D：置信度64-65% + 造热嫌疑（主降 + 平/客升）
        if 64 <= confidence < 66:
            if data['home_chg'] < 0 and (data['draw_chg'] > 0 or data['away_chg'] > 0):
                reasons.append('规律D:造热主队嫌疑(主降+平/客升)')
            elif data['away_chg'] < 0 and (data['draw_chg'] > 0 or data['home_chg'] > 0):
                reasons.append('规律D:造热客队嫌疑(客降+平/主升)')
        
        # 规律五：主胜升幅>5%
        if data['home_chg'] > 5:
            reasons.append(f'规律五:主胜升幅过大(+{data["home_chg"]:.1f}%)')
        
        # 规律五：客胜升幅>5%
        if data['away_chg'] > 5:
            reasons.append(f'规律五:客胜升幅过大(+{data["away_chg"]:.1f}%)')
        
        # 规律B：主胜大幅上升+客队降水（造热客队）
        if data['home_chg'] > 5 and data['away_chg'] < 0:
            reasons.append('规律B:主升>5%+客降=造热客队')
        
        # 澳门推荐和局 + 平赔上升
        macao = data['macao']
        if '和局' in macao and data['draw_chg'] > 0:
            reasons.append('规律A:澳门推和局+平升')
        
        # 澳门推荐和局 + 平赔下降>3%
        if '和局' in macao and data['draw_chg'] < -3:
            reasons.append('规律二:澳门推和局+平降>3%')
        
        # 客队大升+主队微降
        if data['away_chg'] > 8 and data['home_chg'] > -2:
            reasons.append('客队异常升高')
        
        # 平局大幅上升>5%
        if data['draw_chg'] > 5:
            reasons.append(f'平局异常升高(+{data["draw_chg"]:.1f}%)')
        
        if reasons:
            data['reasons'] = reasons
            results.append(data)

# 输出
print('| 编号 | 对阵 | 置信度 | 澳门心水 | 近况差 | 初盘(胜/平/负) | 即时(胜/平/负) | 变化(主/平/客) | 造热嫌疑 |')
print('|------|------|--------|----------|--------|----------------|----------------|----------------|----------|')

for r in results:
    chg_str = f'主{r["home_chg"]:+.1f}% 平{r["draw_chg"]:+.1f}% 客{r["away_chg"]:+.1f}%'
    reasons_str = ' / '.join(r['reasons'])
    init_str = f"{r['init_home']}/{r['init_draw']}/{r['init_away']}"
    real_str = f"{r['home']}/{r['draw']}/{r['away']}"
    print(f"| {r['id']} | {r['match']} | {r['confidence']:.1f}% | {r['macao']} | {r['form_diff']:+d} | {init_str} | {real_str} | {chg_str} | {reasons_str} |")
