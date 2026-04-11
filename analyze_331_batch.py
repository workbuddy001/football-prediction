# -*- coding: utf-8 -*-
"""
3.31比赛批量分析脚本 - 基于4.01修正版框架
"""

# ==================== 所有比赛数据 ====================

matches = []

def calc_form_score(form_str):
    """计算近况得分（最近一场×2，其余×1，满分18）"""
    if not form_str or len(form_str) == 0:
        return 0
    # 左边第一个 = 最近
    scores = []
    for i, c in enumerate(form_str[:6]):  # 取最近6场
        if c == 'W':
            s = 6 if i == 0 else 3
        elif c == 'D':
            s = 2 if i == 0 else 1
        else:  # L
            s = 0
        scores.append(s)
    return sum(scores)

def calc_confidence(form_diff):
    """计算置信度（基于近况差）"""
    abs_diff = abs(form_diff)
    if abs_diff >= 10:
        return min(85, 60 + abs_diff * 2.5)
    elif abs_diff >= 7:
        return 55 + abs_diff * 2
    elif abs_diff >= 4:
        return 50 + abs_diff * 1.5
    else:
        return 40 + abs_diff * 2

def classify_chip_state(jc_h_chg, jc_d_chg, jc_a_chg):
    """分类筹码状态（基于竞彩赔率变化）"""
    h_abs = abs(jc_h_chg)
    d_abs = abs(jc_d_chg)
    a_abs = abs(jc_a_chg)
    total = h_abs + d_abs + a_abs

    # 全锁定
    if h_abs < 0.5 and d_abs < 0.5 and a_abs < 0.5:
        return "全锁定", "市场无强烈信号"
    # 极端造热/推离
    if jc_h_chg < -10:
        return "极端造热主", f"竞彩主赔降{abs(jc_h_chg):.1f}%，筹码大量涌入主队"
    if jc_a_chg < -10:
        return "极端造热客", f"竞彩客赔降{abs(jc_a_chg):.1f}%，筹码大量涌入客队"
    if jc_h_chg > 10:
        return "极端推离主", f"竞彩主赔升{jc_h_chg:.1f}%，筹码被推离主队"
    if jc_a_chg > 10:
        return "极端推离客", f"竞彩客赔升{jc_a_chg:.1f}%，筹码被推离客队"
    # 单向锁定
    lock_count = 0
    change_dirs = []
    for name, chg in [("主", jc_h_chg), ("平", jc_d_chg), ("客", jc_a_chg)]:
        if chg > 2:
            lock_count += 1
            change_dirs.append(f"{name}升")
        elif chg < -2:
            lock_count += 1
            change_dirs.append(f"{name}降")
    if lock_count == 2:
        # 找到没变的那向
        locked = []
        if h_abs < 0.5: locked.append("主")
        if d_abs < 0.5: locked.append("平")
        if a_abs < 0.5: locked.append("客")
        if locked:
            return "单向锁定", f"{'、'.join(locked)}被锁定，市场真实押注方向"
    # 均衡分流
    if total > 2:
        all_mid = 0.5 <= h_abs <= 2 and 0.5 <= d_abs <= 2 and 0.5 <= a_abs <= 2
        if all_mid:
            return "均衡分流", "三向均小幅变化，筹码被均衡引导"
        return "轻度调控", f"总变化{total:.1f}%，市场小幅调控"
    return "观望", "变化不明显，信号微弱"

def analyze_match(m):
    """分析单场比赛"""
    result = {}
    home = m['home']
    away = m['away']
    league = m['league']
    home_form = m['home_form']
    away_form = m['away_form']
    macau_rec = m['macau_rec']  # 澳门推荐: 主/平/客

    # 1. 近况得分
    home_score = calc_form_score(home_form)
    away_score = calc_form_score(away_form)
    form_diff = home_score - away_score  # 正=主队近况优，负=客队近况优

    # 2. 置信度
    confidence = calc_confidence(form_diff)
    conf_dir = "主胜" if form_diff > 0 else ("客胜" if form_diff < 0 else "无倾向")

    # 3. 竞彩赔率变化
    jc_h_init = m['jc_h_init']
    jc_h_rt = m['jc_h_rt']
    jc_d_init = m['jc_d_init']
    jc_d_rt = m['jc_d_rt']
    jc_a_init = m['jc_a_init']
    jc_a_rt = m['jc_a_rt']

    jc_h_chg = (jc_h_rt - jc_h_init) / jc_h_init * 100 if jc_h_init else 0
    jc_d_chg = (jc_d_rt - jc_d_init) / jc_d_init * 100 if jc_d_init else 0
    jc_a_chg = (jc_a_rt - jc_a_init) / jc_a_init * 100 if jc_a_init else 0

    # 4. 澳门赔率变化
    am_h_init = m['am_h_init']
    am_h_rt = m['am_h_rt']
    am_d_init = m['am_d_init']
    am_d_rt = m['am_d_rt']
    am_a_init = m['am_a_init']
    am_a_rt = m['am_a_rt']

    am_h_chg = (am_h_rt - am_h_init) / am_h_init * 100 if am_h_init else 0
    am_d_chg = (am_d_rt - am_d_init) / am_d_init * 100 if am_d_init else 0
    am_a_chg = (am_a_rt - am_a_init) / am_a_init * 100 if am_a_init else 0

    # 5. 离散度（竞彩vs澳门）
    def dispersion(jc, am):
        if am == 0: return 0
        return (jc - am) / am * 100

    disp_h = dispersion(jc_h_rt, am_h_rt)
    disp_d = dispersion(jc_d_rt, am_d_rt)
    disp_a = dispersion(jc_a_rt, am_a_rt)
    disp_avg = abs(disp_h) + abs(disp_d) + abs(disp_a)
    disp_avg /= 3

    # 6. 筹码状态分类
    chip_state, chip_desc = classify_chip_state(jc_h_chg, jc_d_chg, jc_a_chg)

    # 7. 盘口硬度
    am_total = abs(am_h_chg) + abs(am_d_chg) + abs(am_a_chg)
    jc_total = abs(jc_h_chg) + abs(jc_d_chg) + abs(jc_a_chg)

    hardness_tags = []
    if jc_total > 10 and am_total < 0.5:
        hardness_tags.append("[盘口极硬]")
    if jc_total > 3 and am_total < 0.5:
        hardness_tags.append("[盘口硬]")
    # 不怕/不跟
    if am_total < 0.5:
        if jc_h_chg > 3:
            hardness_tags.append("[不怕主]")
        if jc_a_chg > 3:
            hardness_tags.append("[不怕客]")
        if jc_h_chg < -3:
            hardness_tags.append("[不跟主]")
        if jc_a_chg < -3:
            hardness_tags.append("[不跟客]")

    # 8. 竞彩赔率绝对值分析
    jc_min = min(jc_h_rt, jc_d_rt, jc_a_rt)
    jc_min_dir = "主胜" if jc_h_rt == jc_min else ("平局" if jc_d_rt == jc_min else "客胜")
    jc_pressure = "低" if jc_min < 2.5 else ("中" if jc_min < 3.5 else "高")

    am_min = min(am_h_rt, am_d_rt, am_a_rt)
    am_min_dir = "主胜" if am_h_rt == am_min else ("平局" if am_d_rt == am_min else "客胜")

    # 9. 综合判断
    prediction = ""
    reasoning = []
    tags = []

    # 规律O: 近况差极端 + 竞彩全不动
    if abs(form_diff) >= 8 and jc_total < 2:
        if form_diff > 0:
            prediction = "主胜"
            tags.append("规律O")
            reasoning.append(f"近况差{form_diff:.0f}分(极端)+竞彩全不动→主队强信号")
        else:
            prediction = "客胜"
            tags.append("规律O")
            reasoning.append(f"近况差{form_diff:.0f}分(极端)+竞彩全不动→客队强信号")

    # 盘口硬度信号
    if not prediction and hardness_tags:
        if "[盘口极硬]" in hardness_tags:
            if jc_h_chg < -5:
                prediction = "主胜"
                tags.append("盘口极硬+造热主")
                reasoning.append(f"竞彩主赔降{abs(jc_h_chg):.1f}%+澳门不动→盘口极硬，主队实盘")
            elif jc_a_chg < -5:
                prediction = "客胜"
                tags.append("盘口极硬+造热客")
                reasoning.append(f"竞彩客赔降{abs(jc_a_chg):.1f}%+澳门不动→盘口极硬，客队实盘")
            elif jc_h_chg > 5:
                # 澳门不怕主
                prediction = "客胜或平"
                tags.append("不怕主")
                reasoning.append(f"竞彩主赔升{jc_h_chg:.1f}%+澳门不动→澳门不怕主队赢→主队难出")

        if "[不怕主]" in hardness_tags and not prediction:
            tags.append("不怕主")
            reasoning.append("澳门不动+竞彩主赔走高→澳门不怕主队赢")
            if conf_dir == "客胜":
                prediction = "客胜"
            else:
                prediction = "客胜或平"

        if "[不怕客]" in hardness_tags and not prediction:
            tags.append("不怕客")
            reasoning.append("澳门不动+竞彩客赔走高→澳门不怕客队赢")
            if conf_dir == "主胜":
                prediction = "主胜"
            else:
                prediction = "主胜或平"

    # 极端造热判断
    if not prediction:
        if chip_state.startswith("极端造热主"):
            # 真假造热辨别
            other_down = jc_d_chg < -2 or jc_a_chg < -2  # 其他方向也在降
            if macau_rec == "主":
                if not other_down:
                    prediction = "客胜或平"
                    tags.append("真造热主→反向")
                    reasoning.append(f"竞彩主赔降{abs(jc_h_chg):.1f}%(造热)+澳门推主+其他两向均升→真造热→反向")
                else:
                    prediction = "主胜"
                    tags.append("假造热主→顺向")
                    reasoning.append(f"竞彩主赔降但有分流出口→假造热→顺向")
            elif macau_rec == "客":
                prediction = "主胜"
                tags.append("造热主+澳门推客")
                reasoning.append(f"竞彩造热主+澳门推客→信号矛盾→竞彩方向被削弱，但造热为真→反向")
            else:
                prediction = "客胜或平"
                tags.append("造热主+澳门推平")
                reasoning.append(f"竞彩造热主+澳门推平→平局聚焦")

        elif chip_state.startswith("极端造热客"):
            other_down = jc_h_chg < -2 or jc_d_chg < -2
            if macau_rec == "客":
                if not other_down:
                    prediction = "主胜或平"
                    tags.append("真造热客→反向")
                    reasoning.append(f"竞彩客赔降{abs(jc_a_chg):.1f}%(造热)+澳门推客+其他两向均升→真造热→反向")
                else:
                    prediction = "客胜"
                    tags.append("假造热客→顺向")
                    reasoning.append(f"竞彩客赔降但有分流出口→假造热→顺向")
            elif macau_rec == "主":
                prediction = "客胜"
                tags.append("造热客+澳门推主")
                reasoning.append(f"竞彩造热客+澳门推主→信号矛盾")
            else:
                prediction = "主胜或平"
                tags.append("造热客+澳门推平")
                reasoning.append(f"竞彩造热客+澳门推平→平局聚焦")

    # 极端推离判断
    if not prediction:
        if chip_state == "极端推离主":
            prediction = "客胜或平"
            tags.append("推离主")
            reasoning.append("竞彩主赔大幅升高→主队被推离→难出")
        elif chip_state == "极端推离客":
            prediction = "主胜或平"
            tags.append("推离客")
            reasoning.append("竞彩客赔大幅升高→客队被推离→难出")

    # 赔率绝对值判断（赔付压力最小方向）
    if not prediction:
        if jc_pressure == "低" and jc_min_dir == conf_dir:
            prediction = jc_min_dir
            tags.append("赔付压力")
            reasoning.append(f"竞彩{jc_min_dir}赔{jc_min:.2f}(赔付{jc_pressure})，与置信度方向一致")

    # 默认按置信度
    if not prediction:
        if confidence >= 55:
            prediction = conf_dir
            tags.append("置信度方向")
            reasoning.append(f"近况差{form_diff:.0f}分，置信度{confidence:.0f}%→{conf_dir}")
        elif confidence >= 45:
            prediction = f"{conf_dir}或平" if form_diff != 0 else "平局"
            tags.append("中等置信")
            reasoning.append(f"近况差{form_diff:.0f}分，置信度{confidence:.0f}%→方向不明")
        else:
            prediction = "观望"
            tags.append("低置信")
            reasoning.append(f"近况差{form_diff:.0f}分，双方实力接近")

    # 赔率绝对值二次验证
    if prediction and prediction not in ["观望"]:
        # 检查预测方向的赔率绝对值
        pred_odds = jc_h_rt if "主" in prediction else (jc_a_rt if "客" in prediction else jc_d_rt)
        if pred_odds > 3.5:
            reasoning.append(f"⚠️ 预测方向竞彩赔{pred_odds:.2f}>3.5，赔付压力高，需警惕")

    result = {
        'id': m['id'],
        'home': home,
        'away': away,
        'league': league,
        'match_time': m.get('match_time', ''),
        'home_form': home_form,
        'away_form': away_form,
        'home_score': home_score,
        'away_score': away_score,
        'form_diff': form_diff,
        'confidence': confidence,
        'conf_dir': conf_dir,
        'jc_h_init': jc_h_init, 'jc_h_rt': jc_h_rt, 'jc_h_chg': jc_h_chg,
        'jc_d_init': jc_d_init, 'jc_d_rt': jc_d_rt, 'jc_d_chg': jc_d_chg,
        'jc_a_init': jc_a_init, 'jc_a_rt': jc_a_rt, 'jc_a_chg': jc_a_chg,
        'am_h_init': am_h_init, 'am_h_rt': am_h_rt, 'am_h_chg': am_h_chg,
        'am_d_init': am_d_init, 'am_d_rt': am_d_rt, 'am_d_chg': am_d_chg,
        'am_a_init': am_a_init, 'am_a_rt': am_a_rt, 'am_a_chg': am_a_chg,
        'macau_rec': macau_rec,
        'disp_avg': disp_avg,
        'chip_state': chip_state,
        'chip_desc': chip_desc,
        'hardness_tags': hardness_tags,
        'jc_min_dir': jc_min_dir,
        'jc_pressure': jc_pressure,
        'prediction': prediction,
        'tags': tags,
        'reasoning': reasoning,
    }
    return result

# ==================== 填入比赛数据 ====================
# 竞彩赔率: 初盘和即时
# 澳门赔率: 初盘和即时（index 2 = *门）

match_data = [
    # 周二001 喀麦隆vs中国
    {
        'id': '周二001', 'home': '喀麦隆', 'away': '中国', 'league': '国际赛', 'match_time': '2026-04-01 01:00',
        'home_form': 'WDLWDW', 'away_form': 'WLWDLW', 'macau_rec': '中国',
        'jc_h_init': 1.76, 'jc_h_rt': 1.76, 'jc_d_init': 3.30, 'jc_d_rt': 3.30, 'jc_a_init': 3.90, 'jc_a_rt': 3.90,
        'am_h_init': 1.88, 'am_h_rt': 1.88, 'am_d_init': 3.35, 'am_d_rt': 3.35, 'am_a_init': 3.48, 'am_a_rt': 3.48,
    },
    # 周二002 澳大利亚vs库拉索
    {
        'id': '周二002', 'home': '澳大利亚', 'away': '库拉索', 'league': '国际赛', 'match_time': '2026-04-01 01:00',
        'home_form': 'WWDWLW', 'away_form': 'LLDWDL', 'macau_rec': '澳大利亚',
        'jc_h_init': 1.15, 'jc_h_rt': 1.15, 'jc_d_init': 6.50, 'jc_d_rt': 6.50, 'jc_a_init': 11.00, 'jc_a_rt': 11.00,
        'am_h_init': 1.22, 'am_h_rt': 1.22, 'am_d_init': 5.50, 'am_d_rt': 5.50, 'am_a_init': 10.00, 'am_a_rt': 10.00,
    },
    # 周二003 挪威vs瑞士
    {
        'id': '周二003', 'home': '挪威', 'away': '瑞士', 'league': '世预赛', 'match_time': '2026-04-01 02:45',
        'home_form': 'DWWLWL', 'away_form': 'WWWDWW', 'macau_rec': '瑞士',
        'jc_h_init': 2.50, 'jc_h_rt': 2.50, 'jc_d_init': 3.05, 'jc_d_rt': 3.05, 'jc_a_init': 2.72, 'jc_a_rt': 2.72,
        'am_h_init': 2.55, 'am_h_rt': 2.55, 'am_d_init': 3.10, 'am_d_rt': 3.10, 'am_a_init': 2.60, 'am_a_rt': 2.60,
    },
    # 周二004 黑山vs斯洛文尼
    {
        'id': '周二004', 'home': '黑山', 'away': '斯洛文尼', 'league': '世预赛', 'match_time': '2026-04-01 02:45',
        'home_form': 'LLWLWL', 'away_form': 'WDLWWL', 'macau_rec': '和局',
        'jc_h_init': 2.75, 'jc_h_rt': 2.75, 'jc_d_init': 2.95, 'jc_d_rt': 2.95, 'jc_a_init': 2.42, 'jc_a_rt': 2.42,
        'am_h_init': 2.78, 'am_h_rt': 2.78, 'am_d_init': 2.88, 'am_d_rt': 2.88, 'am_a_init': 2.38, 'am_a_rt': 2.38,
    },
    # 周二005 匈牙利vs希腊
    {
        'id': '周二005', 'home': '匈牙利', 'away': '希腊', 'league': '世预赛', 'match_time': '2026-04-01 02:45',
        'home_form': 'WDWWWW', 'away_form': 'WDWLWL', 'macau_rec': '匈牙利',
        'jc_h_init': 1.78, 'jc_h_rt': 1.78, 'jc_d_init': 3.50, 'jc_d_rt': 3.50, 'jc_a_init': 3.95, 'jc_a_rt': 3.95,
        'am_h_init': 1.85, 'am_h_rt': 1.85, 'am_d_init': 3.30, 'am_d_rt': 3.30, 'am_a_init': 3.75, 'am_a_rt': 3.75,
    },
    # 周二006 南非vs巴拿马
    {
        'id': '周二006', 'home': '南非', 'away': '巴拿马', 'league': '国际赛', 'match_time': '2026-04-01 02:00',
        'home_form': 'DLWLDL', 'away_form': 'WWLDWL', 'macau_rec': '巴拿马',
        'jc_h_init': 1.87, 'jc_h_rt': 1.87, 'jc_d_init': 3.20, 'jc_d_rt': 3.20, 'jc_a_init': 3.60, 'jc_a_rt': 3.60,
        'am_h_init': 1.95, 'am_h_rt': 1.95, 'am_d_init': 3.10, 'am_d_rt': 3.10, 'am_a_init': 3.40, 'am_a_rt': 3.40,
    },
    # 周二007 摩洛哥vs巴拉圭
    {
        'id': '周二007', 'home': '摩洛哥', 'away': '巴拉圭', 'league': '国际赛', 'match_time': '2026-04-01 03:00',
        'home_form': 'WDWWDW', 'away_form': 'DWWWDL', 'macau_rec': '摩洛哥',
        'jc_h_init': 1.53, 'jc_h_rt': 1.53, 'jc_d_init': 3.75, 'jc_d_rt': 3.75, 'jc_a_init': 5.50, 'jc_a_rt': 5.50,
        'am_h_init': 1.58, 'am_h_rt': 1.58, 'am_d_init': 3.60, 'am_d_rt': 3.60, 'am_a_init': 5.00, 'am_a_rt': 5.00,
    },
    # 周二008 阿尔及利vs乌拉圭
    {
        'id': '周二008', 'home': '阿尔及利', 'away': '乌拉圭', 'league': '国际赛', 'match_time': '2026-04-01 03:00',
        'home_form': 'WWWDWW', 'away_form': 'WDWWDW', 'macau_rec': '乌拉圭',
        'jc_h_init': 2.45, 'jc_h_rt': 2.45, 'jc_d_init': 3.05, 'jc_d_rt': 3.05, 'jc_a_init': 2.68, 'jc_a_rt': 2.68,
        'am_h_init': 2.45, 'am_h_rt': 2.45, 'am_d_init': 3.05, 'am_d_rt': 3.05, 'am_a_init': 2.65, 'am_a_rt': 2.65,
    },
    # 周二009 苏格兰vs科特迪瓦
    {
        'id': '周二009', 'home': '苏格兰', 'away': '科特迪瓦', 'league': '国际赛', 'match_time': '2026-04-01 02:30',
        'home_form': 'LLWDLW', 'away_form': 'WWWWDW', 'macau_rec': '科特迪瓦',
        'jc_h_init': 2.55, 'jc_h_rt': 2.55, 'jc_d_init': 3.15, 'jc_d_rt': 3.15, 'jc_a_init': 2.60, 'jc_a_rt': 2.60,
        'am_h_init': 2.65, 'am_h_rt': 2.65, 'am_d_init': 3.00, 'am_d_rt': 3.00, 'am_a_init': 2.55, 'am_a_rt': 2.55,
    },
    # 周二010 荷兰vs厄瓜多尔
    {
        'id': '周二010', 'home': '荷兰', 'away': '厄瓜多尔', 'league': '国际赛', 'match_time': '2026-04-01 03:00',
        'home_form': 'WDWWWW', 'away_form': 'WDLDWL', 'macau_rec': '荷兰',
        'jc_h_init': 1.33, 'jc_h_rt': 1.33, 'jc_d_init': 4.75, 'jc_d_rt': 4.75, 'jc_a_init': 7.00, 'jc_a_rt': 7.00,
        'am_h_init': 1.38, 'am_h_rt': 1.38, 'am_d_init': 4.40, 'am_d_rt': 4.40, 'am_a_init': 6.50, 'am_a_rt': 6.50,
    },
    # 周二011 英格兰vs日本
    {
        'id': '周二011', 'home': '英格兰', 'away': '日本', 'league': '国际赛', 'match_time': '2026-04-01 03:00',
        'home_form': 'DWWWWW', 'away_form': 'WWWWDW', 'macau_rec': '英格兰',
        'jc_h_init': 1.50, 'jc_h_rt': 1.50, 'jc_d_init': 4.00, 'jc_d_rt': 4.00, 'jc_a_init': 5.40, 'jc_a_rt': 5.40,
        'am_h_init': 1.53, 'am_h_rt': 1.53, 'am_d_init': 3.80, 'am_d_rt': 3.80, 'am_a_init': 5.50, 'am_a_rt': 5.50,
    },
    # 周二012 奥地利vs韩国
    {
        'id': '周二012', 'home': '奥地利', 'away': '韩国', 'league': '国际赛', 'match_time': '2026-04-01 03:00',
        'home_form': 'WDWWWW', 'away_form': 'WWLWDW', 'macau_rec': '奥地利',
        'jc_h_init': 1.52, 'jc_h_rt': 1.52, 'jc_d_init': 3.90, 'jc_d_rt': 3.90, 'jc_a_init': 5.30, 'jc_a_rt': 5.30,
        'am_h_init': 1.60, 'am_h_rt': 1.60, 'am_d_init': 3.60, 'am_d_rt': 3.60, 'am_a_init': 4.80, 'am_a_rt': 4.80,
    },
    # 周二013 科索沃vs土耳其
    {
        'id': '周二013', 'home': '科索沃', 'away': '土耳其', 'league': '世预赛', 'match_time': '2026-04-01 02:45',
        'home_form': 'WDWLWW', 'away_form': 'WWLWDL', 'macau_rec': '土耳其',
        'jc_h_init': 2.70, 'jc_h_rt': 2.70, 'jc_d_init': 3.05, 'jc_d_rt': 3.05, 'jc_a_init': 2.45, 'jc_a_rt': 2.45,
        'am_h_init': 2.65, 'am_h_rt': 2.65, 'am_d_init': 3.05, 'am_d_rt': 3.05, 'am_a_init': 2.45, 'am_a_rt': 2.45,
    },
    # 周二014 瑞典vs波兰
    {
        'id': '周二014', 'home': '瑞典', 'away': '波兰', 'league': '世预赛', 'match_time': '2026-04-01 02:45',
        'home_form': 'WDLLLL', 'away_form': 'WWDWWW', 'macau_rec': '和局',
        'jc_h_init': 1.88, 'jc_h_rt': 1.95, 'jc_d_init': 3.00, 'jc_d_rt': 2.96, 'jc_a_init': 3.78, 'jc_a_rt': 3.59,
        'am_h_init': 1.98, 'am_h_rt': 2.06, 'am_d_init': 2.90, 'am_d_rt': 2.90, 'am_a_init': 3.64, 'am_a_rt': 3.40,
    },
    # 周二015 波黑vs意大利
    {
        'id': '周二015', 'home': '波黑', 'away': '意大利', 'league': '世预赛', 'match_time': '2026-04-01 02:45',
        'home_form': 'DDWWDL', 'away_form': 'WLWWWW', 'macau_rec': '意大利',
        'jc_h_init': 7.25, 'jc_h_rt': 8.35, 'jc_d_init': 3.75, 'jc_d_rt': 4.16, 'jc_a_init': 1.38, 'jc_a_rt': 1.30,
        'am_h_init': 6.40, 'am_h_rt': 6.95, 'am_d_init': 3.51, 'am_d_rt': 3.80, 'am_a_init': 1.47, 'am_a_rt': 1.40,
    },
    # 周二016 捷克vs丹麦
    {
        'id': '周二016', 'home': '捷克', 'away': '丹麦', 'league': '世预赛', 'match_time': '2026-04-01 02:45',
        'home_form': 'DWWLDD', 'away_form': 'WLDWWW', 'macau_rec': '丹麦',
        'jc_h_init': 3.50, 'jc_h_rt': 3.65, 'jc_d_init': 3.00, 'jc_d_rt': 3.09, 'jc_a_init': 1.96, 'jc_a_rt': 1.88,
        'am_h_init': 3.40, 'am_h_rt': 3.40, 'am_d_init': 3.00, 'am_d_rt': 3.00, 'am_a_init': 2.01, 'am_a_rt': 2.01,
    },
    # 周二017 西班牙vs埃及
    {
        'id': '周二017', 'home': '西班牙', 'away': '埃及', 'league': '国际赛', 'match_time': '2026-04-01 03:00',
        'home_form': 'WDWWWW', 'away_form': 'WDLWDD', 'macau_rec': '西班牙',
        # 竞彩数据从源数据第四节提取
        'jc_h_init': 2.00, 'jc_h_rt': 2.00, 'jc_d_init': 4.05, 'jc_d_rt': 4.05, 'jc_a_init': 2.62, 'jc_a_rt': 2.62,
        # 竞彩官*（第一家）
        'am_h_init': 1.11, 'am_h_rt': 1.11, 'am_d_init': 6.70, 'am_d_rt': 6.70, 'am_a_init': 13.00, 'am_a_rt': 13.00,
    },
    # 周二018 刚果(金)vs牙买加
    {
        'id': '周二018', 'home': '刚果(金)', 'away': '牙买加', 'league': '世预赛', 'match_time': '2026-04-01 05:00',
        'home_form': 'WDWDWW', 'away_form': 'WWWDDW', 'macau_rec': '牙买加',
        'jc_h_init': 3.85, 'jc_h_rt': 3.85, 'jc_d_init': 3.05, 'jc_d_rt': 3.05, 'jc_a_init': 1.85, 'jc_a_rt': 1.85,
        'am_h_init': 1.90, 'am_h_rt': 1.90, 'am_d_init': 2.93, 'am_d_rt': 2.93, 'am_a_init': 3.88, 'am_a_rt': 3.88,
    },
    # 周二019 美国vs葡萄牙
    {
        'id': '周二019', 'home': '美国', 'away': '葡萄牙', 'league': '国际赛', 'match_time': '2026-04-01 07:00',
        'home_form': 'LWWWDW', 'away_form': 'DWLDWW', 'macau_rec': '葡萄牙',
        'jc_h_init': 2.14, 'jc_h_rt': 2.14, 'jc_d_init': 3.55, 'jc_d_rt': 3.55, 'jc_a_init': 2.63, 'jc_a_rt': 2.63,
        'am_h_init': 3.85, 'am_h_rt': 4.20, 'am_d_init': 3.70, 'am_d_rt': 3.80, 'am_a_init': 1.68, 'am_a_rt': 1.60,
    },
    # 周二020 加拿大vs突尼斯
    {
        'id': '周二020', 'home': '加拿大', 'away': '突尼斯', 'league': '国际赛', 'match_time': '2026-04-01 07:30',
        'home_form': 'DWWDDL', 'away_form': 'WDDLWW', 'macau_rec': '突尼斯',
        'jc_h_init': 2.90, 'jc_h_rt': 2.90, 'jc_d_init': 3.15, 'jc_d_rt': 3.15, 'jc_a_init': 2.14, 'jc_a_rt': 2.14,
        'am_h_init': 1.75, 'am_h_rt': 1.66, 'am_d_init': 3.33, 'am_d_rt': 3.50, 'am_a_init': 3.95, 'am_a_rt': 4.20,
    },
    # 周二021 巴西vs克罗地亚
    {
        'id': '周二021', 'home': '巴西', 'away': '克罗地亚', 'league': '国际赛', 'match_time': '2026-04-01 08:00',
        'home_form': 'LDWLWL', 'away_form': 'WWWWDW', 'macau_rec': '和局',
        'jc_h_init': 2.88, 'jc_h_rt': 2.88, 'jc_d_init': 3.40, 'jc_d_rt': 3.40, 'jc_a_init': 2.05, 'jc_a_rt': 2.05,
        'am_h_init': 1.78, 'am_h_rt': 1.78, 'am_d_init': 3.63, 'am_d_rt': 3.63, 'am_a_init': 3.50, 'am_a_rt': 3.50,
    },
    # 周二022 墨西哥vs比利时
    {
        'id': '周二022', 'home': '墨西哥', 'away': '比利时', 'league': '国际赛', 'match_time': '2026-04-01 09:00',
        'home_form': 'DWWWLD', 'away_form': 'WWDWDW', 'macau_rec': '比利时',
        'jc_h_init': 1.74, 'jc_h_rt': 1.74, 'jc_d_init': 3.62, 'jc_d_rt': 3.62, 'jc_a_init': 3.60, 'jc_a_rt': 3.60,
        'am_h_init': 2.93, 'am_h_rt': 3.10, 'am_d_init': 3.27, 'am_d_rt': 3.27, 'am_a_init': 2.10, 'am_a_rt': 2.02,
    },
    # 周二023 伊拉克vs玻利维亚
    {
        'id': '周二023', 'home': '伊拉克', 'away': '玻利维亚', 'league': '世预赛', 'match_time': '2026-04-01 11:00',
        'home_form': 'LLWWWD', 'away_form': 'WWLDLL', 'macau_rec': '玻利维亚',
        'jc_h_init': 5.75, 'jc_h_rt': 5.75, 'jc_d_init': 3.70, 'jc_d_rt': 3.70, 'jc_a_init': 1.46, 'jc_a_rt': 1.46,
        'am_h_init': 2.33, 'am_h_rt': 2.40, 'am_d_init': 2.98, 'am_d_rt': 3.00, 'am_a_init': 2.78, 'am_a_rt': 2.70,
    },
    # 周三001 神户胜利vs清水鼓动
    {
        'id': '周三001', 'home': '神户胜利', 'away': '清水鼓动', 'league': '日职', 'match_time': '2026-04-01 18:00',
        'home_form': 'WDDWWW', 'away_form': 'WDDDDW', 'macau_rec': '神户胜利船',
        'jc_h_init': 3.50, 'jc_h_rt': 3.50, 'jc_d_init': 3.40, 'jc_d_rt': 3.40, 'jc_a_init': 1.82, 'jc_a_rt': 1.82,
        'am_h_init': 1.88, 'am_h_rt': 1.88, 'am_d_init': 3.35, 'am_d_rt': 3.35, 'am_a_init': 3.48, 'am_a_rt': 3.48,
    },
    # 周三002 町田泽维vs东京FC
    {
        'id': '周三002', 'home': '町田泽维', 'away': '东京FC', 'league': '日职', 'match_time': '2026-04-01 18:00',
        'home_form': 'DWLWWD', 'away_form': 'DWDWLW', 'macau_rec': '和局',
        'jc_h_init': 4.70, 'jc_h_rt': 4.70, 'jc_d_init': 3.55, 'jc_d_rt': 3.55, 'jc_a_init': 1.58, 'jc_a_rt': 1.58,
        'am_h_init': 2.30, 'am_h_rt': 2.30, 'am_d_init': 3.25, 'am_d_rt': 3.25, 'am_a_init': 2.71, 'am_a_rt': 2.71,
    },
]

# ==================== 分析并生成报告 ====================

results = []
for m in match_data:
    r = analyze_match(m)
    results.append(r)

# 按置信度排序
results.sort(key=lambda x: x['confidence'], reverse=True)

# 生成Markdown报告
report = []
report.append("# 3.31 比赛分析报告（基于4.01修正版框架）")
report.append("")
report.append("> 分析日期：2026-03-31 | 共" + str(len(results)) + "场比赛")
report.append("> 核心原则：竞彩赔率变化=主信号，澳门心水=辅助信号，赔率绝对值=赔付判断")
report.append("")
report.append("---")
report.append("")

# 一、汇总表
report.append("## 一、预测汇总")
report.append("")
report.append("| 编号 | 比赛 | 赛事 | 近况差 | 置信度 | 竞彩变化 | 澳门不动 | 预测 | 标签 |")
report.append("|------|------|------|--------|--------|----------|----------|------|------|")
for r in results:
    jc_total = abs(r['jc_h_chg']) + abs(r['jc_d_chg']) + abs(r['jc_a_chg'])
    am_total = abs(r['am_h_chg']) + abs(r['am_d_chg']) + abs(r['am_a_chg'])
    jc_str = f"{jc_total:.1f}%"
    am_str = "✅不动" if am_total < 0.5 else f"{am_total:.1f}%"
    tags_str = "、".join(r['tags']) if r['tags'] else "—"
    report.append(f"| {r['id']} | {r['home']}vs{r['away']} | {r['league']} | {r['form_diff']:+.0f} | {r['confidence']:.0f}% | {jc_str} | {am_str} | **{r['prediction']}** | {tags_str} |")

report.append("")
report.append("---")
report.append("")

# 二、重点场次分析
report.append("## 二、重点场次详细分析")
report.append("")

# 信心最高的场次
high_conf = [r for r in results if r['confidence'] >= 55]
report.append("### 🔥 高置信场次（置信度≥55%）")
report.append("")
if high_conf:
    for r in high_conf:
        report.append(f"#### {r['id']} {r['home']} vs {r['away']}")
        report.append("")
        report.append(f"- **赛事**: {r['league']} | **时间**: {r['match_time']}")
        report.append(f"- **近况**: 主队{r['home_form']}（{r['home_score']}分）vs 客队{r['away_form']}（{r['away_score']}分）")
        report.append(f"- **近况差**: {r['form_diff']:+.0f}分 → 置信度{r['confidence']:.0f}%，方向：{r['conf_dir']}")
        report.append(f"- **竞彩赔率**: 主{r['jc_h_init']}→{r['jc_h_rt']}({r['jc_h_chg']:+.1f}%) | 平{r['jc_d_init']}→{r['jc_d_rt']}({r['jc_d_chg']:+.1f}%) | 客{r['jc_a_init']}→{r['jc_a_rt']}({r['jc_a_chg']:+.1f}%)")
        report.append(f"- **澳门赔率**: 主{r['am_h_init']}→{r['am_h_rt']}({r['am_h_chg']:+.1f}%) | 平{r['am_d_init']}→{r['am_d_rt']}({r['am_d_chg']:+.1f}%) | 客{r['am_a_init']}→{r['am_a_rt']}({r['am_a_chg']:+.1f}%)")
        report.append(f"- **澳门心水**: {r['macau_rec']}")
        report.append(f"- **筹码状态**: {r['chip_state']} — {r['chip_desc']}")
        if r['hardness_tags']:
            report.append(f"- **盘口标签**: {' '.join(r['hardness_tags'])}")
        report.append(f"- **竞彩最低赔**: {r['jc_min_dir']}（{min(r['jc_h_rt'], r['jc_d_rt'], r['jc_a_rt']):.2f}，赔付压力{r['jc_pressure']}）")
        report.append(f"- **离散度**: {r['disp_avg']:.1f}%")
        report.append(f"- **预测**: **{r['prediction']}**")
        if r['reasoning']:
            report.append(f"- **分析**: {'；'.join(r['reasoning'])}")
        report.append("")
else:
    report.append("本期无高置信场次。")
    report.append("")

report.append("---")
report.append("")

# 可能爆冷场次
cold = [r for r in results if '反向' in str(r['tags']) or '推离' in str(r['tags'])]
report.append("### ⚡ 可能爆冷场次")
report.append("")
if cold:
    for r in cold:
        report.append(f"- **{r['id']} {r['home']}vs{r['away']}**: {r['prediction']}（{'、'.join(r['reasoning'])}）")
    report.append("")
else:
    report.append("本期无明确爆冷信号。")
    report.append("")

report.append("---")
report.append("")

# 三、全场详细数据
report.append("## 三、全场详细数据")
report.append("")
for r in results:
    report.append(f"### {r['id']} {r['home']} vs {r['away']}")
    report.append("")
    report.append(f"| 维度 | 数据 |")
    report.append(f"|------|------|")
    report.append(f"| 近况 | 主{r['home_form']}({r['home_score']}分) vs 客{r['away_form']}({r['away_score']}分) |")
    report.append(f"| 近况差 | {r['form_diff']:+.0f}分 |")
    report.append(f"| 置信度 | {r['confidence']:.0f}% → {r['conf_dir']} |")
    report.append(f"| 竞彩变化 | 主{r['jc_h_chg']:+.1f}% 平{r['jc_d_chg']:+.1f}% 客{r['jc_a_chg']:+.1f}% |")
    report.append(f"| 澳门变化 | 主{r['am_h_chg']:+.1f}% 平{r['am_d_chg']:+.1f}% 客{r['am_a_chg']:+.1f}% |")
    report.append(f"| 竞彩即时 | 主{r['jc_h_rt']} 平{r['jc_d_rt']} 客{r['jc_a_rt']} |")
    report.append(f"| 澳门即时 | 主{r['am_h_rt']} 平{r['am_d_rt']} 客{r['am_a_rt']} |")
    report.append(f"| 澳门心水 | {r['macau_rec']} |")
    report.append(f"| 筹码状态 | {r['chip_state']} |")
    if r['hardness_tags']:
        report.append(f"| 盘口标签 | {' '.join(r['hardness_tags'])} |")
    report.append(f"| 离散度 | {r['disp_avg']:.1f}% |")
    report.append(f"| **预测** | **{r['prediction']}** |")
    report.append(f"| **分析** | {'；'.join(r['reasoning']) if r['reasoning'] else '—'} |")
    report.append("")

report.append("---")
report.append("")
report.append("## 四、免责声明")
report.append("")
report.append("以上分析基于赔率数据和近况评分模型，仅供娱乐参考，不构成任何投注建议。足球比赛受多种因素影响，赔率分析存在不确定性。请理性对待。")

output = "\n".join(report)
with open(r"D:\work\workbuddy\足球预测\3.31_完整分析报告.md", "w", encoding="utf-8") as f:
    f.write(output)

print("报告已生成: D:\\work\\workbuddy\\足球预测\\3.31_完整分析报告.md")
print(f"\n共分析 {len(results)} 场比赛")
print(f"\n=== 高置信场次 ===")
for r in high_conf:
    print(f"  {r['id']} {r['home']}vs{r['away']}: {r['prediction']} (置信{r['confidence']:.0f}%)")
print(f"\n=== 可能爆冷 ===")
for r in cold:
    print(f"  {r['id']} {r['home']}vs{r['away']}: {r['prediction']}")
print(f"\n=== 盘口硬信号 ===")
hard_matches = [r for r in results if r['hardness_tags']]
for r in hard_matches:
    print(f"  {r['id']} {r['home']}vs{r['away']}: {' '.join(r['hardness_tags'])} → {r['prediction']}")
