#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H9数据集生成脚本 v2.0
遍历所有历史比赛，计算特征，生成h9_dataset.json
新增特征：league_level（联赛级别）、match_nature（比赛性质）
修复：date字段（从match_info.time读取）
"""

import json
import os
import glob
from datetime import datetime

DATASET_FILE = 'h9_dataset.json'
SCORES_FILE = '分析模板/_scores.json'
SPORTTERY_DIR = 'sporttery_data'

# 联赛级别映射（根据用户需求优化）
LEAGUE_LEVEL_MAPPING = {
    "友谊赛": ["国际赛", "友谊赛", "Friendly", "热身赛"],
    "正赛": ["世界杯", "世界杯预选赛", "欧洲杯", "亚洲杯", "非洲杯", "美洲杯", "欧国联", "国家联赛"],
    "联赛": [
        # 顶级联赛
        "西班牙甲级联赛", "意大利甲级联赛", "德国甲级联赛", "英格兰超级联赛", 
        "法国甲级联赛", "荷兰甲级联赛", "葡萄牙超级联赛",
        # 次级联赛
        "德国乙级联赛", "英格兰冠军联赛", "法国乙级联赛", "荷兰乙级联赛", "英格兰甲级联赛",
        # 其他联赛
        "日本职业联赛", "瑞典超级联赛", "芬兰超级联赛", "挪威超级联赛", 
        "沙特职业联赛", "韩国职业联赛", "澳大利亚超级联赛", "美国职业大联盟",
        "英格兰冠军联赛", "英格兰甲级联赛"
    ],
    "杯赛": [
        "欧罗巴联赛", "欧洲冠军联赛", "欧洲协会联赛", "南美解放者杯",
        "英格兰足总杯", "意大利杯", "法国杯", "德国杯", "荷兰杯",
        "亚洲冠军乙级联赛", "亚洲冠军精英联赛", "国王杯", "德国杯"
    ]
}

def standardize_league_level(league_name):
    """标准化联赛级别"""
    if not league_name:
        return "未知"
    
    for level, keywords in LEAGUE_LEVEL_MAPPING.items():
        if any(kw in league_name for kw in keywords):
            return level
    return "其他"

def extract_match_nature(league, handicap):
    """
    提取比赛性质
    league: 联赛名称
    handicap: 让球数（用于辅助判断重要性）
    """
    # 判断比赛类型
    if any(kw in league for kw in ["国际赛", "友谊赛", "Friendly", "热身赛"]):
        match_type = "友谊赛"
        importance = "低"
    elif any(kw in league for kw in ["世界杯", "欧洲杯", "亚洲杯", "非洲杯", "美洲杯"]):
        match_type = "正赛"
        importance = "高"
    elif any(kw in league for kw in ["欧冠", "欧联"]):
        match_type = "杯赛"
        importance = "高"
    elif any(kw in league for kw in ["英超", "西甲", "德甲", "意甲", "法甲"]):
        match_type = "联赛"
        importance = "中"
    else:
        match_type = "联赛"
        importance = "中"
    
    # 判断是否是德比（简化处理：暂时都设为False）
    is_derby = False
    
    # 判断是否是淘汰赛（简化处理：基于联赛名称）
    is_knockout = any(kw in league for kw in ["杯", "决赛", "半决赛", "1/4", "1/8"])
    
    return {
        "type": match_type,
        "importance": importance,
        "is_derby": is_derby,
        "is_knockout": is_knockout
    }

def load_scores():
    """加载实际比赛结果"""
    try:
        with open(SCORES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def calculate_recent_stats(match_list, team_type='home'):
    """
    计算近期比赛统计
    team_type: 'home' 表示主队主场, 'away' 表示客队客场
    """
    if not match_list or len(match_list) == 0:
        return {
            'matches': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'avg_goals_for': 0.0,
            'avg_goals_against': 0.0,
            'avg_net': 0.0,
            'win_rate': 0.0
        }
    
    wins = 0
    draws = 0
    losses = 0
    goals_for = []
    goals_against = []
    
    for match in match_list[:5]:  # 最近5场
        full_goal = match.get('fullCourtGoal', '')
        if not full_goal or ':' not in full_goal:
            continue
        
        try:
            home_score, away_score = map(int, full_goal.split(':'))
            
            if team_type == 'home':
                # 主队主场视角
                gf = home_score
                ga = away_score
            else:
                # 客队客场视角（需要交换）
                gf = away_score
                ga = home_score
            
            goals_for.append(gf)
            goals_against.append(ga)
            
            # 判断胜负（从主队视角）
            home_team = match.get('homeTeamShortName', '')
            away_team = match.get('awayTeamShortName', '')
            
            # 简化处理：假设当前主队是homeTeam
            if gf > ga:
                wins += 1
            elif gf == ga:
                draws += 1
            else:
                losses += 1
                
        except:
            continue
    
    total = wins + draws + losses
    if total == 0:
        return {
            'matches': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'avg_goals_for': 0.0,
            'avg_goals_against': 0.0,
            'avg_net': 0.0,
            'win_rate': 0.0
        }
    
    avg_goals_for = sum(goals_for) / len(goals_for) if goals_for else 0.0
    avg_goals_against = sum(goals_against) / len(goals_against) if goals_against else 0.0
    avg_net = avg_goals_for - avg_goals_against
    win_rate = wins / total
    
    return {
        'matches': total,
        'wins': wins,
        'draws': draws,
        'losses': losses,
        'avg_goals_for': round(avg_goals_for, 2),
        'avg_goals_against': round(avg_goals_against, 2),
        'avg_net': round(avg_net, 2),
        'win_rate': round(win_rate, 2)
    }

def calculate_strength_gap(home_stats, away_stats):
    """
    计算实力差距
    实力差距 = 主队场均净胜球 - 客队场均净胜球
    """
    if home_stats['matches'] == 0 or away_stats['matches'] == 0:
        return 0.0
    
    return round(home_stats['avg_net'] - away_stats['avg_net'], 2)

def extract_features(data):
    """提取特征"""
    preview = data.get('preview', {})
    recent = preview.get('recent', {})
    hhad = data.get('hhad', {})
    hhad_change = data.get('hhad_change', {})
    had = data.get('had', {})
    
    # 主队近期主场
    home_recent_list = recent.get('home', {}).get('matchList', [])
    home_stats = calculate_recent_stats(home_recent_list, 'home')
    
    # 客队近期客场
    away_recent_list = recent.get('away', {}).get('matchList', [])
    away_stats = calculate_recent_stats(away_recent_list, 'away')
    
    # 实力差距
    strength_gap = calculate_strength_gap(home_stats, away_stats)
    
    # 让球盘口
    handicap = hhad.get('让球', '')
    try:
        handicap_val = float(handicap)
    except:
        handicap_val = 0
    
    # 让球赔率
    let_win_odds = float(hhad.get('让胜', 999))
    let_draw_odds = float(hhad.get('让平', 999))
    let_lose_odds = float(hhad.get('让负', 999))
    
    # 让球变化
    let_win_change = hhad_change.get('让胜', {}).get('change_pct', 0)
    let_draw_change = hhad_change.get('让平', {}).get('change_pct', 0)
    let_lose_change = hhad_change.get('让负', {}).get('change_pct', 0)
    
    # 欧赔
    had_home = float(had.get('主胜', 999))
    had_draw = float(had.get('平局', 999))
    had_away = float(had.get('客胜', 999))
    
    return {
        'strength_gap': strength_gap,
        'home_recent': home_stats,
        'away_recent': away_stats,
        'handicap': handicap_val,
        'odds': {
            'let_win': let_win_odds,
            'let_draw': let_draw_odds,
            'let_lose': let_lose_odds
        },
        'odds_change': {
            'let_win': let_win_change,
            'let_draw': let_draw_change,
            'let_lose': let_lose_change
        },
        'had_odds': {
            'home_win': had_home,
            'draw': had_draw,
            'away_win': had_away
        }
    }

def extract_result(data, scores_data):
    """提取实际比赛结果"""
    match_id = data.get('match_id', '')
    match_info = data.get('match_info', {})
    home_team = match_info.get('home_team', '')
    away_team = match_info.get('away_team', '')
    
    # 从_scores.json查找结果
    # 尝试多种key格式
    result = None
    for key_format in [match_id, f"{match_info.get('match_num_str', '')}", home_team]:
        if key_format in scores_data:
            result = scores_data[key_format]
            break
    
    if not result:
        return None
    
    home_score = result.get('home_score', None)
    away_score = result.get('away_score', None)
    
    if home_score is None or away_score is None:
        return None
    
    home_score = int(home_score)
    away_score = int(away_score)
    
    # 计算让球方向
    handicap = data.get('hhad', {}).get('让球', '')
    try:
        handicap_val = float(handicap)
        adjusted_home = home_score + handicap_val
        
        if adjusted_home > away_score:
            handicap_result = '让胜'
        elif adjusted_home == away_score:
            handicap_result = '让平'
        else:
            handicap_result = '让负'
    except:
        handicap_result = '未知'
    
    # 计算欧赔方向
    if home_score > away_score:
        had_result = '主胜'
    elif home_score == away_score:
        had_result = '平局'
    else:
        had_result = '客胜'
    
    return {
        'home_score': home_score,
        'away_score': away_score,
        'total_goals': home_score + away_score,
        'handicap_result': handicap_result,
        'had_result': had_result
    }

def create_dataset():
    """创建数据集"""
    print("=== H9数据集生成开始 ===")
    
    # 加载实际结果
    scores_data = load_scores()
    print(f"已加载实际结果: {len(scores_data)} 场")
    
    # 遍历所有比赛
    dataset = {
        'metadata': {
            'version': '2.0',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_matches': 0,
            'description': 'H9预测器数据集 v2.0 - 添加联赛级别、比赛性质'
        },
        'matches': []
    }
    
    json_files = glob.glob(os.path.join(SPORTTERY_DIR, '*.json'))
    print(f"找到 {len(json_files)} 个数据文件")
    
    processed = 0
    skipped = 0
    
    for filepath in json_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            match_id = data.get('match_id', '')
            match_info = data.get('match_info', {})
            
            # 检查是否有让球数据
            hhad = data.get('hhad', {})
            if not hhad or '让球' not in hhad:
                skipped += 1
                continue
            
            # 提取特征
            features = extract_features(data)
            
            # 提取结果
            result = extract_result(data, scores_data)
            
            # 添加到数据集
            league = match_info.get('league', '')
            league_level = standardize_league_level(league)
            match_nature = extract_match_nature(league, features['handicap'])
            
            # 修复日期：从fetch_time提取日期部分
            fetch_time = data.get('fetch_time', '')
            match_date = fetch_time.split(' ')[0] if fetch_time else ''
            
            match_data = {
                'match_id': match_id,
                'league': league,
                'league_level': league_level,  # 新增：联赛级别
                'match_nature': match_nature,  # 新增：比赛性质
                'date': match_date,  # 修复：从fetch_time提取日期
                'home_team': match_info.get('home_team', ''),
                'away_team': match_info.get('away_team', ''),
                'features': features,
                'result': result,
                'h9_prediction': None  # 暂时为空，后续回测时填充
            }
            
            dataset['matches'].append(match_data)
            processed += 1
            
            if processed % 50 == 0:
                print(f"已处理 {processed} 场比赛...")
                
        except Exception as e:
            print(f"处理 {filepath} 失败: {e}")
            skipped += 1
            continue
    
    dataset['metadata']['total_matches'] = processed
    
    # 保存数据集
    with open(DATASET_FILE, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== 数据集生成完成 ===")
    print(f"总比赛场数: {processed}")
    print(f"跳过场数: {skipped}")
    print(f"数据集已保存到: {DATASET_FILE}")

if __name__ == '__main__':
    create_dataset()
