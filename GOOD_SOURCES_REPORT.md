# 好用播放源检索与实测报告（2026-11-26）

检索来源：GitHub 高星聚合仓（youhunwl/TVAPP 29k★、laoma528/awesome-zhuiju-free 16.6k★、
qist/tvbox 13.3k★、vbskycn/iptv 10.8k★、Lightconer/tvbox-ysc-config 523★ 每日自动更新）、
知乎 2026 教程、Gitee IPTV 合集。全部候选经本机 curl 硬超时实测，不是照抄清单。

## 判定口径
- 站点数 / 频道数：解析 JSON 的 `sites` 数组、M3U 的 `#EXTINF` 行
- 出片率：对每个源的直连采集站（type=1/0）真实请求 `?ac=list`，能返回影片列表算可用
- 资源可达：spider 主 jar/js 与样例 jar 国内 curl 实测（这是"爬虫加载失败"的关键——资源拉不到就必挂）
- 国内电视友好：spider/jar 走 github.io 或国内站 = 友好；走 raw.githubusercontent.com / jsdelivr 的 .jar = 电视端拉不到

---

## 一、点播源实测排名

| 源 | 站点数 | 直连出片率 | spider资源可达 | 能否直接填电视 |
|---|---|---|---|---|
| **clean-selfhost（自包含，我做的）** | 200 | 5/7 (71%) | github.io 全可达 | ✅ 直接填，已根治 |
| **单仓聚合（Lightconer）** | 549 | 10/30 (33%) | gelonghui 200，jar 相对路径 | ⚠ 需配套资源目录 |
| laoliubei（老刘备） | 234 | 5/15 (33%) | `./fty.jar` 相对路径 | ⚠ 需配套资源目录 |
| xiaoma（小马） | 62 | 5/16 (31%) | szyyds.cn 国内站 + gh-proxy | ✅ 可试，资源国内可达 |
| facat（肥猫） | 40 | 全JS站无法API测 | gelonghui 200 | ⚠ 全JS站，需js资源 |
| 4k（xhztv） | 53 | 2/9 (22%) | spider 403 + jar 000 | ❌ 资源挂了，别用 |

关键结论：站点数最多的"单仓聚合 549 站"和"老刘备 234 站"都用**相对路径 jar**（`./libs/jar/*.jar`、`./fty.jar`），
单独把 json 地址填进电视会因缺 jar 报"爬虫加载失败"——这正是之前踩的坑。
`clean-selfhost` 就是把这个资源目录整体镜像到 github.io 后能直接用的版本。

### 直连采集站里实测最快的（跨源通用，可直接作为换源优选）
| 站名 | API | 响应 |
|---|---|---|
| 非凡[直连] | ffzy.tv/api.php/provide/vod | 430ms |
| 建安 | 154.219.117.232:9981/jacloudapi.php | 122ms |
| 火狐采集 | hhzyapi.com/api.php/provide/vod | 890-1350ms |
| 量子资源 | lzizy1.com/api.php/provide/vod | 1012ms |
| 百度采集 | api.apibdzy.com/api.php/provide/vod | 1160-1517ms |
| 光速资源 | api.guangsuapi.com/api.php/provide/vod | 1320-1791ms |
| 虎牙采集 | huyaapi.com/api.php/provide/vod | 1119-2254ms |
| 淘片采集 | taopianapi.com/cjapi/mc/vod/json.html | 3197-4861ms（慢但片全） |

失效网站（各源共有，HTTP=0）：小胡(c.小胡.icu)、索尼(suoniapi.com)、电影天堂(caiji.dyttzyapi.com)、天涯(tyyszy.com)。

---

## 二、直播源实测排名

| 源 | 频道/线路 | 大小 | 实测延迟 | 评价 |
|---|---|---|---|---|
| **live-good（我筛选的）** | 390频道/714线路 | 63KB | 371ms | ✅ 全量curl验证可用，主力 |
| jiandantv-lite | 1598频道/1576线路 | 370KB | 533ms | ✅ 频道最多，备选 |
| iptv-org | 11512频道 | 2.66MB | 772ms | 国外台为主，体积大 |
| zbds-iptv4 | 339频道 | 80KB | 2898ms | 慢，备用 |
| fanmingming/index | 94频道 | 28KB | 344ms | ❌ 实测93个仅1个能连，已废 |
| zbds-iptv6 | 1频道 | 283B | 1380ms | ❌ 空源 |
| vbskycn | - | - | 561ms | ❌ raw路径404 |

---

## 三、最终推荐（好用且能在国内电视上真跑）

**点播**：`https://byshino.github.io/tvbox-mirror/clean-selfhost.json`
（200站，资源全镜像到 github.io，换源不报爬虫失败，已 MuMu 端到端验证）

**直播**：已集成在上面配置内部（live-good.m3u），不用单独填。
想要更多频道可手动追加：`https://fastly.jsdelivr.net/gh/jiandantv/IPTV2026@main/live_lite.m3u`

**备选点播**（主源出问题时换）：`https://fastly.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/xiaoma.json`
（小马源，spider 和 jar 都在国内可达站，62站精简）

**别用**：fanmingming 直播（已废）、4k/xhztv（资源403）、任何 raw.githubusercontent.com 开头的 jar/json（国内 SNI 阻断）。
