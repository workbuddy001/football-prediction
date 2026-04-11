"""
3.21 比赛分析 - 基于 analyze_319_auto_v6.py 简化版
"""

import re
import glob

DATA_DIR = 'd:/work/workbuddy/足球预测/分析模板/3.21'

# 3.21比赛ID列表
match_ids = [
    "周六001", "周六002", "周六003", "周六004", "周六005",
    "周六006", "周六007", "周六008", "周六009", "周六010",
    "周六011", "周六012", "周六013", "周六014", "周六015",
    "周六016", "周六017", "周六018", "周六019", "周六020",
    "周六021", "周六022", "周六023", "周六024", "周六025",
    "周六026", "周六027", "周六028", "周六029", "周六030",
    "周日001", "周日002", "周日003", "周日004", "周日005",
    "周日006", "周日007", "周日008", "周日009", "周日010",
    "周日011", "周日012", "周日013", "周日014", "周日015",
    "周日016", "周日017", "周日018", "周日019", "周日020",
    "周日021", "周日022", "周日023", "周日024", "周日025",
    "周日026", "周日027", "周日028",
]

def extract_jingcai_odds(match_id):
    """从源数据文件提取竞*官*的初盘和即时赔率"""
    file_path = f"{DATA_DIR}/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return None, None, None, None, None, None
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
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
                        init_home = parts[2]
                        real_home = parts[3]
                        init_draw = parts[5]
                        real_draw = parts[6]
                        init_away = parts[8]
                        real_away = parts[9]
                        try:
                            return (float(init_home), float(init_draw), float(init_away),
                                    float(real_home), float(real_draw), float(real_away))
                        except:
                            pass
        
        return None, None, None, None, None, None
        
    except Exception as e:
        return None, None, None, None, None, None

def extract_macao_tip(match_id):
    """提取澳门推荐"""
    file_path = f"{DATA_DIR}/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return None
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        match = re.search(r'澳门推荐\s*\|\s*([^\n|]+)', content)
        if match:
            return match.group(1).strip()
        
        return None
        
    except Exception as e:
        return None

def extract_match_name(match_id):
    """提取比赛名称"""
    file_path = f"{DATA_DIR}/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return match_id
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        home_match = re.search(r'主队\s*\|\s*([^\n|]+)', content)
        away_match = re.search(r'客队\s*\|\s*([^\n|]+)', content)
        
        home = home_match.group(1).strip() if home_match else "主队"
        away = away_match.group(1).strip() if away_match else "客队"
        
        return f"{home} vs {away}"
        
    except Exception as e:
        return match_id

def extract_form_score(match_id):
    """提取并计算近况评分差"""
    file_path = f"{DATA_DIR}/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return 0
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取主队近况走势
        home_trend_match = re.search(r'主队近况走势\s*\|\s*([^\n|]+)', content)
        away_trend_match = re.search(r'客队近况走势\s*\|\s*([^\n|]+)', content)
        
        home_trend = home_trend_match.group(1).strip() if home_trend_match else ""
        away_trend = away_trend_match.group(1).strip() if away_trend_match else ""
        
        # 计算近况评分
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
        
        home_score = calc_score(home_trend)
        away_score = calc_score(away_trend)
        
        return home_score - away_score
        
    except Exception as e:
        return 0

def fmt_change(init_val, real_val):
    """格式化赔率变化幅度"""
    if init_val is None or real_val is None or init_val == 0:
        return "—"
    pct = (real_val - init_val) / init_val * 100
    if abs(pct) < 0.1:
        return "—"
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"

def calculate_confidence(home, draw, away):
    """计算置信度"""
    total = home + draw + away
    home_rate = (total / home) * 100 / 3
    draw_rate = (total / draw) * 100 / 3
    away_rate = (total / away) * 100 / 3
    total_rate = home_rate + draw_rate + away_rate
    home_rate = home_rate / total_rate * 100
    draw_rate = draw_rate / total_rate * 100
    away_rate = away_rate / total_rate * 100
    max_rate = max(home_rate, draw_rate, away_rate)
    return max_rate, home_rate, draw_rate, away_rate

# 提取所有数据
print("="*120)
print("3.21比赛分析")
print("="*120)

matches_data = {}
for mid in match_ids:
    init_home, init_draw, init_away, real_home, real_draw, real_away = extract_jingcai_odds(mid)
    match_name = extract_match_name(mid)
    macao = extract_macao_tip(mid)
    form_diff = extract_form_score(mid)
    
    if real_home is not None and real_draw is not None and real_away is not None:
        matches_data[mid] = {
            "match": match_name,
            "init_home": init_home, "init_draw": init_draw, "init_away": init_away,
            "home": real_home, "draw": real_draw, "away": real_away,
            "macao": macao,
            "form_diff": form_diff
        }
        print(f"{mid}: {match_name} | 近况差: {form_diff:+d}")
    else:
        print(f"{mid}: 未找到竞彩数据!")

# 生成预测
results = []

for mid, data in matches_data.items():
    home = data['home']
    draw = data['draw']
    away = data['away']
    
    confidence, home_rate, draw_rate, away_rate = calculate_confidence(home, draw, away)
    
    if home_rate >= draw_rate and home_rate >= away_rate:
        odds_pred = "主胜"
    elif away_rate >= home_rate and away_rate >= draw_rate:
        odds_pred = "客胜"
    else:
        odds_pred = "平局"
    
    results.append({
        'id': mid,
        'match': data['match'],
        'init_home': data.get('init_home'), 
        'init_draw': data.get('init_draw'), 
        'init_away': data.get('init_away'),
        'home': home,
        'draw': draw,
        'away': away,
        'confidence': confidence,
        'prediction': odds_pred,
        'macao': data.get('macao'),
        'form_diff': data.get('form_diff', 0),
    })

results.sort(key=lambda x: x['id'])

# 输出完整列表
print("\n" + "="*120)
print("【完整数据列表】")
print("="*120)
print(f"| 编号 | 对阵 | 置信度 | 澳门心水 | 近况差 | 初盘(胜/平/负) | 即时(胜/平/负) | 变化(H/D/A) | 最终预测 |")
print(f"|------|------|--------|----------|--------|----------------|----------------|-------------|----------|")

for r in results:
    init_str = f"{r['init_home']}/{r['init_draw']}/{r['init_away']}" if r['init_home'] else "—"
    real_str = f"{r['home']}/{r['draw']}/{r['away']}"
    chg_h = fmt_change(r['init_home'], r['home'])
    chg_d = fmt_change(r['init_draw'], r['draw'])
    chg_a = fmt_change(r['init_away'], r['away'])
    # 完整变化格式
    chg_full = f"主{chg_h} 平{chg_d} 客{chg_a}"
    macao = r['macao'] or "未知"
    print(f"| {r['id']} | {r['match']} | {r['confidence']:.1f}% | {macao} | {r['form_diff']:+d} | {init_str} | {real_str} | {chg_full} | {r['prediction']} |")

# 汇总
print("\n" + "="*60)
print("【最终预测汇总】")
print("="*60)
for r in results:
    print(f"{r['id']}: {r['match']} → {r['prediction']}")
