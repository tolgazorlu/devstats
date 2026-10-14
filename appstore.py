"""App Store downloads from Sales reports: last report day, this week, all time.

All time = YEARLY reports for past years + MONTHLY for finished months + DAILY for the
current month. A period whose report is not published yet falls back to the finer level.
"""
import calendar
import csv
import datetime as dt
import io
import json
import os
import urllib.error
from collections import defaultdict

import asc

CACHE = os.path.join(asc.CONFIG_DIR, "cache")
FIRST_YEAR = 2024
VERSION = {"DAILY": "1_1", "MONTHLY": "1_0", "YEARLY": "1_0"}
# A 404 ("no sales") is only trusted once the period is this many days old;
# before that the report may simply not be published yet.
GRACE = {"DAILY": 4, "MONTHLY": 8, "YEARLY": 15}
ONE_DAY = dt.timedelta(days=1)
SERIES_DAYS = 7

# Apple product type identifiers
KIND = {}
KIND.update({t: "new" for t in ("1", "1F", "1T", "F1", "1E", "1EP", "1EU")})
KIND.update({t: "re" for t in ("3", "3F", "3T", "F3")})
KIND.update({t: "upd" for t in ("7", "7F", "7T", "F7")})
KIND.update({t: "iap" for t in ("IA1", "IA9", "IAY", "IAC", "FI1", "IA1-M", "IA9-M", "IAY-M")})
KINDS = ("new", "re", "upd", "iap")
FIELDS = ("Product Type Identifier", "Units", "SKU", "Parent Identifier", "Apple Identifier")


def fetch(cfg, freq, key, period_end):
    """Rows of a SALES SUMMARY report, [] for a final 'no sales', None if not published yet."""
    path = os.path.join(CACHE, f"{freq}-{key}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    try:
        tsv = asc.request(cfg, "/v1/salesReports", {
            "filter[frequency]": freq, "filter[reportType]": "SALES",
            "filter[reportSubType]": "SUMMARY", "filter[vendorNumber]": cfg["vendor_number"],
            "filter[reportDate]": key, "filter[version]": VERSION[freq],
        }, raw=True).decode()
        rows = [{k: r[k] for k in FIELDS} for r in csv.DictReader(io.StringIO(tsv), delimiter="\t")]
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        if (dt.date.today() - period_end).days < GRACE[freq]:
            return None
        rows = []
    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w") as f:
        json.dump(rows, f)
    return rows


def daily(cfg, day):
    return fetch(cfg, "DAILY", day.isoformat(), day)


def month_rows(cfg, y, m, today):
    """One month: MONTHLY once the month is over and published, else DAILY up to yesterday."""
    first = dt.date(y, m, 1)
    last = dt.date(y, m, calendar.monthrange(y, m)[1])
    if last < today:
        rows = fetch(cfg, "MONTHLY", f"{y}-{m:02d}", last)
        if rows is not None:
            return rows
    out, d = [], first
    while d <= min(last, today - ONE_DAY):
        out += daily(cfg, d) or []
        d += ONE_DAY
    return out


def year_rows(cfg, y, today):
    if y < today.year:
        rows = fetch(cfg, "YEARLY", str(y), dt.date(y, 12, 31))
        if rows is not None:
            return rows
    out = []
    for m in range(1, (12 if y < today.year else today.month) + 1):
        out += month_rows(cfg, y, m, today)
    return out


class Counter:
    def __init__(self, sku_to_id):
        self.sku_to_id = sku_to_id
        self.c = defaultdict(lambda: defaultdict(int))

    def add(self, rows):
        for r in rows:
            kind = KIND.get(r["Product Type Identifier"].strip())
            if not kind:
                continue
            parent = r["Parent Identifier"].strip()  # IAP rows: parent app's SKU
            app = self.sku_to_id.get(parent, parent) if parent else r["Apple Identifier"].strip()
            self.c[app][kind] += int(r["Units"] or 0)

    def of(self, app):
        return {k: self.c.get(app, {}).get(k, 0) for k in KINDS}

    def total(self, kind="new"):
        return sum(v.get(kind, 0) for v in self.c.values())


def collect():
    cfg = asc.load_config()
    apps = {a["id"]: a["attributes"] for a in
            asc.request(cfg, "/v1/apps", {"fields[apps]": "name,sku", "limit": 200})["data"]}
    sku_to_id = {a["sku"]: i for i, a in apps.items()}
    today = dt.date.today()

    last_day, last = None, Counter(sku_to_id)
    for i in range(1, 6):
        rows = daily(cfg, today - i * ONE_DAY)
        if rows is not None:
            last_day = today - i * ONE_DAY
            last.add(rows)
            break

    monday = today - today.weekday() * ONE_DAY
    week = Counter(sku_to_id)
    d = monday
    while last_day and d <= last_day:
        week.add(daily(cfg, d) or [])
        d += ONE_DAY

    series = []
    if last_day:
        for i in range(SERIES_DAYS - 1, -1, -1):
            day = last_day - i * ONE_DAY
            c = Counter(sku_to_id)
            c.add(daily(cfg, day) or [])
            series.append({"date": day.isoformat(), "count": c.total()})

    alltime = Counter(sku_to_id)
    for y in range(FIRST_YEAR, today.year + 1):
        alltime.add(year_rows(cfg, y, today))

    rows = [{"id": a, "name": apps[a]["name"].split(":")[0].strip(),
             "day": last.of(a), "week": week.of(a), "all": alltime.of(a)} for a in apps]
    rows.sort(key=lambda r: (-r["all"]["new"], r["name"]))
    return {
        "last_day": last_day.isoformat() if last_day else None,
        "week_start": monday.isoformat(),
        "day": last.total(), "week": week.total(), "all": alltime.total(),
        "apps": rows, "series": series,
    }
