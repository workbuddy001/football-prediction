# V10 增强版算法 - 多维度特征融合分析
# 基于赔率分散性、走势分析、近况数据、历史交锋等多维度综合判断

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


def calculate_odds_features(data):
    """计算赔率特征"""
    rt = data['realtime_odds']
    if not rt:
        return {}
    
    # 计算平均值
    avg_home = sum(o[0] for o in rt) / len(rt)
    avg_draw = sum(o[1] for o in rt) / len(rt)
    avg_away = sum(o[2] for o in rt) / len(rt)
    
    # 计算标准差（分散性）
    import math
    std_home = math.sqrt(sum((o[0] - avg_home)**2 for o in rt) / len(rt))
    std_draw = math.sqrt(sum((o[1] - avg_draw)**2 for o in rt) / len(rt))
    std_away = math.sqrt(sum((o[2] - avg_away)**2 for o in rt) / len(rt))
    
    # 计算变异系数（分散程度）
    cv_home = std_home / avg_home if avg_home > 0 else 0
    cv_draw = std_draw / avg_draw if avg_draw > 0 else 0
    cv_away = std_away / avg_away if avg_away > 0 else 0
    
    # 赔率变化分析
    init = data.get('initial_odds', [])
    if init and len(init) == len(rt):
        home_changes = [rt[i][0] - init[i][0] for i in range(len(rt))]
        draw_changes = [rt[i][1] - init[i][1] for i in range(len(rt))]
        away_changes = [rt[i][2] - init[i][2] for i in range(len(rt))]
        
        home_down = sum(1 for c in home_changes if c < -0.05)
        home_up = sum(1 for c in home_changes if c > 0.05)
        draw_down = sum(1 for c in draw_changes if c < -0.05)
        draw_up = sum(1 for c in draw_changes if c > 0.05)
        away_down = sum(1 for c in away_changes if c < -0.05)
        away_up = sum(1 for c in away_changes if c > 0.05)
    else:
        home_down = home_up = draw_down = draw_up = away_down = away_up = 0
    
    return {
        'avg_home': avg_home,
        'avg_draw': avg_draw,
        'avg_away': avg_away,
        'cv_home': cv_home,
        'cv_draw': cv_draw,
        'cv_away': cv_away,
        'home_down': home_down,
        'home_up': home_up,
        'draw_down': draw_down,
        'draw_up': draw_up,
        'away_down': away_down,
        'away_up': away_up,
    }


def analyze_form_trend(form_str):
    """分析走势趋势"""
    if not form_str or len(form_str) < 3:
        return 0
    
    # 计算最近几场的积分趋势
    # W=3, D=1, L=0
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
    
    # 最近3场的趋势
    recent = points[-3:]
    older = points[-6:-3] if len(points) >= 6 else points[:-3]
    
    recent_avg = sum(recent) / len(recent)
    older_avg = sum(older) / len(older) if older else recent_avg
    
    return recent_avg - older_avg  # 正数表示上升趋势


def analyze_handicap_trend(handicap_str):
    """分析盘路趋势"""
    if not handicap_str or len(handicap_str) < 3:
        return 0
    
    # W=1, L=-1, D=0 (赢盘=1, 输盘=-1, 走水=0)
    points = []
    for c in handicap_str:
        if c == 'W':
            points.append(1)
        elif c == 'L':
            points.append(-1)
    
    if len(points) < 3:
        return sum(points) / len(points) if points else 0
    
    recent = points[-3:]
    return sum(recent) / len(recent)


def parse_history(history_str):
    """解析历史交锋"""
    if not history_str:
        return 0, 0
    
    # 格式: "主队 X胜Y和Z负"
    match = re.search(r'(\d+)胜(\d+)和(\d+)负', history_str)
    if match:
        home_wins = int(match.group(1))
        draws = int(match.group(2))
        home_losses = int(match.group(3))
        total = home_wins + draws + home_losses
        if total > 0:
            # 返回主队的胜率-负率， 正数对主队有利
            return (home_wins - home_losses) / total, draws / total
    return 0, 0


def is_strong_team(win_rate, goals, losses):
    """判断是否为强队"""
    return win_rate >= 50 or goals >= 15


def predict_v10(data):
    """V10 预测算法 - 多维度综合分析"""
    odds = calculate_odds_features(data)
    if not odds:
        return "未知"
    
    home = data.get('home_team', '')
    away = data.get('away_team', '')
    
    # 基础得分
    home_score = 0
    away_score = 0
    draw_score = 0
    
    # ========================
    # 1. 赔率分析（权重: 40%）
    # ========================
    avg_home = odds.get('avg_home', 2.5)
    avg_draw = odds.get('avg_draw', 3.2)
    avg_away = odds.get('avg_away', 2.8)
    
    # 概率转换
    prob_home = 1 / avg_home if avg_home > 0 else 0
    prob_draw = 1 / avg_draw if avg_draw > 0 else 0
    prob_away = 1 / avg_away if avg_away > 0 else 0
    total_prob = prob_home + prob_draw + prob_away
    
    if total_prob > 0:
        prob_home /= total_prob
        prob_draw /= total_prob
        prob_away /= total_prob
    
    # 赔率分散性分析
    cv_home = odds.get('cv_home', 0)
    cv_away = odds.get('cv_away', 0)
    cv_draw = odds.get('cv_draw', 0)
    
    # 低分散性 = 公司共识度高
    consensus_threshold = 0.15
    
    if cv_home < consensus_threshold and cv_away < consensus_threshold:
        # 共识度高
        if prob_home > prob_away + 0.15:
            home_score += 3
        elif prob_away > prob_home + 0.15:
            away_score += 3
        elif prob_draw > 0.28:
            draw_score += 2
    else:
        # 分散性高，降低置信度
        if prob_home > prob_away + 0.25:
            home_score += 2
        elif prob_away > prob_home + 0.25:
            away_score += 2
    
    # ========================
    # 2. 赔率变化趋势（权重: 15%）
    # ========================
    home_down = odds.get('home_down', 0)
    away_down = odds.get('away_down', 0)
    total_companies = len(odds.get('realtime_odds', [(1,1,1)]))
    
    # 降赔表示被买入
    if home_down > total_companies * 0.5:
        home_score += 2
    if away_down > total_companies * 0.5:
        away_score += 2
    
    # ========================
    # 3. 近况分析（权重: 25%）
    # ========================
    home_wins = data.get('home_wins', 0)
    home_draws = data.get('home_draws', 0)
    home_losses = data.get('home_losses', 0)
    home_win_rate = data.get('home_win_rate', 0)
    home_goals = data.get('home_goals', 0)
    home_lost = data.get('home_lost', 0)
    
    away_wins = data.get('away_wins', 0)
    away_draws = data.get('away_draws', 0)
    away_losses = data.get('away_losses', 0)
    away_win_rate = data.get('away_win_rate', 0)
    away_goals = data.get('away_goals', 0)
    away_lost = data.get('away_lost', 0)
    
    # 胜率对比
    if home_win_rate >= 60:
        home_score += 2
    elif home_win_rate <= 30:
        home_score -= 1
    
    if away_win_rate >= 60:
        away_score += 2
    elif away_win_rate <= 30:
        away_score -= 1
    
    # 进球能力
    if home_goals >= 15:
        home_score += 1
    if away_goals >= 15:
        away_score += 1
    
    # 净胜球
    home_net = home_goals - home_lost
    away_net = away_goals - away_lost
    
    if home_net > 5:
        home_score += 1
    elif home_net < -3:
        home_score -= 1
    
    if away_net > 5:
        away_score += 1
    elif away_net < -3:
        away_score -= 1
    
    # ========================
    # 4. 走势分析（权重: 10%）
    # ========================
    home_trend = analyze_form_trend(data.get('home_form_str', ''))
    away_trend = analyze_form_trend(data.get('away_form_str', ''))
    home_handicap_trend = analyze_handicap_trend(data.get('home_handicap_str', ''))
    away_handicap_trend = analyze_handicap_trend(data.get('away_handicap_str', ''))
    
    if home_trend > 0.5:
        home_score += 1
    elif home_trend < -0.5:
        home_score -= 1
    
    if away_trend > 0.5:
        away_score += 1
    elif away_trend < -0.5:
        away_score -= 1
    
    # 盘路趋势
    if home_handicap_trend > 0.3:
        home_score += 1
    if away_handicap_trend > 0.3:
        away_score += 1
    
    # ========================
    # 5. 历史交锋（权重: 5%）
    # ========================
    history_bias, history_draw_rate = parse_history(data.get('history', ''))
    if history_bias > 0.3:
        home_score += 1
    elif history_bias < -0.3:
        away_score += 1
    
    if history_draw_rate > 0.4:
        draw_score += 1
    
    # ========================
    # 6. 澳门推荐（权重: 5%）
    # ========================
    macao = data.get('macao_tip', '')
    if macao:
        if '贏' in macao or '赢' in macao:
            if home in macao:
                home_score += 2
            elif away in macao:
                away_score += 2
        elif '和' in macao or '平' in macao:
            draw_score += 1
    
    # ========================
    # 7. 平局特殊规则
    # ========================
    # 双方近况都较差（胜率<40%）且赔率接近
    if home_win_rate < 40 and away_win_rate < 40:
        if abs(prob_home - prob_away) < 0.15:
            draw_score += 2
    
    # 双方都是守强攻弱（进球少）
    if home_goals < 12 and away_goals < 12:
        if avg_draw < 3.4:
            draw_score += 1
    
    # ========================
    # 8. 强队输球预警
    # ========================
    home_strong = is_strong_team(home_win_rate, home_goals, home_losses)
    away_strong = is_strong_team(away_win_rate, away_goals, away_losses)
    
    if home_strong and away_strong:
        # 强强对话，降低主队优势
        home_score -= 1
        away_score += 1
    
    # ========================
    # 综合决策
    # ========================
    print(f"  比分: 主{home_score} 平{draw_score} 客{away_score}")
    
    # 找出最高分
    max_score = max(home_score, draw_score, away_score)
    
    # 阈值判断
    if home_score == max_score and home_score - max(home_score, draw_score, away_score) < 2:
        return "主胜"
    elif away_score == max_score and away_score - max(home_score, draw_score, away_score) < 2:
        return "客胜"
    elif draw_score == max_score and draw_score >= 2:
        return "平局"
    else:
        # 默认选择概率最高的
        if prob_home > prob_away + 0.1:
            return "主胜"
        elif prob_away > prob_home + 0.1:
            return "客胜"
        else:
            return "主胜"  # 保守选择主队


def analyze_folder_v10(folder_path):
    """分析文件夹中的所有比赛"""
    results = []
    
    files = sorted(Path(folder_path).glob('*.md'))
    
    for f in files:
        if '源数据' not in f.name:
            continue
        
        print(f"\n分析: {f.name}")
        
        try:
            data = parse_source_file(str(f))
            prediction = predict_v10(data)
            
            # 提取比赛编号
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
        f.write("# V10 算法预测结果\n\n")
        for r in results:
            f.write(f"- {r['id']} {r['home']} vs {r['away']}: **{r['prediction']}** (联赛: {r['league']})\n")


if __name__ == "__main__":
    import sys
    
    # 分析三个文件夹
    folders = [
        (r"d:\work\workbuddy\足球预测\分析模板\3.13", "3.13_V10预测.txt"),
        (r"d:\work\workbuddy\足球预测\分析模板\3.14", "3.14_V10预测.txt"),
        (r"d:\work\workbuddy\足球预测\分析模板\3.15", "3.15_V10预测.txt"),
    ]
    
    for folder, output in folders:
        print(f"\n{'='*60}")
        print(f"分析: {folder}")
        print('='*60)
        
        results = analyze_folder_v10(folder)
        save_results(results, output)
        
        print(f"\n已保存到: {output}")
        print(f"共分析: {len(results)} 场")
