const fs = require('fs');
const path = require('path');

const jsPath = path.join(__dirname, 'static', 'js', 'prematch.js');
let js = fs.readFileSync(jsPath, 'utf-8');

// Step 1: Find and remove the OLD external function
// It starts after "})();\n\n// Final Recommendation Engine"
const extPattern = /\n\n\/\/[^\n]*Final Recommendation Engine[\s\S]*$/;
const beforeClean = js.length;
js = js.replace(extPattern, '');
if (js.length < beforeClean) {
    console.log(`Removed ${beforeClean - js.length} chars of old external function`);
}

// Step 2: Also remove any DUPLICATE _synthesizeFinalRecommendation calls that might exist
// Keep only one call at the right place
const marker = "html += '</div>'; // 结论区end";
let count = 0;
let pos = js.indexOf(marker);
while (pos !== -1) {
    count++;
    let nextPos = js.indexOf(marker, pos + 1);
    if (nextPos !== -1) {
        // Check if there's a _finalRec assignment before this occurrence
        const before = js.substring(pos + marker.length, Math.min(nextPos, pos + marker.length + 500));
        if (before.includes('_finalRec') || before.includes('_synthesize')) {
            // This might be a duplicate block, remove from this marker to next
            console.log(`Found duplicate section around offset ${pos}, removing...`);
            // Find start of the var _finalRec line
            const recStart = js.lastIndexOf('var _finalRec', nextPos);
            const recEnd = js.indexOf('</div>\n                html += \'</div>\'; // 第三部分end', recStart);
            if (recStart > 0 && recEnd > recStart) {
                js = js.substring(0, recStart) + js.substring(recEnd + '</div>'.length);
            }
            // Re-search
            pos = js.indexOf(marker);
            count = 0;
            continue;
        }
    }
    pos = nextPos;
}
console.log(`Found ${count} occurrences of conclusion area end marker`);

// Step 3: Read clean function code
const funcFile = fs.readFileSync(path.join(__dirname, '_final_rec_func.js'), 'utf-8');
const funcMatch = funcFile.match(/var FINAL_REC_FUNC = `([\\s\\S]*?)`;[\s]*$/);
if (!funcMatch) {
    console.error('ERROR: Cannot extract function code');
    process.exit(1);
}
const newFunc = funcMatch[1];

// Step 4: Insert BEFORE the last occurrence of the marker
const insertIdx = js.lastIndexOf(marker);
if (insertIdx === -1) {
    console.error('ERROR: Cannot find insertion point');
    process.exit(1);
}

js = js.substring(0, insertIdx) + newFunc + js.substring(insertIdx);

fs.writeFileSync(jsPath, js, 'utf-8');

console.log(`Inserted ${newFunc.length} chars of new function code`);

// Step 5: Syntax check via spawn
const { execSync } = require('child_process');
try {
    execSync('node --check "' + jsPath.replace(/\\/g, '/') + '"', { stdio: 'pipe' });
    console.log('✅ SYNTAX OK');
} catch(e) {
    console.error('❌ SYNTAX ERROR:', e.stderr.toString());
    process.exit(1);
}
