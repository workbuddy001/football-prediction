"""提取3.11周三9场比赛关键数据 V2"""
import re, os, glob

def calc_form_score(form_str):
    """计算近况得分：W=3 D=1 L=0，最近一场×2，取5场"""
    scores = {'W': 3, 'D': 1, 'L': 0}
    recent = form_str[:5]  # 左边=最新
    total = 0
    for i, ch in enumerate(recent):
        if i == 0:
            total += scores.get(ch, 0) * 2
        else:
            total += scores.get(ch, 0)
    return total

def calc_confidence(avg_init_h, avg_init_d, avg_init_a, form_diff):
    """基于赔率隐含概率+近况差调整的置信度"""
    inv_h = 1 / avg_init_h
    inv_d = 1 / avg_init_d
    inv_a = 1 / avg_init_a
    total = inv_h + inv_d + inv_a
    prob_h = inv_h / total * 100
    prob_d = inv_d / total * 100
    prob_a = inv_a / total * 100
    
    # 置信度 = 赔率概率 + 近况差修正
    # 主队近况好→主胜概率提升；客队近况好→客胜概率提升
    adj = form_diff * 0.5  # 近况差修正系数
    
    conf_h = prob_h + adj
    conf_a = prob_a - adj
    conf_d = prob_d
    
    if conf_h >= conf_a and conf_h >= conf_d:
        return max(30, min(90, conf_h)), "主胜", prob_h, prob_d, prob_a
    elif conf_a >= conf_h and conf_a >= conf_d:
        return max(30, min(90, conf_a)), "客胜", prob_h, prob_d, prob_a
    else:
        return max(30, min(90, conf_d)), "平局", prob_h, prob_d, prob_a

data_dir = r"d:\work\workbuddy\足球预测\分析模板\3.11"

files = sorted(glob.glob(os.path.join(data_dir, "*_源数据.md")))

for f in files:
    with open(f, encoding='utf-8') as fh:
        content = fh.read()
    
    # 提取编号
    num_match = re.search(r'(周三\d+)', os.path.basename(f))
    num = num_match.group(1) if num_match else "?"
    
    # 提取队名 - 从markdown表格中提取
    home_match = re.search(r'\|\s*主队\s*\|\s*(.+?)\s*\|', content)
    away_match = re.search(r'\|\s*客队\s*\|\s*(.+?)\s*\|', content)
    home = home_match.group(1).strip() if home_match else "?"
    away = away_match.group(1).strip() if away_match else "?"
    
    # 近况走势
    hf_match = re.search(r'主队近况走势\s*\|\s*(\w+)', content)
    af_match = re.search(r'客队近况走势\s*\|\s*(\w+)', content)
    hf = hf_match.group(1) if hf_match else "?"
    af = af_match.group(1) if af_match else "?"
    
    # 近况差
    if hf != "?" and af != "?":
        hs = calc_form_score(hf)
        as_ = calc_form_score(af)
        diff = hs - as_
    else:
        diff = 0
    
    # 澳门推荐
    macao_match = re.search(r'\|\s*澳门推荐\s*\|\s*(.+?)\s*\|', content)
    macao = macao_match.group(1).strip() if macao_match else "?"
    
    # 澳门分析
    macao_analysis = re.search(r'\|\s*澳门分析\s*\|\s*(.+?)\s*\|', content)
    macao_text = macao_analysis.group(1).strip() if macao_analysis else ""
    
    # 提取初盘和即时赔率（分别从两个代码块中提取）
    # 初盘在"初盘赔率"section
    init_section = content.split("## 二、初盘赔率")[1].split("## 三、即时赔率")[0] if "## 二、初盘赔率" in content else ""
    rt_section = content.split("## 三、即时赔率")[1].split("## 四、")[0] if "## 三、即时赔率" in content else ""
    
    init_pattern = re.findall(r'\(([\d.]+),\s*([\d.]+),\s*([\d.]+)\)', init_section)
    rt_pattern = re.findall(r'\(([\d.]+),\s*([\d.]+),\s*([\d.]+)\)', rt_section)
    
    if init_pattern and rt_pattern:
        avg_init_h = sum(float(x[0]) for x in init_pattern) / len(init_pattern)
        avg_init_d = sum(float(x[1]) for x in init_pattern) / len(init_pattern)
        avg_init_a = sum(float(x[2]) for x in init_pattern) / len(init_pattern)
        
        avg_rt_h = sum(float(x[0]) for x in rt_pattern) / len(rt_pattern)
        avg_rt_d = sum(float(x[1]) for x in rt_pattern) / len(rt_pattern)
        avg_rt_a = sum(float(x[2]) for x in rt_pattern) / len(rt_pattern)
        
        hc = (avg_rt_h - avg_init_h) / avg_init_h * 100
        dc = (avg_rt_d - avg_init_d) / avg_init_d * 100
        ac = (avg_rt_a - avg_init_a) / avg_init_a * 100
        
        conf, pred, prob_h, prob_d, prob_a = calc_confidence(avg_init_h, avg_init_d, avg_init_a, diff)
    else:
        avg_init_h = avg_init_d = avg_init_a = 0
        avg_rt_h = avg_rt_d = avg_rt_a = 0
        hc = dc = ac = 0
        conf = 0
        pred = "?"
        prob_h = prob_d = prob_a = 0
    
    print(f"{num} | {home} vs {away}")
    print(f"  近况: {hf}/{af} | 近况差: {diff:+d} | 澳门: {macao}")
    print(f"  初盘: {avg_init_h:.2f}/{avg_init_d:.2f}/{avg_init_a:.2f} | 即时: {avg_rt_h:.2f}/{avg_rt_d:.2f}/{avg_rt_a:.2f}")
    print(f"  变化: H{hc:+.1f}% D{dc:+.1f}% A{ac:+.1f}% | 置信度: {conf:.1f}% → {pred}")
    print(f"  赔率概率: 主{prob_h:.1f}% 平{prob_d:.1f}% 客{prob_a:.1f}%")
    if macao_text:
        print(f"  澳门分析: {macao_text[:100]}")
    print()
