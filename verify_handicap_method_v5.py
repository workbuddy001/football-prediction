#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
让球分析通用方法（7步法）验证脚本 V5 ✅ 完整7步法（包含比分反推）
"""
import json, os, sys

def round_stake(amount):
    """取最近2的倍数投注金额，最少2元"""
    return max(2, round(amount / 2) * 2)

# 可调参数
TOP_N = 3
TG_MERGE_THRESHOLD = 0.3
USE_DIRECTION = False
DENSITY_THRESHOLD = 1.2  # 赔率密集度：第3/第1 < 此值时跳过

def load_match_data(match_id):
    fp = f"sporttery_data/{match_id}.json"
    if not os.path.exists(fp):
        return None
    with open(fp, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_handicap_direction(home, away, handicap):
    try:
        home, away = int(home), int(away)
        hv = float(handicap)
        gd = home + hv - away
        return '让胜' if gd > 0 else ('让平' if gd == 0 else '让负')
    except:
        return None

def estimate_goals(avg_for, avg_against):
    """估算球队平均进球期望 [min, max]（放宽范围）"""
    f = avg_for
    if f < 0.5: return (0, 2)     # 极弱
    if f < 1.0: return (0, 2)     # 弱
    if f < 1.5: return (0, 3)     # 一般
    if f < 2.0: return (0, 3)     # 不错
    if f < 2.5: return (0, 4)     # 强
    return (1, 4)                  # 很强

def reverse_score(match_data, handicap, target_direction, total_range):
    """
    比分反推：基于让球方向+总进球范围，找出合理比分
    返回：候选比分列表
    """
    preview = match_data.get('preview', {})
    recent = preview.get('recent', {})
    home_list = recent.get('home', {}).get('matchList', [])[:5]
    away_list = recent.get('away', {}).get('matchList', [])[:5]
    
    hg, hc, ag, ac = [], [], [], []
    for m in home_list:
        try:
            hg.append(int(m.get('homeTeamFullCourtGoalCnt', 0) or 0))
            hc.append(int(m.get('awayTeamFullCourtGoalCnt', 0) or 0))
        except: pass
    for m in away_list:
        try:
            ag.append(int(m.get('awayTeamFullCourtGoalCnt', 0) or 0))
            ac.append(int(m.get('homeTeamFullCourtGoalCnt', 0) or 0))
        except: pass
    
    havg = sum(hg)/len(hg) if hg else 0
    hcavg = sum(hc)/len(hc) if hc else 0
    aavg = sum(ag)/len(ag) if ag else 0
    acavg = sum(ac)/len(ac) if ac else 0
    
    # 估算进/失球期望
    home_exp = estimate_goals(havg, acavg)
    away_exp = estimate_goals(aavg, hcavg)
    
    score_odds = match_data.get('score_odds', {})
    hv = float(handicap)
    candidates = []
    
    for h in range(0, 5):
        for a in range(0, 5):
            total = h + a
            
            # 总进球限制（基于总进球赔率）
            if total_range.startswith('ttg_'):
                range_part = total_range[4:]  # 去掉 "ttg_"
                if '-' in range_part:  # 如 "2-3球"
                    parts = range_part.replace('球', '').split('-')
                    lo, hi = int(parts[0]), int(parts[1])
                    if total < lo or total > hi:
                        continue
                else:  # 如 "2球"
                    g = int(range_part.replace('球', ''))
                    if total != g:
                        continue
            elif total_range == '<=3球' and total > 3:
                continue
            elif total_range == '>=3球' and total < 3:
                continue
            
            # 进球期望严格检查（在范围内才允许）
            if h < home_exp[0] or h > home_exp[1]:
                continue
            if a < away_exp[0] or a > away_exp[1]:
                continue
            
            # 方向检查
            adj = h + hv
            if adj > a:
                direction = '让胜'
            elif adj == a:
                direction = '让平'
            else:
                direction = '让负'
            
            if direction != target_direction:
                continue
            
            # 查赔率（score_odds的key是"主队:客队"格式，如"01:00"=1:0）
            sk_home = f"{h:02d}:{a:02d}"
            odds = float(score_odds.get(sk_home, 999))
            
            # 赔率>50的比分排除（但不排除无赔率数据的比分）
            if odds != 999 and odds > 50:
                continue
            
            candidates.append((h, a, total, odds))
    
    # 按赔率排序
    candidates.sort(key=lambda x: x[3])
    return candidates

def apply_7step_method(match_data):
    """
    完整7步法（含比分反推）
    """
    preview = match_data.get('preview', {})
    recent = preview.get('recent', {})
    home_list = recent.get('home', {}).get('matchList', [])[:5]
    away_list = recent.get('away', {}).get('matchList', [])[:5]
    
    # 近况
    hg, hc, ag, ac = [], [], [], []
    for m in home_list:
        try:
            hg.append(int(m.get('homeTeamFullCourtGoalCnt', 0) or 0))
            hc.append(int(m.get('awayTeamFullCourtGoalCnt', 0) or 0))
        except: pass
    for m in away_list:
        try:
            ag.append(int(m.get('awayTeamFullCourtGoalCnt', 0) or 0))
            ac.append(int(m.get('homeTeamFullCourtGoalCnt', 0) or 0))
        except: pass
    
    havg = sum(hg)/len(hg) if hg else 0
    aavg = sum(ag)/len(ag) if ag else 0
    
    # Step 1-2：不让球
    had = match_data.get('had', {})
    had_h = float(had.get('胜', 0))
    had_d = float(had.get('平', 0))
    had_a = float(had.get('负', 0))
    
    excluded = []
    if had_h > 5.0: excluded.append('让胜')
    if had_d > 3.5: excluded.append('平局')
    if had_a > 5.0: excluded.append('客胜')
    
    reasons = []
    
    # 0球赔率判断：>20时扩容总进球范围（加入大比分候选）
    ttg = match_data.get('total_goals', {})
    ttg0 = float(ttg.get('0球', 0))
    is_high_goal = (ttg0 > 20)
    if is_high_goal:
        reasons.append(f"0球赔率{ttg0}>20，扩容总进球范围（加入大比分候选）")
    
    # Step 3：总进球分析（用总进球赔率排序）
    # 收集所有进球赔率
    tg_odds = []
    for goal_str in ['0球', '1球', '2球', '3球', '4球', '5球', '6球', '7球']:
        v = ttg.get(goal_str, 0)
        if v and float(v) > 0:
            tg_odds.append((goal_str, float(v)))
    tg_odds.sort(key=lambda x: x[1])  # 赔率最低的排前面
    
    # 按0球赔率决定取前N个总进球（>20时扩容）
    n_top = 3 if is_high_goal else 2
    if tg_odds:
        top_goals = [g for g in tg_odds[:n_top]]
        g_nums = [int(g[0].replace('球', '')) for g in top_goals]
        g_nums.sort()
        if len(g_nums) >= 2 and abs(tg_odds[0][1] - tg_odds[1][1]) / tg_odds[0][1] < 0.2:
            total_range = f'ttg_{g_nums[0]}-{g_nums[-1]}球'
            reasons.append(f"总进球{'扩容' if is_high_goal else ''}：取{len(g_nums)}个={g_nums[0]}-{g_nums[-1]}球时")
        else:
            total_range = f'ttg_{g_nums[0]}球'
            reasons.append(f"总进球{'扩容' if is_high_goal else ''}：{g_nums[0]}球")
    else:
        total_range = 'ttg_不限'
        reasons.append("总进球：无赔率数据，不限")
    
    # Step 4：让球盘
    hhad = match_data.get('hhad', {})
    handicap = hhad.get('让球', '')
    hw = float(hhad.get('让胜', 0))
    hd = float(hhad.get('让平', 0))
    hl = float(hhad.get('让负', 0))
    
    if not handicap:
        return None, None, "无让球数据"
    
    prediction = None
    
    # 4.1 让负陷阱
    if had_a < 1.50 and handicap.startswith('+'):
        if hl > 2.10:
            excluded.append('让负')
            reasons.append(f"让负{hl}太高（客胜大热但让负>2.10），排除让负")
    
    # Step 6：比分反推（核心！优先总进球→比分→方向）
    # 先生成所有可能比分（不限方向）, 按总进球赔率选最佳
    
    # 6.1 从score_odds提取所有比分，按赔率排序
    score_odds = match_data.get('score_odds', {})
    all_scores = []
    for sk, so in score_odds.items():
        try:
            parts = sk.split(':')
            h, a = int(parts[0]), int(parts[1])
            o = float(so)
            if h < 6 and a < 6 and o <= 50:  # 限制范围、排除超高赔
                all_scores.append((h, a, o))
        except:
            pass
    
    # 6.2 按总进球赔率筛选（高0球时扩容到前3个）
    if tg_odds:
        n_tg = 3 if is_high_goal else 2
        top_tg = tg_odds[:n_tg]
        allowed_totals = set(int(g[0].replace('球', '')) for g in top_tg)
        reasons.append(f"总进球候选：{sorted(allowed_totals)}（{'扩容' if is_high_goal else '正常'}）")
    else:
        allowed_totals = set(range(0, 6))
    
    # 6.3 在允许的总进球数内，按比分赔率排序
    filtered = [s for s in all_scores if (s[0]+s[1]) in allowed_totals]
    
    # ✅ 旧比分规则：进球期望过滤（estimate_goals）
    if filtered:
        home_exp = estimate_goals(havg, 0)
        away_exp = estimate_goals(aavg, 0)
        old_f = [(h,a,o) for h,a,o in filtered if home_exp[0]<=h<=home_exp[1] and away_exp[0]<=a<=away_exp[1]]
        if old_f:
            filtered = old_f
    
    # ✅ 6.3b score_change过滤：比分赔率变化数据处理
    score_change = match_data.get('score_change', {})
    if score_change:
        new_filtered = []
        change_info = {}  # { (h,a): change_pct }
        for s in filtered:
            h, a, o = s
            sk = f"{h}:{a}"
            chg = score_change.get(sk, {})
            if isinstance(chg, dict):
                cp = float(chg.get('change_pct', 0)) if chg.get('change_pct') else 0
                change_info[(h,a)] = cp
                # 排除大幅升赔的比分（change_pct > 10% = 庄家推离）
                if cp > 10:
                    reasons.append(f"  排除{h}:{a}（赔率升{cp:.0f}% > 10%，庄家推离）")
                    continue
            new_filtered.append(s)
        filtered = new_filtered
        
        # 加权排序：降赔比分（change_pct < -5%）优先 + 近况匹配加权
        def sort_key(s):
            h, a, o = s
            cp = change_info.get((h,a), 0)
            # 降赔加权：降5%相当于odds打9.75折
            adj = o * (1 + cp / 100 * 0.5)  # 降赔→cp<0→adj减小→排前
            # 近况匹配加权：比分越匹配近况，排越前
            if havg > 0 or aavg > 0:
                dev = ((h - havg)**2 + (a - aavg)**2) ** 0.5
                adj *= (1 + 0.3 * dev)  # dev越小→adj越小→排前
            # 方向加权：被排除的方向排后面
            if USE_DIRECTION and handicap:
                hv = float(handicap)
                ds = '让胜' if hv + h > a else ('让平' if hv + h == a else '让负')
                if ds in excluded:
                    adj *= 1.5  # 被排除的方向排后面
            return adj
        filtered.sort(key=sort_key)
        reasons.append(f"score_change+近况加权排序完成（排除升赔>10%，降赔+近况匹配优先）")
    else:
        # 无score_change数据时，用近况+方向加权
        def sort_key_fallback(s):
            h, a, o = s
            adj = o
            # 近况匹配加权
            if havg > 0 or aavg > 0:
                dev = ((h - havg)**2 + (a - aavg)**2) ** 0.5
                adj *= (1 + 0.3 * dev)
            # 方向加权
            if USE_DIRECTION and handicap:
                hv = float(handicap)
                ds = '让胜' if hv + h > a else ('让平' if hv + h == a else '让负')
                adj *= (1.5 if ds in excluded else 1.0)
            return adj
        filtered.sort(key=sort_key_fallback)
        reasons.append("无score_change数据，按近况匹配+方向加权排序")
    
    prediction = None
    final_score = None
    top3_scores = []
    
    if filtered:
        # 取比分赔率最低的前TOP_N个
        final_score = (filtered[0][0], filtered[0][1])
        top3_scores = [(f[0], f[1], f[2]) for f in filtered[:TOP_N]]
        
        # 从最佳比分反推方向
        h_best, a_best, o_best = filtered[0]
        hv = float(handicap)
        adj = h_best + hv
        if adj > a_best:
            prediction = '让胜'
        elif adj == a_best:
            prediction = '让平'
        else:
            prediction = '让负'
        
        reasons.append(f"总进球选{tg_odds[0][0]}(赔率{tg_odds[0][1]})，最佳比分{h_best}:{a_best}(赔率{o_best})，方向{prediction}")
        
        # 检查是否被排除
        if prediction in excluded:
            # 尝试第2个比分
            for f in filtered[1:]:
                h2, a2, o2 = f
                adj2 = h2 + hv
                if adj2 > a2:
                    d2 = '让胜'
                elif adj2 == a2:
                    d2 = '让平'
                else:
                    d2 = '让负'
                if d2 not in excluded:
                    prediction = d2
                    final_score = (h2, a2)
                    reasons.append(f"调整：第2候选{h2}:{a2}(赔率{o2})，方向{prediction}")
                    break
    else:
        # 兜底：用旧逻辑
        reasons.append("无比分数据，使用赔率最低方向")
        odds_list = [('让胜', hw), ('让平', hd), ('让负', hl)]
        for d, o in odds_list:
            if d not in excluded:
                prediction = d
                break
        if not prediction:
            prediction = odds_list[0][0]
    
    # 赔率密集度过滤：前3赔率太接近时跳过（不确定性高）
    if top3_scores and len(top3_scores) >= 3:
        odds = [o for _, _, o in top3_scores[:3]]
        if odds[0] > 0 and odds[2] / odds[0] < DENSITY_THRESHOLD:
            reasons.append(f"❌ 赔率密集度过高（{odds[2]:.1f}/{odds[0]:.1f}={odds[2]/odds[0]:.1f} < {DENSITY_THRESHOLD}），跳过")
            reasons.append(f"   候选赔率：{', '.join(f'{o:.1f}' for o in odds)}")
            return None, None, None, reasons
    
    return prediction, final_score, top3_scores, reasons

def verify_matches(sample_size=15, handicap_filter=None):
    print("=" * 80)
    filter_msg = f"（仅让球{handicap_filter}）" if handicap_filter else ""
    print(f"7步法 V5 ✅ 完整流程（含比分反推）{filter_msg}")
    print("=" * 80)
    
    scores_file = "分析模板/_scores.json"
    with open(scores_file, 'r', encoding='utf-8') as f:
        scores = json.load(f)
    
    candidate_matches = []
    for key, s in scores.items():
        if not key.isdigit():
            continue
        match_id = key
        hs, aw = s.get('home_score'), s.get('away_score')
        if hs is not None and aw is not None:
            if handicap_filter:
                md = load_match_data(match_id)
                if md:
                    hh = md.get('hhad', {})
                    hc = hh.get('让球', '')
                    if hc != handicap_filter:
                        continue
                else:
                    continue
            candidate_matches.append({'match_id': match_id, 'home_score': hs, 'away_score': aw})
    
    print(f"\n找到 {len(candidate_matches)} 场有实际比分的比赛")
    
    import random
    random.seed(42)
    selected = random.sample(candidate_matches, min(sample_size, len(candidate_matches)))
    
    correct, total = 0, 0
    score_exact_correct = 0   # 精确比分命中
    score_top3_correct = 0    # 前3候选命中
    score_total_correct = 0   # 总进球命中
    total_investment = 0      # 总投注额
    total_return = 0          # 总回报
    details = []
    skipped = {'no_match_data': 0, 'no_handicap': 0, 'no_actual_direction': 0, 'no_prediction': 0}
    
    for match in selected:
        mid = match['match_id']
        hs, aw = match['home_score'], match['away_score']
        
        md = load_match_data(mid)
        if not md:
            skipped['no_match_data'] += 1
            continue
        
        hhad = md.get('hhad', {})
        handicap = hhad.get('让球', '')
        if not handicap:
            skipped['no_handicap'] += 1
            continue
        
        ad = get_handicap_direction(hs, aw, handicap)
        if not ad:
            skipped['no_actual_direction'] += 1
            continue
        
        pred, pred_score, top3_scores, reasons = apply_7step_method(md)
        if not pred:
            skipped['no_prediction'] += 1
            continue
        
        ok = (pred == ad)
        if ok:
            correct += 1
        total += 1
        
        # 比分命中检查
        ah, aa = int(hs), int(aw)
        
        # 精确比分命中
        if pred_score:
            ph, pa = pred_score
            if ph == ah and pa == aa:
                score_exact_correct += 1
            if ph + pa == ah + aa:
                score_total_correct += 1
        
        # ROI计算：按赔率权重分配（赔率低的多投）
        N = TOP_N
        match_investment = 0
        match_return = 0
        if top3_scores:
            scores_to_bet = list(top3_scores[:N])
            inv_odds = [1.0/max(o, 1.1) for _, _, o in scores_to_bet]  # 防止除以0
            total_w = sum(inv_odds)
            raw_stakes = [(inv_odds[i] / total_w) * 30 for i in range(N)]
            stakes = [round_stake(s) for s in raw_stakes]
            # 保证总额为偶数
            if sum(stakes) % 2 != 0:
                idx = stakes.index(max(stakes))
                stakes[idx] += 1
            for idx, (h, a, o) in enumerate(scores_to_bet):
                stake = stakes[idx]
                match_investment += stake
                if h == ah and a == aa:
                    score_top3_correct += 1
                    match_return = o * stake
                    break
        
        total_investment += match_investment
        total_return += match_return
        
        details.append({'match_id': mid, 'handicap': handicap, 'prediction': pred, 'pred_score': pred_score, 'top3_scores': top3_scores, 'actual': ad, 'actual_score': f'{hs}:{aw}', 'correct': ok, 'hit_return': match_return, 'reasons': reasons})
    
    print(f"跳过统计：{skipped}")
    print("=" * 80)
    print(f"验证结果：{correct}/{total} 正确（方向准确率 {correct/total*100:.1f}%）")
    if score_exact_correct:
        print(f"精确比分命中（最佳1个）：{score_exact_correct}/{total}（{score_exact_correct/total*100:.1f}%）")
    if score_top3_correct:
        print(f"比分命中（前2候选）：{score_top3_correct}/{total}（{score_top3_correct/total*100:.1f}%）")
    if score_total_correct:
        print(f"总进球命中：{score_total_correct}/{total}（{score_total_correct/total*100:.1f}%）")
    
    # ROI计算
    roi = (total_return - total_investment) / total_investment * 100
    print(f"\n💰 ROI分析（每场投前{TOP_N}个比分×10元）：")
    print(f"   总投注：{total_investment}元（{total}场×{TOP_N*10}元）")
    print(f"   总回报：{total_return:.0f}元")
    print(f"   ROI：{roi:+.1f}%")
    print(f"   平均每场回报：{total_return/total:.1f}元")
    print("=" * 80)
    
    for i, d in enumerate(details, 1):
        status = "✅" if d['correct'] else "❌"
        pred_score_str = f"{d['pred_score'][0]}:{d['pred_score'][1]}" if d['pred_score'] else "无比分"
        top3_str = ', '.join(f"{h}:{a}" for h, a, o in d['top3_scores']) if d.get('top3_scores') else "-"
        match_top3 = "✅" if any(h == int(d['actual_score'].split(':')[0]) and a == int(d['actual_score'].split(':')[1]) for h, a, o in d['top3_scores']) else ""
        print(f"\n{i}. {d['match_id']} (让球{d['handicap']}) 实际{d['actual_score']}")
        print(f"   预测方向：{d['prediction']} {status} | 最佳比分：{pred_score_str} | 前3候选：[{top3_str}] {match_top3}")
        for r in d['reasons']:
            print(f"   - {r}")
    
    return correct, total

if __name__ == '__main__':
    import sys
    n = 15
    hf = None
    N = 3           # 每场投前N个比分
    threshold = 0.3  # 总进球合并阈值
    use_direction = False  # 方向加权
    density = 1.2  # 赔率密集度阈值
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == '--handicap' and i+1 < len(sys.argv):
            hf = sys.argv[i+1]; i += 2
        elif a == '--top' and i+1 < len(sys.argv):
            N = int(sys.argv[i+1]); i += 2
        elif a == '--threshold' and i+1 < len(sys.argv):
            threshold = float(sys.argv[i+1]); i += 2
        elif a == '--density' and i+1 < len(sys.argv):
            density = float(sys.argv[i+1]); i += 2
        elif a == '--direction':
            use_direction = True; i += 1
        elif not a.startswith('--'):
            n = int(a); i += 1
        else:
            i += 1
    
    # 设置参数
    TOP_N = N
    TG_MERGE_THRESHOLD = threshold
    USE_DIRECTION = use_direction
    DENSITY_THRESHOLD = density
    verify_matches(sample_size=n, handicap_filter=hf)
