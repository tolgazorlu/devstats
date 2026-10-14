# Prior art and roadmap

Survey of 30+ open-source repos and commercial apps that show App Store Connect or
GitHub stats in a menu bar, widget, dashboard or CLI (October 2026). Full notes:
[appstore-tools.md](research/appstore-tools.md), [github-tools.md](research/github-tools.md).

## Where Dev Stats stands

No tool found combines App Store and GitHub numbers in one menu bar item and widget.
The closest App Store prior art, AC Widget (no-comment/AppStore-Connect-Widget, MIT,
113 stars), is archived since 2023. Downloads, IAP units and the impressions/conversion
funnel are already on par with the commercial widget apps.

Biggest gaps compared to the field: revenue, ratings/reviews, change vs the previous
period, streaks, notifications, resilience when an API fails.

## Most relevant references (verified with `gh api`, 2026-10-14)

| Repo | Stars | License | Why it matters |
| --- | --- | --- | --- |
| rorkai/App-Store-Connect-CLI | 7,826 | MIT | Most used ASC tool; analytics/sales/finance commands to compare parsing against |
| gitify-app/gitify | 5,368 | MIT | Notification inbox done well; OAuth instead of a pasted token |
| steipete/RepoBar | 2,208 | MIT | Cache-first architecture, rate-limit UI, per-repo stats, bundled CLI |
| nickustinov/itsyconnect-macos | 128 | MIT | Reviews UI, reply via API, Keychain-encrypted credentials |
| no-comment/AppStore-Connect-Widget | 113 | MIT (archived) | Display-currency conversion, multi-account, real-downloads toggle |
| menubar-apps/StreakBar | 32 | GPL-3.0 | Streak bar UX; ideas only (copyleft) |
| nakamekun/app-store-monitor | 1 | MIT | Same stack (Python stdlib); notification dedupe guard, mock mode for tests |
| brunosemfio/mcp-app-store-connect | 0 | Apache-2.0 | Python; reviews, finance, perf metrics endpoints |
| OddOmens/OpenConnect | 0 | MIT + Commons Clause | "What changed since last sync" diff, rankings across storefronts; ideas only |

## Roadmap, ranked by value for an indie developer vs effort

| # | Feature | Source of the idea | API | Effort |
| --- | --- | --- | --- | --- |
| 1 | Change vs previous period (▲ 12% / ▼ 3%, monochrome) | Widgets for ASC, OpenConnect | none, math on data we have | 3-4 steps |
| 2 | Ratings per app (average + count) | OpenConnect, Helm | public `itunes.apple.com/lookup?id=…&country=xx`, no key | 2-3 steps |
| 3 | GitHub current and longest streak | StreakBar, github-streaks, Git Streaks | per-year `contributionsCollection` (cache full day arrays, not only totals) | 3-6 steps |
| 4 | Revenue (developer proceeds) in one currency | AC Widget, appleconnect, Tallyr | Sales report `Developer Proceeds` + `Currency of Proceeds`, cached daily FX table | 4-7 steps |
| 5 | New review alert (macOS notification, once per review) | review-alert services, app-store-monitor | `GET /v1/apps/{id}/customerReviews?sort=-createdDate` | 3-5 steps |
| 6 | Last-good cache, "updated N min ago", rate-limit line | RepoBar | GraphQL `rateLimit { remaining resetAt }` | 3-5 steps |
| 7 | Top repos this week | RepoBar | `commitContributionsByRepository(maxRepositories: 5)` | 2-4 steps |
| 8 | Test suite with mock mode (fake reports) | app-store-monitor | none | 3-5 steps |

Not planned: chart rankings (175 storefront RSS feeds for apps that are not in the
charts), TestFlight, multi-account, PR review queue and CI status (RepoBar and Gitify
already do these well).

## Facts checked on our own account

- iTunes lookup ratings are per storefront: the same app returns 5.0 from 1 rating in
  `country=tr` and 0 in `country=us`. A useful total needs a loop over the storefronts
  the app sells in, weighted by rating count.
- `customerReviews` works with the current (Admin) key and returned 0 written reviews.
  Not yet checked: whether a "Sales and Reports" key can read reviews. If not, review
  alerts need a key with a role that can, which must be settled before revoking the
  Admin key.
- Revenue needs a cache change: report rows are cached with only the columns used for
  downloads, so `Developer Proceeds` and `Currency of Proceeds` must be added to the
  cached fields and old cache files re-fetched once.

## Open questions

- GitHub day boundaries: `contributionsCollection` has no timezone argument and buckets
  days in UTC (per GitHub community discussions). Whether the github.com profile shows
  the same buckets was not verified. Shifting `from`/`to` by the local offset would fix
  "today" locally but break parity with the profile number.
