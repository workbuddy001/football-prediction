# 筛选置信度>55%的比赛

with open('v7_8_full_analysis.md', encoding='utf-8') as f:
    lines = f.readlines()

# 先看看数据结构
print("前5行数据:")
for i, line in enumerate(lines[19:24]):
    print(f"{i}: {line[:100]}")

results = []
for line in lines[19:]:
    if '|' not in line:
        continue
    parts = [p.strip() for p in line.split('|')]
    print(f"Parts: {parts}")
    if len(parts) < 14:
        continue
    try:
        conf_str = parts[4]
        conf = int(conf_str.replace('%', ''))
        print(f"Confidence: {conf}")
        if conf > 55:
            results.append(parts)
    except Exception as e:
        print(f"Error: {e}")
        pass

print(f"\n找到 {len(results)} 场置信度>55%的比赛")
