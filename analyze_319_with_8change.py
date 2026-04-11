"""
3.19 比赛 - 完整预测列表（显示8变化和置信度详情）
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

# 实际实力
strength_info = {
    "周四001": "客强很多",
    "周四002": "接近",
    "周四003": "主强",
    "周四004": "接近",
    "周四005": "客强",
    "周四006": "主强",
    "周四007": "主强",
    "周四008": "主强",
    "周四009": "主强",
    "周四010": "接近",
    "周五001": "接近",
    "周五002": "主强",
    "周五003": "接近",
    "周五004": "客强",
    "周五005": "主强",
    "周五006": "客强",
    "周五007": "接近",
    "周五008": "主强",
    "周五009": "主强",
    "周五010": "主强",
    "周五011": "接近",
    "周五012": "主强",
    "周五013": "客强",
    "周五014": "接近",
    "周五015": "接近",
    "周五016": "接近",
}

# 从源数据计算8变化
def calculate_8_change(match_id):
    """从源数据文件读取并计算8变化"""
    file_path = f"d:/work/workbuddy/足球预测/分析模板/3.19/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return [0, 0, 0]  # 默认无变化
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取初盘赔率
        initial_odds = []
        match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match:
            odds_str = match.group(1)
            for line in odds_str.split('\n'):
                nums = re.findall(r'\d+\.\d+', line)
                if len(nums) >= 3:
                    initial_odds.append((float(nums[0]), float(nums[1]), float(nums[2])))
        
        # 提取即时赔率
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
        
        # 计算8以下赔率的公司数量变化
        initial_under_8 = [0, 0, 0]  # 主胜、平局、客胜
        realtime_under_8 = [0, 0, 0]
        
        for odds in initial_odds:
            if odds[0] < 8: initial_under_8[0] += 1
            if odds[1] < 8: initial_under_8[1] += 1
            if odds[2] < 8: initial_under_8[2] += 1
        
        for odds in realtime_odds:
            if odds[0] < 8: realtime_under_8[0] += 1
            if odds[1] < 8: realtime_under_8[1] += 1
            if odds[2] < 8: realtime_under_8[2] += 1
        
        # 8变化
        change = [
            realtime_under_8[0] - initial_under_8[0],
            realtime_under_8[1] - initial_under_8[1],
            realtime_under_8[2] - initial_under_8[2]
        ]
        
        return change
        
    except Exception as e:
        print(f"读取{match_id}源数据出错: {e}")
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

results = []

for mid, data in matches_data.items():
    confidence, home_rate, draw_rate, away_rate = calculate_confidence(data['home'], data['draw'], data['away'])
    
    # 获取置信度中的选项
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
    
    # 计算8变化
    eight_change = calculate_8_change(mid)
    
    # 判断是否8中庸
    total_change = abs(eight_change[0]) + abs(eight_change[1]) + abs(eight_change[2])
    is_8_zhongyong = total_change <= 3
    
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
    })

# 按编号排序
results.sort(key=lambda x: x['id'])

print("=" * 130)
print("3.19 比赛 - 完整预测列表（显示8变化和置信度详情）")
print("=" * 130)

print(f"\n| 编号 | 对阵 | 置信度详情 | 置信度 | 胜率差 | 8变化 | 偏离 | 预测 |")
print(f"|------|------|------------|--------|--------|-------|------|------|")

for r in results:
    # 置信度详情
    conf_detail = f"主{r['home_rate']:.0f}% 平{r['draw_rate']:.0f}% 客{r['away_rate']:.0f}%"
    
    # 8变化格式化
    ec = r['eight_change']
    eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
    
    # 8中庸标记
    zhongyong_mark = "中" if r['is_8_zhongyong'] else ""
    
    print(f"| {r['id']} | {r['match']} | {conf_detail} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_str} | {r['deviation_type']} | {r['prediction']}{zhongyong_mark} |")

# 按偏离度分类
high_dev = [r for r in results if r['deviation_type'] == "偏离过高"]
low_dev = [r for r in results if r['deviation_type'] == "偏离过低"]
normal_dev = [r for r in results if r['deviation_type'] == "正常"]

print("\n" + "=" * 130)
print("【偏离过高】最可信 (2场)")
print("=" * 130)
print(f"\n| 编号 | 对阵 | 置信度详情 | 置信度 | 胜率差 | 8变化 | 预测 |")
print(f"|------|------|------------|--------|--------|-------|------|")
for r in high_dev:
    conf_detail = f"主{r['home_rate']:.0f}% 平{r['draw_rate']:.0f}% 客{r['away_rate']:.0f}%"
    ec = r['eight_change']
    eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
    print(f"| {r['id']} | {r['match']} | {conf_detail} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_str} | {r['prediction']} |")

print("\n" + "=" * 130)
print("【正常偏离】(14场)")
print("=" * 130)
print(f"\n| 编号 | 对阵 | 置信度详情 | 置信度 | 胜率差 | 8变化 | 预测 |")
print(f"|------|------|------------|--------|--------|-------|------|")
for r in normal_dev:
    conf_detail = f"主{r['home_rate']:.0f}% 平{r['draw_rate']:.0f}% 客{r['away_rate']:.0f}%"
    ec = r['eight_change']
    eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
    print(f"| {r['id']} | {r['match']} | {conf_detail} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_str} | {r['prediction']} |")

print("\n" + "=" * 130)
print("【偏离过低】谨慎对待 (10场)")
print("=" * 130)
print(f"\n| 编号 | 对阵 | 置信度详情 | 置信度 | 胜率差 | 8变化 | 预测 |")
print(f"|------|------|------------|--------|--------|-------|------|")
for r in low_dev:
    conf_detail = f"主{r['home_rate']:.0f}% 平{r['draw_rate']:.0f}% 客{r['away_rate']:.0f}%"
    ec = r['eight_change']
    eight_str = f"[{ec[0]:+d},{ec[1]:+d},{ec[2]:+d}]"
    print(f"| {r['id']} | {r['match']} | {conf_detail} | {r['confidence']:.1f}% | {r['rate_diff']:+.1f}% | {eight_str} | {r['prediction']} |")

# 统计
print("\n" + "=" * 130)
print("统计")
print("=" * 130)
print(f"\n| 类型 | 场数 | 主胜 | 客胜 | 平局 |")
print(f"|------|------|------|------|------|")
print(f"| 偏离过高 | {len(high_dev)} | {sum(1 for r in high_dev if r['prediction']=='主胜')} | {sum(1 for r in high_dev if r['prediction']=='客胜')} | {sum(1 for r in high_dev if r['prediction']=='平局')} |")
print(f"| 正常偏离 | {len(normal_dev)} | {sum(1 for r in normal_dev if r['prediction']=='主胜')} | {sum(1 for r in normal_dev if r['prediction']=='客胜')} | {sum(1 for r in normal_dev if r['prediction']=='平局')} |")
print(f"| 偏离过低 | {len(low_dev)} | {sum(1 for r in low_dev if r['prediction']=='主胜')} | {sum(1 for r in low_dev if r['prediction']=='客胜')} | {sum(1 for r in low_dev if r['prediction']=='平局')} |")
print(f"| 总计 | {len(results)} | {sum(1 for r in results if r['prediction']=='主胜')} | {sum(1 for r in results if r['prediction']=='客胜')} | {sum(1 for r in results if r['prediction']=='平局')} |")
