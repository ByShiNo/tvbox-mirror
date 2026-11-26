#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 GitHub API 下载推荐的 TVBox 系 APK 到桌面（gh api asset endpoint 带 token）。"""
import subprocess, urllib.request, os, hashlib, time

DESKTOP = r"C:\Users\Administrator\Desktop"
token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()

APPS = [
    # (显示名, 本地文件名, api asset url)
    ("WebHomeTV 精简电视版 v5.17.4 (局域网网页管理)",
     "WebHomeTV_leanback-lite-arm64_v8a_5.17.4.apk",
     "https://api.github.com/repos/motao123/webtv/releases/assets/774834996"),
    ("海因影视 TV版 1.4.1 (海报墙+自动测速)",
     "HeinPlay_tv_1.4.1.apk",
     "https://api.github.com/repos/hein1225/HeinPlay/releases/assets/690951069"),
]

for label, fname, url in APPS:
    out = os.path.join(DESKTOP, fname)
    print(f"\n下载: {label}")
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/octet-stream",
        "User-Agent": "v",
    })
    t0 = time.time()
    try:
        data = urllib.request.urlopen(req, timeout=180).read()
        with open(out, "wb") as f:
            f.write(data)
        sha = hashlib.sha256(data).hexdigest().upper()
        print(f"  完成: {len(data)}B  {int(time.time()-t0)}s")
        print(f"  路径: {out}")
        print(f"  SHA256: {sha}")
    except Exception as e:
        print(f"  失败: {str(e)[:120]}")
