"""
提取3.10和3.11比赛的关键数据
"""
import os
import re

def extract_match_data(folder_path):
    """从源数据文件中提取关键信息"""
    results = []
    
    for filename in os.listdir(folder_path):
        if not filename.endswith('_源数据.md'):
            continue
            
        filepath = os.path.join(folder_path, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取比赛编号和名称
        match = re.search(r'编号：(\w+\d+)\|', content)
        if not match:
            continue
        match_id = match.group(1)
        
        # 提取主客队名称
        teams = re.search(r'主队\s*\|\s*(\S+).*客队\s*\|\s*(\S+)', content, re.DOTALL)
        if not teams:
            continue
        home_team = teams.group(1).strip()
        away_team = teams.group(2).strip()
        
        # 提取主客队胜率
        home_rate_match = re.search(r'主队近况.*?胜率(\d+)%', content)
        away_rate_match = re.search(r'客队近况.*?胜率(\d+)%', content)
        
        if not home_rate_match or not away_rate_match:
            continue
            
        home_rate = int(home_rate_match.group(1))
        away_rate = int(away_rate_match.group(1))
        
        # 提取初盘和即时赔率
        initial_odds_match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
        realtime_odds_match = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
        
        if not initial_odds_match or not realtime_odds_match:
            continue
        
        # 计算8的数量
        def count_eights(odds_str):
            count = 0
            # 提取所有赔率数字
            numbers = re.findall(r'\d+\.?\d*', odds_str)
            for num in numbers:
                # 检查末尾是否为8
                if '.' in num:
                    if num.endswith('8'):
                        count += 1
                else:
                    if num.endswith('8'):
                        count += 1
            return count
        
        initial_str = initial_odds_match.group(1)
        realtime_str = realtime_odds_match.group(1)
        
        # 提取主胜、平局、客胜的赔率
        def extract_odds_by_type(odds_str):
            # 提取所有 (主胜, 平局, 客胜) 元组
            tuples = re.findall(r'\((\d+\.?\d*),\s*(\d+\.?\d*),\s*(\d+\.?\d*)\)', odds_str)
            if not tuples:
                return [], [], []
            
            home = [float(t[0]) for t in tuples]
            draw = [float(t[1]) for t in tuples]
            away = [float(t[2]) for t in tuples]
            return home, draw, away
        
        home_odds_i, draw_odds_i, away_odds_i = extract_odds_by_type(initial_str)
        home_odds_r, draw_odds_r, away_odds_r = extract_odds_by_type(realtime_str)
        
        # 计算各选项的平均赔率
        avg_home_i = sum(home_odds_i) / len(home_odds_i) if home_odds_i else 0
        avg_draw_i = sum(draw_odds_i) / len(draw_odds_i) if draw_odds_i else 0
        avg_away_i = sum(away_odds_i) / len(away_odds_i) if away_odds_i else 0
        
        avg_home_r = sum(home_odds_r) / len(home_odds_r) if home_odds_r else 0
        avg_draw_r = sum(draw_odds_r) / len(draw_odds_r) if draw_odds_r else 0
        avg_away_r = sum(away_odds_r) / len(away_odds_r) if away_odds_r else 0
        
        # 计算末尾8的数量
        def count_eights_in_list(odds_list):
            count = 0
            for odd in odds_list:
                odd_str = f"{odd:.2f}"
                if odd_str.endswith('8'):
                    count += 1
            return count
        
        home_eight_i = count_eights_in_list(home_odds_i)
        draw_eight_i = count_eights_in_list(draw_odds_i)
        away_eight_i = count_eights_in_list(away_odds_i)
        
        home_eight_r = count_eights_in_list(home_odds_r)
        draw_eight_r = count_eights_in_list(draw_odds_r)
        away_eight_r = count_eights_in_list(away_odds_r)
        
        total_eight_i = home_eight_i + draw_eight_i + away_eight_i
        total_eight_r = home_eight_r + draw_eight_r + away_eight_r
        eight_change = total_eight_r - total_eight_i
        
        # 确定V7预测（概率最高的选项）
        prob_home = 1 / avg_home_i if avg_home_i > 0 else 0
        prob_draw = 1 / avg_draw_i if avg_draw_i > 0 else 0
        prob_away = 1 / avg_away_i if avg_away_i > 0 else 0
        
        total_prob = prob_home + prob_draw + prob_away
        prob_home /= total_prob
        prob_draw /= total_prob
        prob_away /= total_prob
        
        # V7预测
        if prob_home > prob_draw and prob_home > prob_away:
            v7 = "主胜"
            v7_prob = prob_home
        elif prob_away > prob_draw:
            v7 = "客胜"
            v7_prob = prob_away
        else:
            v7 = "平局"
            v7_prob = prob_draw
        
        confidence = int(v7_prob * 100)
        
        results.append({
            'id': match_id,
            'match': f"{home_team} vs {away_team}",
            'v7': v7,
            'confidence': confidence,
            'home_rate': home_rate,
            'away_rate': away_rate,
            'eight_change': eight_change,
            'home_eight_change': home_eight_r - home_eight_i,
            'draw_eight_change': draw_eight_r - draw_eight_i,
            'away_eight_change': away_eight_r - away_eight_i,
        })
    
    return results

# 提取3.10和3.11的数据
results_310 = extract_match_data('d:/work/workbuddy/足球预测/分析模板/3.10')
results_311 = extract_match_data('d:/work/workbuddy/足球预测/分析模板/3.11')

print("=" * 100)
print("3.10 比赛数据提取")
print("=" * 100)
for r in sorted(results_310, key=lambda x: x['id']):
    print(f"{r['id']}: {r['match']}, V7:{r['v7']}({r['confidence']}%), 状态(主{r['home_rate']}% vs 客{r['away_rate']}%), 8变化:{r['eight_change']:+d}")

print("\n" + "=" * 100)
print("3.11 比赛数据提取")
print("=" * 100)
for r in sorted(results_311, key=lambda x: x['id']):
    print(f"{r['id']}: {r['match']}, V7:{r['v7']}({r['confidence']}%), 状态(主{r['home_rate']}% vs 客{r['away_rate']}%), 8变化:{r['eight_change']:+d}")
