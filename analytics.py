"""Impressions, product page views and conversion rate from the Analytics Reports API.

Reads the "App Store Discovery and Engagement Standard" and "App Downloads Standard"
reports of every ONGOING and ONE_TIME_SNAPSHOT request. Apple publishes the first
instances 1-2 days after a request is created; until then this returns `ready: False`.

Conversion rate follows App Store Connect: (first-time downloads + redownloads) /
unique impressions. Unique counts are summed across report rows, so they are an upper
bound of the true unique figure, the same caveat App Store Connect has across segments.
"""
import csv
import datetime as dt
import io
import json
import os
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import asc

CACHE = os.path.join(asc.CONFIG_DIR, "cache", "analytics")
ENGAGEMENT = "App Store Discovery and Engagement Standard"
DOWNLOADS = "App Downloads Standard"
DOWNLOAD_TYPES = {"First-time download", "Redownload"}
TTL = 3 * 3600  # Apple publishes once a day; listing every run is wasted calls
METRICS = ("impressions", "unique_impressions", "page_views", "downloads")


def instance_totals(cfg, instance_id, report_name):
    """Per (date, app) metric totals of one report instance; cached forever (immutable)."""
    path = os.path.join(CACHE, f"instance-{instance_id}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    out = defaultdict(lambda: defaultdict(int))
    for seg in asc.paginate(cfg, f"/v1/analyticsReportInstances/{instance_id}/segments"):
        tsv = asc.download(seg["attributes"]["url"]).decode()
        for r in csv.DictReader(io.StringIO(tsv), delimiter="\t"):
            key = f"{r['Date']}|{r['App Apple Identifier']}"
            counts, unique = int(r.get("Counts") or 0), int(r.get("Unique Counts") or 0)
            if report_name == ENGAGEMENT:
                if r["Event"] == "Impression":
                    out[key]["impressions"] += counts
                    out[key]["unique_impressions"] += unique
                elif r["Event"] == "Page view" and r["Page Type"] == "Product page":
                    out[key]["page_views"] += counts
            elif r.get("Download Type") in DOWNLOAD_TYPES:
                out[key]["downloads"] += counts
    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w") as f:
        json.dump(out, f)
    return out


def report_ids(cfg):
    """[(access_type, report_name, report_id)] for every app; cached a day (IDs are stable)."""
    path = os.path.join(CACHE, "reports.json")
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < 86400:
        with open(path) as f:
            return [tuple(x) for x in json.load(f)]

    def for_app(app):
        out = []
        for req in asc.paginate(cfg, f"/v1/apps/{app}/analyticsReportRequests"):
            for rep in asc.paginate(cfg, f"/v1/analyticsReportRequests/{req['id']}/reports",
                                    {"filter[name]": f"{ENGAGEMENT},{DOWNLOADS}"}):
                out.append((req["attributes"]["accessType"], rep["attributes"]["name"], rep["id"]))
        return out

    apps = [a["id"] for a in asc.paginate(cfg, "/v1/apps", {"fields[apps]": "name", "limit": 200})]
    with ThreadPoolExecutor(8) as pool:
        ids = [x for chunk in pool.map(for_app, apps) for x in chunk]
    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w") as f:
        json.dump(ids, f)
    return ids


def daily_totals(cfg):
    """{date: {app_id: {metric: n}}}; ONGOING wins over the snapshot for the same date/report."""
    def for_report(item):
        access, name, rid = item
        parts = [instance_totals(cfg, inst["id"], name) for inst in asc.paginate(
            cfg, f"/v1/analyticsReports/{rid}/instances", {"filter[granularity]": "DAILY", "limit": 200})]
        return access, name, parts

    by_source = {}  # (access_type, report_name) -> {date|app: metrics}
    with ThreadPoolExecutor(8) as pool:
        for access, name, parts in pool.map(for_report, report_ids(cfg)):
            bucket = by_source.setdefault((access, name), {})
            for part in parts:
                for key, m in part.items():
                    acc = bucket.setdefault(key, defaultdict(int))
                    for k, v in m.items():
                        acc[k] += v

    merged = {}
    for name in (ENGAGEMENT, DOWNLOADS):
        ongoing = by_source.get(("ONGOING", name), {})
        snapshot = by_source.get(("ONE_TIME_SNAPSHOT", name), {})
        for key in set(ongoing) | set(snapshot):
            src = ongoing if key in ongoing else snapshot
            merged.setdefault(key, defaultdict(int)).update(src[key])

    out = defaultdict(dict)
    for key, m in merged.items():
        date, app = key.split("|")
        out[date][app] = {k: m.get(k, 0) for k in METRICS}
    return out


def summarize(days, start=None, end=None):
    tot = defaultdict(lambda: defaultdict(int))
    for date, apps in days.items():
        if (start and date < start) or (end and date > end):
            continue
        for app, m in apps.items():
            for k, v in m.items():
                tot[app][k] += v
                tot["_all"][k] += v

    def block(m):
        ui = m.get("unique_impressions", 0)
        return {"impressions": m.get("impressions", 0), "page_views": m.get("page_views", 0),
                "downloads": m.get("downloads", 0),
                "conversion": round(100 * m.get("downloads", 0) / ui, 1) if ui else None}

    return {app: block(m) for app, m in tot.items()}


def collect():
    path = os.path.join(CACHE, "summary.json")
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < TTL:
        with open(path) as f:
            return json.load(f)
    days = daily_totals(asc.load_config())
    if not days:
        result = {"ready": False}
    else:
        last = max(days)
        today = dt.date.today()
        monday = (today - dt.timedelta(days=today.weekday())).isoformat()
        result = {"ready": True, "last_day": last, "first_day": min(days),
                  "day": summarize(days, last, last), "week": summarize(days, monday),
                  "all": summarize(days)}
    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w") as f:
        json.dump(result, f)
    return result
