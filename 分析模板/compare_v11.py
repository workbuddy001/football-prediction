# V11 预测结果比对脚本

# 实际结果
actual_results = {
    # 周五 (3.13)
    "周五001": "平局",  # 布里斯班 2:2 西悉尼
    "周五002": "客胜",  # 澳大利亚女 2:1 朝鲜女 -> 主胜
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
    
    # 周六 (3.14)
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
    
    # 周日 (3.15)
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
}

# 读取V11预测结果
def load_predictions(file_path):
    predictions = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('- '):
                import re
                match = re.search(r'(周五|周六|周日)(\d+)', line)
                if match:
                    match_id = match.group(1) + match.group(2)
                    if '**平局**' in line:
                        predictions[match_id] = '平局'
                    elif '**客胜**' in line:
                        predictions[match_id] = '客胜'
                    elif '**主胜**' in line:
                        predictions[match_id] = '主胜'
    return predictions

# 比对函数
def compare_results(predictions, actuals):
    correct = 0
    wrong = 0
    errors = []
    
    for match_id, predicted in predictions.items():
        if match_id not in actuals:
            continue
        
        actual = actuals[match_id]
        is_correct = (predicted == actual)
        
        if is_correct:
            correct += 1
            status = "[OK]"
        else:
            wrong += 1
            status = "[X]"
            errors.append(f"{status} {match_id}: 预测={predicted}, 实际={actual}")
        
        print(f"{status} {match_id}: 预测={predicted}, 实际={actual}")
    
    return correct, wrong, errors

# 主程序
if __name__ == "__main__":
    predictions_313 = load_predictions("3.13_V11预测.txt")
    predictions_314 = load_predictions("3.14_V11预测.txt")
    predictions_315 = load_predictions("3.15_V11预测.txt")
    
    all_predictions = {**predictions_313, **predictions_314, **predictions_315}
    
    print("=" * 60)
    print("V11 预测结果比对")
    print("=" * 60)
    
    print("\n--- 3.13 周五 ---")
    correct_313, wrong_313, _ = compare_results(predictions_313, actual_results)
    total_313 = correct_313 + wrong_313
    hit_313 = correct_313 / total_313 * 100 if total_313 > 0 else 0
    print(f"周五: {correct_313}/{total_313} = {hit_313:.1f}%")
    
    print("\n--- 3.14 周六 ---")
    correct_314, wrong_314, _ = compare_results(predictions_314, actual_results)
    total_314 = correct_314 + wrong_314
    hit_314 = correct_314 / total_314 * 100 if total_314 > 0 else 0
    print(f"周六: {correct_314}/{total_314} = {hit_314:.1f}%")
    
    print("\n--- 3.15 周日 ---")
    correct_315, wrong_315, _ = compare_results(predictions_315, actual_results)
    total_315 = correct_315 + wrong_315
    hit_315 = correct_315 / total_315 * 100 if total_315 > 0 else 0
    print(f"周日: {correct_315}/{total_315} = {hit_315:.1f}%")
    
    total = total_313 + total_314 + total_315
    correct = correct_313 + correct_314 + correct_315
    hit_rate = correct / total * 100 if total > 0 else 0
    
    print("\n" + "=" * 60)
    print(f"总计: {correct}/{total} = {hit_rate:.1f}%")
    print("=" * 60)
    
    if hit_rate >= 80:
        print("[OK] 命中率 >= 80%，无需优化算法")
    else:
        print("[X] 命中率 < 80%，需要继续优化")
