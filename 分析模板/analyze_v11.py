# V11 综合优化版算法 - 基于V7成功经验 + 赔率分散性分析
# 结合V7的平局识别能力和赔率分散性分析

import re
import os
from pathlib import Path

def parse_source_file(filepath):
    """解析源数据文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取基本信息
    home_team = re.search(r'\| 主队 \| (.+) \|', content)
    away_team = re.search(r'\| 客队 \| (.+) \|', content)
    league = re.search(r'\| 赛事 \| (.+) \|', content)
    macao_tip = re.search(r'\| 澳门推荐 \| (.+) \|', content)
    
    # 提取近况数据
    home_form_match = re.search(r'\| 主队近况 \| 近10场，(\d+)胜(\d+)平(\d+)负 进(\d+)球 失(\d+)球 胜率(\d+)%', content)
    away_form_match = re.search(r'\| 客队近况 \| 近10场，(\d+)胜(\d+)平(\d+)负 进(\d+)球 失(\d+)球 胜率(\d+)%', content)
    
    # 提取走势
    home_form_str = re.search(r'\| 主队近况走势 \| (.+) \|', content)
    away_form_str = re.search(r'\| 客队近况走势 \| (.+) \|', content)
    home_handicap_str = re.search(r'\| 主队盘路走势 \| (.+) \|', content)
    away_handicap_str = re.search(r'\| 客队盘路走势 \| (.+) \|', content)
    
    # 提取历史交锋
    history = re.search(r'\| 历史交锋 \| (.+) \|', content)
    
    # 提取赔率
    initial_odds_match = re.findall(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', content.split('## 二、初盘赔率')[1].split('## 三、')[0])
    realtime_odds_match = re.findall(r'\((\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)\)', content.split('## 三、即时赔率')[1].split('## 四、')[0])
    
    # 提取竞彩赔率
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
    data['home_handicap_str'] = home_handicap_str.group(1).strip() if home_handicap_str else ''
    data['away_handicap_str'] = away_handicap_str.group(1).strip() if away_handicap_str else ''
    data['history'] = history.group(1) if history else ''
    
    # 赔率数据
    data['initial_odds'] = [(float(h), float(d), float(a)) for h, d, a in initial_odds_match]
    data['realtime_odds'] = [(float(h), float(d), float(a)) for h, d, a in realtime_odds_match]
    
    if jingcai:
        data['jingcai_home'] = float(jingcai.group(1))
        data['jingcai_draw'] = float(jingcai.group(2))
        data['jingcai_away'] = float(jingcai.group(3))
    
    return data


def analyze_form_trend(form_str):
    """分析走势趋势"""
    if not form_str or len(form_str) < 3:
        return 0
    
    points = []
    for c in form_str:
        if c == 'W':
            points.append(3)
        elif c == 'D':
            points.append(1)
        elif c == 'L':
            points.append(0)
    
    if len(points) < 3:
        return sum(points) / len(points) if points else 0
    
    recent = points[-3:]
    return sum(recent) / len(recent)


def parse_history(history_str):
    """解析历史交锋"""
    if not history_str:
        return 0
    
    match = re.search(r'(\d+)胜(\d+)和(\d+)负', history_str)
    if match:
        home_wins = int(match.group(1))
        draws = int(match.group(2))
        home_losses = int(match.group(3))
        total = home_wins + draws + home_losses
        if total > 0:
            return (home_wins - home_losses) / total, draws / total
    return 0, 0


def predict_v11(data):
    """V11 预测算法 - 综合优化版"""
    home = data.get('home_team', '')
    away = data.get('away_team', '')
    rt = data.get('realtime_odds', [])
    
    if not rt:
        return "未知"
    
    # 计算平均值
    avg_home = sum(o[0] for o in rt) / len(rt)
    avg_draw = sum(o[1] for o in rt) / len(rt)
    avg_away = sum(o[2] for o in rt) / len(rt)
    
    # 概率
    prob_home = 1 / avg_home if avg_home > 0 else 0
    prob_draw = 1 / avg_draw if avg_draw > 0 else 0
    prob_away = 1 / avg_away if avg_away > 0 else 0
    total_prob = prob_home + prob_draw + prob_away
    
    if total_prob > 0:
        prob_home /= total_prob
        prob_draw /= total_prob
        prob_away /= total_prob
    
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
    
    # 1. 澳门推荐权威判断
    macao_home = '贏' in macao or '赢' in macao
    if macao_home:
        if home in macao:
            prob_home += 0.08
        elif away in macao:
            prob_away += 0.08
    
    # 2. 强队近况判断（4场胜以上）
    if home_wins >= 4:
        prob_home += 0.05
    if away_wins >= 4:
        prob_away += 0.05
    
    # 3. 概率优势判断（需超过12%差距）
    prob_diff = abs(prob_home - prob_away)
    if prob_diff > 0.12:
        if prob_home > prob_away:
            prob_home += 0.05
        else:
            prob_away += 0.05
    
    # 4. 概率较低但有特殊信号的判断
    # 4.1 低赔方近况不佳但高赔方更差
    if avg_home < 1.8:  # 主队是热门
        if home_wins < 2 and away_wins < 2:
            # 双方都差，增加平局概率
            prob_draw += 0.10
        elif home_wins < away_wins:
            # 主队热门但近况差，增加客胜概率
            prob_away += 0.08
    
    if avg_away < 1.8:  # 客队是热门
        if away_wins < 2 and home_wins < 2:
            prob_draw += 0.10
        elif away_wins < home_wins:
            prob_home += 0.08
    
    # 5. 平局识别（关键）
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
    home_trend = analyze_form_trend(data.get('home_form_str', ''))
    away_trend = analyze_form_trend(data.get('away_form_str', ''))
    if home_trend < 1 and away_trend < 1:
        prob_draw += 0.04
    
    # 5.5 历史交锋多平局
    history_bias, history_draw_rate = parse_history(data.get('history', ''))
    if history_draw_rate > 0.3:
        prob_draw += 0.05
    
    # 6. 归一化
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


def analyze_folder_v11(folder_path):
    """分析文件夹中的所有比赛"""
    results = []
    
    files = sorted(Path(folder_path).glob('*.md'))
    
    for f in files:
        if '源数据' not in f.name:
            continue
        
        print(f"\n分析: {f.name}")
        
        try:
            data = parse_source_file(str(f))
            prediction = predict_v11(data)
            
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
    """保存预测结果"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# V11 算法预测结果\n\n")
        for r in results:
            f.write(f"- {r['id']} {r['home']} vs {r['away']}: **{r['prediction']}** (联赛: {r['league']})\n")


if __name__ == "__main__":
    folders = [
        (r"d:\work\workbuddy\足球预测\分析模板\3.13", "3.13_V11预测.txt"),
        (r"d:\work\workbuddy\足球预测\分析模板\3.14", "3.14_V11预测.txt"),
        (r"d:\work\workbuddy\足球预测\分析模板\3.15", "3.15_V11预测.txt"),
    ]
    
    for folder, output in folders:
        print(f"\n{'='*60}")
        print(f"分析: {folder}")
        print('='*60)
        
        results = analyze_folder_v11(folder)
        save_results(results, output)
        
        print(f"\n已保存到: {output}")
        print(f"共分析: {len(results)} 场")
