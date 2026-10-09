#!/usr/bin/env python3
"""Stages 1-3 — de-duplicate, classify, and standardise web demand.

Inputs : data/web_games_raw.csv, data/archetypes.json, data/scratch_signal.csv
Outputs: data/games.csv              one row per de-duplicated game franchise (the candidate database)
         data/archetype_demand.csv   one row per mechanic archetype with standardised demand evidence

Standardisation (answers "a #10 monthly rank on 4399 vs 1M plays on CrazyGames"):
  never compare raw numbers across sites. Inside each site convert every game to its SHARE of that site's
  measured attention (plays or votes where published; Zipf 1/rank where only an ordinal rank exists).
  A share is unit-free, so shares can be compared and averaged across sites. Missing = not in that site's
  top list (share 0 on that list), which is itself information; sites we could not read are simply absent
  from the average rather than imputed.
"""
import csv, json, os, re, collections, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, "data", *p)
ZIPF_S = float(os.environ.get("ZIPF_S", "1.0"))

ARCH = json.load(open(D("archetypes.json"), encoding="utf-8"))
ARCH_BY = {a["id"]: a for a in ARCH}
OVERRIDES = json.load(open(D("archetype_overrides.json"), encoding="utf-8")) \
    if os.path.exists(D("archetype_overrides.json")) else {}

# (platform, listing-predicate, metric, signal name, kind, weight)
#   kind 'alltime' = cumulative attention; 'current' = what is being played now.
SIGNALS = [
    ("crazygames", None, "plays", "cg_plays", "alltime", 1.0),
    ("crazygames", "hot", "rank", "cg_hot", "current", 1.0),
    ("poki", None, "votes", "poki_votes", "alltime", 1.0),
    ("poki", None, "rank", "poki_pop", "current", 1.0),
    ("y8", None, "plays", "y8_plays", "alltime", 1.0),
    ("4399", "total_click_rank", "rank", "r4399_total", "alltime", 1.0),
    ("4399", "monthly_click_rank", "rank", "r4399_month", "current", 1.0),
    ("7k7k", "最热游戏", "rank", "r7k_hot", "current", 0.5),
    ("coolmathgames", None, "votes", "cm_votes", "alltime", 0.5),   # hand-picked slug list -> half weight
    ("kongregate", None, "plays", "kong_plays", "alltime", 0.5),    # older/core audience, 60 titles
]
PRESENCE = ["twoplayergames", "lagged", "playgama", "pacogames", "miniplay", "agame"]

STRIP_ZH = re.compile(r"(中文|无敌|选关|修改|完整|终极|加强|豪华|怀旧|经典|正式|电脑|原版|升级|速升|幸运|变态|战略|真人)?版|"
                      r"h5|4399|7k7k|v?\d+(\.\d+)+|双人|三人|单人|新版|online|\(.*?\)|（.*?）")
STRIP_EN = re.compile(r"^play |\bonline\b.*$|[–\-:|] .*$|\bat coolmath games\b|\bgame\b|\bfree\b|\bmultiplayer\b|"
                      r"\b(remastered|redux|lite|classic|html5?|webgl|flash|unblocked|io)\b|\b20\d\d\b|\(.*?\)")


def clean_title(t):
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^Play (.*?)(?: Online.*| on Coolmath.*)?$", r"\1", t)
    t = re.sub(r"\s*[–-] Play.*$|: (Play|Online).*$| – .*Coolmath.*$| at Coolmath Games$", "", t)
    return t.strip()


def franchise_key(t):
    s = t.lower()
    s = STRIP_ZH.sub("", s)
    s = STRIP_EN.sub("", s)
    s = re.sub(r"[’'`\.]", "", s)
    s = re.sub(r"\b(ii|iii|iv)\b", "", s)
    s = re.sub(r"\d+$", "", s.strip())          # trailing sequel number
    s = re.sub(r"[^a-z0-9一-鿿]+", "", s)
    s = re.sub(r"\d+$", "", s)
    return s or re.sub(r"\s+", "", t.lower())


def classify(t):
    tl = t.lower()
    for a in ARCH:
        if re.search(a["rx"], tl, re.I):
            return a["id"]
    return "other"


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    raw = list(csv.DictReader(open(D("web_games_raw.csv"), encoding="utf-8")))
    for r in raw:
        r["title"] = clean_title(r["title"])
        r["key"] = franchise_key(r["title"])

    games = {}

    def G(r):
        g = games.get(r["key"])
        if not g:
            g = games[r["key"]] = dict(key=r["key"], title=r["title"], titles=set(), platforms=set(),
                                       urls=[], released=[], sig={}, raw={}, presence=set())
        g["titles"].add(r["title"])
        if len(r["title"]) < len(g["title"]) and not re.search(r"[一-鿿]", g["title"]) \
                and not re.search(r"\d", r["title"]):
            g["title"] = r["title"]
        return g

    sig_tot = collections.Counter()
    for plat, lst, metric, name, kind, w in SIGNALS:
        best = {}
        for r in raw:
            if r["platform"] != plat or (lst and r["listing"] != lst):
                continue
            v = fnum(r[metric])
            if v is None or v <= 0:
                continue
            if metric == "rank":
                val = 1.0 / (v ** ZIPF_S)
                rawv = v
                if r["key"] in best and best[r["key"]][0] >= val:      # best (lowest) rank per franchise
                    continue
                best[r["key"]] = (val, rawv, r)
            else:
                # franchise total = sum over distinct entries (sequels), each entry counted once
                ent = best.setdefault(r["key"], [0.0, 0.0, r, set()])
                if r["url"] in ent[3]:
                    continue
                ent[3].add(r["url"])
                ent[0] += v
                ent[1] += v
        tot = sum(b[0] for b in best.values())
        sig_tot[name] = len(best)
        for key, b in best.items():
            g = G(b[2])
            g["platforms"].add(plat)
            g["sig"][name] = b[0] / tot if tot else 0.0
            g["raw"][name] = b[1]
            g["urls"].append(b[2]["url"])
            if b[2].get("released"):
                g["released"].append(b[2]["released"][:4])
    # games that only appear in non-signal listings of signal platforms (e.g. 7k7k category blocks, itch)
    for r in raw:
        if r["platform"] in PRESENCE:
            continue
        g = G(r)
        g["platforms"].add(r["platform"])
        if not g["urls"]:
            g["urls"].append(r["url"])
    # presence-only portals: match by franchise key against known games, else add as new (title is real)
    for r in raw:
        if r["platform"] not in PRESENCE:
            continue
        if len(r["key"]) < 4 or len(r["title"].split()) > 7:
            continue
        g = G(r)
        g["presence"].add(r["platform"])

    names = [s[3] for s in SIGNALS]
    weights = {s[3]: s[5] for s in SIGNALS}
    kinds = {s[3]: s[4] for s in SIGNALS}
    out = []
    for g in games.values():
        g["archetype"] = OVERRIDES.get(g["title"].lower()) or classify(" | ".join(sorted(g["titles"])))
        wsum = sum(weights.values())
        g["demand_index"] = sum(g["sig"].get(n, 0.0) * weights[n] for n in names) / wsum
        g["n_signal_platforms"] = len({n.split("_")[0] for n in g["sig"]})
        g["n_sites"] = len(g["platforms"] | g["presence"])
        out.append(g)
    out.sort(key=lambda g: -g["demand_index"])

    cols = ["rank", "title", "archetype", "demand_index_pct", "n_sites", "sites", "first_release_year",
            "cg_plays", "poki_votes", "poki_pop_rank", "cg_hot_rank", "y8_plays", "r4399_total_rank",
            "r4399_month_rank", "r7k_hot_rank", "cm_votes", "kong_plays"] + \
           ["share_" + n for n in names] + ["alt_titles", "url", "key"]
    with open(D("games.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i, g in enumerate(out, 1):
            rw = g["raw"]
            yrs = [int(y) for y in g["released"] if y.isdigit() and 1995 < int(y) < 2027]
            w.writerow([i, g["title"], g["archetype"], round(100 * g["demand_index"], 4), g["n_sites"],
                        ";".join(sorted(g["platforms"] | g["presence"])), min(yrs) if yrs else "",
                        int(rw["cg_plays"]) if "cg_plays" in rw else "",
                        int(rw["poki_votes"]) if "poki_votes" in rw else "",
                        int(rw["poki_pop"]) if "poki_pop" in rw else "",
                        int(rw["cg_hot"]) if "cg_hot" in rw else "",
                        int(rw["y8_plays"]) if "y8_plays" in rw else "",
                        int(rw["r4399_total"]) if "r4399_total" in rw else "",
                        int(rw["r4399_month"]) if "r4399_month" in rw else "",
                        int(rw["r7k_hot"]) if "r7k_hot" in rw else "",
                        int(rw["cm_votes"]) if "cm_votes" in rw else "",
                        int(rw["kong_plays"]) if "kong_plays" in rw else ""] +
                       [round(100 * g["sig"].get(n, 0.0), 4) for n in names] +
                       [" / ".join(sorted(g["titles"] - {g["title"]}))[:160], g["urls"][0] if g["urls"] else "",
                        g["key"]])
    print(len(out), "franchises ->", D("games.csv"), "| with >=1 quantitative signal:",
          sum(1 for g in out if g["sig"]))

    # ---------------------------------------------------------------- archetype roll-up
    scratch = collections.defaultdict(list)
    if os.path.exists(D("scratch_signal.csv")):
        for r in csv.DictReader(open(D("scratch_signal.csv"), encoding="utf-8")):
            scratch[r["archetype"]].append(int(r["sum_views"]))
    agg = collections.defaultdict(lambda: dict(n=0, n_sig=0, sig=collections.Counter(), titles=[], top=0.0,
                                               presence=0, multi=0))
    for g in out:
        a = agg[g["archetype"]]
        a["n"] += 1
        if g["sig"]:
            a["n_sig"] += 1
        for n, v in g["sig"].items():
            a["sig"][n] += v
        a["titles"].append((g["demand_index"], g["title"]))
        a["top"] = max(a["top"], g["demand_index"])
        a["presence"] += len(g["presence"])
        if g["n_sites"] >= 3:
            a["multi"] += 1
    rows = []
    wsum = sum(weights.values())
    w_all = sum(w for n, w in weights.items() if kinds[n] == "alltime")
    w_cur = sum(w for n, w in weights.items() if kinds[n] == "current")
    for aid, a in agg.items():
        tot = sum(a["sig"][n] * weights[n] for n in names) / wsum
        alltime = sum(a["sig"][n] * weights[n] for n in names if kinds[n] == "alltime") / w_all
        current = sum(a["sig"][n] * weights[n] for n in names if kinds[n] == "current") / w_cur
        breadth = sum(1 for n in names if a["sig"][n] >= 0.005)          # >=0.5% of that list's attention
        top3 = [t for _, t in sorted(a["titles"], reverse=True)[:5]]
        rows.append(dict(archetype=aid, zh=ARCH_BY.get(aid, {}).get("zh", "未归类"),
                         origin=ARCH_BY.get(aid, {}).get("origin", ""),
                         n_games=a["n"], n_games_with_signal=a["n_sig"], n_games_on_3plus_sites=a["multi"],
                         web_share_pct=round(100 * tot, 3), alltime_share_pct=round(100 * alltime, 3),
                         current_share_pct=round(100 * current, 3),
                         momentum=round(current / alltime, 2) if alltime > 0 else "",
                         breadth_signals=breadth,
                         brand_dependence=round(a["top"] / tot, 2) if tot > 0 else "",
                         scratch_views_max=max(scratch.get(aid, [0])),
                         **{"share_" + n: round(100 * a["sig"][n], 2) for n in names},
                         top_titles=" | ".join(top3)))
    rows.sort(key=lambda r: -r["web_share_pct"])
    with open(D("archetype_demand.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "archetypes ->", D("archetype_demand.csv"))
    print("signal list sizes:", dict(sig_tot))
    for r in rows:
        print(f"{r['archetype']:24s} n={r['n_games']:4d} web={r['web_share_pct']:6.2f}% all={r['alltime_share_pct']:6.2f}% "
              f"cur={r['current_share_pct']:6.2f}% br={r['breadth_signals']:2d} brand={r['brand_dependence']} | {r['top_titles'][:70]}")


if __name__ == "__main__":
    main()
