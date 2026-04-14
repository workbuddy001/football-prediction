// This is the clean final recommendation function
// Will be inserted into prematch.js inside the IIFE

var FINAL_REC_FUNC = `
                // ====== 最终结论建议（综合所有维度） ======
                var _finalRec = (function(){
                    var _fp = finalPred;
                    var _bt = cc.basic_tendency;
                    var _mt = mc.tip, _mtt = mc.tip_text;
                    if (!_fp && !_bt) return null;

                    var _isTrap = false;
                    if (typeof _verdict !== 'undefined') {
                        _isTrap = (_verdict.indexOf('三重共振') !== -1 || _verdict.indexOf('最优解') !== -1);
                    }

                    if (_isTrap) {
                        var _bdir = '', _boddsVal = 999;
                        if (jcHomeOdds > 0 && jcHomeOdds < _boddsVal) { _bdir = 'home'; _boddsVal = jcHomeOdds; }
                        if (jcAwayOdds > 0 && jcAwayOdds < _boddsVal) { _bdir = 'away'; _boddsVal = jcAwayOdds; }
                        if (jcDrawOdds > 0 && jcDrawOdds < _boddsVal) { _bdir = 'draw'; _boddsVal = jcDrawOdds; }
                        var _bnMap = {home: mi.home_team + '胜', draw: '平局', away: mi.away_team + '胜'};
                        var _boMap = {home: jcHomeOdds, draw: jcDrawOdds, away: jcAwayOdds};
                        var _othersDirs = ['home','draw','away'].filter(function(d){ return d !== _bdir; });
                        var _hpList = [];
                        for (var oi2 = 0; oi2 < _othersDirs.length; oi2++) {
                            var od2 = _othersDirs[oi2], ov2 = _boMap[od2];
                            if (ov2 >= 2.8) _hpList.push(_bnMap[od2] + '(' + ov2.toFixed(2) + ')');
                        }
                        var _trapRs = [];
                        _trapRs.push('⚽ 三重共振检测：排除法 x 让球出口 x 基本面 = 完美共振');
                        _trapRs.push('⚠️ 全市场筹码集中到"显而易见"的方向 = 很好的引导效果');
                        if (_hpList.length > 0) _trapRs.push('💰 标准盘反向高赔付：' + _hpList.join('+'));
                        _trapRs.push('★ 应付最小方向 = ' + _bnMap[_bdir] + '(' + _boddsVal.toFixed(2) + ')');
                        return {icon:'🔥',title:'☯️ 建议关注：' + _bnMap[_bdir] + '（反向II）',
                            color:'#f87171',stars:'★★★★★',bg1:'#ef4444',bg2:'#f97316',border:'#ef444450',shadow:'#ef4444',
                            accent:'#f87171',starColor:'#fb923c',reasons:_trapRs,
                            note:'参考墨尔本城 vs 惠灵顿（2026-04-12）'};
                    }

                    var _isAnomaly = false;
                    if (typeof _verdict !== 'undefined') {
                        _isAnomaly = (_verdict.indexOf('交叉验证异常') !== -1);
                    }
                    if (_isAnomaly) {
                        var _bp2 = '', _bod2 = 999;
                        if (jcHomeOdds > 0 && jcHomeOdds < 1.80) { _bp2 = 'home'; _bod2 = jcHomeOdds; }
                        else if (jcAwayOdds > 0 && jcAwayOdds < 1.80) { _bp2 = 'away'; _bod2 = jcAwayOdds; }
                        else if (jcHomeOdds > 0) { _bp2 = 'home'; _bod2 = jcHomeOdds; }
                        else if (jcAwayOdds > 0) { _bp2 = 'away'; _bod2 = jcAwayOdds; }
                        var _bn2map = {home: mi.home_team + '胜', draw: '平局', away: mi.away_team + '胜'};
                        return {icon:'🚨',title:'⚠️ 交叉验证异常，值得关注 ' + _bn2map[_bp2],
                            color:'#fb923c',stars:'★★★★',bg1:'#f97316',bg2:'#eab308',border:'#f9731640',shadow:'#f97316',
                            accent:'#fb923c',starColor:'#fbbf24',
                            reasons:['👍 让球盘单出口+中水，但标准盘显示异常',
                                _bn2map[_bp2] + '标准盘=' + _bod2.toFixed(2) + (_bod2 < 1.80 ? '(低水)->应付最小' : ''),
                                '📋 如果排除法结论打出，赔付压力会很大'], note:null};
                    }

                    if (_fp) {
                        var pnMap = {home: mi.home_team + '胜', draw: '平局', away: mi.away_team + '胜'};
                        var predName = pnMap[_fp] || _fp;
                        var agreeBT = (_fp === _bt || (_bt === 'draw' && _fp));
                        var mcAgrees2 = (_mt && _mt.indexOf(predName) !== -1);
                        var caseCRs = [], caseIcon, caseStars, caseLvl, caseClr, caseStCl, caseBg1, caseBg2, caseBd, caseAc;
                        if (conf >= 5) {
                            caseCRs.push('🧠 排除法自信度★★★★★：推荐[' + predName + ']');
                            if (agreeBT) caseCRs.push('✅ 基本面(' + predName + ')与排除法一致');
                            else if (_bt) caseCRs.push('❓ 基本面与排除法分歧');
                            if (_mtt) caseCRs.push('💰澳门' + (mcAgrees2?'✅':'❓') + _mtt);
                            caseIcon='💪'; caseStars='★★★★★'; caseLvl='高置信';
                            caseClr='#22c55e'; caseStCl='#4ade80'; caseBg1='#22c55e'; caseBg2='#16a34a'; caseBd='#22c55e40'; caseAc='#4ade80';
                        } else if (conf >= 4) {
                            caseCRs.push('🧠 排除法自信度★★★★：倾向[' + predName + ']');
                            if (agreeBT) caseCRs.push('✅ 基本面支持');
                            if (_mt) caseCRs.push('🧶 澳门推荐与排除法'+(mcAgrees2?'一致':'不同'));
                            caseIcon='🛡️'; caseStars='★★★★'; caseLvl='较为确定';
                            caseClr='#3b82f6'; caseStCl='#93c5fd'; caseBg1='#3b82f6'; caseBg2='#2563eb'; caseBd='#3b82f640'; caseAc='#93c5fd';
                        } else if (conf >= 3) {
                            caseCRs.push('🧠 排除法倾向[' + predName + '](★★★)');
                            caseCRs.push('⚠️ 自信度中等，建议结合赔率判断');
                            if (!agreeBT) caseCRs.push('⚠️ 基本面与排除法不一致，选择需谨慎');
                            caseIcon='🔔'; caseStars='★★★'; caseLvl='有参考价值';
                            caseClr='#eab308'; caseStCl='#facc15'; caseBg1='#eab308'; caseBg2='#ca8a04'; caseBd='#eab30830'; caseAc='#facc15';
                        } else if (conf > 0) {
                            caseCRs.push('🧠 排除法弱倾向[' + predName + '](★★)');
                            caseCRs.push('👀 信号不强烈，仅作参考');
                            caseIcon='🔍'; caseStars='★★'; caseLvl='低置信';
                            caseClr='#f97316'; caseStCl='#fb923c'; caseBg1='#f97316'; caseBg2='#ea580c'; caseBd='#f9731620'; caseAc='#fb923c';
                        } else { return null; }
                        if (hcH > 0) {
                            var hwi2 = _classifyWaterLevel(hcH);
                            if (hwi2.level !== '-' && hwi2.color !== C.textDim) {
                                caseCRs.push('💰 让球盘对应方向=' + hcH.toFixed(2) + '(' + (hwi2.level||'') + ')->应合理');
                            }
                        }
                        return {icon:caseIcon,title:caseLvl+'：'+predName,color:caseClr,stars:caseStars,
                            bg1:caseBg1,bg2:caseBg2,border:caseBd,shadow:caseBg1,
                            accent:caseAc,starColor:caseStCl,reasons:caseCRs,note:null};
                    }

                    if (_bt) {
                        var bn3map = {home: mi.home_team + '胜', draw: '和局', away: mi.away_team + '胜'};
                        var bo3map = {home: jcHomeOdds, draw: jcDrawOdds, away: jcAwayOdds};
                        var mcDir2 = '';
                        if (_mtt) {
                            if (_mtt.indexOf(mi.home_team) !== -1) mcDir2 = 'home';
                            else if (_mtt.indexOf(mi.away_team) !== -1) mcDir2 = 'away';
                            else if (_mtt.indexOf('和') !== -1 || _mtt.indexOf('平') !== -1) mcDir2 = 'draw';
                        }
                        var mcAgree3 = (mcDir2 && mcDir2 === _bt);
                        var d4rs = [], recDir2 = _bt, recOdds2 = bo3map[_bt];
                        d4rs.push('基本面明显倾向 [' + bn3map[_bt] + ']');
                        if (mcDir2) {
                            if (mcAgree3) d4rs.push('💰 澳门心水同向推荐[' + bn3map[mcDir2] + '] ✅');
                            else d4rs.push('💰 澳门心水推[' + bn3map[mcDir2] + ']，与基本面分歧');
                        }
                        var lodDir = '', lodVal = 99;
                        ['home','draw','away'].forEach(function(d){
                            if(bo3map[d]>0&&bo3map[d]<lodVal){lodVal=bo3map[d];lodDir=d;}
                        });
                        if (lodDir === _bt) d4rs.push('★ '+bn3map[_bt]+'赔率='+recOdds2.toFixed(2)+' = 标准盘最低→应付最小');
                        else if (lodDir) d4rs.push('⚠️ 标准盘最低是'+bn3map[lodDir]+'('+lodVal.toFixed(2)+')，与基本面倾向不同');
                        if (hcH > 0) {
                            var hwinfo3 = _classifyWaterLevel(hcH);
                            if (hwinfo3.level !== '-') {
                                var ts3 = hwinfo3.level || '';
                                if(ts3.indexOf('超低')===0||ts3.indexOf('低')===0&&ts3!=='低水') d4rs.push('💦 让球盘主进方向在低/超低水区，应合理');
                                else if(ts3.indexOf('高')===0||ts3.indexOf('超高')===0) d4rs.push('🛑 让球盘主进方向在高/超高水，存在嫌疑');
                            }
                        }
                        var strongFlag=(mcAgree3&&lodDir===_bt), weakFlag=(mcDir2&&!mcAgree3)||(lodDir&&lodDir!==_bt);
                        return{icon:strongFlag?'💪':'📋',title:(strongFlag?'✅ ':'⚠️ ')+'综合判定：'+bn3map[recDir2],
                            color:strongFlag?'#22c55e':(weakFlag?'#f97316':'#3b82f6'),
                            stars:strongFlag?'★★★★':'★★★',bg1:strongFlag?'#22c55e':(weakFlag?'#f97316':'#3b82f6'),
                            bg2:strongFlag?'#16a34a':(weakFlag?'#ea580c':'#2563eb'),
                            border:strongFlag?'#22c55e40':(weakFlag?'#f9731630':'#3b82f640'),
                            shadow:strongFlag?'#22c55e':(weakFlag?'#f97316':'#3b82f6'),
                            accent:strongFlag?'#4ade80':(weakFlag?'#fb923c':'#93c5fd'),
                            starColor:strongFlag?'#4ade80':(weakFlag?'#fb923c':'#93c5fd'),
                            reasons:d4rs,note:weakFlag?'⚠️ 信号存在分歧，建议降级投入或观望':null};
                    }
                    return null;
                })();

`;

module.exports = FINAL_REC_FUNC;
