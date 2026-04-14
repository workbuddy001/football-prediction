import fs from 'fs';
const src = fs.readFileSync('_test_syntax.js', 'utf-8');

// Write as ESM module and try to parse
fs.writeFileSync('_test_esm.mjs', src);

// Use child_process to run node --check and capture output
import { execSync } from 'child_process';
try {
    execSync('node --check _test_esm.mjs', { encoding: 'utf-8', stdio: ['pipe','pipe','pipe'] });
    console.log('OK');
} catch(e) {
    console.log('STDERR:', e.stderr);
    console.log('STDOUT:', e.stdout);
}
