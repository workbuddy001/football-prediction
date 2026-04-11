"""
足球比赛预测分析 - 纯排除法框架 Web服务
用法: python football_web.py [端口号]
默认端口: 8899
"""

import http.server
import json
import os
import re
import glob
import sys
from datetime import datetime
from urllib.parse import unquote, parse_qs

# 数据根目录
DATA_ROOT = r"D:\work\workbuddy\足球预测\分析模板"
SCORES_FILE = os.path.join(DATA_ROOT, "_scores.json")
REVIEW_DIR = os.path.join(DATA_ROOT, "_reviews")


def load_scores():
    """加载比分记录"""
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_scores(scores):
    """保存比分记录"""
    with open(SCORES_FILE, 'w', encoding='utf-8') as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)


def get_match_score(match_id):
    """获取某场比赛的比分"""
    scores = load_scores()
    return scores.get(match_id, None)


def get_result_from_score(home_score, away_score):
    """从比分判断结果"""
    if home_score is None or away_score is None:
        return None
    h, a = int(home_score), int(away_score)
    if h > a:
        return "home"
    elif h == a:
        return "draw"
    else:
        return "away"


def load_review_history():
    """加载所有复盘日志摘要"""
    reviews = []
    if os.path.exists(REVIEW_DIR):
        for fname in sorted(os.listdir(REVIEW_DIR)):
            if fname.endswith('.json'):
                try:
                    with open(os.path.join(REVIEW_DIR, fname), 'r', encoding='utf-8') as f:
                        reviews.append(json.load(f))
                except Exception:
                    pass
    # 按日期倒序
    reviews.sort(key=lambda x: x.get('review_time', ''), reverse=True)
    return reviews


def find_similar_reviews(analysis):
    """
    严格多维匹配：只返回真正有参考价值的相似案例
    
    匹配4个维度（每个维度独立评分，需多维度达标才返回）：
    
    维度1：赛事特征（权重高）
      - 同一联赛 → 15分
      - 赛事类型相同（如都是友谊赛/淘汰赛）→ 10分
    
    维度2：球队状态（权重高）
      - 同一支球队参与（主或客）→ 12分
      - 近况走势模式相似 → 8分
    
    维度3：赔率变化（核心维度）
      - 竞彩方向模式相同（如 DNN=主降其他不动）→ 15分
      - 澳门方向模式相同 → 12分
      - 变化幅度接近（±5%内）→ 6分/方向
      - 排除方向完全一致 → 20分
    
    维度4：预测结论
      - 预测结果相同 → 5分
      - 心水推荐相同 → 3分
    
    === 入选规则（AND逻辑）===
    前置硬性门槛：预测结果必须相同
    
    预测相同时，满足以下条件之一：
    A) 总分 ≥ 35（严格匹配）
    B) 同队+同排除模式（最实用的参考）
    
    否则不返回（宁可少不可错）
    """
    reviews = load_review_history()
    if not reviews:
        return []
    
    # 当前比赛的特征
    current_exclusions = set(analysis.get("exclusions", []))
    current_pred = analysis.get("final_prediction", "")
    current_home = analysis.get("home_team", "")
    current_away = analysis.get("away_team", "")
    current_league = analysis.get("league", "")
    current_warnings = analysis.get("warnings", [])
    
    # 当前赔率变化特征
    om = analysis.get("odds_matrix", {})
    jc_chg = om.get("jingcai", {}).get("change", [0, 0, 0])
    mc_chg = om.get("macao", {}).get("change", [0, 0, 0])
    
    def _chg_sign(v):
        return 'D' if v < -2 else ('U' if v > 2 else 'N')
    
    current_jc_pattern = f"{_chg_sign(jc_chg[0])}{_chg_sign(jc_chg[1])}{_chg_sign(jc_chg[2])}"
    current_mc_pattern = f"{_chg_sign(mc_chg[0])}{_chg_sign(mc_chg[1])}{_chg_sign(mc_chg[2])}"
    
    # 赛事类型提取（从联赛名推断）
    def _match_type(league):
        league_lower = league.lower()
        for kw in ['友谊', '热身赛', 'friendly']:
            if kw in league or kw in league_lower:
                return 'friendly'
        for kw in ['淘汰', '杯赛', 'cup', '附加赛', 'playoff']:
            if kw in league or kw in league_lower:
                return 'knockout'
        return 'league'
    
    current_match_type = _match_type(current_league)
    
    similar = []
    seen_matches = set()
    
    for rev in reviews:
        rid = rev.get('match_id','') + '_' + rev.get('date_folder','')
        if rid in seen_matches: continue
        
        # 历史复盘数据
        rev_exc = set(rev.get('exclusions', []))
        rev_pred = rev.get('prediction', '')
        rev_ht = rev.get('home_team', '')
        rev_at = rev.get('away_team', '')
        rev_lg = rev.get('league', '')
        rev_tip = rev.get('macao_tip', '')
        rev_hf = rev.get('home_form', '')  # 主队近况走势
        rev_af = rev.get('away_form', '')  # 客队近况走势
        
        # 复盘中的赔率指纹（新版才有，旧版为空）
        fp = rev.get('odds_fingerprint', {}) or {}
        
        # ========== 逐维度评分 ==========
        
        # --- 维度1：赛事特征 ---
        dim_league = 0
        league_reasons = []
        
        # 1a. 同联赛
        if current_league and rev_lg and current_league == rev_lg:
            dim_league += 15
            league_reasons.append(f"同联赛:{current_league}")
        else:
            # 1b. 同赛事类型
            rev_mt = _match_type(rev_lg)
            if current_match_type == rev_mt and current_match_type != 'league':
                dim_league += 10
                type_name = {'friendly':'友谊赛','knockout':'淘汰/杯赛'}.get(current_match_type, current_match_type)
                league_reasons.append(f"同类型:{type_name}")
        
        # --- 维度2：球队状态 ---
        dim_team = 0
        team_reasons = []
        
        # 2a. 同一球队
        has_same_team = False
        if current_home and (current_home == rev_ht or current_home == rev_at):
            dim_team += 12
            has_same_team = True
            team_reasons.append(f"同队:{current_home}")
        if current_away and (current_away == rev_at or current_away == rev_ht):
            if not has_same_team:  # 不重复加分
                dim_team += 12
                has_same_team = True
                team_reasons.append(f"同队:{current_away}")
        
        # 2b. 近况走势模式（简化：比较胜负平的分布）
        # 如 "胜平负胜胜" vs "胜胜平胜负" 有一定重叠
        if rev_hf and current_home and current_home == rev_ht:
            pass  # 同队时近况自然相关，不再额外加分避免重复
        elif rev_hf and rev_af:
            # 提取近况中的胜负字符做简单比较
            pass  # 近况文本比较复杂，暂时跳过
        
        # --- 维度3：赔率变化（核心！）---
        dim_odds = 0
        odds_reasons = []
        
        # 3a. 排除方向一致性（最重要！）
        exc_overlap = current_exclusions & rev_exc
        if exc_overlap:
            bonus = len(exc_overlap) * 20
            dim_odds += bonus
            exc_names = {'home':'排除主胜','draw':'排除平局','away':'排除客胜'}
            odds_reasons.append(f"{'+'.join(exc_names.get(e,e) for e in exc_overlap)}")
        
        # 3b. 竞彩变化方向模式（需要赔率指纹数据）
        rev_jc_pat = fp.get('jc_pattern', '')
        if rev_jc_pat and current_jc_pattern == rev_jc_pat:
            dim_odds += 15
            odds_reasons.append(f"竞彩变向:{current_jc_pattern}一致")
        
        # 3c. 澳门变化方向模式
        rev_mc_pat = fp.get('macao_pattern', '')
        if rev_mc_pat and current_mc_pattern == rev_mc_pat:
            dim_odds += 12
            odds_reasons.append(f"澳门变向:{current_mc_pattern}一致")
        
        # 3d. 具体变化幅度对比（±5%容差）
        if fp:
            rjc = [fp.get('jc_home_chg'), fp.get('jc_draw_chg'), fp.get('jc_away_chg')]
            close_count = 0
            for i, cur_val in enumerate(jc_chg):
                rev_val = rjc[i]
                if rev_val is not None and abs(cur_val - rev_val) < 5:
                    close_count += 1
            if close_count >= 2:
                dim_odds += 6
                odds_reasons.append(f"竞彩幅{close_count}方向接近")
            
            # 澳门变化幅度
            rmc = [fp.get('mcao_home_chg'), fp.get('mcao_draw_chg'), fp.get('mcao_away_chg')]
            mc_close = 0
            for i, cur_val in enumerate(mc_chg):
                rev_val = rmc[i]
                if rev_val is not None and abs(cur_val - rev_val) < 5:
                    mc_close += 1
            if mc_close >= 2:
                dim_odds += 6
                odds_reasons.append(f"澳门幅{mc_close}方向接近")
        
        # --- 维度4：预测结论 ---
        dim_pred = 0
        pred_reasons = []
        
        # 4a. 预测结果相同
        if current_pred and rev_pred:
            # 标准化后比较
            def _norm(p):
                p = p.replace(' ', '')
                if '主胜' in p: return '主胜'
                if '平局' in p: return '平局'
                if '客胜' in p: return '客胜'
                if '观望' in p: return '观望'
                return p
            
            if _norm(current_pred) == _norm(rev_pred):
                dim_pred += 5
                pred_reasons.append(f"同预测:{_norm(current_pred)}")
        
        # 4b. 心水推荐相同
        if rev_tip:
            current_tip = analysis.get("macao_tip", "")
            if current_tip and current_tip == rev_tip:
                dim_pred += 3
                pred_reasons.append(f"同心水:{rev_tip}")
        
        # ========== 综合评分与筛选 ==========
        total_score = dim_league + dim_team + dim_odds + dim_pred
        
        # 统计有多少维度有得分
        dims_with_score = sum(1 for d in [dim_league, dim_team, dim_odds, dim_pred] if d > 0)
        
        # 收集所有匹配原因
        all_reasons = league_reasons + team_reasons + odds_reasons + pred_reasons
        
        # === 硬性门槛：预测结果必须相同 ===
        pred_same = False
        if current_pred and rev_pred:
            def _norm(p):
                p = p.replace(' ', '')
                if '主胜' in p: return '主胜'
                if '平局' in p: return '平局'
                if '客胜' in p: return '客胜'
                if '观望' in p: return '观望'
                return p
            pred_same = (_norm(current_pred) == _norm(rev_pred))
        
        # 预测不同 → 直接跳过
        if not pred_same:
            continue
        
        # === 入选判断（严格门槛：≥35分）===
        qualified = False
        
        # 条件A：≥35分（严格匹配）
        if total_score >= 35:
            qualified = True
        
        # 条件B：同队 + 同排除模式（最实用参考，不设分数下限）
        if has_same_team and exc_overlap:
            qualified = True
        
        if qualified and total_score > 0:
            similar.append({
                "match_id": rev.get("match_id",""),
                "home_team": rev_ht,
                "away_team": rev_at,
                "league": rev_lg,
                "prediction": rev_pred,
                "confidence": rev.get("confidence",0),
                "actual_score": rev.get("actual_score",""),
                "result_cn": rev.get("result_cn",""),
                "is_correct": rev.get("is_correct", False),
                "exclusions": list(rev_exc),
                "lessons": [l for l in rev.get('lessons',[]) if l.startswith(('❌','⚠️','✅'))][:3],
                "review_time": rev.get("review_time",""),
                "macao_tip": rev.get("macao_tip", ""),
                "match_score": total_score,
                "match_reasons": all_reasons,
                # 各维度分数（用于展示）
                "dim_scores": {
                    "赛事": dim_league,
                    "球队": dim_team,
                    "赔率": dim_odds,
                    "预测": dim_pred,
                },
            })
            seen_matches.add(rid)
    
    # 按总分排序，最多返回6条
    similar.sort(key=lambda x: x['match_score'], reverse=True)
    return similar[:6]


def generate_review_log(match_id, date_folder, raw_data, analysis, home_score, away_score):
    """
    自动生成复盘日志
    对比预测结果和实际比分，总结经验教训
    """
    prediction = analysis.get("final_prediction", "")
    confidence = analysis.get("confidence", 0)
    exclusions = analysis.get("exclusions", [])
    signals = analysis.get("signals", [])
    warnings = analysis.get("warnings", [])
    
    actual_result = get_result_from_score(home_score, away_score)
    result_cn = {"home": "主胜", "draw": "平局", "away": "客胜"}.get(actual_result, "未知")
    
    # 判断预测是否命中
    pred_direction = ""
    if "主胜" in prediction:
        pred_direction = "home"
    elif "平局" in prediction:
        pred_direction = "draw"
    elif "客胜" in prediction:
        pred_direction = "away"
    else:
        pred_direction = None
    
    is_correct = (pred_direction is not None and pred_direction == actual_result)
    
    # 构建经验总结
    lessons = []
    if is_correct:
        lessons.append(f"✅ 预测{prediction}正确！实际比分为{home_score}:{away_score}({result_cn})")
        if confidence >= 4:
            lessons.append("📈 高置信度预测命中，验证了排除法的可靠性")
        if len(exclusions) >= 2:
            lessons.append(f"📈 多重排除（{'/'.join([direction_name(e) for e in exclusions])}）策略有效")
        
        # 记录命中的关键信号
        strong_signals = [s for s in signals if s.get('strength', 0) >= 4]
        if strong_signals:
            for s in strong_signals[:3]:
                lessons.append(f"📈 关键信号「{s.get('rule','')}」有效：{s.get('detail','')}")
    
    else:
        lessons.append(f"❌ 预测{prediction}错误！实际比分为{home_score}:{away_score}({result_cn})")
        if prediction == "观望":
            lessons.append("⚠️ 当时选择了观望，实际有明确结果")
        else:
            lessons.append(f"❌ 预测{prediction}但实际是{result_cn}，需要反思原因")
            
            # 分析可能失败的原因
            if warnings:
                for w in warnings:
                    lessons.append(f"⚠️ 当时已有警告「{w}」未重视")
            
            if len(exclusions) == 0:
                lessons.append("⚠️ 没有任何有效排除就做出预测，风险过高")
            
            if confidence <= 2:
                lessons.append("⚠️ 低置信度预测本就不应投注")
            
            # 检查是否有矛盾信号
            signal_types = [s.get('rule', '') for s in signals]
            if any('分歧' in s or '矛盾' in s or '不确定' in s for s in signal_types):
                lessons.append("⚠️ 存在分歧/矛盾信号时强行预测，应改为观望")
            
            # 检查心水相关
            tip = raw_data.get("macao_tip", "")
            if tip:
                lessons.append(f"📝 心水推荐为「{tip}」，可作为复盘参考")
    
    # 构建赔率变化指纹（用于后续相似匹配）
    odds_fingerprint = {
        "jc_change_dir": "",       # 竞彩变化方向：H=降主/D=平/A=降客/U=升
        "macao_change_dir": "",     # 澳门变化方向
        "jc_home_chg": round(analysis.get("odds_matrix",{}).get("jingcai",{}).get("change",[0,0,0])[0], 2),
        "jc_draw_chg": round(analysis.get("odds_matrix",{}).get("jingcai",{}).get("change",[0,0,0])[1], 2),
        "jc_away_chg": round(analysis.get("odds_matrix",{}).get("jingcai",{}).get("change",[0,0,0])[2], 2),
        "mcao_home_chg": round(analysis.get("odds_matrix",{}).get("macao",{}).get("change",[0,0,0])[0], 2),
        "mcao_draw_chg": round(analysis.get("odds_matrix",{}).get("macao",{}).get("change",[0,0,0])[1], 2),
        "mcao_away_chg": round(analysis.get("odds_matrix",{}).get("macao",{}).get("change",[0,0,0])[2], 2),
        "jc_init_odds": list(raw_data.get("initial_odds")[0]) if raw_data.get("initial_odds") and len(raw_data.get("initial_odds")) > 0 else [],
        "jc_real_odds": list(raw_data.get("realtime_odds")[0]) if raw_data.get("realtime_odds") and len(raw_data.get("realtime_odds")) > 0 else [],
        "macao_init_odds": list(raw_data.get("initial_odds")[2]) if raw_data.get("initial_odds") and len(raw_data.get("initial_odds")) > 2 else [],
        "macao_real_odds": list(raw_data.get("realtime_odds")[2]) if raw_data.get("realtime_odds") and len(raw_data.get("realtime_odds")) > 2 else [],
        # 变化方向签名：每个方向用 D(降)/U(升)/N(不动) 表示
        "jc_pattern": "",
        "macao_pattern": "",
    }
    
    # 生成方向模式签名
    def _chg_sign(v):
        if v is None: return 'N'
        return 'D' if v < -2 else ('U' if v > 2 else 'N')
    
    jc_h = odds_fingerprint["jc_home_chg"]
    jc_d = odds_fingerprint["jc_draw_chg"]  
    jc_a = odds_fingerprint["jc_away_chg"]
    mc_h = odds_fingerprint["mcao_home_chg"]
    mc_d = odds_fingerprint["mcao_draw_chg"]
    mc_a = odds_fingerprint["mcao_away_chg"]
    
    odds_fingerprint["jc_pattern"] = f"{_chg_sign(jc_h)}{_chg_sign(jc_d)}{_chg_sign(jc_a)}"
    odds_fingerprint["macao_pattern"] = f"{_chg_sign(mc_h)}{_chg_sign(mc_d)}{_chg_sign(mc_a)}"
    
    review = {
        "match_id": match_id,
        "date_folder": date_folder,
        "home_team": raw_data.get("home_team", ""),
        "away_team": raw_data.get("away_team", ""),
        "league": raw_data.get("league", ""),
        "handicap": raw_data.get("handicap", ""),
        "home_form": raw_data.get("home_form", ""),
        "away_form": raw_data.get("away_form", ""),
        "prediction": prediction,
        "confidence": confidence,
        "actual_score": f"{home_score}:{away_score}",
        "actual_result": actual_result,
        "result_cn": result_cn,
        "is_correct": is_correct,
        "exclusions": exclusions,
        "warnings": warnings,
        "key_signals": [
            {"rule": s.get('rule', ''), "detail": s.get('detail', ''), "strength": s.get('strength', 0)}
            for s in signals if s.get('strength', 0) >= 3
        ],
        "lessons": lessons,
        "review_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "macao_tip": raw_data.get("macao_tip", ""),
        # 新增：赔率变化特征（用于相似匹配）
        "odds_fingerprint": odds_fingerprint,
    }
    
    return review


def save_review_log(review):
    """保存复盘日志到文件（同比赛自动覆盖旧复盘）

    同一比赛的判定标准：home_team + away_team + league + match_time 相同
    （即同一对阵的同一类型比赛且开球时间相同）
    """
    os.makedirs(REVIEW_DIR, exist_ok=True)
    match_id = review['match_id']
    date_folder = review.get('date_folder', '')

    # 固定文件名格式：dateFolder_matchId_review.json
    if date_folder:
        filename = f"{date_folder}_{match_id}_review.json"
    else:
        filename = f"{match_id}_review.json"
    filepath = os.path.join(REVIEW_DIR, filename)

    # 覆盖模式：通过 队名+赛事+比赛时间 精确判断是否同一比赛
    home_team = review.get('home_team', '')
    away_team = review.get('away_team', '')
    league = review.get('league', '')
    match_time = review.get('match_time', '')

    for old_file in glob.glob(os.path.join(REVIEW_DIR, '*_review.json')):
        try:
            if os.path.basename(old_file) == filename:
                continue

            with open(old_file, 'r', encoding='utf-8') as f:
                old_data = json.load(f)

            old_ht = old_data.get('home_team', '')
            old_at = old_data.get('away_team', '')
            old_lg = old_data.get('league', '')
            old_mt = old_data.get('match_time', '')

            # 同一比赛：主客两队 + 赛事类型 + 开球时间 完全一致
            is_same_match = False
            if ((home_team and home_team == old_ht) or (away_team and away_team == old_ht)) and \
               ((home_team and home_team == old_at) or (away_team and away_team == old_at)):
                # 队名匹配（考虑主客场互换）+ 赛事相同 + 比赛时间相同
                if (not league or not old_lg or league == old_lg):
                    if (not match_time or not old_mt or match_time == old_mt):
                        is_same_match = True

            if is_same_match:
                os.remove(old_file)
                
        except (OSError, json.JSONDecodeError):
            pass
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(review, f, ensure_ascii=False, indent=2)
    
    return filepath


def get_available_dates():
    """获取所有可用的日期文件夹"""
    dates = []
    if not os.path.exists(DATA_ROOT):
        return dates
    
    for name in sorted(os.listdir(DATA_ROOT)):
        full_path = os.path.join(DATA_ROOT, name)
        if os.path.isdir(full_path) and not name.startswith('.'):
            # 检查是否有源数据文件
            files = glob.glob(os.path.join(full_path, "*_源数据.md"))
            if files:
                # 尝试解析日期显示名
                dates.append({
                    "folder": name,
                    "count": len(files),
                })
    return dates


def parse_source_file(filepath):
    """解析源数据文件，提取所有关键信息"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    data = {}
    
    # 基本信息
    home_match = re.search(r'主队\s*\|\s*([^\n|]+)', content)
    away_match = re.search(r'客队\s*\|\s*([^\n|]+)', content)
    time_match = re.search(r'比赛时间\s*\|\s*([^\n|]+)', content)
    league_match = re.search(r'赛事\s*\|\s*([^\n|]+)', content)
    handicap_match = re.search(r'让球\s*\|\s*([^\n|]+)', content)
    
    data["home_team"] = home_match.group(1).strip() if home_match else ""
    data["away_team"] = away_match.group(1).strip() if away_match else ""
    data["match_time"] = time_match.group(1).strip() if time_match else ""
    data["league"] = league_match.group(1).strip() if league_match else ""
    data["handicap"] = handicap_match.group(1).strip() if handicap_match else ""
    
    # 近况
    home_form_match = re.search(r'主队近况走势\s*\|\s*([^\n|]+)', content)
    away_form_match = re.search(r'客队近况走势\s*\|\s*([^\n|]+)', content)
    home_record_match = re.search(r'主队近况\s*\|([^\n|]+)', content)
    away_record_match = re.search(r'客队近况\s*\|([^\n|]+)', content)
    
    data["home_form"] = home_form_match.group(1).strip() if home_form_match else ""
    data["away_form"] = away_form_match.group(1).strip() if away_form_match else ""
    data["home_record"] = home_record_match.group(1).strip() if home_record_match else ""
    data["away_record"] = away_record_match.group(1).strip() if away_record_match else ""
    
    # 澳门推荐
    macao_tip_match = re.search(r'澳门推荐\s*\|\s*([^\n|]+)', content)
    macao_analysis_match = re.search(r'澳门分析\s*\|\s*([^\n]+?)(?:\n|$)', content)
    data["macao_tip"] = macao_tip_match.group(1).strip() if macao_tip_match else ""
    data["macao_analysis"] = macao_analysis_match.group(1).strip() if macao_analysis_match else ""
    
    # 历史交锋
    history_match = re.search(r'历史交锋\s*\|\s*([^\n|]+)', content)
    data["history"] = history_match.group(1).strip() if history_match else ""
    
    # 竞彩胜平负（让球盘）
    jc_home_match = re.search(r'主胜（[^\n|]*）\s*\|\s*([0-9.]+)', content)
    jc_draw_match = re.search(r'平局\s*\|\s*([0-9.]+)\s*\n', content)
    jc_away_match = re.search(r'客胜（[^\n|]*）\s*\|\s*([0-9.]+)', content)
    
    data["jc_home_odds"] = float(jc_home_match.group(1)) if jc_home_match else None
    data["jc_draw_odds"] = None  # 需要更精确匹配
    data["jc_away_odds"] = float(jc_away_match.group(1)) if jc_away_match else None
    
    # 更精确的竞彩赔率提取（从第四节表格）
    jc_section = re.search(
        r'## 四、竞彩胜平负.*?\n(.*?)(?:---|$)',
        content, re.DOTALL
    )
    if jc_section:
        h = re.search(r'主胜.*?\|\s*([0-9.]+)', jc_section.group(1))
        d = re.search(r'^\|\s*平局\s*\|\s*([0-9.]+)', jc_section.group(1), re.MULTILINE)
        a = re.search(r'客胜.*?\|\s*([0-9.]+)', jc_section.group(1))
        if h: data["jc_home_odds"] = float(h.group(1))
        if d: data["jc_draw_odds"] = float(d.group(1))
        if a: data["jc_away_odds"] = float(a.group(1))
    
    # 提取30家公司赔率数据
    initial_odds = extract_odds_array(content, 'initial_odds')
    realtime_odds = extract_odds_array(content, 'realtime_odds')
    
    data["initial_odds"] = initial_odds
    data["realtime_odds"] = realtime_odds
    
    return data


def extract_odds_array(content, array_name):
    """提取赔率数组"""
    match = re.search(array_name + r'\s*=\s*\[(.*?)\]', content, re.DOTALL)
    odds_list = []
    if match:
        odds_str = match.group(1)
        for line in odds_str.split('\n'):
            nums = re.findall(r'[0-9]+\.[0-9]+', line)
            if len(nums) >= 3:
                odds_list.append((float(nums[0]), float(nums[1]), float(nums[2])))
    return odds_list


def calc_pct(init_val, real_val):
    """计算变化百分比"""
    if init_val is None or real_val is None or init_val == 0:
        return 0.0
    return (real_val - init_val) / init_val * 100


def analyze_match(data):
    """
    核心分析逻辑：纯排除法框架
    返回完整的分析结果
    """
    result = {
        "exclusions": [],      # 排除记录
        "signals": [],          # 所有信号
        "final_prediction": "", # 最终预测
        "confidence": 0,        # 星级 (1-5)
        "confidence_text": "",
        "reasoning": [],        # 推理过程
        "odds_matrix": {},      # 赔率矩阵
        "stats": {},            # 统计数据
        "warnings": [],         # 警告信息
        # 以下用于历史复盘匹配
        "home_team": data.get("home_team", ""),
        "away_team": data.get("away_team", ""),
        "league": data.get("league", ""),
    }
    
    init_odds = data.get("initial_odds", [])
    real_odds = data.get("realtime_odds", [])
    
    if not init_odds or not real_odds:
        result["final_prediction"] = "无数据"
        result["confidence"] = 0
        return result
    
    # === 获取竞彩和澳门赔率 ===
    # 竞彩官方 = index 0, 澳门 = index 2
    jc_init = init_odds[0] if len(init_odds) > 0 else None
    jc_real = real_odds[0] if len(real_odds) > 0 else None
    macao_init = init_odds[2] if len(init_odds) > 2 else None
    macao_real = real_odds[2] if len(real_odds) > 2 else None
    
    if not jc_init or not jc_real:
        result["final_prediction"] = "数据不足"
        return result
    
    # 计算各方向变化百分比
    jc_h_chg = calc_pct(jc_init[0], jc_real[0])
    jc_d_chg = calc_pct(jc_init[1], jc_real[1])
    jc_a_chg = calc_pct(jc_init[2], jc_real[2])
    
    macao_h_chg = calc_pct(macao_init[0], macao_real[0]) if macao_init and macao_real else 0
    macao_d_chg = calc_pct(macao_init[1], macao_real[1]) if macao_init and macao_real else 0
    macao_a_chg = calc_pct(macao_init[2], macao_real[2]) if macao_init and macao_real else 0
    
    result["odds_matrix"] = {
        "jingcai": {
            "init": list(jc_init), "real": list(jc_real),
            "change": [round(jc_h_chg, 2), round(jc_d_chg, 2), round(jc_a_chg, 2)]
        },
        "macao": {
            "init": list(macao_init) if macao_init else [0, 0, 0],
            "real": list(macao_real) if macao_real else [0, 0, 0],
            "change": [round(macao_h_chg, 2), round(macao_d_chg, 2), round(macao_a_chg, 2)]
        }
    }
    
    # === 计算30家统计 ===
    stats = count_odds_changes(init_odds, real_odds)
    result["stats"] = stats
    
    # 当前即时赔率（用竞彩标准盘）
    current_h = jc_real[0]
    current_d = jc_real[1]
    current_a = jc_real[2]
    
    excluded = set()  # 已排除的方向 {'home', 'draw', 'away'}
    signals_detail = []
    
    # 澳门心水
    macao_tip = data.get("macao_tip", "")
    
    # ========== Step 1: 心水排除法（最高优先级） ==========
    if macao_tip:
        tip_dir = parse_macao_direction(macao_tip)
        if tip_dir and tip_dir != "unknown":
            tip_odds = get_tip_odds(tip_dir, current_h, current_d, current_a)
            
            if tip_odds >= 5.0:
                excluded.add(tip_dir)
                signals_detail.append({
                    "rule": "心水排除①",
                    "detail": f"澳门推荐'{macao_tip}'，方向赔率{tip_odds:.2f}≥5.0",
                    "action": f"排除{direction_name(tip_dir)}",
                    "strength": 5,
                })
            elif tip_odds >= 3.5:
                excluded.add(tip_dir)
                signals_detail.append({
                    "rule": "心水排除②",
                    "detail": f"澳门推荐'{macao_tip}'，方向赔率{tip_odds:.2f}≥3.5",
                    "action": f"排除{direction_name(tip_dir)}",
                    "strength": 4,
                })
            elif tip_odds >= 3.0:
                # 检查竞彩信号
                tip_jc_chg = get_tip_jc_change(tip_dir, jc_h_chg, jc_d_chg, jc_a_chg)
                if tip_jc_chg > 3:  # 推离心水
                    excluded.add(tip_dir)
                    signals_detail.append({
                        "rule": "规则B",
                        "detail": f"澳门推{direction_name(tip_dir)}+竞彩推离{tip_jc_chg:.1f}%>3%",
                        "action": f"排除{direction_name(tip_dir)}",
                        "strength": 5,
                    })
                elif abs(tip_jc_chg) <= 2:  # 规则A，降级
                    signals_detail.append({
                        "rule": "规则A（降级）",
                        "detail": f"澳门推{direction_name(tip_dir)}赔率{tip_odds:.2f}，竞彩无明显信号",
                        "action": f"可能排除{direction_name(tip_dir)}（50%命中率）",
                        "strength": 2,
                    })
                elif tip_jc_chg < -2:  # 实盘信号，不能排除
                    signals_detail.append({
                        "rule": "实盘信号",
                        "detail": f"澳门推{direction_name(tip_dir)}+竞彩造热{abs(tip_jc_chg):.1f}%",
                        "action": f"不排除{direction_name(tip_dir)}（实盘）",
                        "strength": 3,
                    })
    
    # ========== Step 2: 赔率绝对值检查 ==========
    if current_h > 5.0:
        excluded.add("home")
        signals_detail.append({
            "rule": "绝对值排除",
            "detail": f"主胜赔率{current_h:.2f}>5.0",
            "action": "排除主胜",
            "strength": 4,
        })
    elif current_h > 3.5:
        signals_detail.append({
            "rule": "绝对值参考",
            "detail": f"主胜赔率{current_h:.2f}>3.5（大概率排除，友谊赛除外）",
            "action": "倾向排除主胜",
            "strength": 3,
        })
    
    if current_d > 5.0:
        excluded.add("draw")
        signals_detail.append({
            "rule": "绝对值排除",
            "detail": f"平局赔率{current_d:.2f}>5.0",
            "action": "排除平局",
            "strength": 4,
        })
    elif current_d > 3.5:
        signals_detail.append({
            "rule": "绝对值参考",
            "detail": f"平局赔率{current_d:.2f}>3.5（大概率排除，友谊赛除外）",
            "action": "倾向排除平局",
            "strength": 3,
        })
    
    if current_a > 5.0:
        excluded.add("away")
        signals_detail.append({
            "rule": "绝对值排除",
            "detail": f"客胜赔率{current_a:.2f}>5.0",
            "action": "排除客胜",
            "strength": 4,
        })
    elif current_a > 3.5:
        signals_detail.append({
            "rule": "绝对值参考",
            "detail": f"客胜赔率{current_a:.2f}>3.5（大概率排除，友谊赛除外）",
            "action": "倾向排除客胜",
            "strength": 3,
        })
    
    if current_h < 1.5:
        signals_detail.append({
            "rule": "低赔排除",
            "detail": f"主胜赔率{current_h:.2f}<1.5，庄家高度自信",
            "action": "排除另外两方向可能性高",
            "strength": 4,
        })
    
    # ========== Step 3: 竞彩×澳门互动检查 ==========
    if macao_init and macao_real:
        # [不怕]标签检查
        for dir_name, dir_idx, jc_chg, macao_chg in [
            ("home", 0, jc_h_chg, macao_h_chg),
            ("draw", 1, jc_d_chg, macao_d_chg),
            ("away", 2, jc_a_chg, macao_a_chg),
        ]:
            dir_odds = [current_h, current_d, current_a][dir_idx]
            
            # 不怕标签：竞彩升 + 澳门不动
            if jc_chg > 1.0 and abs(macao_chg) < 0.5:
                if dir_odds >= 3.5:
                    excluded.add(dir_name)
                    signals_detail.append({
                        "rule": "[不怕]标签",
                        "detail": f"竞彩升{direction_name(dir_name)}{jc_chg:+.1f}%+澳门不动，{direction_name(dir_name)}赔率≥3.5",
                        "action": f"排除{direction_name(dir_name)}",
                        "strength": 4,
                    })
                else:
                    signals_detail.append({
                        "rule": "[不可靠的不怕]",
                        "detail": f"竞彩升{direction_name(dir_name)}+澳门不动，但{direction_name(dir_name)}赔率<3.5",
                        "action": f"不可靠排除{direction_name(dir_name)}",
                        "strength": 1,
                    })
            
            # 不跟标签：竞彩降 + 澳门不动
            if jc_chg < -1.0 and abs(macao_chg) < 0.5:
                signals_detail.append({
                    "rule": "[不跟]标签",
                    "detail": f"竞彩降{direction_name(dir_name)}{jc_chg:+.1f}%+澳门不动",
                    "action": f"{direction_name(dir_name)}造热是假象",
                    "strength": 4,
                })
        
        # 推离/造热检查
        for dir_name, dir_idx, jc_chg, macao_chg in [
            ("home", 0, jc_h_chg, macao_h_chg),
            ("draw", 1, jc_d_chg, macao_d_chg),
            ("away", 2, jc_a_chg, macao_a_chg),
        ]:
            # 推离：竞彩升>5%
            if jc_chg > 5:
                excluded.add(dir_name)
                signals_detail.append({
                    "rule": "推离排除",
                    "detail": f"竞彩{direction_name(dir_name)}升{jc_chg:+.1f}%>5%",
                    "action": f"排除{direction_name(dir_name)}",
                    "strength": 4,
                })
    
    # ========== Step 4: 30家公司共识检查 ==========
    total = stats.get("total", 30)
    
    # 主胜统计
    h_down = stats.get("home", {}).get("down", 0)
    h_up = stats.get("home", {}).get("up", 0)
    d_down = stats.get("draw", {}).get("down", 0)
    d_up = stats.get("draw", {}).get("up", 0)
    a_down = stats.get("away", {}).get("down", 0)
    a_up = stats.get("away", {}).get("up", 0)
    
    consensus_info = f"主降{h_down}升{h_up} / 平降{d_down}升{d_up} / 客降{a_down}升{a_up}"
    signals_detail.append({
        "rule": "30家公司共识",
        "detail": consensus_info,
        "action": "",
        "strength": 3,
    })
    
    # 强共识推离
    if a_up >= total * 0.85:  # 85%以上公司升客胜
        signals_detail.append({
            "rule": "强共识推离客",
            "detail": f"{a_up}/{total}家公司升客胜（>{int(total*0.85)}家阈值）",
            "action": "强烈推离客胜",
            "strength": 4,
        })
    if h_up >= total * 0.85:
        signals_detail.append({
            "rule": "强共识推离主",
            "detail": f"{h_up}/{total}家公司升主胜（>{int(total*0.85)}家阈值）",
            "action": "强烈推离主胜",
            "strength": 4,
        })
    
    # 强共识造热
    if a_down >= total * 0.85:
        signals_detail.append({
            "rule": "强共识造热客",
            "detail": f"{a_down}/{total}家公司降客胜（>{int(total*0.85)}家阈值）",
            "action": "全面造热客（需判断出口结构）",
            "strength": 4,
        })
    if h_down >= total * 0.85:
        signals_detail.append({
            "rule": "强共识造热主",
            "detail": f"{h_down}/{total}家公司降主胜（>{int(total*0.85)}家阈值）",
            "action": "全面造热主（需判断出口结构）",
            "strength": 4,
        })
    
    # ========== Step 5: 竞彩×澳门分歧检测 ==========
    if macao_init and macao_real:
        # 检测分歧
        conflicts = []
        for dir_name, jc_chg, macao_chg in [("主", jc_h_chg, macao_h_chg), ("平", jc_d_chg, macao_d_chg), ("客", jc_a_chg, macao_a_chg)]:
            if (jc_chg > 2 and macao_chg > 2) or (jc_chg < -2 and macao_chg < -2):
                pass  # 同向
            elif abs(jc_chg) > 2 and abs(macao_chg) > 2 and ((jc_chg > 0) != (macao_chg > 0)):
                conflicts.append(f"{dir_name}方向")
        
        if conflicts:
            signals_detail.append({
                "rule": "⚠️ 分歧警告",
                "detail": f"竞彩与澳门在{'/'.join(conflicts)}方向相反",
                "action": "信号降级",
                "strength": 0,
            })
            result["warnings"].append(f"竞彩×澳门在{','.join(conflicts)}方向分歧")
    
    # ========== Step 6: 综合结果 ==========
    result["signals"] = signals_detail
    result["exclusions"] = list(excluded)
    
    n_excluded = len(excluded)
    remaining = set(["home", "draw", "away"]) - excluded
    
    if n_excluded >= 2 and remaining:
        final = remaining.pop()
        result["final_prediction"] = direction_cn(final)
        result["confidence"] = 5
        result["confidence_text"] = "★★★★★ 排除2个方向"
    elif n_excluded == 1:
        remaining_dirs = list(remaining)
        if len(remaining_dirs) == 2:
            odds_remaining = {d: [current_h, current_d, current_a][['home','draw','away'].index(d)] for d in remaining_dirs}
            low_dir = min(odds_remaining.keys(), key=lambda x: odds_remaining[x])
            high_dir = max(odds_remaining.keys(), key=lambda x: odds_remaining[x])
            diff = abs(odds_remaining[low_dir] - odds_remaining[high_dir])
            
            if diff > 0.5:
                result["final_prediction"] = direction_cn(low_dir)
                result["confidence"] = 4
                result["confidence_text"] = f"★★★★ 排除1个，选低赔({odds_remaining[low_dir]:.2f})"
            else:
                result["final_prediction"] = "平局"
                result["confidence"] = 3
                result["confidence_text"] = f"★★★ 排除1个，赔率接近优先考虑平局"
        else:
            result["final_prediction"] = direction_cn(remaining_dirs[0]) if remaining_dirs else "无法判断"
            result["confidence"] = 3
    else:
        result["final_prediction"] = "观望"
        result["confidence"] = 1
        result["confidence_text"] = "★ 无法有效排除"
    
    # 构建推理过程文本
    reasoning_lines = []
    for s in signals_detail:
        if s["action"]:
            reasoning_lines.append(f"• [{s['rule']}] {s['detail']} → {s['action']}")
    result["reasoning"] = reasoning_lines
    
    return result


# ==================== 辅助函数 ====================

def count_odds_changes(initial_odds, realtime_odds):
    """统计30家公司的赔率变化"""
    stats = {
        "home": {"down": 0, "same": 0, "up": 0},
        "draw": {"down": 0, "same": 0, "up": 0},
        "away": {"down": 0, "same": 0, "up": 0},
        "total": 0,
    }
    
    for ini, real in zip(initial_odds, realtime_odds):
        stats["total"] += 1
        for i, (iv, rv) in enumerate(zip(ini, real)):
            key = ["home", "draw", "away"][i]
            pct = (rv - iv) / iv * 100 if iv != 0 else 0
            if pct < -0.5:
                stats[key]["down"] += 1
            elif pct > 0.5:
                stats[key]["up"] += 1
            else:
                stats[key]["same"] += 1
    
    return stats


def parse_macao_direction(tip_str):
    """解析澳门推荐的方向"""
    if not tip_str:
        return "unknown"
    tip_lower = tip_str.lower()
    if "主" in tip_str or "胜" in tip_str:
        return "home"
    elif "客" in tip_str:
        return "away"
    elif "和" in tip_str or "平" in tip_str or "局" in tip_str:
        return "draw"
    return "unknown"


def get_tip_odds(tip_dir, h, d, a):
    """获取澳门推荐方向的赔率"""
    if tip_dir == "home":
        return h
    elif tip_dir == "draw":
        return d
    elif tip_dir == "away":
        return a
    return 0


def get_tip_jc_change(tip_dir, jc_h, jc_d, jc_a):
    """获取澳门推荐方向的竞彩变化"""
    if tip_dir == "home":
        return jc_h
    elif tip_dir == "draw":
        return jc_d
    elif tip_dir == "away":
        return jc_a
    return 0


def direction_name(d):
    """英文方向转中文名称"""
    names = {"home": "主胜", "draw": "平局", "away": "客胜"}
    return names.get(d, d)


def direction_cn(d):
    """英文方向转中文简称"""
    names = {"home": "主胜", "draw": "平局", "away": "客胜"}
    return names.get(d, d)


# ==================== HTTP API ====================

class FootballAPIHandler(http.server.BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        """减少日志噪音"""
        pass
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))
    
    def do_POST(self):
        """处理POST请求：保存比分、生成复盘"""
        parsed = self.path.split('?')[0]
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}
        
        try:
            if parsed == '/api/score':
                # 保存比分
                match_id = data.get('match_id', '')
                date_folder = data.get('date', '')
                home_score = data.get('home_score')
                away_score = data.get('away_score')
                
                if not match_id or home_score is None or away_score is None:
                    self.send_json({"success": False, "error": "缺少必要参数"})
                    return
                
                scores = load_scores()
                key = f"{date_folder}_{match_id}" if date_folder else match_id
                scores[key] = {
                    "match_id": match_id,
                    "date": date_folder,
                    "home_score": int(home_score),
                    "away_score": int(away_score),
                    "score_str": f"{int(home_score)}:{int(away_score)}",
                    "result": get_result_from_score(home_score, away_score),
                    "record_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
                save_scores(scores)
                
                self.send_json({"success": True, "message": f"比分已记录: {int(home_score)}:{int(away_score)}", "data": scores[key]})
            
            elif parsed == '/api/review':
                # 生成复盘日志
                match_id = data.get('match_id', '')
                date_folder = data.get('date', '')
                home_score = data.get('home_score')
                away_score = data.get('away_score')
                
                if not match_id or not date_folder:
                    self.send_json({"success": False, "error": "缺少参数"})
                    return
                
                file_pattern = os.path.join(DATA_ROOT, date_folder, f"{match_id}_*_源数据.md")
                files = glob.glob(file_pattern)
                if not files:
                    self.send_json({"success": False, "error": f"未找到比赛: {match_id}"})
                    return
                
                raw_data = parse_source_file(files[0])
                analysis = analyze_match(raw_data)
                
                review = generate_review_log(
                    match_id, date_folder, raw_data, analysis,
                    home_score, away_score
                )
                filepath = save_review_log(review)
                
                self.send_json({
                    "success": True,
                    "message": "复盘日志已生成",
                    "review": review,
                    "filepath": filepath,
                })
            
            elif parsed == '/api/reviews':
                # 获取所有复盘历史
                reviews = load_review_history()
                self.send_json({"success": True, "data": reviews, "count": len(reviews)})
            
            elif parsed == '/api/reviews/related':
                # 根据队名/联赛查找相关历史复盘经验
                team = query.get('team', [''])[0]
                league = query.get('league', [''])[0]
                
                all_reviews = load_review_history()
                related = []
                seen = set()
                
                for r in all_reviews:
                    rid = r.get('match_id','') + '_' + r.get('date_folder','')
                    if rid in seen: continue
                    
                    score = 0
                    if team:
                        ht, at = r.get('home_team',''), r.get('away_team','')
                        if team == ht: score += 10
                        if team == at: score += 10
                        if team in ht: score += 5
                        if team in at: score += 5
                    if league and league in r.get('league',''): 
                        score += (8 if league == r.get('league','') else 4)
                    
                    if score > 0:
                        r['_rel'] = score
                        related.append(r)
                        seen.add(rid)
                
                related.sort(key=lambda x: x.get('_rel',0), reverse=True)
                self.send_json({"success":True,"data":[{
                    "match_id":r.get("match_id",""),"home_team":r.get("home_team",""),
                    "away_team":r.get("away_team",""),"league":r.get("league",""),
                    "prediction":r.get("prediction",""),"confidence":r.get("confidence",0),
                    "actual_score":r.get("actual_score",""),"result_cn":r.get("result_cn",""),
                    "is_correct":r.get("is_correct",False),"exclusions":r.get("exclusions",[]),
                    "lessons":[l for l in r.get("lessons",[]) if l.startswith(('❌','⚠️'))][:2],
                    "review_time":r.get("review_time",""),"_relevance":r.get("_rel",0)
                } for r in related[:8]],"count":len(related)})
            
            else:
                self.send_json({"success": False, "error": "未知接口"}, status=404)
        
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, status=500)

    def do_GET(self):
        parsed = self.path.split('?')[0]
        query = parse_qs(self.path.split('?')[1]) if '?' in self.path else {}
        
        try:
            if parsed == '/api/dates':
                dates = get_available_dates()
                self.send_json({"success": True, "data": dates})
            
            elif parsed == '/api/scores':
                # 获取所有比分记录
                scores = load_scores()
                self.send_json({"success": True, "data": scores, "count": len(scores)})
            
            elif parsed == '/api/matches':
                date_folder = query.get('date', [''])[0]
                if not date_folder:
                    self.send_json({"success": False, "error": "缺少date参数"})
                    return
                
                data_dir = os.path.join(DATA_ROOT, date_folder)
                if not os.path.exists(data_dir):
                    self.send_json({"success": False, "error": f"目录不存在: {date_folder}"})
                    return
                
                matches = []
                files = sorted(glob.glob(os.path.join(data_dir, "*_源数据.md")))
                
                # 加载比分记录
                scores = load_scores()
                
                for filepath in files:
                    fname = os.path.basename(filepath)
                    # 提取比赛ID
                    id_match = re.match(r'(周[一二三四五六日]\d+)', fname)
                    match_id = id_match.group(1) if id_match else fname.replace('_源数据.md', '')
                    
                    # 快速提取基本信息 + 跑分析
                    try:
                        raw_data = parse_source_file(filepath)
                        analysis = analyze_match(raw_data)
                        
                        # 查找比分记录
                        score_key = f"{date_folder}_{match_id}"
                        score_data = scores.get(score_key)
                        
                        matches.append({
                            "id": match_id,
                            "file": fname,
                            "home": raw_data.get("home_team", ""),
                            "away": raw_data.get("away_team", ""),
                            "league": raw_data.get("league", ""),
                            "time": raw_data.get("match_time", ""),
                            # 新增：分析结果
                            "prediction": analysis.get("final_prediction", ""),
                            "confidence": analysis.get("confidence", 0),
                            "confidence_text": analysis.get("confidence_text", ""),
                            "n_exclusions": len(analysis.get("exclusions", [])),
                            "exclusions": analysis.get("exclusions", []),
                            "warnings": analysis.get("warnings", []),
                            # 比分数据
                            "score": score_data.get("score_str") if score_data else None,
                            "home_score": score_data.get("home_score") if score_data else None,
                            "away_score": score_data.get("away_score") if score_data else None,
                            "actual_result": score_data.get("result") if score_data else None,
                            "has_review": bool(score_data),  # 有比分即可复盘
                        })
                    except Exception as e:
                        # 解析失败时只返回基本信息
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                content = f.read()
                            home_m = re.search(r'主队\s*\|\s*([^\n|]+)', content)
                            away_m = re.search(r'客队\s*\|\s*([^\n|]+)', content)
                            league_m = re.search(r'赛事\s*\|\s*([^\n|]+)', content)
                            time_m = re.search(r'比赛时间\s*\|\s*([^\n|]+)', content)
                            matches.append({
                                "id": match_id, "file": fname,
                                "home": home_m.group(1).strip() if home_m else "",
                                "away": away_m.group(1).strip() if away_m else "",
                                "league": league_m.group(1).strip() if league_m else "",
                                "time": time_m.group(1).strip() if time_m else "",
                                "prediction": "解析错误", "confidence": 0, "n_exclusions": 0,
                                "score": None, "has_review": False,
                            })
                        except Exception:
                            continue
                
                self.send_json({"success": True, "data": matches, "count": len(matches)})
            
            elif parsed == '/api/analyze':
                date_folder = query.get('date', [''])[0]
                match_id = query.get('id', [''])[0]
                
                if not date_folder or not match_id:
                    self.send_json({"success": False, "error": "缺少参数"})
                    return
                
                file_pattern = os.path.join(DATA_ROOT, date_folder, f"{match_id}_*_源数据.md")
                files = glob.glob(file_pattern)
                
                if not files:
                    self.send_json({"success": False, "error": f"未找到比赛: {match_id}"})
                    return
                
                # 解析源数据
                raw_data = parse_source_file(files[0])
                
                # 执行分析
                analysis = analyze_match(raw_data)
                
                # 查找历史复盘参考
                similar_reviews = find_similar_reviews(analysis)
                all_reviews = load_review_history()
                
                response = {
                    "success": True,
                    "raw_data": {
                        "home_team": raw_data.get("home_team", ""),
                        "away_team": raw_data.get("away_team", ""),
                        "league": raw_data.get("league", ""),
                        "match_time": raw_data.get("match_time", ""),
                        "handicap": raw_data.get("handicap", ""),
                        "home_form": raw_data.get("home_form", ""),
                        "away_form": raw_data.get("away_form", ""),
                        "home_record": raw_data.get("home_record", ""),
                        "away_record": raw_data.get("away_record", ""),
                        "history": raw_data.get("history", ""),
                        "macao_tip": raw_data.get("macao_tip", ""),
                        "macao_analysis": raw_data.get("macao_analysis", ""),
                        "jc_odds": [raw_data.get("jc_home_odds"), raw_data.get("jc_draw_odds"), raw_data.get("jc_away_odds")],
                    },
                    "analysis": analysis,
                    "similar_reviews": similar_reviews,
                    "review_count": len(all_reviews) if all_reviews else 0,
                }
                self.send_json(response)
            
            elif parsed == '/api/batch':
                date_folder = query.get('date', [''])[0]
                if not date_folder:
                    self.send_json({"success": False, "error": "缺少date参数"})
                    return
                
                data_dir = os.path.join(DATA_ROOT, date_folder)
                files = sorted(glob.glob(os.path.join(data_dir, "*_源数据.md")))
                
                results = []
                for filepath in files:
                    fname = os.path.basename(filepath)
                    id_match = re.match(r'(周[一二三四五六日]\d+)', fname)
                    match_id = id_match.group(1) if id_match else ""
                    
                    try:
                        raw_data = parse_source_file(filepath)
                        analysis = analyze_match(raw_data)
                        results.append({
                            "id": match_id,
                            "home": raw_data.get("home_team", ""),
                            "away": raw_data.get("away_team", ""),
                            "league": raw_data.get("league", ""),
                            "prediction": analysis.get("final_prediction", ""),
                            "confidence": analysis.get("confidence", 0),
                            "confidence_text": analysis.get("confidence_text", ""),
                            "n_exclusions": len(analysis.get("exclusions", [])),
                            "exclusions": analysis.get("exclusions", []),
                            "warnings": analysis.get("warnings", []),
                        })
                    except Exception as e:
                        results.append({
                            "id": match_id,
                            "prediction": "解析错误",
                            "confidence": 0,
                            "error": str(e),
                        })
                
                self.send_json({"success": True, "data": results, "count": len(results)})
            
            elif parsed == '/api/reviews':
                # 获取所有复盘历史
                reviews = load_review_history()
                self.send_json({"success": True, "data": reviews, "count": len(reviews)})
            
            elif parsed == '/api/reviews/related':
                # 根据队名/联赛查找相关历史复盘经验
                team = query.get('team', [''])[0]
                league = query.get('league', [''])[0]
                
                all_reviews = load_review_history()
                related = []
                seen = set()
                
                for r in all_reviews:
                    rid = r.get('match_id','') + '_' + r.get('date_folder','')
                    if rid in seen: continue
                    
                    score = 0
                    if team:
                        ht, at = r.get('home_team',''), r.get('away_team','')
                        if team == ht: score += 10
                        if team == at: score += 10
                        if team in ht: score += 5
                        if team in at: score += 5
                    if league and league in r.get('league',''): 
                        score += (8 if league == r.get('league','') else 4)
                    
                    if score > 0:
                        r['_rel'] = score
                        related.append(r)
                        seen.add(rid)
                
                related.sort(key=lambda x: x.get('_rel',0), reverse=True)
                self.send_json({"success":True,"data":[{
                    "match_id":r.get("match_id",""),"home_team":r.get("home_team",""),
                    "away_team":r.get("away_team",""),"league":r.get("league",""),
                    "prediction":r.get("prediction",""),"confidence":r.get("confidence",0),
                    "actual_score":r.get("actual_score",""),"result_cn":r.get("result_cn",""),
                    "is_correct":r.get("is_correct",False),"exclusions":r.get("exclusions",[]),
                    "lessons":[l for l in r.get("lessons",[]) if l.startswith(('❌','⚠️'))][:2],
                    "review_time":r.get("review_time",""),"_relevance":r.get("_rel",0)
                } for r in related[:8]],"count":len(related)})
            
            else:
                # 返回HTML主页
                self.serve_html()
        
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, status=500)
    
    def serve_html(self):
        """返回HTML页面（服务端渲染日期按钮）"""
        # 获取可用日期
        dates_data = get_available_dates()
        
        # 生成日期按钮HTML（倒序，最新在前）
        sorted_dates = sorted(dates_data, key=lambda x: x['folder'], reverse=True)
        date_buttons_html = ''
        for i, d in enumerate(sorted_dates):
            active_class = 'active' if i == 0 else ''
            first_count = sorted_dates[0]['count'] if sorted_dates else 0
            first_folder = sorted_dates[0]['folder'] if sorted_dates else ''
            date_buttons_html += f'<button class="date-btn {active_class}" onclick="selectDate(\'{d["folder"]}\', this)" title="{d["count"]}场比赛">{d["folder"]}<span class="count">({d["count"]})</span></button>'
        
        html_path = os.path.join(os.path.dirname(__file__), "football_analyzer.html")
        if os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            # 替换占位符
            html_content = html_content.replace('__DATE_BUTTONS__', date_buttons_html)
            html_content = html_content.replace('__DEFAULT_DATE__', f"{first_folder} ({first_count}场)")
        else:
            html_content = generate_html_page(date_buttons_html, first_folder, first_count)
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))


def generate_html_page(date_buttons_html='', default_date='--', default_count=0):
    """生成内嵌的HTML页面（服务端渲染日期按钮）"""
    template = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>足球预测分析器 - 纯排除法</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }

.header { background: linear-gradient(135deg, #1e293b, #334155); padding: 20px 30px; border-bottom: 1px solid #475569; }
.header h1 { font-size: 24px; background: linear-gradient(90deg, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.header p { color: #94a3b8; font-size: 13px; margin-top: 5px; }

.container { max-width: 1400px; margin: 0 auto; padding: 20px; }

.toolbar { display: flex; gap: 15px; align-items: center; flex-wrap: wrap; margin-bottom: 25px; padding: 18px; background: #1e293b; border-radius: 12px; border: 1px solid #334155; }
.toolbar select, .toolbar button { padding: 10px 18px; font-size: 14px; border-radius: 8px; border: 1px solid #475569; background: #0f172a; color: #e2e8f0; cursor: pointer; transition: all 0.2s; }
.toolbar select:hover, .toolbar button:hover { border-color: #60a5fa; background: #1e3a5f; }
.toolbar button.btn-analyze { background: linear-gradient(135deg, #3b82f6, #6366f1); color: white; font-weight: 600; border: none; padding: 11px 28px; }
.toolbar button.btn-analyze:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(59,130,246,0.4); }
.toolbar button.btn-batch { background: linear-gradient(135deg, #059669, #10b981); color: white; font-weight: 600; border: none; padding: 11px 28px; }
.toolbar button.btn-batch:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(16,185,129,0.4); }
.toolbar .info { color: #94a3b8; font-size: 13px; margin-left: auto; }

.status-bar { display: none; padding: 14px 20px; border-radius: 10px; margin-bottom: 20px; animation: fadeIn 0.3s; }
.status-bar.loading { display: block; background: #1e3a5f; border-left: 4px solid #3b82f6; }
.status-bar.error { display: block; background: #3b1a1a; border-left: 4px solid #ef4444; }
.status-bar.success { display: block; background: #1a3b1a; border-left: 4px solid #22c55e; }

@keyframes fadeIn { from { opacity: 0; transform: translateY(-5px); } to { opacity: 1; transform: translateY(0); } }

/* 表格样式 */
.table-container { overflow-x: auto; border-radius: 12px; border: 1px solid #334155; background: #1e293b; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { background: #334155; color: #cbd5e1; padding: 12px 14px; text-align: left; font-weight: 600; white-space: nowrap; position: sticky; top: 0; }
td { padding: 11px 14px; border-top: 1px solid #334155; vertical-align: middle; }
tr:hover td { background: rgba(59,130,246,0.06); }

.prediction-tag { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; white-space: nowrap; }
.tag-home { background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); }
.tag-draw { background: rgba(234,179,8,0.15); color: #facc15; border: 1px solid rgba(234,179,8,0.3); }
.tag-away { background: rgba(248,113,113,0.15); color: #fca5a5; border: 1px solid rgba(248,113,113,0.3); }
.tag-watch { background: rgba(148,163,184,0.15); color: #94a3b8; border: 1px solid rgba(148,163,184,0.3); }
.tag-error { background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }

.stars { color: #fbbf24; letter-spacing: 2px; }
.confidence-bar { height: 6px; border-radius: 3px; background: #334155; overflow: hidden; min-width: 40px; display: inline-block; vertical-align: middle; margin-right: 6px; }
.confidence-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }
.fill-5 { background: linear-gradient(90deg, #22c55e, #4ade80); }
.fill-4 { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.fill-3 { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.fill-2 { background: linear-gradient(90deg, #f97316, #fb923c); }
.fill-1 { background: #64748b; }

.exclusion-badge { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 11px; margin: 1px; background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.25); }
.warning-badge { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 11px; margin: 1px; background: rgba(245,158,11,0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.25); }

.score-display { font-weight: 700; font-size: 15px; }
.score-input { width: 36px !important; padding: 3px 4px !important; border-radius: 5px !important; border: 1px solid #475569 !important; background: #0f172a !important; color: #e2e8f0 !important; text-align: center; font-size: 12px; }
.btn-save-score { padding: 3px 8px; border-radius: 5px; border: 1px solid #22c55e; background: #0f172a; color: #22c55e; cursor: pointer; font-size: 11px; }
.btn-save-score:hover { background: rgba(34,197,94,0.1); }
.btn-review { padding: 5px 14px; border-radius: 6px; border: 1px solid #a78bfa; background: #0f172a; color: #a78bfa; cursor: pointer; font-size: 12px; }
.btn-review:hover { background: rgba(167,139,250,0.1); }

/* 日期按钮 */
.date-btn { padding: 5px 12px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #94a3b8; cursor: pointer; font-size: 12px; white-space: nowrap; transition: all 0.15s; font-weight: 500; }
.date-btn:hover { border-color: #60a5fa; background: #1e3a5f; color: #e2e8f0; transform: translateY(-1px); }
.date-btn.active { border-color: #3b82f6; background: linear-gradient(135deg, #1e40af, #3b82f6); color: #fff; box-shadow: 0 2px 8px rgba(59,130,246,0.35); }
.date-btn .count { color: rgba(148,163,184,0.7); font-size: 10px; margin-left: 3px; }
.date-btn.active .count { color: rgba(255,255,255,0.7); }

/* 复盘面板 */
.review-summary { background: linear-gradient(135deg, #1e3a5f, #1e293b); border-radius: 10px; padding: 16px; margin-bottom: 14px; }

/* 详情面板 */
.detail-panel { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.65); z-index: 1000; backdrop-filter: blur(4px); animation: fadeIn 0.2s; }
.detail-panel.show { display: flex; align-items: flex-start; justify-content: center; padding: 30px; overflow-y: auto; }
.detail-box { background: #1e293b; border-radius: 16px; border: 1px solid #475569; width: 95%; max-width: 1100px; max-height: 90vh; overflow-y: auto; padding: 28px; position: relative; }
.detail-close { position: absolute; top: 16px; right: 18px; background: none; border: none; color: #94a3b8; font-size: 26px; cursor: pointer; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
.detail-close:hover { background: #334155; color: #fff; }

.detail-header { margin-bottom: 22px; padding-bottom: 16px; border-bottom: 1px solid #334155; }
.detail-header h2 { font-size: 20px; color: #f1f5f9; }
.detail-header .meta { color: #94a3b8; font-size: 13px; margin-top: 6px; }

.section { margin-bottom: 20px; }
.section-title { font-size: 15px; font-weight: 600; color: #cbd5e1; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.section-title .icon { width: 20px; height: 20px; border-radius: 5px; display: flex; align-items: center; justify-content: center; font-size: 12px; }
.icon-blue { background: rgba(59,130,246,0.2); color: #60a5fa; }
.icon-green { background: rgba(34,197,94,0.2); color: #4ade80; }
.icon-yellow { background: rgba(234,179,8,0.2); color: #facc15; }
.icon-red { background: rgba(239,68,68,0.2); color: #f87171; }

.signal-card { padding: 10px 14px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #334155; font-size: 13px; display: flex; justify-content: space-between; align-items: center; }
.signal-card.str5 { border-color: rgba(34,197,94,0.35); background: rgba(34,197,94,0.04); }
.signal-card.str4 { border-color: rgba(59,130,246,0.35); background: rgba(59,130,246,0.04); }
.signal-card.str3 { border-color: rgba(245,158,11,0.35); background: rgba(245,158,11,0.04); }
.signal-card.str2 { border-color: rgba(156,163,175,0.35); background: rgba(156,163,175,0.04); }
.signal-card.str1 { border-color: rgba(239,68,68,0.35); background: rgba(239,68,68,0.04); }
.strength-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-left: 10px; }
.dot-5 { background: #22c55e; box-shadow: 0 0 6px rgba(34,197,94,0.5); }
.dot-4 { background: #3b82f6; box-shadow: 0 0 6px rgba(59,130,246,0.5); }
.dot-3 { background: #f59e0b; box-shadow: 0 0 6px rgba(245,158,11,0.5); }
.dot-2 { background: #94a3b8; }
.dot-1 { background: #ef4444; }
.dot-0 { background: transparent; border: 1px dashed #64748b; }

.odds-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.odds-card { background: #0f172a; border-radius: 10px; padding: 16px; border: 1px solid #334155; }
.odds-card .title { font-size: 12px; color: #94a3b8; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
.odds-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #1e293b; font-size: 14px; }
.odds-row:last-child { border: none; }
.odds-row .label { color: #94a3b8; }
.odds-row .value { font-weight: 600; font-family: "SF Mono", Consolas, monospace; }
.change-up { color: #f87171; }
.change-down { color: #4ade80; }
.change-none { color: #64748b; }

.final-result { background: linear-gradient(135deg, #1e3a5f, #1e293b); border: 1px solid rgba(96,165,250,0.3); border-radius: 12px; padding: 20px; margin-top: 18px; text-align: center; }
.final-result .pred-text { font-size: 26px; font-weight: 800; }
.final-result .conf-text { color: #94a3b8; font-size: 14px; margin-top: 8px; }

.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.stat-item { background: #0f172a; border-radius: 8px; padding: 12px; text-align: center; border: 1px solid #334155; }
.stat-label { font-size: 11px; color: #64748b; text-transform: uppercase; }
.stat-value { font-size: 18px; font-weight: 700; margin-top: 4px; font-family: "SF Mono", Consolas, monospace; }
.stat-sub { font-size: 11px; color: #64748b; margin-top: 2px; }

.empty-state { text-align: center; padding: 60px 20px; color: #64748b; }
.empty-state .emoji { font-size: 48px; margin-bottom: 16px; }

@media (max-width: 768px) {
    .container { padding: 12px; }
    .toolbar { flex-direction: column; align-items: stretch; }
    .toolbar .info { margin-left: 0; }
    .odds-grid { grid-template-columns: 1fr; }
}
</style>
</head>
<body>

<div class="header">
    <h1>⚽ 足球预测分析器 — 纯排除法框架 <span style="font-size:12px;color:#f59e0b;">[V2-按钮版]</span></h1>
    <p>基于造热原理与排除法的足球比赛赔率分析工具 | 自动读取500.com源数据</p>
</div>

<div class="container">
    <div class="toolbar" style="flex-direction:column;align-items:flex-start;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap;">
            <label style="color:#94a3b8;font-size:13px;">📅 选择日期：</label>
            <span id="selectedDate" style="color:#60a5fa;font-weight:600;font-size:14px;">__DEFAULT_DATE__</span>
        </div>
        <div id="dateButtons" style="display:flex;flex-wrap:wrap;gap:6px;max-height:120px;overflow-y:auto;padding:4px;background:#0f172a;border-radius:8px;width:100%;box-sizing:border-box;">
            __DATE_BUTTONS__
        </div>
        <div style="display:flex;gap:10px;margin-top:12px;flex-wrap:wrap;">
            <button class="btn-analyze" onclick="loadMatches()">📋 加载比赛列表</button>
            <button class="btn-batch" onclick="batchAnalyze()">🚀 一键全部分析</button>
            <span class="info" id="matchInfo">请选择日期后加载比赛</span>
        </div>
    </div>
    
    <div id="statusBar" class="status-bar"></div>
    
    <div id="resultsArea">
        <div class="empty-state">
            <div class="emoji">📊</div>
            <p>请选择上方日期文件夹，然后点击「加载比赛列表」或「一键全部分析」</p>
        </div>
    </div>
</div>

<!-- 详情面板 -->
<div class="detail-panel" id="detailPanel" onclick="if(event.target===this)closeDetail()">
    <div class="detail-box" id="detailBox">
        <button class="detail-close" onclick="closeDetail()">×</button>
        <div id="detailContent"></div>
    </div>
</div>

<script>
const API = '';

async function api(path, options = {}) {
    const res = await fetch(API + path, options);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const text = await res.text();
    try { return JSON.parse(text); } 
    catch(e) { throw new Error('非JSON响应 (' + text.substring(0, 80) + ')'); }
}

// 当前选中的日期（服务端已预填）
let currentDate = '';

// 获取当前选中日期
function getSelectedDate() {
    return currentDate;
}

// 初始化日期选择（服务端已渲染按钮，只需设置currentDate）
function initDates() {
    const activeBtn = document.querySelector('.date-btn.active');
    if (activeBtn) {
        // 按钮文本格式: "4.08(11)" -> folder="4.08"
        const btnText = activeBtn.textContent.trim();
        const match = btnText.match(/^([\d.]+)\((\d+)\)$/);
        if (match) {
            currentDate = match[1];
        } else {
            currentDate = btnText.replace(/[()]/g, '').split(' ')[0];
        }
    }
    console.log('日期初始化完成, 选中:', currentDate);
}

// 选择日期按钮
function selectDate(folder, btnEl) {
    currentDate = folder;
    // 更新按钮样式
    document.querySelectorAll('.date-btn').forEach(b => b.classList.remove('active'));
    btnEl.classList.add('active');
    // 更新显示文本
    const countMatch = folder.match(/(.+)\((\d+)\)/);
    if (btnEl.textContent) {
        document.getElementById('selectedDate').textContent = btnEl.textContent.trim();
    }
}

// 加载比赛列表
async function loadMatches() {
    const date = getSelectedDate();
    if (!date) { showStatus('请先选择日期！', 'error'); return; }
    showStatus(`正在加载 ${date} 的比赛列表...`, 'loading');
    
    const res = await api(`/api/matches?date=${encodeURIComponent(date)}`);
    if (!res.success) { showStatus(res.error, 'error'); return; }
    
    document.getElementById('matchInfo').textContent = `${date} 共 ${res.count} 场比赛`;
    
    let html = `<div class="table-container"><table>
        <thead><tr>
            <th>编号</th><th>联赛</th><th>对阵</th><th>比赛时间</th>
            <th>预测</th><th>置信度</th><th>排除</th>
            <th>比分</th>
            <th>操作</th>
        </tr></thead><tbody>`;
    
    res.data.forEach(m => {
        const predClass = (m.prediction||'').includes('主')?'tag-home':(m.prediction||'').includes('平')?'tag-draw':(m.prediction||'').includes('客')?'tag-away':'tag-watch';
        const exclStr = (m.exclusions||[]).map(e=>`<span class="exclusion-badge">${e==='home'?'主胜':e==='draw'?'平局':'客胜'}</span>`).join('');
        const fillCls = `fill-${m.confidence||1}`;
        
        // 比分显示逻辑
        let scoreHtml = '';
        if (m.score) {
            // 已有比分：显示比分 + 复盘按钮
            const resultClass = m.actual_result === 'home' ? 'color:#4ade80' : m.actual_result === 'draw' ? 'color:#facc15' : 'color:#fca5a5';
            scoreHtml = `<span style="font-weight:700;font-size:15px;${resultClass}">${m.score}</span>`;
        } else {
            // 无比分：显示输入框 + 保存按钮
            scoreHtml = `<div style="display:flex;align-items:center;gap:3px;">
                <input type="number" id="hs_${m.id}" placeholder="主" min="0" max="99" style="width:36px;padding:3px 4px;border-radius:5px;border:1px solid #475569;background:#0f172a;color:#e2e8f0;text-align:center;font-size:12px;">
                <span style="color:#64748b">:</span>
                <input type="number" id="as_${m.id}" placeholder="客" min="0" max="99" style="width:36px;padding:3px 4px;border-radius:5px;border:1px solid #475569;background:#0f172a;color:#e2e8f0;text-align:center;font-size:12px;">
                <button onclick="saveScore('${date}','${m.id}','${m.home}')" style="padding:3px 8px;border-radius:5px;border:1px solid #22c55e;background:#0f172a;color:#22c55e;cursor:pointer;font-size:11px;">✓</button>
            </div>`;
        }
        
        // 操作按钮
        let actionHtml = '';
        if (m.score) {
            // 有比分 → 显示复盘按钮
            actionHtml = `<button onclick="doReview('${date}','${m.id}')" style="padding:5px 14px;border-radius:6px;border:1px solid #a78bfa;background:#0f172a;color:#a78bfa;cursor:pointer;font-size:12px;">📝 复盘</button>`;
        }
        actionHtml += ` <button onclick="analyzeOne('${date}','${m.id}')" style="padding:5px 14px;border-radius:6px;border:1px solid #475569;background:#0f172a;color:#60a5fa;cursor:pointer;font-size:12px;">🔍 分析</button>`;
        
        html += `<tr>
            <td style="font-weight:600;color:#60a5fa">${m.id}</td>
            <td>${m.league}</td>
            <td>${m.home} vs <strong>${m.away}</strong></td>
            <td style="color:#94a3b8;font-size:12px">${m.time}</td>
            <td><span class="prediction-tag ${predClass}">${m.prediction||'-'}</span></td>
            <td><div class="confidence-bar"><div class="confidence-fill ${fillCls}" style="width:${(m.confidence||0)*20}%"></div></div>
            <span class="stars">${'★'.repeat(m.confidence||0)}</span></td>
            <td style="text-align:center;font-weight:700;color:${(m.n_exclusions||0)>=2?'#4ade80':(m.n_exclusions||0)>=1?'#60a5fa':'#94a3b8'}">${m.n_exclusions||0}<br><span style="font-size:10px;font-weight:400">${exclStr||''}</span></td>
            <td>${scoreHtml}</td>
            <td style="white-space:nowrap">${actionHtml}</td>
        </tr>`;
    });
    html += '</tbody></table></div>';
    document.getElementById('resultsArea').innerHTML = html;
    showStatus(`已加载 ${res.count} 场比赛（含分析结果）`, 'success');
}

// 保存比分
async function saveScore(date, id, homeTeam) {
    const hs = document.getElementById(`hs_${id}`);
    const as = document.getElementById(`as_${id}`);
    if (!hs || !as || hs.value === '' || as.value === '') {
        showStatus('请填写完整比分！', 'error'); return;
    }
    
    showStatus(`正在记录 ${id} 比分...`, 'loading');
    try {
        const res = await api('/api/score', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ match_id: id, date: date, home_score: hs.value, away_score: as.value })
        });
        if (!res.success) { showStatus(res.error, 'error'); return; }
        showStatus(`${id} 比分已记录：${homeTeam} ${res.data.score_str}`, 'success');
        // 刷新列表以显示比分
        loadMatches();
    } catch(e) { showStatus('保存失败: ' + e.message, 'error'); }
}

// 执行复盘
async function doReview(date, id) {
    if (!confirm(`确认对 ${id} 进行复盘？将自动生成经验总结日志。`)) return;
    showStatus(`正在生成 ${id} 复盘日志...`, 'loading');
    try {
        // 先从scores获取比分
        const scoresRes = await api('/api/scores');
        const scoreKey = date + '_' + id;
        const scoreData = (scoresRes.data || {})[scoreKey];
        
        if (!scoreData) {
            showStatus('未找到该场比赛的比分记录，请先填写比分', 'error'); return;
        }
        
        // 调用复盘API
        const res = await api_post('/api/review', { 
            match_id: id, 
            date: date,
            home_score: scoreData.home_score,
            away_score: scoreData.away_score
        });
        if (!res.success) { showStatus(res.error, 'error'); return; }
        
        const rev = res.review;
        alert(
            `📊 复盘报告：${rev.home_team} vs ${rev.away_team}\n` +
            `━━━━━━━━━━━━━━━━\n` +
            `📋 预测：${rev.prediction} (${rev.confidence}★)\n` +
            `🎯 实际：${rev.actual_score} (${rev.result_cn})\n` +
            `${rev.is_correct ? '✅ 命中！' : '❌ 未命中'}\n` +
            `━━━━━━━━━━━━━━━━\n\n` +
            rev.lessons.join('\n') + '\n\n' +
            `✅ 复盘日志已保存到文件`
        );
        showStatus(`${id} 复盘完成！${rev.is_correct?'命中':'未命中'}`, 'success');
    } catch(e) { showStatus('复盘失败: ' + e.message, 'error'); }
}

// POST请求辅助
async function api_post(path, data) {
    const res = await fetch(API + path, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    return res.json();
}

// 单场详细分析
async function analyzeOne(date, id) {
    showStatus(`正在分析 ${id}...`, 'loading');
    const res = await api(`/api/analyze?date=${encodeURIComponent(date)}&id=${encodeURIComponent(id)}`);
    if (!res.success) { showStatus(res.error, 'error'); return; }
    
    renderDetail(res);
    showStatus(`${id} 分析完成`, 'success');
}

// 批量分析全部
async function batchAnalyze() {
    const date = getSelectedDate();
    if (!date) { showStatus('请先选择日期！', 'error'); return; }
    showStatus(`正在批量分析 ${date} 全部比赛...`, 'loading');
    
    const res = await api(`/api/batch?date=${encodeURIComponent(date)}`);
    if (!res.success) { showStatus(res.error, 'error'); return; }
    
    document.getElementById('matchInfo').textContent = `${date} 分析完成 (${res.count}场)`;
    
    // 统计
    let homeCount=0, drawCount=0, awayCount=0, watchCount=0;
    res.data.forEach(d => {
        if (d.prediction.includes('主')) homeCount++;
        else if (d.prediction.includes('平')) drawCount++;
        else if (d.prediction.includes('客')) awayCount++;
        else watchCount++;
    });
    
    let html = `<div style="margin-bottom:16px;display:flex;gap:12px;flex-wrap:wrap;">
        <div style="background:#1e293b;padding:10px 18px;border-radius:8px;border:1px solid #334155;font-size:13px;">
            📊 总计：<strong style="color:#fff">${res.count}</strong>场 |
            <span style="color:#4ade80">主${homeCount}</span> /
            <span style="color:#facc15">平${drawCount}</span> /
            <span style="color:#fca5a5">客${awayCount}</span> /
            <span style="color:#94a3b8">观望${watchCount}</span>
        </div>
    </div>`;
    
    html += `<div class="table-container"><table>
        <thead><tr>
            <th>编号</th><th>联赛</th><th>对阵</th>
            <th>预测</th><th>置信度</th><th>排除数</th><th>排除方向</th><th>警告</th>
            <th>详情</th>
        </tr></thead><tbody>`;
    
    res.data.forEach(d => {
        const predClass = d.prediction.includes('主')?'tag-home':d.prediction.includes('平')?'tag-draw':d.prediction.includes('客')?'tag-away':'tag-watch';
        const exclStr = (d.exclusions||[]).map(e=>`<span class="exclusion-badge">${e==='home'?'主胜':e==='draw'?'平局':'客胜'}</span>`).join('');
        const warnStr = (d.warnings||[]).map(w=>`<span class="warning-badge">⚠️${w}</span>`).join('');
        
        const fillCls = `fill-${d.confidence||1}`;
        html += `<tr>
            <td style="font-weight:600;color:#60a5fa">${d.id}</td>
            <td>${d.league}</td>
            <td>${d.home} vs <strong>${d.away}</strong></td>
            <td><span class="prediction-tag ${predClass}">${d.prediction}</span></td>
            <td><div class="confidence-bar"><div class="confidence-fill ${fillCls}" style="width:${(d.confidence||0)*20}%"></div></div>
            <span class="stars">${'★'.repeat(d.confidence||0)}</span></td>
            <td style="text-align:center;font-weight:700;color:${d.n_exclusions>=2?'#4ade80':d.n_exclusions>=1?'#60a5fa':'#94a3b8'}">${d.n_exclusions}</td>
            <td>${exclStr||'-'}</td>
            <td>${warnStr||'-'}</td>
            <td><button onclick="analyzeOne('${date}','${d.id}')" style="padding:4px 12px;border-radius:6px;border:1px solid #475569;background:#0f172a;color:#94a3b8;cursor:pointer;font-size:12px;">查看</button></td>
        </tr>`;
    });
    html += '</tbody></table></div>';
    document.getElementById('resultsArea').innerHTML = html;
    showStatus(`${res.count} 场分析完成`, 'success');
}

// 渲染详情面板
function renderDetail(res) {
    const rd = res.raw_data;
    const an = res.analysis;
    
    const om = an.odds_matrix || {};
    const jm = om.jingcai || {};
    const mm = om.macao || {};
    const st = an.stats || {};
    
    let html = `
    <div class="detail-header">
        <h2>${rd.home_team || '?'} vs ${rd.away_team || '?'}</h2>
        <div class="meta">
            📌 ${rd.id || ''} &nbsp;|&nbsp; ⚽ ${rd.league || ''} &nbsp;|&nbsp; 🕐 ${rd.match_time || ''}
            &nbsp;|&nbsp; 让球: ${rd.handicap || '-'}
        </div>
    </div>
    
    <!-- 最终结论 -->
    <div class="final-result">
        <div class="pred-text" style="${an.final_prediction&&an.final_prediction.includes('主')?'color:#4ade80':an.final_prediction&&an.final_prediction.includes('平')?'color:#facc15':an.final_prediction&&an.final_prediction.includes('客')?'color:#fca5a5':'color:#94a3b8'}">
            ${an.final_prediction || '-'}
        </div>
        <div class="conf-text">${an.confidence_text || ''}</div>
    </div>`;
    
    // 基本面信息
    html += `
    <div class="section">
        <div class="section-title"><span class="icon icon-blue">ℹ️</span> 基本面信息</div>
        <div class="odds-grid">
            <div class="odds-card">
                <div class="title">主队近况</div>
                <div class="odds-row"><span class="label">走势</span><span class="value">${rd.home_form || '-'}</span></div>
                <div class="odds-row"><span class="label">战绩</span><span class="value">${rd.home_record || '-'}</span></div>
            </div>
            <div class="odds-card">
                <div class="title">客队近况</div>
                <div class="odds-row"><span class="label">走势</span><span class="value">${rd.away_form || '-'}</span></div>
                <div class="odds-row"><span class="label">战绩</span><span class="value">${rd.away_record || '-'}</span></div>
            </div>
            <div class="odds-card">
                <div class="title">澳门推荐 & 历史</div>
                <div class="odds-row"><span class="label">心水</span><span class="value" style="color:#facc15">${rd.macao_tip || '-'}</span></div>
                <div class="odds-row"><span class="label">交锋</span><span class="value">${rd.history || '-'}</span></div>
            </div>
        </div>
    </div>`;
    
    // 赔率矩阵
    html += `
    <div class="section">
        <div class="section-title"><span class="icon icon-green">💰</span> 赔率矩阵（标准1X2）</div>
        <div class="odds-grid">
            <div class="odds-card">
                <div class="title">🇨🇳 竞彩官方</div>
                <div class="odds-row"><span class="label">主胜</span><span class="value">${jm.init?jm.init[0].toFixed(2):'-'} → ${jm.real?jm.real[0].toFixed(2):'-'}</span><span class="${(jm.change||[])[0]>0?'change-up':(jm.change||[])[0]<0?'change-down':'change-none'}">${((jm.change||[])[0]||0).toFixed(1)>0?'+':''}${((jm.change||[])[0]||0).toFixed(1)}%</span></div>
                <div class="odds-row"><span class="label">平局</span><span class="value">${jm.init?jm.init[1].toFixed(2):'-'} → ${jm.real?jm.real[1].toFixed(2):'-'}</span><span class="${(jm.change||[])[1]>0?'change-up':(jm.change||[])[1]<0?'change-down':'change-none'}">${((jm.change||[])[1]||0).toFixed(1)>0?'+':''}${((jm.change||[])[1]||0).toFixed(1)}%</span></div>
                <div class="odds-row"><span class="label">客胜</span><span class="value">${jm.init?jm.init[2].toFixed(2):'-'} → ${jm.real?jm.real[2].toFixed(2):'-'}</span><span class="${(jm.change||[])[2]>0?'change-up':(jm.change||[])[2]<0?'change-down':'change-none'}">${((jm.change||[])[2]||0).toFixed(1)>0?'+':''}${((jm.change||[])[2]||0).toFixed(1)}%</span></div>
            </div>
            <div class="odds-card">
                <div class="title">🇲🇴 澳门</div>
                <div class="odds-row"><span class="label">主胜</span><span class="value">${mm.init?mm.init[0].toFixed(2):'-'} → ${mm.real?mm.real[0].toFixed(2):'-'}</span><span class="${(mm.change||[])[0]>0?'change-up':(mm.change||[])[0]<0?'change-down':'change-none'}">${((mm.change||[])[0]||0).toFixed(1)>0?'+':''}${((mm.change||[])[0]||0).toFixed(1)}%</span></div>
                <div class="odds-row"><span class="label">平局</span><span class="value">${mm.init?mm.init[1].toFixed(2):'-'} → ${mm.real?mm.real[1].toFixed(2):'-'}</span><span class="${(mm.change||[])[1]>0?'change-up':(mm.change||[])[1]<0?'change-down':'change-none'}">${((mm.change||[])[1]||0).toFixed(1)>0?'+':''}${((mm.change||[])[1]||0).toFixed(1)}%</span></div>
                <div class="odds-row"><span class="label">客胜</span><span class="value">${mm.init?mm.init[2].toFixed(2):'-'} → ${mm.real?mm.real[2].toFixed(2):'-'}</span><span class="${(mm.change||[])[2]>0?'change-up':(mm.change||[])[2]<0?'change-down':'change-none'}">${((mm.change||[])[2]||0).toFixed(1)>0?'+':''}${((mm.change||[])[2]||0).toFixed(1)}%</span></div>
            </div>
        </div>`;
    
    // 30家公司统计
    if (st.total) {
        html += `
        <div style="margin-top:14px">
            <div class="section-title" style="margin-bottom:10px">📊 30家公司赔率变化统计</div>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-label">主胜</div>
                    <div class="stat-value">${st.home?st.home.down:0}<span style="font-size:12px;color:#4ade80">↓</span> / ${st.home?st.home.same:0}= / ${st.home?st.home.up:0}<span style="font-size:12px;color:#f87171">↑</span></div>
                    <div class="stat-sub">共 ${st.total} 家</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">平局</div>
                    <div class="stat-value">${st.draw?st.draw.down:0}<span style="font-size:12px;color:#4ade80">↓</span> / ${st.draw?st.draw.same:0}= / ${st.draw?st.draw.up:0}<span style="font-size:12px;color:#f87171">↑</span></div>
                    <div class="stat-sub">共 ${st.total} 家</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">客胜</div>
                    <div class="stat-value">${st.away?st.away.down:0}<span style="font-size:12px;color:#4ade80">↓</span> / ${st.away?st.away.same:0}= / ${st.away?st.away.up:0}<span style="font-size:12px;color:#f87171">↑</span></div>
                    <div class="stat-sub">共 ${st.total} 家</div>
                </div>
            </div>
        </div>`;
    }
    
    html += '</div>'; // end section
    
    // 信号列表
    if (an.signals && an.signals.length > 0) {
        html += `
        <div class="section">
            <div class="section-title"><span class="icon icon-yellow">🔍</span> 排除法信号分析 (${an.signals.length}条)</div>`;
        an.signals.forEach(s => {
            const strCls = `str${s.strength||0}`;
            const dotCls = `dot-${s.strength||0}`;
            html += `<div class="signal-card ${strCls}">
                <div>
                    <strong style="color:${s.strength>=4?'#4ade80':s.strength==3?'#fbbf24':'#94a3b8'}">${s.rule}</strong>
                    <div style="color:#94a3b8;font-size:12px;margin-top:3px">${s.detail}</div>
                    ${s.action?`<div style="color:#60a5fa;font-size:12px;margin-top:3px">→ ${s.action}</div>`:''}
                </div>
                <div class="strength-dot ${dotCls}" title="强度: ${s.strength}/5"></div>
            </div>`;
        });
        html += '</div>';
    }
    
    // 历史复盘参考
    const simReviews = res.similar_reviews || [];
    if (simReviews.length > 0) {
        // 统计命中率
        const hitCount = simReviews.filter(r => r.is_correct).length;
        const missCount = simReviews.length - hitCount;
        const hitRate = simReviews.length > 0 ? Math.round(hitCount / simReviews.length * 100) : 0;
        
        // 根据历史命中率生成建议
        let suggestion = '';
        if (missCount === simReviews.length && simReviews.length >= 2) {
            suggestion = `<div style="margin-top:10px;padding:10px 14px;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:8px">
                <span style="color:#f87171;font-weight:bold">⚠️ 历史警示：${simReviews.length}条相似案例全部预测失败！</span>
                <div style="color:#fca5a5;font-size:12px;margin-top:4px">
                这意味着当前的排除模式在历史上反复出错，建议：
                • 重新审视排除方向是否有遗漏<br/>
                • 检查是否存在"掩护模式"或"造热陷阱"<br/>
                • 考虑降低置信度或改为观望态度</div>
            </div>`;
        } else if (hitRate <= 33 && simReviews.length >= 3) {
            suggestion = `<div style="margin-top:10px;padding:10px 14px;background:rgba(251,191,36,0.1);border:1px solid rgba(251,191,36,0.3);border-radius:8px">
                <span style="color:#fbbf24;font-weight:bold">⚠️ 历史参考：${simReviews.length}条相似案例仅${hitCount}条命中(${hitRate}%)</span>
                <div style="color:#fcd34d;font-size:12px;margin-top:4px">
                相似模式的历史表现不佳，建议结合其他信号综合判断，不要过度依赖单一排除路径。</div>
            </div>`;
        } else if (hitRate >= 67) {
            suggestion = `<div style="margin-top:10px;padding:10px 14px;background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);border-radius:8px">
                <span style="color:#4ade80;font-weight:bold">✅ 历史支持：${simReviews.length}条相似案例中${hitCount}条命中(${hitRate}%)</span>
                <div style="color:#86efac;font-size:12px;margin-top:4px">
                当前排除模式与历史上成功案例高度相似，可作为信心支撑。但仍需注意具体比赛的特殊性。</div>
            </div>`;
        }
        
        html += `

        <div class="section">
            <div class="section-title"><span class="icon icon-green">📚</span> 历史复盘参考（${simReviews.length}条相似案例 · 命中${hitCount}/${simReviews.length}）</div>
            <div style="font-size:11px;color:#64748b;margin-bottom:4px;line-height:1.6">
                <b>4维匹配标准：</b>赛事（同联赛15/同类型10）| 球队（同队12）| 赔率变向（竞彩模式15/澳门12/排除一致20/幅度接近6）| 预测（相同5/心水3）
                &nbsp;|&nbsp; <b>硬性前提：</b>预测结果必须相同
                &nbsp;|&nbsp; <b>门槛：</b>相似分≥35分 或 同队+同排除
            </div>
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap">
                <div style="display:flex;gap:6px;align-items:center">
                    <span style="font-size:11px;color:#94a3b8">命中率:</span>
                    <div style="width:80px;height:16px;background:#1e293b;border-radius:8px;overflow:hidden;position:relative">
                        <div style="position:absolute;left:0;top:0;height:100%;background:${hitRate>=50?'#22c55e':hitRate>=30?'#f59e0b':'#ef4444'};width:${hitRate}%;transition:width 0.3s"></div>
                    </div>
                    <span style="font-size:11px;font-weight:bold;color:${hitRate>=50?'#4ade80':hitRate>=30?'#fbbf24':'#f87171'}">${hitRate}%</span>
                </div>
            </div>`;

        // === 结果统计（胜/平/负分布）===
        var winCount = 0, drawCount = 0, loseCount = 0;
        simReviews.forEach(function(r) {
            var rc = (r.result_cn || '');
            if (rc.indexOf('主胜') >= 0) winCount++;
            else if (rc.indexOf('客胜') >= 0) loseCount++;
            else if (rc.indexOf('平') >= 0) drawCount++;
            else {
                var sc = r.actual_score || '';
                if (sc) {
                    var parts = sc.split('-');
                    if (parts.length >= 2) {
                        var h = parseInt(parts[0]), a = parseInt(parts[1]);
                        if (!isNaN(h) && !isNaN(a)) {
                            if (h > a) winCount++;
                            else if (h < a) loseCount++;
                            else drawCount++;
                        }
                    }
                }
            }
        });
        var totalDecided = winCount + drawCount + loseCount;
        var statHtml = '<div style="display:flex;align-items:center;gap:16px;margin-bottom:12px;padding:8px 12px;background:#0f172a;border-radius:8px;flex-wrap:wrap">';
        statHtml += '<span style="font-size:11px;color:#94a3b8">📊 结果分布：</span>';
        if (totalDecided > 0) {
            statHtml += '<span style="font-size:12px;color:#4ade80;font-weight:bold">' + winCount + '胜</span>';
            statHtml += ' <span style="color:#334155">·</span> ';
            statHtml += '<span style="font-size:12px;color:#fbbf24;font-weight:bold">' + drawCount + '平</span>';
            statHtml += ' <span style="color:#334155">·</span> ';
            statHtml += '<span style="font-size:12px;color:#f87171;font-weight:bold">' + loseCount + '负</span>';
            statHtml += ' <span style="font-size:11px;color:#64748b;margin-left:4px">（共' + totalDecided + '场）</span>';
        } else {
            statHtml += '<span style="font-size:11px;color:#64748b">暂无结果数据</span>';
        }
        statHtml += '</div>';
        html += statHtml;

        simReviews.forEach(function(rev) {
            var hitTag = rev.is_correct ?
                '<span style="background:rgba(34,197,94,0.15);color:#4ade80;padding:2px 8px;border-radius:4px;font-size:11px">✅命中</span>' :
                '<span style="background:rgba(239,68,68,0.15);color:#f87171;padding:2px 8px;border-radius:4px;font-size:11px">❌未中</span>';

            var reasonTags = '';
            if (rev.match_reasons) {
                reasonTags = rev.match_reasons.map(function(r) {
                    return '<span style="font-size:10px;background:rgba(99,102,241,0.15);color:#a5b4fc;padding:1px 6px;border-radius:3px;margin-right:4px;margin-bottom:2px;display:inline-block">' + r + '</span>';
                }).join('');
            }

            // 各维度得分条
            var ds = rev.dim_scores || {};
            var dimLabels = ['赛事','球队','赔率','预测'];
            var dimColors = ['#60a5fa','#4ade80','#f59e0b','#a78bfa'];
            var dimParts = [];
            for (var di = 0; di < dimLabels.length; di++) {
                var label = dimLabels[di];
                var score = ds[label] || 0;
                var color = dimColors[di];
                var w = Math.min(score * 2, 100);
                dimParts.push(
                    '<div style="flex:1;min-width:50px">' +
                    '<div style="font-size:9px;color:#64748b;text-align:center;margin-bottom:1px">' + label + score + '</div>' +
                    '<div style="height:6px;background:#1e293b;border-radius:3px;overflow:hidden">' +
                    '<div style="width:' + w + '%;height:100%;background:' + color + ';transition:width 0.3s"></div></div></div>'
                );
            }
            var dimHtml = dimParts.join('');

            var clsName = rev.is_correct ? 'str5' : 'str2';
            html += '<div class="signal-card ' + clsName + '" style="margin-bottom:10px"><div>' +
                '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;flex-wrap:wrap">' +
                '<strong style="font-size:13px;color:#cbd5e1">' + rev.home_team + ' vs ' + rev.away_team + '</strong>' +
                '<span style="color:#94a3b8;font-size:11px">' + (rev.league||'') + '</span>' +
                hitTag +
                '<span style="color:#6366f1;font-size:10px;font-weight:bold">' + rev.match_score + '分</span>' +
                '</div>' +
                '<div style="display:flex;gap:6px;margin-bottom:4px;background:#0c1222;padding:4px 8px;border-radius:4px;width:fit-content">' + dimHtml + '</div>' +
                '<div style="color:#94a3b8;font-size:12px">' +
                '预测：<strong>' + (rev.prediction||'') + '</strong> (' + (rev.confidence||0) + '★) | ' +
                '实际：<strong>' + (rev.actual_score||'') + '</strong> (' + (rev.result_cn||'') + ') | ' +
                '排除：' + ((rev.exclusions||[]).map(function(e){ return e==='home'?'主':e==='draw'?'平':'客'; }).join('、') || '无') +
                '</div>';

            // 澳门心水推荐
            var macaoTip = rev.macao_tip || '';
            if (macaoTip) {
                html += '<div style="margin-top:3px;color:#f59e0b;font-size:11.5px">🎯 澳门心水：<strong style="color:#fbbf24">' + macaoTip + '</strong></div>';
            }

            if (reasonTags) {
                html += '<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:2px">' + reasonTags + '</div>';
            }

            // 经验教训
            if (rev.lessons && rev.lessons.length > 0) {
                html += '<div style="margin-top:5px">';
                var lessonsToShow = rev.lessons.slice(0, 3);
                for (var li = 0; li < lessonsToShow.length; li++) {
                    var l = lessonsToShow[li];
                    var lc = '#fbbf24';
                    if (l.indexOf('✅') >= 0) lc = '#4ade80';
                    else if (l.indexOf('❌') >= 0) lc = '#f87171';
                    html += '<div style="font-size:11px;color:' + lc + ';margin-top:2px">💡 ' + l + '</div>';
                }
                html += '</div>';
            }

            html += '</div></div>';
        });
        
        // 追加统计建议
        if (suggestion) {
            html += suggestion;
        }
        
        html += '</div>';
    } else {
        // 没有找到高相似度案例时也提示一下
        if (res.review_count > 0) {
            html += `
            <div class="section" style="opacity:0.6">
                <div class="section-title"><span class="icon icon-gray">📚</span> 历史复盘参考</div>
                <div style="font-size:12px;color:#64748b">
                    已有 ${res.review_count} 条复盘记录，但未找到与当前比赛高度相似的案例。<br/>
                    <b>严格4维门槛：</b>需同时满足 <b>预测结果相同</b> + 赛事/球队/赔率 至少1项达标（总分≥35分 或 同队+同排除）。<br/>
                    这可能是新模式的比赛，或历史中无相同预测结果且高匹配度的案例，建议谨慎分析并保存复盘供未来参考。
                </div>
            </div>`;
        }
    }
    
    // 澳门分析原文
    if (rd.macao_analysis) {
        html += `
        <div class="section">
            <div class="section-title"><span class="icon icon-red">📝</span> 澳门分析原文</div>
            <div style="background:#0f172a;padding:14px;border-radius:8px;border:1px solid #334155;font-size:13px;line-height:1.7;color:#cbd5e1">
                ${rd.macao_analysis}
            </div>
        </div>`;
    }
    
    document.getElementById('detailContent').innerHTML = html;
    document.getElementById('detailPanel').classList.add('show');
}

function closeDetail() {
    document.getElementById('detailPanel').classList.remove('show');
}

function showStatus(msg, type) {
    const bar = document.getElementById('statusBar');
    bar.className = `status-bar ${type}`;
    bar.textContent = msg;
}

// 初始化（日期按钮已由服务端渲染）
initDates();

// ESC关闭详情面板
document.addEventListener('keydown', e => { if (e.key==='Escape') closeDetail(); });
</script>
</body>
</html>'''
    
    # 服务端渲染日期按钮（替换占位符）
    template = template.replace('__DATE_BUTTONS__', date_buttons_html or '<span style="color:#64748b;padding:8px;">暂无可用日期</span>')
    template = template.replace('__DEFAULT_DATE__', f"{default_date} ({default_count}场)" if default_date != '--' else '暂无数据')
    return template


def main():
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
    server = http.server.HTTPServer(('127.0.0.1', port), FootballAPIHandler)
    print(f"""
============================================
  足球预测分析器 - 纯排除法框架
============================================
  服务地址: http://127.0.0.1:{port}
  数据目录: {DATA_ROOT}
  按 Ctrl+C 停止服务
============================================
    """)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\n服务已停止。")
        server.server_close()


if __name__ == "__main__":
    main()
