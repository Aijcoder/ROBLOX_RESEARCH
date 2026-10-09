#!/usr/bin/env python3
"""Draw the report's charts from the CSV outputs -> out/charts/*.png

Run with the project environment:  .venv/bin/python scripts/08_charts.py

Conventions (static images, light surface):
  * one job per chart; the title states the finding, the subtitle says what is plotted
  * colour does one job: a single hue for one series, a one-hue ramp for ordered bands,
    blue + grey when one item is the point, blue/red only for above/below a baseline
  * the palettes below were checked with the dataviz validator (colour-blind separation, contrast)
  * values are labelled sparingly at bar ends; every number is also in the CSVs (the table view)
"""
import csv, json, os, datetime, collections, math, logging
import matplotlib
matplotlib.use("Agg")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch, Rectangle, BoxStyle
from matplotlib.transforms import IdentityTransform
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, PercentFormatter
from matplotlib import patheffects

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, "data", *p)
O = lambda *p: os.path.join(ROOT, "out", *p)
OUT = O("charts")
os.makedirs(OUT, exist_ok=True)

DPI = 200
SURFACE, INK, INK2, MUTED, GRID, BASE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, RED, GREY = "#2a78d6", "#eb6834", "#e34948", "#c3c2b7"
RAMP5 = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]      # ordinal, validated
RAMP4 = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
RAMP3 = ["#86b6ef", "#3987e5", "#0d366b"]
LIGHT, DARK = "#86b6ef", "#1c5cab"                                   # two shades of one hue (before/after)

plt.rcParams.update({
    "font.family": ["PingFang SC", "Arial Unicode MS"],
    "axes.unicode_minus": False, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "text.color": INK, "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": INK2, "font.size": 9,
})

SHORT = {
    "physics_random_duel": "随机物理对战", "head_sports": "大头体育", "coop_duo_puzzle": "双人合作解谜",
    "bike_trials": "载具闯关", "ragdoll_gore_course": "布娃娃摔伤", "troll_platformer": "坑人平台",
    "endless_runner": "无尽跑酷／下坡", "precision_platformer": "精准平台", "rhythm_auto_runner": "节奏跑酷",
    "stickman_swing": "荡绳抓钩", "io_eat_grow": "吞噬成长", "io_territory": "圈地", "io_arena_shooter": "网页射击",
    "sandbox_voxel": "体素沙盒", "kart_battle": "卡丁车乱斗", "tank_maze_duel": "坦克迷宫对战", "bomberman": "炸弹人",
    "tower_defense": "塔防", "gold_miner_claw": "摆钩抓取", "fishing_timing": "钓鱼", "launch_distance": "发射冲距离",
    "train_and_race": "训练竞速", "time_mgmt_cooking": "经营烹饪", "idle_clicker": "放置点击", "merge_drop": "合成掉落",
    "classic_board_card": "棋牌消除", "fruit_slice": "切水果", "physics_destruction": "物理破坏",
    "draw_guess_party": "你画我猜", "hide_seek_prop": "躲猫猫", "tag_arena": "追逐抓人", "car_stunt_drift": "赛车漂移",
    "parking_traffic_puzzle": "停车交通", "pool_billiards": "台球", "mini_golf": "迷你高尔夫",
    "penalty_freekick": "点球任意球", "racket_duel": "球拍对打", "stickman_brawler": "横版格斗",
    "run_gun_coop": "横版射击", "stealth_heist": "潜行偷盗", "upgrade_drive_zombies": "升级冲僵尸",
    "artillery_turn": "抛物线对轰", "dress_up_makeover": "换装", "horror_escape": "恐怖逃生",
    "minigame_collection": "小游戏合集", "rhythm_music": "音游", "helix_stack_tap": "单指反应",
}
GENRE_ZH = {"Simulation": "模拟（大亨、增量）", "Action": "动作", "RPG": "RPG", "Survival": "生存",
            "Roleplay & Avatar Sim": "角色扮演", "Shooter": "射击", "Strategy": "策略", "Sports & Racing": "体育竞速",
            "Party & Casual": "派对休闲", "Adventure": "冒险", "Obby & Platformer": "跑酷平台", "Puzzle": "解谜",
            "Entertainment": "娱乐", "Social": "社交", "Shopping": "购物"}
PICK = "launch_distance"


def rd(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def f(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def fig_ax(title, subtitle, w=8.0, h=4.6, source="数据：Roblox 公开接口与网页平台，2026-10-08 抓取"):
    fig = plt.figure(figsize=(w, h), dpi=DPI, layout="constrained")
    head, foot = 0.82, 0.30
    fig.get_layout_engine().set(rect=(0.012, foot / h, 0.976, 1 - (head + foot) / h))
    esc = lambda t: t.replace("$", r"\$")                # a pair of $ would otherwise switch to math mode
    fig.text(0.025, 1 - 0.30 / h, esc(title), fontsize=13, fontweight=600, color=INK, va="center", ha="left")
    fig.text(0.025, 1 - 0.60 / h, esc(subtitle), fontsize=9.5, color=INK2, va="center", ha="left")
    fig.text(0.025, 0.13 / h, esc(source), fontsize=7.5, color=MUTED, va="center", ha="left")
    ax = fig.add_subplot(111)
    return fig, ax


def style(ax, grid="x", baseline="left"):
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    if baseline:
        ax.spines[baseline].set_visible(True)
        ax.spines[baseline].set_color(BASE)
        ax.spines[baseline].set_linewidth(0.8)
    ax.tick_params(length=0, labelsize=8.5)
    if grid:
        ax.grid(axis=grid, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def round_bars(fig, ax, bars, horizontal=True, r=8):
    """Re-draw bars with a 4px (8 device px) rounded data-end and a square baseline end."""
    fig.canvas.draw()
    for b in bars:
        bb = b.get_window_extent()
        if bb.width < 0.5 or bb.height < 0.5:
            continue
        col, z = b.get_facecolor(), b.get_zorder()
        neg = (b.get_width() < 0) if horizontal else (b.get_height() < 0)
        b.set_visible(False)
        length = bb.width if horizontal else bb.height
        rr = min(r, length / 2, (bb.height if horizontal else bb.width) / 2)
        p = FancyBboxPatch((bb.x0, bb.y0), bb.width, bb.height, boxstyle=BoxStyle("Round", pad=0, rounding_size=rr),
                           transform=IdentityTransform(), fc=col, ec="none", zorder=z, clip_on=False)
        if horizontal:
            sq = Rectangle((bb.x1 - rr if neg else bb.x0, bb.y0), rr, bb.height)
        else:
            sq = Rectangle((bb.x0, bb.y1 - rr if neg else bb.y0), bb.width, rr)
        sq.set(transform=IdentityTransform(), fc=col, ec="none", zorder=z, clip_on=False)
        for a in (p, sq):
            a.set_in_layout(False)
            ax.add_patch(a)


HALO = [patheffects.withStroke(linewidth=2.6, foreground=SURFACE)]      # keeps labels legible over dots


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    print("  ", name)


def legend(ax, handles, loc="lower right", ncol=1):
    lg = ax.legend(handles=handles, loc=loc, frameon=False, fontsize=8.5, ncol=ncol, handlelength=1.2,
                   labelcolor=INK2, borderaxespad=0.4, columnspacing=1.2)
    return lg


def swatch(color, label):
    return Line2D([0], [0], marker="s", color="none", markerfacecolor=color, markeredgecolor="none",
                  markersize=7, label=label)


def dot(color, label, size=6):
    return Line2D([0], [0], marker="o", color="none", markerfacecolor=color, markeredgecolor=SURFACE,
                  markersize=size, label=label)


def money(v, _=None):
    return f"-${abs(v):,.0f}" if v < 0 else f"${v:,.0f}"


def compact(v, _=None):
    if v >= 1e9:
        return f"{v / 1e9:.0f}0 亿" if False else f"{v / 1e8:.0f} 亿"
    if v >= 1e8:
        return f"{v / 1e8:.0f} 亿"
    if v >= 1e4:
        return f"{v / 1e4:.0f} 万"
    return f"{v:,.0f}"


# ============================================================ Roblox market
def c01_top_earning_genre():
    ch = rd(D("roblox_charts.csv"))
    today = datetime.date.fromisoformat(ch[0]["snapshot_utc"][:10])
    te = [r for r in ch if r["query"] == "top-earning"]
    new, old = collections.Counter(), collections.Counter()
    for r in te:
        g = r["genre_l1"] or "(未标注)"
        try:
            young = (today - datetime.date.fromisoformat(r["created"])).days <= 365
        except Exception:
            young = False
        (new if young else old)[g] += 1
    genres = [g for g, _ in (new + old).most_common() if g in GENRE_ZH][:11][::-1]
    fig, ax = fig_ax(f"最赚钱的 {len(te)} 款里，{sum(new.values())} 款创建不到 12 个月",
                     "Roblox「Top Earning」榜各类型的游戏数量，按创建时间拆分")
    y = range(len(genres))
    b1 = ax.barh(y, [new[g] for g in genres], height=0.56, color=DARK, edgecolor=SURFACE, linewidth=1.4)
    b2 = ax.barh(y, [old[g] for g in genres], left=[new[g] for g in genres], height=0.56, color=LIGHT,
                 edgecolor=SURFACE, linewidth=1.4)
    for i, g in enumerate(genres):
        ax.text(new[g] + old[g] + 2, i, f"{new[g] + old[g]}", va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(list(y), [GENRE_ZH[g] for g in genres])
    ax.set_xlim(0, max(new[g] + old[g] for g in genres) * 1.1)
    ax.set_xlabel("游戏数量", fontsize=8.5)
    style(ax)
    legend(ax, [swatch(DARK, "创建不到 12 个月"), swatch(LIGHT, "更早创建")])
    save(fig, "01_top_earning_by_genre.png")


def c02_turnover():
    ch = rd(D("roblox_charts.csv"))
    today = datetime.date.fromisoformat(ch[0]["snapshot_utc"][:10])
    te = [r for r in ch if r["query"] == "top-earning"]
    bins = [(0, 90, "不到 3 个月"), (90, 180, "3–6 个月"), (180, 365, "6–12 个月"), (365, 730, "1–2 年"),
            (730, 1095, "2–3 年"), (1095, 1825, "3–5 年"), (1825, 10 ** 6, "5 年以上")]
    cnt = [0] * len(bins)
    for r in te:
        try:
            a = (today - datetime.date.fromisoformat(r["created"])).days
        except Exception:
            continue
        for i, (lo, hi, _) in enumerate(bins):
            if lo <= a < hi:
                cnt[i] += 1
    fig, ax = fig_ax("最赚钱的游戏大多很年轻：近四分之一上线不到 3 个月",
                     f"Roblox「Top Earning」榜 {len(te)} 款游戏按创建至今的时间分布")
    bars = ax.bar(range(len(bins)), cnt, width=0.24, color=BLUE)
    for i, c in enumerate(cnt):
        ax.text(i, c + max(cnt) * 0.02, str(c), ha="center", va="bottom", fontsize=8.5, color=INK2)
    ax.set_xticks(range(len(bins)), [b[2] for b in bins])
    ax.tick_params(axis="x", colors=INK2)
    ax.set_ylabel("游戏数量", fontsize=8.5)
    ax.set_ylim(0, max(cnt) * 1.15)
    style(ax, grid="y", baseline="bottom")
    round_bars(fig, ax, bars, horizontal=False)
    save(fig, "02_top_earning_age.png")


def c03_reach_vs_retention():
    arch = {a["id"]: a for a in json.load(open(D("archetypes.json"), encoding="utf-8"))}
    rows = [r for r in rd(D("roblox_competitors.csv")) if arch.get(r["archetype"], {}).get("origin") == "web"]
    seen, pts = set(), []
    for r in rows:
        if r["universe_id"] in seen:
            continue
        seen.add(r["universe_id"])
        v, c = f(r["visits"]), f(r["ccu"])
        if v >= 1e5:
            pts.append((v, max(c, 0.7), r["name"]))
    named = [("Super Head Soccer", "Super Head Soccer", (9, 8)), ("Color Game!", "Color Game!（paper.io）", (9, 9)),
             ("Watermelon GO", "Watermelon GO!（合成西瓜）", (10, -9)), ("Stack Ball", "Stack Ball", (9, 2)),
             ("Super Free Kick", "Super Free Kick", (9, -10)), ("Roblox Flappy Bird", "Roblox Flappy Bird", (-9, -12)),
             ("2D Basketball", "2D Basketball（Basket Random）", (-9, 9)), ("+1 Stone Skipping", "+1 Stone Skipping", (-9, 7)),
             ("Kick a Lucky Block", "Kick a Lucky Block", (-9, 8)), ("Broken Bones IV", "Broken Bones IV", (-9, 8))]
    fig, ax = fig_ax("流量好拿，留人难：访问过千万、在线不到百人的移植作品很多",
                     f"网页玩法在 Roblox 上的 {len(pts):,} 款直接竞品：累计访问量与当前同时在线人数（对数坐标）", h=5.0)
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=9, color=GREY, alpha=0.55, linewidths=0, zorder=2)
    for key, label, off in named:
        cand = [p for p in pts if key.lower() in p[2].lower()]
        if not cand:
            continue
        p = max(cand, key=lambda q: q[0])
        ax.scatter([p[0]], [p[1]], s=42, color=BLUE, edgecolors=SURFACE, linewidths=1.4, zorder=4)
        ax.annotate(label, (p[0], p[1]), xytext=off, textcoords="offset points", fontsize=8, color=INK,
                    ha="left" if off[0] > 0 else "right", va="center", zorder=5, path_effects=HALO)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("累计访问量", fontsize=8.5)
    ax.set_ylabel("当前同时在线（CCU）", fontsize=8.5)
    ax.xaxis.set_major_formatter(FuncFormatter(compact))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}" if v >= 1 else "0"))
    ax.tick_params(axis="y", colors=MUTED)
    style(ax, grid="both", baseline="bottom")
    ax.minorticks_off()
    legend(ax, [dot(BLUE, "文中点名的例子", 7), dot(GREY, "其他直接竞品", 5)], loc="upper left")
    save(fig, "03_reach_vs_retention.png")


def c04_web_vs_roblox(rank):
    pts = [(f(r["web_share_pct"]), f(r["roblox_ccu_direct"]), r["archetype"], r["eligible"]) for r in rank]
    pts = [p for p in pts if p[0] > 0]
    summ = json.load(open(O("model_summary.json")))
    fig, ax = fig_ax(f"网页热度几乎不能预测 Roblox 热度（秩相关 {summ['spearman_web_share_vs_roblox_ccu']:.2f}）",
                     f"{len(pts)} 个网页原生玩法：网页注意力份额与 Roblox 直接竞品当前在线人数（对数坐标）", h=5.0)
    lab = {"endless_runner": (7, -9), "launch_distance": (-7, 7), "penalty_freekick": (7, 4), "gold_miner_claw": (7, -8),
           "classic_board_card": (-7, 7), "stealth_heist": (7, 0), "physics_random_duel": (7, 0),
           "helix_stack_tap": (7, 0), "merge_drop": (7, 0), "idle_clicker": (-7, -9), "run_gun_coop": (-7, 7),
           "bomberman": (7, -7), "train_and_race": (7, 6)}
    for x, y, a, el in pts:
        hi = a in ("launch_distance", "endless_runner", "penalty_freekick", "gold_miner_claw")
        ax.scatter([x], [max(y, 8)], s=44 if hi else 26, color=BLUE if hi else GREY, edgecolors=SURFACE,
                   linewidths=1.2, zorder=4 if hi else 3)
        if a in lab:
            off = lab[a]
            ax.annotate(SHORT[a], (x, max(y, 8)), xytext=off, textcoords="offset points", fontsize=8, color=INK2,
                        ha="left" if off[0] > 0 else "right", va="center", zorder=5, path_effects=HALO)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("网页注意力份额（各平台站内份额的加权平均）", fontsize=8.5)
    ax.set_ylabel("Roblox 直接竞品 CCU 合计", fontsize=8.5)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}" if v > 10 else "≈0"))
    ax.tick_params(axis="y", colors=MUTED)
    style(ax, grid="both", baseline="bottom")
    ax.minorticks_off()
    legend(ax, [dot(BLUE, "模型前四名", 7), dot(GREY, "其他玩法", 6)], loc="upper left")
    save(fig, "04_web_vs_roblox_demand.png")


def c05_evidence(rank):
    order = [("proven_open", "需求已证实，新人正在进入"), ("live_open", "有需求，有人进得去"),
             ("live_entrenched", "有需求，被老游戏占着"), ("thin", "需求很薄"),
             ("tried_and_died", "多人试过，留不住人"), ("untested", "没人认真试过（真正的空白）")][::-1]
    cnt = collections.Counter(r["bucket_rbx"] for r in rank)
    fig, ax = fig_ax(f"{len(rank)} 个网页玩法里，只有 {cnt['untested']} 个在 Roblox 上没人认真试过",
                     "按 Roblox 上同玩法尝试者的下场分类（规则见报告第 2 节）", h=3.9)
    vals = [cnt[k] for k, _ in order]
    bars = ax.barh(range(len(order)), vals, height=0.5, color=[BLUE if k == "untested" else GREY for k, _ in order])
    for i, v in enumerate(vals):
        ax.text(v + 0.4, i, str(v), va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(range(len(order)), [z for _, z in order])
    ax.set_xlim(0, max(vals) * 1.1)
    ax.set_xlabel("玩法原型数量", fontsize=8.5)
    style(ax)
    round_bars(fig, ax, bars)
    save(fig, "05_evidence_buckets.png")


# ============================================================ model
def c06_ranking(rank):
    el = [r for r in rank if r["eligible"] == "yes"][:15][::-1]
    fig, ax = fig_ax("前十几名的每小时净值区间几乎完全重叠",
                     "各玩法每开发小时的期望净收入（不含时间成本）：参数不确定性下的 5%–95% 区间、中位数与均值", h=5.6,
                     source="数据：本项目模型输出 out/ranking.csv（600 组参数 × 3,000 次模拟）")
    for i, r in enumerate(el):
        lo, mid, hi, mean = f(r["net_usd_per_hour_p05"]), f(r["net_usd_per_hour_p50"]), f(r["net_usd_per_hour_p95"]), \
            f(r["net_usd_per_hour_mean"])
        ax.plot([lo, hi], [i, i], color=GREY, linewidth=2, solid_capstyle="round", zorder=2)
        ax.scatter([mid], [i], s=30, color=SURFACE, edgecolors=INK2, linewidths=1.2, zorder=3)
        ax.scatter([mean], [i], s=46, color=BLUE, edgecolors=SURFACE, linewidths=1.4, zorder=4)
    ax.axvline(20, color=INK2, linewidth=0.8, zorder=1)
    ax.text(20.8, len(el) - 0.35, "时间成本 $20/小时", fontsize=8, color=INK2, va="bottom")
    ax.set_yticks(range(len(el)), [SHORT[r["archetype"]] for r in el])
    for t, r in zip(ax.get_yticklabels(), el):
        if r["archetype"] == PICK:
            t.set_fontweight("bold")
            t.set_color(INK)
    ax.set_ylim(-0.7, len(el) + 0.2)
    ax.set_xlim(-4, max(f(r["net_usd_per_hour_p95"]) for r in el) * 1.04)
    ax.xaxis.set_major_formatter(FuncFormatter(money))
    ax.set_xlabel("每开发小时净收入（美元）", fontsize=8.5)
    style(ax, baseline=None)
    legend(ax, [dot(BLUE, "均值", 7), Line2D([0], [0], marker="o", color="none", markerfacecolor=SURFACE,
                                           markeredgecolor=INK2, markersize=5.5, label="中位数"),
                Line2D([0], [0], color=GREY, linewidth=2, label="5%–95% 区间")], loc="lower right")
    save(fig, "06_ranking_intervals.png")


def c07_staged(rank):
    el = [r for r in rank if r["eligible"] == "yes"][:10][::-1]
    gain = [f(r["value_of_staging"]) for r in el]
    fig, ax = fig_ax(f"分阶段做比一次性做完，每个项目多出 ${min(gain):,.0f}–${max(gain):,.0f}",
                     "风险调整价值 V（时间按 $20/小时计，亏损加倍计权）：一次性做完与分阶段两种做法", h=4.6,
                     source="数据：本项目模型输出 out/ranking.csv")
    for i, r in enumerate(el):
        a, b = f(r["V_risk_adj_commit"]), f(r["V_risk_adj_staged"])
        ax.plot([a, b], [i, i], color=GREY, linewidth=2, zorder=2)
        ax.scatter([a], [i], s=46, color=LIGHT, edgecolors=SURFACE, linewidths=1.4, zorder=3)
        ax.scatter([b], [i], s=46, color=DARK, edgecolors=SURFACE, linewidths=1.4, zorder=4)
    ax.axvline(0, color=INK2, linewidth=0.8, zorder=1)
    ax.set_yticks(range(len(el)), [SHORT[r["archetype"]] for r in el])
    ax.set_ylim(-0.7, len(el) - 0.3)
    ax.xaxis.set_major_formatter(FuncFormatter(money))
    ax.set_xlabel("风险调整价值 V（美元）", fontsize=8.5)
    style(ax, baseline=None)
    legend(ax, [dot(LIGHT, "一次性做完再上线", 7), dot(DARK, "分阶段、设两道关口", 7)], loc="upper left")
    save(fig, "07_staged_vs_commit.png")


SCEN_ZH = collections.OrderedDict([
    ("prior P(traction) high (8%)", "起量先验 8%（基准 3%）"),
    ("small-game $ mult high (1.0)", "小游戏变现折扣 1.0（基准 0.4）"),
    ("Pareto alpha heavy tail (0.8)", "长尾更肥（指数 0.8）"),
    ("costs x0.7", "工时 ×0.7"),
    ("US 18+ DevEx premium on 20% of spend", "两成收入来自美国成年用户"),
    ("genre monetisation index off (=1 for all)", "关掉类型变现指数"),
    ("costs x1.5", "工时 ×1.5"),
    ("hit size capped at 2,000 CCU", "规模封顶 2,000 CCU"),
    ("Pareto alpha thin tail (1.3)", "长尾更瘦（指数 1.3）"),
    ("ignore all evidence LRs", "忽略全部证据"),
    ("age gate: never unlocks under-16 audience", "始终进不了 16 岁以下目录"),
    ("prior P(traction) low (1%)", "起量先验 1%"),
    ("small-game $ mult low (0.15)", "小游戏变现折扣 0.15"),
])


def c08_sensitivity():
    sens = [r for r in rd(O("sensitivity.csv")) if r["archetype"] == PICK and r["scenario"] in SCEN_ZH]
    base = f(sens[0]["base_net_usd_per_hour"])
    sens.sort(key=lambda r: f(r["net_usd_per_hour"]))
    fig, ax = fig_ax("首选方向对「起量先验」和「小游戏变现折扣」最敏感",
                     f"发射冲距离类：每个假设单独变动时的每小时净值（基准 ${base:.0f}）", h=5.0,
                     source="数据：本项目模型输出 out/sensitivity.csv")
    vals = [f(r["net_usd_per_hour"]) for r in sens]
    bars = ax.barh(range(len(sens)), [v - base for v in vals], left=base, height=0.5,
                   color=[BLUE if v >= base else RED for v in vals])
    for i, v in enumerate(vals):
        ax.text(v + (1.2 if v >= base else -1.2), i, f"${v:.0f}", va="center", ha="left" if v >= base else "right",
                fontsize=8.5, color=INK2)
    ax.axvline(base, color=INK2, linewidth=0.8)
    ax.set_yticks(range(len(sens)), [SCEN_ZH[r["scenario"]] for r in sens])
    ax.set_xlim(min(vals) - 9, max(vals) + 9)
    ax.xaxis.set_major_formatter(FuncFormatter(money))
    ax.set_xlabel("每开发小时净收入（美元）", fontsize=8.5)
    style(ax, baseline=None)
    legend(ax, [swatch(BLUE, "高于基准"), swatch(RED, "低于基准")], loc="lower right")
    round_bars(fig, ax, bars)
    save(fig, "08_sensitivity_pick.png")


def c09_programme():
    prog = rd(O("programme.csv"))
    budgets = sorted({int(p["hour_budget"]) for p in prog})
    ks = sorted({int(p["top_k"]) for p in prog})
    best = max(f(p["p_at_least_one_traction"]) for p in prog)
    fig, ax = fig_ax(f"连做六个便宜的赌注，至少一个起量的概率也只有约 {best * 100:.0f}%",
                     "按模型排名依次做分阶段项目：不同工时预算和候选数量下，至少一个项目起量的概率", h=4.4,
                     source="数据：本项目模型输出 out/programme.csv")
    wbar = 0.1
    allbars = []
    for j, k in enumerate(ks):
        xs = [i + (j - 1) * (wbar + 0.035) for i in range(len(budgets))]
        ys = [next(f(p["p_at_least_one_traction"]) for p in prog if int(p["hour_budget"]) == b and int(p["top_k"]) == k)
              for b in budgets]
        bars = ax.bar(xs, ys, width=wbar, color=RAMP3[j])
        allbars += list(bars)
        for x, yv in zip(xs, ys):
            ax.text(x, yv + 0.006, f"{yv * 100:.0f}%", ha="center", va="bottom", fontsize=8.5, color=INK2)
    ax.set_xticks(range(len(budgets)), [f"{b} 小时预算" for b in budgets])
    ax.tick_params(axis="x", colors=INK2)
    ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.set_ylim(0, best * 1.25)
    ax.set_ylabel("至少一个项目起量的概率", fontsize=8.5)
    style(ax, grid="y", baseline="bottom")
    legend(ax, [swatch(RAMP3[j], f"候选 {k} 个") for j, k in enumerate(ks)], loc="upper left", ncol=3)
    round_bars(fig, ax, allbars, horizontal=False)
    save(fig, "09_programme.png")


def c10_outcomes():
    o = next(r for r in rd(O("outcomes.csv")) if r["archetype"] == PICK)
    items = [("第一道关口被砍（不好玩）", f(o["p_kill_gate_A"]), f"亏约 {f(o['hours_if_kill_A']):.0f} 小时", False),
             ("第二道关口被砍（留存不够）", f(o["p_kill_gate_B"]), f"亏约 {f(o['hours_if_kill_B']):.0f} 小时加试投费", False),
             ("上线了但没起量", f(o["p_launch_no_traction"]), f"亏约 {f(o['hours_if_launch_no_traction']):.0f} 小时", False),
             ("起量：平均在线 100–1,000", f(o["p_traction_100_to_1000"]),
              f"首年收入中位数 ${f(o['rev_median_traction_100_to_1000']):,.0f}", True),
             ("起量：平均在线过千", f(o["p_traction_1000_plus"]),
              f"首年收入中位数 ${f(o['rev_median_traction_1000_plus']):,.0f}", True)][::-1]
    lose = sum(p for _, p, _, good in items if not good)
    fig, ax = fig_ax(f"首选方向最可能的结局：{lose * 100:.0f}% 的情况是亏掉时间",
                     "发射冲距离类按分阶段方式做一次，五种结局各自的概率", h=3.9,
                     source="数据：本项目模型输出 out/outcomes.csv")
    bars = ax.barh(range(len(items)), [p for _, p, _, _ in items], height=0.5,
                   color=[BLUE if g else GREY for _, _, _, g in items])
    for i, (_, p, note, _) in enumerate(items):
        ax.text(p + 0.008, i, f"{p * 100:.1f}%　{note}", va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(range(len(items)), [n for n, _, _, _ in items])
    ax.set_xlim(0, max(p for _, p, _, _ in items) * 1.75)
    ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.set_xlabel("概率", fontsize=8.5)
    style(ax)
    round_bars(fig, ax, bars)
    save(fig, "10_outcomes_pick.png")


# ============================================================ web side
def c11_momentum():
    dem = [r for r in rd(D("archetype_demand.csv")) if r["origin"] == "web" and r["archetype"] in SHORT]
    dem = sorted(dem, key=lambda r: -f(r["web_share_pct"]))[:20][::-1]
    fig, ax = fig_ax("多数网页玩法是「历史热门」：当前份额低于历史份额",
                     "网页注意力份额最高的 20 个玩法：历史累计口径（总游玩、总榜）与当前口径（本周热门、月榜）", h=6.0,
                     source="数据：CrazyGames、Poki、Y8、4399、7k7k、Coolmath、Kongregate，2026-10-08 抓取")
    for i, r in enumerate(dem):
        a, b = f(r["alltime_share_pct"]), f(r["current_share_pct"])
        ax.plot([a, b], [i, i], color=GREY, linewidth=2, zorder=2)
        ax.scatter([a], [i], s=44, color=LIGHT, edgecolors=SURFACE, linewidths=1.4, zorder=3)
        ax.scatter([b], [i], s=44, color=DARK, edgecolors=SURFACE, linewidths=1.4, zorder=4)
    ax.set_yticks(range(len(dem)), [SHORT[r["archetype"]] for r in dem])
    ax.set_ylim(-0.7, len(dem) - 0.3)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
    ax.set_xlabel("占网页平台被测量注意力的份额", fontsize=8.5)
    ax.set_xlim(left=-0.3)
    style(ax, baseline=None)
    legend(ax, [dot(LIGHT, "历史累计份额", 7), dot(DARK, "当前份额", 7)], loc="lower right")
    save(fig, "11_web_alltime_vs_current.png")


def c12_coverage():
    g = rd(D("games.csv"))
    src = [("CrazyGames（游玩次数）", "cg_plays"), ("4399（总榜名次）", "r4399_total_rank"), ("4399（月榜名次）", "r4399_month_rank"),
           ("Y8（游玩次数）", "y8_plays"), ("7k7k（最热榜名次）", "r7k_hot_rank"), ("Poki（投票数）", "poki_votes"),
           ("Coolmath（投票数，手选名单）", "cm_votes"), ("Kongregate（游玩次数）", "kong_plays")]
    vals = sorted([(n, sum(1 for x in g if x[k])) for n, k in src], key=lambda t: t[1])
    tot = sum(1 for x in g if any(x[k] for _, k in src))
    fig, ax = fig_ax("量化数据的覆盖很不均匀：近三分之二来自 CrazyGames",
                     f"有量化信号的 {tot:,} 个游戏系列，按来源计数（一个系列可出现在多个来源）", h=4.0,
                     source="数据：data/games.csv。Newgrounds、17yy、GamePix、Gameflare 返回 403，未覆盖")
    bars = ax.barh(range(len(vals)), [v for _, v in vals], height=0.5, color=BLUE)
    for i, (_, v) in enumerate(vals):
        ax.text(v + 15, i, f"{v:,}", va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(range(len(vals)), [n for n, _ in vals])
    ax.set_xlim(0, max(v for _, v in vals) * 1.1)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_xlabel("游戏系列数量", fontsize=8.5)
    style(ax)
    round_bars(fig, ax, bars)
    save(fig, "12_data_coverage.png")


def c13_launch_timeline():
    rows = [r for r in rd(D("roblox_competitors.csv")) if r["archetype"] == PICK and f(r["ccu"]) >= 1]
    snap = datetime.date(2026, 10, 8)
    fig, ax = fig_ax("发射类的当前在线几乎全在近 12 个月的新品手里",
                     f"发射冲距离类 {len(rows)} 款直接竞品：创建日期与当前同时在线人数（对数坐标）", h=4.8)
    lab = {"+1 Stone Skipping": (-8, 6), "Kick a Lucky Block": (-8, 7), "Kick Ball to Space": (-8, 7),
           "Glide Tower": (-8, 7), "Goal Kick Simulator": (8, 6), "PAPER PLANES!": (8, -7), "Egg Skipping": (-8, -8),
           "Launch a Wheel": (8, 6)}
    for r in rows:
        d = datetime.date.fromisoformat(r["created"])
        if d < datetime.date(2021, 1, 1):
            continue
        new = (snap - d).days <= 365
        ax.scatter([d], [f(r["ccu"])], s=40 if new else 26, color=BLUE if new else GREY, edgecolors=SURFACE,
                   linewidths=1.2, zorder=4 if new else 3)
        for key, off in lab.items():
            if key.lower() in r["name"].lower():
                ax.annotate(key, (d, f(r["ccu"])), xytext=off, textcoords="offset points", fontsize=8, color=INK2,
                            ha="left" if off[0] > 0 else "right", va="center", zorder=5, path_effects=HALO)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_xlabel("创建日期", fontsize=8.5)
    ax.set_ylabel("当前同时在线（CCU）", fontsize=8.5)
    ax.tick_params(axis="y", colors=MUTED)
    style(ax, grid="both", baseline="bottom")
    ax.minorticks_off()
    legend(ax, [dot(BLUE, "创建不到 12 个月", 7), dot(GREY, "更早创建", 6)], loc="upper left")
    save(fig, "13_launch_competitors.png")


# ============================================================ age
AGE_SRC = "数据：Roblox 2026 年第二季度股东信；细分年龄段为推算，假设见 data/age_reference.json"


def a1_age_mix():
    seg = rd(D("age_segments.csv"))
    summ = json.load(open(O("age_summary.json")))
    fig, ax = fig_ax(f"Roblox 日活里约 {summ['derived_share_of_dau_under_18'] * 100:.0f}% 未满 18 岁，成年人约占三成",
                     "各年龄段占日活的份额（推算值），以及其中已完成年龄验证的部分", h=4.0, source=AGE_SRC)
    names = [s["age_band"] + " 岁" for s in seg][::-1]
    tot = [f(s["share_of_dau"]) for s in seg][::-1]
    chk = [f(s["share_of_dau_age_checked"]) for s in seg][::-1]
    ax.barh(range(len(seg)), tot, height=0.5, color=LIGHT, edgecolor=SURFACE, linewidth=1.4)
    b2 = ax.barh(range(len(seg)), chk, height=0.5, color=DARK, edgecolor=SURFACE, linewidth=1.4)
    for i, (t, c) in enumerate(zip(tot, chk)):
        ax.text(t + 0.004, i, f"{t * 100:.0f}%（已验龄 {c * 100:.0f}%）", va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(range(len(seg)), names)
    ax.set_xlim(0, max(tot) * 1.45)
    ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.set_xlabel("占全部日活的份额", fontsize=8.5)
    style(ax)
    legend(ax, [swatch(DARK, "已完成年龄验证"), swatch(LIGHT, "尚未验证")], loc="upper right")
    save(fig, "A1_age_mix.png")


def a2_reach():
    reach = rd(D("age_reach_by_label.csv"))
    summ = json.load(open(O("age_summary.json")))
    lo, hi = summ["trial_phase_reach_range"]
    rows = [("试用期：只对已验龄的 16 岁以上开放", f(reach[0]["share_of_dau"]), True),
            ("过审后，分级为 Moderate", f(reach[2]["share_of_dau"]), False),
            ("过审后，分级为 Minimal 或 Mild", f(reach[1]["share_of_dau"]), False)][::-1]
    fig, ax = fig_ax(f"新游戏起步只能触达约 {rows[-1][1] * 100:.0f}% 的日活",
                     "一款游戏在不同阶段、不同内容分级下能触达的日活份额（推算值）", h=3.3, source=AGE_SRC)
    bars = ax.barh(range(len(rows)), [r[1] for r in rows], height=0.34, color=[BLUE if r[2] else GREY for r in rows])
    for i, (_, v, hl) in enumerate(rows):
        extra = f"（区间 {lo * 100:.0f}%–{hi * 100:.0f}%）" if hl else ""
        ax.text(v + 0.012, i, f"{v * 100:.0f}%{extra}", va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.set_xlim(0, 1.22)
    ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlabel("可触达的日活份额", fontsize=8.5)
    style(ax)
    round_bars(fig, ax, bars)
    save(fig, "A2_reach_by_stage.png")


def a3_value():
    summ = json.load(open(O("age_summary.json")))
    rows = [("未满 18 岁用户", 1.0), ("成年用户（按美国的消费倍数）", 1.5),
            ("美国已验龄成年用户的合格消费（含 DevEx 加成）", summ["creator_value_us18_vs_u18"])][::-1]
    fig, ax = fig_ax(f"一个美国成年用户给开发者带来的收入约为未成年用户的 {rows[0][1]:.1f} 倍",
                     "每个用户给开发者带来的相对收入（未满 18 岁 = 1）。消费倍数为 Roblox 公布的下限", h=3.2,
                     source="数据：Roblox 2026 年第二季度股东信（成年用户消费高出 50% 以上）；Roblox 2026-04-30 公告（DevEx 高 42%）")
    bars = ax.barh(range(len(rows)), [r[1] for r in rows], height=0.34, color=RAMP3[::-1])
    for i, (_, v) in enumerate(rows):
        ax.text(v + 0.03, i, f"{v:.2f}×" if v != 1 else "1×", va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.set_xlim(0, rows[0][1] * 1.15)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}×"))
    ax.set_xlabel("相对收入", fontsize=8.5)
    style(ax)
    round_bars(fig, ax, bars)
    save(fig, "A3_value_per_user.png")


LAB_ZH = {"minimal": "Minimal", "mild": "Mild", "moderate": "Moderate", "restricted": "Restricted"}


def stacked100(ax, labels, shares, colors, names):
    left = [0.0] * len(labels)
    for j, nm in enumerate(names):
        vals = [s[j] for s in shares]
        ax.barh(range(len(labels)), vals, left=left, height=0.52, color=colors[j], edgecolor=SURFACE, linewidth=1.4)
        for i, v in enumerate(vals):
            if v >= 0.07:
                ax.text(left[i] + v / 2, i, f"{v * 100:.0f}%", ha="center", va="center", fontsize=8,
                        color="#ffffff" if j >= 2 else INK)
        left = [l + v for l, v in zip(left, vals)]
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    style(ax, grid=None)


def a4_maturity_market():
    if not os.path.exists(D("maturity_market.csv")):
        return
    m = {r["label"]: r for r in rd(D("maturity_market.csv"))}
    keys = [k for k in ("minimal", "mild", "moderate") if k in m]
    rows = [("榜单上的游戏数", "chart_games_share"), ("榜单游戏的在线人数", "chart_ccu_share"),
            ("最赚钱榜席位", "top_earning_share"), ("其中创建不到 12 个月的", "top_earning_new_12m_share")][::-1]
    known = [sum(f(m[k][col]) for k in keys) for _, col in rows]
    shares = [[f(m[k][col]) / kn if kn else 0 for k in keys] for (_, col), kn in zip(rows, known)]
    open_kids = shares[-2][0] + shares[-2][1]
    fig, ax = fig_ax(f"榜单在线人数的 {open_kids * 100:.0f}% 在 Minimal 或 Mild 分级的游戏里",
                     "Roblox 官方榜单上的游戏按内容分级的构成。Minimal 和 Mild 对所有年龄开放，Moderate 不对 5–8 岁开放", h=3.6,
                     source="数据：Roblox 榜单与搜索接口返回的 contentMaturity 字段，2026-10-08 抓取")
    stacked100(ax, [r[0] for r in rows], shares, RAMP3, keys)
    ax.legend(handles=[swatch(RAMP3[j], LAB_ZH[k]) for j, k in enumerate(keys)], loc="upper center",
              bbox_to_anchor=(0.5, -0.14), ncol=len(keys), frameon=False, fontsize=8.5, labelcolor=INK2)
    save(fig, "A4_maturity_market.png")


def a5_maturity_archetype(rank):
    if not os.path.exists(D("maturity_by_archetype.csv")):
        return
    top = [r["archetype"] for r in rank if r["eligible"] == "yes"][:14]
    m = {r["archetype"]: r for r in rd(D("maturity_by_archetype.csv"))}
    rows = [m[a] for a in top if a in m and f(m[a]["ccu_direct"]) > 0][::-1]
    keys = ["minimal", "mild", "moderate"]
    shares = []
    for r in rows:
        v = [f(r[f"ccu_share_{k}"]) for k in keys]
        s = sum(v)
        shares.append([x / s if s else 0 for x in v])
    fig, ax = fig_ax("候选玩法的竞品几乎全是 Minimal 或 Mild：内容分级不是瓶颈",
                     "模型前 14 名玩法：直接竞品的在线人数按内容分级的构成", h=5.4,
                     source="数据：Roblox 搜索接口返回的 contentMaturity 字段，2026-10-08 抓取")
    stacked100(ax, [SHORT[r["archetype"]] for r in rows], shares, RAMP3, keys)
    ax.legend(handles=[swatch(RAMP3[j], LAB_ZH[k]) for j, k in enumerate(keys)], loc="upper center",
              bbox_to_anchor=(0.5, -0.08), ncol=3, frameon=False, fontsize=8.5, labelcolor=INK2)
    save(fig, "A5_maturity_by_archetype.png")


def a6_scratch():
    if not os.path.exists(D("scratch_age_distribution.csv")):
        return
    sc = [r for r in rd(D("scratch_age_distribution.csv")) if 5 <= int(r["age"]) <= 25]
    summ = json.load(open(O("age_summary.json")))["scratch_signup_age"]
    core = summ["9-12"] + summ["13-15"]
    fig, ax = fig_ax(f"Scratch 用户注册时 {core * 100:.0f}% 在 9–15 岁，峰值 {summ['mode_age']} 岁",
                     "Scratch 全部注册用户按注册时自报年龄的分布（5–25 岁部分）。它决定了 Scratch 信号代表谁", h=4.2,
                     source="数据：scratch.mit.edu/statistics（注册时自报年龄，累计）")
    xs = [int(r["age"]) for r in sc]
    ys = [int(r["registered_users"]) / 1e6 for r in sc]
    bars = ax.bar(xs, ys, width=0.62, color=[BLUE if 9 <= x <= 15 else GREY for x in xs])
    ax.set_xticks(xs)
    ax.tick_params(axis="x", colors=INK2)
    ax.set_xlabel("注册时年龄", fontsize=8.5)
    ax.set_ylabel("注册用户（百万）", fontsize=8.5)
    style(ax, grid="y", baseline="bottom")
    legend(ax, [swatch(BLUE, "9–15 岁"), swatch(GREY, "其他年龄")], loc="upper right")
    round_bars(fig, ax, bars, horizontal=False, r=6)
    save(fig, "A6_scratch_signup_age.png")


def main():
    rank = rd(O("ranking.csv"))
    print("charts ->", os.path.relpath(OUT, ROOT))
    c01_top_earning_genre()
    c02_turnover()
    c03_reach_vs_retention()
    c04_web_vs_roblox(rank)
    c05_evidence(rank)
    c06_ranking(rank)
    c07_staged(rank)
    c08_sensitivity()
    c09_programme()
    c10_outcomes()
    c11_momentum()
    c12_coverage()
    c13_launch_timeline()
    if os.path.exists(D("age_segments.csv")):
        a1_age_mix()
        a2_reach()
        a3_value()
        a4_maturity_market()
        a5_maturity_archetype(rank)
        a6_scratch()


if __name__ == "__main__":
    main()
