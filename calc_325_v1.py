#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3.25比赛数据分析 - 应用3.28优化版筹码分流系统(A-G七维度)
更新：仅使用初盘和即时赔率(30家公司)，第四部分不作为依据
"""

import os
import re

# ============ 数据定义 ============
# 注意：只使用第二部分(初盘)和第三部分(即时)的30家公司赔率数据
# 第四部分(竞彩胜平负赔率)不作为判断依据

matches_data = [
    {
        "id": "周四001",
        "home": "土耳其",
        "away": "罗马尼亚",
        "home_form": "DWWWLW",
        "away_form": "WLWWDL",
        "macao_tip": "主队",
        "initial_avg": (1.50, 4.20, 5.75),
        "realtime_avg": (1.38, 5.05, 7.20),
    },
    {
        "id": "周四002",
        "home": "意大利",
        "away": "北爱尔兰",
        "home_form": "LWWWWW",
        "away_form": "WLLWLW",
        "macao_tip": "主队",
        "initial_avg": (1.29, 5.00, 9.50),
        "realtime_avg": (1.26, 5.35, 11.50),
    },
    {
        "id": "周四003",
        "home": "斯洛伐克",
        "away": "科索沃",
        "home_form": "LWWLWW",
        "away_form": "DWWDWL",
        "macao_tip": "客队",
        "initial_avg": (1.90, 3.30, 4.00),
        "realtime_avg": (2.08, 3.15, 3.75),
    },
    {
        "id": "周四004",
        "home": "威尔士",
        "away": "波黑",
        "home_form": "WWLLLW",
        "away_form": "DWWDLW",
        "macao_tip": "主队",
        "initial_avg": (1.95, 3.30, 4.00),
        "realtime_avg": (1.78, 3.45, 4.65),
    },
    {
        "id": "周四005",
        "home": "波兰",
        "away": "阿尔巴尼",
        "home_form": "WDWWWD",
        "away_form": "LWWWWW",
        "macao_tip": "主队",
        "initial_avg": (1.70, 3.50, 5.20),
        "realtime_avg": (1.66, 3.48, 5.50),
    },
    {
        "id": "周四006",
        "home": "捷克",
        "away": "爱尔兰",
        "home_form": "WWLDDW",
        "away_form": "WWWLLD",
        "macao_tip": "客队",
        "initial_avg": (1.93, 3.35, 3.80),
        "realtime_avg": (1.96, 3.38, 3.82),
    },
    {
        "id": "周四007",
        "home": "丹麦",
        "away": "北马其顿",
        "home_form": "LDWWWD",
        "away_form": "LDDDWL",
        "macao_tip": "和局",
        "initial_avg": (1.30, 5.10, 9.50),
        "realtime_avg": (1.27, 5.35, 10.50),
    },
]

# ============ 近况评分计算 ============

def calc_form_score(form_str):
    """
    计算近况评分
    权重：最近一场×2，其他4场×1（共6场权重）
    得分：赢=3分，平=1分，输=0分
    满分：3×2 + 3×4 = 18分
    """
    if not form_str or len(form_str) < 5:
        return 0
    
    score_map = {'W': 3, 'D': 1, 'L': 0, '赢': 3, '平': 1, '输': 0}
    chars = list(form_str.upper())
    
    # 最近一场（序列最左边）×2
    score = score_map.get(chars[0], 0) * 2
    # 其他4场×1
    for c in chars[1:5]:
        score += score_map.get(c, 0)
    
    return score

def calc_form_diff(home_form, away_form):
    """计算近况差 = 主队得分 - 客队得分"""
    home_score = calc_form_score(home_form)
    away_score = calc_form_score(away_form)
    return home_score - away_score, home_score, away_score

# ============ 置信度计算 ============

def calc_confidence(odds_h, odds_d, odds_a):
    """
    根据赔率计算置信度（使用即时赔率作为参考）
    返回：(h%, d%, a%, max%, direction)
    """
    p_h = 1.0 / odds_h
    p_d = 1.0 / odds_d
    p_a = 1.0 / odds_a
    total = p_h + p_d + p_a
    
    r_h = p_h / total * 100
    r_d = p_d / total * 100
    r_a = p_a / total * 100
    
    max_conf = max(r_h, r_d, r_a)
    if max_conf == r_h:
        direction = "主胜"
    elif max_conf == r_d:
        direction = "平局"
    else:
        direction = "客胜"
    
    return r_h, r_d, r_a, max_conf, direction

# ============ 赔率变化计算 ============

def calc_odds_change(initial, realtime):
    """计算赔率变化百分比"""
    if initial == 0:
        return 0
    return (realtime - initial) / initial * 100

# ============ 真假造热辨别 ============

def analyze_true_false_heat(change_h, change_d, change_a, macao_dir):
    """
    辨别真假造热（规律R）
    返回：(is_true_heat,分流方向,说明)
    """
    # 确定澳门心水方向的赔率变化
    if macao_dir == "主":
        macao_change = change_h
        other_changes = [change_d, change_a]
    elif macao_dir == "客":
        macao_change = change_a
        other_changes = [change_h, change_d]
    elif macao_dir == "平":
        macao_change = change_d
        other_changes = [change_h, change_a]
    else:
        return None, None, "无法判断"
    
    # 澳门心水方向是否大幅降赔（造热）
    if macao_change > -5:  # 不是造热
        return None, None, "非造热状态"
    
    # 检查其他两向是否同步降赔（分流筹码）
    分流_count = sum(1 for c in other_changes if c < -2)
    
    if 分流_count == 0:
        # 其他两向均升或微变 - 真造热（诱盘）
        return True, None, "真造热(诱盘)：筹码单向聚焦"
    else:
        # 至少一向同步降 - 假造热（实盘）
        if other_changes[0] < -2:
            分流_dir = "平" if macao_dir != "平" else "主"
        else:
            分流_dir = "客" if macao_dir != "客" else "平"
        return False, 分流_dir, "假造热(实盘)：筹码有分流出口"

# ============ 筹码分流分析(A-G七维度) ============

def analyze_chips_flow(m, h_score, a_score, form_diff):
    """
    3.28优化版筹码分流系统分析(A-G七维度)
    使用即时赔率作为当前市场真实赔率
    """
    # 使用即时赔率作为当前真实赔率（第四部分不作为依据）
    odds_h, odds_d, odds_a = m["realtime_avg"]
    init_h, init_d, init_a = m["initial_avg"]
    real_h, real_d, real_a = m["realtime_avg"]
    
    # 计算赔率变化
    change_h = calc_odds_change(init_h, real_h)
    change_d = calc_odds_change(init_d, real_d)
    change_a = calc_odds_change(init_a, real_a)
    
    # 确定澳门心水方向
    macao = m["macao_tip"]
    macao_dir = None
    if "主" in macao or m["home"] in macao:
        macao_dir = "主"
    elif "客" in macao or m["away"] in macao:
        macao_dir = "客"
    elif "和" in macao or "平" in macao:
        macao_dir = "平"
    
    # ============ A. 赔率变化状态分类 ============
    changes = [abs(change_h), abs(change_d), abs(change_a)]
    max_change = max(changes)
    
    if max_change < 0.5:
        chip_state = "全锁定"
    elif max_change < 2:
        chip_state = "单向锁定" if sum(1 for c in changes if c < 0.5) == 1 else "均衡分流"
    elif max_change < 5:
        chip_state = "均衡分流"
    elif max_change < 10:
        chip_state = "单向造热"
    else:
        chip_state = "极端造热"
    
    # 判断造热方向（赔率下降=造热）
    heat_dir = None
    if change_h < -5:
        heat_dir = "主"
    elif change_a < -5:
        heat_dir = "客"
    elif change_d < -5:
        heat_dir = "平"
    
    # ============ B. 澳门心水联动规则 ============
    # 澳门推 = 赔率造热同向？
    omen_match = False
    if macao_dir and heat_dir:
        omen_match = (macao_dir == heat_dir)
    
    # ============ C. 赔率绝对值赔付压力规则 ============
    # 使用即时赔率找出赔率最低的方向（赔付压力最小）
    min_odds = min(odds_h, odds_d, odds_a)
    if min_odds == odds_h:
        min_odds_dir = "主"
    elif min_odds == odds_d:
        min_odds_dir = "平"
    else:
        min_odds_dir = "客"
    
    # 高赔方向(>3.5)
    high_odds_dirs = []
    if odds_h > 3.5:
        high_odds_dirs.append("主")
    if odds_d > 3.5:
        high_odds_dirs.append("平")
    if odds_a > 3.5:
        high_odds_dirs.append("客")
    
    # ============ D. 近况差与赔率可动空间规则 ============
    if abs(form_diff) >= 8:
        form_move_space = "极小(<2%)"
    elif abs(form_diff) >= 4:
        form_move_space = "中(2-5%)"
    else:
        form_move_space = "大(>5%)"
    
    # ============ E. 筹码完全聚焦判断 ============
    # 三者同时指向同一方向：澳门心水 + 赔率造热 + 近况支持
    triple_focus = False
    if macao_dir and heat_dir:
        if macao_dir == heat_dir:
            if (form_diff >= 5 and macao_dir == "主") or (form_diff <= -5 and macao_dir == "客"):
                triple_focus = True
    
    # ============ F. 平赔四象限判断 ============
    ping_analysis = ""
    if macao_dir == "平":
        if abs(change_d) < 2:
            ping_analysis = "平赔不动=真方向"
        elif change_d < -5:
            ping_analysis = "平赔大降=规律二触发"
        elif change_d > 0:
            ping_analysis = "平赔上升=被推离"
        elif 3.0 <= odds_d <= 3.2:
            ping_analysis = "诱平陷阱(3.0-3.2)"
    
    # ============ H. 真假造热辨别（规律R） ============
    is_true_heat,分流_dir,heat_analysis = analyze_true_false_heat(change_h, change_d, change_a, macao_dir)
    
    # ============ G. 联动规则综合判断 ============
    prediction = ""
    reason = ""
    stability = 0  # 稳定性评分0-10
    upset_risk = 0  # 爆冷风险0-10
    
    # 获取置信度（基于即时赔率）
    conf_h, conf_d, conf_a, max_conf, conf_dir = calc_confidence(odds_h, odds_d, odds_a)
    
    # 规则应用（按优先级）
    
    # 规则R：真假造热辨别（高优先级）
    if is_true_heat == True:
        # 真造热 - 反向
        if macao_dir == "主":
            prediction = "客胜或平局"
        elif macao_dir == "客":
            prediction = "主胜或平局"
        else:
            prediction = "主胜或客胜"
        reason = "规律R：真造热(诱盘)反向"
        stability = 4
        upset_risk = 8
    elif is_true_heat == False:
        # 假造热 - 顺向（实盘打出）
        if macao_dir == "主":
            prediction = "主胜"
        elif macao_dir == "客":
            prediction = "客胜"
        else:
            prediction = "平局"
        reason = f"规律R：假造热(实盘)顺向，筹码分流至{分流_dir}"
        stability = 7
        upset_risk = 3
    
    # 规则五：主胜升幅>5% → 和局
    elif change_h > 5:
        prediction = "平局"
        reason = "规则五：主胜升幅>5%"
        stability = 6
        upset_risk = 4
    
    # 规则N：规律五+极端造热客队 → 反向主胜
    elif change_h > 5 and change_a < -10 and macao_dir == "客":
        prediction = "主胜"
        reason = "规律N：规律五+极端造热客队+澳门推客"
        stability = 5
        upset_risk = 7
    
    # 规则O：近况差+8以上+赔率微变<2% → 主队打出
    elif form_diff >= 8 and max_change < 2:
        prediction = "主胜"
        reason = "规律O：近况差+8以上+赔率微变"
        stability = 7
        upset_risk = 3
    
    # 规则H：置信度≥66%+赔率变化均<5%+澳门推非主方向 → 按置信度方向
    elif max_conf >= 66 and max_change < 5 and macao_dir != "主":
        prediction = conf_dir
        reason = "规律H：高置信度+赔率稳定"
        stability = 8
        upset_risk = 2
    
    # 规则一：置信度≥66% → 可信打出
    elif max_conf >= 66:
        prediction = conf_dir
        reason = "规律一：置信度≥66%"
        stability = 7
        upset_risk = 3
    
    # 全锁定状态特殊处理
    elif chip_state == "全锁定":
        # 按赔率绝对值最低方向
        prediction = {"主": "主胜", "平": "平局", "客": "客胜"}[min_odds_dir]
        if macao_dir == min_odds_dir:
            reason = "全锁定+澳门同向+赔率最低"
            stability = 8
            upset_risk = 2
        else:
            reason = "全锁定+赔率最低(澳门不同向)"
            stability = 6
            upset_risk = 4
    
    # 筹码聚焦反向
    elif triple_focus:
        # 三重聚焦，反向
        if macao_dir == "主":
            prediction = "客胜"
        elif macao_dir == "客":
            prediction = "主胜"
        else:
            prediction = "平局"
        reason = "规律E：三重聚焦反向"
        stability = 4
        upset_risk = 8
    
    # 澳门推+赔率造热同向
    elif omen_match:
        # 双重聚焦，反向信号
        if macao_dir == "主":
            prediction = "客胜或平局"
        elif macao_dir == "客":
            prediction = "主胜或平局"
        else:
            prediction = "主胜或客胜"
        reason = "澳门推+赔率造热同向=反向"
        stability = 4
        upset_risk = 7
    
    # 默认按置信度
    else:
        prediction = conf_dir
        reason = "按置信度方向"
        stability = 5
        upset_risk = 5
    
    return {
        "chip_state": chip_state,
        "heat_dir": heat_dir,
        "omen_dir": macao_dir,
        "min_odds_dir": min_odds_dir,
        "high_odds_dirs": high_odds_dirs,
        "form_move_space": form_move_space,
        "triple_focus": triple_focus,
        "ping_analysis": ping_analysis,
        "is_true_heat": is_true_heat,
        "分流_dir": 分流_dir,
        "heat_analysis": heat_analysis,
        "prediction": prediction,
        "reason": reason,
        "stability": stability,
        "upset_risk": upset_risk,
        "change_h": change_h,
        "change_d": change_d,
        "change_a": change_a,
        "conf": max_conf,
        "conf_dir": conf_dir,
        "odds_h": odds_h,
        "odds_d": odds_d,
        "odds_a": odds_a,
    }

# ============ 主程序 ============

def main():
    print("=" * 80)
    print("3.25比赛数据分析 - 3.28优化版筹码分流系统(A-G七维度)")
    print("更新：仅使用初盘和即时赔率(30家公司)，第四部分不作为依据")
    print("=" * 80)
    
    results = []
    
    for m in matches_data:
        # 计算近况差
        form_diff, h_score, a_score = calc_form_diff(m["home_form"], m["away_form"])
        
        # 筹码分流分析
        analysis = analyze_chips_flow(m, h_score, a_score, form_diff)
        
        results.append({
            "match": m,
            "form_diff": form_diff,
            "h_score": h_score,
            "a_score": a_score,
            "conf": analysis["conf"],
            "conf_dir": analysis["conf_dir"],
            "analysis": analysis,
        })
    
    # 输出近况差复核
    print("\n" + "=" * 80)
    print("【近况差计算复核】")
    print("=" * 80)
    print(f"{'编号':<10}{'对阵':<25}{'主队近况':<10}{'客队近况':<10}{'主队分':<8}{'客队分':<8}{'近况差':<8}")
    print("-" * 80)
    for r in results:
        m = r["match"]
        print(f"{m['id']:<10}{m['home']} vs {m['away']:<15}{m['home_form']:<10}{m['away_form']:<10}{r['h_score']:<8}{r['a_score']:<8}{r['form_diff']:+d}")
    
    # 输出筹码分流分析
    print("\n" + "=" * 80)
    print("【筹码分流分析(A-G七维度)】")
    print("=" * 80)
    
    for r in results:
        m = r["match"]
        a = r["analysis"]
        print(f"\n{m['id']} {m['home']} vs {m['away']}")
        print("-" * 60)
        print(f"  A.筹码状态: {a['chip_state']}")
        print(f"  B.澳门心水: {a['omen_dir']} | 造热方向: {a['heat_dir']} | 同向: {'是' if a['omen_dir'] == a['heat_dir'] else '否'}")
        print(f"  C.赔率最低: {a['min_odds_dir']} (主{a['odds_h']:.2f}/平{a['odds_d']:.2f}/客{a['odds_a']:.2f})")
        print(f"  D.近况差: {r['form_diff']:+d} | 可动空间: {a['form_move_space']}")
        print(f"  E.三重聚焦: {'是(反向信号)' if a['triple_focus'] else '否'}")
        print(f"  F.平赔分析: {a['ping_analysis'] if a['ping_analysis'] else '无'}")
        print(f"  H.真假造热: {a['heat_analysis']}")
        print(f"  G.赔率变化: 主{a['change_h']:+.1f}% 平{a['change_d']:+.1f}% 客{a['change_a']:+.1f}%")
        print(f"  置信度: {r['conf']:.1f}% ({r['conf_dir']})")
        print(f"  >> 预测: {a['prediction']} | 依据: {a['reason']}")
        print(f"  >> 稳定性: {a['stability']}/10 | 爆冷风险: {a['upset_risk']}/10")
    
    # 输出标准格式表格
    print("\n" + "=" * 80)
    print("【完整数据列表（标准格式）】")
    print("=" * 80)
    print(f"{'| 编号 | 对阵 | 置信度 | 澳门心水 | 近况差 | 初盘(胜/平/负) | 即时(胜/平/负) | 变化(H/D/A) | 最终预测 |':<120}")
    print("-" * 120)
    
    for r in results:
        m = r["match"]
        a = r["analysis"]
        init = m["initial_avg"]
        real = m["realtime_avg"]
        
        init_str = f"{init[0]:.2f}/{init[1]:.2f}/{init[2]:.2f}"
        real_str = f"{real[0]:.2f}/{real[1]:.2f}/{real[2]:.2f}"
        change_str = f"主{a['change_h']:+.1f}% 平{a['change_d']:+.1f}% 客{a['change_a']:+.1f}%"
        
        print(f"| {m['id']} | {m['home']} vs {m['away']} | {r['conf']:.1f}% | {m['macao_tip']} | {r['form_diff']:+d} | {init_str} | {real_str} | {change_str} | {a['prediction']} |")
    
    # 稳胆推荐
    print("\n" + "=" * 80)
    print("【最稳比赛推荐(稳胆)】")
    print("=" * 80)
    stable_matches = [(r, r["analysis"]["stability"]) for r in results if r["analysis"]["stability"] >= 7]
    stable_matches.sort(key=lambda x: x[1], reverse=True)
    
    for i, (r, s) in enumerate(stable_matches[:5], 1):
        m = r["match"]
        a = r["analysis"]
        print(f"{i}. {m['id']} {m['home']} vs {m['away']} -> {a['prediction']}")
        print(f"   稳定性: {s}/10 | 依据: {a['reason']}")
        print(f"   置信度: {r['conf']:.1f}% | 近况差: {r['form_diff']:+d}")
        print(f"   即时赔率: 主{a['odds_h']:.2f} 平{a['odds_d']:.2f} 客{a['odds_a']:.2f}")
        print()
    
    # 爆冷预警
    print("\n" + "=" * 80)
    print("【最可能爆冷的比赛】")
    print("=" * 80)
    upset_matches = [(r, r["analysis"]["upset_risk"]) for r in results if r["analysis"]["upset_risk"] >= 6]
    upset_matches.sort(key=lambda x: x[1], reverse=True)
    
    for i, (r, risk) in enumerate(upset_matches[:5], 1):
        m = r["match"]
        a = r["analysis"]
        print(f"{i}. {m['id']} {m['home']} vs {m['away']}")
        print(f"   爆冷风险: {risk}/10 | 当前预测: {a['prediction']}")
        print(f"   风险依据: {a['reason']}")
        print(f"   澳门心水: {m['macao_tip']} | 赔率造热: {a['heat_dir']}")
        print(f"   即时赔率: 主{a['odds_h']:.2f} 平{a['odds_d']:.2f} 客{a['odds_a']:.2f}")
        print()
    
    # 分歧场次
    print("\n" + "=" * 80)
    print("【分歧场次警示(澳门心水≠赔率最低方向)】")
    print("=" * 80)
    for r in results:
        m = r["match"]
        a = r["analysis"]
        # 判断分歧：澳门心水方向 vs 赔率最低方向
        if a["omen_dir"] and a["min_odds_dir"] and a["omen_dir"] != a["min_odds_dir"]:
            print(f"- {m['id']} {m['home']} vs {m['away']}")
            print(f"  澳门推: {a['omen_dir']} | 赔率最低: {a['min_odds_dir']} | 预测: {a['prediction']}")
            print(f"  即时赔率: 主{a['odds_h']:.2f} 平{a['odds_d']:.2f} 客{a['odds_a']:.2f}")
            print()

if __name__ == "__main__":
    main()
