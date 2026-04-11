# -*- coding: utf-8 -*-
"""
验证"中庸分布与状态不匹配"新规则的准确性
"""

import sys
sys.path.insert(0, 'd:/work/workbuddy/足球预测/分析模板')

from v7_8_segment_analyze import analyze_directory, parse_source_file, predict_match, get_segment
from actual_results_corrected import ACTUAL_RESULTS

def verify_predictions(dir_path, date_prefix):
    """验证预测结果"""
    results = analyze_directory(dir_path)
    
    print(f"\n{'='*100}")
    print(f"验证 {date_prefix} 的'中庸陷阱'预测")
    print(f"{'='*100}")
    
    moderate_trap_predictions = []
    
    for r in results:
        pred = r.get('prediction', '')
        reason_brief = r.get('reason_brief', '')
        
        # 只关注中庸陷阱预测
        if '中庸陷阱' in reason_brief:
            match_id = r['date_num']
            actual = ACTUAL_RESULTS.get(match_id, '未知')
            is_correct = (pred == actual)
            
            moderate_trap_predictions.append({
                'match_id': match_id,
                'match': f"{r['home_team']} vs {r['away_team']}",
                'prediction': pred,
                'actual': actual,
                'is_correct': is_correct,
                'reason': r.get('reason', ''),
                'confidence': r['v7']['confidence'],
                'form_diff': r.get('form_diff'),
                'eight_change': f"[{r['eight_change']['home_8']:+d},{r['eight_change']['draw_8']:+d},{r['eight_change']['away_8']:+d}]"
            })
    
    if not moderate_trap_predictions:
        print(f"\n{date_prefix} 没有触发'中庸陷阱'规则的比赛")
        return
    
    print(f"\n共触发 {len(moderate_trap_predictions)} 场'中庸陷阱'预测:\n")
    print(f"{'编号':<8} {'对阵':<25} {'预测':>6} {'实际':>6} {'结果':>6} {'置信度':>6} {'状态差':>8} {'8变化':>14} {'理由'}")
    print("-" * 120)
    
    correct = 0
    for p in moderate_trap_predictions:
        result_str = "对" if p['is_correct'] else "错"
        if p['actual'] == '未知':
            result_str = "?"
        else:
            correct += 1 if p['is_correct'] else 0
        
        form_diff_str = f"{p['form_diff']:+d}%" if p['form_diff'] is not None else "N/A"
        print(f"{p['match_id']:<8} {p['match']:<25} {p['prediction']:>6} {p['actual']:>6} {result_str:>6} {p['confidence']:>5}% {form_diff_str:>8} {p['eight_change']:>14} {p['reason'][:30]}")
    
    known_results = [p for p in moderate_trap_predictions if p['actual'] != '未知']
    if known_results:
        accuracy = correct / len(known_results) * 100
        print(f"\n准确率: {accuracy:.1f}% ({correct}/{len(known_results)})")
    
    return moderate_trap_predictions

# 验证3.14
print("\n" + "="*100)
print("分析 3.14 数据")
print("="*100)
results_314 = verify_predictions("3.14", "3.14")

# 验证3.15
print("\n" + "="*100)
print("分析 3.15 数据")
print("="*100)
results_315 = verify_predictions("3.15", "3.15")

# 汇总
print("\n" + "="*100)
print("汇总统计")
print("="*100)

all_predictions = []
if results_314:
    all_predictions.extend(results_314)
if results_315:
    all_predictions.extend(results_315)

if all_predictions:
    known = [p for p in all_predictions if p['actual'] != '未知']
    correct = sum(1 for p in known if p['is_correct'])
    if known:
        print(f"\n总计触发: {len(all_predictions)} 场")
        print(f"已知结果: {len(known)} 场")
        print(f"正确预测: {correct} 场")
        print(f"整体准确率: {correct/len(known)*100:.1f}%")
