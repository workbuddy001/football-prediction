# -*- coding: utf-8 -*-
f = open(r'd:\work\workbuddy\足球预测\static\js\prematch.js', 'r', encoding='utf-8')
lines = f.readlines()
f.close()

out = open(r'd:\work\workbuddy\足球预测\_lines_out.txt', 'w', encoding='utf-8')
for i in range(688, 755):
    line = lines[i].rstrip('\n')
    out.write(f'{i+1}: {line}\n')
out.close()
print('Done, wrote', (755-688), 'lines')
