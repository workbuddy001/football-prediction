# V5结果比对分析脚本
import os
import re

# 实际比赛结果
actual_results = {
    # 周五
    "周五001_布里斯班vs西悉尼": "平",     # 2:2
    "周五002_澳大利女vs朝鲜女": "主胜",    # 澳大利亚女 2:1
    "周五003_马格德堡vs达姆施塔": "平",    # 1:1
    "周五004_胡巴尔卡德西亚vs吉达国民": "主胜", # 3:2
    "周五005_克莱蒙vs波城FC": "客胜",      # 0:1
    "周五006_兹沃勒vs格罗宁根": "平",      # 1:1
    "周五007_坎布尔vs罗达JC": "平",        # 1:1
    "周五008_门兴vs圣保利": "主胜",        # 2:0
    "周五009_都灵vs帕尔马": "主胜",        # 4:1
    "周五010_马赛vs欧塞尔": "主胜",        # 1:0
    "周五011_雷克斯vs斯旺西": "主胜",      # 2:0
    "周五012_阿拉维斯vs比利亚雷": "平",    # 1:1
    
    # 周六
    "周六001_中国女vs中国台女": "平",       # 0:0
    "周六002_名古屋鲸vs神户胜利": "客胜",  # 0:3
    "周六003_光州FCvs全北现代": "平",      # 0:0
    "周六004_纽喷气机vs奥克兰FC": "客胜",  # 1:2
    "周六005_鹿岛鹿角vs川崎前锋": "主胜",  # 1:0
    "周六006_东京绿茵vs浦和红钻": "主胜",  # 1:0
    "周六007_大田市民vs金泉尚武": "平",    # 1:1
    "周六008_韩国女vs乌兹别克斯坦女": "主胜", # 6:0
    "周六009_不伦瑞克vs杜塞多夫": "主胜",  # 1:0
    "周六010_考文垂vs南安普敦": "客胜",    # 1:2
    "周六011_赫罗纳vs毕尔巴鄂": "主胜",    # 3:0
    "周六012_国际米兰vs亚特兰大": "平",     # 1:1
    "周六013_霍芬海姆vs沃夫斯堡": "平",    # 1:1
    "周六014_多特蒙德vs奥格斯堡": "主胜",  # 2:0
    "周六015_法兰克福vs海登海姆": "主胜",  # 1:0
    "周六016_勒沃库森vs拜仁": "平",        # 1:1
    "周六017_伯恩利vs伯恩茅斯": "平",      # 0:0
    "周六018_马竞vs赫塔费": "主胜",        # 1:0
    "周六019_洛里昂vs朗斯": "主胜",        # 2:1
    "周六020_那不勒斯vs莱切": "主胜",       # 2:1
    "周六021_莫尔德vs罗森博格": "主胜",    # 2:0
    "周六022_阿森纳vs埃弗顿": "主胜",       # 2:0
    "周六023_切尔西vs纽卡斯尔": "客胜",     # 0:1
    "周六024_汉堡vs科隆": "平",             # 1:1
    "周六025_奥维耶多vs巴伦西亚": "主胜",   # 1:0
    "周六026_埃因霍温vs奈梅亨": "客胜",     # 2:3
    "周六027_赛哈特海湾vs利雅得胜利": "客胜", # 0:5
    "周六028_乌迪内斯vs尤文图斯": "客胜",   # 0:1
    "周六029_西汉姆联vs曼城": "平",         # 1:1
    "周六030_皇马vs埃尔切": "主胜",         # 4:1
    "周六031_阿罗卡vs本菲卡": "客胜",       # 1:2
    "周六032_达拉斯vs圣迭戈FC": "平",       # 3:3
    
    # 周日
    "周日001_日本女vs菲律宾女": "主胜",     # 7:0
    "周日002_长崎航海vs福冈黄蜂": "主胜",   # 1:0
    "周日003_济州SKvs首尔FC": "客胜",       # 1:2
    "周日004_浦项制铁vs仁川联": "平",        # 1:1
    "周日005_墨胜利vs麦克阿瑟FC": "主胜",    # 4:1
    "周日006_特温特vs乌德勒支": "客胜",     # 0:2
    "周日007_维罗纳vs热那亚": "客胜",        # 0:2
    "周日008_沙尔克04vs汉诺威96": "平",      # 2:2
    "周日009_马洛卡vs西班牙人": "主胜",      # 2:1
    "周日010_费耶诺德vsSBV精英": "主胜",    # 2:1
    "周日011_克里斯蒂vs布兰": "主胜",        # 3:2
    "周日012_水晶宫vs利兹联": "平",          # 0:0
    "周日013_诺丁汉vs富勒姆": "平",          # 0:0
    "周日014_曼联vs维拉": "主胜",            # 3:1
    "周日015_比萨vs卡利亚里": "主胜",        # 3:1
    "周日016_萨索洛vs博洛尼亚": "客胜",      # 0:1
    "周日017_不来梅vs美因茨": "客胜",        # 0:2
    "周日018_巴萨vs塞维利亚": "主胜",        # 5:2
    "周日019_瓦勒伦加vs桑纳菲": "主胜",      # 1:0
    "周日020_勒阿弗尔vs里昂": "平",          # 0:0
    "周日021_利物浦vs热刺": "平",            # 1:1
    "周日022_弗赖堡vs柏林联合": "客胜",      # 0:1
    "周日023_科莫vs罗马": "主胜",            # 2:1
    "周日024_贝蒂斯vs塞尔塔": "平",          # 1:1
    "周日025_斯图加特vs莱红牛": "主胜",      # 1:0
    "周日026_拉齐奥vsAC米兰": "主胜",        # 1:0
    "周日027_皇家社会vs奥萨苏纳": "主胜",    # 3:1
    "周日028_波尔图vs摩雷伦斯": "主胜",      # 3:0
    "周日029_温哥华vs明尼苏达": "主胜",      # 6:0
}

# V5预测结果
predictions = {
    # 周五
    "周五001_布里斯班vs西悉尼": "客胜",
    "周五002_Austral女vs朝鲜女": "客胜",
    "周五003_马格德堡vs达姆施塔": "客胜",
    "周五004_胡巴尔卡德西亚vs吉达国民": "主胜",
    "周五005_克莱蒙vs波城FC": "主胜",
    "周五006_兹沃勒vs格罗宁根": "客胜",
    "周五007_坎布尔vs罗达JC": "客胜",
    "周五008_门兴vs圣保利": "客胜",
    "周五009_都灵vs帕尔马": "客胜",
    "周五010_马赛vs欧塞尔": "主胜",
    "周五011_雷克斯vs斯旺西": "平",
    "周五012_阿拉维斯vs比利亚雷": "客胜",
    
    # 周六
    "周六001_中国女vs中国台女": "主胜",
    "周六002_名古屋鲸vs神户胜利": "主胜",
    "周六003_光州FCvs全北现代": "客胜",
    "周六004_纽喷气机vs奥克兰FC": "主胜",
    "周六005_鹿岛鹿角vs川崎前锋": "主胜",
    "周六006_东京绿茵vs浦和红钻": "客胜",
    "周六007_大田市民vs金泉尚武": "客胜",
    "周六008_韩国女vs乌兹别克斯坦女": "主胜",
    "周六009_不伦瑞克vs杜塞多夫": "客胜",
    "周六010_考文垂vs南安普敦": "客胜",
    "周六011_赫罗纳vs毕尔巴鄂": "平",
    "周六012_国际米兰vs亚特兰大": "主胜",
    "周六013_霍芬海姆vs沃夫斯堡": "主胜",
    "周六014_多特蒙德vs奥格斯堡": "客胜",
    "周六015_法兰克福vs海登海姆": "客胜",
    "周六016_勒沃库森vs拜仁": "客胜",
    "周六017_伯恩利vs伯恩茅斯": "平",
    "周六018_马竞vs赫塔费": "客胜",
    "周六019_洛里昂vs朗斯": "平",
    "周六020_那不勒斯vs莱切": "主胜",
    "周六021_莫尔德vs罗森博格": "主胜",
    "周六022_阿森纳vs埃弗顿": "主胜",
    "周六023_切尔西vs纽卡斯尔": "主胜",
    "周六024_汉堡vs科隆": "客胜",
    "周六025_奥维耶多vs巴伦西亚": "平",
    "周六026_埃因霍温vs奈梅亨": "主胜",
    "周六027_赛哈特海湾vs利雅得胜利": "客胜",
    "周六028_乌迪内斯vs尤文图斯": "平",
    "周六029_西汉姆联vs曼城": "客胜",
    "周六030_皇马vs埃尔切": "主胜",
    "周六031_阿罗卡vs本菲卡": "客胜",
    "周六032_达拉斯vs圣迭戈FC": "主胜",
    
    # 周日
    "周日001_日本女vs菲律宾女": "主胜",
    "周日002_长崎航海vs福冈黄蜂": "主胜",
    "周日003_济州SKvs首尔FC": "客胜",
    "周日004_浦项制铁vs仁川联": "平",
    "周日005_墨胜利vs麦克阿瑟FC": "客胜",
    "周日006_特温特vs乌德勒支": "客胜",
    "周日007_维罗纳vs热那亚": "客胜",
    "周日008_沙尔克04vs汉诺威96": "主胜",
    "周日009_马洛卡vs西班牙人": "平",
    "周日010_费耶诺德vsSBV精英": "主胜",
    "周日011_克里斯蒂vs布兰": "客胜",
    "周日012_水晶宫vs利兹联": "平",
    "周日013_诺丁汉vs富勒姆": "客胜",
    "周日014_曼联vs维拉": "主胜",
    "周日015_比萨vs卡利亚里": "平",
    "周日016_萨索洛vs博洛尼亚": "主胜",
    "周日017_不来梅vs美因茨": "主胜",
    "周日018_巴萨vs塞维利亚": "主胜",
    "周日019_瓦勒伦加vs桑纳菲": "主胜",
    "周日020_勒阿弗尔vs里昂": "客胜",
    "周日021_利物浦vs热刺": "主胜",
    "周日022_弗赖堡vs柏林联合": "主胜",
    "周日023_科莫vs罗马": "主胜",
    "周日024_贝蒂斯vs塞尔塔": "主胜",
    "周日025_斯图加特vs莱红牛": "客胜",
    "周日026_拉齐奥vsAC米兰": "平",
    "周日027_皇家社会vs奥萨苏纳": "主胜",
    "周日028_波尔图vs摩雷伦斯": "主胜",
    "周日029_温哥华vs明尼苏达": "主胜",
}

# 修正预测名称映射（因为文件命名可能不同）
name_mapping = {
    "周五002_Austral女vs朝鲜女": "周五002_Austral女vs朝鲜女",
    "周五002_澳大利女vs朝鲜女": "周五002_Austral女vs朝鲜女",
    "周五001_布里斯班vs西悉尼": "周五001_布里斯班vs西悉尼",
    "周五003_马格德堡vs达姆施塔": "周五003_马格德堡vs达姆施塔",
    "周五004_胡巴尔卡德西亚vs吉达国民": "周五004_胡巴尔卡德西亚vs吉达国民",
    "周五005_克莱蒙vs波城FC": "周五005_克莱蒙vs波城FC",
    "周五006_兹沃勒vs格罗宁根": "周五006_兹沃勒vs格罗宁根",
    "周五007_坎布尔vs罗达JC": "周五007_坎布尔vs罗达JC",
    "周五008_门兴vs圣保利": "周五008_门兴vs圣保利",
    "周五009_都灵vs帕尔马": "周五009_都灵vs帕尔马",
    "周五010_马赛vs欧塞尔": "周五010_马赛vs欧塞尔",
    "周五011_雷克斯vs斯旺西": "周五011_雷克斯vs斯旺西",
    "周五012_阿拉维斯vs比利亚雷": "周五012_阿拉维斯vs比利亚雷",
}

# 使用实际结果中的key来匹配预测
def normalize_result(result):
    if "平" in result:
        return "平"
    elif "主胜" in result:
        return "主胜"
    elif "客胜" in result:
        return "客胜"
    return result

def compare():
    correct = 0
    wrong = 0
    details = []
    
    all_matches = set(actual_results.keys())
    
    for match in sorted(all_matches):
        actual = normalize_result(actual_results.get(match, "未知"))
        
        # 查找预测结果
        predicted = None
        for pred_key, pred_val in predictions.items():
            # 简化匹配逻辑
            match_short = match.replace("周五", "").replace("周六", "").replace("周日", "")
            pred_short = pred_key.replace("周五", "").replace("周六", "").replace("周日", "")
            if match_short in pred_short or pred_short in match_short:
                predicted = pred_val
                break
        
        if predicted is None:
            predicted = "未知"
            print(f"Warning: No prediction found for {match}")
            continue
        
        predicted = normalize_result(predicted)
        
        is_correct = (actual == predicted)
        
        if is_correct:
            correct += 1
            status = "[OK]"
        else:
            wrong += 1
            status = "[X]"
        
        details.append(f"{status} {match}: 预测={predicted}, 实际={actual}")
    
    total = correct + wrong
    hit_rate = correct / total * 100 if total > 0 else 0
    
    print("=" * 80)
    print("V5算法 比赛预测结果比对")
    print("=" * 80)
    
    # 分类别统计
    friday_matches = [k for k in all_matches if "周五" in k]
    saturday_matches = [k for k in all_matches if "周六" in k]
    sunday_matches = [k for k in all_matches if "周日" in k]
    
    def count_hit(matches):
        c = 0
        for m in matches:
            actual = normalize_result(actual_results.get(m, ""))
            predicted = None
            for pred_key, pred_val in predictions.items():
                match_short = m.replace("周五", "").replace("周六", "").replace("周日", "")
                pred_short = pred_key.replace("周五", "").replace("周六", "").replace("周日", "")
                if match_short in pred_short or pred_short in match_short:
                    predicted = normalize_result(pred_val)
                    break
            if predicted and actual == predicted:
                c += 1
        return c, len(matches)
    
    friday_hit, friday_total = count_hit(friday_matches)
    saturday_hit, saturday_total = count_hit(saturday_matches)
    sunday_hit, sunday_total = count_hit(sunday_matches)
    
    print(f"\n[周五] 预测正确: {friday_hit}/{friday_total} ({friday_hit/friday_total*100:.1f}%)")
    print(f"[周六] 预测正确: {saturday_hit}/{saturday_total} ({saturday_hit/saturday_total*100:.1f}%)")
    print(f"[周日] 预测正确: {sunday_hit}/{sunday_total} ({sunday_hit/sunday_total*100:.1f}%)")
    
    print(f"\n[总计] 预测正确: {correct}/{total} ({hit_rate:.1f}%)")
    print("\n" + "=" * 80)
    print("详细比对:")
    print("=" * 80)
    
    for d in details:
        print(d)
    
    return hit_rate

if __name__ == "__main__":
    hit_rate = compare()
    print(f"\n最终命中率: {hit_rate:.1f}%")
    if hit_rate >= 80:
        print("[OK] 命中率 >= 80%，无需优化算法")
    else:
        print("[X] 命中率 < 80%，需要优化算法")
