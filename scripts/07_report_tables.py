#!/usr/bin/env python3
"""Regenerate the markdown tables used in REPORT.md from the CSV outputs -> out/report_tables.md"""
import csv, json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, "data", *p)
O = lambda *p: os.path.join(ROOT, "out", *p)


def rd(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def f(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def main():
    out = []
    rank = rd(O("ranking.csv"))
    dem = {r["archetype"]: r for r in rd(D("archetype_demand.csv"))}
    comp = {r["archetype"]: r for r in rd(D("archetype_competition.csv"))}
    arch = {a["id"]: a for a in json.load(open(D("archetypes.json"), encoding="utf-8"))}
    el = [r for r in rank if r["eligible"] == "yes"]

    out.append("## Top 10 (eligible), base case\n")
    out.append("| # | 玩法原型 | P(起量) [5%–95%] | 起量后首年收入中位数 | 到数据关口工时 | 期望总工时(分阶段) | 每小时净值 均值 [5%, 50%, 95%] | 胜过$20/h的世界占比 | 风险调整价值 V(分阶段 / 一次性投入) | P(排第1) | 证据桶 (网页/Roblox/拥挤/头部) |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(el[:10], 1):
        out.append(f"| {i} | {r['zh']} `{r['archetype']}` | {f(r['p_traction_mean'])*100:.1f}% [{f(r['p_traction_p05'])*100:.1f}–{f(r['p_traction_p95'])*100:.1f}] | "
                   f"${int(f(r['rev_if_traction_median'])):,} | {f(r['hours_to_metrics_gate']):.0f} h | {f(r['E_hours_staged']):.0f} h | "
                   f"${f(r['net_usd_per_hour_mean']):.0f} [{f(r['net_usd_per_hour_p05']):.0f}, {f(r['net_usd_per_hour_p50']):.0f}, {f(r['net_usd_per_hour_p95']):.0f}] | "
                   f"{f(r['p_worlds_beating_wage'])*100:.0f}% | ${int(f(r['V_risk_adj_staged'])):,} / ${int(f(r['V_risk_adj_commit'])):,} | {f(r['p_rank1'])*100:.0f}% | "
                   f"{r['bucket_web']} / {r['bucket_rbx']} / {r['bucket_crowd']} / {r['bucket_leaders']} |")

    out.append("\n## All modelled archetypes\n")
    out.append("| 原型 | 可选? | 网页份额% | 品牌依赖 | 动量 | Roblox直接竞品CCU | ≥1k CCU竞品数 | 近12月起量新品 | 坟场 | Roblox证据 | P(起量) | $/h 均值 | 淘汰原因 |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rank:
        c = comp.get(r["archetype"], {})
        out.append(f"| {r['zh']} | {r['eligible']} | {r['web_share_pct']} | {r['brand_dependence']} | {r['momentum']} | "
                   f"{int(f(r['roblox_ccu_direct'])):,} | {r['roblox_n_ccu_1000']} | {r['roblox_new_traction_12m']} | {r['roblox_graveyard']} | "
                   f"{r['bucket_rbx']} | {f(r['p_traction_mean'])*100:.1f}% | {f(r['net_usd_per_hour_mean']):.1f} | {r['screen_fail']} |")

    out.append("\n## Roblox competition (web-origin archetypes)\n")
    out.append("| 原型 | 直接竞品数 | CCU合计 | ≥100 | ≥1k | 近12月≥5M访问的新品 | 坟场(≥1M访问且<20 CCU) | 头部好评率 | 头部距上次更新(天) | 头部5款 |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    for aid, c in sorted(comp.items(), key=lambda kv: -f(kv[1]["ccu_direct"])):
        if arch.get(aid, {}).get("origin") != "web":
            continue
        out.append(f"| {c['zh']} | {c['n_direct']} | {int(f(c['ccu_direct'])):,} | {c['n_ccu_100']} | {c['n_ccu_1000']} | {c['new_traction_12m']} | "
                   f"{c['graveyard_1m_visits_dead']} | {c['top5_like_ratio']} | {c['top5_days_since_update']} | {c['top5'][:230]} |")

    out.append("\n## Sensitivity (net $ per hour; * = best in scenario)\n")
    sens = rd(O("sensitivity.csv"))
    sc = collections.OrderedDict()
    for x in sens:
        sc.setdefault(x["scenario"], []).append(x)
    names = [x["archetype"] for x in next(iter(sc.values()))]
    out.append("| 情景 | " + " | ".join(names) + " |")
    out.append("|---|" + "---|" * len(names))
    out.append("| 基准 | " + " | ".join(f"{f(x['base_net_usd_per_hour']):.1f}" for x in next(iter(sc.values()))) + " |")
    for k, v in sc.items():
        out.append(f"| {k} | " + " | ".join(f"{f(x['net_usd_per_hour']):.1f}{'*' if x['is_best_in_scenario'] else ''}" for x in v) + " |")
    out.append("\n### Risk-adjusted V by scenario\n")
    out.append("| 情景 | " + " | ".join(names) + " |")
    out.append("|---|" + "---|" * len(names))
    out.append("| 基准 | " + " | ".join(f"{int(f(x['base_V'])):,}" for x in next(iter(sc.values()))) + " |")
    for k, v in sc.items():
        out.append(f"| {k} | " + " | ".join(f"{int(f(x['V_risk_adj'])):,}" for x in v) + " |")

    out.append("\n## Programme view\n")
    out.append("| 工时预算 | 候选数 | 实际启动项目 | 用掉工时 | 现金 | P(≥1个起量) | 收入均值 | 收入中位数 | 收入P90 | 收入P99 | 按$20/h计利润均值 | 利润中位数 | P(利润>0) | P(收回现金) |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for p in rd(O("programme.csv")):
        out.append(f"| {p['hour_budget']} | {p['top_k']} | {p['projects_started_mean']} | {p['hours_used_mean']} | ${p['cash_mean']} | "
                   f"{f(p['p_at_least_one_traction'])*100:.1f}% | ${int(f(p['revenue_mean'])):,} | ${int(f(p['revenue_p50'])):,} | ${int(f(p['revenue_p90'])):,} | "
                   f"${int(f(p['revenue_p99'])):,} | ${int(f(p['profit_at_wage_mean'])):,} | ${int(f(p['profit_at_wage_p50'])):,} | "
                   f"{f(p['p_profit_gt0'])*100:.1f}% | {f(p['p_cash_recovered'])*100:.1f}% |")

    out.append("\n## Web demand by archetype\n")
    out.append("| 原型 | 来源 | 游戏数 | 网页注意力份额% | 历史份额% | 当前份额% | 动量 | 广度(信号数) | 品牌依赖 | Scratch浏览量 | 代表作 |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rd(D("archetype_demand.csv")):
        out.append(f"| {r['zh']} | {r['origin']} | {r['n_games']} | {r['web_share_pct']} | {r['alltime_share_pct']} | {r['current_share_pct']} | "
                   f"{r['momentum']} | {r['breadth_signals']} | {r['brand_dependence']} | {int(f(r['scratch_views_max'])):,} | {r['top_titles'][:90]} |")

    open(O("report_tables.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("wrote", O("report_tables.md"), len(out), "lines")


if __name__ == "__main__":
    main()
