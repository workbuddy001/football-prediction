"""批量解析4.03周五源数据，提取关键赔率变化信息"""
import re
import os

data_dir = r"D:\work\workbuddy\足球预测\分析模板\4.03"

def parse_source_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    info = {}
    
    # 基本信息提取
    info['filename'] = os.path.basename(filepath)
    
    # 主队/客队
    m = re.search(r'\|\s*主队\s*\|\s*(.+?)\s*\|', content)
    if m: info['home'] = m.group(1).strip()
    m = re.search(r'\|\s*客队\s*\|\s*(.+?)\s*\|', content)
    if m: info['away'] = m.group(1).strip()
    
    # 赛事
    m = re.search(r'\|\s*赛事\s*\|\s*(.+?)\s*\|', content)
    if m: info['league'] = m.group(1).strip()
    
    # 比赛时间
    m = re.search(r'\|\s*比赛时间\s*\|\s*(.+?)\s*\|', content)
    if m: info['time'] = m.group(1).strip()
    
    # 主/客队近况走势
    m = re.search(r'\|\s*主队近况走势\s*\|\s*(.+?)\s*\|', content)
    if m: info['home_form'] = m.group(1).strip()
    m = re.search(r'\|\s*客队近况走势\s*\|\s*(.+?)\s*\|', content)
    if m: info['away_form'] = m.group(1).strip()
    
    # 主/客队近10场战绩
    m = re.search(r'\|\s*主队近况\s*\|\s*(.+?)\s*\|', content)
    if m: info['home_record'] = m.group(1).strip()
    m = re.search(r'\|\s*客队近况\s*\|\s*(.+?)\s*\|', content)
    if m: info['away_record'] = m.group(1).strip()
    
    # 历史交锋
    m = re.search(r'\|\s*历史交锋\s*\|\s*(.+?)\s*\|', content)
    if m: info['history'] = m.group(1).strip()
    
    # 澳门推荐
    m = re.search(r'\|\s*澳门推荐\s*\|\s*(.+?)\s*\|', content)
    if m: info['macao_tip'] = m.group(1).strip()
    
    # 澳门分析
    m = re.search(r'\|\s*澳门分析\s*\|\s*(.+?)\s*\|', content)
    if m: info['macao_analysis'] = m.group(1).strip()
    
    # 提取initial_odds和realtime_odds
    def extract_odds(content, label):
        pattern = rf'{label}\s*=\s*\[(.*?)\]'
        m = re.search(pattern, content, re.DOTALL)
        if not m: return []
        odds_str = m.group(1)
        odds = []
        for line in odds_str.strip().split('\n'):
            line = line.strip().rstrip(',').strip()
            if line.startswith('#') or not line:
                continue
            # Extract numbers
            nums = re.findall(r'\d+\.\d+', line)
            if len(nums) >= 3:
                odds.append((float(nums[0]), float(nums[1]), float(nums[2])))
        return odds
    
    initial = extract_odds(content, 'initial_odds')
    realtime = extract_odds(content, 'realtime_odds')
    
    info['initial_odds'] = initial
    info['realtime_odds'] = realtime
    
    # 计算关键变化
    if initial and realtime:
        # 竞彩 = index 0
        jc_init = initial[0]
        jc_real = realtime[0]
        info['jc_init'] = jc_init
        info['jc_real'] = jc_real
        info['jc_h_change'] = (jc_real[0] - jc_init[0]) / jc_init[0] * 100
        info['jc_d_change'] = (jc_real[1] - jc_init[1]) / jc_init[1] * 100
        info['jc_a_change'] = (jc_real[2] - jc_init[2]) / jc_init[2] * 100
        
        # 澳门 = index 2
        if len(initial) > 2 and len(realtime) > 2:
            am_init = initial[2]
            am_real = realtime[2]
            info['am_init'] = am_init
            info['am_real'] = am_real
            info['am_h_change'] = (am_real[0] - am_init[0]) / am_init[0] * 100
            info['am_d_change'] = (am_real[1] - am_init[1]) / am_init[1] * 100
            info['am_a_change'] = (am_real[2] - am_init[2]) / am_init[2] * 100
        
        # 趋势统计
        h_down = sum(1 for i, r in zip(initial, realtime) if r[0] < i[0])
        d_up = sum(1 for i, r in zip(initial, realtime) if r[1] > i[1])
        a_down = sum(1 for i, r in zip(initial, realtime) if r[2] < i[2])
        total = len(initial)
        info['trend_h_down'] = h_down
        info['trend_d_up'] = d_up
        info['trend_a_down'] = a_down
        info['trend_total'] = total
        
        # 判断心水方向赔率区间
        tip = info.get('macao_tip', '')
        am_real_a = am_real[2] if 'am_real' in info else 0
        am_real_h = am_real[0] if 'am_real' in info else 0
        am_real_d = am_real[1] if 'am_real' in info else 0
        
        if '和局' in tip or '平' in tip:
            info['tip_dir'] = '平'
            info['tip_odds'] = am_real_d
        elif '客' in tip:
            info['tip_dir'] = '客'
            info['tip_odds'] = am_real_a
        elif '主' in tip or '不败' in tip or '大胜' in tip:
            info['tip_dir'] = '主'
            info['tip_odds'] = am_real_h
        else:
            # 检查是否包含队名（默认推主队）
            home = info.get('home', '')
            if home and home[:3] in tip:
                info['tip_dir'] = '主'
                info['tip_odds'] = am_real_h
            else:
                info['tip_dir'] = tip[:6]
                info['tip_odds'] = 0
    
    return info

# 扫描所有周五文件
friday_files = sorted([f for f in os.listdir(data_dir) if f.startswith('周五') and f.endswith('_源数据.md')])

results = []
for f in friday_files:
    filepath = os.path.join(data_dir, f)
    info = parse_source_file(filepath)
    results.append(info)

# 输出汇总表格
print("=" * 120)
print(f"{'#':<4} {'比赛':<30} {'赛事':<6} {'心水':<8} {'心水赔率':<8} {'竞彩主%':<8} {'竞彩客%':<8} {'澳门主%':<8} {'澳门客%':<8} {'趋势':<20}")
print("=" * 120)

for i, r in enumerate(results):
    match = f"{r.get('home','?')[:6]}vs{r.get('away','?')[:6]}"
    league = r.get('league', '?')[:4]
    tip = r.get('tip_dir', '?')
    tip_odds = f"{r.get('tip_odds',0):.2f}" if r.get('tip_odds',0) > 0 else '?'
    
    jc_h = f"{r.get('jc_h_change',0):+.1f}%"
    jc_a = f"{r.get('jc_a_change',0):+.1f}%"
    am_h = f"{r.get('am_h_change',0):+.1f}%"
    am_a = f"{r.get('am_a_change',0):+.1f}%"
    
    trend_h = r.get('trend_h_down', 0)
    trend_total = r.get('trend_total', 0)
    trend = f"主降{trend_h}/{trend_total}"
    
    print(f"{i+1:<4} {match:<30} {league:<6} {tip:<8} {tip_odds:<8} {jc_h:<8} {jc_a:<8} {am_h:<8} {am_a:<8} {trend:<20}")

print("\n" + "=" * 120)
print("\n详细每场信息：")
for i, r in enumerate(results):
    print(f"\n--- {r['filename']} ---")
    print(f"  {r.get('home','?')} vs {r.get('away','?')} | {r.get('league','')} | {r.get('time','')}")
    print(f"  心水: {r.get('macao_tip','?')} | 心水方向: {r.get('tip_dir','?')} | 心水赔率: {r.get('tip_odds',0):.2f}")
    print(f"  竞彩: 初{r.get('jc_init',(0,0,0))} → 即{r.get('jc_real',(0,0,0))}")
    print(f"  竞彩变化: 主{r.get('jc_h_change',0):+.1f}% 平{r.get('jc_d_change',0):+.1f}% 客{r.get('jc_a_change',0):+.1f}%")
    if 'am_init' in r:
        print(f"  澳门: 初{r.get('am_init',(0,0,0))} → 即{r.get('am_real',(0,0,0))}")
        print(f"  澳门变化: 主{r.get('am_h_change',0):+.1f}% 平{r.get('am_d_change',0):+.1f}% 客{r.get('am_a_change',0):+.1f}%")
    print(f"  趋势: 主降{r.get('trend_h_down',0)}/{r.get('trend_total',0)}")
    print(f"  主近况: {r.get('home_form','?')} | 客近况: {r.get('away_form','?')}")
    if r.get('macao_analysis'):
        print(f"  澳门分析: {r.get('macao_analysis','')[:80]}")
