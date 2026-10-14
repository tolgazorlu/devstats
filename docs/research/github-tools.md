# GitHub activity/menu-bar/widget tools — research for Dev Stats (asc-menubar)

Our baseline (`github.py`): GraphQL via `gh auth token`, no caching except finished-year totals,
no timezone handling (uses UTC day boundaries implicitly), 7-day bar + 25-week heat grid, no
streaks/goals/per-repo/PR-queue/CI.

## Catalog

| Name | URL | OSS/Commercial | Stars / last push / license | Platform | Data source | Notable features | Clever bits |
|---|---|---|---|---|---|---|---|
| GitHub Streaks | github.com/uaoa/github-streaks | OSS | 2★ / 2026-02-04 / MIT | macOS menu bar, Swift | n/a (README doesn't state; no PAT setup step shown, likely public contributions HTML endpoint) | streak counter, mini grid in menu bar, full-year popover, display mode toggle | hover tooltip per day |
| streakerbar | github.com/chaserx/streakerbar | OSS | 2★ / 2015-05-06 (dead) / MIT | macOS menu bar | n/a, old project, pre-GraphQL era | dark/light theme, Homebrew cask install | first-mover but unmaintained since 2015 |
| StreakBar | github.com/menubar-apps/StreakBar | OSS | 32★ / 2026-05-02 / GPL-3.0 | macOS menu bar, Swift | n/a (README omits; actively maintained, Homebrew tap) | day/week view toggle, color theme, border/transparency customization, release-tracked | most "finished" of the pure streak-bar apps; good UX reference for customization options |
| Git Streaks for GitHub | App Store id1525795950 / thegitstreak.app | Commercial (free) | n/a (App Store) | macOS (App Store, also listed in "GitHub Marketplace") | n/a | "make coding a habit" framing, gamified achievements (per landing page) | habit/gamification angle, not technical detail available |
| GitHub Contribution Widget for macOS | github.com/SekulDev/GithubContributionWidgetMacOS | OSS | 8★ / 2025-10-04 / MIT | macOS desktop **widget** (WidgetKit) | REST, explicit PAT (classic, `user:read` scope) entered by user in widget config | desktop widget sizes, username+token stored via widget configuration intent | simplest possible WidgetKit reference: user supplies their own PAT, no `gh` dependency, no OAuth flow — self-admitted "vibe coded," thin but directly comparable to our widget target |
| mohummudh/contributions | github.com/mohummudh/contributions | OSS | 0★ / 2026-02-27 / none (no LICENSE file — reuse needs permission) | macOS desktop **widget** (WidgetKit, App+Widget+Shared targets) | **scrapes** `github.com/<user>?tab=contributions` (XHR) with fallback to `github.com/users/<user>/contributions`; Foundation regex, no deps | App Group + shared `UserDefaults` for username, 30-min WidgetKit timeline refresh, no external deps | closest structural match to our target: separate App/WidgetExtension/Shared split, app-group pattern, pure-regex HTML scraping instead of GraphQL (avoids needing a token at all, but fragile to GitHub markup changes and public-only) |
| Contribution Corner | github.com/Lundeful/ContributionCorner | OSS | 23★ / 2025-04-09 / MIT | macOS menu bar, Swift | **scrapes** GitHub profile HTML via SwiftSoup | fetch-on-click + manual reload button, custom menu bar icon since v1.7 | uses SwiftSoup library for scraping instead of regex; refresh model is "fetch when you open the menu" — a zero-background-refresh pattern worth considering for a lightweight mode |
| AxisContribution | github.com/jasudev/AxisContribution | OSS (library) | 132★ / 2024-04-02 / MIT | iOS+macOS SwiftUI library | takes an array of `Date`s (caller supplies data) | reusable contribution-calendar SwiftUI component, used by ContributionCorner | not a data source, a rendering library — grid/heatmap view component we could vendor or imitate for widget-side rendering ideas |
| GithubContributions menu bar (SNQ-2001) | github.com/SNQ-2001/github-contributions-menubar-macos | OSS | 10★ / 2023-02-21 (stale) / MIT | macOS menu bar | n/a | basic activity display | nothing beyond baseline; stale |
| Contributions for GitHub | App Store id1153432612 | Commercial | n/a | iOS/macOS, **widgets + Apple Watch app** | n/a (app-store listing only) | multi-widget sizes + Watch complication, "Featured on Product Hunt 2016" | earliest "widgets everywhere" precedent incl. Watch — signals demand for a companion complication, no technical detail obtainable |
| Gitify | github.com/gitify-app/gitify | OSS | 5368★ / 2026-10-14 (very active) / MIT | macOS/Windows/Linux menu bar, Electron/TS | REST notifications API + GitHub OAuth (multi-forge: GitHub.com + Enterprise) | unified notification inbox, multi-account, mark as read, filters | biggest/most polished in the whole set; proves OAuth app-token flow (vs. `gh auth token` reuse) is viable and well received; not activity-graph focused, it's notifications |
| github.swiftbar (formerly swiftbar-github-prs via santi-gestal fork) | github.com/iOliverNguyen/github.swiftbar | OSS | 3★ / 2024-08-20 / none | SwiftBar plugin, Go | REST (search API for PRs) | shows PRs/stacked-PR status waiting on the viewer, grouped by stack | same plugin-script model as our SwiftBar part; proves PR-review-queue is a well-liked SwiftBar use case |
| RepoBar | github.com/steipete/RepoBar | OSS (very active, commercial-grade polish) | 2208★ / 2026-10-12 / MIT | macOS menu bar, Swift 6.2, native app + CLI | GitHub App user-token OAuth (Keychain-stored) **or** classic PAT for SSO/org edge cases; REST+GraphQL mixed; SQLite cache; optional GitHub-archive import for offline/rate-limited seeding | multi-repo dashboard: issue/PR counts, CI status, releases, local git checkout state (branch/dirty/ahead-behind), repo-level contribution heatmaps, rate-limit/quota viewer, bundled `repobar` CLI with `--json`/`--plain` output, light/dark/system theming | by far the most sophisticated tool found: (1) persistent SQLite cache with "open from cache, refresh in background" pattern, (2) explicit API-quota/cooldown UI, (3) GitHub-App-based auth instead of PAT, (4) archive-backed resilience to outages/rate limits. Directly useful architecture reference even though its focus is maintainer multi-repo ops, not personal streaks |
| gbar | github.com/jaylann/gbar | OSS | 3★ / 2026-07-22 / NOASSERTION (no clear license — reuse needs permission) | macOS menu bar, Swift | n/a (not inspected in depth, low stars) | general "GitHub in your menu bar" | minor; noted, not deep-dived (stars too low to prioritize) |
| gitbar | github.com/brunokiafuka/gitbar | OSS | 17★ / 2026-06-02 / none (no LICENSE) | macOS menu bar, Swift | n/a | general GitHub menu bar | noted, not deep-dived |
| macos-wakatime | github.com/wakatime/macos-wakatime | OSS | 234★ / 2026-08-09 / BSD-3-Clause | macOS menu bar | WakaTime's own API; tracks Xcode/Figma/Postman usage via local app-activity hooks, not GitHub | today's coding time, per-project time breakdown | adjacent "dev stats" tool: shows a credible model for **local, non-GitHub telemetry** (active-app tracking) that could feed a "time coded today" metric alongside GitHub counts |
| WakaMenu | github.com/hiroshihorie/WakaMenu | OSS | 13★ / 2020-05-14 (dead) / MIT | macOS menu bar, Obj-C | WakaTime API, reads `~/.wakatime.cfg` | minimal "today's time" menu bar text | superseded by official wakatime/macos-wakatime |

Not found / dropped after failed lookups (per the 2-attempt cap): `menubar-apps` org has no separate
`sopenlaz0/github-contribution-graph`, `pkyanam/gh-contributions-macos-menu-bar`, `welsonla/contribution-graph-swiftui`,
and `jryom/swiftbar-github` — none resolved to a real repo under those names/owners across two search
rounds (closest real matches surfaced instead: `pruizlezcano/contribution-graph-swiftui`,
`iOliverNguyen/github.swiftbar`, `santi-gestal/swiftbar-github-prs` which redirects/forks into the
iOliverNguyen repo). Treat these four as unverified/possibly renamed or deleted.

Extra tools found via own searches (per instructions): **RepoBar** (major, see above), **Gitify**
(major, see above), **WakaTime family** (macos-wakatime, WakaMenu) as adjacent dev-telemetry precedent.

## Feature matrix

| Feature | us | StreakBar | github-streaks | ContributionWidget(Sekul) | contributions(mohummudh) | ContributionCorner | RepoBar | Gitify | github.swiftbar |
|---|---|---|---|---|---|---|---|---|---|
| Today/week/year/all-time totals | ✅ | partial | ✅(streak) | ✅ | ✅ | ✅ | — | — | — |
| Breakdown by type (commit/PR/review/issue) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅(per repo) | — | — |
| 7-day bar chart | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | — | — | — |
| Heat grid (weeks) | ✅ (25-wk) | ✅ customizable | ✅ mini grid | ✅ | ✅ | ✅ | ✅ per-repo | — | — |
| Current/longest streak | ❌ | ❌(implied, unverified) | ✅ | ❌ | ❌ | ❌ | ❌ | — | — |
| Desktop widget (WidgetKit) | ✅ (large) | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Menu bar app | ✅(SwiftBar plugin) | ✅ native | ✅ native | ❌ | ❌ | ✅ native | ✅ native | ✅ Electron | ✅ SwiftBar |
| PR review queue / stacked PRs | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (issue/PR counts) | ❌(notifications only) | ✅ |
| CI status | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Per-repo stats / multi-repo dashboard | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Notifications (unified inbox) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Stars/followers growth tracking | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | partial (per repo stars, no history) | ❌ | ❌ |
| Local git checkout state (dirty/ahead-behind) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Offline/cache resilience to rate limits | ❌(no cache except finished years) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (SQLite + archive import) | ❌ | ❌ |
| Rate-limit/quota visibility | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Goals / habit framing | ❌ | ❌ | ❌(name suggests but unconfirmed) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Auth model | `gh auth token` reuse | n/a | n/a | user-supplied classic PAT | n/a (scrapes public page) | n/a (scrapes public page) | GitHub App OAuth + Keychain, PAT fallback | GitHub OAuth | n/a |

## Best ideas worth stealing (ranked, value vs. effort)

1. **Current + longest streak** — highest value/lowest effort. Users explicitly ask for this
   (3 of ~14 tools are built around nothing else).
   - API: reuse our existing `contributionCalendar.weeks[].contributionDays[].date/contributionCount`
     for the current year; for longest streak spanning prior years, loop `contributionsCollection(from, to)`
     per year back to `createdAt` (same pattern `github.py:year_total` already uses for totals) and
     concatenate day arrays.
   - Code: `github.py` (`collect()` — add `streak_current`, `streak_longest` fields, iterate cached
     per-year day arrays similarly to `year_total`), `devstats.py` (render), `widget/Shared/Views.swift`
     (new line/badge). Effort: ~1 file-set, 3–6 steps (new cache format per year storing full day
     arrays, not just totals — current `github-{year}.json` only stores `{"total": n}` and must be
     extended to store the day list too, a small cache-schema bump).
   - Risk: cache migration (old cache files only have `total`, need backward-compat read); defining
     "current streak" edge case at day boundary (see below) needs a documented timezone decision.

2. **Per-repo contribution breakdown using `commitContributionsByRepository`** — medium value,
   low-medium effort, nobody's menu-bar/widget competitor has it (RepoBar has it but at a different,
   heavier multi-repo-dashboard scope).
   - API: `contributionsCollection { commitContributionsByRepository(maxRepositories: 25) { repository { nameWithOwner } contributions { totalCount } } }`
     (same field exists for `pullRequestContributionsByRepository`, `issueContributionsByRepository`,
     `pullRequestReviewContributionsByRepository`).
   - Code: `github.py` (extend `collect()` query, one more nested block), `devstats.py`/`Views.swift`
     for a "top repos today/this week" line. Effort: ~2 files, 2–4 steps.
   - Risk: none significant; GraphQL field is stable and already documented.

3. **Cache-first with background refresh + rate-limit visibility (RepoBar's pattern)** — medium
   value, medium effort; improves resilience, not a user-facing killer feature on its own.
   - API: `rateLimit { limit cost remaining resetAt }` field on any GraphQL query; we already
     cache finished-year totals, so add last-successful-payload caching with timestamp and show
     "last updated Xm ago, falling back to cache" on failure.
   - Code: `github.py` (wrap `graphql()` with try/except falling back to last good JSON in `CACHE`),
     `devstats.py` (status line). Effort: ~1 file, 3–5 steps.
   - Risk: low; mainly bookkeeping.

4. **PR review queue (stacked PRs waiting on viewer)** — medium value for a working dev, higher
   effort because it's a new REST/GraphQL surface, not an extension of `contributionsCollection`.
   - API: REST search `GET /search/issues?q=is:pr+is:open+review-requested:@me` or GraphQL
     `search(query: "is:pr is:open review-requested:@me", type: ISSUE)`.
   - Code: new module (e.g. `github_prs.py`), `devstats.py` menu section, optional widget line.
     Effort: ~2 files, 4–6 steps (new SwiftBar section + caching + click-through URL).
   - Risk: separate rate-limit bucket (REST search has its own quota, lower than GraphQL).

5. **CI status for recent commits/PRs** — lower value for a personal-stats tool (more relevant to
   RepoBar's maintainer-dashboard framing than to "my daily contributions"), higher effort
   (checks-API + per-repo config). Deprioritized unless the user specifically wants a build-status
   glance.

6. **Desktop-widget auth UX: user-supplied PAT vs. `gh auth token` reuse** — SekulDev's and
   mohummudh's widgets solve the "WidgetKit extension can't shell out to `gh`" problem differently:
   SekulDev asks the user to paste a classic PAT into the widget's configuration intent (stored via
   `UserDefaults`/App Group), mohummudh avoids tokens entirely by **scraping the public contributions
   HTML** inside the widget extension. Our current widget presumably already solves this somehow
   (not reviewed here) — if it does not, PAT-in-config (SekulDev's model) is lower effort than
   re-deriving a token inside a widget extension sandbox. Effort: config-only, ~1–2 steps once
   decided; risk is secure storage (Keychain via App Group, not plain `UserDefaults`).

## UTC day-boundary and streak-history questions (answered)

- **Does `contributionsCollection` take a timezone?** No. The field only accepts `from`/`to` as
  `DateTime` (UTC `Z`-suffixed timestamps); there is no timezone parameter. When `from`/`to` are
  omitted, GitHub defaults to the trailing ~371 days ending "now," and the day-bucketing both in
  that default mode and in explicit queries is done in **UTC**, not the viewer's profile timezone —
  confirmed by a long-running GitHub community discussion (`orgs/community/discussions/121029`,
  `discussions/20898`) where users report the calendar's day boundaries not matching their local
  time and GitHub staff pointing to the UTC-anchored calendar as by design. GitHub's own web
  profile calendar has the same UTC-anchored behavior; it does not read the viewer's local
  timezone to shift day buckets. None of the tools reviewed here document a timezone workaround;
  our own `github.py` also computes `dt.date.today()` in local time to look up a UTC-keyed `days`
  dict, which means a contribution made today after midnight UTC but before local midnight (or vice
  versa) can show on the "wrong" local day. This is a pre-existing, unfixed discrepancy worth a
  one-line code comment at minimum; a real fix means re-requesting `from`/`to` shifted by the
  user's UTC offset and accepting that GitHub's own total still won't match (since GitHub itself is
  UTC-anchored) — effectively not fully fixable without diverging from GitHub's canonical numbers.

- **Does streak calculation need history beyond one year?** Yes, for "longest streak" (not for
  "current streak" in the common case). `contributionCalendar` from a single `contributionsCollection`
  call only covers the queried `from`/`to` window (max useful span is about a year before hitting
  size/perf limits GitHub imposes informally). Tools that compute a genuine "longest streak ever"
  (e.g. `franznkemaka/github-streak-api`, confirmed via its README) explicitly loop year-by-year
  from account creation and concatenate — exactly the pattern our `github.py:year_total` already
  uses for totals, so extending it to cache full day-arrays per finished year (not just the sum) is
  the natural path, and is idea #1 above.

## Licensing notes for reuse

- MIT (safe to read/adapt code with attribution): `uaoa/github-streaks`, `chaserx/streakerbar`,
  `SekulDev/GithubContributionWidgetMacOS`, `Lundeful/ContributionCorner`, `jasudev/AxisContribution`,
  `SNQ-2001/github-contributions-menubar-macos`, `gitify-app/gitify`, `wakatime/macos-wakatime`,
  `hiroshihorie/WakaMenu`, `steipete/RepoBar`.
- GPL-3.0 (copyleft, do not vendor code into a closed/private repo without complying): `menubar-apps/StreakBar`.
- No LICENSE file / NOASSERTION (treat as "all rights reserved," do not copy code, ideas/APIs only):
  `mohummudh/contributions`, `brunokiafuka/gitbar`, `jaylann/gbar`, `iOliverNguyen/github.swiftbar`.
- App Store commercial apps (`Git Streaks`, `Contributions for GitHub`): no source available, ideas only.

In all cases we are taking *ideas and API field names* (public GitHub API surface, not copyrightable),
not copying implementation code, so licensing mainly matters only if we ever vendor actual source
(e.g. `AxisContribution`'s SwiftUI rendering component, which MIT permits).
