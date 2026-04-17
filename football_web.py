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

# 数据根目录（自动检测，兼容本地和部署环境）
if __name__ != "__main__":
    # 作为模块导入时，基于文件位置
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
else:
    # 直接运行时，基于文件位置
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_ROOT = os.path.join(_BASE_DIR, "分析模板")
SCORES_FILE = os.path.join(DATA_ROOT, "_scores.json")
REVIEW_DIR = os.path.join(DATA_ROOT, "_reviews")
UPSETS_FILE = os.path.join(DATA_ROOT, "_upsets.json")

# 赛前情报存储目录
INTEL_DIR = os.path.join(_BASE_DIR, "data", "intelligence")
os.makedirs(INTEL_DIR, exist_ok=True)


def get_intel_path(match_key):
    """获取情报存储路径（安全文件名）"""
    safe = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', match_key)
    return os.path.join(INTEL_DIR, f"{safe}.json")


def save_intelligence(match_key, raw_text, parsed_data):
    """保存赛前情报到JSON文件"""
    path = get_intel_path(match_key)
    record = {
        "match_key": match_key,
        "raw_text": raw_text,
        "parsed": parsed_data,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    # 如果已有记录，保留原始录入时间
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                old = json.load(f)
            record["saved_at"] = old.get("saved_time", record["saved_at"])
        except Exception:
            pass
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return record


def load_intelligence(match_key):
    """加载某场比赛的情报"""
    path = get_intel_path(match_key)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def list_intelligence():
    """列出所有已保存的情报"""
    results = []
    for fname in sorted(os.listdir(INTEL_DIR), reverse=True):
        if not fname.endswith('.json'):
            continue
        try:
            with open(os.path.join(INTEL_DIR, fname), 'r', encoding='utf-8') as f:
                rec = json.load(f)
            results.append({
                "match_key": rec.get("match_key", ""),
                "saved_at": rec.get("saved_at", ""),
                "updated_at": rec.get("updated_at", ""),
                "has_injuries": bool(rec.get("parsed", {}).get("injuries")),
                "has_motivation": bool(rec.get("parsed", {}).get("motivation")),
                "file": fname,
            })
        except Exception:
            continue
    return results


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
                "odds_data": rev.get("odds_fingerprint", {}),
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


# ============================================================
# 冷门模式库（Upset Pattern Library）
# 自动收集"无预警爆冷"案例，用于后续模式匹配
# ============================================================

def load_upsets():
    """加载冷门模式库"""
    if os.path.exists(UPSETS_FILE):
        try:
            with open(UPSETS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"upsets": [], "stats": {"total": 0, "by_type": {}}}


def save_upsets(upsets_data):
    """保存冷门模式库"""
    os.makedirs(DATA_ROOT, exist_ok=True)
    with open(UPSETS_FILE, 'w', encoding='utf-8') as f:
        json.dump(upsets_data, f, ensure_ascii=False, indent=2)


def detect_upset_pattern(review):
    """
    检测一场复盘是否为"无预警爆冷"，如果是则生成冷门模式记录
    
    爆冷定义：预测错误 + 被排除的方向(或高赔方向)实际打出
              且当时没有任何冷门警告信号
    
    返回: upset_record 或 None
    """
    # 只处理预测错误的场次
    if review.get("is_correct", False):
        return None
    
    prediction = review.get("prediction", "")
    actual_result = review.get("actual_result", "")  # home/draw/away
    exclusions = set(review.get("exclusions", []))
    warnings = review.get("warnings", [])
    confidence = review.get("confidence", 0)
    
    if not actual_result or not prediction:
        return None
    
    # 提取预测方向
    pred_dir = ""
    if "主胜" in prediction:
        pred_dir = "home"
    elif "平局" in prediction:
        pred_dir = "draw"
    elif "客胜" in prediction:
        pred_dir = "away"
    elif "观望" in prediction:
        return None  # 观望不算爆冷
    
    if not pred_dir:
        return None
    
    # 判断是否为爆冷（预测方向 ≠ 实际结果）
    if pred_dir == actual_result:
        return None  # 预测方向对了但可能选了具体比分错？不对，这是胜平负
    
    # === 分类爆冷类型 ===
    upset_type = ""
    upset_detail = ""
    odds_fp = review.get("odds_fingerprint", {})
    jc_pattern = odds_fp.get("jc_pattern", "")
    mc_pattern = odds_fp.get("macao_pattern", "")
    
    # 类型1：静默型 — 竞彩和澳门都几乎不动(NNN)
    if jc_pattern == "NNN" and (mc_pattern in ("NNN", "")):
        upset_type = "silent"
        upset_detail = "静默型：赔率完全不动，无任何变化信号"
    
    # 类型2：反向掩护型 — 预测热门方向(低赔)，实际冷门方向打出
    # 特征：被排除的方向打出 或 高赔方向打出
    elif actual_result in exclusions:
        upset_type = "reverse_cover"
        dir_cn = {"home": "主胜", "draw": "平局", "away": "客胜"}
        upset_detail = f"反向掩护型：{dir_cn[actual_result]}被系统排除但实际打出"
    
    # 类型3：造热陷阱型 — R8信号存在但仍冷了
    elif any('R8' in w or '冷门' in w for w in warnings):
        upset_type = "heat_trap"
        upset_detail = "造热陷阱型：已有冷门预警信号但不够强/未重视"
    
    # 类型4：其他爆冷
    else:
        upset_type = "unknown"
        upset_detail = "未知类型：预测失败且无明显规律"
    
    # 计算爆冷赔率倍数（实际打出的方向的即时赔率）
    jc_real = odds_fp.get("jc_real_odds", [])
    macao_real = odds_fp.get("macao_real_odds", [])
    
    result_idx = {"home": 0, "draw": 1, "away": 2}.get(actual_result, -1)
    upset_odds = 1.0
    if result_idx >= 0 and len(jc_real) > result_idx:
        upset_odds = jc_real[result_idx]
    
    # 构建冷门特征指纹
    upset_record = {
        "upset_id": f"{review.get('date_folder','')}_{review.get('match_id','')}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "match_id": review.get("match_id", ""),
        "date_folder": review.get("date_folder", ""),
        "home_team": review.get("home_team", ""),
        "away_team": review.get("away_team", ""),
        "league": review.get("league", ""),
        
        # 爆冷核心数据
        "upset_type": upset_type,
        "upset_type_cn": upset_detail,
        "prediction": prediction,
        "predicted_dir": pred_dir,
        "actual_result": actual_result,
        "actual_score": review.get("actual_score", ""),
        "confidence": confidence,
        "was_excluded": actual_result in exclusions,
        "exclusions": list(exclusions),
        
        # 赔率指纹（用于匹配）
        "odds_fingerprint": odds_fp,
        "upset_odds": round(upset_odds, 2),
        
        # 基本面特征
        "home_form": review.get("home_form", ""),
        "away_form": review.get("away_form", ""),
        "handicap": review.get("handicap", ""),
        "macao_tip": review.get("macao_tip", ""),
        
        # 当时有否警告
        "had_cold_warning": len([w for w in warnings if '冷门' in w or 'R8' in w]) > 0,
        "warnings": warnings,
        
        # 时间戳
        "record_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    
    return upset_record


def add_upset_to_library(upset_record):
    """添加一条冷门记录到模式库"""
    lib = load_upsets()
    upsets = lib.get("upsets", [])
    
    # 去重：同一场比赛不重复添加
    match_key = f"{upset_record.get('date_folder','')}_{upset_record.get('match_id','')}"
    existing_idx = None
    for i, u in enumerate(upsets):
        ek = f"{u.get('date_folder','')}_{u.get('match_id','')}"
        if ek == match_key:
            existing_idx = i
            break
    
    if existing_idx is not None:
        upsets[existing_idx] = upset_record  # 更新已有记录
    else:
        upsets.insert(0, upset_record)  # 新记录插到最前
    
    # 更新统计
    by_type = {}
    for u in upsets:
        t = u.get("upset_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    
    lib["upsets"] = upsets[:200]  # 最多保留200条
    lib["stats"] = {
        "total": len(upsets),
        "by_type": by_type,
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    
    save_upsets(lib)
    return lib


def find_similar_upsets(analysis, top_n=5):
    """
    在分析时查找历史相似冷门模式，返回最相似的N条
    
    匹配维度：
    1. 赔率变化模式(jc_pattern/macao_pattern)
    2. 心水推荐反常性
    3. 近况极端程度
    4. 排除方向组合
    """
    lib = load_upsets()
    upsets = lib.get("upsets", [])
    if not upsets:
        return []
    
    current_pred = analysis.get("final_prediction", "")
    current_exc = set(analysis.get("exclusions", []))
    current_home_form = analysis.get("home_form", "")
    current_away_form = analysis.get("away_form", "")
    
    om = analysis.get("odds_matrix", {})
    jc_chg = om.get("jingcai", {}).get("change", [0, 0, 0])
    mc_chg = om.get("macao", {}).get("change", [0, 0, 0])
    
    def _chg_sign(v):
        return 'D' if v < -2 else ('U' if v > 2 else 'N')
    
    current_jc_pat = f"{_chg_sign(jc_chg[0])}{_chg_sign(jc_chg[1])}{_chg_sign(jc_chg[2])}"
    current_mc_pat = f"{_chg_sign(mc_chg[0])}{_chg_sign(mc_chg[1])}{_chg_sign(mc_chg[2])}"
    
    scored = []
    
    for u in upsets:
        score = 0
        reasons = []
        
        fp = u.get("odds_fingerprint", {})
        u_jc_pat = fp.get("jc_pattern", "")
        u_mc_pat = fp.get("macao_pattern", "")
        
        # 维度1：赔率变化模式一致（核心！）
        if u_jc_pat and u_jc_pat == current_jc_pat:
            score += 25
            reasons.append(f"竞彩变向{current_jc_pat}与历史冷门一致")
        if u_mc_pat and u_mc_pat == current_mc_pat:
            score += 20
            reasons.append(f"澳门变向{current_mc_pat}与历史冷门一致")
        
        # 维度2：心水推荐反常（弱队被推荐）
        u_tip = u.get("macao_tip", "")
        current_tip = analysis.get("macao_tip", "")
        
        # 维度3：近况极端程度
        u_home_f = u.get("home_form", "")
        u_away_f = u.get("away_form", "")
        
        # 主队连败检测
        if current_home_form and u_home_f:
            cur_losses = sum(1 for c in current_home_form if c == 'L')
            u_losses = sum(1 for c in u_home_f if c == 'L')
            if cur_losses >= 5 and u_losses >= 5:
                score += 15
                reasons.append(f"主队近况差(≥5败)与冷门模式相似")
        
        # 维度4：排除方向相同
        u_exc = set(u.get("exclusions", []))
        exc_match = current_exc & u_exc
        if exc_match:
            score += len(exc_match) * 10
            reasons.append(f"排除方向{'/'.join(exc_match)}一致")
        
        # 维度5：联赛相同
        if analysis.get("league", "") == u.get("league", ""):
            score += 8
            reasons.append(f"同联赛:{u.get('league','')}")
        
        if score > 0:
            scored.append({
                **u,
                "_match_score": score,
                "_match_reasons": reasons,
            })
    
    # 按分数排序，返回top N（仅返回有意义的匹配：≥20分）
    scored.sort(key=lambda x: x["_match_score"], reverse=True)
    return [s for s in scored[:top_n] if s["_match_score"] >= 20]


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

    # 提取竞彩赔率（字典格式，兼容两种源数据模板）
    if 'jc_odds' not in data or not data.get('jc_odds'):
        jc_dict_match = re.search(r'jc_odds\s*=\s*\{([^}]+)\}', content)
        if jc_dict_match:
            try:
                jcd = {}
                for m in re.finditer(r"['\"](\S+)['\"]\s*:\s*([0-9.]+)", jc_dict_match.group(1)):
                    jcd[m.group(1)] = float(m.group(2))
                if jcd:
                    data['jc_odds'] = jcd
                    # 同时设置独立字段供其他地方使用
                    if '胜' in jcd: data['jc_home_odds'] = jcd['胜']
                    if '平' in jcd: data['jc_draw_odds'] = jcd['平']
                    if '负' in jcd: data['jc_away_odds'] = jcd['负']
            except:
                pass
    
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


# ============================================================
# 赛前情报分析（本地数据推导利好/利空 + 心水对照）
# ============================================================

def get_pre_match_analysis(date_folder, match_id):
    """从已有比赛数据分析赛前情报，推导两队利好/利空因素，对照澳门心水"""

    # 1. 加载源数据
    file_pattern = os.path.join(DATA_ROOT, date_folder, f"{match_id}_*_源数据.md")
    files = glob.glob(file_pattern)
    if not files:
        return {"success": False, "error": f"未找到比赛: {match_id}"}

    raw = parse_source_file(files[0])
    analysis = analyze_match(raw)

    home_team = raw.get("home_team", "")
    away_team = raw.get("away_team", "")
    league = raw.get("league", "")

    # 2. 基本面数据
    form_h_str = raw.get("form_home", "") or raw.get("home_form", "") or raw.get("form_h", "")
    form_a_str = raw.get("form_away", "") or raw.get("away_form", "") or raw.get("form_a", "")
    macao_tip = raw.get("macao_tip", "") or ""
    macao_analysis = raw.get("macao_analysis", "") or ""
    handicap = str(raw.get("handicap", ""))
    h2h = raw.get("history", "") or raw.get("h2h", "")

    # 让球赔率（传给前端展示）
    jc_odds_hc = raw.get('jc_odds', {}) or {}

    # 解析近况走势
    def parse_form(form_str, team_name):
        if not form_str:
            return {"recent": [], "wins": 0, "draws": 0, "losses": 0, "rate": 0}
        results = []
        for ch in str(form_str)[:15]:
            if ch == 'W' or ch == 'D' or ch == 'L':
                results.append(ch)
        wins = results.count('W')
        draws = results.count('D')
        losses = results.count('L')
        total = max(len(results), 1)
        return {
            "recent": "".join(results[:6]),
            "last5": results[:5],
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "rate": round(wins / total * 100),
        }

    home_form = parse_form(form_h_str, home_team)
    away_form = parse_form(form_a_str, away_team)

    # 3. 赔率信号
    # ⚠️ realtime_odds数组第一行是注释(# 格式...)，实际index 0=竞彩(第二行)
    init_odds = (raw.get('initial_odds') or [])
    real_odds = (raw.get('realtime_odds') or [])

    # 竞彩标准盘(index 0=竞彩行，跳过可能的注释行)
    jc_init = init_odds[0] if len(init_odds) > 0 else []
    jc_real = real_odds[0] if len(real_odds) > 0 else []
    # 如果取到的是注释行(非数字)，尝试取下一行
    if jc_real and len(jc_real) >= 3:
        try: float(jc_real[0])
        except (ValueError, TypeError):
            jc_real = real_odds[1] if len(real_odds) > 1 else []
            jc_init = init_odds[1] if len(init_odds) > 1 else []

    macao_init = init_odds[2] if len(init_odds) > 2 else []
    macao_real = real_odds[2] if len(real_odds) > 2 else []

    # 竞彩赔率变化
    jc_h_chg = calc_pct(float(jc_init[0]), float(jc_real[0])) if len(jc_init) >= 3 and len(jc_real) >= 3 else 0
    jc_d_chg = calc_pct(float(jc_init[1]), float(jc_real[1])) if len(jc_init) >= 3 and len(jc_real) >= 3 else 0
    jc_a_chg = calc_pct(float(jc_init[2]), float(jc_real[2])) if len(jc_init) >= 3 and len(jc_real) >= 3 else 0

    current_h = float(jc_real[0]) if jc_real else 0
    current_d = float(jc_real[1]) if jc_real else 0
    current_a = float(jc_real[2]) if jc_real else 0

    # 4. 推导利好/利空因素
    home_favors = []   # 主队利好
    home_unfavors = []  # 主队利空
    away_favors = []   # 客队利好
    away_unfavors = []  # 客队利空

    # --- 近况因素 ---
    if home_form['rate'] >= 70:
        home_favors.append({"type": "form", "text": f"近况火热：{home_form['recent']}(胜率{home_form['rate']}%)", "strength": "strong"})
    elif home_form['rate'] <= 30:
        home_unfavors.append({"type": "form", "text": f"近况低迷：{home_form['recent']}(胜率仅{home_form['rate']}%)", "strength": "strong"})

    if away_form['rate'] >= 70:
        away_favors.append({"type": "form", "text": f"近况火热：{away_form['recent']}(胜率{away_form['rate']}%)", "strength": "strong"})
    elif away_form['rate'] <= 30:
        away_unfavors.append({"type": "form", "text": f"近况低迷：{away_form['recent']}(胜率仅{away_form['rate']}%)", "strength": "strong"})

    # --- 连胜/连败 ---
    last5_h = home_form.get('last5', [])
    streak_h_win = 0; streak_h_loss = 0
    for r in reversed(last5_h):
        if r == 'W': streak_h_win += 1
        else: break
    for r in reversed(last5_h):
        if r == 'L': streak_h_loss += 1
        else: break
    if streak_h_win >= 3:
        home_favors.append({"type": "streak", "text": f"当前连胜{streak_h_win}场，气势正盛", "strength": "medium"})
    if streak_h_loss >= 3:
        home_unfavors.append({"type": "streak", "text": f"当前连败{streak_h_loss}场，士气低落", "strength": "strong"})

    last5_a = away_form.get('last5', [])
    streak_a_win = 0; streak_a_loss = 0
    for r in reversed(last5_a):
        if r == 'W': streak_a_win += 1
        else: break
    for r in reversed(last5_a):
        if r == 'L': streak_a_loss += 1
        else: break
    if streak_a_win >= 3:
        away_favors.append({"type": "streak", "text": f"当前连胜{streak_a_win}场，气势正盛", "strength": "medium"})
    if streak_a_loss >= 3:
        away_unfavors.append({"type": "streak", "text": f"当前连败{streak_a_loss}场，士气低落", "strength": "strong"})

    # --- 赔率位置因素 ---
    if current_h < 1.50:
        home_favors.append({"type": "odds_position", "text": f"主胜赔率{current_h:.2f}极低，庄家看好主队", "strength": "medium"})
    elif current_a < 1.50:
        away_favors.append({"type": "odds_position", "text": f"客胜赔率{current_a:.2f}极低，庄家看好客队", "strength": "medium"})
    elif current_d < 3.00:
        # 平赔偏低
        pass

    # --- [已移除] 赔率变化信号（竞彩/澳门降赔升赔）---
    # 原因：赔率变化数据已在赔付压力矩阵+水位分析中体现，不应重复放入基本面利好/利空
    # 基本面应只包含：近期战绩、主场/客场、历史交锋、排名等纯球队信息
    # 以下内容移除：
    #   - 竞彩主胜/客胜降赔X%（odds_move类型）
    #   - 澳门主胜/客胜降赔Y% 同向造热（macao_move类型）

    # --- 主客场因素（让球盘口暗示） ---
    if handicap:
        h_val = 0
        try: h_val = float(handicap)
        except: pass
        if h_val < -0.5:  # 主让1球以上
            home_favors.append({"type": "handicap", "text": f"主场让{handicap}球，实力优势明显", "strength": "medium"})
        elif h_val > 0.5:   # 客让1球以上
            away_favors.append({"type": "handicap", "text": f"客场让{-h_val}球（受让），客队实力占优", "strength": "medium"})

    # --- 历史交锋 ---
    if h2h:
        import re as _re
        hw_match = _re.search(r'(\d+)胜', h2h)
        dw_match = _re.search(r'(\d+)和|(\d+)平', h2h)
        al_match = _re.search(r'(\d+)负', h2h)
        if hw_match:
            hw = int(hw_match.group(1))
            if hw >= 3:
                home_favors.append({"type": "h2h", "text": f"历史交锋占优({h2h})", "strength": "medium"})

    # 5. 澳门心水解析
    tip_direction = None
    tip_text = ""
    if macao_tip:
        tip_direction = parse_macao_direction(macao_tip)
        tip_dir_cn = direction_name(tip_direction) if tip_direction != "unknown" else ""
        tip_text = f"澳门推荐「{macao_tip}」→ {tip_dir_cn}"

        # 心水方向的赔率
        tip_odds_val = 0
        if tip_direction == "home":
            tip_odds_val = current_h
        elif tip_direction == "draw":
            tip_odds_val = current_d
        elif tip_direction == "away":
            tip_odds_val = current_a

    # 6. 综合结论：利好/利空对比 + 是否配合心水
    home_score = sum(3 if f["strength"] == "strong" else (2 if f["strength"] == "medium" else 1) for f in home_favors)
    home_penalty = sum(3 if u["strength"] == "strong" else (2 if u["strength"] == "medium" else 1) for u in home_unfavors)
    away_score = sum(3 if f["strength"] == "strong" else (2 if f["strength"] == "medium" else 1) for f in away_favors)
    away_penalty = sum(3 if u["strength"] == "strong" else (2 if u["strength"] == "medium" else 1) for u in away_unfavors)

    home_net = home_score - home_penalty
    away_net = away_score - away_penalty

    # 判断基本面倾向
    if home_net > away_net + 3:
        basic_tendency = "home"
        tendency_text = "基本面明显偏向主队"
    elif away_net > home_net + 3:
        basic_tendency = "away"
        tendency_text = "基本面明显偏向客队"
    elif abs(home_net - away_net) <= 3:
        basic_tendency = "draw"
        tendency_text = "基本面双方势均力敌，需警惕平局"
    else:
        basic_tendency = "neutral"
        tendency_text = "基本面略有偏向但不够明确"

    # 7. 与心水对照得出最终判断
    conclusion_parts = []
    verdict_level = ""  # strong_align / align / conflict / neutral / no_tip

    if tip_direction and tip_direction != "unknown":
        # 有心水推荐时做对照
        tip_map = {"home": "主胜", "draw": "平局", "away": "客胜"}
        tendency_map = {"home": "主胜", "draw": "平局/均衡", "away": "客胜", "neutral": "不明确"}

        if tip_direction == basic_tendency:
            verdict_level = "strong_align"
            conclusion_parts.append(f"{tip_text} ✅")
            conclusion_parts.append(f"与基本面倾向「{tendency_map[basic_tendency]}」完全一致")
            conclusion_parts.append("★ 庄家意图与基本面共振，可信度较高")
        elif (tip_direction in ("home", "away") and basic_tendency in ("home", "away") and tip_direction != basic_tendency):
            # 方向矛盾
            verdict_level = "conflict"
            conclusion_parts.append(f"{tip_text}")
            conclusion_parts.append(f"⚠️ 但基本面倾向「{tendency_map[basic_tendency]}」，与心水方向矛盾！")
            conclusion_parts.append("庄家可能在利用基本面引导筹码，需要警惕反向结果")
        else:
            verdict_level = "align"
            conclusion_parts.append(f"{tip_text}")
            conclusion_parts.append(f"基本面倾向「{tendency_map[basic_tendency]}」")
            conclusion_parts.append("心水与基本面无明确冲突，可参考心水方向")
    else:
        verdict_level = "no_tip"
        conclusion_parts.append("本期无明确的澳门心水推荐")
        conclusion_parts.append(f"基本面倾向：{tendency_text}")
        conclusion_parts.append("建议以排除法为主，结合赔率变化判断")

    # 8. 构建返回数据
    result = {
        "success": True,
        "data": {
            "match_info": {
                "league": league,
                "home": home_team,
                "away": away_team,
                "handicap": handicap,
                "hc_odds": jc_odds_hc,          # 让球赔率（竞彩-1/+1球胜平负）
                "h2h": h2h,
            },
            # === 标准盘赔率（不让球，用于水位分析①） ===
            "standard_odds": {
                "home": current_h,             # 竞彩即时主胜
                "draw": current_d,             # 竞彩即时平局
                "away": current_a,             # 竞彩即时客胜
                # 变化百分比
                "home_chg": jc_h_chg,
                "draw_chg": jc_d_chg,
                "away_chg": jc_a_chg,
            },
            # === 让球赔率变化（如果有初盘对比） ===
            "hc_changes": {},
            "form": {
                "home": {
                    "recent": home_form['recent'],
                    "wins": home_form['wins'],
                    "draws": home_form['draws'],
                    "losses": home_form['losses'],
                    "rate": home_form['rate'],
                },
                "away": {
                    "recent": away_form['recent'],
                    "wins": away_form['wins'],
                    "draws": away_form['draws'],
                    "losses": away_form['losses'],
                    "rate": away_form['rate'],
                },
            },
            "home_factors": {
                "favors": home_favors,
                "unfavors": home_unfavors,
                "score": home_score,
                "penalty": home_penalty,
                "net": home_net,
            },
            "away_factors": {
                "favors": away_favors,
                "unfavors": away_unfavors,
                "score": away_score,
                "penalty": away_penalty,
                "net": away_net,
            },
            "macao": {
                "tip": macao_tip,
                "analysis": macao_analysis,
                "direction": tip_direction,
                "tip_text": tip_text,
            },
            "conclusion": {
                "basic_tendency": basic_tendency,
                "tendency_text": tendency_text,
                "verdict_level": verdict_level,
                "parts": conclusion_parts,
                "home_net": home_net,
                "away_net": away_net,
            },
            # === 三大维度（来自分析引擎现有数据）===
            "engine_data": {
                # 维度1: 相似案例命中率
                "review_hit_rate": _calc_review_stats(analysis),
                # 维度2: 冷门预警
                "cold_alerts": analysis.get("warnings", []),
                # 维度3: 排除引擎
                "exclusions": analysis.get("exclusions", []),
                "final_pred": analysis.get("final_prediction", ""),
                "confidence": analysis.get("confidence", 0),
            }
        }
    }

    return result


def _calc_review_stats(analysis):
    """从分析引擎的相似案例中提取命中率统计"""
    reviews = load_review_history()
    if not reviews:
        return {"total": 0, "message": "暂无复盘数据"}
    
    total = len(reviews)
    hit = sum(1 for r in reviews if r.get('is_correct', False))
    
    # 同预测方向命中率
    current_pred = analysis.get('final_prediction', '')
    same_pred = [r for r in reviews if r.get('prediction') == current_pred]
    sp_hit = sum(1 for r in same_pred if r.get('is_correct', False))
    
    # 同联赛
    league = analysis.get('league', '')
    same_league = [r for r in reviews if r.get('league') == league]
    sl_hit = sum(1 for r in same_league if r.get('is_correct', False))
    
    return {
        "total": total,
        "hit": hit,
        "overall_rate": round(hit / total * 100, 1) if total > 0 else 0,
        "same_prediction": {
            "dir": current_pred or "未预测",
            "count": len(same_pred),
            "hit": sp_hit,
            "rate": round(sp_hit / len(same_pred) * 100, 1) if same_pred else 0,
        },
        "same_league": {
            "name": league or "未知",
            "count": len(same_league),
            "hit": sl_hit,
            "rate": round(sl_hit / len(same_league) * 100, 1) if same_league else 0,
        }
    }


def get_handicap_similar(date_folder, match_id):
    """基于让球盘赔率查找相似历史案例（6维度匹配）"""
    # 1. 获取当前比赛数据（与/api/analyze相同方式加载）
    file_pattern = os.path.join(DATA_ROOT, date_folder, f"{match_id}_*_源数据.md")
    files = glob.glob(file_pattern)
    if not files:
        return {"success": False, "error": f"未找到比赛: {match_id}"}

    raw = parse_source_file(files[0])
    analysis = analyze_match(raw)

    # 尝试读取复盘指纹（如果有）
    fingerprint = {}
    review_path = os.path.join(DATA_ROOT, date_folder, '_reviews', f'{match_id}_review.json')
    if os.path.exists(review_path):
        try:
            with open(review_path, 'r', encoding='utf-8') as rf:
                fingerprint = json.load(rf).get('odds_fingerprint', {})
        except:
            pass

    # 当前让球盘信息
    cur_hc = str(raw.get('handicap', ''))
    cur_jc_odds = raw.get('jc_odds') or {}
    cur_hc_odds = fingerprint.get('hc_jc_odds') or {}

    if not cur_hc and not cur_hc_odds:
        return {"success": True, "data": {"similar": [], "summary": {"total_reviews": 0, "matched": 0, "message": "该场比赛无让球盘数据"}}}

    # 当前让球后赔率（优先用hc_jc_odds，其次从jc_odds推算）
    cur_h_win = cur_hc_odds.get('home', '') or (cur_jc_odds.get('home', '') if cur_hc else '')
    cur_h_draw = cur_hc_odds.get('draw', '') or (cur_jc_odds.get('draw', '') if cur_hc else '')
    cur_h_away = cur_hc_odds.get('away', '') or (cur_jc_odds.get('away', '') if cur_hc else '')

    # 不让球赔率
    init_odds = (raw.get('initial_odds') or [])
    jc_init = init_odds[1] if len(init_odds) > 1 else []  # index 1 = 竞彩初赔
    cur_home_init = float(jc_init[0]) if len(jc_init) > 0 else 0
    cur_away_init = float(jc_init[2]) if len(jc_init) > 2 else 0

    cur_league = raw.get('league', '')
    cur_form_h = analysis.get('form_home', '')
    cur_form_a = analysis.get('form_away', '')

    # 2. 遍历所有历史复盘
    all_reviews = load_review_history()
    scored = []

    for r in all_reviews:
        rfp = r.get('odds_fingerprint', {}) or {}
        rhc = str(rfp.get('handicap', ''))
        rhc_odds = rfp.get('hc_jc_odds') or {}
        
        # 如果fingerprint没有handicap，从源数据文件补充读取
        if not rhc:
            r_date = str(r.get('date_folder', ''))
            r_id = str(r.get('match_id', ''))
            if r_date and r_id:
                src_files = glob.glob(os.path.join(DATA_ROOT, r_date, f'{r_id}_*_源数据.md'))
                if src_files:
                    try:
                        src_raw = parse_source_file(src_files[0])
                        rhc = str(src_raw.get('handicap', ''))
                    except: pass
        
        # 必须有让球盘口才能匹配
        if not rhc: continue

        # 如果没有让球赔率，从源数据补充
        if not rhc_odds and r_date and r_id:
            src_files2 = glob.glob(os.path.join(DATA_ROOT, r_date, f'{r_id}_*_源数据.md'))
            if src_files2:
                try:
                    src_raw2 = parse_source_file(src_files2[0])
                    rhc_odds = src_raw2.get('jc_odds') or {}
                except: pass

        score = 0
        reasons = []

        # 维度1: 盘口一致 (25分)
        if rhc == cur_hc:
            score += 25
            reasons.append("盘口一致")
        elif abs(float(rhc) - float(cur_hc)) < 0.5 if rhc.replace('-','').replace('.','').isdigit() and cur_hc.replace('-','').replace('.','').isdigit() else False:
            score += 10
            reasons.append(f"盘口接近({rhc}vs{cur_hc})")

        # 维度2: 让球主赔接近 (20/10分)
        rh_win = rhc_odds.get('home', '')
        if rh_win and cur_h_win:
            try:
                diff = abs(float(rh_win) - float(cur_h_win))
                if diff <= 0.30:
                    score += 20; reasons.append(f"主赔差{diff:.2f}")
                elif diff <= 0.60:
                    score += 10; reasons.append(f"主赔差{diff:.2f}")
            except: pass

        # 维度3: 让球客赔接近 (20/10分)
        rh_away = rhc_odds.get('away', '')
        if rh_away and cur_h_away:
            try:
                diff = abs(float(rh_away) - float(cur_h_away))
                if diff <= 0.30:
                    score += 20; reasons.append(f"客赔差{diff:.2f}")
                elif diff <= 0.60:
                    score += 10; reasons.append(f"客赔差{diff:.2f}")
            except: pass

        # 维度4: 同联赛 (15分)
        if cur_league and cur_league in r.get('league', ''):
            score += 15
            reasons.append("同联赛")

        # 维度5: 让球平赔接近 (10/5分)
        rh_draw = rhc_odds.get('draw', '')
        if rh_draw and cur_h_draw:
            try:
                diff = abs(float(rh_draw) - float(cur_h_draw))
                if diff <= 0.50:
                    score += 10; reasons.append(f"平赔差{diff:.2f}")
                elif diff <= 1.00:
                    score += 5; reasons.append(f"平赔差{diff:.2f}")
            except: pass

        # 维度6: 不让球结构相似 (5分)
        r_init = r.get('initial_odds') or []
        if len(r_init) > 2 and cur_home_init > 0:
            try:
                rhi, rai = float(r_init[0]), float(r_init[2])
                cur_ratio = cur_home_init / max(cur_away_init, 0.01)
                r_ratio = rhi / max(rai, 0.01)
                if abs(cur_ratio - r_ratio) < 0.5:
                    score += 5; reasons.append("结构相似")
            except: pass

        if score >= 40:
            r['_sim_score'] = score
            r['_sim_reasons'] = reasons
            scored.append(r)

    # 按分数排序，取Top6
    scored.sort(key=lambda x: x.get('_sim_score', 0), reverse=True)
    top = scored[:6]

    # 构建返回结果
    result_list = []
    hit_count = 0
    pred_dist = {"主胜": 0, "平局": 0, "客胜": 0}
    actual_dist = {"主胜": 0, "平局": 0, "客胜": 0}

    for r in top:
        item = {
            "match_id": r.get("match_id", ""),
            "date_folder": r.get("date_folder", ""),
            "home_team": r.get("home_team", ""),
            "away_team": r.get("away_team", ""),
            "league": r.get("league", ""),
            "score": r.get("_sim_score", 0),
            "reasons": r.get("_sim_reasons", []),
            "handicap": str(r.get('odds_fingerprint', {}).get('handicap', '')),
            "hc_odds": r.get('odds_fingerprint', {}).get('hc_jc_odds', {}),
            "prediction": r.get("prediction", ""),
            "confidence": r.get("confidence", 0),
            "actual_score": r.get("actual_score", ""),
            "result_cn": r.get("result_cn", ""),
            "is_correct": r.get("is_correct", False),
            "form_home": r.get("form_home", ""),
            "form_away": r.get("form_away", ""),
            "lessons": [l for l in r.get("lessons", []) if l.startswith(('❌','⚠️'))][:2],
        }
        result_list.append(item)

        if r.get("is_correct"): hit_count += 1
        p = r.get("prediction", "")
        a = r.get("result_cn", "")
        for k in pred_dist:
            if k in p: pred_dist[k] += 1
        for k in actual_dist:
            if k in a: actual_dist[k] += 1

    summary = {
        "total_reviews": len(all_reviews),
        "has_handicap": sum(1 for x in all_reviews if str(x.get('odds_fingerprint', {}).get('handicap', ''))),
        "matched": len(top),
        "hit_count": hit_count,
        "hit_rate": f"{hit_count/max(len(top),1)*100:.0f}%" if top else "N/A",
        "pred_dist": pred_dist,
        "actual_dist": actual_dist,
        "current": {
            "handicap": cur_hc,
            "hc_odds": {"home": cur_h_win, "draw": cur_h_draw, "away": cur_h_away},
            "league": cur_league,
        }
    }

    return {"success": True, "data": {"similar": result_list, "summary": summary}}


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
                
                # ★ 冷门模式库：自动检测爆冷并入库
                upset = detect_upset_pattern(review)
                upset_info = None
                if upset:
                    lib = add_upset_to_library(upset)
                    upset_info = {
                        "detected": True,
                        "upset_type": upset["upset_type"],
                        "upset_type_cn": upset["upset_type_cn"],
                        "upset_odds": upset.get("upset_odds", 0),
                        "library_total": lib.get("stats", {}).get("total", 0),
                        "message": f"🧊 检测到{upset['upset_type_cn']}（赔率{upset.get('upset_odds','?')}），已加入冷门模式库",
                    }
                else:
                    upset_info = {"detected": False, "message": "✅ 预测正确/或非爆冷类型"}
                
                self.send_json({
                    "success": True,
                    "message": "复盘日志已生成",
                    "review": review,
                    "filepath": filepath,
                    "upset_detect": upset_info,
                })
            
            elif parsed == '/api/upsets':
                # 获取冷门模式库
                lib = load_upsets()
                upsets = lib.get("upsets", [])
                
                # 支持按类型筛选
                filter_type = data.get('type', '')
                if filter_type:
                    upsets = [u for u in upsets if u.get('upset_type', '') == filter_type]
                
                self.send_json({
                    "success": True,
                    "data": upsets,
                    "stats": lib.get("stats", {}),
                    "count": len(upsets),
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
            
            elif parsed == '/api/intelligence':
                # 保存赛前情报
                match_key = data.get('match_key', '')
                raw_text = data.get('raw_text', '')
                parsed_data = data.get('parsed', {})
                
                if not match_key or not raw_text:
                    self.send_json({"success": False, "error": "缺少match_key或raw_text"})
                    return
                
                record = save_intelligence(match_key, raw_text, parsed_data)
                self.send_json({"success": True, "message": "情报已保存", "data": record})
            
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
            
            elif parsed == '/api/version':
                # 读取版本号
                vf = os.path.join(os.path.dirname(__file__), 'version.txt')
                ver = '?.?.?'
                if os.path.exists(vf):
                    with open(vf, 'r', encoding='utf-8') as f:
                        ver = f.read().strip()
                import datetime as _dt
                bt = _dt.datetime.now().strftime('%Y.%m.%d %H:%M')
                self.send_json({"success": True, "version": ver, "build_time": bt})
            
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
                
                # ★ 查找相似冷门模式
                similar_upsets = find_similar_upsets(analysis)
                upsets_lib = load_upsets()
                
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
                        # ★ 关键：传递完整赔率数组供前端R1规则使用
                        "initial_odds": raw_data.get("initial_odds", []),
                        "realtime_odds": raw_data.get("realtime_odds", []),
                    },
                    "analysis": analysis,
                    "similar_reviews": similar_reviews,
                    "similar_upsets": similar_upsets,  # ★ 新增：相似冷门模式
                    "upsets_stats": upsets_lib.get("stats", {}),  # ★ 冷门库统计
                    "review_count": len(all_reviews) if all_reviews else 0,
                    "match_id": match_id,
                    "date_folder": date_folder,
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
            
            elif parsed == '/api/upsets':
                # 获取冷门模式库（GET）
                lib = load_upsets()
                upsets = lib.get("upsets", [])
                
                filter_type = query.get('type', [''])[0]
                if filter_type:
                    upsets = [u for u in upsets if u.get('upset_type', '') == filter_type]
                
                self.send_json({
                    "success": True,
                    "data": upsets,
                    "stats": lib.get("stats", {}),
                    "count": len(upsets),
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
            
            elif parsed == '/api/intelligence':
                # 加载某场比赛的情报
                match_key = query.get('match_key', [''])[0]
                if not match_key:
                    self.send_json({"success": False, "error": "缺少match_key"})
                    return
                intel = load_intelligence(match_key)
                if intel:
                    self.send_json({"success": True, "data": intel})
                else:
                    self.send_json({"success": True, "data": None, "message": "暂无情报记录"})
            
            elif parsed == '/api/intelligence/list':
                # 列出所有已保存的情报
                items = list_intelligence()
                self.send_json({"success": True, "data": items, "count": len(items)})
            
            elif parsed.startswith('/static/'):
                # 静态文件服务（JS/CSS等外部模块）
                file_path = os.path.join(os.path.dirname(__file__), parsed.lstrip('/'))
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    ext = os.path.splitext(file_path)[1].lower()
                    content_types = {
                        '.js': 'application/javascript; charset=utf-8',
                        '.css': 'text/css; charset=utf-8',
                        '.png': 'image/png',
                        '.svg': 'image/svg+xml',
                    }
                    ct = content_types.get(ext, 'application/octet-stream')
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', ct)
                    self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
                    self.end_headers()
                    self.wfile.write(content)
                else:
                    self.send_json({"success": False, "error": "File not found"}, status=404)

            elif parsed == '/api/handicap-similar':
                # 基于让球盘赔率的相似案例
                date_folder = query.get('date', [''])[0]
                match_id = query.get('match_id', [''])[0]
                result = get_handicap_similar(date_folder, match_id)
                self.send_json(result)

            elif parsed == '/api/pre-match-analysis':
                # 赛前情报分析（利好/利空推导 + 心水对照）
                date_folder = query.get('date', [''])[0]
                match_id = query.get('match_id', [''])[0]
                result = get_pre_match_analysis(date_folder, match_id)
                self.send_json(result)

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
.icon-purple { background: rgba(168,85,247,0.2); color: #a855f7; }
.icon-orange { background: rgba(249,115,22,0.2); color: #f97316; }
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
    <h1>⚽ 足球预测分析器 — 纯排除法框架 <span id="versionInfo" style="font-size:13px;color:#f59e0b;font-weight:bold;"></span></h1>
    <p>基于造热原理与排除法的足球比赛赔率分析工具 | 自动读取500.com源数据</p>
    <div style="margin-top:8px;display:flex;gap:12px;flex-wrap:wrap">
        <a href="#" onclick="showUpsetsLibrary();return false;" style="color:#60a5fa;font-size:12px;text-decoration:none;cursor:pointer" onmouseover="this.style.color='#93c5fd'" onmouseout="this.style.color='#60a5fa'">🧊 冷门模式库</a>
        <span style="color:#334155">|</span>
        <a href="#" onclick="showReviewPage();return false;" style="color:#94a3b8;font-size:12px;text-decoration:none;cursor:pointer" onmouseover="this.style.color='#cbd5e1'" onmouseout="this.style.color='#94a3b8'">📚 历史复盘</a>
    </div>
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
    // 显示版本号
    try {
        const verRes = await api('/api/version');
        const versionEl = document.getElementById('versionInfo');
        if (versionEl && verRes.success) {
            versionEl.textContent = `[V${verRes.version}] | 构建: ${verRes.build_time}`;
        }
    } catch(e) {}
    
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

            // 赔率信息
            var odds = rev.odds_data || {};
            if (odds.jc_real_odds && odds.jc_real_odds.length >= 3) {
                var jco = odds.jc_real_odds;  // 竞彩即时赔率
                var mco = odds.macao_real_odds || [];  // 澳门即时赔率
                var jcInit = odds.jc_init_odds || [];   // 竞彩初盘
                var mcaoInit = odds.macao_init_odds || []; // 澳门初盘

                // 赔率变化箭头函数（提前声明，避免作用域问题）
                function _arrow(cur, init) {
                    var d = cur - init;
                    if (d > 0.02) return '<span style="color:#fca5a5;font-size:11px;font-weight:bold">↑' + d.toFixed(2) + '</span>';
                    else if (d < -0.02) return '<span style="color:#86efac;font-size:11px;font-weight:bold">↓' + Math.abs(d).toFixed(2) + '</span>';
                    return '<span style="color:#475569;font-size:11px">—</span>';
                }

                html += '<div style="margin-top:4px;background:#1e293b;border-radius:6px;padding:8px 10px;font-size:11.5px">';

                // 竞彩赔率行
                html += '<table style="width:100%;border-collapse:collapse">';
                html += '<tr><td colspan="4" style="padding-bottom:2px;color:#94a3b8;font-size:10.5px;font-weight:600">\u7ade\u5f69\u8d54\u7387\uff08\u5373\u65f6 / \u53d8\u5316\uff09</td></tr>';
                html += '<tr>';
                html += '<td style="text-align:center;padding:2px"><span style="color:#94a3b8;font-size:10px">\u4e3b</span><br><strong style="color:#60a5fa;font-size:13px">' + (jco[0]||'-') + '</strong></td>';
                html += '<td style="text-align:center;padding:2px"><span style="color:#94a3b8;font-size:10px">\u5e73</span><br><strong style="color:#fbbf24;font-size:13px">' + (jco[1]||'-') + '</strong></td>';
                html += '<td style="text-align:center;padding:2px"><span style="color:#94a3b8;font-size:10px">\u5ba2</span><br><strong style="color:#a78bfa;font-size:13px">' + (jco[2]||'-') + '</strong></td>';

                // 赔率变化箭头
                if (jcInit.length >= 3) {
                    html += '<td style="text-align:right;padding:2px;white-space:nowrap;vertical-align:bottom;border-left:1px solid #334155;padding-left:8px">';
                    html += '<span style="color:#64748b;font-size:9px">\u53d8\u5316:</span> ';
                    html += _arrow(jco[0], jcInit[0]) + ' ';
                    html += _arrow(jco[1], jcInit[1]) + ' ';
                    html += _arrow(jco[2], jcInit[2]);
                    html += '</td>';
                } else {
                    html += '<td></td>';
                }
                html += '</tr>';

                // 澳门赔率行
                if (mco.length >= 3) {
                    html += '<tr><td colspan="4" style="padding:3px 0 1px;color:#94a3b8;font-size:10.5px;font-weight:600;border-top:1px solid #334155">\u6fb3\u95e8\u8d54\u7387\uff08\u5373\u65f6 / \u53d8\u5316\uff09</td></tr>';
                    html += '<tr>';
                    html += '<td style="text-align:center;padding:2px"><span style="color:#94a3b8;font-size:10px">\u4e3b</span><br><strong style="color:#60a5fa;font-size:13px">' + (mco[0]||'-') + '</strong></td>';
                    html += '<td style="text-align:center;padding:2px"><span style="color:#94a3b8;font-size:10px">\u5e73</span><br><strong style="color:#fbbf24;font-size:13px">' + (mco[1]||'-') + '</strong></td>';
                    html += '<td style="text-align:center;padding:2px"><span style="color:#94a3b8;font-size:10px">\u5ba2</span><br><strong style="color:#a78bfa;font-size:13px">' + (mco[2]||'-') + '</strong></td>';
                    if (mcaoInit.length >= 3) {
                        html += '<td style="text-align:right;padding:2px;white-space:nowrap;vertical-align:bottom;border-left:1px solid #334155;padding-left:8px">';
                        html += '<span style="color:#64748b;font-size:9px">\u53d8\u5316:</span> ';
                        html += _arrow(mco[0], mcaoInit[0]) + ' ';
                        html += _arrow(mco[1], mcaoInit[1]) + ' ';
                        html += _arrow(mco[2], mcaoInit[2]);
                        html += '</td>';
                    } else {
                        html += '<td></td>';
                    }
                    html += '</tr>';
                }

                html += '</table></div>';
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
        
        // ========================================
        // 🧊 相似冷门模式参考
        // ========================================
        // 只显示有意义的匹配（≥20分）
        const simUpsets = (res.similar_upsets || []).filter(function(u) { return u._match_score >= 20; });
        const upsetsStats = res.upsets_stats || {};
        
        if (simUpsets.length > 0) {
            // 计算最高相似度决定警告等级
            var maxScore = Math.max(...simUpsets.map(function(u){return u._match_score;}));
            var warnLevel = maxScore >= 50 ? 'danger' : (maxScore >= 35 ? 'warning' : 'info');
            var levelCfg = {
                danger: {title:'🚨 冷门模式警告', color:'#f87171', bg:'rgba(239,68,68,0.12)', border:'rgba(239,68,68,0.35)', advice:'强烈建议：降低信心/控制仓位或直接观望！'},
                warning: {title:'⚠️ 相似冷门参考', color:'#fbbf24', bg:'rgba(251,191,36,0.10)', border:'rgba(251,191,36,0.30)', advice:'建议：适当降低投注信心，注意被排除方向。'},
                info:   {title:'📋 历史冷门参考（弱相关）', color:'#60a5fa', bg:'rgba(96,165,250,0.08)', border:'rgba(96,165,250,0.20)', advice:'仅供参考：与少量历史冷门有部分特征重合，但相关性不高。'}
            };
            var lc = levelCfg[warnLevel];
            
            html += `
        <div class="section">
            <div class="section-title"><span style="color:${lc.color};font-size:16px">${lc.title}</span>（${simUpsets.length}条相似 · 最高${maxScore}分）
            </div>
            <div style="font-size:11px;color:${lc.color};margin-bottom:8px;line-height:1.6">
                ${warnLevel === 'danger' ? '<b>本场与多条历史爆冷案例高度相似！需格外警惕。</b>' : '以下历史比赛与本场有部分相似特征。'}
                &nbsp;|&nbsp; 📊 冷门库共 ${upsetsStats.total || 0} 条记录
            </div>`;
            
            simUpsets.forEach(function(u, ui) {
                var uType = u.upset_type || 'unknown';
                var typeColors = {
                    'silent': {bg:'#1e3a5f', border:'#3b82f6', text:'#93c5fd', icon:'🔇'},
                    'reverse_cover': {bg:'#3f2a2a', border:'#ef4444', text:'#fca5a5', icon:'🔄'},
                    'heat_trap': {bg:'#3f3510', border:'#f59e0b', text:'#fcd34d', icon:'🔥'},
                    'unknown': {bg:'#2d2d3a', border:'#6b7280', text:'#9ca3af', icon:'❓'}
                };
                var tc = typeColors[uType] || typeColors['unknown'];
                var dirCn = {home:'主胜', draw:'平局', away:'客胜'}[u.actual_result] || '?';
                
                html += `
            <div style="margin-bottom:10px;padding:10px;background:${tc.bg};border:1px solid ${tc.border};border-radius:8px">
                <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:4px;margin-bottom:6px">
                    <div style="display:flex;align-items:center;gap:6px">
                        <b style="font-size:13px;color:#e2e8f0">${u.home_team} vs ${u.away_team}</b>
                        <span style="background:rgba(239,68,68,0.25);color:${tc.text};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">${u.actual_score || '?'}</span>
                        <span style="background:${tc.border}33;color:${tc.text};padding:2px 7px;border-radius:4px;font-size:11px">${tc.icon} ${u.upset_type_cn || ''}</span>
                    </div>
                    <span style="font-size:10px;color:#64748b">相似度:<b style="color:${u._match_score>=40?'#f87171':u._match_score>=25?'#fbbf24':'#94a3b8'}">${u._match_score}</b></span>
                </div>
                <div style="font-size:11px;color:#94a3b8;margin-bottom:4px">
                    ${u.league || ''} | 预测<u>${u.prediction}</u> → 实际<b style="color:#f87171">${dirCn}</b>
                    | 置信度:${u.confidence}★ | 心水:${u.macao_tip || '-'}
                    | 爆冷赔率:${u.upset_odds || '?'}
                </div>`;
                
                if (u._match_reasons && u._match_reasons.length > 0) {
                    html += '<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:2px">';
                    for (var ri=0; ri<u._match_reasons.length && ri<4; ri++) {
                        html += '<span style="font-size:10px;background:rgba(239,68,68,0.15);color:#fca5a5;padding:1px 6px;border-radius:3px;display:inline-block">' + u._match_reasons[ri] + '</span>';
                    }
                    html += '</div>';
                }
                
                html += '</div>';
            });
            
            // 冷门模式总结建议（动态等级）
            var adviceText = {
                danger: '本场与多条历史冷门高度相似（≥50分）！赔率+基本面特征高度吻合。强烈建议跳过或极小仓位试探。',
                warning: '本场与历史冷门有较明显相似（35~49分）。建议降低投注信心，控制仓位，留意被排除方向。',
                info:   '与少量历史冷门有部分特征重合（20~34分）。仅供参考，不单独作为决策依据。'
            };
            html += `
            <div style="margin-top:10px;padding:10px 14px;background:${lc.bg};border:1px solid ${lc.border};border-radius:8px">
                <span style="color:${lc.color};font-weight:bold;font-size:13px">${warnLevel === 'danger' ? '⚠️ 警告' : (warnLevel === 'warning' ? '💡 注意' : '📌 参考')}：${adviceText[warnLevel]}</span>
            </div>`;
            
            html += '</div>';
        }
        
        // ========================================
        // ⚡ 二次分析 · 历史验证（三大模块）
        // ========================================
        
        // --- ① 集体投票模块 ---
        var voteHtml = '';
        var predVotes = {'主胜':0, '平局':0, '客胜':0, '观望':0};
        var excOverlap = {'home':0, 'draw':0, 'away':0};
        var correctByPred = {'主胜':{'hit':0,'total':0}, '平局':{'hit':0,'total':0}, '客胜':{'hit':0,'total':0}, '观望':{'hit':0,'total':0}};
        
        simReviews.forEach(function(r) {
            var p = (r.prediction || '').replace(/ /g, '');
            if (p.indexOf('主胜') >= 0) { predVotes['主胜']++; correctByPred['主胜']['total']++; if(r.is_correct) correctByPred['主胜']['hit']++; }
            else if (p.indexOf('平局') >= 0) { predVotes['平局']++; correctByPred['平局']['total']++; if(r.is_correct) correctByPred['平局']['hit']++; }
            else if (p.indexOf('客胜') >= 0) { predVotes['客胜']++; correctByPred['客胜']['total']++; if(r.is_correct) correctByPred['客胜']['hit']++; }
            else { predVotes['观望']++; }
            
            (r.exclusions || []).forEach(function(e) {
                if (excOverlap[e] !== undefined) excOverlap[e]++;
            });
        });
        
        // 找出投票最多的方向
        var maxVote = 0, topVoteDir = '';
        Object.keys(predVotes).forEach(function(k) { if(predVotes[k] > maxVote) { maxVote = predVotes[k]; topVoteDir = k; }});
        
        // 找出排除重叠最高的方向
        var maxExc = 0, topExcDir = '';
        Object.keys(excOverlap).forEach(function(k) { if(excOverlap[k] > maxExc) { maxExc = excOverlap[k]; topExcDir = k; }});
        
        // 当前基础预测
        var basePred = (res.analysis || {}).final_prediction || res.final_prediction || '';
        var baseConf = (res.analysis || {}).confidence || res.confidence || 0;
        
        // 投票结论
        var voteVerdict = '', voteVerdictColor = '#fbbf24';
        if (basePred.indexOf(topVoteDir) >= 0 && maxVote >= Math.ceil(simReviews.length / 2)) {
            voteVerdict = '✅ 历史多数案例支持你的方向（' + maxVote + '/' + simReviews.length + '票）';
            voteVerdictColor = '#4ade80';
        } else if (topVoteDir && !basePred.includes(topVoteDir) && maxVote >= 2) {
            voteVerdict = '⚠️ 历史案例更倾向「' + topVoteDir + '」（' + maxVote + '票），与你的预测不同';
            voteVerdictColor = '#f87171';
        } else {
            voteVerdict = '📊 方向分散，无绝对多数';
            voteVerdictColor = '#fbbf24';
        }
        
        // 排除重叠描述
        var excNames = {home:'主', draw:'平', away:'客'};
        var excText = [];
        if (excOverlap.home > 0 && excOverlap.home === simReviews.length) excText.push('全排除主');
        if (excOverlap.draw > 0 && excOverlap.draw === simReviews.length) excText.push('全排除平');
        if (excOverlap.away > 0 && excOverlap.away === simReviews.length) excText.push('全排除客');
        var excSummary = excText.length > 0 ? excText.join('、') : ('排除较分散：主'+(excOverlap.home||0)+'·平'+(excOverlap.draw||0)+'·客'+(excOverlap.away||0));
        
        voteHtml += '<div class="section"><div class="section-title"><span class="icon icon-green">📊</span> 集体投票 — 相似案例统计</div>';
        voteHtml += '<div style="background:#0c1222;border-radius:10px;padding:14px;border:1px solid #1e293b">';
        
        // 方向分布条
        voteHtml += '<div style="margin-bottom:12px"><div style="font-size:11px;color:#94a3b8;margin-bottom:5px;font-weight:600">📌 预测方向分布</div><div style="display:flex;gap:4px;height:28px">';
        var dirColors = {'主胜':'#4ade80', '平局':'#fbbf24', '客胜':'#fca5a5', '观望':'#94a3b8'};
        ['主胜','平局','客胜','观望'].forEach(function(d) {
            var pct = simReviews.length > 0 ? Math.round(predVotes[d]/simReviews.length*100) : 0;
            var hitInfo = correctByPred[d];
            var rate = hitInfo.total > 0 ? Math.round(hitInfo.hit/hitInfo.total*100) : 0;
            voteHtml += '<div style="flex:'+predVotes[d]+';min-width:30px;background:' + dirColors[d] + '22;border-radius:4px;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden">';
            voteHtml += '<span style="font-size:11px;font-weight:bold;color:#fff;z-index:1;text-shadow:0 1px 2px rgba(0,0,0,0.5)">' + d.slice(0,1) + '(' + predVotes[d] + ')</span>';
            voteHtml += '<div style="position:absolute;bottom:0;left:0;width:100%;height:' + (100-rate) + '%;background:rgba(0,0,0,0.25)"></div></div>';
        });
        voteHtml += '</div></div>';
        
        // 排除重叠
        voteHtml += '<div style="margin-bottom:12px"><div style="font-size:11px;color:#94a3b8;margin-bottom:5px;font-weight:600">🚫 排除方向重叠度</div>';
        voteHtml += '<div style="display:flex;gap:12px;flex-wrap:wrap">';
        ['home','draw','away'].forEach(function(dk) {
            var v = excOverlap[dk] || 0;
            var isFull = v === simReviews.length && simReviews.length > 0;
            var bg = isFull ? 'rgba(239,68,68,0.15)' : 'rgba(51,65,85,0.5)';
            var border = isFull ? '1px solid #ef4444' : '1px solid #334155';
            var color = isFull ? '#f87171' : '#94a3b8';
            voteHtml += '<div style="padding:6px 16px;border-radius:20px;background:' + bg + ';border:' + border + ';text-align:center">';
            voteHtml += '<div style="font-size:11px;color:' + color + ';font-weight:bold">' + excNames[dk] + '</div>';
            voteHtml += '<div style="font-size:13px;color:#fff;font-weight:bold;margin-top:1px">' + v + '/' + simReviews.length + (isFull ? ' ✓' : '') + '</div></div>';
        });
        voteHtml += '</div><div style="font-size:10.5px;color:#64748b;margin-top:4px">→ ' + excSummary + '</div></div>';
        
        // 投票结论
        voteHtml += '<div style="padding:10px 12px;background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.25);border-radius:8px;text-align:center">';
        voteHtml += '<div style="font-size:13px;color:' + voteVerdictColor + ';font-weight:bold">' + voteVerdict + '</div></div>';
        voteHtml += '</div></div>';
        html += voteHtml;
        
        // ================================================
        // 🔥 二次分析核心：三方向独立排除引擎 v2.0
        // ================================================
        // 核心理念：不对原预测打分，而是对 主/平/客 三个方向
        // 分别判断"它为什么不该出"，给出排除置信度。
        // 排除掉的方向越多，剩余方向越可靠。
        
        var _an = res.analysis || {};
        var signals = _an.signals || [];
        var exclusions_now = _an.exclusions || [];
        var match_type = _an.match_type || '';
        var macaoTip = _an.macao_tip || '';
        var formDiff = _an.form_diff || 0;
        var odds_real = {};
        // ★ 关键：提取30家公司全量赔率，用于R1绝对值判断
        var allRealOdds = {home:[], draw:[], away:[]};
        var maxOdds = {home: 0, draw: 0, away: 0};
        
        // ★★★ 必须在try块之前定义eng对象！★★★
        // ---- 排除引擎数据结构 ----
        // score: 正=保留证据强, 负=排除证据强 (-100 ~ +100)
        // status: 'keep' | 'weak_exclude' | 'strong_exclude' | 'unknown'
        var eng = {
            home: { name:'主胜', score:0, evs:[], color:'#4ade80' },
            draw: { name:'平局', score:0, evs:[], color:'#fbbf24' },
            away: { name:'客胜', score:0, evs:[], color:'#fca5a5' }
        };
        
        var jcReal = odds_real.jc_real || [];
        var jcInit = odds_real.jc_init || [];
        
        try { 
            // ★ V4关键修复：res.raw_data可能已经是对象
            var _rd = (typeof res.raw_data === 'string') ? JSON.parse(res.raw_data || '{}') : (res.raw_data || {});
            
            // 提取竞彩/澳门赔率
            if (_rd.initial_odds && _rd.initial_odds.length > 1) odds_real.jc_init = _rd.initial_odds[1].slice(0,3);
            if (_rd.realtime_odds && _rd.realtime_odds.length > 1) odds_real.jc_real = _rd.realtime_odds[1].slice(0,3);
            if (_rd.initial_odds && _rd.initial_odds.length > 2) odds_real.mac_init = _rd.initial_odds[2].slice(0,3);
            if (_rd.realtime_odds && _rd.realtime_odds.length > 2) odds_real.mac_real = _rd.realtime_odds[2].slice(0,3);
            
            // 提取30家公司全部即时赔率
            if (_rd.realtime_odds && Array.isArray(_rd.realtime_odds) && _rd.realtime_odds.length > 0) {
                for(var ri=0; ri<_rd.realtime_odds.length; ri++) {
                    var row = _rd.realtime_odds[ri];
                    if(Array.isArray(row) && row.length>=3) {
                        var h=Number(row[0]), d=Number(row[1]), a=Number(row[2]);
                        if(h>0) allRealOdds.home.push(h);
                        if(d>0) allRealOdds.draw.push(d);
                        if(a>0) allRealOdds.away.push(a);
                    }
                }
                maxOdds.home = allRealOdds.home.length ? Math.max.apply(null, allRealOdds.home) : 0;
                maxOdds.draw = allRealOdds.draw.length ? Math.max.apply(null, allRealOdds.draw) : 0;
                maxOdds.away = allRealOdds.away.length ? Math.max.apply(null, allRealOdds.away) : 0;
            }
            
            // ★★★ 更新jcReal/jcInit（前面已经提取过）
            jcReal = odds_real.jc_real || [];
            jcInit = odds_real.jc_init || [];
            
            // ════════════════════════════════════
            // 【R8-B】澳门推荐和局+和局赔率升的反向冷门检测（2026-04-12新增）
            // ════════════════════════════════════
            var _tip = (_rd && _rd.macao_tip) ? _rd.macao_tip : '';
            console.log('[DEBUG R8-B] _tip=', _tip, 'jcInit=', jcInit, 'jcReal=', jcReal);
            
            if (jcInit.length === 3 && jcReal.length === 3) {
                var drawOddsNow = jcReal[1];
                var drawOddsInit = jcInit[1];
                console.log('[DEBUG R8-B] drawOddsNow=', drawOddsNow, 'drawOddsInit=', drawOddsInit);
                
                if (drawOddsInit > 0) {
                    var drawChgPct = (drawOddsNow - drawOddsInit) / drawOddsInit * 100;
                    var homeChgPct = (jcReal[0] - jcInit[0]) / jcInit[0] * 100;
                    var awayChgPct = (jcReal[2] - jcInit[2]) / jcInit[2] * 100;
                    console.log('[DEBUG R8-B] drawChgPct=', drawChgPct.toFixed(2), 'homeChgPct=', homeChgPct.toFixed(2), 'awayChgPct=', awayChgPct.toFixed(2));
                    
                    // 条件：澳门推荐和局 + 和局赔率≥3.3 + 和局赔率上升/基本不变 + 客胜/主胜在降赔
                    var macaoRecommendsDraw = (_tip && (_tip.indexOf('和')>=0 || _tip.indexOf('平')>=0 || _tip.indexOf('分')>=0));
                    var drawRising = (drawChgPct >= 0);
                    var drawHighEnough = (drawOddsNow >= 3.3);
                    var awayDropping = (awayChgPct < -2);
                    var homeDropping = (homeChgPct < -2);
                    console.log('[DEBUG R8-B] macaoRecommendsDraw=', macaoRecommendsDraw, 'drawRising=', drawRising, 'drawHighEnough=', drawHighEnough, 'awayDropping=', awayDropping, 'homeDropping=', homeDropping);
                    
                    if (macaoRecommendsDraw && drawRising && drawHighEnough && (awayDropping || homeDropping)) {
                        var r8bScore = 0;
                        var r8bReasons = [];
                        r8bScore += 20; r8bReasons.push('澳门推荐和局');
                        if (drawChgPct >= 3) { r8bScore += 25; r8bReasons.push('和局赔率升'+drawChgPct.toFixed(1)+'%'); }
                        else if (drawChgPct >= 0) { r8bScore += 15; r8bReasons.push('和局赔率基本不变'); }
                        if (awayDropping) { r8bScore += 20; r8bReasons.push('客胜降赔'+awayChgPct.toFixed(1)+'%'); }
                        if (homeDropping) { r8bScore += 15; r8bReasons.push('主胜降赔'+homeChgPct.toFixed(1)+'%'); }
                        if (drawOddsNow >= 3.5) { r8bScore += 15; r8bReasons.push('和局赔率'+drawOddsNow+'够高'); }
                        
                        // 保存R8-B结果
                        eng._r8bScore = r8bScore;
                        eng._r8bReasons = r8bReasons;
                        eng._r8bDrawOdds = drawOddsNow;
                        console.log('[DEBUG R8-B] ★触发！r8bScore=', r8bScore, 'reasons=', r8bReasons);
                    } else {
                        console.log('[DEBUG R8-B] 条件不满足，未触发');
                    }
                }
            }
        } catch(e) { console.log('[DEBUG R8-B] Error:', e); }
        
        console.log('[DEBUG R8-B] eng._r8bScore=', eng._r8bScore);
        
        function addEv(dir, delta, text, rule) {
            eng[dir].score += delta;
            eng[dir].evs.push({d:delta, t:text, r:rule});
        }
        
        function dirOfTip(tip) {
            if (!tip) return null;
            if (tip.indexOf('主')>=0 && tip.indexOf('客')<0) return 'home';
            if (tip.indexOf('平')>=0 || tip.indexOf('和')>=0) return 'draw';
            if (tip.indexOf('客')>=0) return 'away';
            return null;
        }
        function tipOdds() {
            if (!macaoTip || jcReal.length<3) return 0;
            var di = dirOfTip(macaoTip);
            return di!==null ? jcReal[{home:0,draw:1,away:2}[di]] : 0;
        }
        
        // ════════════════════════════════════
        // 规则集：每条规则对特定方向加减分
        // ════════════════════════════════════
        
        // 【R1】赔率绝对值排除（最强信号）
        // ★ V2修复：用30家公司最大赔率(maxOdds)判断，而非仅竞彩一家(jcReal)
        // 原因：竞彩官方可能[1.90,3.65,3.04]但30家中客胜可达8.30
        var r1Source = (allRealOdds.home.length >= 10) ? '30家公司' : '竞彩官方';
        ['home','draw','away'].forEach(function(d, i) {
            // 用30家最大值做排除判断，用jcReal值显示
            var oMax = maxOdds[d];       // 30家中该方向最大赔率
            var oJc = (jcReal.length===3) ? jcReal[i] : oMax; // 显示用
            
            if (oMax >= 6.0) addEv(d, -90, oMax.toFixed(2)+'(30家最高)≥6.0: 极端高赔基本不出('+r1Source+')', 'R1-极端赔');
            else if (oMax >= 5.0) addEv(d, -85, oMax.toFixed(2)+'(30家最高)≥5.0: 历史约90%不出('+r1Source+')', 'R1-极高赔');
            else if (oMax >= 4.0) addEv(d, -65, oMax.toFixed(2)+'(30家最高)≥4.0: 高赔方向大概率不出', 'R1-高赔');
            else if (oMax >= 3.5) {
                // 友谊赛平局例外
                if (!(match_type.indexOf('友谊')>=0 && d==='draw'))
                    addEv(d, -45, oMax.toFixed(2)+'≥3.5: 中高赔需警惕', 'R1-中高赔');
            }
            
            // 碾压检测也改用30家最小值
            if (allRealOdds[d].length >= 10) {
                var oMin = Math.min.apply(null, allRealOdds[d]);
                if (oMin < 1.35) {
                    ['home','draw','away'].forEach(function(d2) { 
                        if(d2!==d) addEv(d2, -(20+Math.round((1.35-oMin)*50)), oMin.toFixed(2)+'(最低)碾压模式:庄家不怕'+eng[d].name+'出', 'R1-碾压'); 
                    });
                }
            } else if (oJc < 1.35 && jcReal.length===3) {
                ['home','draw','away'].forEach(function(d2) { if(d2!==d) addEv(d2, -25, oJc+'极端低赔碾压模式', 'R1-碾压'); });
            }
        });
        
        // 【R2】心水排除法（Step 1 最高优先级）
        if (macaoTip) {
            var ti = dirOfTip(macaoTip);
            var to = tipOdds();
            
            // R2a: 心水赔率≥3.5 → 排除心水方向（80%命中）
            if (to >= 3.5) {
                if (ti==='draw' && to >= 5.0)
                    addEv(ti, -75, '心水推'+macaoTip+'赔率'+to.toFixed(2)+'≥5: 但心水推平局高赔不可靠(⑨号)', 'R2a-心水高赔');
                else
                    addEv(ti, -70, '心水推'+macaoTip+'但赔率高('+to.toFixed(2)+'): 80%历史不出', 'R2a-心水高赔');
            }
            // R2b: 规则B — 竞彩推离心水(升>3%) → 排除心水（4/4=100%）
            else if (jcInit.length>=3 && jcReal.length>=3 && ti!==null) {
                var idx = {home:0,draw:1,away:2}[ti];
                if (jcInit[idx] > 0 && jcReal[idx] > 0) {
                    var chg = (jcReal[idx]-jcInit[idx])/jcInit[idx]*100;
                    if (chg > 3) {
                        addEv(ti, -80, '规则B:竞彩对心水'+macaoTip+'升'+chg.toFixed(1)+'%=言行不一(4/4=100%)', 'R2b-规则B');
                    } else if (chg < -2) {
                        // 竞彩降心水=看好该方向，反向操作
                        addEv(ti, +30, '竞彩对心水降'+Math.abs(chg).toFixed(1)+'%=实盘看好信号(非陷阱)', 'R2b-实盘信号');
                    }
                }
            }
            // R2c: 心水赔率2.0-3.0 + 无竞彩信号 → 灰色区间
            else if (to >= 2.0 && to < 3.0) {
                addEv(ti, -10, '心水赔率'+to.toFixed(2)+'在灰色区间(54.5%),无明确信号', 'R2c-灰色区');
            }
        }
        
        // 【R3】竞彩×澳门互动信号
        signals.forEach(function(s) {
            var t = s.text || '';
            
            // R3a: [不怕]X + X赔率≥3.5 → 强力排除X
            if (t.indexOf('[不怕]') >= 0) {
                var m = t.match(/(\d+\.?\d*)/g);
                var ov = parseFloat(m&&m[0])||0;
                var bd = null;
                if (t.indexOf('主')>=0&&t.indexOf('客')<0) bd='home'; 
                else if (t.indexOf('平')>=0||t.indexOf('和')>=0) bd='draw'; 
                else if (t.indexOf('客')>=0) bd='away';
                if (bd && ov >= 3.5) addEv(bd, -65, '[不怕]'+eng[bd].name+'+赔率'+ov+'≥3.5: 庄家笃定该方向不出(~88%)', 'R3a-[不怕]');
                else if (bd && ov > 0 && ov < 3.5) addEv(bd, +5, '[不怕]'+eng[bd].name+'但赔率仅'+ov+'<3.5: 不可靠(刚果案例❌)', 'R3a-[不怕]低赔');
            }
            
            // R3b: [不跟]X → X造热假象（不直接排除，降低信任）
            if (t.indexOf('[不跟]') >= 0) {
                var bd2 = null;
                if (t.indexOf('主')>=0) bd2='home'; else if (t.indexOf('平')>=0||t.indexOf('和')>=0) bd2='draw'; else if (t.indexOf('客')>=0) bd2='away';
                if (bd2) addEv(bd2, +25, '[不跟]'+eng[bd2].name+': 竞彩单独造热是假象,不代表真出', 'R3b-[不跟]');
            }
            
            // R3c: 推离信号(竞彩升>5%且澳门不同步)
            if ((t.indexOf('推离')>=0||t.indexOf('升')>=0) && s.strength >= 4) {
                var bd3 = null;
                if (t.indexOf('主')>=0&&(t.indexOf('排除主')>=0||t.indexOf('推离主')>=0)) bd3='home';
                else if (t.indexOf('平')>=0||(t.indexOf('排除平')>=0||t.indexOf('推离平')>=0)) bd3='draw';
                else if (t.indexOf('客')>=0||(t.indexOf('排除客')>=0||t.indexOf('推离客')>=0)) bd3='away';
                if (bd3) addEv(bd3, -55, '竞彩推离'+eng[bd3].name+': 庄家不想让该方向出', 'R3c-推离');
            }
        });
        
        // 【R4】历史案例投票排除
        if (simReviews.length > 0) {
            // 统计每个方向在历史案例中被排除的次数
            var excByDir = {home:0, draw:0, away:0};
            simReviews.forEach(function(r) {
                (r.exclusions||[]).forEach(function(e) {
                    if (e.indexOf('主')>=0) excByDir.home++;
                    if (e.indexOf('平')>=0||e.indexOf('和')>=0) excByDir.draw++;
                    if (e.indexOf('客')>=0) excByDir.away++;
                });
            });
            ['home','draw','away'].forEach(function(d) {
                var eCnt = excByDir[d];
                if (eCnt >= simReviews.length && simReviews.length >= 2) {
                    addEv(d, -(30+eCnt*5), simReviews.length+'条案例全部排除'+eng[d].name+'('+eCnt+'/'+simReviews.length+')', 'R4-全排除一致');
                } else if (eCnt >= Math.ceil(simReviews.length*0.7)) {
                    addEv(d, -(15+eCnt*3), '多数案例('+Math.round(eCnt/simReviews.length*100)+'%)排除'+eng[d].name, 'R4-多数排除');
                }
            });
            // 历史结果倾向
            if (topVoteDir && maxVote >= 2) {
                var tvd = topVoteDir.indexOf('主')>=0?'home':topVoteDir.indexOf('平')>=0?'draw':'away';
                if (tvd) addEv(tvd, +(maxVote*3), '历史'+maxVote+'/'+simReviews.length+'条倾向'+topVoteDir, 'R4-历史倾向');
            }
        }
        
        // 【R5】反模式陷阱检测（影响当前预测方向的可靠性）
        // R5a: 单出口全面造热陷阱
        var hasDualHeat = false, hasPush = 0;
        signals.forEach(function(s) {
            if (s.text && s.text.indexOf('同向')>=0 && s.text.indexOf('造热')>=0 && s.strength>=4) hasDualHeat=true;
            if (s.text && (s.text.indexOf('推离')>=0||s.text.indexOf('升')>=0)) hasPush++;
        });
        if (hasDualHeat && hasPush >= 2) {
            // 对当前预测方向扣分（因为当前预测很可能就是被造热的方向）
            var bp = basePred.indexOf('主')>=0?'home':basePred.indexOf('平')>=0?'draw':'away';
            addEv(bp, -50, '🔴单出口全面造热陷阱(⑭号): 三方向同向≠可靠,当前预测可能是陷阱', 'R5a-造热陷阱');
        }
        
        // R5b: 友谊赛特殊处理
        if (match_type.indexOf('友谊')>=0 && basePred!=='观望' && baseConf<=4) {
            var bp2 = basePred.indexOf('主')>=0?'home':basePred.indexOf('平')>=0?'draw':'away';
            addEv(bp2, -30, '⚠️友谊赛选'+basePred+'命中率仅33%(墨西哥❌巴西❌)', 'R5b-友谊赛');
        }
        
        // R5c: 全面分歧信号
        var sigD = {home:false,draw:false,away:false};
        signals.forEach(function(s){var t=s.text||'';if(t.indexOf('排除主')>=0)sigD.home=true;if(t.indexOf('排除平')>=0)sigD.draw=true;if(t.indexOf('排除客')>=0)sigD.away=true;});
        if (Object.keys(sigD).filter(function(k){return sigD[k]}).length >= 3) {
            // 全方向都有排除信号→反而最危险，降低所有排除分的权重
            ['home','draw','away'].forEach(function(d){ eng[d].score *= 0.5; });
        }
        
        // 【R6】掩护模式检测
        var quietDraw = false;
        signals.forEach(function(s){ if(s.text&&s.text.indexOf('平赔')>=0&&s.text.indexOf('不动')>=0) quietDraw=true; });
        if (quietDraw) {
            addEv('draw', +20, '平赔安静保护(⑬⑯⑲号): 庄家可能在掩护平局', 'R6-掩护平局');
        }
        
        // 【R7】近况差辅助
        if (formDiff !== 0) {
            if (formDiff >= 8) {
                addEv('home', +15*(Math.min(formDiff,15)/8), '近况差支持主队(+'+formDiff+')', 'R7-近况主优');
                addEv('away', -10*(Math.min(formDiff,15)/8), '近况差不利客队(-'+formDiff+')', 'R7-近况客劣');
            } else if (formDiff <= -8) {
                addEv('away', +15*(Math.min(Math.abs(formDiff),15)/8), '近况差支持客队('+formDiff+')', 'R7-近况客优');
                addEv('home', -10*(Math.min(Math.abs(formDiff),15)/8), '近况差不利于主队('+formDiff+')', 'R7-近况主劣');
            }
        }
        
        // ════════════════════════════════════
        // 【R8】冷门检测器（2026-04-12新增）
        // 核心逻辑：当"赔率变化信号"足够强时，可以覆盖"赔率绝对值排除"
        // 适用场景：阿森纳1-2伯恩茅斯、米堡1-2米尔沃尔、伯明翰0-1布莱克本
        // 特征：某方向赔率≥3.5(本应被R1排除) + 但竞彩/澳门大幅降该方向 + 多家公司同向
        // 原理：庄家在主动引导筹码去低赔方向，掩护高赔方向打出 = 典型造热陷阱
        // ════════════════════════════════════
        if (jcReal.length === 3 && allRealOdds.home.length >= 20) {
            ['home','draw','away'].forEach(function(d, i) {
                var oJc = jcReal[i];           // 竞彩即时赔率
                var oMax = maxOdds[d];         // 30家最高赔率
                var oJcInit = (jcInit.length===3) ? jcInit[i] : oJc;
                
                // 条件1：该方向赔率偏高（≥3.5），本来会被R1排除
                var isHighOdds = (oMax >= 3.5);
                
                if (!isHighOdds) return; // 只处理高赔方向
                
                // 条件2：计算竞彩对该方向的变化幅度
                var chgPct = (oJcInit > 0) ? ((oJc - oJcInit) / oJcInit * 100) : 0;
                var jcDropping = (chgPct < -4);   // 竞彩降>4%
                var jcStrongDrop = (chgPct < -7); // 竞彩降>7%（强信号）
                
                // 条件3：统计30家公司中降该方向的比例
                var dirIdx = {home:0, draw:1, away:2}[d];
                var dropCount = 0, totalCount = allRealOdds[d].length;
                if (_rd.initial_odds && _rd.initial_odds.length > 0) {
                    for(var ri=0; ri<totalCount && ri<_rd.realtime_odds.length; ri++) {
                        var initRow = _rd.initial_odds[ri];
                        var rtRow = _rd.realtime_odds[ri];
                        if(Array.isArray(initRow) && Array.isArray(rtRow) && initRow.length>dirIdx && rtRow.length>dirIdx) {
                            var oi=Number(initRow[dirIdx]), or=Number(rtRow[dirIdx]);
                            if(oi>0 && or>0 && or<oi*0.97) dropCount++; // 降>3%
                        }
                    }
                }
                var dropRatio = (totalCount > 0) ? dropCount / totalCount : 0;
                var consensusDrop = (dropCount >= 20);    // ≥20家同向降
                var strongConsensus = (dropCount >= 25);  // ≥25家强共识
                
                // 条件4：澳门是否也同向降（如果有数据）
                var macaoAgrees = false;
                if (odds_real.mac_real && odds_real.mac_init) {
                    var macDir = {home:0,draw:1,away:2}[d];
                    if(odds_real.mac_real[macDir] && odds_real.mac_init[macDir]) {
                        var mInit = Number(odds_real.mac_init[macDir]);
                        var mReal = Number(odds_real.mac_real[macDir]);
                        if(mInit > 0 && mReal < mInit * 0.96) macaoAgrees = true; // 澳门降>4%
                    }
                }

                // R8 判定逻辑：变化信号覆盖绝对值排除
                var r8Score = 0;
                var r8Reasons = [];
                
                // 基础分：竞彩大幅降赔（最关键信号）
                if (jcStrongDrop) { r8Score += 40; r8Reasons.push('竞彩强降'+chgPct.toFixed(1)+'%'); }
                else if (jcDropping) { r8Score += 25; r8Reasons.push('竞彩降'+chgPct.toFixed(1)+'%'); }
                
                // 加分：多公司共识
                if (strongConsensus) { r8Score += 30; r8Reasons.push(dropCount+'/30家强共识'); }
                else if (consensusDrop) { r8Score += 18; r8Reasons.push(dropCount+'/30家同向降'); }
                
                // 加分：澳门同向（竞彩×澳门互动确认）
                if (macaoAgrees) { r8Score += 15; r8Reasons.push('澳门同向降'); }
                
                // 加分：心水恰好推荐该方向（庄家公开建议与实际打出一致）
                var _tip = (res.raw_data && res.raw_data.macao_tip) ? res.raw_data.macao_tip : '';
                if (_tip) {
                    var tipDirs = [];
                    if (_tip.indexOf(eng['home'].name)>=0) tipDirs.push('home');
                    else if (_tip.indexOf(eng['away'].name)>=0) tipDirs.push('away');
                    if ((_tip.indexOf('和')>=0 || _tip.indexOf('平')>=0) && d==='draw') tipDirs.push('draw');
                    if (tipDirs.indexOf(d) >= 0) { r8Score += 10; r8Reasons.push('心水同向('+_tip+')'); }
                }
                
                // 最终判定：R8得分→给正分覆盖R1的负分
                // 分级覆盖策略：
                //   r8Score≥65(极端): bonus=90, 足以翻转任何R1排除
                //   r8Score≥50(强):   bonus=75, 可翻大多数排除
                //   r8Score≥35(中):   bonus=45, 减弱排除力度
                if (r8Score >= 65) {
                    var bonus = Math.min(r8Score, 90);  // 极端信号允许更高覆盖
                    addEv(d, bonus, '[R8-冷门检测⚡] '+r8Reasons.join(' + ')+': 极端变化信号强力覆盖绝对值', 'R8-冷门');
                    eng[d]._coldAlert = 'strong'; // 标记强冷门
                } else if (r8Score >= 50) {
                    var bonus = Math.min(r8Score, 75);
                    addEv(d, bonus, '[R8-冷门检测] '+r8Reasons.join(' + ')+': 变化信号覆盖绝对值', 'R8-冷门');
                    eng[d]._coldAlert = 'medium';
                } else if (r8Score >= 30) {
                    addEv(d, Math.round(r8Score * 0.7), '[R8-冷门预警] '+r8Reasons.join(' + ')+': 存在冷门可能，降低排除置信度', 'R8-预警');
                    eng[d]._coldAlert = 'weak';
                }
            });
        }
        
        // ════════════════════════════════════
        // 计算最终排除状态（V2: 阈值+相对比较）
        // ════════════════════════════════════
        var EX_STRONG = -35;    // ≤-35: 强排除（红）— 原来太严(-45),错过中等信号
        var EX_WEAK = -12;      // ≤-12: 弱排除（黄）— 原来太严(-20),多数规则无法触发
        
        ['home','draw','away'].forEach(function(d) {
            var sc = eng[d].score;
            if (sc <= EX_STRONG) eng[d].status = 'strong_exclude';
            else if (sc <= EX_WEAK) eng[d].status = 'weak_exclude';
            else if (sc > 8) eng[d].status = 'keep';
            else eng[d].status = 'neutral';
        });
        
        // ★ 相对比较：即使无人达强排除，最低分方向若明显低于其他两方 → 弱排除
        var scores = [eng.home.score, eng.draw.score, eng.away.score];
        var dirs = ['home','draw','away'];
        var minSc = Math.min.apply(null, scores);
        var midSc = scores.sort(function(a,b){return a-b})[1]; // 排序后取中间值
        // 重新获取排序后的中间分数
        var sortedSc = scores.slice().sort(function(a,b){return a-b});
        minSc = sortedSc[0];
        midSc = sortedSc[1];
        
        if (minSc > EX_WEAK && minSc < 5 && (midSc - minSc) >= 15) {
            // 最低分方向比中间高15+且自身为负 → 给个弱排除
            dirs.forEach(function(d) { if(eng[d].score===minSc && eng[d].status==='neutral') eng[d].status='weak_exclude'; });
        }
        
        // 统计排除数
        var strongExc = 0, weakExc = 0;
        ['home','draw','away'].forEach(function(d) {
            if (eng[d].status==='strong_exclude') strongExc++;
            else if (eng[d].status==='weak_exclude') weakExc++;
        });
        
        // 最终结论
        var finalDirs = [];
        var finalText = '', finalColor = '#94a3b8', finalStars = 0;
        
        ['home','draw','away'].forEach(function(d) {
            if (eng[d].status!=='strong_exclude') finalDirs.push(d);
        });
        
        if (finalDirs.length === 1) {
            var fd = finalDirs[0];
            finalText = eng[fd].name; finalColor = eng[fd].color; finalStars = 5;
        } else if (finalDirs.length === 2) {
            // 两方向剩余：比较分数，高的更可信
            var d1=finalDirs[0], d2=finalDirs[1];
            if (jcReal.length===3) {
                var o1=jcReal[{home:0,draw:1,away:2}[d1]], o2=jcReal[{home:0,draw:1,away:2}[d2]];
                if (Math.abs(o1-o2)>0.5) {
                    var lower = o1<o2?d1:d2;
                    finalText = eng[lower].name+'(优选)'; finalColor = eng[lower].color; finalStars = 4;
                } else {
                    finalText = '平局(胶着)'; finalColor = '#fbbf24'; finalStars = 3;
                }
            } else {
                finalText = eng[d1].score>eng[d2].score?eng[d1].name:eng[d2].name; finalStars = 3;
            }
        } else if (finalDirs.length === 3) {
            // 三方向均未排除：综合分数+赔率+证据给出倾向（V2增强版）
            var scores = finalDirs.map(function(d) { return {d:d, s:eng[d].score, e:eng[d].evidence}; });
            scores.sort(function(a,b){return b.s - a.s}); // 分数高排前面=更可信
            var topDir = scores[0].d;
            var topScore = scores[0].s;
            var midScore = scores[1].s;
            var botScore = scores[2].s; // 最低分=最危险
            var botDir = scores[2].d;
            
            var recText = '', recColor = '#94a3b8', recStars = 1;
            var gapTopMid = topScore - midScore;
            var gapMidBot = midScore - botScore;
            
            // 关键改进：即使无人达排除阈值，最低分方向若明显更低 → 可视为"隐性排除"
            var hasImplicitExclude = (botScore < 0 && gapMidBot >= 12);
            var hasClearLeader = (gapTopMid >= 10 && topScore > 5);
            
            if (jcReal.length===3) {
                var oH=jcReal[0], oD=jcReal[1], oA=jcReal[2];
                var minO = Math.min(oH,oD,oA);
                var maxO = Math.max(oH,oD,oA);
                
                // A类：有超高赔(>5) → 排除高赔后选低赔 = 最可靠
                if (maxO > 5.0) {
                    var lowDirs = finalDirs.filter(function(d) { return jcReal[{home:0,draw:1,away:2}[d]] <= 5.0; });
                    if (lowDirs.length === 1) {
                        recText = eng[lowDirs[0]].name+'(唯一<5)';
                        recColor = eng[lowDirs[0]].color;
                        recStars = hasClearLeader ? 4 : 3;
                    } else if (lowDirs.length === 2) {
                        var lo1=lowDirs[0], lo2=lowDirs[1];
                        var odd1=jcReal[{home:0,draw:1,away:2}[lo1]], odd2=jcReal[{home:0,draw:1,away:2}[lo2]];
                        if (Math.abs(odd1-odd2)>0.5) {
                            var prefLow = odd1<odd2?lo1:lo2;
                            recText = eng[prefLow].name+'(排除>5优选)';
                            recColor = eng[prefLow].color;
                            recStars = 3;
                        } else {
                            // 赔率接近时看分数
                            recText = eng[topDir].name+'(低赔区优选)';
                            recColor = eng[topDir].color;
                            recStars = 2;
                        }
                    }
                }
                // B类：碾压盘口(<1.35)
                else if (minO < 1.35 && maxO - minO > 3.0) {
                    var lowOdir = {0:'home',1:'draw',2:'away'}[[oH,oD,oA].indexOf(minO)];
                    recText = eng[lowOdir].name+'(碾压盘)';
                    recColor = eng[lowOdir].color;
                    recStars = 3;
                }
                // C类：分数有明显分层 → 给倾向
                else if (hasImplicitExclude || hasClearLeader) {
                    var leader = hasImplicitExclude ? topDir : topDir;
                    recText = eng[leader].name + (hasImplicitExclude ? '(排除'+eng[botDir].name+'后)' : '(分数领先)');
                    recColor = eng[leader].color;
                    recStars = hasImplicitExclude ? 3 : 2;
                }
                // D类：有微弱分数优势
                else if (gapTopMid >= 5 && topScore > 0) {
                    recText = eng[topDir].name+'(微弱倾向)';
                    recColor = eng[topDir].color;
                    recStars = 2;
                }
                else {
                    recText = '观望(无区分度)';
                    recColor = '#64748b';
                    recStars = 1;
                }
            } else {
                // 无即时赔率：纯按分数
                if (hasClearLeader) {
                    recText = eng[topDir].name+'(明显领先)';
                    recColor = eng[topDir].color;
                    recStars = 2;
                } else if (hasImplicitExclude) {
                    recText = eng[topDir].name+'(相对更优)';
                    recColor = eng[topDir].color;
                    recStars = 2;
                } else {
                    recText = '观望(数据不足)';
                    recColor = '#64748b';
                    recStars = 1;
                }
            }
            
            finalText = recText; finalColor = recColor; finalStars = recStars;
        }
        
        // 最终兜底：如果还是没有文本
        if (!finalText) {
            finalText = '观望'; finalColor = '#64748b; finalStars = 1';
        }
        
        // 友谊赛降级
        if (match_type.indexOf(' friendship')>=0 && finalStars >= 4 && strongExc < 2) {
            finalStars--; finalText += '(友谊赛降级)';
        }
        
        // ════════════════════════════════════
        // ★ V3.3 R8极端冷门降级系统（影响结论星级+文本）
        // ════════════════════════════════════
        var hasExtremeCold = false, hasMediumCold = false;
        ['home','draw','away'].forEach(function(d) {
            if (eng[d]._coldAlert === 'strong') hasExtremeCold = true;
            else if (eng[d]._coldAlert === 'medium' || eng[d]._coldAlert === 'weak') hasMediumCold = true;
        });
        
        if (hasExtremeCold) {
            // ⚡ 极端冷门：至少降1星，加冷门标记到结论文字
            finalStars = Math.max(1, finalStars - 1);
            if (finalStars >= 2) { finalText += ' ⚡冷门预警'; finalColor = '#f59e0b'; }
            else { finalText = '⚠️冷门风险高(' + finalText + ')'; finalColor = '#f97316'; }
        } else if (hasMediumCold) {
            // ⚠️ 中等冷门：不降星但标记警告
            if (finalStars >= 3) finalText += ' ⚠️冷门可能';
        }
        
        // 渲染三方向排除面板
        // ════════════════════════════════════
        var exHtml = '<div class="section"><div class="section-title"><span class="icon icon-purple">🔍</span> 三方向排除引擎</div>';
        exHtml += '<div style="background:#0c1222;border-radius:10px;padding:14px;border:1px solid #334155">';
        
        // 三方向条形图
        exHtml += '<div style="font-size:11px;color:#94a3b8;margin-bottom:8px;font-weight:600">📊 方向安全性评估（负分=排除证据 / 正分=保留证据）</div>';
        exHtml += '<div style="display:flex;flex-direction:column;gap:8px">';
        
        ['home','draw','away'].forEach(function(d) {
            var e = eng[d];
            var sc = e.score;
            // 归一化到 -100 ~ +100 显示
            var normSc = Math.max(-100, Math.min(100, sc));
            var barPct = 50 + normSc/2; // -100→0%, 0→50%, +100→100%
            
            var stColor, stText, stBg, stBorder;
            if (e.status==='strong_exclude') { stColor='#ef4444'; stText='🚫 强排除'; stBg='rgba(239,68,68,0.15)'; stBorder='1px solid rgba(239,68,68,0.4)'; }
            else if (e.status==='weak_exclude') { stColor='#fbbf24'; stText='⚠️ 弱排除'; stBg='rgba(251,191,36,0.12)'; stBorder='1px solid rgba(251,191,36,0.4)'; }
            else if (e.status==='keep') { stColor='#4ade80'; stText='✅ 安全'; stBg='rgba(74,222,128,0.1)'; stBorder='1px solid rgba(74,222,128,0.4)'; }
            else { stColor='#94a3b8'; stText='➖ 中性'; stBg='rgba(148,163,184,0.08)'; stBorder='1px solid rgba(148,163,184,0.3)'; }
            
            exHtml += '<div style="'+stBg+';border-radius:8px;border:'+stBorder+';overflow:hidden">';
            exHtml += '<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 10px">';
            exHtml += '<div style="display:flex;align-items:center;gap:8px;min-width:70px">';
            exHtml += '<span style="color:'+e.color+';font-weight:bold;font-size:14px">'+e.name+'</span>';
            exHtml += '<span style="font-size:11px;color:'+stColor+';font-weight:600;padding:2px 8px;border-radius:10px;background:rgba(0,0,0,0.2)">'+stText+'</span>';
            if (jcReal.length>2) exHtml += '<span style="font-size:11px;color:#64748b">('+jcReal[{home:0,draw:1,away:2}[d]].toFixed(2)+')</span>';
            exHtml += '</div>';
            exHtml += '<div style="font-size:13px;font-weight:bold;color:'+(sc>=0?'#4ade80':'#ef4444')+'">' + (sc>=0?'+':'') + sc + '</div>';
            exHtml += '</div>';
            
            // 分数条背景（灰底表示中性线）
            exHtml += '<div style="height:6px;background:#1e293b;border-radius:3px;margin:0 10px 8px;position:relative">';
            exHtml += '<div style="position:absolute;left:50%;top:-2px;width:2px;height:10px;background:#475569;z-index:2"></div>'; // 零线标记
            exHtml += '<div style="height:100%;border-radius:3px;width:'+barPct+'%;background:linear-gradient(to right,#ef4444 0%,#fbbf25 40%,#4ade80 60%,#22c55e 100%);transition:width 0.3s;min-width:'+(normSc<-95?'2px':'0')+'"></div>';
            exHtml += '</div>';
            
            // 关键证据（只显示最强的2条）
            var topEvs = e.evs.slice().sort(function(a,b){return Math.abs(a.d)-Math.abs(b.d)}).reverse().slice(0,2);
            if (topEvs.length > 0) {
                exHtml += '<div style="padding:0 10px 8px;display:flex;flex-direction:column;gap:3px">';
                topEvs.forEach(function(ev) {
                    var ec = ev.d<0?'#f87171':ev.d>0?'#4ade80':'#94a3b8';
                    var ep = ev.d<0?'↓ ':ev.d>0?'↑ ':'· ';
                    exHtml += '<div style="font-size:10.5px;color:'+ec+';line-height:1.4">' + ep + '[' + ev.r + '] ' + ev.t + '</div>';
                });
                if (e.evs.length > 2) exHtml += '<div style="font-size:10px;color:#475569">... 还有'+(e.evs.length-2)+'条证据</div>';
                exHtml += '</div>';
            }
            exHtml += '</div>';
        });
        exHtml += '</div>';
        
        // 最终结论框
        var conclusionBg = finalStars>=4?'rgba(74,222,128,0.08)':finalStars>=3?'rgba(251,191,36,0.08)':finalStars>=2?'rgba(96,165,250,0.08)':'rgba(239,68,68,0.12)';
        var conclusionBorder = finalStars>=4?'1px solid rgba(74,222,128,0.35)':finalStars>=3?'1px solid rgba(251,191,36,0.35)':finalStars>=2?'1px solid rgba(96,165,250,0.35)':'1px solid rgba(239,68,68,0.4)';
        
        exHtml += '<div style="margin-top:14px;padding:16px;border-radius:10px;background:'+conclusionBg+';border:'+conclusionBorder+'">';
        exHtml += '<div style="text-align:center">';
        exHtml += '<div style="font-size:11px;color:#64748b;margin-bottom:6px">排除引擎结论 · '+strongExc+'强排除 + '+weakExc+'弱排除</div>';
        
        // R8-B 反向冷门警告
        var r8bWarning = '';
        if (eng._r8bScore && eng._r8bScore >= 45) {
            var r8bLevel = eng._r8bScore >= 65 ? '⚡极端' : '⚠️中等';
            var r8bColor = eng._r8bScore >= 65 ? '#f87171' : '#fbbf24';
            r8bWarning = '<span style="color:'+r8bColor+';font-weight:bold;font-size:10px;margin-left:8px">['+r8bLevel+'反向冷门]</span>';
        }
        
        exHtml += '<div style="font-size:22px;color:'+finalColor+';font-weight:bold">';
        for(var si=0;si<finalStars;si++) exHtml+='★';
        for(var si=finalStars;si<5;si++) exHtml+='☆';
        exHtml += ' ' + finalText + r8bWarning + '</div>';
        
        // ★ 冷门预警横幅（V3.3增强版：覆盖所有有R8信号的方向，不限finalDirs；V3.4：加入R8-B检测）
        var coldDirs = [];
        
        // R8-B 反向冷门检测结果
        if (eng._r8bScore && eng._r8bScore >= 25) {
            var r8bLevel = eng._r8bScore >= 65 ? 'strong' : (eng._r8bScore >= 45 ? 'medium' : 'weak');
            coldDirs.push({d:'draw', level:r8bLevel, name:'和局', st: eng.draw.status, isR8B:true, score:eng._r8bScore, reasons:eng._r8bReasons});
        }
        
        ['home','draw','away'].forEach(function(d) {
            // 方式1：_coldAlert标记直接检测
            if (eng[d]._coldAlert) {
                // R8-B 已添加的不重复
                if (!(d === 'draw' && eng._r8bScore && eng._r8bScore >= 25)) {
                    coldDirs.push({d:d, level:eng[d]._coldAlert, name:eng[d].name, st: eng[d].status});
                }
            }
            // 方式2：扫描证据列表中的R8标签（兜底）
            else if (eng[d] && eng[d].evs) {
                var hasR8 = eng[d].evs.some(function(ev){ return ev.r && (ev.r.indexOf('R8-')===0); });
                if (hasR8) {
                    // R8-B 已添加的不重复
                    if (!(d === 'draw' && eng._r8bScore && eng._r8bScore >= 25)) {
                        coldDirs.push({d:d, level:'medium', name:eng[d].name, st: eng[d].status});
                    }
                }
            }
        });
        // 去重
        if(coldDirs.length>0) {
            var seen={}; coldDirs=coldDirs.filter(function(cd){ if(seen[cd.d]) return false; seen[cd.d]=true; return true; });
        }
        
        if (coldDirs.length > 0) {
            var bannerBg = hasExtremeCold ? 'rgba(239,68,68,0.12)' : 'rgba(251,191,36,0.1)';
            var bannerBorder = hasExtremeCold ? '#ef4444' : '#f59e0b';
            var bannerTitle = hasExtremeCold ? '🚨 极端冷门预警' : '⚠️ 冷门预警';
            exHtml += '<div style="margin-top:8px;padding:10px 12px;border-radius:6px;background:'+bannerBg+';border-left:3px solid '+bannerBorder+'">';
            exHtml += '<span style="font-size:12px;color:'+(hasExtremeCold?'#f87171':'#f59e0b')+';font-weight:bold">'+bannerTitle+'：</span>';
            exHtml += '<span style="font-size:11.5px;color:#cbd5e1">以下方向检测到造热陷阱信号</span><br>';
            coldDirs.forEach(function(cd) {
                var tag = cd.level==='strong' ? '⚡极端' : (cd.level==='medium' ? '⚠️中等' : '💡微弱');
                var stTag = cd.st==='strong_exclude' ? '(🚫强排除)' : (cd.st==='weak_exclude' ? '(⚠️弱排除)' : '');
                var dirColor = cd.level==='strong' ? '#f87171' : '#fbbf24';
                var extraInfo = '';
                if (cd.isR8B && cd.reasons) {
                    extraInfo = ' <span style="color:#a78bfa;font-size:9px">[R8-B:'+cd.reasons.join('+')+']</span>';
                }
                exHtml += '· <span style="font-weight:bold;color:'+dirColor+'">'+cd.name+'</span> <span style="color:'+dirColor+';font-size:10px">'+tag+stTag+'</span>'+extraInfo+' ';
            });
            
            // 警告文本
            var hasR8B = coldDirs.some(function(cd){ return cd.isR8B; });
            var warnText;
            if (hasExtremeCold) {
                warnText = '竞彩大幅降赔 + 多公司同向 + 澳门同向 = 典型造热陷阱！该方向可能打出，主方向结论不可信。';
            } else if (hasR8B) {
                var r8bDir = coldDirs.find(function(cd){ return cd.isR8B; });
                if (r8bDir && r8bDir.score >= 65) {
                    warnText = 'R8-B反向冷门⚡：澳门推荐和局但赔率不配合下降='+r8bDir.name+'可能打出，建议观望或极小仓。';
                } else {
                    warnText = 'R8-B检测到和局可能，请降低仓位或关注双选。';
                }
            } else {
                warnText = '存在造热陷阱迹象，建议降低投注仓位或跳过本场。';
            }
            exHtml += '<br><span style="font-size:11px;color:#94a3b8;margin-top:2px;display:inline-block">'+warnText+'</span></div>';
        }
        
        // 投注建议（V3.3：R8极端冷门时降级建议；V3.4：R8-B反向冷门时降级建议）
        var advice = '', adviceColor = '#64748b';
        var r8bHighAlert = (eng._r8bScore && eng._r8bScore >= 45); // R8-B 高分冷门
        var r8bMedAlert = (eng._r8bScore && eng._r8bScore >= 25);  // R8-B 中分冷门
        
        if (hasExtremeCold) {
            // ⚡ 极端冷门信号 → 建议观望或极小仓试探
            advice = '🚨 谨慎/观望 — 检测到⚡极端冷门造热陷阱信号（竞彩大幅降赔+多公司同向），排除方向可能打出，建议跳过或仅极小仓位试探'; adviceColor = '#ef4444';
        } else if (hasMediumCold && finalStars >= 4) {
            // ⚠️ 中等冷门 + 高星级 → 降一档
            advice = '⚠️ 控制仓位 — 存在冷门可能，如投注请控制在常规的1/2以内'; adviceColor = '#f59e0b';
        } else if (r8bHighAlert) {
            // R8-B 高分反向冷门 → 和局可能打出，警告
            var r8bDetail = eng._r8bReasons ? eng._r8bReasons.join(' + ') : '';
            advice = '⚠️ 控制仓位 — R8-B反向冷门检测到和局可能('+eng._r8bScore+'分)：'+r8bDetail; adviceColor = '#f59e0b';
        } else if (r8bMedAlert) {
            // R8-B 中分 → 存在和局可能
            var r8bDetail = eng._r8bReasons ? eng._r8bReasons.join(' + ') : '';
            advice = '🟡 注意和局 — R8-B检测('+eng._r8bScore+'分)：'+r8bDetail; adviceColor = '#fbbf24';
        } else if (finalStars >= 4 && strongExc >= 1) {
            advice = '✅ 建议投注 — 排除法置信度高，排除'+strongExc+'方向后剩余唯一选择'; adviceColor = '#22c55e';
        } else if (finalStars >= 3) {
            advice = '🟡 可小试 — 有一定排除依据，但需控制仓位'; adviceColor = '#eab308';
        } else if (finalStars === 2) {
            advice = '⚪ 谨慎参考 — 信号偏弱，仅作为辅助判断，不建议重仓'; adviceColor = '#94a3b8';
        } else {
            advice = '❌ 建议观望 — 无足够排除证据支撑，跳过本场'; adviceColor = '#ef4444';
        }
        exHtml += '<div style="margin-top:8px;padding:10px;border-radius:6px;background:rgba(0,0,0,0.2);border-left:3px solid '+adviceColor+'">';
        exHtml += '<span style="font-size:12px;color:'+adviceColor+';font-weight:bold">💰 投注建议：</span>';
        exHtml += '<span style="font-size:12px;color:#cbd5e1">'+advice+'</span></div>';
        
        // 与原预测对比
        var predMatch = (basePred.indexOf(finalText)>=0 || finalText.indexOf(basePred)>=0);
        if (!predMatch && basePred!=='观望' && finalStars>=3) {
            exHtml += '<div style="margin-top:10px;padding:10px;background:rgba(96,165,250,0.1);border:1px solid rgba(96,165,250,0.3);border-radius:8px;text-align:left">';
            exHtml += '<div style="font-size:12px;color:#60a5fa;font-weight:bold">⚡ 排除引擎与原始预测不一致</div>';
            exHtml += '<div style="font-size:11.5px;color:#cbd5e1;margin-top:4px">原始预测：<strong style="color:#f59e0b">'+basePred+'</strong> ★'.repeat(baseConf).repeat(Math.max(0,5-baseConf)?'☆'.repeat(5-baseConf):'') + '</div>';
            exHtml += '<div style="font-size:11.5px;color:#cbd5e1;margin-top:2px">引擎结论：<strong style="color:'+finalColor+'">'+finalText+'</strong></div>';
            exHtml += '<div style="font-size:10.5px;color:#64748b;margin-top:4px">排除引擎基于赔率/心水/信号等多维交叉验证得出结论，当与原始预测冲突时应优先参考引擎结果。</div>';
            exHtml += '</div>';
        }
        exHtml += '</div></div>';
        exHtml += '</div></div>';
        
        html += exHtml;
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

    // 加载让球盘相似案例（独立模块）
    if (typeof window.renderPreMatchAnalysis === 'function') {
        window.renderPreMatchAnalysis(res);
    }
}

function closeDetail() {
    var dp = document.getElementById('detailPanel');
    dp.classList.remove('show');
    dp.style.display = '';
}

function showStatus(msg, type) {
    const bar = document.getElementById('statusBar');
    bar.className = `status-bar ${type}`;
    bar.textContent = msg;
}

// 初始化（日期按钮已由服务端渲染）
initDates();

// ========================================
// 🧊 冷门模式库浏览
// ========================================
async function showUpsetsLibrary() {
    try {
        const res = await api('/api/upsets');
        if (!res.success) return;
        
        const upsets = res.data || [];
        const stats = res.stats || {};
        const total = stats.total || 0;
        const byType = stats.by_type || {};
        
        let html = `
    <button class="detail-close" onclick="closeDetail()" style="position:absolute;top:12px;right:16px;z-index:10">
    <div style="padding:24px;padding-top:8px">
            <h2 style="color:#e2e8f0;font-size:20px;margin-bottom:4px">🧊 冷门模式库</h2>
            <p style="color:#64748b;font-size:13px;margin-bottom:16px">
                自动收集复盘时检测到的"无预警爆冷"案例，用于后续分析时做模式匹配参考
            </p>
            
            <!-- 统计概览 -->
            <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px;padding:14px;background:#0f172a;border-radius:10px">
                <div style="text-align:center;min-width:80px">
                    <div style="font-size:28px;font-weight:bold;color:#f87171">${total}</div>
                    <div style="font-size:11px;color:#64748b">总记录</div>
                </div>
                ${Object.entries(byType).map(([k,v]) => {
                    const typeMap = {silent:{icon:'🔇',name:'静默型',color:'#3b82f6'},reverse_cover:{icon:'🔄',name:'反向掩护',color:'#ef4444'},heat_trap:{icon:'🔥',name:'造热陷阱',color:'#f59e0b'},unknown:{icon:'❓',name:'未知',color:'#6b7280'}};
                    const t = typeMap[k] || typeMap.unknown;
                    return `<div style="text-align:center;min-width:80px"><div style="font-size:22px;font-weight:bold;color:${t.color}">${v}</div><div style="font-size:11px;color:#64748b">${t.icon} ${t.name}</div></div>`;
                }).join('')}
                ${total === 0 ? '<div style="color:#64748b;font-size:13px;padding:20px;text-align:center">暂无冷门记录。<br/>每当你复盘一场预测错误的比赛时，系统会自动检测是否为爆冷并加入此库。</div>' : ''}
            </div>`;
        
        if (upsets.length > 0) {
            // 按类型分组
            const grouped = {};
            upsets.forEach(u => {
                const t = u.upset_type || 'unknown';
                if (!grouped[t]) grouped[t] = [];
                grouped[t].push(u);
            });
            
            Object.keys(grouped).forEach(type => {
                var items = grouped[type];
                const tc = {silent:{bg:'#1e3a5f',bd:'#3b82f6',tx:'#93c5fd',icon:'🔇',cn:'静默型：赔率完全不动'},
                           reverse_cover:{bg:'#3f2a2a',bd:'#ef4444',tx:'#fca5a5',icon:'🔄',cn:'反向掩护：被排除方向实际打出'},
                           heat_trap:{bg:'#3f3510',bd:'#f59e0b',tx:'#fcd34d',icon:'🔥',cn:'造热陷阱：有预警但不够强'},
                           unknown:{bg:'#2d2d3a',bd:'#6b7280',tx:'#9ca3af',icon:'❓',cn:'未知类型'}}[type] || {bg:'#1e293b',bd:'#475569',tx:'#94a3b8',icon:'❓',cn:type};
                
                html += `
            <div style="margin-bottom:18px">
                <h3 style="color:${tc.tx};font-size:15px;margin-bottom:8px">${tc.icon} ${tc.cn} (${items.length}场)</h3>
                <div style="overflow-x:auto">
                <table style="width:100%;border-collapse:collapse;font-size:12px">
                    <thead><tr style="background:#1e293b;color:#94a3b8">
                        <th style="padding:6px 8px;text-align:left">比赛</th>
                        <th>联赛</th>
                        <th>预测→实际</th>
                        <th>比分</th>
                        <th>赔率</th>
                        <th>置信度</th>
                        <th>竞彩变向</th>
                        <th>时间</th>
                    </tr></thead>`;
                
                items.forEach(u => {
                    const dirCn = {home:'主胜',draw:'平局',away:'客胜'}[u.actual_result]||'?';
                    const fp = u.odds_fingerprint || {};
                    html += `<tr style="border-bottom:1px solid #1e293b;background:${tc.bg}33">
                        <td style="padding:6px 8px;color:#e2e8f0;white-space:nowrap">${u.home_team}<br/><span style="color:#64748b;font-size:11px">vs ${u.away_team}</span></td>
                        <td style="color:#94a3b8;text-align:center;font-size:11px">${u.league||'-'}</td>
                        <td style="text-align:center"><span style="color:#64748b">${u.prediction||'?'}</span> → <b style="color:#f87171">${dirCn}</b>${u.was_excluded?'<br/><span style="color:#fbbf24;font-size:10px">(被排除)</span>':''}</td>
                        <td style="text-align:center;font-weight:bold;color:#fca5a5">${u.actual_score||'?'}</td>
                        <td style="text-align:center;color:#fbbf24">${u.upset_odds||'?'}</td>
                        <td style="text-align:center;color:${u.confidence>=4?'#4ade80':u.confidence>=2?'#fbbf24':'#64748b'}">${u.confidence||0}★</td>
                        <td style="text-align:center;font-size:11px;font-family:monospace;color:${fp.jc_pattern==='NNN'?'#60a5fa':'#94a3b8'}">${fp.jc_pattern||'-'}</td>
                        <td style="color:#475569;font-size:10px;text-align:center">${u.record_time||''}</td>
                    </tr>`;
                });
                
                html += `</table></div></div>`;
            });
        }
        
        html += '</div>';
        
        document.getElementById('detailContent').innerHTML = html;
        document.getElementById('detailPanel').classList.add('show');
    } catch(e) {
        console.error('加载冷门库失败:', e);
    }
}

// ========================================
// 📚 历史复盘浏览
// ========================================
async function showReviewPage() {
    try {
        const res = await api('/api/reviews');
        if (!res.success) return;
        
        const reviews = res.data || [];
        reviews.sort((a,b) => (b.review_time||'').localeCompare(a.review_time||''));
        
        let correctCount = reviews.filter(r => r.is_correct).length;
        let html = `
    <button class="detail-close" onclick="closeDetail()" style="position:absolute;top:12px;right:16px;z-index:10">
    <div style="padding:24px;padding-top:8px">
            <h2 style="color:#e2e8f0;font-size:20px;margin-bottom:4px">📚 历史复盘记录</h2>
            <p style="color:#64748b;font-size:13px;margin-bottom:16px">
                共 ${reviews.length} 条 · 命中 ${correctCount}/${reviews.length}(${reviews.length?Math.round(correctCount/reviews.length*100):0}%)
            </p>`;
            
        if (reviews.length === 0) {
            html += `<div style="color:#64748b;padding:30px;text-align:center">暂无复盘记录。在比赛列表中点击"复盘"按钮即可添加。</div>`;
        } else {
            html += `<div style="overflow-x:auto">
            <table style="width:100%;border-collapse:collapse;font-size:12px">
                <thead><tr style="background:#1e293b;color:#94a3b8">
                    <th style="padding:6px 8px;text-align:left">比赛</th>
                    <th>预测</th>
                    <th>结果</th>
                    <th>状态</th>
                    <th>置信度</th>
                    <th>排除方向</th>
                    <th>时间</th>
                </tr></thead>`;
            
            reviews.slice(0, 50).forEach(r => {
                const hitTag = r.is_correct ? 
                    '<span style="color:#4ade80">✅</span>' : '<span style="color:#f87171">❌</span>';
                html += `<tr style="border-bottom:1px solid #1e293b">
                    <td style="padding:6px 8px;white-space:nowrap;color:#e2e8f0">${r.home_team} vs ${r.away_team}<br/><span style="color:#64748b;font-size:10px">${r.league||'·'} ${r.match_id||''}</span></td>
                    <td style="text-align:center;color:#94a3b8">${r.prediction||'?'}</td>
                    <td style="text-align:center;color:#e2e8f0;font-weight:bold">${r.result_cn||'?'}</td>
                    <td style="text-align:center">${hitTag}</td>
                    <td style="text-align:center;color:${(r.confidence||0)>=4?'#4ade80':'#94a3b8'}">${r.confidence||0}★</td>
                    <td style="text-align:center;font-size:11px;color:#64748b">${(r.exclusions||[]).join('/')||'无'}</td>
                    <td style="color:#475569;font-size:10px">${r.review_time||''}</td>
                </tr>`;
            });
            
            if (reviews.length > 50) {
                html += `<tr><td colspan="7" style="text-align:center;color:#64748b;padding:8px">... 还有${reviews.length-50}条更早的记录</td></tr>`;
            }
            html += `</table></div>`;
        }
        
        html += '</div>';
        
        document.getElementById('detailContent').innerHTML = html;
        document.getElementById('detailPanel').classList.add('show');
    } catch(e) {
        console.error('加载复盘失败:', e);
    }
}

// 初始化（日期按钮已由服务端渲染）

// 页面加载时立即显示版本号
(async function() {
    try {
        const verRes = await api('/api/version');
        const el = document.getElementById('versionInfo');
        if (el && verRes.success) {
            el.textContent = '[V' + verRes.version + '] | 构建: ' + verRes.build_time;
        }
    } catch(e) {}
})();

// ESC关闭详情面板
document.addEventListener('keydown', e => { if (e.key==='Escape') closeDetail(); });
</script>
<link rel="stylesheet" href="/static/css/intelligence.css">
<script src="/static/js/intelligence-parser.js"></script>
<script src="/static/js/prematch.js"></script>
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
    # 默认绑定 0.0.0.0 以支持外部访问
    host = os.environ.get("HOST", "0.0.0.0")
    server = http.server.HTTPServer((host, port), FootballAPIHandler)
    print(f"""
============================================
  足球预测分析器 - 纯排除法框架
============================================
  服务地址: http://{host}:{port}
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
