
const API = '';

async function api(path, options = {}) {
    const res = await fetch(API + path, options);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const text = await res.text();
    try { return JSON.parse(text); } 
    catch(e) { throw new Error('非JSON响应 (' + text.substring(0, 80) + ')'); }
}

// 当前选中的日期（服务端已预填）
let currentDate = '';

// 获取当前选中日期
function getSelectedDate() {
    return currentDate;
}

// 初始化日期选择（服务端已渲染按钮，只需设置currentDate）
function initDates() {
    const activeBtn = document.querySelector('.date-btn.active');
    if (activeBtn) {
        // 按钮文本格式: "4.08(11)" -> folder="4.08"
        const btnText = activeBtn.textContent.trim();
        const match = btnText.match(/^([\d.]+)\((\d+)\)$/);
        if (match) {
            currentDate = match[1];
        } else {
            currentDate = btnText.replace(/[()]/g, '').split(' ')[0];
        }
    }
    console.log('日期初始化完成, 选中:', currentDate);
}

// 选择日期按钮
function selectDate(folder, btnEl) {
    currentDate = folder;
    // 更新按钮样式
    document.querySelectorAll('.date-btn').forEach(b => b.classList.remove('active'));
    btnEl.classList.add('active');
    // 更新显示文本
    const countMatch = folder.match(/(.+)\((\d+)\)/);
    if (btnEl.textContent) {
        document.getElementById('selectedDate').textContent = btnEl.textContent.trim();
    }
}

// 加载比赛列表
async function loadMatches() {
    // 显示版本号
    try {
        const verRes = await api('/api/version');
        const versionEl = document.getElementById('versionInfo');
        if (versionEl && verRes.success) {
            versionEl.textContent = `[V${verRes.version}] | 构建: ${verRes.build_time}`;
        }
    } catch(e) {}
    
    const date = getSelectedDate();
    if (!date) { showStatus('请先选择日期！', 'error'); return; }
    showStatus(`正在加载 ${date} 的比赛列表...`, 'loading');
    
    const res = await api(`/api/matches?date=${encodeURIComponent(date)}`);
    if (!res.success) { showStatus(res.error, 'error'); return; }
    
    document.getElementById('matchInfo').textContent = `${date} 共 ${res.count} 场比赛`;
    
    let html = `<div class="table-container"><table>
        <thead><tr>
            <th>编号</th><th>联赛</th><th>对阵</th><th>比赛时间</th>
            <th>预测</th><th>置信度</th><th>排除</th>
            <th>比分</th>
            <th>操作</th>
        </tr></thead><tbody>`;
    
    res.data.forEach(m => {
        const predClass = (m.prediction||'').includes('主')?'tag-home':(m.prediction||'').includes('平')?'tag-draw':(m.prediction||'').includes('客')?'tag-away':'tag-watch';
        const exclStr = (m.exclusions||[]).map(e=>`<span class="exclusion-badge">${e==='home'?'主胜':e==='draw'?'平局':'客胜'}</span>`).join('');
        const fillCls = `fill-${m.confidence||1}`;
        
        // 比分显示逻辑
        let scoreHtml = '';
        if (m.score) {
            // 已有比分：显示比分 + 复盘按钮
            const resultClass = m.actual_result === 'home' ? 'color:#4ade80' : m.actual_result === 'draw' ? 'color:#facc15' : 'color:#fca5a5';
            scoreHtml = `<span style="font-weight:700;font-size:15px;${resultClass}">${m.score}</span>`;
        } else {
            // 无比分：显示输入框 + 保存按钮
            scoreHtml = `<div style="display:flex;align-items:center;gap:3px;">
                <input type="number" id="hs_${m.id}" placeholder="主" min="0" max="99" style="width:36px;padding:3px 4px;border-radius:5px;border:1px solid #475569;background:#0f172a;color:#e2e8f0;text-align:center;font-size:12px;">
                <span style="color:#64748b">:</span>
                <input type="number" id="as_${m.id}" placeholder="客" min="0" max="99" style="width:36px;padding:3px 4px;border-radius:5px;border:1px solid #475569;background:#0f172a;color:#e2e8f0;text-align:center;font-size:12px;">
                <button onclick="saveScore('${date}','${m.id}','${m.home}')" style="padding:3px 8px;border-radius:5px;border:1px solid #22c55e;background:#0f172a;color:#22c55e;cursor:pointer;font-size:11px;">✓</button>
            </div>`;
        }
        
        // 操作按钮
        let actionHtml = '';
        if (m.score) {
            // 有比分 → 显示复盘按钮
            actionHtml = `<button onclick="doReview('${date}','${m.id}')" style="padding:5px 14px;border-radius:6px;border:1px solid #a78bfa;background:#0f172a;color:#a78bfa;cursor:pointer;font-size:12px;">📝 复盘</button>`;
        }
        actionHtml += ` <button onclick="analyzeOne('${date}','${m.id}')" style="padding:5px 14px;border-radius:6px;border:1px solid #475569;background:#0f172a;color:#60a5fa;cursor:pointer;font-size:12px;">🔍 分析</button>`;
        
        html += `<tr>
            <td style="font-weight:600;color:#60a5fa">${m.id}</td>
            <td>${m.league}</td>
            <td>${m.home} vs <strong>${m.away}</strong></td>
            <td style="color:#94a3b8;font-size:12px">${m.time}</td>
            <td><span class="prediction-tag ${predClass}">${m.prediction||'-'}</span></td>
            <td><div class="confidence-bar"><div class="confidence-fill ${fillCls}" style="width:${(m.confidence||0)*20}%"></div></div>
            <span class="stars">${'★'.repeat(m.confidence||0)}</span></td>
            <td style="text-align:center;font-weight:700;color:${(m.n_exclusions||0)>=2?'#4ade80':(m.n_exclusions||0)>=1?'#60a5fa':'#94a3b8'}">${m.n_exclusions||0}<br><span style="font-size:10px;font-weight:400">${exclStr||''}</span></td>
            <td>${scoreHtml}</td>
            <td style="white-space:nowrap">${actionHtml}</td>
        </tr>`;
    });
    html += '</tbody></table></div>';
    document.getElementById('resultsArea').innerHTML = html;
    showStatus(`已加载 ${res.count} 场比赛（含分析结果）`, 'success');
}

// 保存比分
async function saveScore(date, id, homeTeam) {
    const hs = document.getElementById(`hs_${id}`);
    const as = document.getElementById(`as_${id}`);
    if (!hs || !as || hs.value === '' || as.value === '') {
        showStatus('请填写完整比分！', 'error'); return;
    }
    
    showStatus(`正在记录 ${id} 比分...`, 'loading');
    try {
        const res = await api('/api/score', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ match_id: id, date: date, home_score: hs.value, away_score: as.value })
        });
        if (!res.success) { showStatus(res.error, 'error'); return; }
        showStatus(`${id} 比分已记录：${homeTeam} ${res.data.score_str}`, 'success');
        // 刷新列表以显示比分
        loadMatches();
    } catch(e) { showStatus('保存失败: ' + e.message, 'error'); }
}

// 执行复盘
async function doReview(date, id) {
    if (!confirm(`确认对 ${id} 进行复盘？将自动生成经验总结日志。`)) return;
    showStatus(`正在生成 ${id} 复盘日志...`, 'loading');
    try {
        // 先从scores获取比分
        const scoresRes = await api('/api/scores');
        const scoreKey = date + '_' + id;
        const scoreData = (scoresRes.data || {})[scoreKey];
        
        if (!scoreData) {
            showStatus('未找到该场比赛的比分记录，请先填写比分', 'error'); return;
        }
        
        // 调用复盘API
        const res = await api_post('/api/review', { 
            match_id: id, 
            date: date,
            home_score: scoreData.home_score,
            away_score: scoreData.away_score
        });
        if (!res.success) { showStatus(res.error, 'error'); return; }
        
        const rev = res.review;
        alert(
            `📊 复盘报告：${rev.home_team} vs ${rev.away_team}\n` +
            `━━━━━━━━━━━━━━━━\n` +
            `📋 预测：${rev.prediction} (${rev.confidence}★)\n` +
            `🎯 实际：${rev.actual_score} (${rev.result_cn})\n` +
            `${rev.is_correct ? '✅ 命中！' : '❌ 未命中'}\n` +
            `━━━━━━━━━━━━━━━━\n\n` +
            rev.lessons.join('\n') + '\n\n' +
            `✅ 复盘日志已保存到文件`
        );
        showStatus(`${id} 复盘完成！${rev.is_correct?'命中':'未命中'}`, 'success');
    } catch(e) { showStatus('复盘失败: ' + e.message, 'error'); }
}

// POST请求辅助
async function api_post(path, data) {
    const res = await fetch(API + path, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    return res.json();
}

// 单场详细分析
async function analyzeOne(date, id) {
    showStatus(`正在分析 ${id}...`, 'loading');
    const res = await api(`/api/analyze?date=${encodeURIComponent(date)}&id=${encodeURIComponent(id)}`);
    if (!res.success) { showStatus(res.error, 'error'); return; }
    
    await renderDetail(res);
    showStatus(`${id} 分析完成`, 'success');
}

// 批量分析全部
async function batchAnalyze() {
    const date = getSelectedDate();
    if (!date) { showStatus('请先选择日期！', 'error'); return; }
    showStatus(`正在批量分析 ${date} 全部比赛...`, 'loading');
    
    const res = await api(`/api/batch?date=${encodeURIComponent(date)}`);
    if (!res.success) { showStatus(res.error, 'error'); return; }
    
    document.getElementById('matchInfo').textContent = `${date} 分析完成 (${res.count}场)`;
    
    // 统计
    let homeCount=0, drawCount=0, awayCount=0, watchCount=0;
    res.data.forEach(d => {
        if (d.prediction.includes('主')) homeCount++;
        else if (d.prediction.includes('平')) drawCount++;
        else if (d.prediction.includes('客')) awayCount++;
        else watchCount++;
    });
    
    let html = `<div style="margin-bottom:16px;display:flex;gap:12px;flex-wrap:wrap;">
        <div style="background:#1e293b;padding:10px 18px;border-radius:8px;border:1px solid #334155;font-size:13px;">
            📊 总计：<strong style="color:#fff">${res.count}</strong>场 |
            <span style="color:#4ade80">主${homeCount}</span> /
            <span style="color:#facc15">平${drawCount}</span> /
            <span style="color:#fca5a5">客${awayCount}</span> /
            <span style="color:#94a3b8">观望${watchCount}</span>
        </div>
    </div>`;
    
    html += `<div class="table-container"><table>
        <thead><tr>
            <th>编号</th><th>联赛</th><th>对阵</th>
            <th>预测</th><th>置信度</th><th>排除数</th><th>排除方向</th><th>警告</th>
            <th>详情</th>
        </tr></thead><tbody>`;
    
    res.data.forEach(d => {
        const predClass = d.prediction.includes('主')?'tag-home':d.prediction.includes('平')?'tag-draw':d.prediction.includes('客')?'tag-away':'tag-watch';
        const exclStr = (d.exclusions||[]).map(e=>`<span class="exclusion-badge">${e==='home'?'主胜':e==='draw'?'平局':'客胜'}</span>`).join('');
        const warnStr = (d.warnings||[]).map(w=>`<span class="warning-badge">⚠️${w}</span>`).join('');
        
        const fillCls = `fill-${d.confidence||1}`;
        html += `<tr>
            <td style="font-weight:600;color:#60a5fa">${d.id}</td>
            <td>${d.league}</td>
            <td>${d.home} vs <strong>${d.away}</strong></td>
            <td><span class="prediction-tag ${predClass}">${d.prediction}</span></td>
            <td><div class="confidence-bar"><div class="confidence-fill ${fillCls}" style="width:${(d.confidence||0)*20}%"></div></div>
            <span class="stars">${'★'.repeat(d.confidence||0)}</span></td>
            <td style="text-align:center;font-weight:700;color:${d.n_exclusions>=2?'#4ade80':d.n_exclusions>=1?'#60a5fa':'#94a3b8'}">${d.n_exclusions}</td>
            <td>${exclStr||'-'}</td>
            <td>${warnStr||'-'}</td>
            <td><button onclick="analyzeOne('${date}','${d.id}')" style="padding:4px 12px;border-radius:6px;border:1px solid #475569;background:#0f172a;color:#94a3b8;cursor:pointer;font-size:12px;">查看</button></td>
        </tr>`;
    });
    html += '</tbody></table></div>';
    document.getElementById('resultsArea').innerHTML = html;
    showStatus(`${res.count} 场分析完成`, 'success');
}

// 渲染详情面板
async function renderDetail(res) {
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
                        var hst = hcSimRes.stats || {};
                        var hcur = hcSimRes.current || {};
                        
                        html += '<div style="margin-top:8px;background:linear-gradient(135deg,#1a0f0a,#0f1419);border-radius:8px;padding:10px 12px;border:1px solid #4a3520">';
                        
                        // 标题行
                        html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">';
                        html += '<span style="font-size:11.5px;color:#f59e0b;font-weight:bold">⚖️ 让球盘相似案例</span>';
                        if (hcur.handicap) {
                            html += '<span style="background:#3d2a08;color:#fbbf24;padding:1px 7px;border-radius:4px;font-size:10px;font-family:monospace">当前盘口:' + hcur.handicap + '</span>';
                        }
                        html += '</div>';
                        
                        // 汇总统计条
                        if (hst.total > 0) {
                            html += '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:6px;padding:5px 8px;background:rgba(0,0,0,0.25);border-radius:5px;font-size:9.5px;color:#94a3b8">';
                            html += '<span>📊 <b style="color:#e2e8f0">' + hst.total + '</b> 条相似</span>';
                            if (hst.correct_rate) html += '<span style="color:#4ade80">命中:' + hst.correct_rate + '</span>';
                            
                            // 预测方向分布
                            if (hst.pred_distribution) {
                                Object.keys(hst.pred_distribution).forEach(function(pk) {
                                    var pc = hst.pred_distribution[pk];
                                    var pcolor = pk.indexOf('主')>=0 ? '#60a5fa' : pk.indexOf('客')>=0 ? '#fca5a5' : '#fbbf24';
                                    html += '<span style="color:'+pcolor+'">' + pk + ':' + pc + '票</span>';
                                });
                            }
                            
                            // 实际结果分布
                            if (hst.result_distribution) {
                                html += '<span style="color:#334155">|</span>';
                                Object.keys(hst.result_distribution).forEach(function(rk) {
                                    var rc = hst.result_distribution[rk];
                                    var rcolor = rk.indexOf('主')>=0 ? '#60a5fa' : rk.indexOf('客')>=0 ? '#fca5a5' : '#fbbf24';
                                    html += '<span style="color:'+rcolor+'">' + rk + '×' + rc + '</span>';
                                });
                            }
                            html += '</div>';
                        }
                        
                        // 每条相似案例卡片
                        for (var ci = 0; ci < hcs.length; ci++) {
                            var c = hcs[ci];
                            var isHit = c.is_correct;
                            var cardBorder = isHit ? '1px solid #22c55e40' : '1px solid #ef444430';
                            var cardBg = isHit ? 'rgba(34,197,94,0.04)' : 'rgba(239,68,68,0.03)';
                            
                            html += '<div style="margin-top:5px;padding:6px 8px;border-radius:5px;background:' + cardBg + ';border-left:3px solid ' + (isHit ? '#22c55e' : '#ef444450') + ';' + cardBorder + '">';
                            
                            // 案例标题
                            html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px">';
                            var caseTitle = c.home_team + ' vs ' + c.away_team;
                            html += '<span style="font-weight:600;color:#e2e8f0;font-size:11px">' + caseTitle + '</span>';
                            html += '<div style="display:flex;gap:5px;align-items:center">';
                            // 相似度分数
                            html += '<span style="background:#2a1f0e;color:#f59e0b;padding:1px 6px;border-radius:3px;font-size:9.5px;font-weight:bold">' + c.score + '分</span>';
                            // 命中/失败标记
                            if (isHit) {
                                html += '<span style="background:#16653430;color:#4ade80;padding:1px 5px;border-radius:3px;font-size:9px">✓命中</span>';
                            } else {
                                html += '<span style="#501a1a30;color:#fca5a5;padding:1px 5px;border-radius:3px;font-size:9px">✗未中</span>';
                            }
                            html += '</div></div>';
                            
                            // 匹配原因标签
                            if (c.match_reasons && c.match_reasons.length > 0) {
                                html += '<div style="margin-bottom:3px;display:flex;flex-wrap:wrap;gap:3px">';
                                for (var ri=0;ri<c.match_reasons.length;ri++) {
                                    html += '<span style="background:#1e293b;color:#94a3b8;padding:1px 5px;border-radius:3px;font-size:9px">' + c.match_reasons[ri] + '</span>';
                                }
                                html += '</div>';
                            }
                            
                            // 让球赔率对比表（紧凑版）
                            if (c.case_hc_odds && c.case_hc_odds.length >= 2 || hcur.hc_odds && hcur.hc_odds.filter(function(x){return x>0}).length >= 2) {
                                html += '<table style="width:100%;border-collapse:collapse;font-size:10px;margin:2px 0">';
                                html += '<tr><td style="padding:1px;color:#64748b;width:40px">让球赔率</td>';
                                ['home','draw','away'].forEach(function(hi, hx) {
                                    html += '<td style="text-align:center;width:45px;padding:1px">';
                                    var sv = c.case_hc_odds && c.case_hc_odds[hx] ? c.case_hc_odds[hx].toFixed(2) : '-';
                                    var cv = hcur.hc_odds && hcur.hc_odds[hx] ? hcur.hc_odds[hx].toFixed(2) : null;
                                    html += '<strong style="color:#fff;font-size:10.5px">' + sv + '</strong>';
                                    if (cv) html += '<br><span style="color:#fbbf24;font-size:8.5px">' + cv + '</span>';
                                    html += '</td>';
                                });
                                html += '</tr></table>';
                            }
                            
                            // 基本面对比 + 结果参考（一行紧凑显示）
                            html += '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:3px;padding-top:3px;border-top:1px solid #1e293b;font-size:9.5px">';
                            
                            // 近况对比
                            if (c.home_form) {
                                html += '<div><span style="color:#60a5fa">主近况:</span> <span style="font-family:monospace;color:#cbd5e1">' + c.home_form + '</span>';
                                if (hcur.home_form) html += ' <span style="color:#334155">| 当前 </span><span style="font-family:monospace;color:#94a3b8">' + hcur.home_form + '</span>';
                                html += '</div>';
                            }
                            if (c.away_form) {
                                html += '<div><span style="color:#a78bfa">客近况:</span> <span style="font-family:monospace;color:#cbd5e1">' + c.away_form + '</span>';
                                if (hcur.away_form) html += ' <span style="color:#334155">| 当前 </span><span style="font-family:monospace;color:#94a3b8">' + hcur.away_form + '</span>';
                                html += '</div>';
                            }
                            html += '</div>';
                            
                            // 推理结论行
                            html += '<div style="margin-top:3px;display:flex;align-items:center;gap:6px;font-size:9.5px">';
                            html += '<span style="color:#64748b">预测:</span>';
                            html += '<span style="color:#60a5fa;font-weight:600">' + (c.prediction || '-') + '</span>';
                            if (c.confidence) html += '<span style="color:#fbbf24">★' + c.confidence + '</span>';
                            if (c.actual_score) {
                                html += '<span style="color:#334155">→ 实际:</span>';
                                html += '<span style="color:' + (isHit ? '#4ade80' : '#fca5a5') + ';font-weight:600">' + c.actual_score;
                                if (c.result_cn) html += '(' + c.result_cn + ')';
                                html += '</span>';
                            }
                            
                            // 自动生成简短推理
                            var reasoning_parts = [];
                            if (c.score >= 65) reasoning_parts.push('高度相似');
                            else if (c.score >= 55) reasoning_parts.push('较接近');
                            else reasoning_parts.push('部分匹配');
                            
                            if (isHit) reasoning_parts.push('该案例命中可作正向参考');
                            else reasoning_parts.push('该案例未中需谨慎参考');
                            
                            if (c.exclusions && c.exclusions.length >= 2) reasoning_parts.push('当时排除明确');
                            
                            html += '</div>';
                            
                            // 推理文字
                            html += '<div style="margin-top:2px;color:#6366f1;font-size:9px;font-style:italic">💡 ' + reasoning_parts.join(' · ') + '</div>';
                            
                            html += '</div>'; // end case card
                        }
                        
                        // 综合推理结论
                        if (hcs.length >= 2) {
                            html += '<div style="margin-top:6px;padding:6px 10px;background:#1a1333;border:1px solid #3730a3;border-radius:5px">';
                            html += '<div style="font-size:10px;color:#a78bfa;font-weight:600;margin-bottom:3px">📋 综合推理</div>';
                            
                            // 综合判断逻辑
                            var hitCount = hcs.filter(function(x){return x.is_correct}).length;
                            var totalC = hcs.length;
                            var hitRate = Math.round(hitCount / totalC * 100);
                            
                            // 找出最倾向的方向
                            var dirCounts = {home:0, draw:0, away:0};
                            var resDirs = [];
                            hcs.forEach(function(cc) {
                                var rs = cc.actual_score;
                                if (!rs) return;
                                var parts = rs.match(/(\d+)-(\d+)/);
                                if (parts) {
                                    var hh = parseInt(parts[1]), aa = parseInt(parts[2]);
                                    if (hh > aa) resDirs.push('home');
                                    else if (hh < aa) resDirs.push('away');
                                    else resDirs.push('draw');
                                }
                            });
                            
                            var rcHome = resDirs.filter(function(d){return d==='home'}).length;
                            var rcDraw = resDirs.filter(function(d){return d==='draw'}).length;
                            var rcAway = resDirs.filter(function(d){return d==='away'}).length;
                            var maxR = Math.max(rcHome, rcDraw, rcAway);
                            
                            // 生成综合推理文字
                            var finalReasons = [];
                            finalReasons.push(totalC + '条案例中' + hitCount + '条命中(' + hitRate + '%)');
                            
                            var topScore = hcs[0].score;
                            if (topScore >= 70) finalReasons.push('最高相似度' + topScore + '分，特征高度吻合');
                            else if (topScore >= 55) finalReasons.push('最高相似度' + topScore + '分，有一定参考价值');
                            
                            if (maxR > 0) {
                                var favDir = '', favCount = 0;
                                if (rcHome === maxR && rcHome > 0) { favDir = '主胜'; favCount = rcHome; }
                                else if (rcAway === maxR && rcAway > 0) { favDir = '客胜'; favCount = rcAway; }
                                else if (rcDraw === maxR && rcDraw > 0) { favDir = '平局'; favCount = rcDraw; }
                                
                                if (favDir && favCount >= 2) {
                                    finalReasons.push(favDir + '出线' + favCount + '/' + totalC + '次最多');
                                } else if (totalC >= 3 && maxR <= 1) {
                                    finalReasons.push('结果分散，无绝对主流');
                                }
                            }
                            
                            // 最终建议
                            var adviceText = '';
                            var adviceColor = '#94a3b8';
                            if (hitRate >= 70 && totalC >= 3 && maxR >= 2) {
                                adviceText = '✅ 历史规律较一致，可重点参考主流方向';
                                adviceColor = '#4ade80';
                            } else if (hitRate >= 50 && totalC >= 3) {
                                adviceText = '⚠️ 规律中等，建议结合基本面综合判断';
                                adviceColor = '#fbbf24';
                            } else if (hitRate < 50 || totalC < 3) {
                                adviceText = '📊 样本不足或规律不稳定，仅供参考';
                                adviceColor = '#64748b';
                            } else if (maxR <= 1 && totalC >= 3) {
                                adviceText = '🔄 结果分散，各方向均有出现可能';
                                adviceColor = '#a78bfa';
                            }
                            
                            html += '<div style="color:#cbd5e1;font-size:10px;line-height:1.6">';
                            html += finalReasons.join('；') + '。';
                            html += '</div>';
                            html += '<div style="margin-top:3px;color:' + adviceColor + ';font-size:10px;font-weight:600">' + adviceText + '</div>';
                            
                            html += '</div>'; // end 综合推理
                        }
                        
                        html += '</div>'; // end 让球盘相似案例容器
                    } else if (hcSimRes.success && (!hcSimRes.similar_cases || hcSimRes.similar_cases.length === 0)) {
                        // 无相似案例时显示提示
                        html += '<div style="margin-top:8px;padding:6px 10px;background:#1a1a1a20;border-radius:5px;border:1px solid #1e293b">';
                        html += '<span style="color:#64748b;font-size:10px">⚖️ 让球盘相似案例：暂无足够相似的复盘记录（盘口=' + (hcur.handicap||'?') + '）</span>';
                        html += '</div>';
                    }
                } catch(e) {
                    console.error('加载让球盘相似案例出错:', e);
                }
            }

            if (reasonTags) {
                html += '<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:2px">' + reasonTags + '</div>';
            }

            // 经验教训
            if (rev.lessons && rev.lessons.length > 0) {
                html += '<div style="margin-top:5px">';
                var lessonsToShow = rev.lessons.slice(0, 3);
                for (var li = 0; li < lessonsToShow.length; li++) {
                    var l = lessonsToShow[li];
                    var lc = '#fbbf24';
                    if (l.indexOf('✅') >= 0) lc = '#4ade80';
                    else if (l.indexOf('❌') >= 0) lc = '#f87171';
                    html += '<div style="font-size:11px;color:' + lc + ';margin-top:2px">💡 ' + l + '</div>';
                }
                html += '</div>';
            }

            html += '</div></div>';
        });
        
        // 追加统计建议
        if (suggestion) {
            html += suggestion;
        }
        
        html += '</div>';
        
        // ========================================
        // 🧊 相似冷门模式参考
        // ========================================
        // 只显示有意义的匹配（≥20分）
        const simUpsets = (res.similar_upsets || []).filter(function(u) { return u._match_score >= 20; });
        const upsetsStats = res.upsets_stats || {};
        
        if (simUpsets.length > 0) {
            // 计算最高相似度决定警告等级
            var maxScore = Math.max(...simUpsets.map(function(u){return u._match_score;}));
            var warnLevel = maxScore >= 50 ? 'danger' : (maxScore >= 35 ? 'warning' : 'info');
            var levelCfg = {
                danger: {title:'🚨 冷门模式警告', color:'#f87171', bg:'#1f1218', border:'#3d1a1e', advice:'强烈建议：降低信心/控制仓位或直接观望！'},
                warning: {title:'⚠️ 相似冷门参考', color:'#fbbf24', bg:'#2a2008', border:'#4a3514', advice:'建议：适当降低投注信心，注意被排除方向。'},
                info:   {title:'📋 历史冷门参考（弱相关）', color:'#60a5fa', bg:'#0c1525', border:'#1a2d45', advice:'仅供参考：与少量历史冷门有部分特征重合，但相关性不高。'}
            };
            var lc = levelCfg[warnLevel];
            
            html += `
        <div class="section">
            <div class="section-title"><span style="color:${lc.color};font-size:16px">${lc.title}</span>（${simUpsets.length}条相似 · 最高${maxScore}分）
            </div>
            <div style="font-size:11px;color:${lc.color};margin-bottom:8px;line-height:1.6">
                ${warnLevel === 'danger' ? '<b>本场与多条历史爆冷案例高度相似！需格外警惕。</b>' : '以下历史比赛与本场有部分相似特征。'}
                &nbsp;|&nbsp; 📊 冷门库共 ${upsetsStats.total || 0} 条记录
            </div>`;
            
            simUpsets.forEach(function(u, ui) {
                var uType = u.upset_type || 'unknown';
                var typeColors = {
                    'silent': {bg:'#1e3a5f', border:'#3b82f6', text:'#93c5fd', icon:'🔇'},
                    'reverse_cover': {bg:'#3f2a2a', border:'#ef4444', text:'#fca5a5', icon:'🔄'},
                    'heat_trap': {bg:'#3f3510', border:'#f59e0b', text:'#fcd34d', icon:'🔥'},
                    'unknown': {bg:'#2d2d3a', border:'#6b7280', text:'#9ca3af', icon:'❓'}
                };
                var tc = typeColors[uType] || typeColors['unknown'];
                var dirCn = {home:'主胜', draw:'平局', away:'客胜'}[u.actual_result] || '?';
                
                html += `
            <div style="margin-bottom:10px;padding:10px;background:${tc.bg};border:1px solid ${tc.border};border-radius:8px">
                <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:4px;margin-bottom:6px">
                    <div style="display:flex;align-items:center;gap:6px">
                        <b style="font-size:13px;color:#e2e8f0">${u.home_team} vs ${u.away_team}</b>
                        <span style="background:#2a1518;color:${tc.text};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">${u.actual_score || '?'}</span>
                        <span style="background:${tc.border}33;color:${tc.text};padding:2px 7px;border-radius:4px;font-size:11px">${tc.icon} ${u.upset_type_cn || ''}</span>
                    </div>
                    <span style="font-size:10px;color:#64748b">相似度:<b style="color:${u._match_score>=40?'#f87171':u._match_score>=25?'#fbbf24':'#94a3b8'}">${u._match_score}</b></span>
                </div>
                <div style="font-size:11px;color:#94a3b8;margin-bottom:4px">
                    ${u.league || ''} | 预测<u>${u.prediction}</u> → 实际<b style="color:#f87171">${dirCn}</b>
                    | 置信度:${u.confidence}★ | 心水:${u.macao_tip || '-'}
                    | 爆冷赔率:${u.upset_odds || '?'}
                </div>`;
                
                if (u._match_reasons && u._match_reasons.length > 0) {
                    html += '<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:2px">';
                    for (var ri=0; ri<u._match_reasons.length && ri<4; ri++) {
                        html += '<span style="font-size:10px;background:#2a1518;color:#fca5a5;padding:1px 6px;border-radius:3px;display:inline-block">' + u._match_reasons[ri] + '</span>';
                    }
                    html += '</div>';
                }
                
                html += '</div>';
            });
            
            // 冷门模式总结建议（动态等级）
            var adviceText = {
                danger: '本场与多条历史冷门高度相似（≥50分）！赔率+基本面特征高度吻合。强烈建议跳过或极小仓位试探。',
                warning: '本场与历史冷门有较明显相似（35~49分）。建议降低投注信心，控制仓位，留意被排除方向。',
                info:   '与少量历史冷门有部分特征重合（20~34分）。仅供参考，不单独作为决策依据。'
            };
            html += `
            <div style="margin-top:10px;padding:10px 14px;background:${lc.bg};border:1px solid ${lc.border};border-radius:8px">
                <span style="color:${lc.color};font-weight:bold;font-size:13px">${warnLevel === 'danger' ? '⚠️ 警告' : (warnLevel === 'warning' ? '💡 注意' : '📌 参考')}：${adviceText[warnLevel]}</span>
            </div>`;
            
            html += '</div>';
        }
        
        // ========================================
        // ⚡ 二次分析 · 历史验证（三大模块）
        // ========================================
        
        // --- ① 集体投票模块（宽松版：包含反向案例） ---
        var voteHtml = '';
        var predVotes = {'主胜':0, '平局':0, '客胜':0, '观望':0};
        var oppVotes = {'主胜':0, '平局':0, '客胜':0, '观望':0};  // 反向案例票数
        var excOverlap = {'home':0, 'draw':0, 'away':0};
        var correctByPred = {'主胜':{'hit':0,'total':0}, '平局':{'hit':0,'total':0}, '客胜':{'hit':0,'total':0}, '观望':{'hit':0,'total':0}};
        
        simReviews.forEach(function(r) {
            var p = (r.prediction || '').replace(/ /g, '');
            var isOpp = r.is_opposite;  // 反向案例标记
            if (p.indexOf('主胜') >= 0) { 
                predVotes['主胜']++; if(isOpp) oppVotes['主胜']++;
                correctByPred['主胜']['total']++; if(r.is_correct) correctByPred['主胜']['hit']++; 
            }
            else if (p.indexOf('平局') >= 0) { 
                predVotes['平局']++; if(isOpp) oppVotes['平局']++;
                correctByPred['平局']['total']++; if(r.is_correct) correctByPred['平局']['hit']++; 
            }
            else if (p.indexOf('客胜') >= 0) { 
                predVotes['客胜']++; if(isOpp) oppVotes['客胜']++;
                correctByPred['客胜']['total']++; if(r.is_correct) correctByPred['客胜']['hit']++; 
            }
            else { predVotes['观望']++; if(isOpp) oppVotes['观望']++; }
            
            (r.exclusions || []).forEach(function(e) {
                if (excOverlap[e] !== undefined) excOverlap[e]++;
            });
        });
        
        // 统计反向案例总数
        var totalSame = simReviews.length;
        var totalOpp = Object.values(oppVotes).reduce(function(a,b){return a+b;}, 0);
        var totalAll = simReviews.length;
        
        // 找出投票最多的方向
        var maxVote = 0, topVoteDir = '';
        Object.keys(predVotes).forEach(function(k) { if(predVotes[k] > maxVote) { maxVote = predVotes[k]; topVoteDir = k; }});
        
        // 找出排除重叠最高的方向
        var maxExc = 0, topExcDir = '';
        Object.keys(excOverlap).forEach(function(k) { if(excOverlap[k] > maxExc) { maxExc = excOverlap[k]; topExcDir = k; }});
        
        // 当前基础预测
        var basePred = (res.analysis || {}).final_prediction || res.final_prediction || '';
        var baseConf = (res.analysis || {}).confidence || res.confidence || 0;
        
        // 投票结论（宽松版：考虑反向案例）
        var voteVerdict = '', voteVerdictColor = '#fbbf24';
        var sameDirVotes = predVotes[topVoteDir] - (oppVotes[topVoteDir]||0);  // 同向票数
        var oppDirVotes = oppVotes[topVoteDir] || 0;  // 反向票数
        
        if (basePred.indexOf(topVoteDir) >= 0 && maxVote >= Math.ceil(totalAll / 2)) {
            if (totalOpp > 0) {
                voteVerdict = '✅ 历史多数支持「' + topVoteDir + '」（同向' + sameDirVotes + '/' + totalAll + '，含' + totalOpp + '条反向对比）';
            } else {
                voteVerdict = '✅ 历史多数案例支持你的方向（' + maxVote + '/' + totalAll + '票）';
            }
            voteVerdictColor = '#4ade80';
        } else if (topVoteDir && !basePred.includes(topVoteDir) && maxVote >= 2) {
            if (oppDirVotes >= maxVote) {
                voteVerdict = '⚠️ 反向案例倾向「' + topVoteDir + '」（' + oppDirVotes + '票），高度相似但结果相反，需警惕！';
            } else {
                voteVerdict = '⚠️ 历史案例更倾向「' + topVoteDir + '」（' + maxVote + '票），与你的预测不同';
            }
            voteVerdictColor = '#f87171';
        } else {
            voteVerdict = '📊 方向分散，无绝对多数' + (totalOpp > 0 ? '（含' + totalOpp + '条反向）' : '');
            voteVerdictColor = '#fbbf24';
        }
        
        // 排除重叠描述
        var excNames = {home:'主', draw:'平', away:'客'};
        var excText = [];
        if (excOverlap.home > 0 && excOverlap.home === simReviews.length) excText.push('全排除主');
        if (excOverlap.draw > 0 && excOverlap.draw === simReviews.length) excText.push('全排除平');
        if (excOverlap.away > 0 && excOverlap.away === simReviews.length) excText.push('全排除客');
        var excSummary = excText.length > 0 ? excText.join('、') : ('排除较分散：主'+(excOverlap.home||0)+'·平'+(excOverlap.draw||0)+'·客'+(excOverlap.away||0));
        
        voteHtml += '<div class="section"><div class="section-title"><span class="icon icon-green">📊</span> 集体投票 — 相似案例统计（' + totalAll + '条' + (totalOpp > 0 ? ' · 含' + totalOpp + '条反向对比' : '') + '）</div>';
        voteHtml += '<div style="background:#0c1222;border-radius:10px;padding:14px;border:1px solid #1e293b">';
        
        // 方向分布条（区分同向/反向）
        voteHtml += '<div style="margin-bottom:12px"><div style="font-size:11px;color:#94a3b8;margin-bottom:5px;font-weight:600">📌 预测方向分布 <span style="color:#64748b;font-weight:normal">■ 同向 / ▣ 反向对比</span></div><div style="display:flex;gap:4px;height:28px">';
        var dirColors = {'主胜':'#4ade80', '平局':'#fbbf24', '客胜':'#fca5a5', '观望':'#94a3b8'};
        ['主胜','平局','客胜','观望'].forEach(function(d) {
            var sameV = predVotes[d] - (oppVotes[d]||0);
            var oppV = oppVotes[d] || 0;
            var hitInfo = correctByPred[d];
            var rate = hitInfo.total > 0 ? Math.round(hitInfo.hit/hitInfo.total*100) : 0;
            var totalV = predVotes[d];
            if (totalV > 0) {
                voteHtml += '<div style="flex:'+totalV+';min-width:30px;background:' + dirColors[d] + '22;border-radius:4px;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden;border:' + (oppV > 0 ? '1px dashed ' + dirColors[d] + '66' : 'none') + '">';
                voteHtml += '<span style="font-size:11px;font-weight:bold;color:#fff;z-index:1;text-shadow:0 1px 2px #0008">' + d.slice(0,1) + '(' + sameV;
                if (oppV > 0) voteHtml += '+' + oppV + '反';
                voteHtml += ')</span>';
                voteHtml += '<div style="position:absolute;bottom:0;left:0;width:100%;height:' + (100-rate) + '%;background:#0008"></div></div>';
            }
        });
        voteHtml += '</div></div>';
        
        // 排除重叠
        voteHtml += '<div style="margin-bottom:12px"><div style="font-size:11px;color:#94a3b8;margin-bottom:5px;font-weight:600">🚫 排除方向重叠度</div>';
        voteHtml += '<div style="display:flex;gap:12px;flex-wrap:wrap">';
        ['home','draw','away'].forEach(function(dk) {
            var v = excOverlap[dk] || 0;
            var isFull = v === totalAll && totalAll > 0;
            var bg = isFull ? 'rgba(239,68,68,0.15)' : 'rgba(51,65,85,0.5)';
            var border = isFull ? '1px solid #ef4444' : '1px solid #334155';
            var color = isFull ? '#f87171' : '#94a3b8';
            voteHtml += '<div style="padding:6px 16px;border-radius:20px;background:' + bg + ';border:' + border + ';text-align:center">';
            voteHtml += '<div style="font-size:11px;color:' + color + ';font-weight:bold">' + excNames[dk] + '</div>';
            voteHtml += '<div style="font-size:13px;color:#fff;font-weight:bold;margin-top:1px">' + v + '/' + totalAll + (isFull ? ' ✓' : '') + '</div></div>';
        });
        voteHtml += '</div><div style="font-size:10.5px;color:#64748b;margin-top:4px">→ ' + excSummary + '</div></div>';
        
        // 投票结论
        voteHtml += '<div style="padding:10px 12px;background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.25);border-radius:8px;text-align:center">';
        voteHtml += '<div style="font-size:13px;color:' + voteVerdictColor + ';font-weight:bold">' + voteVerdict + '</div></div>';
        voteHtml += '</div></div>';
        html += voteHtml;
        
        // ================================================
        // 🔥 二次分析核心：三方向独立排除引擎 v2.0
        // ================================================
        // 核心理念：不对原预测打分，而是对 主/平/客 三个方向
        // 分别判断"它为什么不该出"，给出排除置信度。
        // 排除掉的方向越多，剩余方向越可靠。
        
        var _an = res.analysis || {};
        var signals = _an.signals || [];
        var exclusions_now = _an.exclusions || [];
        var match_type = _an.match_type || '';
        var macaoTip = _an.macao_tip || '';
        var formDiff = _an.form_diff || 0;
        var odds_real = {};
        // ★ 关键：提取30家公司全量赔率，用于R1绝对值判断
        var allRealOdds = {home:[], draw:[], away:[]};
        var maxOdds = {home: 0, draw: 0, away: 0};
        
        // ★★★ 必须在try块之前定义eng对象！★★★
        // ---- 排除引擎数据结构 ----
        // score: 正=保留证据强, 负=排除证据强 (-100 ~ +100)
        // status: 'keep' | 'weak_exclude' | 'strong_exclude' | 'unknown'
        var eng = {
            home: { name:'主胜', score:0, evs:[], color:'#4ade80' },
            draw: { name:'平局', score:0, evs:[], color:'#fbbf24' },
            away: { name:'客胜', score:0, evs:[], color:'#fca5a5' }
        };
        
        var jcReal = odds_real.jc_real || [];
        var jcInit = odds_real.jc_init || [];
        
        try { 
            // ★ V4关键修复：res.raw_data可能已经是对象
            var _rd = (typeof res.raw_data === 'string') ? JSON.parse(res.raw_data || '{}') : (res.raw_data || {});
            
            // 提取竞彩/澳门赔率（index 0=竞彩官方, index 1=威廉希尔, index 2=澳门）
            if (_rd.initial_odds && _rd.initial_odds.length > 0) odds_real.jc_init = _rd.initial_odds[0].slice(0,3);
            if (_rd.realtime_odds && _rd.realtime_odds.length > 0) odds_real.jc_real = _rd.realtime_odds[0].slice(0,3);
            if (_rd.initial_odds && _rd.initial_odds.length > 2) odds_real.mac_init = _rd.initial_odds[2].slice(0,3);
            if (_rd.realtime_odds && _rd.realtime_odds.length > 2) odds_real.mac_real = _rd.realtime_odds[2].slice(0,3);
            
            // 提取30家公司全部即时赔率
            if (_rd.realtime_odds && Array.isArray(_rd.realtime_odds) && _rd.realtime_odds.length > 0) {
                for(var ri=0; ri<_rd.realtime_odds.length; ri++) {
                    var row = _rd.realtime_odds[ri];
                    if(Array.isArray(row) && row.length>=3) {
                        var h=Number(row[0]), d=Number(row[1]), a=Number(row[2]);
                        if(h>0) allRealOdds.home.push(h);
                        if(d>0) allRealOdds.draw.push(d);
                        if(a>0) allRealOdds.away.push(a);
                    }
                }
                maxOdds.home = allRealOdds.home.length ? Math.max.apply(null, allRealOdds.home) : 0;
                maxOdds.draw = allRealOdds.draw.length ? Math.max.apply(null, allRealOdds.draw) : 0;
                maxOdds.away = allRealOdds.away.length ? Math.max.apply(null, allRealOdds.away) : 0;
            }
            
            // ★★★ 更新jcReal/jcInit（前面已经提取过）
            jcReal = odds_real.jc_real || [];
            jcInit = odds_real.jc_init || [];
            
            // ════════════════════════════════════
            // 【R8-B】澳门推荐和局+和局赔率升的反向冷门检测（2026-04-12新增）
            // ════════════════════════════════════
            var _tip = (_rd && _rd.macao_tip) ? _rd.macao_tip : '';
            console.log('[DEBUG R8-B] _tip=', _tip, 'jcInit=', jcInit, 'jcReal=', jcReal);
            
            if (jcInit.length === 3 && jcReal.length === 3) {
                var drawOddsNow = jcReal[1];
                var drawOddsInit = jcInit[1];
                console.log('[DEBUG R8-B] drawOddsNow=', drawOddsNow, 'drawOddsInit=', drawOddsInit);
                
                if (drawOddsInit > 0) {
                    var drawChgPct = (drawOddsNow - drawOddsInit) / drawOddsInit * 100;
                    var homeChgPct = (jcReal[0] - jcInit[0]) / jcInit[0] * 100;
                    var awayChgPct = (jcReal[2] - jcInit[2]) / jcInit[2] * 100;
                    console.log('[DEBUG R8-B] drawChgPct=', drawChgPct.toFixed(2), 'homeChgPct=', homeChgPct.toFixed(2), 'awayChgPct=', awayChgPct.toFixed(2));
                    
                    // 条件：澳门推荐和局 + 和局赔率≥3.3 + 和局赔率上升/基本不变 + 客胜/主胜在降赔
                    var macaoRecommendsDraw = (_tip && (_tip.indexOf('和')>=0 || _tip.indexOf('平')>=0 || _tip.indexOf('分')>=0));
                    var drawRising = (drawChgPct >= 0);
                    var drawHighEnough = (drawOddsNow >= 3.3);
                    var awayDropping = (awayChgPct < -2);
                    var homeDropping = (homeChgPct < -2);
                    console.log('[DEBUG R8-B] macaoRecommendsDraw=', macaoRecommendsDraw, 'drawRising=', drawRising, 'drawHighEnough=', drawHighEnough, 'awayDropping=', awayDropping, 'homeDropping=', homeDropping);
                    
                    if (macaoRecommendsDraw && drawRising && drawHighEnough && (awayDropping || homeDropping)) {
                        var r8bScore = 0;
                        var r8bReasons = [];
                        r8bScore += 20; r8bReasons.push('澳门推荐和局');
                        if (drawChgPct >= 3) { r8bScore += 25; r8bReasons.push('和局赔率升'+drawChgPct.toFixed(1)+'%'); }
                        else if (drawChgPct >= 0) { r8bScore += 15; r8bReasons.push('和局赔率基本不变'); }
                        if (awayDropping) { r8bScore += 20; r8bReasons.push('客胜降赔'+awayChgPct.toFixed(1)+'%'); }
                        if (homeDropping) { r8bScore += 15; r8bReasons.push('主胜降赔'+homeChgPct.toFixed(1)+'%'); }
                        if (drawOddsNow >= 3.5) { r8bScore += 15; r8bReasons.push('和局赔率'+drawOddsNow+'够高'); }
                        
                        // 保存R8-B结果
                        eng._r8bScore = r8bScore;
                        eng._r8bReasons = r8bReasons;
                        eng._r8bDrawOdds = drawOddsNow;
                        console.log('[DEBUG R8-B] ★触发！r8bScore=', r8bScore, 'reasons=', r8bReasons);
                    } else {
                        console.log('[DEBUG R8-B] 条件不满足，未触发');
                    }
                }
            }
        } catch(e) { console.log('[DEBUG R8-B] Error:', e); }
        
        console.log('[DEBUG R8-B] eng._r8bScore=', eng._r8bScore);
        
        function addEv(dir, delta, text, rule) {
            eng[dir].score += delta;
            eng[dir].evs.push({d:delta, t:text, r:rule});
        }
        
        function dirOfTip(tip) {
            if (!tip) return null;
            if (tip.indexOf('主')>=0 && tip.indexOf('客')<0) return 'home';
            if (tip.indexOf('平')>=0 || tip.indexOf('和')>=0) return 'draw';
            if (tip.indexOf('客')>=0) return 'away';
            return null;
        }
        function tipOdds() {
            if (!macaoTip || jcReal.length<3) return 0;
            var di = dirOfTip(macaoTip);
            return di!==null ? jcReal[{home:0,draw:1,away:2}[di]] : 0;
        }
        
        // ════════════════════════════════════
        // 规则集：每条规则对特定方向加减分
        // ════════════════════════════════════
        
        // 【R1】赔率绝对值排除（最强信号）
        // ★ V2修复：用30家公司最大赔率(maxOdds)判断，而非仅竞彩一家(jcReal)
        // 原因：竞彩官方可能[1.90,3.65,3.04]但30家中客胜可达8.30
        var r1Source = (allRealOdds.home.length >= 10) ? '30家公司' : '竞彩官方';
        ['home','draw','away'].forEach(function(d, i) {
            // 用30家最大值做排除判断，用jcReal值显示
            var oMax = maxOdds[d];       // 30家中该方向最大赔率
            var oJc = (jcReal.length===3) ? jcReal[i] : oMax; // 显示用
            
            if (oMax >= 6.0) addEv(d, -90, oMax.toFixed(2)+'(30家最高)≥6.0: 极端高赔基本不出('+r1Source+')', 'R1-极端赔');
            else if (oMax >= 5.0) addEv(d, -85, oMax.toFixed(2)+'(30家最高)≥5.0: 历史约90%不出('+r1Source+')', 'R1-极高赔');
            else if (oMax >= 4.0) addEv(d, -65, oMax.toFixed(2)+'(30家最高)≥4.0: 高赔方向大概率不出', 'R1-高赔');
            else if (oMax >= 3.5) {
                // 友谊赛平局例外
                if (!(match_type.indexOf('友谊')>=0 && d==='draw'))
                    addEv(d, -45, oMax.toFixed(2)+'≥3.5: 中高赔需警惕', 'R1-中高赔');
            }
            
            // 碾压检测也改用30家最小值
            if (allRealOdds[d].length >= 10) {
                var oMin = Math.min.apply(null, allRealOdds[d]);
                if (oMin < 1.35) {
                    ['home','draw','away'].forEach(function(d2) { 
                        if(d2!==d) addEv(d2, -(20+Math.round((1.35-oMin)*50)), oMin.toFixed(2)+'(最低)碾压模式:庄家不怕'+eng[d].name+'出', 'R1-碾压'); 
                    });
                }
            } else if (oJc < 1.35 && jcReal.length===3) {
                ['home','draw','away'].forEach(function(d2) { if(d2!==d) addEv(d2, -25, oJc+'极端低赔碾压模式', 'R1-碾压'); });
            }
        });
        
        // 【R2】心水排除法（Step 1 最高优先级）
        if (macaoTip) {
            var ti = dirOfTip(macaoTip);
            var to = tipOdds();
            
            // R2a: 心水赔率≥3.5 → 排除心水方向（80%命中）
            if (to >= 3.5) {
                if (ti==='draw' && to >= 5.0)
                    addEv(ti, -75, '心水推'+macaoTip+'赔率'+to.toFixed(2)+'≥5: 但心水推平局高赔不可靠(⑨号)', 'R2a-心水高赔');
                else
                    addEv(ti, -70, '心水推'+macaoTip+'但赔率高('+to.toFixed(2)+'): 80%历史不出', 'R2a-心水高赔');
            }
            // R2b: 规则B — 竞彩推离心水(升>3%) → 排除心水（4/4=100%）
            else if (jcInit.length>=3 && jcReal.length>=3 && ti!==null) {
                var idx = {home:0,draw:1,away:2}[ti];
                if (jcInit[idx] > 0 && jcReal[idx] > 0) {
                    var chg = (jcReal[idx]-jcInit[idx])/jcInit[idx]*100;
                    if (chg > 3) {
                        addEv(ti, -80, '规则B:竞彩对心水'+macaoTip+'升'+chg.toFixed(1)+'%=言行不一(4/4=100%)', 'R2b-规则B');
                    } else if (chg < -2) {
                        // 竞彩降心水=看好该方向，反向操作
                        addEv(ti, +30, '竞彩对心水降'+Math.abs(chg).toFixed(1)+'%=实盘看好信号(非陷阱)', 'R2b-实盘信号');
                    }
                }
            }
            // R2c: 心水赔率2.0-3.0 + 无竞彩信号 → 灰色区间
            else if (to >= 2.0 && to < 3.0) {
                addEv(ti, -10, '心水赔率'+to.toFixed(2)+'在灰色区间(54.5%),无明确信号', 'R2c-灰色区');
            }
        }
        
        // 【R3】竞彩×澳门互动信号
        signals.forEach(function(s) {
            var t = s.text || '';
            
            // R3a: [不怕]X + X赔率≥3.5 → 强力排除X
            if (t.indexOf('[不怕]') >= 0) {
                var m = t.match(/(\d+\.?\d*)/g);
                var ov = parseFloat(m&&m[0])||0;
                var bd = null;
                if (t.indexOf('主')>=0&&t.indexOf('客')<0) bd='home'; 
                else if (t.indexOf('平')>=0||t.indexOf('和')>=0) bd='draw'; 
                else if (t.indexOf('客')>=0) bd='away';
                if (bd && ov >= 3.5) addEv(bd, -65, '[不怕]'+eng[bd].name+'+赔率'+ov+'≥3.5: 庄家笃定该方向不出(~88%)', 'R3a-[不怕]');
                else if (bd && ov > 0 && ov < 3.5) addEv(bd, +5, '[不怕]'+eng[bd].name+'但赔率仅'+ov+'<3.5: 不可靠(刚果案例❌)', 'R3a-[不怕]低赔');
            }
            
            // R3b: [不跟]X → X造热假象（不直接排除，降低信任）
            if (t.indexOf('[不跟]') >= 0) {
                var bd2 = null;
                if (t.indexOf('主')>=0) bd2='home'; else if (t.indexOf('平')>=0||t.indexOf('和')>=0) bd2='draw'; else if (t.indexOf('客')>=0) bd2='away';
                if (bd2) addEv(bd2, +25, '[不跟]'+eng[bd2].name+': 竞彩单独造热是假象,不代表真出', 'R3b-[不跟]');
            }
            
            // R3c: 推离信号(竞彩升>5%且澳门不同步)
            if ((t.indexOf('推离')>=0||t.indexOf('升')>=0) && s.strength >= 4) {
                var bd3 = null;
                if (t.indexOf('主')>=0&&(t.indexOf('排除主')>=0||t.indexOf('推离主')>=0)) bd3='home';
                else if (t.indexOf('平')>=0||(t.indexOf('排除平')>=0||t.indexOf('推离平')>=0)) bd3='draw';
                else if (t.indexOf('客')>=0||(t.indexOf('排除客')>=0||t.indexOf('推离客')>=0)) bd3='away';
                if (bd3) addEv(bd3, -55, '竞彩推离'+eng[bd3].name+': 庄家不想让该方向出', 'R3c-推离');
            }
        });
        
        // 【R4】历史案例投票排除
        if (simReviews.length > 0) {
            // 统计每个方向在历史案例中被排除的次数
            var excByDir = {home:0, draw:0, away:0};
            simReviews.forEach(function(r) {
                (r.exclusions||[]).forEach(function(e) {
                    if (e.indexOf('主')>=0) excByDir.home++;
                    if (e.indexOf('平')>=0||e.indexOf('和')>=0) excByDir.draw++;
                    if (e.indexOf('客')>=0) excByDir.away++;
                });
            });
            ['home','draw','away'].forEach(function(d) {
                var eCnt = excByDir[d];
                if (eCnt >= simReviews.length && simReviews.length >= 2) {
                    addEv(d, -(30+eCnt*5), simReviews.length+'条案例全部排除'+eng[d].name+'('+eCnt+'/'+simReviews.length+')', 'R4-全排除一致');
                } else if (eCnt >= Math.ceil(simReviews.length*0.7)) {
                    addEv(d, -(15+eCnt*3), '多数案例('+Math.round(eCnt/simReviews.length*100)+'%)排除'+eng[d].name, 'R4-多数排除');
                }
            });
            // 历史结果倾向
            if (topVoteDir && maxVote >= 2) {
                var tvd = topVoteDir.indexOf('主')>=0?'home':topVoteDir.indexOf('平')>=0?'draw':'away';
                if (tvd) addEv(tvd, +(maxVote*3), '历史'+maxVote+'/'+simReviews.length+'条倾向'+topVoteDir, 'R4-历史倾向');
            }
        }
        
        // 【R5】反模式陷阱检测（影响当前预测方向的可靠性）
        // R5a: 单出口全面造热陷阱
        var hasDualHeat = false, hasPush = 0;
        signals.forEach(function(s) {
            if (s.text && s.text.indexOf('同向')>=0 && s.text.indexOf('造热')>=0 && s.strength>=4) hasDualHeat=true;
            if (s.text && (s.text.indexOf('推离')>=0||s.text.indexOf('升')>=0)) hasPush++;
        });
        if (hasDualHeat && hasPush >= 2) {
            // 对当前预测方向扣分（因为当前预测很可能就是被造热的方向）
            var bp = basePred.indexOf('主')>=0?'home':basePred.indexOf('平')>=0?'draw':'away';
            addEv(bp, -50, '🔴单出口全面造热陷阱(⑭号): 三方向同向≠可靠,当前预测可能是陷阱', 'R5a-造热陷阱');
        }
        
        // R5b: 友谊赛特殊处理
        if (match_type.indexOf('友谊')>=0 && basePred!=='观望' && baseConf<=4) {
            var bp2 = basePred.indexOf('主')>=0?'home':basePred.indexOf('平')>=0?'draw':'away';
            addEv(bp2, -30, '⚠️友谊赛选'+basePred+'命中率仅33%(墨西哥❌巴西❌)', 'R5b-友谊赛');
        }
        
        // R5c: 全面分歧信号
        var sigD = {home:false,draw:false,away:false};
        signals.forEach(function(s){var t=s.text||'';if(t.indexOf('排除主')>=0)sigD.home=true;if(t.indexOf('排除平')>=0)sigD.draw=true;if(t.indexOf('排除客')>=0)sigD.away=true;});
        if (Object.keys(sigD).filter(function(k){return sigD[k]}).length >= 3) {
            // 全方向都有排除信号→反而最危险，降低所有排除分的权重
            ['home','draw','away'].forEach(function(d){ eng[d].score *= 0.5; });
        }
        
        // 【R6】掩护模式检测
        var quietDraw = false;
        signals.forEach(function(s){ if(s.text&&s.text.indexOf('平赔')>=0&&s.text.indexOf('不动')>=0) quietDraw=true; });
        if (quietDraw) {
            addEv('draw', +20, '平赔安静保护(⑬⑯⑲号): 庄家可能在掩护平局', 'R6-掩护平局');
        }
        
        // 【R7】近况差辅助
        if (formDiff !== 0) {
            if (formDiff >= 8) {
                addEv('home', +15*(Math.min(formDiff,15)/8), '近况差支持主队(+'+formDiff+')', 'R7-近况主优');
                addEv('away', -10*(Math.min(formDiff,15)/8), '近况差不利客队(-'+formDiff+')', 'R7-近况客劣');
            } else if (formDiff <= -8) {
                addEv('away', +15*(Math.min(Math.abs(formDiff),15)/8), '近况差支持客队('+formDiff+')', 'R7-近况客优');
                addEv('home', -10*(Math.min(Math.abs(formDiff),15)/8), '近况差不利于主队('+formDiff+')', 'R7-近况主劣');
            }
        }
        
        // ════════════════════════════════════
        // 【R8】冷门检测器（2026-04-12新增）
        // 核心逻辑：当"赔率变化信号"足够强时，可以覆盖"赔率绝对值排除"
        // 适用场景：阿森纳1-2伯恩茅斯、米堡1-2米尔沃尔、伯明翰0-1布莱克本
        // 特征：某方向赔率≥3.5(本应被R1排除) + 但竞彩/澳门大幅降该方向 + 多家公司同向
        // 原理：庄家在主动引导筹码去低赔方向，掩护高赔方向打出 = 典型造热陷阱
        // ════════════════════════════════════
        if (jcReal.length === 3 && allRealOdds.home.length >= 20) {
            ['home','draw','away'].forEach(function(d, i) {
                var oJc = jcReal[i];           // 竞彩即时赔率
                var oMax = maxOdds[d];         // 30家最高赔率
                var oJcInit = (jcInit.length===3) ? jcInit[i] : oJc;
                
                // 条件1：该方向赔率偏高（≥3.5），本来会被R1排除
                var isHighOdds = (oMax >= 3.5);
                
                if (!isHighOdds) return; // 只处理高赔方向
                
                // 条件2：计算竞彩对该方向的变化幅度
                var chgPct = (oJcInit > 0) ? ((oJc - oJcInit) / oJcInit * 100) : 0;
                var jcDropping = (chgPct < -4);   // 竞彩降>4%
                var jcStrongDrop = (chgPct < -7); // 竞彩降>7%（强信号）
                
                // 条件3：统计30家公司中降该方向的比例
                var dirIdx = {home:0, draw:1, away:2}[d];
                var dropCount = 0, totalCount = allRealOdds[d].length;
                if (_rd.initial_odds && _rd.initial_odds.length > 0) {
                    for(var ri=0; ri<totalCount && ri<_rd.realtime_odds.length; ri++) {
                        var initRow = _rd.initial_odds[ri];
                        var rtRow = _rd.realtime_odds[ri];
                        if(Array.isArray(initRow) && Array.isArray(rtRow) && initRow.length>dirIdx && rtRow.length>dirIdx) {
                            var oi=Number(initRow[dirIdx]), or=Number(rtRow[dirIdx]);
                            if(oi>0 && or>0 && or<oi*0.97) dropCount++; // 降>3%
                        }
                    }
                }
                var dropRatio = (totalCount > 0) ? dropCount / totalCount : 0;
                var consensusDrop = (dropCount >= 20);    // ≥20家同向降
                var strongConsensus = (dropCount >= 25);  // ≥25家强共识
                
                // 条件4：澳门是否也同向降（如果有数据）
                var macaoAgrees = false;
                if (odds_real.mac_real && odds_real.mac_init) {
                    var macDir = {home:0,draw:1,away:2}[d];
                    if(odds_real.mac_real[macDir] && odds_real.mac_init[macDir]) {
                        var mInit = Number(odds_real.mac_init[macDir]);
                        var mReal = Number(odds_real.mac_real[macDir]);
                        if(mInit > 0 && mReal < mInit * 0.96) macaoAgrees = true; // 澳门降>4%
                    }
                }

                // R8 判定逻辑：变化信号覆盖绝对值排除
                var r8Score = 0;
                var r8Reasons = [];
                
                // 基础分：竞彩大幅降赔（最关键信号）
                if (jcStrongDrop) { r8Score += 40; r8Reasons.push('竞彩强降'+chgPct.toFixed(1)+'%'); }
                else if (jcDropping) { r8Score += 25; r8Reasons.push('竞彩降'+chgPct.toFixed(1)+'%'); }
                
                // 加分：多公司共识
                if (strongConsensus) { r8Score += 30; r8Reasons.push(dropCount+'/30家强共识'); }
                else if (consensusDrop) { r8Score += 18; r8Reasons.push(dropCount+'/30家同向降'); }
                
                // 加分：澳门同向（竞彩×澳门互动确认）
                if (macaoAgrees) { r8Score += 15; r8Reasons.push('澳门同向降'); }
                
                // 加分：心水恰好推荐该方向（庄家公开建议与实际打出一致）
                var _tip = (res.raw_data && res.raw_data.macao_tip) ? res.raw_data.macao_tip : '';
                if (_tip) {
                    var tipDirs = [];
                    if (_tip.indexOf(eng['home'].name)>=0) tipDirs.push('home');
                    else if (_tip.indexOf(eng['away'].name)>=0) tipDirs.push('away');
                    if ((_tip.indexOf('和')>=0 || _tip.indexOf('平')>=0) && d==='draw') tipDirs.push('draw');
                    if (tipDirs.indexOf(d) >= 0) { r8Score += 10; r8Reasons.push('心水同向('+_tip+')'); }
                }
                
                // 最终判定：R8得分→给正分覆盖R1的负分
                // 分级覆盖策略：
                //   r8Score≥65(极端): bonus=90, 足以翻转任何R1排除
                //   r8Score≥50(强):   bonus=75, 可翻大多数排除
                //   r8Score≥35(中):   bonus=45, 减弱排除力度
                if (r8Score >= 65) {
                    var bonus = Math.min(r8Score, 90);  // 极端信号允许更高覆盖
                    addEv(d, bonus, '[R8-冷门检测⚡] '+r8Reasons.join(' + ')+': 极端变化信号强力覆盖绝对值', 'R8-冷门');
                    eng[d]._coldAlert = 'strong'; // 标记强冷门
                } else if (r8Score >= 50) {
                    var bonus = Math.min(r8Score, 75);
                    addEv(d, bonus, '[R8-冷门检测] '+r8Reasons.join(' + ')+': 变化信号覆盖绝对值', 'R8-冷门');
                    eng[d]._coldAlert = 'medium';
                } else if (r8Score >= 30) {
                    addEv(d, Math.round(r8Score * 0.7), '[R8-冷门预警] '+r8Reasons.join(' + ')+': 存在冷门可能，降低排除置信度', 'R8-预警');
                    eng[d]._coldAlert = 'weak';
                }
            });
        }
        
        // ════════════════════════════════════
        // 计算最终排除状态（V2: 阈值+相对比较）
        // ════════════════════════════════════
        var EX_STRONG = -35;    // ≤-35: 强排除（红）— 原来太严(-45),错过中等信号
        var EX_WEAK = -12;      // ≤-12: 弱排除（黄）— 原来太严(-20),多数规则无法触发
        
        ['home','draw','away'].forEach(function(d) {
            var sc = eng[d].score;
            if (sc <= EX_STRONG) eng[d].status = 'strong_exclude';
            else if (sc <= EX_WEAK) eng[d].status = 'weak_exclude';
            else if (sc > 8) eng[d].status = 'keep';
            else eng[d].status = 'neutral';
        });
        
        // ★ 相对比较：即使无人达强排除，最低分方向若明显低于其他两方 → 弱排除
        var scores = [eng.home.score, eng.draw.score, eng.away.score];
        var dirs = ['home','draw','away'];
        var minSc = Math.min.apply(null, scores);
        var midSc = scores.sort(function(a,b){return a-b})[1]; // 排序后取中间值
        // 重新获取排序后的中间分数
        var sortedSc = scores.slice().sort(function(a,b){return a-b});
        minSc = sortedSc[0];
        midSc = sortedSc[1];
        
        if (minSc > EX_WEAK && minSc < 5 && (midSc - minSc) >= 15) {
            // 最低分方向比中间高15+且自身为负 → 给个弱排除
            dirs.forEach(function(d) { if(eng[d].score===minSc && eng[d].status==='neutral') eng[d].status='weak_exclude'; });
        }
        
        // 统计排除数
        var strongExc = 0, weakExc = 0;
        ['home','draw','away'].forEach(function(d) {
            if (eng[d].status==='strong_exclude') strongExc++;
            else if (eng[d].status==='weak_exclude') weakExc++;
        });
        
        // 最终结论
        var finalDirs = [];
        var finalText = '', finalColor = '#94a3b8', finalStars = 0;
        
        ['home','draw','away'].forEach(function(d) {
            if (eng[d].status!=='strong_exclude') finalDirs.push(d);
        });
        
        if (finalDirs.length === 1) {
            var fd = finalDirs[0];
            finalText = eng[fd].name; finalColor = eng[fd].color; finalStars = 5;
        } else if (finalDirs.length === 2) {
            // 两方向剩余：比较分数，高的更可信
            var d1=finalDirs[0], d2=finalDirs[1];
            if (jcReal.length===3) {
                var o1=jcReal[{home:0,draw:1,away:2}[d1]], o2=jcReal[{home:0,draw:1,away:2}[d2]];
                if (Math.abs(o1-o2)>0.5) {
                    var lower = o1<o2?d1:d2;
                    finalText = eng[lower].name+'(优选)'; finalColor = eng[lower].color; finalStars = 4;
                } else {
                    finalText = '平局(胶着)'; finalColor = '#fbbf24'; finalStars = 3;
                }
            } else {
                finalText = eng[d1].score>eng[d2].score?eng[d1].name:eng[d2].name; finalStars = 3;
            }
        } else if (finalDirs.length === 3) {
            // 三方向均未排除：综合分数+赔率+证据给出倾向（V2增强版）
            var scores = finalDirs.map(function(d) { return {d:d, s:eng[d].score, e:eng[d].evidence}; });
            scores.sort(function(a,b){return b.s - a.s}); // 分数高排前面=更可信
            var topDir = scores[0].d;
            var topScore = scores[0].s;
            var midScore = scores[1].s;
            var botScore = scores[2].s; // 最低分=最危险
            var botDir = scores[2].d;
            
            var recText = '', recColor = '#94a3b8', recStars = 1;
            var gapTopMid = topScore - midScore;
            var gapMidBot = midScore - botScore;
            
            // 关键改进：即使无人达排除阈值，最低分方向若明显更低 → 可视为"隐性排除"
            var hasImplicitExclude = (botScore < 0 && gapMidBot >= 12);
            var hasClearLeader = (gapTopMid >= 10 && topScore > 5);
            
            if (jcReal.length===3) {
                var oH=jcReal[0], oD=jcReal[1], oA=jcReal[2];
                var minO = Math.min(oH,oD,oA);
                var maxO = Math.max(oH,oD,oA);
                
                // A类：有超高赔(>5) → 排除高赔后选低赔 = 最可靠
                if (maxO > 5.0) {
                    var lowDirs = finalDirs.filter(function(d) { return jcReal[{home:0,draw:1,away:2}[d]] <= 5.0; });
                    if (lowDirs.length === 1) {
                        recText = eng[lowDirs[0]].name+'(唯一<5)';
                        recColor = eng[lowDirs[0]].color;
                        recStars = hasClearLeader ? 4 : 3;
                    } else if (lowDirs.length === 2) {
                        var lo1=lowDirs[0], lo2=lowDirs[1];
                        var odd1=jcReal[{home:0,draw:1,away:2}[lo1]], odd2=jcReal[{home:0,draw:1,away:2}[lo2]];
                        if (Math.abs(odd1-odd2)>0.5) {
                            var prefLow = odd1<odd2?lo1:lo2;
                            recText = eng[prefLow].name+'(排除>5优选)';
                            recColor = eng[prefLow].color;
                            recStars = 3;
                        } else {
                            // 赔率接近时看分数
                            recText = eng[topDir].name+'(低赔区优选)';
                            recColor = eng[topDir].color;
                            recStars = 2;
                        }
                    }
                }
                // B类：碾压盘口(<1.35)
                else if (minO < 1.35 && maxO - minO > 3.0) {
                    var lowOdir = {0:'home',1:'draw',2:'away'}[[oH,oD,oA].indexOf(minO)];
                    recText = eng[lowOdir].name+'(碾压盘)';
                    recColor = eng[lowOdir].color;
                    recStars = 3;
                }
                // C类：分数有明显分层 → 给倾向
                else if (hasImplicitExclude || hasClearLeader) {
                    var leader = hasImplicitExclude ? topDir : topDir;
                    recText = eng[leader].name + (hasImplicitExclude ? '(排除'+eng[botDir].name+'后)' : '(分数领先)');
                    recColor = eng[leader].color;
                    recStars = hasImplicitExclude ? 3 : 2;
                }
                // D类：有微弱分数优势
                else if (gapTopMid >= 5 && topScore > 0) {
                    recText = eng[topDir].name+'(微弱倾向)';
                    recColor = eng[topDir].color;
                    recStars = 2;
                }
                else {
                    recText = '观望(无区分度)';
                    recColor = '#64748b';
                    recStars = 1;
                }
            } else {
                // 无即时赔率：纯按分数
                if (hasClearLeader) {
                    recText = eng[topDir].name+'(明显领先)';
                    recColor = eng[topDir].color;
                    recStars = 2;
                } else if (hasImplicitExclude) {
                    recText = eng[topDir].name+'(相对更优)';
                    recColor = eng[topDir].color;
                    recStars = 2;
                } else {
                    recText = '观望(数据不足)';
                    recColor = '#64748b';
                    recStars = 1;
                }
            }
            
            finalText = recText; finalColor = recColor; finalStars = recStars;
        }
        
        // 最终兜底：如果还是没有文本
        if (!finalText) {
            finalText = '观望'; finalColor = '#64748b; finalStars = 1';
        }
        
        // 友谊赛降级
        if (match_type.indexOf(' friendship')>=0 && finalStars >= 4 && strongExc < 2) {
            finalStars--; finalText += '(友谊赛降级)';
        }
        
        // ════════════════════════════════════
        // ★ V3.3 R8极端冷门降级系统（影响结论星级+文本）
        // ════════════════════════════════════
        var hasExtremeCold = false, hasMediumCold = false;
        ['home','draw','away'].forEach(function(d) {
            if (eng[d]._coldAlert === 'strong') hasExtremeCold = true;
            else if (eng[d]._coldAlert === 'medium' || eng[d]._coldAlert === 'weak') hasMediumCold = true;
        });
        
        if (hasExtremeCold) {
            // ⚡ 极端冷门：至少降1星，加冷门标记到结论文字
            finalStars = Math.max(1, finalStars - 1);
            if (finalStars >= 2) { finalText += ' ⚡冷门预警'; finalColor = '#f59e0b'; }
            else { finalText = '⚠️冷门风险高(' + finalText + ')'; finalColor = '#f97316'; }
        } else if (hasMediumCold) {
            // ⚠️ 中等冷门：不降星但标记警告
            if (finalStars >= 3) finalText += ' ⚠️冷门可能';
        }
        
        // 渲染三方向排除面板
        // ════════════════════════════════════
        var exHtml = '<div class="section"><div class="section-title"><span class="icon icon-purple">🔍</span> 三方向排除引擎</div>';
        exHtml += '<div style="background:#0c1222;border-radius:10px;padding:14px;border:1px solid #334155">';
        
        // 三方向条形图
        exHtml += '<div style="font-size:11px;color:#94a3b8;margin-bottom:8px;font-weight:600">📊 方向安全性评估（负分=排除证据 / 正分=保留证据）</div>';
        exHtml += '<div style="display:flex;flex-direction:column;gap:8px">';
        
        ['home','draw','away'].forEach(function(d) {
            var e = eng[d];
            var sc = e.score;
            // 归一化到 -100 ~ +100 显示
            var normSc = Math.max(-100, Math.min(100, sc));
            var barPct = 50 + normSc/2; // -100→0%, 0→50%, +100→100%
            
            var stColor, stText, stBg, stBorder;
            if (e.status==='strong_exclude') { stColor='#ef4444'; stText='🚫 强排除'; stBg='rgba(239,68,68,0.15)'; stBorder='1px solid rgba(239,68,68,0.4)'; }
            else if (e.status==='weak_exclude') { stColor='#fbbf24'; stText='⚠️ 弱排除'; stBg='rgba(251,191,36,0.12)'; stBorder='1px solid rgba(251,191,36,0.4)'; }
            else if (e.status==='keep') { stColor='#4ade80'; stText='✅ 安全'; stBg='rgba(74,222,128,0.1)'; stBorder='1px solid rgba(74,222,128,0.4)'; }
            else { stColor='#94a3b8'; stText='➖ 中性'; stBg='rgba(148,163,184,0.08)'; stBorder='1px solid rgba(148,163,184,0.3)'; }
            
            exHtml += '<div style="'+stBg+';border-radius:8px;border:'+stBorder+';overflow:hidden">';
            exHtml += '<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 10px">';
            exHtml += '<div style="display:flex;align-items:center;gap:8px;min-width:70px">';
            exHtml += '<span style="color:'+e.color+';font-weight:bold;font-size:14px">'+e.name+'</span>';
            exHtml += '<span style="font-size:11px;color:'+stColor+';font-weight:600;padding:2px 8px;border-radius:10px;background:rgba(0,0,0,0.2)">'+stText+'</span>';
            if (jcReal.length>2) exHtml += '<span style="font-size:11px;color:#64748b">('+jcReal[{home:0,draw:1,away:2}[d]].toFixed(2)+')</span>';
            exHtml += '</div>';
            exHtml += '<div style="font-size:13px;font-weight:bold;color:'+(sc>=0?'#4ade80':'#ef4444')+'">' + (sc>=0?'+':'') + sc + '</div>';
            exHtml += '</div>';
            
            // 分数条背景（灰底表示中性线）
            exHtml += '<div style="height:6px;background:#1e293b;border-radius:3px;margin:0 10px 8px;position:relative">';
            exHtml += '<div style="position:absolute;left:50%;top:-2px;width:2px;height:10px;background:#475569;z-index:2"></div>'; // 零线标记
            exHtml += '<div style="height:100%;border-radius:3px;width:'+barPct+'%;background:linear-gradient(to right,#ef4444 0%,#fbbf25 40%,#4ade80 60%,#22c55e 100%);transition:width 0.3s;min-width:'+(normSc<-95?'2px':'0')+'"></div>';
            exHtml += '</div>';
            
            // 关键证据（只显示最强的2条）
            var topEvs = e.evs.slice().sort(function(a,b){return Math.abs(a.d)-Math.abs(b.d)}).reverse().slice(0,2);
            if (topEvs.length > 0) {
                exHtml += '<div style="padding:0 10px 8px;display:flex;flex-direction:column;gap:3px">';
                topEvs.forEach(function(ev) {
                    var ec = ev.d<0?'#f87171':ev.d>0?'#4ade80':'#94a3b8';
                    var ep = ev.d<0?'↓ ':ev.d>0?'↑ ':'· ';
                    exHtml += '<div style="font-size:10.5px;color:'+ec+';line-height:1.4">' + ep + '[' + ev.r + '] ' + ev.t + '</div>';
                });
                if (e.evs.length > 2) exHtml += '<div style="font-size:10px;color:#475569">... 还有'+(e.evs.length-2)+'条证据</div>';
                exHtml += '</div>';
            }
            exHtml += '</div>';
        });
        exHtml += '</div>';
        
        // 最终结论框
        var conclusionBg = finalStars>=4?'rgba(74,222,128,0.08)':finalStars>=3?'rgba(251,191,36,0.08)':finalStars>=2?'rgba(96,165,250,0.08)':'rgba(239,68,68,0.12)';
        var conclusionBorder = finalStars>=4?'1px solid rgba(74,222,128,0.35)':finalStars>=3?'1px solid rgba(251,191,36,0.35)':finalStars>=2?'1px solid rgba(96,165,250,0.35)':'1px solid rgba(239,68,68,0.4)';
        
        exHtml += '<div style="margin-top:14px;padding:16px;border-radius:10px;background:'+conclusionBg+';border:'+conclusionBorder+'">';
        exHtml += '<div style="text-align:center">';
        exHtml += '<div style="font-size:11px;color:#64748b;margin-bottom:6px">排除引擎结论 · '+strongExc+'强排除 + '+weakExc+'弱排除</div>';
        
        // R8-B 反向冷门警告
        var r8bWarning = '';
        if (eng._r8bScore && eng._r8bScore >= 45) {
            var r8bLevel = eng._r8bScore >= 65 ? '⚡极端' : '⚠️中等';
            var r8bColor = eng._r8bScore >= 65 ? '#f87171' : '#fbbf24';
            r8bWarning = '<span style="color:'+r8bColor+';font-weight:bold;font-size:10px;margin-left:8px">['+r8bLevel+'反向冷门]</span>';
        }
        
        exHtml += '<div style="font-size:22px;color:'+finalColor+';font-weight:bold">';
        for(var si=0;si<finalStars;si++) exHtml+='★';
        for(var si=finalStars;si<5;si++) exHtml+='☆';
        exHtml += ' ' + finalText + r8bWarning + '</div>';
        
        // ★ 冷门预警横幅（V3.3增强版：覆盖所有有R8信号的方向，不限finalDirs；V3.4：加入R8-B检测）
        var coldDirs = [];
        
        // R8-B 反向冷门检测结果
        if (eng._r8bScore && eng._r8bScore >= 25) {
            var r8bLevel = eng._r8bScore >= 65 ? 'strong' : (eng._r8bScore >= 45 ? 'medium' : 'weak');
            coldDirs.push({d:'draw', level:r8bLevel, name:'和局', st: eng.draw.status, isR8B:true, score:eng._r8bScore, reasons:eng._r8bReasons});
        }
        
        ['home','draw','away'].forEach(function(d) {
            // 方式1：_coldAlert标记直接检测
            if (eng[d]._coldAlert) {
                // R8-B 已添加的不重复
                if (!(d === 'draw' && eng._r8bScore && eng._r8bScore >= 25)) {
                    coldDirs.push({d:d, level:eng[d]._coldAlert, name:eng[d].name, st: eng[d].status});
                }
            }
            // 方式2：扫描证据列表中的R8标签（兜底）
            else if (eng[d] && eng[d].evs) {
                var hasR8 = eng[d].evs.some(function(ev){ return ev.r && (ev.r.indexOf('R8-')===0); });
                if (hasR8) {
                    // R8-B 已添加的不重复
                    if (!(d === 'draw' && eng._r8bScore && eng._r8bScore >= 25)) {
                        coldDirs.push({d:d, level:'medium', name:eng[d].name, st: eng[d].status});
                    }
                }
            }
        });
        // 去重
        if(coldDirs.length>0) {
            var seen={}; coldDirs=coldDirs.filter(function(cd){ if(seen[cd.d]) return false; seen[cd.d]=true; return true; });
        }
        
        if (coldDirs.length > 0) {
            var bannerBg = hasExtremeCold ? 'rgba(239,68,68,0.12)' : 'rgba(251,191,36,0.1)';
            var bannerBorder = hasExtremeCold ? '#ef4444' : '#f59e0b';
            var bannerTitle = hasExtremeCold ? '🚨 极端冷门预警' : '⚠️ 冷门预警';
            exHtml += '<div style="margin-top:8px;padding:10px 12px;border-radius:6px;background:'+bannerBg+';border-left:3px solid '+bannerBorder+'">';
            exHtml += '<span style="font-size:12px;color:'+(hasExtremeCold?'#f87171':'#f59e0b')+';font-weight:bold">'+bannerTitle+'：</span>';
            exHtml += '<span style="font-size:11.5px;color:#cbd5e1">以下方向检测到造热陷阱信号</span><br>';
            coldDirs.forEach(function(cd) {
                var tag = cd.level==='strong' ? '⚡极端' : (cd.level==='medium' ? '⚠️中等' : '💡微弱');
                var stTag = cd.st==='strong_exclude' ? '(🚫强排除)' : (cd.st==='weak_exclude' ? '(⚠️弱排除)' : '');
                var dirColor = cd.level==='strong' ? '#f87171' : '#fbbf24';
                var extraInfo = '';
                if (cd.isR8B && cd.reasons) {
                    extraInfo = ' <span style="color:#a78bfa;font-size:9px">[R8-B:'+cd.reasons.join('+')+']</span>';
                }
                exHtml += '· <span style="font-weight:bold;color:'+dirColor+'">'+cd.name+'</span> <span style="color:'+dirColor+';font-size:10px">'+tag+stTag+'</span>'+extraInfo+' ';
            });
            
            // 警告文本
            var hasR8B = coldDirs.some(function(cd){ return cd.isR8B; });
            var warnText;
            if (hasExtremeCold) {
                warnText = '竞彩大幅降赔 + 多公司同向 + 澳门同向 = 典型造热陷阱！该方向可能打出，主方向结论不可信。';
            } else if (hasR8B) {
                var r8bDir = coldDirs.find(function(cd){ return cd.isR8B; });
                if (r8bDir && r8bDir.score >= 65) {
                    warnText = 'R8-B反向冷门⚡：澳门推荐和局但赔率不配合下降='+r8bDir.name+'可能打出，建议观望或极小仓。';
                } else {
                    warnText = 'R8-B检测到和局可能，请降低仓位或关注双选。';
                }
            } else {
                warnText = '存在造热陷阱迹象，建议降低投注仓位或跳过本场。';
            }
            exHtml += '<br><span style="font-size:11px;color:#94a3b8;margin-top:2px;display:inline-block">'+warnText+'</span></div>';
        }
        
        // 投注建议（V3.3：R8极端冷门时降级建议；V3.4：R8-B反向冷门时降级建议）
        var advice = '', adviceColor = '#64748b';
        var r8bHighAlert = (eng._r8bScore && eng._r8bScore >= 45); // R8-B 高分冷门
        var r8bMedAlert = (eng._r8bScore && eng._r8bScore >= 25);  // R8-B 中分冷门
        
        if (hasExtremeCold) {
            // ⚡ 极端冷门信号 → 建议观望或极小仓试探
            advice = '🚨 谨慎/观望 — 检测到⚡极端冷门造热陷阱信号（竞彩大幅降赔+多公司同向），排除方向可能打出，建议跳过或仅极小仓位试探'; adviceColor = '#ef4444';
        } else if (hasMediumCold && finalStars >= 4) {
            // ⚠️ 中等冷门 + 高星级 → 降一档
            advice = '⚠️ 控制仓位 — 存在冷门可能，如投注请控制在常规的1/2以内'; adviceColor = '#f59e0b';
        } else if (r8bHighAlert) {
            // R8-B 高分反向冷门 → 和局可能打出，警告
            var r8bDetail = eng._r8bReasons ? eng._r8bReasons.join(' + ') : '';
            advice = '⚠️ 控制仓位 — R8-B反向冷门检测到和局可能('+eng._r8bScore+'分)：'+r8bDetail; adviceColor = '#f59e0b';
        } else if (r8bMedAlert) {
            // R8-B 中分 → 存在和局可能
            var r8bDetail = eng._r8bReasons ? eng._r8bReasons.join(' + ') : '';
            advice = '🟡 注意和局 — R8-B检测('+eng._r8bScore+'分)：'+r8bDetail; adviceColor = '#fbbf24';
        } else if (finalStars >= 4 && strongExc >= 1) {
            advice = '✅ 建议投注 — 排除法置信度高，排除'+strongExc+'方向后剩余唯一选择'; adviceColor = '#22c55e';
        } else if (finalStars >= 3) {
            advice = '🟡 可小试 — 有一定排除依据，但需控制仓位'; adviceColor = '#eab308';
        } else if (finalStars === 2) {
            advice = '⚪ 谨慎参考 — 信号偏弱，仅作为辅助判断，不建议重仓'; adviceColor = '#94a3b8';
        } else {
            advice = '❌ 建议观望 — 无足够排除证据支撑，跳过本场'; adviceColor = '#ef4444';
        }
        exHtml += '<div style="margin-top:8px;padding:10px;border-radius:6px;background:rgba(0,0,0,0.2);border-left:3px solid '+adviceColor+'">';
        exHtml += '<span style="font-size:12px;color:'+adviceColor+';font-weight:bold">💰 投注建议：</span>';
        exHtml += '<span style="font-size:12px;color:#cbd5e1">'+advice+'</span></div>';
        
        // 与原预测对比
        var predMatch = (basePred.indexOf(finalText)>=0 || finalText.indexOf(basePred)>=0);
        if (!predMatch && basePred!=='观望' && finalStars>=3) {
            exHtml += '<div style="margin-top:10px;padding:10px;background:rgba(96,165,250,0.1);border:1px solid rgba(96,165,250,0.3);border-radius:8px;text-align:left">';
            exHtml += '<div style="font-size:12px;color:#60a5fa;font-weight:bold">⚡ 排除引擎与原始预测不一致</div>';
            exHtml += '<div style="font-size:11.5px;color:#cbd5e1;margin-top:4px">原始预测：<strong style="color:#f59e0b">'+basePred+'</strong> ★'.repeat(baseConf).repeat(Math.max(0,5-baseConf)?'☆'.repeat(5-baseConf):'') + '</div>';
            exHtml += '<div style="font-size:11.5px;color:#cbd5e1;margin-top:2px">引擎结论：<strong style="color:'+finalColor+'">'+finalText+'</strong></div>';
            exHtml += '<div style="font-size:10.5px;color:#64748b;margin-top:4px">排除引擎基于赔率/心水/信号等多维交叉验证得出结论，当与原始预测冲突时应优先参考引擎结果。</div>';
            exHtml += '</div>';
        }
        exHtml += '</div></div>';
        exHtml += '</div></div>';
        
        html += exHtml;
    } else {
        // 没有找到高相似度案例时也提示一下
        if (res.review_count > 0) {
            html += `
            <div class="section" style="opacity:0.6">
                <div class="section-title"><span class="icon icon-gray">📚</span> 历史复盘参考</div>
                <div style="font-size:12px;color:#64748b">
                    已有 ${res.review_count} 条复盘记录，但未找到与当前比赛高度相似的案例。<br/>
                    <b>严格4维门槛：</b>需同时满足 <b>预测结果相同</b> + 赛事/球队/赔率 至少1项达标（总分≥35分 或 同队+同排除）。<br/>
                    这可能是新模式的比赛，或历史中无相同预测结果且高匹配度的案例，建议谨慎分析并保存复盘供未来参考。
                </div>
            </div>`;
        }
    }
    
    // 澳门分析原文
    if (rd.macao_analysis) {
        html += `
        <div class="section">
            <div class="section-title"><span class="icon icon-red">📝</span> 澳门分析原文</div>
            <div style="background:#0f172a;padding:14px;border-radius:8px;border:1px solid #334155;font-size:13px;line-height:1.7;color:#cbd5e1">
                ${rd.macao_analysis}
            </div>
        </div>`;
    }
    
    document.getElementById('detailContent').innerHTML = html;
    document.getElementById('detailPanel').classList.add('show');
}

function closeDetail() {
    var dp = document.getElementById('detailPanel');
    dp.classList.remove('show');
    dp.style.display = '';
}

function showStatus(msg, type) {
    const bar = document.getElementById('statusBar');
    bar.className = `status-bar ${type}`;
    bar.textContent = msg;
}

// 初始化（日期按钮已由服务端渲染）
initDates();

// ========================================
// 🧊 冷门模式库浏览
// ========================================
async function showUpsetsLibrary() {
    try {
        const res = await api('/api/upsets');
        if (!res.success) return;
        
        const upsets = res.data || [];
        const stats = res.stats || {};
        const total = stats.total || 0;
        const byType = stats.by_type || {};
        
        let html = `
    <button class="detail-close" onclick="closeDetail()" style="position:absolute;top:12px;right:16px;z-index:10">
    <div style="padding:24px;padding-top:8px">
            <h2 style="color:#e2e8f0;font-size:20px;margin-bottom:4px">🧊 冷门模式库</h2>
            <p style="color:#64748b;font-size:13px;margin-bottom:16px">
                自动收集复盘时检测到的"无预警爆冷"案例，用于后续分析时做模式匹配参考
            </p>
            
            <!-- 统计概览 -->
            <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px;padding:14px;background:#0f172a;border-radius:10px">
                <div style="text-align:center;min-width:80px">
                    <div style="font-size:28px;font-weight:bold;color:#f87171">${total}</div>
                    <div style="font-size:11px;color:#64748b">总记录</div>
                </div>
                ${Object.entries(byType).map(([k,v]) => {
                    const typeMap = {silent:{icon:'🔇',name:'静默型',color:'#3b82f6'},reverse_cover:{icon:'🔄',name:'反向掩护',color:'#ef4444'},heat_trap:{icon:'🔥',name:'造热陷阱',color:'#f59e0b'},unknown:{icon:'❓',name:'未知',color:'#6b7280'}};
                    const t = typeMap[k] || typeMap.unknown;
                    return `<div style="text-align:center;min-width:80px"><div style="font-size:22px;font-weight:bold;color:${t.color}">${v}</div><div style="font-size:11px;color:#64748b">${t.icon} ${t.name}</div></div>`;
                }).join('')}
                ${total === 0 ? '<div style="color:#64748b;font-size:13px;padding:20px;text-align:center">暂无冷门记录。<br/>每当你复盘一场预测错误的比赛时，系统会自动检测是否为爆冷并加入此库。</div>' : ''}
            </div>`;
        
        if (upsets.length > 0) {
            // 按类型分组
            const grouped = {};
            upsets.forEach(u => {
                const t = u.upset_type || 'unknown';
                if (!grouped[t]) grouped[t] = [];
                grouped[t].push(u);
            });
            
            Object.keys(grouped).forEach(type => {
                var items = grouped[type];
                const tc = {silent:{bg:'#1e3a5f',bd:'#3b82f6',tx:'#93c5fd',icon:'🔇',cn:'静默型：赔率完全不动'},
                           reverse_cover:{bg:'#3f2a2a',bd:'#ef4444',tx:'#fca5a5',icon:'🔄',cn:'反向掩护：被排除方向实际打出'},
                           heat_trap:{bg:'#3f3510',bd:'#f59e0b',tx:'#fcd34d',icon:'🔥',cn:'造热陷阱：有预警但不够强'},
                           unknown:{bg:'#2d2d3a',bd:'#6b7280',tx:'#9ca3af',icon:'❓',cn:'未知类型'}}[type] || {bg:'#1e293b',bd:'#475569',tx:'#94a3b8',icon:'❓',cn:type};
                
                html += `
            <div style="margin-bottom:18px">
                <h3 style="color:${tc.tx};font-size:15px;margin-bottom:8px">${tc.icon} ${tc.cn} (${items.length}场)</h3>
                <div style="overflow-x:auto">
                <table style="width:100%;border-collapse:collapse;font-size:12px">
                    <thead><tr style="background:#1e293b;color:#94a3b8">
                        <th style="padding:6px 8px;text-align:left">比赛</th>
                        <th>联赛</th>
                        <th>预测→实际</th>
                        <th>比分</th>
                        <th>赔率</th>
                        <th>置信度</th>
                        <th>竞彩变向</th>
                        <th>时间</th>
                    </tr></thead>`;
                
                items.forEach(u => {
                    const dirCn = {home:'主胜',draw:'平局',away:'客胜'}[u.actual_result]||'?';
                    const fp = u.odds_fingerprint || {};
                    html += `<tr style="border-bottom:1px solid #1e293b;background:${tc.bg}33">
                        <td style="padding:6px 8px;color:#e2e8f0;white-space:nowrap">${u.home_team}<br/><span style="color:#64748b;font-size:11px">vs ${u.away_team}</span></td>
                        <td style="color:#94a3b8;text-align:center;font-size:11px">${u.league||'-'}</td>
                        <td style="text-align:center"><span style="color:#64748b">${u.prediction||'?'}</span> → <b style="color:#f87171">${dirCn}</b>${u.was_excluded?'<br/><span style="color:#fbbf24;font-size:10px">(被排除)</span>':''}</td>
                        <td style="text-align:center;font-weight:bold;color:#fca5a5">${u.actual_score||'?'}</td>
                        <td style="text-align:center;color:#fbbf24">${u.upset_odds||'?'}</td>
                        <td style="text-align:center;color:${u.confidence>=4?'#4ade80':u.confidence>=2?'#fbbf24':'#64748b'}">${u.confidence||0}★</td>
                        <td style="text-align:center;font-size:11px;font-family:monospace;color:${fp.jc_pattern==='NNN'?'#60a5fa':'#94a3b8'}">${fp.jc_pattern||'-'}</td>
                        <td style="color:#475569;font-size:10px;text-align:center">${u.record_time||''}</td>
                    </tr>`;
                });
                
                html += `</table></div></div>`;
            });
        }
        
        html += '</div>';
        
        document.getElementById('detailContent').innerHTML = html;
        document.getElementById('detailPanel').classList.add('show');
    } catch(e) {
        console.error('加载冷门库失败:', e);
    }
}

// ========================================
// 📚 历史复盘浏览
// ========================================
async function showReviewPage() {
    try {
        const res = await api('/api/reviews');
        if (!res.success) return;
        
        const reviews = res.data || [];
        reviews.sort((a,b) => (b.review_time||'').localeCompare(a.review_time||''));
        
        let correctCount = reviews.filter(r => r.is_correct).length;
        let html = `
    <button class="detail-close" onclick="closeDetail()" style="position:absolute;top:12px;right:16px;z-index:10">
    <div style="padding:24px;padding-top:8px">
            <h2 style="color:#e2e8f0;font-size:20px;margin-bottom:4px">📚 历史复盘记录</h2>
            <p style="color:#64748b;font-size:13px;margin-bottom:16px">
                共 ${reviews.length} 条 · 命中 ${correctCount}/${reviews.length}(${reviews.length?Math.round(correctCount/reviews.length*100):0}%)
            </p>`;
            
        if (reviews.length === 0) {
            html += `<div style="color:#64748b;padding:30px;text-align:center">暂无复盘记录。在比赛列表中点击"复盘"按钮即可添加。</div>`;
        } else {
            html += `<div style="overflow-x:auto">
            <table style="width:100%;border-collapse:collapse;font-size:12px">
                <thead><tr style="background:#1e293b;color:#94a3b8">
                    <th style="padding:6px 8px;text-align:left">比赛</th>
                    <th>预测</th>
                    <th>结果</th>
                    <th>状态</th>
                    <th>置信度</th>
                    <th>排除方向</th>
                    <th>时间</th>
                </tr></thead>`;
            
            reviews.slice(0, 50).forEach(r => {
                const hitTag = r.is_correct ? 
                    '<span style="color:#4ade80">✅</span>' : '<span style="color:#f87171">❌</span>';
                html += `<tr style="border-bottom:1px solid #1e293b">
                    <td style="padding:6px 8px;white-space:nowrap;color:#e2e8f0">${r.home_team} vs ${r.away_team}<br/><span style="color:#64748b;font-size:10px">${r.league||'·'} ${r.match_id||''}</span></td>
                    <td style="text-align:center;color:#94a3b8">${r.prediction||'?'}</td>
                    <td style="text-align:center;color:#e2e8f0;font-weight:bold">${r.result_cn||'?'}</td>
                    <td style="text-align:center">${hitTag}</td>
                    <td style="text-align:center;color:${(r.confidence||0)>=4?'#4ade80':'#94a3b8'}">${r.confidence||0}★</td>
                    <td style="text-align:center;font-size:11px;color:#64748b">${(r.exclusions||[]).join('/')||'无'}</td>
                    <td style="color:#475569;font-size:10px">${r.review_time||''}</td>
                </tr>`;
            });
            
            if (reviews.length > 50) {
                html += `<tr><td colspan="7" style="text-align:center;color:#64748b;padding:8px">... 还有${reviews.length-50}条更早的记录</td></tr>`;
            }
            html += `</table></div>`;
        }
        
        html += '</div>';
        
        document.getElementById('detailContent').innerHTML = html;
        document.getElementById('detailPanel').classList.add('show');
    } catch(e) {
        console.error('加载复盘失败:', e);
    }
}

// 初始化（日期按钮已由服务端渲染）

// 页面加载时立即显示版本号
(async function() {
    try {
        const verRes = await api('/api/version');
        const el = document.getElementById('versionInfo');
        if (el && verRes.success) {
            el.textContent = '[V' + verRes.version + '] | 构建: ' + verRes.build_time;
        }
    } catch(e) {}
})();

// ESC关闭详情面板
document.addEventListener('keydown', e => { if (e.key==='Escape') closeDetail(); });
