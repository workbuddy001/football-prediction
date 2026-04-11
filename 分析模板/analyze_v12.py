# V12 最终优化版算法 - 基于V7最佳逻辑
# 结合概率判断、澳门推荐、平局识别

import re
import os
from pathlib import Path

def parse_source_file(filepath):
    """解析源数据文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    home_team = re.search(r'\| 主队 \| (.+) \|', content)
    away_team = re.search(r'\| 客队 \| (.+) \|', content)
    league = re.search(r'\| 赛事 \| (.+) \|', content)
    macao_tip = re.search(r'\| 澳门推荐 \| (.+) \|', content)
    
    home_form_match = re.search(r'\| 主队近况 \| 近10场，(\d+)胜(\d+)平(\d+)负 进(\d+)球 失(\d+)球 胜率(\d+)%', content)
    away_form_match = re.search(r'\| 客队近况 \| 近10场，(\d+)胜(\d+)平(\d+)负 进(\d+)球 失(\d+)球 胜率(\d+)%', content)
    
    home_form_str = re.search(r'\| 主队近况走势 \| (.+) \|', content)
    away_form_str = re.search(r'\| 客队近况走势 \| (.+) \|', content)
    
    history = re.search(r'\| 历史交锋 \| (.+) \|', content)
    
    initial_odds_match = re.findall(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', content.split('## 二、初盘赔率')[1].split('## 三、')[0])
    realtime_odds_match = re.findall(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', content.split('## 三、即时赔率')[1].split('## 四、')[0])
    
    jingcai = re.search(r'\| 主胜（.*赢） \| (\d+\.\d+) \|.*\| 平局 \| (\d+\.\d+) \|.*\| 客胜（.*赢） \| (\d+\.\d+) \|', content)
    
    data = {
        'home_team': home_team.group(1) if home_team else '',
        'away_team': away_team.group(1) if away_team else '',
        'league': league.group(1) if league else '',
        'macao_tip': macao_tip.group(1).strip() if macao_tip else '',
    }
    
    if home_form_match:
        data['home_wins'] = int(home_form_match.group(1))
        data['home_draws'] = int(home_form_match.group(2))
        data['home_losses'] = int(home_form_match.group(3))
        data['home_goals'] = int(home_form_match.group(4))
        data['home_lost'] = int(home_form_match.group(5))
        data['home_win_rate'] = int(home_form_match.group(6))
    
    if away_form_match:
        data['away_wins'] = int(away_form_match.group(1))
        data['away_draws'] = int(away_form_match.group(2))
        data['away_losses'] = int(away_form_match.group(3))
        data['away_goals'] = int(away_form_match.group(4))
        data['away_lost'] = int(away_form_match.group(5))
        data['away_win_rate'] = int(away_form_match.group(6))
    
    data['home_form_str'] = home_form_str.group(1).strip() if home_form_str else ''
    data['away_form_str'] = away_form_str.group(1).strip() if away_form_str else ''
    data['history'] = history.group(1) if history else ''
    
    data['initial_odds'] = [(float(h), float(d), float(a)) for h, d, a in initial_odds_match]
    data['realtime_odds'] = [(float(h), float(d), float(a)) for h, d, a in realtime_odds_match]
    
    if jingcai:
        data['jingcai_home'] = float(jingcai.group(1))
        data['jingcai_draw'] = float(jingcai.group(2))
        data['jingcai_away'] = float(jingcai.group(3))
    
    return data


def predict_v12(data):
    """V12 预测算法 - 基于V7逻辑的优化版"""
    home = data.get('home_team', '')
    away = data.get('away_team', '')
    rt = data.get('realtime_odds', [])
    
    if not rt:
        return "未知"
    
    # 计算即时赔率平均值
    avg_home = sum(o[0] for o in rt) / len(rt)
    avg_draw = sum(o[1] for o in rt) / len(rt)
    avg_away = sum(o[2] for o in rt) / len(rt)
    
    # 转换为概率
    prob_home = 1 / avg_home if avg_home > 0 else 0
    prob_draw = 1 / avg_draw if avg_draw > 0 else 0
    prob_away = 1 / avg_away if avg_away > 0 else 0
    total = prob_home + prob_draw + prob_away
    if total > 0:
        prob_home /= total
        prob_draw /= total
        prob_away /= total
    
    # 近况数据
    home_wins = data.get('home_wins', 0)
    home_draws = data.get('home_draws', 0)
    home_win_rate = data.get('home_win_rate', 0)
    home_goals = data.get('home_goals', 0)
    home_lost = data.get('home_lost', 0)
    
    away_wins = data.get('away_wins', 0)
    away_draws = data.get('away_draws', 0)
    away_win_rate = data.get('away_win_rate', 0)
    away_goals = data.get('away_goals', 0)
    away_lost = data.get('away_lost', 0)
    
    # 澳门推荐
    macao = data.get('macao_tip', '')
    macao_home = '贏' in macao or '赢' in macao
    
    # 1. 澳门推荐权威判断 (权重最大)
    if macao_home:
        if home in macao:
            prob_home += 0.10  # 提升主胜概率
        elif away in macao:
            prob_away += 0.10  # 提升客胜概率
    
    # 2. 强队近况判断 (4场胜以上)
    if home_wins >= 4:
        prob_home += 0.05
    if away_wins >= 4:
        prob_away += 0.05
    
    # 3. 概率优势判断 (需超过12%差距)
    prob_diff = abs(prob_home - prob_away)
    if prob_diff > 0.12:
        if prob_home > prob_away:
            prob_home += 0.05
        else:
            prob_away += 0.05
    
    # 4. 低赔方近况不佳判断
    if avg_home < 1.8:
        if home_wins < 2 and away_wins >= 3:
            prob_away += 0.08
    
    if avg_away < 1.8:
        if away_wins < 2 and home_wins >= 3:
            prob_home += 0.08
    
    # 5. 平局识别
    # 5.1 双方平局都很多
    if home_draws >= 3 and away_draws >= 3:
        prob_draw += 0.08
    
    # 5.2 赔率显示接近且平局偏低
    if 2.8 < avg_draw < 3.3 and prob_diff < 0.15:
        prob_draw += 0.06
    
    # 5.3 双方都是守强攻弱
    if home_goals < 12 and away_goals < 12:
        prob_draw += 0.05
    
    # 5.4 盘路都是下坡走势
    if 'D' in data.get('home_form_str', '') or 'L' in data.get('home_form_str', ''):
        if 'D' in data.get('away_form_str', '') or 'L' in data.get('away_form_str', ''):
            prob_draw += 0.04
    
    # 5.5 历史交锋多平局
    if data.get('history', ''):
        match = re.search(r'(\d+)胜(\d+)和(\d+)负', data['history'])
        if match:
            draws = int(match.group(2))
            total = int(match.group(1)) + draws + int(match.group(3))
            if total > 0 and draws / total > 0.3:
                prob_draw += 0.05
    
    # 重新归一化
    total = prob_home + prob_draw + prob_away
    if total > 0:
        prob_home /= total
        prob_draw /= total
        prob_away /= total
    
    # 决策
    if prob_draw > 0.28 and prob_draw >= prob_home and prob_draw >= prob_away:
        return "平局"
    elif prob_home >= prob_away:
        return "主胜"
    else:
        return "客胜"


def analyze_folder_v12(folder_path):
    results = []
    files = sorted(Path(folder_path).glob('*.md'))
    
    for f in files:
        if '源数据' not in f.name:
            continue
        
        print(f"\n分析: {f.name}")
        
        try:
            data = parse_source_file(str(f))
            prediction = predict_v12(data)
            match_id = f.name.split('_')[0]
            
            results.append({
                'id': match_id,
                'home': data.get('home_team', ''),
                'away': data.get('away_team', ''),
                'prediction': prediction,
                'league': data.get('league', '')
            })
            
            print(f"  预测: {prediction}")
            
        except Exception as e:
            print(f"  错误: {e}")
    
    return results


def save_results(results, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# V12 算法预测结果\n\n")
        for r in results:
            f.write(f"- {r['id']} {r['home']} vs {r['away']}: **{r['prediction']}** (联赛: {r['league']})\n")


if __name__ == "__main__":
    folders = [
        (r"d:\work\workbuddy\足球预测\分析模板\3.13", "3.13_V12预测.txt"),
        (r"d:\work\workbuddy\足球预测\分析模板\3.14", "3.14_V12预测.txt"),
        (r"d:\work\workbuddy\足球预测\分析模板\3.15", "3.15_V12预测.txt"),
    ]
    
    for folder, output in folders:
        print(f"\n{'='*60}")
        print(f"分析: {folder}")
        print('='*60)
        
        results = analyze_folder_v12(folder)
        save_results(results, output)
        
        print(f"\n已保存到: {output}")
        print(f"共分析: {len(results)} 场")
