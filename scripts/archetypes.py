#!/usr/bin/env python3
"""Mechanic archetypes — the unit of analysis for cross-platform arbitrage.

A web game title is not portable; its core loop is. Every collected game is mapped to one archetype
by `rx` (regex on the lower-cased title, first match in list order wins). Roblox supply is measured
with `rbx_q` (search queries) and `rbx_rx` (regex on the Roblox experience name that marks a result as
a *direct* competitor for the same core loop). `scratch_q` measures how much kids build/play the
mechanic on Scratch (audience closest to Roblox's).

Judgement fields (cost, screens) are the analyst's and are labelled as such in the report:
  mvp_h      (optimistic, likely, pessimistic) solo+AI hours to a playable, publishable MVP
  launch_h   extra hours from MVP to a monetised launch build (content, UI, shop, mobile polish)
  upkeep_h   hours / month to keep it alive if it gets traction
  rbx_genre  Roblox genre (L1 or L2 label as returned by Roblox) used for the monetisation multiplier
  screens    Stage-2 pass/fail screens, each an observable property of the loop:
     s5   rule is understood in ~5 s without text
     s10  first funny/satisfying event within ~10 s of control
     rep  a round/attempt is short and restart is instant (replay loop intrinsic, no meta needed)
     grief  'low' | 'med' | 'high' — can one hostile player ruin others' sessions?
     touch  works with 1-2 thumbs
     solo_ok  fun with 1 player online (matters at low CCU: empty servers kill multiplayer-only games)
     aud  audience overlap with Roblox's core (kids/teens) is plausible given where the web demand comes from
  origin     'web' | 'roblox' (the web versions are clones of Roblox hits — reverse flow) | 'mmo' etc.

Run this file to write data/archetypes.json.
"""
import json, os

A = []


def arch(id, zh, loop, rx, rbx_q, rbx_rx, scratch_q, mvp_h, launch_h, upkeep_h, rbx_genre,
         s5, s10, rep, grief, touch, solo_ok, aud, origin="web", note=""):
    A.append(dict(id=id, zh=zh, loop=loop, rx=rx, roblox_queries=rbx_q, rbx_rx=rbx_rx, scratch_q=scratch_q,
                  mvp_h=mvp_h, launch_h=launch_h, upkeep_h=upkeep_h, rbx_genre=rbx_genre,
                  screens=dict(s5=s5, s10=s10, rep=rep, grief=grief, touch=touch, solo_ok=solo_ok, aud=aud),
                  origin=origin, note=note))


Y, N = True, False

# ---- reverse-flow first so that web clones of Roblox hits are not counted as web-native demand
arch("rbx_reverse", "Roblox反向移植(偷脑腐/Obby/99夜)", "web clones of current Roblox hits",
     r"brainrot|\bobby\b|99 nights|steal a|steal an|\+1 speed|keyboard escape|tsunami|grow a garden|"
     r"murder mystery|roblox|robby|sprunki|squid game|squid:|squid escape|memerot|lucky block|脑腐",
     ["obby"], r"$^", [], (0, 0, 0), 0, 0, "Obby & Platformer", Y, Y, Y, "low", Y, Y, Y, origin="roblox",
     note="Evidence that web portals now clone Roblox hits within weeks; not an arbitrage source.")

arch("mmo_pet_social", "页游MMO/养成社区(洛克王国/赛尔号/奥比岛)", "persistent MMO, pet collection, social world",
     r"洛克王国|赛尔号|奥拉星|卡布西游|奥比岛|小花仙|西普大陆|龙斗士|造梦西游|造梦无双|造梦大乱斗|功夫派|皮卡堂|弹弹堂|"
     r"三国杀|生死狙击|火线精英|原神|迷你世界|我的世界|奥奇传说|神将世界|三国群英|touch|触动|天空之舞|bit heroes|"
     r"三国快打|美食大战老鼠|逃跑吧|全民枪神|全民主公|传奇|江湖|封神|剑侠",
     [], r"$^", [], (0, 0, 0), 0, 0, "RPG", N, N, N, "med", N, Y, Y, origin="mmo",
     note="Out of scope: multi-year live-service products, not minigames.")

arch("physics_random_duel", "随机物理双人对战(Basket/Soccer Random)",
     "one-button ragdoll athletes; first to 5; every point re-rolls field/ball/bodies",
     r"\b(basket|soccer|volley|boxing|hockey|football|pong) random\b|getaway shootout|rooftop snipers|wrestle (jump|bros)|"
     r"tug the table|soccer physics|flip duel|get on top|drunken (boxing|wrestle|duel)|ragdoll (hit|archers|chaos|arena|duel)|"
     r"puppet fighter|house of hazards|tube jumpers|basketbros|basket bros|soccer bros|football bros|hockey bros|"
     r"random 2 ?player|stick duel|duel of|疯狂的鸽子|ragdoll soccer|striker dummies|搞怪碰碰球|双人疯狂兔子",
     ["basket random", "soccer random", "ragdoll soccer", "wrestle jump", "rooftop snipers", "ragdoll duel",
      "physics soccer", "ball vs ball", "2 player ragdoll"],
     r"random|ragdoll.*(soccer|basket|duel|sport|football)|wrestle|rooftop sniper|getaway shootout|wobbly|ball vs ball|"
     r"floppy|goofy.*(soccer|ball)|physics.*(soccer|football|basket)",
     ["basket random", "soccer random", "getaway shootout"],
     (35, 60, 110), 60, 12, "Party & Casual", Y, Y, Y, "low", Y, N, Y)

arch("head_sports", "大头体育对战(Head Soccer/Basketball Stars)",
     "1v1 side-view arcade sport with big-head characters, power shots",
     r"head (soccer|ball|basket|sports)|sports heads|basketball (stars|legends)|football legends|soccer legends|"
     r"big head|head volley|street ?ball|街篮|热血篮球|tap-tap shots|basket and ball|cannon basketball",
     ["head soccer", "big head football", "basketball stars", "1v1 basketball", "2d soccer"],
     r"head (soccer|ball|football)|big head|1v1.*(basket|soccer)|basketball (stars|legends|rivals)|hoops|2d (soccer|basket)",
     ["head soccer", "basketball legends"],
     (40, 70, 130), 60, 12, "Sports", Y, Y, Y, "low", Y, N, Y)

arch("coop_duo_puzzle", "双人合作解谜平台(森林冰火人)",
     "two characters with complementary immunities/abilities must both reach exits; levers, plates, timing",
     r"fireboy|watergirl|fire and water|冰火人|冰娃|火娃|冰火|王子公主|王子与公主|money movers|粘液实验室|闪翼双星|"
     r"red and blue|red and green|blue and red|pico park|屁王兄弟|双刃战士|冷冻双侠|两个小人|双人逃亡|"
     r"小怪物探险|茶叶蛋大冒险|魔性兔子人|super bunny man|bad ice.?cream|坏蛋冰淇淋|冰淇凌坏蛋|duo survival|"
     r"little steps big troubles|3 pandas",
     ["fireboy and watergirl", "2 player obby", "2 player puzzle", "duo obby", "teamwork puzzles", "co-op puzzle",
      "fire and water obby", "chained together"],
     r"2[ -]?player|two player|duo|together|team ?work|co-?op|fire.*water|chained|carry .* together|couple|friend obby|"
     r"\[2p\]|2-3-4",
     ["fireboy and watergirl", "2 player platformer"],
     (45, 80, 150), 80, 20, "Obby & Platformer", Y, Y, Y, "low", Y, N, Y,
     note="Content treadmill: demand is per-level; each level is hand-built.")

arch("bike_trials", "物理越野摩托关卡(Moto X3M)",
     "2D physics bike, throttle/lean, short trap-filled tracks, 3-star times, instant restart",
     r"moto ?x3m|mx offroad|moto (extreme|trial|maniac|road)|bike (trial|stunt|race)|stunt bike|wheelie|dirt bike|"
     r"trial(s)? (bike|xtreme)|疯狂摩托|越野摩托|极限越野|摩托|自行车对战|super bike|impossible bike|turbo moto|"
     r"hill climb|drive mad|eggy car|jelly truck|doodle road|draw.*(bridge|road)|deadly descent|drive quest|"
     r"装载卡车|truck loader|疯狂过山车|rail in the air",
     ["moto x3m", "bike obby", "dirt bike obby", "obby but you're on a bike", "drive mad", "hill climb"],
     r"bike|moto|scooter|kart|skateboard|hill climb|drive mad|on a (bike|car|scooter|kart|skateboard)|unicycle|bmx",
     ["moto x3m", "hill climb racing"],
     (50, 90, 170), 80, 15, "Obby & Platformer", Y, Y, Y, "low", Y, Y, Y)

arch("ragdoll_gore_course", "布娃娃自残/受伤闯关(Happy Wheels/Short Life)",
     "ragdoll character through deadly obstacle course; comedy from dismemberment / damage score",
     r"happy wheels|short life|mutilate a doll|ragdoll playground|kick the buddy|whack your|stickman destruction|"
     r"break (your )?bones|ragdoll throw|turbo dismount|dismount|整蛊火柴人|handless|amy autopsy|elastic man|"
     r"ragdoll (sandbox|show)|playground|no pain no gain|spiderdoll|hit him",
     ["happy wheels", "broken bones", "ragdoll", "dismount", "ragdoll playground"],
     r"broken bones|ragdoll|dismount|happy wheels|break.*bones|fling",
     ["happy wheels", "ragdoll"],
     (40, 70, 130), 60, 12, "Physics Sim", Y, Y, Y, "low", Y, Y, Y,
     note="Roblox content-maturity limits gore; comedy must come from ragdoll, not blood.")

arch("troll_platformer", "陷阱/坑人平台(Level Devil/Only Up/Getting Over It)",
     "platformer whose level lies to you; or one long punishing climb; death is the joke",
     r"level devil|troll|cat mario|only up|getting over it|big tower tiny square|史上最坑|史上最贱|是男人就下|"
     r"只有一道门|going up|rage|unfair|devil level|i wanna|trap adventure|there is no game|achievement unlocked|"
     r"猫里奥|借力攀登|babel tower",
     ["level devil", "troll obby", "troll tower", "only up", "getting over it", "rage obby"],
     r"troll|only up|getting over it|level devil|rage|impossible|don't touch|trap|hardest obby|climb",
     ["level devil", "getting over it"],
     (30, 55, 100), 60, 12, "Obby & Platformer", Y, Y, Y, "low", Y, Y, Y)

arch("endless_runner", "三车道无尽跑酷(Subway Surfers/Temple Run)",
     "auto-run, swipe lanes/jump/slide, coins, speed ramps until you crash",
     r"subway surf|temple run|talking tom gold run|om nom run|酷跑|跑酷|runner|dino (run|dash|game)|dinosaur game|"
     r"tunnel rush|逃命的火鸡|jetpack|bus rush|rail rush|surfers|sky riders|slope(?! multi)|slope multiplayer|"
     r"crazy roll|ball fall|going balls|rolling ball|two ball 3d|color road|summer rider|snow rider|skytrip|aquapark|"
     r"stair race|tall man|sandwich runner|ice cream stack|count masters|count control|crowd run|blob runner|"
     r"toilet race|shape dudes|fun race|飞机障碍|萌少年",
     ["subway surfers", "endless runner", "temple run", "slope", "snow rider", "going balls", "tunnel rush"],
     r"subway|endless (run|runner)|temple run|slope|snow rider|sled|going balls|tunnel rush|infinite run|bobsled|"
     r"runner|rolling ball|marble",
     ["subway surfers", "slope"],
     (40, 70, 130), 70, 12, "Runner", Y, Y, Y, "low", Y, Y, Y)

arch("precision_platformer", "竞速/精准平台(Vex/OvO/Run 3)",
     "tight-control 2D/3D platformer with speedrun timers and many short stages",
     r"\bvex ?\d|\bovo\b|\brun ?[123]?\b$|^run\b|exit path|n game|parkour block|super meat|electric man|g-switch|"
     r"stickman (parkour|crazy box)|wall jumper|sticky ninja|candy jump|神奇小妖怪|炫酷旋转忍者|飞天忍者猫|neon challenge|"
     r"sprint league|world's hardest game|小鸭历险记|大嘴怪冒险|超级马里奥(?!水上)|super mario",
     ["parkour", "speed run", "run 3", "vex obby", "wall hop obby", "2d platformer"],
     r"parkour|speed ?run|wall ?hop|2d (obby|platformer)|difficulty chart|tower of|run 3|vex|flood escape",
     ["platformer", "parkour"],
     (50, 90, 170), 80, 15, "Obby & Platformer", Y, Y, Y, "low", Y, Y, Y)

arch("rhythm_auto_runner", "节奏自动跑酷(Geometry Dash)",
     "auto-scrolling one-button obstacle course synced to music; die-and-retry; user levels",
     r"geometry (dash|vibes|jump|arrow|neon|lite)|space waves|dancing line|rolling sky|beat (jump|dash)|tiles hop|"
     r"wave dash|impossible game|color tunnel|节奏",
     ["geometry dash", "beat bounce", "rhythm obby", "geometry dash obby", "wave obby"],
     r"geometry|\bgd\b|beat (bounce|dash)|rhythm.*(obby|runner|dash)|wave (obby|dash)|impossible (game|squares)|dash world",
     ["geometry dash", "geometry dash wave"],
     (45, 80, 150), 80, 15, "Runner", Y, Y, Y, "low", Y, Y, Y,
     note="Brand-driven: much of the demand is for Geometry Dash itself (trademark/trade-dress risk).")

arch("stickman_swing", "荡绳/抓钩过关(Stickman Hook)",
     "tap-and-hold to grapple the nearest anchor, release with momentum; flow-state swinging",
     r"stickman hook|hanger|swing(o| monkey| man)|spider (stick|swing)|rope (hero|swing|man)|hook (a|and)|grapple|"
     r"handulum|钢铁蜘蛛侠|amazing strange rope|web swing|fly this|蜘蛛侠",
     ["stickman hook", "swing obby", "grapple obby", "web swing", "spider swing", "rope swing obby"],
     r"swing|grappl|hook|web ?sling|spider|rope|zipline",
     ["stickman hook", "grappling hook"],
     (35, 60, 110), 60, 12, "Obby & Platformer", Y, Y, Y, "low", Y, Y, Y)

arch("io_eat_grow", "吞噬成长竞技场(agar/slither/hole.io/大鱼吃小鱼)",
     "move, eat smaller things/players, grow, get eaten; instant respawn",
     r"agar|slither|snake\.?io|snake vs|worms?\.?zone|little ?big ?snake|gulper|hole\.?io|holey|hole io|"
     r"大鱼吃小鱼|fish eat|eat.*grow|feeding frenzy|flyordie|fly or die|evoworld|evowars|stabfish|minigiants|"
     r"happy snakes|贪食蛇|贪吃蛇|蛇蛇大作战|吃水果的小蛇|snake game|^snake$|powerline|cubes 2048|growden|"
     r"eat the world|blob|吃豆豆|salmonz|duckpark|petnest|monkey tag io|you monster|dino simulator|meeland|"
     r"mope|chompers|snowball\.io|霸气的蠕虫|eating simulator|google snake",
     ["agar", "slither", "hole.io", "eat the world", "snake io", "eat blobs", "fish eat fish", "eat to grow"],
     r"agar|slither|snake|hole|eat (the|and|to|blob|fish|everything)|blob|devour|absorb|feed.*grow|fish.*eat|\.io",
     ["agar.io", "slither.io", "hole.io"],
     (40, 70, 130), 60, 12, "Party & Casual", Y, Y, Y, "low", Y, N, Y,
     note="Needs bots to feel alive at low CCU.")

arch("io_territory", "圈地/占领(paper.io/Hexanaut/领地之争)",
     "leave base, draw a loop, close it to claim area; trail is your weakness",
     r"paper\.?io|paperio|hexanaut|splix|tileman|defly|territor|领地|land grab|color fill|hexellent|openfront|frontwars|"
     r"conquer|pixel conquest",
     ["paper.io", "territory io", "claim territory", "hexanaut", "color the map", "conquer territory"],
     r"paper|territor|claim|hexa|conquer|paint the|color (the|war)|land|splat",
     ["paper.io", "territory"],
     (45, 80, 150), 60, 12, "Strategy", Y, Y, Y, "low", Y, N, Y)

arch("io_arena_shooter", "网页FPS/建造对枪/吃鸡(Shell Shockers/1v1.lol)",
     "browser FPS deathmatch / build-fight / battle royale",
     r"shell shockers|krunker|1v1|buildnow|veck\.io|kour|kirka|voxiom|cryzen|repuls|bullet force|hazmob|fragen|"
     r"forward assault|pixel warfare|skillwarz|poxel|fortzone|battle royale|winter clash|bodycamera|time shooter|"
     r"吃鸡|枪战|反恐|狙击|sniper|fps|shooter|counter craft|rush team|surviv\.io|battledudes|copter royale|"
     r"guns guns|bullet bros|方块世界|名枪|特工|blockade3d|assault bots|rescue six",
     ["1v1 build fight", "fps arena", "gun game", "battle royale"],
     r"rivals|arsenal|fps|1v1|gun|shooter|battle royale|sniper|duels", [],
     (150, 260, 450), 200, 40, "Deathmatch Shooter", Y, Y, Y, "med", N, N, Y,
     note="Roblox's most contested, studio-dominated genre; anti-cheat mandatory.")

arch("sandbox_voxel", "体素沙盒/多模式(Bloxd/Miniblox/MineFun)", "minecraft-like voxel sandbox with minigame modes",
     r"bloxd|miniblox|minefun|vectaria|cuberealm|paper minecraft|grindcraft|sandbox city|minecraft|craft(?!sman)|aground",
     ["minecraft", "voxel sandbox"], r"craft|voxel|block.*(world|build)|mine.*build", [],
     (200, 350, 600), 200, 40, "Sandbox", N, N, N, "med", N, Y, Y)

arch("kart_battle", "卡丁车道具乱斗(Smash Karts)", "small arena, drive, pick up weapon box, blow up others, 3-min rounds",
     r"smash karts|kart|碰碰车|bumper car|derby crash|demolition derby|crash karts|泡泡堂卡丁车|battle cars",
     ["smash karts", "kart battle", "bumper cars", "kart racing", "demolition derby"],
     r"kart|bumper|derby|crash.*car|car.*(battle|crush|smash)",
     ["smash karts", "mario kart"],
     (70, 120, 220), 100, 20, "Vehicle Sim", Y, Y, Y, "low", Y, N, Y)

arch("tank_maze_duel", "迷宫坦克弹射对战(坦克动荡/Tank Trouble)",
     "top-down tanks in a maze; bullets ricochet; one hit kills; 10-second rounds",
     r"tank trouble|坦克动荡|az tank|awesome tanks|tank stars|tanks? (battle|arena|mayhem|duel|fury)|坦克大战|3d坦克|全民坦克|"
     r"diep|hills of steel|经典90坦克|tank",
     ["tank trouble", "tank battle", "tank maze", "tank duel", "ricochet tanks", "diep"],
     r"tank|ricochet|diep",
     ["tank trouble", "tank game"],
     (40, 70, 130), 60, 12, "Action", Y, Y, Y, "low", Y, N, Y)

arch("bomberman", "炸弹人迷宫(Q版泡泡堂/Bomb It/Playing With Fire)",
     "grid maze, drop bombs, blast walls for power-ups, trap opponents",
     r"泡泡堂|bomb it|playing with fire|bomber|炸弹人|blast buddies|boom(?!erang)",
     ["bomberman", "bomb it", "bomber arena", "bomb maze", "playing with fire"],
     r"bomber|bomb (it|maze|arena)|blast|tnt (run|tag|rush)",
     ["bomberman"],
     (45, 80, 150), 60, 12, "Party & Casual", Y, Y, Y, "low", Y, N, Y)

arch("tower_defense", "塔防/植物大战僵尸", "place units along lanes/paths; waves; upgrade economy",
     r"植物大战僵尸|plants vs|bloons|tower defen|kingdom rush|皇家守卫军|皇城突袭|保卫萝卜|cursed treasure|守卫|守城|"
     r"creeper world|perfect tower|塔防|age of war|战争进化史|米拉奇战记|stick war|火柴人战争|城邦争霸|西游大战僵尸|"
     r"英雄防线|小猴子守城|war the knights|janissary|swords and sandals",
     ["tower defense", "plants vs zombies", "plants vs brainrots", "bloons"],
     r"tower defen|\btd\b|defense|plants vs|bloons", ["tower defense", "plants vs zombies"],
     (120, 200, 350), 160, 40, "Tower Defense", Y, N, N, "low", Y, Y, Y,
     note="Proven and monetises well on Roblox, but crowded with studios (22 of top-472 earners).")

arch("gold_miner_claw", "摆钩抓取时机(黄金矿工/Claw)",
     "swinging hook; press at the right moment; heavier loot reels slower; hit quota in 60 s; shop between rounds",
     r"黄金矿工|gold miner|claw master|claw|抓娃娃|dig gold miner|reel gold|钻头车挖宝石|挖地小子|gold dig",
     ["gold miner", "claw machine", "claw", "grab the gold"],
     r"gold miner|claw|grab.*gold|crane",
     ["gold miner", "claw machine"],
     (25, 45, 85), 50, 10, "Incremental Simulator", Y, Y, Y, "low", Y, Y, Y)

arch("fishing_timing", "钓鱼升级(Tiny Fishing)", "cast depth, hook as many as possible on the way up, upgrade line/depth",
     r"tiny fishing|fishing|钓鱼|海边钓鱼|fish(ing)? (master|life|tycoon)|the farmer",
     ["tiny fishing", "fishing simulator", "fisch"],
     r"fish(?!.*eat)", ["fishing game"],
     (60, 100, 180), 100, 25, "Incremental Simulator", Y, Y, Y, "low", Y, Y, Y,
     note="Fisch-era fishing sims are saturated on Roblox.")

arch("launch_distance", "发射飞行+升级(Learn to Fly/Burrito Bison/Dolphin Olympics)",
     "one launch input, watch flight, bounce/boost, earn by distance, buy upgrades, launch again",
     r"learn to fly|learn fly|burrito bison|toss the turtle|kitten cannon|dolphin olympics|crazy flips|golf orbit|"
     r"launch|flight|fly (far|away)|into space|rocket (toss|launch)|hobo launch|johnny upgrade|potty racers|"
     r"stone skipping|ragdoll cannon|shoot.*cannon|炮打|cannon|solipskier|accelerator|duck life space",
     ["learn to fly", "launch simulator", "cannon launch", "slingshot", "stone skipping", "how far can you fly",
      "launch yourself"],
     r"launch|cannon|sling|catapult|fly (far|race|for)|how far|skipping|yeet|throw (a|your|the)|kick .* (far|off)|"
     r"flight|glide",
     ["learn to fly", "burrito bison"],
     (25, 45, 85), 50, 15, "Incremental Simulator", Y, Y, Y, "low", Y, Y, Y)

arch("train_and_race", "养成训练→比赛(Duck Life)",
     "train stats with 20-second minigames, then auto-race rivals; stat gates tournaments",
     r"duck ?life|小鸭子游泳|pet race|race clicker|train.*race|olympics(?!.*dolphin)",
     ["duck life", "race clicker", "pet racing", "train and race", "speed training race"],
     r"duck life|race clicker|train.*(race|speed)|speed (race|run sim)|\+1 speed|racing sim|legends of speed",
     ["duck life"],
     (50, 85, 160), 80, 20, "Incremental Simulator", Y, N, N, "low", Y, Y, Y)

arch("time_mgmt_cooking", "订单制作/时间管理(老爹系列/烹饪)",
     "customers order, assemble item through stations against the clock, tips, shop upgrades",
     r"papa.?s |papa louie|老爹|cooking|cook|烹饪|蛋糕|食谱|汉堡|burger|pizza|bartender|coffee shop|lemonade|煎饼|甜甜圈|"
     r"restaurant|diner|monkey mart|my perfect hotel|farm frenzy|做饭|烤|奶油鸡|ice cream|cafe|bakery|"
     r"piece of cake|supermarket|goods master|school cleaning|robo cleaner|60 second burger",
     ["papa's pizzeria", "cooking game", "restaurant tycoon", "work at a pizza place", "my restaurant", "cafe"],
     r"restaurant|pizza|cook|cafe|bakery|burger|diner|kitchen|chef|sushi|bakeon", ["papa's pizzeria", "cooking"],
     (90, 150, 270), 120, 30, "Tycoon", Y, N, N, "low", Y, Y, Y,
     note="Roblox equivalents (restaurant tycoons, Work at a Pizza Place) are long-established.")

arch("idle_clicker", "放置/点击增量(Cookie Clicker/Idle Breakout)", "click, buy generators, prestige",
     r"clicker|idle|cookie|incremental|trimps|reactor|incremancer|增量|点击器|躺平模拟器|capybara|planet clicker|"
     r"tycoon|mining empire|startup|皇帝成长计划|mowing|lumber|mr\.? mine|heavy mining|成长计划|摆摊|cell to singularity",
     ["clicker simulator", "idle game", "incremental"],
     r"clicker|idle|incremental|\+1|simulator|tycoon", ["clicker", "idle game"],
     (40, 70, 130), 80, 30, "Incremental Simulator", Y, N, N, "low", Y, Y, Y,
     note="This IS the Roblox meta (72 Incremental + 75 Tycoon in top-472 earners). No arbitrage gap.")

arch("merge_drop", "合成掉落(Suika/2048/合成)", "drop/merge identical items into bigger ones; board fills up",
     r"suika|watermelon|2048|merge|合成|西瓜|mergest|knife merge|ball shooter 2048|stick merge|养了个羊|消灭星星|"
     r"block blast|blocky blast|tentrix|block ?buster|block blaster|tetris|方块|screw|sort|分装|color (stack|match|shape)|"
     r"tower swap|one line|goods|anycolor",
     ["suika", "watermelon game", "merge fruit", "2048", "block blast", "merge"],
     r"suika|watermelon|2048|merge|block blast|tetris|sort|stack", ["suika", "2048"],
     (25, 45, 85), 40, 8, "Match & Merge", Y, Y, Y, "low", Y, Y, N,
     note="Demand skews to adult casual/mobile; Roblox puzzle trending median CCU is the lowest of all genres.")

arch("classic_board_card", "棋牌/连连看/泡泡龙/麻将(传统休闲)", "classic tabletop, matching and card games",
     r"连连看|麻将|mahjong|斗地主|象棋|chess|五子|军棋|拖拉机|纸牌|solitaire|checkers|ludo|uno|four colors|crazy eights|"
     r"bubble (shoot|blast|storm)|祖玛|zuma|打豆豆|斗兽棋|飞行棋|tic tac toe|four in a row|mancala|hangman|word|"
     r"crossword|sudoku|minesweeper|jewel|match ?3|candy|domino|backgammon|trivia|quiz|guessr|brain test|"
     r"iq ball|bloxorz|sugar,? sugar|factory balls|civiballs|push the box|unpuzzle|multitask|塔罗|扑克|"
     r"master chess|对对碰|消除|小鳄鱼爱洗澡|cut the rope|water flow|thief puzzle|draw (to save|the ways)|save the doge|"
     r"帮鸟儿解冻|亚当|逃出|escape (game|room)|trace|hidden|find (me|the)|爸爸把我手机|家里的故事|机械迷城|"
     r"snail bob|wheely|蜗牛|河马饲养员|逗小猴|longcat|perfect shape|teleport master|hide the evidence|"
     r"大富翁|跑得快|泡泡龙|消你妹|snakes and ladders|connect 4|smarty bubbles|wood block|block champ|"
     r"what's the difference|guess the|darts|breakout",
     ["chess", "uno", "mahjong", "bubble shooter", "word game", "escape room"],
     r"chess|uno|mahjong|bubble|word|bingo|monopoly|sudoku|minesweeper|escape room", ["chess", "bubble shooter"],
     (30, 60, 120), 40, 8, "Puzzle", Y, N, Y, "low", Y, Y, N,
     note="Audience mismatch (adult casual). Kept in the database as a control group.")

arch("fruit_slice", "切割手感(切水果/Slice Master)", "swipe or tap-to-flip a blade through objects; juice + combo",
     r"切水果|fruit ninja|水果忍者|slice master|slice|切块|knife (hit|up|rain)|chop|cut it|slicing",
     ["fruit ninja", "slice master", "slicing simulator", "cut fruit", "knife flip"],
     r"slice|slicing|fruit ninja|cut (it|the|all)|chop|knife (flip|hit)|peel", ["fruit ninja", "slice master"],
     (25, 45, 85), 50, 10, "Incremental Simulator", Y, Y, Y, "low", Y, Y, Y)

arch("physics_destruction", "物理爆破/攻城(高楼爆破/Crush the Castle/星球毁灭)",
     "aim one shot / place charges; watch structure collapse; score by destruction",
     r"爆破|crush the castle|angry birds|demolition(?! derby)|destroy|destruction|planet smash|smash (the|city)|"
     r"tear blocks down|机器人攻城|siege|wrecking|bomb the|royal smash|kick lucky|pc breakdown|kill time in your office|"
     r"crazy office|domino peak|干掉太阳|愤怒的小鸟|build and crush|car crash simulator|sportcars crash",
     ["destroy the building", "demolition", "angry birds", "smash the city", "destruction simulator",
      "crush the castle"],
     r"destroy|destruct|demolit|smash|wreck|angry birds|break (the|a|everything)|nuke|explode|crush",
     ["angry birds", "destruction"],
     (35, 60, 110), 60, 12, "Physics Sim", Y, Y, Y, "low", Y, Y, Y)

arch("draw_guess_party", "你画我猜(skribbl/Draw This)", "one draws a prompt, others type guesses",
     r"skribbl|gartic|draw this|draw (it|and guess)|你画我猜|奇妙画板|沙画|color artist|coloring",
     ["draw it", "guess the drawing", "skribbl", "speed draw", "draw and guess"],
     r"draw|doodle|sketch|paint", ["draw and guess"],
     (60, 100, 180), 60, 12, "Party & Casual", Y, N, Y, "high", Y, N, Y,
     note="Free-draw + chat is a moderation and griefing liability.")

arch("hide_seek_prop", "躲猫猫/变身道具(Hide Online/Prop Hunt)", "hiders become props; seekers shoot; short rounds",
     r"hide online|prop (hunt|busters)|hunters and props|hide (and|n) (seek|paint)|躲猫猫|hide or|paint or hunt",
     ["hide and seek", "prop hunt"], r"hide|prop hunt|seek", ["hide and seek"],
     (60, 100, 180), 80, 15, "Party & Casual", Y, Y, Y, "med", Y, N, Y,
     note="Roblox natives (Hide and Seek Extreme etc.) long established.")

arch("tag_arena", "小场地追逐抓人(Tag)", "2-4 players, tiny platform arena, 'it' passes on touch, timer",
     r"^tag$|tag run|\btag\b(?! io)|freeze tag|duck duck|抓人|hot potato|timebomb|time bomb",
     ["tag", "untitled tag game", "freeze tag", "bomb tag", "hot potato"],
     r"\btag\b|hot potato|time ?bomb|infection", ["tag game"],
     (30, 55, 100), 60, 12, "Party & Casual", Y, Y, Y, "low", Y, N, Y)

arch("car_stunt_drift", "开放场地飙车/漂移/特技(Madalin/Drift Hunters/3D飙车)",
     "free-roam or lap driving, drift score, ramps",
     r"drift|madalin|stunt car|飙车|赛车|四驱|跑车|racing|racer|rally|traffic (rider|run)|highway|night city|"
     r"car (driver|circle)|polytrack|flying car|trackracing|drag racer|burnout|offroad|russian|truck driver|tuk tuk|"
     r"police chase|carnado|grand (city|extreme)|punk racing|极速飞车|水上摩托|公路汽车|货车|拉力赛|jetpack racing|"
     r"super star car|bus driver|ships 3d|real city|street car|air fighter|疯狂战车|完美漂移|车",
     ["drift", "stunt cars", "car racing", "drift simulator"],
     r"drift|racing|car|driving|drive", ["racing game"],
     (100, 180, 320), 140, 30, "Vehicle Sim", Y, Y, N, "low", N, Y, Y,
     note="Vehicle sims are an established, asset-heavy Roblox category (26 of top-472 earners).")

arch("parking_traffic_puzzle", "停车/交通疏导(Parking Fury/Traffic Jam)", "steer into bay without scratching / untangle jam",
     r"parking|停车|traffic jam|car out|traffic escape|unblock|my parking lot|clear the jam",
     ["parking", "traffic jam puzzle", "car parking", "parking jam"],
     r"parking|traffic|jam", ["parking"],
     (40, 70, 130), 50, 10, "Puzzle", Y, N, Y, "low", Y, Y, N)

arch("pool_billiards", "台球(8 Ball Pool/彩8对战)", "turn-based cue aiming, 1v1",
     r"8 ?ball|billiard|pool (live|club|game)|\bpool\b|台球|彩8|桌球|snooker",
     ["8 ball pool", "pool", "billiards"], r"8 ?ball|pool|billiard|snooker", ["8 ball pool"],
     (60, 100, 180), 60, 12, "Sports", Y, N, N, "low", Y, N, N)

arch("mini_golf", "迷你高尔夫", "aim/power putt through trick holes; party turn order",
     r"mini ?golf|golf|wonderputt|putt",
     ["mini golf", "golf", "super golf"], r"golf|putt", ["mini golf"],
     (55, 90, 170), 80, 15, "Sports", Y, Y, Y, "low", Y, Y, Y)

arch("penalty_freekick", "点球/任意球(Penalty Shooters/Free Kick)", "swipe to shoot, then keep; best of 5",
     r"penalty|free ?kick|world cup (kicks|soccer caps)|soccer skills|点球|任意球|soccer real|cg fc|no fault cup|"
     r"soccer caps|curve ball|retro bowl|football legends",
     ["penalty shootout", "free kick", "penalty kick", "football penalty"],
     r"penalty|free ?kick|shootout|goalkeeper|kick", ["penalty kick"],
     (35, 60, 110), 60, 12, "Sports", Y, Y, Y, "low", Y, Y, Y)

arch("racket_duel", "火柴人羽毛球/乒乓/网球对打", "side-view rally; move + swing timing; first to N",
     r"羽毛球|badminton|ping pong|table tennis|tennis|乒乓|网球|排球|volley(?! random)|沙滩球|pong(?! random)",
     ["badminton", "ping pong", "table tennis", "tennis", "volleyball 2d"],
     r"badminton|ping ?pong|table tennis|tennis|racket|paddle|volley", ["badminton", "pong"],
     (40, 70, 130), 60, 12, "Sports", Y, Y, Y, "low", Y, N, Y)

arch("stickman_brawler", "横版格斗/火柴人乱斗(死神VS火影/拳皇wing/Supreme Duelist)",
     "2D platform fighter, 1v1 or FFA, special moves; local 2P on web",
     r"死神vs火影|死神VS火影|拳王|拳皇|king of fighters|乱斗|格斗|妖尾|真人快打|铁拳|stick(man)? (fight|kombat|battle|clash|"
     r"duel|epic|arena|dragon)|supreme duelist|superfighters|super fighters|gun mayhem|疯狂小人战斗|混乱大枪战|"
     r"火柴人.*(决斗|格斗|战士|神器)|双人决斗|mechastick|karate|dragon fist|punch boxing|kakato|幻想纹章|"
     r"mad stick|magic battleground|disaster arena|party time|游戏明星大乱斗|英雄大作战|avatar fortress",
     ["stick fight", "supreme duelist", "2d fighting", "platform fighter", "stickman fight", "battlegrounds"],
     r"stick ?(fight|man)|duelist|2d fight|platform fighter|smash|battlegrounds|brawl", ["stickman fight", "street fighter"],
     (110, 180, 320), 140, 30, "Battlegrounds & Fighting", Y, Y, Y, "med", N, N, Y,
     note="Roblox Battlegrounds is studio-dominated (43 of top-472 earners); hit-detection netcode is costly.")

arch("run_gun_coop", "横版闯关射击/动作RPG(战火英雄/二战前线/勇者之路/造梦)",
     "side-scrolling shooter or beat-em-up with weapon unlocks, stages, bosses; 1-2P",
     r"战火英雄|strike force|二战前线|爆枪突击|合金|狼牙|未来战士|救世英雄|勇者之路|勇者之刃|勇闯地下城|dnf|西游战记|西游灭妖|"
     r"国王的勇士|三国小镇|plazma burst|metal slug|box ?head|load up and kill|madness|sift heads|ray part|hobo|"
     r"双箭头|机甲小子|变形金刚|骇客大战|火线风暴|突击对决|荒岛枪训|skull kid|swords & souls|epic battle fantasy|"
     r"mardek|cardinal quest|king's league|大冒险|超级火柴战士|乐高|梦幻超人|城市正义|卡西龙|gunblood|"
     r"scary teacher|kindergarten|fleeing the complex|escaping the prison|animator vs|khan kluay",
     ["side scroller shooter", "2d shooter", "metal slug", "strike force heroes"],
     r"2d (shooter|rpg)|side ?scroll|metal slug|run and gun", [],
     (180, 300, 520), 200, 40, "Action RPG", N, Y, N, "low", N, Y, Y,
     note="Content-heavy (stages, bosses, weapons). High cost per hour of play.")

arch("stealth_heist", "潜行偷盗(Bob the Robber)", "sneak past guards/cameras, pick locks, grab loot, exit",
     r"bob the robber|robber|thief|stealth|heist|burglar|troll thief|偷|dig out of prison|escape from prison|"
     r"barry prison|prison escape|逃狱",
     ["bob the robber", "stealth heist", "rob the house", "thief simulator", "prison escape"],
     r"rob|thief|heist|stealth|burglar|steal|prison|jail", ["bob the robber"],
     (70, 120, 220), 100, 20, "Adventure", Y, N, N, "low", Y, Y, Y,
     note="'Steal a ...' is the 2026 Roblox meta — demand proven but the meta is crowded.")

arch("upgrade_drive_zombies", "升级载具冲关(Earn to Die)", "drive until fuel ends, smash zombies, earn, upgrade, go further",
     r"earn to die|zombie (derby|road|drive|car)|road of the dead|drive.*zombie|dead paradise",
     ["earn to die", "zombie car", "drive through zombies", "dusty trip"],
     r"earn to die|zombie.*(car|drive|road)|dusty trip|road trip", ["earn to die"],
     (60, 100, 180), 90, 20, "Vehicle Sim", Y, Y, Y, "low", Y, Y, Y)

arch("artillery_turn", "回合抛物线对轰(Raft Wars/Worms/弹弹堂式)", "set angle+power, lob projectile, terrain/positions change",
     r"raft wars|worms(?!\.?zone| zone)|gunbound|ddtank|gravitee|tank stars|bow(man| master)|arrow challenge|apple shooter|"
     r"孤城神箭|大炮色彩|archer|archery|炮打气球|\\bangle|fortress fight",
     ["raft wars", "worms", "artillery", "bow duel", "archery duel"],
     r"artillery|worms|raft wars|bow|archer|archery|catapult duel", ["raft wars", "worms"],
     (50, 85, 160), 70, 12, "Strategy", Y, Y, Y, "low", Y, N, Y)

arch("dress_up_makeover", "换装/化妆/美甲", "pick outfit/makeup; (web) no fail state",
     r"dress ?up|makeover|make ?up|换装|装扮|化妆|美甲|美发|发型|面膜|公主|新娘|fashion|salon|nails|stylist|试衣|约会|"
     r"y2k|bestie|snapstyle|vortella|decor life|phone case|眼影|女孩的|小美|阿sue|美女|super dress|diva",
     ["dress up", "makeover", "fashion show"], r"dress|fashion|makeover|outfit|style", ["dress up"],
     (80, 130, 240), 150, 40, "Dress Up", Y, Y, Y, "low", Y, Y, Y,
     note="Dress To Impress owns this on Roblox; asset volume is the moat.")

arch("horror_escape", "恐怖逃生", "first-person hide/escape from pursuer",
     r"granny|horror|scary|backrooms|haunted|poppy playtime|five nights|fnaf|恐怖|鬼|among us|amogus|^murder$|murder mafia",
     ["horror", "escape horror"], r"horror|scary|backrooms|doors|granny", [],
     (120, 200, 360), 150, 30, "Survival", Y, N, N, "low", N, Y, Y,
     note="Roblox survival/horror is large and studio-contested (43 of top-472 earners).")

arch("minigame_collection", "双人/多人小游戏合集(MiniBattles/2-3-4 Player)",
     "random 20-60 s micro-duels, running score across rounds",
     r"minibattles|mini ?battles|2[- ]?3[- ]?4 player|12 mini|party games|mini games|minigames|retro sports|乐高游戏嘉年华|"
     r"dumb ways|warioware|游戏嘉年华|robby mini",
     ["2 player minigames", "minibattles", "epic minigames", "minigames", "party games"],
     r"minigame|mini ?game|party|microgame|slopware|endless games", ["minigames"],
     (80, 140, 260), 100, 25, "Minigame", Y, Y, Y, "low", Y, N, Y,
     note="Each minigame is its own small game: cost scales with count.")

arch("rhythm_music", "音游(FNF/钢琴块)", "hit notes on beat",
     r"friday night funkin|fnf|piano|节奏大师|钢琴|magic tiles|music catch|perfect piano|beat ?ball|blob opera|choir|opera",
     ["funky friday", "rhythm game", "piano tiles"], r"funk|rhythm|piano|beat", ["friday night funkin"],
     (80, 140, 250), 120, 25, "Music & Rhythm", Y, Y, Y, "low", Y, Y, Y,
     note="Music licensing risk; Funky Friday already holds the niche.")

arch("helix_stack_tap", "超休闲单指反应(Helix Jump/Stack/Flappy)", "one-tap timing with instant fail/retry",
     r"helix|stack(?! colors)|flappy|copter(?! royale)|color switch|knife hit|doodle jump|crossy|frogger|塔|"
     r"tap tap|ball jump|bounce|弹跳球|red ball|plonky|perfect|rise up|zigzag|stack colors|chicken scream",
     ["flappy bird", "helix jump", "stack tower", "crossy road", "doodle jump"],
     r"flappy|helix|stack|crossy|cross the road|doodle jump|tap", ["flappy bird", "doodle jump"],
     (20, 35, 70), 40, 8, "Party & Casual", Y, Y, Y, "low", Y, Y, Y,
     note="Great on web, weak on Roblox: no social surface, <2 min sessions.")


# Manual corrections after reading the top-260 franchises by demand index (regex cannot know that
# "Bubble Shooter" is not a shooter). Keys are lower-cased display titles.
OVERRIDES = {
    "bubble shooter": "classic_board_card", "pool bubbles": "classic_board_card",
    "twisted tangle": "classic_board_card", "penalty shooters 2": "penalty_freekick",
    "temple run 2": "endless_runner", "talking tom gold run": "endless_runner",
    "count masters: stickman games": "endless_runner", "red ball 4": "precision_platformer",
    "hills of steel": "artillery_turn", "tank stars": "artillery_turn",
    "avatar fortress fight 2": "artillery_turn", "bouncemasters": "launch_distance",
    "catapult king": "physics_destruction", "全民坦克大战": "mmo_pet_social",
    "retro bowl": "other", "scary teacher 3d": "other", "kindergarten": "other",
    "swords and sandals 2": "other", "the king's league: odyssey": "other", "multitask": "other",
    "human dominoes": "other", "disaster arena": "other", "gunblood": "other", "load up and kill": "other",
    "murder": "other",
    "claw master": "other",          # claw-machine roguelike (CrazyGames, Aug 2026), not a Gold Miner hook
}


# ---------------------------------------------------------------------------------------------------------
# Curated Roblox competitor matching. After reading the raw search results and the descriptions of the
# ambiguous experiences (2026-10-08), the first-pass `rbx_rx` patterns were replaced by (include, exclude)
# pairs so that "direct competitor" means "same core loop", not "shares a word".
# e.g. 'Ball VS Ball' is an auto-battler, not a physics duel; 'Tank Wars!' is a tycoon; 'Kick a Lucky Block'
# and 'Ping Pong Training' are launch-distance incrementals; 'Tank Game!' is a diep.io-like.
CURATED = {
    "physics_random_duel": (r"2d basketball|basket random|soccer random|ragdoll (soccer|basket|football|sport)|wobbly (soccer|sport)|"
                            r"floppy|goofy (soccer|sport)|rooftop snipers|getaway shootout|wrestle jump|random sports", r"arm wrestle"),
    "head_sports": (r"head soccer|head ball|head football|big head (soccer|ball|football)|2d soccer|basketball stars", r"$^"),
    "coop_duo_puzzle": (r"2[ -]?player.*obby|obby.*2[ -]?player|\[2 ?p(layer)?\]|duo\b|together|team ?work|fire.{0,4}water|"
                        r"water.{0,4}fire|chained|1 & 2 player|2-3-4|tank mates|bird buddy|drive it!|be my camera|dog walk|"
                        r"team .*(run|escape|breakout)",
                        r"tycoon|\brp\b|roleplay|guess|would you rather|steal|lifetogether|pizza|ice cream"),
    "bike_trials": (r"obby but you.?re on a|bike obby|skateboard (obby|of hell)|scooter obby|biker duo|bike downhill|dirt bike|"
                    r"bmx|kart of hell|unicycle|drive it!|grapple cart|bike of hell|motorcycle obby|moto obby",
                    r"empire|lifestyle|bikelife|world|evolution|tsunami|wideopen|animals|\+1"),
    "ragdoll_gore_course": (r"broken bones|break your (bones|friends)|ragdoll|dismount|fling (things|playground)|survive the slope",
                            r"tower|\brp\b|fighting|skydiving|stack|blood"),
    "troll_platformer": (r"troll obby|rage bait|level devil|getting over it|ball and axe|only up|mount kara|deadly obby|"
                         r"climb \[|troll .*tower|tower.*troll|impossible obby|rage obby|hardest obby", r"$^"),
    "endless_runner": (r"subway|endless run|temple run|\bslope\b|snow rider|\bsled|bobsled|^ski$|ski racing|ski or die|"
                       r"speed runner|slide 9|downhill|infinite run|tunnel rush|run or d(ie|ead)",
                       r"nyc subway|automated|marble|survive the slope|bike downhill|speed run 4"),
    "rhythm_auto_runner": (r"geometry|\bgd\b|beat bounce|poly dash|dash world|dashblox|electric dash|impossible (game|squares)|"
                           r"rhythm (obby|runner)|wave (obby|dash)", r"find the|defense|doomspire|elevator"),
    "stickman_swing": (r"swing|grappl|\bhook\b|web ?sling|zipline|spider-?man|rope",
                       r"jump rope|fish|kill|evolution|pickaxe|katana|simulator|survive|^spider$|hooked!"),
    "io_eat_grow": (r"agar|slither|snake|\bworm\b|worm odyssey|\bhole\b|be a hole|eat (the|blob|fish|everything)|blob|devour|absorb|"
                    r"fish eat|black hole|world\.io|cellular|be a tornado|tank game|^tanks!|diep",
                    r"scp|hole in the wall|fishing|tower|hungry|wormface|inchworm|cave"),
    "io_territory": (r"territor|paper\.?io|color\.io|paint\.io|color game|capture for|splat|hexa|land\.io|claim (the|land|tiles)",
                     r"conquer the world|rts|country"),
    "kart_battle": (r"kart (arena|wars|battle)|smash kart|bumper (cars|balls)|car battles|roblox karts|crash cars|kart racing|karting",
                    r"obby|of hell|\+1|tsunami|chocolate"),
    "tank_maze_duel": (r"tank trouble|ttank|ricochet|tank (fight|duel|maze|arena)|tanks? battle", r"fish tank|tank mates|merge|tycoon|train"),
    "bomberman": (r"bomber(man)?\b|bomb it|bomb maze|playing with fire|blast zone|super bomb survival|bomb arena", r"squadron|railway"),
    "gold_miner_claw": (r"gold miner|claw fishing|grab.*gold|claw machine|the claw|be a claw", r"\+1 claw"),
    "launch_distance": (r"stone skipping|egg skipping|launch|cannon vs|slingshot|catapult|fly (far|a glider)|how far|yeet|"
                        r"kick a lucky block|kick ball to space|hit a golf ball|ping pong training|throw (a|your|the)|glide tower|"
                        r"learn to fly|paper plane|\+1 .*throw|kick .* (far|off)|goal kick",
                        r"flight (simulator|world|master)|airport|pilot|project flight|airstrike|nuke|launch things"),
    "merge_drop": (r"suika|watermelon|2048|fruit game|merge fruit|block blast|tetris|color stack|stack the shapes|\bsort", r"merge a|army"),
    "fruit_slice": (r"fruit ninja|fruit samurai|slic(e|ing)|cut (stuff|a fruit|fruit)|chop", r"grass|cut it out|tree|engine"),
    "physics_destruction": (r"destroy|destruct|demolit|smash (the|a)|wreck|angry (birds|block)|car crushers|build and crush|crush",
                            r"merge a nuke|escape|animatronics"),
    "parking_traffic_puzzle": (r"parking (jam|panic|level)|car parking|draw parking|traffic (flow|jam|escape)|my parking lot|unblock",
                               r"clean|wideopen|roanoke|overtake|my parking lot|tycoon"),
    "pool_billiards": (r"8.?ball|billiard|snooker|pool (duels|classic|1v1|hall)", r"swimming|deep|dive|noodle|leave pool|clean|bowling"),
    "mini_golf": (r"mini ?golf|super golf|golf frenzy|realistic golf|crazy golf|deadly golf|dab golf|putt",
                  r"clean|picker|tycoon|training|lucky block|hit a golf ball|obby"),
    "penalty_freekick": (r"penalty|free ?kick|shootout|goalkeeper|winning penalty", r"lucky block|needoh|door"),
    "racket_duel": (r"racket|badminton|ping ?pong|table tennis|tennis|pong rivals|padel", r"training|volleyball"),
    "upgrade_drive_zombies": (r"earn to die|death race|zombie.*(car|drive|road)|drive.*zombie|dusty trip|road trip", r"$^"),
    "artillery_turn": (r"artillery|worms\b|raft wars|archery duel|bow (battle|arena)|catapult duel|gunbound",
                       r"hungry|worm tower|showcase|testing|bots"),
    "minigame_collection": (r"minigame|mini ?game|party games|machine party|endless games|scroll a game|slopware|microgame|"
                            r"violent party|party chaos|table (mini)?games",
                            r"daycare|pet party|murder party|friday night|make a party|mimic"),
    "helix_stack_tap": (r"flappy|helix|stack ball|crossy|cross (the|a) (road|street)|doodle jump|tap tap", r"stack the shapes|color stack"),
}
for _a in A:
    _a["rbx_ex"] = r"$^"
    if _a["id"] in CURATED:
        _a["rbx_rx"], _a["rbx_ex"] = CURATED[_a["id"]]
    # Stage-2 audience screen is overridden by Roblox's own evidence: pool (8 Ball Duels, 4.7k CCU) and
    # puzzle-stackers (Color Stack, Stack the Shapes, >1k CCU each) do find a Roblox audience.
    if _a["id"] in ("merge_drop", "pool_billiards", "parking_traffic_puzzle"):
        _a["screens"]["aud"] = True


def dump():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "data", "archetypes.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(A, f, ensure_ascii=False, indent=1)
    with open(os.path.join(root, "data", "archetype_overrides.json"), "w", encoding="utf-8") as f:
        json.dump(OVERRIDES, f, ensure_ascii=False, indent=1)
    print(len(A), "archetypes ->", path)


if __name__ == "__main__":
    dump()
