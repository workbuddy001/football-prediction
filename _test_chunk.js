(async () => {
    const rd = res.raw_data;
    const an = res.analysis;
    
    const om = an.odds_matrix || {};
    const jm = om.jingcai || {};
    const mm = om.macao || {};
    const st = an.stats || {};
    
    let html = `
    <div class="detail-header">
        <h2>${rd.home_team || '?'} vs ${rd.away_team || '?'}</h2>
        <div class="meta">
            📌 ${rd.id || ''} &nbsp;|&nbsp; ⚽ ${rd.league || ''} &nbsp;|&nbsp; 🕐 ${rd.match_time || ''}
            &nbsp;|&nbsp; 让球: ${rd.handicap || '-'}
        </div>
    </div>
    
    <!-- 最终结论 -->
    <div class="final-result">
        <div class="pred-text" style="${an.final_prediction&&an.final_prediction.includes('主')?'color:#4ade80':an.final_prediction&&an.final_prediction.includes('平')?'color:#facc15':an.final_prediction&&an.final_prediction.includes('客')?'color:#fca5a5':'color:#94a3b8'}">
            ${an.final_prediction || '-'}
        </div>
        <div class="conf-text">${an.confidence_text || ''}</div>
    </div>`;
    
    // 基本面信息
    html += `
    <div class="section">
        <div class="section-title"><span class="icon icon-blue">ℹ️</span> 基本面信息</div>
        <div class="odds-grid">
            <div class="odds-card">
                <div class="title">主队近况</div>
                <div class="odds-row"><span class="label">走势</span><span class="value">${rd.home_form || '-'}</span></div>
                <div class="odds-row"><span class="label">战绩</span><span class="value">${rd.home_record || '-'}</span></div>
            </div>
            <div class="odds-card">
                <div class="title">客队近况</div>
                <div class="odds-row"><span class="label">走势</span><span class="value">${rd.away_form || '-'}</span></div>
                <div class="odds-row"><span class="label">战绩</span><span class="value">${rd.away_record || '-'}</span></div>
            </div>
            <div class="odds-card">
                <div class="title">澳门推荐 & 历史</div>
                <div class="odds-row"><span class="label">心水</span><span class="value" style="color:#facc15">${rd.macao_tip || '-'}</span></div>
                <div class="odds-row"><span class="label">交锋</span><span class="value">${rd.history || '-'}</span></div>
            </div>
        </div>
    </div>`;
    
    // 赔率矩阵
    html += `
    <div class="section">
        <div class="section-title"><span class="icon icon-green">💰</span> 赔率矩阵（标准1X2）</div>
        <div class="odds-grid">
            <div class="odds-card">
                <div class="title">🇨🇳 竞彩官方</div>
                <div class="odds-row"><span class="label">主胜</span><span class="value">${jm.init?jm.init[0].toFixed(2):'-'} → ${jm.real?jm.real[0].toFixed(2):'-'}</span><span class="${(jm.change||[])[0]>0?'change-up':(jm.change||[])[0]<0?'change-down':'change-none'}">${((jm.change||[])[0]||0).toFixed(1)>0?'+':''}${((jm.change||[])[0]||0).toFixed(1)}%</span></div>
                <div class="odds-row"><span class="label">平局</span><span class="value">${jm.init?jm.init[1].toFixed(2):'-'} → ${jm.real?jm.real[1].toFixed(2):'-'}</span><span class="${(jm.change||[])[1]>0?'change-up':(jm.change||[])[1]<0?'change-down':'change-none'}">${((jm.change||[])[1]||0).toFixed(1)>0?'+':''}${((jm.change||[])[1]||0).toFixed(1)}%</span></div>
                <div class="odds-row"><span class="label">客胜</span><span class="value">${jm.init?jm.init[2].toFixed(2):'-'} → ${jm.real?jm.real[2].toFixed(2):'-'}</span><span class="${(jm.change||[])[2]>0?'change-up':(jm.change||[])[2]<0?'change-down':'change-none'}">${((jm.change||[])[2]||0).toFixed(1)>0?'+':''}${((jm.change||[])[2]||0).toFixed(1)}%</span></div>
            </div>
            <div class="odds-card">
                <div class="title">🇲🇴 澳门</div>
                <div class="odds-row"><span class="label">主胜</span><span class="value">${mm.init?mm.init[0].toFixed(2):'-'} → ${mm.real?mm.real[0].toFixed(2):'-'}</span><span class="${(mm.change||[])[0]>0?'change-up':(mm.change||[])[0]<0?'change-down':'change-none'}">${((mm.change||[])[0]||0).toFixed(1)>0?'+':''}${((mm.change||[])[0]||0).toFixed(1)}%</span></div>
                <div class="odds-row"><span class="label">平局</span><span class="value">${mm.init?mm.init[1].toFixed(2):'-'} → ${mm.real?mm.real[1].toFixed(2):'-'}</span><span class="${(mm.change||[])[1]>0?'change-up':(mm.change||[])[1]<0?'change-down':'change-none'}">${((mm.change||[])[1]||0).toFixed(1)>0?'+':''}${((mm.change||[])[1]||0).toFixed(1)}%</span></div>
                <div class="odds-row"><span class="label">客胜</span><span class="value">${mm.init?mm.init[2].toFixed(2):'-'} → ${mm.real?mm.real[2].toFixed(2):'-'}</span><span class="${(mm.change||[])[2]>0?'change-up':(mm.change||[])[2]<0?'change-down':'change-none'}">${((mm.change||[])[2]||0).toFixed(1)>0?'+':''}${((mm.change||[])[2]||0).toFixed(1)}%</span></div>
            </div>
        </div>`;
    
    // 30家公司统计
    if (st.total) {
        html += `
        <div style="margin-top:14px">
            <div class="section-title" style="margin-bottom:10px">📊 30家公司赔率变化统计</div>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-label">主胜</div>
                    <div class="stat-value">${st.home?st.home.down:0}<span style="font-size:12px;color:#4ade80">↓</span> / ${st.home?st.home.same:0}= / ${st.home?st.home.up:0}<span style="font-size:12px;color:#f87171">↑</span></div>
                    <div class="stat-sub">共 ${st.total} 家</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">平局</div>
                    <div class="stat-value">${st.draw?st.draw.down:0}<span style="font-size:12px;color:#4ade80">↓</span> / ${st.draw?st.draw.same:0}= / ${st.draw?st.draw.up:0}<span style="font-size:12px;color:#f87171">↑</span></div>
                    <div class="stat-sub">共 ${st.total} 家</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">客胜</div>
                    <div class="stat-value">${st.away?st.away.down:0}<span style="font-size:12px;color:#4ade80">↓</span> / ${st.away?st.away.same:0}= / ${st.away?st.away.up:0}<span style="font-size:12px;color:#f87171">↑</span></div>
                    <div class="stat-sub">共 ${st.total} 家</div>
                </div>
            </div>
        </div>`;
    }
    
    html += '</div>'; // end section
    
    // 信号列表
    if (an.signals && an.signals.length > 0) {
        html += `
        <div class="section">
            <div class="section-title"><span class="icon icon-yellow">🔍</span> 排除法信号分析 (${an.signals.length}条)</div>`;
        an.signals.forEach(s => {
            const strCls = `str${s.strength||0}`;
            const dotCls = `dot-${s.strength||0}`;
            html += `<div class="signal-card ${strCls}">
                <div>
                    <strong style="color:${s.strength>=4?'#4ade80':s.strength==3?'#fbbf24':'#94a3b8'}">${s.rule}</strong>
                    <div style="color:#94a3b8;font-size:12px;margin-top:3px">${s.detail}</div>
                    ${s.action?`<div style="color:#60a5fa;font-size:12px;margin-top:3px">→ ${s.action}</div>`:''}
                </div>
                <div class="strength-dot ${dotCls}" title="强度: ${s.strength}/5"></div>
            </div>`;
        });
        html += '</div>';
    }
    
    // 历史复盘参考
    const simReviews = res.similar_reviews || [];
    
    if (simReviews.length > 0) {
        // 统计命中率
        const hitCount = simReviews.filter(r => r.is_correct).length;
        const missCount = simReviews.length - hitCount;
        const hitRate = simReviews.length > 0 ? Math.round(hitCount / simReviews.length * 100) : 0;
        
        // 根据历史命中率生成建议
        let suggestion = '';
        if (missCount === simReviews.length && simReviews.length >= 2) {
            suggestion = `<div style="margin-top:10px;padding:10px 14px;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:8px">
                <span style="color:#f87171;font-weight:bold">⚠️ 历史警示：${simReviews.length}条相似案例全部预测失败！</span>
                <div style="color:#fca5a5;font-size:12px;margin-top:4px">
                这意味着当前的排除模式在历史上反复出错，建议：
                • 重新审视排除方向是否有遗漏<br/>
                • 检查是否存在"掩护模式"或"造热陷阱"<br/>
                • 考虑降低置信度或改为观望态度</div>
            </div>`;
        } else if (hitRate <= 33 && simReviews.length >= 3) {
            suggestion = `<div style="margin-top:10px;padding:10px 14px;background:rgba(251,191,36,0.1);border:1px solid rgba(251,191,36,0.3);border-radius:8px">
                <span style="color:#fbbf24;font-weight:bold">⚠️ 历史参考：${simReviews.length}条相似案例仅${hitCount}条命中(${hitRate}%)</span>
                <div style="color:#fcd34d;font-size:12px;margin-top:4px">
                相似模式的历史表现不佳，建议结合其他信号综合判断，不要过度依赖单一排除路径。</div>
            </div>`;
        } else if (hitRate >= 67) {
            suggestion = `<div style="margin-top:10px;padding:10px 14px;background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);border-radius:8px">
                <span style="color:#4ade80;font-weight:bold">✅ 历史支持：${simReviews.length}条相似案例中${hitCount}条命中(${hitRate}%)</span>
                <div style="color:#86efac;font-size:12px;margin-top:4px">
                当前排除模式与历史上成功案例高度相似，可作为信心支撑。但仍需注意具体比赛的特殊性。</div>
            </div>`;
        }
        
        html += `

        <div class="section">
            <div class="section-title"><span class="icon icon-green">📚</span> 历史复盘参考（${simReviews.length}条相似案例 · 命中${hitCount}/${simReviews.length}${totalOpp > 0 ? ' · 含'+totalOpp+'条反向' : ''}）</div>
            <div style="font-size:11px;color:#64748b;margin-bottom:4px;line-height:1.6">
                <b>4维匹配标准：</b>赛事（同联赛15/同类型10）| 球队（同队12）| 赔率变向（竞彩模式15/澳门12/排除一致20/幅度接近6）| 预测（相同5/心水3）
                &nbsp;|&nbsp; <b>硬性前提：</b>预测结果必须相同
                &nbsp;|&nbsp; <b>门槛：</b>相似分≥35分 或 同队+同排除
            </div>
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap">
                <div style="display:flex;gap:6px;align-items:center">
                    <span style="font-size:11px;color:#94a3b8">命中率:</span>
                    <div style="width:80px;height:16px;background:#1e293b;border-radius:8px;overflow:hidden;position:relative">
                        <div style="position:absolute;left:0;top:0;height:100%;background:${hitRate>=50?'#22c55e':hitRate>=30?'#f59e0b':'#ef4444'};width:${hitRate}%;transition:width 0.3s"></div>
                    </div>
                    <span style="font-size:11px;font-weight:bold;color:${hitRate>=50?'#4ade80':hitRate>=30?'#fbbf24':'#f87171'}">${hitRate}%</span>
                </div>
            </div>`;

        // === 结果统计（胜/平/负分布）===
        var winCount = 0, drawCount = 0, loseCount = 0;
        simReviews.forEach(function(r) {
            var rc = (r.result_cn || '');
            if (rc.indexOf('主胜') >= 0) winCount++;
            else if (rc.indexOf('客胜') >= 0) loseCount++;
            else if (rc.indexOf('平') >= 0) drawCount++;
            else {
                var sc = r.actual_score || '';
                if (sc) {
                    var parts = sc.split('-');
                    if (parts.length >= 2) {
                        var h = parseInt(parts[0]), a = parseInt(parts[1]);
                        if (!isNaN(h) && !isNaN(a)) {
                            if (h > a) winCount++;
                            else if (h < a) loseCount++;
                            else drawCount++;
                        }
                    }
                }
            }
        });
        var totalDecided = winCount + drawCount + loseCount;
        var statHtml = '<div style="display:flex;align-items:center;gap:16px;margin-bottom:12px;padding:8px 12px;background:#0f172a;border-radius:8px;flex-wrap:wrap">';
        statHtml += '<span style="font-size:11px;color:#94a3b8">📊 结果分布：</span>';
        if (totalDecided > 0) {
            statHtml += '<span style="font-size:12px;color:#4ade80;font-weight:bold">' + winCount + '胜</span>';
            statHtml += ' <span style="color:#334155">·</span> ';
            statHtml += '<span style="font-size:12px;color:#fbbf24;font-weight:bold">' + drawCount + '平</span>';
            statHtml += ' <span style="color:#334155">·</span> ';
            statHtml += '<span style="font-size:12px;color:#f87171;font-weight:bold">' + loseCount + '负</span>';
            statHtml += ' <span style="font-size:11px;color:#64748b;margin-left:4px">（共' + totalDecided + '场）</span>';
        } else {
            statHtml += '<span style="font-size:11px;color:#64748b">暂无结果数据</span>';
        }
        statHtml += '</div>';
        html += statHtml;

        simReviews.forEach(function(rev) {
            var hitTag = rev.is_correct ?
                '<span style="background:rgba(34,197,94,0.15);color:#4ade80;padding:2px 8px;border-radius:4px;font-size:11px">✅命中</span>' :
                '<span style="background:rgba(239,68,68,0.15);color:#f87171;padding:2px 8px;border-radius:4px;font-size:11px">❌未中</span>';

            var reasonTags = '';
            if (rev.match_reasons) {
                reasonTags = rev.match_reasons.map(function(r) {
                    return '<span style="font-size:10px;background:rgba(99,102,241,0.15);color:#a5b4fc;padding:1px 6px;border-radius:3px;margin-right:4px;margin-bottom:2px;display:inline-block">' + r + '</span>';
                }).join('');
            }

            // 各维度得分条
            var ds = rev.dim_scores || {};
            var dimLabels = ['赛事','球队','赔率','预测'];
            var dimColors = ['#60a5fa','#4ade80','#f59e0b','#a78bfa'];
            var dimParts = [];
            for (var di = 0; di < dimLabels.length; di++) {
                var label = dimLabels[di];
                var score = ds[label] || 0;
                var color = dimColors[di];
                var w = Math.min(score * 2, 100);
                dimParts.push(
                    '<div style="flex:1;min-width:50px">' +
                    '<div style="font-size:9px;color:#64748b;text-align:center;margin-bottom:1px">' + label + score + '</div>' +
                    '<div style="height:6px;background:#1e293b;border-radius:3px;overflow:hidden">' +
                    '<div style="width:' + w + '%;height:100%;background:' + color + ';transition:width 0.3s"></div></div></div>'
                );
            }
            var dimHtml = dimParts.join('');

            var clsName = rev.is_correct ? 'str5' : 'str2';
            var isOppTag = rev.is_opposite ? '<span style="background:rgba(168,85,247,0.2);color:#c084fc;padding:2px 8px;border-radius:4px;font-size:10px;border:1px dashed #a855f7">↔ 反向</span>' : '';
            html += '<div class="signal-card ' + clsName + '" style="margin-bottom:10px' + (rev.is_opposite ? ';border-left:3px solid #a855f7' : '') + '"><div>' +
                '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;flex-wrap:wrap">' +
                '<strong style="font-size:13px;color:#cbd5e1">' + rev.home_team + ' vs ' + rev.away_team + '</strong>' +
                '<span style="color:#94a3b8;font-size:11px">' + (rev.league||'') + '</span>' +
                hitTag + isOppTag +
                '<span style="color:#6366f1;font-size:10px;font-weight:bold">' + rev.match_score + '分</span>' +
                '</div>' +
                '<div style="display:flex;gap:6px;margin-bottom:4px;background:#0c1222;padding:4px 8px;border-radius:4px;width:fit-content">' + dimHtml + '</div>' +
                '<div style="color:#94a3b8;font-size:12px">' +
                '预测：<strong>' + (rev.prediction||'') + '</strong> (' + (rev.confidence||0) + '★) | ' +
                '实际：<strong>' + (rev.actual_score||'') + '</strong> (' + (rev.result_cn||'') + ') | ' +
                '排除：' + ((rev.exclusions||[]).map(function(e){ return e==='home'?'主':e==='draw'?'平':'客'; }).join('、') || '无') +
                '</div>';

            // 澳门心水推荐
            var macaoTip = rev.macao_tip || '';
            if (macaoTip) {
                html += '<div style="margin-top:3px;color:#f59e0b;font-size:11.5px">🎯 澳门心水：<strong style="color:#fbbf24">' + macaoTip + '</strong></div>';
            }

            // 赔率信息
            var odds = rev.odds_data || {};
            if (odds.jc_real_odds && odds.jc_real_odds.length >= 3) {
                var jco = odds.jc_real_odds;  // 竞彩即时赔率
                var mco = odds.macao_real_odds || [];  // 澳门即时赔率
                var jcInit = odds.jc_init_odds || [];   // 竞彩初盘
                var mcaoInit = odds.macao_init_odds || []; // 澳门初盘

                // 赔率变化箭头函数（提前声明，避免作用域问题）
                function _arrow(cur, init) {
                    var d = cur - init;
                    if (d > 0.02) return '<span style="color:#fca5a5;font-size:11px;font-weight:bold">↑' + d.toFixed(2) + '</span>';
                    else if (d < -0.02) return '<span style="color:#86efac;font-size:11px;font-weight:bold">↓' + Math.abs(d).toFixed(2) + '</span>';
                    return '<span style="color:#475569;font-size:11px">—</span>';
                }

                html += '<div style="margin-top:4px;background:#1e293b;border-radius:6px;padding:8px 10px;font-size:11.5px">';

                // 竞彩赔率行
                html += '<table style="width:100%;border-collapse:collapse">';
                html += '<tr><td colspan="4" style="padding-bottom:2px;color:#94a3b8;font-size:10.5px;font-weight:600">\u7ade\u5f69\u8d54\u7387\uff08\u5373\u65f6 / \u53d8\u5316\uff09</td></tr>';
                html += '<tr>';
                html += '<td style="text-align:center;padding:2px"><span style="color:#94a3b8;font-size:10px">\u4e3b</span><br><strong style="color:#60a5fa;font-size:13px">' + (jco[0]||'-') + '</strong></td>';
                html += '<td style="text-align:center;padding:2px"><span style="color:#94a3b8;font-size:10px">\u5e73</span><br><strong style="color:#fbbf24;font-size:13px">' + (jco[1]||'-') + '</strong></td>';
                html += '<td style="text-align:center;padding:2px"><span style="color:#94a3b8;font-size:10px">\u5ba2</span><br><strong style="color:#a78bfa;font-size:13px">' + (jco[2]||'-') + '</strong></td>';

                // 赔率变化箭头
                if (jcInit.length >= 3) {
                    html += '<td style="text-align:right;padding:2px;white-space:nowrap;vertical-align:bottom;border-left:1px solid #334155;padding-left:8px">';
                    html += '<span style="color:#64748b;font-size:9px">\u53d8\u5316:</span> ';
                    html += _arrow(jco[0], jcInit[0]) + ' ';
                    html += _arrow(jco[1], jcInit[1]) + ' ';
                    html += _arrow(jco[2], jcInit[2]);
                    html += '</td>';
                } else {
                    html += '<td></td>';
                }
                html += '</tr>';

                // 澳门赔率行
                if (mco.length >= 3) {
                    html += '<tr><td colspan="4" style="padding:3px 0 1px;color:#94a3b8;font-size:10.5px;font-weight:600;border-top:1px solid #334155">\u6fb3\u95e8\u8d54\u7387\uff08\u5373\u65f6 / \u53d8\u5316\uff09</td></tr>';
                    html += '<tr>';
                    html += '<td style="text-align:center;padding:2px"><span style="color:#94a3b8;font-size:10px">\u4e3b</span><br><strong style="color:#60a5fa;font-size:13px">' + (mco[0]||'-') + '</strong></td>';
                    html += '<td style="text-align:center;padding:2px"><span style="color:#94a3b8;font-size:10px">\u5e73</span><br><strong style="color:#fbbf24;font-size:13px">' + (mco[1]||'-') + '</strong></td>';
                    html += '<td style="text-align:center;padding:2px"><span style="color:#94a3b8;font-size:10px">\u5ba2</span><br><strong style="color:#a78bfa;font-size:13px">' + (mco[2]||'-') + '</strong></td>';
                    if (mcaoInit.length >= 3) {
                        html += '<td style="text-align:right;padding:2px;white-space:nowrap;vertical-align:bottom;border-left:1px solid #334155;padding-left:8px">';
                        html += '<span style="color:#64748b;font-size:9px">\u53d8\u5316:</span> ';
                        html += _arrow(mco[0], mcaoInit[0]) + ' ';
                        html += _arrow(mco[1], mcaoInit[1]) + ' ';
                        html += _arrow(mco[2], mcaoInit[2]);
                        html += '</td>';
                    } else {
                        html += '<td></td>';
                    }
                    html += '</tr>';
                }

                html += '</table></div>';

                // ════════════════════════════════════
                // 【核心】让球盘对比分析：盘口 + 让球赔率 vs 不让球赔率
                // ════════════════════════════════════
                var revHc = rev.handicap || '';
                var baseHc = res.analysis ? (res.analysis.handicap || '') : '';
                
                // 获取当前比赛数据
                var curJcOdds = [], curMacOdds = [], _curRd = {};
                try { _curRd = (typeof res.raw_data === 'string') ? JSON.parse(res.raw_data||'{}') : (res.raw_data||{}); } catch(e){}
                try {
                    if (_curRd.realtime_odds && _curRd.realtime_odds.length > 0) curJcOdds = _curRd.realtime_odds[0].slice(0,3);
                    if (_curRd.realtime_odds && _curRd.realtime_odds.length > 2) curMacOdds = _curRd.realtime_odds[2].slice(0,3);
                } catch(e){}

                // 当前比赛的让球盘赔率（第四节竞彩让球赔率）— 从 raw_data.jc_odds 获取
                var curHcJcOdds = [];
                // 优先从 raw_data.jc_odds（API正确位置），兼容旧格式
                var _rdJcOdds = (res.raw_data && res.raw_data.jc_odds) ? res.raw_data.jc_odds :
                    ((res.analysis && res.analysis.jc_odds) ? res.analysis.jc_odds : null);
                if (_rdJcOdds && Array.isArray(_rdJcOdds) && _rdJcOdds.filter(function(x){return x>0;}).length >= 2) {
                    curHcJcOdds = [_rdJcOdds[0]||0, _rdJcOdds[1]||0, _rdJcOdds[2]||0];
                }
                
                // 案例的让球盘赔率（从复盘指纹中获取）
                var revFp = rev.odds_fingerprint || {};
                var revHcJcOdds = [];  // 案例当时的让球赔率（如果有存储的话）

                html += '<div style="margin-top:6px;background:#0c1222;border-radius:6px;padding:8px 10px;border:1px solid #1e293b">';
                html += '<div style="font-size:10.5px;color:#94a3b8;font-weight:600;margin-bottom:4px">⚖️ 让球盘 & 不让球赔率对比</div>';

                // ===== 第一行：让球盘口对比 =====
                if (revHc || baseHc) {
                    var hcSame = (revHc && baseHc && String(revHc) === String(baseHc));
                    html += '<div style="display:flex;align-items:center;gap:8px;padding-bottom:4px;border-bottom:1px solid #1e293b;margin-bottom:6px">';
                    html += '<span style="color:#64748b;font-size:10px;min-width:52px">让球:</span>';
                    html += '<span style="background:' + (hcSame?'#1f4a2e':'#4a3a18') + ';padding:1px 8px;border-radius:4px;font-weight:bold;color:' + (hcSame?'#4ade80':'#fbbf24') + ';font-size:12px;font-family:monospace">' + (revHc||'-') + '</span>';
                    if (baseHc) {
                        html += '<span style="color:#334155">→</span>';
                        html += '<span style="color:#94a3b8;font-size:11px;font-family:monospace">' + baseHc + '</span>';
                        if (!hcSame && revHc && baseHc) html += '<span style="color:#f59e0b;font-size:9.5px;margin-left:2px">⚠盘口不同</span>';
                    }
                    html += '</div>';
                }

                // ===== 核心对比表：不让球(标准) vs 让球后 =====
                html += '<table style="width:100%;border-collapse:collapse;font-size:10.5px">';
                
                // 表头
                html += '<tr><td style="padding:2px"></td>';
                html += '<td colspan="3" style="text-align:center;padding:2px;color:#60a5fa;font-size:9.5px;border-bottom:1px solid #1e334a"><strong>🏠 主胜</strong></td>';
                html += '<td colspan="3" style="text-align:center;padding:2px;color:#fbbf24;font-size:9.5px;border-bottom:1px solid #43341a"><strong>🤝 平局</strong></td>';
                html += '<td colspan="3" style="text-align:center;padding:2px;color:#fca5a5;font-size:9.5px;border-bottom:1px solid #4a1a1a"><strong>✈️ 客胜</strong></td></tr>';

                html += '<tr><td style="padding:1px"></td>';
                ['主','平','客'].forEach(function() {
                    html += '<td style="padding:1px 3px;text-align:center;color:#64748b;font-size:9px;width:40px">案例</td>';
                    html += '<td style="padding:1px 3px;text-align:center;color:#64748b;font-size:9px;width:40px">当前</td>';
                    html += '<td style="padding:1px 2px;text-align:center;color:#475569;font-size:8px;width:22px">差</td>';
                });
                html += '</tr>';

                // ---- 数据行1：竞彩不让球（标准欧赔） ----
                if (jco.length >= 3 && curJcOdds.length >= 3) {
                    html += '<tr style="background:#0a1628;border-top:1px solid #1e293b">';
                    html += '<td style="padding:2px 2px;text-align:right;color:#60a5fa;font-size:9.5px;font-weight:600">竞彩<br><span style="font-weight:normal;color:#475569;font-size:8px">不让球</span></td>';
                    
                    [0,1,2].forEach(function(idx) {
                        var sv = jco[idx], cv = curJcOdds[idx];
                        var diff = (sv - cv).toFixed(2);
                        var dAbs = Math.abs(sv - cv);
                        var dc = dAbs < 0.15 ? '#22c55e' : dAbs < 0.35 ? '#eab308' : '#ef4444';
                        html += '<td style="text-align:center;padding:1px"><strong style="color:#fff;font-size:12px">' + sv.toFixed(2) + '</strong></td>';
                        html += '<td style="text-align:center;padding:1px"><span style="color:#94a3b8;font-size:10px">' + cv.toFixed(2) + '</span></td>';
                        html += '<td style="text-align:center;padding:1px"><span style="color:'+dc+';font-size:9px;font-weight:bold">'+(diff>0?'+':'')+diff+'</span></td>';
                    });
                    html += '</tr>';
                }

                // ---- 数据行2：竞彩让球盘（★核心！第四节数据）----
                // 案例的让球赔率
                var rHcOdds = [];
                if (revFp.hc_jc_odds && Array.isArray(revFp.hc_jc_odds)) rHcOdds = revFp.hc_jc_odds;
                
                if ((rHcOdds.length >= 3 || revHc) && (curHcJcOdds.length >= 2 || baseHc)) {
                    html += '<tr style="background:#2a1e08;border-top:1px dashed #334155">';
                    
                    // 左侧标签：显示让球数
                    var hcLabel = revHc ? ('让'+revHc) : '让球';
                    html += '<td style="padding:2px 2px;text-align:right;color:#f59e0b;font-size:9.5px;font-weight:600">' + hcLabel + '<br><span style="font-weight:normal;color:#475569;font-size:8px">让球后</span></td>';
                    
                    [0,1,2].forEach(function(idx) {
                        var sv = (rHcOdds[idx] !== undefined && rHcOdds[idx] > 0) ? rHcOdds[idx] : null;
                        var cv = (curHcJcOdds[idx] > 0) ? curHcJcOdds[idx] : null;

                        if (sv === null && cv === null) {
                            html += '<td colspan="3" style="text-align:center;padding:1px;color:#334155">-</td>';
                            return;
                        }
                        
                        html += '<td style="text-align:center;padding:1px">';
                        if (sv !== null) {
                            html += '<strong style="color:#fff;font-size:12px;background:#3d2a08;padding:0 3px;border-radius:2px">' + sv.toFixed(2) + '</strong>';
                        } else { html += '<span style="color:#334155">-</span>'; }
                        html += '</td>';
                        
                        html += '<td style="text-align:center;padding:1px">';
                        if (cv !== null) html += '<span style="color:#fbbf24;font-size:10px">' + cv.toFixed(2) + '</span>';
                        else html += '<span style="color:#334155">-</span>';
                        html += '</td>';
                        
                        if (sv !== null && cv !== null) {
                            var diff2 = (sv-cv).toFixed(2), dA2 = Math.abs(sv-cv);
                            var dc2 = dA2<0.15?'#22c55e':dA2<0.5?'#eab308':'#ef4444';
                            html += '<td style="text-align:center;padding:1px"><span style="color:'+dc2+';font-size:9px;font-weight:bold">'+(diff2>0?'+':'')+diff2+'</span></td>';
                        } else {
                            html += '<td style="text-align:center;padding:1px">-</td>';
                        }
                    });
                    html += '</tr>';
                }

                // ---- 数据行3：澳门不让球 ----
                if (mco.length >= 3 && curMacOdds.length >= 3) {
                    html += '<tr style="border-top:1px solid #1e293b">';
                    html += '<td style="padding:2px 2px;text-align:right;color:#a78bfa;font-size:9.5px;font-weight:600">澳门<br><span style="font-weight:normal;color:#475569;font-size:8px">不让球</span></td>';
                    [0,1,2].forEach(function(idx) {
                        var sv=mco[idx]||0,cv=curMacOdds[idx];
                        var diff3=(sv-cv).toFixed(2),dA3=Math.abs(sv-cv);
                        var dc3=dA3<0.15?'#22c55e':dA3<0.35?'#eab308':'#ef4444';
                        html+='<td style="text-align:center;padding:1px"><strong style="color:#fff;font-size:12px">'+sv.toFixed(2)+'</strong></td>';
                        html+='<td style="text-align:center;padding:1px"><span style="color:#94a3b8;font-size:10px">'+cv.toFixed(2)+'</span></td>';
                        html+='<td style="text-align:center;padding:1px"><span style="color:'+dc3+';font-size:9px;font-weight:bold">'+(diff3>0?'+':'')+diff3+'</span></td>';
                    });
                    html+='</tr>';
                }

                html+='</table>';

                // ===== 关键洞察：让球前后赔率变化量 =====
                if (jco.length>=3 && (rHcOdds.length>=3 || curHcJcOdds.length>=2)) {
                    html+='<div style="margin-top:6px;padding-top:4px;border-top:1px dashed #334155;font-size:9.5px">';
                    
                    // 案例的让球效应
                    if (rHcOdds.length>=3 && jco.length>=3) {
                        var hChg = rHcOdds[0]>0 ? ((rHcOdds[0]/jco[0]-1)*100).toFixed(0)+'%' : '-';
                        var aChg = rHcOdds[2]>0 ? ((rHcOdds[2]/jco[2]-1)*100).toFixed(0)+'%' : '-';
                        var dChg = rHcOdds[1]>0 ? ((rHcOdds[1]/jco[1]-1)*100).toFixed(0)+'%' : '-';

                        html+='<div style="display:inline-flex;gap:10px;margin-right:16px">';
                        html+='<span style="color:#64748b">案例让球效应('+ (revHc||'?') +'):</span>';
                        html+='<span style="color:#60a5fa">主↑'+hChg+'</span>';
                        html+='<span style="color:#fbbf24">平'+dChg+'</span>';
                        html+='<span style="color:#fca5a5">客↓'+aChg+'</span>';
                        html+='</div>';
                    }

                    // 当前比赛的让球效应
                    if (curHcJcOdds.length>=2 && curJcOdds.length>=3) {
                        var chChg = curHcJcOdds[0]>0 ? ((curHcJcOdds[0]/curJcOdds[0]-1)*100).toFixed(0)+'%' : '-';
                        var caChg = curHcJcOdds[2]>0 ? ((curHcJcOdds[2]/curJcOdds[2]-1)*100).toFixed(0)+'%' : '-';

                        html+='<div style="display:inline-flex;gap:10px">';
                        html+='<span style="color:#64748b">当前('+(baseHc||'?')+'):</span>';
                        html+='<span style="color:#60a5fa">主↑'+chChg+'</span>';
                        html+='<span style="color:#fca5a5">客↓'+caChg+'</span>';
                        html+='</div>';
                    }
                    html+='</div>';
                }

                // ===== 变向模式对比 =====
                var curJcPat='',curMcPat='';
                try {
                    var _chgFn=function(v){return v<-2?'D':v>2?'U':'N';};
                    var cJI=(_curRd.initial_odds&&_curRd.initial_odds.length>0)?_curRd.initial_odds[0].slice(0,3):[];
                    var cMI=(_curRd.initial_odds&&_curRd.initial_odds.length>2)?_curRd.initial_odds[2].slice(0,3):[];
                    if(cJI.length>=3) curJcPat=_chgFn(curJcOdds[0]-cJI[0])+_chgFn(curJcOdds[1]-cJI[1])+_chgFn(curJcOdds[2]-cJI[2]);
                    if(cMI.length>=3) curMcPat=_chgFn(curMacOdds[0]-cMI[0])+_chgFn(curMacOdds[1]-cMI[1])+_chgFn(curMacOdds[2]-cMI[2]);
                }catch(e){}

                var simJcPat=revFp.jc_pattern||'---', simMcPat=revFp.macao_pattern||'---';
                if(simJcPat!=='---'||simMcPat!=='---') {
                    html+='<div style="margin-top:5px;padding-top:4px;border-top:1px solid #1e293b;display:flex;align-items:center;gap:8px">';
                    html+='<span style="color:#6366f1;font-size:9.5px">变向:</span>';

                    var jPM=(curJcPat&&simJcPat&&curJcPat===simJcPat);
                    html+='<span style="background:'+(jPM?'#162d30':'#2d1616')+';color:'+(jPM?'#4ade80':'#fca5a5')+';padding:1px 6px;border-radius:3px;font-family:monospace;font-size:10px">'+simJcPat+'</span>';
                    if(curJcPat) html+='<span style="color:#475569;font-size:9px">'+curJcPat+'</span>';

                    html+='<span style="color:#334155">|</span>';

                    var mPM=(curMcPat&&simMcPat&&curMcPat===simMcPat);
                    html+='<span style="background:'+(mPM?'#162d30':'#2d1616')+';color:'+(mPM?'#4ade80':'#fca5a5')+';padding:1px 6px;border-radius:3px;font-family:monospace;font-size:10px">'+simMcPat+'</span>';
                    if(curMcPat) html+='<span style="color:#475569;font-size:9px">'+curMcPat+'</span>';

                    var pBoth=(jPM?1:0)+(mPM?1:0);
                    if(pBoth===2) html+='<span style="color:#22c55e;font-size:9px;font-weight:bold;margin-left:4px">✓一致</span>';
                    else if(pBoth===1) html+='<span style="color:#eab308;font-size:9px;margin-left:4px">部分</span>';
                    else html+='<span style="color:#ef4444;font-size:9px;margin-left:4px">⚠不同</span>';
                    html+='</div>';
                }

                // 近况对比
                var revHf=rev.home_form||'',revAf=rev.away_form||'',curHf=baseAna.home_form||'',curAf=baseAna.away_form||'';
                
                if (revHf || revAf) {
                    html += '<div style="margin-top:4px;padding-top:4px;border-top:1px solid #1e293b">';
                    html += '<div style="display:flex;gap:16px;font-size:10.5px">';
                    if (revHf && curHf) {
                        html += '<div><span style="color:#64748b">主近况:</span> ';
                        html += '<span style="color:#60a5fa;font-family:monospace">' + revHf + '</span>';
                        html += ' <span style="color:#334155">|</span> ';
                        html += '<span style="color:#94a3b8;font-family:monospace">' + curHf + '</span></div>';
                    }
                    if (revAf && curAf) {
                        html += '<div><span style="color:#64748b">客近况:</span> ';
                        html += '<span style="color:#a78bfa;font-family:monospace">' + revAf + '</span>';
                        html += ' <span style="color:#334155">|</span> ';
                        html += '<span style="color:#94a3b8;font-family:monospace">' + curAf + '</span></div>';
                    }
                    html += '</div></div>';
                }

                html += '</div>'; // end 对比模块容器
            
            // ════════════════════════════════════
            // ★ Phase 2b: 让球盘相似案例独立分析模块（调用新API）
            // ════════════════════════════════════
            var _hcDateFolder = res.date_folder || '';
            var _hcMatchId = res.match_id || '';
            if (_hcDateFolder && _hcMatchId && (res.raw_data && res.raw_data.handicap)) {
                try {
                    // 调用后端API获取让球盘相似案例
                    var hcSimRes = await api('/api/handicap-similar?match_id=' + encodeURIComponent(_hcMatchId) + '&date=' + encodeURIComponent(_hcDateFolder));
                    if (hcSimRes.success && hcSimRes.similar_cases && hcSimRes.similar_cases.length > 0) {
                        var hcs = hcSimRes.similar_cases;

})();