var mjcDzxxCommon = {
    channelType:'football',
    midStr : commonV1Fun.getPara('mid'), 
    gmStr :commonV1Fun.getPara('gm'),
    tournamentId:'',
    sportteryTournamentId:'',
    matchIdStr:'',//sportteryMatchId 官方赛事ID; matchId 外部数据赛事ID
    dispatchData:['mid','gm'],
    paramsStr:'',
    getMatchTopData: function (type, matchId) {
        if(type) mjcDzxxCommon.channelType = type;
        var apiUrl = jsCommonDataV1.webApi + '/gateway/uniform/'+mjcDzxxCommon.channelType+'/getMatchInfoAndVoteV1.qry?matchId='+matchId;
        if(mjcDzxxCommon.channelType == "football"){
            if(mjcDzxxCommon.midStr !='' && mjcDzxxCommon.midStr != null){
                mjcDzxxCommon.matchIdStr = 'sportteryMatchId='+mjcDzxxCommon.midStr
            }else{
                 mjcDzxxCommon.matchIdStr ='matchId='+mjcDzxxCommon.gmStr
            }
            apiUrl = jsCommonDataV1.webApi + '/gateway/uniform/football/getMatchHeadV1.qry?source=m&'+mjcDzxxCommon.matchIdStr
        }
        commonV1Fun.ajaxFun(
            mjcDzxxCommon.showMatchTop,
            apiUrl,
            undefined,
            'get'
        )
    },
    showMatchTop: function (d) {
        if (d.errorCode == 0 && Object.keys(d.value).length != 0) {
            var str = (mjcDzxxCommon.channelType == "football") ? mjcDzxxCommon.getMatchHtmlFb(d.value) : mjcDzxxCommon.getMatchHtmlBk(d.value[0]);
            if(mjcDzxxCommon.channelType == "football"){
                $(".m-matchData-team").html(str); 
            }else{
                $(".m-matchData-team").html(str); 
            }
        }else{
            //$("body").html("请求参数异常！");
        }
    },
    getMatchHtmlFb: function (info) {
        mjcDzxxCommon.tournamentId = info.tournamentId
        mjcDzxxCommon.sportteryTournamentId = info.sportteryTournamentId
        mjcDzxxCommon.gmStr = info.matchId
        mjcDzxxCommon.midStr = info.sportteryMatchId
        mjcDzxxCommon.paramsStr = mjcDzxxCommon.queryString(mjcDzxxCommon.dispatchData);
        var errorImgH = jsCommonDataV1.resDomain + '/res_1_0/jcwm/images/dtc/icon_zd.png';
        var errorImgA = jsCommonDataV1.resDomain + '/res_1_0/jcwm/images/dtc/icon_kd.png';
        var tmpPara =''
        if(mjcDzxxCommon.paramsStr !=''){
            tmpPara ='&'+mjcDzxxCommon.paramsStr
        }
        var str ='<div class="left">'
        // if(info.sportteryHomeTeamId >0 && info.sportteryHomeTeamId !=''){
        //     str +='<a href="/zqlszl/qdry/?tid='+info.sportteryHomeTeamId+tmpPara+'">';
        // }else{
        //     str +='<a href="/zqlszl/qdry/?wbtid='+info.homeTeamId+tmpPara+'">';
        // }
        if(info.uniformHomeTeamId !=0) {
            str += '<a href="/zqlszl/qdzl/index.html?tid=' + info.uniformHomeTeamId + tmpPara + '">';
        }
        str +='<img src="'+info.homeTeamLogoPath+'" onerror="javascript:this.src=\''+errorImgH +'\'"/>'+
        '<div>'+
            '<span>'+info.homeTeamShortName+'</span>'+
        '</div>'
        if(info.uniformHomeTeamId !=0) {
            str +='</a>'
        }
        str +='</div>'+
    '<div class="middle">'+
        '<div class="matchTime">'
        if(info.matchNum !=''){
        str +='<span class="m-marr20">'+info.matchNum+'</span>'
        }
        str +='<span id="leagueId" c_id="'+info.tournamentId+'">'
        if(info.tournamentCnShortName !=''){
            str +='<a href="/zqlszl/?uniformLeagueId='+info.uniformLeagueId+'&tournamentId='+info.tournamentId+tmpPara+'">'+info.tournamentCnShortName+'>'+'</a>'
        }
        str +='</span></div>';
        if(info.fullCourtGoal !='' && info.fullCourtGoal !=undefined &&  info.fullCourtGoal  !='-1:-1'){
            str +='<div>'+mjcDzxxCommon.setScoreStyle(info.fullCourtGoal)+'</div>'
        }else{
            str += '<span class="vdata">VS</span>'
        }
        if(info.matchDateTime !=''){
            str +='<div class="matchTime2">'+info.matchDateTime+'</div>'
        }else{
            str +='<div>&nbsp;</div>'
        }
        
    str +='</div>'+
    '<div class="right">'
    // if(info.sportteryAwayTeamId >0 && info.sportteryAwayTeamId !=''){
    //     str +='<a href="/zqlszl/qdry/?tid='+info.sportteryAwayTeamId+tmpPara+'">';
    // }else{
    //     str +='<a href="/zqlszl/qdry/?wbtid='+info.awayTeamId+tmpPara+'">';
    // }
        if(info.uniformAwayTeamId !=0) {
            str += '<a href="/zqlszl/qdzl/index.html?tid=' + info.uniformAwayTeamId + tmpPara + '">';
        }
        str +='<img src="'+info.awayTeamLogoPath+'" onerror="javascript:this.src=\''+errorImgA +'\'"/>'+
        '<div>'+info.awayTeamShortName+'</div>'
        if(info.uniformAwayTeamId !=0) {
            str +='</a>'
        }
        str +='</div>'
        return str;
    },
    getMatchHtmlBk: function (info) {
        //var str = '<span class="u-icol"><img src="'+ info['awayLogo']+'"></span><span class="u-icor"><img src="'+ info['homeLogo']+'"></span><span><p class="num">'+ info['matchNum']+ " "+info['leagueNameAbbr'] + '</p><p class="agaside">'+info['awayTeam']+' VS '+ info['homeTeam'] +'</p><p class="date">'+ info['matchDateTime']+ '</p></span>'; 
        var str='<div class="matchTime"><span class="m-marr20">'+ info['matchNum']+'</span><span>'+info['leagueNameAbbr'] +" "+info['matchDateTime'].slice(0,-3)+'</span></div>'+
        '<div class="matchTeam">'+
            '<div class="left"><span class="u-venue">(客)</span><span>'+info['awayTeam']+'</span></div>'+
            '<div class="middle">VS</div>'+
            '<div class="right"><span>'+ info['homeTeam'] +'</span><span class="u-venue">(主)</span></div>'+
        '</div>';
        return str;
    },
    setScoreStyle: function(val){
        if(val=="" || val.indexOf(':')==-1  ) return ''
        let score = val.split(":")
        let scoreStr = "<div class='m-score'>";
            scoreStr +="<div class='m-score-left'>"+score[0]+"</div>"+
            "<div class='m-score-middle'>:</div>"+
            "<div class='m-score-right'>"+score[1]+"</div>"+
            "</div>"
        return scoreStr
    },
    // 获取?后面的参数
    getQueryStrings() {
        var data={};
        var parameter=(window.location.search.length>0)?window.location.search.substring(1):0;
        if(parameter!=0){
            var arg=parameter.split('&');
            for(var i=0;i<arg.length;i++){
                var name=decodeURIComponent(arg[i].split("=")[0]);
                var value=decodeURIComponent(arg[i].split("=")[1]);
                data[name]=value;
            }
        }else{
            data=null;
        }
        return data;
    },
    //参数拼接为字符串
    queryString(dispatchData){
        var parList = mjcDzxxCommon.getQueryStrings()
        if(parList == null) return
        var parKeys = Object.keys(parList);
        var hrefStr =''
        for(var j=0; j<parKeys.length; j++){
            if(dispatchData && dispatchData.length >0 && dispatchData !=undefined){
                if(dispatchData.indexOf(parKeys[j]) == -1){
                    if(hrefStr !=''){
                        hrefStr +="&";
                    }
                    hrefStr += parKeys[j] + "="+commonV1Fun.getPara(parKeys[j]);
                }
                    
            }else{
                if(hrefStr !=''){
                    hrefStr +="&";
                }
                hrefStr += parKeys[j] + "="+commonV1Fun.getPara(parKeys[j]);
            }
            
        }
        return hrefStr
    }
}
