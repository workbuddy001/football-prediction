import { execSync } from 'child_process';
import fs from 'fs';

try {
    execSync('node --check _test_syntax.js', { stdio: 'pipe' });
    fs.writeFileSync('_check_out.txt', 'OK');
} catch(e) {
    const stderr = e.stderr?.toString() || '';
    const stdout = e.stdout?.toString() || '';
    fs.writeFileSync('_check_err.txt', 'STDERR:\n' + stderr + '\nSTDOUT:\n' + stdout);
}
