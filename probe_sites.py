#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_sites.py — TVBox 清洗版多片源实时监测 + 待改进项清单

对 clean-m.json 的每个站点做两件事：
  1) Java 爬虫类站点(csp_XXX)：解包对应 jar(站点 jar + 顶层 fty.jar)，
     用 dex 二进制字符串扫描确认 com.github.catvod.spider.XXX 类是否真实存在。
  2) 直连 API / JS URL 站点：发 HTTP GET 探测可达性与响应时间。

输出：
  probe_report.json   机器可读完整结果
  PROBE_REPORT.md     人可读报告 + 待改进项清单(可直接生成 clean-m v2)

纯标准库，可反复跑，作为"实时监测"的落地工具。
"""
import json
import os
import re
import ssl
import sys
import time
import zipfile
import hashlib
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = os.path.dirname(os.path.abspath(__file__))
MIRROR_JSON = os.path.join(BASE, "mirror", "clean-m.json")
CACHE_DIR = os.path.join(BASE, ".jar_cache")
REPORT_JSON = os.path.join(BASE, "probe_report.json")
REPORT_MD = os.path.join(BASE, "PROBE_REPORT.md")

TIMEOUT = 12
WORKERS = 16
UA = "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"
# dex 里类描述符是 ASCII: Lcom/github/catvod/spider/Juqq;
CLASS_RE = re.compile(rb"Lcom/github/catvod/spider/([A-Za-z0-9_$]+);")

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def ensure_cache():
    os.makedirs(CACHE_DIR, exist_ok=True)


def fetch_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CTX) as r:
        return r.read()


def get_jar(url):
    """下载 jar 到缓存，返回本地路径。url 可能带 ;md5;... 后缀。"""
    clean = url.split(";")[0]
    key = hashlib.md5(clean.encode()).hexdigest() + ".jar"
    path = os.path.join(CACHE_DIR, key)
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return path
    data = fetch_bytes(clean)
    with open(path, "wb") as f:
        f.write(data)
    return path


def classes_in_jar(path):
    """从 jar 的所有 dex 里扫出 spider 类名集合。"""
    names = set()
    try:
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.endswith(".dex"):
                    raw = z.read(n)
                    for m in CLASS_RE.finditer(raw):
                        names.add(m.group(1).decode("ascii", "replace"))
    except Exception:
        return names
    return names


def api_kind(api):
    """返回 ('java', 类名) / ('python', None) / ('http', None) / ('other', None)"""
    api = (api or "").strip()
    if not api:
        return ("empty", None)
    if api.lower().startswith("http://") or api.lower().startswith("https://"):
        return ("http", None)
    if api.lower().startswith("py_"):
        # drpy/py 脚本爬虫：类不在 jar 里，实际读 ext 指向的 .py 文件
        return ("python", None)
    if api.lower().startswith("csp_"):
        return ("java", api[4:])
    # 直接类名(无 csp_ 前缀)也算 java，但少见
    if re.fullmatch(r"[A-Za-z0-9_]+", api):
        return ("java", api)
    return ("other", None)


def main():
    ensure_cache()
    m = json.load(open(MIRROR_JSON, encoding="utf-8"))
    sites = m["sites"]
    top_spider = m.get("spider", "")

    # 顶层 jar 类集合(所有 java 站点的公共后备)
    top_classes = set()
    if top_spider:
        try:
            top_classes = classes_in_jar(get_jar(top_spider))
            print(f"[顶层 spider] {len(top_classes)} 个 spider 类: {top_spider.split(';')[0]}")
        except Exception as e:
            print(f"[顶层 spider] 加载失败: {e}")

    # 关键：App 把所有 jar 全局加载，类可能在任意站点 jar 里。
    # 因此先合并「顶层 jar + 所有站点专属 jar」的类集合。
    all_jar_urls = set()
    if top_spider:
        all_jar_urls.add(top_spider)
    for s in sites:
        if s.get("jar"):
            all_jar_urls.add(s["jar"])
    all_classes = set()
    for u in all_jar_urls:
        try:
            all_classes |= classes_in_jar(get_jar(u))
        except Exception:
            pass
    print(f"[全局类库] {len(all_jar_urls)} 个 jar, 合并 {len(all_classes)} 个 spider 类")

    def probe_one(s):
        name = s.get("name", "?")
        key = s.get("key", "?")
        api = s.get("api", "")
        kind, cls = api_kind(api)
        rec = {"key": key, "name": name, "api": api, "kind": kind}

        if kind == "java":
            ok = cls in all_classes
            rec["class"] = cls
            rec["status"] = "OK" if ok else "MISSING_CLASS"
            rec["detail"] = "类存在(全局jar)" if ok else f"类 {cls} 不在任何 jar 中"
        elif kind == "python":
            # py_ 脚本爬虫：校验 ext 指向的 .py 文件是否可达
            ext = s.get("ext", "")
            if isinstance(ext, str) and ext.startswith("http"):
                try:
                    data = fetch_bytes(ext.split("+")[0].split("$$$")[0])
                    rec["status"] = "OK"
                    rec["detail"] = f"PY脚本可达 {len(data)}B"
                except Exception as e:
                    rec["status"] = "SCRIPT_ERR"
                    rec["detail"] = str(e)[:60]
            else:
                rec["status"] = "OK"
                rec["detail"] = "PY脚本(相对路径,依赖本地libs)"
        elif kind == "http":
            t0 = time.time()
            try:
                data = fetch_bytes(api)
                ms = int((time.time() - t0) * 1000)
                rec["status"] = "OK"
                rec["ms"] = ms
                rec["detail"] = f"HTTP 200 {len(data)}B {ms}ms"
            except urllib.error.HTTPError as e:
                rec["status"] = "HTTP_ERR"
                rec["detail"] = f"HTTP {e.code}"
            except Exception as e:
                rec["status"] = "NET_ERR"
                rec["detail"] = str(e)[:80]
        elif kind == "empty":
            rec["status"] = "EMPTY_API"
            rec["detail"] = "api 为空"
        else:
            rec["status"] = "OTHER"
            rec["detail"] = "非标准 api 格式"

        return rec

    print(f"[探测] {len(sites)} 个站点, {WORKERS} 并发, 超时 {TIMEOUT}s ...")
    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(probe_one, s): s for s in sites}
        done = 0
        for f in as_completed(futs):
            results.append(f.result())
            done += 1
            if done % 40 == 0:
                print(f"  进度 {done}/{len(sites)}")

    order = {"OK": 0, "MISSING_CLASS": 1, "SCRIPT_ERR": 2, "HTTP_ERR": 3, "NET_ERR": 4, "EMPTY_API": 5, "OTHER": 6}
    results.sort(key=lambda r: (order.get(r["status"], 9), r["name"]))

    from collections import Counter
    cnt = Counter(r["status"] for r in results)
    bad = [r for r in results if r["status"] != "OK"]

    json.dump(
        {"generated": time.strftime("%Y-%m-%d %H:%M:%S %z"), "total": len(sites),
         "counts": dict(cnt), "top_spider": top_spider, "results": results},
        open(REPORT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2,
    )

    lines = ["# TVBox 多片源实时监测报告", "",
             f"- 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S %z')}",
             f"- 站点总数：{len(sites)}",
             f"- 顶层 spider：{top_spider.split(';')[0]}", "",
             "## 状态统计", ""]
    for k, v in cnt.most_common():
        lines.append(f"- **{k}**: {v}")
    lines += ["", "## 待改进项（非 OK 站点）", ""]
    lines.append("| 站点 | key | 类型 | 问题 |")
    lines.append("|---|---|---|---|")
    for r in bad:
        lines.append(f"| {r['name']} | {r['key']} | {r['kind']} | {r['status']}: {r['detail']} |")
    lines += ["", "## 说明", "",
              "- `MISSING_CLASS`：Java 爬虫类缺失，切换过去必报『爬虫加载失败』→ 建议从配置剔除。",
              "- `SCRIPT_ERR`：PY 脚本爬虫的脚本文件不可达 → 建议剔除。",
              "- `HTTP_ERR`/`NET_ERR`：直连采集站当前不可达，可能是临时故障 → 可保留观察或剔除。",
              "- `OK`：类存在(全局jar)/PY脚本可达/HTTP 200，可正常加载。", ""]
    open(REPORT_MD, "w", encoding="utf-8").write("\n".join(lines))

    print("\n=== 状态统计 ===")
    for k, v in cnt.most_common():
        print(f"  {k}: {v}")
    print(f"\n待改进项 {len(bad)} 个 → {REPORT_MD}")
    print(f"完整结果 → {REPORT_JSON}")


if __name__ == "__main__":
    main()
