# 置信度>=55%的比赛格式化输出
import re

content = open('result.txt', 'r', encoding='utf-8', errors='ignore').read()

# 分割每个比赛块
blocks = re.split(r'={80,}', content)[1:]  # 跳过开头

print('=' * 70)
print('置信度>=55%的比赛（共15场）')
print('=' * 70)

count = 0
for block in blocks:
    if 'V7预测:' not in block:
        continue

    # 提取信息
    filename = re.search(r'【([^】]+)】', block)
    v7_pred = re.search(r'V7预测: ([^\(]+) \(置信度: (\d+)%\)', block)
    actual = re.search(r'实际结果: ([^\[]+)\[([^\]]+)\]', block)
    macao = re.search(r'澳门推荐: ([^\n|\|]+)', block)
    home_form = re.search(r'主队近况: ([^\n|\|]+)', block)
    away_form = re.search(r'客队近况: ([^\n|\|]+)', block)
    init_8 = re.search(r'初盘8数量: (\d+),', block)
    real_8 = re.search(r'即时盘8数量: (\d+),', block)
    diff_8 = re.search(r'变化: ([^\n]+)', block)
    pattern = re.search(r'模式: ([^\n,]+)', block)
    recommendation = re.search(r'推荐: ([^\n]+)', block)

    if not all([filename, v7_pred, actual]):
        continue

    conf = int(v7_pred.group(2))
    if conf < 55:
        continue

    count += 1

    # 提取主队/客队
    match_info = filename.group(1)
    teams_part = match_info.split('_', 1)[1] if '_' in match_info else match_info
    teams = teams_part.replace('vs', 'vs')

    # 提取胜场数
    home_w = re.search(r'\((\d+)胜\)', home_form.group(1)) if home_form else None
    away_w = re.search(r'\((\d+)胜\)', away_form.group(1)) if away_form else None
    home_wins = home_w.group(1) if home_w else '?'
    away_wins = away_w.group(1) if away_w else '?'

    # 清理澳门推荐
    macao_str = macao.group(1).strip() if macao else ''

    print(f"\n{count}. {match_info}")
    print(f"V7预测: {v7_pred.group(1).strip()} ({conf}%)")
    print(f"实际: {actual.group(1).strip()} [{actual.group(2)}]")
    print(f"澳门推荐: {macao_str}")
    print(f"主队近况: {home_form.group(1).strip().split('|')[0].strip()} ({home_wins}胜)")
    print(f"客队近况: {away_form.group(1).strip().split('|')[0].strip()} ({away_wins}胜)")
    print(f"8探测: 初盘{init_8.group(1)} → 即时{real_8.group(1)} ({diff_8.group(1)})")
    print(f"模式: {pattern.group(1).strip() if pattern else 'N/A'}")
    print(f"推荐: {recommendation.group(1).strip() if recommendation else 'N/A'}")
