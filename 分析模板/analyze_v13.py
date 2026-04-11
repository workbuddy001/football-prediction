# V13 算法 - 基于凯利指数和赔率变化趋势分析
# 结合网上搜索到的专业分析方法：
# 1. 凯利指数验证
# 2. 赔率变动趋势追踪
# 3. 多家机构对比法
# 4. 成交量辅助验证

import re
import os
from pathlib import Path
import math

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
    
    # 提取初盘和即时赔率
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


def calculate_kelly_index(odds_list, probability):
    """
    计算凯利指数
    凯利指数 = 赔率 * 概率
    若凯利指数 < 1，说明庄家有一定利润空间
    若凯利指数接近或超过1，可能存在高风险
    """
    if not odds_list or probability <= 0:
        return 1.0
    
    kelly_values = []
    for odd in odds_list:
        kelly = odd * probability
        kelly_values.append(kelly)
    
    return sum(kelly_values) / len(kelly_values)


def analyze_odds_change_trend(initial_odds, realtime_odds):
    """
    分析赔率变化趋势
    返回: (主队降赔次数, 平局降赔次数, 客队降赔次数, 总公司数)
    """
    if not initial_odds or not realtime_odds or len(initial_odds) != len(realtime_odds):
        return 0, 0, 0, 0
    
    home_down = 0
    draw_down = 0
    away_down = 0
    total = len(initial_odds)
    
    for i in range(total):
        init = initial_odds[i]
        rt = realtime_odds[i]
        
        # 降赔表示被买入（热门）
        if rt[0] < init[0] - 0.05:
            home_down += 1
        if rt[1] < init[1] - 0.05:
            draw_down += 1
        if rt[2] < init[2] - 0.05:
            away_down += 1
    
    return home_down, draw_down, away_down, total


def analyze_consensus(odds_list):
    """
    分析赔率共识度（分散性）
    使用变异系数(CV)
    """
    if not odds_list:
        return 0.3
    
    # 提取主胜赔率
    home_odds = [o[0] for o in odds_list]
    avg = sum(home_odds) / len(home_odds)
    variance = sum((x - avg) ** 2 for x in home_odds) / len(home_odds)
    std = math.sqrt(variance)
    cv = std / avg if avg > 0 else 0
    
    return cv


def predict_v13(data):
    """V13 预测算法 - 基于凯利指数和赔率变化趋势"""
    home = data.get('home_team', '')
    away = data.get('away_team', '')
    initial = data.get('initial_odds', [])
    rt = data.get('realtime_odds', [])
    
    if not rt:
        return "未知"
    
    # 1. 计算基础概率（基于即时赔率）
    avg_home = sum(o[0] for o in rt) / len(rt)
    avg_draw = sum(o[1] for o in rt) / len(rt)
    avg_away = sum(o[2] for o in rt) / len(rt)
    
    prob_home = 1 / avg_home if avg_home > 0 else 0
    prob_draw = 1 / avg_draw if avg_draw > 0 else 0
    prob_away = 1 / avg_away if avg_away > 0 else 0
    total_prob = prob_home + prob_draw + prob_away
    
    if total_prob > 0:
        prob_home /= total_prob
        prob_draw /= total_prob
        prob_away /= total_prob
    
    # 2. 凯利指数分析（新增）
    # 凯利指数越低，说明庄家越安全
    kelly_home = calculate_kelly_index([o[0] for o in rt], prob_home)
    kelly_draw = calculate_kelly_index([o[1] for o in rt], prob_draw)
    kelly_away = calculate_kelly_index([o[2] for o in rt], prob_away)
    
    # 凯利指数低于0.9的选项可能更有价值
    if kelly_home < 0.9:
        prob_home += 0.05
    if kelly_draw < 0.9:
        prob_draw += 0.03
    if kelly_away < 0.9:
        prob_away += 0.05
    
    # 3. 赔率变化趋势分析（新增）
    if initial and len(initial) == len(rt):
        home_down, draw_down, away_down, total = analyze_odds_change_trend(initial, rt)
        
        # 降赔表示热门
        if home_down > total * 0.6:
            prob_home += 0.08
        if away_down > total * 0.6:
            prob_away += 0.08
        if draw_down > total * 0.5:
            prob_draw += 0.03
    
    # 4. 赔率共识度分析
    cv = analyze_consensus(rt)
    consensus_threshold = 0.12
    
    if cv < consensus_threshold:
        # 共识度高，降低风险
        if prob_home > prob_away + 0.15:
            prob_home += 0.05
        elif prob_away > prob_home + 0.15:
            prob_away += 0.05
    else:
        # 分散性高，需要更保守
        pass
    
    # 5. 近况分析
    home_wins = data.get('home_wins', 0)
    home_draws = data.get('home_draws', 0)
    home_win_rate = data.get('home_win_rate', 0)
    home_goals = data.get('home_goals', 0)
    
    away_wins = data.get('away_wins', 0)
    away_draws = data.get('away_draws', 0)
    away_win_rate = data.get('away_win_rate', 0)
    away_goals = data.get('away_goals', 0)
    
    # 澳门推荐
    macao = data.get('macao_tip', '')
    if macao:
        if '贏' in macao or '赢' in macao:
            if home in macao:
                prob_home += 0.10
            elif away in macao:
                prob_away += 0.10
    
    # 强队近况
    if home_wins >= 4:
        prob_home += 0.05
    if away_wins >= 4:
        prob_away += 0.05
    
    # 6. 平局识别
    # 双方平局都很多
    if home_draws >= 3 and away_draws >= 3:
        prob_draw += 0.08
    
    # 赔率接近且平局偏低
    if 2.8 < avg_draw < 3.3 and abs(prob_home - prob_away) < 0.15:
        prob_draw += 0.06
    
    # 双方守强攻弱
    if home_goals < 12 and away_goals < 12:
        prob_draw += 0.05
    
    # 7. 历史交锋多平局
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


def analyze_folder_v13(folder_path):
    results = []
    files = sorted(Path(folder_path).glob('*.md'))
    
    for f in files:
        if '源数据' not in f.name:
            continue
        
        print(f"\n分析: {f.name}")
        
        try:
            data = parse_source_file(str(f))
            prediction = predict_v13(data)
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
        f.write("# V13 算法预测结果\n\n")
        for r in results:
            f.write(f"- {r['id']} {r['home']} vs {r['away']}: **{r['prediction']}** (联赛: {r['league']})\n")


if __name__ == "__main__":
    folders = [
        (r"d:\work\workbuddy\足球预测\分析模板\3.13", "3.13_V13预测.txt"),
        (r"d:\work\workbuddy\足球预测\分析模板\3.14", "3.14_V13预测.txt"),
        (r"d:\work\workbuddy\足球预测\分析模板\3.15", "3.15_V13预测.txt"),
    ]
    
    for folder, output in folders:
        print(f"\n{'='*60}")
        print(f"分析: {folder}")
        print('='*60)
        
        results = analyze_folder_v13(folder)
        save_results(results, output)
        
        print(f"\n已保存到: {output}")
        print(f"共分析: {len(results)} 场")
