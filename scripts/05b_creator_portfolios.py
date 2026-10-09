#!/usr/bin/env python3
"""Reality check — are the leading competitors published by creators with an existing portfolio?

For the top direct competitors of the shortlisted archetypes, list the other public experiences of the
same creator (group or user) and how many of those passed 1M visits.
Caveat: a publisher can open a fresh group per game, so "no other games" does not prove "solo developer".

-> data/roblox_creator_portfolios.csv
Usage: python3 scripts/05b_creator_portfolios.py [archetype:count ...]
"""
import csv, json, os, ssl, sys, time, collections, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, "data", *p)
CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem") if os.path.exists("/etc/ssl/cert.pem") \
    else ssl.create_default_context()
DEFAULT = [("launch_distance", 9), ("physics_destruction", 7), ("penalty_freekick", 4), ("endless_runner", 5)]


def get(url):
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                return json.loads(r.read())
        except Exception:  # noqa
            time.sleep(3)
    return {}


def main():
    picks = [(a.split(":")[0], int(a.split(":")[1])) for a in sys.argv[1:]] or DEFAULT
    by = collections.defaultdict(list)
    for r in csv.DictReader(open(D("roblox_competitors.csv"), encoding="utf-8")):
        by[r["archetype"]].append(r)
    chosen = [(a, r) for a, n in picks for r in by[a][:n]]
    det = {str(g["id"]): g for g in get("https://games.roblox.com/v1/games?universeIds=" +
                                        ",".join(r["universe_id"] for _, r in chosen)).get("data", [])}
    out = []
    for a, r in chosen:
        g = det.get(r["universe_id"])
        if not g:
            continue
        c = g["creator"]
        members = None
        if c["type"] == "Group":
            games = get(f"https://games.roblox.com/v2/groups/{c['id']}/gamesV2?accessFilter=2&limit=50&sortOrder=Desc")
            members = get(f"https://groups.roblox.com/v1/groups/{c['id']}").get("memberCount")
        else:
            games = get(f"https://games.roblox.com/v2/users/{c['id']}/games?accessFilter=2&limit=50&sortOrder=Desc")
        others = [x for x in (games.get("data") or []) if str(x.get("id")) != r["universe_id"]]
        visits = sorted((x.get("placeVisits", 0) for x in others), reverse=True)
        out.append(dict(archetype=a, name=r["name"], ccu=r["ccu"], creator=c["name"], creator_type=c["type"],
                        group_members=members, other_games=len(others),
                        other_games_ge_1m_visits=sum(v >= 1_000_000 for v in visits),
                        top_other_visits=visits[0] if visits else 0))
        print(f"{a:20s} {r['name'][:30]:30s} {c['type'][:1]}:{c['name'][:22]:22s} others={len(others)} "
              f">=1M={out[-1]['other_games_ge_1m_visits']}")
        time.sleep(0.5)
    with open(D("roblox_creator_portfolios.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    zero = sum(o["other_games"] == 0 for o in out)
    print(f"{len(out)} creators checked; {zero} have no other public game; "
          f"{sum(o['other_games_ge_1m_visits'] >= 1 for o in out)} have another game with >=1M visits")


if __name__ == "__main__":
    main()
