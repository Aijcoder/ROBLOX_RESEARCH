#!/usr/bin/env python3
"""Age-segment analysis.

What can be said about age with public data, and what cannot:
  * Roblox publishes the age mix of age-checked users, age-check penetration, and how much more U.S. adults
    spend. From these the full-population mix is DERIVED below (algebra shown), then split into finer bands
    with labelled ASSUMPTIONS.
  * Per experience, only the content-maturity label is public. It decides which account tiers may enter.
    The actual audience age of an experience is visible only to its owner — it is not estimated here.
  * Scratch publishes the age at sign-up of its users; it calibrates what the Scratch demand probe measures.

Inputs : data/age_reference.json, data/roblox_maturity.csv, data/roblox_charts.csv,
         data/roblox_competitors.csv, data/archetypes.json
Outputs: data/age_segments.csv, data/age_reach_by_label.csv, data/maturity_market.csv,
         data/maturity_by_archetype.csv, data/scratch_age_distribution.csv, out/age_summary.json
"""
import csv, json, os, ssl, collections, datetime, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, "data", *p)
O = lambda *p: os.path.join(ROOT, "out", *p)
REF = json.load(open(D("age_reference.json"), encoding="utf-8"))
CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem") if os.path.exists("/etc/ssl/cert.pem") \
    else ssl.create_default_context()
LABELS = ["minimal", "mild", "moderate", "restricted"]


def I(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def wcsv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "rows ->", os.path.relpath(path, ROOT))


def population(share_16_17=None, share_5_8=None):
    """Derive the age mix of ALL daily users from what Roblox states about age-checked users.

    Let x = share of DAU under 18, p18 = age-check penetration among adults.
      checked share of DAU:   0.60*x + p18*(1-x) = 0.57
      adults among checked:   p18*(1-x) / 0.57   = 0.27
    => p18*(1-x) = 0.1539, x = (0.57-0.1539)/0.60 = 0.6935, p18 = 0.502
    """
    A = REF["assumptions"]
    s1617 = A["share_16_17_within_13_17"]["value"] if share_16_17 is None else share_16_17
    s58 = A["share_5_8_within_under_13"]["value"] if share_5_8 is None else share_5_8
    checked = REF["age_checked_share_of_dau"]["value"]
    mix = REF["age_checked_mix"]["value"]
    pu18 = REF["u18_age_check_penetration"]["value"]["global"]
    adults_checked = mix["18_plus"] * checked
    x = (checked - adults_checked) / pu18
    p18 = adults_checked / (1 - x)
    u13 = x * mix["under_13"] / (mix["under_13"] + mix["13_17"])
    t1317 = x - u13
    bands = [("5-8", u13 * s58, pu18), ("9-12", u13 * (1 - s58), pu18), ("13-15", t1317 * (1 - s1617), pu18),
             ("16-17", t1317 * s1617, pu18), ("18+", 1 - x, p18)]
    return x, p18, bands


def main():
    A = REF["assumptions"]
    ratio18 = A["monetisation_ratio_18plus_applies_globally"]["value"]
    dev = REF["devex_usd_per_robux"]["value"]
    prem = dev["us_18plus_eligible"] / dev["standard"]
    x, p18, bands = population()

    # ---------------------------------------------------------------- segments
    seg = []
    for name, share, pen in bands:
        adult = name == "18+"
        if name == "5-8":
            tier, content, chat = "Roblox Kids", "Minimal, Mild", "off by default"
        elif name in ("9-12", "13-15"):
            tier, content, chat = "Roblox Select", "Minimal, Mild, Moderate", "off until age-checked, then gradual"
        else:
            tier = "Roblox (if age-checked) / Roblox Select (if not)"
            content, chat = "Minimal, Mild, Moderate" + (" (+Restricted if checked)" if adult else ""), \
                "on by default if age-checked"
        seg.append(dict(
            age_band=name, share_of_dau=round(share, 4), age_check_penetration=round(pen, 3),
            share_of_dau_age_checked=round(share * pen, 4), account_tier=tier, content_allowed=content, chat=chat,
            reachable_in_16plus_trial_phase=round(share * pen, 4) if name in ("16-17", "18+") else 0.0,
            relative_spend_per_user=ratio18 if adult else 1.0,
            devex_usd_per_robux=dev["standard"],
            relative_creator_value_per_user=ratio18 if adult else 1.0,
            relative_creator_value_if_us_18plus_eligible=round(ratio18 * prem, 2) if adult else "",
            basis="share: derived + assumed split" if name != "18+" else "share: derived"))
    wcsv(D("age_segments.csv"), seg)

    # ------------------------------------------------- reach of one game by label and stage
    kids = bands[0][1]
    std = sum(s * p for n, s, p in bands if n in ("16-17", "18+"))            # age-checked 16+
    adults_checked = bands[4][1] * bands[4][2]
    select = 1 - kids - std

    def value(parts):                       # parts: list of (share_of_dau, relative spend)
        return sum(s * v for s, v in parts)

    tot_value = value([(s, ratio18 if n == "18+" else 1.0) for n, s, _ in bands])
    v_std = value([(bands[3][1] * bands[3][2], 1.0), (adults_checked, ratio18)])
    v_kids = kids * 1.0
    v_select = tot_value - v_std - v_kids
    reach = [
        dict(stage="trial phase (before 250 highly engaged plays)", label="any (not Restricted)",
             share_of_dau=round(std, 4), share_of_spending_power=round(v_std / tot_value, 4),
             who="age-checked 16+ only"),
        dict(stage="eligible for Kids and Select", label="Minimal or Mild",
             share_of_dau=1.0, share_of_spending_power=1.0, who="everyone"),
        dict(stage="eligible for Kids and Select", label="Moderate",
             share_of_dau=round(1 - kids, 4), share_of_spending_power=round(1 - v_kids / tot_value, 4),
             who="everyone except Roblox Kids (5-8)"),
        dict(stage="any", label="Restricted", share_of_dau=round(adults_checked, 4),
             share_of_spending_power=round(adults_checked * ratio18 / tot_value, 4), who="age-checked 18+ only"),
    ]
    wcsv(D("age_reach_by_label.csv"), reach)
    lo = population(share_16_17=A["share_16_17_within_13_17"]["range"][0])[2]
    hi = population(share_16_17=A["share_16_17_within_13_17"]["range"][1])[2]
    std_lo = sum(s * p for n, s, p in lo if n in ("16-17", "18+"))
    std_hi = sum(s * p for n, s, p in hi if n in ("16-17", "18+"))

    # --------------------------------------------------------------- maturity of the market
    mat = {}
    if os.path.exists(D("roblox_maturity.csv")):
        mat = {r["universe_id"]: (r["content_maturity"] or "").lower() or "unrated"
               for r in csv.DictReader(open(D("roblox_maturity.csv"), encoding="utf-8"))}
    ch = list(csv.DictReader(open(D("roblox_charts.csv"), encoding="utf-8")))
    today = datetime.date.fromisoformat(ch[0]["snapshot_utc"][:10])
    uniq = {r["universe_id"]: r for r in ch}
    te = [r for r in ch if r["query"] == "top-earning"]
    m = collections.defaultdict(lambda: collections.Counter())
    for r in uniq.values():
        lab = mat.get(r["universe_id"], "unknown")
        m[lab]["chart_games"] += 1
        m[lab]["chart_ccu"] += I(r["playing"])
    for r in te:
        lab = mat.get(r["universe_id"], "unknown")
        m[lab]["top_earning"] += 1
        try:
            if (today - datetime.date.fromisoformat(r["created"])).days <= 365:
                m[lab]["top_earning_new_12m"] += 1
        except Exception:
            pass
    tot = collections.Counter()
    for c in m.values():
        tot.update(c)
    market = []
    for lab in LABELS + sorted(k for k in m if k not in LABELS):
        c = m.get(lab)
        if not c:
            continue
        market.append(dict(label=lab, chart_games=c["chart_games"], chart_games_share=round(c["chart_games"] / tot["chart_games"], 4),
                           chart_ccu=c["chart_ccu"], chart_ccu_share=round(c["chart_ccu"] / tot["chart_ccu"], 4),
                           top_earning=c["top_earning"], top_earning_share=round(c["top_earning"] / max(1, tot["top_earning"]), 4),
                           top_earning_new_12m=c["top_earning_new_12m"],
                           top_earning_new_12m_share=round(c["top_earning_new_12m"] / max(1, tot["top_earning_new_12m"]), 4)))
    if market:
        wcsv(D("maturity_market.csv"), market)

    # ------------------------------------------------------------- maturity by archetype
    arch = {a["id"]: a for a in json.load(open(D("archetypes.json"), encoding="utf-8"))}
    by = collections.defaultdict(list)
    for r in csv.DictReader(open(D("roblox_competitors.csv"), encoding="utf-8")):
        by[r["archetype"]].append(r)
    rows = []
    for aid, lst in by.items():
        if arch.get(aid, {}).get("origin") != "web":
            continue
        cnt, ccu = collections.Counter(), collections.Counter()
        for r in lst:
            lab = mat.get(r["universe_id"], "unknown")
            cnt[lab] += 1
            ccu[lab] += I(r["ccu"])
        n, c = sum(cnt.values()), sum(ccu.values())
        known = n - cnt["unknown"]
        row = dict(archetype=aid, zh=arch[aid]["zh"], n_direct=n, n_with_label=known, ccu_direct=c)
        for lab in LABELS:
            row[f"games_{lab}"] = cnt[lab]
            row[f"ccu_share_{lab}"] = round(ccu[lab] / c, 4) if c else 0
        row["ccu_share_open_to_kids_5_8"] = round((ccu["minimal"] + ccu["mild"]) / c, 4) if c else 0
        rows.append(row)
    rows.sort(key=lambda r: -r["ccu_direct"])
    if rows:
        wcsv(D("maturity_by_archetype.csv"), rows)

    # ------------------------------------------------------------------- Scratch ages
    sc = []
    try:
        req = urllib.request.Request("https://scratch.mit.edu/statistics/data/monthly/", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            d = json.loads(r.read())
        vals = d["age_distribution_data"][0]["values"]
        tot_s = sum(v["y"] for v in vals)
        sc = [dict(age=v["x"], registered_users=v["y"], share=round(v["y"] / tot_s, 5)) for v in vals]
        wcsv(D("scratch_age_distribution.csv"), sc)
    except Exception as e:  # keep the last saved copy if Scratch is unreachable
        print("scratch fetch failed:", repr(e)[:80])
        if os.path.exists(D("scratch_age_distribution.csv")):
            sc = [dict(age=I(r["age"]), registered_users=I(r["registered_users"]), share=float(r["share"]))
                  for r in csv.DictReader(open(D("scratch_age_distribution.csv"), encoding="utf-8"))]
    scratch_bands = {}
    if sc:
        def band(lo_, hi_):
            return round(sum(r["share"] for r in sc if lo_ <= r["age"] <= hi_), 4)
        scratch_bands = {"<=8": band(0, 8), "9-12": band(9, 12), "13-15": band(13, 15), "16-17": band(16, 17),
                         "18+": band(18, 200), "mode_age": max(sc, key=lambda r: r["registered_users"])["age"]}

    summary = dict(
        derived_share_of_dau_under_18=round(x, 4), derived_age_check_penetration_18plus=round(p18, 3),
        share_of_dau_by_band={n: round(s, 4) for n, s, _ in bands},
        tiers_share_of_dau=dict(kids=round(kids, 4), select=round(select, 4), standard_16plus_checked=round(std, 4)),
        trial_phase_reach_share_of_dau=round(std, 4), trial_phase_reach_range=[round(std_lo, 4), round(std_hi, 4)],
        trial_phase_share_of_spending_power=round(v_std / tot_value, 4),
        spending_power_by_tier=dict(kids=round(v_kids / tot_value, 4), select=round(v_select / tot_value, 4),
                                    standard=round(v_std / tot_value, 4)),
        us18_devex_premium=round(prem - 1, 3), creator_value_us18_vs_u18=round(ratio18 * prem, 2),
        scratch_signup_age=scratch_bands,
        maturity_labels_known=sum(1 for v in mat.values() if v in LABELS), maturity_rows=len(mat))
    json.dump(summary, open(O("age_summary.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
