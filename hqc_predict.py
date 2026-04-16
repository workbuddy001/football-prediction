"""
hqc_predict.py  v3
半全场预测引擎（含全场赔率联合分析 + 球队状态）

预测维度（7维加权）：
  1. 全局历史命中率            (22%)
  2. 半全场赔率区间命中率       (18%)
  3. 市场隐含概率（逆赔率归一）  (12%)
  4. 联赛偏向                  (8%)
  5. ★全场倾向×半全场结果概率   (18%) ← 新增
  6. ★全场主胜赔率区间命中率    (10%) ← 新增
  7. ★球队状态系数             (12%) ← v3新增
"""
import json
import os
from collections import defaultdict
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hqc_data")
HQC_CN_LABELS   = ['胜胜', '胜平', '胜负', '平胜', '平平', '平负', '负胜', '负平', '负负']
SPF_BIAS_LABELS = ['强主', '弱主', '均势', '弱客', '强客']

# ── 权重配置 v2 ──
WEIGHT_GLOBAL_RATE   = 0.22   # 全局命中率
WEIGHT_ODDS_BUCKET   = 0.18   # 半全场赔率区间历史命中率
WEIGHT_INVERSE_ODDS  = 0.12   # 半全场逆赔率（市场隐含概率）
WEIGHT_LEAGUE_BIAS   = 0.08   # 联赛偏向
WEIGHT_SPF_BIAS      = 0.18   # ★ 全场倾向×半全场条件概率
WEIGHT_SPF_WIN_BIN   = 0.10   # ★ 全场主胜赔率区间命中率
WEIGHT_TEAM_FORM      = 0.12   # ★ 球队状态系数（v3新增）

# ── v3: 神奇尾数排除规则 ───────────────────────────────────
# 命中率低于22%且样本量>=30场的赔率尾数，在推荐时降权或排除
MAGIC_BAD_SUFFIXES = [
    '.00', '.50',  # 整角/半角：极低命中率（5.7%/11.1%）
    '.75', '.95',  # 用户指定神奇尾数（12.3%/10.9%）
    '.60', '.80',  # 6/8结尾（16.9%/15.9%）
    '.30', '.70',  # 3/7结尾（19.8%/12.5%）
    '.10', '.90',  # 1/9结尾（9.4%/11.1%）
    '.25', '.15', '.35',  # 5/15/35结尾（17.1%/17.4%/19.0%）
]


def _is_magic_bad(odds_val):
    """判断赔率尾数是否属于低命中率神奇尾数"""
    if odds_val <= 0:
        return False
    frac = f'{odds_val:.2f}'[-2:]
    return f'.{frac}' in MAGIC_BAD_SUFFIXES

HQC_ODDS_BINS = [
    (1.0,  2.0),
    (2.0,  4.0),
    (4.0,  8.0),
    (8.0,  15.0),
    (15.0, 30.0),
    (30.0, 999),
]

SPF_WIN_BINS = [
    (1.0,  1.5,  "主赔<1.5（超强主）"),
    (1.5,  2.0,  "主赔1.5-2.0（强主）"),
    (2.0,  2.8,  "主赔2.0-2.8（弱主）"),
    (2.8,  3.5,  "主赔2.8-3.5（均势偏主）"),
    (3.5,  5.0,  "主赔3.5-5.0（均势）"),
    (5.0,  8.0,  "主赔5.0-8.0（偏客）"),
    (8.0,  999,  "主赔8.0+（强客）"),
]


def load_stats():
    report_file = os.path.join(DATA_DIR, 'hqc_analysis_report.json')
    if not os.path.exists(report_file):
        print("[!] 未找到分析报告，请先运行 hqc_stats.py")
        return None
    with open(report_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_all_data():
    all_matches = []
    if not os.path.exists(DATA_DIR):
        return all_matches
    for fname in sorted(os.listdir(DATA_DIR)):
        if (fname.startswith('hqc_') and fname.endswith('.json')
                and 'summary' not in fname and 'predict' not in fname
                and 'report' not in fname and 'analysis' not in fname):
            fpath = os.path.join(DATA_DIR, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    all_matches.extend([m for m in data if isinstance(m, dict)])
            except Exception:
                pass
    return all_matches


def get_hqc_bin(odds_val):
    for i, (lo, hi) in enumerate(HQC_ODDS_BINS):
        if lo <= odds_val < hi:
            return i
    return len(HQC_ODDS_BINS) - 1


def get_spf_win_bin_name(win_odds):
    for lo, hi, name in SPF_WIN_BINS:
        if lo <= win_odds < hi:
            return name
    return None


def build_hqc_bin_hit_rate(history):
    """半全场赔率区间×结果 历史命中率"""
    bin_data = defaultdict(lambda: defaultdict(lambda: {'total': 0, 'hit': 0}))
    for m in history:
        if not m.get('半全场结果') or not m.get('半全场赔率'):
            continue
        result = m['半全场结果']
        for label in HQC_CN_LABELS:
            o = m['半全场赔率'].get(label, 0)
            if o <= 0:
                continue
            b = get_hqc_bin(o)
            bin_data[label][b]['total'] += 1
            if label == result:
                bin_data[label][b]['hit'] += 1

    hit_rate_map = {}
    for label in HQC_CN_LABELS:
        hit_rate_map[label] = {}
        for b in range(len(HQC_ODDS_BINS)):
            d = bin_data[label][b]
            rate = d['hit'] / d['total'] if d['total'] > 0 else None
            hit_rate_map[label][b] = {'rate': rate, 'total': d['total'], 'hit': d['hit']}
    return hit_rate_map


def build_league_hit_rate(history):
    """联赛×结果 命中率"""
    league_data = defaultdict(lambda: defaultdict(int))
    for m in history:
        if not m.get('半全场结果'):
            continue
        lg  = m.get('联赛', '未知')
        res = m['半全场结果']
        league_data[lg][res] += 1
        league_data[lg]['__total__'] += 1

    league_rate = {}
    for lg, ld in league_data.items():
        total = ld['__total__']
        league_rate[lg] = {
            label: ld.get(label, 0) / total for label in HQC_CN_LABELS
        }
    return league_rate


def build_spf_bias_hit_rate(history):
    """
    ★ 全场倾向 × 半全场结果 条件概率
    返回 dict[全场倾向][半全场结果] = 条件概率
    """
    bias_data = defaultdict(lambda: defaultdict(int))
    for m in history:
        if not m.get('半全场结果') or not m.get('全场倾向'):
            continue
        bias = m['全场倾向']
        res  = m['半全场结果']
        if bias in SPF_BIAS_LABELS and res in HQC_CN_LABELS:
            bias_data[bias][res] += 1
            bias_data[bias]['__total__'] += 1

    bias_rate = {}
    for bias in SPF_BIAS_LABELS:
        total = bias_data[bias].get('__total__', 0)
        if total == 0:
            continue
        bias_rate[bias] = {
            label: bias_data[bias].get(label, 0) / total
            for label in HQC_CN_LABELS
        }
    return bias_rate


def build_spf_win_bin_hit_rate(history):
    """
    ★ 全场主胜赔率区间 × 半全场结果 命中率
    返回 dict[区间名][半全场结果] = 命中率
    """
    win_bin_data = defaultdict(lambda: defaultdict(int))
    for m in history:
        if not m.get('半全场结果') or not m.get('全场胜平负赔率'):
            continue
        win_o = m['全场胜平负赔率'].get('胜', 0)
        if win_o <= 0:
            continue
        bin_name = get_spf_win_bin_name(win_o)
        if not bin_name:
            continue
        res = m['半全场结果']
        win_bin_data[bin_name][res] += 1
        win_bin_data[bin_name]['__total__'] += 1

    win_bin_rate = {}
    for bin_name, data in win_bin_data.items():
        total = data.get('__total__', 0)
        if total == 0:
            continue
        win_bin_rate[bin_name] = {
            label: data.get(label, 0) / total for label in HQC_CN_LABELS
        }
    return win_bin_rate


def build_team_form_stats(history):
    """
    ★ v3: 球队状态 × 半全场结果 统计
    基于主/客队近况胜率（从球队状态字段计算）与半全场结果的关联
    返回：(主队强态场次数, 客队强态场次数, 弱态场次数)
    用于判断：当主队/客队状态强/弱时，半全场结果如何分布
    """
    # 按主队强态/弱态分组统计
    home_strong = defaultdict(lambda: defaultdict(int))   # 主队近10场胜率>=50%
    home_strong_total = defaultdict(int)
    home_weak = defaultdict(lambda: defaultdict(int))    # 主队近10场胜率<50%
    home_weak_total = defaultdict(int)
    away_strong = defaultdict(lambda: defaultdict(int))  # 客队近10场胜率>=50%
    away_strong_total = defaultdict(int)
    away_weak = defaultdict(lambda: defaultdict(int))    # 客队近10场胜率<50%
    away_weak_total = defaultdict(int)

    for m in history:
        if not m.get('半全场结果'):
            continue
        res = m['半全场结果']
        shuju = m.get('球队状态', {})
        if not shuju:
            continue

        home_w = shuju.get('主队胜', -1)
        home_d = shuju.get('主队平', -1)
        away_w = shuju.get('客队胜', -1)
        away_d = shuju.get('客队平', -1)

        if home_w < 0 or away_w < 0:
            continue

        home_total = home_w + home_d + shuju.get('主队负', 0)
        away_total = away_w + away_d + shuju.get('客队负', 0)

        if home_total == 0 or away_total == 0:
            continue

        home_wr = home_w / home_total   # 主队近10场胜率
        away_wr = away_w / away_total   # 客队近10场胜率

        if home_wr >= 0.5:
            home_strong[res] += 1
            home_strong_total[res] += 1
            home_strong['__total__'] += 1
        else:
            home_weak[res] += 1
            home_weak_total[res] += 1
            home_weak['__total__'] += 1

        if away_wr >= 0.5:
            away_strong[res] += 1
            away_strong_total[res] += 1
            away_strong['__total__'] += 1
        else:
            away_weak[res] += 1
            away_weak_total[res] += 1
            away_weak['__total__'] += 1

    def to_rates(d, total_key='__total__'):
        total = d.get(total_key, 0)
        if total == 0:
            return {}
        return {label: d.get(label, 0) / total for label in HQC_CN_LABELS}

    return {
        'home_strong': to_rates(dict(home_strong)),
        'home_weak': to_rates(dict(home_weak)),
        'away_strong': to_rates(dict(away_strong)),
        'away_weak': to_rates(dict(away_weak)),
        'home_strong_n': home_strong.get('__total__', 0),
        'home_weak_n': home_weak.get('__total__', 0),
        'away_strong_n': away_strong.get('__total__', 0),
        'away_weak_n': away_weak.get('__total__', 0),
    }


def calc_team_form_score(match):
    """
    ★ v3: 计算球队状态系数
    返回每个半全场结果的球队状态加成分数（0.5~1.5）
    逻辑：
    - 主队强态(+0.15)：支持 胜胜/平胜
    - 主队弱态(-0.15)：支持 负负/平负
    - 客队强态(-0.15)：支持 负负/平负
    - 客队弱态(+0.15)：支持 胜胜/平胜
    - 近况含连W：额外+0.05
    - 近况含连L：额外-0.05
    """
    shuju = match.get('球队状态', {})
    if not shuju:
        return {}  # 无球队状态数据

    scores = {label: 1.0 for label in HQC_CN_LABELS}

    home_w = shuju.get('主队胜', -1)
    home_d = shuju.get('主队平', -1)
    away_w = shuju.get('客队胜', -1)
    away_d = shuju.get('客队平', -1)

    if home_w < 0 or away_w < 0:
        return scores

    home_total = home_w + home_d + shuju.get('主队负', 0)
    away_total = away_w + away_d + shuju.get('客队负', 0)
    if home_total == 0 or away_total == 0:
        return scores

    home_wr = home_w / home_total
    away_wr = away_w / away_total

    # 主队强态：支持主队半场领先或全场领先
    if home_wr >= 0.6:
        for label in ['胜胜', '平胜', '胜负']:
            scores[label] += 0.10
        for label in ['负负', '平负']:
            scores[label] -= 0.10
    elif home_wr >= 0.5:
        for label in ['胜胜', '平胜']:
            scores[label] += 0.06
        for label in ['负负', '平负']:
            scores[label] -= 0.06
    elif home_wr < 0.4:
        for label in ['负负', '平负', '负平']:
            scores[label] += 0.10
        for label in ['胜胜', '平胜']:
            scores[label] -= 0.10

    # 客队强态：支持客队半场领先或全场领先
    if away_wr >= 0.6:
        for label in ['负负', '平负', '负平']:
            scores[label] += 0.10
        for label in ['胜胜', '平胜']:
            scores[label] -= 0.10
    elif away_wr >= 0.5:
        for label in ['负负', '平负']:
            scores[label] += 0.06
        for label in ['胜胜', '平胜']:
            scores[label] -= 0.06
    elif away_wr < 0.4:
        for label in ['胜胜', '平胜', '胜负']:
            scores[label] += 0.10
        for label in ['负负', '平负']:
            scores[label] -= 0.10

    # 连W/连L加成（近6场内统计）
    for side, pos_labels, neg_labels in [
        ('home', ['胜胜', '平胜', '胜负'], ['负负', '平负', '负平']),
        ('away', ['负负', '平负', '负平'], ['胜胜', '平胜', '胜负']),
    ]:
        trend_key = f'{side}队近况走势'
        trend = shuju.get(trend_key, '')
        if len(trend) >= 3:
            recent = trend[:3]
            win_cnt = recent.count('W')
            if win_cnt >= 2:  # 近3场2胜以上
                for label in pos_labels:
                    scores[label] += 0.05
            elif win_cnt <= 1:  # 近3场最多1胜
                for label in neg_labels:
                    scores[label] += 0.05

    # 限制范围
    for label in HQC_CN_LABELS:
        scores[label] = max(0.5, min(1.5, scores[label]))

    return scores


def _calc_spf_bias(spf_odds):
    """根据全场赔率计算市场倾向标签（与fetch.py保持一致）"""
    if not spf_odds or len(spf_odds) < 3:
        return '未知'
    w = spf_odds.get('胜', 0)
    d = spf_odds.get('平', 0)
    l = spf_odds.get('负', 0)
    if w <= 0 or d <= 0 or l <= 0:
        return '未知'
    inv_w = 1/w; inv_d = 1/d; inv_l = 1/l
    total = inv_w + inv_d + inv_l
    p_win = inv_w / total
    p_los = inv_l / total
    if p_win >= 0.55:
        return '强主'
    elif p_win >= 0.42:
        return '弱主'
    elif p_los >= 0.55:
        return '强客'
    elif p_los >= 0.42:
        return '弱客'
    else:
        return '均势'


def predict_match(match, stats, history, hqc_bin_rate, league_rate, spf_bias_rate, spf_win_bin_rate, team_form_stats=None):
    """
    对单场比赛进行半全场预测（7维加权 v3）
    """
    hqc_odds = match.get('半全场赔率', {})
    league   = match.get('联赛', '未知')
    spf_odds = match.get('全场胜平负赔率', {})

    if not hqc_odds:
        return None

    # 获取或计算全场倾向
    bias = match.get('全场倾向') or _calc_spf_bias(spf_odds)

    # 获取全场主胜赔率区间
    spf_win_o = spf_odds.get('胜', 0) if spf_odds else 0
    spf_win_bin = get_spf_win_bin_name(spf_win_o) if spf_win_o > 0 else None

    global_rates = {s[0]: s[1]['命中率'] for s in stats.get('sorted_by_rate', [])}

    scores  = {}
    details = {}

    # 半全场市场隐含概率（归一化）
    total_inv_hqc = sum(1.0 / hqc_odds[l] for l in HQC_CN_LABELS if hqc_odds.get(l, 0) > 0)

    # ── 7维加权合成 v3 ──
    for label in HQC_CN_LABELS:
        o = hqc_odds.get(label, 0)
        if o <= 0:
            continue

        # ── 维度1: 全局历史命中率 ──
        g_rate = global_rates.get(label, 0.111)

        # ── 维度2: 半全场赔率区间命中率 ──
        b = get_hqc_bin(o)
        b_data = hqc_bin_rate.get(label, {}).get(b, {})
        b_rate  = b_data.get('rate') or 0.111
        b_sample = b_data.get('total', 0)

        # ── 维度3: 半全场市场隐含概率（归一化） ──
        inv_o = 1.0 / o
        market_prob = inv_o / total_inv_hqc if total_inv_hqc > 0 else 0.111

        # ── 维度4: 联赛×结果 命中率 ──
        lg_rate = league_rate.get(league, {}).get(label, 0.111)

        # ── 维度5: ★ 全场倾向 × 半全场结果 条件概率 ──
        bias_available = bias in spf_bias_rate
        bias_prob = spf_bias_rate.get(bias, {}).get(label, 0.111) if bias_available else 0.111

        # ── 维度6: ★ 全场主胜赔率区间命中率 ──
        spf_bin_available = spf_win_bin in spf_win_bin_rate
        spf_bin_prob = spf_win_bin_rate.get(spf_win_bin, {}).get(label, 0.111) if spf_bin_available else 0.111

        # ── 维度7: ★ 球队状态系数（v3新增）─────────────────────────
        team_form_mult = calc_team_form_score(match)
        tf_available = bool(team_form_mult)
        tf_mult = team_form_mult.get(label, 1.0) if tf_available else 1.0

        # ── 加权合成 ──
        # 若无全场数据，将SPF权重分配给其他维度
        if not bias_available and not spf_bin_available:
            # 退化为v2：全局+区间+市场+联赛+球队状态
            w1, w2, w3, w4, w5, w6 = 0.28, 0.25, 0.18, 0.12, 0.0, 0.0
            w7 = WEIGHT_TEAM_FORM
            wsum = w1 + w2 + w3 + w4 + w5 + w6 + w7
            w1 /= wsum; w2 /= wsum; w3 /= wsum; w4 /= wsum; w7 /= wsum
        else:
            w1 = WEIGHT_GLOBAL_RATE
            w2 = WEIGHT_ODDS_BUCKET
            w3 = WEIGHT_INVERSE_ODDS
            w4 = WEIGHT_LEAGUE_BIAS
            w5 = WEIGHT_SPF_BIAS    if bias_available    else 0
            w6 = WEIGHT_SPF_WIN_BIN if spf_bin_available else 0
            w7 = WEIGHT_TEAM_FORM   if tf_available      else 0
            # 归一化权重
            wsum = w1 + w2 + w3 + w4 + w5 + w6 + w7
            w1 /= wsum; w2 /= wsum; w3 /= wsum
            w4 /= wsum; w5 /= wsum; w6 /= wsum; w7 /= wsum

        base_score = (w1 * g_rate +
                  w2 * b_rate +
                  w3 * market_prob +
                  w4 * lg_rate +
                  w5 * bias_prob +
                  w6 * spf_bin_prob)

        # 球队状态系数作为乘数叠加到基础分上
        score = base_score * tf_mult

        # ── v3: 神奇尾数惩罚 ────────────────────────────
        is_bad = _is_magic_bad(o)
        if is_bad:
            score *= 0.6   # 神奇尾数赔率降权40%

        scores[label]  = round(score, 6)
        details[label] = {
            'odds':         o,
            'global_rate':  round(g_rate, 4),
            'bin_rate':     round(b_rate, 4),
            'market_prob':  round(market_prob, 4),
            'league_rate':  round(lg_rate, 4),
            'bias_prob':    round(bias_prob, 4),
            'spf_bin_prob': round(spf_bin_prob, 4),
            'tf_mult':      round(tf_mult, 3),
            'is_bad_suffix': is_bad,
            'score':        round(score, 6),
            'bin_sample':   b_sample,
        }


    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top1 = sorted_scores[0]
    top2 = sorted_scores[1] if len(sorted_scores) > 1 else None
    top3 = sorted_scores[2] if len(sorted_scores) > 2 else None

    top3_sum   = sum(s for _, s in sorted_scores[:3])
    confidence = (top1[1] / top3_sum * 3) if top3_sum > 0 else 0.33
    value_index = top1[1] * hqc_odds.get(top1[0], 1)

    return {
        'top1':          top1[0],
        'top2':          top2[0] if top2 else '',
        'top3':          top3[0] if top3 else '',
        'confidence':    round(confidence, 4),
        'value_index':   round(value_index, 4),
        'sorted_scores': sorted_scores,
        'details':       details,
        'spf_bias':      bias,
        'spf_win_odds':  spf_win_o,
        'spf_win_bin':   spf_win_bin or '未知',
        'has_spf':       bool(spf_odds),
    }


def predict_day(date_str=None, show_top=30):
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    cache_file = os.path.join(DATA_DIR, f"hqc_{date_str}.json")
    if not os.path.exists(cache_file):
        print(f"[!] 未找到 {date_str} 的数据，尝试实时抓取...")
        from hqc_fetch import parse_hqc_page as _phqc, parse_spf_page as _pspf
        spf_dict   = _pspf(date_str)
        day_matches = _phqc(date_str, spf_dict=spf_dict, fetch_shuju=True)
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(day_matches, f, ensure_ascii=False, indent=2)
    else:
        with open(cache_file, 'r', encoding='utf-8') as f:
            day_matches = json.load(f)
        # 若旧缓存缺少SPF字段，静默补充
        if day_matches and '全场胜平负赔率' not in day_matches[0]:
            print(f"  [升级] 补充SPF赔率...")
            from hqc_fetch import parse_spf_page as _pspf, _calc_spf_bias
            spf_dict = _pspf(date_str)
            for m in day_matches:
                fid = m.get('fixture_id', '')
                if fid and fid in spf_dict:
                    m['全场胜平负赔率'] = spf_dict[fid].get('全场胜平负赔率', {})
                    m['全场结果']       = spf_dict[fid].get('全场结果', '')
                    m['全场倾向']       = _calc_spf_bias(m['全场胜平负赔率'])
                else:
                    m.setdefault('全场胜平负赔率', {})
                    m.setdefault('全场结果', '')
                    m.setdefault('全场倾向', '未知')
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(day_matches, f, ensure_ascii=False, indent=2)

    if not day_matches:
        print(f"当日 {date_str} 无比赛数据")
        return []

    stats = load_stats()
    if not stats:
        print("[!] 请先运行 hqc_stats.py 生成统计报告")
        return []

    history        = load_all_data()
    hqc_bin_rate   = build_hqc_bin_hit_rate(history)
    league_rate    = build_league_hit_rate(history)
    spf_bias_rate  = build_spf_bias_hit_rate(history)
    spf_win_bin_rate = build_spf_win_bin_hit_rate(history)
    team_form_stats = build_team_form_stats(history)

    print(f"\n{'='*75}")
    print(f"半全场预测 v3（含全场赔率+球队状态）- {date_str}  共 {len(day_matches)} 场")
    print(f"历史数据: {len(history)} 场")
    spf_cnt = sum(1 for m in history if m.get('全场胜平负赔率'))
    print(f"含全场SPF赔率: {spf_cnt} 场（用于全场倾向分析）")
    print(f"{'='*75}")

    results = []
    for m in day_matches:
        if not m.get('半全场赔率'):
            continue
        pred = predict_match(m, stats, history, hqc_bin_rate, league_rate,
                             spf_bias_rate, spf_win_bin_rate, team_form_stats)
        if not pred:
            continue
        results.append({
            '编号':         m.get('编号', ''),
            '联赛':         m.get('联赛', ''),
            '日期':         m.get('日期', date_str),
            '时间':         m.get('时间', ''),
            '主队':         m.get('主队', ''),
            '客队':         m.get('客队', ''),
            '半全场赔率':   m.get('半全场赔率', {}),
            '全场胜平负赔率': m.get('全场胜平负赔率', {}),
            '全场倾向':     pred['spf_bias'],
            '球队状态':     m.get('球队状态', {}),
            '预测结果':     pred,
            '实际结果':     m.get('半全场结果', ''),
        })

    results.sort(key=lambda x: x['预测结果']['value_index'], reverse=True)

    # 打印汇总表
    print(f"\n{'编号':<8} {'联赛':<10} {'主队':<12} {'客队':<12} "
          f"{'全场倾向':<8} {'推荐':<6} {'赔率':>6} {'信度':>6} {'价值':>7} {'实际':>5}")
    print("-" * 90)
    for r in results[:show_top]:
        p      = r['预测结果']
        top1   = p['top1']
        o1     = r['半全场赔率'].get(top1, 0)
        actual = r['实际结果'] or '-'
        mark   = '[HIT]' if actual == top1 else ('[MISS]' if actual not in ('-', '') else '[ .. ]')
        print(f"{r['编号']:<8} {r['联赛']:<10} {r['主队']:<12} {r['客队']:<12} "
              f"{p['spf_bias']:<8} {top1:<6} {o1:>6.2f} {p['confidence']*100:>5.1f}% "
              f"{p['value_index']:>7.4f} {actual:>5} {mark}")

    # 详细前3场
    print(f"\n{'='*75}\n详细预测（前3场）")
    for r in results[:3]:
        p = r['预测结果']
        spf = r.get('全场胜平负赔率', {})
        print(f"\n>> {r['编号']} {r['联赛']}  {r['主队']} vs {r['客队']}  ({r['时间']})")
        print(f"   全场SPF赔率: 主胜{spf.get('胜','?')} 平{spf.get('平','?')} 客胜{spf.get('负','?')}"
              f"  → 全场倾向: [{p['spf_bias']}]  主赔区间: {p['spf_win_bin']}")
        print(f"   推荐: {p['top1']}  置信度 {p['confidence']*100:.1f}%  价值指数 {p['value_index']:.4f}")
        print(f"   候选: {p['top2']} / {p['top3']}")
        print(f"   {'结果':<6} {'赔率':>6} {'全局率':>7} {'区间率':>7} {'市场概率':>8} "
              f"{'联赛率':>7} {'全场倾向概率':>12} {'主赔区间概率':>12} {'态系数':>6} {'综合分':>8}")
        for lbl, det in sorted(p['details'].items(), key=lambda x: x[1]['score'], reverse=True)[:5]:
            print(f"   {lbl:<6} {det['odds']:>6.2f} {det['global_rate']*100:>6.1f}% "
                  f"{det['bin_rate']*100:>6.1f}% {det['market_prob']*100:>7.1f}% "
                  f"{det['league_rate']*100:>6.1f}% {det['bias_prob']*100:>11.1f}% "
                  f"{det['spf_bin_prob']*100:>11.1f}% {det['tf_mult']:>6.3f} {det['score']:>8.4f}")
        if r['实际结果']:
            hit = r['实际结果'] == p['top1']
            print(f"   实际结果: {r['实际结果']} {'[HIT]' if hit else '[MISS]'}")

    out_file = os.path.join(DATA_DIR, f"hqc_predict_{date_str}.json")
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[HIT] 预测结果已保存: {out_file}")
    return results


if __name__ == '__main__':
    import sys
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
    predict_day(date_str)
