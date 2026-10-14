"""Star ratings per app from Apple's public lookup API (no key needed).

Ratings are per storefront, so we query every storefront the app has downloads in
(plus us and tr), then combine them weighted by rating count. A small daily history
gives "new ratings in the last 7 days".
"""
import datetime as dt
import json
import os
import time
import urllib.parse
import urllib.request
from collections import defaultdict

import asc

CACHE = os.path.join(asc.CONFIG_DIR, "cache")
TTL = 12 * 3600
ALWAYS = ("us", "tr")
HISTORY_DAYS = 60


def lookup(ids, country):
    url = "https://itunes.apple.com/lookup?" + urllib.parse.urlencode({"id": ",".join(ids), "country": country})
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r).get("results", [])


def combine(per_country):
    """[(avg, count), ...] -> (weighted average, total count)."""
    total = sum(c for _, c in per_country)
    if not total:
        return None, 0
    return round(sum(a * c for a, c in per_country) / total, 2), total


def new_since(history, app, count, today, days=7):
    """Ratings gained since the newest history entry at least `days` old."""
    old = [d for d in history if d <= (today - dt.timedelta(days=days)).isoformat() and app in history[d]]
    if not old:
        return None
    return count - history[max(old)][app]


def collect(app_ids, storefronts):
    path = os.path.join(CACHE, "ratings.json")
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < TTL:
        with open(path) as f:
            return json.load(f)

    per_app = defaultdict(list)       # app -> [(avg, count)]
    countries = defaultdict(dict)     # app -> {cc: [avg, count]}
    for cc in sorted(set(storefronts) | set(ALWAYS)):
        try:
            results = lookup(app_ids, cc)
        except OSError:
            continue
        for r in results:
            n = r.get("userRatingCount") or 0
            if n:
                app = str(r["trackId"])
                per_app[app].append((r["averageUserRating"], n))
                countries[app][cc] = [r["averageUserRating"], n]
        time.sleep(0.3)  # the lookup API throttles bursts

    today = dt.date.today()
    hist_path = os.path.join(CACHE, "ratings-history.json")
    history = {}
    if os.path.exists(hist_path):
        with open(hist_path) as f:
            history = json.load(f)

    apps, all_pairs = {}, []
    for app in app_ids:
        avg, count = combine(per_app.get(app, []))
        all_pairs += per_app.get(app, [])
        apps[app] = {"average": avg, "count": count, "new_7d": new_since(history, app, count, today),
                     "countries": dict(sorted(countries[app].items(), key=lambda kv: -kv[1][1]))}
    avg, count = combine(all_pairs)

    history[today.isoformat()] = {a: v["count"] for a, v in apps.items()}
    cutoff = (today - dt.timedelta(days=HISTORY_DAYS)).isoformat()
    history = {d: v for d, v in history.items() if d >= cutoff}

    result = {"average": avg, "count": count, "apps": apps,
              "new_7d": sum(v["new_7d"] for v in apps.values() if v["new_7d"] is not None)
              if any(v["new_7d"] is not None for v in apps.values()) else None}
    os.makedirs(CACHE, exist_ok=True)
    with open(hist_path, "w") as f:
        json.dump(history, f)
    with open(path, "w") as f:
        json.dump(result, f)
    return result
