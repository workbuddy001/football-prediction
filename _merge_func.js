const fs = require('fs');
const path = require('path');

// Read the clean function code from separate file
const funcCode = fs.readFileSync(path.join(__dirname, '_final_rec_func.js'), 'utf-8');
// Extract just the template literal content (between first ` and last `)
const match = funcCode.match(/var FINAL_REC_FUNC = `(?:[^`]|``)*`;/s);
if (!match) {
    console.error('ERROR: Could not extract function code');
    process.exit(1);
}
const newFunc = match[1];

// Read current prematch.js
let js = fs.readFileSync(path.join(__dirname, 'static', 'js', 'prematch.js'), 'utf-8');

// 1. Remove external function if present (after IIFE closing)
const iifeEnd = js.indexOf('\n})();\n\n');
if (iifeEnd !== -1) {
    const afterIIFE = js.substring(iifeEnd + 6); // after })();
    // Check for Final Recommendation Engine comment
    const extStart = afterIIFE.indexOf('// Final Recommendation Engine');
    if (extStart !== -1) {
        console.log(`Removing external function at offset ${extStart}`);
        // Find end of that function (next empty-ish area or EOF)
        let extEnd = afterIIFE.lastIndexOf('}\n');
        if (extEnd > extStart) {
            js = js.substring(0, iifeEnd + 6) + '\n})();\n';
            console.log('External function removed');
        }
    }
}

// 2. Insert inside IIFE before "html += '</div>'; // 结论区end"
const insertMarker = "html += '</div>'; // 结论区end";
const insertIdx = js.indexOf(insertMarker);
if (insertIdx === -1) {
    console.error('ERROR: Cannot find insertion point');
    process.exit(1);
}

js = js.substring(0, insertIdx) + newFunc + js.substring(insertIdx);

fs.writeFileSync(path.join(__dirname, 'static', 'js', 'prematch.js'), js, 'utf-8');

// Verify syntax
try {
    require('vm').compileFunction(js, [], { filename: 'prematch.js' });
} catch(e) {
    console.error('SYNTAX ERROR:', e.message);
    process.exit(1);
}

console.log('SUCCESS: Function inserted INSIDE IIFE, syntax verified');
