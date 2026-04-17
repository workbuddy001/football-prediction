var mjcGdjjCommon = {
    channelType:'football',
    pool_list: [{code:'mnl', name:'胜负'},{code:'hdc',name:'让分胜负'},{code:'hilo',name:'大小分'},{code:'wnm',name:'胜分差'}],
    pool_list_fb: [{code:'had', name:'胜平负'},{code:'hhad',name:'让球胜平负'},{code:'crs',name:'比分'},{code:'ttg',name:'总进球'},{code:'hafu',name:'半全场胜平负'}],
    getData: function (type,matchId) {
        var interfaceName = "getFixedBonusV1.qry";
        if(type) mjcGdjjCommon.channelType = type;
        if(type == "basketball") interfaceName = "getFixedBonusV2.qry";
        commonV1Fun.ajaxFun(
            mjcGdjjCommon.showData,
            jsCommonDataV1.webApi + '/gateway/uniform/'+mjcGdjjCommon.channelType+'/' + interfaceName + '?clientCode='+commonV1Fun.comClientCode+'&matchId='+matchId,
            undefined,
            'get'
        )
    },
    showData: function (d) {
        mjcGdjjCommon.showNoData();
        if (d.errorCode == 0) {
            if (Object.keys(d.value).length != 0) {
                if( mjcGdjjCommon.channelType == 'football'){
                    mjcGdjjCommon.checkFailResultFb(d.value);
                    if(d.value.isCancel != 1) {
                        mjcGdjjCommon.getMatchResultHtmlFb(d.value);
                    }
                }else{
                    mjcGdjjCommon.checkFailResult(d.value);
                    mjcGdjjCommon.getMatchResultHtmlBk(d.value);
                }
            }
        }
    },
    showNoData: function () {
        $('.content').css('display','none')
        $('.no-result').css('display','none')
        $(".no-result1").css('display','none')
    },
    checkFailResult: function (data) {

        var tempFaultHtml = "";
        var checkStatus = true;
        var mchInfo = data.matchInfo;
        var mchHis = data.oddsHistory;
        var mchRes = data.matchResult;
        for (var k = 0; k < mjcGdjjCommon.pool_list.length; k++) {
            var element = mjcGdjjCommon.pool_list[k];
            if(element.code == "mnl" || element.code == "wnm"){
                var resData = mchHis[element.code+'List'];
            }else{
                var resData = Object.keys(mchHis[element.code+'List']);
            }
            if (resData && resData.length > 0){
                tempFaultHtml += '<div class="m-lotteryResult-td"><div class="left">'+element.name+'</div></div>';
            }
        }
        if(mchInfo.sectionsNo999 =="-1:-1"){
            tempFaultHtml += '<div class="m-data-none"><div>单场：<span>退票</span><br/>过关：<span>所有投注选择无效</span></div></div>';
            checkStatus = false;
        } else {
            if (mchRes == "" || JSON.stringify(mchRes) == '{}') {
                tempFaultHtml += '<div class="m-data-none">暂未开奖</div>';
                checkStatus = false;
            }
        }
        if(checkStatus == false){
            $("#match_rs").append(tempFaultHtml);
        }else{
            mjcGdjjCommon.showMatchResultHtml(mchRes);
        }
    },
    checkFailResultFb: function (data) {
        var tempFaultHtml = "";
        var checkStatus = true;
        //var mchInfo = data.matchInfo;
        var mchHis = data.oddsHistory;
        var mchRes = data.matchResultList;

        if(data.sectionsNo999 == '无效场次'){
            tempFaultHtml += '<div class="m-none" style="padding:40px; text-align:center">'+
                '<div class="u-game">无效场次,请关注<a href="//m.sporttery.cn/ssgg/">赛事公告</a>。</div>'+

                '</div>'
            checkStatus = false;
        }else if(data.matchResultList.length ===0){
            tempFaultHtml += '<div class="m-none" style="padding:40px; text-align:center">'+
                '<div>暂无数据</div>'+
                '<div class="u-game">游戏：胜平负、让球胜平负、比分、总进球、半全场胜平负</div>'+
                '</div>'
            checkStatus = false;
        }
        if(data.isCancel =="1"){
            $('.content').css('display','none')
            $('.no-result2').css('display','block');
        }else {
            if (checkStatus == false) {
                $("#match_rs").append(tempFaultHtml);
                $('.m-none').css("display", "inline")
            } else {
                mjcGdjjCommon.showMatchResultHtmlFb(mchRes);
            }
        }
    },
    showMatchResultHtml: function (d) {
        var mr_tr = {mnl:"",hdc:"",hilo:"",wnm:""};
        for (var k = 0; k < mjcGdjjCommon.pool_list.length; k++) {
            var element = mjcGdjjCommon.pool_list[k];
            var tempHtml = "";
            var resData = d[element.code+'ResultList'];
            if (resData.length > 0){
                tempHtml += '<div class="m-lotteryResult-td"><div class="left">'+element.name+'</div><div class="middle">';
                var tempResultHtml = "";
                var tempOddsHtml = "";
                for (var i = 0; i < resData.length; i++) {
                    var ele = resData[i];
                    tempResultHtml += '<div>';
                    if(JSON.stringify(ele.goalLine) != "{}" && ele.goalLine != ""){
                        tempResultHtml += '('+ele.goalLine+')';
                    }
                    var resultColor = "";//区分颜色，负为蓝色时改为bgblue
                    if(ele.combination){
                        if(element.code == "wnm"){
                            if(ele.combination > 0){
                                resultColor = "bgred";
                            }
                        }else{
                            if(ele.combination.toLowerCase() == "h"){
                                resultColor = "bgred";
                            }
                        }
                        resultColor = "bgred";
                    }
                    tempResultHtml += '<span class="'+resultColor+'">'+(ele.combinationDesc?ele.combinationDesc:'--')+'</span></div>'
                    tempOddsHtml += '<div>'+(ele.odds?ele.odds:'--')+'</div>';
                }
                mr_tr[element.code] = tempHtml + tempResultHtml + '</div><div class="right">' + tempOddsHtml + '</div></div>';
            }
        }
        $("#match_rs").append(mr_tr.mnl+mr_tr.hdc+mr_tr.hilo+mr_tr.wnm);
    },
    showMatchResultHtmlFb: function (d) {
        var tmpResult ={}
        Object.keys(d).forEach(function(h){
        tmpResult[d[h].code.toLowerCase()] = d[h]
        })
        var mr_tr = {had:"",hhad:"",crs:"",ttg:"",hafu:""};
        var tempHtmlTh = '<div class="m-lotteryResult-th"><div class="left">游戏</div><div class="middle">开奖结果</div><div class="right">奖金</div></div>';
        for (var k = 0; k < mjcGdjjCommon.pool_list_fb.length; k++) {
            var element = mjcGdjjCommon.pool_list_fb[k];
            var resData = tmpResult[element.code];
            var tempHtml = '';
            var tempResultHtml = "";
            var tempOddsHtml = "";
            var ele = resData;
            if(element.code !='hhad'){
                tempHtml += '<div class="m-lotteryResult-td"><div class="left">'+element.name+'</div><div class="middle">';
            }else{
                if(ele){
                    if(ele.combinationDesc && ele.combinationDesc !=''){
                        tempHtml += '<div class="m-lotteryResult-td"><div class="left">'+element.name+'</div><div class="middle">';
                    }else{
                        tempHtml += '<div class="m-lotteryResult-td"><div class="left">'+element.name+'('+ ele.goalLine+')</div><div class="middle">';
                    }
                }else{
                    tempHtml += '<div class="m-lotteryResult-td"><div class="left">'+element.name+'</div><div class="middle">';
                }

            }
            var resultColor = "bgred";//区分颜色，负为蓝色时改为bgblue
            if (resData && Object.keys(resData).length > 0){
                tempResultHtml += '<div>';
                resultColor = "bgred"
                tempResultHtml += '<span class="'+resultColor+'">'+(ele.combinationDesc?ele.combinationDesc:'--')+'</span></div>'
                tempOddsHtml += '<div>'+(ele.odds?ele.odds:'--')+'</div>';
            }else{
                tempResultHtml += '<div>';
                resultColor = "";//区分颜色，负为蓝色时改为bgblue
                tempResultHtml += '<span class="'+resultColor+'">--</span></div>'
                tempOddsHtml += '<div>--</div>';
            }
            mr_tr[element.code] = tempHtml + tempResultHtml + '</div><div class="right">' + tempOddsHtml + '</div></div>';
        }

        var allStr = '<div class="m-lotteryResult-table">'+tempHtmlTh+mr_tr.had+mr_tr.hhad+mr_tr.crs+mr_tr.ttg+mr_tr.hafu + "</div>"
        $("#match_rs").append(allStr);
    },
    showSingleIcon: function (d) {
        for(var i=0; i<d.length; i++){
            if(d[i].single == 1){
                var game = d[i].poolCode;
                if(game == 'TTG' || game == 'HAFU' || game == 'CRS'){
                    $("#"+game.toLowerCase()+" .m-title").addClass('u-bgdan');
                }else{
                    $("#"+game.toLowerCase()).parent().find(".m-title").addClass('u-bgdan');
                }
            }
        }
    },
    getTrendHtml: function (d) {
        var arrow = "<em></em>";
        var up_str="<em><img src='//static.sporttery.cn/res_1_0/jcwm/images/ico-up1.png'></em>";
        var down_str="<em><img src='//static.sporttery.cn/res_1_0/jcwm/images/ico-dw1.png'></em>";
        if(d == "1"){
            arrow = up_str;
        }else if(d == "-1"){
            arrow = down_str;
        }
        return arrow;
    },
    getResultObj: function (r) {
        var resultObj = {'had':'','hhad':'','ttg':'','hafu':'','crs':''};
        if(r.length > 0){
            for(i in r){
                var game = r[i].code.toLowerCase();
                resultObj[game] = r[i].combination.toLowerCase();
            }
        }
        return resultObj;
    },
    getMatchResultHtmlFb: function (rs) {
        if(JSON.stringify(rs.oddsHistory) == "{}"){
            //mjcGdjjCommon.showNoData();
            //return;
        }
        $(".content").css("display","block")
        var odds_list = rs.oddsHistory;
        var pool_rs = mjcGdjjCommon.getResultObj(rs.matchResultList);
        var str ="";
        var poolList = ['had','hhad','ttg','hafu','crs'];
        //mjcGdjjCommon.showSingleIcon(odds_list.singleList);
        for(var i=0; i<poolList.length; i++){
            var game = poolList[i];
            switch (game){
                case "ttg":
                    var list = odds_list.ttgList;
                    if(list !=undefined && list.length > 0){
                        str =''
                    }else{
                        $("#"+game+"_none").css('display','flex');
                        $("#"+game+"_rs").html('--');
                        continue;
                    }
                    var resultName = pool_rs[game];
                    var ars = pool_rs[game].replace('+','');
                    for(var j=0; j<list.length; j++){
                        var odd = list[j];
                        str += "<div class='m-time'>发布时间："+ odd.updateDate + " " + odd.updateTime +"</div><ul class='m-data'>";
                        for(z=0;z<8;z++){
                            if(z<7){
                                str +="<li><p class='u-tt2'>"+z+"</p>"
                            }else{
                                str +="<li><p class='u-tt2'>"+z+"+</p>"
                            }
                            var ele='s'+z;
                            var trend='s'+z+'f';
                            var rs_class=(String(z)===ars)?"class=''":"";
                            var d_arrow = mjcGdjjCommon.getTrendHtml(odd[trend]);
                            // str += "<span  "+rs_class+">"+odd[ele]+ d_arrow +"</span>";
                            str += "<p class='u-odds'>"+odd[ele]+ d_arrow +"</p>";
                            str += "</li>";
                        }
                        str += "</li></ul>";
                    }
                    $("#"+game+"_rs").html(resultName?resultName:'--');
                    $("#"+game).append(str);
                    break;
                case "hafu":
                    var list = odds_list.hafuList;
                    if(list !=undefined && list.length > 0){
                        str =''
                    }else{
                        $("#"+game+"_none").css('display','flex');
                        $("#"+game+"_rs").html('--');
                        continue;
                    }
                    var ars = pool_rs[game].replace(":","");
                    var items={'hh':'胜胜','hd':'胜平','ha':'胜负','dh':'平胜','dd':'平平','da':'平负','ah':'负胜','ad':'负平','aa':'负负'};
                    for(var j=0; j<list.length; j++){
                        var odd = list[j];
                        str += "<div class='m-time'>发布时间："+ odd.updateDate + " " + odd.updateTime +"</div><ul class='m-data'>";
                          for(ele in items){
                            str +="<li>"
                            str += "<p class='u-tt2'>"+items[ele]+"</p>";
                            var trend=ele+'f';
                            var rs_class=(ele==ars)?"class=''":"";
                            var d_arrow = mjcGdjjCommon.getTrendHtml(odd[trend]);
                            //str += "<span "+rs_class+">"+odd[ele]+ d_arrow +"</span>";
                            str += "<p class='u-odds'>"+odd[ele]+ d_arrow +"</p>";
                            str += "</li>";
                        }
                        str += "</ul>";
                    }
                    $("#"+game+"_rs").html(items[ars]?items[ars]:'--');
                    $("#"+game).append(str);
                    break;
                case "crs":
                    var list = odds_list.crsList;
                    if(list !=undefined && list.length > 0){
                        str =''
                    }else{
                        $("#"+game+"_none").css('display','flex');
                        $("#"+game+"_rs").html('--');
                        continue;
                    }
                    var ars = pool_rs[game].replace(":-","s");
                    var items=new Array();
                    items.push(['s01s00','s02s00','s02s01','s03s00','s03s01','s03s02','s04s00','s04s01','s04s02','s05s00','s05s01','s05s02','s-1sh']);
                    items.push(['s00s00','s01s01','s02s02','s03s03','s-1sd']);
                    items.push(['s00s01','s00s02','s01s02','s00s03','s01s03','s02s03','s00s04','s01s04','s02s04','s00s05','s01s05','s02s05','s-1sa']);
                    //var titleHtml = ["<li class='u-tt2'><span>1:0</span><span>2:0</span><span>2:1</span><span>3:0</span><span>3:1</span><span>3:2</span><span>4:0</span></li>","<li class='u-tt2'><span>4:1</span><span>4:2</span><span>5:0</span><span>5:1</span><span>5:2</span><span>胜其它</span></li>","<li class='u-tt2'><span>0:0</span><span>1:1</span><span>2:2</span><span>3:3</span><span>平其它</span></li>","<li class='u-tt2'><span>0:1</span><span>0:2</span><span>1:2</span><span>0:3</span><span>1:3</span><span>2:3</span><span>0:4</span></li>","<li class='u-tt2'><span>1:4</span><span>2:4</span><span>0:5</span><span>1:5</span><span>2:5</span><span>负其它</span></li>"];
                    var resultName = {"s-1sh": "胜其它", "s-1sd": "平其它", "s-1sa": "负其它"};
                    if(ars.indexOf('-1') != -1){
                        ars = "s"+ars;
                        var resultHtml = resultName[ars];
                    }else{
                        var resultHtml = ars;
                        ars = "s0"+ars.replace(":","s0");
                    }

                    for(var j=0; j<list.length; j++){
                        var odd = list[j];
                        str += "<div class='m-time'>发布时间："+ odd.updateDate + " " + odd.updateTime +"</div><ul class='m-data m-data-1'>";
                        for(y in items){
                            var ele=items[y];
                            //str += titleHtml[y];
                            var scoreTitle='';
                            for(x in ele){
                                if(ele[x].indexOf('-1') != -1){

                                    scoreTitle = resultName[ele[x]];
                                }else{
                                    scoreTitle = ele[x].replaceAll("s0",":").substring(1);
                                }
                                str += "<li>";
                                str += "<p class='u-tt2'>"+scoreTitle+"</p>";
                                var eleLine=ele[x];
                                var trend=eleLine+'f';
                                var rs_class=(eleLine==ars)?"class=''":"";
                                var d_arrow = mjcGdjjCommon.getTrendHtml(odd[trend]);
                                // str += "<span "+rs_class+">"+odd[eleLine]+ d_arrow +"</span>";
                                str += "<p class='u-odds'>"+odd[eleLine]+ d_arrow +"</p>";
                                str += "</li>";
                            }
                            str +='<li class="u-line"></li>'
                        }
                        str += "</ul>";
                    }
                    $("#"+game+"_rs").html(resultHtml?resultHtml:'--');
                    $("#"+game).append(str);
                    break;
                default:
                    var list = odds_list[game+'List'];
                    var resultName = {'had':{'h':'胜','d':'平','a':'负'},'hhad':{'h':'让胜','d':'让平','a':'让负'}};
                    var curResult = resultName[game];
                    var ars = pool_rs[game];
                    var goalLine = '';
                    if(list != undefined && list.length > 0){
                        str =''
                    }else{
                        $("#"+game).css('display','none');
                        $("#"+game+"_none").css('display','flex');
                        $("#"+game+"_rs").html('--');
                        continue;
                    }
                    for(var j=0; j<list.length; j++){
                        var odd = list[j];
                        str += "<li>";
                        str += "<i>" +odd.updateDate+" "+odd.updateTime+"</i>";
                        for(x in curResult){
                            var eleLine=curResult[x];
                            var trend=x+'f';
                            var rs_class=(x==ars)?"class=''":"";
                            var d_arrow = mjcGdjjCommon.getTrendHtml(odd[trend]);
                            str += "<span "+rs_class+">"+odd[x]+ d_arrow +"</span>";
                        }
                        str += "</li>";
                        goalLine = odd.goalLine;
                    }
                    $("#"+game+"_rs").html(curResult[ars]?curResult[ars]:'--');
                    if(goalLine != ""){
                        $("#hhad_goalline").html("（" + goalLine + "）");
                    }
                    $("#"+game).append(str);
                    break;
            }

        }
    },
    getMatchResultHtmlBk: function (rs) {
        if(JSON.stringify(rs.oddsHistory) == "{}"){
            mjcGdjjCommon.showNoData();
            return;
        }
        if (Object.keys(rs.oddsHistory).length>0) {

            if (rs.oddsHistory.mnlList.length <=0 &&
                Object.keys(rs.oddsHistory.hdcList).length<=0 &&
                Object.keys(rs.oddsHistory.hiloList).length<=0 &&
                rs.oddsHistory.wnmList.length <=0 ) {
                    var tmp = ' <div class="m-lotteryResult-th">'+
                    '<div class="left">游戏</div>'+
                    '<div class="middle">开奖结果</div>'+
                    '<div class="right">奖金</div>'+
                '</div>'+
            '<div class="m-lotteryResult-td"><div class="left">胜负</div></div><div class="m-lotteryResult-td"><div class="left">让分胜负</div></div><div class="m-lotteryResult-td"><div class="left">大小分</div></div><div class="m-lotteryResult-td"><div class="left">胜分差</div></div><div class="m-data-none">暂未开奖</div>';
                    $("#match_rs").html(tmp);
                    for(var i=0; i<$('.m-recentCompetition').length; i++){
                        if(i !=0){
                            $('.m-recentCompetition').eq(i).css("display","none");
                        }
                    }
                    //return;
                }
        }
        var odds_list = rs.oddsHistory;
        var pool_rs = ['mnl','hdc','hilo','wnm'];
        var str ="";
        //mjcGdjjCommon.showSingleIcon(odds_list.singleList);
        for(var i=0; i<pool_rs.length; i++){
            var game = pool_rs[i];
            str = "";
            switch (game){
                case "mnl":
                    var list = odds_list.mnlList;
                    str += '<div class="m-fixedBonus-th"><div class="left">发布时间</div><div class="middle">主负</div><div class="right">主胜</div></div>';
                    var resultName = '--';
                    if(list.length > 0){
                        for(var j=0; j<list.length; j++){
                            var odd = list[j];
                            str += mjcGdjjCommon.getHistoryLineHmtl(odd, game);
                        }
                        resultName = list[0].combinationDesc?list[0].combinationDesc:'--';
                        $("#"+game+"_rs").html('彩果<span class="bgred">' + resultName + '</span>');
                        $("#"+game).html(str);
                    }else{
                        $("#"+game+"_rs").parents(".m-recentCompetition").hide();
                    }
                    break;
                case "wnm":
                    var list = odds_list.wnmList;
                    var resultName = '--';
                    if(list.length > 0){
                        for(var j=0; j<list.length; j++){
                            var odd = list[j];
                            var ars = odd.combination?odd.combination.replace("-","l").replace("+","w"):'';
                            var strl = '', strw = '';
                            for(z=1;z<7;z++){
                                var l_ele='l'+z;
                                var w_ele='w'+z;
                                var l_class={odds:odd['l'+z], trend:odd[l_ele+'f']};
                                var w_class={odds:odd['w'+z], trend:odd[w_ele+'f']};
                                var l_arrow = mjcGdjjCommon.getTrendHtmlBk(l_class);
                                var w_arrow = mjcGdjjCommon.getTrendHtmlBk(w_class);
                                strl +='<td>'+l_arrow+'</td>';
                                strw +='<td>'+w_arrow+'</td>';
                            }
                            str +='<div class="m-winningDifference">'+
                            '<div class="m-time">发布时间<span>'+odd.updateDate +" "+ odd.updateTime + '</span></div>'+
                            '<table class="m-winningDifference-table" border="0" cellpadding="0" cellspacing="0">'+
                            '<tr><th></th><th>1-5</th><th>6-10</th><th>11-15</th><th>16-20</th><th>21-25</th><th>26+</th></tr>';
                            str += '<tr><td><div class="u-name">客胜</div></td>';
                            str += strl;
                            str += '</tr>';
                            str += '<tr><td><div class="u-name">主胜</div></td>';
                            str += strw;
                            str += '</tr></table></div>';
                        }
                        resultName = list[0].combinationDesc?list[0].combinationDesc:'--';
                        $("#"+game+"_rs").html('彩果<span class="bgred">' + resultName + '</span>');
                        $("#"+game).append(str);
                    }else{
                        $("#"+game+"_rs").parents(".m-recentCompetition").hide();
                    }
                    break;
                default:
                    var list = odds_list[game+'List'];
                    str += '<div class="m-fixedBonus-th"><div class="left">发布时间</div>';
                    if(game == 'hdc'){
                        str += '<div class="middle">主负</div><div class="right">主胜</div>';
                    }else{
                        str += '<div class="middle">大</div><div class="right">小</div>';
                    }
                    str += '</div>';
                    if(Object.keys(list).length>0){
                        Object.keys(list).forEach(function(h){
                            str += '<div class="m-fixedBonus-td-letPoints"><div class="m-fixedBonus-td"><div class="black">'+(game=="hdc"?"让分":"预设总分")+'<span>（'+h+'）</span></div><div class="m-title-right">彩果<span class="bgred">'+(list[h][0]['combinationDesc']?list[h][0]['combinationDesc']:"--")+'</span></div></div>';
                            for(var j=0; j<list[h].length; j++){
                                var odd = list[h][j];
                                str += mjcGdjjCommon.getHistoryLineHmtl(odd, game);
                            }
                            str += '</div>';
                        });
                        $("#"+game).append(str);
                    }else{
                        $("#"+game).parents(".m-recentCompetition").hide();
                    }
                    break;
            }
        }
    },
    getHistoryLineHmtl: function (d, g) {
        var str = "";
        var col_content = {};
        if (g == "hilo") {
            col_content = {c1: {odds:d.h, trend:d.hf}, c2: {odds:d.l, trend:d.lf}};
        }else{
            col_content = {c1: {odds:d.a, trend:d.af}, c2: {odds:d.h, trend:d.hf}};
        }
        str = '<div class="m-fixedBonus-td">';
        str += '<div class="left">'+d.updateDate+ ' '+d.updateTime+'</div>';
        str += '<div class="middle">';
        str += mjcGdjjCommon.getTrendHtmlBk(col_content.c1);
        str += '</div><div class="right">';
        str += mjcGdjjCommon.getTrendHtmlBk(col_content.c2);
        str += '</div></div>';
        return str;
    },
    getTrendHtmlBk: function (d) {
        var arrow = '<span class="black">'+ d.odds +'</span><span class="icon-none"></span>';
        var up_str='<span class="icon-up"></span>';
        var down_str='<span class="icon-down"></span>';
        if(d.trend == "1"){
            arrow = '<span class="black">'+ d.odds +'</span>' + up_str;//如字和向上箭头同时变红时改为red
        }else if(d.trend == "-1"){
            arrow = '<span class="black">'+ d.odds +'</span>' + down_str;//如字和向下箭头同时变蓝时改为blue
        }
        return arrow;
    }
}
