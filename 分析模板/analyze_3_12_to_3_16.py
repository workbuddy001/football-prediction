"""
用新规律分析3.12-3.16比赛
"""
import os
import re
import json

# 实际结果数据
actual_results = {
    # 3.12
    "周四001": "平局",  # 淡宾尼士 1:1 曼谷联
    "周四002": "平局",  # 博洛尼亚 1:1 罗马
    "周四003": "主胜",  # 斯图加特 2:1 波尔图
    "周四004": "客胜",  # 里尔 1:2 维拉
    "周四005": "主胜",  # 帕纳辛纳 2:0 贝蒂斯
    "周四006": "平局",  # 阿尔克马 1:1 布斯巴达
    "周四007": "客胜",  # 新未来SC 0:2 布赖代合作
    "周四008": "客胜",  # 费伦茨 1:2 布拉加
    "周四009": "客胜",  # 亨克 1:2 弗赖堡
    "周四010": "主胜",  # 诺丁汉 3:0 中日德兰
    "周四011": "客胜",  # 塞尔塔 0:2 里昂
    "周四012": "客胜",  # 水晶宫 0:1 拉纳卡
    
    # 3.13
    "周五001": "平局",  # 布里斯班 2:2 西悉尼
    "周五002": "主胜",  # 澳大利亚女 2:1 朝鲜女
    "周五003": "平局",  # 马格德堡 1:1 达姆施塔
    "周五004": "主胜",  # 胡巴尔卡德西亚 3:2 吉达国民
    "周五005": "客胜",  # 克莱蒙 0:1 波城FC
    "周五006": "平局",  # 兹沃勒 1:1 格罗宁根
    "周五007": "平局",  # 坎布尔 1:1 罗达JC
    "周五008": "主胜",  # 门兴 2:0 圣保利
    "周五009": "主胜",  # 都灵 4:1 帕尔马
    "周五010": "主胜",  # 马赛 1:0 欧塞尔
    "周五011": "主胜",  # 雷克斯 2:0 斯旺西
    "周五012": "平局",  # 阿拉维斯 1:1 比利亚雷
    
    # 3.14
    "周六001": "平局",  # 中国女 0:0 中国台女
    "周六002": "客胜",  # 名古屋鲸 0:3 神户胜利
    "周六003": "平局",  # 光州FC 0:0 全北现代
    "周六004": "客胜",  # 纽喷气机 1:2 奥克兰FC
    "周六005": "主胜",  # 鹿岛鹿角 1:0 川崎前锋
    "周六006": "主胜",  # 东京绿茵 1:0 浦和红钻
    "周六007": "平局",  # 大田市民 1:1 金泉尚武
    "周六008": "主胜",  # 韩国女 6:0 乌兹别克斯坦
    "周六009": "主胜",  # 不伦瑞克 1:0 杜塞多夫
    "周六010": "客胜",  # 考文垂 1:2 南安普敦
    "周六011": "主胜",  # 赫罗纳 3:0 毕尔巴鄂
    "周六012": "平局",  # 国际米兰 1:1 亚特兰大
    "周六013": "平局",  # 霍芬海姆 1:1 沃夫斯堡
    "周六014": "主胜",  # 多特蒙德 2:0 奥格斯堡
    "周六015": "主胜",  # 法兰克福 1:0 海登海姆
    "周六016": "平局",  # 勒沃库森 1:1 拜仁
    "周六017": "平局",  # 伯恩利 0:0 伯恩茅斯
    "周六018": "主胜",  # 马竞 1:0 赫塔费
    "周六019": "主胜",  # 洛里昂 2:1 朗斯
    "周六020": "主胜",  # 那不勒斯 2:1 莱切
    "周六021": "主胜",  # 莫尔德 2:0 罗森博格
    "周六022": "主胜",  # 阿森纳 2:0 埃弗顿
    "周六023": "客胜",  # 切尔西 0:1 纽卡斯尔
    "周六024": "平局",  # 汉堡 1:1 科隆
    "周六025": "主胜",  # 奥维耶多 1:0 巴伦西亚
    "周六026": "客胜",  # 埃因霍温 2:3 奈梅亨
    "周六027": "客胜",  # 赛哈特海湾 0:5 利雅得胜利
    "周六028": "客胜",  # 乌迪内斯 0:1 尤文图斯
    "周六029": "平局",  # 西汉姆联 1:1 曼城
    "周六030": "主胜",  # 皇马 4:1 埃尔切
    "周六031": "客胜",  # 阿罗卡 1:2 本菲卡
    "周六032": "平局",  # 达拉斯 3:3 圣迭戈FC
    
    # 3.15
    "周日001": "主胜",  # 日本女 7:0 菲律宾
    "周日002": "主胜",  # 长崎航海 1:0 福冈黄蜂
    "周日003": "客胜",  # 济州SK 1:2 首尔FC
    "周日004": "平局",  # 浦项制铁 1:1 仁川联
    "周日005": "主胜",  # 墨胜利 4:1 麦克阿瑟FC
    "周日006": "客胜",  # 特温特 0:2 乌德勒支
    "周日007": "客胜",  # 维罗纳 0:2 热那亚
    "周日008": "平局",  # 沙尔克04 2:2 汉诺威96
    "周日009": "主胜",  # 马洛卡 2:1 西班牙人
    "周日010": "主胜",  # 费耶诺德 2:1 SBV精英
    "周日011": "主胜",  # 克里斯蒂 3:2 布兰
    "周日012": "平局",  # 水晶宫 0:0 利兹联
    "周日013": "平局",  # 诺丁汉 0:0 富勒姆
    "周日014": "主胜",  # 曼联 3:1 维拉
    "周日015": "主胜",  # 比萨 3:1 卡利亚里
    "周日016": "客胜",  # 萨索洛 0:1 博洛尼亚
    "周日017": "客胜",  # 不来梅 0:2 美因茨
    "周日018": "主胜",  # 巴萨 5:2 塞维利亚
    "周日019": "主胜",  # 瓦勒伦加 1:0 桑纳菲
    "周日020": "平局",  # 勒阿弗尔 0:0 里昂
    "周日021": "平局",  # 利物浦 1:1 热刺
    "周日022": "客胜",  # 弗赖堡 0:1 柏林联合
    "周日023": "主胜",  # 科莫 2:1 罗马
    "周日024": "平局",  # 贝蒂斯 1:1 塞尔塔
    "周日025": "主胜",  # 斯图加特 1:0 莱红牛
    "周日026": "主胜",  # 拉齐奥 1:0 AC米兰
    "周日027": "主胜",  # 皇家社会 3:1 奥萨苏纳
    "周日028": "主胜",  # 波尔图 3:0 摩雷伦斯
    "周日029": "主胜",  # 温哥华 6:0 明尼苏达
    
    # 3.16
    "周一001": "客胜",  # 海尔蒙特 0:4 坎布尔
    "周一002": "客胜",  # 克雷莫纳 0:2 佛罗伦萨
    "周一003": "平局",  # 阿纳西 1:1 特鲁瓦
    "周一004": "平局",  # 布伦特 2:2 狼队
    "周一005": "主胜",  # 朴次茅斯 2:1 德比郡
    "周一006": "平局",  # 巴列卡诺 1:1 莱万特
    "周二001": "主胜",  # 悉尼FC 2:1 墨尔本城
    "周二002": "主胜",  # 中国女 2:1  Austral女
    "周二004": "平局",  # 里斯本 2:2 博德闪耀
    "周二006": "平局",  # 阿森纳 1:1 勒沃库森
    "周二007": "客胜",  # 切尔西 1:2 巴黎圣曼
    "周二008": "客胜",  # 曼城 1:2 皇马
}

def count_8_in_odds(odds_list):
    count = 0
    for odd in odds_list:
        for o in odd:
            o_str = f"{o:.2f}"
            if o_str.endswith('8'):
                count += 1
    return count

def extract_data_from_file(filepath):
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    
    num_match = re.search(r'编号：(\w+)\s*\|', content)
    if not num_match:
        return None
    num = num_match.group(1)
    
    home_match = re.search(r'\| 主队 \|\s*(.+?)\s*\|', content)
    away_match = re.search(r'\| 客队 \|\s*(.+?)\s*\|', content)
    if not home_match or not away_match:
        return None
    home = home_match.group(1).strip()
    away = away_match.group(1).strip()
    
    home_rate_match = re.search(r'主队近况.*?胜率\s*(\d+)%', content)
    away_rate_match = re.search(r'客队近况.*?胜率\s*(\d+)%', content)
    home_rate = int(home_rate_match.group(1)) if home_rate_match else 0
    away_rate = int(away_rate_match.group(1)) if away_rate_match else 0
    diff = home_rate - away_rate
    
    init_match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if init_match:
        try:
            odds_str = '[' + init_match.group(1) + ']'
            initial_odds = eval(odds_str)
            init_8 = count_8_in_odds(initial_odds)
        except:
            init_8 = 0
    else:
        init_8 = 0
    
    real_match = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if real_match:
        try:
            odds_str = '[' + real_match.group(1) + ']'
            realtime_odds = eval(odds_str)
            real_8 = count_8_in_odds(realtime_odds)
        except:
            real_8 = 0
    else:
        real_8 = 0
    
    return {
        'num': num,
        'match': f"{home} vs {away}",
        'home_rate': home_rate,
        'away_rate': away_rate,
        'diff': diff,
        'init_8': init_8,
        'real_8': real_8,
        'change_8': real_8 - init_8,
        'actual': actual_results.get(num, None)
    }

# 提取所有数据
all_matches = []
for day in ['3.12', '3.13', '3.14', '3.15', '3.16']:
    day_dir = f'd:/work/workbuddy/足球预测/分析模板/{day}'
    if not os.path.exists(day_dir):
        continue
    
    for f in sorted(os.listdir(day_dir)):
        if f.endswith('_源数据.md'):
            filepath = os.path.join(day_dir, f)
            data = extract_data_from_file(filepath)
            if data and data['actual']:
                all_matches.append((day, data))

# 按日期排序
all_matches.sort(key=lambda x: (x[0], x[1]['num']))

def get_zone(diff):
    if diff < -15:
        return "客队极好"
    elif diff > 15:
        return "主队极好"
    else:
        return "焦灼"

def get_prediction(m):
    diff = m['diff']
    change_8 = m['change_8']
    zone = get_zone(diff)
    
    # 按规律：新规律是看8变化的方向
    # 规律：8变化>0时，客队极好→反选，其他→跟庄家
    # 但我们需要更精确的规律
    
    if change_8 > 0:
        # 8增加时
        if zone == "客队极好":
            # 反选
            return "反选(客极好)", zone
        else:
            # 跟庄家
            return "跟庄家", zone
    elif change_8 < 0:
        # 8减少时
        if zone == "客队极好":
            # 8减少+客队极好=实盘
            return "跟庄家", zone
        else:
            return "观察", zone
    else:
        return "无8变化", zone

# 输出
print("=" * 130)
print("3.12-3.16 比赛分析 - 按新规律（8变化+胜率差）")
print("规律: 8增加时，客队极好→反选，其他→跟庄家 | 8减少时，客队极好→跟庄家")
print("=" * 130)
print()
print("| 日期 | 编号 | 对阵 | 胜率差 | 区间 | 8变化 | 按规律预测 | 实际 | 结果 |")
print("|------|------|------|--------|------|-------|------------|------|------|")

total = 0
correct = 0

for day, m in all_matches:
    pred, zone = get_prediction(m)
    actual = m['actual']
    
    # 判断结果
    if "无8变化" in pred:
        result = "-"
    elif "反选" in pred:
        # 反选：预测客队极好时，打出主胜或平局
        if zone == "客队极好":
            # 客队极好时反选，预测主胜或平局
            # 实际打出主胜或平局就算对
            if actual in ["主胜", "平局"]:
                result = "OK"
                correct += 1
            else:
                result = "NO"
            total += 1
    elif "跟庄家" in pred:
        # 需要判断跟庄家的方向
        # 这里简化处理：假设跟庄家就是预测主胜（因为8增加时通常主胜8增加最多）
        # 实际应该根据更多数据判断
        if actual == "主胜":
            result = "OK"
            correct += 1
        else:
            result = "NO"
        total += 1
    else:
        result = "-"
    
    print(f"| {day} | {m['num']} | {m['match']} | {m['diff']:+d}% | {zone} | {m['change_8']:+d} | {pred} | {actual} | {result} |")

print()
print("=" * 130)
print(f"统计: {correct}/{total} = {correct/total*100:.1f}%")
