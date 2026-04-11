import subprocess, sys
result = subprocess.run([sys.executable, 'd:\\work\\workbuddy\\足球预测\\分析模板\\fetch_full.py'],
    capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
print("STDOUT:", result.stdout[:3000])
print("STDERR:", result.stderr[:3000])
print("EXIT:", result.returncode)
