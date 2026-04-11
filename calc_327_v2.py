# -*- coding: utf-8 -*-
"""
3.27比赛完整分析脚本 - 应用3.28优化后的筹码分流体系（A-G七个维度）
"""

# ============================================================
# 16场比赛完整数据
# ============================================================
matches = [
    {
        'id': '周五001', 'home': '新西兰', 'away': '芬兰',
        'jc_init': (2.05, 3.00, 3.25), 'jc_real': (2.60, 2.90, 2.50),
        'omen': '客队胜', 'home_form': 'LLDLLL', 'away_form': 'WLLWLL'
    },
    {
        'id': '周五002', 'home': '中国', 'away': '库拉索',
        'jc_init': (3.50, 3.15, 1.90), 'jc_real': (5.42, 3.65, 1.49),
        'omen': '客队胜', 'home_form': 'WLLWLL', 'away_form': 'DWDWWD'
    },
    {
        'id': '周五003', 'home': '澳大利亚', 'away': '喀麦隆',
        'jc_init': (1.65, 3.27, 4.60), 'jc_real': (1.78, 3.25, 3.85),
        'omen': '无', 'home_form': '无', 'away_form': '无'
    },
    {
        'id': '周五004', 'home': '神户胜利', 'away': '广岛三箭',
        'jc_init': (2.47, 3.15, 2.47), 'jc_real': (2.51, 3.12, 2.44),
        'omen': '主队胜', 'home_form': 'DDWWWW', 'away_form': 'LLWWLL'
    },
    {
        'id': '周五005', 'home': '奥地利', 'away': '加纳',
        'jc_init': (1.45, 3.90, 5.45), 'jc_real': (1.43, 3.95, 5.65),
        'omen': '主队胜', 'home_form': 'DWLWWW', 'away_form': 'LLLWWW'
    },
    {
        'id': '周五006', 'home': '南非', 'away': '巴拿马',
        'jc_init': (1.90, 3.00, 3.70), 'jc_real': (1.97, 2.90, 3.61),
        'omen': '客队胜', 'home_form': 'LWLWWW', 'away_form': 'LDWWDW'
    },
    {
        'id': '周五007', 'home': '希腊', 'away': '巴拉圭',
        'jc_init': (1.90, 3.15, 3.50), 'jc_real': (1.89, 3.10, 3.60),
        'omen': '和局', 'home_form': 'DWLLLW', 'away_form': 'WLLDWD'
    },
    {
        'id': '周五008', 'home': '荷兰', 'away': '挪威',
        'jc_init': (1.51, 3.90, 4.75), 'jc_real': (1.54, 3.85, 4.55),
        'omen': '和局', 'home_form': 'WDWWWD', 'away_form': 'WWDWWW'
    },
    {
        'id': '周五009', 'home': '英格兰', 'away': '乌拉圭',
        'jc_init': (1.43, 3.75, 6.10), 'jc_real': (1.39, 3.95, 6.40),
        'omen': '主队胜', 'home_form': 'WWWWWW', 'away_form': 'LDWWDW'
    },
    {
        'id': '周五010', 'home': '瑞士', 'away': '德国',
        'jc_init': (2.82, 3.35, 2.10), 'jc_real': (3.45, 3.64, 1.77),
        'omen': '和局', 'home_form': 'DWDWWW', 'away_form': 'WWWWWL'
    },
    {
        'id': '周五011', 'home': '西班牙', 'away': '塞尔维亚',
        'jc_init': (1.30, 5.00, 9.50), 'jc_real': (1.20, 6.00, 12.00),
        'omen': '主队胜', 'home_form': 'DWWWWW', 'away_form': 'WLWLLW'
    },
    {
        'id': '周五012', 'home': '摩洛哥', 'away': '厄瓜多尔',
        'jc_init': (2.65, 2.75, 2.58), 'jc_real': (2.45, 2.70, 2.85),
        'omen': '和局', 'home_form': 'DDWWWD', 'away_form': 'WDDDWD'
    },
    {
        'id': '周六001', 'home': '町田泽维', 'away': '川崎前锋',
        'jc_init': (1.79, 3.56, 3.45), 'jc_real': (1.79, 3.56, 3.45),
        'omen': '主队胜', 'home_form': 'WLWWDW', 'away_form': 'LWLDLD'
    },
    {
        'id': '周六002', 'home': '浦项制铁', 'away': '江原FC',
        'jc_init': (3.06, 2.75, 2.28), 'jc_real': (2.96, 2.75, 2.34),
        'omen': '和局', 'home_form': 'DLDDLD', 'away_form': 'DDDLDL'
    },
    {
        'id': '周六012', 'home': '威廉二世', 'away': '格拉夫',
        'jc_init': (2.03, 3.75, 2.70), 'jc_real': (2.03, 3.75, 2.70),
        'omen': '主队胜', 'home_form': 'WWDWLW', 'away_form': 'LWLDWW'
    },
    {
        'id': '周六014', 'home': '埃因FC', 'away': '埃门',
        'jc_init': (1.93, 3.60, 3.00), 'jc_real': (1.93, 3.60, 3.00),
        'omen': '主队胜', 'home_form': 'LWWLLW', 'away_form': 'LDLWWL'
    },
]

# ============================================================
# 近况差计算（最近一场×2，其余4场×1，W=3 D=1 L=0）
# ============================================================
def calc_form_score(form_str):
    if form_str == '无':
        return None
    score_map = {'W': 3, 'D': 1, 'L': 0}
    chars = list(form_str)
    if len(chars) < 1:
        return 0
    score = score_map.get(chars[0], 0) * 2  # 最近一场×2
    for c in chars[1:5]:  # 其余4场×1
        score += score_map.get(c, 0)
    return score

# ============================================================
# 竞彩置信度计算
# ============================================================
def calc_confidence(odds_h, odds_d, odds_a):
    p_h = 1.0 / odds_h
    p_d = 1.0 / odds_d
    p_a = 1.0 / odds_a
    total = p_h + p_d + p_a
    r_h = p_h / total * 100
    r_d = p_d / total * 100
    r_a = p_a / total * 100
    max_r = max(r_h, r_d, r_a)
    if r_h == max_r:
        direction = '主胜'
    elif r_a == max_r:
        direction = '客胜'
    else:
        direction = '平局'
    return round(r_h, 1), round(r_d, 1), round(r_a, 1), round(max_r, 1), direction

# ============================================================
# 赔率变化计算
# ============================================================
def calc_change(init, real):
    return round((real - init) / init * 100, 1)

# ============================================================
# 筹码分流分析（3.28优化版A-G维度）
# ============================================================
def analyze_chips_flow(m, h_score, a_score, conf_h, conf_d, conf_a, conf_val, conf_dir, ch, cd, ca):
    """
    应用3.28优化后的筹码分流体系：
    A. 赔率变化状态分类
    B. 澳门心水联动规则
    C. 赔率绝对值赔付压力规则
    D. 近况差与赔率可动空间规则
    E. 筹码完全聚焦=反向信号最强
    F. 平赔四象限判断
    G. 联动规则
    """
    
    # 获取即时赔率
    rh, rd, ra = m['jc_real']
    ih, id_, ia = m['jc_init']
    
    # 计算近况差
    form_diff = h_score - a_score if h_score is not None and a_score is not None else None
    
    # A. 赔率变化状态分类
    changes = [abs(ch), abs(cd), abs(ca)]
    max_change = max(changes)
    
    if max_change < 0.5:
        chip_state = "全锁定"
    elif all(c < 0.5 for c in changes):
        chip_state = "全锁定"
    elif sum(1 for c in changes if c > 2) == 2 and any(c < 0.5 for c in changes):
        chip_state = "单向锁定"
    elif all(0.5 <= c <= 2 for c in changes):
        chip_state = "均衡分流"
    elif any(c > 10 for c in changes):
        chip_state = "极端造热"
    elif any(5 <= c <= 10 for c in changes):
        chip_state = "单向造热"
    elif any(c > 10 for c in changes if c > 0):
        chip_state = "极端推离"
    else:
        chip_state = "普通变动"
    
    # 确定造热方向
    heat_dir = None
    heat_pct = 0
    if ch < -5:
        heat_dir, heat_pct = "主", abs(ch)
    if cd < -5:
        heat_dir, heat_pct = "平", abs(cd)
    if ca < -5:
        heat_dir, heat_pct = "客", abs(ca)
    
    # B. 澳门心水联动分析
    omen = m['omen']
    omen_dir_map = {'主队胜': '主', '客队胜': '客', '和局': '平', '无': '无'}
    omen_dir = omen_dir_map.get(omen, '无')
    
    # C. 赔率绝对值赔付压力
    min_odds = min(rh, rd, ra)
    min_dir = '主' if rh == min_odds else ('客' if ra == min_odds else '平')
    
    # 高赔判断 (>3.5)
    high_odds_dirs = []
    if rh > 3.5: high_odds_dirs.append('主')
    if rd > 3.5: high_odds_dirs.append('平')
    if ra > 3.5: high_odds_dirs.append('客')
    
    # D. 近况差与赔率可动空间
    form_move_space = "大"
    if form_diff is not None:
        if abs(form_diff) >= 8:
            form_move_space = "极小(<2%)"
        elif 4 <= abs(form_diff) <= 7:
            form_move_space = "中(2-5%)"
    
    # E. 筹码完全聚焦检测（三重叠加）
    triple_focus = False
    if form_diff is not None:
        if heat_dir and omen_dir != '无':
            # 澳门推 + 造热 + 近况支持同向
            form_supports = (form_diff > 0 and heat_dir == '主') or (form_diff < 0 and heat_dir == '客')
            omen_matches = (omen_dir == heat_dir)
            if form_supports and omen_matches and heat_pct > 10:
                triple_focus = True
    
    # F. 平赔四象限判断
    ping_analysis = ""
    if omen_dir == '平':
        if rd >= 3.0 and rd <= 3.2 and abs(cd) < 2:
            ping_analysis = "诱平陷阱(规律P)"
        elif cd > 0:
            ping_analysis = "平赔被推离(实盘调整)"
        elif abs(cd) < 2:
            ping_analysis = "平局真方向(不敢动)"
        elif cd < -5:
            ping_analysis = "平局难出(规律二)"
    
    # 综合预测
    prediction = conf_dir
    reason = []
    stability = 0
    upset_risk = 0
    
    # 规则应用
    
    # 规则五：主胜升幅>5% → 和局
    if ch > 5:
        prediction = "平局"
        reason.append("规律五:主胜升幅>5%")
        stability += 1
    
    # 规则N：规律五 + 极端造热客队 → 反向主胜
    if ch > 5 and ca < -10 and omen_dir == '客':
        prediction = "主胜"
        reason.append("规律N:极端造热客队反向")
        upset_risk += 3
    elif ch > 5 and ca < -10 and omen_dir == '客' and ca >= -20:
        prediction = "主胜"
        reason.append("规律N(中等):造热反向")
        upset_risk += 2
    
    # 规则O：近况差≥8 + 赔率微变<2%
    if form_diff is not None and form_diff >= 8 and max_change < 2:
        prediction = "主胜"
        reason.append("规律O:近况差+8+赔率微变")
        stability += 2
    
    # 规则Q：近况差极大+置信<65%+赔率全变>2%
    if form_diff is not None and form_diff >= 10 and conf_val < 65 and all(c > 2 for c in [abs(ch), abs(cd), abs(ca)]):
        prediction = "平局"
        reason.append("规律Q:防过热平局")
        upset_risk += 2
    
    # 规则P：平赔3.0-3.2 + 澳门推平 + 变化<2%
    if ping_analysis == "诱平陷阱(规律P)":
        # 诱平反向，赔付最小方向
        prediction = min_dir + "胜" if min_dir != '平' else "平局"
        if min_dir == '主':
            prediction = "主胜"
        elif min_dir == '客':
            prediction = "客胜"
        reason.append("规律P:诱平反向")
    
    # 规则H：置信≥66% + 赔率变化均<5% + 澳门推非主方向
    if conf_val >= 66 and max_change < 5:
        prediction = conf_dir
        reason.append("规律H:高置信稳胆")
        stability += 2
    
    # 规则一：置信≥66% + 澳门同向
    if conf_val >= 66 and ((conf_dir == '主胜' and omen_dir == '主') or 
                           (conf_dir == '客胜' and omen_dir == '客') or
                           (conf_dir == '平局' and omen_dir == '平')):
        prediction = conf_dir
        reason.append("规律一:高置信+澳门同向")
        stability += 1
    
    # 规则二：平局难出（平初<3或降>5%）
    if id_ < 3.0 or cd < -5:
        if prediction == "平局":
            prediction = conf_dir if conf_dir != "平局" else "主胜"
        reason.append("规律二:平局难出")
    
    # 规则三：置信度≤40%
    if conf_val <= 40:
        reason.append("规律三:低置信")
        # 顺赔率变动，但排除造热
        if heat_dir == '主' and ch < -5:
            prediction = "客胜"
        elif heat_dir == '客' and ca < -5:
            prediction = "主胜"
        elif heat_dir == '平' and cd < -5:
            prediction = "主胜" if conf_h > conf_a else "客胜"
    
    # 筹码完全聚焦反向（E维度）
    if triple_focus:
        if prediction == "主胜":
            prediction = "客胜"
        elif prediction == "客胜":
            prediction = "主胜"
        reason.append("筹码三重聚焦反向")
        upset_risk += 3
    
    # 赔率绝对值赔付压力（C维度）
    if '客' in high_odds_dirs and prediction == "客胜":
        if ra > 3.5:
            prediction = "平局" if rd < 3.5 else "主胜"
            reason.append("客赔过高赔付压力")
    if '平' in high_odds_dirs and prediction == "平局":
        if rd > 3.5:
            prediction = min_dir + "胜"
            reason.append("平赔过高赔付压力")
    
    # 全锁定 + 近况差≥8 → 主队超强信号
    if chip_state == "全锁定" and form_diff is not None and form_diff >= 8:
        prediction = "主胜"
        reason.append("全锁定+近况差+8")
        stability += 2
    
    # 单向锁定平方向 → 平局真方向
    if chip_state == "单向锁定" and abs(cd) < 0.5 and omen_dir == '平':
        prediction = "平局"
        reason.append("平赔锁定+澳门推平")
        stability += 1
    
    return {
        'chip_state': chip_state,
        'heat_dir': heat_dir,
        'heat_pct': heat_pct,
        'omen_dir': omen_dir,
        'min_odds_dir': min_dir,
        'high_odds_dirs': high_odds_dirs,
        'form_move_space': form_move_space,
        'triple_focus': triple_focus,
        'ping_analysis': ping_analysis,
        'prediction': prediction,
        'reason': '; '.join(reason) if reason else '按置信度',
        'stability': stability,
        'upset_risk': upset_risk
    }

# ============================================================
# 主程序
# ============================================================
print("=" * 80)
print("3.27比赛完整分析 - 筹码分流体系V2（3.28优化版）")
print("=" * 80)

results = []

for m in matches:
    # 近况差计算
    h_score = calc_form_score(m['home_form'])
    a_score = calc_form_score(m['away_form'])
    form_diff = h_score - a_score if h_score is not None and a_score is not None else None
    
    # 竞彩置信度
    rh, rd, ra = m['jc_real']
    conf_h, conf_d, conf_a, conf_val, conf_dir = calc_confidence(rh, rd, ra)
    
    # 赔率变化
    ih, id_, ia = m['jc_init']
    ch = calc_change(ih, rh)
    cd = calc_change(id_, rd)
    ca = calc_change(ia, ra)
    
    # 筹码分流分析
    analysis = analyze_chips_flow(m, h_score, a_score, conf_h, conf_d, conf_a, conf_val, conf_dir, ch, cd, ca)
    
    results.append({
        'id': m['id'],
        'match': f"{m['home']} vs {m['away']}",
        'home_form': m['home_form'],
        'away_form': m['away_form'],
        'h_score': h_score,
        'a_score': a_score,
        'form_diff': form_diff,
        'conf_val': conf_val,
        'conf_dir': conf_dir,
        'conf_h': conf_h,
        'conf_d': conf_d,
        'conf_a': conf_a,
        'ch': ch,
        'cd': cd,
        'ca': ca,
        'omen': m['omen'],
        'chip_state': analysis['chip_state'],
        'prediction': analysis['prediction'],
        'reason': analysis['reason'],
        'stability': analysis['stability'],
        'upset_risk': analysis['upset_risk'],
        'ih': ih, 'id_': id_, 'ia': ia,
        'rh': rh, 'rd': rd, 'ra': ra
    })

# 输出近况差复核
print("\n" + "=" * 80)
print("① 近况差计算复核")
print("=" * 80)
print(f"{'编号':<10} {'主队':<10} {'近况':<8} {'主分':<5} {'客队':<10} {'近况':<8} {'客分':<5} {'近况差':<8}")
print("-" * 80)

for r in results:
    h_str = str(r['h_score']) if r['h_score'] is not None else '无'
    a_str = str(r['a_score']) if r['a_score'] is not None else '无'
    d_str = f"+{r['form_diff']}" if r['form_diff'] is not None and r['form_diff'] > 0 else (str(r['form_diff']) if r['form_diff'] is not None else '无')
    print(f"{r['id']:<10} {r['match'].split(' vs ')[0]:<10} {r['home_form']:<8} {h_str:<5} {r['match'].split(' vs ')[1]:<10} {r['away_form']:<8} {a_str:<5} {d_str:<8}")

# 输出置信度和变化
print("\n" + "=" * 80)
print("② 竞彩置信度 & 赔率变化")
print("=" * 80)
print(f"{'编号':<10} {'预测方向':<10} {'置信度':<8} {'主%':<6} {'平%':<6} {'客%':<6} {'主变化':<8} {'平变化':<8} {'客变化':<8}")
print("-" * 80)

for r in results:
    ch_s = f"{r['ch']:+.1f}%"
    cd_s = f"{r['cd']:+.1f}%"
    ca_s = f"{r['ca']:+.1f}%"
    print(f"{r['id']:<10} {r['conf_dir']:<10} {r['conf_val']:<8.1f} {r['conf_h']:<6.1f} {r['conf_d']:<6.1f} {r['conf_a']:<6.1f} {ch_s:<8} {cd_s:<8} {ca_s:<8}")

# 输出筹码分流分析
print("\n" + "=" * 80)
print("③ 筹码分流分析")
print("=" * 80)

for r in results:
    print(f"\n【{r['id']}】{r['match']}")
    print(f"  筹码状态: {r['chip_state']}")
    print(f"  澳门心水: {r['omen']}")
    print(f"  近况差: {r['form_diff'] if r['form_diff'] is not None else '无'}")
    print(f"  赔率变化: 主{r['ch']:+.1f}% 平{r['cd']:+.1f}% 客{r['ca']:+.1f}%")
    print(f"  竞彩方向: {r['conf_dir']} {r['conf_val']:.1f}%")
    print(f"  → 最终预测: {r['prediction']}")
    print(f"  → 依据: {r['reason']}")
    if r['stability'] >= 2:
        print(f"  [稳] 稳定性: {r['stability']}星")
    if r['upset_risk'] >= 2:
        print(f"  [险] 爆冷风险: {r['upset_risk']}级")

# 输出完整数据表格
print("\n" + "=" * 80)
print("④ 完整数据表格（标准格式）")
print("=" * 80)
print(f"{'编号':<10} {'对阵':<25} {'置信度':<12} {'澳门心水':<10} {'近况差':<8} {'初盘(H/D/A)':<18} {'即时(H/D/A)':<18} {'变化(H/D/A)':<22} {'最终预测':<10}")
print("-" * 150)

for r in results:
    match_short = r['match'][:22]
    conf_str = f"{r['conf_dir']}{r['conf_val']:.1f}%"
    init_odds = f"{r['ih']:.2f}/{r['id_']:.2f}/{r['ia']:.2f}"
    real_odds = f"{r['rh']:.2f}/{r['rd']:.2f}/{r['ra']:.2f}"
    change_str = f"{r['ch']:+.1f}%/{r['cd']:+.1f}%/{r['ca']:+.1f}%"
    form_diff_str = f"+{r['form_diff']}" if r['form_diff'] is not None and r['form_diff'] > 0 else (str(r['form_diff']) if r['form_diff'] is not None else '无')
    
    print(f"{r['id']:<10} {match_short:<25} {conf_str:<12} {r['omen']:<10} {form_diff_str:<8} {init_odds:<18} {real_odds:<18} {change_str:<22} {r['prediction']:<10}")

# 最稳比赛
print("\n" + "=" * 80)
print("⑤ 最稳比赛列表（稳定性★★+）")
print("=" * 80)
stable_matches = [r for r in results if r['stability'] >= 2]
stable_matches.sort(key=lambda x: x['stability'], reverse=True)

print(f"{'稳定性':<10} {'编号':<10} {'对阵':<30} {'预测':<10} {'核心依据'}")
print("-" * 100)
for r in stable_matches:
    stars = '[稳]' + str(r['stability']) + '星'
    print(f"{stars:<10} {r['id']:<10} {r['match']:<30} {r['prediction']:<10} {r['reason']}")

# 最可能爆冷
print("\n" + "=" * 80)
print("⑥ 最可能爆冷比赛列表（风险2级+）")
print("=" * 80)
upset_matches = [r for r in results if r['upset_risk'] >= 2]
upset_matches.sort(key=lambda x: x['upset_risk'], reverse=True)

print(f"{'风险等级':<12} {'编号':<10} {'对阵':<30} {'预测':<10} {'爆冷类型':<15} {'主要依据'}")
print("-" * 120)
for r in upset_matches:
    risk = '[险]' + str(r['upset_risk']) + '级'
    upset_type = "规律N反向" if "规律N" in r['reason'] else ("规律Q过热" if "规律Q" in r['reason'] else "三重聚焦")
    print(f"{risk:<12} {r['id']:<10} {r['match']:<30} {r['prediction']:<10} {upset_type:<15} {r['reason']}")

print("\n" + "=" * 80)
print("分析完成")
print("=" * 80)
