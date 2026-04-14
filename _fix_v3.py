# Simple Python script to fix prematch.js
# 1) Remove old external function (after IIFE closing)
# 2) Insert clean new function INSIDE IIFE

f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'r', encoding='utf-8')
t = f.read()
f.close()

# 1) Remove old external function after "})();"
iife_end = t.rfind('\n})();\n')
if iife_end == -1:
    print("ERROR: Cannot find IIFE end")
    exit(1)

after_iife = t[iife_end + len('\n})();\n'):]
if 'Final Recommendation' in after_iife:
    print(f"Removing {len(after_iife)} chars of old external function...")
    t = t[:iife_end] + '\n})();\n'

# 2) Read the clean function from _final_rec_func.js
f = open('d:/work/workbuddy/足球预测/_final_rec_func.js', 'r', encoding='utf-8')
func_src = f.read()
f.close()

# Extract content between first ` and last `
start = func_src.find('`')
if start == -1:
    print("ERROR: No backtick found in func file")
    exit(1)
end = func_src.rfind('`')
if end <= start:
    print("ERROR: Cannot find closing backtick")
    exit(1)

new_func = func_src[start+1:end]
print(f"Extracted {len(new_func)} chars of clean function code")

# 3) Insert before "html += '</div>'; // 结论区end"
marker = "html += '</div>'; // 结论区end"
idx = t.find(marker)
if idx == -1:
    # Try last occurrence
    idx = t.rfind(marker)
if idx == -1:
    print("ERROR: Cannot find insertion marker")
    exit(1)

print(f"Inserting at offset {idx}")
t = t[:idx] + new_func + t[idx:]

f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'w', encoding='utf-8')
f.write(t)
f.close()

print("File written successfully")
