# V16 算法 - V7成功经验 + 末位8探测准则
# 结合V7的平局识别和V15的8探测，但调整反向操作策略

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


def count_eights(odds_list):
    """统计赔率中末尾8的个数"""
    count_8 = 0
    count_88 = 0
    
    for odds in odds_list:
        for odd in odds:
            odd_str = f"{odd:.2f}"
            if odd_str.endswith('8'):
                count_8 += 1
                if odd_str.endswith('88'):
                    count_88 += 1
    
    return count_8, count_88


def analyze_8_pattern(initial_odds, realtime_odds):
    """分析8的变化模式"""
    if not initial_odds or not realtime_odds:
        return 'unknown', 0
    
    init_8, init_88 = count_eights(initial_odds)
    rt_8, rt_88 = count_eights(realtime_odds)
    
    diff_8 = rt_8 - init_8
    diff_88 = rt_88 - init_88
    
    if diff_88 > 0:
        return 'dead_end', diff_88
    elif diff_8 < -init_8 + 2 and rt_8 <= 2:
        return 'safe_haven', -diff_8
    else:
        return 'normal', 0


def predict_v16(data):
    """V16 预测算法 - V7 + 8探测(保守版)"""
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
    
    # 分析8的变化模式（仅用于警告，不轻易反向）
    pattern, intensity = analyze_8_pattern(initial, rt)
    
    # 澳门推荐（权重最大 - V7核心）
    macao = data.get('macao_tip', '')
    if macao:
        if '贏' in macao or '赢' in macao:
            if home in macao:
                prob_home += 0.10
            elif away in macao:
                prob_away += 0.10
    
    # V7核心逻辑：强队近况判断
    home_wins = data.get('home_wins', 0)
    home_draws = data.get('home_draws', 0)
    home_win_rate = data.get('home_win_rate', 0)
    home_goals = data.get('home_goals', 0)
    
    away_wins = data.get('away_wins', 0)
    away_draws = data.get('away_draws', 0)
    away_win_rate = data.get('away_win_rate', 0)
    away_goals = data.get('away_goals', 0)
    
    if home_wins >= 4:
        prob_home += 0.05
    if away_wins >= 4:
        prob_away += 0.05
    
    # V7核心逻辑：概率优势
    if abs(prob_home - prob_away) > 0.12:
        if prob_home > prob_away:
            prob_home += 0.05
        else:
            prob_away += 0.05
    
    # V7核心逻辑：平局识别（5条规则）
    # 1. 双方平局都很多
    if home_draws >= 3 and away_draws >= 3:
        prob_draw += 0.08
    
    # 2. 赔率接近且平局偏低
    if 2.8 < avg_draw < 3.3 and abs(prob_home - prob_away) < 0.15:
        prob_draw += 0.06
    
    # 3. 双方守强攻弱
    if home_goals < 12 and away_goals < 12:
        prob_draw += 0.05
    
    # 4. 盘路下坡
    if 'D' in data.get('home_form_str', '') or 'L' in data.get('home_form_str', ''):
        if 'D' in data.get('away_form_str', '') or 'L' in data.get('away_form_str', ''):
            prob_draw += 0.04
    
    # 5. 历史交锋多平局
    if data.get('history', ''):
        match = re.search(r'(\d+)胜(\d+)和(\d+)负', data['history'])
        if match:
            draws = int(match.group(2))
            total = int(match.group(1)) + draws + int(match.group(3))
            if total > 0 and draws / total > 0.3:
                prob_draw += 0.05
    
    # V15逻辑：仅在强烈信号时轻微调整（不同于V15的反向）
    # 补饵收割：不反向，而是降低该选项权重
    if pattern == 'dead_end':
        # 找出哪个选项有更多8
        rt_8_home = sum(1 for o in rt if str(o[0]).endswith('8'))
        rt_8_away = sum(1 for o in rt if str(o[2]).endswith('8'))
        
        if rt_8_home > rt_8_away:
            prob_home -= 0.05  # 轻微降低
        else:
            prob_away -= 0.05
    
    # 归一化
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


def analyze_folder_v16(folder_path):
    results = []
    files = sorted(Path(folder_path).glob('*.md'))
    
    for f in files:
        if '源数据' not in f.name:
            continue
        
        print(f"\n分析: {f.name}")
        
        try:
            data = parse_source_file(str(f))
            prediction = predict_v16(data)
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
        f.write("# V16 算法预测结果\n\n")
        for r in results:
            f.write(f"- {r['id']} {r['home']} vs {r['away']}: **{r['prediction']}** (联赛: {r['league']})\n")


if __name__ == "__main__":
    folders = [
        (r"d:\work\workbuddy\足球预测\分析模板\3.13", "3.13_V16预测.txt"),
        (r"d:\work\workbuddy\足球预测\分析模板\3.14", "3.14_V16预测.txt"),
        (r"d:\work\workbuddy\足球预测\分析模板\3.15", "3.15_V16预测.txt"),
    ]
    
    for folder, output in folders:
        print(f"\n{'='*60}")
        print(f"分析: {folder}")
        print('='*60)
        
        results = analyze_folder_v16(folder)
        save_results(results, output)
        
        print(f"\n已保存到: {output}")
        print(f"共分析: {len(results)} 场")
