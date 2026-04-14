import fs from 'fs';
const src = fs.readFileSync('_test_syntax.js', 'utf-8');
const lines = src.split('\n');

let inStr = false, strType = '', depth = 0;

for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    for (let j = 0; j < line.length; j++) {
        const c = line[j];
        
        if (c === '`' && !inStr) {
            inStr = true;
            strType = 'template';
            console.log(`OPEN template at L${i+1} col${j}: ${line.trim().slice(0,80)}`);
        } else if (c === "'" && !inStr) {
            inStr = true; strType = 'squote';
        } else if (c === '"' && !inStr) {
            inStr = true; strType = 'dquote';
        } else if ((c === "'" && strType === 'squote') || (c === '"' && strType === 'dquote')) {
            let esc = false, k = j;
            while (k > 0 && line[k-1] === '\\') { esc = !esc; k--; }
            if (!esc) { inStr = false; strType = ''; }
        } else if (c === '`' && strType === 'template') {
            let esc = false, k = j;
            while (k > 0 && line[k-1] === '\\') { esc = !esc; k--; }
            if (!esc && depth === 0) {
                inStr = false;
                console.log(`CLOSE template at L${i+1} col${j}: ${line.trim().slice(0,80)}`);
            } else if (!esc) {
                depth--;
            }
        } else if (c === '{' && inStr && strType === 'template') {
            // check for ${
            if (j > 0 && line[j-1] === '$') depth++;
        }
    }
}

if (inStr) console.log(`\n!!! STILL IN ${strType} AT END OF FILE (${lines.length} lines) !!!`);
