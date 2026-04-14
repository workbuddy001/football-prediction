// ============================================================
// 赛前情报解析器 (Intelligence Parser)
// 功能：将用户粘贴的赛前分析文本 → 结构化数据
// 数据源：用户手动录入 / 粘贴外部文章
// ============================================================

var IntelParser = (function() {
    
    // ============================================================
    // 1. 常量定义
    // ============================================================
    
    // 伤停关键词
    var INJURY_KEYWORDS = ['缺阵', '伤缺', '伤病', '受伤', '腿筋', '肌肉拉伤', '脚踝', '膝盖',
        '十字韧带', '骨折', '手术', '恢复中', '长期伤缺'];
    var SUSPEND_KEYWORDS = ['停赛', '红牌停赛', '黄牌累积', '禁赛', '停'];
    var DOUBTFUL_KEYWORDS = ['存疑', '出战成疑', '待定', '可能复出', '状态未达100%', 
        '勉强出战', '勉强出场', '有望复出'];
    var AVAILABLE_KEYWORDS = ['可出战', '可首发', '全部健康', '健康', '能够首发', 
        '确认首发', '均可首发'];
    
    // 位置关键词
    var POS_GOALKEEPER = ['门将', '门将奥布拉克', '门将', '守门员', 'GK'];
    var POS_DEFENDER = ['后卫', '中卫', '边卫', '左后卫', '右后卫', 'CB', 'RB', 'LB', 
        '中后卫', '中后卫组合', '防线', '后防', '后防线', '防线上'];
    var MIDFIELDER = ['中场', '前腰', '后腰', '边锋', '中前卫', 'CM', 'AM', 'DM', 
        '中场核心', '中场硬度', '腰', '中路'];
    var FORWARD = ['前锋', '中锋', '左边锋', '右边锋', '边路', 'ST', 'LW', 'RW', '射手',
        '头号射手', '进攻核心', '10号位', '爆点', '攻击手', '箭头人物'];
    
    // 战意关键词
    var MOTIVATION_HIGH = ['必须', '必须赢', '必须胜', '生死战', '决战', '背水一战',
        '全力争胜', '全力以赴', '不容有失', '争四', '争冠', '保级', '欧冠资格',
        '晋级关键', '淘汰赛', '决赛', '德比', '死敌', '复仇', '冠军争夺',
        '狂攻', '全线压上', '不留后路', '翻盘', '逆转', '地狱级难度也要上'];
    var MOTIVATION_LOW = ['无欲无求', '轮换', '练兵', '替补阵容', '留力',
        '主力休息', '无关紧要', '无压力', '安全区', '中游安全', '欧战无望',
        '保级无忧', '放弃', '摆烂', '拖时间', '死守', '大巴', '守住常规时间'];
    var MOTIVATION_MEDIUM = ['正常发挥', '正常比赛', '例行公事'];
    
    // 战术关键词
    var TACTIC_ATTACK = ['高位压迫', '控球率', '压上', '猛攻', '进攻犀利', '流畅',
        '配合默契', '全线压上', '狂攻', '占据主动', '有进球'];
    var TACTIC_DEFEND = ['死守', '大巴', '退守', '密集防守', '防守韧性', '防守体系完整',
        '全员退守', '切断连线', '封锁', '摆大巴', '放弃控球', '防守骨架'];
    var TACTIC_COUNTER = ['反击', '偷球', '偷鸡', '速度', '突击', '伺机偷球', '快速反击',
        '定位球是重要得分手段', '反击依靠'];
    
    // 影响力评级（用于btMult计算）
    var IMPACT_HIGH = ['核心', '主力', '队长', '关键', '头号', '重要', '骨干', '绝对主力', '绝对主力'];
    var IMPACT_MEDIUM = ['主力', '常规首发', '常用', '常驻', '稳定首发'];
    var IMPACT_LOW = ['轮换', '替补', '边缘', '年轻', '小将', '板凳'];

    // ============================================================
    // 2. 主解析入口
    // ============================================================
    
    /**
     * 解析赛前情报文本
     * @param {string} text - 用户输入的原始文本
     * @param {string} homeTeam - 主队名称（用于区分主客）
     * @param {string} awayTeam - 客队名称
     * @returns {Object} 解析结果
     */
    function parse(text, homeTeam, awayTeam) {
        if (!text || !homeTeam || !awayTeam) return null;
        
        var result = {
            rawText: text,
            homeTeam: homeTeam,
            awayTeam: awayTeam,
            
            // === 元信息 ===
            meta: extractMeta(text),
            
            // === 伤停信息 ===
            injuries: {
                home: extractInjuries(text, homeTeam),
                away: extractInjuries(text, awayTeam)
            },
            
            // === 战意评估 ===
            motivation: {
                home: extractMotivation(text, homeTeam),
                away: extractMotivation(text, awayTeam)
            },
            
            // === 战术风格 ===
            tactics: {
                home: extractTactics(text, homeTeam),
                away: extractTactics(text, awayTeam)
            },
            
            // === 综合结论 ===
            conclusion: extractConclusion(text),
            
            // === btMult 计算所需的数据 ===
            btMultData: null  // 后续填充
        };
        
        // 计算影响分数
        result.injuries.home.impactScore = calcInjuryImpact(result.injuries.home);
        result.injuries.away.impactScore = calcInjuryImpact(result.injuries.away);
        result.injuryGap = result.injuries.away.impactScore - result.injuries.home.impactScore;
        
        // 计算战意系数
        result.motivation.home.mult = motivationToMult(result.motivation.home.level);
        result.motivation.away.mult = motivationToMult(result.motivation.away.level.level);
        result.motivationGap = result.motivation.home.mult - result.motivation.away.mult;
        
        // 填充btMult数据
        result.btMultData = {
            injuryGap: result.injuryGap,
            homeInjuryScore: result.injuries.home.impactScore,
            awayInjuryScore: result.injuries.away.impactScore,
            homeMotivationLevel: result.motivation.home.level,
            awayMotivationLevel: result.motivation.away.level,
            homeMotivationMult: result.motivation.home.mult,
            awayMotivationMult: result.motivation.away.mult,
            motivationGap: result.motivationGap
        };
        
        console.log('[IntelParser] Parsed:', JSON.stringify({
            h_injury: result.injuries.home.impactScore,
            a_injury: result.injuries.away.impactScore,
            injury_gap: result.injuryGap.toFixed(2),
            h_moti: result.motivation.home.level,
            a_moti: result.motivation.away.level,
            moti_gap: result.motivationGap.toFixed(3)
        }));
        
        return result;
    }

    // ============================================================
    // 3. 元信息提取：赛事/时间/场地/首回合
    // ============================================================
    function extractMeta(text) {
        var meta = {};
        
        // 赛事类型
        var matchTypes = ['欧冠', '英超', '西甲', '意甲', '德甲', '法甲', '足总杯',
            '联赛杯', '国王杯', '德国杯', '意大利杯', '友谊赛', '世界杯', '欧洲杯',
            '亚冠', '中超', '日职', '澳超', 'K联赛', '美职', '附加赛', '淘汰赛', '1/4决赛', '半决赛', '决赛'];
        for (var i = 0; i < matchTypes.length; i++) {
            if (text.indexOf(matchTypes[i]) !== -1) { meta.competition = matchTypes[i]; break; }
        }
        
        // 时间（格式：2026-04-15 或 YYYY-MM-DD）
        var dateMatch = text.match(/(\d{4})\s*[-年]\s*(\d{1,2})\s*[-月]\s*(\d{1,2})/);
        if (dateMatch) meta.date = dateMatch[1] + '-' + pad(dateMatch[2]) + '-' + pad(dateMatch[3]);
        
        // 场地
        var venueMatch = text.match(/场地[：:]\s*([^\n\r，。]+)/);
        if (venueMatch) meta.venue = venueMatch[1].trim();
        
        // 首回合比分
        var firstLegMatch = text.match(/首回合[：:\s]*(.+?)[\n\r]/);
        if (firstLegMatch) meta.firstLeg = firstLegMatch[1].trim();
        
        // 晋级形势
        if (text.indexOf('必须净胜') !== -1 || text.indexOf('必须') !== -1) meta.situation = 'must_win';
        if (text.indexOf('只要不输') !== -1 || text.indexOf('稳稳晋级') !== -1) meta.situation = 'safe_position';
        if (text.indexOf('翻盘') !== -1 || text.indexOf('逆转') !== -1) meta.situation = 'comeback';
        
        return meta;
    }
    
    function pad(n) { return n.length === 1 ? '0' + n : n; }

    // ============================================================
    // 4. 伤停信息提取（按球队）
    // ============================================================
    function extractInjuries(text, teamName) {
        var result = {
            team: teamName,
            out: [],       // 缺阵/伤停
            doubtful: [],   // 存疑
            available: [],  // 可出战
            suspended: [],  // 停赛
            
            summary: '',    // 该队段落摘要
            impactScore: 0  // 总影响分(-5~0)
        };
        
        // 找到该队的段落（从队名开始到下一个队名或章节结束）
        var section = findTeamSection(text, teamName);
        result.summary = section;
        
        if (!section) return result;
        
        // 提取球员列表
        // 格式1: "- 球员名：（原因）"
        var lines = section.split(/[\n\r]/);
        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            if (!line || line.indexOf('-') !== 0 && line.indexOf('·') !== 0 && line.indexOf('、') === -1) continue;
            
            // 提取球员名和原因
            var playerInfo = parsePlayerLine(line);
            if (!playerInfo.name) continue;
            
            // 判断状态
            var status = classifyPlayerStatus(line, playerInfo.reason);
            playerInfo.status = status;
            playerInfo.impact = assessPlayerImpact(line, playerInfo.name);
            playerInfo.position = guessPosition(line, playerInfo.name);
            
            if (status === 'out' || status === 'injured') result.out.push(playerInfo);
            else if (status === 'suspended') result.suspended.push(playerInfo);
            else if (status === 'doubtful') result.doubtful.push(playerInfo);
            else if (status === 'available') result.available.push(playerInfo);
        }
        
        // 也尝试从段落描述中提取未列表的重要球员
        extractImplicitInjuries(section, teamName, result);
        
        return result;
    }
    
    /**
     * 找到某球队的段落区域
     */
    function findTeamSection(text, teamName) {
        // 简化方案：用字符串查找代替复杂正则
        var markers = ['一、', '二、', '三、', '四、', '五、', '六、', '七、', '八、', '九、', '十、',
                       '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.',
                       '【', 'vs ', 'VS ', ' 对'];
        
        // 找到队名首次出现位置
        var idx = text.indexOf(teamName);
        if (idx === -1) return '';
        
        // 从队名后开始（跳过队名行本身）
        var start = text.indexOf('\n', idx);
        if (start === -1) start = idx + teamName.length;
        else start += 1;
        
        // 找到下一个章节标记作为结束位置
        var end = text.length;
        for (var i = 0; i < markers.length; i++) {
            var mi = text.indexOf(markers[i], start);
            // 忽略行首的列表项（- xxx）
            if (mi > 0 && mi < end) {
                var prevChar = text.substring(mi - 5, mi);
                // 如果前面是行首或换行+缩进，才认为是章节标记
                if (/[\n\r]$/.test(prevChar) || /^\s*$/.test(prevChar)) {
                    end = mi;
                }
            }
        }
        
        var section = text.substring(start, end).trim();
        return section || text.substring(start, Math.min(start + 500, text.length));
    }
    
    function getOtherTeamMarker(currentTeam) {
        return '(?:主队|客队|对方|对手)';
    }
    
    /**
     * 解析球员行
     */
    function parsePlayerLine(line) {
        var name = '', reason = '';
        
        // 格式: "- 库巴西：红牌停赛"
        var m1 = line.match(/[-·、]\s*(.+?)[:：:()\s（]*(.+)/);
        if (m1) { name = m1[1].trim(); reason = m1[2].trim(); }
        else {
            // 格式: "库巴西：红牌停赛" 或 "库巴西 红牌停赛"
            var m2 = line.match(/[-·、]?\s*(.+?)[:：:\s]+(.+)/);
            if (m2) { name = m2[1].trim(); reason = m2[2].trim(); }
            else {
                // 只有一个名字的行
                var m3 = line.match(/[-·、]\s*(.+?)/);
                if (m3) name = m3[1].trim();
            }
        }
        
        // 清理名字中的标点和多余文字
        name = name.replace(/[：:()（）\[\]]/g, '').trim();
        if (name.length > 15) name = name.substring(0, 15); // 名字太长可能是误识别
        
        return { name: name, reason: reason };
    }
    
    /**
     * 分类球员状态
     */
    function classifyPlayerStatus(line, reason) {
        var combined = (line + ' ' + reason).toLowerCase ? (line + ' ' + reason).toLowerCase() : (line + ' ' + reason);
        
        // 先检查停赛（优先）
        for (var s = 0; s < SUSPEND_KEYWORDS.length; s++) {
            if (combined.indexOf(SUSPEND_KEYWORDS[s]) !== -1) return 'suspended';
        }
        
        // 检查存疑
        for (var d = 0; d < DOUBTFUL_KEYWORDS.length; d++) {
            if (combined.indexOf(DOUBTFUL_KEYWORDS[d]) !== -1) return 'doubtful';
        }
        
        // 检查可出战
        for (var a = 0; a < AVAILABLE_KEYWORDS.length; a++) {
            if (combined.indexOf(AVAILABLE_KEYWORDS[a]) !== -1) return 'available';
        }
        
        // 检查伤缺
        for (var ij = 0; ij < INJURY_KEYWORDS.length; ij++) {
            if (combined.indexOf(INJURY_KEYWORDS[ij]) !== -1) return 'injured';
        }
        
        // 默认根据上下文判断
        if (line.indexOf('缺阵') !== -1 || reason.indexOf('缺') !== -1) return 'out';
        if (line.indexOf('可') !== -1 || reason.indexOf('可') !== -1) return 'available';
        
        return 'unknown'; // 无法判断
    }
    
    /**
     * 评估球员影响力 (-3 ~ 0)
     */
    function assessPlayerImpact(line, playerName) {
        var combined = line + ' ' + playerName;
        
        // 高影响力 (-2.5 ~ -3)
        for (var h = 0; h < IMPACT_HIGH.length; h++) {
            if (combined.indexOf(IMPACT_HIGH[h]) !== -1) return -3.0;
        }
        
        // 门将总是高影响
        for (var g = 0; g < POS_GOALKEEPER.length; g++) {
            if (combined.indexOf(POS_GOALKEEPER[g]) !== -1) return -3.0;
        }
        
        // 中等影响力 (-1.5 ~ -2)
        if (combined.indexOf('主力') !== -1) return -2.0;
        
        // 根据位置判断
        var pos = guessPosition(line, playerName);
        if (pos === 'defender') return -2.0;
        if (pos === 'midfielder') return -1.5;
        if (pos === 'forward') return -2.0;  // 进攻核心也高
        
        return -1.0; // 默认中等影响
    }
    
    /**
     * 猜测位置
     */
    function guessPosition(line, playerName) {
        var combined = line;
        for (var g = 0; g < POS_GOALKEEPER.length; g++) {
            if (combined.indexOf(POS_GOALKEEPER[g]) !== -1) return 'goalkeeper';
        }
        for (var d = 0; d < POS_DEFENDER.length; d++) {
            if (combined.indexOf(POS_DEFENDER[d]) !== -1) return 'defender';
        }
        for (var m = 0; m < MIDFIELDER.length; m++) {
            if (combined.indexOf(MIDFIELDER[m]) !== -1) return 'midfielder';
        }
        for (var f = 0; f < FORWARD.length; f++) {
            if (combined.indexOf(FORWARD[f]) !== -1) return 'forward';
        }
        return 'unknown';
    }
    
    /**
     * 从段落描述中隐式提取伤停（不在列表中的重要信息）
     */
    function extractImplicitInjuries(section, teamName, result) {
        // 检查"后防线残缺"、"后防灾难级"等描述
        if (section.indexOf('后防灾难') !== -1 || section.indexOf('后防线直接拆家') !== -1 ||
            section.indexOf('防线残缺') !== -1 || section.indexOf('后防残缺') !== -1) {
            result.out.push({ name: '[防线整体]', reason: '后防线严重不整', status: 'out', impact: -2.5, position: 'defender' });
        }
        
        // 检查"中场硬度不足"
        if (section.indexOf('中场硬度不足') !== -1 || section.indexOf('中场薄弱') !== -1) {
            result.out.push({ name: '[中场]', reason: '中场实力不足', status: 'out', impact: -1.5, position: 'midfielder' });
        }
        
        // 检查"进攻端削弱"
        if (section.indexOf('边路爆点进一步削弱') !== -1 || section.indexOf('火力受损') !== -1 ||
            section.indexOf('进攻端受损') !== -1) {
            result.out.push({ name: '[进攻线]', reason: '进攻火力受损', status: 'out', impact: -2.0, position: 'forward' });
        }
        
        // "整体健康"
        if (section.indexOf('整体健康') !== -1 || section.indexOf('全员健康') !== -1) {
            result.summary += ' [整体健康]';
        }
    }

    // ============================================================
    // 5. 伤停影响分计算
    // ============================================================
    function calcInjuryImpact(injuryData) {
        if (!injuryData) return 0;
        
        var score = 0;
        
        // 缺阵球员
        for (var o = 0; o < injuryData.out.length; o++) {
            score += (injuryData.out[o].impact || -1.5);
        }
        
        // 停赛球员
        for (var s = 0; s < injuryData.suspended.length; s++) {
            score += (injuryData.suspended[s].impact || -2.0);
        }
        
        // 存疑球员（折半计算）
        for (var d = 0; d < injuryData.doubtful.length; d++) {
            score += (injuryData.doubtful[d].impact || -1.0) * 0.5;
        }
        
        // 封底：最低-6
        return Math.max(-6, Math.round(score * 10) / 10);
    }

    // ============================================================
    // 6. 战意提取
    // ============================================================
    function extractMotivation(text, teamName) {
        var section = findTeamSection(text, teamName);
        if (!section) return { level: 'medium', reasons: [], confidence: 0.3 };
        
        var highCount = 0, lowCount = 0, medCount = 0;
        var reasons = [];
        
        // 高战意检测
        for (var h = 0; h < MOTIVATION_HIGH.length; h++) {
            if (section.indexOf(MOTIVATION_HIGH[h]) !== -1) {
                highCount++;
                reasons.push({ type: 'high', keyword: MOTIVATION_HIGH[h], source: 'keyword' });
            }
        }
        
        // 低战意检测
        for (var l = 0; l < MOTIVATION_LOW.length; l++) {
            if (section.indexOf(MOTIVATION_LOW[l]) !== -1) {
                lowCount++;
                reasons.push({ type: 'low', keyword: MOTIVATION_LOW[l], source: 'keyword' });
            }
        }
        
        // 中等战意
        for (var m = 0; m < MOTIVATION_MEDIUM.length; m++) {
            if (section.indexOf(MOTIVATION_MEDIUM[m]) !== -1) {
                medCount++;
            }
        }
        
        // 从元信息补充
        var meta = {}; // 额外上下文
        if (text.indexOf(teamName + '必须') !== -1) { highCount++; reasons.push({type:'high',keyword:'必须赢',source:'context'}); }
        if ((section.indexOf('死守') !== -1 || section.indexOf('守住') !== -1) && 
            section.indexOf('反击') !== -1) {
            lowCount++;
            reasons.push({type:'low',keyword:'死守反击模式',source:'context'});
        }
        if (section.indexOf('主场不败') !== -1 || section.indexOf('魔鬼主场') !== -1) {
            highCount++;
            reasons.push({type:'high',keyword:'魔鬼主场',source:'context'});
        }
        
        // 判定等级
        var level, confidence;
        if (highCount > lowCount + 1) {
            level = 'high'; confidence = Math.min(0.95, 0.5 + highCount * 0.15);
        } else if (lowCount > highCount + 1) {
            level = 'low'; confidence = Math.min(0.95, 0.5 + lowCount * 0.15);
        } else if (highCount === lowCount && highCount > 0) {
            level = 'medium'; confidence = 0.4;
        } else if (medCount > 0 || (highCount > 0 && lowCount > 0)) {
            level = 'medium'; confidence = 0.35;
        } else {
            level = 'medium'; confidence = 0.2; // 无明确信号
        }
        
        return { level: level, confidence: confidence, reasons: reasons, rawCounts: { high: highCount, low: lowCount } };
    }
    
    function motivationToMult(level) {
        if (level === 'high') return 1.15;
        if (level === 'low') return 0.85;
        return 1.0; // medium
    }

    // ============================================================
    // 7. 战术风格提取
    // ============================================================
    function extractTactics(text, teamName) {
        var section = findTeamSection(text, teamName);
        if (!section) return { style: 'balanced', keywords: [] };
        
        var attackScore = 0, defendScore = 0, counterScore = 0;
        var keywords = [];
        
        for (var a = 0; a < TACTIC_ATTACK.length; a++) {
            if (section.indexOf(TACTIC_ATTACK[a]) !== -1) { attackScore++; keywords.push(TACTIC_ATTACK[a]); }
        }
        for (var d = 0; d < TACTIC_DEFEND.length; d++) {
            if (section.indexOf(TACTIC_DEFEND[d]) !== -1) { defendScore++; keywords.push(TACTIC_DEFEND[d]); }
        }
        for (var c = 0; c < TACTIC_COUNTER.length; c++) {
            if (section.indexOf(TACTIC_COUNTER[c]) !== -1) { counterScore++; keywords.push(TACTIC_COUNTER[c]); }
        }
        
        var style = 'balanced';
        if (attackScore > defendScore + 1 && attackScore > counterScore) style = 'attack';
        else if (defendScore > attackScore + 1) style = 'defend';
        else if (counterScore >= 2) style = 'counter';
        
        return { style: style, scores: { attack: attackScore, defend: defendScore, counter: counterScore }, keywords: keywords };
    }

    // ============================================================
    // 8. 结论提取
    // ============================================================
    function extractConclusion(text) {
        var result = {
            prediction: '',
            confidence: '',
            reasoning: [],
            goals: '',
            scores: []
        };
        
        // 找结论段落
        var sections = ['综合结论', '方向参考', '最终版', '胜负关键', '综合判定'];
        for (var s = 0; s < sections.length; s++) {
            var idx = text.indexOf(sections[s]);
            if (idx !== -1) {
                var conclusionPart = text.substring(idx, Math.min(text.length, idx + 800));
                
                // 方向预测
                var dirMatch = conclusionPart.match(/(?:赛果|方向|预测|结论)[：:]\s*([^\n\r]+)/);
                if (dirMatch) result.prediction = dirMatch[1].trim();
                
                // 比分参考
                var scoreMatches = conclusionPart.matchAll(/比分参考[：:]\s*([^\n\r]+)/g);
                if (scoreMatches) {
                    for (var sm of scoreMatches) {
                        result.scores.push(sm[1].trim());
                    }
                }
                
                // 总进球
                var goalMatch = conclusionPart.match(/总进球[：:]\s*([^\n\r]+)/);
                if (goalMatch) result.goals = goalMatch[1].trim();
                
                // 关键理由
                var reasonMatches = conclusionPart.matchAll(/^\s*(?:\d+[\.、]?\s*)(.+)/gm);
                if (reasonMatches) {
                    for (var rm of reasonMatches) {
                        var r = rm[1].trim();
                        if (r.length > 5 && r.length < 100) result.reasoning.push(r);
                    }
                }
                
                break;
            }
        }
        
        // 如果没找到标准标题，尝试其他方式
        if (!result.prediction) {
            var altPatterns = [
                /[更合]理的走向是[：:]\s*([^\n\r]+)/,
                /本场[更合]?\s*([^\n\r]{10,80}?方向[^\n\r]*)/,
            ];
            for (var ap = 0; ap < altPatterns.length; ap++) {
                var am = text.match(altPatterns[ap]);
                if (am) { result.prediction = am[1].trim(); break; }
            }
        }
        
        return result;
    }

    // ============================================================
    // 9. 利好利空生成器 — 用于前端展示
    // ============================================================
    
    /**
     * 将解析结果转换为利好/利空条目
     */
    function generateFactors(parsedData) {
        if (!parsedData) return { positives: [], negatives: [], neutral: [] };
        
        var pos = []; // 利好
        var neg = []; // 利空
        var neu = []; // 中性
        
        var ht = parsedData.homeTeam;
        var at = parsedData.awayTeam;
        
        // ---- 主队利好 ----
        // 对方有重大伤停
        if (parsedData.injuries.away.impactScore <= -3) {
            pos.push({ team: 'home', type: 'injury_opponent',
                text: at + '严重伤停(' + parsedData.injuries.away.impactScore + '分)，我方相对受益',
                strength: 'strong', icon: '🩹' });
        }
        // 我方战意高
        if (parsedData.motivation.home.level === 'high') {
            pos.push({ team: 'home', type: 'motivation',
                text: '战意强烈(' + parsedData.motivation.home.rawCounts.high + '个信号)',
                strength: parsedData.motivation.home.confidence > 0.7 ? 'strong' : 'medium', icon: '🔥' });
        }
        // 我方阵容完整
        if (parsedData.injuries.home.impactScore >= -1 && parsedData.injuries.home.out.length === 0) {
            pos.push({ team: 'home', type: 'lineup',
                text: '阵容基本完整，无明显伤停', strength: 'medium', icon: '✅' });
        }
        // 主场优势
        if (parsedData.meta.firstLeg || parsedData.meta.competition) {
            if (parsedData.meta.situation === 'safe_position') {
                pos.push({ team: 'home', type: 'situation',
                    text: '形势有利：' + (parsedData.meta.firstLeg || ''),
                    strength: 'strong', icon: '🏆' });
            }
        }
        
        // ---- 主队利空 ----
        // 我方有重大伤停
        if (parsedData.injuries.home.impactScore <= -3) {
            neg.push({ team: 'home', type: 'injury_self',
                text: ht + '严重伤停(' + parsedData.injuries.home.impactScore + '分)' +
                     formatPlayerList(parsedData.injuries.home.out.slice(0, 3)),
                strength: 'strong', icon: '❌' });
        } else if (parsedData.injuries.home.impactScore <= -1.5) {
            neg.push({ team: 'home', type: 'injury_self',
                text: ht + '有伤停(' + parsedData.injuries.home.impactScore + '分)',
                strength: 'medium', icon: '⚠️' });
        }
        // 我方战意低
        if (parsedData.motivation.home.level === 'low') {
            neg.push({ team: 'home', type: 'motivation',
                text: '战意不足(' + parsedData.motivation.home.rawCounts.low + '个低战意信号)',
                strength: 'medium', icon: '😐' });
        }
        // 我方战术被动
        if (parsedData.tactics.home.style === 'defend') {
            neu.push({ team: 'home', type: 'tactic',
                text: '预计采用防守策略(' + parsedData.tactics.home.keywords.slice(0,2).join('+') + ')',
                icon: '🛡️' });
        }
        
        // ---- 客队利好 ----
        if (parsedData.injuries.home.impactScore <= -3) {
            pos.push({ team: 'away', type: 'injury_opponent',
                text: ht + '严重伤停，' + at + '相对受益',
                strength: 'strong', icon: '🩹' });
        }
        if (parsedData.motivation.away.level === 'high') {
            pos.push({ team: 'away', type: 'motivation',
                text: at + '战意强烈(' + parsedData.motivation.away.rawCounts.high + '个信号)',
                strength: parsedData.motivation.away.confidence > 0.7 ? 'strong' : 'medium', icon: '🔥' });
        }
        if (parsedData.injuries.away.impactScore >= -1 && parsedData.injuries.away.out.length === 0) {
            pos.push({ team: 'away', type: 'lineup',
                text: at + '阵容基本完整', strength: 'medium', icon: '✅' });
        }
        
        // ---- 客队利空 ----
        if (parsedData.injuries.away.impactScore <= -3) {
            neg.push({ team: 'away', type: 'injury_self',
                text: at + '严重伤停(' + parsedData.injuries.away.impactScore + '分)' +
                     formatPlayerList(parsedData.injuries.away.out.slice(0, 3)),
                strength: 'strong', icon: '❌' });
        } else if (parsedData.injuries.away.impactScore <= -1.5) {
            neg.push({ team: 'away', type: 'injury_self',
                text: at + '有伤停(' + parsedData.injuries.away.impactScore + '分)',
                strength: 'medium', icon: '⚠️' });
        }
        if (parsedData.motivation.away.level === 'low') {
            neg.push({ team: 'away', type: 'motivation',
                text: at + '战意不足(' + parsedData.motivation.away.rawCounts.low + '个低战意信号)',
                strength: 'medium', icon: '😐' });
        }
        if (parsedData.tactics.away.style === 'defend') {
            neu.push({ team: 'away', type: 'tactic',
                text: at + '预计采用防守策略',
                icon: '🛡️' });
        }
        
        // ---- 综合判断 ----
        if (parsedData.conclusion.prediction) {
            neu.push({ team: 'both', type: 'conclusion',
                text: '📋 文章结论: ' + parsedData.conclusion.prediction,
                icon: '📝' });
        }
        
        return { positives: pos, negatives: neg, neutral: neu };
    }
    
    function formatPlayerList(players) {
        if (!players || players.length === 0) return '';
        var names = [];
        for (var i = 0; i < players.length; i++) names.push(players[i].name);
        return ' [' + names.join(', ') + ']';
    }

    // ============================================================
    // 10. 升级后的btMult计算器
    // ============================================================
    
    /**
     * 使用解析后的情报数据升级btMult
     * @param {Object} baseBtMult - 原始btMult值（仅基于近况）
     * @param {string} direction - 当前计算的方向 home/draw/away
     * @param {Object} intelData - parse() 的返回值
     * @returns {Object} { value, breakdown }
     */
    function upgradeBtMult(baseBtMult, direction, intelData) {
        if (!intelData || !intelData.btMultData) {
            return { value: baseBtMult, breakdown: '无情报数据，使用原始btMult' };
        }
        
        var bd = intelData.btMultData;
        
        // 伤停修正：每分±3%，范围±15%
        var injuryAdjust = 1 + bd.injuryGap * 0.03;
        injuryAdjust = Math.max(0.85, Math.min(1.15, injuryAdjust));
        
        // 战意修正：比值方式
        var motivationAdjust = bd.homeMotivationMult / bd.awayMotivationMult;
        // 根据方向调整
        if (direction === 'home') motivationAdjust = motivationAdjust;         // 主胜：主战意/客场意
        else if (direction === 'away') motivationAdjust = 1 / motivationAdjust;  // 客胜：客场意/主战意
        else motivationAdjust = 1.0;                                           // 平局：中性
        motivationAdjust = Math.max(0.85, Math.min(1.15, motivationAdjust));
        
        // 合成
        var finalValue = baseBtMult * injuryAdjust * motivationAdjust;
        finalValue = Math.max(0.65, Math.min(1.40, finalValue)); // 总范围放宽
        finalValue = Math.round(finalValue * 1000) / 1000;
        
        return {
            value: finalValue,
            breakdown: {
                base: Math.round(baseBtMult * 1000) / 1000,
                injuryGap: bd.injuryGap,
                injuryAdjust: Math.round(injuryAdjust * 1000) / 1000,
                homeMotivation: bd.homeMotivationLevel,
                awayMotivation: bd.awayMotivationLevel,
                motivationAdjust: Math.round(motivationAdjust * 1000) / 1000,
                final: finalValue
            }
        };
    }

    // ============================================================
    // 公开API
    // ============================================================
    return {
        parse: parse,
        generateFactors: generateFactors,
        upgradeBtMult: upgradeBtMult,
        calcInjuryImpact: calcInjuryImpact,
        getVersion: function() { return '1.0.0'; }
    };
})();
