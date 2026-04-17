# -*- coding: utf-8 -*-
f = 'd:/work/workbuddy/足球预测/static/js/prematch.js'
c = open(f, 'r', encoding='utf-8').read()

# The exact problematic text
old = "h += \\'<td style=\"padding:6px 8px;text-align:right,color:\\'+(drow.coef<1?\\'#4ade80\\'':(drow.coef>1?\\'#ef4444\\'':\\'#94a3b8\\''))+\\';font-family:monospace\">\\\\u00d7\\'+drow.coef+\\'</td>\\';"

if old in c:
    new = "var _cf2 = (drow.coef<1 ? '#4ade80' : (drow.coef>1 ? '#ef4444' : '#94a3b8')); h += \\\"<td style=padding:6px 8px;text-align:right;color:\\\"+_cf2+\\\";font-family:monospace>\\u00d7\\\"+drow.coef+\\\"</td>\\\";"
    c = c.replace(old, new)
    print('FIXED')
else:
    # Use regex to find and replace the whole line
    import re
    # Match from "h += '<td style="padding" to "</td>';"
    pattern = r"h\s*\+=\s*'<td style=\"padding:6px 8px;.*?drow\.coef\+</td>'\s*;"
    m = re.search(pattern, c)
    if m:
        print("Found with regex, replacing...")
        replacement = 'var _cf2 = (drow.coef<1 ? "#4ade80" : (drow.coef>1 ? "#ef4444" : "#94a3b8")); h += "<td style=padding:6px 8px;text-align:right;color:"+_cf2+";font-family:monospace>\\u00d7"+drow.coef+"</td>";'
        c = c[:m.start()] + replacement + c[m.end():]
        print('FIXED via regex')
    else:
        print("Regex also failed")
        # Just show surrounding lines around position 116400
        idx = c.find('\\u00d7')
        if idx > 0:
            print(repr(c[idx-150:idx+50]))

open(f, 'w', encoding='utf-8').write(c)
