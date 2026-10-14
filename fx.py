"""Exchange rates for converting App Store proceeds to one display currency.

Source: open.er-api.com (free, no key, updated daily, 160+ currencies). Rates are cached
for a day; on a network failure the last cached table is used.
"""
import json
import os
import time
import urllib.request

import asc

CACHE = os.path.join(asc.CONFIG_DIR, "cache")
URL = "https://open.er-api.com/v6/latest/{base}"
TTL = 86400


def rates(base):
    """{currency: units of that currency per 1 `base`}."""
    path = os.path.join(CACHE, f"fx-{base}.json")
    fresh = os.path.exists(path) and time.time() - os.path.getmtime(path) < TTL
    if not fresh:
        try:
            with urllib.request.urlopen(URL.format(base=base), timeout=20) as r:
                body = json.load(r)
            if body.get("result") == "success":
                os.makedirs(CACHE, exist_ok=True)
                with open(path, "w") as f:
                    json.dump(body["rates"], f)
                return body["rates"]
        except OSError:
            pass  # fall back to the last cached table below
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {base: 1.0}


def convert(amount, currency, table):
    """`amount` in `currency` expressed in the table's base currency, None if unknown."""
    rate = table.get(currency)
    if not rate:
        return None
    return amount / rate
