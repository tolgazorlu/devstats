# App Store Connect stats tools — research for Dev Stats

Our project (`~/projects/asc-menubar`, SwiftBar menu bar in Python + a WidgetKit
desktop widget reading `~/.config/asc-menubar/snapshot.json`) currently has:
downloads (day/week/all-time), redownloads, updates, IAP units, impressions,
product page views, conversion rate, GitHub contributions. Missing: revenue/
proceeds, ratings/reviews, rankings, country breakdown, period-over-period
comparison, notifications, subscriptions, TestFlight, multi-account.

## Candidates

### Open source

| Name | URL | Stars | Last push | License | Platform | Data sources | Notable / clever |
|---|---|---|---|---|---|---|---|
| AC Widget (no-comment) | github.com/no-comment/AppStore-Connect-Widget | 113 | 2023-10-16 (**archived**, author moved to gettrendly.app) | MIT | iOS/Mac WidgetKit app | Sales and Trends reports via ASC API | Multiple widget sizes, multi-account switch, **user-selectable display currency** (converts proceeds), real-downloads-vs-units toggle, redownloads on/off, haptics, no telemetry. Closest prior art to our widget; author abandoned it for a paid rewrite, so no active pressure from this one but code is reusable (MIT). |
| itsyconnect-macos | github.com/nickustinov/itsyconnect-macos | 128 | 2026-10-12 (active) | MIT | Electron + Next.js desktop app, self-hosted SQLite, no cloud | ASC metadata/TestFlight/Analytics/Reviews endpoints | Full ASC replacement: metadata editing across locales, AI translation (BYO LLM key), TestFlight tester management, **review reply drafting and reply-to-review via API**, credentials AES-256-GCM + macOS Keychain master key. Heaviest/most ambitious OSS tool; good reference for reviews UI, not for menu bar/widget pattern. |
| Applytics-trmnl | github.com/EricRogersTechnology/Applytics-trmnl | 1 | 2026-09-18 | MIT | TRMNL e-ink display plugin | n/a (not inspected in depth, low stars) | Niche: renders ASC metrics for a TRMNL e-ink device, not relevant to our stack beyond confirming demand for "stats on a small glanceable surface". |
| store-finance-desk | github.com/greatzhai/store-finance-desk (org solodept) | 10 | 2026-06-10 | MIT | Flutter desktop, local-first | App Store + Google Play finance | "Privacy-first local financial dashboard" for both stores; cross-platform parity idea (we're iOS-only, fine as-is). |
| app-store-connect-data-cli (`adc`) | github.com/BunnyxStudio/app-store-connect-data-cli | 8 | 2026-04-11 | Apache-2.0 | Swift CLI, Homebrew | Sales, Finance, Customer Reviews, Analytics | Explicitly **read-only**, normalizes monetary values to one **reporting currency**, has a configurable **display timezone**, JSON output mode for agents/cron. Clean scope discipline worth copying: "what this CLI does not do" list. Apache-2.0: code reusable with attribution. |
| app-store-connect-dashboard | github.com/igorkulman/app-store-connect-dashboard | 3 | 2026-09-29 | none (no LICENSE file — all rights reserved by default) | Node/JS self-hosted web dashboard | Sales reports | Downloads/purchases/revenue across all apps; no license file so **ideas only, no code reuse**. |
| OpenConnect | github.com/OddOmens/OpenConnect | 0 | 2026-10-10 (very active) | **MIT + Commons Clause** (source-available, no resale) | Docker self-hosted web dashboard | Sales & Trends, Finance, Customer Reviews, Analytics Reports, iTunes RSS-style charts | Richest feature set seen: proceeds with **currency conversion to a chosen display currency**, subscriptions (trials/offers/billing retry), reviews with developer responses, **ratings and Top Free/Paid/Grossing rankings across all 175 storefronts**, world map/device/territory breakdowns, a **"sync report" popup that diffs what changed since the last sync** (new reviews, rating deltas, chart moves, revised report dates), **incremental sync** (handful of requests per run, not a 365-day backfill), shareable PNG "stat cards", read-only container hardening. Commons Clause blocks commercial resale of the code itself but the mechanics (sync-report diffing, incremental sync, rankings via storefront loop) are freely copyable as ideas. |
| appleconnect | github.com/stanleyswiss/appleconnect | 0 | 2026-06-24 | MIT | Node/Express PWA, mobile-first | Sales & Trends report (gzip parse) | Server-side JWT so the `.p8` never reaches a browser; **daily FX table to roll multi-currency proceeds into one USD total**; disk-cached finalized reports for fast "all-time"; optional **web push notifications**; shows only READY_FOR_SALE apps by default (cuts noise from old/removed apps) — small idea worth stealing for our app list. |
| asc-terminal / "Orchard" | github.com/heocoi/asc-terminal | 0 | 2026-03-29 | MIT | TypeScript, self-hosted dashboard | Sales reports | Same "self-hosted sales dashboard" pattern as others above, nothing distinctive found beyond the README blurb; low effort to skip further study. |
| appstore-reports-dashboard | github.com/abataille/appstore-reports-dashboard | 1 | 2026-06-27 | MIT | JS local dashboard | Sales & Analytics | Generic local dashboard, no standout feature found in the metadata; not worth a deep README read given 1 star. |
| AppRankly | github.com/zmsp/AppRankly | 28 | 2026-10-09 (active) | **AGPL-3.0** | Docker, self-hosted, cross-platform (iOS + Android) | ASC + Google Play Console, plus **AI-assisted ASO**: keyword discovery via store autocomplete, keyword rank checks, competitor comparison, listing audits (OpenAI/Anthropic/Gemini, BYO key) | Strongest ASO angle of the batch: retention cohorts, survival curves, release markers overlaid on installs/uninstalls, zero-cost keyword discovery via store autocomplete scraping. AGPL-3.0 means **reusing its code would force our project to go AGPL too** — treat as ideas-only unless we want that license. |
| App-Store-Connect-CLI (`asc`) | github.com/rorkai/App-Store-Connect-CLI | **7,826** | 2026-10-14 (very active) | MIT | Go CLI, Homebrew/winget, Windows too | Builds, TestFlight, submissions, signing, screenshots, subscriptions, analytics | By far the most popular tool found (release automation, not a stats surface), but ships `analytics`/`sales`/`finance` report commands we could shell out to or crib request/parsing logic from (MIT, Go — would need a port or a subprocess call from Python). Also ships a 25-skill "agent skills" pack for driving it from Claude Code, an interesting distribution pattern. |
| ASC-CLI-UI ("ASC Manager") | github.com/prusaluy07/ASC-CLI-UI | 0 | 2026-07-03 | MIT | Native SwiftUI macOS app, wraps `asc` CLI, iPhone companion via CloudKit | Delegates everything to `asc` CLI | Good proof that a thin SwiftUI shell over a CLI backend works; its "Reports" screen just wraps `asc`'s analytics/sales/finance commands with a save-folder and auto-decompress — same pattern we could use for optional heavier reports instead of writing our own parser for every report type. CloudKit mirror to iPhone is a bigger idea (multi-device sync) beyond current scope. |
| mcp-app-store-connect | github.com/brunosemfio/mcp-app-store-connect | 0 | 2026-09-23 | Apache-2.0 | Python, FastMCP (read-only MCP server) | Analytics Reports, Sales and Trends, Finance Reports, Customer Reviews, perfPowerMetrics | Clean enumeration of the full read-only API surface we could still add: `list_customer_reviews` (reviews/ratings by territory), `download_finance_report` (fiscal-month proceeds), `get_perf_power_metrics` (crash/hang/energy metrics from Xcode org). Apache-2.0, Python — the closest-license, closest-language match to copy snippets from directly. |
| app-store-monitor | github.com/nakamekun/app-store-monitor | 1 | 2026-06-01 | MIT | Python stdlib-only CLI | `/v1/apps`, Analytics Reports (discovery/engagement/downloads/sessions) | Same language/stack as us (Python, ES256 JWT via OpenSSL, zero third-party deps). Features: SQLite history, Markdown daily KPI report, **Discord webhook with a once-per-metric-date guard** (dedupe so a cron re-run doesn't re-notify), deterministic **mock mode** for demos/tests without real credentials. The notification-dedupe idea and the mock-data-for-tests idea are both directly portable to our Python codebase (MIT). |

### Commercial (metadata from product pages / App Store listings; no pricing or exact numbers invented)

| Name | Platform | Notable features |
|---|---|---|
| App Vitals (potatostudios.dev) | iPhone app + medium Home Screen widget | Rolling 30-day downloads, first-time downloads, redownloads, proceeds, sales, refunds, updates, subscriptions, IAP, pre-orders, bundles; user picks up to 4 metrics for the widget; manual refresh with cached fallback for the widget. |
| Widgets for ASC: Metrics (aka "Metrics: ASC Widgets & Sales") | iOS/iPad widgets (not macOS-verified) | Dashboard across every tracked app with **green/red delta pills vs. the previous period**, switchable 7/14/30/90-day windows, 90-day trend charts, page views/sessions/crashes/active devices/installs/deletions, per-version crash counts tied to "What's New", reviews with developer-response status, a **"Daily AI Insight"** on-device summary of portfolio movement vs. prior period (uses Apple's Foundation Models). The delta-vs-previous-period pill and the on-device LLM daily summary are both concrete, scoped ideas. |
| Store Analytics App & Widget | iOS/iPad | Sales, revenue, proceeds, downloads in a "simple dashboard"; direct ASC API fetch. No standout beyond the baseline. |
| App Sales+ / App Sales - Store Reports | iOS | Widget variety for sales analytics; nothing beyond baseline found. |
| SoldIt: Sales Tracker & Widget | iOS | "Stop refreshing App Store Connect, celebrate every sale" — framed around real-time/near-real-time sale celebration (push-style), profit/income/subscriber tracking. |
| Tallyr: App Revenue Tracker | iPhone only | **"Know the moment someone buys your app" on the Lock Screen**, shows net proceeds after Apple's cut, not just gross. Lock Screen live-ish notification is the standout idea. |
| Helm (helm-app.com) | Native Mac + iPhone app, plus `helm-asc` CLI | Full ASC workflow suite (releases, ASO, screenshots, TestFlight, reviews, IAPs, accessibility nutrition labels, AI localization). iPhone app has **reviews, TestFlight, notifications, Home Screen widget, and a "Passport" App Clip for beta stamps**. Closest commercial analogue to "a widget plus a bigger companion app"; reviews + push notifications are the pieces we lack. |
| AppSales for App Store Connect (RanduSoft) | iPhone, paid ($2.99) | Widget-based sales analytics, no distinguishing detail beyond listing text. |
| Revenue Bar / MRRbar (RevenueCat-focused, found while searching "RC Menu Stats") | macOS menu bar | Not ASC-native (they read RevenueCat's own API for MRR/ARR), but confirm the "menu bar always-visible revenue number" pattern is a validated commercial niche; "RC Menu Stats" itself did not resolve to a real listing — treat as not found after 2 searches. |
| AppScout | n/a | Could not find via "Show HN AppScout App Store Connect" (0 results after 2 searches) — **skipped per cap**. |
| appfigures | Web + mobile, not menu bar/widget-native | Broad ASO suite: downloads, revenue, reviews, keyword ranks, competitor tracking, store feature detection. Confirms demand for competitor/keyword tracking beyond our own-app scope; likely overkill for our project's purpose. |
| Review-alert services (Mentio, ReviewsMonitor, AppStoreReview) | Web/Slack/email/Telegram bots, not widgets | Pure notification layer: instant alert the moment a new review lands, some also watch competitor reviews and chart position. Validates that "new review -> push/webhook" is a standalone, well-liked feature worth doing cheaply (poll `customerReviews` endpoint, diff against last-seen id). |

## Feature matrix

| Feature | AC Widget | OpenConnect | itsyconnect | appleconnect | AppRankly | asc CLI | App Vitals | Widgets for ASC | Helm | Tallyr | **Dev Stats (us)** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Downloads (day/week/all-time) | yes | yes | yes | yes | yes | yes | yes | yes | yes | n/a | **yes** |
| Redownloads / updates / IAP units | yes | yes | n/a | yes (IAP) | n/a | yes | yes | n/a | n/a | n/a | **yes** |
| Impressions / page views / conversion | n/a | yes | yes | n/a | n/a | yes | n/a | yes | n/a | n/a | **yes** |
| Revenue / proceeds | yes (multi-currency) | yes (multi-currency) | n/a | yes (FX to USD) | n/a | yes | yes | yes | n/a | yes (net of Apple's cut) | **no** |
| Reviews / ratings | n/a | yes (all 175 storefronts) | yes (+ AI reply drafting) | n/a | n/a | n/a | n/a | yes | yes | n/a | **no** |
| Rankings / chart position | n/a | yes | n/a | n/a | n/a (ASO keyword rank, not chart) | n/a | n/a | n/a | n/a | n/a | **no** |
| Country/territory breakdown | n/a | yes (map) | n/a | yes | n/a | n/a | n/a | n/a | n/a | n/a | **no** |
| Period-over-period comparison | n/a | yes (sync report diff) | n/a | n/a | n/a | n/a | n/a | yes (delta pills) | n/a | n/a | **no** |
| Notifications / alerts | n/a | n/a (just a sync popup) | n/a | yes (web push) | n/a | n/a | n/a | n/a | yes | yes (lock screen) | **no** |
| Subscriptions | n/a | yes | n/a | n/a | n/a | yes | yes | n/a | n/a | yes | **no** |
| TestFlight | n/a | n/a | yes | n/a | n/a | yes | n/a | n/a | yes | n/a | **no** |
| Multi-account | yes | n/a | yes | n/a | n/a | n/a | n/a | n/a | n/a | n/a | **no** |
| GitHub contributions | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | **yes (unique to us)** |

## Best ideas worth stealing (ranked, value-for-indie-dev vs. effort)

1. **Revenue/proceeds (converted to a display currency)** — highest value, moderate effort.
   - API: Sales and Trends report (`reportType=SALES`, `reportSubType=SUMMARY`) already gives
     `Proceeds` and `Currency of Proceeds` per row; alternatively Finance Reports for fiscal-month
     totals. Pattern to copy: appleconnect's daily-FX-table conversion, or AC Widget's
     user-selected currency.
   - Our code: extend `appstore.py` (same report rows we already parse for downloads, add
     `Proceeds`/`Customer Price`/`Currency of Proceeds` columns), add a small FX lookup (daily
     rate from a free API or exchangerate host, cached in `~/.config/asc-menubar/cache/`), surface
     a `revenue_today`/`revenue_week`/`revenue_all_time` number in `devstats.py` snapshot, add a
     row in `widget/Shared/Views.swift`. Rough effort: 4-7 steps (parser change, FX fetch+cache,
     snapshot field, SwiftBar line, widget view, README update, manual test against real report).
   - Risks: Apple's per-row proceeds are already net of their cut but in the storefront's local
     currency; FX source must be reliable and cached (no live lookup from the widget itself, which
     is sandboxed with no network). Report delay is the same ~1-2 days as downloads, nothing new.

2. **New-review notification (not a full reviews dashboard)** — high value, low effort.
   - API: `GET /v1/apps/{id}/customerReviews` (needs a key role that includes reviews access).
     Diff the latest review id/date against the last-seen id stored in cache, like
     app-store-monitor's "once-per-metric-date guard" for Discord.
   - Our code: new `reviews.py` (list reviews, compare to `~/.config/asc-menubar/cache/last_review.json`),
     surface "N new reviews" + average rating in `devstats.py`/menu, optional macOS
     `osascript -e 'display notification'` or just a flagged line in the SwiftBar menu (no OS-level
     push needed for a 30-min-poll menu bar app). Rough effort: 3-5 steps.
   - Risks: review endpoint requires the right API key role (may need a role bump like the
     existing Admin-then-Sales-and-Reports dance for impressions); Apple paginates and
     rate-limits, so don't full-backfill every run — only fetch newest page.

3. **Ratings + average rating per app (no reviews UI)** — medium value, very low effort.
   - API: no ASC credentials needed at all — the **public `itunes.apple.com/lookup?id=...`**
     endpoint returns `averageUserRating`, `averageUserRatingForCurrentVersion`,
     `userRatingCount` for any public app, confirmed live in this research (full JSON retrieved).
   - Our code: tiny addition to `appstore.py` or a new `ratings.py`: one unauthenticated HTTP call
     per tracked app, cache for a day. Add to snapshot and widget. Rough effort: 2-3 steps, by far
     the cheapest win here, no .p8/JWT involved.
   - Risks: only works for apps already live on the Store (fine for us); no country breakdown
     this way, only the storefront iTunes is queried against (pick one territory, document it).

4. **Period-over-period delta pills** ("+12% vs last week") — medium value, low-medium effort.
   - API: none new, pure derived math over report rows we already fetch for downloads
     (and revenue once added): current period vs. immediately preceding period of equal length.
   - Our code: a small helper in `devstats.py` (or `analytics.py`) to compute delta % given two
     numbers, add to snapshot alongside existing weekly/day numbers, render as a colored
     up/down glyph in both the SwiftBar menu and `Views.swift`. Rough effort: 3-4 steps.
   - Risks: none significant; just needs a stable "previous period" definition to avoid confusing
     numbers (match App-Vitals/Widgets-for-ASC convention of trailing N days vs. prior N days).

5. **Chart ranking (Top Free/Paid/Grossing position)** — lower value for most indie apps outside
   top charts, higher effort.
   - API: Apple's public RSS-style "Top Charts" feeds (`itunes.apple.com/{cc}/rss/topfreeapplications/...`)
     per storefront/category, as OpenConnect does across all 175 storefronts.
   - Our code: new module to poll chart feeds for configured storefronts/categories, cache and
     diff. Rough effort: 6-10 steps (storefront loop, category mapping, caching, rank-change
     diffing, UI for showing "not ranked" gracefully). Lower priority unless the app is realistically
     chart-adjacent.
   - Risks: scraping an RSS feed per storefront is a lot of network calls for an app that rarely
     ranks; easy to deprioritize behind revenue/reviews/ratings.

6. **Subscriptions / TestFlight / multi-account** — real indie needs but out of scope for a
   "glance at your numbers" widget; defer unless the user's own apps have subscriptions. If
   needed later, Sales and Trends `reportSubType=SUBSCRIPTION`/`SUBSCRIPTION_EVENT` and the
   `betaTesters`/`builds` endpoints are the entry points; effort is dashboard-sized (10+ steps),
   not widget-sized.

## Licensing notes

- **Directly reusable with attribution:** `app-store-connect-data-cli` (Apache-2.0, Swift),
  `mcp-app-store-connect` (Apache-2.0, Python — same language as us, closest code to actually
  copy from), `app-store-monitor` (MIT, Python stdlib-only, same stack as us), AC Widget (MIT,
  Swift, for widget-side currency/multi-account patterns), `appleconnect` (MIT), `asc` CLI (MIT,
  Go — would need a port, not a straight copy).
- **Ideas only, not code:** OpenConnect (MIT + Commons Clause — source-available but the
  Commons Clause forbids selling the software itself; fine to read and reimplement the sync-diff
  and multi-storefront-ranking approach ourselves), AppRankly (AGPL-3.0 — copying code would
  require relicensing our whole project AGPL, not worth it for a menu bar tool), `app-store-connect-dashboard`
  (no LICENSE file = all rights reserved by default, do not copy).
- Commercial apps (App Vitals, Widgets for ASC, Helm, Tallyr, SoldIt, etc.): no source available,
  ideas only, confirmed from public product pages / App Store listings, never from decompiled
  binaries.

## Skipped after cap

- AppScout: no results after 2 searches.
- "RC Menu Stats" (as literally named): did not resolve to a real listing; found adjacent
  RevenueCat menu bar tools (Revenue Bar, MRRbar) instead, noted above.
