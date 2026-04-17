# -*- coding: utf-8 -*-
"""
三方向排除引擎 回测脚本 v2
用 R1-R8 规则对 255 场历史复盘进行命中率验证
"""

import json, os, glob
from collections import defaultdict

REVIEW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '分析模板', '_reviews')

CN = {'home': '主胜', 'draw': '平局', 'away': '客胜'}
IDX = {'home': 0, 'draw': 1, 'away': 2}


class Engine:
    def __init__(self):
        self.reset()

    def reset(self):
        self.scores = {'home': 0, 'draw': 0, 'away': 0}
        self.evs = {'home': [], 'draw': [], 'away': []}

    def add(self, d, delta, text, rule=''):
        self.scores[d] += delta
        self.evs[d].append({'d': delta, 't': text, 'r': rule})

    def run(self, fp):
        """Run all rules against odds_fingerprint dict."""
        self.reset()

        ji = fp.get('jc_init_odds', [])      # 竞彩初盘 [主,平,客]
        jr = fp.get('jc_real_odds', [])       # 竞彩即时
        mi = fp.get('macao_init_odds', [])    # 澳门初盘
        mr = fp.get('macao_real_odds', [])     # 澳门即时

        jhc = float(fp.get('jc_home_chg', 0))
        jdc = float(fp.get('jc_draw_chg', 0))
        jac = float(fp.get('jc_away_chg', 0))
        mhc = float(fp.get('mcao_home_chg', 0))
        mdc = float(fp.get('mcao_draw_chg', 0))
        mac = float(fp.get('mcao_away_chg', 0))

        tip = str(fp.get('macao_tip') or '')
        mt  = str(fp.get('match_type') or '')
        lg  = str(fp.get('league') or '')

        # ── R1: 赔率绝对值排除 ──
        for d in ('home', 'draw', 'away'):
            o = jr[IDX[d]] if len(jr) > IDX[d] else 0
            if o >= 6.0:
                self.add(d, -90, '%.2f>=6.0: 极端高赔基本不出' % o, 'R1-极端赔')
            elif o >= 5.0:
                self.add(d, -85, '%.2f>=5.0: 历史约90%%不出' % o, 'R1-极高赔')
            elif o >= 4.0:
                self.add(d, -65, '%.2f>=4.0: 高赔方向大概率不出' % o, 'R1-高赔')
            elif o >= 3.5:
                friendly = '友谊' in mt or '友谊' in lg
                if not (friendly and d == 'draw'):
                    self.add(d, -45, '%.2f>=3.5: 中高赔需警惕' % o, 'R1-中高赔')

            # 碾压
            if 0 < o < 1.35:
                for d2 in ('home','draw','away'):
                    if d2 != d:
                        bonus = -(20 + round((1.35-o)*50))
                        self.add(d2, bonus, '%.2f碾压模式' % o, 'R1-碾压')

        # ── R2: 心水排除法 ──
        if tip:
            ti = None
            if   '主' in tip and '客' not in tip: ti = 'home'
            elif ('平' in tip or '和' in tip):         ti = 'draw'
            elif '客' in tip:                           ti = 'away'

            if ti:
                idx = IDX[ti]
                to = jr[idx] if len(jr) > idx else 0

                if to >= 5.0 and ti == 'draw':
                    self.add(ti, -75, '心水推%s赔率%.2f>=5: 但推平局不可靠' % (tip,to), 'R2a-心水高赔')
                elif to >= 3.5:
                    self.add(ti, -70, '心水推%s但赔率高(%.2f): 80%%不出' % (tip,to), 'R2a-心水高赔')
                elif len(ji) >= 3 and len(jr) >= 3 and ji[idx] > 0 and jr[idx] > 0:
                    chg = (jr[idx]-ji[idx]) / ji[idx] * 100
                    if chg > 3:
                        self.add(ti, -80, '规则B:竞彩对心水升%.1f%%(4/4=100%%)' % chg, 'R2b-规则B')
                    elif chg < -2:
                        self.add(ti, +30, '竞彩对心水降%.1f%%=实盘信号' % abs(chg), 'R2b-实盘信号')
                elif 2.0 <= to < 3.0:
                    self.add(ti, -10, '心水赔率%.2f在灰色区间(54.5%%)' % to, 'R2c-灰色区')

        # ── R3: 竞彩x澳门互动 ──
        dirs_data = [
            ('home', 0, jhc, mhc),
            ('draw', 1, jdc, mdc),
            ('away', 2, jac, mac),
        ]

        for dn, di, jcc, mcc in dirs_data:
            ov = jr[di] if len(jr) > di else 0

            # [不怕]: 竞彩升+澳门不动
            if jcc > 1.0 and abs(mcc) < 0.5:
                if ov >= 3.5:
                    self.add(dn, -65, '[不怕]%s+赔率%.1f>=3.5(~88%%)' % (CN[dn], ov), 'R3a-[不怕]')
                elif 0 < ov < 3.5:
                    self.add(dn, +5, '[不怕]%s但赔率%.1f<3.5:不可靠' % (CN[dn], ov), 'R3a-[不怕]低赔')

            # [不跟]: 竞彩降+澳门不动
            if jcc < -1.0 and abs(mcc) < 0.5:
                self.add(dn, +25, '[不跟]%s: 竞彩单独造热是假象' % CN[dn], 'R3b-[不跟]')

            # 推离: 竞彩升>5%
            if jcc > 5:
                self.add(dn, -55, '竞彩推离%s(升%.1f%%)' % (CN[dn], jcc), 'R3c-推离')

        # ── R5a: 单出口造热陷阱 ──
        heat_dir = None
        push_cnt = 0
        for dn, _, jcc, mcc in dirs_data:
            if jcc < -5 and mcc < -5:
                heat_dir = dn          # 记录造热方向
            if jcc > 5:
                push_cnt += 1

        if heat_dir and push_cnt >= 2:
            self.add(heat_dir, -50, '单出口全面造热陷阱', 'R5a-造热陷阱')

        # ── R6: 平赔安静保护 ──
        if abs(mdc) < 0.5 and abs(jdc) < 1.0:
            self.add('draw', +20, '平赔安静保护: 庄家可能在掩护平局', 'R6-掩护平局')

        # ── 结果判定 ──
        best = max(self.scores, key=self.scores.get)
        bs = self.scores[best]
        if bs > 10:   lv = 'safe'
        elif bs > 0:  lv = 'caution'
        elif bs > -30: lv = 'neutral'
        else:         lv = 'dangerous'

        excl = [d for d in ('home','draw','away') if self.scores[d] < -30]

        return {
            'scores': dict(self.scores),
            'best': best,
            'score': bs,
            'level': lv,
            'excluded': excl,
            'evs': dict(self.evs),
        }


def load_reviews():
    reviews = []
    for fpath in sorted(glob.glob(os.path.join(REVIEW_DIR, '*.json'))):
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                d = json.load(f)
                if isinstance(d, dict) and d.get('match_id'):
                    reviews.append(d)
        except Exception:
            pass
    return reviews


def main():
    print('=' * 72)
    print('  三方向排除引擎 回测报告 (255场复盘)')
    print('=' * 72)

    reviews = load_reviews()
    n = len(reviews)
    print('\n加载 %d 条复盘记录\n' % n)

    engine = Engine()
    total = correct = no_data = errs = 0
    by_lv = defaultdict(lambda: [0, 0])     # [total, correct]
    by_bd = defaultdict(lambda: [0, 0])     # by_best_dir
    by_act = defaultdict(int)
    rstat = defaultdict(lambda: [0, 0])     # rule stats: [triggered, hit_when_triggered]
    results = []

    for rev in reviews:
        total += 1
        mid = rev['match_id']
        actual = rev.get('actual_result', '?')
        pred_o = rev.get('prediction', '?')
        fp = rev.get('odds_fingerprint', {})
        by_act[actual] += 1

        if not fp or not fp.get('jc_real_odds'):
            no_data += 1
            continue

        try:
            res = engine.run(fp)
        except Exception as e:
            errs += 1
            continue

        hit = (res['best'] == actual)
        orig_hit = (pred_o == actual) if pred_o != '?' else None

        results.append({
            'id': mid, 'home': rev.get('home_team','?'), 'away': rev.get('away_team','?'),
            'actual': actual, 'pred_o': pred_o,
            'best': res['best'], 'score': res['score'], 'lv': res['lv'],
            'hit': hit, 'orig_hit': orig_hit, 'excl': res['excluded'],
            'sc': res['scores'],
        })

        if hit: correct += 1
        by_lv[res['lv']][0] += 1
        if hit: by_lv[res['lv']][1] += 1
        by_bd[res['best']][0] += 1
        if hit: by_bd[res['best']][1] += 1

        for d in ('home','draw','away'):
            for ev in res['evs'].get(d, []):
                rstat[ev['r']][0] += 1
                if hit: rstat[ev['r']][1] += 1

    valid = total - no_data

    # ═══ 输出报告 ═══
    print('%s' % ('='*72))
    print('  总览')
    print('%s' % ('='*72))
    print('  总场次:     %d' % total)
    print('  有效数据:   %d' % valid)
    print('  无数据跳过: %d' % no_data)
    print('  解析错误:   %d' % errs)
    print()
    if valid > 0:
        print('  引擎命中率: %d/%d = %.1f%%' % (correct, valid, correct/valid*100))

    oc = sum(1 for r in results if r['orig_hit'] == True)
    ot = sum(1 for r in results if r['orig_hit'] is not None)
    if ot > 0:
        print('  原预测命中: %d/%d = %.1f%%' % (oc, ot, oc/ot*100))

    print()
    print('%s' % ('='*72))
    print('  按安全等级分')
    print('%s' % ('='*72))
    for lv in ('safe','caution','neutral','dangerous'):
        t, c = by_lv[lv]
        if t > 0:
            p = c/t*100
            bar = '#' * int(p/2) + '-' * min(25-int(p/2), 25)
            print('  %-10s: %3d/%3d (%5.1f%%)  %s' % (lv, t, c, p, bar))

    print()
    print('%s" % ("="*72))
    print('  引擎选择方向 vs 实际结果')
    print('%s' % ('='*72))
    for d in ('home','draw','away'):
        t, c = by_bd[d]
        if t > 0:
            print('  选%-4s: %3d/%3d (%5.1f%%)' % (CN[d], t, c, c/t*100))

    print('\n实际结果分布:')
    for a, cnt in sorted(by_act.items(), key=lambda x:-x[1]):
        pct = cnt/valid*100 if valid>0 else 0
        print('  %-4s: %3d场 (%.1f%%)' % (CN.get(a,a), int(cnt), pct))

    print()
    print('%s' % ('='*72))
    print('  各规则触发统计 (触发>=3次)')
    print('%s' % ('='*72))
    print('  %-24s %5s  %10s' % ('规则', '触发', '方向正确率'))
    print('  %s' % ('-'*44))
    for rule, (trig, rhit) in sorted(rstat.items(), key=lambda x:-x[1][0]):
        if trig >= 3:
            p = rhit/trig*100
            tag = 'OK' if p>55 else ('??' if p>45 else 'XX')
            print('  %s %-22s %5d  %7.1f%%' % (tag, rule[:22], trig, p))

    # 错误案例 Top20
    print()
    print('%s' % ('='*72))
    print('  错误案例 Top20 (引擎最自信却错的)')
    print('%s' % ('='*72))
    wr = sorted([r for r in results if not r['hit']], key=lambda x:-x['score'])[:20]
    for i, r in enumerate(wr):
        s = r['sc']
        ex = '/'.join([CN[e] for e in r['excl']])
        print('  %2d. [%s] %s vs %s' % (i+1,r['id'],r['home'],r['away']))
        print('      引擎=%s(%+d) | 实际=%s | 原预=%s' % (CN[r['best']],r['score'],CN[r['actual']],r['pred_o']))
        print('      主%+d 平%+d 客%+d | 排除:[%s]' % (s['home'],s['draw'],s['away'],ex))

    # 正确案例 Top15
    print()
    print('%s' % ('='*72))
    print('  正确案例 Top15 (引擎高置信度)')
    print('%s' % ('='*72))
    rr = sorted([r for r in results if r['hit']], key=lambda x:-x['score'])[:15]
    for i, r in enumerate(rr):
        print('  %2d. [%s] %s vs %s  OK %s(%+d) 实际=%s Lv=%s' %
              (i+1,r['id'],r['home'],r['away'], CN[r['best']],r['score'],
               CN[r['actual']], r['lv']))

    # R7 近况差专项
    print()
    print('%s' % ('='*72))
    print('  专项: 近况差辅助(R7)效果验证')
    print('%s' % ('='*72))
    fc = fcor = 0
    for r in results:
        rv = next((x for x in reviews if x['match_id']==r['id']), None)
        if not rv: continue
        hf, af = rv.get('home_form',''), rv.get('away_form','')
        if not hf or not af: continue
        def _fs(s):
            sc=0; w=[2,1,1,1,1,1]
            for ii,ch in enumerate(s[:6]):
                if ch=='W': sc+=3*w[ii]
                elif ch=='D': sc+=w[ii]
            return sc
        diff = _fs(hf) - _fs(af)
        if abs(diff) >= 8:
            fc += 1
            if ('home' if diff>0 else 'away') == r['actual']:
                fcor += 1
    if fc > 0:
        print('  近况差>=8分: %d场 | 命中: %d/%d = %.1f%%' % (fc, fcor, fc, fcor/fc*100))
        rp = fcor/fc*100
        if rp < 50:  print('  !! 低于随机 -> 应删除')
        elif rp < 60: print('  ?? 勉强过随机 -> 价值有限')


if __name__ == '__main__':
    main()
