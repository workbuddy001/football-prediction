// Wrap extracted JS as module to get precise error
import { fileURLToPath } from 'url';
import fs from 'fs';

const src = fs.readFileSync('_test_syntax.js', 'utf-8');
try {
    // Try parsing as module body
    new Function(src);
    console.log('✅ No errors');
} catch(e) {
    console.log('Error:', e.message);
    console.log('Stack:', e.stack);
}
