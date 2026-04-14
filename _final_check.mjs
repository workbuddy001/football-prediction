import { execSync } from 'child_process';
import fs from 'fs';

const result = execSync('"C:\\Program Files\\nodejs\\node.exe" --check _test_syntax.js', {
    encoding: 'utf-8',
    stdio: ['pipe', 'pipe', 'pipe']
});
fs.writeFileSync('_final_out.txt', result.toString());
console.log('OK:', result.toString().slice(0,200));
