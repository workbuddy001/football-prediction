import pandas as pd
df = pd.read_excel('d:/work/workbuddy/足球预测/3.15_比赛预测汇总.xlsx')
print('Columns:', list(df.columns))
print('Shape:', df.shape)
print(df.head(3))
