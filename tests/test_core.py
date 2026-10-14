"""Behavior tests for the data layer. No network: API calls are replaced with fixtures.

Run: .venv/bin/python -m unittest discover -s tests
"""
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analytics  # noqa: E402
import appstore  # noqa: E402
import devstats  # noqa: E402
import fx  # noqa: E402
import github  # noqa: E402
import ratings  # noqa: E402
import reviews  # noqa: E402


def sale(ptype, units, app="100", country="TR", proceeds="0", currency="", parent=""):
    return {"Product Type Identifier": ptype, "Units": str(units), "SKU": "sku-" + app,
            "Parent Identifier": parent, "Apple Identifier": app, "Developer Proceeds": proceeds,
            "Currency of Proceeds": currency, "Country Code": country}


class AppStoreCounterTest(unittest.TestCase):
    def test_counts_kinds_countries_and_iap_parent(self):
        c = appstore.Counter({"sku-100": "100"})
        c.add([sale("1", 3), sale("1F", 2, country="US"), sale("3", 1), sale("7", 5),
               sale("IA1", 2, app="900", parent="sku-100", proceeds="1.50", currency="USD"),
               sale("ZZ", 9)])  # unknown types are ignored
        self.assertEqual(c.of("100"), {"new": 5, "re": 1, "upd": 5, "iap": 2})
        self.assertEqual(c.top_countries(), [("TR", 3), ("US", 2)])
        # proceeds are per unit: 2 x 1.50 USD
        self.assertEqual(c.revenue({"USD": 1.0}), 3.0)

    def test_revenue_converts_and_reports_missing_rate(self):
        c = appstore.Counter({})
        c.add([sale("IA1", 1, proceeds="10", currency="EUR"), sale("IA1", 4, proceeds="25", currency="TRY")])
        table = {"TRY": 1.0, "EUR": 0.025}  # 1 TRY = 0.025 EUR, so 10 EUR = 400 TRY
        self.assertEqual(c.revenue(table), 500.0)
        self.assertIsNone(c.revenue({"TRY": 1.0}))

    def test_change(self):
        self.assertEqual(appstore.change(6, 4), 50.0)
        self.assertEqual(appstore.change(1, 4), -75.0)
        self.assertIsNone(appstore.change(5, 0))

    def test_month_falls_back_to_daily_when_monthly_not_published(self):
        calls = []

        def fake_fetch(cfg, freq, key, end):
            calls.append(freq)
            if freq == "MONTHLY":
                return None
            return [sale("1", 1)]

        with mock.patch.object(appstore, "fetch", fake_fetch):
            rows = appstore.month_rows({}, 2026, 9, dt.date(2026, 10, 3))
        self.assertEqual(len(rows), 30)  # one row per day of September
        self.assertEqual(calls[0], "MONTHLY")


class FxTest(unittest.TestCase):
    def test_convert(self):
        self.assertAlmostEqual(fx.convert(10, "USD", {"USD": 0.02}), 500.0)
        self.assertIsNone(fx.convert(10, "XXX", {"USD": 0.02}))


class RatingsTest(unittest.TestCase):
    def test_combine_weights_by_count(self):
        self.assertEqual(ratings.combine([(5.0, 3), (3.0, 1)]), (4.5, 4))
        self.assertEqual(ratings.combine([]), (None, 0))

    def test_new_since_uses_entry_at_least_a_week_old(self):
        hist = {"2026-10-01": {"a": 10}, "2026-10-06": {"a": 12}, "2026-10-12": {"a": 14}}
        self.assertEqual(ratings.new_since(hist, "a", 15, dt.date(2026, 10, 14)), 3)
        self.assertIsNone(ratings.new_since(hist, "a", 15, dt.date(2026, 10, 5)))


class ReviewsTest(unittest.TestCase):
    def test_first_run_is_silent_then_only_unseen(self):
        items = [{"id": "1"}, {"id": "2"}]
        self.assertEqual(reviews.diff(items, None), [])
        self.assertEqual(reviews.diff(items, {"1"}), [{"id": "2"}])

    def test_forbidden_key_is_reported_not_raised(self):
        import urllib.error
        err = urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
        with mock.patch.object(reviews.asc, "load_config", return_value={}), \
                mock.patch.object(reviews, "fetch", side_effect=err):
            out = reviews.collect({"1": "App"})
        self.assertFalse(out["available"])


class StreakTest(unittest.TestCase):
    def days(self, *dates):
        return {d: 1 for d in dates}

    def test_today_without_contributions_keeps_streak(self):
        d = self.days("2026-10-11", "2026-10-12", "2026-10-13")
        self.assertEqual(github.streaks(d, dt.date(2026, 10, 14)), (3, 3))

    def test_gap_resets_current_but_not_longest(self):
        d = self.days("2025-12-30", "2025-12-31", "2026-01-01", "2026-01-02", "2026-10-13", "2026-10-14")
        self.assertEqual(github.streaks(d, dt.date(2026, 10, 14)), (2, 4))  # longest spans the year change

    def test_zero_counts_are_not_contributions(self):
        d = {"2026-10-13": 0, "2026-10-14": 2}
        self.assertEqual(github.streaks(d, dt.date(2026, 10, 14)), (1, 1))


class AnalyticsTest(unittest.TestCase):
    ENG = ("Date\tApp Apple Identifier\tEvent\tPage Type\tCounts\tUnique Counts\n"
           "2026-10-12\t100\tImpression\tNo page\t100\t80\n"
           "2026-10-12\t100\tPage view\tProduct page\t20\t18\n"
           "2026-10-12\t100\tTap\tNo page\t15\t15\n")
    DL = ("Date\tApp Apple Identifier\tDownload Type\tCounts\n"
          "2026-10-12\t100\tFirst-time download\t3\n"
          "2026-10-12\t100\tAuto-update\t9\n")

    def test_parse_and_conversion(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(analytics, "CACHE", tmp), \
                mock.patch.object(analytics.asc, "paginate", lambda cfg, path, params=None: iter([{"attributes": {"url": path}}])), \
                mock.patch.object(analytics.asc, "download", lambda url: (self.ENG if "E" in url else self.DL).encode()):
            e = analytics.instance_totals(None, "E", analytics.ENGAGEMENT)
            d = analytics.instance_totals(None, "D", analytics.DOWNLOADS)
        key = "2026-10-12|100"
        days = {"2026-10-12": {"100": {**e[key], **d[key]}}}
        s = analytics.summarize(days)["100"]
        self.assertEqual((s["impressions"], s["page_views"], s["downloads"]), (100, 20, 3))
        self.assertEqual(s["conversion"], 3.8)  # 3 / 80 unique impressions


class FormattingTest(unittest.TestCase):
    def test_money_arrow_safe(self):
        self.assertEqual(devstats.money(0, "TRY"), "₺0")
        self.assertEqual(devstats.money(12.5, "USD"), "$12,50")
        self.assertEqual(devstats.money(1234.4, "TRY"), "₺1.234")
        self.assertEqual(devstats.money(5, "SAR"), "5,00 SAR")
        self.assertEqual(devstats.arrow(12.4), "▲%12")
        self.assertEqual(devstats.arrow(-3), "▼%3")
        self.assertEqual(devstats.arrow(None), "")
        self.assertEqual(devstats.safe("--a | b\nc"), "a / b c")


class FallbackTest(unittest.TestCase):
    def test_failed_source_keeps_last_good_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap_path = os.path.join(tmp, "snapshot.json")
            with open(snap_path, "w") as f:
                json.dump({"github": {"login": "old"}, "fetched": {"github": "2026-10-14T10:00:00+03:00"}}, f)

            def boom():
                raise RuntimeError("offline")

            with mock.patch.object(devstats, "SNAPSHOT", snap_path), \
                    mock.patch.object(devstats.appstore, "collect", boom), \
                    mock.patch.object(devstats.analytics, "collect", lambda: {"ready": False}), \
                    mock.patch.object(devstats.github, "collect", boom):
                snap, errors = devstats.gather()
            self.assertEqual(snap["github"], {"login": "old"})
            self.assertIn("github", errors)
            with open(snap_path) as f:
                self.assertEqual(json.load(f)["fetched"]["github"], "2026-10-14T10:00:00+03:00")
            buf = io.StringIO()
            with redirect_stdout(buf):
                devstats.stale_note("github", errors, snap)
            self.assertIn("14.10 10:00", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
