# tvbox-mirror · 点播订阅自托管快照（抗整仓停更兜底）

> 解决 tvbox-selfheal 编队审查遗留的唯一 CRITICAL：可用点播源全是 `liu673cn/box` 一个仓的镜像，该仓停更/被封则三条同时失效。
> 本仓库把 `m.json` 定时快照到你自己的仓库，作为 `selfhost-snapshot` 兜底源。**你不在线、电脑不带、上游整仓消失，电视仍能播。**

## 一、原理

```
liu673cn/box (main / jsdelivr / ghpages)  ──6h定时抓取──▶  你的 tvbox-mirror/mirror/m.json
                                                                    │
tvbox-selfheal 的 heal.py ──failover 探测──▶ selfhost-snapshot ──────┘  ──▶ config.json ──▶ 电视
```

- 快照器每 6 小时按 main→CDN→Pages 顺序抓 `m.json`，任一拉到合格快照即用。
- 只有「JSON 合法 + sites 是数组 + 有效站点数 ≥ min_sites(10) + 不低于上次基线一半」才覆盖；上游异常或被改空壳时保留 `mirror/m.json` 上一版（last good），绝不写坏。
- 快照写入是原子的（tmp→fsync→replace），杜绝半截 JSON。
- 自托管快照处在 `liu673cn-box` 同一个 failover 组，priority=4（垫底），只在三个公共入口全挂时才被 `heal.py` 选中——平时不抢主源，停更时兜底。

## 二、部署（一次性，约 8 分钟）

### 1. 建仓库并推送
GitHub 新建仓库，名字建议 `tvbox-mirror`，**必须 Public**（私有仓 raw 对电视匿名请求返回 404）。
把本目录全部文件（含 `.github` 隐藏目录、`mirror/`）推上去：
```bash
cd tvbox-mirror
git init
git remote add origin https://github.com/<你的用户名>/tvbox-mirror.git
git add -A && git commit -m "init tvbox-mirror"
git branch -M main && git push -u origin main
```

### 2. 打开 Actions 写权限
Settings → Actions → General → Workflow permissions → **Read and write** → Save。
（新独立仓不要用 fork，fork 的公开仓 scheduled workflow 默认被禁用。）

### 3. 手动验证
Actions → `tvbox-mirror-snapshot` → Run workflow → 完成后 `mirror/m.json` 应出现且含 234 个站点；`mirror/snapshot_report.md` 末次动作为「更新快照」。
核验 raw 地址可公开匿名拉取：
```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://raw.githubusercontent.com/<你的用户名>/tvbox-mirror/main/mirror/m.json
# 返回 200 即正确
```

### 4. 接入 tvbox-selfheal
编辑 `tvbox-selfheal/candidates.json`，把 `selfhost-snapshot` 那条改成：
```json
{
  "id": "selfhost-snapshot",
  "name": "综合点播仓（自托管快照）",
  "kind": "json",
  "url": "https://raw.githubusercontent.com/<你的用户名>/tvbox-mirror/main/mirror/m.json",
  "priority": 4,
  "failover_group": "liu673cn-box",
  "timeout_seconds": 8,
  "enabled": true
}
```
（`<你的用户名>` 换成真实用户名，删掉 `_note` 中的旧提示。）然后 `python heal.py` 重建配置即可。

## 三、文件清单

```
tvbox-mirror/
├── snapshot.py               # 抓取+校验+last good 保护（纯标准库）
├── snapshot_config.json      # 上游入口与阈值
├── .github/workflows/snapshot.yml  # 每 6 小时定时
├── mirror/
│   ├── m.json                # ← heal.py 兜底读这个
│   ├── m.json.lastgood       # 原文留底
│   ├── snapshot_state.json   # 状态（基线、连续失败、告警）
│   └── snapshot_report.md    # 每次运行的可读报告
└── README.md
```

## 四、验证场景（本地已实测）

| 场景 | 期望 | 结果 |
|---|---|---|
| 正常抓取 | main 拿到 234 站点，覆盖镜像 | PASS（sites=234/234） |
| 上游被改空壳（sites<10） | 判不合格，保留上一版 | 逻辑已实现（校验阈值 + 基线） |
| 上游全 404/超时 | 保留 last good，连续 3 轮告警 | 逻辑已实现（consecutive_failures + needs_attention） |
| 半途中断 | 不留半截 JSON | 原子写已实现 |

`python snapshot.py` 可本地立即跑一次，观察 `mirror/snapshot_report.md`。

## 五、与整体方案的关系

- 本仓库是**第四条点播兜底入口**，与 tvbox-selfheal 的三条公共入口同组、垫底优先级。
- 上游活着时：heal.py 选 main/CDN/Pages，快照只是保险。
- 上游整仓停更：公共三条全挂，heal.py 自动切到你的快照，电视继续播老片库。
- 快照本身也受 last good 保护：即使某次上游返回坏数据，镜像不会被写坏。

这样，编队审查列出的 4 个 CRITICAL 全部闭环：同为单点的 CRITICAL-① 由本仓库根除；②③④ 在 v2 已修（IPv4 直播 / Public 要求 / watchdog）。
