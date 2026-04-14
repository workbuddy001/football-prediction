/**
 * 赛前情报分析模块 V4（完整重写版）
 * 功能：
 *   ① 赔率水位分析（不让球/标准1X2）
 *   ② 让球盘水位分析（六档水位+出口结构）
 *   ③ 赔付压力矩阵（标准盘×让球盘交叉对比）
 *   ④ 诱导/实盘防守检测（交叉验证）
 *   ④ 综合最终建议
 * 依赖：/api/pre-match-analysis 接口
 */
(function () {
    'use strict';

    // ==================== 颜色常量 ====================
    var C = {
        bg: '#0f172a',
        card: '#1e293b',
        border: '#334155',
        text: '#e2e8f0',
        textDim: '#94a3b8',
        home: '#3b82f6',
        away: '#f97316',
        good: '#22c55e',
        bad: '#ef4444',
        tip: '#f59e0b',
        strong: '#dc2626',
        medium: '#eab308',
        weak: '#9ca3af',
        alignGood: '#16a34a',
        conflictBad: '#ea580c',
        draw: '#a855f7'
    };

    // ==================== 工具函数 ====================
    function esc(s) { return String(s || '').replace(/&/g,'&').replace(/</g,'<').replace(/>/g,'>'); }
    
    function strengthBadge(strength) {
        var map = {'strong':'<span style="background:#7f1d1d;color:#fca5a5;padding:1px 6px;border-radius:4px;font-size:11px;font-weight:bold">强</span>','medium':'<span style="background:#854d0e;color:#fde047;padding:1px 6px;border-radius:4px;font-size:11px">中</span>','weak':'<span style="background:#374151;color:#9ca3b7;padding:1px 6px;border-radius:4px;font-size:11px">弱</span>'};
        return map[strength] || '';
    }

    function renderFactors(factors, isFavor) {
        if (!factors || factors.length === 0) return '<div style="color:'+C.textDim+';font-size:12px;padding:8px 0;text-align:center">暂无明显因素</div>';
        var h = '';
        for (var i = 0; i < factors.length; i++) {
            var f = factors[i], ic = isFavor ? C.good : C.bad, icon = isFavor ? '\u2705' : '\u274c';
            h += '<div style="padding:6px 10px;margin-bottom:4px;background:'+(isFavor?'#064e20':'#450a0a')+'30;border-radius:6px;border-left:3px solid '+ic+'"><span style="margin-right:6px">'+icon+'</span><span style="color:'+C.text+'">'+esc(f.text)+'</span> '+strengthBadge(f.strength)+'</div>';
        }
        return h;
    }

    function renderFormBar(form) {
        if (!form || !form.recent) return '';
        var dots = '', recent = form.recent;
        for (var j = 0; j < recent.length && j < 6; j++) {
            var ch = recent[j], color = ch === 'W' ? C.good : (ch === 'D' ? '#9ca3b7' : C.bad);
            dots += '<span style="display:inline-block;width:18px;height:18px;line-height:18px;text-align:center;border-radius:50%;background:'+color+'25;color:'+color+';font-weight:bold;font-size:11px;margin-right:3px">'+ch+'</span>';
        }
        return '<div>'+dots+'</div><div style="font-size:11px;color:'+C.textDim+';margin-top:4px">'+form.wins+'胜'+form.draws+'平'+form.losses+'负 | 胜率 '+form.rate+'%</div>';
    }

    function verdictStyle(level) {
        switch(level){
            case 'strong_align': return {bg:'#14532d',border:'#22c55e',text:'\u2705 高度一致 — 庄家意图与基本面共振，可信度较高',color:C.alignGood};
            case 'align': return {bg:'#1e3a28',border:'#86efac',text:'\u2713 基本一致 — 心水与基本面无冲突，可作正向参考',color:'#86efac'};
            case 'conflict': return {bg:'#451a03',border:'#fb923c',text:'\u26a0\ufe0f 方向矛盾！基本面与心水方向相反，庄家可能在利用基本面引导筹码',color:C.conflictBad};
            case 'neutral': return {bg:'#1e293b',border:'#94a3b8',text:'— 中立：双方势均力敌，需结合排除法综合判断',color:C.textDim};
            case 'no_tip': return {bg:'#172554',border:'#60a5fa',text:'\u2139 无明确心水推荐，以排除法为主',color:'#93c5fd'};
            default: return {bg:C.card,border:C.border,text:'',color:C.text};
        }
    }

    // ==================== 水位分类 ====================
    function classifyStdWater(o) {
        if (!o||isNaN(o)||o<=0) return {level:'-',text:'无数据',color:C.textDim,tier:-1};
        if(o>3.5) return {level:'超高水',text:'>3.5 玩家望而却步',color:'#ef4444',tier:6};
        if(o>=2.8) return {level:'高水',text:'2.8-3.5 高倍诱惑',color:'#f97316',tier:5};
        if(o>=2.45) return {level:'中庸',text:'2.45-2.8 无所适从/分散',color:'#eab308',tier:4};
        if(o>=1.80) return {level:'中水',text:'1.8-2.45 容易偏向',color:'#22c55e',tier:3};
        if(o>=1.50) return {level:'低水',text:'1.5-1.8 默认易出',color:'#3b82f6',tier:2};
        return {level:'超低水',text:'<1.5 概率很大但无肉',color:'#06b6d4',tier:1};
    }

    function classifyHcWater(o) {
        if(!o||o<=0) return {tier:0,level:'-',intent:'无数据',color:C.textDim};
        if(o>4.2) return {tier:6,level:'超高水',intent:'强阻 拉高让你不敢买',color:'#ef4444'};
        if(o>3.5) return {tier:5,level:'高水',intent:'微阻 轻度劝退',color:'#f97316'};
        if(o>2.8) return {tier:4,level:'中高水',intent:'博取高倍',color:'#eab308'};
        if(o>2.0) return {tier:3,level:'中低水',intent:'引 合理区间引导',color:'#22c55e'};
        if(o>1.5) return {tier:2,level:'低水',intent:'守 低赔实盘防守',color:'#3b82f6'};
        return {tier:1,level:'超低水',intent:'确 大概率方向',color:'#06b6d4'};
    }

    // ==================== 主渲染函数 ====================
    window.renderPreMatchAnalysis = function(res) {
        var raw = res.raw_data || {};
        var matchId = res.match_id || raw.match_id || '';
        var dateFolder = res.date_folder || raw.date_folder || '';

        if(!matchId||!dateFolder) return Promise.resolve(null);

        var containerId = 'preMatchSection';
        var existing = document.getElementById(containerId);
        if(existing) existing.remove();

        return api('/api/pre-match-analysis?match_id='+encodeURIComponent(matchId)+'&date='+encodeURIComponent(dateFolder)).then(function(pmRes) {
            if(!pmRes.success||!pmRes.data){ console.warn('赛前情报数据异常:',pmRes.error); return null; }

            var d=pmRes.data, mi=d.match_info, hf=d.home_factors, af=d.away_factors;
            var mc=d.macao, cc=d.conclusion, ed=d.engine_data||{};
            var detailContent = document.getElementById('detailContent');
            if(!detailContent) return null;

            var html='', excList=ed.exclusions||[], finalPred=ed.final_pred||'', conf=ed.confidence||0;

            // 赔付矩阵结论变量（函数级声明，在赔付矩阵块内赋值）
            var bestResult='', worstResult='', isPushedAwayBest=false;

            // ===== 标题栏 =====
            html+='<div id="'+containerId+'" style="margin-top:14px;background:'+C.card+';border:1px solid '+C.border+';border-radius:10px;overflow:hidden">';
            html+='<div style="display:flex;align-items:center;justify-content:space-between;padding:10px 14px;background:linear-gradient(135deg,#1e3a5f 0%,#1e293b 100%);border-bottom:1px solid '+C.border+'">';
            html+='<span style="font-weight:bold;font-size:15px">\ud83d\udd0d 赛前情报分析</span>';
            if(mi.handicap) html+='<span style="font-size:12px;color:#93c5fd;background:#1e3a5f;padding:3px 8px;border-radius:5px">盘口: '+mi.handicap+'</span>';
            else html+='<span style="font-size:12px;color:#94a3b8">标准盘</span>';
            html+='</div>';

            // ===== 近况对比 =====
            html+='<div style="padding:12px 14px;border-bottom:1px solid '+C.border+'">';
            html+='<div style="font-size:12px;color:'+C.tip+';font-weight:600;margin-bottom:8px">\ud83d\udcca 近期状态对比</div>';
            html+='<div style="display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:center">';
            html+='<div style="text-align:center"><div style="color:'+C.home+';font-weight:bold;margin-bottom:4px">'+esc(mi.home)+'</div>'+renderFormBar(d.form.home)+'</div>';
            html+='<div style="color:'+C.textDim+';font-weight:bold;font-size:13px;padding:0 4px">VS</div>';
            html+='<div style="text-align:center"><div style="color:'+C.away+';font-weight:bold;margin-bottom:4px">'+esc(mi.away)+'</div>'+renderFormBar(d.form.away)+'</div>';
            html+='</div>';

            // 让球赔率
            if(mi.hc_odds&&Object.keys(mi.hc_odds).length>0){
                var ho=mi.hc_odds;
                html+='<div style="margin-top:8px;padding:8px 10px;background:#1e3a5f30;border-radius:6px;border:1px solid #3b82f620">';
                html+='<div style="font-size:11px;color:#93c5fd;margin-bottom:4px">\u2696\ufe0f 竞彩让球赔率('+mi.handicap+'球)</div>';
                html+='<table style="width:100%;text-align:center;font-size:12px"><tr style="color:'+C.textDim+'"><td>主胜</td><td>平局</td><td>客胜</td></tr>';
                html+='<tr><td style="color:'+C.good+';font-weight:bold">'+esc(String(ho['胜']||ho.home||'-'))+'</td><td style="color:#9ca3b7;font-weight:bold">'+esc(String(ho['平']||ho.draw||'-'))+'</td><td style="color:'+C.bad+';font-weight:bold">'+esc(String(ho['负']||ho.away||'-'))+'</td></tr></table></div>';
            }

            // 历史交锋
            if(mi.h2h&&mi.h2h.trim()!=''){
                html+='<div style="margin-top:8px;padding:7px 10px;background:rgba(168,85,247,0.08);border-radius:6px;border-left:3px solid '+C.draw+'">';
                html+='<span style="font-size:11px;color:'+C.draw+';font-weight:600">\u2694 历史交锋：</span>';
                html+='<span style="font-size:12px;color:'+C.text+'">'+esc(mi.h2h)+'</span></div>';
            }
            html+='</div>'; // 近况结束

            // ===== 利好/利空因素 =====
            html+='<div style="padding:12px 14px;display:grid;grid-template-columns:1fr 1fr;gap:12px;border-bottom:1px solid '+C.border+'">';
            html+='<div><div style="font-size:13px;font-weight:600;margin-bottom:6px;color:'+C.home+'">\ud83c\udfe0 '+esc(mi.home)+' <span style="font-size:11px;font-weight:normal;color:'+(hf.net>=0?C.good:C.bad)+'">('+(hf.net>=0?'+':'')+hf.net+'分)</span></div>';
            html+='<div style="margin-bottom:6px"><div style="font-size:11px;color:'+C.good+';margin-bottom:3px">利好因素</div>'+renderFactors(hf.favors,true)+'</div>';
            html+='<div><div style="font-size:11px;color:'+C.bad+';margin-bottom:3px">利空因素</div>'+renderFactors(hf.unfavors,false)+'</div></div>';

            html+='<div><div style="font-size:13px;font-weight:600;margin-bottom:6px;color:'+C.away+'">\u2708\ufe0f '+esc(mi.away)+' <span style="font-size:11px;font-weight:normal;color:'+(af.net>=0?C.good:C.bad)+'">('+(af.net>=0?'+':'')+af.net+'分)</span></div>';
            html+='<div style="margin-bottom:6px"><div style="font-size:11px;color:'+C.good+';margin-bottom:3px">利好因素</div>'+renderFactors(af.favors,true)+'</div>';
            html+='<div><div style="font-size:11px;color:'+C.bad+';margin-bottom:3px">利空因素</div>'+renderFactors(af.unfavors,false)+'</div></div>';
            html+='</div>'; // 因素区域结束

            // ===== 分析引擎参考 =====
            var hasEngineData=ed.review_stats||(ed.cold_alerts&&ed.cold_alerts.length>0)||(ed.exclusions&&ed.exclusions.length>0);
            if(hasEngineData){
                html+='<div style="padding:12px 14px;border-bottom:1px solid '+C.border+'">';
                html+='<div style="font-size:12px;color:#f59e0b;font-weight:600;margin-bottom:8px">\ud83e\udd16 分析引擎参考</div>';

                // 复盘命中率
                var rs=ed.review_stats;
                if(rs&&rs.total>0){
                    var spDir=rs.same_prediction?rs.same_prediction.dir:'-', spRate=rs.same_prediction?rs.same_prediction.rate:0;
                    var spColor=spRate>=70?C.good:(spRate>=40?'#eab308':C.bad);
                    html+='<div style="background:'+(spRate>=50?'#064e2025':'#450a0a25')+';border-radius:6px;padding:8px 10px;margin-bottom:6px;border-left:3px solid '+(spRate>=50?C.good:C.bad)+'">';
                    html+='<span style="font-size:11px;font-weight:600;margin-right:4px">'+(spRate>=50?'\u2705':'\u274c')+'</span>';
                    html+='<span style="font-size:12px;color:'+C.text+'">历史复盘：总体命中率 <b>'+esc(rs.overall_rate+'%')+'</b>';
                    if(spDir&&spDir!='未预测') html+=' | 同预测「<b style="color:'+spColor+'">'+esc(spDir)+'</b>」命中 <b>'+esc(spRate+'%')+'</b>';
                    html+='</span></div>';
                }

                // 冷门预警
                var ca=ed.cold_alerts||[];
                for(var ci=0;ci<ca.length;ci++){
                    var alert=(typeof ca[ci]==='object')?ca[ci].detail||'':String(ca[ci]);
                    if(!alert)continue;
                    var isHighCold=alert.indexOf('冷门')!==-1||alert.indexOf('R8')!==-1||alert.indexOf('造热')!==-1;
                    var cLevel=isHighCold?'high':(alert.indexOf('掩护')!==-1?'medium':'weak');
                    html+='<div style="padding:6px 10px;margin-bottom:4px;background:#450a0a30;border-radius:6px;border-left:3px solid '+C.bad+'"><span>\u26a0\ufe0f</span> <span style="font-size:11.5px;color:'+C.text+'">'+esc(alert)+'</span> '+strengthBadge(cLevel)+'</div>';
                }

                // 排除引擎
                if(excList.length>0){
                    var dm={home:'主胜',draw:'平局',away:'客胜'}, excText=excList.map(function(e){return dm[e]||e;}).join('/');
                    html+='<div style="padding:6px 10px;margin-bottom:4px;background:#064e2030;border-radius:6px;border-left:3px solid '+C.good+'"><span>\u2705</span> <span style="font-size:11.5px;color:'+C.text+'">排除法排除 <b style="color:'+C.good+'">'+esc(excText)+'</b>，剩余 <b>'+(3-excList.length)+'</b> 个方向</span> '+strengthBadge(excList.length>=2?'strong':'medium')+'</div>';
                }
                if(finalPred){
                    var pdn={home:'主胜',draw:'平局',away:'客胜'}[finalPred]||finalPred;
                    var stars='\u2605'.repeat(conf), ihc=conf>=4;
                    html+='<div style="padding:6px 10px;background:'+(ihc?'#064e2025':'#17255425')+';border-radius:6px;border-left:3px solid '+(ihc?C.alignGood:'#60a5fa')+'"><span style="font-size:11.5px;color:'+C.text+'">'+(ihc?'\ud83d\udd25':'\u26a0\ufe0f')+' 排除法预测：<b style="color:'+(ihc?C.alignGood:C.tip)+'">'+esc(pdn)+'</b> '+stars+'</span></div>';
                }
                html+='</div>'; // 引擎区域结束
            }

            // ===== 澳门心水 + 综合推理结论 =====
            html+='<div style="padding:12px 14px">';

            // 澳门心水
            if(mc.tip){
                html+='<div style="background:#42200625;border:1px solid #78350f40;border-radius:8px;padding:10px 12px;margin-bottom:10px">';
                html+='<div style="font-size:12px;color:'+C.tip+';font-weight:600;margin-bottom:4px">\ud83d\udcb0 澳门心水</div>';
                html+='<div style="font-size:13px;color:'+C.text+';margin-bottom:4px">'+esc(mc.tip_text)+'</div>';
                if(mc.analysis&&mc.analysis.length>0) html+='<div style="font-size:11px;color:'+C.textDim+';line-height:1.5">'+esc(mc.analysis.substring(0,200))+(mc.analysis.length>200?'...':'')+'</div>';
                html+='</div>';
            }

            // ===== 综合推理结论容器 =====
            var vs=verdictStyle(cc.verdict_level);
            html+='<div style="background:'+vs.bg+';border:1px solid '+vs.border+'40;border-radius:8px;padding:12px 14px">';
            html+='<div style="font-size:13px;font-weight:600;margin-bottom:8px;color:'+vs.color+'">\ud83d\udccb 综合推理结论（水位分析）</div>';

            // ========== Step 1: 标准盘赔率（不让球）= 竞彩官方即时赔率 ==========
            // 数据优先级：standard_odds → realtime_odds竞彩行(index 0/1) → 遍历找有效行
            var _stdOdds=d.standard_odds||{};
            var stdHome=parseFloat(_stdOdds.home)||0, stdDraw=parseFloat(_stdOdds.draw)||0, stdAway=parseFloat(_stdOdds.away)||0;

            // 尝试从 realtime_odds 取竞彩官方即时赔率（更准确）
            if(stdHome===0&&stdDraw===0&&stdAway===0){
                var _rtOdds=raw.realtime_odds;
                if(_rtOdds&&Array.isArray(_rtOdds)){
                    // 竞彩通常在index 0或1（跳过注释行），格式:[主胜,平局,客胜]
                    var _jcRow=null;
                    for(var _jci=0;_jci<Math.min(5,_rtOdds.length);_jci++){
                        var _jr=_rtOdds[_jci];
                        if(_jr&&Array.isArray(_jr)&&_jr.length>=3&&!isNaN(parseFloat(_jr[0]))&&parseFloat(_jr[0])>0){
                            _jcRow=_jr; break;
                        }
                    }
                    if(_jcRow){
                        stdHome=parseFloat(_jcRow[0]); stdDraw=parseFloat(_jcRow[1]); stdAway=parseFloat(_jcRow[2]);
                    }
                    // 最后兜底：取index 0
                    if(stdHome===0&&_rtOdds.length>0){
                        var _r0=_rtOdds[0];
                        if(_r0&&Array.isArray(_r0)&&_r0.length>=3&&!isNaN(parseFloat(_r0[0]))){
                            stdHome=parseFloat(_r0[0]); stdDraw=parseFloat(_r0[1]); stdAway=parseFloat(_r0[2]);
                        }
                    }
                }
            }

            html+='<div style="margin-bottom:10px"><span style="font-size:11.5px;color:#93c5fd;font-weight:600">\u2460 赔率水位分析（不让球）</span></div>';
            html+='<table style="width:100%;border-collapse:collapse;text-align:center;font-size:11.5px;margin-bottom:8px">';
            html+='<tr style="color:'+C.textDim+';border-bottom:1px solid '+C.border+'"><td style="padding:5px">方向</td><td>赔率</td><td>水位</td><td>含义</td></tr>';

            var dirs=[{name:'主胜',odds:stdHome,color:C.home},{name:'平局',odds:stdDraw,color:C.draw},{name:'客胜',odds:stdAway,color:C.away}];
            for(var di=0;di<dirs.length;di++){
                var dd=dirs[di], wc=classifyStdWater(dd.odds);
                html+='<tr style="border-bottom:1px solid '+C.border+'20"><td style="padding:5px;color:'+dd.color+';font-weight:bold">'+dd.name+'</td>';
                html+='<td style="padding:5px;color:'+C.text+';font-weight:bold;font-size:13px">'+(dd.odds?dd.odds.toFixed(2):'-')+'</td>';
                html+='<td style="padding:5px;color:'+wc.color+';font-weight:bold">'+wc.level+'</td>';
                html+='<td style="padding:5px;color:'+C.textDim+'">'+wc.text+'</td></tr>';
            }
            html+='</table>';

            // 庄家意图
            var intentHtml='';
            if(stdHome>0&&stdAway>0){
                var gap=Math.abs(stdHome-stdAway), lo=Math.min(stdHome,stdAway), hi=Math.max(stdHome,stdAway);
                if(gap<0.3&&stdDraw>2.45&&stdDraw<3.5) intentHtml='主客实力接近，平赔处于中庸区间，庄家通过中庸赔率分散投注，平局打出概率不低。';
                else if(lo<1.50){var fd=stdHome<stdAway?'主队':'客队'; intentHtml=fd+'超低水（'+lo.toFixed(2)+'），基本面悬殊极大，庄家不给肉，玩家默认该方向打出概率大。'}
                else if(lo<1.80){var fd2=stdHome<stdAway?'主队':'客队'; intentHtml=fd2+'低水（'+lo.toFixed(2)+'），基本面有优势但不碾压，庄家低水防御实盘。'}
                else if(hi>2.8) intentHtml='高水方向存在诱惑空间，需警惕是否为造热陷阱。';
                else intentHtml='各方向水位分布均匀，无极端值，比赛不确定性较高。';
            }
            if(intentHtml){
                html+='<div style="background:#17255430;border-radius:6px;padding:7px 10px;margin-bottom:10px;border-left:3px solid #60a5fa">';
                html+='<span style="font-size:11px;color:#60a5fa;font-weight:600">\ud83d\dca1 庄家意图：</span>';
                html+='<span style="font-size:11.5px;color:'+C.text+'">'+esc(intentHtml)+'</span></div>';
            }

            // ========== Step 2: 让球盘赔率 ==========
            var hcData=mi.hc_odds, hcH=0, hcD=0, hcA=0, hasHc=false;
            if(hcData&&Object.keys(hcData).length>0){
                hcD=parseFloat(hcData['平']||hcData.draw||hcData['draw']||0)||parseFloat(hcData.h_draw||0);
                hcH=parseFloat(hcData['胜']||hcData.home||hcData['home']||0)||parseFloat(hcData.h_win||0);
                hcA=parseFloat(hcData['负']||hcData.away||hcData['away']||0)||parseFloat(hcData.h_away||0);
                hasHc=(hcH>0||hcD>0||hcA>0);
            }

            if(hasHc){
                html+='<div style="margin-bottom:6px"><span style="font-size:11.5px;color:#93c5fd;font-weight:600">\u2461 让球盘水位分析('+(mi.handicap||'?')+'球)</span></div>';
                html+='<table style="width:100%;border-collapse:collapse;text-align:center;font-size:11.5px;margin-bottom:8px">';
                html+='<tr style="color:'+C.textDim+';border-bottom:1px solid '+C.border+';"><td style="padding:4px">方向</td><td>赔率</td><td>水位档</td><td>庄家意图</td></tr>';

                var hDirs=[{name:'让球后主胜',odds:hcH,color:C.home},{name:'让球后平',odds:hcD,color:C.draw},{name:'让球后客胜',odds:hcA,color:C.away}];
                for(var hi=0;hi<hDirs.length;hi++){
                    var hd=hDirs[hi], hw=classifyHcWater(hd.odds);
                    html+='<tr style="border-bottom:1px solid '+C.border+'20"><td style="padding:5px;color:'+hd.color+';font-weight:bold">'+hd.name+'</td>';
                    html+='<td style="padding:5px;color:'+C.text+';font-weight:bold;font-size:13px">'+(hd.odds?hd.odds.toFixed(2):'-')+'</td>';
                    html+='<td style="padding:5px;color:'+hw.color+';font-weight:bold">'+hw.level+'</td>';
                    html+='<td style="padding:5px;color:'+C.textDim+'">'+hw.intent+'</td></tr>';
                }
                html+='</div>';

                // 深度解读 + 出口结构
                var tH=classifyHcWater(hcH), tD=classifyHcWater(hcD), tA=classifyHcWater(hcA);
                var tierH=tH.tier, tierD=tD.tier, tierA=tA.tier;
                var lowDirs=[], midCount=0, highCount=0;
                if(tierH<=2) lowDirs.push('主胜('+hcH.toFixed(2)+')');
                if(tierD<=2) lowDirs.push('平('+hcD.toFixed(2)+')');
                if(tierA<=2) lowDirs.push('客胜('+hcA.toFixed(2)+')');
                if(tierH>=3&&tierH<=4) midCount++; if(tierD>=3&&tierD<=4) midCount++; if(tierA>=3&&tierA<=4) midCount++;
                if(tierH>=5) highCount++; if(tierD>=5) highCount++; if(tierA>=5) highCount++;

                var exitType='', exitDir='';
                if(lowDirs.length===1&&highCount>=1){exitType='single';exitDir=lowDirs[0];}
                else if(lowDirs.length>=2){exitType='double';}
                else if(midCount>=2){exitType='scatter';}
                else{exitType='blocked';}

                var interpParts=[];
                if(hcH>0) interpParts.push('让球后主胜'+hcH.toFixed(2)+'('+tH.level+'):'+(tierH>=5?'超高水=阻盘':(tierH>=3?'高水=诱导区':'在愿意买区间'+(tierH<=2?'，正常引导':''))));
                if(hcD>0) interpParts.push('让球后平'+hcD.toFixed(2)+'('+tD.level+'):'+(tierD>=5?'超高水=阻盘，平局被劝退':(tierD>=3?'高水/中庸':'在合理区间')));
                if(hcA>0) interpParts.push('让球后客胜'+hcA.toFixed(2)+'('+tA.level+'):'+(tierA>=5?'超高水=阻，受让方难翻盘':(tierA>=3?'中庸/高水':'在愿意买区间，被看好')));

                var exitLabel='';
                if(exitType==='single') exitLabel='<b>\ud83e\udeaa <span style="color:#f97316">出口结构：单出口</span></b> \u26a0\ufe0f 筹码被迫集中到 '+esc(exitDir);
                else if(exitType==='double') exitLabel='<b>\ud83e\udeaa <span style="color:#22c55e">出口结构：双出口</span></b> \u2705 筹码分流，无显而易见的引导';
                else if(exitType==='scatter') exitLabel='<b>\ud83e\udeaa <span style="color:#eab308">出口结构：分散</span></b> 各方向均在中庸区，确定性低';
                else exitLabel='<b>\ud83e\udeaa <span style="color:#94a3b8">出口结构：封锁</span></b> 全方向高水/超高水，玩家难下手';

                html+='<div style="background:#17255430;border-radius:6px;padding:8px 10px;margin-bottom:10px;border-left:3px solid #60a5fa">';
                html+='<span style="font-size:11px;color:#93c5fd;font-weight:600">\u2696\ufe0f 让球盘深度解读：</span>';
                html+='<span style="font-size:11.5px;color:'+C.text+'">'+interpParts.join('<br>')+'</span>';
                html+='<div style="margin-top:6px">'+exitLabel+'</div></div>';

            // ========== Step ③: 赔付压力矩阵 ==========
            if(stdHome>0&&stdDraw>0&&stdAway>0){
                html+='<div style="margin-bottom:10px"><span style="font-size:11.5px;color:#93c5fd;font-weight:600">\u2462 \u8d54\u4ed8\u538b\u529b\u77e9\u9635\uff08\u6807\u51c6\u76d8 \u00d7 \u8ba9\u7403\u76d8\uff09</span></div>';
                html+='<table style="width:100%;border-collapse:collapse;text-align:center;font-size:11px;margin-bottom:8px">';
                html+='<tr style="color:'+C.textDim+';border-bottom:1px solid '+C.border+'">';
                html+='<td style="padding:4px">\u8d5b\u679c</td><td>\u6807\u51c6\u76d8</td><td>\u8ba9\u7403\u76d8</td><td>\u7efc\u5408\u8d54\u4ed8\u5206</td><td>\u5e94\u4ed8\u538b\u529b</td></tr>';

                // 赔付矩阵：根据盘口正负决定每个赛果的让球赔付
                // 正盘口(+1/+0.5)=主队受让，负盘口(-1/-0.5)=主队让球
                var _hcp=parseFloat(mi.handicap||'0')||0;
                var _posHcp=_hcp>0;  // true=受让(如+1), false=让球(如-1)
                var p1_std=stdHome, p2_std=stdDraw, p3_std=stdAway;
                var p1_hc, p2_hc, p3_hc;

                if(_posHcp){
                    // === 受让盘(如+1)：主队加球 ===
                    // 实际主胜 → 加球后更大优势 → 让球后主胜=hcH
                    // 实际平局 → 加球后主队领先 → 让球后主胜=hcH
                    // 实际客胜(1球差) → 加球后平手 → 让球后平=hcD
                    // 实际客胜(≥2球) → 加球后仍输 → 让球后客胜=hcA (保守取中间)
                    p1_hc=hcH;           // 主胜→让球后主胜
                    p2_hc=hcH;           // 平局→让球后主胜(受让变胜)
                    p3_hc=(Math.abs(_hcp)>=1)?hcD:hcA;  // 客胜→让球后平或客胜
                } else {
                    // === 让球盘(如-1)：主队减球 ===
                    // 实际主胜(大胜≥2球) → 减球后仍胜 → 让球后主胜=hcH
                    // 实际主胜(小胜1球) → 减球后平 → 让球后平=hcD
                    // 实际平局 → 减球后客队领先 → 让球后客胜=hcA
                    // 实际客胜 → 减球后更惨 → 让球后客胜=hcA
                    p1_hc=hcH;           // 主胜→让球后主胜
                    p2_hc=hcA;           // 平局→让球后客胜
                    p3_hc=hcA;           // 客胜→让球后客胜
                }

                function _payColor(odds){return odds<1.80?C.good:(odds<2.5?C.tip:(odds<3.5?C.warn:C.bad));}
                function _payTag(odds){return odds<1.80?'\u4f4e\u6c34\u2705':(odds<2.5?'\u4e2d\u6c34':(odds<3.5?'\u9ad8\u6c34\u26a0\ufe0f':'\u8d85\u9ad8\u274c'));}

                // 动态综合风险分：标准盘赔率 + 该赛果对应的竞彩让球赔率(p1_hc/p2_hc/p3_hc)
                // p1_hc/p2_hc/p3_hc 已通过赔付矩阵根据盘口正负映射完成
                function _payoutScore(direction){
                    var sOdds=(direction==='home'?p1_std:(direction==='draw'?p2_std:p3_std));
                    var hOdds=(direction==='home'?p1_hc:(direction==='draw'?p2_hc:p3_hc));

                    if(!hasHcData||!hOdds||hOdds<=0) return sOdds + 99;

                    // 标准盘60% + 让球盘40%
                    var baseScore=sOdds*0.6 + hOdds*0.4;

                    // 系数1：澳门心水系数（心水推的方向筹码多1.35倍）
                    var mcMult=1.0;
                    if(mcDir && mcDir===direction) mcMult=1.35;
                    else if(mcDir==='draw' && direction==='draw') mcMult=1.35;
                    else if(!mcDir || mcDir==='no_tip') mcMult=1.0;
                    else mcMult=1.0;

                    // 系数2：基本面倾斜系数（基本面倾向+每25分+10%上限30%，反向-每40分-20%下限80%）
                    var btMult=1.0;
                    var btGap=(hf.net!==undefined&&af.net!==undefined)?(af.net||0)-(hf.net||0):0;
                    if(bt2){
                        if(bt2===direction){
                            btMult=Math.min(1.3, 1+Math.abs(btGap)/25);
                        } else {
                            btMult=Math.max(0.8, 1-Math.abs(btGap)/40);
                        }
                    }

                    var finalScore = baseScore * mcMult * btMult;
                    console.log('[PAY_DEBUG] '+direction+' base='+baseScore.toFixed(2)+' mc='+mcMult.toFixed(2)+'(dir:'+mcDir+') bt='+btMult.toFixed(2)+'(t2:'+bt2+') → '+finalScore.toFixed(2));
                    return finalScore;
                }

                // 动态损益描述
                function _profitText(sOdds,hOdds,score,minScore,maxScore){
                    if(!hOdds||hOdds<=0)return '-';
                    var range=maxScore-minScore;
                    if(range<=0)range=1;

                    // 相对位置：得分越接近最低=庄家越想看到
                    var pos=(score-minScore)/range;  // 0=最优解, 1=最怕

                    if(pos<0.15)
                        return '<span style="color:'+C.good+'">\u5e94\u4ed8\u538b\u529b\u6700\u5c0f \u2705</span>';
                    else if(pos<0.35)
                        return '<span style="color:'+C.tip+'">\u5e94\u4ed8\u8f83\u5c0f \ud83d\udcc6</span>';
                    else if(pos<0.65)
                        return '<span style="color:'+C.warn+'">\u4e00\u8d54\u4e00\u8d58</span>';
                    else if(pos<0.85)
                        return '<span style="color:#fb923c">\u5e94\u4ed8\u8f83\u5927 \u26a0\ufe0f</span>';
                    else
                        return '<span style="color:'+C.bad+'">\u5e94\u4ed8\u538b\u529b\u6700\u5927 \u274c</span>';
                }

                // hasHcData 必须在 _payoutScore 调用之前定义（函数内部依赖此变量）
                var hasHcData=hasHc&&(hcH>0||hcD>0||hcA>0);

                // mcDir 和 bt2 也必须在 _payoutScore 调用之前定义（函数内部依赖这两个系数）
                var bt2=cc.basic_tendency||'';
                var mcHasRec=!!(mc&&mc.tip), mcDir='';
                if(mc && mc.tip_text){
                    var tt=mc.tip_text;
                    // 澳门格式固定为 "推荐「队名 賏/和/負」→"
                    // 正确做法：先提取队名（关键字前的文字），再判断属于主/客
                    var winChars=['\u8d0f','\u8d01','\u8cd0','\u8d62','\u80dc'];
                    var loseChars=['\u8d1f','\u8d1f\u5957'];  
                    var drawChars=['\u548c','\u5e73'];

                    // 提取关键字及其位置
                    var kwPos=-1, kwType='', foundChar='';
                    for(var ki=0;ki<winChars.length&&kwPos===-1;ki++){kwPos=tt.indexOf(winChars[ki]);if(kwPos!==-1){foundChar=winChars[ki];kwType='win';}}
                    for(var li=0;li<loseChars.length&&kwPos===-1;li++){kwPos=tt.indexOf(loseChars[li]);if(kwPos!==-1){foundChar=loseChars[li];kwType='lose';}}
                    for(var di=0;di<drawChars.length&&kwPos===-1;di++){kwPos=tt.indexOf(drawChars[di]);if(kwPos!==-1){foundChar=drawChars[di];kwType='draw';}}

                    if(kwPos>0){
                        // 提取关键字前面的队名部分（去掉前缀如 澳门推荐「 等）
                        var teamPart=tt.substring(0,kwPos).replace(/^[^\u4e00-\u9fff]*/,'').trim();
                        teamPart=teamPart.replace(/\s+$/,'');

                        if(teamPart && teamPart.length>=2){
                            // 智能队名匹配：处理长短名差异（曼彻斯特联 vs 曼联、赫塔费 vs 赫塔菲等）
                            function _matchTeam(mcName, pageName){
                                // 完全包含
                                if(mcName.indexOf(pageName)!==-1 || pageName.indexOf(mcName)!==-1) return true;
                                // 前2字匹配（覆盖绝大多数中文队名缩写：曼联/曼城/皇马等）
                                var mcPre2=mcName.substring(0,2), pgPre2=(pageName.length>=2?pageName.substring(0,2):pageName);
                                if(mcPre2===pgPre2) return true;
                                // 前1字+第2字交叉（曼彻 vs 曼联：首字相同）
                                if(mcName[0]===pageName[0]) return true;
                                return false;
                            }

                            if(_matchTeam(teamPart, mi.home)){
                                mcDir=(kwType==='win'?'home':(kwType==='lose'?'away':'draw'));
                            } else if(_matchTeam(teamPart, mi.away)){
                                mcDir=(kwType==='win'?'away':(kwType==='lose'?'home':'draw'));
                            } else {
                                // fallback
                                if(kwType==='win') mcDir='home';
                                else if(kwType==='lose') mcDir='away';
                                else mcDir='draw';
                            }
                        } else {
                            if(kwType==='win') mcDir='home';
                            else if(kwType==='lose') mcDir='away';
                            else mcDir='draw';
                        }
                    }
                    console.log('[MC_DEBUG] tip_text='+tt+' → teamPart="'+teamPart+'" type='+kwType+' → mcDir='+mcDir);
                }

                // [DEBUG] 显示mcDir和Unicode码位（上线前删除此段）
                var _debugTipText=(mc&&mc.tip_text)||'NULL';
                var _debugChars='';
                for(var _di=0;_di<_debugTipText.length;_di++){
                    var _dc=_debugTipText.charCodeAt(_di);
                    if(_dc>0x4E00){_debugChars+=_debugTipText[_di]+'=U+'+_dc.toString(16).toUpperCase()+' ';}
                }
                html+='<div style="font-size:10px;color:#f97306;background:#1e1e1e;padding:6px 8px;margin-bottom:4px;border-radius:4px;line-height:1.6">';
                html+='<b>[DEBUG]</b> mcDir=<b style="color:'+(mcDir?'#4ade80':'#ef4444')+'">'+(mcDir||'EMPTY')+'</b> | bt2='+(bt2||'EMPTY');
                html+='<br><b>\u4e2d\u6587\u5b57\u7b26\u7801\u4f4d:</b> '+_debugChars;
                html+='</div>';

                // 计算三个方向的得分（传入direction即可，内部自动取所有让球赔率）
                var sc1=_payoutScore('home');
                var sc2=_payoutScore('draw');
                var sc3=_payoutScore('away');
                var allScores=[sc1,sc2,sc3].filter(function(x){return x<99;});
                var minS=Math.min.apply(Math,allScores.length?allScores:[999]);
                var maxS=Math.max.apply(Math,allScores.length?allScores:[0]);

                html+='<tr style="border-bottom:1px solid '+C.border+'30">';
                html+='<td style="padding:5px;color:'+C.home+';font-weight:bold">'+mi.home+'\u80dc</td>';
                html+='<td style="padding:5px;font-weight:bold;color:'+_payColor(p1_std)+'">'+p1_std.toFixed(2)+' '+_payTag(p1_std)+'</td>';
                html+='<td style="padding:5px;font-weight:bold;color:'+(hasHcData?_payColor(p1_hc):C.textDim)+'">'+(hasHcData?p1_hc.toFixed(2):'-')+'</td>';
                html+='<td style="padding:5px;color:'+C.textDim+';font-size:10.5px">'+sc1.toFixed(2)+'\u5206'+(bt2==='home'?'<span style="color:#22c55e;margin-left:2px">\ud83d\udcc6</span>':(bt2==='away'?'<span style="color:#ef4444;margin-left:2px">\u2193</span>':''))+'</td>';
                html+='<td style="padding:5px;font-weight:bold">'+_profitText(p1_std,p1_hc,sc1,minS,maxS)+'</td></tr>';

                html+='<tr style="border-bottom:1px solid '+C.border+'30">';
                html+='<td style="padding:5px;color:'+C.draw+';font-weight:bold">\u5e73\u5c40</td>';
                html+='<td style="padding:5px;font-weight:bold;color:'+_payColor(p2_std)+'">'+p2_std.toFixed(2)+' '+_payTag(p2_std)+'</td>';
                html+='<td style="padding:5px;font-weight:bold;color:'+(hasHcData?_payColor(p2_hc):C.textDim)+'">'+(hasHcData?p2_hc.toFixed(2):'-')+'</td>';
                html+='<td style="padding:5px;color:'+C.textDim+';font-size:10.5px">'+sc2.toFixed(2)+'\u5206'+(mcDir==='draw'?'<span style="color:#f97316;margin-left:2px">\ud83d\udcc6\u5fc3\u6c34</span>':(bt2==='draw'?'<span style="color:#22c55e;margin-left:2px">\ud83d\udcc6</span>':''))+'</td>';
                html+='<td style="padding:5px;font-weight:bold">'+_profitText(p2_std,p2_hc,sc2,minS,maxS)+'</td></tr>';

                html+='<tr style="border-bottom:1px solid '+C.border+'30">';
                html+='<td style="padding:5px;color:'+C.away+';font-weight:bold">'+mi.away+'\u80dc</td>';
                html+='<td style="padding:5px;font-weight:bold;color:'+_payColor(p3_std)+'">'+p3_std.toFixed(2)+' '+_payTag(p3_std)+'</td>';
                html+='<td style="padding:5px;font-weight:bold;color:'+(hasHcData?_payColor(p3_hc):C.textDim)+'">'+(hasHcData?p3_hc.toFixed(2):'-')+'</td>';
                html+='<td style="padding:5px;color:'+C.textDim+';font-size:10.5px">'+sc3.toFixed(2)+'\u5206'+(bt2==='away'?'<span style="color:#22c55e;margin-left:2px">\ud83d\udcc6</span>':'')+'</td>';
                html+='<td style="padding:5px;font-weight:bold">'+_profitText(p3_std,p3_hc,sc3,minS,maxS)+'</td></tr>';
                html+='</table>';

                // 庄家最优解推演（基于动态得分）
                if(hasHcData){
                    var results=[];
                    results.push({name:mi.home+'\u80dc',std:p1_std,hc:p1_hc,score:sc1});
                    results.push({name:'\u5e73\u5c40',std:p2_std,hc:p2_hc,score:sc2});
                    results.push({name:mi.away+'\u80dc',std:p3_std,hc:p3_hc,score:sc3});
                    results.sort(function(a,b){return a.score-b.score;});
                    var best=results[0], worst=results[2];

                    html+='<div style="background:#064e2025;border-radius:6px;padding:7px 10px;margin-top:6px;border-left:3px solid #4ade80">';
                    html+='<span style="font-size:11px;color:#4ade80;font-weight:600">\ud83d\dcb0 \u5e84\u5bb6\u6700\u4f18\u89e3\uff1a</span>';
                    html+='<span style="font-size:11.5px;color:'+C.text+'">';
                    html+='\u7efc\u5408\u6700\u4f4e\u8d54\u4ed8 = <b style="color:#4ade80">'+best.name+'</b>(';
                    html+='\u6807\u51c6'+best.std.toFixed(2);
                    if(best.hc>0) html+ +'+\u8ba9\u7403'+best.hc.toFixed(2);
                    html+=')';

                    var bestIsHome=(best.name.indexOf(mi.home)!==-1);
                    var bestIsDraw=(best.name.indexOf('\u5e73')!==-1);
                    var bestDir=bestIsHome?'home':(bestIsDraw?'draw':'away');
                    // 赋值给外层变量（供综合判定使用）
                    bestResult=bestDir;
                    worstResult=(worst.name.indexOf(mi.home)!==-1)?'home':((worst.name.indexOf('\u5e73')!==-1)?'draw':'away');
                    var bestChgPct=(bestDir==='home'?((d.jc_home_chg||0)):(bestDir==='draw'?(d.jc_draw_chg||0):(d.jc_away_chg||0)));
                    var mcBestChg=(bestDir==='home'?((d.mcao_home_chg||0)):(bestDir==='draw'?(d.mcao_draw_chg||0):(d.mcao_away_chg||0)));

                    if(bestChgPct>3||mcBestChg>3){
                        isPushedAwayBest=true;  // 标记推离最优解
                        html+=' <span style="color:#f97316;font-size:10.5px;margin-left:4px">|</span> ';
                        html+='<span style="color:#f97316;font-size:11px;font-weight:600">\u26a0\ufe0f \u63a8\u79bb\u6700\u4f18\u89e3</span>';
                        html+='<span style="color:'+C.textDim+';font-size:10.5px">(\u7ade\u5f69';
                        if(bestChgPct>0) html+='+'+bestChgPct.toFixed(1)+'%'; else html+=bestChgPct.toFixed(1)+'%';
                        if(mcBestChg>0) html+=' \u6fb3\u95e8+'+mcBestChg.toFixed(1)+'%';
                        html+=')</span>';
                        html+='<br><span style="color:#fca5a5;font-size:10.5px">\u2192 \u62c9\u9ad8+\u8d54\u4ed8\u6700\u4f4e=\u5e84\u5bb6\u771f\u60f3\u770b\u5230\u7684\u7ed3\u679c</span>';
                    } else {
                        html+=' <span style="color:#4ade80;font-size:10.5px;margin-left:4px">|</span> ';
                        html+='<span style="color:'+C.textDim+';font-size:10.5px">\u8d54\u4ed8\u538b\u529b\u6700\u5c0f\u7684\u65b9\u5411</span>';
                    }
                    html+='</span></div>';

                    if(worst.score>5){
                        html+='<div style="background:#450a0a20;border-radius:6px;padding:5px 10px;margin-top:4px;border-left:3px solid #ef444480">';
                        html+='<span style="font-size:10.5px;color:#f87171">\u2620\ufe0f \u6700\u6015\uff1a'+worst.name+'</span>';
                        html+='<span style="color:'+C.textDim+';font-size:10px"> (\u6807\u51c6'+worst.std.toFixed(2);
                        if(worst.hc>0) html+ +'+\u8ba9\u7403'+worst.hc.toFixed(2);
                        html+=')</span></div>';
                    }
                } else {
                    var sResults=[
                        {name:mi.home+'\u80dc',odds:stdHome},
                        {name:'\u5e73\u5c40',odds:stdDraw},
                        {name:mi.away+'\u80dc',odds:stdAway}
                    ];
                    sResults.sort(function(a,b){return a.odds-b.odds;});
                    html+='<div style="background:#064e2025;border-radius:6px;padding:6px 10px;margin-top:4px;border-left:3px solid #4ade80">';
                    html+='<span style="font-size:11px;color:#4ade80;font-weight:600">\ud83d\dcb0 \u6807\u51c6\u76d8\u6700\u4f4e\u8d54\uff1a</span>';
                    html+='<span style="color:'+C.text+';font-size:11.5px"><b style="color:#4ade80">'+sResults[0].name+'</b>('+sResults[0].odds.toFixed(2)+') ';
                    if(sResults[2].odds>3.5) html+='<span style="color:'+C.textDim+';font-size:10px">|\u6700\u9ad8\u8d54\u4ed8='+sResults[2].name+'('+sResults[2].odds.toFixed(2)+')</span>';
                    html+='</span></div>';
                }
            }

            // ========== 交叉验证 ==========
                var refPred=finalPred||cc.basic_tendency||'';
                var hcValidCount=(hcH>0?1:0)+(hcD>0?1:0)+(hcA>0?1:0);

                // 赔付矩阵结论变量（已在上方赋值，此处只初始化isPushedAwayBest）
                isPushedAwayBest=false;

                html+='<div style="margin-bottom:6px"><span style="font-size:11.5px;color:#93c5fd;font-weight:600">\u2463 诱导 / 实盘防守检测（交叉验证）</span></div>';

                if(hcValidCount>=2&&refPred){
                    var jcMap={'home':{odds:hcH,name:'让球后主胜(赢盘)'},'draw':{odds:hcD,name:'让球后平'},'away':{odds:hcA,name:'让球后客胜(输盘)'}};
                    var jm=jcMap[refPred]||jcMap['away'], jco=jm.odds, jcn=jm.name, jcw=classifyHcWater(jco);
                    var predStdOdds=(refPred==='home'?stdHome:(refPred==='draw'?stdDraw:stdAway));
                    var predName={home:mi.home+'胜',draw:'平局',away:mi.away+'胜'}[refPred]||refPred;
                    var antiName=(refPred==='home'?mi.away+'胜':(refPred==='draw'?'平局':mi.home+'胜'));
                    var antiStdOdds=(refPred==='home'?stdAway:(refPred==='draw'?stdHome:stdHome));
                    var bt=cc.basic_tendency||'', btAgrees=(bt&&bt===refPred);
                    var isTrap=false, isAnomaly=false;

                    html+='<div style="background:#1a1a2e35;border-radius:8px;padding:10px 12px;margin-bottom:10px;border:1px solid #33415540">';

                    // A. 三重共振陷阱
                    if(exitType==='single'&&jcw.tier===3&&predStdOdds>2.45&&antiStdOdds<1.80&&btAgrees){
                        isTrap=true; isAnomaly=true;
                        html+='<div style="background:#450a0a50;border-radius:6px;padding:10px;margin-bottom:8px;border:1px solid #ef444480">';
                        html+='<div style="font-size:12px;color:#f87171;font-weight:bold;margin-bottom:6px">\u2622\ufe0f 三重共振陷阱警报</div>';
                        var bDir='', bOd=999;
                        if(stdHome>0&&stdHome<bOd){bDir='home';bOd=stdHome;} if(stdDraw>0&&stdDraw<bOd){bDir='draw';bOd=stdDraw;} if(stdAway>0&&stdAway<bOd){bDir='away';bOd=stdAway;}
                        var bn={home:mi.home+'胜',draw:'平局',away:mi.away+'胜'};
                        html+='<div style="font-size:11.5px;color:'+C.text+';line-height:1.8">';
                        html+='\u25b8 排除法预测 ['+predName+'] \u00d7 让球单出口 \u00d7 基本面 = <b style="color:#f87171">完美共振</b><br>';
                        html+='\u25b8 全市场筹码被引导到"显而易见"的方向 = 很好的引导效果<br>';
                        if(antiStdOdds>2.8) html+='\u25b8 \ud83d\udcb0 反向['+antiName+']标准盘='+antiStdOdds.toFixed(2)+'(高赔付)<br>';
                        html+='\u2605 应付最小方向 = <b style="color:#4ade80">'+bn[bDir]+'('+bOd.toFixed(2)+')</b>';
                        html+='</div>';
                        html+='<div style="margin-top:6px;font-size:11px;color:#fca5a5">参考：墨尔本城vs惠灵顿(2026-04-12)三重共振\u2192反向主胜2-0</div>';
                        html+='</div>';

                    } else if(exitType==='single'&&jcw.tier<=3&&predStdOdds>2.8){
                        isAnomaly=true;
                        html+='<div style="background:#42200640;border-radius:6px;padding:8px 10px;margin-bottom:6px;border-left:3px solid #f97316">';
                        html+='<span style="color:#fb923c;font-weight:bold;font-size:12px">\u26a0\ufe0f 交叉验证异常</span>';
                        html+='<span style="font-size:11.5px;color:'+C.text+';margin-left:6px">['+predName+']标准盘='+predStdOdds.toFixed(2)+'(高水) \u2192 应付压力大</span></div>';

                    } else if(jcw.tier>=5){
                        html+='<div style="background:#451a0330;border-radius:6px;padding:8px 10px;margin-bottom:6px;border-left:3px solid #f97316">';
                        html+='<span style="color:#f97316;font-weight:bold;font-size:12px">\u26a0\ufe0f 矛盾信号</span>';
                        html+='<span style="font-size:11.5px;color:'+C.text+';margin-left:6px">排除方向['+predName+']对应让球方向='+jco.toFixed(2)+'('+jcw.level+')</span></div>';

                    } else if(exitType==='double'&&jcw.tier<=3){
                        html+='<div style="background:#064e2030;border-radius:6px;padding:8px 10px;margin-bottom:6px;border-left:3px solid '+C.good+'">';
                        html+='<span style="color:'+C.good+';font-weight:bold;font-size:12px">\u2705 实盘防守</span>';
                        html+='<span style="font-size:11.5px;color:'+C.text+';margin-left:6px">['+predName+']让球对应='+jco.toFixed(2)+'('+jcw.level+') 双出口筹码分流</span></div>';

                    } else if(jcw.tier<=2){
                        html+='<div style="background:#17255430;border-radius:6px;padding:8px 10px;margin-bottom:6px;border-left:3px solid #3b82f6">';
                        html+='<span style="color:#3b82f6;font-weight:bold;font-size:12px">\u2705 应付合理</span>';
                        html+='<span style="font-size:11.5px;color:'+C.text+';margin-left:6px">['+predName+']让球对应='+jco.toFixed(2)+'('+jcw.level+')</span></div>';

                    } else {
                        html+='<div style="background:#1e293b30;border-radius:6px;padding:8px 10px;margin-bottom:6px"><span style="color:'+C.textDim+';font-size:11.5px">\ud83d\udccd 中性信号：['+predName+']\u2192让球'+jcn+'='+jco.toFixed(2)+'('+jcw.level+')</span></div>';
                    }

                    // 方向详情行
                    html+='<div style="margin-top:6px;padding:6px 8px;background:#0f172a40;border-radius:4px">';
                    html+='<span style="color:#ef4444;font-weight:bold">\ud83d\udf1b</span> ';
                    html+='<span style="font-size:11.5px;color:'+C.text+'">'+predName+' \u2192 '+jcn+' = <b style="color:'+jcw.color+'">'+jco.toFixed(2)+'</b>('+jcw.level+')</span>';
                    var oDirs=[];
                    if(refPred!=='home') oDirs.push('主胜('+hcH.toFixed(2)+','+tH.level+')');
                    if(refPred!=='draw') oDirs.push('平('+hcD.toFixed(2)+','+tD.level+')');
                    if(refPred!=='away') oDirs.push('客胜('+hcA.toFixed(2)+','+tA.level+')');
                    if(oDirs.length>0) html+='<br><span style="color:'+C.textDim+';font-size:11px">其他: '+oDirs.join(' + ')+'</span>';
                    html+='</div>';

                    // 基本面共振提示
                    if(bt) {
                        html+='<div style="margin-top:4px;font-size:11px">';
                        if(btAgrees) html+='<span style="color:#f87171">\u26a0\ufe0f 基本面倾向与预测一致\u2192筹码更集中</span>';
                        else html+='<span style="color:'+C.good+'">\u2714\ufe0f 基本面倾向['+({home:mi.home+'胜',draw:'平局',away:mi.away+'胜'}[bt])+']与预测分歧\u2192降低误导概率</span>';
                        html+='</div>';
                    }

                    // 标准盘交叉信息
                    if(stdHome>0){
                        html+='<div style="margin-top:6px;padding:6px 8px;background:#1e3a5f25;border-radius:4px;border-left:2px solid #60a5fa">';
                        html+='<span style="font-size:11px;color:#93c5fd;font-weight:600">\ud83d\udccc 标准盘交叉验证:</span><br>';
                        html+='<span style="font-size:11px;color:'+C.text+'">['+predName+']标准盘=';
                        if(predStdOdds>0){
                            var pc=predStdOdds<1.80?C.good:(predStdOdds>2.8?'#ef4444':'#eab308');
                            html+='<b style="color:'+pc+'">'+predStdOdds.toFixed(2)+'</b>';
                            html+=(predStdOdds<1.80?'(低水/应付压力小)':(predStdOdds>2.8?'(高赔付压力大!)':'(中水)'));
                            if(antiStdOdds>0&&antiStdOdds<predStdOdds) html+=' vs [反向]='+antiStdOdds.toFixed(2)+' <span style="color:#f87171">(更低!)</span>';
                        } else html+='-(无数据)';
                        html+='</span></div>';
                    }
                    html+='</div>'; // 交叉验证面板end

                    // ========== Step 5: 综合判定 + 最终建议 ==========
                    html+='<div style="margin-top:10px"><span style="font-size:11.5px;color:#93c5fd;font-weight:600">\u2463 综合判定</span></div>';
                    
                    var mcAgrees2=(mcDir&&mcDir===bt2);

                    html+='<div style="background:#0f172a45;border-radius:8px;padding:10px 12px;border-left:3px solid '+vs.border+'">';
                    
                    // 基本面
                    var btLbl=bt2?({home:mi.home+'胜',draw:'平局',away:mi.away+'胜'}[bt2]):'均衡';
                    var btColor = bt2 === 'home' ? C.home : (bt2 === 'draw' ? C.draw : (bt2 === 'away' ? C.away : C.textDim));
                    html+='<div style="font-size:12px;color:'+C.text+';margin-bottom:4px">基本面: <b style="color:'+btColor+'">'+esc(btLbl)+'</b></div>';
                    if(hf.net!==undefined||af.net!==undefined) html+=' &nbsp;<span style="color:'+C.textDim+';font-size:11px">('+(hf.net>=0?'+':'')+hf.net+'/'+(af.net>=0?'+':'')+af.net+')</span>';
                    html+='</div>';

                    // 澳门
                    if(mc.tip){
                        html+='<div style="font-size:12px;color:'+C.text+';margin-bottom:4px">\ud83d\udcb0 澳门: <b style="color:'+C.tip+'">'+esc(mc.tip_text)+'</b>';
                        if(bt2&&mcDir) html+=' <span style="font-size:10px">('+(mcAgrees2?'\u2192':'\u2208')+')</span>';
                        html+='</div>';
                    } else {
                        html+='<div style="font-size:12px;color:'+C.textDim+';margin-bottom:4px">\ud83d\udcb0 澳门: <span style="color:'+C.textDim+'">本期无明确的澳门心水推荐</span></div>';
                    }

                    // 排除法
                    if(finalPred){
                        var fpN2={home:mi.home+'胜',draw:'平局',away:mi.away+'胜'}[finalPred]||finalPred;
                        var fpColor = conf >= 4 ? C.alignGood : C.tip;
                        html+='<div style="font-size:12px;color:'+C.text+';margin-bottom:4px">\ud83e\udde0 排除: <b style="color:'+fpColor+'">'+esc(fpN2)+'</b> '+String.fromCharCode(9733).repeat(conf)+'</div>';
                    } else if(excList.length>0){
                        var dm2={home:'主胜',draw:'平局',away:'客胜'};
                        html+='<div style="font-size:12px;color:'+C.text+';margin-bottom:4px">\ud83e\udde0 排除: <b style="color:'+C.good+'">'+excList.map(function(e){return dm2[e]||e;}).join('/')+'</b></div>';
                    }

                    // 庄家赔付矩阵结论（核心！）
                    if(hasHc&&bestResult){
                        var brN={home:mi.home+'胜',draw:'平局',away:mi.away+'胜'}[bestResult]||bestResult;
                        var wrN={home:mi.home+'胜',draw:'平局',away:mi.away+'胜'}[worstResult]||worstResult;

                        // === 阻盘检测 ===
                        // 标准盘哪个方向赔率最低？如果该方向让球盘超高(>3.5)=阻盘
                        var stdLowest='home';
                        if(stdDraw>0 && stdDraw<stdHome && stdDraw<stdAway) stdLowest='draw';
                        else if(stdAway>0 && stdAway<stdHome && stdAway<=stdDraw) stdLowest='away';

                        var _lowStdOdds=(stdLowest==='home')?stdHome:(stdLowest==='draw'?stdDraw:stdAway);
                        var _lowHcOdds=(stdLowest==='home')?p1_hc:(stdLowest==='draw'?p2_hc:p3_hc);
                        var _isBlockedDir=(_lowStdOdds<=2.1 && _lowHcOdds>3.0);  // 标准盘低赔+让球盘高=阻
                        var _blockedName=(stdLowest==='home')?mi.home+'胜':((stdLowest==='draw')?'平局':mi.away+'胜');

                        html+='<div style="font-size:12px;color:'+C.text+';margin-bottom:4px">\ud83d\udcb8 庄家赔付: ';
                        if(_isBlockedDir){
                            // ★★★ 阻盘模式：标准盘最低赔方向被让球盘超高阻拦
                            html+='<b style="color:#f87171">'+esc(_blockedName)+'</b>';
                            html+=' <span style="color:#f87171;font-size:10.5px">(标准盘'+_lowStdOdds.toFixed(2)+'低赔\u274c但让球盘'+_lowHcOdds.toFixed(2)+'=</span>';
                            html+='<span style="color:#ef4444;font-weight:bold">\u963b\u76d8!)</span>';
                            if(bt2===stdLowest){
                                html+=' <span style="color:#22c55e;font-size:10px">+\u57fa\u672c\u9762\u540c\u5411=\u771f\u65b9\u5411</span>';
                            }
                        } else if(isPushedAwayBest){
                            html+='<b style="color:#22c55e">'+esc(brN)+'</b>';
                            html+=' <span style="color:#f97316;font-size:10.5px">(推离最优解! 庄家最想看到但劝退玩家)</span>';
                        } else {
                            html+='<b style="color:'+C.good+'">最优='+esc(brN)+' | 最怕='+esc(wrN)+'</b>';
                        }
                        html+='</div>';

                        // 赔付 vs 排除法 冲突检测
                        if(finalPred && finalPred !== bestResult){
                            html+='<div style="font-size:11px;color:#f97316;margin-bottom:4px;padding:3px 6px;background:#42200630;border-radius:3px">';
                            html+='<span>\u26a0\ufe0f 赔付最优('+esc(brN)+') \u2260 排除法('+esc(fpN2)+') \u2192 以赔付为准</span></div>';
                        } else if(finalPred && finalPred === bestResult && !isPushedAwayBest){
                            html+='<div style="font-size:11px;color:#22c55e;margin-bottom:4px"><span>\u2705 赔付与排除法一致 \u2192 双重确认</span></div>';
                        }
                    }

                    // 结论（五维综合：阻盘检测 > 推离最优解 > 基本面压制 > 赔付+排除法一致 > 赔付优先）
                    var reasonHtml='';
                    var finalVerdict='', finalColor=C.text;

                    if(isTrap&&isAnomaly){
                        reasonHtml='排除法\u00d7\u8ba9\u7403\u51fa\u53e3\u00d7\u57fa\u672c\u9762=\u5b8c\u7f8e\u5171\u632f \u2192 \u5e94\u5bf9\u53cd\u5411';
                        finalVerdict='reverse';
                        finalColor=C.warn;
                    }
                    else if(hasHc&&bestResult){
                        var brN={home:mi.home+'胜',draw:'平局',away:mi.away+'胜'}[bestResult]||bestResult;
                        var btGap=(hf.net!==undefined&&af.net!==undefined)?Math.abs((hf.net||0)-(af.net||0)):0;
                        var btFavorsBest=(bt2===bestResult);

                        // === 核心判定树 ===
                        // ① 阻盘模式（最高优先级）：标准盘低赔方向被让球盘超高水阻拦 + 基本面同向 = 真方向
                        if(_isBlockedDir && bt2===stdLowest){
                            reasonHtml='\u963b\u76d8\u6a21\u5f0f\uff01'+_blockedName+'\u88ab\u8ba9\u7403\u76d8\u8d85\u9ad8\u6c34\u963b\u62e6,\u57fa\u672c\u9762\u540c\u5411=\u771f\u65b9\u5411';
                            finalVerdict=bt2; finalColor='#22c55e';
                        }
                        // ② 推离最优解
                        else if(isPushedAwayBest){
                            // ★★★ 推离最优解：庄家拉高最低赔付方向 = 真方向
                            reasonHtml='\u63a8\u79bb\u6700\u4f18\u89e3\u2192\u5e84\u5bb6\u62c9\u9ad8'+brN+'(\u6700\u4f4e\u8d54\u4ed8)=\u771f\u65b9\u5411';
                            finalVerdict=bestResult;
                            finalColor='#22c55e';
                        }
                        else if(btGap>=6 && !btFavorsBest && bestResult){
                            // ⚠️ 基本面一面倒(差≥6分)且与赔付最优矛盾 → 基本面优先
                            var btN2={home:mi.home+'胜',draw:'平局',away:mi.away+'胜'}[bt2]||bt2;
                            reasonHtml='\u57fa\u672c\u9762\u5de7\u5dee('+btGap+'\u5206)\u503e\u5411'+btN2+',\u8d54\u4ed8\u6700\u4f18('+brN+')\u88ab\u57fa\u672c\u9762\u538b\u5236 \u2192 \u57fa\u672c\u9762\u4f18\u5148';
                            finalVerdict=bt2;
                            finalColor=bt2==='home'?C.home:(bt2==='draw'?C.draw:C.away);
                        }
                        else if(btGap>=4 && !btFavorsBest){
                            // ⚠️ 中等基本面差距(4-5分)，赔付最优可能被阻盘
                            var btN2={home:mi.home+'胜',draw:'平局',away:mi.away+'胜'}[bt2]||bt2;
                            // 检测阻盘：赔付最优方向在让球盘是否超高赔(>3.5)
                            var _bestHcOdds=(bestResult==='home')?hcH:(bestResult==='draw'?hcD:hcA);
                            var _isBlocked=_bestHcOdds>3.5;
                            if(_isBlocked){
                                reasonHtml='\u963b\u76d8\u68c0\u6d4b\uff1a\u8d54\u4ed8\u6700\u4f18('+brN+')\u8ba9\u7403\u76d8'+_bestHcOdds.toFixed(2)+'=\u8d85\u9ad8\u6c34\u963b\u76d8,\u57fa\u672c\u9762('+btN2+')\u66f4\u53ef\u9760';
                                finalVerdict=bt2;
                                finalColor=bt2==='home'?C.home:(bt2==='draw'?C.draw:C.away);
                            } else {
                                reasonHtml='\u57fa\u672c\u9762\u503e\u5411('+btN2+')\u4e0e\u8d58\u4ed8\u51b2\u7a81 \u2192 \u89c2\u671b/\u9632\u5e73';
                                finalVerdict='cautious';
                                finalColor=C.tip;
                            }
                        }
                        else if(finalPred && finalPred===bestResult){
                            reasonHtml='\u8d58\u4ed8\u6700\u4f18+\u6392\u9664\u6cd5\u53cc\u91cd\u786e\u8ba4';
                            finalVerdict=bestResult;
                            finalColor=C.good;
                        }
                        else if(finalPred && finalPred!==bestResult){
                            var fpN2={home:mi.home+'胜',draw:'平局',away:mi.away+'胜'}[finalPred]||finalPred;
                            // 小差距(<4分)：赔付优先
                            reasonHtml='\u8d58\u4ed8\u6700\u4f18('+brN+')\u4e0e\u6392\u9664\u6cd5('+fpN2+')\u51b2\u7a81 \u2192 \u4ee5\u8d58\u4ed8\u4e3a\u51c6';
                            finalVerdict=bestResult;
                            finalColor=C.good;
                        }
                        else {
                            reasonHtml=\u57fa\u4e8e\u8d58\u4ed8\u538b\u529b\u77e9\u9635;
                            finalVerdict=bestResult;
                            finalColor=C.good;
                        }

                        // 显示冲突提示（如果有的话）
                        if(!isPushedAwayBest && bt2 && bt2!==bestResult && btGap<6){
                            html+='<div style="font-size:10.5px;color:'+C.textDim+';margin-bottom:4px;padding:2px 6px;background:#222220;border-radius:3px">';
                            html+='<span>\ud83d\udcc6 \u57fa\u672c\u9762\u500e\u5411'+({home:mi.home+'胜',draw:'平局',away:mi.away+'胜'}[bt2])+'('+(hf.net||0)+'/'+(af.net||0)+')</span>';
                            html+='</div>';
                        }
                    }
                    else if(finalPred) reasonHtml='\u57fa\u4e8e\u6392\u9664\u6cd5\u5f15\u7406'+(excList.length>=2?'(\u6392\u96642\u65b9\u5411)':'');
                    else if(bt2) reasonHtml=mcHasRec?'基本面+'(mcAgrees2?'澳门同向':'澳门分歧'):'基于基本面倾向';

                    if(reasonHtml) html+='<div style="margin-top:6px;padding:6px 8px;background:#ffffff08;border-radius:4px"><span style="font-size:11.5px;color:'+C.textDim+'">\u25b8 '+reasonHtml+'</span></div>';
                    html+='</div>'; // 综合判定容器 end

                } else {
                    // 无让球数据的简洁模式
                    html+='<div style="margin-bottom:6px"><span style="font-size:11.5px;color:#93c5fd;font-weight:600">\u2461 让球盘</span></div>';
                    html+='<div style="padding:8px 10px;color:'+C.textDim+';font-size:11.5px;background:#17255425;border-radius:6px;margin-bottom:10px">\ud83d\udc64 本场无让球盘数据</div>';
                    
                    html+='<div style="margin-bottom:6px"><span style="font-size:11.5px;color:#93c5fd;font-weight:600">\u2463 综合判定</span></div>';
                    html+='<div style="background:#0f172a45;border-radius:8px;padding:10px 12px;border-left:3px solid '+vs.border+'">';
                    var sbt=cc.basic_tendency||'', sbtLbl=sbt?({home:mi.home+'胜',draw:'平局',away:mi.away+'胜'}[sbt]):'均衡';
                    html+='<div style="font-size:12px;color:'+C.text+'">基本面: <b>'+esc(sbtLbl)+'</b> &nbsp;|&nbsp; ';
                    if(finalPred){
                        var sfpN={home:mi.home+'胜',draw:'平局',away:mi.away+'胜'}[finalPred]||finalPred;
                        html+='排除: <b style="color:'+C.alignGood+'">'+esc(sfpN)+'</b> \u2605'.repeat(conf||0);
                    } else if(excList.length>0){
                        html+='排除: <b style="color:'+C.good+'">'+excList.map(function(e){return{home:'主胜',draw:'平局',away:'客胜'}[e]||e;}).join('/')+'</b>';
                    } else html+='排除: <span style="color:'+C.textDim+'">无明确排除</span>';
                    html+='</div></div>';
                }

                // 澳门分析原文（始终显示）
                if(mc.analysis){
                    html+='<div style="margin-top:8px;padding:8px 10px;background:#1e293b40;border-radius:6px;border-left:3px solid '+C.border+'">';
                    html+='<div style="font-size:11px;color:'+C.textDim+';margin-bottom:3px;font-weight:600">澳门分析原文</div>';
                    html+='<div style="font-size:11.5px;color:'+C.text+';line-height:1.6">'+esc(mc.analysis.substring(0,300))+(mc.analysis.length>300?'...':'')+' |</div></div>';
                }

                html+='</div>'; // 综合推理结论容器 end
            } else {
                // 无让球盘的简化模式
                html+='<div style="margin-bottom:6px"><span style="font-size:11.5px;color:#93c5fd;font-weight:600">\u2461 让球盘</span></div>';
                html+='<div style="padding:8px 10px;color:'+C.textDim+';font-size:11.5px;background:#17255425;border-radius:6px;margin-bottom:10px">\ud83d\udc64 本场无让球盘数据</div>';

                html+='<div style="margin-bottom:6px"><span style="font-size:11.5px;color:#93c5fd;font-weight:600">\u2463 综合判定</span></div>';
                html+='<div style="background:#0f172a45;border-radius:8px;padding:10px 12px;border-left:3px solid '+vs.border+'">';
                var sbt2=cc.basic_tendency||'', slbl=sbt2?({home:mi.home+'胜',draw:'平局',away:mi.away+'胜'}[sbt2]):'均衡';
                html+='<div style="font-size:12px;color:'+C.text+'">基本面: <b>'+esc(slbl)+'</b> &nbsp;|&nbsp; ';
                if(finalPred){
                    var sfn2={home:mi.home+'胜',draw:'平局',away:mi.away+'胜'}[finalPred]||finalPred;
                    html+='排除: <b style="color:'+C.alignGood+'">'+esc(sfn2)+'</b> \u2605'.repeat(conf||0);
                } else if(excList.length>0){
                    html+='排除: <b style="color:'+C.good+'">'+excList.map(function(e){return{home:'主胜',draw:'平局',away:'客胜'}[e]||e;}).join('/')+'</b>';
                } else html+='排除: <span style="color:'+C.textDim+'">无明确排除</span>';
                html+='</div></div>';
            }

            html+='</div>'; // 第四部分 padding end
            html+='</div>'; // 赛前情报卡片 end

            detailContent.insertAdjacentHTML('beforeend', html);

        })["catch"](function(err) { console.error('赛前情报加载出错:', err); });
    };
})();
