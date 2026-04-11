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

# 实际比赛结果
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

# 计算预测正确性
results = []
for idx, row in df.iterrows():
    match_id = row['编号'][:4]
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

print("result_df列名:", result_df.columns.tolist())
print(result_df.head())
