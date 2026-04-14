# -*- coding: utf-8 -*-
"""
重写prematch.js：删除第890行开始的坏重复IIFE，从888行继续正确完成Step 2/3/4+最终结论
"""
import re

with open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# 找到坏代码起始位置：line 890 (0-indexed=889) 的 /** 注释
bad_start = None
for i in range(880, min(900, len(lines))):
    if '/**' in lines[i] and i >= 888:
        bad_start = i
        print(f"Bad code starts at line {i+1}: {lines[i][:60].strip()}")
        break

if bad_start is None:
    print("ERROR: Cannot find bad code start!")
    exit(1)

# 保留 0 到 bad_start-1 行（即第1到889行）
good_lines = lines[:bad_start]
print(f"Keeping {len(good_lines)} good lines (1-{bad_start})")

# 新的续写代码（接在第889行 html += '<td>方向</td><td>赔率</td><td>水位档</td><td>庄家意图</td></tr>'; 之后）
new_code = r'''

                    // --- 让球盘六档水位分类 ---
                    function _hcClassify(o) {
                        if (!o || o <= 0) return {tier:0, level:'-', intent:'无数据', color:C.textDim};
                        if (o > 4.5) return {tier:6, level:'超高水', intent:'阻 拉高让你不敢买', color:'#ef4444'};
                        if (o > 3.5) return {tier:5, level:'高水', intent:'诱 高倍勾你博', color:'#f97316'};
                        if (o > 2.8) return {tier:4, level:'中高水',意图:'分 分流筹码', color:'#eab308'};
                        if (o > 2.0) return {tier:3, level:'中低水', intent:'引 合理区间引导', color:'#22c55e'};
                        if (o > 1.5) return {tier:2, level:'低水', intent:'守 低赔实盘防守', color:'#3b82f6'};
                        return {tier:1, level:'超低水', intent:'确 大概率方向', color:'#06b6d4'};
                    }

                    var hcDirs = [
                        {name: '让球后主胜', odds: hcH, color: C.home},
                        {name: '让球后平', odds: hcD, color: C.draw},
                        {name: '让球后客胜', odds: hcA, color: C.away}
                    ];
                    for (var hi = 0; hi < hcDirs.length; hi++) {
                        var hd = hcDirs[hi];
                        var hw = _hcClassify(hd.odds);
                        html += '<tr style="border-bottom:1px solid ' + C.border + '20">';
                        html += '<td style="padding:5px;color:' + hd.color + ';font-weight:bold">' + hd.name + '</td>';
                        html += '<td style="padding:5px;color:' + C.text + ';font-weight:bold;font-size:13px">' + (hd.odds ? hd.odds.toFixed(2) : '-') + '</td>';
                        html += '<td style="padding:5px;color:' + hw.color + ';font-weight:bold">' + hw.level + '</td>';
                        html += '<td style="padding:5px;color:' + C.textDim + '">' + hw.intent + '</td>';
                        html += '</tr>';
                    }
                    html += '</table>';

                    // 让球盘深度解读
                    var hcInterpret = '';
                    // 出口结构判断
                    var lowTier = 7, midCount = 0, highTier = 0;
                    var tierH = _hcClassify(hcH).tier, tierD = _hcClassify(hcD).tier, tierA = _hcClassify(hcA).tier;
                    var lowDirs = [];
                    if (tierH <= 2) { lowDirs.push('主胜(' + hcH.toFixed(2) + ')'); lowTier = Math.min(lowTier, tierH); }
                    if (tierD <= 2) { lowDirs.push('平(' + hcD.toFixed(2) + ')'); lowTier = Math.min(lowTier, tierD); }
                    if (tierA <= 2) { lowDirs.push('客胜(' + hcA.toFixed(2) + ')'); lowTier = Math.min(lowTier, tierA); }
                    if (tierH === 3 || tierH === 4) midCount++;
                    if (tierD === 3 || tierD === 4) midCount++;
                    if (tierA === 3 || tierA === 4) midCount++;
                    if (tierH >= 5) highTier++;
                    if (tierD >= 5) highTier++;
                    if (tierA >= 5) highTier++;

                    var exitType = '', exitDir = '';
                    if (lowDirs.length === 1 && highTier >= 1) {
                        exitType = 'single'; exitDir = lowDirs[0];   // 单出口
                    } else if (lowDirs.length >= 2) {
                        exitType = 'double';                          // 双出口
                    } else if (midCount >= 2) {
                        exitType = 'scatter';                         // 分散
                    } else {
                        exitType = 'blocked';                         // 封锁
                    }

                    // 构建深度解读文本
                    var interpParts = [];
                    if (hcH > 0) interpParts.push('\u8BA9\u7403\u540E\u4E3B\u80DC' + hcH.toFixed(2) + '(' + _hcClassify(hcH).level + '):' + (tierH>=5?'\u8D85\u9AD8\u6C34=\u963B\u76D8':(tierH>=3?'\u9AD8\u6C34=\u8BF1\u5BFC\u533A':'\u5728\u613F\u610F\u4E70\u533A\u95F4') + (tierH<=2?'\uFF0C\u6B63\u5E38\u5F15\u5BFC':'')));
                    if (hcD > 0) interpParts.push('\u8BA9\u7403\u540E\u5E73' + hcD.toFixed(2) + '(' + _hcClassify(hcD).level + '):' + (tierD>=5?'\u8D85\u9AD8\u6C34=\u963B\u76D8\uFF0C\u5E73\u5C40\u88AB\u52D1\u9000':(tierD>=3?'\u9AD8\u6C34/\u4E2D\u5E9A':'\u5728\u5408\u7406\u533A\u95F4')));
                    if (hcA > 0) interpParts.push('\u8BA9\u7403\u540E\u5BA2\u80DC' + hcA.toFixed(2) + '(' + _hcClassify(hcA).level + '):' + (tierA>=5?'\u8D85\u9AD8\u6C34=\u963B\uFF0C\u53D7\u8BA9\u65B9\u96BEFFED\u76D8':(tierA>=3?'\u4E2D\u5E9A/\u9AD8\u6C34':'\u5728\u613F\u610F\u4E70\u533A\u95F4\uFF0C\u88AB\u770B\u597D')));

                    hcInterpret = interpParts.join('<br>');

                    // 出口结构标注
                    var exitLabel = '';
                    if (exitType === 'single') {
                        exitLabel = '<b>\uD83E\uDEAA <span style="color:#f97316">\u51FA\u53E3\u7ED3\u6784\uFF1A\u5355\u51FA\u53E3</span></b> \u26A0\uFE0F \u7B79\u7801\u88AB\u8FEB\u96C6\u4E2D\u5230 ' + esc(exitDir);
                    } else if (exitType === 'double') {
                        exitLabel = '<b>\uD83E\uDEAA <span style="color:#22c55e">\u51FA\u53E3\u7ED3\u6784\uFF1A\u53CC\u51FA\u53E3</span></b> \u2705 \u7B79\u7801\u5206\u6D41\uFF0C\u65E0\u663E\u800C\u6613\u89C1\u7684\u5F15\u5BFC';
                    } else if (exitType === 'scatter') {
                        exitLabel = '<b>\uD83E\uDEAA <span style="color:#eab308">\u51FA\u53E3\u7ED3\u6784\uFF1A\u5206\u6563</span></b> \u5404\u65B9\u5411\u5747\u5728\u4E2D\u5E9A\u533A\uFF0C\u786E\u5B9A\u6027\u4F4E';
                    } else {
                        exitLabel = '<b>\uD83E\uDEAA <span style="color:#94a3b8">\u51FA\u53E3\u7ED3\u6784\uFF1A\u5C01\u9501</span></b> \u5168\u65B9\u5411\u9AD8\u6C34/\u8D85\u9AD8\u6C34\uFF0C\u73A9\u5BB6\u96BE\u4E0B\u624B';
                    }

                    html += '<div style="background:#17255430;border-radius:6px;padding:8px 10px;margin-bottom:10px;border-left:3px solid #60a5fa">';
                    html += '<span style="font-size:11px;color:#93c5fd;font-weight:600">⚖️ 让球盘深度解读：</span>';
                    html += '<span style="font-size:11.5px;color:' + C.text + '">' + hcInterpret + '</span>';
                    html += '<div style="margin-top:6px">' + exitLabel + '</div>';
                    html += '</div>';

                    // --- Step 3: 诱导/实盘防守检测（交叉验证） ---
                    var _refPred = finalPred || cc.basic_tendency || '';
                    var _hcValidCount = (hcH > 0 ? 1 : 0) + (hcD > 0 ? 1 : 0) + (hcA > 0 ? 1 : 0);

                    html += '<div style="margin-bottom:6px"><span style="font-size:11.5px;color:#93c5fd;font-weight:600">③ 诱导 / 实盘防守检测（交叉验证）</span></div>';

                    if (_hcValidCount >= 2 && _refPred) {
                        // 映射参考方向到让球盘对应方向
                        var _jcMap = {'home': {odds: hcH, name: '\u8BA9\u7403\u540E\u4E3B\u80DC(\u8D62\u76D8)', dirCode: 'home'},
                                      'draw': {odds: hcD, name: '\u8BA9\u7403\u540E\u5E73', dirCode: 'draw'},
                                      'away': {odds: hcA, name: '\u8BA9\u7403\u540E\u5BA2\u80DC(\u8D67\u76D8)', dirCode: 'away'}};
                        var _jcm = _jcMap[_refPred] || _jcMap['away'];
                        var _jco = _jcm.odds;
                        var _jcn = _jcm.name;
                        var _jcw = _hcClassify(_jco);

                        // 标准盘数据
                        var _stdHome = jcHomeOdds, _stdDraw = jcDrawOdds, _stdAway = jcAwayOdds;
                        var _predStdOdds = (_refPred === 'home' ? _stdHome : (_refPred === 'draw' ? _stdDraw : _stdAway));
                        var _predName = {home: mi.home + '\u80DC', draw: '\u5E73\u5C40', away: mi.away + '\u80DC'}[_refPred] || _refPred;
                        var _antiName = (_refPred === 'home' ? mi.away + '\u80DC' : (_refPred === 'draw' ? '\u5E73\u5C40' : mi.home + '\u80DC'));
                        var _antiStdOdds = (_refPred === 'home' ? _stdAway : (_refPred === 'draw' ? _stdHome : _stdHome));

                        html += '<div style="background:#1a1a2e35;border-radius:8px;padding:10px 12px;margin-bottom:10px;border:1px solid #33415540">';

                        // 判断逻辑
                        var _isTrap = false, _isAnomaly = false, _verdicts = [];

                        // 条件1：单出口 + 中水/低水
                        if (exitType === 'single' && _jcw.tier <= 3) {
                            _verdicts.push({type: 'warn', text: '\u26A0\uFE0F \u5355\u51FA\u53E3+\u4E2D\u4F4E\u6C34\uFF0C\u5F15\u5BFC\u7591\u4F1F'});
                            // 标准盘检验
                            if (_predStdOdds > 2.8) {
                                _verdicts.push({type: 'danger', text: '\uD83D\uDCB0 \u9884\u6D4B[' + _predName + ']\u6807\u51C6\u76D8=' + _predStdOdds.toFixed(2) + '(\u9AD8\u6C34)\u2192 \u5E94\u4ED8\u538B\u529B\u5927'});
                                _isAnomaly = true;
                            }
                            if (_antiStdOdds < 1.80) {
                                _verdicts.push({type: 'info', text: '\u2605 \u53CD\u5411[' + _antiName + ']\u6807\u51C6\u76D8=' + _antiStdOdds.toFixed(2) + '(\u4F4E\u6C34)\u2192 \u5E94\u4ED8\u538B\u529B\u6700\u5C0F'});
                                _isAnomaly = true;
                            }
                        }

                        // 条件2：矛盾信号（排除方向在诱/阻区间）
                        if (_jcw.tier >= 4) {
                            _verdicts.push({type: 'warn', text: '\u26A0\uFE0F \u77DB\u76FE\u4FE1\u53F7\uFF01\u6392\u9664\u65B9\u5418\u5728\u8BF1/\u963B\u533A\u95F4'});
                        }

                        // 基本面共振检测
                        var bt = cc.basic_tendency || '';
                        if (bt && bt === _refPred && exitType === 'single') {
                            _verdicts.push({type: 'danger', text: '+\u57FA\u672C\u9762\u5171\u632F\uFF0C\u8BF7\u76D8\u5ACC\u7591\u5347\u7EA7'});
                            _isTrap = true;
                        }

                        // 三重共振最终判定
                        var _crossVerdict = '';
                        if (_isTrap && _isAnomaly) {
                            _crossVerdict = '\uD83D\uDD25 \u4E09\u91CD\u5171\u632F\u9677\u9631\uFF01\u5EFA\u8BAE\u5173\u6CE8\u53CD\u5411:[' + _antiName + ']';
                        } else if (_isAnomaly) {
                            _crossVerdict = '\uD83DDAAD \u4EA4\u53C9\u9A8C\u8BC1\u5F02\u5E38\uFF0C\u503C\u5F97\u5173\u6CE8\u53CD\u5411';
                        } else if (_isTrap) {
                            _crossVerdict = '\u26A0\uFE0F \u5355\u51FA\u53E3\u8BF7\u76D8\u5ACC\u7591\uFF0C\u7EC3\u5408\u5224\u65AD';
                        } else if (_verdicts.length > 0) {
                            _crossVerdict = '\uD83D\uDEE1 \u5B58\u5728\u5F15\u5BFC\u7591\u4F1F\uFF0C\u9700\u7ED3\u5408\u8D54\u7387\u5224\u65AD';
                        } else {
                            _crossVerdict = '\u2705 \u8BAD\u53F7\u6B63\u5E38\uFF0C\u65E0\u660E\u663E\u5F15\u5BFC';
                        }

                        // 输出各条判断
                        for (var vi = 0; vi < _verdicts.length; vi++) {
                            var v = _verdicts[vi];
                            var vc = v.type === 'danger' ? '#ef4444' : (v.type === 'warn' ? '#f97316' : '#60a5fa');
                            html += '<div style="padding:4px 0;color:' + vc + ';font-size:11.5px;font-weight:500">' + v.text + '</div>';
                        }

                        // 参考方向信息
                        html += '<div style="margin-top:6px;padding-top:6px;border-top:1px solid ' + C.border + '40;font-size:11.5px;color:' + C.textDim + '">';
                        html += '\uD83E\uDD1D \u53C2\u8003\u65B9\u5411 ' + esc(_refPred.toUpperCase()) + ' \u2192 ' + esc(_jcn) + '=' + (_jco > 0 ? _jco.toFixed(2) : '?') + '(' + _jcw.level + ')';
                        html += '</div>';

                        // 交叉验证面板
                        if (_stdHome > 0 || _stdAway > 0) {
                            html += '<div style="margin-top:6px;background:#0f172a60;border-radius:6px;padding:8px 10px;border-left:3px solid ' + (_isAnalogy ? '#ef4444' : '#60a5fa') + '">';
                            html += '<div style="font-size:11px;color:#93c5fd;font-weight:600;margin-bottom:4px">\uD83D\uDD0E \u4EA4\u53C9\u9A8C\u8BC1\uFF1A</div>';
                            html += '<div style="font-size:11.5px;color:' + C.text + '">';
                            html += '\u6807\u51C6\u76D8' + esc(_predName) + '=';
                            if (_predStdOdds > 0) {
                                var pc = _predStdOdds < 1.80 ? '#06b6d4' : (_predStdOdds < 2.45 ? '#22c55e' : (_predStdOdds < 2.8 ? '#eab308' : '#ef4444'));
                                html += '<b style="color:' + pc + '">' + _predStdOdds.toFixed(2) + '</b>';
                            } else {
                                html += '<b style="color:' + C.textDim + '">?</b>';
                            }
                            html += '<br>';
                            // 基本面共振
                            if (bt) {
                                var btAgree = (bt === _refPred);
                                html += '\u57FA\u672C\u9762\u503E\u5411\u4E0E\u9884\u6D4B' + (btAgree ? '\u4E00\u81F4\u2192\u7B79\u7801\u66F4\u96C6\u4E2D' : '\u5206\u6B67\u2192\u964D\u4F4E\u8BF7\u76D8\u5ACC\u7591');
                            }
                            html += '</div></div>';
                        }

                        // 最终交叉结论
                        html += '<div style="margin-top:6px;padding:6px 10px;border-radius:6px;background:' + (_isTrap ? '#450a0a30' : (_isAnomaly ? '#42200625' : '#064e2020')) + ';border-left:3px solid ' + (_isTrap ? C.bad : (_isAnomaly ? C.tip : C.good)) + '">';
                        html += '<span style="font-size:12px;font-weight:bold;color:' + (_isTrap ? C.bad : (_isAnomaly ? C.tip : C.good)) + '">' + _crossVerdict + '</span>';
                        html += '</div>';

                        html += '</div>'; // Step 3 container end
                    } else if (_hcValidCount >= 2 && !_refPred) {
                        html += '<div style="padding:6px 10px;background:#17255425;border-radius:6px;color:' + C.textDim + ';font-size:11.5px">';
                        html += '\uD83D\uDC40 \u6709\u8BA9\u7403\u76D8\u6570\u636E\u4F46\u65E0\u6392\u9664\u6CD5/\u57FA\u672C\u9762\u7ED3\u8BBA\uFF0C\u65E0\u6CD5\u8fdb\u884C\u4EA4\u53C9\u9A8C\u8BC1';
                        html += '</div>';
                    } else {
                        html += '<div style="padding:6px 10px;color:' + C.textDim + ';font-size:11.5px">';
                        html += '\uD83D\uDC64 \u65E0\u8BA9\u7403\u76D8\u6570\u636E\uFF0C\u8DF3\u8FC7\u4EA4\u53C9\u9A8C\u8BC1';
                        html += '</div>';
                    }

                    // --- Step 4: 综合判定 ---
                    html += '<div style="margin-bottom:6px"><span style="font-size:11.5px;color:#93c5fd;font-weight:600">③ 综合判定</span></div>';
                    html += '<div style="background:#0f172a45;border-radius:8px;padding:10px 12px;margin-bottom:10px;border-left:3px solid ' + vs.border + '">';

                    // 基本面行
                    var btIcon = '\uD83D\uDCCB', btColor = C.text;
                    if (bt === 'home') { btIcon = '\uD83C\uDFE0'; btColor = C.home; }
                    else if (bt === 'draw') { btIcon = '\uD83D\uDCCD'; btColor = C.draw; }
                    else if (bt === 'away') { btIcon = '\u2708\uFE0F'; btColor = C.away; }
                    var btLabel = bt ? ({home: mi.home + '\u80DC', draw: '\u5E73\u5C40', away: mi.away + '\u80DC'}[bt]) : '\u5747\u8861';

                    html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:4px 0;border-bottom:1px solid ' + C.border + '30">';
                    html += '<span style="font-size:11.5px;color:' + C.textDim + '">\u57FA\u672C\u9762:</span>';
                    html += '<span style="font-size:12px;color:' + btColor + ';font-weight:bold">' + btIcon + ' ' + esc(btLabel);
                    // 近况差
                    if (cc.form_diff !== undefined && cc.form_diff !== null) {
                        var fd = parseFloat(cc.form_diff);
                        var fdStr = fd >= 0 ? '+' + fd : String(fd);
                        var fdColor = fd >= 8 ? C.good : (fd <= -8 ? C.bad : C.textDim);
                        html += ' <span style="color:' + fdColor + ';font-size:11px">(' + fdStr + ')</span>';
                    }
                    html += '</span></div>';

                    // 澳门心水行
                    var mcRecText = mc.tip_text || '';
                    var mcHasRec = mc.tip && mc.tip.indexOf('\u65E0') === -1;
                    html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:4px 0;border-bottom:1px solid ' + C.border + '30">';
                    html += '<span style="font-size:11.5px;color:' + C.textDim + '">\uD83D\uDCB0 \u6FB3\u95E8:</span>';
                    if (mcHasRec && mcRecText) {
                        html += '<span style="font-size:11.5px;color:' + C.tip + '">\u6FB3\u95E8\u63A8\u8350\u300C' + esc(mcRecText.substring(0, 20)) + (mcRecText.length > 20 ? '...' : '') + '\u300D\u2192 ';
                        // 心水与基本面对比
                        if (bt) {
                            var mcInBT = mcRecText.indexOf(btLabel) !== -1 ||
                                        (bt === 'draw' && (mcRecText.indexOf('\u548C') !== -1 || mcRecText.indexOf('\u5E73') !== -1));
                            if (mcInBT) {
                                html += '<span style="color:' + C.good + '">\u5E73\u5C40</span> \u2705';
                            } else {
                                html += '<span style="color:' + C.textDim + '">\u672C\u671F\u65E0\u660E\u786E\u7684\u6FB3\u95E8\u5FC3\u6C34\u63A8\u8350</span>';
                            }
                        } else {
                            html += '<span style="color:' + C.text + '">\u65E0\u660E\u786E\u65B9\u5411</span>';
                        }
                    } else {
                        html += '<span style="font-size:11.5px;color:' + C.textDim + '">\u672C\u671F\u65E0\u660E\u786E\u7684\u6FB3\u95E8\u5FC3\u6C34\u63A8\u8350</span>';
                    }
                    html += '</div></div>';

                    // 排除法行
                    html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:4px 0">';
                    html += '<span style="font-size:11.5px;color:' + C.textDim + '">\uD83E\uDD1D \u6392\u9664:</span>';
                    if (finalPred) {
                        var fpName = {home: mi.home + '\u80DC', draw: '\u5E73\u5C40', away: mi.away + '\u80DC'}[finalPred] || finalPred;
                        var stars = '\u2605'.repeat(Math.max(1, Math.min(5, conf || 0)));
                        html += '<span style="font-size:12px;color:' + C.alignGood + ';font-weight:bold">' + esc(fpName) + ' ' + stars + '</span>';
                    } else if (excList.length > 0) {
                        var excNames = excList.map(function(ex){ return {home:'\u4E3B\u80DC',draw:'\u5E73\u5C40',away:'\u5BA2\u80DC'}[ex] || ex; }).join(',');
                        html += '<span style="font-size:11.5px;color:' + C.good + '">\u6392\u9664' + esc(excNames) + '\uFF0C\u5269' + (3-excList.length) + '\u65B9\u5411</span>';
                    } else {
                        html += '<span style="font-size:11.5px;color:' + C.textDim + '">\u65E0\u660E\u786E\u6392\u9664</span>';
                    }
                    html += '</div>'; // 排除法行结束

                    // 最终建议（整合所有信号）
                    html += '<div style="margin-top:8px;padding:8px 10px;border-radius:6px;" id="finalRecommendationBox">';
                    
                    // 简洁的最终建议逻辑
                    var finalAdvice = '', finalAdviceColor = C.text, finalStars = '';
                    
                    if (_isTrap && _isAnomaly) {
                        // 三重共振陷阱 → 反向建议
                        finalAdvice = '\uD83D\uDD25 \u5EFA\u8BAE\u5173\u6CE8\uFF1A' + _antiName + ' \uFF08\u53CD\u5411\uFF09';
                        finalAdviceColor = '#f87171';
                        finalStars = '\u2605\u2605\u2605\u2605\u2605';
                    } else if (finalPred) {
                        // 有排除法结论
                        var fpn2 = {home: mi.home + '\u80DC', draw: '\u5E33\u5C40', away: mi.away + '\u80DC'}[finalPred] || finalPred;
                        var confLv = conf || 0;
                        if (confLv >= 5) {
                            finalAdvice = '\uD83D\uDCAA \u9AD8\u5EA6\u786E\u5B9A\uFF1A' + fpn2;
                            finalAdviceColor = '#22c55e';
                            finalStars = '\u2605\u2605\u2605\u2605\u2605';
                        } else if (confLv >= 4) {
                            finalAdvice = '\uD83D\uDEE1 \u8F83\u4E3A\u786E\u5B9A\uFF1A' + fpn2;
                            finalAdviceColor = '#3b82f6';
                            finalStars = '\u2605\u2605\u2605\u2605';
                        } else if (confLv >= 3) {
                            finalAdvice = '\uD83D\uDD14 \u6709\u53C2\u8003\uFF1A' + fpn2;
                            finalAdviceColor = '#eab308';
                            finalStars = '\u2605\u2605\u2605';
                        } else {
                            finalAdvice = '\uD83D\uDD33 \u5F31\u503E\u5411\uFF1A' + fpn2;
                            finalAdviceColor = '#f97316';
                            finalStars = '\u2605\u2605';
                        }
                    } else if (bt) {
                        // 无排除法，基于基本面
                        var btn2 = {home: mi.home + '\u80DC', draw: '\u5E33\u5C40', away: mi.away + '\u80DC'}[bt] || bt;
                        // 检查澳门是否同向
                        var mcAgrees2 = false;
                        if (mcHasRec && mcRecText) {
                            if (bt === 'home' && mcRecText.indexOf(mi.home) !== -1) mcAgrees2 = true;
                            else if (bt === 'away' && mcRecText.indexOf(mi.away) !== -1) mcAgrees2 = true;
                            else if (bt === 'draw' && (mcRecText.indexOf('\u548C') !== -1 || mcRecText.indexOf('\u5E73') !== -1)) mcAgrees2 = true;
                        }
                        
                        if (mcAgrees2) {
                            finalAdvice = '\uD83D\uDC4D \u7EFC\u5408\u5224\u5B9A\uFF1A' + btn2;
                            finalAdviceColor = '#22c55e';
                            finalStars = '\u2605\u2605\u2605\u2605';
                        } else if (mcHasRec && !mcAgrees2) {
                            finalAdvice = '\uD83D\uDDD3 \u7EFC\u5408\u5224\u5B9A\uFF1A' + btn2 + ' \u26A0\uFE0F';
                            finalAdviceColor = '#f97316';
                            finalStars = '\u2605\u2605\u2605';
                        } else {
                            finalAdvice = '\uD83D\uDCCD \u7EFC\u5408\u5224\u5B9A\uFF1A' + btn2;
                            finalAdviceColor = '#3b82f6';
                            finalStars = '\u2605\u2605\u2605';
                        }
                    } else {
                        finalAdvice = '\uD83D\uDC64 \u4FE1\u53F7\u4E0D\u8DB3\uFF0C\u5EFA\u8BAE\u89C2\u671B';
                        finalAdviceColor = C.textDim;
                        finalStars = '';
                    }

                    html += '<div style="display:flex;align-items:center;justify-content:space-between">';
                    html += '<span style="font-size:13px;font-weight:bold;color:' + finalAdviceColor + '">' + finalAdvice + ' ' + finalStars + '</span>';
                    html += '</div>';

                    // 补充推理说明
                    var reasonHtml = '';
                    if (_isTrap && _isAnomaly) {
                        reasonHtml = '\u2622\uFE0F \u6392\u9664\u6CD5\u00D7\u8BA9\u7403\u51FA\u53E3\u00D7\u57FA\u672C\u9762=\u5B8C\u7F8E\u5171\u632F\u2192\u5E94\u5BF9\u53CD\u5411';
                    } else if (finalPred) {
                        reasonHtml = '\u2714\uFE0F \u57FA\u4E8E\u6392\u9664\u6CD5\u5F15\u64CE' + (excList.length >= 2 ? '\uFF08\u6392\u96642\u65B9\u5411\uFF09' : '');
                    } else if (bt) {
                        if (mcHasRec) reasonHtml = '\u57FA\u672C\u9762+' + (mcAgrees2 ? '\u6FB3\u95E8\u540C\u5411' : '\u6FB3\u95E8\u5206\u6B67');
                        else reasonHtml = '\u57FA\u4E8E\u57FA\u672C\u9762\u503E\u5411';
                    }
                    
                    if (reasonHtml) {
                        html += '<div style="margin-top:4px;font-size:11px;color:' + C.textDim + '">\u25B8 ' + reasonHtml + '</div>';
                    }

                    html += '</div>'; // finalRecommendationBox end
                    html += '</div>'; // 综合判定容器 end

                } else {
                    // 无让球盘数据的简洁模式
                    html += '<div style="margin-bottom:6px"><span style="font-size:11.5px;color:#93c5fd;font-weight:600">② 让球盘</span></div>';
                    html += '<div style="padding:8px 10px;color:' + C.textDim + ';font-size:11.5px;background:#17255425;border-radius:6px;margin-bottom:10px">';
                    html += '\uD83D\uDC64 \u672C\u573A\u65E0\u8BA9\u7403\u76D8\u6570\u636E';
                    html += '</div>';

                    // 简化版综合判定
                    html += '<div style="margin-bottom:6px"><span style="font-size:11.5px;color:#93c5fd;font-weight:600">③ 综合判定</span></div>';
                    html += '<div style="background:#0f172a45;border-radius:8px;padding:10px 12px;margin-bottom:10px;border-left:3px solid ' + vs.border + '">';
                    
                    var sbt = cc.basic_tendency || '';
                    var sbtLabel = sbt ? ({home: mi.home + '\u80DC', draw: '\u5E33\u5C40', away: mi.away + '\u80DC'}[sbt]) : '\u5747\u8861';
                    html += '<div style="font-size:12px;color:' + C.text + '">';
                    html += '\u57FA\u672C\u9762: <b>' + esc(sbtLabel) + '</b> &nbsp;|&nbsp; ';
                    if (finalPred) {
                        var sfpName = {home: mi.home + '\u80DC', draw: '\u5E33\u5C40', away: mi.away + '\u80DC'}[finalPred] || finalPred;
                        html += '\u6392\u9664: <b style="color:' + C.alignGood + '">' + esc(sfpName) + '</b> ' + '\u2605'.repeat(conf || 0);
                    } else if (excList.length > 0) {
                        html += '\u6392\u9664: <b style="color:' + C.good + '">' + excList.map(function(e){return {home:'\u4E3B\u80DC',draw:'\u5E73\u5C40',away:'\u5BA2\u80DC'}[e]||e;}).join('/') + '</b>';
                    } else {
                        html += '\u6392\u9664: <span style="color:' + C.textDim + '">\u65E0\u660E\u786E\u6392\u9664</span>';
                    }
                    html += '</div>';
                    html += '</div>';
                }

                // 澳门分析原文（始终显示）
                if (mc.analysis) {
                    html += '<div style="margin-top:8px;padding:8px 10px;background:#1e293b40;border-radius:6px;border-left:3px solid ' + C.border + '">';
                    html += '<div style="font-size:11px;color:' + C.textDim + ';margin-bottom:3px;font-weight:600">\u6FB3\u95E8\u5206\u6790\u539F\u6587</div>';
                    html += '<div style="font-size:11.5px;color:' + C.text + ';line-height:1.6">' + esc(mc.analysis.substring(0, 300)) + (mc.analysis.length > 300 ? '...' : '') + ' |</div>';
                    html += '</div>';
                }

                html += '</div>'; // 综合推理结论容器 end
                html += '</div>'; // 赛前情报卡片 end

                // 插入DOM
                detailContent.insertAdjacentHTML('beforeend', html);

            })["catch"](function(err) {
                console.error('\u8D5B\u524D\u60C5\u62A5\u52A0\u8F7D\u51FA\u9519:', err);
            });

    };
})();
'''

# 合并：好代码 + 新代码
result_lines = good_lines + [new_code]

# 写回
with open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'w', encoding='utf-8') as f:
    f.writelines(result_lines)

print(f"\nDone! Written {len(result_lines)} total lines")
print(f"Removed bad IIFE (lines {bad_start+1} to {len(lines)})")
print(f"Added new code from line {bad_start+1}")
