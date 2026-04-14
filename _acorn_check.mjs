// Use acorn for precise error reporting
import fs from 'fs';
const src = fs.readFileSync('_test_syntax.js', 'utf-8');

try {
    const {parse} = await import('acorn');
    parse(src, {ecmaVersion:2024, sourceType:'module'});
    console.log('OK');
} catch(e) {
    console.log('\n=== ACORN ERROR ===');
    console.log(e.message);
    console.log('Pos:', e.pos);
    
    // Show context around error position
    const before = Math.max(0, e.pos - 100);
    const after = Math.min(src.length, e.pos + 100);
    console.log('\nContext around error:');
    console.log('...' + src.slice(before, after) + '...');
    console.log('^'.padStart(e.pos - before + 3));
}
