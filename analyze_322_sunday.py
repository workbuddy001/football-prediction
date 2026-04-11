"""
3.22 周日比赛 - 完整分析脚本（含近况评分）
基于 analyze_319_auto_v6.py 和 analyze_321_with_form.py 整合
"""

import os
import re
import glob

DATA_DIR = "d:/work/workbuddy/足球预测/分析模板/3.22"

def extract_match_data(match_id):
    """从源数据文件提取比赛数据"""
    file_path = f"{DATA_DIR}/{match_id}_*_源数据.md"
    files = glob.glob(file_path)
    
    if not files:
        return None
    
    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取基本信息
        home_match = re.search(r'\| 主队 \| (.+) \|', content)
        away_match = re.search(r'\| 客队 \| (.+) \|', content)
        time_match = re.search(r'\| 比赛时间 \| (.+) \|', content)
        league_match = re.search(r'\| 赛事 \| (.+) \|', content)
        macao_match = re.search(r'\| 澳门推荐 \| (.+) \|', content)
        home_form_match = re.search(r'\| 主队近况走势 \| (.+) \|', content)
        away_form_match = re.search(r'\| 客队近况走势 \| (.+) \|', content)
        
        # 提取竞彩赔率（从"五、赔率变动对比"表格）
        jingcai_pattern = r'\| 竞\*官\* \| ([\d.]+) \| ([\d.]+) \| [↓↑—]+ \| ([\d.]+) \| ([\d.]+) \| [↓↑—]+ \| ([\d.]+) \| ([\d.]+) \| [↓↑—]+ \|'
        jingcai_match = re.search(jingcai_pattern, content)
        
        if jingcai_match:
            init_home = float(jingcai_match.group(1))
            init_draw = float(jingcai_match.group(3))
            init_away = float(jingcai_match.group(5))
            real_home = float(jingcai_match.group(2))
            real_draw = float(jingcai_match.group(4))
            real_away = float(jingcai_match.group(6))
        else:
            return None
        
        return {
            'home_team': home_match.group(1).strip() if home_match else '',
            'away_team': away_match.group(1).strip() if away_match else '',
            'match_time': time_match.group(1).strip() if time_match else '',
            'league': league_match.group(1).strip() if league_match else '',
            'macao_tip': macao_match.group(1).strip() if macao_match else '',
            'home_form': home_form_match.group(1).strip() if home_form_match else '',
            'away_form': away_form_match.group(1).strip() if away_form_match else '',
            'init_home': init_home, 'init_draw': init_draw, 'init_away': init_away,
            'home': real_home, 'draw': real_draw, 'away': real_away,
        }
    except Exception as e:
        print(f"读取{match_id}出错: {e}")
        return None

def calculate_form_score(trend):
    """计算近况评分 - 复核版本
    评分规则：最近一场权重2，其他权重1（共5场权重）
    得分：赢=3分，平=1分，输=0分
    满分：3×2 + 3×4 = 18分（最近1场×2 + 其他4场×1）
    """
    if not trend or trend == "暂无":
        return None, None
    
    # 映射: W=胜(3分), D=平(1分), L=负(0分)
    score_map = {'W': 3, 'D': 1, 'L': 0}
    
    # 只取最近5场
    recent = trend[:5] if len(trend) >= 5 else trend
    
    scores = []
    for i, char in enumerate(recent):
        if char in score_map:
            # 最近一场(i=0)权重2，其他权重1
            weight = 2 if i == 0 else 1
            scores.append(score_map[char] * weight)
    
    total_score = sum(scores)
    # 标准化到0-100分（满分18分）
    normalized_score = total_score / 18 * 100 if scores else None
    
    return total_score, normalized_score

def calculate_confidence(home, draw, away):
    """计算置信度和各选项概率"""
    total = home + draw + away
    home_rate = (total / home) * 100 / 3
    draw_rate = (total / draw) * 100 / 3
    away_rate = (total / away) * 100 / 3
    total_rate = home_rate + draw_rate + away_rate
    home_rate = home_rate / total_rate * 100
    draw_rate = draw_rate / total_rate * 100
    away_rate = away_rate / total_rate * 100
    max_rate = max(home_rate, draw_rate, away_rate)
    return max_rate, home_rate, draw_rate, away_rate

def fmt_change(init_val, real_val):
    """格式化赔率变化幅度"""
    if init_val is None or real_val is None or init_val == 0:
        return 0
    pct = (real_val - init_val) / init_val * 100
    return pct

def get_macao_direction(macao_tip, home_team, away_team):
    """判断澳门推荐方向"""
    if '和局' in macao_tip or '平局' in macao_tip:
        return '和局'
    elif home_team and home_team.split()[0] in macao_tip:
        return '主队'
    elif away_team and away_team.split()[0] in macao_tip:
        return '客队'
    else:
        # 模糊匹配
        if '贏' in macao_tip or '赢' in macao_tip:
            if home_team[:2] in macao_tip or home_team[:3] in macao_tip:
                return '主队'
            elif away_team[:2] in macao_tip or away_team[:3] in macao_tip:
                return '客队'
        return '未知'

# 比赛ID列表（28场）
match_ids = [
    "周日001", "周日002", "周日003", "周日004", "周日005", "周日006", "周日007",
    "周日008", "周日009", "周日010", "周日011", "周日012", "周日013", "周日014",
    "周日015", "周日016", "周日017", "周日018", "周日019", "周日020", "周日021",
    "周日022", "周日023", "周日024", "周日025", "周日026", "周日027", "周日028"
]

# 提取所有比赛数据
print("=" * 100)
print("3.22 周日 28场比赛数据提取与近况评分复核")
print("=" * 100)
print("\n【近况评分计算方式复核】")
print("- 权重：最近一场×2，其他4场×1（共6分权重）")
print("- 得分：赢=3分，平=1分，输=0分")
print("- 满分：3×2 + 3×4 = 18分")
print("- 近况差 = 主队得分 - 客队得分")
print("- 标准化：得分/18×100")
print()

results = []

for mid in match_ids:
    data = extract_match_data(mid)
    if not data:
        print(f"{mid}: 数据提取失败")
        continue
    
    # 计算近况评分
    home_score, home_norm = calculate_form_score(data['home_form'])
    away_score, away_norm = calculate_form_score(data['away_form'])
    score_diff = (home_score - away_score) if (home_score and away_score) else 0
    
    # 计算置信度
    confidence, home_rate, draw_rate, away_rate = calculate_confidence(
        data['home'], data['draw'], data['away']
    )
    
    # 计算赔率变化
    pct_h = fmt_change(data['init_home'], data['home'])
    pct_d = fmt_change(data['init_draw'], data['draw'])
    pct_a = fmt_change(data['init_away'], data['away'])
    
    # 澳门方向
    macao_dir = get_macao_direction(data['macao_tip'], data['home_team'], data['away_team'])
    
    # 原始预测
    if home_rate >= draw_rate and home_rate >= away_rate:
        raw_pred = "主胜"
    elif away_rate >= home_rate and away_rate >= draw_rate:
        raw_pred = "客胜"
    else:
        raw_pred = "平局"
    
    results.append({
        'id': mid,
        'home_team': data['home_team'],
        'away_team': data['away_team'],
        'match_time': data['match_time'],
        'league': data['league'],
        'home_form': data['home_form'],
        'away_form': data['away_form'],
        'home_score': home_score,
        'away_score': away_score,
        'score_diff': score_diff,
        'init_odds': f"{data['init_home']}/{data['init_draw']}/{data['init_away']}",
        'real_odds': f"{data['home']}/{data['draw']}/{data['away']}",
        'pct_change': f"主{pct_h:+.1f}% 平{pct_d:+.1f}% 客{pct_a:+.1f}%",
        'confidence': confidence,
        'home_rate': home_rate,
        'draw_rate': draw_rate,
        'away_rate': away_rate,
        'macao_tip': data['macao_tip'],
        'macao_dir': macao_dir,
        'raw_pred': raw_pred,
        'pct_h': pct_h,
        'pct_d': pct_d,
        'pct_a': pct_a,
    })

# 输出完整数据列表
print("=" * 100)
print("【完整数据列表（标准格式）】")
print("=" * 100)
print(f"\n| 编号 | 对阵 | 置信度 | 澳门心水 | 近况差 | 初盘(胜/平/负) | 即时(胜/平/负) | 变化(H/D/A) | 最终预测 |")
print(f"|------|------|--------|----------|--------|----------------|----------------|-------------|----------|")

for r in results:
    print(f"| {r['id']} | {r['home_team']} vs {r['away_team']} | {r['confidence']:.1f}% | {r['macao_dir']} | {r['score_diff']:+d} | {r['init_odds']} | {r['real_odds']} | {r['pct_change']} | {r['raw_pred']} |")

# 输出近况评分详细
print("\n" + "=" * 100)
print("【近况评分详细复核】")
print("=" * 100)
print(f"\n| 编号 | 对阵 | 主队走势 | 客队走势 | 主队分 | 客队分 | 近况差 | 标准化主 | 标准化客 |")
print(f"|------|------|----------|----------|--------|--------|--------|----------|----------|")

for r in results:
    home_norm = r['home_score'] / 18 * 100 if r['home_score'] else 0
    away_norm = r['away_score'] / 18 * 100 if r['away_score'] else 0
    print(f"| {r['id']} | {r['home_team']} vs {r['away_team']} | {r['home_form'][:6] if r['home_form'] else '-':<8} | {r['away_form'][:6] if r['away_form'] else '-':<8} | {r['home_score'] if r['home_score'] else '-':<6} | {r['away_score'] if r['away_score'] else '-':<6} | {r['score_diff']:+6.0f} | {home_norm:6.1f}% | {away_norm:6.1f}% |")

# 规律审核 - 找出最稳和可能爆冷的比赛
print("\n" + "=" * 100)
print("【规律二次审核 - 最稳比赛列表】")
print("=" * 100)
print("\n筛选条件（基于Memory中的规律体系）：")
print("1. 规律一：澳门分胜负 + 置信度≥66%")
print("2. 规律H：置信度≥66% + 赔率变化均<5% + 澳门推非主方向 → 按置信度方向打出")
print("3. 规律O：近况差+8以上 + 赔率微变<2% → 主队打出")
print("4. 全锁定状态 + 近况差≥8 → 主队超强信号")
print()

stable_picks = []
for r in results:
    is_stable = False
    reason = []
    
    # 条件1: 规律一 - 澳门分胜负 + 置信度≥66%
    if r['macao_dir'] != '和局' and r['confidence'] >= 66:
        is_stable = True
        reason.append("规律一(≥66%)")
    
    # 条件2: 规律H - 置信度≥66% + 赔率变化均<5%
    if r['confidence'] >= 66 and abs(r['pct_h']) < 5 and abs(r['pct_d']) < 5 and abs(r['pct_a']) < 5:
        is_stable = True
        reason.append("规律H(稳定)")
    
    # 条件3: 规律O - 近况差+8以上 + 赔率微变<2%
    if r['score_diff'] >= 8 and abs(r['pct_h']) < 2 and abs(r['pct_d']) < 2 and abs(r['pct_a']) < 2:
        is_stable = True
        reason.append("规律O(近况强)")
    
    # 条件4: 全锁定状态（赔率变化均<0.5%）+ 近况差≥8
    if abs(r['pct_h']) < 0.5 and abs(r['pct_d']) < 0.5 and abs(r['pct_a']) < 0.5 and r['score_diff'] >= 8:
        is_stable = True
        reason.append("全锁定+近况强")
    
    if is_stable:
        stable_picks.append({
            'id': r['id'],
            'match': f"{r['home_team']} vs {r['away_team']}",
            'confidence': r['confidence'],
            'score_diff': r['score_diff'],
            'macao_dir': r['macao_dir'],
            'prediction': r['raw_pred'],
            'reason': ' + '.join(reason)
        })

if stable_picks:
    print(f"| 编号 | 对阵 | 置信度 | 近况差 | 澳门 | 预测 | 稳定原因 |")
    print(f"|------|------|--------|--------|------|------|----------|")
    for p in stable_picks:
        print(f"| {p['id']} | {p['match']:<22} | {p['confidence']:.1f}% | {p['score_diff']:+d} | {p['macao_dir']:<4} | {p['prediction']:<4} | {p['reason']} |")
else:
    print("未找到满足最稳条件的比赛")

print("\n" + "=" * 100)
print("【规律二次审核 - 可能爆冷比赛列表】")
print("=" * 100)
print("\n筛选条件（基于Memory中的规律体系）：")
print("1. 规律N：规律五触发（主升>5%）+ 澳门推荐客队 + 客队被造热 → 反向主胜")
print("2. 规律五：主胜升幅>5% → 直接预测和局")
print("3. 极端造热：某方向赔率降>10% + 近况不支持 → 反向")
print("4. 规律Q：近况差极大(+10) + 置信度<65% + 赔率全变>2% → 防过热平局")
print("5. 规律R：真假造热辨别 - 澳门心水方向赔率降>10% + 其他两向均升 → 反向")
print()

upset_picks = []
for r in results:
    is_upset = False
    reason = []
    upset_direction = r['raw_pred']
    
    # 条件1: 规律五 - 主胜升幅>5%
    if r['pct_h'] > 5:
        is_upset = True
        reason.append("规律五(主升>5%)")
        upset_direction = "平局"
    
    # 条件2: 极端造热 - 某方向赔率降>10%
    if r['pct_h'] < -10:
        is_upset = True
        reason.append(f"主极端造热({r['pct_h']:.1f}%)")
        upset_direction = "客胜/平局"
    if r['pct_a'] < -10:
        is_upset = True
        reason.append(f"客极端造热({r['pct_a']:.1f}%)")
        upset_direction = "主胜/平局"
    
    # 条件3: 规律Q - 近况差极大 + 置信度<65% + 赔率全变>2%
    if abs(r['score_diff']) >= 10 and r['confidence'] < 65 and abs(r['pct_h']) > 2 and abs(r['pct_d']) > 2 and abs(r['pct_a']) > 2:
        is_upset = True
        reason.append("规律Q(过热防平)")
        upset_direction = "平局"
    
    # 条件4: 规律R - 澳门方向赔率降>10% + 其他两向均升
    if r['macao_dir'] == '主队' and r['pct_h'] < -10 and r['pct_d'] > 0 and r['pct_a'] > 0:
        is_upset = True
        reason.append("规律R(真造热)")
        upset_direction = "客胜/平局"
    if r['macao_dir'] == '客队' and r['pct_a'] < -10 and r['pct_h'] > 0 and r['pct_d'] > 0:
        is_upset = True
        reason.append("规律R(真造热)")
        upset_direction = "主胜/平局"
    
    # 条件5: 低置信度 + 澳门造热
    if r['confidence'] < 55 and r['macao_dir'] != '和局':
        if (r['macao_dir'] == '主队' and r['pct_h'] < -5) or (r['macao_dir'] == '客队' and r['pct_a'] < -5):
            is_upset = True
            reason.append("低置信+造热")
            upset_direction = "反向/平局"
    
    if is_upset:
        upset_picks.append({
            'id': r['id'],
            'match': f"{r['home_team']} vs {r['away_team']}",
            'confidence': r['confidence'],
            'score_diff': r['score_diff'],
            'macao_dir': r['macao_dir'],
            'original': r['raw_pred'],
            'upset': upset_direction,
            'reason': ' + '.join(reason)
        })

if upset_picks:
    print(f"| 编号 | 对阵 | 置信度 | 近况差 | 澳门 | 原预测 | 爆冷方向 | 原因 |")
    print(f"|------|------|--------|--------|------|--------|----------|------|")
    for p in upset_picks:
        print(f"| {p['id']} | {p['match']:<22} | {p['confidence']:.1f}% | {p['score_diff']:+d} | {p['macao_dir']:<4} | {p['original']:<4} | {p['upset']:<8} | {p['reason']} |")
else:
    print("未找到明显的爆冷信号")

# 统计
print("\n" + "=" * 100)
print("【统计汇总】")
print("=" * 100)
print(f"\n总场次: {len(results)}")
print(f"最稳比赛: {len(stable_picks)} 场")
print(f"可能爆冷: {len(upset_picks)} 场")
print(f"\n预测分布:")
print(f"  主胜: {sum(1 for r in results if r['raw_pred'] == '主胜')} 场")
print(f"  平局: {sum(1 for r in results if r['raw_pred'] == '平局')} 场")
print(f"  客胜: {sum(1 for r in results if r['raw_pred'] == '客胜')} 场")

# 保存结果
output_file = "d:/work/workbuddy/足球预测/3.22_analysis_result.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("3.22 周日 28场比赛分析结果\n")
    f.write("=" * 100 + "\n\n")
    f.write("【近况评分计算方式】\n")
    f.write("- 权重：最近一场×2，其他4场×1（共6分权重）\n")
    f.write("- 得分：赢=3分，平=1分，输=0分\n")
    f.write("- 满分：3×2 + 3×4 = 18分\n")
    f.write("- 近况差 = 主队得分 - 客队得分\n\n")
    
    f.write("【完整数据列表】\n\n")
    for r in results:
        f.write(f"{r['id']} {r['home_team']} vs {r['away_team']}\n")
        f.write(f"  联赛: {r['league']} | 时间: {r['match_time']}\n")
        f.write(f"  赔率: {r['init_odds']} → {r['real_odds']} | 变化: {r['pct_change']}\n")
        f.write(f"  置信度: {r['confidence']:.1f}% (主{int(r['home_rate'])}% 平{int(r['draw_rate'])}% 客{int(r['away_rate'])}%)\n")
        f.write(f"  主队走势: {r['home_form']} ({r['home_score']}分) | 客队走势: {r['away_form']} ({r['away_score']}分)\n")
        f.write(f"  近况差: {r['score_diff']:+d} | 澳门: {r['macao_tip']} ({r['macao_dir']})\n")
        f.write(f"  预测: {r['raw_pred']}\n\n")

print(f"\n分析结果已保存到: {output_file}")
