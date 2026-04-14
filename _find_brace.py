"""Precise brace balance checker - find exactly which line breaks async context"""
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('_test_syntax.js', 'r', encoding='utf-8') as f:
    lines = [l.rstrip() for l in f.readlines()]

# Track brace balance, ignoring strings/templates
balance = 0
func_stack = []  # track function entries

for i, line in enumerate(lines):
    ln = i + 1  # 1-based
    
    # Remove string contents for counting
    clean = re.sub(r"'[^']*'", '', line)
    clean = re.sub(r'"[^"]*"', '', clean)
    # Remove template literal content (keep ${} for braces)
    clean = re.sub(r'[^${}`]*', '', clean.replace('`',''))
    
    opens = clean.count('{')
    closes = clean.count('}')
    
    old_balance = balance
    balance += opens - closes
    
    # Detect function start
    m = re.match(r'\s*(async\s+)?function\s+(\w+)', line)
    if m:
        func_name = m.group(2)
        func_stack.append((ln, func_name))
        print(f"L{ln:4d}: {'async ' if m.group(1) else ''}function {func_name}() {{  [bal={old_balance}->{balance}]")
        continue
    
    # Detect closing of a function-level }
    if closes > opens and balance < len(func_stack):
        if func_stack:
            closed_fn = func_stack.pop()
            print(f"L{ln:4d}: }}  ← closes function '{closed_fn[1]}' (opened L{closed_fn[0]})  [bal={old_balance}->{balance}]")
            continue
    
    # Highlight important areas
    if 790 <= ln <= 830:
        marker = ''
        if 'await' in line:
            marker = ' ⚠️ AWAIT HERE'
        print(f"L{ln:4d}: [{old_balance:3d}->{balance:3d}] {line[:120]}{marker}")
