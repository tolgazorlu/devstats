#!/usr/bin/env python3
"""Create the Analytics Reports requests (ONGOING + ONE_TIME_SNAPSHOT) for every app.

Needed once for impressions and conversion rate. Apple only lets an **Admin** API key
create these; afterwards a "Sales and Reports" key can read the reports, so switch the
config to such a key and revoke the Admin one. Safe to re-run: existing requests are kept.

Usage: .venv/bin/python scripts/request_reports.py
"""
import os
import sys
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asc  # noqa: E402


def main():
    cfg = asc.load_config()
    for app in asc.paginate(cfg, "/v1/apps", {"fields[apps]": "name", "limit": 200}):
        aid, name = app["id"], app["attributes"]["name"]
        existing = {r["attributes"]["accessType"] for r in
                    asc.paginate(cfg, f"/v1/apps/{aid}/analyticsReportRequests")}
        for access in ("ONGOING", "ONE_TIME_SNAPSHOT"):
            if access in existing:
                print(f"exists   {access:<17} {name}")
                continue
            try:
                asc.request(cfg, "/v1/analyticsReportRequests", method="POST", body={"data": {
                    "type": "analyticsReportRequests", "attributes": {"accessType": access},
                    "relationships": {"app": {"data": {"type": "apps", "id": aid}}}}})
                print(f"created  {access:<17} {name}")
            except urllib.error.HTTPError as e:
                hint = " (needs an Admin key)" if e.code == 403 else ""
                print(f"FAILED   {access:<17} {name}: HTTP {e.code}{hint}")


if __name__ == "__main__":
    main()
