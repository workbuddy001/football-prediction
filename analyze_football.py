"""
3.21比赛 - 加入近况评分的分析脚本
新增功能：球队近况评分系统
- 最近一场权重2，其他权重1
- 赢=3分，平=1分，输=0分
"""

import os
import re
import glob
import json

DATA_DIR = "d:/work/workbuddy/足球预测/分析模板"
JSON_FILE = f"{DATA_DIR}/matches_full_2026-03-21.json"

def load_match_data():
    """从JSON文件加载比赛数据"""
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def calculate_form_score(trend):
    """
    计算近况评分
    评分规则：最近一场权重2，其他权重1
    得分：赢=3分，平=1分，输=0分
    
    trend: 走势字符串，如 "DDLDLL" (D=平,L=负,W=胜)
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
    # 标准化到0-100分（满分是3*2 + 3*1 + 3*1 + 3*1 + 3*1 = 15分）
    normalized_score = total_score / 15 * 100 if scores else None
    
    return total_score, normalized_score

def extract_trend_from_json(match_id, match_data):
    """从JSON数据提取近况走势"""
    for m in match_data:
        if m.get("编号") == match_id:
            home_trend = m.get("数据分析", {}).get("主队近况走势", "")
            away_trend = m.get("数据分析", {}).get("客队近况走势", "")
            return home_trend, away_trend
    return "", ""

def analyze_form_vs_odds(home_trend, away_trend, odds_change):
    """
    分析近况与赔率变化的关系
    
    返回: (分析结果, 近况差值, 建议)
    
    odds_change: {"home": 变化百分比, "draw": ..., "away": ...}
    """
    home_score, home_norm = calculate_form_score(home_trend)
    away_score, away_norm = calculate_form_score(away_trend)
    
    if home_score is None or away_score is None:
        return "无近况数据", 0, "按原算法"
    
    # 近况差值
    score_diff = home_score - away_score  # 正值=主队近况更好
    
    # 分析近况与赔率关系
    analysis = []
    advice = "按原算法"
    
    # 主队近况更好
    if score_diff >= 6:  # 主队明显更好
        if odds_change.get("home", 0) < -2:  # 主胜降赔
            analysis.append("[OK]近况支持+赔率合理降水")
            advice = "维持原预测"
        elif odds_change.get("home", 0) > 2:  # 主胜升赔
            analysis.append("[!]近况支持但赔率反向上升")
            advice = "庄家不惧主胜打出，防冷"
        else:  # 主胜不变
            analysis.append("[!]近况支持+赔率不变")
            advice = "庄家不调整，高压区"

    # 客队近况更好
    elif score_diff <= -6:  # 客队明显更好
        if odds_change.get("away", 0) < -2:  # 客胜降赔
            analysis.append("[OK]近况支持+赔率合理降水")
            advice = "维持原预测"
        elif odds_change.get("away", 0) > 2:  # 客胜升赔
            analysis.append("[!]近况支持但赔率反向上升")
            advice = "庄家不惧客胜打出，防冷"
        else:
            analysis.append("[!]近况支持+赔率不变")
            advice = "庄家不调整，高压区"
    
    # 近况接近
    else:
        analysis.append("双方近况接近")
        advice = "按原算法"
    
    return " | ".join(analysis), score_diff, advice


def extract_jingcai_odds(match_id, match_data):
    """从JSON数据提取竞彩赔率"""
    for m in match_data:
        if m.get("编号") == match_id:
            ou = m.get("欧赔数据", {}).get("欧赔列表", [])
            for company in ou:
                if "竞*官*" in company.get("公司", ""):
                    try:
                        return {
                            "init_home": float(company.get("初盘胜", 0)),
                            "init_draw": float(company.get("初盘平", 0)),
                            "init_away": float(company.get("初盘负", 0)),
                            "home": float(company.get("即时胜", 0)),
                            "draw": float(company.get("即时平", 0)),
                            "away": float(company.get("即时负", 0)),
                        }
                    except:
                        pass
    return None


def extract_macao_tip(match_id, match_data):
    """从JSON数据提取澳门推荐"""
    for m in match_data:
        if m.get("编号") == match_id:
            return m.get("数据分析", {}).get("澳门推荐", "")
    return ""


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


# 加载数据
print("加载比赛数据...")
match_data = load_match_data()

# 比赛ID列表
match_ids = [
    "周六001", "周六002", "周六003", "周六004", "周六005",
    "周六006", "周六008", "周六009", "周六010",
    "周六011", "周六012", "周六014", "周六016", "周六017", "周六018", "周六019",
    "周六021", "周六022", "周六023", "周六024", "周六025",
    "周六026", "周六027", "周六028", "周六029",
    "周日001", "周日002", "周日003", "周日004", "周日005",
    "周日006", "周日008", "周日010", "周日012", "周日017",
    "周日020", "周日027",
]

# 分析结果
results = []

print("\n" + "="*80)
print("3.21比赛 - 近况评分分析")
print("="*80)

for mid in match_ids:
    # 提取数据
    odds_data = extract_jingcai_odds(mid, match_data)
    macao = extract_macao_tip(mid, match_data)
    home_trend, away_trend = extract_trend_from_json(mid, match_data)
    
    if not odds_data:
        print(f"{mid}: 未找到竞彩数据!")
        continue
    
    home = odds_data["home"]
    draw = odds_data["draw"]
    away = odds_data["away"]
    init_home = odds_data["init_home"]
    init_draw = odds_data["init_draw"]
    init_away = odds_data["init_away"]
    
    # 计算置信度
    confidence, home_rate, draw_rate, away_rate = calculate_confidence(home, draw, away)
    
    # 计算赔率变化
    odds_change = {
        "home": fmt_change(init_home, home),
        "draw": fmt_change(init_draw, draw),
        "away": fmt_change(init_away, away)
    }
    
    # 计算近况评分
    home_score, home_norm = calculate_form_score(home_trend)
    away_score, away_norm = calculate_form_score(away_trend)
    score_diff = home_score - away_score if (home_score and away_score) else 0
    
    # 分析近况与赔率
    form_analysis, _, form_advice = analyze_form_vs_odds(home_trend, away_trend, odds_change)
    
    # 确定澳门推荐方向（通过与主队名比对，而非"主"字）
    home_team = ""
    away_team = ""
    for m in match_data:
        if m.get("编号") == mid:
            home_team = m.get("主队", "")
            away_team = m.get("客队", "")
            break
    
    if "和局" in macao or "平局" in macao:
        macao_dir = "和局"
    elif home_team and home_team in macao:
        macao_dir = "主队"
    elif away_team and away_team in macao:
        macao_dir = "客队"
    else:
        # 兜底：原来的"主"字判断
        macao_dir = "和局" if "和局" in macao else ("主队" if "主" in macao else "客队")
    
    # 原始预测
    if home_rate >= draw_rate and home_rate >= away_rate:
        raw_pred = "主胜"
    elif away_rate >= home_rate and away_rate >= draw_rate:
        raw_pred = "客胜"
    else:
        raw_pred = "平局"
    
    # 获取比赛名称
    match_name = mid
    for m in match_data:
        if m.get("编号") == mid:
            match_name = f"{m.get('主队', '主队')} vs {m.get('客队', '客队')}"
            break
    
    results.append({
        "id": mid,
        "match": match_name,
        "odds": f"{home}/{draw}/{away}",
        "confidence": confidence,
        "home_trend": home_trend,
        "away_trend": away_trend,
        "home_score": home_score,
        "away_score": away_score,
        "score_diff": score_diff,
        "odds_change": odds_change,
        "form_analysis": form_analysis,
        "form_advice": form_advice,
        "macao": macao,
        "macao_dir": macao_dir,
        "raw_pred": raw_pred,
    })

# 输出分析结果
print("\n[近况评分分析结果]")
print("="*100)
print(f"{'编号':<8} {'对阵':<25} {'置信度':<6} {'主队走势':<6} {'客队走势':<6} {'主队分':<5} {'客队分':<5} {'差值':<4} {'赔变'} {'近况分析'}")
print("-"*100)

for r in results:
    home_trend = r["home_trend"][:5] if r["home_trend"] else "-"
    away_trend = r["away_trend"][:5] if r["away_trend"] else "-"
    home_score = r["home_score"] if r["home_score"] else "-"
    away_score = r["away_score"] if r["away_score"] else "-"
    score_diff = r["score_diff"] if r["score_diff"] else 0
    
    # 赔率变化摘要
    oc = r["odds_change"]
    change_str = f"H{int(oc['home'])}/D{int(oc['draw'])}/A{int(oc['away'])}"
    
    print(f"{r['id']:<8} {r['match']:<25} {r['confidence']:.1f}%  {home_trend:<6} {away_trend:<6} {str(home_score):<5} {str(away_score):<5} {score_diff:+.0f}   {change_str}  {r['form_analysis'][:30]}")

# 单选列表（加入近况分析）
print("\n" + "="*100)
print("[单选列表]")
print("="*100)

single_picks = []
for r in results:
    confidence = r["confidence"]
    macao_dir = r["macao_dir"]
    raw_pred = r["raw_pred"]
    score_diff = r["score_diff"]
    odds_change = r["odds_change"]
    form_advice = r["form_advice"]
    
    # 单选条件
    is_single = False
    
    # 条件1：澳门分胜负 + 置信度≥66%
    if macao_dir != "和局" and confidence >= 66:
        is_single = True
    
    # 条件2：澳门推平局 + 平初<3 或 平降>5%（规律二）
    # 需要获取平局数据...
    
    if is_single:
        # 近况验证 - 添加赔率变化幅度规律
        # 规律：置信度≥66%时：
        # - 赔率变化小(<2%) + 近况差大(≥5) → 大胜可能
        # - 造热幅度大(主胜降>4%或客胜降>4%) → 防冷
        # - 变化适中 → 正常小胜
        verify = ""
        
        # 提取主胜/客胜的变化幅度（取绝对值）
        home_chg = odds_change.get("home", 0)
        away_chg = odds_change.get("away", 0)
        abs_home_chg = abs(home_chg)
        abs_away_chg = abs(away_chg)
        
        # 主队方向
        if macao_dir == "主队":
            if score_diff >= 5 and abs_home_chg < 2:
                # 近况好 + 赔率变化小 → 大胜
                verify = "[OK]近况好+赔变小幅→大胜"
            elif score_diff >= 5 and home_chg > 4:
                # 近况一般 + 造热大 → 防冷
                verify = "[!]造热大→防冷"
            elif score_diff >= 6 and home_chg > 2:
                verify = "[!]近况支持但赔上升-防冷"
            elif score_diff >= 6 and home_chg < -2:
                verify = "[OK]近况+赔率双支持"
            else:
                verify = "按原算法"
        
        # 客队方向
        elif macao_dir == "客队":
            if score_diff <= -5 and abs_away_chg < 2:
                # 近况好 + 赔率变化小 → 大胜
                verify = "[OK]近况好+赔变小幅→大胜"
            elif score_diff <= -5 and away_chg > 4:
                # 近况一般 + 造热大 → 防冷
                verify = "[!]造热大→防冷"
            elif score_diff <= -6 and away_chg > 2:
                verify = "[!]近况支持但赔上升-防冷"
            elif score_diff <= -6 and away_chg < -2:
                verify = "[OK]近况+赔率双支持"
            else:
                verify = "按原算法"
        else:
            verify = "按原算法"
        
        # ============================================================
        # 庄家分散筹码核心逻辑分析
        # 原理：赔率变化的唯一目的是分散筹码，分散筹码需要条件支撑
        # 没有条件支撑的逆势变化 = 庄家在冒险 = 正路仍会打出
        # ============================================================
        def analyze_chip_dispersion(macao_dir, score_diff, home_chg, away_chg, draw_chg, confidence):
            """
            筹码流向分析：
            1. 筹码天然流向哪边？（近况+澳门决定）
            2. 庄家赔率变化是顺势还是逆势？
            3. 逆势时有没有条件支撑？
            返回：(筹码分析, 庄家行为, 最终结论)
            """
            # 判断筹码天然流向
            if macao_dir == "主队":
                natural_flow = "主队"
                key_chg = home_chg   # 主队赔率变化
            else:
                natural_flow = "客队"
                key_chg = away_chg

            # 庄家行为判断
            # 顺势：筹码流向方向，庄家降水 → 加速集中，庄家不敢降
            # 逆势：筹码流向方向，庄家升水 → 试图分散筹码

            if key_chg <= 0:
                # 降水或不变：筹码流向方向在降水
                if abs(key_chg) < 2:
                    behavior = "维稳"
                    if abs(score_diff) >= 5:
                        conclusion = "筹码无法分散，正路大胜"
                        risk = "低"
                    else:
                        conclusion = "正路小胜"
                        risk = "低"
                elif abs(key_chg) <= 4:
                    behavior = "合理降水"
                    conclusion = "正路打出"
                    risk = "低"
                else:
                    # 降水超过4%：过度造热，筹码会高度集中，庄家赌博
                    behavior = "过度降水(造热)"
                    conclusion = "筹码高度集中，庄家在赌，需有条件支撑，否则出冷"
                    risk = "高"
            else:
                # 升水：逆势，庄家试图分散筹码
                if key_chg > 4:
                    behavior = "逆势大幅升水(造热)"
                    conclusion = "庄家强行造热，需有条件支撑，否则正路仍出"
                    risk = "高"
                elif key_chg > 2:
                    behavior = "逆势小幅升水"
                    conclusion = "轻度造热，防冷但正路概率仍大"
                    risk = "中"
                else:
                    behavior = "微幅波动"
                    conclusion = "基本维稳，正路打出"
                    risk = "低"

            return natural_flow, behavior, conclusion, risk

        natural_flow, behavior, conclusion, risk = analyze_chip_dispersion(
            macao_dir, score_diff, home_chg, away_chg,
            odds_change.get("draw", 0), confidence
        )

        risk_tag = {"低": "[OK]", "中": "[!]", "高": "[!!]"}.get(risk, "")

        single_picks.append({
            "id": r["id"],
            "match": r["match"],
            "confidence": confidence,
            "macao": r["macao"],
            "pred": raw_pred,
            "verify": verify,
            "home_score": r["home_score"],
            "away_score": r["away_score"],
            "score_diff": score_diff,
            "natural_flow": natural_flow,
            "behavior": behavior,
            "conclusion": conclusion,
            "risk": risk,
            "risk_tag": risk_tag,
            "home_chg": home_chg,
            "draw_chg": odds_change.get("draw", 0),
            "away_chg": away_chg,
        })

print(f"\n{'编号':<8} {'对阵':<22} {'置信度':<6} {'澳门推荐':<12} {'预测':<4} {'近况验证':<20} {'主队分':<4} {'客队分':<4}")
print("-"*100)

for p in single_picks:
    print(f"{p['id']:<8} {p['match']:<22} {p['confidence']:.1f}%  {p['macao']:<12} {p['pred']:<4} {p['verify']:<20} {str(p['home_score']):<4} {str(p['away_score']):<4}")

print(f"\n共 {len(single_picks)} 场可单选")

# ============================================================
# 最终环节：庄家分散筹码总结分析
# ============================================================
print("\n" + "="*100)
print("【最终分析：庄家分散筹码行为判断】")
print("核心方针：赔率变化的目的是分散筹码，分散筹码需要条件支撑。没有条件支撑的逆势变化=庄家冒险=正路仍出")
print("="*100)
print(f"\n{'编号':<8} {'对阵':<22} {'近况差':<6} {'赔率变化(H/D/A)':<18} {'筹码流向':<6} {'庄家行为':<16} {'风险':<4} {'结论'}")
print("-"*100)

for p in single_picks:
    chg_str = f"H{p['home_chg']:+.1f}% D{p['draw_chg']:+.1f}% A{p['away_chg']:+.1f}%"
    diff_str = f"{p['score_diff']:+d}"
    print(f"{p['id']:<8} {p['match']:<22} {diff_str:<6} {chg_str:<18} {p['natural_flow']:<6} {p['behavior']:<16} {p['risk_tag']}{p['risk']:<3} {p['conclusion']}")

# 保存结果
output_file = "d:/work/workbuddy/足球预测/3.21_form_analysis.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("3.21比赛 - 近况评分分析结果\n")
    f.write("="*100 + "\n\n")
    f.write("评分规则：最近一场权重2，其他权重1 | 赢=3分，平=1分，输=0分\n\n")
    
    for r in results:
        f.write(f"{r['id']} {r['match']}\n")
        f.write(f"  赔率: {r['odds']} | 置信度: {r['confidence']:.1f}%\n")
        f.write(f"  主队走势: {r['home_trend']} ({r['home_score']}分) | 客队走势: {r['away_trend']} ({r['away_score']}分)\n")
        f.write(f"  近况差: {r['score_diff']:+d} | 赔率变化: {r['odds_change']}\n")
        f.write(f"  澳门: {r['macao']} | 预测: {r['raw_pred']}\n")
        f.write(f"  近况分析: {r['form_analysis']}\n")
        f.write("\n")

print(f"\n结果已保存到: {output_file}")
