#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从每个候选点播源抽取 type=3 直连API站点，真实请求验证能否返回影片。"""
import subprocess, json, re, concurrent.futures, time, os

OUT = os.path.dirname(os.path.abspath(__file__))
curl = r"C:\Windows\System32\curl.exe"

SOURCES = {
    "单仓聚合(549)": "https://fastly.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/单仓聚合.json",
    "laoliubei(234)": "https://fastly.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/laoliubei.json",
    "xiaoma(62)": "https://fastly.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/xiaoma.json",
    "facat(40)": "https://6296.kstore.vip/facat.json",
    "4k(53)": "https://fastly.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/4k.json",
    "clean-selfhost(200)": "https://byshino.github.io/tvbox-mirror/clean-selfhost.json",
}

def get_json(url):
    b = subprocess.run([curl, "-sS", "-L", "--max-time", "12", "-A", "Mozilla/5.0", url],
                       capture_output=True, timeout=16).stdout
    t = re.sub(r"^\s*//.*$", "", b.decode("utf-8", "replace"), flags=re.M)
    return json.loads(t)

def probe_api(item):
    src, site = item
    api = site.get("api", "")
    if not api.startswith("http"):
        return dict(src=src, name=site.get("name", "?"), api=api[:60], ok=False, err="非http")
    # 构造采集站列表请求
    sep = "&" if "?" in api else "?"
    test_url = api.rstrip("/") + sep + "ac=list"
    t0 = time.time()
    try:
        p = subprocess.run([curl, "-sS", "-L", "--max-time", "8", "-A", "Mozilla/5.0",
                            "-w", "\n__C__%{http_code}", test_url],
                           capture_output=True, timeout=11)
        raw = p.stdout
        idx = raw.rfind(b"__C__")
        code = int(raw[idx+5:].strip()) if idx >= 0 else 0
        body = raw[:idx] if idx >= 0 else raw
        ms = int((time.time()-t0)*1000)
        txt = body.decode("utf-8", "replace")
        n = 0
        try:
            j = json.loads(txt)
            if isinstance(j, dict):
                lst = j.get("list") or j.get("data") or j.get("rows") or []
                n = len(lst) if isinstance(lst, list) else 0
                total = j.get("total", "")
            else:
                n = len(j) if isinstance(j, list) else 0
                total = ""
        except Exception:
            total = ""
        return dict(src=src, name=site.get("name", "?"), api=api[:60],
                    ok=(code == 200 and n > 0), code=code, n=n, ms=ms, total=total)
    except subprocess.TimeoutExpired:
        return dict(src=src, name=site.get("name", "?"), api=api[:60], ok=False, err="超时", ms=8000)
    except Exception as e:
        return dict(src=src, name=site.get("name", "?"), api=api[:60], ok=False, err=str(e)[:40])

tasks = []
src_meta = {}
for src, url in SOURCES.items():
    try:
        j = get_json(url)
        sites = [s for s in j.get("sites", []) if str(s.get("type")) == "3" and s.get("api", "").startswith("http")]
        # 每源抽前25个 type=3
        pick = sites[:25]
        src_meta[src] = dict(total_sites=len(j.get("sites", [])), type3=len(sites), sampled=len(pick))
        for s in pick:
            tasks.append((src, s))
    except Exception as e:
        src_meta[src] = dict(err=str(e)[:50])

with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
    results = list(ex.map(probe_api, tasks))

# 按源汇总
print("=" * 78)
print("各源 type=3 直连API站点真实出片率抽样（每源最多25站）")
print("=" * 78)
summary = {}
for src in SOURCES:
    rs = [r for r in results if r.get("src") == src]
    ok = [r for r in rs if r.get("ok")]
    meta = src_meta.get(src, {})
    rate = f"{len(ok)}/{len(rs)}" if rs else "-"
    print(f"\n【{src}】总站={meta.get('total_sites','?')} type3={meta.get('type3','?')} 抽样={rate}")
    print(f"  实测出片 {len(ok)} 个，样例:")
    for r in ok[:5]:
        print(f"    ✓ {r['name'][:22]:<24} {r['ms']:>5}ms  list={r.get('n')}条  {r['api'][:45]}")
    bad = [r for r in rs if not r.get("ok")]
    if bad:
        print(f"  失败样例({len(bad)}):")
        for r in bad[:3]:
            print(f"    ✗ {r['name'][:22]:<24} HTTP={r.get('code','?')} {r.get('err','')} {r['api'][:40]}")
    summary[src] = dict(meta, sampled_ok=len(ok), sampled_total=len(rs))

with open(os.path.join(OUT, "sample_api_result.json"), "w", encoding="utf-8") as f:
    json.dump(dict(summary=summary, details=results), f, ensure_ascii=False, indent=2)
print("\n明细已存 sample_api_result.json")
