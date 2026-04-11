# V13 预测结果比对脚本

actual_results = {
    "周五001": "平局", "周五002": "客胜", "周五003": "平局", "周五004": "主胜",
    "周五005": "客胜", "周五006": "平局", "周五007": "平局", "周五008": "主胜",
    "周五009": "主胜", "周五010": "主胜", "周五011": "主胜", "周五012": "平局",
    
    "周六001": "平局", "周六002": "客胜", "周六003": "平局", "周六004": "客胜",
    "周六005": "主胜", "周六006": "主胜", "周六007": "平局", "周六008": "主胜",
    "周六009": "主胜", "周六010": "客胜", "周六011": "主胜", "周六012": "平局",
    "周六013": "平局", "周六014": "主胜", "周六015": "主胜", "周六016": "平局",
    "周六017": "平局", "周六018": "主胜", "周六019": "主胜", "周六020": "主胜",
    "周六021": "主胜", "周六022": "主胜", "周六023": "客胜", "周六024": "平局",
    "周六025": "主胜", "周六026": "客胜", "周六027": "客胜", "周六028": "客胜",
    "周六029": "平局", "周六030": "主胜", "周六031": "客胜", "周六032": "平局",
    
    "周日001": "主胜", "周日002": "主胜", "周日003": "客胜", "周日004": "平局",
    "周日005": "主胜", "周日006": "客胜", "周日007": "客胜", "周日008": "平局",
    "周日009": "主胜", "周日010": "主胜", "周日011": "主胜", "周日012": "平局",
    "周日013": "平局", "周日014": "主胜", "周日015": "主胜", "周日016": "客胜",
    "周日017": "客胜", "周日018": "主胜", "周日019": "主胜", "周日020": "平局",
    "周日021": "平局", "周日022": "客胜", "周日023": "主胜", "周日024": "平局",
    "周日025": "主胜", "周日026": "主胜", "周日027": "主胜", "周日028": "主胜",
    "周日029": "主胜",
}

def load_predictions(file_path):
    predictions = {}
    import re
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('- '):
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

def compare_results(predictions, actuals):
    correct = 0
    wrong = 0
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
        print(f"{status} {match_id}: 预测={predicted}, 实际={actual}")
    return correct, wrong

if __name__ == "__main__":
    predictions_313 = load_predictions("3.13_V13预测.txt")
    predictions_314 = load_predictions("3.14_V13预测.txt")
    predictions_315 = load_predictions("3.15_V13预测.txt")
    
    print("=" * 60)
    print("V13 预测结果比对")
    print("=" * 60)
    
    print("\n--- 3.13 周五 ---")
    correct_313, wrong_313 = compare_results(predictions_313, actual_results)
    total_313 = correct_313 + wrong_313
    hit_313 = correct_313 / total_313 * 100 if total_313 > 0 else 0
    print(f"周五: {correct_313}/{total_313} = {hit_313:.1f}%")
    
    print("\n--- 3.14 周六 ---")
    correct_314, wrong_314 = compare_results(predictions_314, actual_results)
    total_314 = correct_314 + wrong_314
    hit_314 = correct_314 / total_314 * 100 if total_314 > 0 else 0
    print(f"周六: {correct_314}/{total_314} = {hit_314:.1f}%")
    
    print("\n--- 3.15 周日 ---")
    correct_315, wrong_315 = compare_results(predictions_315, actual_results)
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
