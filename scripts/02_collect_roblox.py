#!/usr/bin/env python3
"""Stage 4 input — snapshot Roblox supply and live demand from Roblox's public endpoints.

  --charts   Roblox chart sorts (Top Playing Now, Up-and-Coming, Top Earning, Trending in <genre>, ...)
             -> data/roblox_charts.csv
  --search   For every archetype in data/archetypes.json run its Roblox search queries
             -> data/roblox_search_raw.csv  (every result, unfiltered)

Every row is enriched from games.roblox.com (visits, playing, created, updated, favourites, genre).
These are point-in-time snapshots: `playing` moves with time of day / day of week.
"""
import csv, json, os, ssl, sys, time, datetime, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SID = "11111111-1111-1111-1111-111111111111"
CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem") if os.path.exists("/etc/ssl/cert.pem") \
    else ssl.create_default_context()
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(8 * (i + 1))
                continue
            if i == tries - 1:
                print("  HTTP", e.code, url[:110])
            time.sleep(2)
        except Exception as e:  # noqa
            if i == tries - 1:
                print("  ERR", repr(e)[:80], url[:110])
            time.sleep(2)
    return {}


def details(ids):
    """universeId -> detail dict (batched)."""
    out = {}
    ids = list(dict.fromkeys(ids))
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        j = get("https://games.roblox.com/v1/games?universeIds=" + ",".join(map(str, chunk)))
        for g in j.get("data", []):
            out[g["id"]] = g
        time.sleep(0.4)
    return out


def enrich(row, d):
    g = d.get(row["universe_id"], {})
    row.update(visits=g.get("visits"), playing_detail=g.get("playing"), favorites=g.get("favoritedCount"),
               created=(g.get("created") or "")[:10], updated=(g.get("updated") or "")[:10],
               genre_l1=g.get("genre_l1") or row.get("genre_l1") or "", genre_l2=g.get("genre_l2") or "",
               max_players=g.get("maxPlayers"), creator=(g.get("creator") or {}).get("name"),
               creator_type=(g.get("creator") or {}).get("type"))
    return row


COLS = ["snapshot_utc", "group", "query", "rank", "universe_id", "root_place_id", "name", "playing",
        "up_votes", "down_votes", "like_ratio", "visits", "playing_detail", "favorites", "created",
        "updated", "genre_l1", "genre_l2", "max_players", "creator", "creator_type", "is_sponsored"]


def base_row(group, query, rank, g):
    up, dn = g.get("totalUpVotes") or 0, g.get("totalDownVotes") or 0
    return dict(snapshot_utc=NOW, group=group, query=query, rank=rank, universe_id=g.get("universeId"),
                root_place_id=g.get("rootPlaceId"), name=g.get("name"), playing=g.get("playerCount"),
                up_votes=up, down_votes=dn, like_ratio=round(up / (up + dn), 4) if up + dn else "",
                genre_l1=g.get("genreL1", ""), is_sponsored=g.get("isSponsored", False))


def write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "rows ->", path)


def charts():
    rows, tok = [], ""
    sort_ids = []
    for _ in range(12):
        u = f"https://apis.roblox.com/explore-api/v1/get-sorts?sessionId={SID}&device=computer&country=us"
        if tok:
            u += "&sortsPageToken=" + urllib.parse.quote(tok)
        j = get(u)
        for s in j.get("sorts", []):
            if s.get("contentType") == "Games":
                sort_ids.append((s["sortId"], s.get("sortDisplayName")))
        tok = j.get("nextSortsPageToken")
        if not tok:
            break
        time.sleep(0.4)
    for sid, name in sort_ids:
        games, ptok = [], ""
        for _ in range(10):
            u = (f"https://apis.roblox.com/explore-api/v1/get-sort-content?sessionId={SID}&sortId={sid}"
                 f"&device=computer&country=us")
            if ptok:
                u += "&pageToken=" + urllib.parse.quote(ptok)
            j = get(u)
            games += j.get("games", [])
            ptok = j.get("nextPageToken")
            if not ptok:
                break
            time.sleep(0.4)
        for i, g in enumerate(games, 1):
            rows.append(base_row("chart", sid, i, g))
        print(f"  {sid:42s} {len(games)}")
    d = details([r["universe_id"] for r in rows])
    write(os.path.join(DATA, "roblox_charts.csv"), [enrich(r, d) for r in rows])


def search():
    arch = json.load(open(os.path.join(DATA, "archetypes.json"), encoding="utf-8"))
    rows = []
    for a in arch:
        for q in a["roblox_queries"]:
            got, tok = [], ""
            for _ in range(2):  # two result pages per query
                u = ("https://apis.roblox.com/search-api/omni-search?searchQuery=" + urllib.parse.quote(q) +
                     f"&pageToken={urllib.parse.quote(tok)}&sessionId={SID}&pageType=all")
                j = get(u)
                for grp in j.get("searchResults", []):
                    if grp.get("contentGroupType") == "Game":
                        got += grp.get("contents", [])
                tok = j.get("nextPageToken") or ""
                time.sleep(0.6)
                if not tok:
                    break
            for i, g in enumerate(got, 1):
                rows.append(base_row(a["id"], q, i, g))
            print(f"  {a['id']:28s} {q:32s} {len(got)}")
    d = details([r["universe_id"] for r in rows])
    write(os.path.join(DATA, "roblox_search_raw.csv"), [enrich(r, d) for r in rows])


if __name__ == "__main__":
    if "--charts" in sys.argv:
        charts()
    if "--search" in sys.argv:
        search()
    if len(sys.argv) == 1:
        print(__doc__)
