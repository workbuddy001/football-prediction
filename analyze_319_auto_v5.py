"""
3.19 比赛 - 完整预测列表（从源数据自动提取竞彩赔率）
"""

import os
import re
import glob

def extract_jingcai_odds(match_id):
    """从源数据文件提取竞彩胜平负赔率"""
    file_path = f"d:/work/workbuddy/足球预测/分析模板/3.19/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return None, None, None
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找"竞彩胜平负赔率"表格
        # 格式: | 主胜（xxx赢） | 4.50 |
        home_match = re.search(r'主胜[（(].*?[）)]\s*\|\s*(\d+\.\d+)', content)
        draw_match = re.search(r'平局\s*\|\s*(\d+\.\d+)', content)
        away_match = re.search(r'客胜[（(].*?[）)]\s*\|\s*(\d+\.\d+)', content)
        
        home = float(home_match.group(1)) if home_match else None
        draw = float(draw_match.group(1)) if draw_match else None
        away = float(away_match.group(1)) if away_match else None
        
        return home, draw, away
        
    except Exception as e:
        print(f"读取{match_id}竞彩赔率出错: {e}")
        return None, None, None

def extract_macao_tip(match_id):
    """从源数据文件提取澳门推荐"""
    file_path = f"d:/work/workbuddy/足球预测/分析模板/3.19/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return None
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找澳门推荐
        match = re.search(r'澳门推荐\s*\|\s*([^\n|]+)', content)
        if match:
            return match.group(1).strip()
        
        # 备用搜索
        match = re.search(r'澳门推荐.*?([主胜客和]+)', content)
        if match:
            tip = match.group(1)
            if "主" in tip:
                return "主胜"
            elif "客" in tip:
                return "客胜"
            elif "和" in tip or "平" in tip:
                return "平局"
        
        return None
        
    except Exception as e:
        return None

def extract_match_name(match_id):
    """从源数据文件提取比赛名称"""
    file_path = f"d:/work/workbuddy/足球预测/分析模板/3.19/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return match_id
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找主队和客队
        home_match = re.search(r'主队\s*\|\s*([^\n|]+)', content)
        away_match = re.search(r'客队\s*\|\s*([^\n|]+)', content)
        
        home = home_match.group(1).strip() if home_match else "主队"
        away = away_match.group(1).strip() if away_match else "客队"
        
        return f"{home} vs {away}"
        
    except Exception as e:
        return match_id

# 比赛ID列表
match_ids = [
    "周四001", "周四002", "周四003", "周四004", "周四005",
    "周四006", "周四007", "周四008", "周四009", "周四010",
    "周五001", "周五002", "周五003", "周五004", "周五005",
    "周五006", "周五007", "周五008", "周五009", "周五010",
    "周五011", "周五012", "周五013", "周五014", "周五015", "周五016"
]

# 自动提取所有比赛的竞彩赔率
matches_data = {}
for mid in match_ids:
    home, draw, away = extract_jingcai_odds(mid)
    match_name = extract_match_name(mid)
    macao = extract_macao_tip(mid)
    
    if home and draw and away:
        matches_data[mid] = {
            "match": match_name,
            "home": home,
            "draw": draw,
            "away": away,
            "macao": macao
        }
        print(f"{mid}: 主{home} 平{draw} 客{away} | 澳门: {macao}")
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
    file_path = f"d:/work/workbuddy/足球预测/分析模板/3.19/{match_id}_*_源数据.md"
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
    file_path = f"d:/work/workbuddy/足球预测/分析模板/3.19/{match_id}_*_源数据.md"
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
    
    # 澳门推荐（从源数据提取）
    macao = data.get('macao', '-')
    
    # 赔率变化
    odds_stats = extract_odds_change(mid)
    odds_change = format_odds_change_pct(odds_stats)
    
    results.append({
        'id': mid,
        'match': data['match'],
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
    })

results.sort(key=lambda x: x['id'])

# 输出结果
print("\n" + "=" * 220)
print("3.19 比赛 - 完整预测列表（自动提取竞彩赔率）")
print("=" * 220)
print("赔率变化说明: 主降/稳/升 = 主胜降赔/不变/升赔的公司百分比; 平降/稳/升 = 平局降/不变/升; 客降/稳/升 = 客胜降/不变/升")

print(f"\n| 编号 | 对阵 | 竞彩赔率 | 置信度详情 | 置信度 | 胜率差 | 8变化 | 赔率变化 | 澳门 | 预测 |")
print(f"|------|------|----------|------------|--------|--------|-------|----------|------|------|")

for r in results:
    ec = r['eight_change']
    eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
    zhongyong_mark = "中" if r['is_8_zhongyong'] else ""
    
    # 置信度详情
    conf_detail = f"主{int(r['home_rate'])}% 平{int(r['draw_rate'])}% 客{int(r['away_rate'])}%"
    
    # 竞彩赔率
    odds_str = f"{r['home']}/{r['draw']}/{r['away']}"
    
    print(f"| {r['id']} | {r['match']} | {odds_str} | {conf_detail} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_str} | {r['odds_change']} | {r['macao']} | {r['prediction']}{zhongyong_mark} |")

# 按偏离度分类
high_dev = [r for r in results if r['deviation_type'] == "偏离过高"]
low_dev = [r for r in results if r['deviation_type'] == "偏离过低"]
normal_dev = [r for r in results if r['deviation_type'] == "正常"]

print("\n" + "=" * 220)
print("【偏离过高】最可信")
print("=" * 220)
if high_dev:
    print(f"\n| 编号 | 对阵 | 竞彩赔率 | 置信度详情 | 置信度 | 胜率差 | 8变化 | 澳门 | 预测 |")
    print(f"|------|------|----------|------------|--------|--------|-------|------|------|")
    for r in high_dev:
        ec = r['eight_change']
        eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
        conf_detail = f"主{int(r['home_rate'])}% 平{int(r['draw_rate'])}% 客{int(r['away_rate'])}%"
        odds_str = f"{r['home']}/{r['draw']}/{r['away']}"
        print(f"| {r['id']} | {r['match']} | {odds_str} | {conf_detail} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_str} | {r['macao']} | {r['prediction']} |")
else:
    print("无")

print("\n" + "=" * 220)
print("【正常偏离】")
print("=" * 220)
if normal_dev:
    print(f"\n| 编号 | 对阵 | 竞彩赔率 | 置信度详情 | 置信度 | 胜率差 | 8变化 | 澳门 | 预测 |")
    print(f"|------|------|----------|------------|--------|--------|-------|------|------|")
    for r in normal_dev:
        ec = r['eight_change']
        eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
        conf_detail = f"主{int(r['home_rate'])}% 平{int(r['draw_rate'])}% 客{int(r['away_rate'])}%"
        odds_str = f"{r['home']}/{r['draw']}/{r['away']}"
        print(f"| {r['id']} | {r['match']} | {odds_str} | {conf_detail} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_str} | {r['macao']} | {r['prediction']} |")
else:
    print("无")

print("\n" + "=" * 220)
print("【偏离过低】谨慎对待")
print("=" * 220)
if low_dev:
    print(f"\n| 编号 | 对阵 | 竞彩赔率 | 置信度详情 | 置信度 | 胜率差 | 8变化 | 澳门 | 预测 |")
    print(f"|------|------|----------|------------|--------|--------|-------|------|------|")
    for r in low_dev:
        ec = r['eight_change']
        eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
        conf_detail = f"主{int(r['home_rate'])}% 平{int(r['draw_rate'])}% 客{int(r['away_rate'])}%"
        odds_str = f"{r['home']}/{r['draw']}/{r['away']}"
        print(f"| {r['id']} | {r['match']} | {odds_str} | {conf_detail} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_str} | {r['macao']} | {r['prediction']} |")
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

# 澳门与预测对比
def check_macao_match(macao, prediction):
    if not macao:
        return False
    macao = macao.lower()
    if '和局' in macao or '平' in macao:
        return prediction == "平局"
    elif '客' in macao or '贏' in macao:
        # 需要判断是主队赢还是客队赢
        if 'vs' in str(macao):
            return False
        return prediction == "客胜"
    elif '主' in macao:
        return prediction == "主胜"
    return False

macao_match = sum(1 for r in results if check_macao_match(r['macao'], r['prediction']))
print(f"\n澳门与预测一致: {macao_match}/{len(results)} ({macao_match/len(results)*100:.0f}%)")
