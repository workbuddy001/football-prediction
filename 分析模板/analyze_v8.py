# V8优化版赔率分析算法 - 基于欧赔核心思维
import os
import re
import numpy as np

def extract_odds_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    home_team = re.search(r'主队\s*\|\s*(.+)', content)
    away_team = re.search(r'客队\s*\|\s*(.+)', content)
    league = re.search(r'赛事\s*\|\s*(.+)', content)
    home_form = re.search(r'主队近况走势\s*\|\s*(.+)', content)
    away_form = re.search(r'客队近况走势\s*\|\s*(.+)', content)
    home_handicap = re.search(r'主队盘路走势\s*\|\s*(.+)', content)
    away_handicap = re.search(r'客队盘路走势\s*\|\s*(.+)', content)
    macao_tip = re.search(r'澳门推荐\s*\|\s*(.+)', content)
    
    init_match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if init_match:
        odds_str = init_match.group(1)
        initial_odds = eval('[' + odds_str + ']')
    else:
        initial_odds = []
    
    real_match = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if real_match:
        odds_str = real_match.group(1)
        realtime_odds = eval('[' + odds_str + ']')
    else:
        realtime_odds = []
    
    return {
        'home_team': home_team.group(1).strip() if home_team else '',
        'away_team': away_team.group(1).strip() if away_team else '',
        'league': league.group(1).strip() if league else '',
        'home_form': home_form.group(1).strip() if home_form else '',
        'away_form': away_form.group(1).strip() if away_form else '',
        'home_handicap': home_handicap.group(1).strip() if home_handicap else '',
        'away_handicap': away_handicap.group(1).strip() if away_handicap else '',
        'macao_tip': macao_tip.group(1).strip() if macao_tip else '',
        'initial_odds': initial_odds,
        'realtime_odds': realtime_odds,
    }

def count_wins(form):
    if not form:
        return 0
    return sum(1 for c in form.upper() if c == 'W')

def count_losses(form):
    if not form:
        return 0
    return sum(1 for c in form.upper() if c == 'L')

def count_draws(form):
    if not form:
        return 0
    return sum(1 for c in form.upper() if c == 'D')

# 强队列表（人气指数）
STRONG_TEAMS = {
    '英超': ['曼城', '阿森纳', '利物浦', '曼联', '切尔西', '热刺', '纽卡斯尔'],
    '西甲': ['皇马', '巴萨', '马竞', '塞维利亚', '皇家社会'],
    '意甲': ['国米', '尤文', 'AC米兰', '那不勒斯', '罗马', '拉齐奥'],
    '德甲': ['拜仁', '多特', '勒沃库森', '莱红牛', '法兰克福'],
    '法甲': ['巴黎', '马赛', '里昂', '摩纳哥', '里尔'],
    '荷甲': ['阿贾克斯', '埃因霍温', '费耶诺德', '阿尔克马尔'],
    '葡超': ['本菲卡', '波尔图', '葡萄牙体育', '布拉加'],
    '日职': ['神户胜利', '横滨水手', '川崎前锋', '鹿岛鹿角', '浦和红钻'],
    '韩职': ['全北现代', '蔚山现代', '首尔FC', '浦项制铁'],
    '澳超': ['悉尼FC', '墨胜利', '珀斯光荣', '阿德莱德'],
    '中超': ['海港', '泰山', '三镇', '国安', '蓉城'],
    '沙特': ['利雅得胜利', '吉达国民', '利雅得新月', '赛哈特海湾'],
    '挪超': ['莫尔德', '罗森博格', '博德闪耀', '维京'],
    '美职足': ['洛杉矶FC', '迈阿密', '纽约城', '亚特兰大'],
}

# 高人气球队（人气溢价）
HIGH_PRESTIGE_TEAMS = ['皇马', '巴萨', '曼联', '利物浦', '拜仁', '尤文', '国米', 'AC米兰', '巴黎', '曼城', '阿森纳', '切尔西', '马竞', '热刺', '多特', '波尔图', '本菲卡']

def get_team_prestige(team_name):
    """获取球队人气指数"""
    for league, teams in STRONG_TEAMS.items():
        for i, t in enumerate(teams):
            if t in team_name or team_name in t:
                return 10 - i  # 排名越高，分数越高
    if any(t in team_name for t in HIGH_PRESTIGE_TEAMS):
        return 8
    return 3

def analyze_match_v8(data):
    """V8算法 - 基于欧赔核心思维理论"""
    if not data['initial_odds'] or not data['realtime_odds']:
        return None
    
    real_home = [o[0] for o in data['realtime_odds']]
    real_draw = [o[1] for o in data['realtime_odds']]
    real_away = [o[2] for o in data['realtime_odds']]
    
    # 变化百分比
    home_pct = [(data['realtime_odds'][i][0] - data['initial_odds'][i][0]) / data['initial_odds'][i][0] * 100 
                for i in range(len(data['initial_odds']))]
    draw_pct = [(data['realtime_odds'][i][1] - data['initial_odds'][i][1]) / data['initial_odds'][i][1] * 100 
                for i in range(len(data['initial_odds']))]
    away_pct = [(data['realtime_odds'][i][2] - data['initial_odds'][i][2]) / data['initial_odds'][i][2] * 100 
                for i in range(len(data['initial_odds']))]
    
    # 概率
    real_home_prob = [1/x*100 for x in real_home]
    real_draw_prob = [1/x*100 for x in real_draw]
    real_away_prob = [1/x*100 for x in real_away]
    
    # 统计变化趋势
    home_up_pct = sum(1 for x in home_pct if x > 0) / len(home_pct) * 100
    home_down_pct = sum(1 for x in home_pct if x < 0) / len(home_pct) * 100
    draw_up_pct = sum(1 for x in draw_pct if x > 0) / len(draw_pct) * 100
    draw_down_pct = sum(1 for x in draw_pct if x < 0) / len(draw_pct) * 100
    away_up_pct = sum(1 for x in away_pct if x > 0) / len(away_pct) * 100
    away_down_pct = sum(1 for x in away_pct if x < 0) / len(away_pct) * 100
    
    # 平均值
    avg_home = np.mean(real_home)
    avg_draw = np.mean(real_draw)
    avg_away = np.mean(real_away)
    
    avg_home_prob = np.mean(real_home_prob)
    avg_draw_prob = np.mean(real_draw_prob)
    avg_away_prob = np.mean(real_away_prob)
    
    # 近况分析
    home_wins = count_wins(data['home_form'])
    away_wins = count_wins(data['away_form'])
    home_losses = count_losses(data['home_form'])
    away_losses = count_losses(data['away_form'])
    home_draws = count_draws(data['home_form'])
    away_draws = count_draws(data['away_form'])
    
    # 澳门推荐
    macao_tip = data['macao_tip'].upper() if data['macao_tip'] else ""
    
    # ===== 欧赔核心思维分析 =====
    
    # 1. 计算人气指数差异
    home_prestige = get_team_prestige(data['home_team'])
    away_prestige = get_team_prestige(data['away_team'])
    prestige_diff = home_prestige - away_prestige
    
    # 2. 分布分析 - 基础分布
    # 强队主场优势明显
    is_home_strong = avg_home < 1.5
    is_away_strong = avg_away < 1.5
    
    # ===== V8算法规则 =====
    
    # 规则1: 极强队主场 (主胜<1.35) -> 必博主胜
    if avg_home < 1.35:
        first_choice = f"{data['home_team']}主胜"
        first_prob = f"{avg_home_prob:.0f}%"
        reason = "极强队主场"
    
    # 规则2: 极强队客场 (客胜<1.35) -> 必博客胜
    elif avg_away < 1.35:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "极强队客场"
    
    # 规则3: 强队主场(1.35-1.6) + 澳门支持 -> 主胜
    elif avg_home < 1.6 and ("主" in macao_tip and "客" not in macao_tip):
        first_choice = f"{data['home_team']}主胜"
        first_prob = f"{avg_home_prob:.0f}%"
        reason = "强队主场+澳门支持"
    
    # 规则4: 强队客场(1.35-1.6) + 澳门支持 -> 客胜
    elif avg_away < 1.6 and "客" in macao_tip:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "强队客场+澳门支持"
    
    # 规则5: 分布利于主队 - 高人气+近况好
    elif home_prestige > away_prestige + 2 and home_wins >= 3 and avg_home < 2.2:
        first_choice = f"{data['home_team']}主胜"
        first_prob = f"{avg_home_prob:.0f}%"
        reason = "分布利于主队"
    
    # 规则6: 分布利于客队 - 高人气+近况好
    elif away_prestige > home_prestige + 2 and away_wins >= 3 and avg_away < 2.2:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "分布利于客队"
    
    # ===== 平局识别（基于核心思维） =====
    
    # 规则7: 广实接近 + 近况相似 -> 防平
    elif abs(home_prestige - away_prestige) <= 2 and abs(home_wins - away_wins) <= 1 and avg_draw_prob > 26:
        first_choice = "平局"
        first_prob = f"{avg_draw_prob:.0f}%"
        reason = "广实接近均势"
    
    # 规则8: 胜赔上升 + 平赔下降 -> 诱平手法
    elif home_up_pct > 30 and draw_down_pct > 30 and avg_draw_prob > 25:
        first_choice = "平局"
        first_prob = f"{avg_draw_prob:.0f}%"
        reason = "平局受保护"
    
    # 规则9: 两队都多平局近况 -> 防平
    elif home_draws >= 2 and away_draws >= 2 and avg_draw_prob > 24:
        first_choice = "平局"
        first_prob = f"{avg_draw_prob:.0f}%"
        reason = "两队多平局"
    
    # ===== 分胜负规则 =====
    
    # 规则10: 主队近况极佳(W>=4) -> 主胜
    elif home_wins >= 4:
        first_choice = f"{data['home_team']}主胜"
        first_prob = f"{avg_home_prob:.0f}%"
        reason = "主队近况极佳"
    
    # 规则11: 客队近况极佳(W>=4) -> 客胜
    elif away_wins >= 4:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "客队近况极佳"
    
    # 规则12: 主胜概率明显高于其他(>15%) -> 主胜
    elif avg_home_prob > avg_away_prob + 15 and avg_home_prob > avg_draw_prob + 15:
        first_choice = f"{data['home_team']}主胜"
        first_prob = f"{avg_home_prob:.0f}%"
        reason = "主胜概率优势明显"
    
    # 规则13: 客胜概率明显高于其他(>15%) -> 客胜
    elif avg_away_prob > avg_home_prob + 15 and avg_away_prob > avg_draw_prob + 15:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "客胜概率优势明显"
    
    # 规则14: 主胜概率最高 -> 主胜
    elif avg_home_prob >= avg_away_prob and avg_home_prob >= avg_draw_prob:
        first_choice = f"{data['home_team']}主胜"
        first_prob = f"{avg_home_prob:.0f}%"
        reason = "主胜概率最高"
    
    # 规则15: 客胜概率最高 -> 客胜
    elif avg_away_prob >= avg_home_prob and avg_away_prob >= avg_draw_prob:
        first_choice = f"{data['away_team']}客胜"
        first_prob = f"{avg_away_prob:.0f}%"
        reason = "客胜概率最高"
    
    # 默认: 概率最高
    else:
        if avg_draw_prob > 28:
            first_choice = "平局"
            first_prob = f"{avg_draw_prob:.0f}%"
        elif avg_home_prob >= avg_away_prob:
            first_choice = f"{data['home_team']}主胜"
            first_prob = f"{avg_home_prob:.0f}%"
        else:
            first_choice = f"{data['away_team']}客胜"
            first_prob = f"{avg_away_prob:.0f}%"
        reason = "默认概率最高"
    
    return {
        'home_team': data['home_team'],
        'away_team': data['away_team'],
        'first_choice': first_choice,
        'first_prob': first_prob,
        'reason': reason,
    }

def analyze_folder(folder_path):
    files = [f for f in os.listdir(folder_path) if f.endswith('_源数据.md')]
    
    results = []
    for f in sorted(files):
        filepath = os.path.join(folder_path, f)
        try:
            data = extract_odds_from_file(filepath)
            result = analyze_match_v8(data)
            if result:
                result['filename'] = f.replace('_源数据.md', '')
                results.append(result)
                print(f"{result['filename']}: {result['first_choice']} ({result['reason']})")
        except Exception as e:
            print(f"Error: {f} - {e}")
    
    return results

# 分析三个文件夹
print("=" * 60)
print("V8算法分析 3.13 文件夹 (周五)")
print("=" * 60)
results_313 = analyze_folder(r"d:\work\workbuddy\足球预测\分析模板\3.13")

print("\n" + "=" * 60)
print("V8算法分析 3.14 文件夹 (周六)")
print("=" * 60)
results_314 = analyze_folder(r"d:\work\workbuddy\足球预测\分析模板\3.14")

print("\n" + "=" * 60)
print("V8算法分析 3.15 文件夹 (周日)")
print("=" * 60)
results_315 = analyze_folder(r"d:\work\workbuddy\足球预测\分析模板\3.15")

print(f"\n总计: 3.13={len(results_313)}, 3.14={len(results_314)}, 3.15={len(results_315)}")
