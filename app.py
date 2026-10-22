"""Steam Game Recommender — Streamlit demo.

Run:  streamlit run app.py
Needs steam_recommender_model.joblib (exported by the notebook) in the same folder.

Besides the hybrid score, the app closes four gaps found in existing game recommenders:
  1. dislikes are used (never recommended, similar games pushed down)
  2. variety re-ranking (MMR) so the top list isn't full of near-duplicates
  3. a hidden-gems control against popularity bias
  4. practical filters: release year, price, rating, platform
and adds "describe the game you want": free-text search over the same TF-IDF space as the content model.
A Kids tab shows only age-appropriate games (Under 13 / 13–17): Steam community tags, plus Steam's official
age data if fetch_age_ratings.py was run, plus parent controls. The Kids lock in the sidebar applies it to every tab.

Layout: a dark streaming-service style ("Midnight Marquee", see themes.py). The #1 pick fills a big billboard,
and the rest comes in rows you scroll sideways: Top 10, "Because you liked X", Hidden gems, Newer games.
"""
import html
import json
import os
import re

import joblib
import numpy as np
import pandas as pd
import scipy.sparse as sp
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "steam_recommender_model.joblib")
OFFICIAL_PATH = os.path.join(HERE, "steam_age.json")        # optional: made once by fetch_age_ratings.py
OVERRIDES_PATH = os.path.join(HERE, "age_overrides.json")   # optional: saved by the parent controls in the Kids tab
RATINGS = ["Overwhelmingly Negative", "Very Negative", "Negative", "Mostly Negative", "Mixed",
           "Mostly Positive", "Positive", "Very Positive", "Overwhelmingly Positive"]

st.set_page_config(page_title="Next Game · Steam Recommender", page_icon="🎮", layout="wide")

from themes import theme_css


def H(markup: str):
    """Render raw HTML. Lines are de-indented so markdown never turns them into code blocks."""
    st.markdown("\n".join(line.strip() for line in markup.splitlines() if line.strip()), unsafe_allow_html=True)


esc = html.escape

H(theme_css())     # design: dark streaming-service layout (see themes.py)


# ============================================================== model
@st.cache_resource(show_spinner="Loading model…")
def load_model():
    m = joblib.load(MODEL_PATH)
    cat = m["catalog"].copy()
    dup = cat.title.duplicated(keep=False)                       # disambiguate duplicate titles
    cat["label"] = np.where(dup, cat.title + " (" + cat.item_id + ")", cat.title)
    players = cat.players.to_numpy().astype(float)
    cat["year"] = pd.to_numeric(cat.get("date_release", pd.Series(dtype=str)).astype(str).str[:4], errors="coerce")
    cat["rating_rank"] = cat["rating"].map({r: i for i, r in enumerate(RATINGS)}) if "rating" in cat else np.nan
    m["catalog"] = cat
    m["label_to_idx"] = {l: i for i, l in enumerate(cat.label)}
    m["user_idx"] = {u: i for i, u in enumerate(m["user_ids"])}
    m["popular_order"] = np.argsort(-players)
    m["pop_norm"] = np.log1p(players) / np.log1p(players.max())  # 0 = niche ... 1 = most popular
    m["gem_cut"] = np.quantile(players, 0.5)                      # below median fans = "hidden gem"
    m.setdefault("gap_defaults", {"lam": 0.5, "variety": 0.3, "gamma": 0.2})
    m["search"] = build_search(m)
    m["age"] = age_masks(cat)                                     # Kids section (tag rules)
    m["id_idx"] = {str(a): i for i, a in enumerate(cat.item_id)}
    norm = cat.title.str.lower().str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip()
    words = norm.str.split().str.len()
    m["title_norm"] = norm.to_numpy()
    # titles we look for inside a sentence: specific enough not to be ordinary words
    multi = (words >= 2) & (norm.str.len() >= 8) & ~((words == 2) & norm.str.startswith("the "))
    single = (words == 1) & (norm.str.len() >= 8) & (cat.players >= m["gem_cut"])
    m["title_cands"] = np.flatnonzero((multi | single).to_numpy())
    return m


# ============================================================== "describe the game you want" search
SYNONYMS = {
    "friends": "co-op online co-op multiplayer", "friend": "co-op online co-op multiplayer", "coop": "co-op",
    "scary": "horror", "creepy": "horror", "spooky": "horror", "funny": "comedy", "cosy": "cozy relaxing",
    "cozy": "cozy relaxing", "chill": "relaxing", "calm": "relaxing", "hard": "difficult", "tough": "difficult",
    "challenging": "difficult", "car": "racing driving", "cars": "racing driving", "soccer": "football soccer sports",
    "football": "football soccer sports", "space": "space sci-fi", "guns": "shooter", "shooting": "shooter fps",
    "story": "story rich", "farm": "farming sim", "farming": "farming sim", "survive": "survival",
    "solo": "singleplayer", "pixel": "pixel graphics", "base": "base building", "cards": "card game",
}


def _tok(t):
    return str(t).strip().lower().replace(" ", "_").replace("-", "_")


def build_search(m):
    """Index for free-text search. New model files ship the notebook's own TF-IDF vectorizers, so a sentence
    lands in exactly the same space as the games' content vectors (tags + description). Older files fall back
    to an index of tags built here."""
    if "tfidf_tags" in m:
        tv, dv, w = m["tfidf_tags"], m["tfidf_desc"], m.get("desc_weight", 0.5)
        X = m["X_content"]
        names = [t.replace("_", " ") for t in tv.get_feature_names_out()] + list(dv.get_feature_names_out())

        def vec(text, tags):
            return normalize(sp.hstack([tv.transform([" ".join(tags)]), w * dv.transform([text])]).tocsr())
    else:
        tv = TfidfVectorizer(token_pattern=r"[^ ]+", sublinear_tf=True)
        X = normalize(tv.fit_transform(m["catalog"].tags.apply(lambda ts: " ".join(_tok(t) for t in ts))))
        names = [t.replace("_", " ") for t in tv.get_feature_names_out()]

        def vec(text, tags):
            return normalize(tv.transform([" ".join(tags)]))
    clean = lambda t: re.sub(r"\s+", " ", re.sub(r"[()]", " ", t.replace("_", " "))).strip()   # football_(soccer) -> football soccer
    phrases = sorted(((clean(t), t) for t in tv.vocabulary_), key=lambda p: -len(p[0]))
    return {"X": X.tocsr(), "vec": vec, "phrases": phrases, "names": np.array(names)}


def understand(m, query):
    """Sentence -> (tag tokens found, games named in it)."""
    q = query.lower().replace("-", " ")
    extra = " ".join(SYNONYMS[w] for w in re.findall(r"[a-z]+", q) if w in SYNONYMS).replace("-", " ")
    qx = f" {q} {extra} "
    tags = [tok for phrase, tok in m["search"]["phrases"] if re.search(rf"\b{re.escape(phrase)}\b", qx)]
    qn = " " + re.sub(r"[^a-z0-9]+", " ", query.lower()) + " "
    found = [i for i in m["title_cands"] if f" {m['title_norm'][i]} " in qn]
    found = [i for i in found if not any(i != j and m["title_norm"][i] in m["title_norm"][j] for j in found)]
    return list(dict.fromkeys(tags)), found[:3]


def search(m, query, alpha, k, variety=0.0, gamma=0.0, allowed=None):
    S, cat = m["search"], m["catalog"]
    tags, titles = understand(m, query)
    q = S["vec"](query + " " + " ".join(t.replace("_", " ") for t in tags), tags)
    if q.nnz == 0 and not titles:
        return None
    n = len(cat)
    text = np.asarray((S["X"] @ q.T).todense()).ravel() if q.nnz else np.zeros(n)
    score = minmax(text) if q.nnz else np.zeros(n)
    score = score + 0.1 * (cat.rating_rank.fillna(4).to_numpy() / 8)          # small boost for well-reviewed games
    if titles:                                                                    # "like <game>": blend in the hybrid
        cf_n, cb_n = hybrid_parts(m, history_from_games(m, titles), alpha)
        like = alpha * cf_n + (1 - alpha) * cb_n
        score = 0.5 * score + 0.5 * like if q.nnz else like
        score[titles] = -np.inf
    if gamma > 0:
        score = score - gamma * m["pop_norm"]
    if allowed is not None:
        score[~allowed] = -np.inf
    if variety > 0:
        top = mmr(score, k, variety, m["X_content"])
    else:
        finite = np.flatnonzero(np.isfinite(score))
        top = finite[np.argsort(-score[finite])[:k]]

    whys = []
    for j in top:                                   # which words of the sentence this game matched most
        c = S["X"][j].multiply(q).tocsr()
        terms = S["names"][c.indices[np.argsort(-c.data)[:3]]] if c.nnz else []
        parts = []
        if len(terms):
            parts.append("Matches your words: <b>" + esc(" · ".join(terms)) + "</b>")
        if titles:
            parts.append("Similar to <b>" + esc(", ".join(cat.title.iloc[t] for t in titles)) + "</b>")
        whys.append("<br>".join(parts) or "Close match overall")
    shown = np.clip(score[top], 0, 1)
    return top, shown, whys, tags, titles


def minmax(v):
    finite = np.isfinite(v)
    lo, hi = v[finite].min(), v[finite].max()
    return (v - lo) / (hi - lo) if hi > lo else np.zeros_like(v)


def row_from(idx, n, weight=1.0):
    idx = list(idx)
    return sp.csr_matrix((np.full(len(idx), weight, dtype=np.float32), ([0] * len(idx), idx)), shape=(1, n))


def mmr(score, k, variety, X, n_cand=100):
    """Maximal Marginal Relevance: each next pick = relevance minus similarity to games already picked."""
    finite = np.flatnonzero(np.isfinite(score))
    if len(finite) == 0:
        return np.array([], dtype=int)
    cand = finite[np.argsort(-score[finite])[:n_cand]]
    rel = score[cand]
    rel = (rel - rel.min()) / (rel.max() - rel.min() + 1e-9)
    sim = (X[cand] @ X[cand].T).toarray()
    chosen = [0]
    closest = sim[0].copy()
    while len(chosen) < min(k, len(cand)):
        val = (1 - variety) * rel - variety * closest
        val[chosen] = -np.inf
        j = int(np.argmax(val))
        chosen.append(j)
        closest = np.maximum(closest, sim[j])
    return cand[chosen]


def hybrid_parts(m, history, alpha):
    X, S = m["X_content"], m["S_cf"]
    cf_n = minmax(np.asarray((history @ S).todense()).ravel())
    cb_n = minmax(np.asarray((normalize(history @ X) @ X.T).todense()).ravel())
    return cf_n, cb_n


def recommend(m, history, alpha, k, disliked=(), lam=0.5, variety=0.0, gamma=0.0, allowed=None):
    """history: 1 x n_games sparse row of weights (1 + log(1 + hours)). disliked: game indices."""
    X, S = m["X_content"], m["S_cf"]
    n = X.shape[0]
    cf_n, cb_n = hybrid_parts(m, history, alpha)
    match = alpha * cf_n + (1 - alpha) * cb_n                    # the hybrid score shown as "match"
    score = match.copy()

    disliked = [d for d in disliked if d not in set(history.indices)]
    if disliked and lam > 0:                                      # gap 1: use dislikes
        D = row_from(disliked, n)
        pen = alpha * minmax(np.asarray((D @ S).todense()).ravel()) \
            + (1 - alpha) * minmax(np.asarray((normalize(D @ X) @ X.T).todense()).ravel())
        score -= lam * pen
    if gamma > 0:                                                 # gap 3: hidden gems
        score -= gamma * m["pop_norm"]

    score[history.indices] = -np.inf
    if disliked:
        score[disliked] = -np.inf
    if allowed is not None:                                       # gap 4: filters
        score[~allowed] = -np.inf

    if variety > 0:                                               # gap 2: variety re-ranking
        top = mmr(score, k, variety, X)
    else:
        finite = np.flatnonzero(np.isfinite(score))
        top = finite[np.argsort(-score[finite])[:k]]

    # explanation: which liked game drives each recommendation most
    hist_idx, hist_w = history.indices, history.data
    S_hist = S[hist_idx]
    C_hist = (X[hist_idx] @ X[top].T).toarray() if len(top) else np.zeros((len(hist_idx), 0))
    reasons = []
    for col, j in enumerate(top):
        contrib = S_hist[:, j].toarray().ravel() * hist_w
        reasons.append(hist_idx[np.argmax(contrib)] if contrib.max() > 0 else hist_idx[np.argmax(C_hist[:, col])])
    return top, match[top], cf_n[top], cb_n[top], reasons


def history_from_games(m, idx):
    return row_from(idx, len(m["catalog"]), 1 + np.log1p(10))


# ============================================================== Kids section: age filter
# The dataset has no official age ratings (ESRB / PEGI), so we estimate them from Steam's community tags.
# Tags are ordered by player votes; the weakest few are often joke tags (FIFA 22 has "Sexual Content" at #20).
ADULT = {"Mature", "Nudity", "Sexual Content", "NSFW", "Hentai", "Gore", "Violent", "Blood",
         "Horror", "Psychological Horror", "Survival Horror", "Gambling"}
TEEN_BLOCK = ADULT | {"FPS", "Shooter", "Third-Person Shooter", "Looter Shooter", "Military", "War", "World War II",
                      "Zombies", "Assassin", "Crime", "Dark Fantasy"}
KIDS_BLOCK = TEEN_BLOCK | {"Fighting", "2D Fighter", "Beat 'em up", "Hack and Slash", "Battle Royale", "Dark", "Dark Humor",
                           "Romance", "Dating Sim", "Lovecraftian", "Psychological", "Thriller", "Vampire", "Demons",
                           "Werewolves", "Visual Novel", "Cyberpunk", "Dystopian", "Post-apocalyptic"}
FAMILY = {"Family Friendly", "Cute", "Cartoon", "Cartoony", "Colorful", "Educational", "Cozy", "Wholesome",
          "Relaxing", "LEGO", "Hand-drawn"}
BAD_TITLE = r"hentai|\bsex|nsfw|\bnude|naked|porn|xxx|lewd|erotic|waifu|18\+"
TRUST_TOP = 15      # 13–17: only the 15 most-voted tags count · under 13: every tag counts


def age_masks(cat):
    """True = suitable for that age group. Untagged games are always left out: we can't check them."""
    tags = cat.tags.apply(list)
    known = (tags.str.len() > 0).to_numpy() & ~cat.title.str.contains(BAD_TITLE, case=False, regex=True).to_numpy()
    teen = known & ~tags.apply(lambda ts: bool(set(ts[:TRUST_TOP]) & TEEN_BLOCK)).to_numpy()
    kids = teen & ~tags.apply(lambda ts: bool(set(ts) & KIDS_BLOCK)).to_numpy() \
                & tags.apply(lambda ts: bool(set(ts) & FAMILY)).to_numpy()
    return {"Under 13": kids, "13–17": teen}


@st.cache_resource(show_spinner=False)
def official_age(_m, mtime):
    """Steam's own age data (fetch_age_ratings.py): the required age set on the store page and its
    mature-content descriptors. Blocks a game for a band when Steam itself says it is too old for it.
    mtime is part of the cache key, so a re-fetched file is picked up without restarting."""
    with open(OFFICIAL_PATH, encoding="utf-8") as f:
        data = json.load(f)
    n = len(_m["catalog"])
    checked, age, mature = np.zeros(n, bool), np.zeros(n, int), np.zeros(n, bool)
    for app_id, d in data.items():
        j = _m["id_idx"].get(str(app_id))
        if j is not None and isinstance(d, dict):
            checked[j], age[j], mature[j] = True, int(d.get("age") or 0), bool(d.get("desc"))
    return {"checked": checked,
            "Under 13": checked & ((age > 0) | mature),       # any age gate or mature-content warning
            "13–17": checked & ((age > 13) | mature)}         # 15+/16+/17+/18+ or a mature-content warning


def read_overrides():
    try:
        with open(OVERRIDES_PATH, encoding="utf-8") as f:
            o = json.load(f)
    except (OSError, ValueError):
        o = {}
    return {"hide": [str(x) for x in o.get("hide", [])], "allow": [str(x) for x in o.get("allow", [])]}


def save_overrides(hide, allow):
    with open(OVERRIDES_PATH, "w", encoding="utf-8") as f:
        json.dump({"hide": hide, "allow": allow}, f, indent=1)


# ============================================================== components
# Steam serves game art from a public CDN. Each URL is listed twice (current + older path); with stacked CSS
# backgrounds the first image that exists covers the rest, and a coloured poster with the title sits underneath.
SHARED = "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{}/{}"
LEGACY = "https://cdn.akamai.steamstatic.com/steam/apps/{}/{}"
STORE = "https://store.steampowered.com/app/{}"
PLAY = ('<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 4.6v14.8a1 1 0 0 0 1.52.85l12.1-7.4a1 1 0 0 0 0-1.7'
        'L8.52 3.75A1 1 0 0 0 7 4.6z"/></svg>')
INFO = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">'
        '<circle cx="12" cy="12" r="9.5"/><path d="M12 11v6M12 7.6v.01"/></svg>')


def art(app_id, *files):
    a = esc(str(app_id))
    return ", ".join(f"url('{base.format(a, f)}')" for f in files for base in (SHARED, LEGACY))


def poster(app_id, angle=135):
    """Fallback colours: a stable hue per game, so every missing image still gets its own poster."""
    try:
        h = (int(app_id) * 137.508) % 360
    except ValueError:
        h = 210
    h2 = (h + 55) % 360
    return (f"--fb:radial-gradient(circle at 78% 22%, hsl({h:.0f} 75% 50% / .55), transparent 58%),"
            f"linear-gradient({angle}deg, hsl({h:.0f} 45% 17%), hsl({h2:.0f} 55% 9%))")


def price_txt(g):
    p = g.get("price_final")
    if p is None or pd.isna(p):
        return None
    return "Free" if p == 0 else f"${p:.2f}"


def mix_pct(alpha, c1, c2):
    """Share of the final score that came from players (CF) vs content."""
    a, b = alpha * float(c1), (1 - alpha) * float(c2)
    return 100 * a / (a + b) if a + b > 0 else 50.0


def tile(m, j, *, match=None, pa=None, why=None, portrait=False, progress=None, note=None, nope=False, delay=0):
    g = m["catalog"].iloc[j]
    files = ("library_600x900.jpg", "header.jpg") if portrait else ("header.jpg",)
    chips = []
    if nope:
        chips.append('<span class="chip nope">Disliked</span>')
    if g.players < m["gem_cut"]:
        chips.append('<span class="chip gem">Gem</span>')
    pr = price_txt(g)
    if pr and not portrait:
        chips.append(f'<span class="chip right">{pr}</span>')
    meta = []
    if match is not None:
        meta.append(f'<span class="mt">{match:.0%} match</span>')
    if pd.notna(g.get("year")):
        meta.append(f"<span>{int(g.year)}</span>")
    if note:
        meta.append(f"<span>{esc(note)}</span>")
    elif not portrait and isinstance(g.get("rating"), str):
        meta.append(f"<span>{esc(g.rating)}</span>")
    peek = ""
    if not portrait:
        tags = "<i>•</i>".join(esc(str(t)) for t in list(g.tags)[:4]) or "No tags"
        mix = ""
        if pa is not None:
            mix = (f'<div class="mix"><div class="a" style="width:{pa:.0f}%"></div><div class="b" style="width:{100 - pa:.0f}%"></div></div>'
                   f'<div class="mixl"><span>PLAYERS {pa:.0f}%</span><span>CONTENT {100 - pa:.0f}%</span></div>')
        peek = f'<div class="peek">{tags}{mix}</div>'
    prog = f'<div class="prog"><i style="width:{max(3, progress):.0f}%"></i></div>' if progress is not None else ""
    return f"""<a class="tile{' nope' if nope else ''}" href="{STORE.format(esc(g.item_id))}" target="_blank" style="--d:{delay}ms">
<div class="art" style="{poster(g.item_id)}">
<div class="ph">{esc(g.title)}</div>
<div class="img" style="background-image:{art(g.item_id, *files)}"></div>
{f'<div class="chips-top">{"".join(chips)}</div>' if chips else ""}
{peek}
{prog}
</div>
<div class="cap">
<div class="t">{esc(g.title)}</div>
{f'<div class="m">{"".join(meta)}</div>' if meta else ""}
{f'<div class="w">{why}</div>' if why else ""}
</div>
</a>"""


LOCK = None    # set when the Kids lock is on: games that may be named on screen


def shown_name(j):
    """A game's title, or None if the Kids lock hides it."""
    return None if (LOCK is not None and not LOCK[j]) else m["catalog"].title.iloc[j]


def because(m, j):
    name = shown_name(j)
    return f"Because you liked <b>{esc(name)}</b>" if name else "From their play history"


def rec_tiles(m, top, score, cf, cb, reasons, alpha, why=because):
    return "".join(tile(m, j, match=s, pa=mix_pct(alpha, c1, c2), why=why(m, r) if why else None, delay=i * 45)
                   for i, (j, s, c1, c2, r) in enumerate(zip(top, score, cf, cb, reasons)))


def top10(m, idx, scores=None, notes=None):
    out = []
    for r, j in enumerate(idx[:10], 1):
        s = None if scores is None else scores[r - 1]
        note = None if notes is None else notes[r - 1]
        out.append(f'<div class="t10" style="--d:{r * 55}ms"><span class="num"><span>{r}</span></span>'
                   f'{tile(m, j, match=s, portrait=True, note=note)}</div>')
    return "".join(out)


def shelf(title, inner, sub="", cls=""):
    if not inner:
        return ""
    return (f'<section class="shelf {cls}"><div class="sh">{title}{f" <small>{esc(sub)}</small>" if sub else ""}</div>'
            f'<div class="track">{inner}</div></section>')


def billboard(m, j, kicker, *, match=None, pa=None, blurb="", side=""):
    g = m["catalog"].iloc[j]
    meta = []
    if match is not None:
        meta.append(f'<span class="match">{match:.0%} match</span>')
    if pd.notna(g.get("year")):
        meta.append(f"<span>{int(g.year)}</span>")
    if isinstance(g.get("rating"), str):
        meta.append(f'<span class="box">{esc(g.rating.upper())}</span>')
    pr = price_txt(g)
    if pr:
        meta.append(f"<span>{pr}</span>")
    if bool(g.get("steam_deck", False)):
        meta.append('<span class="box">STEAM DECK</span>')
    if g.players < m["gem_cut"]:
        meta.append('<span class="gem">HIDDEN GEM</span>')
    desc = str(g.get("blurb", "") or "").strip()
    text = esc(desc) if desc else blurb
    tags = "<i>•</i>".join(esc(str(t)) for t in list(g.tags)[:5])
    mix = ""
    if pa is not None:
        mix = (f'<div class="bb-mix"><div class="lbl"><span>Why it\'s here</span><span><span class="nc">α</span> {m.get("alpha_now", "")}</span></div>'
               f'<div class="bar"><div class="a" style="width:{pa:.0f}%"></div><div class="b" style="width:{100 - pa:.0f}%"></div></div>'
               f'<div class="lbl"><span>Players {pa:.0f}%</span><span>Content {100 - pa:.0f}%</span></div></div>')
    return f"""<section class="billboard" style="{poster(g.item_id, 120)}">
<div class="bb-ghost">{esc(g.title)}</div>
<div class="bb-art" style="background-image:{art(g.item_id, 'library_hero.jpg', 'header.jpg')}"></div>
<div class="bb-copy">
<div class="bb-kicker">{kicker}</div>
<div class="bb-title">{esc(g.title)}</div>
<div class="bb-meta">{"".join(meta)}</div>
<div class="bb-blurb">{text}</div>
{f'<div class="bb-tags">{tags}</div>' if tags else ""}
<div class="bb-cta"><a class="btn play" href="{STORE.format(esc(g.item_id))}" target="_blank">{PLAY}View on Steam</a>{side}</div>
</div>
{mix}
</section>"""


def ghost(text):
    return f'<span class="btn ghost">{INFO}{text}</span>'


def label(text, sub=""):
    H(f'<div class="label">{esc(text)}{f" <small>{esc(sub)}</small>" if sub else ""}</div>')


def empty(title, text):
    H(f'<div class="empty"><b>{esc(title)}</b>{esc(text)}</div>')


def table_html(df, best_col=None, lower_better=(), plain=()):
    best = df[best_col].idxmax() if best_col else None
    head = "".join(f"<th>{esc(c)}</th>" for c in ["Model", *df.columns])
    body = ""
    for name, r in df.iterrows():
        cells = ""
        for c in df.columns:
            v = r[c]
            if pd.isna(v):
                cells += "<td>–</td>"
                continue
            top = df[c].min() if c in lower_better else df[c].max()
            cells += f'<td class="{"top" if v == top and c not in plain else ""}">{v:.4f}</td>'
        body += f'<tr class="{"best" if name == best else ""}"><td>{esc(name)}</td>{cells}</tr>'
    dense = " dense" if len(df.columns) > 6 else ""
    return f'<div class="mwrap"><table class="mtable{dense}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def mask_of(idx, n):
    out = np.zeros(n, dtype=bool)
    out[list(idx)] = True
    return out


# ============================================================== app
if not os.path.exists(MODEL_PATH):
    H(theme_css())
    empty("Model file not found", "Run the notebook, then put steam_recommender_model.joblib next to app.py.")
    st.stop()

m = load_model()
cat = m["catalog"]
N = len(cat)
dflt = m["gap_defaults"]
GEM = cat.players.to_numpy() < m["gem_cut"]

# age filter = tag rules, minus games Steam's official data rules out, plus/minus the parent controls
OFF = official_age(m, os.path.getmtime(OFFICIAL_PATH)) if os.path.exists(OFFICIAL_PATH) else None
OV = read_overrides()
HIDE = mask_of([m["id_idx"][i] for i in OV["hide"] if i in m["id_idx"]], N)
ALLOW = mask_of([m["id_idx"][i] for i in OV["allow"] if i in m["id_idx"]], N)
SAFE = {b: ((mk & ~OFF[b] if OFF else mk) | ALLOW) & ~HIDE for b, mk in m["age"].items()}

with st.sidebar:
    H('<div class="side-h">Kids lock</div>')
    lock_on = st.toggle("Age-appropriate games only, on every tab", key="lock")
    lock_band = None
    if lock_on:
        lock_band = st.segmented_control("Lock age group", list(SAFE), default="Under 13", key="lock_band") or "Under 13"
        LOCK = SAFE[lock_band]

    H('<div class="side-h" style="margin-top:1.2rem">Blend</div>')
    alpha = st.slider("α · players ↔ content", 0.0, 1.0, float(m["best_alpha"]), 0.05,
                      help="1.0 = only what similar players like · 0.0 = only similar tags and descriptions")
    H(f'<div class="note">Tuned best α on held-out data: <b>{m["best_alpha"]}</b></div>')

    H('<div class="side-h" style="margin-top:1.2rem">Discovery</div>')
    variety = st.slider("Variety", 0.0, 0.8, float(dflt["variety"]), 0.05,
                        help="Re-ranks the list so it isn't full of near-identical games (MMR). 0 = off.")
    gamma = st.slider("Hidden gems", 0.0, 0.6, float(dflt["gamma"]), 0.05,
                      help="Pushes very popular games down so smaller games get a chance. 0 = off.")
    lam = st.slider("Avoid games like my dislikes", 0.0, 1.0, float(dflt["lam"]), 0.05,
                    help="How strongly games similar to your disliked games are pushed down.")

    H('<div class="side-h" style="margin-top:1.2rem">Filters</div>')
    allowed = LOCK.copy() if lock_on else np.ones(N, dtype=bool)
    years = cat.year.dropna()
    if len(years):
        y0, y1 = int(years.min()), int(years.max())
        yr = st.slider("Release year", y0, y1, (y0, y1))
        if yr != (y0, y1):
            allowed &= cat.year.between(*yr).fillna(False).to_numpy()
    if "price_final" in cat:
        max_price = st.select_slider("Max price (USD)", ["Free", 5, 10, 20, 30, 40, 60, "Any"], value="Any")
        if max_price != "Any":
            cap = 0 if max_price == "Free" else max_price
            allowed &= (cat.price_final.fillna(0) <= cap).to_numpy()
    if "rating" in cat:
        min_rating = st.select_slider("Minimum Steam rating", ["Any"] + RATINGS[4:], value="Any")
        if min_rating != "Any":
            allowed &= (cat.rating_rank >= RATINGS.index(min_rating)).fillna(False).to_numpy()
    plats = [(c, n) for c, n in [("steam_deck", "Steam Deck"), ("mac", "Mac"), ("linux", "Linux")] if c in cat]
    if plats:
        need = st.multiselect("Must run on", [n for _, n in plats])
        for c, n in plats:
            if n in need:
                allowed &= cat[c].astype(bool).to_numpy()
    if not allowed.all():
        H(f'<div class="note">{allowed.sum():,} of {N:,} games match the filters</div>')

    H('<div class="side-h" style="margin-top:1.2rem">Results</div>')
    k = st.slider("Games per row", 6, 30, 12, 3, help="How many games each row (and the search) shows. Top 10 always shows 10.")
    H("""<div class="legend">
<div><span style="background:var(--cf)"></span>Players like you (collaborative)</div>
<div><span style="background:var(--cb)"></span>Similar content (tags + description)</div>
</div>""")

filt = None if allowed.all() else allowed
m["alpha_now"] = f"{alpha:.2f}"
ymax = int(years.max()) if len(years) else None

H(f"""<div class="topbar">
<div class="brand">Next<span>Game</span></div>
<div class="tb-meta">{f'<span class="lockbadge">Kids lock · {lock_band}</span>' if lock_on else ""}<span><b>{N:,}</b> games</span><span><b>{len(m['user_ids']):,}</b> demo players</span><span>hybrid · <span class="nc">α</span> <b>{alpha:.2f}</b></span></div>
</div>""")

tab1, tab_kids, tab0, tab2, tab3 = st.tabs(["Pick games", "Kids", "Describe it", "Explore a player", "How well it works"])


def personal_rows(history, liked, dis, seen, who="you", obj="you", base=None):
    """Extra rows under the top picks. Each row skips games already shown higher up the page."""
    rows = []
    base = allowed if base is None else base
    blocked = mask_of(seen | set(liked) | set(dis), N)
    for x in liked[:3]:
        t, s, c1, c2, r = recommend(m, history_from_games(m, [x]), alpha, k, dis, lam, variety, gamma, base & ~blocked)
        verb = "liked" if who == "you" else "played"
        rows.append(shelf(f"Because {who} {verb} <em>{esc(cat.title.iloc[x])}</em>", rec_tiles(m, t, s, c1, c2, r, alpha, why=None)))
        blocked[t] = True
    t, s, c1, c2, r = recommend(m, history, alpha, k, dis, lam, variety, gamma, base & GEM & ~blocked)
    rows.insert(1 if rows else 0, shelf(f"Hidden gems <em>for {obj}</em>", rec_tiles(m, t, s, c1, c2, r, alpha), "smaller games, big match"))
    blocked[t] = True
    if ymax:
        fresh = (cat.year >= ymax - 2).fillna(False).to_numpy()
        t, s, c1, c2, r = recommend(m, history, alpha, k, dis, lam, variety, gamma, base & fresh & ~blocked)
        rows.append(shelf(f"Newer games <em>for {obj}</em>", rec_tiles(m, t, s, c1, c2, r, alpha), f"released {ymax - 2}–{ymax}"))
    return rows


# ---------------------------------------------------------------- tab 1: home feed
with tab1:
    pool = m["popular_order"] if LOCK is None else m["popular_order"][LOCK[m["popular_order"]]]
    options = cat.label.iloc[pool].tolist()                         # most popular first (only safe games under the lock)
    c1, c2 = st.columns(2, gap="medium")
    picked = c1.multiselect("Games you enjoy", options, max_selections=10, key=f"pick_{lock_band}",
                            placeholder="Games you enjoy — e.g. ELDEN RING, Cyberpunk 2077, EA SPORTS FC 24…")
    disliked_labels = c2.multiselect("Games you didn't enjoy (optional)", [o for o in options if o not in picked],
                                     max_selections=10, key=f"dislike_{lock_band}",
                                     placeholder="Games you didn't like — we'll steer away from them")
    if picked:
        idx = [m["label_to_idx"][p] for p in picked]
        dis = [m["label_to_idx"][p] for p in disliked_labels]
        hist = history_from_games(m, idx)
        top, score, cf, cb, reasons = recommend(m, hist, alpha, 10 + k, dis, lam, variety, gamma, filt)
        if len(top):
            pa0 = mix_pct(alpha, cf[0], cb[0])
            g0 = cat.iloc[top[0]]
            blurb = (f"Recommended because you liked <b>{esc(cat.title.iloc[reasons[0]])}</b>. {pa0:.0f}% of this pick comes from "
                     f"players with taste like yours and {100 - pa0:.0f}% from similar tags and description.")
            sub = f"{len(idx)} liked" + (f" · {len(dis)} disliked" if dis else "")
            H(billboard(m, top[0], "<b>#1</b> Pick for you", match=score[0], pa=pa0, blurb=blurb,
                        side=ghost(f"{int(g0.players):,} fans · {g0.median_hours:.0f}h median"))
              + shelf('<span class="t10mark">TOP 10</span> Picks for you', top10(m, top, score), sub, cls="lift"))
            rows = [shelf("More picks <em>for you</em>", rec_tiles(m, top[10:], score[10:], cf[10:], cb[10:], reasons[10:], alpha))]
            rows += personal_rows(hist, idx, dis, set(top.tolist()))
            if dis:
                rows.append(shelf("You didn't enjoy", "".join(tile(m, d, nope=True, delay=i * 45) for i, d in enumerate(dis)),
                                  "we steer away from games like these"))
            H("".join(rows))
        else:
            empty("No games match these filters", "Loosen the filters in the sidebar.")
    else:
        order = m["popular_order"][allowed[m["popular_order"]]]
        if len(order):
            j0 = order[0]
            g0 = cat.iloc[j0]
            blurb = (f"Liked by <b>{int(g0.players):,}</b> players in our sample, with a median of {g0.median_hours:.0f} hours played. "
                     "Add a few games you love above and this page turns into your own feed.")
            H(billboard(m, j0, "<b>No.1</b> Most played in our data", blurb=blurb, side=ghost("Pick games above to personalise"))
              + shelf('<span class="t10mark">TOP 10</span> Most played', top10(m, order, notes=[f"{int(p):,} fans" for p in cat.players.iloc[order[:10]]]),
                      "in the dataset", cls="lift"))
            rr = cat.rating_rank.fillna(0).to_numpy()
            gems = np.flatnonzero(allowed & GEM & (rr >= 7))
            gems = gems[np.argsort(-cat.players.to_numpy()[gems])][:k]
            loved = np.flatnonzero(allowed & (rr >= 8))
            loved = loved[np.argsort(-cat.players.to_numpy()[loved])][:k]
            dates = cat.get("date_release", pd.Series([""] * N)).astype(str).to_numpy()
            newest = np.flatnonzero(allowed & (cat.players.to_numpy() >= m["gem_cut"]))
            newest = newest[np.argsort(dates[newest])[::-1]][:k]
            rows = [shelf("Hidden gems <em>players love</em>", "".join(tile(m, j, note=f"{int(cat.players.iloc[j]):,} fans", delay=i * 45) for i, j in enumerate(gems)),
                          "fewer fans · very positive reviews"),
                    shelf("Overwhelmingly <em>positive</em>", "".join(tile(m, j, delay=i * 45) for i, j in enumerate(loved))),
                    shelf("Newest <em>in the catalogue</em>", "".join(tile(m, j, delay=i * 45) for i, j in enumerate(newest)))]
            H("".join(rows))
        else:
            empty("No games match these filters", "Loosen the filters in the sidebar.")

# ---------------------------------------------------------------- Kids: only age-appropriate games, everywhere on the tab
KID_ROWS = [("Family <em>favourites</em>", {"Family Friendly"}),
            ("Play <em>together</em>", {"Local Co-Op", "Local Multiplayer", "Co-op", "Online Co-Op", "Split Screen", "Party Game"}),
            ("Cozy &amp; <em>creative</em>", {"Relaxing", "Cozy", "Wholesome", "Building", "Sandbox", "Crafting", "Farming Sim", "Life Sim"}),
            ("Puzzles &amp; <em>brain teasers</em>", {"Puzzle", "Logic", "Educational", "Puzzle Platformer"})]

with tab_kids, st.container(key="kids"):
    H('<div class="kids-head"><span class="kids-logo">kids</span><div><div class="page-h">Games for <em>younger players</em></div>'
      '<div class="page-sub">Every pick and every row on this tab only uses games that pass the age filter.</div></div></div>')
    c1, c2 = st.columns([1, 3], vertical_alignment="bottom")
    band = c1.segmented_control("Age group", list(SAFE), default="Under 13", key="kids_band") or "Under 13"
    safe = SAFE[band]
    kallow = allowed & safe
    korder = m["popular_order"][kallow[m["popular_order"]]]
    kpicked = c2.multiselect("Games they enjoy", cat.label.iloc[m["popular_order"][safe[m["popular_order"]]]].tolist(),
                             max_selections=10, key=f"kids_pick_{band}",
                             placeholder="Pick a few games they like — only age-appropriate games are listed")
    if kpicked:
        idx = [m["label_to_idx"][p] for p in kpicked]
        hist = history_from_games(m, idx)
        top, score, cf, cb, reasons = recommend(m, hist, alpha, 10 + k, [], lam, variety, gamma, kallow)
        if len(top):
            pa0 = mix_pct(alpha, cf[0], cb[0])
            g0 = cat.iloc[top[0]]
            blurb = (f"Because they liked <b>{esc(cat.title.iloc[reasons[0]])}</b>. Passes the <b>{band}</b> filter, "
                     f"and {pa0:.0f}% of this pick comes from players with the same taste.")
            H(billboard(m, top[0], f"<b>KIDS</b> Top pick · {band}", match=score[0], pa=pa0, blurb=blurb,
                        side=ghost(f"{int(g0.players):,} fans · {g0.median_hours:.0f}h median"))
              + shelf('<span class="t10mark">TOP 10</span> Picks for them', top10(m, top, score), band, cls="lift"))
            rows = [shelf("More picks <em>for them</em>", rec_tiles(m, top[10:], score[10:], cf[10:], cb[10:], reasons[10:], alpha))]
            rows += personal_rows(hist, idx, [], set(top.tolist()), obj="them", base=kallow)
            H("".join(rows))
        else:
            empty("No games match these filters", "Loosen the filters in the sidebar.")
    elif len(korder):
        j0 = korder[0]
        blurb = (f"The most played game in our data that passes the <b>{band}</b> filter. "
                 "Pick a few games they enjoy above and this page turns into their own feed.")
        H(billboard(m, j0, f"<b>KIDS</b> Most played · {band}", blurb=blurb, side=ghost("Age-filtered with Steam tags"))
          + shelf('<span class="t10mark">TOP 10</span> Most played', top10(m, korder, notes=[f"{int(p):,} fans" for p in cat.players.iloc[korder[:10]]]),
                  band, cls="lift"))
        tagsets = cat.tags.apply(set)
        rows = []
        for title, want in KID_ROWS:
            idx = np.flatnonzero(kallow & tagsets.apply(lambda ts: bool(ts & want)).to_numpy())
            idx = idx[np.argsort(-cat.players.to_numpy()[idx])][:k]
            rows.append(shelf(title, "".join(tile(m, j, delay=i * 45) for i, j in enumerate(idx))))
        H("".join(rows))
    else:
        empty("No games match these filters", "Loosen the filters in the sidebar.")
    if OFF is not None:
        official_line = (f"<b>Steam's official age data:</b> {OFF['checked'].sum():,} of the most-played games were also checked against the "
                         f"age and mature-content warnings set on their Steam store page; {(m['age'][band] & OFF[band]).sum():,} that the tags "
                         f"allowed were removed by it.")
    else:
        official_line = ("<b>Steam's official age data:</b> not added yet. Run <b>python fetch_age_ratings.py</b> once to also check "
                         "the most-played games against the age and mature-content warnings on their Steam store page.")
    override_line = (f" (parent controls: {HIDE.sum()} hidden, {ALLOW.sum()} always allowed)" if HIDE.any() or ALLOW.any() else "")
    H(f"""<div class="safety"><b>How we keep it age-appropriate</b>
<p>Our dataset has no official age ratings (ESRB / PEGI), so the filter uses Steam's community tags, which players vote on.</p>
<ul>
<li><b>13–17:</b> no games whose top {TRUST_TOP} tags include Mature, Nudity, Sexual Content, Gore, Violent, Blood, Horror or Gambling, and no shooters, war, zombie or crime games.</li>
<li><b>Under 13:</b> all of that, plus no fighting, romance, dark or horror-adjacent games, checked across every tag. The game must also be tagged as family-friendly, for example Family Friendly, Cute, Cartoon or Relaxing.</li>
<li>Games with no tags, or with adult words in the title, are always left out, because we can't check them.</li>
<li>If Steam's own store data says a game needs an age gate (Under 13) or is 15+ (13–17), or it carries a mature-content warning, it is removed even when the tags look fine.</li>
</ul>
<p>{official_line}</p>
<p><span class="count">{safe.sum():,} of {N:,} games</span> pass the {band} filter{override_line}. Tags and store settings can still be wrong,
so a parent can always hide or allow a specific game below, and the <b>Kids lock</b> in the sidebar applies the same filter to every tab.</p>
</div>""")
    all_labels = cat.label.iloc[m["popular_order"]].tolist()
    lab = lambda ids: [cat.label.iloc[m["id_idx"][i]] for i in ids if i in m["id_idx"]]
    with st.expander("Parent controls · always hide or always allow a game"):
        ov_hide = st.multiselect("Always hide from kids", all_labels, default=lab(OV["hide"]), key="ov_hide",
                                 placeholder="Games kids should never see, whatever the filter says")
        ov_allow = st.multiselect("Always allow", [x for x in all_labels if x not in ov_hide], default=[x for x in lab(OV["allow"]) if x not in ov_hide],
                                  key="ov_allow", placeholder="Games you have checked yourself and are happy with")
        if st.button("Save parent controls", type="primary"):
            save_overrides([str(cat.item_id.iloc[m["label_to_idx"][x]]) for x in ov_hide],
                           [str(cat.item_id.iloc[m["label_to_idx"][x]]) for x in ov_allow])
            st.rerun()
        H('<div class="note">Saved in <b>age_overrides.json</b> next to app.py. A hidden game is removed everywhere the age filter is used, '
          'including the Kids lock; an allowed game skips the filter for both age groups.</div>')

# ---------------------------------------------------------------- tab 0: describe the game you want
EXAMPLES = ["a relaxing farming game to play with friends", "hard dark fantasy with tough bosses",
            "story rich sci-fi RPG in space", "scary zombie survival with friends",
            "something like Stardew Valley but in space"]


def _use_example():
    if st.session_state.get("example"):
        st.session_state.q = st.session_state.example


with tab0:
    H('<div class="page-h">Describe the game <em>you want</em></div>'
      '<div class="page-sub">In your own words: a genre, a mood, who you play with, or a game you like.</div>')
    query = st.text_input("Describe the game you want", key="q", label_visibility="collapsed",
                          placeholder="e.g. a relaxing farming game to play with friends")
    st.pills("Try one", EXAMPLES, key="example", on_change=_use_example)
    if query.strip():
        res = search(m, query, alpha, k, variety, gamma, filt)
        if res is None:
            empty("No match for those words", "Try words like a genre, a mood or a game you like.")
        else:
            top, shown, whys, tags, titles = res
            chips = [f"<span>{esc(t.replace('_', ' '))}</span>" for t in tags[:10]]
            chips += [f"<span>like {esc(cat.title.iloc[t])}</span>" for t in titles]
            if chips:
                H('<div class="chips">Understood ' + "".join(chips) + "</div>")
            if len(top):
                grid = "".join(tile(m, j, match=s, why=w.replace("<br>", " · "), delay=i * 40)
                               for i, (j, s, w) in enumerate(zip(top, shown, whys)))
                H(f'<section class="shelf"><div class="sh">Top results <small>{len(top)} games</small></div><div class="grid">{grid}</div></section>')
            else:
                empty("No games match these filters", "Loosen the filters in the sidebar.")

# ---------------------------------------------------------------- tab 2: a real player from the dataset
with tab2:
    c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
    if "demo_user" not in st.session_state:
        st.session_state.demo_user = m["user_ids"][0]
    if c2.button("Random player", width="stretch", type="primary"):
        st.session_state.demo_user = m["user_ids"][np.random.randint(len(m["user_ids"]))]
    uid = c1.text_input("Player ID from the dataset", key="demo_user")
    if uid in m["user_idx"]:
        u = m["user_idx"][uid]
        row = m["R"][u]
        dis = m["D"][u].indices.tolist() if "D" in m else []
        order = np.argsort(-row.data)
        liked = row.indices[order]
        hours = np.expm1(row.data[order] - 1)
        mx = max(float(hours.max()), 1.0)
        hue = sum(map(ord, str(uid))) * 37 % 360
        H(f"""<div class="profile"><div class="avatar" style="--h:{hue}">{esc(str(uid)[-2:])}</div>
<div><div class="pname">Player {esc(str(uid))}</div>
<div class="pmeta">{len(liked)} liked · {hours.sum():,.0f} h played · {len(dis)} disliked</div></div></div>""")
        top, score, cf, cb, reasons = recommend(m, row, alpha, 10 + k, dis, lam, variety, gamma, filt)
        show = np.ones(len(liked), bool) if LOCK is None else LOCK[liked]          # Kids lock: don't show unsafe history
        hidden_n = int((~show).sum())
        cont_sub = f"{int(show.sum())} games they liked" + (f" · {hidden_n} hidden by Kids lock" if hidden_n else "")
        cont = "".join(tile(m, j, note=f"{h:,.0f} h played", progress=100 * h / mx, delay=i * 45)
                       for i, (j, h) in enumerate(zip(liked[show], hours[show])))
        dis_shown = [d for d in dis if LOCK is None or LOCK[d]]
        lock_msg = (f'<div class="lockmsg">All {hidden_n} games this player liked are hidden by the Kids lock. '
                    'Their recommendations below are still age-appropriate.</div>') if hidden_n and not cont else ""
        if len(top):
            pa0 = mix_pct(alpha, cf[0], cb[0])
            g0 = cat.iloc[top[0]]
            name = shown_name(reasons[0])
            blurb = ((f"Because they played <b>{esc(name)}</b>. " if name else "Picked from this player's play history. ")
                     + f"{pa0:.0f}% of this pick comes from players with the same taste and {100 - pa0:.0f}% from similar tags and description.")
            H(billboard(m, top[0], "<b>Up next</b> for this player", match=score[0], pa=pa0, blurb=blurb,
                        side=ghost(f"{int(g0.players):,} fans · {g0.median_hours:.0f}h median"))
              + (shelf("Continue playing", cont, cont_sub, cls="lift") or lock_msg))
            rows = [shelf('<span class="t10mark">TOP 10</span> Up next for them', top10(m, top, score)),
                    shelf("More picks <em>for them</em>", rec_tiles(m, top[10:], score[10:], cf[10:], cb[10:], reasons[10:], alpha))]
            rows += personal_rows(row, liked[show][:1].tolist(), dis, set(top.tolist()) | set(liked.tolist()), who="they", obj="them")
            if dis_shown:
                rows.append(shelf("Didn't click with them", "".join(tile(m, d, nope=True, delay=i * 45) for i, d in enumerate(dis_shown)),
                                  "their “not recommended” reviews"))
            H("".join(rows))
        else:
            H(shelf("Continue playing", cont, cont_sub) or lock_msg)
            empty("No games match these filters", "Loosen the filters in the sidebar.")
    elif uid:
        empty("Player not found", "Use the Random player button to load someone from the dataset.")

# ---------------------------------------------------------------- tab 3: evaluation
with tab3:
    H('<div class="page-h">How well <em>it works</em></div>'
      '<div class="page-sub">Offline tests from the notebook: 20% of each player\'s liked games were hidden, and each model had to find them.</div>')
    met = pd.DataFrame(m["metrics"]).set_index("model")
    ndcg = [c for c in met.columns if c.startswith("NDCG")][0]
    best = met[ndcg].idxmax()

    label("Offline evaluation", "20% OF EACH PLAYER'S LIKED GAMES HIDDEN")
    H(table_html(met, ndcg))

    label(ndcg, "HIGHER IS BETTER")
    mxv = met[ndcg].max() or 1
    bars = "".join(
        f'<div class="brow {"best" if n == best else ""}"><span>{esc(n)}</span>'
        f'<span class="btrack"><i style="width:{100 * v / mxv:.1f}%"></i></span><span class="v">{v:.3f}</span></div>'
        for n, v in met[ndcg].items())
    H(f'<div class="bars">{bars}</div>')

    if "gap_metrics" in m:
        gaps = pd.DataFrame(m["gap_metrics"]).set_index("model")
        label("Closing the gaps", "DISLIKES · VARIETY · HIDDEN GEMS")
        bad = [c for c in gaps.columns if c.startswith("DislikedHit")]
        H(table_html(gaps, None, lower_better=bad))
        H("""<div class="note" style="margin-top:.8rem">
<b>DislikedHit@10</b> — share of players shown a game they actually disliked (lower is better).
<b>Diversity@10</b> — how different the 10 games are from each other.
<b>Novelty@10</b> and <b>LongTail@10</b> — how much the list reaches beyond the most popular games.
</div>""")

    if "cold_metrics" in m:
        cold = pd.DataFrame(m["cold_metrics"]).set_index("model")
        label("The new-game test", "500 GAMES WITH NO REVIEWS")
        H(table_html(cold, None, plain=[c for c in cold.columns if c.startswith("NewInTop")]))
        H("""<div class="note" style="margin-top:.8rem">
500 games were hidden from training to act as brand-new releases. CF and Popularity cannot tell them apart;
content-based and the hybrid can, because they read each game's tags and description.
</div>""")

    H("""<div class="note" style="margin-top:1.6rem">
<b>Precision / Recall / NDCG / HitRate@K</b> — how well the hidden games are ranked in each player's top K.<br>
<b>Coverage</b> — share of the catalogue recommended to at least one player. Popularity scores well on accuracy
but shows everyone the same handful of games; the hybrid keeps accuracy while spreading recommendations across the catalogue.
</div>""")
