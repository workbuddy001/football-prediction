import { getQueryKey } from '../common/util.js';
import { getMatchFeatureV1, getResultHistoryV1, getMatchTablesV1, getInjurySuspensionV1, getMatchPlayerV1, getFutureMatchesV1, getMatchResultV1 } from '../common/apis.js';
const app =  Vue.createApp({
    data() {
      return {
        notShowJcJfbAry:[], //竞彩开售不展示积分榜的赛事，填入相应的赛事的ID，如多个请用,分割 如['1234','3456']
        notShowWbsjJfbAry:[], // 竞彩未开售的赛事列表
        notShowJcShooterAry:[], //竞彩开售不展示射手信息模块，如多个请用,分割 如['1234','3456']
        notShowWbsjShooterAry:[], // 不竞彩未开售的赛事列表
        notShowJcInjuryAry:[], //竞彩开售不展示伤停的赛事，如多个请用,分割 如['1234','3456']
        notShowWbsjInjuryAry:[], // 竞彩未开售的赛事列表
        isShowJfb:true, //false 为不展示积分榜
        isShowShooter:true, //false 为不展示射手榜
        isShowInjury:true, //false 为不展示伤停
        tabTxt:["特征分析","历史交锋","积分榜","比赛近况","未来赛事","射手信息","伤停一览"],
        tabName:["featureAnalysis","historicalConfrontation","leagueTable","recentGames","futureMatch","shooterInfo","layOffList"],
        active: 0,
        info:[],
        noData:0, // 0:为接口返回问题，1：为无奖牌，2：有奖牌
        tabOffsetTop:'1.76rem',
        // 历史
        limit:5,
        tournamentFlag:0,
        homeAwayFlag:0,
        btnDisabled:true,
        // 比赛近况
        limitR:5,
        tournamentFlagR:0,
        homeAwayFlagR:0,
        btnDisabledR:true,
        matchHeader:{},
        sportteryMatchId:0, // 官方赛事ID
        matchId :0, //外部数据赛事ID
        midStr:'',//传入mid参数串
        matchFeature:{},
        featureSort :['last','sameHomeAway','eachHomeAway','eachSameHomeAway','goalAvg','lossGoalAvg'],
        featureTxt:['近10场交锋','同主客交锋','近10场战况','同主客战况','近10场场均进球','近10场场均失球'],
        resultHistory:{},
        matchTables:{},
        matchPlayer:{},
        matchResult:{},
        //homeMatchResult:{},
        //awayMatchResult:{},
        matchSort:['home','away'],//比赛近况、未来赛事、射手榜、伤停一览用
        futureMatches:{},
        injurySuspensioneature:{},
        EventTracking:{
            matchId:'',
            leagueId:''
        },
        mid: getQueryKey('mid'), // 竞彩开售
        gm: getQueryKey('gm'), // 竞彩不开售
        isSHA:getQueryKey('SHA'),
        isFixed:false,
        dispatchData:['mid','gm'],
        paramsStr:'',
        isScrollOver:false,
        t1:0,
        t2:0,
        timer:0,
        isShowBackTop: false,
      }
    },
    created() {
        if(this.mid == null){
            this.midStr = 'matchId='+this.gm
        }else{
            this.midStr = 'sportteryMatchId='+this.mid
        }
    },
    mounted(){
        this.getTabSHA()
        this.getMatchFeatureV1()
        this.getResultHistoryV1()
        this.getJfbShow()
        if(this.isShowJfb){
            this.getMatchTablesV1()
        }
        this.getMatchResultV1()
        this.getFutureMatchesV1()
        if(this.isShowShooter) {
            this.getMatchPlayerV1()
        }
        if(this.isShowInjury) {
            this.getInjurySuspensionV1();
        }
        this.paramsStr = mjcDzxxCommon.queryString(this.dispatchData)
    },
    methods:{
        getTabSHA(){
            if (this.isSHA == "false") {
                this.tabOffsetTop ='0.86rem';
                document.body.style.height='100vh';
            }else{
                this.tabOffsetTop = '1.76rem'
            }
        },

        scrollData(event){
            this.isScrollOver = false
            if (document.getElementById('lszl_1220').innerHTML =="") return false
            if(event.isFixed){
                document.getElementById('matchDataNav').style.position="fixed";
                this.isFixed = true
            }else{
                document.getElementById('matchDataNav').style.position="relative";
                this.isFixed = false
            }
           // const scrollTop = event.target.scrollTop;
            //console.log('滚动高度：', event,event.isFixed);
        // 处理scroll事件的逻辑
            clearTimeout(this.timer);
            this.t1 = this.getScrollTop();
            this.timer = setTimeout(this.isScrollEnd, 500);
        },
        isScrollEnd() {
            this.t2 = this.getScrollTop();
            if(this.t2 === this.t1){
              this.isScrollOver = true
            }
          },
        getScrollTop () {
            let scrollTmp = document.getElementsByClassName('g-matchData')[0].scrollTop
            let heightTmp = document.getElementsByClassName('g-matchData')[0].offsetHeight;
            if(scrollTmp > heightTmp){
                this.isShowBackTop = true
            }else{
                this.isShowBackTop = false
            }
            return scrollTmp
        },
        async getMatchFeatureV1(){
            try{
                let sendUrl = `${getMatchFeatureV1}?termLimits=10&${this.midStr}`;
                let res = await this.sendGet(sendUrl);
                this.matchFeature = {}
                if ( res.status == 200 && res.data.errorCode == "0") {
                    if (JSON.stringify(res.data.value) !== '{}') {
                        this.matchFeature = res.data.value
                    }
                }

            } catch (err) {
                //this.noData = 0
                console.log(err);
            }
        },
        async getResultHistoryV1(){
            try{
                // limit:5,
                // tournamentFlag:0,
                // homeAwayFlag:0,
                let sendUrl = `${getResultHistoryV1}?${this.midStr}&termLimits=${this.limit}&tournamentFlag=${this.tournamentFlag}&homeAwayFlag=${this.homeAwayFlag}`;
                let res = await this.sendGet(sendUrl);
                this.resultHistory = {}
                if ( res.status == 200 && res.data.errorCode == "0") {
                    this.btnDisabled = true
                    if (JSON.stringify(res.data.value) !== '{}') {
                        this.resultHistory = res.data.value
                    }
                }else{
                    this.btnDisabled = true
                }
            }catch (err) {
                console.log(err);
                this.btnDisabled = true
            }


        },
        async getMatchTablesV1(){
            try{
                let sendUrl = `${getMatchTablesV1}?${this.midStr}`;
                let res = await this.sendGet(sendUrl);
                this.matchTables = {}
                if ( res.status == 200 && res.data.errorCode == "0") {
                    if (JSON.stringify(res.data.value) !== '{}') {
                        this.matchTables = res.data.value
                    }
                }
            }catch(err){
                console.log(err);
            }
        },

        async getMatchPlayerV1(){
            try{
                let sendUrl = `${getMatchPlayerV1}?${this.midStr}&termLimits=3`;
                let res = await this.sendGet(sendUrl);
                this.matchPlayer = {}
                if ( res.status == 200 && res.data.errorCode == "0") {
                    if (JSON.stringify(res.data.value) !== '{}') {
                        this.matchPlayer = res.data.value
                    }
                }
            }catch(err){
                console.log(err);
            }
        },
        async getMatchResultV1(){
            try{
                let sendUrl = `${getMatchResultV1}?${this.midStr}&termLimits=${this.limitR}&tournamentFlag=${this.tournamentFlagR}&homeAwayFlag=${this.homeAwayFlagR}`;
                let res = await this.sendGet(sendUrl);
                this.matchResult = {}
                if ( res.status == 200 && res.data.errorCode == "0") {

                    this.btnDisabledR = true
                    if (JSON.stringify(res.data.value) !== '{}') {
                        this.matchResult = res.data.value
                    }
                }else{
                    this.btnDisabledR = true
                }
            } catch (err) {
                this.btnDisabledR = true
                console.log(err);
            }
        },
        async getFutureMatchesV1(){
            try{
                let sendUrl = `${getFutureMatchesV1}?${this.midStr}&termLimits=4`;
                let res = await this.sendGet(sendUrl);
                this.futureMatches = {}
                if ( res.status == 200 && res.data.errorCode == "0") {
                    if (JSON.stringify(res.data.value) !== '{}') {
                        this.futureMatches = res.data.value
                    }
                }
            } catch (err) {
                console.log(err);
            }
        },
        async getInjurySuspensionV1(){
            try{
                let sendUrl = `${getInjurySuspensionV1}?${this.midStr}`;
                let res = await this.sendGet(sendUrl);
                this.injurySuspensioneature = {}
                if ( res.status == 200 && res.data.errorCode == "0") {
                    if (JSON.stringify(res.data.value) !== '{}') {
                        this.injurySuspensioneature = res.data.value
                    }
                }
            } catch (err) {
                console.log(err);
            }
        },
        //设置当前球队色值 curTeamName：当前球队名, listTeamName：列表中球队名, matchResult：彩果
        setTeamColor(curTeamName, listTeamName, teamMatchResult){
            let color =''
            if(curTeamName == listTeamName){
                if(teamMatchResult =='home'){
                    color = 'm-red'
                }else if(teamMatchResult == 'draw'){
                    color = 'm-green'

                }else if (teamMatchResult == 'away'){
                    color = 'm-blue'
                }
            }
            return color

        },
        sendGet(url) {
            return axios.get(url);
        },
        sendPost(url, params) {
            return axios.post(url, params);
        },
        setScoreStyle(val){
            if(val=="" || val.indexOf(':')==-1) return ''
            let score = val.split(":")
            let scoreStr = "<div class='m-score'>";
                scoreStr +="<div class='m-score-left'>"+score[0]+"</div><div class='m-score-middle'>:</div><div class='m-score-right'>"+score[1]+"</div>"
                scoreStr+"</div>"
            return scoreStr
        },
        getFeatureStatus(key){
            if(key =='') return '-1'
             return this.featureSort.indexOf(key)
        },
        getFeatureHave(data){
            let keys = Object.keys(data);
            let num =0;
            if(keys.length>0){
                for(let i=0; i<keys.length; i++){
                    if(this.getFeatureStatus(keys[i])>-1){
                        // Object.keys(data[keys[i]]).length >0
                        num ++;
                    }
                }
            }
            return num;
        },
        setPercentage(val){
            let percent = '0'
            if(val=='' || val== undefined) return '0%';
            if(val+''.indexOf(".")>-1){
                percent = parseInt(val)*100 +"%"
            }else{
                percent = val>100? '100%': val+"%"
            }
            return percent
        },
        clickTabSecond(data){
            if(Object.keys(data).length >0) {
                this.setTrackEvent(data.name)
            }

        },
        /**
         *
         * @param {string} eventName 埋点名称
         * @param {string} url 跳转链接
         * @param {string} data 默认为空，传入球队信息
         * @param {string} dd 默认为空，传主客队
         * @returns
         */
        clickLink(eventName,url){
            if(url =='') return
            this.setTrackEvent(eventName)
            window.location.href = url+(this.paramsStr !=''?'&'+this.paramsStr:'');
        },
        /**
         *
         * @param {string} eventName 埋点名称
         * @param {string} data 默认为空，传入球队信息
         * @returns
         */
        clickLinkQd(eventName, data){
            let str=''
            // if(data.sportteryTeamId =='' && data.teamId =='' ){
            //     return false
            // }
            // if(data.sportteryTeamId !=''){
            //     str = 'tid='+data.sportteryTeamId
            // }else{
            //     str = 'wtid='+data.teamId
            // }
            str = 'tid='+data.sportteryTeamId
            this.setTrackEvent(eventName,data)
            window.location.href ='/zqlszl/qdzl/?'+str+(this.paramsStr !=''?'&'+this.paramsStr:'')
        },
        setTrackEvent(eventName, data={}){
            var op_desc={
                matchId: mjcDzxxCommon.midStr,
                wbsjMatchId: mjcDzxxCommon.gmStr,
                leagueId:mjcDzxxCommon.sportteryTournamentId,
                wbsjLeagueId:mjcDzxxCommon.tournamentId

            }
            op_desc.teamId = data.sportteryTeamId
            op_desc.wbsjTeamId = data.teamId
            try{
                dc.trackEvent('click_matchDetail_'+eventName, {'desc':JSON.stringify(op_desc)})
            }catch(error){

            }
        },
        /**
         *
         * @param {string} val 设置变量名称
         * @param {string} type 类型 his:历史对阵; rec:比赛近况
         * @returns
         */
         async clickBtn(val, type){
            this[val] == 0 ? this[val] = 1 : this[val] = 0
            let trackName ='historical_sameHomeAway'
            if(type == 'his'){
                // 请求历史对阵
                if(val == 'homeAwayFlag'){
                    trackName ='historical_sameHomeAway'
                }else{
                    trackName ='historical_sameLeague'
                }

                this.btnDisabled = false
                this.getResultHistoryV1();

            }else{
                // 请求比赛近况
                if(val == 'homeAwayFlagR'){
                    trackName ='recentGames_sameHomeAway'
                }else{
                    trackName ='recentGames_sameLeague'
                }
                this.btnDisabledR = false
                this.getMatchResultV1();

            }
            this.setTrackEvent(trackName)
        },
        /**
         *
         * @param {string} val 设置变量名称
         * @param {string} type 类型 his:历史对阵; rec:比赛近况
         * @param {Number} num 设置的值，5或10
         * @returns
         */
         async clickMatchNums(val, type, num){
            if(this[val] == num) return
            this[val] == 5 ? this[val] = 10 : this[val] = 5
            let trackName ='historical_last10'
            if(type == 'his'){
                // 请求历史对阵
                trackName ='historical_last10'
                if(num == 5){
                    trackName ='historical_last5'
                }
                this.btnDisabled = false
                this.getResultHistoryV1()

            }else{
                // 请求比赛近况
                trackName = 'recentGames_last10'
                if(num == 5){
                    trackName ='recentGames_last5'
                }
                this.btnDisabledR = false
                this.getMatchResultV1();

            }
            this.setTrackEvent(trackName)
        },
        setMatchFeatureTitle(txt, num){
            let name='';
            name = txt;
            if(txt.indexOf("10")>-1){
                name = txt.replace("10", num);
            }
            return name;
        },
        setBssjLink(data){
            if(data.sportteryMatchId =='' && data.matchId ==''){
                return false;
            }
            let str=''
            if(data.sportteryMatchId !=''){
                str = 'mid='+data.sportteryMatchId
            }else{
                str = 'gm='+data.matchId
            }
            window.location.href = '/zqlszl/bssj/?'+str+(this.paramsStr !=''?'&'+this.paramsStr:'')
        },
        setQdLink(tid){
            let str=''
            str = 'tid='+tid
            return '/zqlszl/qdzl/?'+str+(this.paramsStr !=''?'&'+this.paramsStr:'')
        },
        setNullFormat(val){
            if(val == null || val ==''){
                return '-'
            }
            return val
        },
        clickTop(){
            if(!this.isScrollOver){ return }
            this.isScrollOver = false
            document.getElementById('matchDataNav').style.position="relative";
            this.isFixed = false;
            this.isShowBackTop = false;
            document.getElementsByClassName('g-matchData')[0].scrollTop = 0

        },
        setScoreStyleLittle(val){
            if(val=="" || val.indexOf(':')==-1) return ''
            let score = val.split(":")
            let scoreStr = "<span>";
                scoreStr +="<span>"+score[0]+"</span><span class='m-colon'>:</span><span>"+score[1]+"</span>"
                scoreStr+"</span>"
            return scoreStr
        },
        /*处理时间YYYY 变为YY，或不展示时间*/
        dealCharacters(val, index){
            if(index < val.length){
                return val.substring(index)
            }else{
                return  val
            }
        },
        setDateToYY(dateStr){
            let da = new Date(dateStr.replaceAll('-','/'))
            let years = da.getFullYear()
            let month = (da.getMonth()+1)
            let days = da.getDate()
            let monthStr = month.toString().length ===1?'0'+month:month
            let dayStr=days.toString().length ===1?'0'+days:days
            let hour = da.getHours()
            let hourStr =  hour.toString().length ===1?'0'+hour:hour

            let minutes= da.getMinutes()
            let minutesStr= minutes.toString().length ===1?'0'+minutes:minutes
            return years.toString().substring(2)+'-'+monthStr +'-'+  dayStr + ' ' + hourStr+':'+ minutesStr;
        },
        linkToLeague(info, tab){
            if(info){
                let tabStr =''
                if(tab != undefined){
                    tabStr = '&tab='+tab
                }
               return '/zqlszl/?tournamentId='+info.tournamentId +tabStr +(this.paramsStr !=''?'&'+this.paramsStr:'') ;
            }else {
                return '#'
            }
        },
        // 判断积分榜、射手、伤停是否在前端展示
        getJfbShow(){
            if(this.notShowJcJfbAry.length ==0 && this.notShowWbsjJfbAry.length ==0) this.isShowJfb = true
            if(this.notShowJcShooterAry.length ==0 && this.notShowWbsjShooterAry.length ==0) this.isShowShooter = true
            if(this.notShowJcInjuryAry.length ==0 && this.notShowWbsjInjuryAry.length ==0) this.isShowInjury = true
            if(this.mid !=null && this.notShowJcJfbAry.indexOf(this.mid) > -1){
                this.isShowJfb = false;
            }else{
                if(this.notShowWbsjJfbAry.indexOf(this.gm) > -1) {
                    this.isShowJfb = false;
                }
            }
            if(this.mid !=null && this.notShowJcShooterAry.indexOf(this.mid) > -1){
                this.isShowShooter = false;
            }else{
                if(this.notShowWbsjShooterAry.indexOf(this.gm) > -1) {
                    this.isShowShooter = false;
                }
            }
            if(this.mid !=null && this.notShowJcInjuryAry.indexOf(this.mid) > -1){
                this.isShowInjury = false;
            }else{
                if(this.notShowWbsjInjuryAry.indexOf(this.gm) > -1) {
                    this.isShowInjury = false;
                }
            }
        }
    }
  })
  app.use(vant);
  app.use(vant.Tab);
  app.use(vant.Tabs);
  app.use(vant.BackTop);
  app.mount('#bssj')