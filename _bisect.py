"""Binary search for the exact line causing the await error"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('_test_syntax.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

import subprocess

# We know renderDetail starts at line 266
# Test progressively more code to find where it breaks
start = 266  # renderDetail function start
# end = 820   # after the await line

for end in range(start+5, 825, 5):
    chunk = ''.join(lines[start:end])
    
    # Wrap in async IIFE to make top-level valid
    test_code = '(async () => {\n' + chunk + '\n})();'
    
    with open('_test_chunk.js', 'w', encoding='utf-8') as f:
        f.write(test_code)
    
    result = subprocess.run(
        ['C:\\Program Files\\nodejs\\node.exe', '--check', '_test_chunk.js'],
        capture_output=True, text=True
    )
    
    status = '✅' if result.returncode == 0 else '❌'
    print(f'{status} Lines {start}-{end}: balance_error={result.returncode}')
    if result.returncode != 0 and 'await' in (result.stderr or ''):
        print(f'  >>> FIRST AWAIT ERROR at end={end} <<<')
        # Show last few lines added
        for i in range(end-5, end):
            print(f'     L{i+1}: {lines[i].rstrip()[:100]}')
        break
