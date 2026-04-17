"""Fix backtest script f-string issues"""
with open('_backtest_engine.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace(
    "f\"引擎命中率: {correct}/{total-no_data} = {correct/(total-no_data)*100:.1f}%\" if total-no_data > 0 else \"N/A\"",
    "f\"引擎命中率: {correct}/{valid} = {correct/valid*100:.1f}%\""
)

old_block = '''print(f"总场次:     {total}")
    print(f"有效数据:   {total - no_data}")
    print(f"无数据跳过: {no_data}")
    print(f"解析错误:   {len(errors)}")
    print(f"")
    print(f"引擎命中率:'''

new_block = '''valid = total - no_data
    print(f"总场次:     {total}")
    print(f"有效数据:   {valid}")
    print(f"无数据跳过: {no_data}")
    print(f"解析错误:   {len(errors)}")
    print(f"")
    if valid > 0:
        print(f"引擎命中率:'''

if old_block in code:
    code = code.replace(old_block, new_block)
else:
    # Try to find and fix line by line
    lines = code.split('\n')
    for i, line in enumerate(lines):
        if 'total - no_data' in line and 'valid' not in line:
            if '有效数据' in line:
                lines[i] = line.replace('total - no_data', 'valid')
            elif '引擎命中率' in line:
                lines[i] = line.replace('{total-no_data}', '{valid}').split(' if ')[0]
    # Insert valid definition before first use
    for i, line in enumerate(lines):
        if '总场次' in line:
            lines.insert(i, '    valid = total - no_data')
            break
    code = '\n'.join(lines)

# Also fix similar patterns elsewhere  
import re
code = re.sub(r'\{total-no_data\}', '{valid}', code)

with open('_backtest_engine.py', 'w', encoding='utf-8') as f:
    f.write(code)

# Verify syntax
import ast
ast.parse(code)
print("FIXED OK")
