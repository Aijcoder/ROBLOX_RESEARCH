#!/usr/bin/env python3
"""Age gate per experience — Roblox content-maturity label and minimum age.

The label decides which age-based account types can enter an experience at all (Roblox Kids 5-8,
Roblox Select 9-15, standard 16+, and users who have not completed an age check), so it is the one
age-related fact that is public per experience. Audience age itself is only visible to the owner.

Re-asks the chart and search endpoints (which return the label) for every chart sort and every archetype
query, and keeps one row per experience. Labels do not move with time of day, so this can be joined to
the earlier CCU snapshot by universe_id.

-> data/roblox_maturity.csv
"""
import csv, json, os, ssl, time, urllib.request, urllib.parse, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, "data", *p)
SID = "11111111-1111-1111-1111-111111111111"
CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem") if os.path.exists("/etc/ssl/cert.pem") \
    else ssl.create_default_context()


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            time.sleep(8 * (i + 1) if e.code == 429 else 2)
        except Exception:  # noqa
            time.sleep(2)
    return {}


def main():
    seen = {}

    def keep(g, source):
        uid = g.get("universeId")
        if uid is None or uid in seen:
            return
        seen[uid] = dict(universe_id=uid, name=g.get("name"), minimum_age=g.get("minimumAge"),
                         content_maturity=g.get("contentMaturity"),
                         label=g.get("ageRecommendationDisplayName"), source=source)

    tok, sorts = "", []
    for _ in range(12):
        u = f"https://apis.roblox.com/explore-api/v1/get-sorts?sessionId={SID}&device=computer&country=us"
        if tok:
            u += "&sortsPageToken=" + urllib.parse.quote(tok)
        j = get(u)
        sorts += [s["sortId"] for s in j.get("sorts", []) if s.get("contentType") == "Games"]
        tok = j.get("nextSortsPageToken")
        if not tok:
            break
        time.sleep(0.4)
    for sid in sorts:
        ptok = ""
        for _ in range(10):
            u = (f"https://apis.roblox.com/explore-api/v1/get-sort-content?sessionId={SID}&sortId={sid}"
                 f"&device=computer&country=us")
            if ptok:
                u += "&pageToken=" + urllib.parse.quote(ptok)
            j = get(u)
            for g in j.get("games", []):
                keep(g, "chart")
            ptok = j.get("nextPageToken")
            if not ptok:
                break
            time.sleep(0.4)
    print("charts:", len(seen), flush=True)

    arch = json.load(open(D("archetypes.json"), encoding="utf-8"))
    for a in arch:
        for q in a["roblox_queries"]:
            tok = ""
            for _ in range(2):
                u = ("https://apis.roblox.com/search-api/omni-search?searchQuery=" + urllib.parse.quote(q) +
                     f"&pageToken={urllib.parse.quote(tok)}&sessionId={SID}&pageType=all")
                j = get(u)
                for grp in j.get("searchResults", []):
                    if grp.get("contentGroupType") == "Game":
                        for g in grp.get("contents", []):
                            keep(g, "search")
                tok = j.get("nextPageToken") or ""
                time.sleep(0.6)
                if not tok:
                    break
        print(f"  {a['id']:26s} total {len(seen)}", flush=True)

    with open(D("roblox_maturity.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["universe_id", "name", "minimum_age", "content_maturity", "label", "source"])
        w.writeheader()
        w.writerows(seen.values())
    print(len(seen), "experiences ->", D("roblox_maturity.csv"))


if __name__ == "__main__":
    main()
