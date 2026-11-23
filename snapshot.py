#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tvbox-mirror · 点播订阅自托管快照器

作用：
    把公共点播仓的 m.json 抓到自己仓库的 mirror/ 目录，作为抗「上游整仓停更/被封」的兜底。
    - 多上游 failover：main → jsdelivr → ghpages，任一拉到合格快照即用
    - 严格校验：JSON 合法 + sites 是数组 + 有效站点数 >= min_sites，且不低于上次基线的一半
    - last good 保护：只有合格快照才覆盖 mirror/m.json；上游异常/被改空壳时保留上一版，绝不写坏
    - 原子写入：tmp -> fsync -> os.replace，杜绝半截 JSON
    - 每次运行写可读报告 mirror/snapshot_report.md 与状态 mirror/snapshot_state.json

纯 Python 标准库，GitHub Actions / 本地均可直接跑，无需 pip install。

用法：
    python snapshot.py
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
CONF = os.path.join(BASE, "snapshot_config.json")
MIRROR_DIR = os.path.join(BASE, "mirror")
OUT = os.path.join(MIRROR_DIR, "m.json")
STATE = os.path.join(MIRROR_DIR, "snapshot_state.json")
REPORT = os.path.join(MIRROR_DIR, "snapshot_report.md")

CST = timezone(timedelta(hours=8))


def now_str():
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S %z")


def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else default
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print("WARN: 读取 %s 失败（%s），按默认处理" % (path, e))
        return default


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def write_json(path, obj):
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def fetch(url, timeout):
    """返回 (ok, text, status, err, elapsed_ms, byte_len)。"""
    t0 = time.monotonic()
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; TVBox-Mirror/1.0)", "Accept": "*/*"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
            raw = resp.read(16 * 1024 * 1024)
            elapsed = int((time.monotonic() - t0) * 1000)
            return (200 <= status < 300), raw.decode("utf-8", errors="replace"), status, "", elapsed, len(raw)
    except urllib.error.HTTPError as e:
        return False, "", e.code, "HTTPError %s" % e.code, int((time.monotonic() - t0) * 1000), 0
    except Exception as e:
        return False, "", 0, "%s: %s" % (type(e).__name__, e), int((time.monotonic() - t0) * 1000), 0


def strip_json_comments(text):
    """去掉 jsonc 注释：整行 // 注释 + /* */ 块注释，保留 URL 里的 //。"""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out = []
    for line in text.splitlines():
        if line.lstrip().startswith("//"):
            continue
        out.append(line)
    return "\n".join(out)


def count_valid_sites(text):
    """解析 m.json，返回 (是否有效, 有效站点数, 原始站点总数, 错误说明)。"""
    try:
        data = json.loads(strip_json_comments(text))
    except (json.JSONDecodeError, ValueError) as e:
        return False, 0, 0, "JSON 解析失败: %s" % e
    sites = data.get("sites")
    if not isinstance(sites, list):
        return False, 0, 0, "sites 字段缺失或非数组"
    valid = [s for s in sites if isinstance(s, dict) and s.get("api")]
    return True, len(valid), len(sites), ""


def render_report(state, attempts):
    lines = [
        "# tvbox-mirror 快照运行报告",
        "",
        "- 运行时间：%s" % now_str(),
        "- 本轮动作：**%s**" % state.get("last_action", "-"),
        "- 当前快照有效站点数：%s" % state.get("site_count", "-"),
        "- 快照更新时间：%s" % state.get("last_success", "-"),
        "- 连续抓取失败：%s" % state.get("consecutive_failures", 0),
        "",
        "## 上游探测明细",
        "",
        "| 上游 | HTTP | 延迟ms | 字节 | 有效站点 | 结果 | 说明 |",
        "|---|---|---|---|---|---|---|",
    ]
    for a in attempts:
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            a.get("name", a.get("url", "-")), a.get("status", "-"),
            a.get("latency_ms", "-"), a.get("bytes", "-"), a.get("sites", "-"),
            "OK" if a.get("ok") else "FAIL", a.get("note", ""),
        ))
    lines += [
        "",
        "## 机制说明",
        "",
        "- 多上游按顺序 failover，任一拉到合格 m.json 即停止。",
        "- 合格判据：JSON 合法 + sites 数组 + 有效站点数 >= min_sites，且不低于上次基线的一半（防上游被改空壳）。",
        "- 不合格时保留 mirror/m.json 上一版（last good），绝不写坏；同步写本报告与告警状态。",
        "",
    ]
    if state.get("needs_attention"):
        lines.insert(0, "> ## 持续失效告警：连续 %d 轮未拿到合格快照，mirror/m.json 保持上一版\n" % state.get("consecutive_failures", 0))
    return "\n".join(lines)


def main():
    conf = load_json(CONF, {})
    if not conf:
        print("ERROR: 缺少或无法读取 snapshot_config.json")
        sys.exit(1)

    upstreams = conf.get("upstreams", [])
    timeout = conf.get("timeout_seconds", 12)
    min_sites = int(conf.get("min_sites", 10))
    fail_alert = int(conf.get("failures_before_alert", 3))

    state = load_json(STATE, {})
    baseline = int(state.get("site_count", 0) or 0)
    os.makedirs(MIRROR_DIR, exist_ok=True)

    print("[1/4] 按优先级抓取上游 m.json（共 %d 个入口）..." % len(upstreams))
    attempts = []
    picked = None
    picked_text = ""
    picked_sites = 0
    for u in upstreams:
        name = u.get("name", u.get("url", "-"))
        to = u.get("timeout_seconds", timeout)
        ok, text, status, err, elapsed, nbytes = fetch(u["url"], to)
        attempt = {"name": name, "url": u["url"], "status": status,
                   "latency_ms": elapsed, "bytes": nbytes, "sites": 0,
                   "ok": False, "note": ""}
        if not ok:
            attempt["note"] = err or ("HTTP %s" % status)
            attempts.append(attempt)
            print("      [FAIL] %-24s %s" % (name, attempt["note"]))
            continue
        parsed, valid_sites, raw_sites, perr = count_valid_sites(text)
        attempt["sites"] = valid_sites
        if not parsed:
            attempt["note"] = perr
            attempts.append(attempt)
            print("      [FAIL] %-24s %s" % (name, perr))
            continue
        floor = max(min_sites, int(baseline * 0.5)) if baseline else min_sites
        if valid_sites < floor:
            attempt["note"] = "有效站点 %d < 阈值 %d（基线 %d，原始 %d）" % (valid_sites, floor, baseline, raw_sites)
            attempts.append(attempt)
            print("      [FAIL] %-24s %s" % (name, attempt["note"]))
            continue
        attempt["ok"] = True
        attempt["note"] = "合格，有效站点 %d/%d" % (valid_sites, raw_sites)
        attempts.append(attempt)
        picked, picked_text, picked_sites = u, text, valid_sites
        print("      [ OK ] %-24s %s" % (name, attempt["note"]))
        break

    print("[2/4] 判定动作 ...")
    if picked:
        # 合格快照：原子覆盖 mirror/m.json，同时留一份 lastgood 双保险
        clean = json.loads(strip_json_comments(picked_text))
        write_json(OUT, clean)                 # 去掉注释后重新序列化，保证 TVBox 能直接解析
        write_text(OUT + ".lastgood", picked_text)  # 原文留底，便于比对
        state["site_count"] = picked_sites
        state["last_success"] = now_str()
        state["consecutive_failures"] = 0
        state["needs_attention"] = False
        state["last_source"] = picked.get("name", picked.get("url", "-"))
        state["last_action"] = "更新快照：%s（有效站点 %d）" % (state["last_source"], picked_sites)
    else:
        # 全部不合格：保留 last good，绝不覆盖
        cnt = int(state.get("consecutive_failures", 0)) + 1
        state["consecutive_failures"] = cnt
        state["last_fail"] = now_str()
        existed = os.path.exists(OUT)
        if existed:
            state["last_action"] = "失效保护：保留上一版 mirror/m.json（本轮无合格上游）"
        else:
            state["last_action"] = "首次运行且无合格上游：尚未生成 mirror/m.json"
        if cnt >= fail_alert:
            state["needs_attention"] = True
            state["last_action"] += "；连续失败达 %d 轮，需检查上游" % cnt
        print("      WARN: %s" % state["last_action"])

    state["last_run"] = now_str()
    print("[3/4] 写入状态与报告 ...")
    write_json(STATE, state)
    write_text(REPORT, render_report(state, attempts))
    print("[4/4] 完成：%s" % state["last_action"])
    if state.get("needs_attention"):
        print("      !! 连续 %d 轮失败，已在报告中升级告警" % state["consecutive_failures"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
