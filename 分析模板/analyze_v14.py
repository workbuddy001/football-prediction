# V14 算法 - 诱盘识别与反向思维
# 基于网上学到的技巧：
# 1. 区分主动与被动调整
# 2. 临场与初盘方向相反需警惕
# 3. 特定模式识别冷门

import re
import os
from pathlib import Path

def parse_source_file(filepath):
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
        data['home_draws'] = int(home_form_match.group(1))
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


def detect_trap(initial_odds, realtime_odds, home_wins, away_wins):
    """
    诱盘检测
    检测赔率变化与基本面是否矛盾
    """
    if not initial_odds or not realtime_odds or len(initial_odds) != len(realtime_odds):
        return 0
    
    trap_score = 0
    
    # 提取典型公司的赔率（取前5家权威公司）
    sample_size = min(5, len(initial_odds))
    
    for i in range(sample_size):
        init = initial_odds[i]
        rt = realtime_odds[i]
        
        # 初盘低赔方（热门）
        if init[0] < init[2]:  # 主队是热门
            # 临场主胜升赔
            if rt[0] > init[0] + 0.1:
                # 但客队近况更差
                if away_wins < home_wins:
                    trap_score += 1  # 可能是诱盘
        elif init[2] < init[0]:  # 客队是热门
            if rt[2] > init[2] + 0.1:
                if home_wins < away_wins:
                    trap_score += 1
    
    return trap_score


def predict_v14(data):
    """V14 预测算法 - 诱盘识别版"""
    home = data.get('home_team', '')
    away = data.get('away_team', '')
    initial = data.get('initial_odds', [])
    rt = data.get('realtime_odds', [])
    
    if not rt:
        return "未知"
    
    # 基础概率
    avg_home = sum(o[0] for o in rt) / len(rt)
    avg_draw = sum(o[1] for o in rt) / len(rt)
    avg_away = sum(o[2] for o in rt) / len(rt)
    
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
    if macao:
        if '贏' in macao or '赢' in macao:
            if home in macao:
                prob_home += 0.12
            elif away in macao:
                prob_away += 0.12
    
    # 诱盘检测
    trap_score = 0
    if initial and len(initial) == len(rt):
        trap_score = detect_trap(initial, rt, home_wins, away_wins)
    
    # 如果检测到诱盘信号，反向操作
    if trap_score >= 2:
        # 初盘低赔方可能被高估
        if avg_home < avg_away:
            prob_away += 0.10
        else:
            prob_home += 0.10
    
    # 强队近况
    if home_wins >= 4:
        prob_home += 0.05
    if away_wins >= 4:
        prob_away += 0.05
    
    # 概率优势
    if abs(prob_home - prob_away) > 0.12:
        if prob_home > prob_away:
            prob_home += 0.05
        else:
            prob_away += 0.05
    
    # 平局识别
    if home_draws >= 3 and away_draws >= 3:
        prob_draw += 0.08
    
    if 2.8 < avg_draw < 3.3 and abs(prob_home - prob_away) < 0.15:
        prob_draw += 0.06
    
    if home_goals < 12 and away_goals < 12:
        prob_draw += 0.05
    
    # 历史交锋
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


def analyze_folder_v14(folder_path):
    results = []
    files = sorted(Path(folder_path).glob('*.md'))
    
    for f in files:
        if '源数据' not in f.name:
            continue
        
        print(f"\n分析: {f.name}")
        
        try:
            data = parse_source_file(str(f))
            prediction = predict_v14(data)
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
        f.write("# V14 算法预测结果\n\n")
        for r in results:
            f.write(f"- {r['id']} {r['home']} vs {r['away']}: **{r['prediction']}** (联赛: {r['league']})\n")


if __name__ == "__main__":
    folders = [
        (r"d:\work\workbuddy\足球预测\分析模板\3.13", "3.13_V14预测.txt"),
        (r"d:\work\workbuddy\足球预测\分析模板\3.14", "3.14_V14预测.txt"),
        (r"d:\work\workbuddy\足球预测\分析模板\3.15", "3.15_V14预测.txt"),
    ]
    
    for folder, output in folders:
        print(f"\n{'='*60}")
        print(f"分析: {folder}")
        print('='*60)
        
        results = analyze_folder_v14(folder)
        save_results(results, output)
        
        print(f"\n已保存到: {output}")
        print(f"共分析: {len(results)} 场")
