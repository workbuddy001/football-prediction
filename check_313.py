import pandas as pd

df = pd.read_excel('3.13_V3预测.xlsx')
print("列名:", df.columns.tolist())
print("\n数据预览:")
print(df.head(15))
