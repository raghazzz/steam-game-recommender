"""Fetch Steam's official age data for the Kids section.

For the most-played games in the model, this asks the Steam store for two things the publisher sets on
each game's store page:
  * required_age  - the age gate (0 = none, otherwise 13 / 15 / 16 / 17 / 18)
  * content_descriptors - mature-content warnings (1 some nudity or sexual content, 2 frequent violence or
    gore, 3 adults-only sexual content, 4 frequent nudity or sexual content, 5 general mature content)
and saves them in steam_age.json next to app.py. The app then removes a game from the Kids section when
Steam's own data says it is too old, even if its community tags looked fine.

Run once, from the project folder (the app does not need to be running):
    python fetch_age_ratings.py              # top 600 games, about 15 minutes
    python fetch_age_ratings.py --max 2000   # more games, about 50 minutes

Steam allows roughly one request every 1.5 seconds, so it is slow on purpose. You can stop it with
Ctrl+C at any time: progress is saved, and running it again skips the games already done.
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.request

import joblib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "steam_recommender_model.joblib")
OUT_PATH = os.path.join(HERE, "steam_age.json")
URL = "https://store.steampowered.com/api/appdetails?appids={}&cc=us&l=english"


def fetch(app_id):
    """{'age': int, 'desc': [ids]} for one game, or None if Steam has no store page for it."""
    req = urllib.request.Request(URL.format(app_id), headers={"User-Agent": "Mozilla/5.0 (student recommender project)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    entry = (data or {}).get(str(app_id)) or {}
    if not entry.get("success"):
        return None
    d = entry.get("data") or {}
    try:
        age = int(str(d.get("required_age", 0)).strip() or 0)
    except ValueError:
        age = 0
    ids = (d.get("content_descriptors") or {}).get("ids") or []
    return {"age": age, "desc": sorted(int(i) for i in ids)}


def save(done):
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(done, f)
    os.replace(tmp, OUT_PATH)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max", type=int, default=600, help="how many of the most-played games to check (default 600)")
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between requests (default 1.5)")
    args = ap.parse_args()

    if not os.path.exists(MODEL_PATH):
        raise SystemExit("steam_recommender_model.joblib not found - put it next to this script first.")
    cat = joblib.load(MODEL_PATH)["catalog"]
    order = np.argsort(-cat.players.to_numpy())[: args.max]
    wanted = [str(cat.item_id.iloc[i]) for i in order]

    done = {}
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as f:
            done = json.load(f)
    todo = [a for a in wanted if a not in done]
    print(f"{len(wanted) - len(todo)} of {len(wanted)} games already saved, {len(todo)} to fetch "
          f"(about {len(todo) * args.delay / 60:.0f} minutes). Ctrl+C stops safely.")

    try:
        for n, app_id in enumerate(todo, 1):
            for attempt in range(4):
                try:
                    done[app_id] = fetch(app_id)
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 429:                              # too many requests: Steam asks us to slow down
                        print("  Steam asked us to slow down - waiting 60 seconds...")
                        time.sleep(60)
                    else:
                        done[app_id] = None
                        break
                except (urllib.error.URLError, TimeoutError, ValueError):
                    time.sleep(5 * (attempt + 1))                  # network hiccup: wait and retry
            if n % 25 == 0:
                save(done)
                print(f"  {n}/{len(todo)} fetched")
            time.sleep(args.delay)
    except KeyboardInterrupt:
        print("\nStopped - progress saved. Run the script again to continue.")
    finally:
        save(done)

    found = [v for v in done.values() if isinstance(v, dict)]
    gated = sum(v["age"] > 0 for v in found)
    warned = sum(bool(v["desc"]) for v in found)
    print(f"\nSaved {OUT_PATH}\n{len(found)} games with store data: {gated} have an age gate, "
          f"{warned} have mature-content warnings. Restart the app (or refresh) to use it.")


if __name__ == "__main__":
    main()
