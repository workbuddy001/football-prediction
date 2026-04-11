# -*- coding: utf-8 -*-
"""
3.31比赛批量分析脚本 V2 - 从源数据文件自动读取竞彩/澳门初盘和即时盘
竞彩=第1条(index 0)，澳门=第3条(index 2)
"""

import re
import os
import glob

DATA_DIR = r"D:\work\workbuddy\足球预测\分析模板\3.31"
OUTPUT_FILE = r"D:\work\workbuddy\足球预测\3.31_完整分析报告.md"

def calc_form_score(form_str):
    """计算近况得分（最近一场×2，其余×1，满分18）"""
    if not form_str or len(form_str) == 0:
        return 0
    scores = []
    for i, c in enumerate(form_str[:6]):
        if c == 'W':
            s = 6 if i == 0 else 3
        elif c == 'D':
            s = 2 if i == 0 else 1
        else:
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

def parse_source_file(filepath):
    """从源数据文件解析比赛数据"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    m = {}

    # 1. 基本信息
    home_match = re.search(r'\|\s*主队\s*\|\s*(.+?)\s*\|', content)
    away_match = re.search(r'\|\s*客队\s*\|\s*(.+?)\s*\|', content)
    time_match = re.search(r'\|\s*比赛时间\s*\|\s*(.+?)\s*\|', content)
    league_match = re.search(r'\|\s*赛事\s*\|\s*(.+?)\s*\|', content)
    macau_match = re.search(r'\|\s*澳门推荐\s*\|\s*(.+?)\s*\|', content)

    m['home'] = home_match.group(1).strip() if home_match else ''
    m['away'] = away_match.group(1).strip() if away_match else ''
    m['match_time'] = time_match.group(1).strip() if time_match else ''
    m['league'] = league_match.group(1).strip() if league_match else ''
    macau_rec = macau_match.group(1).strip() if macau_match else ''
    # 标准化澳门推荐
    if '主' in macau_rec and '赢' in macau_rec:
        m['macau_rec'] = '主'
    elif '和' in macau_rec or '平' in macau_rec:
        m['macau_rec'] = '平'
    elif '客' in macau_rec or '赢' in macau_rec:
        m['macau_rec'] = '客'
    else:
        m['macau_rec'] = macau_rec

    # 近况走势
    home_form_match = re.search(r'\|\s*主队近况走势\s*\|\s*(\w+)\s*\|', content)
    away_form_match = re.search(r'\|\s*客队近况走势\s*\|\s*(\w+)\s*\|', content)
    m['home_form'] = home_form_match.group(1).strip() if home_form_match else ''
    m['away_form'] = away_form_match.group(1).strip() if away_form_match else ''

    # 2. 解析初盘赔率（第二节）
    init_section = content.split('## 二、初盘赔率')[1].split('## 三、即时赔率')[0] if '## 二、初盘赔率' in content else ''
    rt_section = content.split('## 三、即时赔率')[1].split('## 四、')[0] if '## 三、即时赔率' in content else ''

    # 提取所有赔率条目
    init_odds = []
    rt_odds = []

    # 解析initial_odds数组
    init_match = re.search(r'initial_odds\s*=\s*\[(.*?)\]', init_section, re.DOTALL)
    if init_match:
        odds_text = init_match.group(1)
        for line in odds_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            nums = re.findall(r'\d+\.\d+', line)
            if len(nums) >= 3:
                init_odds.append((float(nums[0]), float(nums[1]), float(nums[2])))

    # 解析realtime_odds数组
    rt_match = re.search(r'realtime_odds\s*=\s*\[(.*?)\]', rt_section, re.DOTALL)
    if rt_match:
        odds_text = rt_match.group(1)
        for line in odds_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            nums = re.findall(r'\d+\.\d+', line)
            if len(nums) >= 3:
                rt_odds.append((float(nums[0]), float(nums[1]), float(nums[2])))

    # ============ 竞彩赔率数据来源 ============
    # 竞彩初盘：第二节index 0（竞*官* = 500.com竞彩官方）
    # 竞彩即时盘：第三节index 0（竞*官* = 500.com竞彩官方）
    # 第四节是让球后的赔率，不参与胜平负分析
    # 澳门初盘：第二节index 2（*门）
    # 澳门即时盘：第三节index 2（*门）

    # 竞彩初盘 = 第二节 index 0
    if len(init_odds) > 0:
        m['jc_h_init'] = init_odds[0][0]
        m['jc_d_init'] = init_odds[0][1]
        m['jc_a_init'] = init_odds[0][2]
    else:
        m['jc_h_init'] = None
        m['jc_d_init'] = None
        m['jc_a_init'] = None

    # 竞彩即时盘 = 第三节 index 0（竞*官*）
    if len(rt_odds) > 0:
        m['jc_h_rt'] = rt_odds[0][0]
        m['jc_d_rt'] = rt_odds[0][1]
        m['jc_a_rt'] = rt_odds[0][2]
    else:
        m['jc_h_rt'] = None
        m['jc_d_rt'] = None
        m['jc_a_rt'] = None

    # 确定澳门初盘/即时盘（index 2 = *门）
    if len(init_odds) > 2:
        m['am_h_init'] = init_odds[2][0]
        m['am_d_init'] = init_odds[2][1]
        m['am_a_init'] = init_odds[2][2]
    else:
        m['am_h_init'] = None
        m['am_d_init'] = None
        m['am_a_init'] = None

    if len(rt_odds) > 2:
        m['am_h_rt'] = rt_odds[2][0]
        m['am_d_rt'] = rt_odds[2][1]
        m['am_a_rt'] = rt_odds[2][2]
    else:
        m['am_h_rt'] = None
        m['am_d_rt'] = None
        m['am_a_rt'] = None

    # 提取比赛编号
    filename = os.path.basename(filepath)
    id_match = re.match(r'(周[二三]\d+)', filename)
    m['id'] = id_match.group(1) if id_match else ''

    return m

def classify_chip_state(jc_h_chg, jc_d_chg, jc_a_chg):
    """分类筹码状态（基于竞彩赔率变化）"""
    h_abs = abs(jc_h_chg)
    d_abs = abs(jc_d_chg)
    a_abs = abs(jc_a_chg)
    total = h_abs + d_abs + a_abs

    if h_abs < 0.5 and d_abs < 0.5 and a_abs < 0.5:
        return "全锁定", "市场无强烈信号"
    if jc_h_chg < -10:
        return "极端造热主", f"竞彩主赔降{abs(jc_h_chg):.1f}%，筹码大量涌入主队"
    if jc_a_chg < -10:
        return "极端造热客", f"竞彩客赔降{abs(jc_a_chg):.1f}%，筹码大量涌入客队"
    if jc_h_chg > 10:
        return "极端推离主", f"竞彩主赔升{jc_h_chg:.1f}%，筹码被推离主队"
    if jc_a_chg > 10:
        return "极端推离客", f"竞彩客赔升{jc_a_chg:.1f}%，筹码被推离客队"
    lock_count = 0
    for chg in [jc_h_chg, jc_d_chg, jc_a_chg]:
        if abs(chg) > 2:
            lock_count += 1
    if lock_count == 2:
        locked = []
        if h_abs < 0.5: locked.append("主")
        if d_abs < 0.5: locked.append("平")
        if a_abs < 0.5: locked.append("客")
        if locked:
            return "单向锁定", f"{'、'.join(locked)}被锁定，市场真实押注方向"
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
    macau_rec = m['macau_rec']

    # 1. 近况得分
    home_score = calc_form_score(home_form)
    away_score = calc_form_score(away_form)
    form_diff = home_score - away_score

    # 2. 置信度
    confidence = calc_confidence(form_diff)
    conf_dir = "主胜" if form_diff > 0 else ("客胜" if form_diff < 0 else "无倾向")

    # 3. 竞彩赔率变化
    jc_h_init = m.get('jc_h_init')
    jc_h_rt = m.get('jc_h_rt')
    jc_d_init = m.get('jc_d_init')
    jc_d_rt = m.get('jc_d_rt')
    jc_a_init = m.get('jc_a_init')
    jc_a_rt = m.get('jc_a_rt')

    jc_h_chg = (jc_h_rt - jc_h_init) / jc_h_init * 100 if jc_h_init and jc_h_rt else 0
    jc_d_chg = (jc_d_rt - jc_d_init) / jc_d_init * 100 if jc_d_init and jc_d_rt else 0
    jc_a_chg = (jc_a_rt - jc_a_init) / jc_a_init * 100 if jc_a_init and jc_a_rt else 0

    # 4. 澳门赔率变化
    am_h_init = m.get('am_h_init')
    am_h_rt = m.get('am_h_rt')
    am_d_init = m.get('am_d_init')
    am_d_rt = m.get('am_d_rt')
    am_a_init = m.get('am_a_init')
    am_a_rt = m.get('am_a_rt')

    am_h_chg = (am_h_rt - am_h_init) / am_h_init * 100 if am_h_init and am_h_rt else 0
    am_d_chg = (am_d_rt - am_d_init) / am_d_init * 100 if am_d_init and am_d_rt else 0
    am_a_chg = (am_a_rt - am_a_init) / am_a_init * 100 if am_a_init and am_a_rt else 0

    # 5. 离散度
    def dispersion(jc, am):
        if am == 0: return 0
        return (jc - am) / am * 100

    disp_h = dispersion(jc_h_rt or 0, am_h_rt or 0)
    disp_d = dispersion(jc_d_rt or 0, am_d_rt or 0)
    disp_a = dispersion(jc_a_rt or 0, am_a_rt or 0)
    disp_avg = (abs(disp_h) + abs(disp_d) + abs(disp_a)) / 3

    # 初盘离散度
    disp_h_init = dispersion(jc_h_init or 0, am_h_init or 0)
    disp_d_init = dispersion(jc_d_init or 0, am_d_init or 0)
    disp_a_init = dispersion(jc_a_init or 0, am_a_init or 0)

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
    jc_min = min(jc_h_rt or 99, jc_d_rt or 99, jc_a_rt or 99)
    jc_min_dir = "主胜" if jc_h_rt == jc_min else ("平局" if jc_d_rt == jc_min else "客胜")
    jc_pressure = "低" if jc_min < 2.5 else ("中" if jc_min < 3.5 else "高")

    am_min = min(am_h_rt or 99, am_d_rt or 99, am_a_rt or 99)

    # 9. 方向对比
    if am_total < 0.5 and jc_total < 0.5:
        dir_compare = "全不动"
    elif am_total < 0.5:
        dir_compare = "澳门不动"
    elif jc_total < 0.5:
        dir_compare = "竞彩不动"
    else:
        # 检查方向是否一致
        jc_dirs = [(jc_h_chg > 0) - (jc_h_chg < 0), (jc_d_chg > 0) - (jc_d_chg < 0), (jc_a_chg > 0) - (jc_a_chg < 0)]
        am_dirs = [(am_h_chg > 0) - (am_h_chg < 0), (am_d_chg > 0) - (am_d_chg < 0), (am_a_chg > 0) - (am_a_chg < 0)]
        same = sum(1 for j, a in zip(jc_dirs, am_dirs) if j == a and j != 0)
        diff = sum(1 for j, a in zip(jc_dirs, am_dirs) if j != a and j != 0 and a != 0)
        dir_compare = "同向" if same >= 2 else "分歧"

    # 一致性
    if disp_avg < 2:
        consistency = "高度一致"
    elif disp_avg < 5:
        consistency = "基本一致"
    elif disp_avg < 10:
        consistency = "轻度分歧"
    elif disp_avg < 15:
        consistency = "明显分歧"
    else:
        consistency = "严重分歧"

    # 10. 综合判断
    prediction = ""
    reasoning = []
    tags = []

    # 规律O
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
            other_down = jc_d_chg < -2 or jc_a_chg < -2
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
                reasoning.append(f"竞彩造热主+澳门推客→信号矛盾→竞彩方向被削弱")
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

    # 极端推离
    if not prediction:
        if chip_state == "极端推离主":
            prediction = "客胜或平"
            tags.append("推离主")
            reasoning.append("竞彩主赔大幅升高→主队被推离→难出")
        elif chip_state == "极端推离客":
            prediction = "主胜或平"
            tags.append("推离客")
            reasoning.append("竞彩客赔大幅升高→客队被推离→难出")

    # 赔率绝对值
    if not prediction:
        if jc_pressure == "低" and jc_min_dir == conf_dir:
            prediction = jc_min_dir
            tags.append("赔付压力")
            reasoning.append(f"竞彩{jc_min_dir}赔{jc_min:.2f}(赔付{jc_pressure})，与置信度方向一致")

    # 默认
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
        pred_odds = jc_h_rt if "主" in prediction else (jc_a_rt if "客" in prediction else jc_d_rt)
        if pred_odds and pred_odds > 3.5:
            reasoning.append(f"⚠️ 预测方向竞彩赔{pred_odds:.2f}>3.5，赔付压力高，需警惕")

    # 方向对比附加标签
    if dir_compare == "澳门不动" and hardness_tags:
        dir_compare_display = f"澳门不动{' '.join(hardness_tags)}"
    else:
        dir_compare_display = dir_compare

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
        'disp_h_init': disp_h_init, 'disp_d_init': disp_d_init, 'disp_a_init': disp_a_init,
        'disp_h': disp_h, 'disp_d': disp_d, 'disp_a': disp_a,
        'disp_avg': disp_avg,
        'consistency': consistency,
        'chip_state': chip_state,
        'chip_desc': chip_desc,
        'hardness_tags': hardness_tags,
        'jc_min_dir': jc_min_dir,
        'jc_pressure': jc_pressure,
        'dir_compare': dir_compare,
        'dir_compare_display': dir_compare_display,
        'prediction': prediction,
        'tags': tags,
        'reasoning': reasoning,
    }
    return result


# ==================== 主流程 ====================

# 扫描所有源数据文件
files = sorted(glob.glob(os.path.join(DATA_DIR, "*_源数据.md")))
print(f"找到 {len(files)} 个源数据文件")

# 解析所有比赛
all_matches = []
parse_errors = []
for f in files:
    try:
        m = parse_source_file(f)
        all_matches.append(m)
        print(f"  ✅ {m['id']} {m['home']}vs{m['away']}")
        print(f"     竞彩初盘: {m['jc_h_init']}/{m['jc_d_init']}/{m['jc_a_init']} → 即时: {m['jc_h_rt']}/{m['jc_d_rt']}/{m['jc_a_rt']}")
        print(f"     澳门初盘: {m['am_h_init']}/{m['am_d_init']}/{m['am_a_init']} → 即时: {m['am_h_rt']}/{m['am_d_rt']}/{m['am_a_rt']}")
    except Exception as e:
        print(f"  ❌ {os.path.basename(f)}: {e}")
        parse_errors.append(os.path.basename(f))

print(f"\n解析成功: {len(all_matches)} 场, 失败: {len(parse_errors)} 场")
if parse_errors:
    print(f"失败文件: {parse_errors}")

# 分析所有比赛
results = []
for m in all_matches:
    r = analyze_match(m)
    results.append(r)

# 按置信度排序
results.sort(key=lambda x: x['confidence'], reverse=True)

# 生成Markdown报告
report = []
report.append("# 3.31 比赛分析报告（基于4.01修正版框架）")
report.append("")
report.append("> 分析日期：2026-04-01 | 共" + str(len(results)) + "场比赛")
report.append("> 数据来源：500.com竞彩足球 | 竞彩初盘/即时盘从源数据自动解析")
report.append("> 核心原则：竞彩赔率变化=主信号，澳门心水=辅助信号，赔率绝对值=赔付判断")
report.append("")
report.append("---")
report.append("")

# 一、完整数据列表（按OUTPUT_TEMPLATE格式）
report.append("## 一、完整数据列表")
report.append("")
report.append("| 编号 | 对阵 | 置信度 | 澳门心水 | 近况差 | 初盘(竞彩) | 初盘(澳门) | 离散度(初盘→即时) | 一致性 | 变化(竞彩) | 变化(澳门) | 方向对比 | 最终预测 |")
report.append("|------|------|--------|----------|--------|-----------|-----------|------------------|--------|-----------|-----------|----------|----------|")

for r in results:
    # 初盘竞彩
    jc_init_str = f"{r['jc_h_init']}/{r['jc_d_init']}/{r['jc_a_init']}" if r['jc_h_init'] else "—"
    # 初盘澳门
    am_init_str = f"{r['am_h_init']}/{r['am_d_init']}/{r['am_a_init']}" if r['am_h_init'] else "—"
    # 离散度 初盘→即时
    disp_init = f"H{r['disp_h_init']:+.1f} D{r['disp_d_init']:+.1f} A{r['disp_a_init']:+.1f}"
    disp_rt = f"H{r['disp_h']:+.1f} D{r['disp_d']:+.1f} A{r['disp_a']:+.1f}"
    disp_str = f"{disp_init}→{disp_rt}"
    # 竞彩变化
    def fmt_chg(v):
        if abs(v) < 0.05:
            return "—"
        return f"{v:+.1f}%"
    jc_chg_str = f"H{fmt_chg(r['jc_h_chg'])} D{fmt_chg(r['jc_d_chg'])} A{fmt_chg(r['jc_a_chg'])}"
    am_chg_str = f"H{fmt_chg(r['am_h_chg'])} D{fmt_chg(r['am_d_chg'])} A{fmt_chg(r['am_a_chg'])}"

    tags_str = "、".join(r['tags']) if r['tags'] else "—"
    pred = r['prediction']

    report.append(f"| {r['id']} | {r['home']}vs{r['away']} | {r['confidence']:.0f}% | {r['macau_rec']} | {r['form_diff']:+.0f} | {jc_init_str} | {am_init_str} | {disp_str} | {r['consistency']} | {jc_chg_str} | {am_chg_str} | {r['dir_compare_display']} | **{pred}** |")

report.append("")
report.append("---")
report.append("")

# 二、汇总表
report.append("## 二、预测汇总")
report.append("")
report.append("| 编号 | 比赛 | 赛事 | 近况差 | 置信度 | 竞彩初盘 | 竞彩即时 | 竞彩变化 | 澳门不动 | 预测 | 标签 |")
report.append("|------|------|------|--------|--------|----------|----------|----------|----------|------|------|")
for r in results:
    jc_total = abs(r['jc_h_chg']) + abs(r['jc_d_chg']) + abs(r['jc_a_chg'])
    am_total = abs(r['am_h_chg']) + abs(r['am_d_chg']) + abs(r['am_a_chg'])
    jc_init_str = f"{r['jc_h_init']}/{r['jc_d_init']}/{r['jc_a_init']}" if r['jc_h_init'] else "—"
    jc_rt_str = f"{r['jc_h_rt']}/{r['jc_d_rt']}/{r['jc_a_rt']}" if r['jc_h_rt'] else "—"
    jc_chg_str = f"H{r['jc_h_chg']:+.1f}% D{r['jc_d_chg']:+.1f}% A{r['jc_a_chg']:+.1f}%"
    am_str = "✅不动" if am_total < 0.5 else f"{am_total:.1f}%"
    tags_str = "、".join(r['tags']) if r['tags'] else "—"
    report.append(f"| {r['id']} | {r['home']}vs{r['away']} | {r['league']} | {r['form_diff']:+.0f} | {r['confidence']:.0f}% | {jc_init_str} | {jc_rt_str} | {jc_chg_str} | {am_str} | **{r['prediction']}** | {tags_str} |")

report.append("")
report.append("---")
report.append("")

# 三、重点场次分析
report.append("## 三、重点场次详细分析")
report.append("")

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
        report.append(f"- **竞彩初盘**: 主{r['jc_h_init']} / 平{r['jc_d_init']} / 客{r['jc_a_init']}")
        report.append(f"- **竞彩即时**: 主{r['jc_h_rt']} / 平{r['jc_d_rt']} / 客{r['jc_a_rt']}")
        report.append(f"- **竞彩变化**: 主{r['jc_h_chg']:+.1f}% | 平{r['jc_d_chg']:+.1f}% | 客{r['jc_a_chg']:+.1f}%")
        report.append(f"- **澳门初盘**: 主{r['am_h_init']} / 平{r['am_d_init']} / 客{r['am_a_init']}")
        report.append(f"- **澳门即时**: 主{r['am_h_rt']} / 平{r['am_d_rt']} / 客{r['am_a_rt']}")
        report.append(f"- **澳门变化**: 主{r['am_h_chg']:+.1f}% | 平{r['am_d_chg']:+.1f}% | 客{r['am_a_chg']:+.1f}%")
        report.append(f"- **澳门心水**: {r['macau_rec']}")
        report.append(f"- **离散度**: 初盘均值{(abs(r['disp_h_init'])+abs(r['disp_d_init'])+abs(r['disp_a_init']))/3:.1f}% → 即时均值{r['disp_avg']:.1f}%（{r['consistency']}）")
        report.append(f"- **方向对比**: {r['dir_compare']}")
        report.append(f"- **筹码状态**: {r['chip_state']} — {r['chip_desc']}")
        if r['hardness_tags']:
            report.append(f"- **盘口标签**: {' '.join(r['hardness_tags'])}")
        report.append(f"- **竞彩最低赔**: {r['jc_min_dir']}（{min(r['jc_h_rt'] or 99, r['jc_d_rt'] or 99, r['jc_a_rt'] or 99):.2f}，赔付压力{r['jc_pressure']}）")
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
        report.append(f"- **{r['id']} {r['home']}vs{r['away']}**: {r['prediction']}（{'；'.join(r['reasoning'])}）")
    report.append("")
else:
    report.append("本期无明确爆冷信号。")
    report.append("")

report.append("---")
report.append("")

# 四、全场详细数据
report.append("## 四、全场详细数据")
report.append("")
for r in results:
    report.append(f"### {r['id']} {r['home']} vs {r['away']}")
    report.append("")
    report.append(f"| 维度 | 数据 |")
    report.append(f"|------|------|")
    report.append(f"| 近况 | 主{r['home_form']}({r['home_score']}分) vs 客{r['away_form']}({r['away_score']}分) |")
    report.append(f"| 近况差 | {r['form_diff']:+.0f}分 |")
    report.append(f"| 置信度 | {r['confidence']:.0f}% → {r['conf_dir']} |")
    report.append(f"| **竞彩初盘** | **主{r['jc_h_init']} / 平{r['jc_d_init']} / 客{r['jc_a_init']}** |")
    report.append(f"| **竞彩即时** | **主{r['jc_h_rt']} / 平{r['jc_d_rt']} / 客{r['jc_a_rt']}** |")
    report.append(f"| 竞彩变化 | 主{r['jc_h_chg']:+.1f}% 平{r['jc_d_chg']:+.1f}% 客{r['jc_a_chg']:+.1f}% |")
    report.append(f"| 澳门初盘 | 主{r['am_h_init']} / 平{r['am_d_init']} / 客{r['am_a_init']} |")
    report.append(f"| 澳门即时 | 主{r['am_h_rt']} / 平{r['am_d_rt']} / 客{r['am_a_rt']} |")
    report.append(f"| 澳门变化 | 主{r['am_h_chg']:+.1f}% 平{r['am_d_chg']:+.1f}% 客{r['am_a_chg']:+.1f}% |")
    report.append(f"| 澳门心水 | {r['macau_rec']} |")
    report.append(f"| 离散度 | H{r['disp_h']:+.1f} D{r['disp_d']:+.1f} A{r['disp_a']:+.1f}（均值{r['disp_avg']:.1f}%）|")
    report.append(f"| 一致性 | {r['consistency']} |")
    report.append(f"| 方向对比 | {r['dir_compare']} |")
    report.append(f"| 筹码状态 | {r['chip_state']} |")
    if r['hardness_tags']:
        report.append(f"| 盘口标签 | {' '.join(r['hardness_tags'])} |")
    report.append(f"| **预测** | **{r['prediction']}** |")
    report.append(f"| **分析** | {'；'.join(r['reasoning']) if r['reasoning'] else '—'} |")
    report.append("")

report.append("---")
report.append("")
report.append("## 五、免责声明")
report.append("")
report.append("以上分析基于赔率数据和近况评分模型，仅供娱乐参考，不构成任何投注建议。足球比赛受多种因素影响，赔率分析存在不确定性。请理性对待。")

output = "\n".join(report)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(output)

print(f"\n✅ 报告已生成: {OUTPUT_FILE}")
print(f"\n共分析 {len(results)} 场比赛")
print(f"\n=== 高置信场次 ===")
for r in high_conf:
    print(f"  {r['id']} {r['home']}vs{r['away']}: {r['prediction']} (置信{r['confidence']:.0f}%)")
    print(f"    竞彩初盘: {r['jc_h_init']}/{r['jc_d_init']}/{r['jc_a_init']} → 即时: {r['jc_h_rt']}/{r['jc_d_rt']}/{r['jc_a_rt']}")
    print(f"    竞彩变化: H{r['jc_h_chg']:+.1f}% D{r['jc_d_chg']:+.1f}% A{r['jc_a_chg']:+.1f}%")
print(f"\n=== 可能爆冷 ===")
for r in cold:
    print(f"  {r['id']} {r['home']}vs{r['away']}: {r['prediction']}")
print(f"\n=== 盘口硬信号 ===")
hard_matches = [r for r in results if r['hardness_tags']]
for r in hard_matches:
    print(f"  {r['id']} {r['home']}vs{r['away']}: {' '.join(r['hardness_tags'])} → {r['prediction']}")
