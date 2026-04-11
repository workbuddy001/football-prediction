# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ============================================================
# 16场比赛完整数据
# ============================================================
matches = [
    {
        'id': '周五001', 'home': '新西兰', 'away': '芬兰',
        'jc_init': (2.05, 3.00, 3.25), 'jc_real': (2.60, 2.90, 2.50),
        'omen': '客队胜',
        'home_form': 'LLDLLL', 'away_form': 'WLLWLL'
    },
    {
        'id': '周五002', 'home': '中国', 'away': '库拉索',
        'jc_init': (3.50, 3.15, 1.90), 'jc_real': (5.42, 3.65, 1.49),
        'omen': '客队胜',
        'home_form': 'WLLWLL', 'away_form': 'DWDWWD'
    },
    {
        'id': '周五003', 'home': '澳大利亚', 'away': '喀麦隆',
        'jc_init': (1.65, 3.27, 4.60), 'jc_real': (1.78, 3.25, 3.85),
        'omen': '无',
        'home_form': '无', 'away_form': '无'
    },
    {
        'id': '周五004', 'home': '神户胜利', 'away': '广岛三箭',
        'jc_init': (2.47, 3.15, 2.47), 'jc_real': (2.51, 3.12, 2.44),
        'omen': '主队胜',
        'home_form': 'DDWWWW', 'away_form': 'LLWWLL'
    },
    {
        'id': '周五005', 'home': '奥地利', 'away': '加纳',
        'jc_init': (1.45, 3.90, 5.45), 'jc_real': (1.43, 3.95, 5.65),
        'omen': '主队胜',
        'home_form': 'DWLWWW', 'away_form': 'LLLWWW'
    },
    {
        'id': '周五006', 'home': '南非', 'away': '巴拿马',
        'jc_init': (1.90, 3.00, 3.70), 'jc_real': (1.97, 2.90, 3.61),
        'omen': '客队胜',
        'home_form': 'LWLWWW', 'away_form': 'LDWWDW'
    },
    {
        'id': '周五007', 'home': '希腊', 'away': '巴拉圭',
        'jc_init': (1.90, 3.15, 3.50), 'jc_real': (1.89, 3.10, 3.60),
        'omen': '和局',
        'home_form': 'DWLLLW', 'away_form': 'WLLDWD'
    },
    {
        'id': '周五008', 'home': '荷兰', 'away': '挪威',
        'jc_init': (1.51, 3.90, 4.75), 'jc_real': (1.54, 3.85, 4.55),
        'omen': '和局',
        'home_form': 'WDWWWD', 'away_form': 'WWDWWW'
    },
    {
        'id': '周五009', 'home': '英格兰', 'away': '乌拉圭',
        'jc_init': (1.43, 3.75, 6.10), 'jc_real': (1.39, 3.95, 6.40),
        'omen': '主队胜',
        'home_form': 'WWWWWW', 'away_form': 'LDWWDW'
    },
    {
        'id': '周五010', 'home': '瑞士', 'away': '德国',
        'jc_init': (2.82, 3.35, 2.10), 'jc_real': (3.45, 3.64, 1.77),
        'omen': '和局',
        'home_form': 'DWDWWW', 'away_form': 'WWWWWL'
    },
    {
        'id': '周五011', 'home': '西班牙', 'away': '塞尔维亚',
        'jc_init': (1.30, 5.00, 9.50), 'jc_real': (1.20, 6.00, 12.00),
        'omen': '主队胜',
        'home_form': 'DWWWWW', 'away_form': 'WLWLLW'
    },
    {
        'id': '周五012', 'home': '摩洛哥', 'away': '厄瓜多尔',
        'jc_init': (2.65, 2.75, 2.58), 'jc_real': (2.45, 2.70, 2.85),
        'omen': '和局',
        'home_form': 'DDWWWD', 'away_form': 'WDDDWD'
    },
    {
        'id': '周六001', 'home': '町田泽维', 'away': '川崎前锋',
        'jc_init': (1.79, 3.56, 3.45), 'jc_real': (1.79, 3.56, 3.45),
        'omen': '主队胜',
        'home_form': 'WLWWDW', 'away_form': 'LWLDLD'
    },
    {
        'id': '周六002', 'home': '浦项制铁', 'away': '江原FC',
        'jc_init': (3.06, 2.75, 2.28), 'jc_real': (2.96, 2.75, 2.34),
        'omen': '和局',
        'home_form': 'DLDDLD', 'away_form': 'DDDLDL'
    },
    {
        'id': '周六012', 'home': '威廉二世', 'away': '格拉夫',
        'jc_init': (2.03, 3.75, 2.70), 'jc_real': (2.03, 3.75, 2.70),
        'omen': '主队胜',
        'home_form': 'WWDWLW', 'away_form': 'LWLDWW'
    },
    {
        'id': '周六014', 'home': '埃因FC', 'away': '埃门',
        'jc_init': (1.93, 3.60, 3.00), 'jc_real': (1.93, 3.60, 3.00),
        'omen': '主队胜',
        'home_form': 'LWWLLW', 'away_form': 'LDLWWL'
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
    score = score_map.get(chars[0], 0) * 2
    for c in chars[1:5]:
        score += score_map.get(c, 0)
    return score

print('='*70)
print('【近况差计算复核】最近1场×2，其余4场×1，W=3 D=1 L=0，满分18')
print('='*70)
print(f"{'编号':<10} {'主队近况':<10} {'主分':>4} {'客队近况':<10} {'客分':>4} {'近况差':>6}")
print('-'*70)

form_results = {}
for m in matches:
    h_score = calc_form_score(m['home_form'])
    a_score = calc_form_score(m['away_form'])
    if h_score is None or a_score is None:
        diff = None
        diff_str = '无数据'
    else:
        diff = h_score - a_score
        diff_str = ('+' if diff > 0 else '') + str(diff)
    form_results[m['id']] = (h_score, a_score, diff)
    h_str = str(h_score) if h_score is not None else '无'
    a_str = str(a_score) if a_score is not None else '无'
    print(f"{m['id']:<10} {m['home_form']:<10} {h_str:>4} {m['away_form']:<10} {a_str:>4} {diff_str:>6}")

# ============================================================
# 竞彩置信度计算（使用即时赔率）
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
    if r_h >= r_d and r_h >= r_a:
        direction = '主胜'
    elif r_a >= r_h and r_a >= r_d:
        direction = '客胜'
    else:
        direction = '平局'
    return round(r_h, 1), round(r_d, 1), round(r_a, 1), round(max_r, 1), direction

# ============================================================
# 赔率变化计算
# ============================================================
def calc_change(init_v, real_v):
    return round((real_v - init_v) / init_v * 100, 1)

def fmt_change(v):
    return ('+' if v > 0 else '') + str(v) + '%'

print()
print('='*70)
print('【竞彩置信度 & 赔率变化】')
print('='*70)

confidence_results = {}
change_results = {}
for m in matches:
    ih, id_, ia = m['jc_init']
    rh, rd, ra = m['jc_real']
    r_h, r_d, r_a, conf, direction = calc_confidence(rh, rd, ra)
    ch = calc_change(ih, rh)
    cd = calc_change(id_, rd)
    ca = calc_change(ia, ra)
    confidence_results[m['id']] = (r_h, r_d, r_a, conf, direction)
    change_results[m['id']] = (ch, cd, ca)
    print(f"{m['id']}: {direction} {conf}% | 主{r_h}% 平{r_d}% 客{r_a}% | 变化: 主{fmt_change(ch)} 平{fmt_change(cd)} 客{fmt_change(ca)}")

# ============================================================
# 筹码分流分析
# ============================================================
def analyze_chips_flow(ch, cd, ca):
    """
    判断筹码分流状态
    全锁定: 三向变化均<0.5%
    单向锁定: 某一向<0.5%，另两向>2%
    均衡分流: 三向0.5-2%
    极端造热: 某方向降>10%
    极端推离: 某方向升>10%
    单向造热: 某方向降5-10%
    """
    abs_ch, abs_cd, abs_ca = abs(ch), abs(cd), abs(ca)
    locked = {'主': abs_ch < 0.5, '平': abs_cd < 0.5, '客': abs_ca < 0.5}
    lock_count = sum(locked.values())
    
    # 极端造热检测
    extreme_hot = []
    if ch < -10: extreme_hot.append('主')
    if cd < -10: extreme_hot.append('平')
    if ca < -10: extreme_hot.append('客')
    
    # 极端推离检测
    extreme_push = []
    if ch > 10: extreme_push.append('主')
    if cd > 10: extreme_push.append('平')
    if ca > 10: extreme_push.append('客')
    
    # 单向造热 5-10%
    moderate_hot = []
    if -10 <= ch < -5: moderate_hot.append('主')
    if -10 <= cd < -5: moderate_hot.append('平')
    if -10 <= ca < -5: moderate_hot.append('客')

    if lock_count == 3:
        return '全锁定', '庄家静观，无引导信号，纯按近况差/置信度', None
    
    if extreme_hot:
        hot_dirs = '、'.join(extreme_hot)
        return f'极端造热({hot_dirs})', f'{hot_dirs}方向被极端压低>10%，反向信号强', extreme_hot
    
    if extreme_push:
        push_dirs = '、'.join(extreme_push)
        return f'极端推离({push_dirs})', f'{push_dirs}方向被大幅推离，该方向冷门', None
    
    if lock_count == 1:
        locked_dir = [k for k, v in locked.items() if v][0]
        moving_dirs = [k for k, v in locked.items() if not v]
        return f'单向锁定({locked_dir})', f'{locked_dir}方向被锁定=庄家真实押注（强信号）', [locked_dir]
    
    if moderate_hot:
        hot_dirs = '、'.join(moderate_hot)
        return f'单向造热({hot_dirs})', f'{hot_dirs}方向中等造热5-10%，结合规律判断', moderate_hot
    
    max_abs = max(abs_ch, abs_cd, abs_ca)
    if max_abs < 0.5:
        return '全锁定', '庄家静观，无引导信号', None
    elif max_abs <= 2:
        return '均衡分流', '三向均小幅变化，无强方向信号，按置信度方向', None
    else:
        return '普通变动', '赔率有明显变动，结合其他规律判断', None

print()
print('='*70)
print('【筹码分流分析】')
print('='*70)
chips_results = {}
for m in matches:
    ch, cd, ca = change_results[m['id']]
    status, desc, signal = analyze_chips_flow(ch, cd, ca)
    chips_results[m['id']] = (status, desc, signal)
    print(f"{m['id']}: [{status}] {desc}")

# ============================================================
# 规律二次审核
# ============================================================
print()
print('='*70)
print('【规律二次审核 + 最终预测】')
print('='*70)

final_predictions = {}
for m in matches:
    mid = m['id']
    r_h, r_d, r_a, conf, base_dir = confidence_results[mid]
    ch, cd, ca = change_results[mid]
    h_score, a_score, form_diff = form_results[mid]
    omen = m['omen']
    chips_status, chips_desc, chips_signal = chips_results[mid]
    ih, id_, ia = m['jc_init']
    rh, rd, ra = m['jc_real']
    
    prediction = base_dir
    rules_triggered = []
    stability = 0  # 稳定性得分
    upset_risk = 0  # 爆冷风险
    notes = []
    
    # --- 规律五：主胜升幅>5% → 和局 ---
    if ch > 5:
        rules_triggered.append('规律五(主升>5%→和局)')
        # 进一步检测规律N
        if ca < -10:
            prediction = '主胜'
            rules_triggered.append('规律N(极端造热客队+规律五→反向主胜)')
            upset_risk += 2
            notes.append('规律N极端反向：庄家造热客队>10%，主胜概率大')
        elif ca < -5:
            prediction = '主胜'
            rules_triggered.append('规律N(中等造热客队+规律五→主胜)')
            upset_risk += 1
            notes.append('规律N中等反向：客队造热5-10%，倾向主胜')
        else:
            prediction = '和局'
            notes.append('规律五触发：主升>5%，预测和局')
    
    # --- 规律一：置信度≥66% + 分胜负赛 ---
    if conf >= 66 and omen != '和局' and '规律五' not in str(rules_triggered):
        rules_triggered.append(f'规律一(置信度{conf}%≥66%)')
        prediction = base_dir
        stability += 2
        notes.append(f'高置信度{conf}%，可信打出')
    
    # --- 规律H：置信度≥66% + 赔率变化均<5% + 澳门推非主方向 ---
    if conf >= 66 and abs(ch) < 5 and abs(cd) < 5 and abs(ca) < 5:
        rules_triggered.append('规律H(高置信+赔率稳定)')
        stability += 1
        notes.append('规律H：赔率变动小，按置信度方向稳胆')
    
    # --- 规律二：平局难出 ---
    draw_hard = False
    if id_ < 3.0:
        rules_triggered.append('规律二(平初赔<3.0,平难出)')
        draw_hard = True
    if cd < -5:
        rules_triggered.append('规律二(平赔降>5%,平难出)')
        draw_hard = True
    if draw_hard and prediction == '平局':
        prediction = base_dir if base_dir != '平局' else ('主胜' if r_h >= r_a else '客胜')
        notes.append('规律二：平局难出，修正预测')
    
    # --- 规律I：极端造热双向 + 近况差≤-10 + 平赔不变 ---
    if form_diff is not None and form_diff <= -10:
        if abs(ch) > 8 and abs(ca) > 8 and abs(cd) < 2:
            rules_triggered.append('规律I(极端造热+近况差≤-10+平赔不变→平局)')
            prediction = '平局'
            upset_risk += 2
            notes.append('规律I：极端双向造热+平赔不变，预测平局')
    
    # --- 规律L：极端造热客队 + 近况差≤-10 + 平赔不降反升 ---
    if form_diff is not None and form_diff <= -10:
        if ca < -8 and cd > 0:
            rules_triggered.append('规律L(极端造热客队+平赔升→主胜)')
            prediction = '主胜'
            notes.append('规律L：客队极端造热但平赔反升，主胜')
    
    # --- 规律O：近况差≥+8 + 赔率微变<2% ---
    if form_diff is not None and form_diff >= 8:
        if abs(ch) < 2 and abs(cd) < 2 and abs(ca) < 2:
            rules_triggered.append('规律O(近况差≥+8+赔率微变→主队打出)')
            prediction = '主胜'
            stability += 1
            notes.append('规律O：近况差优势大+赔率微变，主队打出')
    
    # --- 规律Q：近况差极大≥+10 + 置信度<65% + 赔率全变>2% ---
    if form_diff is not None and form_diff >= 10:
        if conf < 65 and abs(ch) > 2 and abs(cd) > 2 and abs(ca) > 2:
            rules_triggered.append('规律Q(近况差+10+置信<65%+赔率全变→防过热平局)')
            prediction = '平局'
            upset_risk += 2
            notes.append('规律Q：近况差极大但置信不足+赔率全变，防过热平局')
    
    # --- 规律P：平赔3.0-3.2 + 澳门推平 + 变化<2% → 诱平反向 ---
    if omen == '和局' and 3.0 <= rd <= 3.2:
        if abs(ch) < 2 and abs(cd) < 2 and abs(ca) < 2:
            rules_triggered.append('规律P(诱平反向)')
            # 诱平，按主/客方向
            if r_h >= r_a:
                prediction = '主胜'
            else:
                prediction = '客胜'
            upset_risk += 1
            notes.append('规律P：平赔3.0-3.2+澳门推平+变化小，诱平反向')
    
    # --- 规律J：澳门推平 + 平赔<3.0 + 主升 + 客降 ---
    if omen == '和局' and rd < 3.0:
        if ch > 0 and ca < 0:
            rules_triggered.append('规律J(澳门推平+平赔<3.0+主升客降→客胜)')
            prediction = '客胜'
            notes.append('规律J：澳门推平但平赔<3.0且主升客降，客胜')
    
    # --- 全锁定检测 ---
    if chips_status == '全锁定':
        if form_diff is not None and form_diff >= 8:
            stability += 2
            notes.append('全锁定+近况差≥+8：主队超强信号')
    
    # --- 单向锁定信号 ---
    if '单向锁定' in chips_status and chips_signal:
        locked_dir = chips_signal[0]
        if locked_dir == '主' and prediction == '主胜':
            stability += 2
            notes.append('单向锁定主方向，双重确认主胜')
        elif locked_dir == '客' and prediction == '客胜':
            stability += 2
            notes.append('单向锁定客方向，双重确认客胜')
        elif locked_dir == '平' and prediction == '平局':
            stability += 2
            notes.append('单向锁定平方向，双重确认平局')
        else:
            upset_risk += 1
            notes.append(f'单向锁定{locked_dir}方向但预测不同，爆冷警惕')
    
    # --- 置信度55-65%区间风险 ---
    if 55 <= conf < 66:
        upset_risk += 1
        notes.append(f'置信度{conf}%处于55-65%危险区间，约50%概率被平打断')
    
    # 综合稳定性vs爆冷
    # 澳门同向加稳定性
    omen_match = False
    if omen == '主队胜' and prediction == '主胜':
        omen_match = True
        stability += 1
    elif omen == '客队胜' and prediction == '客胜':
        omen_match = True
        stability += 1
    elif omen == '和局' and prediction == '平局':
        omen_match = True
        stability += 1
    
    final_predictions[mid] = {
        'base_dir': base_dir,
        'prediction': prediction,
        'conf': conf,
        'r_h': r_h, 'r_d': r_d, 'r_a': r_a,
        'ch': ch, 'cd': cd, 'ca': ca,
        'ih': ih, 'id_': id_, 'ia': ia,
        'rh': rh, 'rd': rd, 'ra': ra,
        'form_diff': form_diff,
        'omen': omen,
        'chips': chips_status,
        'rules': rules_triggered,
        'stability': stability,
        'upset_risk': upset_risk,
        'notes': notes,
        'omen_match': omen_match,
    }
    
    print(f"\n{mid} {m['home']} vs {m['away']}")
    print(f"  置信度: {base_dir} {conf}% | 近况差: {form_diff}")
    print(f"  赔率变化: 主{fmt_change(ch)} 平{fmt_change(cd)} 客{fmt_change(ca)}")
    print(f"  筹码状态: {chips_status}")
    print(f"  澳门推荐: {omen}")
    print(f"  触发规律: {', '.join(rules_triggered) if rules_triggered else '无'}")
    print(f"  最终预测: {prediction} | 稳定性{stability} 爆冷风险{upset_risk}")
    for note in notes:
        print(f"    → {note}")

# ============================================================
# 完整数据表格（标准格式）
# ============================================================
print()
print('='*70)
print('【完整数据列表 - 标准格式】')
print('='*70)
print(f"{'编号':<8} {'对阵':<18} {'置信':<8} {'澳门':<8} {'近况差':<6} {'初盘H/D/A':<18} {'即时H/D/A':<18} {'变化H/D/A':<20} {'最终预测':<8}")
print('-'*120)

for m in matches:
    mid = m['id']
    fp = final_predictions[mid]
    home_away = f"{m['home']} vs {m['away']}"
    ih, id_v, ia = m['jc_init']
    rh, rd, ra = m['jc_real']
    init_str = f"{ih}/{id_v}/{ia}"
    real_str = f"{rh}/{rd}/{ra}"
    ch, cd, ca = fp['ch'], fp['cd'], fp['ca']
    change_str = f"主{fmt_change(ch)}/平{fmt_change(cd)}/客{fmt_change(ca)}"
    conf_str = f"{fp['base_dir']}{fp['conf']}%"
    fd = str(fp['form_diff']) if fp['form_diff'] is not None else '无'
    if fp['form_diff'] is not None and fp['form_diff'] > 0:
        fd = '+' + fd
    print(f"{mid:<8} {home_away:<18} {conf_str:<8} {fp['omen']:<8} {fd:<6} {init_str:<18} {real_str:<18} {change_str:<20} {fp['prediction']:<8}")

# ============================================================
# 稳胆列表（稳定性≥2）
# ============================================================
print()
print('='*70)
print('【最稳比赛列表（稳定性≥2）】')
print('='*70)
stable_list = [(mid, fp) for mid, fp in final_predictions.items() if fp['stability'] >= 2]
stable_list.sort(key=lambda x: -x[1]['stability'])
for mid, fp in stable_list:
    m = next(x for x in matches if x['id'] == mid)
    print(f"  {mid} {m['home']} vs {m['away']}: 预测【{fp['prediction']}】稳定性={fp['stability']} | {', '.join(fp['rules'][:3])}")

# ============================================================
# 爆冷风险列表（爆冷风险≥2）
# ============================================================
print()
print('='*70)
print('【最可能爆冷比赛列表（爆冷风险≥2）】')
print('='*70)
upset_list = [(mid, fp) for mid, fp in final_predictions.items() if fp['upset_risk'] >= 2]
upset_list.sort(key=lambda x: -x[1]['upset_risk'])
for mid, fp in upset_list:
    m = next(x for x in matches if x['id'] == mid)
    print(f"  {mid} {m['home']} vs {m['away']}: 预测【{fp['prediction']}】爆冷风险={fp['upset_risk']} | {', '.join(fp['rules'][:3])}")
    for note in fp['notes']:
        print(f"      → {note}")

print()
print('='*70)
print('分析完成！')
print('='*70)
