# TVBox 多片源实时监测报告

- 生成时间：2026-11-25 21:59:14 +0800
- 站点总数：223
- 顶层 spider：https://raw.liucn.cc/box/fty.jar

## 状态统计

- **OK**: 211
- **NET_ERR**: 8
- **HTTP_ERR**: 4

## 待改进项（非 OK 站点）

| 站点 | key | 类型 | 问题 |
|---|---|---|---|
| 🎧有声┃小说 | 有声小说js | http | HTTP_ERR: HTTP 404 |
| 🐭┃贱贱┃P2P | 贱贱 | http | HTTP_ERR: HTTP 404 |
| 💣┃磁力p2p┃搜索 | drpy_js_lf_p2p | http | HTTP_ERR: HTTP 404 |
| 📽️聚短┃视频 | 聚短视频js | http | HTTP_ERR: HTTP 404 |
| ⛱┃可可┃采集 | 可可资源 | http | NET_ERR: <urlopen error [Errno 11001] getaddrinfo failed> |
| 🌪️暴风影音 | 暴风采集 | http | NET_ERR: <urlopen error timed out> |
| 🐉┃索尼┃高清 | csp_SNzy | http | NET_ERR: <urlopen error timed out> |
| 🐯┃奇虎┃采集 | 奇虎资源 | http | NET_ERR: <urlopen error [Errno 11001] getaddrinfo failed> |
| 👒┃小胡┃资源┃ | csp_小胡 | http | NET_ERR: 'latin-1' codec can't encode characters in position 2-3: ordinal not in range(25 |
| 🛰️飞速┃采集 | feisu | http | NET_ERR: <urlopen error [Errno 11001] getaddrinfo failed> |
| 🥗┃非凡┃资源 | csp_非凡资源 | http | NET_ERR: <urlopen error timed out> |
| 🦁┃四九┃资源 | 49zy | http | NET_ERR: <urlopen error [Errno 11001] getaddrinfo failed> |

## 说明

- `MISSING_CLASS`：Java 爬虫类缺失，切换过去必报『爬虫加载失败』→ 建议从配置剔除。
- `SCRIPT_ERR`：PY 脚本爬虫的脚本文件不可达 → 建议剔除。
- `HTTP_ERR`/`NET_ERR`：直连采集站当前不可达，可能是临时故障 → 可保留观察或剔除。
- `OK`：类存在(全局jar)/PY脚本可达/HTTP 200，可正常加载。
