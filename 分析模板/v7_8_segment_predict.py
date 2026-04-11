# -*- coding: utf-8 -*-
"""
V7+8变化 分段权重分析法 - 命令行预测工具
基于置信度分段的足球比赛预测公式
"""

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
        return '低于55%'

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
    if segment == '低于55%':
        return '不使用', segment
    
    config = SEGMENT_CONFIG[segment]
    t1 = config['t1']
    t2 = config['t2']
    t3 = config['t3']
    default = config['default']
    
    # 高开程度 = 置信度 - 胜率差
    over = conf - diff
    
    # 规则1: 强信号 - 胜率差足够大
    if diff >= t1:
        return '主胜', segment
    if diff <= -t1:
        return '客胜', segment
    
    # 规则2: 高开走冷 - 置信度高估但实际实力差距不大
    if over > t2 and abs(diff) < t3:
        return '平局', segment
    
    # 规则3: 8变化极端值
    if home_8 >= 2:
        return '主胜', segment
    if home_8 <= -3:
        return '平局', segment
    if away_8 >= 3:
        return '客胜', segment
    
    # 规则4: 默认值
    return default, segment

def print_formula():
    """打印公式说明"""
    print("\n" + "="*70)
    print("V7+8变化 分段权重分析法 公式说明")
    print("="*70)
    print("\n分段配置:")
    print("-"*70)
    print(f"{'分段':<10} {'胜率差阈值':>12} {'高开阈值':>10} {'小胜差阈值':>12} {'默认':>8}")
    print("-"*70)
    for seg, cfg in SEGMENT_CONFIG.items():
        print(f"{seg:<10} >={cfg['t1']:>10}% >{cfg['t2']:>8}% <{cfg['t3']:>10}% {cfg['default']:>8}")
    print("-"*70)
    
    print("\n预测规则 (按优先级):")
    print("  规则1: 胜率差 >= 阈值 → 主胜")
    print("  规则2: 胜率差 <= -阈值 → 客胜")
    print("  规则3: 高开(置信度-胜率差 > 高开阈值) 且 |胜率差| < 小胜差阈值 → 平局")
    print("  规则4: 主胜8变化 >= 2 → 主胜")
    print("  规则5: 主胜8变化 <= -3 → 平局")
    print("  规则6: 客胜8变化 >= 3 → 客胜")
    print("  规则7: 默认 → 该分段的默认值")

def interactive_predict():
    """交互式预测"""
    print_formula()
    
    print("\n" + "="*70)
    print("开始预测 (输入 q 退出)")
    print("="*70)
    
    while True:
        try:
            print("\n请输入比赛数据 (格式: 置信度,胜率差,主胜8,平局8,客胜8)")
            print("例如: 59,37,2,1,0  表示 置信度59%, 胜率差+37%, 8变化[2,1,0]")
            user_input = input("\n> ").strip()
            
            if user_input.lower() == 'q':
                print("退出预测")
                break
            
            parts = user_input.split(',')
            if len(parts) != 5:
                print("输入格式错误！请输入5个数字，用逗号分隔")
                continue
            
            conf = int(parts[0])
            diff = int(parts[1])
            home_8 = int(parts[2])
            draw_8 = int(parts[3])
            away_8 = int(parts[4])
            
            prediction, segment = predict_match(conf, diff, home_8, draw_8, away_8)
            
            over = conf - diff
            print(f"\n--- 分析结果 ---")
            print(f"  置信度: {conf}%")
            print(f"  胜率差: {diff:+d}%")
            print(f"  8变化: [{home_8:+d},{draw_8:+d},{away_8:+d}]")
            print(f"  高开程度: {over:+.0f}% ({'主胜高开' if over > 0 else '客胜高开' if over < 0 else '无'})")
            print(f"  所属分段: {segment}")
            print(f"  ★ 预测结果: {prediction}")
            
        except ValueError:
            print("输入格式错误！请输入数字")
        except Exception as e:
            print(f"错误: {e}")

def batch_predict(data_file):
    """批量预测"""
    import json
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 根据数据结构提取数据
    if isinstance(data, dict):
        matches = data.get('matches', [])
    else:
        matches = data
    
    results = []
    
    print(f"\n共 {len(matches)} 场比赛")
    print("-"*100)
    print(f"{'比赛':<30} {'置信度':>6} {'胜率差':>8} {'8变化':>12} {'分段':>8} {'预测':>6}")
    print("-"*100)
    
    for match in matches:
        # 尝试不同的字段名
        match_name = (match.get('match_name') or 
                     match.get('match') or 
                     match.get('编号') or
                     f"{match.get('主队','')} vs {match.get('客队','')}")
        
        # V7数据
        v7 = match.get('v7_prediction') or match.get('v7') or {}
        conf = v7.get('confidence', 0) if isinstance(v7, dict) else 0
        diff = v7.get('win_rate_diff', 0) if isinstance(v7, dict) else 0
        
        # 8变化
        odds = match.get('odds_change') or match.get('eight_change') or {}
        home_8 = odds.get('home_8', 0) if isinstance(odds, dict) else 0
        draw_8 = odds.get('draw_8', 0) if isinstance(odds, dict) else 0
        away_8 = odds.get('away_8', 0) if isinstance(odds, dict) else 0
        
        if conf > 0:
            prediction, segment = predict_match(conf, diff, home_8, draw_8, away_8)
            print(f"{match_name[:28]:<30} {conf:>5}% {diff:>+7}% [{home_8:+2},{draw_8:+2},{away_8:+2}] {segment:>8} {prediction:>6}")
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

def main():
    """主函数"""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description='V7+8变化 分段权重分析法 - 预测工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python v7_8_segment_predict.py -i                    # 交互式预测
  python v7_8_segment_predict.py -f data.json           # 批量预测
  python v7_8_segment_predict.py --formula               # 查看公式说明
        """
    )
    parser.add_argument('--formula', '-fml', action='store_true', help='显示公式说明')
    parser.add_argument('--interactive', '-i', action='store_true', help='交互式预测模式')
    parser.add_argument('--file', '-f', help='批量预测数据文件')
    
    args = parser.parse_args()
    
    if args.formula:
        print_formula()
    elif args.interactive:
        interactive_predict()
    elif args.file:
        batch_predict(args.file)
    else:
        print_formula()
        print("\n请使用参数:")
        print("  -i, --interactive  交互式预测")
        print("  -f, --file        批量预测")
        print("  --formula         查看公式说明")

if __name__ == '__main__':
    main()
