import fs from 'fs';
const src = fs.readFileSync('_test_syntax.js', 'utf-8');
const lines = src.split('\n');

// More robust parser using state machine
let lastOpen = null;
let stack = []; // stack of {line, col, type}

for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    for (let j = 0; j < line.length; j++) {
        const c = line[j];
        
        if (!stack.length || stack[stack.length-1].type === 'code') {
            // In code context
            if (c === '`') {
                stack.push({line: i+1, col: j, type: 'template', depth: 0});
                lastOpen = {line: i+1, col: j};
            } else if (c === "'") {
                stack.push({type: 'squote'});
            } else if (c === '"') {
                stack.push({type: 'dquote'});
            }
        } else {
            const ctx = stack[stack.length-1];
            
            if (ctx.type === 'template') {
                if (c === '$' && j+1 < line.length && line[j+1] === '{') {
                    // Entering ${} expression
                    stack.push({type: 'expr'});
                } else if (c === '`') {
                    // Check escaped
                    let esc = false, k = j;
                    while (k > 0 && line[k-1] === '\\') { esc = !esc; k--; }
                    if (!esc) {
                        if (stack.length > 1 && stack[stack.length-2].type === 'expr') {
                            // This closes an inner template inside ${}
                            stack.pop(); // pop template
                            stack.pop(); // pop expr  
                        } else {
                            stack.pop(); // pop outer template
                        }
                    }
                } else if (c === '}' && ctx.type === 'expr' && stack.length > 1) {
                    stack.pop(); // close expr
                }
            } else if (ctx.type === 'squote') {
                if (c === "'" && (j===0 || line[j-1] !== '\\')) stack.pop();
            } else if (ctx.type === 'dquote') {
                if (c === '"' && (j===0 || line[j-1] !== '\\')) stack.pop();
            } else if (ctx.type === 'expr') {
                if (c === '`') {
                    stack.push({type: 'inner_template'});
                } else if (c === '}') {
                    // Only close if not inside inner template
                    const prev = stack[stack.length-2];
                    if (!prev || prev.type !== 'inner_template') {
                        stack.pop();
                    }
                } else if (c === "'" && !stack.find(s => s.type === 'squote')) {
                    stack.push({type: 'squote'});
                } else if (c === '"' && !stack.find(s => s.type === 'dquote')) {
                    stack.push({type: 'dquote'});
                }
            } else if (ctx.type === 'inner_template') {
                if (c === '`') {
                    let esc = false, k = j;
                    while (k > 0 && line[k-1] === '\\') { esc = !esc; k--; }
                    if (!esc) stack.pop();
                }
            }
        }
    }
    
    // Debug: print stack size every 50 lines around the error area
    if ((i+1) % 100 === 0 || i < 10 || (2100 <= i+1 && i+1 <= 2120)) {
        console.log(`L${i+1}: stack=[${stack.map(s=>s.type).join(',')}]`);
    }
}

console.log(`\nFinal stack (${stack.length}):`);
for (const s of stack) {
    console.log(`  ${JSON.stringify(s)}`);
}
if (lastOpen) console.log(`\nLast opened: L${lastOpen.line} col${lastOpen.col}`);
