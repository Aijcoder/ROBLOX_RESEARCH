#!/usr/bin/env python3
"""Stage 4 — Roblox supply, live demand and competition per archetype.

Inputs : data/roblox_search_raw.csv, data/roblox_charts.csv, data/archetypes.json
Outputs: data/roblox_competitors.csv     every direct competitor found (one row per archetype x experience)
         data/archetype_competition.csv  competition metrics per archetype
         data/roblox_genre_stats.csv     genre-level structure of the Roblox market (from Roblox's own charts)

"Direct competitor" = a search result whose NAME matches the archetype's `rbx_rx`. Name-matching is crude:
it misses re-themed clones and admits false positives, so the per-archetype lists for every shortlisted
archetype were read by hand (see REPORT). Treat CCU sums as order-of-magnitude.
"""
import csv, json, os, re, collections, datetime, statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, "data", *p)
ARCH = json.load(open(D("archetypes.json"), encoding="utf-8"))


def I(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def days(datestr, today):
    try:
        return (today - datetime.date.fromisoformat(datestr)).days
    except Exception:
        return None


def main():
    rows = list(csv.DictReader(open(D("roblox_search_raw.csv"), encoding="utf-8")))
    today = datetime.date.fromisoformat(rows[0]["snapshot_utc"][:10])
    by = collections.defaultdict(dict)
    for r in rows:
        cur = by[r["group"]].get(r["universe_id"])
        if cur is None or I(r["rank"]) < I(cur["rank"]):
            by[r["group"]][r["universe_id"]] = r

    comp_rows, summ = [], []
    for a in ARCH:
        res = list(by.get(a["id"], {}).values())
        rx = re.compile(a["rbx_rx"], re.I)
        ex = re.compile(a.get("rbx_ex") or r"$^", re.I)
        direct = [r for r in res if rx.search(r["name"] or "") and not ex.search(r["name"] or "")]
        for r in direct:
            r["_ccu"] = I(r["playing"])
            r["_age"] = days(r["created"], today)
            r["_stale"] = days(r["updated"], today)
        direct.sort(key=lambda r: -r["_ccu"])
        ccu = sum(r["_ccu"] for r in direct)
        n100 = sum(r["_ccu"] >= 100 for r in direct)
        n1000 = sum(r["_ccu"] >= 1000 for r in direct)
        attempts = [r for r in direct if I(r["visits"]) >= 10_000]
        grave = [r for r in direct if I(r["visits"]) >= 1_000_000 and r["_ccu"] < 20]
        new_hits = [r for r in direct if r["_age"] is not None and r["_age"] <= 365 and r["_ccu"] >= 100]
        # entrants of the last 12 months that reached >=5M visits: at ~10 min/visit that is ~95 CCU-years,
        # i.e. the model's definition of traction, observed directly
        new_tr = [r for r in direct if r["_age"] is not None and r["_age"] <= 365 and I(r["visits"]) >= 5_000_000]
        new_all = [r for r in direct if r["_age"] is not None and r["_age"] <= 365]
        top5 = direct[:5]
        w = sum(r["_ccu"] for r in top5) or 1
        like = sum((float(r["like_ratio"]) if r["like_ratio"] else 0) * r["_ccu"] for r in top5) / w
        stale = sum((r["_stale"] or 0) * r["_ccu"] for r in top5) / w
        age = sum((r["_age"] or 0) * r["_ccu"] for r in top5) / w
        hhi = sum((r["_ccu"] / ccu) ** 2 for r in direct) if ccu else 0
        # which Roblox genre do the direct competitors actually sit in? (CCU-weighted mode, top entry capped
        # so that one giant does not decide it)
        gw1, gw2 = collections.Counter(), collections.Counter()
        for r in direct:
            wgt = min(r["_ccu"], 5000) + 1
            gw1[r["genre_l1"] or ""] += wgt
            gw2[r["genre_l2"] or ""] += wgt
        gw1.pop("", None)
        gw2.pop("", None)
        obs_l1 = gw1.most_common(1)[0][0] if gw1 else ""
        obs_l2 = gw2.most_common(1)[0][0] if gw2 else ""
        summ.append(dict(
            archetype=a["id"], zh=a["zh"], n_search_results=len(res), n_direct=len(direct),
            n_attempts_10k_visits=len(attempts), ccu_direct=ccu, n_ccu_100=n100, n_ccu_1000=n1000,
            top1_name=(direct[0]["name"] if direct else ""), top1_ccu=(direct[0]["_ccu"] if direct else 0),
            top1_share=round(direct[0]["_ccu"] / ccu, 2) if ccu else "", hhi=round(hhi, 2),
            new_hits_12m=len(new_hits), new_hits_ccu=sum(r["_ccu"] for r in new_hits),
            new_entrants_12m_found=len(new_all), new_traction_12m=len(new_tr),
            new_entrant_visits_12m=sum(I(r["visits"]) for r in new_all),
            graveyard_1m_visits_dead=len(grave),
            alive_ratio=round(n100 / len(attempts), 3) if attempts else "",
            top5_like_ratio=round(like, 3), top5_days_since_update=round(stale), top5_age_days=round(age),
            visits_direct=sum(I(r["visits"]) for r in direct), observed_genre_l1=obs_l1, observed_genre_l2=obs_l2,
            top5=" | ".join(f"{r['name'][:32]} ({r['_ccu']:,} CCU; {I(r['visits'])/1e6:.1f}M visits; {r['created'][:7]})"
                            for r in top5)))
        for r in direct[:60]:
            comp_rows.append(dict(archetype=a["id"], name=r["name"], ccu=r["_ccu"], visits=I(r["visits"]),
                                  like_ratio=r["like_ratio"], up_votes=r["up_votes"], created=r["created"],
                                  updated=r["updated"], age_days=r["_age"], days_since_update=r["_stale"],
                                  genre_l1=r["genre_l1"], genre_l2=r["genre_l2"], creator=r["creator"],
                                  creator_type=r["creator_type"], universe_id=r["universe_id"],
                                  url=f"https://www.roblox.com/games/{r['root_place_id']}",
                                  found_by_query=r["query"]))
    with open(D("roblox_competitors.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(comp_rows[0].keys()))
        w.writeheader()
        w.writerows(comp_rows)
    with open(D("archetype_competition.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summ[0].keys()))
        w.writeheader()
        w.writerows(summ)
    print(len(comp_rows), "competitor rows;", len(summ), "archetypes")

    # ------------------------------------------------------------ genre structure from Roblox charts
    ch = list(csv.DictReader(open(D("roblox_charts.csv"), encoding="utf-8")))
    ctoday = datetime.date.fromisoformat(ch[0]["snapshot_utc"][:10])
    te = [r for r in ch if r["query"] == "top-earning"]
    tp = [r for r in ch if r["query"] == "top-playing-now"]
    # every distinct experience seen on any chart, for CCU by genre
    uniq = {}
    for r in ch:
        uniq[r["universe_id"]] = r
    out = []
    for level in ("genre_l1", "genre_l2"):
        gs = collections.defaultdict(lambda: dict(earn_n=0, earn_w=0.0, earn_ccu=0, young=0, young_ccu=[],
                                                  chart_ccu=0, chart_n=0, top_play_ccu=0))
        for i, r in enumerate(te, 1):
            g = gs[r[level] or "(none)"]
            g["earn_n"] += 1
            g["earn_w"] += 1.0 / i                      # Zipf proxy for revenue share by earning rank
            g["earn_ccu"] += I(r["playing"])
            ag = days(r["created"], ctoday)
            if ag is not None and ag <= 365:
                g["young"] += 1
                g["young_ccu"].append(I(r["playing"]))
        for r in uniq.values():
            g = gs[r[level] or "(none)"]
            g["chart_ccu"] += I(r["playing"])
            g["chart_n"] += 1
        for r in tp:
            gs[r[level] or "(none)"]["top_play_ccu"] += I(r["playing"])
        ratios = collections.defaultdict(list)       # robust version: per-game (1/rank)/CCU, median by genre
        allr = []
        for i, r in enumerate(te, 1):
            c = I(r["playing"])
            if c > 0:
                ratios[r[level] or "(none)"].append((1.0 / i) / c)
                allr.append((1.0 / i) / c)
        med_all = statistics.median(allr)
        tot_w = sum(g["earn_w"] for g in gs.values())
        tot_c = sum(g["earn_ccu"] for g in gs.values())
        for name, g in gs.items():
            if g["earn_n"] == 0 and g["chart_n"] < 5:
                continue
            idx = (g["earn_w"] / tot_w) / (g["earn_ccu"] / tot_c) if g["earn_ccu"] else ""
            out.append(dict(level=level, genre=name, top_earning_n=g["earn_n"],
                            top_earning_zipf_share=round(g["earn_w"] / tot_w, 4),
                            top_earning_ccu=g["earn_ccu"],
                            earn_per_ccu_index=round(idx, 2) if idx != "" else "",
                            earn_per_ccu_index_robust=round(statistics.median(ratios[name]) / med_all, 2)
                            if ratios.get(name) else "",
                            new_12m_in_top_earning=g["young"],
                            new_12m_median_ccu=int(statistics.median(g["young_ccu"])) if g["young_ccu"] else "",
                            all_charts_n=g["chart_n"], all_charts_ccu=g["chart_ccu"],
                            top_playing_ccu=g["top_play_ccu"]))
    out.sort(key=lambda r: (r["level"], -r["top_earning_n"]))
    with open(D("roblox_genre_stats.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(len(out), "genre rows")
    for s in sorted(summ, key=lambda s: -s["ccu_direct"]):
        print(f"{s['archetype']:24s} dir={s['n_direct']:3d} att={s['n_attempts_10k_visits']:3d} ccu={s['ccu_direct']:>8,} n100={s['n_ccu_100']:3d} "
              f"n1k={s['n_ccu_1000']:2d} newtr={s['new_traction_12m']:2d} grave={s['graveyard_1m_visits_dead']:2d} "
              f"like={s['top5_like_ratio']:.2f} stale={s['top5_days_since_update']:4d}d | {s['top5'][:150]}")


if __name__ == "__main__":
    main()
