#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_clean_v3.py — 网络优化版配置

基于 clean-m-v2.json（210 站，已剔除坏站），按 net_benchmark.json 的实测延迟
重排 sites 顺序：快的直连站优先，慢的靠后，不可测的 Java 爬虫站保持原序在后。
目的：App 搜索/切源列表优先展示响应快的站，提升实际播放流畅度。

不增删任何站点（纯重排），保留 v2 的健康过滤成果。
"""
import json
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "mirror", "clean-m-v2.json")
BENCH = os.path.join(BASE, "net_benchmark.json")
OUT = os.path.join(BASE, "mirror", "clean-m-v3.json")


def main():
    m = json.load(open(SRC, encoding="utf-8"))
    bench = json.load(open(BENCH, encoding="utf-8"))

    # key -> latency
    lat_map = {}
    for r in bench["sites"]:
        if r["ok"] and r["latency_ms"] is not None:
            lat_map[r["key"]] = r["latency_ms"]

    sites = m["sites"]
    total = len(sites)

    # 分两组：可测速直连站(按延迟升序) / 其余(保持原相对顺序)
    measured = []
    unmeasured = []
    for idx, s in enumerate(sites):
        key = s.get("key")
        if key in lat_map:
            measured.append((lat_map[key], idx, s))
        else:
            unmeasured.append((idx, s))

    measured.sort(key=lambda x: (x[0], x[1]))
    new_sites = [s for _, _, s in measured] + [s for _, s in unmeasured]

    m["sites"] = new_sites
    json.dump(m, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    print(f"v3 生成: {total} 站（{len(measured)} 个直连站按网速重排 + {len(unmeasured)} 个其余站保持原序）")
    print("\n=== 重排后前 12 站（最快优先）===")
    for s in new_sites[:12]:
        lat = lat_map.get(s.get("key"))
        print(f"  {lat if lat else '  --':>5}ms  {s.get('name')[:22]:24} {s.get('key')}")


if __name__ == "__main__":
    main()
