# 回归测试 - 详细统计脚本
import sys
sys.path.append('.')
from final_retrospect import *

# 运行分析
actual_results = load_actual_results()

all_results = []
folders = [
    (r"d:\work\workbuddy\足球预测\分析模板\3.13", "周五"),
    (r"d:\work\workbuddy\足球预测\分析模板\3.14", "周六"),
    (r"d:\work\workbuddy\足球预测\分析模板\3.15", "周日"),
]

for folder, day in folders:
    results = analyze_folder(folder, day)
    all_results.extend(results)

all_results.sort(key=lambda x: x['confidence'], reverse=True)

# 详细统计
print("=" * 80)
print("回归测试详细统计")
print("=" * 80)

# 按推荐类型统计
recommendation_types = ['强烈推荐', '降权', '排除', '谨慎推荐', '一般推荐', '不推荐']

for rec_type in recommendation_types:
    recall = [r for r in all_results if r['final']['recommendation'] == rec_type]
    correct = sum(1 for r in recall 
                 if {'home': '主胜', 'draw': '平局', 'away': '客胜'}[r['choice']] == actual_results.get(r['match_id'], ''))
    if recall:
        hit_rate = correct / len(recall) * 100
        print(f"\n【{rec_type}】")
        print(f"  场次: {len(recall)}, 正确: {correct}, 命中率: {hit_rate:.1f}%")
        print(f"  比赛列表:")
        for r in recall:
            match_id = r['match_id']
            actual = actual_results.get(match_id, '')
            pred = {'home': '主胜', 'draw': '平局', 'away': '客胜'}[r['choice']]
            is_correct = "O" if pred == actual else "X"
            print(f"    {r['filename']}: 预测={pred}({r['confidence']:.0f}%) 实际={actual} {is_correct}")
            print(f"      原因: {r['final']['reason']}")

# 总结
print("\n" + "=" * 80)
print("总结")
print("=" * 80)

total = len([r for r in all_results if r['match_id'] in actual_results])
correct = sum(1 for r in all_results if r['match_id'] in actual_results 
              and {'home': '主胜', 'draw': '平局', 'away': '客胜'}[r['choice']] == actual_results.get(r['match_id'], ''))
print(f"\n总比赛数: {total}, 正确: {correct}, 命中率: {correct/total*100:.1f}%")
