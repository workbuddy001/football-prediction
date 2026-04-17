var urls = ['/jczx/jczq/bsxxv1/','/zqlszl/bssj/','/mjc/zqtj/','/mjc/zqzb/','/mjc/zqgdjjv1/'];
var navs = ['资讯', '前瞻','统计','直播','固定奖金'];
var tracks = ['matchInfo', 'matchDetail','matchStatistics','matchLive', 'fixedBonus']
$(document).ready(function(){
	try {
		if (commonV1Fun.getPara('SHA') == "false") {
			$(".g-header").css("display", "none");
			$(".g-more-mask").css("display", "none");
			$(".g-cont").addClass("g-cont-2").removeClass("g-cont-1");
		}
	} catch (e) {}

	var url = window.location.href;
	if(url.indexOf('match_hhad.html') >-1|| url.indexOf('match_asia.html')>-1){
		window.location.href='//info.sporttery.cn/bdjj.html';
		return;
	}
	var hrefStr = str = ''
	//获取参数串
	hrefStr = mjcDzxxCommon.queryString()
	var LinkLen = navs.length
	if(mjcDzxxCommon.midStr == null || mjcDzxxCommon.midStr == ''){
		LinkLen = navs.length - 3
	}
	for(var i=0; i<LinkLen; i++){
		var css = '';
		var u = window.location.href;

		if(u.indexOf(urls[i]) > 0) {
			css = "class='active'";
		}
		str +='<div><a onclick="clickTabs(\''+tracks[i]+'\', \''+urls[i]+'?'+hrefStr+'\')"' +css + ' >'+navs[i]+'</a></div>'
	}
	$("#matchDataNav").html(str);
	//$('.g-cont').scroll(function(){
	if(url.indexOf('/bssj/') < 0){
		$(window).scroll(function(){
			if($(window).scrollTop() >$('.m-matchData-team').height()){
				$("#matchDataNav").css("position", "fixed");
				$("#matchDataNav").css("box-shadow", '0 0.06rem 0.06rem 0 rgba(0,0,0,0.10)')
			}else{
				$("#matchDataNav").css("position", "relative");
				$("#matchDataNav").css("box-shadow", 'none')
			}

		})
	}
})
function clickTabs(type,url){
	var op_desc={
		wbsjMatchId: mjcDzxxCommon.gmStr,
		matchId: mjcDzxxCommon.midStr,
		leagueId:mjcDzxxCommon.sportteryTournamentId,
		wbsjLeagueId:mjcDzxxCommon.tournamentId,
	}
	try{
		//dc.trackEvent('click_matchData_'+type,  op_desc)
		bdEvent('click_matchData_'+type, JSON.stringify(op_desc));
		//bdEvent('click_matchData_'+type, '点击比赛信息按钮', 'click', '');  //翻转事件
	}catch(error){

	}
	window.location.href = url;
}