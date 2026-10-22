"""UI theme for the Steam recommender app: "Midnight Marquee".

A dark, cinematic streaming-service layout: a full-width billboard for the #1 pick, then rows of game
tiles you scroll sideways ("Top 10", "Because you liked X", "Hidden gems for you", "Continue playing").
Game art comes straight from Steam's public image CDN; every tile also has a coloured poster with the
game's title underneath, so the layout still looks right when an image is missing or offline.
"""

FONTS = ("https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800"
         "&family=Hanken+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap")

CSS = r"""
:root{
  --f-display:'Barlow Condensed', 'Arial Narrow', sans-serif; --f-body:'Hanken Grotesk', system-ui, sans-serif;
  --f-mono:'JetBrains Mono', ui-monospace, monospace;
  --bg:#0a0a0d; --panel:#14141a; --panel-2:#1d1d25; --line:#2a2a35; --line-soft:#1f1f28;
  --text:#f4f1ea; --muted:#aaa6b4; --dim:#706d7c;
  --accent:#ff5f2e; --accent-2:#ffb547; --on-accent:#0a0a0d; --match:#46e08a;
  --cf:#ff5f2e; --cb:#4cc2ff; --gutter:3.2vw;
}

/* ---------------------------------------------------------------- page */
html, body, .stApp, [data-testid="stAppViewContainer"]{ background:var(--bg) !important; color:var(--text); font-family:var(--f-body); }
.stApp{ background:radial-gradient(1100px 520px at 85% -8%, rgba(255,95,46,.10), transparent 60%), var(--bg) !important; }
.stApp::after{ content:""; position:fixed; inset:0; pointer-events:none; z-index:999990; opacity:.045; mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E"); }
[data-testid="stHeader"]{ background:transparent; }
.block-container{ padding:1.1rem var(--gutter) 4rem !important; max-width:100% !important; }
.stApp p, .stApp label, .stApp li{ font-family:var(--f-body); }
.nc{ text-transform:none !important; letter-spacing:0; }
::selection{ background:var(--accent); color:var(--on-accent); }

/* ---------------------------------------------------------------- sidebar + widgets */
[data-testid="stSidebar"]{ background:#0e0e13 !important; border-right:1px solid var(--line); }
[data-testid="stSidebar"] *{ color:var(--text); }
[data-testid="stWidgetLabel"] p{ color:var(--muted) !important; font-weight:500; font-size:.85rem; }
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="input"] > div, .stTextInput input{
  background:var(--panel) !important; color:var(--text) !important; border-color:var(--line) !important; border-radius:6px !important; }
[data-baseweb="popover"] ul, [data-baseweb="menu"]{ background:var(--panel-2) !important; }
[data-baseweb="tag"]{ background:var(--panel-2) !important; border:1px solid var(--line); border-radius:4px !important; }
[data-baseweb="tag"] span, [data-baseweb="tag"] svg{ color:var(--text) !important; fill:var(--text) !important; }
[data-testid="stSlider"] [role="slider"]{ background:var(--accent) !important; box-shadow:0 0 0 4px rgba(255,95,46,.18) !important; }
[data-testid="stSliderThumbValue"]{ color:var(--accent-2) !important; font-family:var(--f-mono); }
.stButton button{ border-radius:6px !important; font-weight:700; }
.stButton button[kind="primary"]{ background:var(--text) !important; color:var(--on-accent) !important; border:none !important; }
.stButton button[kind="primary"]:hover{ background:#fff !important; }
.stTextInput input{ font-size:1.05rem; padding:.75rem 1rem; }
[data-testid="stPills"] button{ background:var(--panel) !important; border:1px solid var(--line) !important; border-radius:999px !important; }
[data-testid="stPills"] button p{ color:var(--muted) !important; font-size:.82rem; }

.side-h{ font-family:var(--f-mono); font-size:.68rem; letter-spacing:.22em; color:var(--dim) !important; text-transform:uppercase; margin:.4rem 0 .1rem; }
.note{ color:var(--muted); font-size:.86rem; line-height:1.6; }
.note b{ color:var(--text); }
.legend{ display:flex; flex-direction:column; gap:.45rem; margin-top:.6rem; font-size:.82rem; color:var(--muted); }
.legend span{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:.5rem; vertical-align:middle; }

/* ---------------------------------------------------------------- top bar + nav */
.topbar{ display:flex; align-items:center; justify-content:space-between; gap:1rem; flex-wrap:wrap; margin-bottom:.15rem; animation:fade .6s ease both; }
.brand{ font-family:var(--f-display); font-weight:800; font-size:2.25rem; line-height:1; letter-spacing:.01em; text-transform:uppercase;
  background:linear-gradient(180deg, var(--accent-2), var(--accent) 70%); -webkit-background-clip:text; background-clip:text; color:transparent; }
.brand span{ color:var(--text); -webkit-text-fill-color:var(--text); margin-left:.12em; }
.tb-meta{ display:flex; gap:1.3rem; font-family:var(--f-mono); font-size:.72rem; letter-spacing:.08em; color:var(--dim); text-transform:uppercase; }
.tb-meta b{ color:var(--muted); font-weight:700; }
.tb-meta .lockbadge{ color:#0a0a0d; background:linear-gradient(135deg, #ffd43b, #36b9ff); padding:.2rem .55rem; border-radius:4px; font-weight:700; letter-spacing:.08em; }
[data-baseweb="tab-list"]{ gap:1.7rem; border-bottom:none !important; }
[data-baseweb="tab"]{ padding:.45rem 0 !important; background:transparent !important; }
[data-baseweb="tab"] p{ font-family:var(--f-body) !important; font-size:.95rem !important; font-weight:500; color:var(--muted) !important; transition:color .2s; }
[data-baseweb="tab"]:hover p{ color:var(--text) !important; }
[data-baseweb="tab"][aria-selected="true"] p{ color:var(--text) !important; font-weight:700; }
[data-baseweb="tab-highlight"]{ background:var(--accent) !important; height:2px !important; }
[data-baseweb="tab-border"]{ display:none; }

.picker-h{ font-family:var(--f-mono); font-size:.7rem; letter-spacing:.2em; color:var(--dim); text-transform:uppercase; margin:.4rem 0 -.3rem; }

/* ---------------------------------------------------------------- billboard (hero) */
.billboard{ position:relative; isolation:isolate; overflow:hidden; display:flex; align-items:flex-end;
  margin:.9rem calc(-1 * var(--gutter)) 0; min-height:500px; height:64vh; max-height:660px; background:var(--fb); }
.bb-ghost{ position:absolute; right:-2vw; top:8%; z-index:-3; font-family:var(--f-display); font-weight:800; text-transform:uppercase;
  font-size:clamp(7rem, 17vw, 16rem); line-height:.82; text-align:right; max-width:75%; color:transparent;
  -webkit-text-stroke:2px rgba(255,255,255,.13); overflow:hidden; }
.bb-art{ position:absolute; inset:0; z-index:-2; background-size:cover; background-position:center 22%; transform-origin:70% 40%;
  animation:drift 26s ease-in-out infinite alternate; }
.billboard::before{ content:""; position:absolute; inset:0; z-index:-1;
  background:linear-gradient(90deg, rgba(10,10,13,.94) 0%, rgba(10,10,13,.72) 30%, rgba(10,10,13,.12) 64%, transparent 80%),
             linear-gradient(0deg, var(--bg) 0%, rgba(10,10,13,.4) 22%, transparent 45%); }
.bb-copy{ position:relative; padding:0 var(--gutter) 6.8rem; max-width:min(680px, 92vw); }
.bb-copy > *{ animation:rise .7s cubic-bezier(.2,.8,.2,1) both; }
.bb-copy > :nth-child(2){ animation-delay:.08s } .bb-copy > :nth-child(3){ animation-delay:.16s }
.bb-copy > :nth-child(4){ animation-delay:.24s } .bb-copy > :nth-child(5){ animation-delay:.32s } .bb-copy > :nth-child(6){ animation-delay:.4s }
.bb-kicker{ display:flex; align-items:center; gap:.65rem; font-family:var(--f-mono); font-size:.72rem; letter-spacing:.24em; color:var(--accent-2); text-transform:uppercase; }
.bb-kicker b{ background:var(--accent); color:var(--on-accent); padding:.18rem .45rem .14rem; border-radius:3px; letter-spacing:.06em; font-weight:700; }
.billboard .bb-title{ font-family:var(--f-display) !important; font-weight:800 !important; font-size:clamp(2.8rem, 6.2vw, 5.8rem) !important; line-height:.88 !important;
  text-transform:uppercase; letter-spacing:-.005em; margin:.55rem 0 .85rem !important; padding:0 !important; color:var(--text) !important;
  text-shadow:0 6px 40px rgba(0,0,0,.55); }
.bb-meta{ display:flex; align-items:center; gap:.85rem; flex-wrap:wrap; font-size:.95rem; color:var(--text); }
.bb-meta .match{ color:var(--match); font-weight:700; }
.bb-meta .box{ border:1px solid rgba(244,241,234,.45); border-radius:3px; padding:.08rem .42rem; font-family:var(--f-mono); font-size:.66rem; font-weight:700; letter-spacing:.06em; }
.bb-meta .gem{ background:var(--cb); color:#04121c; border-radius:3px; padding:.1rem .45rem; font-family:var(--f-mono); font-size:.66rem; font-weight:700; letter-spacing:.06em; }
.bb-blurb{ color:#dedae4; font-size:1.03rem; line-height:1.55; margin:.95rem 0 0; max-width:560px;
  display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
.bb-blurb b{ color:var(--text); }
.bb-tags{ margin-top:.7rem; font-size:.85rem; color:var(--muted); }
.bb-tags i{ font-style:normal; color:var(--dim); margin:0 .45rem; }
.bb-cta{ display:flex; gap:.7rem; flex-wrap:wrap; margin-top:1.3rem; }
.btn{ display:inline-flex; align-items:center; gap:.6rem; padding:.72rem 1.5rem .72rem 1.25rem; border-radius:6px; font-weight:700; font-size:1.02rem;
  text-decoration:none !important; transition:transform .2s ease, background .2s ease; }
.btn:hover{ transform:translateY(-1px); }
.btn svg{ width:20px; height:20px; }
.btn.play, .btn.play:visited{ background:var(--text); color:var(--on-accent) !important; }
.btn.play:hover{ background:#fff; }
.btn.ghost{ background:rgba(110,110,125,.42); color:var(--text) !important; backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px); font-weight:600; }
.btn.ghost b{ font-weight:700; }
.bb-mix{ position:absolute; right:0; bottom:7rem; display:flex; flex-direction:column; gap:.35rem; min-width:200px;
  padding:.55rem var(--gutter) .55rem 1rem; background:rgba(10,10,13,.55); border-left:3px solid var(--accent); backdrop-filter:blur(6px);
  font-family:var(--f-mono); font-size:.68rem; letter-spacing:.1em; color:var(--muted); text-transform:uppercase; animation:fade 1s .5s ease both; }
.bb-mix .bar{ display:flex; height:4px; border-radius:4px; overflow:hidden; background:var(--panel-2); }
.bb-mix .bar .a{ background:var(--cf); } .bb-mix .bar .b{ background:var(--cb); }
.bb-mix .lbl{ display:flex; justify-content:space-between; gap:1rem; }

/* ---------------------------------------------------------------- rows ("shelves") */
.shelf{ position:relative; margin-top:1.15rem; }
.shelf.lift{ margin-top:-4.2rem; z-index:2; }
.lockmsg{ position:relative; z-index:2; margin-top:-3.6rem; padding:.7rem 1rem; border-left:3px solid #36b9ff; background:rgba(20,20,26,.75);
  border-radius:6px; color:var(--muted); font-size:.88rem; max-width:640px; }
.shelf .sh{ display:flex; align-items:baseline; gap:.7rem; margin:0 !important; padding:0 !important;
  font-family:var(--f-body) !important; font-weight:700 !important; font-size:1.22rem !important; color:var(--text) !important; letter-spacing:0; }
.shelf .sh em{ font-style:normal; color:var(--accent-2); }
.shelf .sh small{ font-family:var(--f-mono); font-weight:500; font-size:.68rem; letter-spacing:.14em; color:var(--dim); text-transform:uppercase; }
.shelf .sh .t10mark{ font-family:var(--f-display); font-weight:800; font-size:1.05rem; letter-spacing:.02em; color:var(--on-accent);
  background:var(--accent); padding:.05rem .4rem 0; border-radius:3px; line-height:1.2; }
.track{ display:flex; gap:.65rem; overflow-x:auto; overflow-y:hidden; scroll-snap-type:x proximity; scroll-padding-left:var(--gutter);
  padding:.85rem var(--gutter) 1.2rem; margin:0 calc(-1 * var(--gutter));
  scrollbar-width:thin; scrollbar-color:#34343f transparent;
  -webkit-mask-image:linear-gradient(90deg, transparent 0, #000 var(--gutter), #000 calc(100% - 5vw), transparent);
          mask-image:linear-gradient(90deg, transparent 0, #000 var(--gutter), #000 calc(100% - 5vw), transparent); }
.track::-webkit-scrollbar{ height:6px; } .track::-webkit-scrollbar-thumb{ background:#34343f; border-radius:6px; }

/* ---------------------------------------------------------------- tiles */
.tile, .tile:visited{ position:relative; flex:none; width:clamp(220px, 18.5vw, 300px); min-width:0; scroll-snap-align:start; color:var(--text) !important;
  text-decoration:none !important; animation:rise .55s cubic-bezier(.2,.8,.2,1) both; animation-delay:var(--d, 0ms); }
.art{ position:relative; aspect-ratio:460/215; border-radius:6px; overflow:hidden; background:var(--fb);
  transition:transform .32s cubic-bezier(.2,.8,.2,1), box-shadow .32s ease; }
.tile:hover .art{ transform:scale(1.055); box-shadow:0 22px 44px -14px rgba(0,0,0,.95), 0 0 0 2px var(--accent); }
.art .ph{ position:absolute; inset:0; display:flex; align-items:flex-end; padding:.65rem .8rem; font-family:var(--f-display); font-weight:800;
  font-size:1.38rem; line-height:.92; text-transform:uppercase; color:rgba(255,255,255,.9); letter-spacing:.005em; overflow:hidden; }
.art .img{ position:absolute; inset:0; background-size:cover; background-position:center; transition:transform .6s ease; }
.tile:hover .art .img{ transform:scale(1.04); }
.chips-top{ position:absolute; top:.45rem; left:.45rem; right:.45rem; display:flex; gap:.3rem; z-index:2; }
.chip{ font-family:var(--f-mono); font-weight:700; font-size:.6rem; letter-spacing:.08em; text-transform:uppercase; padding:.16rem .4rem;
  border-radius:3px; background:rgba(10,10,13,.78); color:var(--text); }
.chip.gem{ background:var(--cb); color:#04121c; }
.chip.nope{ background:#3a3a44; color:#d6d3dc; }
.chip.right{ margin-left:auto; }
.peek{ position:absolute; left:0; right:0; bottom:0; z-index:2; padding:1.6rem .7rem .6rem;
  background:linear-gradient(0deg, rgba(8,8,10,.96) 35%, rgba(8,8,10,.6) 70%, transparent); transform:translateY(102%);
  transition:transform .32s cubic-bezier(.2,.8,.2,1); font-size:.72rem; color:#e9e5ee; }
.tile:hover .peek{ transform:none; }
.tile:hover .art .ph{ opacity:0; transition:opacity .2s; }
.peek i{ font-style:normal; color:var(--dim); margin:0 .35rem; }
.peek .mix{ display:flex; height:4px; border-radius:4px; overflow:hidden; margin-top:.45rem; background:var(--panel-2); }
.peek .mix .a{ background:var(--cf); } .peek .mix .b{ background:var(--cb); }
.peek .mixl{ display:flex; justify-content:space-between; margin-top:.25rem; font-family:var(--f-mono); font-size:.58rem; letter-spacing:.06em; color:var(--muted); }
.prog{ position:absolute; left:.65rem; right:.65rem; bottom:.6rem; height:3px; border-radius:3px; background:rgba(255,255,255,.22); z-index:2; }
.prog i{ display:block; height:100%; border-radius:3px; background:var(--accent); }
.cap{ padding:.55rem .1rem 0; }
.cap .t{ font-weight:600; font-size:.93rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.cap .m{ display:flex; gap:.55rem; flex-wrap:wrap; margin-top:.12rem; font-size:.78rem; color:var(--muted); }
.cap .m .mt{ color:var(--match); font-weight:700; }
.cap .w{ margin-top:.2rem; font-size:.76rem; color:var(--dim); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.cap .w b{ color:var(--muted); font-weight:600; }
.tile.nope .art{ filter:grayscale(1) brightness(.6); }
.tile.nope:hover .art{ box-shadow:0 22px 44px -14px rgba(0,0,0,.95), 0 0 0 2px #55535f; }

/* Top 10 row: portrait art with big outlined rank numbers */
.t10{ --w:clamp(128px, 10.2vw, 168px); flex:none; display:flex; align-items:flex-start; scroll-snap-align:start;
  animation:rise .55s cubic-bezier(.2,.8,.2,1) both; animation-delay:var(--d, 0ms); }
.t10 .num{ height:calc(var(--w) * 1.5); display:flex; align-items:flex-end; font-family:var(--f-display); font-weight:800;
  font-size:calc(var(--w) * 1.85); line-height:.8; letter-spacing:-.04em; color:var(--bg); -webkit-text-stroke:3px #575563;
  margin-right:calc(var(--w) * -.17); user-select:none; transition:-webkit-text-stroke-color .3s; }
.t10 .num span{ display:block; transform:translateY(var(--nudge, 0)); }
.t10:hover .num{ -webkit-text-stroke-color:var(--accent); }
.t10 .tile{ width:var(--w); animation:none; z-index:1; }
.t10 .art{ aspect-ratio:2/3; }
.t10 .art .ph{ align-items:center; justify-content:center; text-align:center; font-size:1.5rem; padding:.8rem; }
.t10 .cap .t{ font-size:.85rem; }

/* search results grid */
.grid{ display:grid; grid-template-columns:repeat(auto-fill, minmax(232px, 1fr)); gap:1.5rem .9rem; margin-top:1rem; }
.grid .tile{ width:auto; }

/* ---------------------------------------------------------------- search + player pages */
.page-h{ font-family:var(--f-display); font-weight:800; font-size:clamp(2rem, 3.6vw, 3rem); line-height:.95; text-transform:uppercase; margin:1.1rem 0 .2rem; }
.page-h em{ font-style:normal; color:var(--accent); }
.page-sub{ color:var(--muted); font-size:.95rem; margin-bottom:.4rem; }
.chips{ display:flex; gap:.4rem; flex-wrap:wrap; align-items:center; margin:.6rem 0 0; font-family:var(--f-mono); font-size:.68rem; letter-spacing:.12em; color:var(--dim); text-transform:uppercase; }
.chips span{ font-family:var(--f-body); letter-spacing:0; text-transform:none; font-size:.82rem; color:var(--text); background:var(--panel); border:1px solid var(--line); padding:.2rem .65rem; border-radius:999px; }
.profile{ display:flex; align-items:center; gap:1rem; margin:1rem 0 0; }
.avatar{ width:58px; height:58px; border-radius:8px; display:grid; place-items:center; font-family:var(--f-display); font-weight:800; font-size:1.9rem;
  color:#fff; background:linear-gradient(135deg, hsl(var(--h) 75% 55%), hsl(calc(var(--h) + 50) 70% 35%)); box-shadow:0 10px 30px -10px hsl(var(--h) 80% 50% / .6); }
.pname{ font-family:var(--f-display); font-weight:700; font-size:1.6rem; line-height:1; text-transform:uppercase; }
.pmeta{ font-family:var(--f-mono); font-size:.72rem; letter-spacing:.08em; color:var(--muted); margin-top:.3rem; }
.empty{ border:1px dashed var(--line); border-radius:8px; padding:2.2rem; text-align:center; color:var(--muted); margin-top:1.2rem; background:rgba(20,20,26,.5); }
.empty b{ display:block; font-family:var(--f-display); font-weight:700; font-size:1.5rem; text-transform:uppercase; color:var(--text); margin-bottom:.2rem; }

/* ---------------------------------------------------------------- Kids tab (own, brighter accent colours) */
.st-key-kids{ --accent:#36b9ff; --accent-2:#ffd43b; --match:#7ee787; }
.kids-head{ display:flex; align-items:center; gap:1.2rem; margin-top:.9rem; }
.kids-head .page-h{ margin-top:0; }
.kids-logo{ flex:none; font-family:var(--f-display); font-weight:800; font-size:2.7rem; line-height:1; text-transform:lowercase; letter-spacing:.01em;
  padding:.18rem .85rem .3rem; border-radius:16px; color:#0a0a0d; transform:rotate(-5deg);
  background:linear-gradient(135deg, #ffd43b 0%, #ff8f3d 45%, #36b9ff 100%); box-shadow:0 14px 34px -14px rgba(54,185,255,.75); }
.safety{ margin-top:2rem; padding:1.1rem 1.3rem; border:1px solid var(--line); border-left:3px solid var(--accent); border-radius:8px;
  background:rgba(20,20,26,.6); color:var(--muted); font-size:.88rem; line-height:1.6; }
.safety > b{ font-family:var(--f-display); font-size:1.25rem; text-transform:uppercase; color:var(--text); letter-spacing:.01em; }
.safety p{ margin:.35rem 0; } .safety ul{ margin:.3rem 0 .4rem 1.1rem; padding:0; } .safety li{ margin:.2rem 0; }
.safety li b, .safety .count{ color:var(--text); font-weight:700; }

/* ---------------------------------------------------------------- metrics tab */
.label{ display:flex; align-items:center; gap:.8rem; margin:1.8rem 0 .8rem; font-family:var(--f-display); font-weight:700; font-size:1.45rem; text-transform:uppercase; color:var(--text); }
.label::after{ content:""; flex:1; height:1px; background:var(--line); }
.label small{ font-family:var(--f-mono); font-weight:500; font-size:.66rem; letter-spacing:.14em; color:var(--dim); }
.mwrap{ overflow-x:auto; border-radius:8px; border:1px solid var(--line); }
.mtable{ width:100%; border-collapse:collapse; font-size:.86rem; background:var(--panel); }
.mtable th{ text-align:right; font-family:var(--f-mono); font-size:.66rem; letter-spacing:.1em; color:var(--dim); font-weight:500; padding:.8rem 1rem;
  border:none !important; border-bottom:1px solid var(--line) !important; text-transform:uppercase; background:#101015; }
.mtable th:first-child, .mtable td:first-child{ text-align:left; }
.mtable td{ text-align:right; padding:.7rem 1rem; border:none !important; border-bottom:1px solid var(--line-soft) !important; font-family:var(--f-mono); color:var(--text); }
.mtable td:first-child{ font-family:var(--f-body); font-weight:600; white-space:nowrap; }
.mtable tr:last-child td{ border-bottom:none !important; }
.mtable tr.best td{ background:rgba(255,95,46,.09); }
.mtable tr.best td:first-child{ box-shadow:inset 3px 0 0 var(--accent); }
.mtable td.top{ color:var(--accent-2); font-weight:700; }
.mtable.dense th, .mtable.dense td{ padding:.6rem .55rem; font-size:.76rem; }
.mtable.dense th{ font-size:.6rem; letter-spacing:.04em; }
.bars{ display:flex; flex-direction:column; gap:.7rem; margin-top:.4rem; }
.brow{ display:grid; grid-template-columns:170px 1fr 70px; align-items:center; gap:.8rem; font-size:.86rem; color:var(--text); }
.btrack{ height:12px; background:var(--panel-2); border-radius:3px; overflow:hidden; }
.btrack i{ display:block; height:100%; border-radius:3px; background:#4a4856; animation:grow .9s ease both; transform-origin:left; }
.brow.best .btrack i{ background:linear-gradient(90deg, var(--accent), var(--accent-2)); }
.brow .v{ font-family:var(--f-mono); color:var(--muted); text-align:right; }

@keyframes rise{ from{ opacity:0; transform:translateY(16px); } to{ opacity:1; transform:none; } }
@keyframes fade{ from{ opacity:0; } to{ opacity:1; } }
@keyframes grow{ from{ transform:scaleX(0); } to{ transform:scaleX(1); } }
@keyframes drift{ from{ transform:scale(1.02); } to{ transform:scale(1.1) translate(-1%, 1%); } }
@media (prefers-reduced-motion: reduce){ *{ animation:none !important; transition:none !important; } }
@media (max-width:760px){
  .billboard{ min-height:440px; height:auto; } .bb-copy{ padding-bottom:2.2rem; } .bb-mix{ display:none; } .shelf.lift{ margin-top:0; }
  .brow{ grid-template-columns:110px 1fr 56px; } .tb-meta{ display:none; }
}
"""


def theme_css(name: str = "Midnight Marquee") -> str:
    return f"<style>@import url('{FONTS}');\n{CSS}</style>"
