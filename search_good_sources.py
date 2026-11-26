#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检索到的候选播放源批量实测：HTTP 可达性 + 大小 + 内容格式 + 站点/频道数。
用 curl --max-time 硬超时（urllib 的 timeout 管不到 DNS 解析）。"""
import subprocess, concurrent.futures, json, re, time, os

OUT = os.path.dirname(os.path.abspath(__file__))

# (id, 类别, url)
CANDIDATES = [
    # ===== 点播-聚合仓(Lightconer 每日更新) =====
    ("lc-单仓聚合-jsdelivr", "vod", "https://fastly.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/单仓聚合.json"),
    ("lc-多仓订阅-jsdelivr", "vod", "https://fastly.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/多仓订阅.json"),
    ("lc-laoliubei-jsdelivr", "vod", "https://fastly.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/laoliubei.json"),
    ("lc-feimao-jsdelivr", "vod", "https://fastly.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/feimao.json"),
    ("lc-xiaoma-jsdelivr", "vod", "https://fastly.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/xiaoma.json"),
    ("lc-4k-jsdelivr", "vod", "https://fastly.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/4k.json"),
    ("lc-单仓-pages", "vod", "https://lightconer.github.io/tvbox-ysc-config/output/单仓聚合.json"),
    ("lc-单仓-raw", "vod", "https://raw.githubusercontent.com/Lightconer/tvbox-ysc-config/main/output/单仓聚合.json"),
    # ===== 点播-直连站(来自 laoma528/Lightconer 清单) =====
    ("liucn-raw", "vod", "https://raw.liucn.cc/box/m.json"),
    ("xhztv-4k", "vod", "http://xhztv.top/4k.json"),
    ("szyyds-x", "vod", "https://szyyds.cn/tv/x.json"),
    ("facat-kstore", "vod", "https://6296.kstore.vip/facat.json"),
    ("wex-kstore", "vod", "https://d.kstore.dev/download/9280/wex.json"),
    ("fantaiying-jsdelivr", "vod", "https://fastly.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/fantaiying.json"),
    ("4k-xhztv", "vod", "http://xhztv.top/4k.json"),
    # ===== 点播-基准对照(已验证可用) =====
    ("BASE-clean-selfhost", "vod", "https://byshino.github.io/tvbox-mirror/clean-selfhost.json"),
    ("BASE-liu-ghpages", "vod", "https://liu673cn.github.io/box/m.json"),
    # ===== 直播 =====
    ("zbds-iptv4-m3u", "live", "https://live.zbds.top/tv/iptv4.m3u"),
    ("zbds-iptv4-txt", "live", "https://live.zbds.top/tv/iptv4.txt"),
    ("zbds-iptv6-m3u", "live", "https://live.zbds.top/tv/iptv6.m3u"),
    ("vbskycn-raw-m3u", "live", "https://raw.githubusercontent.com/vbskycn/iptv/master/iptv4.m3u"),
    ("fanming-index-jsdelivr", "live", "https://fastly.jsdelivr.net/gh/fanmingming/live@main/tv/m3u/index.m3u"),
    ("jiandantv-lite-jsdelivr", "live", "https://fastly.jsdelivr.net/gh/jiandantv/IPTV2026@main/live_lite.m3u"),
    ("iptv-org-m3u", "live", "https://iptv-org.github.io/iptv/index.m3u"),
    ("BASE-live-good", "live", "https://byshino.github.io/tvbox-mirror/live-good.m3u"),
]

curl = r"C:\Windows\System32\curl.exe"

def fetch(item):
    sid, cat, url = item
    t0 = time.time()
    try:
        p = subprocess.run(
            [curl, "-sS", "-L", "--max-time", "12", "-A", "Mozilla/5.0",
             "-o", "-", "-w", "\n__HTTP__%{http_code}__SIZE__%{size_download}__URL__%{url_effective}",
             url],
            capture_output=True, timeout=16,
        )
        raw = p.stdout
        # 分离 body 和 meta
        marker = b"__HTTP__"
        idx = raw.rfind(marker)
        if idx < 0:
            return dict(id=sid, cat=cat, url=url, ok=False, err="无HTTP标记", ms=int((time.time()-t0)*1000))
        body = raw[:idx]
        meta = raw[idx+len(marker):].decode("utf-8", "replace")
        m = re.search(r"__HTTP__(\d+)__SIZE__(\d+)__URL__(.*)", "__HTTP__"+meta)
        code = int(m.group(1)) if m else 0
        eff = m.group(3).strip() if m else url
        ms = int((time.time()-t0)*1000)
        ok = 200 <= code < 400 and len(body) > 200
        result = dict(id=sid, cat=cat, url=url, eff=eff, code=code, size=len(body), ok=ok, ms=ms)
        # 内容分析
        try:
            txt = body.decode("utf-8", "replace")
        except Exception:
            txt = ""
        if cat == "vod":
            # 去 jsonc 注释
            clean = re.sub(r"^\s*//.*$", "", txt, flags=re.M)
            try:
                j = json.loads(clean)
                sites = j.get("site", []) if isinstance(j, dict) else []
                result["sites"] = len(sites)
                result["has_spider"] = bool(j.get("spider")) if isinstance(j, dict) else False
                result["fmt"] = "json-ok"
            except Exception as e:
                result["fmt"] = "json-parse-fail"
                result["head"] = txt[:80].replace("\n", " ")
        else:
            lines = [l for l in txt.splitlines() if "#EXTINF" in l]
            urls = [l for l in txt.splitlines() if l.strip().startswith(("http://", "https://"))]
            result["channels"] = len(lines)
            result["lines"] = len(urls)
            result["fmt"] = "m3u" if "#EXTM3U" in txt else ("txt" if urls else "unknown")
        return result
    except subprocess.TimeoutExpired:
        return dict(id=sid, cat=cat, url=url, ok=False, err="超时", ms=int((time.time()-t0)*1000))
    except Exception as e:
        return dict(id=sid, cat=cat, url=url, ok=False, err=str(e)[:60], ms=int((time.time()-t0)*1000))

with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    results = list(ex.map(fetch, CANDIDATES))

results.sort(key=lambda r: (r.get("cat", ""), not r.get("ok", False), r.get("ms", 99999)))
with open(os.path.join(OUT, "good_sources_probe.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

for cat in ("vod", "live"):
    print(f"\n{'='*70}\n{'点播源' if cat=='vod' else '直播源'} 实测结果\n{'='*70}")
    for r in [x for x in results if x.get("cat") == cat]:
        flag = "OK " if r.get("ok") else "BAD"
        extra = ""
        if cat == "vod":
            extra = f"sites={r.get('sites','?')} spider={'Y' if r.get('has_spider') else 'N'} fmt={r.get('fmt','?')}"
        else:
            extra = f"频道={r.get('channels','?')} 线路={r.get('lines','?')} fmt={r.get('fmt','?')}"
        print(f"[{flag}] {r['id']:<26} {r.get('ms','?'):>6}ms  {r.get('size','?'):>8}B  {extra}")
        if r.get("err"):
            print(f"        err={r['err']}")
        if r.get("code") and not (200 <= r["code"] < 400):
            print(f"        HTTP={r['code']}  eff={r.get('eff','')[:80]}")
print(f"\n明细已存 good_sources_probe.json")
