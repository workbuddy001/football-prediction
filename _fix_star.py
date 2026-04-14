f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'r', encoding='utf-8')
t = f.read()
f.close()

# Fix: remove stray '*' line that appears after table </tr> and before comment block
lines = t.split('\n')
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Check if this line is a standalone '*'
    if line.strip() == '*' or (line.strip() == '*' and i + 1 < len(lines) and lines[i+1].strip().startswith('*')):
        # Skip this stray * line
        print(f"Removing stray * at line {i+1}: {line[:60]}")
        i += 1
        continue
    new_lines.append(line)
    i += 1

t = '\n'.join(new_lines)
f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'w', encoding='utf-8')
f.write(t)
f.close()
print("Done")
