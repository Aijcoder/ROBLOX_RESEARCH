#!/usr/bin/env python3
"""Stages 5-8 — risk-adjusted opportunity model.

    V_i = E[R_i - C_i] - lambda * E[max(0, C_i - R_i)]          (expected profit minus expected loss)

Structure (kept deliberately simple; every parameter is in data/model_params.json with its provenance):

  1. P(traction_i)  — Bayesian update in odds form.  prior odds x LR_web x LR_roblox x LR_competition x LR_fit
     "traction" = averaging >= 100 concurrent players over the first 12 months.
     The prior and the LR *ranges* are assumptions; which LR bucket an archetype falls in is decided by
     measured data (web share, Roblox CCU of direct competitors, new entrants, graveyard, like ratio).
  2. Size given traction — Pareto tail, exponent from the observed Roblox CCU distribution, capped.
  3. Revenue = CCU-hours x (platform DevEx $ per engaged hour) x small-game discount x genre index.
  4. Cost = hours (three-point estimate x overrun) x opportunity wage + cash for the paid test.
  5. Staged policy: prototype -> fun gate -> MVP + paid soft launch -> metrics gate -> launch build.
     Gates are imperfect tests (sensitivity/specificity); value of information = V(staged) - V(commit).

Two-level Monte Carlo: outer loop = "worlds" (parameter uncertainty, shared by all archetypes so that
rankings are compared inside the same world); inner loop = outcome uncertainty.

Outputs: out/ranking.csv, out/sensitivity.csv, out/model_summary.json
"""
import csv, json, os, sys, math, zlib
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, "data", *p)
O = lambda *p: os.path.join(ROOT, "out", *p)
os.makedirs(O(), exist_ok=True)

P = json.load(open(D("model_params.json"), encoding="utf-8"))
ARCH = json.load(open(D("archetypes.json"), encoding="utf-8"))


def val(name):
    return P[name]["value"]


def load(path, key):
    return {r[key]: r for r in csv.DictReader(open(path, encoding="utf-8"))}


def F(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


DEM = load(D("archetype_demand.csv"), "archetype")
COMP = load(D("archetype_competition.csv"), "archetype")
GEN = {(r["level"], r["genre"]): r for r in csv.DictReader(open(D("roblox_genre_stats.csv"), encoding="utf-8"))}


def genre_index(a):
    """Earnings-per-CCU index of the Roblox genre the archetype's direct competitors sit in.
    Robust proxy: median over top earners of (1/earning-rank)/CCU, relative to the all-genre median.
    Sub-genre (L2) is used only when >= `genre_l2_min_n` top earners carry it, else the parent genre (L1);
    the result is shrunk toward 1 and clipped, because it is a rank-based proxy and not revenue."""
    c = COMP.get(a["id"], {})
    cands = []
    if F(c.get("ccu_direct")) >= 100:
        cands = [("genre_l2", c.get("observed_genre_l2")), ("genre_l1", c.get("observed_genre_l1"))]
    cands += [("genre_l2", a["rbx_genre"]), ("genre_l1", a["rbx_genre"])]
    for level, label in cands:
        r = GEN.get((level, label)) if label else None
        if not r or r["earn_per_ccu_index_robust"] == "":
            continue
        n = F(r["top_earning_n"])
        if level == "genre_l2" and n < val("genre_l2_min_n"):
            continue
        if n < 1:
            continue
        k = val("genre_index_shrink_n")
        lo, hi = val("genre_index_clip")
        return float(np.clip((n * F(r["earn_per_ccu_index_robust"]) + k) / (n + k), lo, hi)), int(n), label
    return val("genre_index_absent"), 0, a["rbx_genre"]


# ------------------------------------------------------------------ evidence -> LR buckets (data-driven)
web_elig = [a for a in ARCH if a["origin"] == "web"]
shares = sorted(F(DEM.get(a["id"], {}).get("web_share_pct")) for a in web_elig)
t1, t2 = np.percentile(shares, [33.3, 66.7])


def buckets(a):
    d, c, s = DEM.get(a["id"], {}), COMP.get(a["id"], {}), a["screens"]
    b = {}
    share = F(d.get("web_share_pct"))
    b["web"] = "high" if share >= t2 else ("mid" if share >= t1 else "low")
    b["brand"] = "brand" if F(d.get("brand_dependence")) >= val("brand_dependence_cut") else "genre"
    mom = d.get("momentum", "")
    b["momentum"] = "fading" if (mom != "" and F(mom) < 0.25) else ("rising" if (mom != "" and F(mom) >= 1.0) else "flat")
    ccu, new, grave, att = F(c.get("ccu_direct")), F(c.get("new_hits_12m")), F(c.get("graveyard_1m_visits_dead")), \
        F(c.get("n_attempts_10k_visits"))
    newtr = F(c.get("new_traction_12m"))
    if newtr >= 3 and ccu >= 5000:
        b["rbx"] = "proven_open"          # big live demand AND several entrants of the last year got traction
    elif newtr >= 1 and ccu >= 500:
        b["rbx"] = "live_open"
    elif ccu >= 1000:
        b["rbx"] = "live_entrenched"      # demand exists but nobody new has broken in for a year
    elif att < 2:
        b["rbx"] = "untested"             # nobody really tried -> genuinely unknown
    elif grave >= 2 and ccu < 500:
        b["rbx"] = "tried_and_died"       # several got >=1M visits and are empty now -> not a gap, a grave
    elif ccu >= 100:
        b["rbx"] = "thin"
    else:
        b["rbx"] = "weak_attempts"
    n1k = F(c.get("n_ccu_1000"))
    b["crowd"] = "crowded" if n1k >= 8 else ("contested" if n1k >= 3 else ("few" if n1k >= 1 else "none"))
    like, stale = F(c.get("top5_like_ratio")), F(c.get("top5_days_since_update"))
    if ccu < 100:
        b["leaders"] = "na"
    elif like >= 0.90 and stale <= 30:
        b["leaders"] = "strong"
    elif like < 0.75 or stale > 180:
        b["leaders"] = "weak"
    else:
        b["leaders"] = "ok"
    b["fit"] = [k for k, bad in (("solo", not s["solo_ok"]), ("s10", not s["s10"]), ("rep", not s["rep"]),
                                 ("grief", s["grief"] == "med"), ("touch", not s["touch"])) if bad]
    return b


def screen_fail(a):
    s, out = a["screens"], []
    if a["origin"] != "web":
        out.append("not web-native (reverse flow / MMO)")
    if not s["aud"]:
        out.append("audience mismatch")
    if s["grief"] == "high":
        out.append("griefing/moderation")
    if a["mvp_h"][1] > val("max_mvp_hours_solo"):
        out.append(f"MVP > {val('max_mvp_hours_solo')} h")
    if not s["s5"]:
        out.append("not graspable in 5 s")
    return out


def tri(rng, lo, mode, hi, size):
    return rng.triangular(lo, mode, hi, size) if hi > lo else np.full(size, float(mode))


def lr_draw(rng, name, key, n):
    lo, hi = P["likelihood_ratios"][name][key]
    return np.exp(rng.uniform(math.log(lo), math.log(hi), n))


def simulate(a, W, overrides=None, seed=7):
    """W = dict of world-level parameter arrays (n_world,). Returns per-world summary arrays."""
    ov = overrides or {}
    rng = np.random.default_rng(seed + zlib.crc32(a["id"].encode()) % 10_000)   # stable across runs
    nW, nI = len(W["p0_odds"]), int(val("inner_draws"))
    b = buckets(a)
    lr = lr_draw(rng, "web", b["web"], nW) * lr_draw(rng, "brand", b["brand"], nW) * \
        lr_draw(rng, "momentum", b["momentum"], nW) * lr_draw(rng, "rbx", b["rbx"], nW) * \
        lr_draw(rng, "crowd", b["crowd"], nW) * lr_draw(rng, "leaders", b["leaders"], nW)
    for f in b["fit"]:
        lr = lr * lr_draw(rng, "fit", f, nW)
    if ov.get("no_lr"):
        lr = np.ones(nW)
    odds = W["p0_odds"] * lr
    p = np.minimum(odds / (1 + odds), val("p_traction_cap"))                      # (nW,)

    gi, gi_n, gi_label = genre_index(a)
    gm = (1.0 if ov.get("no_genre") else gi) * np.exp(rng.normal(0, val("genre_index_sigma"), nW))
    usd_h = W["usd_per_hour"] * W["small_game_mult"] * gm                          # (nW,)

    o, m, pe = a["mvp_h"]
    scale = ov.get("cost_mult", 1.0)
    mvp = tri(rng, o, m, pe, (nW, nI)) * np.exp(rng.normal(math.log(val("overrun_median")), val("overrun_sigma"),
                                                           (nW, nI))) * scale
    launch = a["launch_h"] * np.exp(rng.normal(math.log(val("overrun_median")), val("overrun_sigma"), (nW, nI))) * scale
    cash_test = tri(rng, *val("cash_test_usd"), (nW, nI))

    trac = rng.random((nW, nI)) < p[:, None]
    u = rng.random((nW, nI))
    thr, cap = val("traction_ccu"), ov.get("ccu_cap", val("ccu_cap"))
    y_hit = np.minimum(thr * u ** (-1.0 / W["alpha"][:, None]), cap)
    y_miss = np.minimum(np.exp(rng.normal(math.log(val("fail_ccu_median")), val("fail_ccu_sigma"), (nW, nI))), thr * 0.6)
    y = np.where(trac, y_hit, y_miss)
    tail = np.where(trac, W["tail_mult"][:, None], 1.0)
    rev_full = y * 8760.0 * usd_h[:, None] * tail * ov.get("rev_mult", 1.0)
    up_months = np.where(trac, 12.0, val("upkeep_months_if_fail"))
    upkeep = a["upkeep_h"] * up_months * np.where(trac, 1 + np.log10(np.maximum(y, thr) / thr), 1.0) * scale

    wage = W["wage"][:, None]
    # ---- policy A: commit (build everything, launch, see what happens)
    h_commit = mvp + launch + upkeep
    prof_commit = rev_full - cash_test - wage * h_commit

    # ---- policy B: staged with two imperfect gates
    g = P["gates"]["value"]
    passA = rng.random((nW, nI)) < np.where(trac, g["A_pass_if_traction"], g["A_pass_if_not"])
    passB = rng.random((nW, nI)) < np.where(trac, g["B_pass_if_traction"], g["B_pass_if_not"])
    hA = mvp * g["proto_fraction"]
    hB = mvp * (1 - g["proto_fraction"])
    reachB = passA
    reachC = passA & passB
    h_staged = hA + np.where(reachB, hB, 0) + np.where(reachC, launch + upkeep, 0)
    cash_staged = np.where(reachB, cash_test, 0)
    # a killed MVP is left published: it still earns whatever a non-launched build earns (negligible) -> 0
    rev_staged = np.where(reachC, rev_full, 0.0)
    prof_staged = rev_staged - cash_staged - wage * h_staged

    lam = val("lambda_risk")

    def V(x):
        return x.mean(axis=1) - lam * np.maximum(-x, 0).mean(axis=1)

    killA, killB = ~passA, passA & ~passB
    outcomes = dict(
        p_kill_gate_A=float(killA.mean()), p_kill_gate_B=float(killB.mean()),
        p_launch_no_traction=float((reachC & ~trac).mean()),
        p_traction_100_to_1000=float((reachC & trac & (y < 1000)).mean()),
        p_traction_1000_plus=float((reachC & trac & (y >= 1000)).mean()),
        p_traction_but_killed=float((trac & ~reachC).mean()),
        hours_if_kill_A=float(hA[killA].mean()), hours_if_kill_B=float((hA + hB)[killB].mean()),
        hours_if_launch_no_traction=float(h_staged[reachC & ~trac].mean()) if (reachC & ~trac).any() else 0.0,
        rev_median_traction_100_to_1000=float(np.median(rev_full[reachC & trac & (y < 1000)]))
        if (reachC & trac & (y < 1000)).any() else 0.0,
        rev_median_traction_1000_plus=float(np.median(rev_full[reachC & trac & (y >= 1000)]))
        if (reachC & trac & (y >= 1000)).any() else 0.0)
    return dict(
        outcomes=outcomes,
        buckets=b, genre_index=gi, genre_n=gi_n, genre_label=gi_label, p=p,
        samp=dict(h=h_staged[:, :150], rev=rev_staged[:, :150], cash=cash_staged[:, :150],
                  hit=(reachC & trac)[:, :150]),
        V_staged=V(prof_staged), V_commit=V(prof_commit),
        E_profit_staged=prof_staged.mean(axis=1), E_rev_staged=rev_staged.mean(axis=1),
        E_hours_staged=h_staged.mean(axis=1), E_cash_staged=cash_staged.mean(axis=1),
        E_hours_commit=h_commit.mean(axis=1),
        p_profit=(prof_staged > 0).mean(axis=1), p_rev10k=(rev_staged >= 10_000).mean(axis=1),
        p_reachC=reachC.mean(axis=1),
        rev_if_traction=np.array([np.median(rev_full[i][trac[i]]) if trac[i].any() else np.nan for i in range(nW)]),
        prof_pool=prof_staged.ravel()[:: max(1, (nW * nI) // 200_000)],
        hours_to_gateB=(hA + np.where(reachB, hB, 0)).mean(axis=1),
    )


def worlds(n, rng, fix=None):
    fix = fix or {}

    def ln(name):
        v = P[name]["value"]
        return np.exp(rng.normal(math.log(v["median"]), v["sigma"], n))

    W = dict(
        p0_odds=ln("prior_traction_odds"),
        usd_per_hour=np.full(n, val("usd_per_engaged_hour_platform")),
        small_game_mult=ln("small_game_monetisation_mult"),
        alpha=rng.uniform(*val("pareto_alpha"), n),
        tail_mult=rng.uniform(*val("tail_value_mult"), n),
        wage=np.full(n, float(val("opportunity_wage_usd_h"))),
    )
    for k, v in fix.items():
        W[k] = np.full(n, float(v))
    return W


def q(x, p):
    return float(np.nanpercentile(x, p))


def main():
    nW = int(val("outer_worlds"))
    W = worlds(nW, np.random.default_rng(11))
    res, rows = {}, []
    for a in ARCH:
        if a["origin"] != "web":
            continue
        r = simulate(a, W)
        res[a["id"]] = r
    ids = list(res)
    elig = [i for i in ids if not screen_fail(next(a for a in ARCH if a["id"] == i))]
    # rank stability across worlds (eligible only)
    Vmat = np.vstack([res[i]["V_staged"] for i in elig])                 # (n_arch, nW)
    Hmat = np.vstack([(res[i]["E_rev_staged"] - res[i]["E_cash_staged"]) / res[i]["E_hours_staged"] for i in elig])
    order = np.argsort(-Hmat, axis=0)
    rank1 = {elig[k]: float((order[0] == k).mean()) for k in range(len(elig))}
    top3 = {elig[k]: float((order[:3] == k).any(axis=0).mean()) for k in range(len(elig))}

    for a in ARCH:
        if a["id"] not in res:
            continue
        r, d, c = res[a["id"]], DEM.get(a["id"], {}), COMP.get(a["id"], {})
        sf = screen_fail(a)
        net_per_h = (r["E_rev_staged"] - r["E_cash_staged"]) / r["E_hours_staged"]
        rows.append(dict(
            archetype=a["id"], zh=a["zh"], eligible="yes" if not sf else "no", screen_fail="; ".join(sf),
            web_share_pct=d.get("web_share_pct", ""), brand_dependence=d.get("brand_dependence", ""),
            momentum=d.get("momentum", ""), roblox_ccu_direct=c.get("ccu_direct", ""),
            roblox_n_ccu_1000=c.get("n_ccu_1000", ""), roblox_new_traction_12m=c.get("new_traction_12m", ""),
            roblox_attempts=c.get("n_attempts_10k_visits", ""),
            roblox_graveyard=c.get("graveyard_1m_visits_dead", ""),
            bucket_web=r["buckets"]["web"], bucket_rbx=r["buckets"]["rbx"], bucket_crowd=r["buckets"]["crowd"],
            bucket_leaders=r["buckets"]["leaders"], fit_penalties=",".join(r["buckets"]["fit"]),
            genre=r["genre_label"], genre_index=round(r["genre_index"], 2), genre_top_earners=r["genre_n"],
            mvp_h_likely=a["mvp_h"][1], launch_h=a["launch_h"],
            p_traction_mean=round(float(r["p"].mean()), 4), p_traction_p05=round(q(r["p"], 5), 4),
            p_traction_p95=round(q(r["p"], 95), 4),
            rev_if_traction_median=round(q(r["rev_if_traction"], 50)),
            E_revenue=round(float(r["E_rev_staged"].mean())),
            E_hours_staged=round(float(r["E_hours_staged"].mean()), 1),
            hours_to_metrics_gate=round(float(r["hours_to_gateB"].mean()), 1),
            E_hours_commit=round(float(r["E_hours_commit"].mean()), 1),
            E_cash=round(float(r["E_cash_staged"].mean())),
            net_usd_per_hour_mean=round(float(net_per_h.mean()), 2),
            net_usd_per_hour_p05=round(q(net_per_h, 5), 2), net_usd_per_hour_p50=round(q(net_per_h, 50), 2),
            net_usd_per_hour_p95=round(q(net_per_h, 95), 2),
            p_worlds_beating_wage=round(float((net_per_h > W["wage"]).mean()), 3),
            E_profit_at_wage=round(float(r["E_profit_staged"].mean())),
            V_risk_adj_staged=round(float(r["V_staged"].mean())), V_risk_adj_commit=round(float(r["V_commit"].mean())),
            value_of_staging=round(float((r["V_staged"] - r["V_commit"]).mean())),
            p_profit_gt0=round(float(r["p_profit"].mean()), 4), p_rev_ge_10k=round(float(r["p_rev10k"].mean()), 4),
            profit_p05=round(q(r["prof_pool"], 5)), profit_p50=round(q(r["prof_pool"], 50)),
            profit_p95=round(q(r["prof_pool"], 95)), profit_p99=round(q(r["prof_pool"], 99)),
            p_rank1=round(rank1.get(a["id"], 0), 3), p_top3=round(top3.get(a["id"], 0), 3)))
    rows.sort(key=lambda r: (r["eligible"] != "yes", -r["net_usd_per_hour_mean"]))
    with open(O("ranking.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    with open(O("outcomes.csv"), "w", newline="", encoding="utf-8") as f:
        keys = list(next(iter(res.values()))["outcomes"].keys())
        w = csv.writer(f)
        w.writerow(["archetype"] + keys)
        for i in ids:
            w.writerow([i] + [round(res[i]["outcomes"][k], 5) for k in keys])

    # evidence check: does web demand predict Roblox live demand for the same mechanic?
    xs = [F(DEM.get(i, {}).get("web_share_pct")) for i in ids]
    ys = [F(COMP.get(i, {}).get("ccu_direct")) for i in ids]

    def rank(v):
        o = np.argsort(v)
        r = np.empty(len(v))
        r[o] = np.arange(len(v))
        return r

    rho = float(np.corrcoef(rank(xs), rank(ys))[0, 1])

    # ------------------------------------------------------------------ sensitivity on the top eligible
    top = [r["archetype"] for r in rows if r["eligible"] == "yes"][:8]
    sens = []
    base = {t: next(r for r in rows if r["archetype"] == t)["net_usd_per_hour_mean"] for t in top}
    baseV = {t: next(r for r in rows if r["archetype"] == t)["V_risk_adj_staged"] for t in top}
    scen = [
        ("prior P(traction) low (1%)", dict(fix=dict(p0_odds=0.0101))),
        ("prior P(traction) high (8%)", dict(fix=dict(p0_odds=0.087))),
        ("small-game $ mult low (0.15)", dict(fix=dict(small_game_mult=0.15))),
        ("small-game $ mult high (1.0)", dict(fix=dict(small_game_mult=1.0))),
        ("Pareto alpha heavy tail (0.8)", dict(fix=dict(alpha=0.8))),
        ("Pareto alpha thin tail (1.3)", dict(fix=dict(alpha=1.3))),
        ("hit size capped at 2,000 CCU", dict(ov=dict(ccu_cap=2000))),
        ("costs x1.5", dict(ov=dict(cost_mult=1.5))),
        ("costs x0.7", dict(ov=dict(cost_mult=0.7))),
        ("wage $0/h", dict(fix=dict(wage=0))),
        ("wage $40/h", dict(fix=dict(wage=40))),
        ("ignore all evidence LRs", dict(ov=dict(no_lr=True))),
        ("genre monetisation index off (=1 for all)", dict(ov=dict(no_genre=True))),
        ("age gate: never unlocks under-16 audience", dict(ov=dict(rev_mult=val("age_gate_16plus_value_share")))),
        ("US 18+ DevEx premium on 20% of spend", dict(ov=dict(rev_mult=1 + val("us18_devex_premium") * val("us18_spend_share_scenario")))),
    ]
    for name, s in scen:
        Ws = worlds(max(200, nW // 2), np.random.default_rng(11), s.get("fix"))
        vals = {}
        for t in top:
            a = next(x for x in ARCH if x["id"] == t)
            r = simulate(a, Ws, s.get("ov"))
            vals[t] = (float(((r["E_rev_staged"] - r["E_cash_staged"]) / r["E_hours_staged"]).mean()),
                       float(r["V_staged"].mean()))
        best = max(vals, key=lambda t: vals[t][0])
        for t in top:
            sens.append(dict(scenario=name, archetype=t, net_usd_per_hour=round(vals[t][0], 2),
                             base_net_usd_per_hour=base[t], V_risk_adj=round(vals[t][1]), base_V=baseV[t],
                             is_best_in_scenario="yes" if t == best else ""))
    with open(O("sensitivity.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(sens[0].keys()))
        w.writeheader()
        w.writerows(sens)

    # ------------------------------------------------------------------ programme view (several cheap bets)
    # Run the staged process on the top-K eligible archetypes in order until an hour budget is used up.
    order_ids = [r["archetype"] for r in rows if r["eligible"] == "yes"]
    prog = []
    for H in val("programme_hour_budgets"):
        for K in (1, 3, 6):
            ids_k = order_ids[:K]
            used = np.zeros_like(res[ids_k[0]]["samp"]["h"])
            rev = np.zeros_like(used)
            cash = np.zeros_like(used)
            hits = np.zeros_like(used)
            started = np.zeros_like(used)
            for i in ids_k:
                sp = res[i]["samp"]
                go = used < H                                   # start the next project only if hours remain
                used = used + np.where(go, sp["h"], 0)
                rev = rev + np.where(go, sp["rev"], 0)
                cash = cash + np.where(go, sp["cash"], 0)
                hits = hits + np.where(go, sp["hit"], 0)
                started = started + go
            wage = float(val("opportunity_wage_usd_h"))
            prof = rev - cash - wage * used
            prog.append(dict(hour_budget=H, top_k=K, projects_started_mean=round(float(started.mean()), 2),
                             hours_used_mean=round(float(used.mean())), cash_mean=round(float(cash.mean())),
                             p_at_least_one_traction=round(float((hits > 0).mean()), 3),
                             revenue_mean=round(float(rev.mean())), revenue_p50=round(q(rev, 50)),
                             revenue_p90=round(q(rev, 90)), revenue_p99=round(q(rev, 99)),
                             profit_at_wage_mean=round(float(prof.mean())), profit_at_wage_p50=round(q(prof, 50)),
                             p_profit_gt0=round(float((prof > 0).mean()), 3),
                             p_cash_recovered=round(float((rev > cash).mean()), 3)))
    with open(O("programme.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(prog[0].keys()))
        w.writeheader()
        w.writerows(prog)

    summary = dict(n_worlds=nW, inner=int(val("inner_draws")), web_share_terciles=[float(t1), float(t2)],
                   spearman_web_share_vs_roblox_ccu=round(rho, 3), n_archetypes_modelled=len(ids),
                   n_eligible=len(elig), top6=top)
    json.dump(summary, open(O("model_summary.json"), "w"), indent=1)
    print(json.dumps(summary, ensure_ascii=False))
    for pr in prog:
        print("programme", pr)
    hdr = f"{'archetype':24s} el  P(tr)  [p05-p95]   rev|tr   E[rev]  E[h]  $/h mean [p05,p50,p95]      V_stg  V_cmt  P(>0) P#1  rbx/crowd/leaders"
    print(hdr)
    for r in rows:
        print(f"{r['archetype']:24s} {r['eligible'][:1]}  {r['p_traction_mean']*100:4.1f}% [{r['p_traction_p05']*100:4.1f}-{r['p_traction_p95']*100:4.1f}] "
              f"{r['rev_if_traction_median']:>7,} {r['E_revenue']:>7,} {r['E_hours_staged']:5.0f} {r['net_usd_per_hour_mean']:6.2f} "
              f"[{r['net_usd_per_hour_p05']:5.2f},{r['net_usd_per_hour_p50']:5.2f},{r['net_usd_per_hour_p95']:6.2f}] "
              f"{r['V_risk_adj_staged']:>7,} {r['V_risk_adj_commit']:>7,} {r['p_profit_gt0']*100:4.1f}% {r['p_rank1']*100:3.0f}% bw={r['p_worlds_beating_wage']*100:3.0f}%  "
              f"{r['bucket_rbx']}/{r['bucket_crowd']}/{r['bucket_leaders']} gi={r['genre_index']} {r['screen_fail'][:30]}")


if __name__ == "__main__":
    main()
