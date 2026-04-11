"""
3.19 比赛 - 完整预测列表（从源数据自动提取"竞*官*"的初盘+即时赔率）
"""

import os
import re
import glob

DATA_DIR = "d:/work/workbuddy/足球预测/分析模板/3.26"

def extract_jingcai_odds(match_id):
    """从源数据文件提取"竞*官*"的初盘和即时赔率（第五部分表格）
    返回: (初盘主, 初盘平, 初盘客, 即时主, 即时平, 即时客)
    """
    file_path = f"{DATA_DIR}/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return None, None, None, None, None, None
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找第五部分"赔率变动对比"表格中的"竞*官*"行
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
                    # 实际parts: ['', '竞*官*', '初盘胜', '即时胜', '变动', '初盘平', '即时平', '变动', '初盘负', '即时负', '变动', '']
                    # 索引:        0     1          2         3        4      5         6        7      8         9        10      11
                    if len(parts) >= 10:
                        init_home = parts[2]  # 初盘胜
                        real_home = parts[3]  # 即时胜
                        init_draw = parts[5]  # 初盘平
                        real_draw = parts[6]  # 即时平
                        init_away = parts[8]  # 初盘负
                        real_away = parts[9]  # 即时负
                        try:
                            return (float(init_home), float(init_draw), float(init_away),
                                    float(real_home), float(real_draw), float(real_away))
                        except:
                            pass
        
        return None, None, None, None, None, None
        
    except Exception as e:
        print(f"读取{match_id}竞彩赔率出错: {e}")
        return None, None, None, None, None, None


def fmt_change(init_val, real_val):
    """格式化赔率变化幅度，如 +3.5% 或 -8.2%"""
    if init_val is None or real_val is None or init_val == 0:
        return "—"
    pct = (real_val - init_val) / init_val * 100
    if abs(pct) < 0.1:
        return "—"
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"

def extract_macao_tip(match_id):
    """从源数据文件提取澳门推荐"""
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
    """从源数据文件提取比赛名称"""
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

# 比赛ID列表（3.26周四）
match_ids = [
    "周四001", "周四002", "周四003", "周四004", "周四005",
    "周四006", "周四007", "周四008", "周四009", "周四010",
]

# 自动提取所有比赛的竞彩赔率
matches_data = {}
for mid in match_ids:
    init_home, init_draw, init_away, real_home, real_draw, real_away = extract_jingcai_odds(mid)
    match_name = extract_match_name(mid)
    macao = extract_macao_tip(mid)
    
    if real_home is not None and real_draw is not None and real_away is not None:
        matches_data[mid] = {
            "match": match_name,
            "init_home": init_home, "init_draw": init_draw, "init_away": init_away,
            "home": real_home, "draw": real_draw, "away": real_away,
            "macao": macao
        }
        print(f"{mid}: 初盘{init_home}/{init_draw}/{init_away} → 即时{real_home}/{real_draw}/{real_away} | 澳门: {macao}")
    else:
        print(f"{mid}: 未找到竞彩数据!")

# 实际实力（手动补充）
strength_info = {
    "周四001": "客强很多", "周四002": "接近", "周四003": "主强", "周四004": "接近",
    "周四005": "客强", "周四006": "主强", "周四007": "主强", "周四008": "主强",
    "周四009": "主强", "周四010": "接近", "周五001": "接近", "周五002": "主强",
    "周五003": "接近", "周五004": "客强", "周五005": "主强", "周五006": "客强",
    "周五007": "接近", "周五008": "主强", "周五009": "主强", "周五010": "主强",
    "周五011": "接近", "周五012": "主强", "周五013": "客强", "周五014": "接近",
    "周五015": "接近", "周五016": "接近",
}

def extract_odds_change(match_id):
    """从源数据文件提取完整的赔率变化统计"""
    file_path = f"{DATA_DIR}/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return {"home": {"down": 0, "same": 0, "up": 0}, "draw": {"down": 0, "same": 0, "up": 0}, "away": {"down": 0, "same": 0, "up": 0}, "total": 30}
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        stats = {"home": {"down": 0, "same": 0, "up": 0}, "draw": {"down": 0, "same": 0, "up": 0}, "away": {"down": 0, "same": 0, "up": 0}, "total": 0}
        
        lines = content.split('\n')
        in_table = False
        for line in lines:
            if '初盘胜' in line and '即时胜' in line:
                in_table = True
                continue
            if in_table:
                if line.startswith('---') or line.startswith('>'):
                    break
                if '|' in line and ('↓' in line or '↑' in line or '—' in line):
                    parts = [p.strip() for p in line.split('|')]
                    home_change = parts[4] if len(parts) > 4 else ""
                    draw_change = parts[7] if len(parts) > 7 else ""
                    away_change = parts[10] if len(parts) > 10 else ""
                    
                    if '↓' in home_change:
                        stats["home"]["down"] += 1
                    elif '↑' in home_change:
                        stats["home"]["up"] += 1
                    else:
                        stats["home"]["same"] += 1
                    
                    if '↓' in draw_change:
                        stats["draw"]["down"] += 1
                    elif '↑' in draw_change:
                        stats["draw"]["up"] += 1
                    else:
                        stats["draw"]["same"] += 1
                    
                    if '↓' in away_change:
                        stats["away"]["down"] += 1
                    elif '↑' in away_change:
                        stats["away"]["up"] += 1
                    else:
                        stats["away"]["same"] += 1
        
        stats["total"] = stats["home"]["down"] + stats["home"]["same"] + stats["home"]["up"]
        if stats["total"] == 0:
            stats["total"] = 30
            
        return stats
        
    except Exception as e:
        print(f"读取{match_id}赔率变化出错: {e}")
        return {"home": {"down": 0, "same": 0, "up": 0}, "draw": {"down": 0, "same": 0, "up": 0}, "away": {"down": 0, "same": 0, "up": 0}, "total": 30}

def calculate_8_change(match_id):
    """从源数据文件读取并计算8变化"""
    file_path = f"{DATA_DIR}/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return [0, 0, 0]
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        initial_odds = []
        match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match:
            odds_str = match.group(1)
            for line in odds_str.split('\n'):
                nums = re.findall(r'\d+\.\d+', line)
                if len(nums) >= 3:
                    initial_odds.append((float(nums[0]), float(nums[1]), float(nums[2])))
        
        realtime_odds = []
        match = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match:
            odds_str = match.group(1)
            for line in odds_str.split('\n'):
                nums = re.findall(r'\d+\.\d+', line)
                if len(nums) >= 3:
                    realtime_odds.append((float(nums[0]), float(nums[1]), float(nums[2])))
        
        if not initial_odds or not realtime_odds:
            return [0, 0, 0]
        
        initial_under_8 = [0, 0, 0]
        realtime_under_8 = [0, 0, 0]
        
        for odds in initial_odds:
            if odds[0] < 8: initial_under_8[0] += 1
            if odds[1] < 8: initial_under_8[1] += 1
            if odds[2] < 8: initial_under_8[2] += 1
        
        for odds in realtime_odds:
            if odds[0] < 8: realtime_under_8[0] += 1
            if odds[1] < 8: realtime_under_8[1] += 1
            if odds[2] < 8: realtime_under_8[2] += 1
        
        change = [
            realtime_under_8[0] - initial_under_8[0],
            realtime_under_8[1] - initial_under_8[1],
            realtime_under_8[2] - initial_under_8[2]
        ]
        
        return change
        
    except Exception as e:
        return [0, 0, 0]

def calculate_confidence(home, draw, away):
    """计算置信度和各选项概率"""
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

def format_odds_change_pct(stats):
    """格式化赔率变化为百分比"""
    total = stats.get("total", 30)
    if total == 0:
        total = 30
    
    h = stats["home"]
    d = stats["draw"]
    a = stats["away"]
    
    h_down = h['down'] / total * 100
    h_same = h['same'] / total * 100
    h_up = h['up'] / total * 100
    d_down = d['down'] / total * 100
    d_same = d['same'] / total * 100
    d_up = d['up'] / total * 100
    a_down = a['down'] / total * 100
    a_same = a['same'] / total * 100
    a_up = a['up'] / total * 100
    
    return f"主{int(h_down)}/{int(h_same)}/{int(h_up)} 平{int(d_down)}/{int(d_same)}/{int(d_up)} 客{int(a_down)}/{int(a_same)}/{int(a_up)}"

# 生成预测结果
results = []

for mid, data in matches_data.items():
    home = data['home']
    draw = data['draw']
    away = data['away']
    
    confidence, home_rate, draw_rate, away_rate = calculate_confidence(home, draw, away)
    
    # 根据概率确定预测
    if home_rate >= draw_rate and home_rate >= away_rate:
        odds_pred = "主胜"
    elif away_rate >= home_rate and away_rate >= draw_rate:
        odds_pred = "客胜"
    else:
        odds_pred = "平局"
    
    rate_diff = home_rate - away_rate
    
    if confidence > 0:
        deviation = abs(rate_diff) / confidence
    else:
        deviation = 0
    
    # 实际实力修正
    strength = strength_info.get(mid, "接近")
    if "客强" in strength and odds_pred == "主胜":
        final_pred = "客胜"
    elif "主强" in strength and odds_pred == "客胜":
        final_pred = "主胜"
    else:
        final_pred = odds_pred
    
    # 偏离类型
    if deviation > 0.7:
        deviation_type = "偏离过高"
    elif deviation < 0.3:
        deviation_type = "偏离过低"
    else:
        deviation_type = "正常"
    
    # 8变化
    eight_change = calculate_8_change(mid)
    
    # 8中庸
    total_change = abs(eight_change[0]) + abs(eight_change[1]) + abs(eight_change[2])
    is_8_zhongyong = total_change <= 3
    
    # 澳门推荐
    macao = data.get('macao', '-')
    
    # 赔率变化
    odds_stats = extract_odds_change(mid)
    odds_change = format_odds_change_pct(odds_stats)
    
    # 计算赔率变化百分比（供规律使用）
    init_h_val = data.get('init_home') or 0
    init_d_val = data.get('init_draw') or 0
    init_a_val = data.get('init_away') or 0
    pct_h = (home - init_h_val) / init_h_val * 100 if init_h_val else 0
    pct_d = (draw - init_d_val) / init_d_val * 100 if init_d_val else 0
    pct_a = (away - init_a_val) / init_a_val * 100 if init_a_val else 0

    # 规律一标注：澳门推分胜负 + 置信度是否≥66%
    macao_str = macao or ''
    macao_is_draw = '和局' in macao_str
    rule1_tag = ""
    if not macao_is_draw:
        if confidence >= 66:
            rule1_tag = "[规律一:可信>=66%]"
        elif confidence >= 55:
            rule1_tag = "[规律一:慎55~65%]"
        else:
            rule1_tag = "[规律一:高危<55%]"
    
    # 规律三标注：置信度≤40%的2-3-2架构比赛
    # 注意：pct_h, pct_d, pct_a 已在上面370-372行定义
    rule3_tag = ""
    is_low_confidence = confidence <= 40
    if is_low_confidence:
        # 判断澳门心水方向（直接使用已定义的pct_h, pct_d, pct_a）
        macao_home = False
        macao_away = False
        vs_pos = data['match'].find(' vs ')
        if vs_pos > 0:
            macao_home_team = data['match'][:vs_pos].strip()
            macao_away_team = data['match'][vs_pos+4:].strip()
            if macao and macao_home_team:
                macao_home = macao_home_team in macao
            if macao and macao_away_team:
                macao_away = macao_away_team in macao
        
        # ====== 先判断规律二：澳门推平局 ======
        if macao_is_draw:
            # 规律二：平局初始<3.0 或 下降>5% → 平局难出
            init_d_val = data.get('init_draw') or 0
            draw_hard = False
            if init_d_val > 0 and init_d_val < 3.0:
                draw_hard = True
            elif pct_d < -5.0:
                draw_hard = True
            
            if draw_hard:
                rule3_tag = "[规律三:平局难出]"
            else:
                rule3_tag = "[规律三:平局可出]"
        else:
            # 澳门未推荐和局，继续规律三判断
            # 顺赔率变动 + 造热排除澳门
            change_direction = ""
            if pct_h < pct_d and pct_h < pct_a:
                change_direction = "主降"
            elif pct_a < pct_h and pct_a < pct_d:
                change_direction = "客降"
            elif pct_d < pct_h and pct_d < pct_a:
                change_direction = "平降"
            
            # 造热澳门判断
            is_zaore = False
            if macao_home and pct_h < -3:  # 主降=造热主队
                is_zaore = True
            elif macao_away and pct_a < -3:  # 客降=造热客队
                is_zaore = True
            elif macao_is_draw and pct_d < -3:  # 平降=造热平局
                is_zaore = True
            
            if is_zaore:
                rule3_tag = "[规律三:造热排除澳门]"
            else:
                rule3_tag = "[规律三:顺赔率变动]"

    results.append({
        'id': mid,
        'match': data['match'],
        'init_home': data.get('init_home'), 'init_draw': data.get('init_draw'), 'init_away': data.get('init_away'),
        'home': home,
        'draw': draw,
        'away': away,
        'confidence': confidence,
        'home_rate': home_rate,
        'draw_rate': draw_rate,
        'away_rate': away_rate,
        'rate_diff': rate_diff,
        'deviation': deviation,
        'deviation_type': deviation_type,
        'prediction': final_pred,
        'eight_change': eight_change,
        'is_8_zhongyong': is_8_zhongyong,
        'macao': macao,
        'odds_change': odds_change,
        'pct_change': [pct_h, pct_d, pct_a],
        'rule1_tag': rule1_tag,
        'rule3_tag': rule3_tag,
        'is_low_confidence': is_low_confidence,
    })

results.sort(key=lambda x: x['id'])

# ====== 双选建议计算 ======
def get_double_choice(r):
    """计算双选建议 - 基于平局是否能被排除的客观分析
    返回: (双选建议, 是否强烈建议)
    """
    pred = r['prediction']
    confidence = r['confidence']
    pct_h = r['pct_change'][0]
    pct_d = r['pct_change'][1]
    pct_a = r['pct_change'][2]
    macao = r.get('macao', '')
    macao_draw = '和局' in macao
    
    # 提取主客队名
    match = r['match']
    vs_pos = match.find(' vs ')
    if vs_pos > 0:
        home_team = match[:vs_pos].strip()
        away_team = match[vs_pos+4:].strip()
    else:
        home_team = ""
        away_team = ""
    
    # 获取初始平局赔率
    init_d_val = r.get('init_draw', 0)
    
    # 判断澳门方向
    macao_home = home_team in macao or (home_team.replace('FC', '') in macao)
    macao_away = away_team in macao or (away_team.replace('FC', '') in macao)
    
    double_choice = ""
    strongRecommend = False
    
    # ====== 第一步：判断平局是否可以被排除 ======
    # 规律二：平局难出条件
    draw_can_exclude = False
    
    if init_d_val > 0 and init_d_val < 3.0:
        # 条件1：平局初始赔率 < 3.0 → 平局难出
        draw_can_exclude = True
    elif pct_d < -5.0:
        # 条件2：平局赔率下降 > 5% → 平局难出
        draw_can_exclude = True
    elif macao_draw and pct_d > 3.0:
        # 条件3：澳门推荐和局 + 平赔上升 > 3% → 平局难出（规律A）
        draw_can_exclude = True
    
    # ====== 第二步：检查特殊造热条件 ======
    # 客胜大幅上升 > 8% → 造热/赶盘，需要双选防冷
    # 澳门推荐主胜 + 主胜下降 + 客胜上升>8% → 造热主队嫌疑，主胜难出
    # 置信度<68%时触发，置信度>=68%可能打出
    if macao_home and pct_h < 0 and pct_a > 8.0 and confidence < 68:
        # 澳门推荐主胜 + 主胜下降 + 客胜大幅上升 = 造热主队
        # 预测反向：和局或客胜
        if pred == "主胜":
            double_choice = "和/客"
            strongRecommend = True
    elif pct_a > 8.0 and confidence < 68:
        # 客胜大幅上升 = 赶盘信号，但往往出意外，需双选
        if pred == "主胜":
            double_choice = "主/和"
            strongRecommend = True
        elif pred == "客胜":
            double_choice = "和/客"
            strongRecommend = True
    
    # ====== 第三步：根据平局排除结果决定 ======
    elif draw_can_exclude:
        # 平局可以被排除 → 单选即可，不需要双选
        double_choice = ""
        strongRecommend = False
    else:
        # 平局难以被排除 → 建议双选
        # 规律F：置信度41-55% + 澳门推和局 + 平赔3.5-3.7小降 → 平局可出
        if macao_draw and 41 <= confidence <= 55 and 3.5 <= init_d_val <= 3.7 and -3 < pct_d < 0:
            # 规律F明确指出平局可出，必须双选
            if pred == "主胜":
                double_choice = "主/和"
                strongRecommend = True
            elif pred == "客胜":
                double_choice = "客/和"
                strongRecommend = True
        elif macao_draw:
            # 澳门推荐和局，但平局未被排除 → 建议双选防平
            if pred == "主胜":
                double_choice = "主/和"
                strongRecommend = True
            elif pred == "客胜":
                double_choice = "客/和"
                strongRecommend = True
        elif 55 <= confidence < 66:
            # 置信度55-65%接近66%但未达 → 建议双选防平
            if pred == "主胜":
                double_choice = "主/和"
                strongRecommend = True
            elif pred == "客胜":
                double_choice = "客/和"
                strongRecommend = True
        elif confidence < 50:
            # 低置信度 + 非澳门推和局 → 视情况双选
            if pred == "主胜":
                double_choice = "主/和"
                strongRecommend = True
            elif pred == "客胜":
                double_choice = "客/和"
                strongRecommend = True
    
    # 稳胆比赛不需要双选
    if confidence >= 66:
        double_choice = ""
        strongRecommend = False
    
    return double_choice, strongRecommend

# 为所有比赛计算双选建议
for r in results:
    double_choice, strong = get_double_choice(r)
    r['double_choice'] = double_choice
    r['double_choice_strong'] = strong

# ====== 过热检测 ======
# 逻辑：澳门推荐方向与预测一致 + 赔率变化幅度>3%倾向澳门方向 = 过热
OVERHEAT_THRESHOLD = 3.0  # 3%

def is_overheated(r):
    """检测是否过热：澳门同向 + 赔率大幅变化(无论升或降)>5%
    澳门推荐判断：澳门推荐文字中包含主队或客队名（模糊匹配）
    """
    if not r.get('macao') or not r['init_home']:
        return False, ""
    
    macao = r['macao'].replace('贏', '赢').replace(' 贏', ' 赢')
    pred = r['prediction']
    init_h, init_d, init_a = r['init_home'], r['init_draw'], r['init_away']
    real_h, real_d, real_a = r['home'], r['draw'], r['away']
    
    # 计算变化百分比
    pct_h = (real_h - init_h) / init_h * 100 if init_h else 0
    pct_d = (real_d - init_d) / init_d * 100 if init_d else 0
    pct_a = (real_a - init_a) / init_a * 100 if init_a else 0
    
    # 从比赛名称提取主客队（用于模糊匹配）
    vs_pos = r['match'].find(' vs ')
    if vs_pos > 0:
        macao_home_team = r['match'][:vs_pos].strip()
        macao_away_team = r['match'][vs_pos+4:].strip()
    else:
        macao_home_team = ""
        macao_away_team = ""
    
    # 澳门方向判断：模糊匹配（澳门推荐文字包含主队或客队名的任意部分）
    # 例如："墨尔本胜利" 包含 "墨胜利" / "巴塞罗那" 包含 "巴萨"
    def is_macao_home(macao_str, team_name):
        if not team_name:
            return False
        # 检查澳门推荐是否包含队伍名的任意2个连续字符（避免太严格）
        for i in range(len(team_name)):
            for j in range(i+2, len(team_name)+1):
                if team_name[i:j] in macao_str:
                    return True
        return False
    
    macao_home = is_macao_home(macao, macao_home_team) or is_macao_home(macao, macao_away_team.replace('FC', '').replace(' ', ''))
    macao_away = is_macao_home(macao, macao_away_team) or is_macao_home(macao, macao_home_team.replace('FC', '').replace(' ', ''))
    # 修正：需要分开判断
    macao_home = is_macao_home(macao, macao_home_team)
    macao_away = is_macao_home(macao, macao_away_team)
    macao_draw = '和局' in macao
    
    reason = ""
    warn_type = ""  # 过热/反向
    
    # 过热/反向检测：澳门同向 + 三个赔率中任意一个变化>8%
    # 过热 = 该方向赔率下降（市场一边倒）
    # 反向 = 该方向赔率上升（庄家抬价赶盘）
    
    big_change_threshold = 8.0  # 大幅变化阈值
    
    # 核心逻辑：
    # 1. 预测方向赔率上升 → 反向操作（庄家赶盘）→ 可能打出
    # 2. 预测方向赔率下降 → 市场过热 → 爆冷
    # 3. 非预测方向大幅变化 → 资金流向对家 → 也需警惕
    
    if pred == "主胜" and macao_home:
        # 预测方向（主胜）变化
        if abs(pct_h) > big_change_threshold:
            reason = f"主胜{'降' if pct_h < 0 else '升'}{abs(pct_h):.1f}%"
            warn_type = "过热" if pct_h < 0 else "反向"
        # 非预测方向大幅变化
        elif abs(pct_d) > big_change_threshold:
            reason = f"平局{'升' if pct_d > 0 else '降'}{abs(pct_d):.1f}%"
            warn_type = "警惕"
        elif abs(pct_a) > big_change_threshold:
            reason = f"客胜{'升' if pct_a > 0 else '降'}{abs(pct_a):.1f}%"
            warn_type = "警惕"
    
    elif pred == "客胜" and macao_away:
        if abs(pct_a) > big_change_threshold:
            reason = f"客胜{'降' if pct_a < 0 else '升'}{abs(pct_a):.1f}%"
            warn_type = "过热" if pct_a < 0 else "反向"
        elif abs(pct_d) > big_change_threshold:
            reason = f"平局{'升' if pct_d > 0 else '降'}{abs(pct_d):.1f}%"
            warn_type = "警惕"
        elif abs(pct_h) > big_change_threshold:
            reason = f"主胜{'升' if pct_h > 0 else '降'}{abs(pct_h):.1f}%"
            warn_type = "警惕"
    
    elif pred == "和局" and macao_draw:
        if abs(pct_d) > big_change_threshold:
            reason = f"平局{'降' if pct_d < 0 else '升'}{abs(pct_d):.1f}%"
            warn_type = "过热" if pct_d < 0 else "反向"
        elif abs(pct_h) > big_change_threshold:
            reason = f"主胜{'升' if pct_h > 0 else '降'}{abs(pct_h):.1f}%"
            warn_type = "警惕"
        elif abs(pct_a) > big_change_threshold:
            reason = f"客胜{'升' if pct_a > 0 else '降'}{abs(pct_a):.1f}%"
            warn_type = "警惕"
    
    if reason:
        r['warn_type'] = warn_type
        return True, reason
    
    # ====== 新增检测：正常偏离中的异常情况 ======
    
    # 情况1：澳门推荐和局（平局赛）→ 规律二检测
    # 规律二：平局初始赔率<3.0 或 平局赔率大幅下降>5% → 平局难出
    if macao_draw:
        draw_hard = False
        draw_hard_reason = ""
        init_d_val = r.get('init_draw') or 0

        if init_d_val > 0 and init_d_val < 3.0:
            draw_hard = True
            draw_hard_reason = f"平局初始赔率{init_d_val}低于3.0→平局难出"
        elif pct_d < -5.0:
            draw_hard = True
            draw_hard_reason = f"平局赔率大幅下降{pct_d:.1f}%→平局难出"

        if draw_hard:
            reason = draw_hard_reason
            warn_type = "平局难出"
        elif pred != "和局" and abs(pct_d) > 3.0:
            reason = f"澳门推荐和局但平局{'降' if pct_d < 0 else '升'}{abs(pct_d):.1f}%"
            warn_type = "警惕"
    
    # 情况2：任意方向变化>8%（不局限于澳门同向）
    if not reason:
        max_change = max(abs(pct_h), abs(pct_d), abs(pct_a))
        if max_change > 8.0:
            if abs(pct_h) == max_change:
                reason = f"主胜{'升' if pct_h > 0 else '降'}{abs(pct_h):.1f}%"
            elif abs(pct_d) == max_change:
                reason = f"平局{'升' if pct_d > 0 else '降'}{abs(pct_d):.1f}%"
            else:
                reason = f"客胜{'升' if pct_a > 0 else '降'}{abs(pct_a):.1f}%"
            warn_type = "波动大"
    
    # 情况3：无变化实盘 + 高置信度
    if not reason:
        if pct_h == 0 and pct_d == 0 and pct_a == 0:
            if r['confidence'] >= 60:
                reason = f"实盘无变化 置信度{r['confidence']:.1f}%"
                warn_type = "实盘"
    
    if reason:
        r['warn_type'] = warn_type
        return True, reason
    
    # ====== 新增检测：偏离过低中的异常情况 ======
    if r['deviation_type'] == "偏离过低":
        pred = r['prediction']
        macao = r['macao']
        
        # 情况1：澳门推荐主队 + 平局和客队同时下降（反向操作）
        if macao == "主队胜" and pct_d < 0 and pct_a < 0:
            reason = f"澳门推荐主队但平局{pct_d:.1f}%客队{pct_a:.1f}%同时降"
            warn_type = "反向"
        
        # 情况2：澳门推荐客队 + 主队上升（造热客队）
        elif macao == "客队胜" and pct_h > 0:
            reason = f"客队过热 主胜升{pct_h:.1f}%"
            warn_type = "过热"
        
        # 情况3：偏离过低 + 无变化实盘 + 高赔（高水难出）
        elif pct_h == 0 and pct_d == 0 and pct_a == 0:
            if r['confidence'] < 40:  # 偏离过低 + 低置信度
                reason = f"偏离过低+实盘无变化 置信度仅{r['confidence']:.1f}%"
                warn_type = "实盘"
    
    if reason:
        r['warn_type'] = warn_type
        return True, reason
    
    # ====== 新增检测：偏离过高中的异常情况 ======
    if r['deviation_type'] == "偏离过高":
        pred = r['prediction']
        
        # 情况1：非预测方向大幅上升>10%（造热强势方）
        if pred == "主胜":
            # 平局和客胜都大幅上升，造热主队
            if pct_d > 10 and pct_a > 10:
                reason = f"造热主队 平局升{pct_d:.1f}%客胜升{pct_a:.1f}%"
                warn_type = "造热"
            # 非预测方向上升>10%
            elif pct_d > 10:
                reason = f"平局升{pct_d:.1f}% 造热主队"
                warn_type = "警惕"
            elif pct_a > 10:
                reason = f"客胜升{pct_a:.1f}% 造热主队"
                warn_type = "警惕"
        elif pred == "客胜":
            # 主胜和平局都大幅上升，造热客队
            if pct_h > 10 and pct_d > 10:
                reason = f"造热客队 主胜升{pct_h:.1f}%平局升{pct_d:.1f}%"
                warn_type = "造热"
            # 非预测方向上升>10%
            elif pct_h > 10:
                reason = f"主胜升{pct_h:.1f}% 造热客队"
                warn_type = "警惕"
            elif pct_d > 10:
                reason = f"平局升{pct_d:.1f}% 造热客队"
                warn_type = "警惕"
        
        # 情况3：客队不变但主队下降（诱盘）
        if pred == "客胜" and abs(pct_a) < 0.1 and pct_h < 0:
            reason = f"客胜不变主胜降{pct_h:.1f}% 诱盘"
            warn_type = "诱盘"
        
        # 情况2：无变化实盘（区分高水和低水）
        elif abs(pct_h) < 0.1 and abs(pct_d) < 0.1 and abs(pct_a) < 0.1:
            if r['confidence'] >= 60:
                reason = f"实盘无变化 置信度{r['confidence']:.1f}%"
                warn_type = "实盘"
            else:
                reason = f"实盘无变化 置信度{r['confidence']:.1f}%"
                warn_type = "实盘"
        
        # 情况4：主队轻微上升但非预测方向上升更多（造热主队）
        elif pred == "客胜" and pct_h > 0 and (pct_d > pct_h or pct_a > pct_h):
            if pct_d > 10 or pct_a > 10:
                reason = f"主胜升{pct_h:.1f}%平局升{pct_d:.1f}% 造热客队"
                warn_type = "造热"
        
        # 情况4：主队方向轻微上升（反向）
        elif pred == "主胜" and 0 < pct_h < 5:
            reason = f"主胜轻微升水{pct_h:.1f}% 反向"
            warn_type = "反向"
    
    if reason:
        r['warn_type'] = warn_type
        return True, reason
    
    return False, ""

# 检测所有比赛
overheated = []
for r in results:
    is_ov, reason = is_overheated(r)
    if is_ov:
        r['overheat_reason'] = reason
        overheated.append(r)

# 输出结果
print("\n" + "=" * 220)
print("3.19 比赛 - 完整预测列表（提取竞*官*即时赔率）")
print("=" * 220)
print("赔率变化说明: 主降/稳/升 = 主胜降赔/不变/升赔的公司百分比; 平降/稳/升 = 平局降/不变/升; 客降/稳/升 = 客胜降/不变/升")

print(f"\n| 编号 | 对阵 | 竞彩初盘 | 竞彩即时 | 赔率变化幅度 | 置信度详情 | 置信度 | 胜率差 | 8变化 | 赔率变化 | 澳门 | 预测 | 双选 | 规律建议 |")
print(f"|------|------|----------|----------|-------------|------------|--------|--------|-------|----------|------|------|------|----------|")

for r in results:
    ec = r['eight_change']
    eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
    zhongyong_mark = "中" if r['is_8_zhongyong'] else ""
    conf_detail = f"主{int(r['home_rate'])}% 平{int(r['draw_rate'])}% 客{int(r['away_rate'])}%"
    init_str = f"{r['init_home']}/{r['init_draw']}/{r['init_away']}" if r['init_home'] else "—"
    real_str = f"{r['home']}/{r['draw']}/{r['away']}"
    chg_h = fmt_change(r['init_home'], r['home'])
    chg_d = fmt_change(r['init_draw'], r['draw'])
    chg_a = fmt_change(r['init_away'], r['away'])
    # 双选建议
    double_choice = r.get('double_choice', '')
    double_mark = f"**{double_choice}**" if r.get('double_choice_strong') and double_choice else double_choice
    chg_str = f"主{chg_h} 平{chg_d} 客{chg_a}"
    # 规律一和规律三都显示
    rule_tag = r.get('rule1_tag', '')
    rule3_tag = r.get('rule3_tag', '')
    all_tags = rule_tag + " " + rule3_tag if rule3_tag else rule_tag
    print(f"| {r['id']} | {r['match']} | {init_str} | {real_str} | {chg_str} | {conf_detail} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_str} | {r['odds_change']} | {r['macao']} | {r['prediction']}{zhongyong_mark} | {double_mark} | {all_tags} |")

# 按偏离度分类
high_dev = [r for r in results if r['deviation_type'] == "偏离过高"]
low_dev = [r for r in results if r['deviation_type'] == "偏离过低"]
normal_dev = [r for r in results if r['deviation_type'] == "正常"]

print("\n" + "=" * 220)
print("【偏离过高】最可信")
print("=" * 220)
if high_dev:
    print(f"\n| 编号 | 对阵 | 竞彩初盘 | 竞彩即时 | 赔率变化幅度 | 置信度详情 | 置信度 | 胜率差 | 8变化 | 澳门 | 预测 |")
    print(f"|------|------|----------|----------|-------------|------------|--------|--------|-------|------|------|")
    for r in high_dev:
        ec = r['eight_change']
        eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
        conf_detail = f"主{int(r['home_rate'])}% 平{int(r['draw_rate'])}% 客{int(r['away_rate'])}%"
        init_str = f"{r['init_home']}/{r['init_draw']}/{r['init_away']}" if r['init_home'] else "—"
        real_str = f"{r['home']}/{r['draw']}/{r['away']}"
        chg_h = fmt_change(r['init_home'], r['home'])
        chg_d = fmt_change(r['init_draw'], r['draw'])
        chg_a = fmt_change(r['init_away'], r['away'])
        chg_str = f"主{chg_h} 平{chg_d} 客{chg_a}"
        print(f"| {r['id']} | {r['match']} | {init_str} | {real_str} | {chg_str} | {conf_detail} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_str} | {r['macao']} | {r['prediction']} |")
else:
    print("无")

print("\n" + "=" * 220)
print("【正常偏离】")
print("=" * 220)
if normal_dev:
    print(f"\n| 编号 | 对阵 | 竞彩初盘 | 竞彩即时 | 赔率变化幅度 | 置信度详情 | 置信度 | 胜率差 | 8变化 | 澳门 | 预测 |")
    print(f"|------|------|----------|----------|-------------|------------|--------|--------|-------|------|------|")
    for r in normal_dev:
        ec = r['eight_change']
        eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
        conf_detail = f"主{int(r['home_rate'])}% 平{int(r['draw_rate'])}% 客{int(r['away_rate'])}%"
        init_str = f"{r['init_home']}/{r['init_draw']}/{r['init_away']}" if r['init_home'] else "—"
        real_str = f"{r['home']}/{r['draw']}/{r['away']}"
        chg_h = fmt_change(r['init_home'], r['home'])
        chg_d = fmt_change(r['init_draw'], r['draw'])
        chg_a = fmt_change(r['init_away'], r['away'])
        chg_str = f"主{chg_h} 平{chg_d} 客{chg_a}"
        print(f"| {r['id']} | {r['match']} | {init_str} | {real_str} | {chg_str} | {conf_detail} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_str} | {r['macao']} | {r['prediction']} |")
else:
    print("无")

print("\n" + "=" * 220)
print("【偏离过低】谨慎对待")
print("=" * 220)
if low_dev:
    print(f"\n| 编号 | 对阵 | 竞彩初盘 | 竞彩即时 | 赔率变化幅度 | 置信度详情 | 置信度 | 胜率差 | 8变化 | 澳门 | 预测 |")
    print(f"|------|------|----------|----------|-------------|------------|--------|--------|-------|------|------|")
    for r in low_dev:
        ec = r['eight_change']
        eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
        conf_detail = f"主{int(r['home_rate'])}% 平{int(r['draw_rate'])}% 客{int(r['away_rate'])}%"
        init_str = f"{r['init_home']}/{r['init_draw']}/{r['init_away']}" if r['init_home'] else "—"
        real_str = f"{r['home']}/{r['draw']}/{r['away']}"
        chg_h = fmt_change(r['init_home'], r['home'])
        chg_d = fmt_change(r['init_draw'], r['draw'])
        chg_a = fmt_change(r['init_away'], r['away'])
        chg_str = f"主{chg_h} 平{chg_d} 客{chg_a}"
        print(f"| {r['id']} | {r['match']} | {init_str} | {real_str} | {chg_str} | {conf_detail} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_str} | {r['macao']} | {r['prediction']} |")
else:
    print("无")

# 统计
print("\n" + "=" * 220)
print("统计")
print("=" * 220)

print(f"\n| 类型 | 场数 | 主胜 | 客胜 | 平局 |")
print(f"|------|------|------|------|------|")
print(f"| 偏离过高 | {len(high_dev)} | {sum(1 for r in high_dev if r['prediction']=='主胜')} | {sum(1 for r in high_dev if r['prediction']=='客胜')} | {sum(1 for r in high_dev if r['prediction']=='平局')} |")
print(f"| 正常偏离 | {len(normal_dev)} | {sum(1 for r in normal_dev if r['prediction']=='主胜')} | {sum(1 for r in normal_dev if r['prediction']=='客胜')} | {sum(1 for r in normal_dev if r['prediction']=='平局')} |")
print(f"| 偏离过低 | {len(low_dev)} | {sum(1 for r in low_dev if r['prediction']=='主胜')} | {sum(1 for r in low_dev if r['prediction']=='客胜')} | {sum(1 for r in low_dev if r['prediction']=='平局')} |")
print(f"| 总计 | {len(results)} | {sum(1 for r in results if r['prediction']=='主胜')} | {sum(1 for r in results if r['prediction']=='客胜')} | {sum(1 for r in results if r['prediction']=='平局')} |")

# ====== 生成修正预测 ======
def get_fixed_prediction(r):
    """根据异常类型生成修正预测 - 给出具体胜平负"""
    warn_type = r.get('warn_type', '')
    pred = r['prediction']
    conf = r['confidence']
    pct_change = r.get('pct_change', [0, 0, 0])
    pct_h = pct_change[0]
    pct_d = pct_change[1]
    pct_a = pct_change[2]
    macao = r.get('macao', '')
    init_d_val = r.get('init_draw') or 0
    
    # ====== 规律三：置信度≤40%比赛处理（2-3-2架构）======
    # 优先级最高：置信度≤40%时，优先使用规律三判断
    if r.get('is_low_confidence', False):
        # 判断澳门心水方向
        macao_home = False
        macao_away = False
        macao_is_draw = '和局' in (macao or '')
        
        vs_pos = r['match'].find(' vs ')
        if vs_pos > 0:
            macao_home_team = r['match'][:vs_pos].strip()
            macao_away_team = r['match'][vs_pos+4:].strip()
            if macao and macao_home_team in macao:
                macao_home = True
            if macao and macao_away_team in macao:
                macao_away = True
        
        # ====== 先判断规律二：澳门推平局 ======
        if macao_is_draw:
            # 规律二：平局初始<3.0 或 下降>5% → 平局难出
            draw_hard = False
            if init_d_val > 0 and init_d_val < 3.0:
                draw_hard = True
            elif pct_d < -5.0:
                draw_hard = True
            
            if draw_hard:
                # 平局难出 → 顺赔率变动方向
                # 找变化最大的方向（下降最多=最热）
                if pct_a < pct_h:
                    return '客胜'  # 客降更多
                else:
                    return '主胜'
            else:
                # 平局正常可出：澳门推荐和局 + 平局初始>=3 + 变化>-5%
                # 预测和局
                return '和局'
        
        # ====== 规律二判断结束，继续规律三：顺赔率变动 + 造热排除 ======
        
        # 顺赔率变动方向
        # 找出变化最大的方向（负值表示下降=热，正值表示上升=冷）
        min_pct = min(pct_h, pct_d, pct_a)
        
        # 如果赔率变化造热澳门心水，排除澳门推荐
        is_zaore = False
        corrected_pred = pred  # 默认保持原预测
        
        if macao_home and pct_h < -3:  # 主降=造热主队
            is_zaore = True
            # 排除澳门推荐，反向或选其他
            if pred == '主胜':
                corrected_pred = '客胜'  # 反向
            elif pred == '和局':
                corrected_pred = '客胜' if pct_a < pct_d else '主胜'
        elif macao_away and pct_a < -3:  # 客降=造热客队
            is_zaore = True
            if pred == '客胜':
                corrected_pred = '主胜'  # 反向
            elif pred == '和局':
                corrected_pred = '主胜' if pct_h < pct_d else '客胜'
        elif macao_is_draw and pct_d < -3:  # 平降=造热平局
            is_zaore = True
            # 排除和局，按变化方向
            if pct_h < pct_a:
                corrected_pred = '主胜'
            else:
                corrected_pred = '客胜'
        
        # 如果造热了，返回修正预测
        if is_zaore:
            return corrected_pred
        
        # 未造热：顺赔率变动方向
        # 赔率下降的方向是热门方向，结果大概率走这个方向
        if pct_h < pct_d and pct_h < pct_a:
            return '主胜'  # 主降，走主
        elif pct_a < pct_h and pct_a < pct_d:
            return '客胜'  # 客降，走客
        elif pct_d < pct_h and pct_d < pct_a:
            # 平降，澳门如果推荐和局则出和局，否则按主/客
            if macao_is_draw:
                return '和局'
            return pred
        # 无明显方向 → 规律C：低置信度+澳门推荐主胜 → 平局概率大
        # 澳门推荐主胜 + 置信度40% + 赔率应降不降
        if macao_home and conf <= 41:
            return '和局'
        
        return pred

    # ====== 规律A（更新）：1-3-3格式 + 澳门推和局 + 平赔上升 ======
    # 典型格式：1-3-3赔率（如1.76/3.95/3.25）
    # 关键：澳门推荐和局 + 平赔不降反升 + 顶到3.95以上 = 平局难出
    init_h = r.get('init_home') or 0
    init_d = r.get('init_draw') or 0
    init_a = r.get('init_away') or 0
    
    # 重新计算macao_is_draw（因为可能是从is_low_confidence分支外调用）
    macao_is_draw = '和局' in (macao or '')
    
    if macao_is_draw and 45 <= conf <= 55:
        # 判断是否1-3-3或3-3-1格式：平局最高 + 最低赔率方向明确
        # 1-3-3：主胜最低，平局最高，客胜次高（1.76/3.95/3.25）
        # 3-3-1：客胜最低，平局最高，主胜次高（3.15/3.65/1.86）
        if init_h > 0 and init_d > 0 and init_a > 0:
            # 平局最高
            is_highest_draw = (init_d > init_h and init_d > init_a)
            # 1-3-3格式：主胜最低
            is_133 = (init_h < init_a and init_d > init_a * 1.3 and init_d > 3.5)
            # 3-3-1格式：客胜最低
            is_331 = (init_a < init_h and init_d > init_h * 1.1 and init_d > 3.5)
            
            if is_133 or is_331:
                # 1-3-3格式：平赔上升 → 平局难出，反向
                # 3-3-1格式 + 平赔下降 → 平局正常可出
                if pct_d > 0:
                    # 平赔上升 → 驱赶资金，平局难出
                    if init_h < init_a:  # 1-3-3格式，主胜最低 → 返客胜
                        return '客胜'
                    else:  # 3-3-1格式，客胜最低 → 返主胜
                        return '主胜'
                elif pct_d <= 0 and pct_d > -5:
                    # 平赔下降（<5%）→ 真实不看好平局，平局正常可出
                    # 3-3-1格式 + 澳门推荐和局 → 预测和局
                    if init_a < init_h:  # 3-3-1格式
                        return '和局'
                # 平赔顶到3.95以上 → 庄家不惧平局赔付
                if init_d >= 3.9 and pct_d <= 0:
                    # 双向保护：即使平赔下降，只要顶到高位仍可反向
                    if init_h < init_a:
                        return '客胜'
                    else:
                        return '主胜'
                # 平赔大幅下降（<-5%）→ 平局难出，保持原预测
    
    # ====== 规律B：2-3-2格局 + 客队过热 + 澳门同向 + 主胜大幅上升 ======
    # 典型格式：2-3-2赔率（如2.72/3.35/2.16）
    # 关键：主胜升幅>5% → 平局概率大
    if 38 <= conf <= 45:
        if init_h > 0 and init_d > 0 and init_a > 0:
            max_odds = max(init_h, init_d, init_a)
            min_odds = min(init_h, init_d, init_a)
            is_232 = (max_odds / min_odds < 1.5 and 
                     min(init_h, init_a) < 2.8 and 
                     2.8 < init_d < 3.5)
            
            if is_232:
                # 客队过热 + 与澳门推荐同向
                macao_home = False
                macao_away = False
                vs_pos = r['match'].find(' vs ')
                if vs_pos > 0:
                    macao_home_team = r['match'][:vs_pos].strip()
                    macao_away_team = r['match'][vs_pos+4:].strip()
                    if macao and macao_home_team in macao:
                        macao_home = True
                    if macao and macao_away_team in macao:
                        macao_away = True
                
                # 客队过热 + 与澳门同向 + 主胜大幅上升
                if macao_away and pct_a < -5 and pct_h > 5:
                    # 置信度低，强行造热，平局概率大
                    return '和局'
                
                # 主胜升幅>5%，平局概率大
                if pct_h > 5:
                    return '和局'
    
    # ====== 规律C：低置信度（40%） + 澳门推荐主胜 ======
    # 关键：置信度≤41%，澳门推荐主胜，赔率应降不降
    if conf <= 41:
        macao_home = False
        vs_pos = r['match'].find(' vs ')
        if vs_pos > 0:
            macao_home_team = r['match'][:vs_pos].strip()
            if macao and macao_home_team in macao:
                macao_home = True
        
        # 澳门推荐主胜 + 置信度≤41% → 平局概率大
        if macao_home:
            # 赔率应降不降（主胜不降），平局概率大
            if pct_h >= 0:  # 主胜不降或上升
                return '和局'
    
    # ====== 规律D：置信度64-65% + 造热嫌疑 ======
    # 关键：置信度64%+但未达70%，给主队造热嫌疑，造热影响筹码流动，需防平
    if 60 <= conf <= 65:
        # 赔率变化：主降 + 平/客升 → 造热主队嫌疑
        if pct_h < 0 and (pct_d > 0 or pct_a > 0):
            # 主降幅度小(<2%) → 最多赢一球，需防平
            if -2 < pct_h < 0:
                return '和局'
        # 主队赔率升 → 难打出
        if pct_h > 0 and pred == '主胜':
            return '和局'
    
    # ====== 规律E：2-3-2格局 + 置信度44% + 澳门同路 + 平赔<3.0 ======
    # 关键：2-3-2格局 + 置信度40-48% + 赔率降主队 + 澳门推荐同路 → 排除澳门
    # 关键：平赔<3.0且无变化 → 诱盘嫌疑，客队打出
    if 40 <= conf <= 48:
        if init_h > 0 and init_d > 0 and init_a > 0:
            max_odds = max(init_h, init_d, init_a)
            min_odds = min(init_h, init_d, init_a)
            is_232 = (max_odds / min_odds < 1.5 and 
                     min(init_h, init_a) < 2.8 and 
                     2.8 < init_d < 3.5)
            
            if is_232:
                macao_home = False
                macao_away = False
                vs_pos = r['match'].find(' vs ')
                if vs_pos > 0:
                    macao_home_team = r['match'][:vs_pos].strip()
                    macao_away_team = r['match'][vs_pos+4:].strip()
                    if macao and macao_home_team in macao:
                        macao_home = True
                    if macao and macao_away_team in macao:
                        macao_away = True
                
                # 赔率降主队 + 澳门推荐同路 → 难打出
                if macao_home and pct_h < 0:
                    # 平赔<3.0且无变化 → 诱盘嫌疑，客队打出
                    if init_d_val < 3.0 and abs(pct_d) < 2:
                        return '客胜'
                    # 否则反向
                    return '客胜'
    
    # ====== 规律二：澳门推平局 + 平局难出 ======
    # 条件：平局初始<3.0 或 平局赔率大幅下降>5%
    if warn_type == '平局难出':
        # 平局难出，预测从主胜/客胜中按置信度选
        if pred == '主胜':
            return '主胜'
        elif pred == '客胜':
            return '客胜'
        else:
            return '主胜'  # 偏向主队
    
    # ====== 规律五（提前）：主胜升幅>5% → 平局概率大 ======
    # 在过热检查之前执行，因为主胜升幅>5%优先级最高
    init_h = r.get('init_home') or 0
    if init_h > 0 and pct_h > 5:
        # 主胜升幅>5%，平局概率大于主胜
        return '和局'
    
    # 过热/造热/反向/诱盘 → 反向推荐
    if warn_type in ['过热', '造热', '反向', '诱盘']:
        if pred == '主胜':
            return '客胜'
        elif pred == '客胜':
            return '主胜'
        else:
            return pred
    
    # 警惕 → 根据变化方向判断
    # 但如果同时满足规律一（偏离过高+置信度≥66%），则规律一优先，保持原预测
    if warn_type == '警惕':
        if r.get('deviation_type') == '偏离过高' and conf >= 66:
            # 规律一优先：偏离过高+高置信度，保持原预测
            return pred
        # 平局上升最多，防平
        if pct_d > pct_h and pct_d > pct_a:
            return '平局'
        # 客胜上升，防客胜
        elif pct_a > pct_h and pct_a > pct_d:
            return '客胜'
        # 主胜上升，防主胜
        elif pct_h > pct_d and pct_h > pct_a:
            return '主胜'
        return pred
    
    # 波动大 → 反向或防平
    if warn_type == '波动大':
        if pred == '主胜':
            return '客胜'
        elif pred == '客胜':
            return '主胜'
        elif pred == '平局':
            return '主胜'
        return pred
    
    # ====== 规律一：实盘 + 置信度判断 ======
    if warn_type == '实盘':
        if conf >= 66:
            # 规律一：≥66% 可信，保持原预测
            return pred
        elif conf >= 55:
            # 55~65% 谨慎，保持原预测但标注
            return pred
        else:
            # <55% 高危，反向
            if pred == '主胜':
                return '客胜'
            elif pred == '客胜':
                return '主胜'
            else:
                return '主胜'
    
    # ====== 规律F（提前）：置信度41-55% + 澳门推荐和局 + 平赔3.5-3.7小降 ======
    # 新增规律（2026-03-21）：填补规律一（≥66%）和三（≤40%）之间的盲区
    # 关键：置信度41-55% + 澳门推荐和局 + 平局赔率3.5-3.7 + 平赔小降(-3%到0%) → 平局正常可出
    # 注意：这个规律需要在所有其他规律之前判断，因为即使没有warn_type也要执行
    if macao_is_draw and 41 <= conf <= 55:
        if init_d > 3.5 and init_d < 3.7:
            if -3 <= pct_d <= 0:
                # 规律F触发：平局正常可出
                return '和局'
    
    return pred

# ====== 过热提醒列表 ======
print("\n" + "=" * 220)
print("【过热提醒 + 规律判断】(规律一: 澳门分胜负+置信度≥66% | 规律二: 澳门推平局+初始<3或降>5%→平局难出 | 规律三: 置信度≤40%顺赔率变动+造热排除澳门)")
print("=" * 220)
if overheated:
    print(f"\n| 编号 | 对阵 | 竞彩即时 | 赔率变化 | 置信度 | 胜率差 | 澳门 | 预测 | 修正预测 | 类型 | 原因 | 规律建议 |")
    print(f"|------|------|----------|---------|--------|--------|------|------|----------|------|---------|----------|")
    for r in overheated:
        ec = r['eight_change']
        eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
        real_str = f"{r['home']}/{r['draw']}/{r['away']}"
        chg_h = fmt_change(r['init_home'], r['home'])
        chg_d = fmt_change(r['init_draw'], r['draw'])
        chg_a = fmt_change(r['init_away'], r['away'])
        chg_str = f"主{chg_h} 平{chg_d} 客{chg_a}"
        warn_type = r.get('warn_type', '')
        fixed_pred = get_fixed_prediction(r)
        rule_tag = r.get('rule1_tag', '')
        rule3_tag = r.get('rule3_tag', '')
        all_tags = rule_tag + " " + rule3_tag if rule3_tag else rule_tag
        print(f"| {r['id']} | {r['match']} | {real_str} | {chg_str} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {r['macao']} | {r['prediction']} | {fixed_pred} | {warn_type} | {r.get('overheat_reason', '')} | {all_tags} |")
else:
    print("\n无过热比赛")
