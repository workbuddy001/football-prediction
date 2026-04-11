# 测试V8在3.15上的表现
import re
import ast
from pathlib import Path
import openpyxl

def parse_315(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    info = {}
    match = re.match(r'.+?(\d+)_(.+?)vs(.+?)_源数据', filepath.stem)
    if match:
        info['match_id'] = f"周日{match.group(1)}"
        info['home_team'] = match.group(2)
        info['away_team'] = match.group(3)
    
    # 近况
    match = re.search(r'主队.*?近况走势.*?([WL]+)', content)
    if match:
        form = match.group(1).upper()
        info['home_w'] = form.count('W')
        info['home_l'] = form.count('L')
    
    match = re.search(r'客队.*?近况走势.*?([WL]+)', content)
    if match:
        form = match.group(1).upper()
        info['away_w'] = form.count('W')
        info['away_l'] = form.count('L')
    
    # 赔率
    initial = []
    match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if match:
        try:
            initial = ast.literal_eval(re.sub(r'#.*', '', '[' + match.group(1) + ']'))
        except:
            pass
    
    realtime = []
    match = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if match:
        try:
            realtime = ast.literal_eval(re.sub(r'#.*', '', '[' + match.group(1) + ']'))
        except:
            pass
    
    info['initial_odds'] = initial
    info['realtime_odds'] = realtime
    
    return info

# V8分析函数
def analyze_v8(info):
    home = info.get('home_team', '')
    away = info.get('away_team', '')
    initial = info.get('initial_odds', [])
    realtime = info.get('realtime_odds', [])
    home_w = info.get('home_w', 0)
    home_l = info.get('home_l', 0)
    away_w = info.get('away_w', 0)
    away_l = info.get('away_l', 0)
    
    if not initial or not realtime:
        return {"预测": "数据不足", "把握度": "D"}
    
    avg_home = sum(x[0] for x in realtime) / len(realtime)
    avg_draw = sum(x[1] for x in realtime) / len(realtime)
    avg_away = sum(x[2] for x in realtime) / len(realtime)
    
    prob_home = (1/avg_home) / (1/avg_home + 1/avg_draw + 1/avg_away)
    prob_draw = (1/avg_draw) / (1/avg_home + 1/avg_draw + 1/avg_away)
    prob_away = (1/avg_away) / (1/avg_home + 1/avg_draw + 1/avg_away)
    
    avg_init_draw = sum(x[1] for x in initial) / len(initial)
    draw_change = (avg_draw - avg_init_draw) / avg_init_draw * 100
    draw_up = sum(1 for i in range(len(initial)) if realtime[i][1] > initial[i][1])
    draw_down_pct = (len(initial) - draw_up) / len(initial) * 100
    
    details = []
    prediction = ""
    confidence = "D"
    
    if avg_away < 1.5:
        prediction = f"{away}客胜"
        confidence = "A"
    elif avg_home < 1.5:
        prediction = f"{home}主胜"
        confidence = "A"
    elif 1.5 < avg_away < 2.0:
        if prob_draw > 0.25 or draw_down_pct > 40:
            prediction = "平局"
            confidence = "C"
        else:
            prediction = f"{away}客胜"
            confidence = "B"
    elif 1.5 < avg_home < 2.0 and home_w >= home_l:
        if prob_draw > 0.28 or draw_down_pct > 45:
            prediction = "平局"
            confidence = "C"
        else:
            prediction = f"{home}主胜"
            confidence = "B"
    elif draw_down_pct > 50 and prob_draw > 0.25:
        prediction = "平局"
        confidence = "C"
    elif prob_draw > 0.30:
        prediction = "平局"
        confidence = "C"
    elif prob_home > 0.55:
        prediction = f"{home}主胜"
        confidence = "B"
    elif prob_away > 0.55:
        prediction = f"{away}客胜"
        confidence = "B"
    else:
        if prob_home > prob_away and prob_home > prob_draw:
            prediction = f"{home}主胜"
        elif prob_away > prob_home and prob_away > prob_draw:
            prediction = f"{away}客胜"
        else:
            prediction = "平局"
    
    return {"预测": prediction, "把握度": confidence}

# 分析3.15
folder = Path("分析模板/3.15")
files = list(folder.glob("*.md"))

results15 = []
for f in files:
    info = parse_315(f)
    if not info.get('home_team') or not info.get('initial_odds'):
        continue
    result = analyze_v8(info)
    results15.append({
        '编号': info.get('match_id'),
        '预测': result['预测'],
        '把握度': result['把握度']
    })

actual_15 = {
    "周日001": "主胜", "周日003": "客胜", "周日004": "平局", "周日006": "客胜",
    "周日007": "客胜", "周日008": "平局", "周日009": "主胜", "周日010": "主胜",
    "周日011": "主胜", "周日012": "平局", "周日013": "平局", "周日014": "主胜",
    "周日015": "主胜", "周日016": "客胜", "周日017": "客胜", "周日018": "主胜",
    "周日019": "主胜", "周日020": "平局", "周日021": "平局", "周日022": "客胜",
    "周日023": "主胜", "周日024": "平局", "周日025": "主胜", "周日026": "主胜",
    "周日027": "主胜", "周日028": "客胜", "周日029": "主胜",
}

def check(p, a):
    p = p.lower()
    if "主胜" in p: return "主胜" == a
    if "客胜" in p: return "客胜" == a
    if "平局" in p: return "平局" == a
    return False

correct15 = sum(1 for r in results15 if check(r['预测'], actual_15.get(r['编号'], '')))
print(f"V8算法 - 3.15准确率: {correct15/29*100:.1f}% ({correct15}/29)")

# 把握度统计
for conf in ['A', 'B', 'C']:
    conf_r = [r for r in results15 if r['把握度'] == conf]
    c = sum(1 for r in conf_r if check(r['预测'], actual_15.get(r['编号'], '')))
    print(f"把握度{conf}: {c}/{len(conf_r)}")
