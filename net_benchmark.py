#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
net_benchmark.py — TVBox 播放源网络优化检测

两个层面：
  A) 候选配置源层面：对 candidates.json 里的每个源做多轮测速
     (DNS/TCP/TLS 握手 + 下载速率 + 稳定性)，给出综合排名。
  B) 配置内站点层面：对 clean-m-v2.json 里每个 HTTP API 采集站测速，
     按响应速度排名，供重排站点优先级 / 生成优化版配置。

输出 JSON + Markdown 报告，纯标准库。
"""
import json
import os
import ssl
import sys
import time
import socket
import urllib.request
import urllib.error
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
CAND = os.path.join(ROOT, "tvbox-selfheal", "candidates.json")
CLEAN = os.path.join(BASE, "mirror", "clean-m-v2.json")
OUT_JSON = os.path.join(BASE, "net_benchmark.json")
OUT_MD = os.path.join(BASE, "NET_BENCHMARK.md")

UA = "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"
ROUNDS = 3
TIMEOUT = 10
WORKERS = 16
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def measure(url, download=True):
    """返回 (latency_ms, speed_kbps, size, err)"""
    latencies, speeds, sizes = [], [], []
    err = None
    for _ in range(ROUNDS):
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
                ttfb = (time.perf_counter() - t0) * 1000
                data = r.read() if download else b""
            total = (time.perf_counter() - t0) * 1000
            latencies.append(ttfb)
            sizes.append(len(data))
            if total > ttfb and len(data) > 0:
                speeds.append(len(data) * 8 / 1024 / ((total - ttfb) / 1000))
        except Exception as e:
            err = str(e)[:70]
            time.sleep(0.3)
    if not latencies:
        return (None, None, 0, err or "all failed")
    return (round(sum(latencies) / len(latencies)),
            round(sum(speeds) / len(speeds)) if speeds else 0,
            max(sizes), None)


def score(lat, speed, ok):
    """综合分：延迟越低越好(占60%)，速率越高越好(占40%)"""
    if not ok or lat is None:
        return 0
    lat_score = max(0, 100 - lat / 20)          # 2000ms->0, 0ms->100
    spd_score = min(100, (speed or 0) / 50)      # 5000KB/s->100
    return round(lat_score * 0.6 + spd_score * 0.4)


def bench_candidates():
    cand = json.load(open(CAND, encoding="utf-8"))
    urls = []
    for grp, arr in cand["groups"].items():
        for s in arr:
            if s.get("enabled", True):
                urls.append((grp, s["id"], s["url"]))
    print(f"[A] 候选源 {len(urls)} 个, 每源 {ROUNDS} 轮...")
    res = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(measure, u): (g, i, u) for g, i, u in urls}
        for f in as_completed(futs):
            g, i, u = futs[f]
            lat, spd, size, err = f.result()
            res.append({"group": g, "id": i, "url": u, "latency_ms": lat,
                        "speed_kbps": spd, "size": size, "err": err,
                        "score": score(lat, spd, err is None)})
    res.sort(key=lambda r: (-r["score"], r["latency_ms"] or 99999))
    return res


def bench_sites():
    m = json.load(open(CLEAN, encoding="utf-8"))
    sites = [s for s in m["sites"] if str(s.get("api", "")).startswith("http")]
    print(f"[B] HTTP采集站 {len(sites)} 个, 每站 {ROUNDS} 轮...")
    res = []
    def work(s):
        lat, spd, size, err = measure(s["api"], download=False)
        return {"key": s.get("key"), "name": s.get("name"), "api": s["api"],
                "latency_ms": lat, "ok": err is None, "err": err}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for r in ex.map(work, sites):
            res.append(r)
    res.sort(key=lambda r: (r["latency_ms"] is None, r["latency_ms"] or 99999))
    return res


def main():
    a = bench_candidates()
    b = bench_sites()
    json.dump({"generated": time.strftime("%Y-%m-%d %H:%M:%S %z"),
               "candidates": a, "sites": b},
              open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    lines = ["# TVBox 播放源网络优化检测报告", "",
             f"- 生成：{time.strftime('%Y-%m-%d %H:%M:%S %z')}",
             f"- 每源/站测 {ROUNDS} 轮取均值，延迟=首字节时间", "",
             "## A. 候选配置源网络排名（延迟60% + 速率40%）", "",
             "| 排名 | 源 | 组 | 延迟ms | 速率KB/s | 大小B | 综合分 | 错误 |",
             "|---|---|---|---|---|---|---|---|"]
    for n, r in enumerate(a, 1):
        lines.append(f"| {n} | {r['id']} | {r['group']} | {r['latency_ms']} | {r['speed_kbps']} | {r['size']} | **{r['score']}** | {r['err'] or '-'} |")
    ok_c = [r for r in a if r["err"] is None]
    lines += ["", "## B. 配置内 HTTP 采集站响应排名（前30）", "",
              "| 排名 | 站点 | 延迟ms | 状态 |", "|---|---|---|---|"]
    for n, r in enumerate(b[:30], 1):
        lines.append(f"| {n} | {r['name']} | {r['latency_ms']} | {'OK' if r['ok'] else r['err']} |")
    fast = [r for r in b if r["ok"]]
    slow = [r for r in b if not r["ok"]]
    lines += ["", "## 结论", "",
              f"- 候选源健康 {len(ok_c)}/{len(a)}，最快：**{a[0]['id'] if a else 'N/A'}**（{a[0]['latency_ms'] if a else '-'}ms，{a[0]['url'] if a else '-'}）",
              f"- HTTP采集站可达 {len(fast)}/{len(b)}，最慢 {len(slow)} 个见 probe_sites 报告。", ""]
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(lines))

    print("\n=== 候选源排名 ===")
    for n, r in enumerate(a, 1):
        print(f"  {n}. {r['id']:20} {r['latency_ms']}ms {r['speed_kbps']}KB/s score={r['score']}")
    print(f"\n报告 → {OUT_MD}")


if __name__ == "__main__":
    main()
