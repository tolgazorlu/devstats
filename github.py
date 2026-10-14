"""GitHub contributions, the numbers on the profile overview: today, week, last year, all time."""
import datetime as dt
import json
import os
import shutil
import subprocess
import urllib.request

import asc

GH = shutil.which("gh") or next(
    (p for p in ("/opt/homebrew/bin/gh", "/usr/local/bin/gh") if os.path.exists(p)), "gh")
CACHE = os.path.join(asc.CONFIG_DIR, "cache")
CALENDAR_WEEKS = 25


def graphql(query):
    token = subprocess.run([GH, "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if body.get("errors"):
        raise RuntimeError(body["errors"][0]["message"])
    return body["data"]


def year_total(year, created):
    """Contribution total for a finished calendar year (cached forever)."""
    path = os.path.join(CACHE, f"github-{year}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)["total"]
    start = max(dt.datetime(year, 1, 1), created).strftime("%Y-%m-%dT%H:%M:%SZ")
    q = f'{{ viewer {{ contributionsCollection(from: "{start}", to: "{year}-12-31T23:59:59Z") ' \
        '{ contributionCalendar { totalContributions } } } }'
    total = graphql(q)["viewer"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"total": total}, f)
    return total


def collect():
    v = graphql("""{ viewer { login createdAt contributionsCollection {
        totalCommitContributions totalPullRequestContributions totalIssueContributions
        totalPullRequestReviewContributions restrictedContributionsCount
        contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } } } } }""")["viewer"]
    cc = v["contributionsCollection"]
    days = {d["date"]: d["contributionCount"]
            for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]}

    today = dt.date.today()
    created = dt.datetime.strptime(v["createdAt"], "%Y-%m-%dT%H:%M:%SZ")
    this_year = sum(n for d, n in days.items() if d.startswith(str(today.year)))
    alltime = this_year + sum(year_total(y, created) for y in range(created.year, today.year))
    monday = today - dt.timedelta(days=today.weekday())

    def span(start, n):
        return [{"date": (start + dt.timedelta(days=i)).isoformat(),
                 "count": days.get((start + dt.timedelta(days=i)).isoformat(), 0)} for i in range(n)]

    return {
        "login": v["login"],
        "since": created.year,
        "today": days.get(today.isoformat(), 0),
        "week": sum(days.get((monday + dt.timedelta(days=i)).isoformat(), 0) for i in range(today.weekday() + 1)),
        "last_year": cc["contributionCalendar"]["totalContributions"],
        "alltime": alltime,
        "breakdown": {
            "commit": cc["totalCommitContributions"],
            "pr": cc["totalPullRequestContributions"],
            "review": cc["totalPullRequestReviewContributions"],
            "issue": cc["totalIssueContributions"],
            "private": cc["restrictedContributionsCount"],
        },
        "series": span(today - dt.timedelta(days=6), 7),
        # Monday-aligned weeks ending with the current one, for the heat grid
        "calendar": span(monday - dt.timedelta(weeks=CALENDAR_WEEKS - 1), CALENDAR_WEEKS * 7),
    }
