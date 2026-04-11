import re

content = open('d:/work/workbuddy/足球预测/分析模板/3.15/周日014_曼联vs维拉_源数据.md', 'r', encoding='utf-8').read()

# 测试正则
match = re.search(r'主队近况[：:]\s*近10场[，,]\s*(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
print("主队近况匹配:", match)

match = re.search(r'客队近况[：:]\s*近10场[，,]\s*(\d+)胜(\d+)平(\d+)负.*?胜率(\d+)%', content)
print("客队近况匹配:", match)

# 打印相关行
for line in content.split('\n'):
    if '主队近况' in line or '客队近况' in line:
        print(line)
