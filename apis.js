import { url } from './util.js';
//根据栏目id查询文章列表接口
export const getNews = url + '/gateway/info/getInfoListByChannelV1.inf';
//今日提点-cms资讯吐露数据
export const getTodayImportant =
  '//www.sporttery.cn/push/todayimportant/todayimportant.pdata';
//足球根据比赛ID获取对阵及支持率接口
export const getMatchInfo =
  url + '/gateway/uniform/football/getMatchInfoAndVoteV1.qry';
//根据栏目id，tag,是否存在比赛Id查询文章列表接口
export const getInfoList =
  url + '/gateway/info/getInfoListByChannelAndTagV1.inf';
//根据比赛ID或是否推送APP查询文章列表接口
export const getInfoListByMatchV1 =
  url + '/gateway/info/getInfoListByMatchV1.inf';

//根据球队ID获取球队荣誉
export const getTeamThrophyListV1 =
  url + '/gateway/wbsj/football/getTeamThrophyListV1.qry';
//查询足球比赛公共头部消息
export const  getMatchHeadV1 =
  url + '/gateway/uniform/football/getMatchHeadV1.qry';
//查询比赛的主客队特征分析列表
export const  getMatchFeatureV1 =
  url + '/gateway/uniform/football/getMatchFeatureV1.qry';
//查询比赛数据历史交锋列表
export const  getResultHistoryV1 =
  url + '/gateway/uniform/football/getResultHistoryV1.qry';
//查询比赛数据积分榜列表
export const  getMatchTablesV1 =
  url + '/gateway/uniform/football/getMatchTablesV1.qry';
//查询比赛数据伤停信息
export const  getInjurySuspensionV1 =
  url + '/gateway/uniform/football/getInjurySuspensionV1.qry';
//查询足球比赛信息
export const  getInfoListByMatchV2 =
  url + '/gateway/info/getInfoListByMatchV2.inf';
//查询球队未来赛程列表
export const  getFutureMatchesV1 =
  url + '/gateway/uniform/football/getFutureMatchesV1.qry';
//查询球队赛果赛程列表
export const  getMatchResultV1 =
  url + '/gateway/uniform/football/getMatchResultV1.qry';
//比赛数据射手信息接口
export const  getMatchPlayerV1 =
  url + '/gateway/uniform/football/getMatchPlayerV1.qry';