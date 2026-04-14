// Precise checker: find which exact { opens the problematic scope
import fs from 'fs';
const src = fs.readFileSync('_test_syntax.js', 'utf-8');
const lines = src.split('\n');

// Find renderDetail start
const renderStart = lines.findIndex(l => l.includes('async function renderDetail'));
console.log(`renderDetail at line ${renderStart + 1}`);

// Try wrapping each progressively larger chunk in async IIFE
// Track balance to find the "leak"
for (let end = renderStart + 1; end <= 825; end++) {
    const chunk = lines.slice(renderStart, end).join('\n');
    
    // Count raw { and } ignoring nothing - just raw
    let opens = 0, closes = 0;
    for (const c of chunk) {
        if (c === '{') opens++;
        if (c === '}') closes++;
    }
    
    const net = opens - closes;
    
    // Test syntax
    const wrapped = `(async()=>{${chunk}})();`;
    fs.writeFileSync('_test_tmp.js', wrapped);
    
    const {execSync} = await import('child_process');
    try {
        execSync('node --check _test_tmp.js', {stdio: 'pipe'});
    } catch(e) {
        const err = e.stderr?.toString() || '';
        if (err.includes('await') && err.includes('only valid')) {
            console.log(`\n=== AWAIT ERROR at source line ${end+1} (net balance: ${net}) ===`);
            console.log(`Error: ${err.split('\n').filter(l=>l.trim())[0]}`);
            
            // Show last 10 lines with their individual net contribution
            for (let i = Math.max(renderStart, end-15); i < end; i++) {
                const l = lines[i];
                let o=0,c=0;
                for(const ch of l){if(ch==='{')o++;if(ch==='}')c++;}
                console.log(`  L${i+1}: net=${o-c:+d} (${o}o ${c}c) | ${l.slice(0,100)}`);
            }
            process.exit(1);
        }
    }
}
console.log('No await error found in range');
