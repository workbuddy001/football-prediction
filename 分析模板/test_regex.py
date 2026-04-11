import re
f='周二001_印度女vs中国台女_源数据.md'
m=re.search(r'([周][\u4e00-\u9fa5]\d+)_([^_]+)vs([^_]+)_', f)
print('匹配结果:', m)
if m:
    print('groups:', m.groups())
