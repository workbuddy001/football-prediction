# 调试脚本
import sys
import re
sys.path.append('.')
from final_retrospect import *

actual_results = load_actual_results()
folders = [
    (r"d:\work\workbuddy\足球预测\分析模板\3.14", "周六"),
]
for folder, day in folders:
    results = analyze_folder(folder, day)
    for r in results:
        if '中国女' in r['home_team']:
            print(f"比赛: {r['home_team']} vs {r['away_team']}")
            print(f"V7预测: {r['choice']} ({r['confidence']:.0f}%)")
            print(f"澳门推荐: {r['data']['macao_tip']}")
            print(f"主队: {r['data']['home_team']}, 客队: {r['data']['away_team']}")
            print(f"8分析: {r['eight_analysis']}")
            print(f"最终决策: {r['final']}")
