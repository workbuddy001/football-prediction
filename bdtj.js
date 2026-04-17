var jstr = "https://static.sporttery.cn/res_1_0/tcw/default/common/js/tcdc_v1.0.0.min.js";
var consoleStr = 'https://static.sporttery.cn/res_1_0/jcwm/default/common/vconsole.min.js';
var dc;
var saconfig;
var dataFrom ={
  dev:"JingCaiWeb-Dev",
  test:"JingCaiWeb-Test",
  dt01:"JingCaiWeb-Test",
  dt02:"JingCaiWeb-Test",
  gray:"JingCaiWeb",
  prd:"JingCaiWeb"
}
var currentFrom = getEnv(jsCommonDataV1.env, dataFrom);
function getEnv(evn,data){
  var from = data.prd;
  if(evn != undefined){
    if(evn == "dev" || evn == "test" ||evn == "gray" ||evn == "prd"){
      from = data[evn];
    }
  } 
  return from;
}
setTimeout(tcTrackFun,3000)
function tcTrackFun(){
  try{
    var js=document.createElement("script");
    js.src=jstr;
    js.defer=true;
    js.onload=function(){
      saconfig = {
        "serverUrl": "https://receive.sporttery.cn?compress=0",
        "showLog": true,
        "baiduKey": "860f3361e3ed9c994816101d37900758",
        "dataFrom": currentFrom,
        "page_from":"JCMSite",
        "appName": "Wap",
        "source": "",
        "publicData": {
        }
      };
      dc= new TCDataCollect(saconfig,{});
    }
    document.getElementsByTagName('head')[0].appendChild(js);

  }catch(e){
  }
}

var isSHowConsoleDebug = window.location.href.indexOf('console')
if(isSHowConsoleDebug == -1){
  if(!!jsCommonDataV1 && !!jsCommonDataV1.env && jsCommonDataV1.env !='prd'){
    try{
      var js1=document.createElement("script");
      js1.src=consoleStr;
      js1.onload=function(){
        var vConsole = new window.VConsole();
      }
      document.getElementsByTagName('head')[0].appendChild(js1);
    }catch(e){
    }
  }
}
var probeWG1D5KmJs = {
  probeWG1D5KmJsStr: "https://static.sporttery.cn/res_1_0/jcwm/default/common/tingyun-origin.js",
  tokenOrKey:{
    dev:{
      "token":'2318b58b05884a05bb5334957c4a598b',
      "key":'yKd2voZ4f8c'
    },
    test:{
      "token":"d2eb0a2d2ecc488fbcf645534a4e20d7",
      "key":"3yP9pWESUtI"
    },
    dt01:{
      "token":"d2eb0a2d2ecc488fbcf645534a4e20d7",
      "key":"3yP9pWESUtI"
    },
    dt02:{
      "token":"095aac440a03419eba3df6191e912a8c",
      "key":"8ND8iY_AGr4"
    },
    gray:{
      "token":"939aad30df5f4a99b7163a921ebfaf8c",
      "key":"9otJUUDAaeg"
    },
    prd:{
      "token":"3d6edba1e66a4172832e0cb2e2f57907",
      "key":"jVR5d0mH9fQ"
    }
  },
  runProbeAPM:function (){
    try {
      var bjs = document.createElement("script")
      bjs.src = probeWG1D5KmJs.probeWG1D5KmJsStr
      bjs.type = "text/javascript"
      document.getElementsByTagName('head')[0].appendChild(bjs);
      var environment = jsCommonDataV1 && jsCommonDataV1.env && jsCommonDataV1.env !='' ?jsCommonDataV1.env:'prd'
      bjs.onload=function() {
        window.TingyunWeb("init",
            {
              "domain":"apkdata.sporttery.cn/guanyun/tybrs",
              "token":probeWG1D5KmJs.tokenOrKey[environment].token,
              "key":probeWG1D5KmJs.tokenOrKey[environment].key,
              "id":"4Nl_NnGbjwY",
              "ajax" : {
                "bodyMaxSize" : 10
              },
              "requestTracing" : {
                "propagators" : [ "tingyun" ]
              },
              "replay" : {
                "sampleRate" : 0.1
              },
              "webVitals" : {
                "ttiThreshold" : 4000
              }
            }  )
      }
    }catch (e){
    }
  }
}
setTimeout(probeWG1D5KmJs.runProbeAPM(), 3100)

/**
* @description: 点击事件统计，包括百度和G3
* @author: 李明
* @version: v1.0.0
* @param 
*    opt_label：点击事件名称，必传。
*    opt_desc：点击事件说明，必传。
*    category：点击元素的类型，可选。
*    action： 事件名称，可选。
*/
function bdEvent(opt_label, opt_desc) {
  try{
    var category = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : 'link';
    var action = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : 'click';
    if(opt_desc == '') opt_desc = '点击';
    dc.trackEvent({"eventName": opt_label},{"category":category,"platForm":action,"desc":opt_desc});
  }catch(e){    
  }
}
