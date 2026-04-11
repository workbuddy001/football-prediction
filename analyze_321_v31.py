#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3.21 周六+周日比赛 V3.2规律体系回测分析
V3.2变更：中等置信度门槛55%→60%，新增规律T（全变失控弱化）
"""

import re

def calc_prob_from_odds(h, d, a):
    """赔率→概率"""
    total = 1/h + 1/d + 1/a
    return (1/h/total*100, 1/d/total*100, 1/a/total*100)

def calc_change(initial, realtime):
    """赔率变化%"""
    def pct(i, r):
        if i == 0: return 0
        return (r - i) / i * 100
    return (pct(initial[0], realtime[0]), pct(initial[1], realtime[1]), pct(initial[2], realtime[2]))

def parse_macao_direction(macao_tip):
    """解析澳门方向"""
    if '和' in macao_tip or '平' in macao_tip:
        return "平局"
    return macao_tip  # 保持原样，后面手动标注

def analyze_with_v31(match_id, teams, initial_str, realtime_str, macao_tip, form_diff, home_form, away_form):
    """
    用V3.1规律体系分析单场
    返回: (预测方向, 置信度, 触发规律, 分析说明)
    """
    # 解析赔率
    h_i, d_i, a_i = [float(x) for x in initial_str.split('/')]
    h_r, d_r, a_r = [float(x) for x in realtime_str.split('/')]
    
    initial_avg = (h_i, d_i, a_i)
    realtime_avg = (h_r, d_r, a_r)
    
    # 计算赔率变化
    hc, dc, ac = calc_change(initial_avg, realtime_avg)
    
    # 计算概率
    hp, dp, ap = calc_prob_from_odds(h_r, d_r, a_r)
    max_prob = max(hp, dp, ap)
    if hp == max_prob: pred = "主胜"
    elif dp == max_prob: pred = "平局"
    else: pred = "客胜"
    conf = max_prob
    
    # 澳门方向
    macao = parse_macao_direction(macao_tip)
    
    predictions = []
    reasons = []
    triggered = []
    
    # ===== V3.1规律体系 =====
    
    # 规律R：真假造热辨别（最高优先级）
    if macao == "客胜" and ac < -10:
        if hc > 0 and dc > 0:
            predictions.append(("主胜", 85, "规律R：真造热诱盘"))
            reasons.append("澳门推客+客造热>10%，主/平均升无分流，反向主胜")
            triggered.append("规律R-真造热")
        elif dc < 0 or hc < 0:
            predictions.append(("客胜", 75, "规律R：假造热实盘"))
            reasons.append("澳门推客+客降，但平/主同步降分流筹码，客胜实盘")
            triggered.append("规律R-假造热")
    
    if macao == "主胜" and hc < -10:
        if ac > 0 and dc > 0:
            predictions.append(("客胜", 85, "规律R：真造热诱盘"))
            reasons.append("澳门推主+主造热>10%，客/平均升无分流，反向客胜")
            triggered.append("规律R-真造热")
        elif dc < 0 or ac < 0:
            predictions.append(("主胜", 75, "规律R：假造热实盘"))
            reasons.append("澳门推主+主降，但平/客同步降分流筹码，主胜实盘")
            triggered.append("规律R-假造热")
    
    # 规律T（V3.2新增）：三向赔率全变>5% → 庄家失控
    rule_t_triggered = abs(hc) > 5 and abs(dc) > 5 and abs(ac) > 5

    # 规律一：置信度≥66%+澳门同向 → 可信（V3.2修正：规律T排除）
    if conf >= 66 and not rule_t_triggered:
        if (pred == "主胜" and macao == "主胜") or (pred == "客胜" and macao == "客胜"):
            predictions.append((pred, 82, "规律一：高置信度+澳门同向"))
            reasons.append(f"置信度{conf:.1f}%≥66%，澳门推荐一致，可信打出")
            triggered.append("规律一")
    elif conf >= 66 and rule_t_triggered:
        # 规律T弱化：规律一/规律H降级为观望
        if (pred == "主胜" and macao == "主胜") or (pred == "客胜" and macao == "客胜"):
            triggered.append("规律T-弱化规律一")
            reasons.append(f"置信度{conf:.1f}%≥66%，澳门同向，但三向全变>5%庄家失控，规律一降级")
    
    # 规律Q：近况差≥10+置信<65%+全变>2% → 防过热平局
    if form_diff >= 10 and conf < 65 and min(abs(hc), abs(dc), abs(ac)) > 2:
        predictions.append(("平局", 70, "规律Q：过热防平"))
        reasons.append("近况差极大但置信度不匹配，赔率变化有造热嫌疑，防平局")
        triggered.append("规律Q")
    
    # 规律S（V3.1修正版）
    if abs(form_diff) <= 2 and max(abs(hc), abs(dc), abs(ac)) > 5:
        hot_direction = None
        if ac < -5: hot_direction = "客胜"
        elif hc < -5: hot_direction = "主胜"
        elif hc > 5: hot_direction = "客胜"
        elif ac > 5: hot_direction = "主胜"
        
        if hot_direction and macao != hot_direction and macao != "平局":
            if hot_direction == "客胜" and h_r < 3.4:
                predictions.append(("主胜", 80, "规律S：近况持平+客造热反向"))
                reasons.append(f"近况差{form_diff}客胜造热({ac:.1f}%)但澳门不推客，反向主胜")
                triggered.append("规律S")
            elif hot_direction == "主胜" and a_r < 3.4:
                predictions.append(("客胜", 80, "规律S：近况持平+主造热反向"))
                reasons.append(f"近况差{form_diff}主胜造热({hc:.1f}%)但澳门不推主，反向客胜")
                triggered.append("规律S")
    
    # 规律五V3.1-双热
    if hc > 5 and ac < -5 and abs(form_diff) > 3 and macao == "平局":
        predictions.append(("客胜", 75, "规律五V3.1-双热"))
        reasons.append("主客均被造热+澳门推平局，客胜降幅更大，倾向客胜")
        triggered.append("规律五V3.1-双热")
    
    # 规律N（V3.1修正版）
    if hc > 5 and macao == "客胜" and ac < -10 and a_r >= 2.5:
        predictions.append(("主胜", 80, "规律N：规律五+极端造热客队"))
        reasons.append("主胜升幅>5%+澳门推客+客队极端造热，反向主胜")
        triggered.append("规律N")
    
    # 规律J（V3.1修正版）
    if macao == "平局" and d_r < 3.0 and hc > 0 and ac < 0 and dc >= -2:
        predictions.append(("客胜", 72, "规律J：推平诱客"))
        reasons.append("澳门推平但平赔<3.0且不降，主升客降，客胜")
        triggered.append("规律J")
    
    # 规律O
    if form_diff >= 8 and max(abs(hc), abs(dc), abs(ac)) < 2:
        predictions.append(("主胜", 80, "规律O：近况差大+赔率微变"))
        reasons.append(f"近况差+{form_diff}，赔率微变<2%，主队打出信号")
        triggered.append("规律O")
    
    # 规律P：平赔3.0-3.2+澳门推平局+变化<2% → 诱平
    if 3.0 <= d_r <= 3.2 and macao == "平局" and abs(dc) < 2:
        if ac > 0:
            predictions.append(("客胜", 75, "规律P：诱平陷阱"))
            reasons.append("平赔3.0-3.2诱平区间，筹码分散主/平，客队漏网")
            triggered.append("规律P")
    
    # 规律U（V3.1修正版）
    if form_diff >= 8 and hc < -5 and ac > 5 and macao != "主胜":
        predictions.append(("平局", 82, "规律U：近况碾压+主造热+澳门不推主"))
        reasons.append(f"近况差+{form_diff}主队碾压，主胜造热但澳门不推主，诱导信号")
        triggered.append("规律U")
    
    # 规律V（V3.1修正版）
    if form_diff <= -8 and ac < -5 and hc > 5 and macao != "客胜":
        predictions.append(("平局", 82, "规律V：近况碾压客+客造热+澳门不推客"))
        reasons.append(f"近况差{form_diff}客队碾压，客胜造热但澳门不推客，诱导信号")
        triggered.append("规律V")
    
    # 规律五V3.1：主升>5%+澳门推平+|差|>3
    if hc > 5 and ac > -5 and abs(form_diff) > 3 and macao == "平局":
        predictions.append(("平局", 85, "规律五V3.1：主升>5%+澳门推平"))
        reasons.append("主胜赔率大幅上升+澳门推平局+近况有差距，和局概率高")
        triggered.append("规律五V3.1")
    
    # 规律H：高置信度+赔率稳定+澳门≠置信度方向（V3.2修正：规律T排除）
    if conf >= 66 and max(abs(hc), abs(dc), abs(ac)) < 5 and not rule_t_triggered:
        if macao != pred:
            predictions.append((pred, 78, "规律H：高置信度热度分散"))
            reasons.append("置信度≥66%，赔率变化<5%，热度分散≠结果不打出")
            triggered.append("规律H")
    
    # 规律G：高置信度+变化幅度判断（V3.2修正：规律T排除）
    if conf >= 66 and not rule_t_triggered:
        if abs(hc) < 2 and form_diff >= 5:
            predictions.append(("主胜", 75, "规律G：高置信度+小变化+近况优"))
            reasons.append("高置信度+赔率变化小+近况差大，可能大胜")
            triggered.append("规律G")
        elif hc < -4:
            predictions.append(("平局", 60, "规律G：主胜造热防冷"))
            reasons.append("主胜大幅造热(>4%)，需防平局")
            triggered.append("规律G-防冷")
    elif conf >= 66 and rule_t_triggered:
        # 规律T弱化：规律G也降级
        if abs(hc) < 2 and form_diff >= 5:
            triggered.append("规律T-弱化规律G")
        elif hc < -4:
            triggered.append("规律T-弱化规律G")
    
    # 规律二：平局难出
    if d_r < 3.0 or dc < -5:
        if pred == "平局":
            if hc < ac:
                predictions.append(("主胜", 65, "规律二：平局难出转主胜"))
                reasons.append("平赔<3.0或降幅>5%，平局难出")
                triggered.append("规律二")
            else:
                predictions.append(("客胜", 65, "规律二：平局难出转客胜"))
                reasons.append("平赔<3.0或降幅>5%，平局难出")
                triggered.append("规律二")
    
    # 规律K：客队强造热+近况持平+平降>3%
    if ac < -8 and abs(form_diff) <= 2 and dc < -3:
        predictions.append(("主胜/平局", 68, "规律K：客队过热主不败"))
        reasons.append("客队强造热但近况持平，平降分流，主队不败")
        triggered.append("规律K")
    
    # 规律I：极端造热+近况差≤-10+平赔不变
    if hc < -10 and ac > 10 and form_diff <= -10 and abs(dc) < 1:
        predictions.append(("平局", 70, "规律I：极端造热平局"))
        reasons.append("极端造热客队+近况客优+平赔不变，平局")
        triggered.append("规律I")
    
    # 规律L：极端造热客队+近况差≤-10+平赔反升
    if ac < -10 and form_diff <= -10 and dc > 0:
        predictions.append(("主胜", 75, "规律L：极端造热反向主胜"))
        reasons.append("极端造热客队+近况客优+平赔反升，主胜")
        triggered.append("规律L")
    
    # 默认预测（V3.2修正：中等置信度门槛从55%提高到60%）
    if not predictions:
        if conf >= 66:
            predictions.append((pred, conf, "高置信度默认"))
            reasons.append(f"置信度{conf:.1f}%≥66%，按概率最高方向")
        elif conf >= 60:
            predictions.append((pred, conf, "中等置信度V3.2"))
            reasons.append(f"置信度{conf:.1f}%在60-65%区间，谨慎参与")
        else:
            predictions.append(("观望", conf, "低置信度V3.2：建议观望"))
            reasons.append(f"置信度{conf:.1f}%<60%，数据不足，建议观望不投注")
    
    # 多规律投票
    if len(predictions) > 1:
        direction_votes = {}
        for p, c, r in predictions:
            if p not in direction_votes:
                direction_votes[p] = {'count': 0, 'total_conf': 0, 'rules': []}
            direction_votes[p]['count'] += 1
            direction_votes[p]['total_conf'] += c
            direction_votes[p]['rules'].append(r)
        
        best_direction = None
        best_score = 0
        for direction, data in direction_votes.items():
            avg_conf = data['total_conf'] / data['count']
            score = data['count'] * 60 + avg_conf * 0.4
            if score > best_score:
                best_score = score
                best_direction = direction
        
        if best_direction:
            best_data = direction_votes[best_direction]
            best_conf = best_data['total_conf'] / best_data['count']
            best_rule = f"投票胜出({best_data['count']}条)"
            best_pred = (best_direction, best_conf, best_rule)
        else:
            best_pred = max(predictions, key=lambda x: x[1])
    else:
        best_pred = max(predictions, key=lambda x: x[1])
    
    return {
        'prediction': best_pred[0],
        'confidence': best_pred[1],
        'rule': best_pred[2],
        'reason': ' | '.join(reasons),
        'triggered': triggered,
        'all_preds': predictions,
        'prob': (hp, dp, ap),
        'change': (hc, dc, ac),
        'macao': macao,
        'pred_original': pred,
        'conf_original': conf
    }


def main():
    # 从3.21_result.txt解析数据
    print("=" * 100)
    print("3.21 周六+周日比赛 V3.2规律体系分析（优化版）")
    print("=" * 100)
    
    # 周六比赛数据 (match_id, teams, initial, realtime, macao_tip, form_diff, home_form, away_form)
    saturday_matches = [
        ("周六001", "布里斯班 vs 惠灵顿", "1.85/3.40/3.40", "2.02/3.32/3.00", "惠灵顿凤凰 贏", -4, "DDLDL", "WDLLD"),
        ("周六002", "大田市民 vs 全北现代", "2.79/3.15/2.21", "2.52/3.10/2.44", "全北现代 贏", -2, "WDDDL", "WDDLW"),
        ("周六003", "福冈黄蜂 vs 大阪钢巴", "3.20/3.15/2.01", "3.70/3.30/1.80", "大阪钢巴 贏", -5, "DLLLL", "DLDWD"),
        ("周六004", "墨胜利 vs 中央海岸", "1.34/4.55/6.12", "1.38/4.36/5.70", "和局", +0, "WDDWD", "DWDWW"),
        ("周六005", "日本女 vs 澳大利女", "4.90/3.80/1.51", "6.20/4.10/1.38", "日本女足 贏", -2, "WWDWW", "WWWWW"),
        ("周六006", "帕德博恩 vs 德累斯顿", "1.65/3.70/3.95", "1.72/3.60/3.70", "德累斯顿 贏", -1, "DDWWD", "WDWDL"),
        ("周六007", "伊普斯 vs 米尔沃尔", "1.56/3.65/4.68", "1.58/3.60/4.58", "伊普斯维奇 贏", +2, "WDDWW", "LWWWW"),
        ("周六008", "埃尔切 vs 马洛卡", "1.97/3.18/3.25", "1.97/3.10/3.34", "马洛卡 贏", -5, "LLDLD", "WDLLL"),
        ("周六009", "帕尔马 vs 克雷莫纳", "1.85/3.05/3.85", "1.95/2.95/3.60", "帕尔马 贏", +7, "LDDWW", "LLLLD"),
        ("周六010", "海登海姆 vs 勒沃库森", "5.10/4.18/1.44", "5.40/4.45/1.39", "勒沃库森 贏", -5, "LLLDL", "LDDDW"),
        ("周六011", "科隆 vs 门兴", "2.12/3.33/2.80", "2.08/3.25/2.93", "门兴格拉德巴赫 贏", -6, "DLLDL", "WLWLL"),
        ("周六012", "沃夫斯堡 vs 不来梅", "2.30/3.40/2.50", "2.27/3.40/2.53", "和局", -3, "DLLLD", "LWWLL"),
        ("周六014", "富勒姆 vs 伯恩利", "1.42/3.95/5.80", "1.42/3.95/5.80", "和局", +5, "DLLWW", "DLLDL"),
        ("周六015", "南安普敦 vs 牛津联", "1.44/3.90/5.60", "1.42/3.95/5.80", "牛津联 贏", +5, "WWDWW", "DWWWL"),
        ("周六016", "西班牙人 vs 赫塔费", "2.38/2.60/3.08", "2.28/2.60/3.27", "赫塔费 贏", -6, "LDDLD", "LWWLW"),
        ("周六017", "福图纳 vs 特温特", "5.80/4.40/1.37", "6.05/4.60/1.34", "特温特 贏", +2, "WLWWL", "LWWWD"),
        ("周六018", "图卢兹 vs 洛里昂", "1.87/3.12/3.65", "1.78/3.15/4.00", "图卢兹 贏", -2, "WLDLD", "WDDDD"),
        ("周六019", "AC米兰 vs 都灵", "1.28/4.50/8.00", "1.28/4.50/8.00", "AC米兰 贏", -2, "LWWLD", "WLWLL"),
        ("周六020", "维京 vs 莫尔德", "1.60/3.95/4.00", "1.63/3.95/3.80", "莫尔德 贏", -6, "LLWWD", "WLWDW"),
        ("周六021", "埃弗顿 vs 切尔西", "3.25/3.25/1.95", "3.10/3.25/2.01", "切尔西 贏", +2, "LWWLL", "LLLDW"),
        ("周六022", "多特蒙德 vs 汉堡", "1.30/4.70/6.80", "1.25/5.10/7.50", "多特蒙德 贏", +4, "WWLLD", "DWLLD"),
        ("周六023", "奥萨苏纳 vs 赫罗纳", "1.88/3.30/3.40", "1.90/3.20/3.45", "赫罗纳 贏", -6, "LDLWD", "WDLDW"),
        ("周六024", "莱万特 vs 奥维耶多", "2.07/3.10/3.10", "2.03/3.10/3.18", "莱万特 贏", -2, "DDWLL", "WDLLD"),
        ("周六025", "本菲卡 vs 吉马良斯", "1.17/5.60/10.50", "1.16/5.66/11.00", "本菲卡 贏", +9, "WDWLW", "LLDLW"),
        ("周六026", "尤文图斯 vs 萨索洛", "1.25/4.85/8.10", "1.19/5.30/10.00", "尤文图斯 贏", +4, "WWDWL", "LLWWW"),
        ("周六027", "利兹联 vs 布伦特", "2.33/3.15/2.62", "2.37/3.05/2.64", "布伦特福德 贏", -1, "DWLLD", "DDDWL"),
        ("周六028", "塞维利亚 vs 巴伦西亚", "2.10/3.00/3.13", "2.08/2.90/3.30", "和局", -3, "LDDWD", "LWWLW"),
        ("周六029", "尼斯 vs 巴黎圣曼", "6.90/5.10/1.27", "6.90/5.10/1.27", "巴黎圣日耳曼 贏", -5, "WLDLD", "WWLWD"),
        ("周六030", "温哥华 vs 圣何塞", "1.42/4.30/5.20", "1.42/4.30/5.20", "温哥华白帽 贏", -3, "LWLWW", "LWWWW"),
    ]
    
    sunday_matches = [
        ("周日001", "首尔FC vs 光州FC", "1.44/3.56/6.50", "1.44/3.56/6.50", "首尔FC 贏", +4, "WWLLW", "DDWDD"),
        ("周日002", "大阪樱花 vs 神户胜利", "2.97/3.35/2.03", "2.97/3.35/2.03", "神户胜利船 贏", -10, "LWDLL", "DWWWW"),
        ("周日003", "浦和红钻 vs 町田泽维", "2.60/3.10/2.38", "2.60/3.10/2.38", "和局", -2, "DLWLW", "LWWDW"),
        ("周日004", "珀斯 vs 墨尔本城", "3.36/3.40/1.86", "3.36/3.40/1.86", "和局", -6, "LDDLL", "WDDLL"),
        ("周日005", "奈梅亨 vs 海伦芬", "1.60/4.10/3.85", "1.60/4.10/3.85", "奈梅亨尼美根 贏", -2, "WWWLD", "WWWLW"),
        ("周日006", "科莫 vs 比萨", "1.17/5.50/10.75", "1.17/5.50/10.75", "科莫 贏", +10, "WWDWW", "WLLLL"),
        ("周日007", "纽卡斯尔 vs 桑德兰", "1.53/3.65/5.00", "1.53/3.65/5.00", "纽卡斯尔联 贏", +3, "LWDLW", "LLWDL"),
        ("周日010", "费耶诺德 vs 阿贾克斯", "1.85/3.70/3.15", "1.85/3.70/3.15", "和局", +2, "WDLWW", "WLDDW"),
        ("周日011", "博洛尼亚 vs 拉齐奥", "2.10/2.95/3.18", "2.10/2.95/3.18", "和局", -2, "DWDLW", "WWDLD"),
        ("周日012", "亚特兰大 vs 维罗纳", "1.27/4.60/8.00", "1.27/4.60/8.00", "和局", +0, "LDLDD", "LWLLL"),
        ("周日013", "维拉 vs 西汉姆联", "1.72/3.52/3.80", "1.75/3.50/3.68", "和局", +2, "WLWLL", "DDWLD"),
        ("周日014", "热刺 vs 诺丁汉", "2.15/3.15/2.90", "2.15/3.15/2.90", "和局", -1, "WDLLL", "WDLDL"),
        ("周日015", "美因茨 vs 法兰克福", "1.91/3.45/3.16", "1.91/3.45/3.16", "法兰克福 贏", -1, "WWDDD", "WDWLW"),
        ("周日016", "塞尔塔 vs 阿拉维斯", "1.69/3.18/4.50", "1.69/3.18/4.50", "维戈塞尔塔 贏", +7, "WDDLW", "DLLDD"),
        ("周日017", "格罗宁根 vs 阿尔克马", "2.50/3.45/2.28", "2.50/3.45/2.28", "阿尔克马尔 贏", -10, "DWLLL", "WWWLW"),
        ("周日018", "布兰 vs 特罗姆瑟", "1.75/3.50/3.68", "1.75/3.50/3.68", "特羅素 贏", -3, "WLDLD", "WLDDW"),
        ("周日019", "马赛 vs 里尔", "1.72/3.45/3.87", "1.72/3.45/3.87", "马赛 贏", +6, "WWDWL", "LWLDW"),
        ("周日020", "阿森纳 vs 曼城", "2.13/3.05/3.02", "2.13/3.05/3.02", "阿森纳 贏", +11, "WWDWW", "LDLWD"),
        ("周日021", "圣保利 vs 弗赖堡", "2.51/2.89/2.60", "2.51/2.89/2.60", "和局", +0, "LDWWL", "WLLDL"),
        ("周日022", "罗马 vs 莱切", "1.30/4.25/8.00", "1.30/4.25/8.00", "罗马 贏", -2, "DLDLD", "LWLLW"),
        ("周日023", "纽约城 vs 迈阿密国际", "2.26/3.45/2.52", "2.26/3.45/2.52", "國際邁亞密 贏", +3, "WWWDL", "DDDWW"),
        ("周日024", "毕尔巴鄂 vs 贝蒂斯", "1.87/3.25/3.50", "1.87/3.25/3.50", "和局", -4, "LLLDW", "WDLLD"),
        ("周日025", "奥格斯堡 vs 斯图加特", "3.25/3.55/1.85", "3.25/3.55/1.85", "斯图加特 贏", +2, "LLWWW", "LWLDW"),
        ("周日026", "佛罗伦萨 vs 国际米兰", "4.65/3.77/1.54", "4.65/3.77/1.54", "国际米兰 贏", +7, "WWWDL", "DLDWL"),
        ("周日027", "皇马 vs 马竞", "1.75/3.75/3.45", "1.75/3.75/3.45", "和局", +6, "WWWWL", "LWWWL"),
        ("周日028", "布拉加 vs 波尔图", "3.00/3.05/2.14", "3.00/3.05/2.14", "波尔图 贏", +0, "WLDWW", "WWWDL"),
    ]
    
    all_matches = saturday_matches + sunday_matches
    
    results = []
    stable_matches = []  # 稳胆
    upset_matches = []   # 爆冷
    watch_matches = []   # 观望
    
    print(f"\n{'='*100}")
    print(f"{{'编号':<8}} {{'对阵':<22}} {{'置信度':<7}} {{'澳门':<10}} {{'近况差':<7}} {{'变化(H/D/A)':<28}} {{'V3.2预测':<8}} {'规律'}")
    print(f"{'='*100}")
    
    for match in all_matches:
        mid, teams, ini, rt, macao, fd, hf, af = match
        r = analyze_with_v31(mid, teams, ini, rt, macao, fd, hf, af)
        
        hc, dc, ac = r['change']
        change_str = f"H{hc:+.1f}% D{dc:+.1f}% A{ac:+.1f}%"
        
        results.append((mid, teams, r))
        
        # 分类
        if r['prediction'] == "观望":
            watch_matches.append((mid, teams, r))
        elif r['confidence'] >= 75 and r['prediction'] in ["主胜", "客胜"]:
            stable_matches.append((mid, teams, r))
        
        # 爆冷信号
        upset_signals = []
        if r['prediction'] == "平局" and r['confidence'] >= 70:
            upset_signals.append("平局信号")
        if "规律R" in str(r['triggered']) and "真造热" in str(r['triggered']):
            upset_signals.append("反向爆冷")
        if r['prediction'] == "观望" and r['conf_original'] >= 60:
            upset_signals.append("高置信观望")
        if upset_signals:
            upset_matches.append((mid, teams, r, upset_signals))
        
        print(f"{mid:<8} {teams:<22} {r['conf_original']:.1f}%   {r['macao']:<10} {fd:+d}     {change_str:<28} {r['prediction']:<8} {r['rule']}")
    
    # ===== 统计 =====
    print(f"\n{'='*100}")
    print("[统计] V3.2规律体系分析统计")
    print(f"{'='*100}")
    
    pred_count = {}
    form_diff_dict = {m[0]: m[5] for m in all_matches}
    
    for mid, teams, r in results:
        p = r['prediction']
        pred_count[p] = pred_count.get(p, 0) + 1
    
    print(f"\n方向统计：主胜 {pred_count.get('主胜',0)} | 客胜 {pred_count.get('客胜',0)} | 平局 {pred_count.get('平局',0)} | 观望 {pred_count.get('观望',0)} | 主胜/平局 {pred_count.get('主胜/平局',0)}")
    print(f"总场次：{len(results)}")
    
    # 规律触发统计
    rule_count = {}
    for mid, teams, r in results:
        for rule in r['triggered']:
            rule_count[rule] = rule_count.get(rule, 0) + 1
    
    print(f"\n规律触发统计：")
    for rule, count in sorted(rule_count.items(), key=lambda x: -x[1]):
        print(f"  {rule}: {count}场")
    
    # ===== 最稳比赛 =====
    print(f"\n{'='*100}")
    print("[稳胆] V3.2最稳比赛（置信度>=75%+明确方向）")
    print(f"{'='*100}")
    print(f"\n{{'编号':<8}} {{'对阵':<22}} {{'置信度':<7}} {{'澳门':<10}} {{'近况差':<7}} {{'V3.2预测':<8}} {'规律'}")
    print(f"{'-'*90}")
    
    for mid, teams, r in stable_matches:
        fd = form_diff_dict.get(mid, 0)
        print(f"{mid:<8} {teams:<22} {r['confidence']:.0f}%    {r['macao']:<10} {fd:+d}     {r['prediction']:<8} {r['rule']}")
    
    # ===== 爆冷信号 =====
    print(f"\n{'='*100}")
    print("[爆冷] V3.2爆冷信号")
    print(f"{'='*100}")
    print(f"\n{{'编号':<8}} {{'对阵':<22}} {{'置信度':<7}} {{'澳门':<10}} {{'近况差':<7}} {{'V3.2预测':<8}} {'信号'}")
    print(f"{'-'*90}")
    
    for item in upset_matches:
        mid, teams, r, signals = item
        fd = form_diff_dict.get(mid, 0)
        print(f"{mid:<8} {teams:<22} {r['confidence']:.0f}%    {r['macao']:<10} {fd:+d}     {r['prediction']:<8} {', '.join(signals)}")
    
    # ===== 观望场次 =====
    print(f"\n{'='*100}")
    print("[观望] V3.2观望场次（不投注）")
    print(f"{'='*100}")
    for mid, teams, r in watch_matches:
        print(f"  {mid} {teams} - {r['reason']}")
    
    print(f"\n分析完成！共{len(results)}场比赛，{len(stable_matches)}场稳胆，{len(upset_matches)}场爆冷信号，{len(watch_matches)}场观望")


if __name__ == "__main__":
    main()
