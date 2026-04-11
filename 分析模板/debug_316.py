content = open('3.16/周一001_海尔蒙特vs坎布尔_源数据.md', 'r', encoding='utf-8').read()
import re
home = re.search(r'\| 主队 \|\s*(.+)', content)
print('home:', repr(home.group(1)) if home else 'None')
away = re.search(r'\| 客队 \|\s*(.+)', content)
print('away:', repr(away.group(1)) if away else 'None')
league = re.search(r'\| 赛事 \|\s*(.+)', content)
print('league:', repr(league.group(1)) if league else 'None')
