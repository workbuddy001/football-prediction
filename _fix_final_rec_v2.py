# Write clean version of _synthesizeFinalRecommendation INSIDE IIFE
# Using actual Chinese characters, not unicode escapes

f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'r', encoding='utf-8')
lines = f.readlines()
f.close()

# Find the insertion point: "html += '</div>'; // 结论区end"
insert_line = None
for i, line in enumerate(lines):
    if "html += '</div>'; // 结论区end" in line:
        insert_line = i
        break

if insert_line is None:
    print("ERROR: Cannot find insertion point")
    exit(1)

print(f"Found insertion at line {insert_line + 1}")

# Build the new function code using raw Chinese text
new_func_code = '''
                // ====== 最终结论建议（综合所有维度） ======
                var _finalRec = (function(){
                    var _fp = finalPred;
                    var _bt = cc.basic_tendency;
                    var _mt = mc.tip, _mtt = mc.tip_text;
                    if (!_fp && !_bt) return null;

                    // Case A: Triple resonance TRAP -> reverse recommendation
                    var _isTrap = false;
                    if (typeof _verdict !== 'undefined') {
                        _isTrap = (_verdict.indexOf('\u4E09\u91CD\u5171\u632F') !== -1 || _verdict.indexOf('\u6700\u4F18\u89E3') !== -1);
                    }

                    if (_isTrap) {
                        var _bdir = '', _boddsVal = 999;
                        if (jcHomeOdds > 0 && jcHomeOdds < _boddsVal) { _bdir = 'home'; _boddsVal = jcHomeOdds; }
                        if (jcAwayOdds > 0 && jcAwayOdds < _boddsVal) { _bdir = 'away'; _boddsVal = jcAwayOdds; }
                        if (jcDrawOdds > 0 && jcDrawOdds < _boddsVal) { _bdir = 'draw'; _boddsVal = jcDrawOdds; }

                        var _bnMap = {home: mi.home_team + '\u80DC', draw: '\u5E73\u5C40', away: mi.away_team + '\u80DC'};
                        var _boMap = {home: jcHomeOdds, draw: jcDrawOdds, away: jcAwayOdds};
                        var _othersDirs = ['home','draw','away'].filter(function(d){ return d !== _bdir; });
                        var _hpList = [];
                        for (var oi2 = 0; oi2 < _othersDirs.length; oi2++) {
                            var od2 = _othersDirs[oi2], ov2 = _boMap[od2];
                            if (ov2 >= 2.8) _hpList.push(_bnMap[od2] + '(' + ov2.toFixed(2) + ')');
                        }

                        var _trapRs = [];
                        _trapRs.push('\u2622\uFE0F \u4E09\u91CD\u5171\u632F\u68C0\u6D4B\uFF1A\u6392\u9664\u6CD5 x \u8BA9\u7403\u51FA\u53E3 x \u57FA\u672C\u9762 = \u5B8C\u7F8E\u5171\u632F');
                        _trapRs.push('\u26A0\uFE0F \u5168\u5E02\u573A\u7B79\u7801\u96C6\u4E2D\u5230\"\u663E\u800C\u6613\u89C1\"\u7684\u65B9\u5411 = \u5F88\u597D\u7684\u5F15\u5BFC\u6548\u679C');
                        if (_hpList.length > 0) _trapRs.push('\uD83D\uDCB0 \u6807\u51C6\u76D8\u53CD\u5411\u9AD8\u8D54\u4ED8\uFF1A' + _hpList.join('+'));
                        _trapRs.push('\u2605 \u5E94\u4ED8\u6700\u5C0F\u65B9\u5411 = ' + _bnMap[_bdir] + '(' + _boddsVal.toFixed(2) + ')');

                        return {
                            icon: '\uD83D\uDD25',
                            title: '\u2622\uFE0F \u5EFA\u8BAE\u5173\u6CE8\uFF1A' + _bnMap[_bdir] + '\uFF08\u53CD\u5411\uFF29\uFF29',
                            color: '#f87171', stars: '\u2605\u2605\u2605\u2605\u2605',
                            bg1: '#ef4444', bg2: '#f97316', border: '#ef444450', shadow: '#ef4444',
                            accent: '#f87171', starColor: '#fb923c',
                            reasons: _trapRs,
                            note: '\u53C2\u8003\u58A0\u5C14\u672C\u57CE vs \u60E0\u7075\u987F\uFF082026-04-12\uFF09'
                        };
                    }

                    // Case B: Cross-validation anomaly
                    var _isAnomaly = false;
                    if (typeof _verdict !== 'undefined') {
                        _isAnomaly = (_verdict.indexOf('\u4EA9\u53C9\u9A8C\u8BC1\u5F02\u5E38') !== -1);
                    }

                    if (_isAnomaly) {
                        var _bp2 = '', _bod2 = 999;
                        if (jcHomeOdds > 0 && jcHomeOdds < 1.80) { _bp2 = 'home'; _bod2 = jcHomeOdds; }
                        else if (jcAwayOdds > 0 && jcAwayOdds < 1.80) { _bp2 = 'away'; _bod2 = jcAwayOdds; }
                        else if (jcHomeOdds > 0) { _bp2 = 'home'; _bod2 = jcHomeOdds; }
                        else if (jcAwayOdds > 0) { _bp2 = 'away'; _bod2 = jcAwayOdds; }

                        var _bn2map = {home: mi.home_team + '\u80DC', draw: '\u5E73\u5C40', away: mi.away_team + '\u80DC'};
                        return {
                            icon: '\uD83D\uDEA8',
                            title: '\u26A0\uFE0F \u4EA9\u53C9\u9A8C\u8BC1\u5F02\u5E38\uFF0C\u503C\u5F97\u5173\u6CE8 ' + _bn2map[_bp2],
                            color: '#fb923c', stars: '\u2605\u2605\u2605\u2605',
                            bg1: '#f97316', bg2: '#eab308', border: '#f9731640', shadow: '#f97316',
                            accent: '#fb923c', starColor: '#fbbf24',
                            reasons: [
                                '\uD83D\uDD35 \u8BA9\u7403\u76D8\u5355\u51FA\u53E3 + \u4E2D\u6C34\uFF0C\u4F46\u6807\u51C6\u76D8\u663E\u793A\u5F02\u5E38',
                                _bn2map[_bp2] + '\u6807\u51C6\u76D8=' + _bod2.toFixed(2) + (_bod2 < 1.80 ? '(\u4F4E\u6C34)->\u5E94\u4ED8\u538B\u529B\u6700\u5C0F' : ''),
                                '\uD83D\uDCCB \u5982\u679C\u6392\u9664\u6CD5\u7ED3\u8BBA\u6253\u51FA\uFF0C\u5E94\u4ED8\u538B\u529B\u4F1A\u5F88\u5927'
                            ],
                            note: null
                        };
                    }

                    // Case C: Has exclusion prediction
                    if (_fp) {
                        var pnMap = {home: mi.home_team + '\u80DC', draw: '\u5E73\u5C40', away: mi.away_team + '\u80DC'};
                        var predName = pnMap[_fp] || _fp;
                        var agreeBT = (_fp === _bt || (_bt === 'draw' && _fp));
                        var mcAgrees2 = (_mt && _mt.indexOf(predName) !== -1);

                        var caseCRs = [], caseIcon, caseStars, caseLvl,
                            caseClr, caseStCl, caseBg1, caseBg2, caseBd, caseAc;

                        if (conf >= 5) {
                            caseCRs.push('\u{1F9E0}\u6392\u9664\u6CD5\u81EA\u4FE1\u5EA6\u2605\u2605\u2605\u2605\u2605\uFF1A\u63A8\u8350[' + predName + ']');
                            if (agreeBT) caseCRs.push('\u2714\uFE0F \u57FA\u672C\u9762(' + predName + ')\u4E0E\u6392\u9664\u6CD5\u4E00\u81F4');
                            else if (_bt) caseCRs.push('\u2753 \u57FA\u672C\u9762\u4E0E\u6392\u9664\u6CD5\u5206\u6B67');
                            if (_mtt) caseCRs.push('\uD83D\uDCB0\u6FB3\u95E8' + (mcAgrees2 ? '\u2714\uFE0F' : '\u2753') + _mtt);
                            caseIcon = '\uD83D\uDCAA'; caseStars = '\u2605\u2605\u2605\u2605\u2605';
                            caseLvl = '\u9AD8\u7F6E\u4FE1';
                            caseClr = '#22c55e'; caseStCl = '#4ade80';
                            caseBg1 = '#22c55e'; caseBg2 = '#16a34a';
                            caseBd = '#22c55e40'; caseAc = '#4ade80';
                        } else if (conf >= 4) {
                            caseCRs.push('\u{1F9E0}\u6392\u9664\u6CD5\u81EA\u4FE1\u5EA6\u2605\u2605\u2605\u2605\uFF1A\u503E\u5411[' + predName + ']');
                            if (agreeBT) caseCRs.push('\u2714\uFE0F \u57FA\u672C\u9762\u652F\u6301');
                            if (_mt) caseCRs.push('\uD83D\uDCF6 \u6FB3\u95E8\u63A8\u8350\u4E0E\u6392\u9664\u6CD5' + (mcAgrees2 ? '\u4E00\u81F4' : '\u4E0D\u540C'));
                            caseIcon = '\uD83D\uDEE1'; caseStars = '\u2605\u2605\u2605\u2605';
                            caseLvl = '\u8F83\u4E3A\u786E\u5B9A';
                            caseClr = '#3b82f6'; caseStCl = '#93c5fd';
                            caseBg1 = '#3b82f6'; caseBg2 = '#2563eb';
                            caseBd = '#3b82f640'; caseAc = '#93c5fd';
                        } else if (conf >= 3) {
                            caseCRs.push('\u{1F9E0}\u6392\u9664\u6CD5\u503E\u5411[' + predName + '](\u2605\u2605\u2605)');
                            caseCRs.push('\u26A0\uFE0F \u81EA\u4FE1\u5EA6\u4E2D\u7B49\uFF0C\u5EF6\u8BAE\u7ED3\u5408\u8D54\u7387\u5224\u65AD');
                            if (!agreeBT) caseCRs.push('\u26A0\uFE0F \u57FA\u672C\u9762\u4E0E\u6392\u9664\u6CD5\u4E0D\u4E00\u81F4\uFF0C\u9009\u62E9\u9700\u8C28\u614E');
                            caseIcon = '\uD83D\uDD14'; caseStars = '\u2605\u2605\u2605';
                            caseLvl = '\u6709\u53C2\u8003\u4EF7\u503C';
                            caseClr = '#eab308'; caseStCl = '#facc15';
                            caseBg1 = '#eab308'; caseBg2 = '#ca8a04';
                            caseBd = '#eab30830'; caseAc = '#facc15';
                        } else if (conf > 0) {
                            caseCRs.push('\u{1F9E0}\u6392\u9664\u6CD5\u5F31\u503E\u5411[' + predName + '](\u2605\u2605)');
                            caseCRs.push('\uD83D\uDC40 \u4FE1\u53F7\u4E0D\u5F3A\u70C8\uFF0C\u4EC5\u4F5C\u53C2\u8003');
                            caseIcon = '\uD83D\uDD33'; caseStars = '\u2605\u2605';
                            caseLvl = '\u4F4E\u7F6E\u4FE1';
                            caseClr = '#f97316'; caseStCl = '#fb923c';
                            caseBg1 = '#f97316'; caseBg2 = '#ea580c';
                            caseBd = '#f9731620'; caseAc = '#fb923c';
                        } else {
                            return null;
                        }

                        // Handicap check using internal function
                        if (hcH > 0) {
                            var hwi2 = _classifyWaterLevel(hcH);
                            if (hwi2.level !== '-' && hwi2.color !== C.textDim) {
                                var tierStr = hwi2.level || '';
                                if (tierStr.indexOf('\u8D85\u4F4E') === 0 || tierStr.indexOf('\u4F4E\u6C34') === 0) {
                                    caseCRs.push('\uD83D\uDCB0 \u8BA9\u7403\u76D8\u5BF9\u5E94\u65B9\u5411=' + hcH.toFixed(2) + '(' + tierStr + ')->\u5E94\u4ED8\u5408\u7406');
                                }
                            }
                        }

                        return {
                            icon: caseIcon,
                            title: caseLvl + '\uFF1A' + predName,
                            color: caseClr, stars: caseStars,
                            bg1: caseBg1, bg2: caseBg2, border: caseBd, shadow: caseBg1,
                            accent: caseAc, starColor: caseStCl,
                            reasons: caseCRs, note: null
                        };
                    }

                    // Case D: No exclusion -> basic tendency driven
                    if (_bt) {
                        var bn3map = {home: mi.home_team + '\u80DC', draw: '\u5E38\u5C40', away: mi.away_team + '\u80DC'};
                        var bo3map = {home: jcHomeOdds, draw: jcDrawOdds, away: jcAwayOdds};

                        var mcDir2 = '';
                        if (_mtt) {
                            if (_mtt.indexOf(mi.home_team) !== -1) mcDir2 = 'home';
                            else if (_mtt.indexOf(mi.away_team) !== -1) mcDir2 = 'away';
                            else if (_mtt.indexOf('\u548C') !== -1 || _mtt.indexOf('\u5E73') !== -1) mcDir2 = 'draw';
                        }
                        var mcAgree3 = (mcDir2 && mcDir2 === _bt);

                        var d4rs = [], recDir2 = _bt, recOdds2 = bo3map[_bt];
                        d4rs.push('\u57FA\u672C\u9762\u660E\u663E\u503E\u5411 [' + bn3map[_bt] + ']');

                        if (mcDir2) {
                            if (mcAgree3) d4rs.push('\uD83D\uDCB0 \u6FB3\u95E8\u5FC3\u6C34\u540C\u5411\u63A8\u8350[' + bn3map[mcDir2] + '] \u2705');
                            else d4rs.push('\uD83D\uDCB0 \u6FB3\u95E8\u5FC3\u6C43\u63A8[' + bn3map[mcDir2 + ']\uFF0C\u4E0E\u57FA\u672C\u9762\u5206\u6B67');
                        }

                        // Std odds lowest check
                        var lodDir = '', lodVal = 99;
                        var dirsToCheck = ['home', 'draw', 'away'];
                        for (var di3 = 0; di3 < dirsToCheck.length; di3++) {
                            var dd = dirsToCheck[di3];
                            if (bo3map[dd] > 0 && bo3map[dd] < lodVal) { lodVal = bo3map[dd]; lodDir = dd; }
                        }
                        if (lodDir === _bt) {
                            d4rs.push('\u2605 ' + bn3map[_bt] + '\u8D54\u7387=' + recOdds2.toFixed(2) + ' = \u6807\u51C6\u76D8\u6700\u4F4E -> \u5E94\u4ED8\u538B\u529B\u6700\u5C0F');
                        } else if (lodDir) {
                            d4rs.push('\u26A0\uFE0F \u6807\u51C6\u76D8\u6700\u4F4E\u662F' + bn3map[lodDir] + '(' + lodVal.toFixed(2) + ')\uFF0C\u4E0E\u57FA\u672C\u9762\u503E\u5411\u4E0D\u540C');
                        }

                        // Handicap cross-check
                        if (hcH > 0) {
                            var hwinfo3 = _classifyWaterLevel(hcH);
                            if (hwinfo3.level !== '-') {
                                var tierS3 = hwinfo3.level || '';
                                var isLowWater = (tierS3.indexOf('\u8D85\u4F4E') === 0 || tierS3.indexOf('\u4F4E\u6C34') === 0);
                                var isHighWater = (tierS3.indexOf('\u9AD8\u6C34') === 0 || tierS3.indexOf('\u8D85\u9AD8') === 0);
                                if (isLowWater) {
                                    d4rs.push('\uD83D\uDCB6 \u8BA9\u7403\u76D8\u4E3B\u8FDB\u65B9\u5411\u5728\u4F4E/\u8D85\u4F4E\u6C34\u533A\uFF0C\u5E94\u4ED8\u5408\u7406');
                                } else if (isHighWater) {
                                    d4rs.push('\uD83D\uDEDB \u8BA9\u7403\u76D8\u4E3B\u8FDB\u65B9\u5411\u5728\u9AD8/\u8D85\u9AD8\u6C34\uFF0C\u5B58\u5728\u7591\u597F');
                                }
                            }
                        }

                        var strongFlag = (mcAgree3 && lodDir === _bt);
                        var weakFlag = (mcDir2 && !mcAgree3) || (lodDir && lodDir !== _bt);

                        return {
                            icon: strongFlag ? '\uD83D\uDCAA' : '\uD83D\uDCCB',
                            title: (strongFlag ? '\u2705 ' : (weakFlag ? '\u26A0\uFE0F ' : '')) + '\u7EFC\u5408\u5224\u5B9A\uFF1A' + bn3map[recDir2],
                            color: strongFlag ? '#22c55e' : (weakFlag ? '#f97316' : '#3b82f6'),
                            stars: strongFlag ? '\u2605\u2605\u2605\u2605' : '\u2605\u2605\u2605',
                            bg1: strongFlag ? '#22c55e' : (weakFlag ? '#f97316' : '#3b82f6'),
                            bg2: strongFlag ? '#16a34a' : (weakFlag ? '#ea580c' : '#2563eb'),
                            border: strongFlag ? '#22c55e40' : (weakFlag ? '#f9731630' : '#3b82f640'),
                            shadow: strongFlag ? '#22c55e' : (weakFlag ? '#f97316' : '#3b82f6'),
                            accent: strongFlag ? '#4ade80' : (weakFlag ? '#fb923c' : '#93c5fd'),
                            starColor: strongFlag ? '#4ade80' : (weakFlag ? '#fb923c' : '#93c5fd'),
                            reasons: d4rs,
                            note: weakFlag ? '\u26A0\uFE0F \u4FE1\u53F7\u5B58\u5728\u5206\u6B67\uFF0C\u5EFA\u8BAE\u964D\u7EA7\u6295\u5165\u6216\u89C2\u671B' : null
                        };
                    }

                    return null;
                })();

'''

# Also remove old external function if still present
# Check if there's still an external function after the IIFE closing
ext_marker = "// Final Recommendation Engine"
has_external = False
for i, line in enumerate(lines):
    if ext_marker in line and i > insert_line:
        has_external = True
        # Find end: next empty line after closing brace
        # Remove from this line onwards until we hit the right pattern
        print(f"Found external function at line {i+1}, removing...")
        lines = lines[:i]
        break

# Insert the new function before the conclusion area end
lines.insert(insert_line, new_func_code)

with open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("SUCCESS: Final recommendation function inserted INSIDE IIFE")
if has_external:
    print("Also removed old external function")
