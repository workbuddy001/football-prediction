f=open('d:/work/workbuddy/足球预测/static/js/prematch.js','r',encoding='utf-8')
t=f.read();f.close()

depth=0
lines=t.split('\n')
for lineno in range(len(lines)):
    line=lines[lineno]
    for ch in line:
        if ch=='{':depth+=1
        elif ch=='}':depth-=1
    if depth>5 and lineno>400:
        # Write to file instead of print (avoid encoding issues)
        out=open('d:/work/workbuddy/足球预测/_brace_debug.txt','a',encoding='utf-8')
        out.write(f'Line {lineno+1}: depth={depth}\n  {line.strip()[:100]}\n')
        out.close()
        if lineno>715:break

# Find max depth
depth2=0;md=0;mp=0
for i,ch in enumerate(t):
    if ch=='{':depth2+=1
    elif ch=='}':depth2-=1
    if depth2>md:md=depth2;mp=i
out=open('d:/work/workbuddy/足球预测/_brace_debug.txt','a',encoding='utf-8')
out.write(f'\nMax depth={md} at char {mp} line {t[:mp].count(chr(10))+1}')
out.close()
print('Done, see _brace_debug.txt')
