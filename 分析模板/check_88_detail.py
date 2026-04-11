import re, os, sys
sys.path.append('.')
from final_retrospect import extract_odds_from_file, analyze_match_v7, analyze_8_pattern

# 检查置信度>=55%的比赛
high_conf_matches = ['周日001','周六008','周六001','周日018','周日010','周五010','周六013','周六012','周六014','周六016','周日011','周六015','周日006','周日014','周五007']

print("检查置信度>=55%比赛中的88情况：")
print("="*80)

for mid in high_conf_matches:
    # 找到对应比赛
    for folder in [r'd:\work\workbuddy\足球预测\分析模板\3.13',
                   r'd:\work\workbuddy\足球预测\分析模板\3.14',
                   r'd:\work\workbuddy\足球预测\分析模板\3.15']:
        for f in os.listdir(folder):
            if not f.endswith('_源数据.md'): continue
            if mid in f:
                filepath = os.path.join(folder, f)
                data = extract_odds_from_file(filepath)
                result = analyze_match_v7(data)
                if result:
                    eight = analyze_8_pattern(data['initial_odds'], data['realtime_odds'], result['choice'])
                    
                    # 检查各选项是否有88
                    real_home = [o[0] for o in data['realtime_odds']]
                    real_draw = [o[1] for o in data['realtime_odds']]
                    real_away = [o[2] for o in data['realtime_odds']]
                    
                    home_88 = any(f"{o:.2f}".endswith('88') for o in real_home)
                    draw_88 = any(f"{o:.2f}".endswith('88') for o in real_draw)
                    away_88 = any(f"{o:.2f}".endswith('88') for o in real_away)
                    
                    choice_name = {'home': '主胜', 'draw': '平局', 'away': '客胜'}[result['choice']]
                    choice_has_88 = {'home': home_88, 'draw': draw_88, 'away': away_88}[result['choice']]
                    
                    print(f"\n{mid}: {data['home_team']} vs {data['away_team']}")
                    print(f"  V7预测: {choice_name} ({result['confidence']:.0f}%)")
                    print(f"  主胜有88: {home_88}, 平局有88: {draw_88}, 客胜有88: {away_88}")
                    print(f"  V7选项有88: {choice_has_88}")
                break
