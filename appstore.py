"""App Store downloads and proceeds from Sales reports.

Periods: last report day, this week (Monday start) with the same days of last week for
comparison, last 7 report days as a series, and all time. All time = YEARLY reports for
past years + MONTHLY for finished months + DAILY for the current month. A period whose
report is not published yet falls back to the finer level.

Proceeds are converted to the display currency (config "currency", default USD) with
today's rate, so all-time revenue is an approximation; App Store Connect uses the rate
of each payment month.
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
import fx

CACHE = os.path.join(asc.CONFIG_DIR, "cache")
CACHE_VERSION = "v2"  # bump when FIELDS changes, old files are then ignored
FIRST_YEAR = 2024
VERSION = {"DAILY": "1_1", "MONTHLY": "1_0", "YEARLY": "1_0"}
# A 404 ("no sales") is only trusted once the period is this many days old;
# before that the report may simply not be published yet.
GRACE = {"DAILY": 4, "MONTHLY": 8, "YEARLY": 15}
ONE_DAY = dt.timedelta(days=1)
SERIES_DAYS = 7
TOP_COUNTRIES = 10

# Apple product type identifiers
KIND = {}
KIND.update({t: "new" for t in ("1", "1F", "1T", "F1", "1E", "1EP", "1EU")})
KIND.update({t: "re" for t in ("3", "3F", "3T", "F3")})
KIND.update({t: "upd" for t in ("7", "7F", "7T", "F7")})
KIND.update({t: "iap" for t in ("IA1", "IA9", "IAY", "IAC", "FI1", "IA1-M", "IA9-M", "IAY-M")})
KINDS = ("new", "re", "upd", "iap")
FIELDS = ("Product Type Identifier", "Units", "SKU", "Parent Identifier", "Apple Identifier",
          "Developer Proceeds", "Currency of Proceeds", "Country Code")


def fetch(cfg, freq, key, period_end):
    """Rows of a SALES SUMMARY report, [] for a final 'no sales', None if not published yet."""
    path = os.path.join(CACHE, f"{CACHE_VERSION}-{freq}-{key}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    try:
        tsv = asc.request(cfg, "/v1/salesReports", {
            "filter[frequency]": freq, "filter[reportType]": "SALES",
            "filter[reportSubType]": "SUMMARY", "filter[vendorNumber]": cfg["vendor_number"],
            "filter[reportDate]": key, "filter[version]": VERSION[freq],
        }, raw=True).decode()
        rows = [{k: r.get(k, "") for k in FIELDS} for r in csv.DictReader(io.StringIO(tsv), delimiter="\t")]
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


def days_rows(cfg, start, end):
    out, d = [], start
    while d <= end:
        out += daily(cfg, d) or []
        d += ONE_DAY
    return out


class Counter:
    """Units per kind, proceeds per currency and new downloads per country, per app."""

    def __init__(self, sku_to_id):
        self.sku_to_id = sku_to_id
        self.units = defaultdict(lambda: defaultdict(int))
        self.money = defaultdict(lambda: defaultdict(float))
        self.countries = defaultdict(lambda: defaultdict(int))

    def add(self, rows):
        for r in rows:
            kind = KIND.get(r["Product Type Identifier"].strip())
            if not kind:
                continue
            parent = r["Parent Identifier"].strip()  # IAP rows: parent app's SKU
            app = self.sku_to_id.get(parent, parent) if parent else r["Apple Identifier"].strip()
            units = int(r["Units"] or 0)
            self.units[app][kind] += units
            proceeds = float(r.get("Developer Proceeds") or 0)  # per unit
            currency = (r.get("Currency of Proceeds") or "").strip()
            if proceeds and currency:
                self.money[app][currency] += proceeds * units
            if kind == "new" and r.get("Country Code"):
                self.countries[app][r["Country Code"].strip()] += units

    def of(self, app):
        return {k: self.units.get(app, {}).get(k, 0) for k in KINDS}

    def total(self, kind="new"):
        return sum(v.get(kind, 0) for v in self.units.values())

    def revenue(self, rates, app=None):
        """Proceeds of one app (or all) in the display currency; None if a rate is missing."""
        pools = [self.money.get(app, {})] if app else self.money.values()
        total = 0.0
        for pool in pools:
            for currency, amount in pool.items():
                converted = fx.convert(amount, currency, rates)
                if converted is None:
                    return None
                total += converted
        return round(total, 2)

    def top_countries(self, app=None, n=TOP_COUNTRIES):
        merged = defaultdict(int)
        for a, cs in self.countries.items():
            if app is None or a == app:
                for c, v in cs.items():
                    merged[c] += v
        return sorted(merged.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def change(current, previous):
    """Percent change, None when there is nothing to compare against."""
    if not previous:
        return None
    return round(100 * (current - previous) / previous, 1)


def collect():
    cfg = asc.load_config()
    currency = cfg.get("currency", "USD").upper()
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

    # this week up to the last published day vs the same weekdays of last week
    monday = today - today.weekday() * ONE_DAY
    week, prev_week = Counter(sku_to_id), Counter(sku_to_id)
    if last_day and last_day >= monday:
        week.add(days_rows(cfg, monday, last_day))
        prev_week.add(days_rows(cfg, monday - 7 * ONE_DAY, last_day - 7 * ONE_DAY))

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

    rates = fx.rates(currency) if any(alltime.money.values()) else {currency: 1.0}

    def revenue(app=None):
        return {"day": last.revenue(rates, app), "week": week.revenue(rates, app),
                "all": alltime.revenue(rates, app)}

    rows = []
    for a in apps:
        rows.append({
            "id": a, "name": apps[a]["name"].split(":")[0].strip(),
            "day": last.of(a), "week": week.of(a), "prev_week": prev_week.of(a), "all": alltime.of(a),
            "revenue": revenue(a),
            "countries": alltime.top_countries(a, 5),
        })
    rows.sort(key=lambda r: (-r["all"]["new"], r["name"]))
    return {
        "last_day": last_day.isoformat() if last_day else None,
        "week_start": monday.isoformat(),
        "day": last.total(), "week": week.total(), "prev_week": prev_week.total(), "all": alltime.total(),
        "week_change": change(week.total(), prev_week.total()),
        "currency": currency, "revenue": revenue(),
        "countries": alltime.top_countries(),
        "storefronts": sorted({c.lower() for cs in alltime.countries.values() for c in cs}),
        "apps": rows, "series": series,
    }
