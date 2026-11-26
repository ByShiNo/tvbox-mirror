# GitHub 活跃 TVBox 版本检索与选型（2026-11-26）

检索自 GitHub API（按 star / 更新时间排序）并逐个读 README、release 验证。
针对"FongMi leanback 遥控器填配置难用"这个痛点，重点找解决交互问题的版本。

## 一、活跃度总表（真实 star / 最后更新）

| 项目 | ★ | 最后更新 | 类型 | 许可 |
|---|---|---|---|---|
| youhunwl/TVAPP | 29.5k | 11-26 | APK 资源合集 | - |
| j4Uq/TVBoxOSC | 18.5k | 11-12 | TVBoxOSC 分支，release 20261111 | - |
| laoma528/awesome-zhuiju-free | 16.6k | 11-26 | 资源指南，每天检测 | CC BY |
| qist/tvbox | 13.3k | 11-26 | OK影视配置 | - |
| MoonTechLab/LunaTV | 11.0k | 09-10 | Web 影视站 | CC BY-NC-SA |
| gaotianliuyun/gao | 8.3k | 2024-11 | FongMi配置（停更） | - |
| 2hacc/TVBox | 5.9k | 2024-12 | TVBox接口（停更） | - |
| Decohererk/DecoTV | 2.4k | 07-16 | LunaTV二开，Web站 | NOASSERTION |
| **Zhou-Li-Bin/Tvbox-QingNing** | 2.2k | 11-25 | 接口+直播源聚合 | - |
| jinenge/tvbox | 1.2k | 06-14 | 内置源TVBox | - |
| **motao123/webtv (WebHomeTV)** | 217 | 11-22 | FongMi增强壳，release v5.17.4 | GPL-3.0 |
| **hein1225/HeinPlay** | 107 | 11-03 | Flutter跨平台，release 1.4.1 | - |
| dhicoc/FusionTV-KitKat | 20 | 10-04 | 老电视Android4.4优化 | GPL-3.0 |

> 高 star 的多是**配置源仓库**不是 App 本体；真正的 App 本体下面单列。

## 二、针对"难用"的推荐（已下载到桌面 + MuMu 实测）

### 推荐1：WebHomeTV v5.17.4 —— 直接解决遥控器填配置痛点 ⭐主推
- 源：github.com/motao123/webtv（基于 FongMi/CatVod 二开，包名同为 com.fongmi.android.tv）
- **核心卖点**：
  - **局域网管理页**：手机/电脑浏览器打开，直接填配置 URL、文件管理、远端遥控播放——不用在电视上用遥控器戳输入框
  - **一键同步**：配置/站源/脚本jar/WebHome/历史/收藏/登录态在手机与电视间迁移
  - **导入预检失败不覆盖**当前配置（比原版安全）
  - 三内核 EXO/IJK/MPV，多源更新+断点续传+SHA256校验+应用内更新
  - 域名无关：配置直接吃我现在用的 `clean-selfhost.json`
- 版本：v5.17.4（2026-11-21 发布，21 个包，每周更新）
- 选包：universal=不确定架构通用 / lite=精简(去掉MPV+Python，56MB) / arm64_v8a=64位 / armeabi_v7a=32位
- ⚠️ 首次启动会弹"远程依赖确认"——这是加载配置里 jar 的正常确认，选信任自己的配置即可
- **桌面包**：`WebHomeTV_leanback-lite-arm64_v8a_5.17.4.apk`（56MB，SHA256 3F89411173ABF2CDF8A6971E1F61CDB496844147EE8D078E0863B6FF081DBE3A）
- MuMu 实测：安装成功（versionName 5.17.4），主页正常，设置页含 Enhancements 增强功能入口

### 推荐2：海因影视 HeinPlay 1.4.1 —— 界面最好看、自动测速
- 源：github.com/hein1225/HeinPlay（Flutter 跨平台，每周更新）
- **核心卖点**：
  - 海报墙 + 豆瓣/Bangumi 评分 + 遥控器焦点导航（比 FongMi 的列表界面现代得多）
  - **详情页自动对所有播放源测速并排序**，无播放记录时测完再播——解决手动换源试错
  - 多播放器后端：ExoPlayer 默认(起播快)、mpv 备用(兼容 ffmpeg 网络栈，能放部分 ExoPlayer 连不上的源)
  - 完整直播体系：EPG 节目单、时移回放、LunaTV 内置源+M3U 自定义源
  - 片头片尾跳过、画面比例切换、控制栏自动隐藏
  - tvLegacy 版兼容 Android 5.0+ 老电视
- 版本：1.4.1（2026-10-30），另有鸿蒙/Windows/Linux/手机版
- **桌面包**：`HeinPlay_tv_1.4.1.apk`（63MB，SHA256 3B48D7093DDD8854C2B900AD79E1322EA8A041B098CFFE556EE4BF98EB43E57E）
- 架构：单个 tv.apk 通用；老电视用 tvLegacy.apk（桌面未下，需要可补）

### 备选3：j4Uq/TVBoxOSC —— 纯正原版 TVBoxOS 活跃分支
- 18.5k star，release 20261111（每周更新），基于 TVBoxOS + takagen99/Box
- 适合：想要最接近原生 TVBoxOS 体验、不 Enhanced 的用户
- 桌面未下载（需要可补）

### 备选4：dhicoc/FusionTV-KitKat —— 超老电视救星
- Android 4.4 ARM32 老电视优化版，2026-10 更新
- 适合：海信老机型（Android 4.4/5.x）装不上新版时用

## 三、配置兼容性（关键）

WebHomeTV 和 FongMi **包名相同、配置通用**，直接填现在的地址即可：
```
https://byshino.github.io/tvbox-mirror/clean-selfhost.json
```
HeinPlay 是独立生态，支持 M3U 直播 + 自己的源体系，点播源需要在它自己的数据源配置里加。

## 四、结论

- 嫌 FongMi 填配置难用 → **换 WebHomeTV**，用手机浏览器就能配置，这是对症下药
- 嫌 FongMi 界面丑/换源麻烦 → **换海因影视**，海报墙+自动测速排序
- 两个都是 2026-11 仍活跃更新、GPL/开源、配置不锁定
- 高 star 的 TVBoxOSC 是纯原版体验备选；FusionTV-KitKat 留给超老电视
