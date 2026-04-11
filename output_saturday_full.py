# -*- coding: utf-8 -*-
"""
输出周六比赛完整预测列表 - 每个表格都显示近况差
优化版：去重 + 正确提取近况差
"""
import re

# 读取结果文件
with open('3.21_result.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 解析所有周六比赛数据（只取第一部分数据）
saturday_matches = []
seen = set()

for line in lines:
    if not line.startswith('周六'):
        continue
    if 'vs' not in line:
        continue
    
    parts = line.split()
    if len(parts) < 12:
        continue
    
    match_id = parts[0]
    # 去重
    if match_id in seen:
        continue
    seen.add(match_id)
    
    # 对阵
    idx = line.find('vs')
    match_name = line[line.find(match_id)+len(match_id)+1:idx-1]
    
    # 赔率
    odds_match = re.search(r'(\d+\.\d+/\d+\.\d+/\d+\.\d+)', line)
    odds = odds_match.group(1) if odds_match else ''
    
    # 置信度
    conf_match = re.search(r'(\d+\.\d+)%', line)
    conf = float(conf_match.group(1)) if conf_match else 0
    
    # 澳门
    macao_match = re.search(r'(\S+)\s+贏', line)
    macao = macao_match.group(1) if macao_match else '和局'
    
    # 预测
    pred_match = re.search(r'(主胜|客胜|和局)', line)
    pred = pred_match.group(1) if pred_match else ''
    
    # 赔率变化 - 多种格式兼容
    h_chg_match = re.search(r'H([+-]?\d+\.?\d*)%', line)
    d_chg_match = re.search(r'D([+-]?\d+\.?\d*)%', line)
    a_chg_match = re.search(r'A([+-]?\d+\.?\d*)%', line)
    
    h_val = float(h_chg_match.group(1)) if h_chg_match else 0
    d_val = float(d_chg_match.group(1)) if d_chg_match else 0
    a_val = float(a_chg_match.group(1)) if a_chg_match else 0
    
    # 近况差 - 格式：队伍近5场 +近况差 分析
    # 例如: LDLWD  WDLDW    -6   双方近况接近 或 LDLWD  WDLDW    +9   [!]近况支持+赔不变
    # 使用更灵活的正则
    form_diff = 0
    analysis = ''
    
    # 查找 "字母序列 字母序列 数字 分析" 模式
    form_pattern = re.search(r'(\w{5})\s+(\w{5})\s+([+-]?\d+)\s+(.+)$', line)
    if form_pattern:
        form_diff = int(form_pattern.group(3))
        analysis = form_pattern.group(4)
    
    saturday_matches.append({
        'id': match_id,
        'match': match_name,
        'odds': odds,
        'confidence': conf,
        'macao': macao,
        'prediction': pred,
        'h_chg': h_val,
        'd_chg': d_val,
        'a_chg': a_val,
        'form_diff': form_diff,
        'analysis': analysis
    })

# 按编号排序
saturday_matches.sort(key=lambda x: x['id'])

# 分类
single_picks = []  # 置信度>=66%
key_matches = []   # 重点比赛
other = []        # 其他

for m in saturday_matches:
    if m['confidence'] >= 66:
        single_picks.append(m)
    elif '[!]' in m['analysis'] or '近况矛盾' in m['analysis'] or 'OK' in m['analysis'] or abs(m['form_diff']) >= 4:
        key_matches.append(m)
    else:
        other.append(m)

# 输出
print('='*135)
print('周六比赛完整预测列表（每个表格都显示近况差）')
print('='*135)

# 单选推荐
print('\n' + '='*80)
print('【单选推荐】置信度>=66%')
print('='*80)
print(f"{'编号':<8} {'对阵':<20} {'竞彩即时':<14} {'置信度':<8} {'澳门':<10} {'预测':<4} {'赔率变化(H/D/A)':<22} {'近况差':<6}")
print('-'*135)
for m in single_picks:
    chg_str = f"H{m['h_chg']:+.1f}% D{m['d_chg']:+.1f}% A{m['a_chg']:+.1f}%"
    print(f"{m['id']:<8} {m['match']:<20} {m['odds']:<14} {m['confidence']:.1f}%    {m['macao']:<10} {m['prediction']:<4} {chg_str:<22} {m['form_diff']:+5}")

# 重点比赛
print('\n' + '='*80)
print('【重点比赛】需防冷/防反向/近况差>=4')
print('='*80)
print(f"{'编号':<8} {'对阵':<20} {'竞彩即时':<14} {'澳门':<10} {'预测':<4} {'赔率变化(H/D/A)':<22} {'近况差':<6} {'状态分析'}")
print('-'*135)
for m in key_matches:
    chg_str = f"H{m['h_chg']:+.1f}% D{m['d_chg']:+.1f}% A{m['a_chg']:+.1f}%"
    print(f"{m['id']:<8} {m['match']:<20} {m['odds']:<14} {m['macao']:<10} {m['prediction']:<4} {chg_str:<22} {m['form_diff']:+5}   {m['analysis']}")

# 其他比赛
print('\n' + '='*80)
print('【其他比赛】')
print('='*80)
print(f"{'编号':<8} {'对阵':<20} {'竞彩即时':<14} {'置信度':<8} {'澳门':<10} {'预测':<4} {'赔率变化(H/D/A)':<22} {'近况差':<6}")
print('-'*135)
for m in other:
    chg_str = f"H{m['h_chg']:+.1f}% D{m['d_chg']:+.1f}% A{m['a_chg']:+.1f}%"
    print(f"{m['id']:<8} {m['match']:<20} {m['odds']:<14} {m['confidence']:.1f}%    {m['macao']:<10} {m['prediction']:<4} {chg_str:<22} {m['form_diff']:+5}")

print('\n' + '='*80)
print('【关键总结】')
print('='*80)

# 找出高压区比赛：近况差>=4 + 赔率不变（主胜或客胜）
# 主队近况好 + 主胜赔率不变 或 客队近况好 + 客胜赔率不变
high_risk = []
for m in saturday_matches:
    if abs(m['form_diff']) >= 4 and 'OK' not in m['analysis']:
        # 主队近况好且主胜赔率不变
        if m['form_diff'] > 0 and m['h_chg'] == 0:
            high_risk.append(m)
        # 客队近况好且客胜赔率不变（包括置信度>=66%的高热比赛）
        elif m['form_diff'] < 0 and m['a_chg'] == 0:
            high_risk.append(m)

# 矛盾比赛
contradict = [m for m in saturday_matches if abs(m['form_diff']) >= 4 and ('!' in m['analysis']) and 'OK' not in m['analysis'] and m not in high_risk]
# 正路比赛
ok_match = [m for m in saturday_matches if 'OK' in m['analysis']]

print(f"高度防冷比赛({len(high_risk)}场) - 近况好+赔率不变:")
for m in high_risk:
    print(f"   {m['id']} {m['match']} - 近况差:{m['form_diff']:+d} - 赔率变化:H{m['h_chg']:.0f}% A{m['a_chg']:.0f}%")

print(f"\n需防反向/矛盾比赛({len(contradict)}场) - 近况与赔率变动矛盾:")
for m in contradict:
    print(f"   {m['id']} {m['match']} - 近况差:{m['form_diff']:+d}")

print(f"\n正路比赛({len(ok_match)}场) - 近况支持+赔率降水:")
for m in ok_match:
    print(f"   {m['id']} {m['match']} - 近况差:{m['form_diff']:+d}")
