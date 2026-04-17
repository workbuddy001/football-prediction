# -*- coding: utf-8 -*-
"""
fetch_full_enhanced.py - 增强版抓取脚本 v2
功能：
1. 抓取竞彩列表页（胜平负/让球）
2. 抓取半全场页面 (playid=272)
3. 抓取进球数页面 (playid=270)
4. 抓取比分页面 (playid=271)
5. 抓取亚洲盘口页面
6. 生成预测记录模板文件
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import urllib.request
import re
import json
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match_record import MatchRecord, generate_txt

# ==================== 配置 ====================
TARGET_DATE = "2026-04-17"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "分析模板", TARGET_DATE.replace('-', '.'))
RAW_HTML_BASE = os.path.join(OUT_DIR, f"page_raw_{TARGET_DATE}")
# 输出完整版（包含30家公司欧赔）
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "分析模板", f"matches_full_{TARGET_DATE}.json")

os.makedirs(OUT_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://odds.500.com/',
}


def fetch(url):
    """通用HTTP请求"""
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=20)
    return resp.read().decode('gbk', errors='replace')


def strip_tags(html):
    """去除HTML标签"""
    return re.sub(r'<[^>]+>', '', html).strip()


def parse_shuju(fixture_id):
    """抓取数据分析页面（近况/交锋/澳门推荐）"""
    url = f'https://odds.500.com/fenxi/shuju-{fixture_id}.shtml'
    try:
        content = fetch(url)
    except Exception as e:
        return {'error': str(e)}

    result = {}

    # 历史交锋
    his = re.search(r'<span class="his_info">(.*?)</span>\s*</div>', content, re.S)
    if his:
        his_text = strip_tags(his.group(1))
        result['交战历史摘要'] = his_text
        m_short = re.search(r'双方近\d+次交战，(.+?)(\d+)胜(\d+)平(\d+)负', his_text)
        if m_short:
            team = m_short.group(1).strip('，, ')
            w, d, l = m_short.group(2), m_short.group(3), m_short.group(4)
            result['历史交锋'] = f'{team} {w}胜{d}和{l}负'

    # 近况摘要
    records = re.findall(r'<p class="record_msg">(.*?)</p>', content, re.S)
    if len(records) >= 1:
        result['主队近况'] = strip_tags(records[0])
    if len(records) >= 2:
        result['客队近况'] = strip_tags(records[1])

    # 澳门推荐和近况走势
    recommend_block = re.search(r'<div class="M_box recommend">(.*?)</table>', content, re.S)
    if recommend_block:
        rb = recommend_block.group(1)
        tr_list = re.findall(r'<tr>(.*?)</tr>', rb, re.S)

        def parse_form(td_html):
            letters = re.findall(r'<font[^>]*>([WLD1])</font>', td_html, re.I)
            return ''.join(letters).upper()

        if len(tr_list) >= 1:
            home_tds = re.findall(r'<td[^>]*>(.*?)</td>', tr_list[0], re.S)
            if len(home_tds) >= 2:
                result['主队近况走势'] = parse_form(home_tds[1])
            if len(home_tds) >= 3:
                result['主队盘路走势'] = parse_form(home_tds[2])

        if len(tr_list) >= 2:
            away_tds = re.findall(r'<td[^>]*>(.*?)</td>', tr_list[1], re.S)
            if len(away_tds) >= 2:
                result['客队近况走势'] = parse_form(away_tds[1])
            if len(away_tds) >= 3:
                result['客队盘路走势'] = parse_form(away_tds[2])

        tip_m = re.search(r'推介\s*-\s*<font[^>]*>(.*?)</font>', rb, re.S)
        if tip_m:
            result['澳门推荐'] = strip_tags(tip_m.group(1)).strip()

        analysis_m = re.search(r'class="td_one td_no4"[^>]*>(.*?)</td>', rb, re.S)
        if analysis_m:
            result['澳门分析'] = strip_tags(analysis_m.group(1)).strip('\u3000').strip()

    return result


def parse_yazhi(fixture_id):
    """抓取亚洲盘口页面"""
    url = f'https://odds.500.com/fenxi/yazhi-{fixture_id}.shtml'
    try:
        content = fetch(url)
    except Exception as e:
        return {'error': str(e)}

    result = {}

    # 查找表格行
    yazhi_rows = re.findall(
        r'<tr[^>]*class="[^"]*tr_?(?:odd|even)"[^>]*>(.*?)</tr>',
        content, re.S
    )

    for row in yazhi_rows:
        co_m = re.search(r'<span[^>]*class="quancheng"[^>]*>([^<]+)</span>', row)
        if not co_m:
            continue
        company = co_m.group(1).strip()

        # 提取赔率数据
        numbers = re.findall(r'(?:data-odds|>)(\d+\.?\d*)', row)
        if len(numbers) >= 4:
            result[company] = {
                'init': {
                    'home_odds': numbers[0] if len(numbers) > 0 else '',
                    'handicap': numbers[1] if len(numbers) > 1 else '',
                    'away_odds': numbers[2] if len(numbers) > 2 else '',
                },
                'realtime': {
                    'home_odds': numbers[3] if len(numbers) > 3 else '',
                    'handicap': numbers[4] if len(numbers) > 4 else '',
                    'away_odds': numbers[5] if len(numbers) > 5 else '',
                }
            }

    return result


def parse_ouzhi(fixture_id):
    """抓取欧洲赔率详情页面（30家公司初盘+即时盘）"""
    url = f'https://odds.500.com/fenxi/ouzhi-{fixture_id}.shtml'
    try:
        content = fetch(url)
    except Exception as e:
        return {'error': str(e)}
    
    results = []
    lines = content.split('\n')
    
    current_company = ""
    current_odds = []
    
    for line in lines:
        # 公司名行
        if 'tb_plgs' in line:
            m = re.search(r'<span[^>]*>([^<]+)</span>', line)
            if m:
                current_company = m.group(1).strip()
        
        # 赔率行（包含 klfc=）
        if 'klfc=' in line and current_company:
            odds = re.findall(r'<td[^>]*>\s*([\d.]+)\s*</td>', line)
            if odds:
                current_odds.extend(odds)
                # 当有6个赔率时，保存
                if len(current_odds) >= 6:
                    results.append({
                        '公司': current_company,
                        '初盘胜': current_odds[0], '初盘平': current_odds[1], '初盘负': current_odds[2],
                        '即时胜': current_odds[3], '即时平': current_odds[4], '即时负': current_odds[5],
                    })
                    current_company = ""
                    current_odds = []
    
    return {'欧赔列表': results}


def parse_list_page_with_fixture(html_content, fixture_id):
    """
    从列表页解析指定比赛的赔率数据
    支持：胜平负、让球、半全场、比分、进球数等
    """
    # 查找该比赛的行 (fixtureid可能在属性中间)
    match_row_m = re.search(
        rf'<tr[^>]*data-fixtureid="{fixture_id}"[^>]*>(.*?)</tr>',
        html_content, re.S
    )

    if not match_row_m:
        return {}

    row_html = match_row_m.group(1)
    result = {}

    # 提取 data-sp 属性（赔率）
    spf = re.findall(r'data-type="spf"\s+data-value="(\d+)"\s+data-sp="([\d.]+)"', row_html)
    for val, sp in spf:
        label = {'3': '胜', '1': '平', '0': '负'}.get(val, val)
        result[f'竞彩_{label}'] = sp

    # 提取让球数据
    rq = re.findall(r'data-type="rq"\s+data-value="(\d+)"\s+data-sp="([\d.]+)"', row_html)
    for val, sp in rq:
        label = {'3': '让胜', '1': '让平', '0': '让负'}.get(val, val)
        result[label] = sp

    # 提取半全场 (data-type="bqc")
    # data-value 格式: "3-3"(胜胜), "3-1"(胜平), "3-0"(胜负),
    #                   "1-3"(平胜), "1-1"(平平), "1-0"(平负),
    #                   "0-3"(负胜), "0-1"(负平), "0-0"(负负)
    hf_value_map = {
        '3-3': '胜胜', '3-1': '胜平', '3-0': '胜负',
        '1-3': '平胜', '1-1': '平平', '1-0': '平负',
        '0-3': '负胜', '0-1': '负平', '0-0': '负负',
    }
    hf_buttons = re.findall(r'data-type="bqc"\s+data-value="([^"]+)"\s+data-sp="([\d.]+)"', row_html)
    for val, sp in hf_buttons:
        label = hf_value_map.get(val, f'未知_{val}')
        result[f'半全_{label}'] = sp

    # 提取比分 (data-type="bf")
    bf_buttons = re.findall(r'data-type="bf"\s+data-value="([^"]+)"\s+data-sp="([\d.]+)"', row_html)
    for val, sp in bf_buttons:
        result[f'比分_{val}'] = sp

    # 提取进球数 (data-type="jqs")
    jqs_buttons = re.findall(r'data-type="jqs"\s+data-value="(\d+)"\s+data-sp="([\d.]+)"', row_html)
    for val, sp in jqs_buttons:
        key = val if int(val) < 7 else '7+'
        result[f'进球_{key}'] = sp

    # 提取大小球 (data-type="dxf")
    dxf_buttons = re.findall(r'data-type="dxf"\s+data-value="([^"]+)"\s+data-sp="([\d.]+)"', row_html)
    for val, sp in dxf_buttons:
        if '大' in val or float(val) > 2.5:
            result['大球'] = sp
            result['盘口'] = val
        else:
            result['小球'] = sp

    return result


def fetch_page_by_playid(playid):
    """按玩法ID抓取列表页"""
    url = f"https://trade.500.com/jczq/?playid={playid}&g=2&date={TARGET_DATE}"
    try:
        content = fetch(url)
        # 保存原始页面
        filepath = f"{RAW_HTML_BASE}_playid{playid}.html"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return content
    except Exception as e:
        print(f"  抓取 playid={playid} 失败: {e}")
        return ""


def attr(attrs_str, name):
    """从属性字符串提取属性值"""
    m = re.search(rf'data-{name}="([^"]*)"', attrs_str)
    return m.group(1) if m else ''


def extract_match_list(html_content):
    """提取比赛列表"""
    match_rows = re.findall(
        r'<tr[^>]+class="bet-tb-tr[^"]*"([^>]+)>(.*?)</tr>',
        html_content, re.S
    )
    matches = []
    for attrs_str, row_html in match_rows:
        fixture_id = attr(attrs_str, 'fixtureid')
        if fixture_id:
            matches.append({
                'fixture_id': fixture_id,
                'match_num': attr(attrs_str, 'matchnum'),
                'league': attr(attrs_str, 'simpleleague'),
                'date': attr(attrs_str, 'matchdate'),
                'time': attr(attrs_str, 'matchtime'),
                'home': attr(attrs_str, 'homesxname'),
                'away': attr(attrs_str, 'awaysxname'),
                'rangqiu': attr(attrs_str, 'rangqiu'),
            })
    return matches


# ==================== 主程序 ====================
def main():
    print(f"{'=' * 60}")
    print(f"增强版抓取脚本 v2 - {TARGET_DATE}")
    print(f"{'=' * 60}")

    # 1. 抓取主列表页（胜平负/让球）
    print(f"\n[1/5] 抓取主列表页 (playid=312)...")
    html_312 = fetch_page_by_playid(312)
    if not html_312:
        print("  ✗ 抓取失败")
        return

    # 2. 抓取附属赔率页面
    print(f"\n[2/5] 抓取半全场页面 (playid=272)...")
    html_272 = fetch_page_by_playid(272)
    time.sleep(0.5)

    print(f"\n[3/5] 抓取进球数页面 (playid=270)...")
    html_270 = fetch_page_by_playid(270)
    time.sleep(0.5)

    print(f"\n[4/5] 抓取比分页面 (playid=271)...")
    html_271 = fetch_page_by_playid(271)

    # 3. 提取比赛列表
    print(f"\n[5/5] 解析比赛数据...")
    matches = extract_match_list(html_312)
    print(f"  发现 {len(matches)} 场比赛")

    all_data = []

    for i, match in enumerate(matches):
        fixture_id = match['fixture_id']
        print(f"\n  [{i+1}/{len(matches)}] {match['match_num']} {match['league']}: {match['home']} vs {match['away']}")

        # 从各页面提取该比赛赔率
        odds_312 = parse_list_page_with_fixture(html_312, fixture_id)
        odds_272 = parse_list_page_with_fixture(html_272, fixture_id)
        odds_270 = parse_list_page_with_fixture(html_270, fixture_id)
        odds_271 = parse_list_page_with_fixture(html_271, fixture_id)

        # 合并赔率
        all_odds = {**odds_312, **odds_272, **odds_270, **odds_271}

        # 抓取数据分析
        print(f"    → 抓取数据分析...")
        shuju = parse_shuju(fixture_id)
        time.sleep(0.3)

        # 抓取亚洲盘口
        print(f"    → 抓取亚洲盘口...")
        yazhi = parse_yazhi(fixture_id)
        time.sleep(0.3)

        # 抓取欧洲赔率（30家公司初盘+即时盘）
        print(f"    → 抓取欧赔数据...")
        ouzhi = parse_ouzhi(fixture_id)
        time.sleep(0.3)

        entry = {
            **match,
            '赔率': all_odds,
            '数据分析': shuju,
            '亚洲盘口': yazhi,
            '欧赔数据': ouzhi,  # 新增
        }
        all_data.append(entry)

        # 打印摘要
        if '历史交锋' in shuju:
            print(f"    交锋: {shuju['历史交锋']}")
        if '澳门推荐' in shuju:
            print(f"    心水: {shuju['澳门推荐']}")
        if yazhi:
            print(f"    亚盘: {len(yazhi)} 家公司")
        if ouzhi.get('欧赔列表'):
            print(f"    欧赔: {len(ouzhi['欧赔列表'])} 家公司")

    # 保存完整数据
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\n  ✓ 数据已保存: {OUT_JSON}")

    print(f"\n{'=' * 60}")
    print(f"抓取完成！共 {len(all_data)} 场比赛")
    print(f"{'=' * 60}")

    # 生成预测记录模板
    print(f"\n生成预测记录模板...")
    generate_templates(all_data)

    return all_data


def generate_templates(all_data):
    """为每场比赛生成预测记录模板文件"""
    for entry in all_data:
        record = MatchRecord(
            fixture_id=entry.get('fixture_id', ''),
            home=entry.get('home', ''),
            away=entry.get('away', ''),
            league=entry.get('league', ''),
            match_time=f"{entry.get('date', '')} {entry.get('time', '')}",
            handicap=entry.get('rangqiu', '')
        )

        # 填充数据
        odds = entry.get('赔率', {})
        shuju = entry.get('数据分析', {})
        yazhi = entry.get('亚洲盘口', {})

        # 竞彩赔率
        record.jc_odds = {
            'init': {
                'home': float(odds.get('竞彩_胜', 0)),
                'draw': float(odds.get('竞彩_平', 0)),
                'away': float(odds.get('竞彩_负', 0))
            },
            'realtime': {
                'home': float(odds.get('竞彩_胜', 0)),
                'draw': float(odds.get('竞彩_平', 0)),
                'away': float(odds.get('竞彩_负', 0))
            }
        }

        # 澳门心水
        record.macau_rec = shuju.get('澳门推荐', '')
        record.macau_analysis = shuju.get('澳门分析', '')
        record.history_h2h = shuju.get('历史交锋', '')

        # 近况走势
        record.home_form = shuju.get('主队近况走势', '')
        record.away_form = shuju.get('客队近况走势', '')

        # 半全场赔率
        hf_keys = ['胜胜', '胜平', '胜负', '平胜', '平平', '平负', '负胜', '负平', '负负']
        for key in hf_keys:
            val = odds.get(f'半全_{key}', '')
            if val:
                record.half_full_odds[key] = val

        # 比分赔率
        score_keys = ['1:0', '2:0', '2:1', '3:0', '3:1', '3:2', '4:0', '4:1', '4:2', '5:0', '5:1', '5:2',
                     '0:0', '0:1', '0:2', '0:3', '1:1', '1:2', '1:3', '2:2', '2:3',
                     '胜其它', '负其它', '平其它']
        for key in score_keys:
            val = odds.get(f'比分_{key}', '')
            if val:
                record.score_odds[key] = val

        # 进球数
        for i in range(8):
            key = str(i) if i < 7 else '7+'
            val = odds.get(f'进球_{i}' if i < 7 else '进球_7', '')
            if val:
                record.total_goals_odds[key] = val

        # 大小球
        if '大球' in odds:
            record.over_under_odds = {
                '大球': odds.get('大球', ''),
                '小球': odds.get('大球', ''),  # 需要另一个字段
                '盘口': odds.get('盘口', '2.5')
            }

        # 亚洲盘口
        record.yazhi = yazhi

        # 生成文件
        filename, content = generate_txt(record)
        filepath = os.path.join(OUT_DIR, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ {filename}")
        except Exception as e:
            print(f"  ✗ {filename}: {e}")


if __name__ == "__main__":
    main()
