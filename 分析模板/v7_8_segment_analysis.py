# -*- coding: utf-8 -*-
"""
V7+8变化 分段权重分析法
基于置信度分段的足球比赛预测公式

分段规则:
- 55-60%: 胜率差>=30%主胜, <=-30%客胜, 高开>0%且|胜率差|<15%平局, 默认客胜
- 60-65%: 胜率差>=45%主胜, <=-45%客胜, 高开>0%且|胜率差|<15%平局, 默认主胜  
- 65-70%: 胜率差>=60%主胜, <=-60%客胜, 高开>0%且|胜率差|<15%平局, 默认客胜
- 70-75%: 胜率差>=50%主胜, <=-50%客胜, 高开>0%且|胜率差|<15%平局, 默认平局
- 75-80%: 胜率差>=60%主胜, <=-60%客胜, 高开>0%且|胜率差|<15%平局, 默认主胜
- 80%+:   胜率差>=25%主胜, <=-25%客胜, 高开>0%且|胜率差|<15%平局, 默认主胜
"""

import os
import json
import re
from datetime import datetime

# ============== 分段配置 ==============
SEGMENT_CONFIG = {
    '55-60%': {'t1': 30, 't2': 0, 't3': 15, 'default': '客胜'},
    '60-65%': {'t1': 45, 't2': 0, 't3': 15, 'default': '主胜'},
    '65-70%': {'t1': 60, 't2': 0, 't3': 15, 'default': '客胜'},
    '70-75%': {'t1': 50, 't2': 0, 't3': 15, 'default': '平局'},
    '75-80%': {'t1': 60, 't2': 0, 't3': 15, 'default': '主胜'},
    '80%+':   {'t1': 25, 't2': 0, 't3': 15, 'default': '主胜'},
}

def get_segment(conf):
    """根据置信度获取分段"""
    if 55 <= conf < 60:
        return '55-60%'
    elif 60 <= conf < 65:
        return '60-65%'
    elif 65 <= conf < 70:
        return '65-70%'
    elif 70 <= conf < 75:
        return '70-75%'
    elif 75 <= conf < 80:
        return '75-80%'
    elif conf >= 80:
        return '80%+'
    else:
        return None

def predict_match(conf, diff, home_8, draw_8, away_8):
    """
    预测比赛
    
    参数:
    - conf: 置信度 (0-100)
    - diff: 胜率差 (-100到+100, 正数表示主队更强)
    - home_8, draw_8, away_8: 8变化
    
    返回: 预测结果 (主胜/平局/客胜)
    """
    segment = get_segment(conf)
    if not segment:
        return 'N/A'  # 置信度低于55%不使用
    
    config = SEGMENT_CONFIG[segment]
    t1 = config['t1']
    t2 = config['t2']
    t3 = config['t3']
    default = config['default']
    
    # 高开程度 = 置信度 - 胜率差
    over = conf - diff
    
    # 规则1: 强信号 - 胜率差足够大
    if diff >= t1:
        return '主胜'
    if diff <= -t1:
        return '客胜'
    
    # 规则2: 高开走冷 - 置信度高估但实际实力差距不大
    if over > t2 and abs(diff) < t3:
        return '平局'
    
    # 规则3: 8变化极端值
    if home_8 >= 2:
        return '主胜'
    if home_8 <= -3:
        return '平局'
    if away_8 >= 3:
        return '客胜'
    
    # 规则4: 默认值
    return default

def analyze_v7_data(json_path):
    """分析V7预测数据"""
    # 读取JSON数据
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        matches = data.get('matches', [])
    else:
        matches = data
    
    results = []
    
    for match in matches:
        # 提取基本信息
        match_name = match.get('match_name', '')
        v7_prediction = match.get('v7_prediction', {})
        
        # 获取置信度和胜率差
        conf = v7_prediction.get('confidence', 0)
        diff = v7_prediction.get('win_rate_diff', 0)
        
        # 获取8变化
        odds_change = match.get('odds_change', {})
        home_8 = odds_change.get('home_8', 0)
        draw_8 = odds_change.get('draw_8', 0)
        away_8 = odds_change.get('away_8', 0)
        
        # 预测
        prediction = predict_match(conf, diff, home_8, draw_8, away_8)
        segment = get_segment(conf)
        
        results.append({
            'match_name': match_name,
            'confidence': conf,
            'diff': diff,
            'home_8': home_8,
            'draw_8': draw_8,
            'away_8': away_8,
            'prediction': prediction,
            'segment': segment,
        })
    
    return results

def analyze_source_files(source_dir):
    """分析源数据目录中的所有文件"""
    results = []
    
    # 遍历目录
    for filename in os.listdir(source_dir):
        if not filename.endswith('_源数据.md'):
            continue
        
        # 提取日期
        match = re.search(r'([周][\u4e00-\u9fa5]\d+)_', filename)
        if match:
            date_num = match.group(1)
        else:
            date_num = filename[:6]
        
        # 读取源数据文件
        filepath = os.path.join(source_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取V7预测和8变化数据
        # 这里需要根据实际文件格式进行调整
        
        results.append({
            'filename': filename,
            'date_num': date_num,
        })
    
    return results

def load_from_json_summary(json_path):
    """从汇总JSON文件加载数据并预测"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        matches = data.get('matches', [])
    else:
        matches = data
    
    results = []
    
    for match in matches:
        match_name = match.get('match_name', '')
        
        # V7预测数据
        v7 = match.get('v7_prediction', {})
        conf = v7.get('confidence', 0)
        diff = v7.get('win_rate_diff', 0)
        
        # 8变化
        odds_change = match.get('odds_change', {})
        home_8 = odds_change.get('home_8', 0)
        draw_8 = odds_change.get('draw_8', 0)
        away_8 = odds_change.get('away_8', 0)
        
        # 预测
        if conf >= 55:
            prediction = predict_match(conf, diff, home_8, draw_8, away_8)
            segment = get_segment(conf)
        else:
            prediction = '不使用'
            segment = '低于55%'
        
        results.append({
            'match': match_name,
            'conf': conf,
            'diff': diff,
            'home_8': home_8,
            'draw_8': draw_8,
            'away_8': away_8,
            'prediction': prediction,
            'segment': segment,
        })
    
    return results

def print_results(results, show_all=True):
    """打印预测结果"""
    print("\n" + "="*100)
    print("V7+8变化 分段权重分析法 预测结果")
    print("="*100)
    
    # 按分段统计
    segment_stats = {}
    
    for r in results:
        seg = r.get('segment', 'N/A')
        if seg not in segment_stats:
            segment_stats[seg] = {'total': 0, 'used': 0}
        segment_stats[seg]['total'] += 1
        if r['prediction'] != '不使用':
            segment_stats[seg]['used'] += 1
    
    print("\n分段统计:")
    for seg in ['55-60%', '60-65%', '65-70%', '70-75%', '75-80%', '80%+', '低于55%']:
        if seg in segment_stats:
            stats = segment_stats[seg]
            print(f"  {seg}: {stats['used']} 场")
    
    # 打印详细结果
    print("\n详细预测:")
    print("-"*100)
    print(f"{'比赛':<30} {'置信度':>6} {'胜率差':>8} {'8变化':>12} {'分段':>8} {'预测':>6}")
    print("-"*100)
    
    for r in results:
        match = r.get('match', r.get('match_name', ''))[:28]
        conf = r.get('conf', 0)
        diff = r.get('diff', 0)
        h8 = r.get('home_8', 0)
        d8 = r.get('draw_8', 0)
        a8 = r.get('away_8', 0)
        seg = r.get('segment', '')
        pred = r.get('prediction', '')
        
        print(f"{match:<30} {conf:>5}% {diff:>+7}% [{h8:>+2},{d8:>+2},{a8:>+2}] {seg:>8} {pred:>6}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='V7+8变化 分段权重分析法')
    parser.add_argument('--json', '-j', help='JSON数据文件路径', 
                       default='matches_full_2026-03-12.json')
    parser.add_argument('--dir', '-d', help='源数据目录', 
                       default='.')
    parser.add_argument('--output', '-o', help='输出文件路径')
    
    args = parser.parse_args()
    
    # 查找JSON文件
    json_path = args.json
    if not os.path.exists(json_path):
        # 尝试在不同目录查找
        for root, dirs, files in os.walk('.'):
            for f in files:
                if f.startswith('matches_full_') and f.endswith('.json'):
                    json_path = os.path.join(root, f)
                    print(f"找到数据文件: {json_path}")
                    break
    
    if os.path.exists(json_path):
        print(f"正在分析: {json_path}")
        results = load_from_json_summary(json_path)
        print_results(results)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {args.output}")
    else:
        print("未找到数据文件，请指定 --json 参数")
        print(__doc__)

if __name__ == '__main__':
    main()
