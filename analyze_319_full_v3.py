"""
3.19 比赛 - 完整预测列表（显示8变化、置信度详情、澳门推荐、完整赔率变化）
"""

import os
import re
import glob

# 竞彩赔率数据
matches_data = {
    "周四001": {"match": "中国台女 vs 朝鲜女", "home": 1.72, "draw": 4.65, "away": 3.00},
    "周四002": {"match": "弗赖堡 vs 亨克", "home": 2.41, "draw": 3.38, "away": 2.39},
    "周四003": {"match": "里昂 vs 塞尔塔", "home": 1.53, "draw": 3.65, "away": 4.55},
    "周四004": {"match": "中日德兰 vs 诺丁汉", "home": 2.45, "draw": 3.20, "away": 2.48},
    "周四005": {"match": "拉纳卡 vs 水晶宫", "home": 3.15, "draw": 3.30, "away": 1.91},
    "周四006": {"match": "美因茨 vs 奥洛穆茨", "home": 1.45, "draw": 3.90, "away": 5.20},
    "周四007": {"match": "罗马 vs 博洛尼亚", "home": 1.93, "draw": 3.35, "away": 3.10},
    "周四008": {"match": "波尔图 vs 斯图加特", "home": 1.82, "draw": 3.50, "away": 3.45},
    "周四009": {"match": "维拉 vs 里尔", "home": 1.77, "draw": 3.45, "away": 3.65},
    "周四010": {"match": "贝蒂斯 vs 帕纳辛纳", "home": 2.02, "draw": 3.30, "away": 3.03},
    "周五001": {"match": "西悉尼 vs 阿德莱德", "home": 2.38, "draw": 3.35, "away": 2.48},
    "周五002": {"match": "汉诺威96 vs 不伦瑞克", "home": 2.02, "draw": 3.50, "away": 2.95},
    "周五003": {"match": "卡斯鲁厄 vs 菲尔特", "home": 2.28, "draw": 3.30, "away": 2.70},
    "周五004": {"match": "卡利亚里 vs 那不勒斯", "home": 4.00, "draw": 3.65, "away": 1.66},
    "周五005": {"match": "克莱蒙 vs 圣旺红星", "home": 1.85, "draw": 3.30, "away": 3.55},
    "周五006": {"match": "波城FC vs 蒙彼利埃", "home": 3.10, "draw": 3.20, "away": 2.02},
    "周五007": {"match": "布洛涅 vs 南锡", "home": 2.35, "draw": 3.15, "away": 2.65},
    "周五008": {"match": "赫拉克勒 vs SBV精英", "home": 2.10, "draw": 3.45, "away": 2.80},
    "周五009": {"match": "罗达JC vs 海尔蒙特", "home": 1.75, "draw": 3.65, "away": 3.65},
    "周五010": {"match": "莱红牛 vs 霍芬海姆", "home": 1.62, "draw": 3.90, "away": 4.25},
    "周五011": {"match": "热那亚 vs 乌迪内斯", "home": 2.60, "draw": 3.10, "away": 2.42},
    "周五012": {"match": "朗斯 vs 昂热", "home": 1.50, "draw": 3.70, "away": 5.25},
    "周五013": {"match": "伯恩茅斯 vs 曼联", "home": 3.65, "draw": 3.45, "away": 1.77},
    "周五014": {"match": "普雷斯顿 vs 斯托克城", "home": 2.35, "draw": 3.20, "away": 2.65},
    "周五015": {"match": "比利亚雷 vs 皇家社会", "home": 2.10, "draw": 3.35, "away": 2.90},
    "周五016": {"match": "阿马多拉 vs 卡萨皮亚", "home": 2.48, "draw": 2.95, "away": 2.60},
}

# 澳门推荐
macao_tips = {
    "周四001": "和局", "周四002": "客胜", "周四003": "和局", "周四004": "主胜",
    "周四005": "和局", "周四006": "主胜", "周四007": "主胜", "周四008": "主胜",
    "周四009": "客胜", "周四010": "客胜", "周五001": "和局", "周五002": "主胜",
    "周五003": "客胜", "周五004": "客胜", "周五005": "和局", "周五006": "客胜",
    "周五007": "主胜", "周五008": "和局", "周五009": "主胜", "周五010": "主胜",
    "周五011": "主胜", "周五012": "主胜", "周五013": "和局", "周五014": "客胜",
    "周五015": "主胜", "周五016": "和局",
}

# 实际实力
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
        
        # 提取表格数据
        stats = {"home": {"down": 0, "same": 0, "up": 0}, "draw": {"down": 0, "same": 0, "up": 0}, "away": {"down": 0, "same": 0, "up": 0}, "total": 0}
        
        # 查找赔率变动表格
        lines = content.split('\n')
        in_table = False
        for line in lines:
            if '初盘胜' in line and '即时胜' in line:
                in_table = True
                continue
            if in_table:
                if line.startswith('---') or line.startswith('>'):
                    break
                # 匹配变动列中的箭头
                if '↓' in line or '↑' in line or '—' in line:
                    parts = line.split('|')
                    if len(parts) >= 8:
                        # 第4列是主胜变动，第6列是平局变动，第8列是客胜变动
                        home_change = parts[4].strip() if len(parts) > 4 else ""
                        draw_change = parts[6].strip() if len(parts) > 6 else ""
                        away_change = parts[8].strip() if len(parts) > 8 else ""
                        
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
        print(f"读取{match_id}出错: {e}")
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

def format_odds_change(stats):
    """格式化赔率变化为简短的字符串"""
    total = stats.get("total", 30)
    if total == 0:
        total = 30
    
    h = stats["home"]
    d = stats["draw"]
    a = stats["away"]
    
    # 主胜: 降/稳/升
    h_str = f"{h['down']}/{h['same']}/{h['up']}"
    # 平局: 降/稳/升
    d_str = f"{d['down']}/{d['same']}/{d['up']}"
    # 客胜: 降/稳/升
    a_str = f"{a['down']}/{a['same']}/{a['up']}"
    
    return f"主{h_str} 平{d_str} 客{a_str}"

results = []

for mid, data in matches_data.items():
    confidence, home_rate, draw_rate, away_rate = calculate_confidence(data['home'], data['draw'], data['away'])
    
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
    macao = macao_tips.get(mid, "-")
    
    # 赔率变化
    odds_stats = extract_odds_change(mid)
    odds_change = format_odds_change(odds_stats)
    
    results.append({
        'id': mid,
        'match': data['match'],
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

print("=" * 180)
print("3.19 比赛 - 完整预测列表（显示8变化、置信度详情、澳门推荐、完整赔率变化）")
print("=" * 180)
print("赔率变化说明: 主X/Y/Z = 主胜降/不变/升的公司数; 平X/Y/Z = 平局降/不变/升; 客X/Y/Z = 客胜降/不变/升")

print(f"\n| 编号 | 对阵 | 置信度详情 | 置信度 | 胜率差 | 8变化 | 赔率变化(降/稳/升) | 澳门 | 预测 |")
print(f"|------|------|------------|--------|--------|-------|---------------------|------|------|")

for r in results:
    conf_detail = f"主{r['home_rate']:.0f}% 平{r['draw_rate']:.0f}% 客{r['away_rate']:.0f}%"
    ec = r['eight_change']
    eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
    zhongyong_mark = "中" if r['is_8_zhongyong'] else ""
    
    print(f"| {r['id']} | {r['match']} | {conf_detail} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_str} | {r['odds_change']} | {r['macao']} | {r['prediction']}{zhongyong_mark} |")

# 按偏离度分类
high_dev = [r for r in results if r['deviation_type'] == "偏离过高"]
low_dev = [r for r in results if r['deviation_type'] == "偏离过低"]
normal_dev = [r for r in results if r['deviation_type'] == "正常"]

print("\n" + "=" * 180)
print("【偏离过高】最可信 (2场)")
print("=" * 180)
print(f"\n| 编号 | 对阵 | 置信度详情 | 置信度 | 胜率差 | 8变化 | 赔率变化(降/稳/升) | 澳门 | 预测 |")
print(f"|------|------|------------|--------|--------|-------|---------------------|------|------|")
for r in high_dev:
    conf_detail = f"主{r['home_rate']:.0f}% 平{r['draw_rate']:.0f}% 客{r['away_rate']:.0f}%"
    ec = r['eight_change']
    eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
    print(f"| {r['id']} | {r['match']} | {conf_detail} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_str} | {r['odds_change']} | {r['macao']} | {r['prediction']} |")

print("\n" + "=" * 180)
print("【正常偏离】(14场)")
print("=" * 180)
print(f"\n| 编号 | 对阵 | 置信度详情 | 置信度 | 胜率差 | 8变化 | 赔率变化(降/稳/升) | 澳门 | 预测 |")
print(f"|------|------|------------|--------|--------|-------|---------------------|------|------|")
for r in normal_dev:
    conf_detail = f"主{r['home_rate']:.0f}% 平{r['draw_rate']:.0f}% 客{r['away_rate']:.0f}%"
    ec = r['eight_change']
    eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
    print(f"| {r['id']} | {r['match']} | {conf_detail} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_str} | {r['odds_change']} | {r['macao']} | {r['prediction']} |")

print("\n" + "=" * 180)
print("【偏离过低】谨慎对待 (10场)")
print("=" * 180)
print(f"\n| 编号 | 对阵 | 置信度详情 | 置信度 | 胜率差 | 8变化 | 赔率变化(降/稳/升) | 澳门 | 预测 |")
print(f"|------|------|------------|--------|--------|-------|---------------------|------|------|")
for r in low_dev:
    conf_detail = f"主{r['home_rate']:.0f}% 平{r['draw_rate']:.0f}% 客{r['away_rate']:.0f}%"
    ec = r['eight_change']
    eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
    print(f"| {r['id']} | {r['match']} | {conf_detail} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_str} | {r['odds_change']} | {r['macao']} | {r['prediction']} |")

# 统计
print("\n" + "=" * 180)
print("统计")
print("=" * 180)

print(f"\n| 类型 | 场数 | 主胜 | 客胜 | 平局 |")
print(f"|------|------|------|------|------|")
print(f"| 偏离过高 | {len(high_dev)} | {sum(1 for r in high_dev if r['prediction']=='主胜')} | {sum(1 for r in high_dev if r['prediction']=='客胜')} | {sum(1 for r in high_dev if r['prediction']=='平局')} |")
print(f"| 正常偏离 | {len(normal_dev)} | {sum(1 for r in normal_dev if r['prediction']=='主胜')} | {sum(1 for r in normal_dev if r['prediction']=='客胜')} | {sum(1 for r in normal_dev if r['prediction']=='平局')} |")
print(f"| 偏离过低 | {len(low_dev)} | {sum(1 for r in low_dev if r['prediction']=='主胜')} | {sum(1 for r in low_dev if r['prediction']=='客胜')} | {sum(1 for r in low_dev if r['prediction']=='平局')} |")
print(f"| 总计 | {len(results)} | {sum(1 for r in results if r['prediction']=='主胜')} | {sum(1 for r in results if r['prediction']=='客胜')} | {sum(1 for r in results if r['prediction']=='平局')} |")

print("\n" + "=" * 180)
print("澳门推荐与预测对比")
print("=" * 180)
print(f"\n| 编号 | 对阵 | 预测 | 澳门推荐 | 一致? |")
print(f"|------|------|------|----------|-------|")
for r in results:
    match_str = "O" if ((r['macao'] == "主胜" and r['prediction'] == "主胜") or (r['macao'] == "客胜" and r['prediction'] == "客胜") or (r['macao'] == "和局" and r['prediction'] == "平局")) else "X"
    print(f"| {r['id']} | {r['match']} | {r['prediction']} | {r['macao']} | {match_str} |")
