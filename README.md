# Roblox 玩法套利研究 — 数据与模型

主报告见 [REPORT.md](REPORT.md)。本目录的所有数字都可以用下面的脚本重新生成。

## 目录

| 路径 | 内容 |
|---|---|
| `REPORT.md` | 研究结论、方法、反方分析、MVP 验证方案、Go/No-Go 标准 |
| `CLAUDE_DOC.md` | Claude 文档版报告的 Markdown 导出（更短，四张图换成静态图） |
| `data/web_games_raw.csv` | 网页小游戏平台原始记录（每个 平台×榜单×游戏 一行，只记录平台自己公布的数字） |
| `data/games.csv` | **候选数据库**：去重后的游戏系列，一行一个，含各平台指标、标准化份额、玩法原型 |
| `data/archetypes.json` | 49 个玩法原型的定义、Roblox 检索词、成本三点估计、筛选项（由 `scripts/archetypes.py` 生成） |
| `data/archetype_overrides.json` | 人工修正的分类（同样由 `scripts/archetypes.py` 生成） |
| `data/archetype_demand.csv` | 每个原型的跨平台需求证据（标准化份额、广度、品牌依赖度、动量、Scratch 信号） |
| `data/roblox_charts.csv` | Roblox 官方榜单快照（Top Earning 472 款、Top Playing、Up-and-Coming、各类型 Trending） |
| `data/roblox_search_raw.csv` | 每个原型的 Roblox 检索结果（未过滤） |
| `data/roblox_competitors.csv` | 每个原型的直接竞品（一行一个体验：CCU、访问量、好评率、创建/更新日期） |
| `data/archetype_competition.csv` | 每个原型的竞争强度指标 |
| `data/roblox_genre_stats.csv` | Roblox 类型结构（Top Earning 席位、每 CCU 收入指数、新品数量） |
| `data/roblox_creator_portfolios.csv` | 头部竞品发行方名下的其他作品 |
| `data/scratch_signal.csv` | Scratch 上各玩法的儿童自制克隆浏览量 |
| `data/roblox_maturity.csv` | 每款 Roblox 游戏的内容分级标签（决定哪些年龄段能进入） |
| `data/age_reference.json` | 年龄相关的事实与假设，逐条标注来源 |
| `data/age_segments.csv` 等 | 年龄段分析的输出：各年龄段份额、可触达范围、分级构成、Scratch 注册年龄 |
| `data/model_params.json` | **全部模型参数**，每个都标注 measured / derived / assumed 及来源 |
| `out/ranking.csv` | 模型输出：每个原型的起量概率、收入、工时、每小时净值、风险调整价值、排名稳定性 |
| `out/sensitivity.csv` | 敏感性分析 |
| `out/programme.csv` | 连续做几个分阶段项目时的结果分布 |
| `out/outcomes.csv` | 每个原型按分阶段方式做一次的五种结局概率 |
| `out/report_tables.md` | 报告中所有表格的完整版 |
| `out/charts/*.png` | 19 张图（13 张主图，6 张年龄分析图） |

## 复现 / 更新

抓取和建库只用 Python 3 标准库。模型需要 numpy，画图需要 matplotlib；本机系统自带的 numpy 是坏的（缺 `numpy.random`），所以这两步在项目内的虚拟环境里跑：

```bash
python3 -m venv .venv && .venv/bin/pip install numpy matplotlib     # 只需一次

python3 scripts/01_collect_web.py        # 抓取小游戏平台（缓存在 .cache/web；加 --refresh 强制重抓）
python3 scripts/archetypes.py            # 生成 data/archetypes.json
python3 scripts/02_collect_roblox.py --charts --search   # Roblox 榜单 + 竞品检索（约 20 分钟）
python3 scripts/02b_collect_maturity.py  # 内容分级标签（约 10 分钟）
python3 scripts/03_scratch_signal.py     # Scratch 信号
python3 scripts/04_build_db.py           # 去重、分类、标准化 -> games.csv, archetype_demand.csv
python3 scripts/05_competition.py        # 竞争指标 -> archetype_competition.csv, roblox_genre_stats.csv
python3 scripts/05b_creator_portfolios.py   # 可选：头部竞品发行方的作品组合
.venv/bin/python scripts/06_model.py     # 蒙特卡洛 -> out/ranking.csv 等
python3 scripts/07_report_tables.py      # -> out/report_tables.md
python3 scripts/09_age_analysis.py       # 年龄段分析 -> data/age_*.csv, out/age_summary.json
.venv/bin/python scripts/08_charts.py    # -> out/charts/*.png
```

改假设：编辑 `data/model_params.json` 后重跑第 6、7 步。最值得先改的三个：`opportunity_wage_usd_h`（你一小时的机会成本）、`archetypes.py` 里各原型的 `mvp_h`（工时估计）、`prior_traction_odds`（起量先验）。

新增玩法：在 `scripts/archetypes.py` 里加一个 `arch(...)`，需要的话在 `CURATED` 里写竞品的包含／排除规则，然后从第 2 步重跑。

## 注意

- Roblox 的 CCU 是抓取时刻的快照，随时段和星期波动，重新抓取会得到不同的绝对值。
- 模型的随机数种子是固定的：数据不变时，重跑 `06_model.py` 得到完全相同的数字。
- 图表中文字体用 macOS 自带的 PingFang SC，其他系统需要改 `08_charts.py` 顶部的字体设置。
- python.org 版的 Python 在 macOS 上不带根证书，脚本改用系统的 `/etc/ssl/cert.pem`，证书校验保持开启。
- 17yy、GamePix、Gameflare、Newgrounds 返回 403，没有绕过；覆盖情况见报告第 3 节。
