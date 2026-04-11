import pandas as pd

# 读取预测数据
df = pd.read_excel('d:/work/workbuddy/足球预测/3.15_比赛预测汇总.xlsx')

# 转换概率列
def to_float(x):
    if isinstance(x, str):
        return float(x.replace('%', ''))
    return float(x)

df['主胜概率'] = df['主胜概率'].apply(to_float)
df['平局概率'] = df['平局概率'].apply(to_float)
df['客胜概率'] = df['客胜概率'].apply(to_float)

# 实际比赛结果 (编号格式: 周日001)
actual_results = {
    '周日001': ('日本女', 1),
    '周日002': ('福冈黄蜂', 1),
    '周日003': ('首尔FC', 0),
    '周日004': ('仁川联', 2),  # 1:1 平局
    '周日005': ('墨胜利', 1),  # 4:1 主胜
    '周日006': ('乌德勒支', 0),  # 0:2 客胜
    '周日007': ('热那亚', 0),  # 0:2 客胜
    '周日008': ('汉诺威96', 2),  # 2:2 平局
    '周日009': ('马洛卡', 1),  # 2:1 主胜
    '周日010': ('费耶诺德', 1),  # 2:1 主胜
    '周日011': ('布兰', 0),  # 3:2 主胜
    '周日012': ('水晶宫', 2),  # 0:0 平局
    '周日013': ('诺丁汉', 2),  # 0:0 平局
    '周日014': ('曼联', 1),  # 3:1 主胜
    '周日015': ('比萨', 1),  # 3:1 主胜
    '周日016': ('博洛尼亚', 0),  # 0:1 客胜
    '周日017': ('美因茨', 0),  # 0:2 客胜
    '周日018': ('巴萨', 1),  # 5:2 主胜
    '周日019': ('瓦勒伦加', 1),  # 1:0 主胜
    '周日020': ('里昂', 2),  # 0:0 平局
    '周日021': ('利物浦', 2),  # 1:1 平局
    '周日022': ('柏林联合', 0),  # 0:1 客胜
    '周日023': ('科莫', 1),  # 2:1 主胜
    '周日024': ('贝蒂斯', 2),  # 1:1 平局
    '周日025': ('斯图加特', 1),  # 1:0 主胜
    '周日026': ('拉齐奥', 1),  # 1:0 主胜
    '周日027': ('皇家社会', 1),  # 3:1 主胜
    '周日028': ('波尔图', 1),  # 3:0 主胜
    '周日029': ('温哥华', 1),  # 6:0 主胜
}
# 0=主胜, 1=客胜, 2=平局

# 预测结果
def get_predicted_result(row):
    if '主胜' in str(row['首选']):
        return 0
    elif '客胜' in str(row['首选']):
        return 1
    else:
        return 2

# 获取最高概率选项
def get_max_prob(row):
    probs = [row['主胜概率'], row['平局概率'], row['客胜概率']]
    return max(probs)

# 计算预测正确性 - 编号格式是 周日001_xxx
results = []
for idx, row in df.iterrows():
    # 提取编号: "周日001_日本女vs菲律宾女主" -> "周日001"
    match_id = row['编号'].split('_')[0]
    pred_result = get_predicted_result(row)
    pred_prob = get_max_prob(row)
    actual_result_tuple = actual_results.get(match_id)
    if actual_result_tuple:
        actual_result = actual_result_tuple[1]
        is_correct = 1 if pred_result == actual_result else 0
        results.append({
            '编号': match_id,
            '预测': row['首选'],
            '预测概率': pred_prob,
            '实际': actual_result,
            '正确': is_correct,
            '盘型': row['盘型']
        })

result_df = pd.DataFrame(results)

print("=" * 60)
print("按置信度(预测概率)分组的准确率分析")
print("=" * 60)

# 分组
bins = [0, 30, 40, 50, 55, 60, 70, 80, 90, 100]
labels = ['0-30%', '30-40%', '40-50%', '50-55%', '55-60%', '60-70%', '70-80%', '80-90%', '90-100%']
result_df['概率区间'] = pd.cut(result_df['预测概率'], bins=bins, labels=labels)

# 统计
grouped = result_df.groupby('概率区间', observed=True).agg({
    '正确': ['sum', 'count']
}).reset_index()
grouped.columns = ['概率区间', '正确数', '总数']
grouped['准确率'] = (grouped['正确数'] / grouped['总数'] * 100).round(1)

print("\n按置信度区间统计:")
print(grouped.to_string(index=False))

# 特别分析55%以下
print("\n" + "=" * 60)
print("重点分析: 置信度 <=55% 的预测")
print("=" * 60)

low_conf = result_df[result_df['预测概率'] <= 55]
high_conf = result_df[result_df['预测概率'] > 55]

low_acc = low_conf['正确'].sum() / len(low_conf) * 100 if len(low_conf) > 0 else 0
high_acc = high_conf['正确'].sum() / len(high_conf) * 100 if len(high_conf) > 0 else 0

print(f"\n置信度 <=55%: {len(low_conf)}场, 正确{low_conf['正确'].sum()}场, 准确率 {low_acc:.1f}%")
print(f"置信度 >55%:  {len(high_conf)}场, 正确{high_conf['正确'].sum()}场, 准确率 {high_acc:.1f}%")

# 详细列出55%以下错误的比赛
print("\n55%以下错误的比赛详情:")
error_low = low_conf[low_conf['正确'] == 0]
for _, row in error_low.iterrows():
    print(f"  {row['编号']}: 预测{row['预测']} ({row['预测概率']:.1f}%) - 实际{'主胜' if row['实际']==0 else '客胜' if row['实际']==1 else '平局'}")

# 验证用户的发现
print("\n" + "=" * 60)
print("验证用户发现: 错误比赛是否都是置信度<=55%")
print("=" * 60)

all_errors = result_df[result_df['正确'] == 0]
errors_le55 = all_errors[all_errors['预测概率'] <= 55]
errors_gt55 = all_errors[all_errors['预测概率'] > 55]

print(f"\n总错误: {len(all_errors)}场")
print(f"置信度<=55%的错误: {len(errors_le55)}场 ({len(errors_le55)/len(all_errors)*100:.1f}%)")
print(f"置信度>55%的错误: {len(errors_gt55)}场 ({len(errors_gt55)/len(all_errors)*100:.1f}%)")

# 详细列出所有错误
print("\n所有错误比赛:")
for _, row in all_errors.iterrows():
    actual_str = '主胜' if row['实际']==0 else '客胜' if row['实际']==1 else '平局'
    print(f"  {row['编号']}: 预测{row['预测']} ({row['预测概率']:.1f}%) vs 实际{actual_str} [{row['盘型']}]")

# 分析55%以上错误的比赛
if len(errors_gt55) > 0:
    print("\n55%以上仍然错误的原因分析:")
    for _, row in errors_gt55.iterrows():
        actual_str = '主胜' if row['实际']==0 else '客胜' if row['实际']==1 else '平局'
        print(f"  {row['编号']}: {row['预测']} ({row['预测概率']:.1f}%) vs 实际{actual_str}")
