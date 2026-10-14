"""GitHub contributions, the numbers on the profile overview, plus streaks and top repos.

Days are bucketed in UTC by GitHub (contributionsCollection has no timezone argument),
so "today" here is the UTC date as well. That keeps every number consistent with the
contribution calendar; the cost is that the day flips at 03:00 Turkish time.
"""
import datetime as dt
import json
import os
import shutil
import subprocess
import urllib.parse
import urllib.request

import asc

GH = shutil.which("gh") or next(
    (p for p in ("/opt/homebrew/bin/gh", "/usr/local/bin/gh") if os.path.exists(p)), "gh")
CACHE = os.path.join(asc.CONFIG_DIR, "cache")
CALENDAR_WEEKS = 25
TOP_REPOS = 5
ONE_DAY = dt.timedelta(days=1)


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


def calendar_days(cal):
    return {d["date"]: d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]}


def year_days(year, created):
    """{date: count} for a finished calendar year (cached forever)."""
    path = os.path.join(CACHE, f"github-days-{year}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    start = max(dt.datetime(year, 1, 1), created).strftime("%Y-%m-%dT%H:%M:%SZ")
    q = f'{{ viewer {{ contributionsCollection(from: "{start}", to: "{year}-12-31T23:59:59Z") ' \
        '{ contributionCalendar { weeks { contributionDays { date contributionCount } } } } } }'
    days = calendar_days(graphql(q)["viewer"]["contributionsCollection"]["contributionCalendar"])
    days = {d: n for d, n in days.items() if d.startswith(str(year))}
    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w") as f:
        json.dump(days, f)
    return days


def streaks(days, today):
    """(current, longest) runs of consecutive days with contributions.

    The current streak stays alive through today until the day is over, so a day
    without contributions yet does not reset it to zero.
    """
    d = today if days.get(today.isoformat(), 0) else today - ONE_DAY
    current = 0
    while days.get(d.isoformat(), 0):
        current += 1
        d -= ONE_DAY
    longest = run = 0
    prev = None
    for key in sorted(k for k, n in days.items() if n):
        day = dt.date.fromisoformat(key)
        run = run + 1 if prev and day - prev == ONE_DAY else 1
        longest = max(longest, run)
        prev = day
    return current, max(longest, current)


def span_sum(days, start, n):
    return sum(days.get((start + i * ONE_DAY).isoformat(), 0) for i in range(n))


def change(current, previous):
    if not previous:
        return None
    return round(100 * (current - previous) / previous, 1)


def top_repos(login, since, limit=TOP_REPOS, max_pages=10):
    """Repos with the most commits authored since `since` (a date), private ones included.

    GraphQL's commitContributionsByRepository leaves out private-repo work (it shows up
    only as restrictedContributionsCount), so this uses the commit search API instead.
    Search covers default branches and returns at most 1000 commits.
    """
    token = subprocess.run([GH, "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    counts, seen, total = {}, 0, None
    for page in range(1, max_pages + 1):
        q = urllib.parse.quote(f"author:{login} author-date:>={since.isoformat()}")
        req = urllib.request.Request(
            f"https://api.github.com/search/commits?q={q}&per_page=100&page={page}",
            headers={"Authorization": f"bearer {token}", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.load(r)
        total = body["total_count"]
        for item in body["items"]:
            repo = item["repository"]
            key = repo["full_name"]
            counts.setdefault(key, {"name": key, "url": repo["html_url"], "private": repo["private"], "commits": 0})
            counts[key]["commits"] += 1
        seen += len(body["items"])
        if not body["items"] or seen >= total:
            break
    ranked = sorted(counts.values(), key=lambda r: -r["commits"])
    return ranked[:limit], total


def collect():
    today = dt.datetime.now(dt.timezone.utc).date()
    monday = today - today.weekday() * ONE_DAY
    v = graphql("""{ rateLimit { limit remaining resetAt }
      viewer { login createdAt
        contributionsCollection {
          totalCommitContributions totalPullRequestContributions totalIssueContributions
          totalPullRequestReviewContributions restrictedContributionsCount
          contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } } } } }""")
    rate, v = v["rateLimit"], v["viewer"]
    cc = v["contributionsCollection"]
    recent = calendar_days(cc["contributionCalendar"])

    created = dt.datetime.strptime(v["createdAt"], "%Y-%m-%dT%H:%M:%SZ")
    days = {}
    for y in range(created.year, today.year):
        days.update(year_days(y, created))
    days.update(recent)  # the live calendar wins for overlapping dates
    alltime = sum(n for d, n in days.items() if d <= today.isoformat())
    current, longest = streaks(days, today)

    def span(start, n):
        return [{"date": (start + i * ONE_DAY).isoformat(),
                 "count": days.get((start + i * ONE_DAY).isoformat(), 0)} for i in range(n)]

    week = span_sum(days, monday, today.weekday() + 1)
    prev_week = span_sum(days, monday - 7 * ONE_DAY, today.weekday() + 1)
    try:
        repos, week_commits = top_repos(v["login"], monday)
    except OSError:  # search has its own, lower rate limit; the rest of the stats still count
        repos, week_commits = [], None
    return {
        "login": v["login"],
        "since": created.year,
        "today": days.get(today.isoformat(), 0),
        "week": week,
        "prev_week": prev_week,
        "week_change": change(week, prev_week),
        "last_year": cc["contributionCalendar"]["totalContributions"],
        "alltime": alltime,
        "streak": {"current": current, "longest": longest},
        "breakdown": {
            "commit": cc["totalCommitContributions"],
            "pr": cc["totalPullRequestContributions"],
            "review": cc["totalPullRequestReviewContributions"],
            "issue": cc["totalIssueContributions"],
            "private": cc["restrictedContributionsCount"],
        },
        "top_repos": repos,
        "week_commits": week_commits,
        "rate_limit": rate,
        "series": span(today - 6 * ONE_DAY, 7),
        # Monday-aligned weeks ending with the current one, for the heat grid
        "calendar": span(monday - (CALENDAR_WEEKS - 1) * 7 * ONE_DAY, CALENDAR_WEEKS * 7),
    }
