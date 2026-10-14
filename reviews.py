"""Newest written customer reviews per app, with "new since last run" detection.

Uses GET /v1/apps/{id}/customerReviews. Not every API key role may read reviews; on
401/403 this returns {"available": False} and the rest of the menu is unaffected.
The first run only records what exists, so you are not flooded with old reviews.
"""
import json
import os
import urllib.error
from concurrent.futures import ThreadPoolExecutor

import asc

CACHE = os.path.join(asc.CONFIG_DIR, "cache")
SEEN = os.path.join(CACHE, "reviews-seen.json")
PER_APP = 10
LATEST = 8


def fetch(cfg, app_id):
    r = asc.request(cfg, f"/v1/apps/{app_id}/customerReviews", {
        "sort": "-createdDate", "limit": PER_APP,
        "fields[customerReviews]": "rating,title,body,reviewerNickname,createdDate,territory",
    })
    return r["data"], r.get("meta", {}).get("paging", {}).get("total", len(r["data"]))


def diff(reviews, seen):
    """Reviews whose id is not in `seen`; nothing on the very first run (seen is None)."""
    if seen is None:
        return []
    return [r for r in reviews if r["id"] not in seen]


def collect(apps):
    """apps: {app_id: name}."""
    cfg = asc.load_config()
    try:
        with ThreadPoolExecutor(8) as pool:
            results = dict(zip(apps, pool.map(lambda a: fetch(cfg, a), apps)))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return {"available": False, "reason": f"HTTP {e.code}: bu API anahtarının rolü yorumları okuyamıyor"}
        raise

    reviews, totals = [], {}
    for app, (data, total) in results.items():
        totals[app] = total
        for d in data:
            a = d["attributes"]
            reviews.append({"id": d["id"], "app": app, "app_name": apps[app], "rating": a.get("rating"),
                            "title": a.get("title") or "", "body": (a.get("body") or "")[:300],
                            "nickname": a.get("reviewerNickname") or "", "territory": a.get("territory") or "",
                            "date": (a.get("createdDate") or "")[:10]})
    reviews.sort(key=lambda r: r["date"], reverse=True)

    seen = None
    if os.path.exists(SEEN):
        with open(SEEN) as f:
            seen = set(json.load(f))
    new = diff(reviews, seen)
    os.makedirs(CACHE, exist_ok=True)
    with open(SEEN, "w") as f:
        json.dump(sorted((seen or set()) | {r["id"] for r in reviews}), f)

    return {"available": True, "total": sum(totals.values()), "per_app": totals,
            "latest": reviews[:LATEST], "new": new}
