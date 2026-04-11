import re
filepath = '分析模板/3.14/周六001_中国女vs中国台女_源数据.md'
with open(filepath, 'r', encoding='utf-8') as file:
    content = file.read()

# 提取澳门推荐
macao_match = re.search(r'澳门推荐\s*\|\s*(\S+)', content)
if macao_match:
    print('找到:', macao_match.group(1))
else:
    macao_match = re.search(r'澳门推荐[:：]\s*(.+)', content)
    if macao_match:
        print('找到2:', macao_match.group(1)[:30])
    else:
        print('未找到')
