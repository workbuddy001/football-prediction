# -*- coding: utf-8 -*-
import json
import re

# 读取数据
with open('分析模板/matches_full_2026-03-21.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('3.21_form_analysis.txt', 'r', encoding='utf-8') as f:
    analysis = f.read()

# 提取所有周六比赛的近况数据
form_data = {}
# 使用DOTALL模式匹配整个比赛块
pattern = r'周六(\d+)\s+.*?近况差:\s*([+-]?\d+)'
matches = re.findall(pattern, analysis, re.DOTALL)
for mid, form_diff in matches:
    form_data[mid] = {
        'home': '',
        'away': '',
        'form_diff': int(form_diff)
    }

# 已单选的比赛（置信度>=66%）
single_picks = ['017', '019', '022', '025', '026', '029']

print('='*230)
print('周六比赛赔率分析与预测（其他比赛）- 通过赔率变化和近况差分析')
print('='*230)
print()
print(f'{"编号":<8} {"对阵":<20} {"初盘主/平/客":<18} {"即时主/平/客":<18} {"变化(H/D/A)":<20} {"近况差":<8} {"澳门推荐":<14} {"预测":<6} {"分析依据"}')
print('-'*230)

results = []

for match in data:
    bid = match.get('编号', '')
    if '周六' not in bid:
        continue
    
    mid = bid.replace('周六', '')
    if mid in single_picks:
        continue  # 跳过已单选的
    
    home = match.get('主队', '')
    away = match.get('客队', '')
    
    # 欧赔数据
    ou = match.get('欧赔数据', {})
    ou_list = ou.get('欧赔列表', [])
    
    jc_odds = None
    for o in ou_list:
        if '竞*官*' in o.get('公司', ''):
            jc_odds = o
            break
    
    if not jc_odds:
        continue
    
    h0 = float(jc_odds.get('初盘胜', 0))
    d0 = float(jc_odds.get('初盘平', 0))
    a0 = float(jc_odds.get('初盘负', 0))
    
    h1 = float(jc_odds.get('即时胜', 0))
    d1 = float(jc_odds.get('即时平', 0))
    a1 = float(jc_odds.get('即时负', 0))
    
    if not h0:
        continue
    
    # 计算变化
    h_chg = (h1-h0)/h0*100
    d_chg = (d1-d0)/d0*100 if d0 else 0
    a_chg = (a1-a0)/a0*100 if a0 else 0
    
    # 获取近况数据
    form = form_data.get(mid, {})
    form_diff = form.get('form_diff', 0)
    
    # 澳门推荐
    macao = match.get('数据分析', {}).get('澳门推荐', '')[:12]
    
    # ======== 核心分析原则 ========
    # 赔率变化能否掩护正确结果打出，并且正确结果尽量要赔付减少
    # 澳门心水 = 庄家真实意图（正确结果）
    # 状态差 = 玩家基础信息
    # 赔率变化 = 庄家诱导筹码的工具
    
    # 判断澳门推荐方向
    macao_clean = macao.replace(' 贏', '').replace(' 孖', '').strip()
    is_macao_home = macao_clean == home
    is_macao_away = macao_clean == away
    is_macao_draw = '和局' in macao
    
    def analyze_with_core_principle(h_chg, a_chg, d_chg, is_macao_home, is_macao_away, is_macao_draw, form_diff):
        """
        核心原则：赔率变化能否掩护正确结果打出
        
        用户新规律（2026-03-22）：
        1. 近况差大（≥5）+ 澳门推荐强势方 + 赔率能分散强势方 → 强势方能出
        2. 近况差大（≥5）+ 澳门推荐强势方 + 赔率无法分散 → 强势方难出
        """
        
        # ======== 近况差大（≥5）时的特殊判断 ========
        abs_diff = abs(form_diff)
        
        # 澳门推荐主队 + 近况主队好（form_diff >= 5）
        if is_macao_home and form_diff >= 5:
            # 能否分散主胜水位？
            if h_chg < 0:
                # 主胜降水 → 分散成功，庄家保护 → 主胜能出
                return ('主胜', f'近况主好(+{form_diff})+澳门推主+主降{h_chg:.1f}%，分散成功庄家保护')
            else:
                # 主胜升水 → 无法分散，强势方难出
                return ('客胜', f'近况主好(+{form_diff})+澳门推主+主升{h_chg:.1f}%，无法分散庄家不惧')
        
        # 澳门推荐客队 + 近况客队好（form_diff <= -5）
        if is_macao_away and form_diff <= -5:
            # 能否分散客胜水位？
            if a_chg < 0:
                # 客胜降水 → 分散成功，庄家保护 → 客胜能出
                return ('客胜', f'近况客好({form_diff})+澳门推客+客降{a_chg:.1f}%，分散成功庄家保护')
            else:
                # 客胜升水 → 无法分散，强势方难出
                return ('主胜', f'近况客好({form_diff})+澳门推客+客升{a_chg:.1f}%，无法分散庄家不惧')
        
        # ======== 普通情况：澳门推荐某方 ========
        # 澳门推荐主队
        if is_macao_home:
            if h_chg > 0:
                # 主胜升水 → 庄家在保护主队，减少赔付
                if h_chg >= 5:
                    return ('主胜', f'澳门推主+主升{h_chg:.1f}%，庄家保护减少赔付')
                else:
                    return ('主胜', f'澳门推主+主升{h_chg:.1f}%，无法分散给肉吃')
            elif h_chg < 0:
                # 主胜降水 → 庄家在造热主队
                if h_chg <= -4:
                    return ('客胜', f'澳门推主但主降{h_chg:.1f}%，造热诱盘防冷')
                else:
                    return ('主胜', f'澳门推主+主降{h_chg:.1f}%，小幅造热')
        
        # 澳门推荐客队
        elif is_macao_away:
            if a_chg > 0:
                # 客胜升水 → 庄家在保护客队
                if a_chg >= 5:
                    return ('客胜', f'澳门推客+客升{a_chg:.1f}%，庄家保护减少赔付')
                else:
                    return ('客胜', f'澳门推客+客升{a_chg:.1f}%，无法分散给肉吃')
            elif a_chg < 0:
                # 客胜降水 → 庄家在造热客队
                if a_chg <= -4:
                    return ('主胜', f'澳门推客但客降{a_chg:.1f}%，造热诱盘防冷')
                else:
                    return ('客胜', f'澳门推客+客降{a_chg:.1f}%，小幅造热')
        
        # 澳门推荐和局
        elif is_macao_draw:
            if d_chg > 0:
                return ('和局', f'澳门推和局+平升{d_chg:.1f}%，庄家不惧平局赔付')
            elif d_chg < -5:
                return ('主胜' if h_chg < a_chg else '客胜', f'澳门推和局但平降{d_chg:.1f}%，排除和局')
            else:
                return ('和局', f'澳门推和局+平变{d_chg:.1f}%')
        
        # 无澳门推荐，按常规逻辑
        return (None, None)
    
    # 先用核心原则判断
    prediction, reason = analyze_with_core_principle(h_chg, a_chg, d_chg, is_macao_home, is_macao_away, is_macao_draw, form_diff)
    
    # 如果核心原则没给出预测，用原有逻辑
    if not prediction:
        # ======== 用户规律：排除平局 ========
        abs_diff = abs(form_diff)
        
        def check_macao_and_heat(h_chg, a_chg, macao, base_reason, home, away):
            """检查澳门心水和造热嫌疑"""
            macao_clean = macao.replace(' 贏', '').replace(' 孖', '').strip()
            is_macao_home = macao_clean == home
            is_macao_away = macao_clean == away
            is_macao_draw = '和局' in macao
            
            if is_macao_home:
                if h_chg < -4:
                    return ('客胜', base_reason + '，主胜造热<-4%但澳门推主，需防冷')
                else:
                    return ('主胜', base_reason + '，澳门推主，顺澳门')
            elif is_macao_away:
                if a_chg < -4:
                    return ('主胜', base_reason + '，客胜造热<-4%但澳门推客，需防冷')
                else:
                    return ('客胜', base_reason + '，澳门推客，顺澳门')
            elif is_macao_draw:
                return ('和局', base_reason + '，澳门推荐和局')
            else:
                if h_chg < a_chg:
                    return ('主胜', base_reason + '，主降水方向')
                else:
                    return ('客胜', base_reason + '，客降水方向')
        
        if abs_diff <= 5:
            # 平局降水>2%
            if d_chg < -2:
                base_reason = '排除和局: 近况差' + str(form_diff) + '≤5 + 平降' + str(round(d_chg,1)) + '%>2%'
                prediction, reason = check_macao_and_heat(h_chg, a_chg, macao, base_reason, home, away)
            # 平初<3.20
            elif d0 < 3.20:
                base_reason = '排除和局: 近况差' + str(form_diff) + '≤5 + 平初' + str(d0) + '<3.20'
                prediction, reason = check_macao_and_heat(h_chg, a_chg, macao, base_reason, home, away)
            # 规律一：主胜升幅>5% -> 平局概率大
            elif h_chg > 5:
                prediction = '和局'
                reason = '主胜升幅过大(>+5%)，庄家不惧主胜'
            else:
                # 默认和局
                prediction = '和局'
                reason = '近况差接近(≤5)，无明显方向'
        # 规律一：主胜升幅>5% -> 平局概率大
        elif h_chg > 5:
            prediction = '和局'
            reason = '主胜升幅过大(>+5%)，庄家不惧主胜'
        # 规律二：澳门推荐和局 + 平赔条件
        elif '和局' in macao:
            if d0 < 3.0:
                # 平初<3.0，庄家不看好平局
                if h_chg < a_chg:
                    prediction = '主胜'
                    reason = '澳门推和局但平赔<' + str(d0) + '低，平局难出，降水方向主胜'
                else:
                    prediction = '客胜'
                    reason = '澳门推和局但平赔<' + str(d0) + '低，平局难出，降水方向客胜'
            elif d_chg < -5:
                # 平降>5%，庄家主动压缩平局
                if h_chg < a_chg:
                    prediction = '主胜'
                    reason = '澳门推和局但平降' + str(round(d_chg,1)) + '%，平局难出'
                else:
                    prediction = '客胜'
                    reason = '澳门推和局但平降' + str(round(d_chg,1)) + '%，平局难出'
            else:
                # 平赔适中且变化小，正常可出
                prediction = '和局'
                reason = '澳门推和局，平赔' + str(d0) + '适中，变化小'
        # 规律三：近况支持但赔率反向
        elif form_diff >= 6 and h_chg > 2:
            prediction = '和局'
            reason = '近况主队好(+' + str(form_diff) + ')但主胜反升，防冷'
        elif form_diff <= -6 and a_chg > 2:
            prediction = '和局'
            reason = '近况客队好(' + str(form_diff) + ')但客胜反升，防冷'
        # 规律四：造热排除
        elif h_chg < -4 and '主' not in macao and '和局' not in macao:
            prediction = '客胜'
            reason = '主胜造热但澳门不推主，排除澳门'
        elif a_chg < -4 and '客' not in macao and '和局' not in macao:
            prediction = '主胜'
            reason = '客胜造热但澳门不推客，排除澳门'
        # 规律五：顺赔率变动
        elif h_chg < -2 and a_chg > 0:
            prediction = '主胜'
            reason = '主降水+客升水，顺变动方向'
        elif a_chg < -2 and h_chg > 0:
            prediction = '客胜'
            reason = '客降水+主升水，顺变动方向'
        elif h_chg < -2:
            prediction = '主胜'
            reason = '主胜降水，顺变动方向'
        elif a_chg < -2:
            prediction = '客胜'
            reason = '客胜降水，顺变动方向'
        elif d_chg < -3:
            prediction = '和局'
            reason = '平局降水，和局概率大'
        # 规律六：澳门同路
        elif '主' in macao and h_chg < 0:
            prediction = '主胜'
            reason = '澳门推荐主胜+主降水，同路'
        elif '客' in macao and a_chg < 0:
            prediction = '客胜'
            reason = '澳门推荐客胜+客降水，同路'
        # 默认
        else:
            prediction = '和局'
            reason = '无明显方向'
    
    results.append({
        'bid': bid,
        'home': home,
        'away': away,
        'h0': h0, 'd0': d0, 'a0': a0,
        'h1': h1, 'd1': d1, 'a1': a1,
        'h_chg': h_chg, 'd_chg': d_chg, 'a_chg': a_chg,
        'form_diff': form_diff,
        'macao': macao,
        'prediction': prediction,
        'reason': reason
    })

# 按编号排序输出
for r in sorted(results, key=lambda x: x['bid']):
    bid = r['bid']
    home = r['home'][:8]
    away = r['away'][:8]
    h0, d0, a0 = r['h0'], r['d0'], r['a0']
    h1, d1, a1 = r['h1'], r['d1'], r['a1']
    h_chg, d_chg, a_chg = r['h_chg'], r['d_chg'], r['a_chg']
    form_diff = r['form_diff']
    macao = r['macao']
    pred = r['prediction']
    reason = r['reason']
    
    chg_str = 'H' + format(h_chg, '+.1f') + '% D' + format(d_chg, '+.1f') + '% A' + format(a_chg, '+.1f') + '%'
    form_str = format(form_diff, '+d')
    
    print(f'{bid:<8} {home}vs{away:<10} {h0:.2f}/{d0:.2f}/{a0:.2f}   {h1:.2f}/{d1:.2f}/{a1:.2f}   {chg_str:<20} {form_str:<8} {macao:<14} {pred:<6} {reason}')
