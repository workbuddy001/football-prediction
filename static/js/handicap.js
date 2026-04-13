/**
 * 让球盘相似案例分析模块（独立JS文件）
 * 依赖：主页面已定义的 api() 函数和全局变量
 * 加载方式：<script src="/static/js/handicap.js"></script> （放在主script之后）
 *
 * 语法检查：node --check static/js/handicap.js
 */

(function() {
    'use strict';

    // ========== 配置 ==========
    var SIM_THRESHOLD = 40;   // 相似度门槛
    var MAX_CASES = 6;        // 最大显示案例数

    // ========== 工具函数 ==========
    function safeNum(v, def) {
        if (v === null || v === undefined || v === '') return def;
        var n = Number(v);
        return isNaN(n) ? def : n;
    }

    function esc(s) {
        var d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }

    /**
     * 渲染让球盘相似案例区块
     * @param {Object} res - 完整比赛分析数据
     */
    window.renderHandicapSimilar = function(res) {
        var raw = res.raw_data || {};
        var analysis = res.analysis || {};

        // 获取当前比赛ID和日期
        var matchId = res.match_id || raw.match_id || '';
        var dateFolder = res.date_folder || raw.date_folder || '';

        // 检查是否有让球盘数据
        var hc = String(raw.handicap || '');
        var jcOdds = raw.jc_odds || {};
        var hasHandicap = !!(hc && Object.keys(jcOdds).length > 0);

        // 如果没有让球盘，不显示该模块
        if (!hc) {
            return Promise.resolve(null);
        }

        var containerId = 'handicapSimilarSection';
        // 如果已有内容则先移除
        var existing = document.getElementById(containerId);
        if (existing) existing.remove();

        // 创建容器，插入到详情面板中合适位置
        var detailContent = document.getElementById('detailContent');
        if (!detailContent) return Promise.resolve(null);

        var section = document.createElement('div');
        section.id = containerId;
        section.innerHTML = '<div style="text-align:center;padding:30px;color:#94a3b8"><span class="spinner">⚖️</span> 正在匹配让球盘相似案例...</div>';

        // 找到详情内容区域的末尾插入
        detailContent.appendChild(section);

        // 调用API获取相似案例
        return api('/api/handicap-similar?match_id=' + encodeURIComponent(matchId) + '&date=' + encodeURIComponent(dateFolder))
            .then(function(hcRes) {
                if (!hcRes.success) {
                    section.innerHTML = '<div style="padding:15px;color:#f87171;text-align:center">⚠️ 让球盘相似案例加载失败：' + esc(hcRes.error || '未知错误') + '</div>';
                    return null;
                }

                var data = hcRes.data || {};
                var similar = data.similar || [];
                var summary = data.summary || {};
                var curHc = summary.current ? summary.current.handicap : hc;

                if (similar.length === 0) {
                    var noDataMsg = summary.message || ('未找到盘口「' + esc(curHc) + '」的相似历史案例');
                    section.innerHTML = '<div style="padding:20px;color:#94a3b8;text-align:center;font-size:13px">⚖️ 让球盘相似案例<br><span style="color:#64748b">' + esc(noDataMsg) + '</span></div>';
                    return null;
                }

                // 渲染完整结果
                section.innerHTML = buildHandicapHTML(similar, summary, curHc);
                return hcRes;
            })
            .catch(function(err) {
                section.innerHTML = '<div style="padding:15px;color:#f87171;text-align:center">⚠️ 加载出错：' + esc(err.message || '网络错误') + '</div>';
                return null;
            });
    };

    /**
     * 构建完整的让球盘相似案例 HTML
     */
    function buildHandicapHTML(similar, summary, curHc) {
        var html = '';

        // 标题栏
        html += '<div style="margin-top:25px;border-top:1px solid #334155;padding-top:20px">';
        html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">';
        html += '<span style="font-size:16px;font-weight:bold;color:#e2e8f0">⚖️ 让球盘相似案例</span>';
        html += '<span style="font-size:12px;color:#94a3b8;background:#1e293b;padding:3px 10px;border-radius:10px">当前盘口: ' + esc(curHc) + '</span>';
        html += '</div>';

        // 汇总统计条
        var s = summary;
        var hitRate = s.hit_rate || '0%';
        var pd = s.pred_dist || {"主胜": 0, "平局": 0, "客胜": 0};
        var ad = s.actual_dist || {"主胜": 0, "平局": 0, "客胜": 0};

        html += '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px;padding:10px 14px;background:#1e293b;border-radius:8px;border:1px solid #334155">';

        // 统计项
        html += statBadge('📊', similar.length + '条相似', '#3b82f6');
        html += statBadge('✅ 命中', (s.hit_count || 0) + '/' + similar.length, s.hit_count > similar.length / 2 ? '#22c55e' : '#ef4444');
        html += statBadge('📈 命中率', hitRate, '#a78bfa');

        // 预测分布
        var predParts = [];
        for (var k in pd) { if (pd[k] > 0) predParts.push(k + ':' + pd[k]); }
        if (predParts.length > 0) html += statBadge('🎯 预测', predParts.join(' '), '#f59e0b');

        // 实际分布
        var actParts = [];
        for (var k2 in ad) { if (ad[k2] > 0) actParts.push(k2 + ad[k2]); }
        if (actParts.length > 0) html += statBadge('📌 结果', actParts.join(' '), '#06b6d4');

        html += '</div>'; // 汇总统计条结束

        // 案例列表
        for (var i = 0; i < similar.length; i++) {
            html += buildCaseCard(similar[i], i + 1);
        }

        // 综合推理结论
        html += buildConclusion(similar, summary);

        html += '</div>'; // 主section结束

        return html;
    }

    /**
     * 单个统计徽章
     */
    function statBadge(emoji, text, color) {
        return '<span style="font-size:11px;padding:4px 10px;background:' + color + '18;color:' + color + ';border-radius:6px;border:1px solid ' + color + '30;white-space:nowrap">' + emoji + ' ' + esc(text) + '</span>';
    }

    /**
     * 构建单条案例卡片
     */
    function buildCaseCard(c, idx) {
        var isHit = c.is_correct === true;
        var score = c.score || 0;

        // 卡片头部颜色
        var borderColor = isHit ? '#22c55e50' : '#ef444450';
        var hitTag = isHit ? '<span style="background:#22c55e;color:#000;font-size:11px;padding:2px 8px;border-radius:4px;font-weight:bold">✓命中</span>' : '<span style="background:#ef4444;color:#fff;font-size:11px;padding:2px 8px;border-radius:4px">✗未中</span>';

        var h = '';
        h += '<div style="margin-bottom:12px;padding:14px;background:#16202e;border-radius:10px;border:1px solid ' + borderColor + '">';

        // 标题行
        h += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">';
        h += '<span style="font-size:13px;font-weight:600;color:#e2e8f0">案例#' + idx + ': ' + esc(c.home_team) + ' vs ' + esc(c.away_team) + '</span>';
        h += '<div style="display:flex;align-items:center;gap:8px">';
        h += '<span style="background:' + (score >= 60 ? '#22c55e30' : score >= 45 ? '#f59e0b30' : '#64748b30') + ';color:' + (score >= 60 ? '#22c55e' : score >= 45 ? '#f59e0b' : '#94a3b8') + ';font-size:12px;padding:2px 8px;border-radius:4px;font-weight:bold">' + score + '分</span>';
        h += hitTag;
        h += '</div></div>';

        // 匹配原因标签
        var reasons = c.reasons || [];
        if (reasons.length > 0) {
            h += '<div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:10px">';
            for (var ri = 0; ri < reasons.length; ri++) {
                h += '<span style="font-size:11px;background:#0ea5e918;color:#38bdf8;padding:2px 7px;border-radius:4px;border:1px solid #0ea5e928">' + esc(reasons[ri]) + '✓</span>';
            }
            h += '</div>';
        }

        // 让球赔率对比表
        h += buildOddsTable(c);

        // 近况对比
        if (c.form_home || c.form_away) {
            h += '<div style="margin-top:8px;display:flex;gap:12px;font-size:11px;color:#94a3b8">';
            h += '<span>主近况: <b style="color:#e2e8f0">' + esc(c.form_home || '?') + '</b></span>';
            h += '<span>客近况: <b style="color:#e2e8f0">' + esc(c.form_away || '?') + '</b></span>';
            h += '</div>';
        }

        // 预测 vs 实际
        var predText = (c.prediction || '') + (c.confidence ? ' ★'.repeat(Math.min(c.confidence, 5)) : '');
        var actualText = c.result_cn || c.actual_score || '-';
        h += '<div style="margin-top:8px;font-size:12px;display:flex;justify-content:space-between;padding:6px 10px;background:#0f172a66;border-radius:6px">';
        h += '<span>预测: <b style="color:#60a5fa">' + esc(predText) + '</b></span>';
        h += '<span>实际: <b style="' + (isHit ? 'color:#22c55e' : 'color:#ef4444') + '">' + esc(actualText) + '</b></span>';
        h += '</div>';

        // 推理文字
        h += buildCaseReasoning(c, score);

        h += '</div>'; // 卡片结束

        return h;
    }

    /**
     * 构建让球赔率对比紧凑表
     */
    function buildOddsTable(c) {
        var ho = c.hc_odds || {};
        var hHome = safeNum(ho.home, 0), hDraw = safeNum(ho.draw, 0), hAway = safeNum(ho.away, 0);
        var hcStr = c.handicap || '-';

        var hasData = hHome > 0 || hDraw > 0 || hAway > 0;

        var h = '<table style="width:100%;border-collapse:collapse;font-size:11px;margin:8px 0">';
        h += '<tr style="color:#64748b">';
        h += '<td style="padding:3px 6px;width:70px"></td>';
        h += '<td style="padding:3px 6px;text-align:center;width:22%">主</td>';
        h += '<td style="padding:3px 6px;text-align:center;width:22%">平</td>';
        h += '<td style="padding:3px 6px;text-align:center;width:22%">客</td>';
        h += '</tr>';

        // 让球后赔率行（高亮）
        h += '<tr style="background:#1e3a2f;border:1px solid #22543d;border-radius:4px">';
        h += '<td style="padding:4px 6px;color:#4ade80;font-weight:bold;font-size:11px">★ 让球' + esc(hcStr) + '</td>';
        h += '<td style="padding:4px 6px;text-align:center;color:#e2e8f0;font-weight:600">' + (hHome > 0 ? hHome.toFixed(2) : '-') + '</td>';
        h += '<td style="padding:4px 6px;text-align:center;color:#e2e8f0">' + (hDraw > 0 ? hDraw.toFixed(2) : '-') + '</td>';
        h += '<td style="padding:4px 6px;text-align:center;color:#e2e8f0;font-weight:600">' + (hAway > 0 ? hAway.toFixed(2) : '-') + '</td>';
        h += '</tr>';

        if (!hasData) {
            h += '<tr><td colspan="4" style="padding:4px 6px;text-align:center;color:#64748b;font-size:10px">(老案例缺少让球赔率明细)</td></tr>';
        }

        h += '</table>';
        return h;
    }

    /**
     * 构建单条案例的推理文字
     */
    function buildCaseReasoning(c, score) {
        var isHit = c.is_correct === true;
        var msg = '';
        var color = '';
        var icon = '';

        if (score >= 65) {
            icon = '💡';
            if (isHit) { msg = '高度相似 · 该案例命中可作强正向参考'; color = '#22c55e'; }
            else { msg = '高度相似 · 但该案例未命中需谨慎参考'; color = '#f59e0b'; }
        } else if (score >= 50) {
            icon = '💡';
            if (isHit) { msg = '较接近 · 可作为一般参考'; color = '#60a5fa'; }
            else { msg = '较接近 · 但该案例未命中参考价值有限'; color = '#94a3b8'; }
        } else {
            icon = '📌';
            if (isHit) { msg = '基本匹配 · 有一定参考价值'; color = '#94a3b8'; }
            else { msg = '基本匹配 · 参考价值较低'; color = '#64748b'; }
        }

        // 教训提示
        var lessons = c.lessons || [];
        var lessonHtml = '';
        if (lessons.length > 0) {
            lessonHtml = '<div style="margin-top:4px;font-size:11px;color:#f87171">' + esc(lessons[0]) + '</div>';
        }

        return '<div style="margin-top:6px;padding:6px 10px;background:' + color + '10;border-left:3px solid ' + color + ';border-radius:0 6px 6px 0;font-size:12px;color:' + color + '">' + icon + ' ' + msg + lessonHtml + '</div>';
    }

    /**
     * 构建综合推理结论
     */
    function buildConclusion(similar, summary) {
        var total = similar.length;
        if (total === 0) return '';

        var hits = summary.hit_count || 0;
        var rate = hits / total;
        var maxScore = similar.length > 0 ? (similar[0].score || 0) : 0;

        // 统计最倾向的方向
        var dirCount = {"主胜": 0, "平局": 0, "客胜": 0};
        for (var i = 0; i < similar.length; i++) {
            var p = similar[i].prediction || '';
            for (var k in dirCount) {
                if (p.indexOf(k) !== -1) dirCount[k]++;
            }
        }
        var topDir = '无';
        var maxDir = 0;
        for (var k2 in dirCount) {
            if (dirCount[k2] > maxDir) { maxDir = dirCount[k2]; topDir = k2; }
        }

        // 结论级别判定
        var level, levelColor, advice;

        if (total >= 3 && rate >= 0.67 && maxScore >= 55) {
            level = '✅ 规律一致';
            levelColor = '#22c55e';
            advice = '历史相似案例命中率较高（' + Math.round(rate*100) + '%），最高相似度' + maxScore + '分。可重点参考主流预测方向「' + topDir + '」作为辅助判断依据。';
        } else if (total >= 3 && rate >= 0.5) {
            level = '⚠️ 中等信号';
            levelColor = '#f59e0b';
            advice = '历史案例命中率中等（' + Math.round(rate*100) + '%），规律不够强烈。可作为辅助参考但不作为主要决策依据。';
        } else if (total < 3) {
            level = '📊 样本不足';
            levelColor = '#94a3b8';
            advice = '仅找到' + total + '条相似案例，样本太少不具备统计意义。建议观望或仅作极弱参考。';
        } else {
            level = '🔄 结果分散';
            levelColor = '#64748b';
            advice = '案例较多但命中率低且方向分散，说明此类让球盘结构下结果不确定性高。不建议基于此做出倾向性判断。';
        }

        var h = '';
        h += '<div style="margin-top:16px;padding:14px;background:#1e293b;border-radius:10px;border:1px solid #334155">';
        h += '<div style="font-size:14px;font-weight:bold;color:#e2e8f0;margin-bottom:8px">📋 综合推理结论</div>';
        h += '<div style="display:inline-block;background:' + levelColor + '18;color:' + levelColor + ';padding:3px 12px;border-radius:6px;font-size:13px;font-weight:bold;margin-bottom:10px">' + level + '</div>';
        h += '<div style="font-size:13px;color:#cbd5e1;line-height:1.7">' + advice + '</div>';

        // 详细统计
        h += '<div style="margin-top:10px;font-size:11px;color:#64748b;line-height:1.6">';
        h += '· ' + total + '条案例中 ' + hits + '条命中（' + Math.round(rate*100) + '%）<br>';
        h += '· 最高相似度：' + maxScore + '分 | 主流方向：「' + topDir + '」（' + maxDir + '/' + total + '票）<br>';
        h += '· 数据来源：历史复盘库（共' + (summary.total_reviews || 0) + '条，其中' + (summary.has_handicap || 0) + '条有让球盘数据）';
        h += '</div>';

        h += '</div>';

        return h;
    }

})();
