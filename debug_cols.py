import pandas as pd
df = pd.read_excel('d:/work/workbuddy/足球预测/3.15_比赛预测汇总.xlsx')
print("列名:", df.columns.tolist())
print("\n第一行:")
print(df.iloc[0])
