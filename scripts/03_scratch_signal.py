#!/usr/bin/env python3
"""Stage 3 input — Scratch as an audience-matched demand probe.

For each archetype's `scratch_q`, ask Scratch's public search (mode=popular) for the top 40 projects
and record their view counts. Scratch's users are roughly Roblox's age band, and they only remake what
they already love playing, so "views on kid-made clones of mechanic X" is a like-for-like signal that
needs no cross-site normalisation. Caveat: branded queries measure the brand as well as the mechanic.

-> data/scratch_signal.csv
"""
import csv, json, os, ssl, time, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem") if os.path.exists("/etc/ssl/cert.pem") \
    else ssl.create_default_context()


def get(url):
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa
            time.sleep(2)
    return []


def main():
    arch = json.load(open(os.path.join(ROOT, "data", "archetypes.json"), encoding="utf-8"))
    rows = []
    for a in arch:
        for q in a["scratch_q"]:
            res = get("https://api.scratch.mit.edu/search/projects?limit=40&offset=0&mode=popular&q=" +
                      urllib.parse.quote(q))
            views = sorted([p["stats"]["views"] for p in res], reverse=True)
            loves = sum(p["stats"]["loves"] for p in res)
            rows.append(dict(archetype=a["id"], query=q, n=len(views), sum_views=sum(views),
                             top1_views=views[0] if views else 0,
                             median_views=views[len(views) // 2] if views else 0, sum_loves=loves,
                             top_title=(max(res, key=lambda p: p["stats"]["views"])["title"] if res else "")))
            print(f"{a['id']:26s} {q:28s} n={len(views):2d} views={sum(views):>11,}")
            time.sleep(0.5)
    path = os.path.join(ROOT, "data", "scratch_signal.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "rows ->", path)


if __name__ == "__main__":
    main()
