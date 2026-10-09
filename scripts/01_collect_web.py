#!/usr/bin/env python3
"""Stage 1 — collect real demand signals from web game portals.

Writes data/web_games_raw.csv: one row per (platform, listing, game).
Only numbers that the portal itself publishes are recorded; nothing is imputed here.
Raw pages are cached under CACHE so re-runs are cheap and auditable.

Usage: python3 scripts/01_collect_web.py [--refresh]
"""
import csv, json, os, re, ssl, sys, time, html, hashlib, socket, datetime, urllib.request, urllib.error

socket.setdefaulttimeout(25)   # a stalled host must not hang the whole run
from concurrent.futures import ThreadPoolExecutor

# python.org builds on macOS ship without a CA bundle; use the system one (verification stays on).
SSL_CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem") if os.path.exists("/etc/ssl/cert.pem") \
    else ssl.create_default_context()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.environ.get("GAMES_CACHE", os.path.join(ROOT, ".cache", "web"))
OUT = os.path.join(ROOT, "data", "web_games_raw.csv")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
REFRESH = "--refresh" in sys.argv
TODAY = datetime.date.today().isoformat()
os.makedirs(CACHE, exist_ok=True)
os.makedirs(os.path.dirname(OUT), exist_ok=True)

FAILS = []


def fetch(url, enc="utf-8", tries=2):
    key = hashlib.md5(url.encode()).hexdigest()
    path = os.path.join(CACHE, key)
    if os.path.exists(path) and not REFRESH:
        return open(path, "rb").read().decode(enc, "ignore")
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
                data = r.read()
            open(path, "wb").write(data)
            time.sleep(0.25)
            return data.decode(enc, "ignore")
        except urllib.error.HTTPError as e:
            err = str(e)
            if e.code == 404:                       # remember dead URLs so re-runs do not ask again
                open(path, "wb").write(b"")
                break
            time.sleep(1.5)
        except Exception as e:  # noqa
            err = str(e)
            time.sleep(1.5)
    FAILS.append((url, err))
    return ""


def pmap(fn, items, workers=6):
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(fn, items))


def num(s):
    """'27,191,026' / '3.3M' / '524.5K' -> float"""
    if s is None:
        return None
    s = str(s).strip().replace(",", "")
    m = re.match(r"^([\d.]+)\s*([KMB]?)", s, re.I)
    if not m or not m.group(1):
        return None
    try:
        return float(m.group(1)) * {"": 1, "K": 1e3, "M": 1e6, "B": 1e9}[m.group(2).upper()]
    except ValueError:
        return None


ROWS = []


def add(platform, listing, rank, title, url="", plays=None, votes=None, likes=None,
        rating=None, rating_scale=None, released="", tags=""):
    title = html.unescape(re.sub(r"\s+", " ", title or "")).strip()
    if not title:
        return
    ROWS.append(dict(platform=platform, listing=listing, rank=rank, title=title, url=url,
                     plays=plays, votes=votes, likes=likes, rating=rating,
                     rating_scale=rating_scale, released=released, tags=tags, fetched=TODAY))


# ---------------------------------------------------------------- CrazyGames
def crazygames():
    pages = [("hot", f"https://www.crazygames.com/hot?page={p}") for p in range(1, 6)]
    for tag in ["c/action", "c/adventure", "c/casual", "c/clicker", "c/driving", "c/puzzle",
                "c/shooting", "c/sports", "c/io", "t/2-player", "t/multiplayer", "t/stickman",
                "t/parkour", "t/racing", "t/fighting", "t/simulation", "t/tower-defense",
                "t/idle", "t/physics", "t/skill", "t/escape", "t/horror", "t/platformer",
                "t/sandbox", "t/snake", "t/zombie", "t/tycoon", "t/survival", "t/fun"]:
        for p in (1, 2):
            pages.append((tag, f"https://www.crazygames.com/{tag}?page={p}"))
    seen = set()
    for listing, url in pages:
        s = fetch(url)
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', s, re.S)
        if not m:
            continue
        try:
            pp = json.loads(m.group(1))["props"]["pageProps"]
        except Exception:
            continue
        games = (pp.get("games") or {}).get("items") or []
        pg = int(re.search(r"page=(\d+)", url).group(1))
        for i, g in enumerate(games):
            key = (listing, g.get("slug"))
            if key in seen:
                continue
            seen.add(key)
            add("crazygames", listing, (pg - 1) * 40 + i + 1, g.get("name"),
                "https://www.crazygames.com/game/" + str(g.get("slug")),
                plays=g.get("totalPlays"), likes=g.get("totalLikes"),
                released=str(g.get("releaseYear") or ""), tags=g.get("categoryName") or "")


# ---------------------------------------------------------------------- Poki
def poki():
    s = fetch("https://poki.com/en/popular")
    tiles, seen = [], set()
    # two blocks on the page: "Popular this week" (12 tiles) then the general popular grid
    for m in re.finditer(r'<a class="[^"]*"\s+href="(/en/g/[^"]+)"[^>]*data-tile-list="([^"]+)"', s):
        if m.group(1) in seen:
            continue
        seen.add(m.group(1))
        tiles.append((len(tiles) + 1, m.group(1), m.group(2)))

    def one(a):
        i, slug, lst = a
        g = fetch("https://poki.com" + slug)
        t = re.search(r'<meta property="og:title" content="([^"]+)"', g)
        title = re.sub(r"\s*[-|].*$", "", html.unescape(t.group(1))) if t else slug.split("/")[-1].replace("-", " ").title()
        up = re.search(r'up_count\\":(\d+)', g)
        rv = re.search(r'"ratingValue":([\d.]+),"ratingCount":(\d+)', g)
        pub = re.search(r'"datePublished":"([\d-]+)"', g)
        return (i, slug, lst, title, int(up.group(1)) if up else None,
                float(rv.group(1)) if rv else None, int(rv.group(2)) if rv else None,
                pub.group(1) if pub else "")

    for i, slug, lst, title, up, rating, votes, pub in pmap(one, tiles):
        add("poki", "popular_page:" + lst, i, title, "https://poki.com" + slug, votes=votes, likes=up,
            rating=rating, rating_scale=5, released=pub)


# ------------------------------------------------------------------------ Y8
def y8():
    items = []
    for p in (1, 2, 3):
        s = fetch(f"https://www.y8.com/popular/games?page={p}")
        for m in re.finditer(r'<li id="item_\d+"[^>]*data-label-ids="([^"]*)".*?<a aria-label="([^"]+)" href="([^"]+)".*?'
                             r'item__rating">([\d.]+)<', s, re.S):
            items.append((len(items) + 1, m.group(2), m.group(3), m.group(1), m.group(4)))

    def one(it):
        rank, title, url, labels, rating = it
        g = fetch(url)
        pl = re.search(r"([\d,]+)\s*play times", g)
        lk = re.search(r'id="voting-button-yes".*?votes-count">\s*([\d.,KM]+)', g, re.S)
        return rank, title, url, labels, rating, num(pl.group(1)) if pl else None, num(lk.group(1)) if lk else None

    for rank, title, url, labels, rating, plays, likes in pmap(one, items):
        add("y8", "popular", rank, title, url, plays=plays, likes=likes, rating=float(rating),
            rating_scale=10, tags=html.unescape(labels))


# ---------------------------------------------------------------------- 4399
def g4399():
    for listing, url in (("total_click_rank", "https://www.4399.com/flash/ph.htm"),
                         ("monthly_click_rank", "https://www.4399.com/flash/zph.htm")):
        s = fetch(url, enc="gb18030")
        m = re.search(r'<ul class="tm_list">(.*?)</ul>', s, re.S)
        if not m:
            continue
        for i, li in enumerate(re.findall(r"<li>(.*?)</li>", m.group(1), re.S), 1):
            a = re.search(r'<a href="([^"]+)"><img alt="([^"]+)"', li)
            ems = re.findall(r"<em>(.*?)</em>", li, re.S)
            if not a:
                continue
            cat = re.sub(r"<[^>]+>", "", ems[0]) if ems else ""
            date = re.sub(r"<[^>]+>", "", ems[1]) if len(ems) > 1 else ""
            href = a.group(1)
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = "https://www.4399.com" + href
            add("4399", listing, i, a.group(2), href, released=date, tags=cat)


# ---------------------------------------------------------------------- 7k7k
def g7k7k():
    s = fetch("https://www.7k7k.com/top/")
    # the page is a sequence of headed blocks; keep the block heading as listing name
    parts = re.split(r"<h[23][^>]*>(.*?)</h[23]>", s, flags=re.S)
    for k in range(1, len(parts) - 1, 2):
        head = re.sub(r"<[^>]+>", "", parts[k]).strip()
        body = parts[k + 1]
        games = re.findall(r'<li class="game_item">\s*<a href="([^"]+)">.*?alt="([^"]+)"', body, re.S)
        for i, (href, name) in enumerate(games, 1):
            add("7k7k", head or "top", i, name, "https:" + href if href.startswith("//") else href)


# ----------------------------------------------------------------- Kongregate
def kongregate():
    s = fetch("https://www.kongregate.com/games?sort=gameplays")
    seen = set()
    for m in re.finditer(r'<a href="(/en/games/[^"]+)"[^>]*>.*?<div class="font-semibold truncate mb-1">\s*(.*?)\s*</div>'
                         r'.*?★</span>\s*<span>([\d.]+)</span>.*?<div class="text-right">\s*([\d.,KMB]+)\s*plays',
                         s, re.S):
        if m.group(1) in seen:
            continue
        seen.add(m.group(1))
        add("kongregate", "games_sorted_by_gameplays_page", len(seen), m.group(2),
            "https://www.kongregate.com" + m.group(1), plays=num(m.group(4)),
            rating=float(m.group(3)), rating_scale=5)


# ---------------------------------------------------------------- Armor Games
def armor():
    # NB: Armor's public listings surface recent releases, not its all-time catalogue.
    seen = set()
    for listing, url in (("recent_popular", "https://armorgames.com/games/popular"),
                         ("category_all", "https://armorgames.com/category/all")):
        s = fetch(url)
        for m in re.finditer(r'<h5><a href="(/[a-z0-9\-]+/\d+)" title="([^"]+)">.*?</h5>\s*<p class="plays">([\d,]+) plays</p>'
                             r'\s*<p class="rating">Rating: ([\d.]+)/10', s, re.S):
            if m.group(1) in seen:
                continue
            seen.add(m.group(1))
            add("armorgames", listing, len(seen), m.group(2), "https://armorgames.com" + m.group(1),
                plays=num(m.group(3)), rating=float(m.group(4)), rating_scale=10)


# ------------------------------------------------------------- Coolmath Games
COOLMATH_SLUGS = """run-3 run-2 run fireboy-and-watergirl-in-the-forest-temple fireboy-and-watergirl-2-light-temple
fireboy-and-watergirl-3-ice-temple bloxorz moto-x3m moto-x3m-2 snake tiny-fishing idle-breakout parking-fury
big-tower-tiny-square checkers chess 8-ball-pool iq-ball retro-ping-pong hangman crazy-eights there-is-no-game
duck-life duck-life-2 duck-life-3 duck-life-4 learn-fly learn-fly-2 penalty-kick-online slice-master clicker-heroes
jelly-truck worlds-hardest-game worlds-hardest-game-2 copter-royale awesome-tanks awesome-tanks-2 candy-jump
sugar-sugar papas-pizzeria papas-freezeria papas-burgeria papas-scooperia coffee-shop lemonade-stand
tower-defense bloons-tower-defense bloons-tower-defense-2 red-ball-4-volume-1 red-ball-4 red-ball
wheely wheely-2 2048 suika-watermelon-game tag basket-random basketbros swingo powerline-io curve-ball-3d
hexanaut-io ovo ovo-2 vex-3 vex-4 vex-5 vex-6 vex-7 vex-8 geometry-dash jumping-shell exit-path
defly-io little-alchemy little-alchemy-2 dino-game flappy-bird crossy-road pac-man tetris minesweeper
solitaire four-in-a-row tic-tac-toe chess-vs-computer mancala billiards darts mini-golf bowling
cannon-basketball basket-and-ball stickman-hook cut-the-rope bob-the-robber bob-the-robber-2 trace
escape-the-freezer push-the-box jacksmith civiballs b-cubed electric-man johnny-upgrade raft-wars raft-wars-2
grindcraft doodle-god factory-balls line-rider happy-wheels worlds-easyest-game cookie-clicker
truck-loader zoo-escape plumber maze 60-second-burger-run drift-boss draw-play eggy-car
atari-breakout atari-asteroids snake-vs-block paper-io paper-io-2 slither-io agar-io hole-io
dinosaur-game catch-the-candy handulum sticky-ninja-missions wall-jumper stick-merge idle-startup-tycoon
idle-mining-empire idle-dice learn-to-fly-idle metal-detector-tycoon clean-up-io
learn-to-fly learn-to-fly-2 learn-to-fly-3 burrito-bison zombie-launcher zombie-launcher-2
duck-life-2-world-champion duck-life-3-evolution moto-x3m-pool-party moto-x3m-spooky-land moto-x3m-winter
tag-game slope-tunnel snowman-skiing""".split()


def coolmath():
    sm = fetch("https://www.coolmathgames.com/sitemap.xml")
    valid = set(re.findall(r"coolmathgames\.com/0-([a-z0-9\-]+)<", sm))
    slugs = [s for s in COOLMATH_SLUGS if (not valid) or s in valid]

    def one(slug):
        g = fetch("https://www.coolmathgames.com/0-" + slug)
        t = re.search(r'<meta property="og:title" content="([^"]+)"', g)
        rc = re.search(r'rate-count">([\d.]+)\s*/\s*5</span><span class="vote-count"\s*>\(([\d,]+) Votes\)', g)
        rel = re.search(r"Rel[^<]*</div><div class=\"field-row-right\">([^<]+)<", g)
        if not rc:
            return None
        title = re.sub(r"\s*[-|].*$", "", t.group(1)) if t else slug
        return slug, title, float(rc.group(1)), num(rc.group(2)), rel.group(1) if rel else ""

    res = [r for r in pmap(one, slugs) if r]
    res.sort(key=lambda r: -r[3])
    for i, (slug, title, rating, votes, rel) in enumerate(res, 1):
        add("coolmathgames", "curated_known_titles_by_votes", i, title,
            "https://www.coolmathgames.com/0-" + slug, votes=votes, rating=rating, rating_scale=5, released=rel)


# -------------------------------------------------------------------- Scratch
def scratch():
    seen = set()
    for mode in ("popular", "trending"):
        for off in (0, 40, 80):
            s = fetch(f"https://api.scratch.mit.edu/explore/projects?limit=40&offset={off}&mode={mode}&q=games")
            try:
                arr = json.loads(s)
            except Exception:
                continue
            for p in arr:
                if p["id"] in seen:
                    continue
                seen.add(p["id"])
                st = p.get("stats", {})
                add("scratch", f"explore_games_{mode}", len(seen), p.get("title", ""),
                    f"https://scratch.mit.edu/projects/{p['id']}", plays=st.get("views"),
                    likes=st.get("loves"), votes=st.get("favorites"),
                    released=(p.get("history", {}).get("shared") or "")[:10],
                    tags=f"remixes={st.get('remixes')}")


# -------------------------------------------------------------------- itch.io
def itch():
    items = []
    for listing, url in (("top_rated_web", "https://itch.io/games/top-rated/platform-web"),
                         ("popular_web", "https://itch.io/games/platform-web"),
                         ("top_rated_web_p2", "https://itch.io/games/top-rated/platform-web?page=2")):
        s = fetch(url)
        for i, m in enumerate(re.finditer(r'<a[^>]*class="title game_link"[^>]*href="([^"]+)"[^>]*>([^<]+)<|'
                                          r'<a[^>]*href="([^"]+)"[^>]*class="title game_link"[^>]*>([^<]+)<', s), 1):
            href = m.group(1) or m.group(3)
            title = m.group(2) or m.group(4)
            items.append((listing, i, href, title))

    def one(it):
        listing, i, href, title = it
        g = fetch(href)
        rv = re.search(r'"ratingValue":"?([\d.]+)"?,"ratingCount":(\d+)|"ratingCount":(\d+),"ratingValue":"?([\d.]+)', g)
        rating = votes = None
        if rv:
            rating = float(rv.group(1) or rv.group(4))
            votes = int(rv.group(2) or rv.group(3))
        return listing, i, href, title, rating, votes

    for listing, i, href, title, rating, votes in pmap(one, items):
        add("itch.io", listing, i, title, href, votes=votes, rating=rating, rating_scale=5)


# ------------------------------------------------- presence-only portal lists
PRESENCE = {
    "friv": ("https://www.friv.com/", r'alt="([^"]{3,60})"'),
    "lagged": ("https://lagged.com/", r'alt="([^"]{3,60}?)(?: Game)?"'),
    "miniplay": ("https://www.miniplay.com/", r'alt="([^"_]{3,60})"'),
    "addictinggames": ("https://www.addictinggames.com/", r'alt="([^"]{3,60})"'),
    "twoplayergames": ("https://www.twoplayergames.org/", r'alt="([^"]{3,60})"'),
    "iogames.space": ("https://iogames.space/", r'alt="([^"]{3,60})"'),
    "playgama": ("https://playgama.com/", r'alt="([^"]{3,60})"'),
    "agame": ("https://www.agame.com/games/popular", r'alt="([^"]{3,60})"'),
    "1001games": ("https://www.1001games.com/", r'alt="([^"]{3,60})"'),
    "pacogames": ("https://www.pacogames.com/", r'alt="([^"]{3,60})"'),
    "kizi": ("https://kizi.com/", r'alt="([^"]{3,60})"'),
}
JUNK = re.compile(r"logo|icon|app ?store|google play|avatar|banner|facebook|twitter|youtube|no ad|"
                  r"featured|popular games|new games|categories|casino|slots|^games?$|addicting games", re.I)


def presence():
    for name, (url, pat) in PRESENCE.items():
        s = fetch(url)
        seen = []
        for t in re.findall(pat, s):
            t = html.unescape(t).strip()
            if JUNK.search(t) or t in seen:
                continue
            seen.append(t)
        for i, t in enumerate(seen, 1):
            add(name, "front_or_popular_page", i, t, url)


def main():
    for fn in (crazygames, poki, y8, g4399, g7k7k, kongregate, armor, coolmath, itch, presence):
        n0 = len(ROWS)
        try:
            fn()
        except Exception as e:  # keep going; report coverage honestly
            FAILS.append((fn.__name__, repr(e)))
        print(f"{fn.__name__:12s} +{len(ROWS) - n0} rows")
    cols = ["platform", "listing", "rank", "title", "url", "plays", "votes", "likes", "rating",
            "rating_scale", "released", "tags", "fetched"]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(ROWS)
    print("rows", len(ROWS), "->", OUT)
    print("failures", len(FAILS))
    for u, e in FAILS[:25]:
        print("  ", u, e)


if __name__ == "__main__":
    main()
