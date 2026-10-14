"""Security regression tests: untrusted text in the menu, credential scope, input checks.

Run: .venv/bin/python -m unittest discover -s tests
"""
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import asc  # noqa: E402
import devstats  # noqa: E402

# Swift's CharacterSet.newlines, which SwiftBar uses to split plugin output into lines
SWIFT_NEWLINES = "\n\r\x0b\x0c\x85\u2028\u2029"


def swiftbar_lines(output):
    for ch in SWIFT_NEWLINES[1:]:
        output = output.replace(ch, "\n")
    return [line for line in output.split("\n") if line]


def params(line):
    """Parameters the way SwiftBar reads them: everything after the first '|'."""
    return line.partition("|")[2]


EVIL = ("Harika\u2028Güncelleme gerekli | bash=/usr/bin/open param1=-a param2=Calculator\r"
        "--- \x85href=https://evil.example \u202e tersten\u200b")


class MenuInjectionTest(unittest.TestCase):
    def review(self, **over):
        r = {"id": "1", "app": "123", "app_name": "App", "rating": 5, "territory": "TUR", "date": "2026-10-14",
             "nickname": EVIL, "title": EVIL, "body": EVIL}
        r.update(over)
        return r

    def render(self, rv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            devstats.emit_guarded(lambda: devstats.review_lines(rv, None, "--"))
        return buf.getvalue()

    def test_review_text_cannot_add_lines_or_parameters(self):
        out = self.render({"latest": [self.review()]})
        lines = swiftbar_lines(out)
        # every line still belongs to the review submenu, none became a top-level item
        self.assertTrue(all(line.startswith("--") for line in lines), lines)
        for line in lines:
            self.assertNotIn("bash=", params(line))
            self.assertNotIn("evil.example", params(line))
        self.assertNotIn("\u202e", out)  # bidi override removed
        self.assertNotIn("\u200b", out)

    def test_safe_strips_every_swift_newline_and_separator(self):
        for ch in SWIFT_NEWLINES:
            self.assertNotIn(ch, devstats.safe(f"a{ch}b"))
        self.assertEqual(devstats.safe("--- x | y"), "x / y")

    def test_bad_rating_and_date_do_not_crash(self):
        out = self.render({"latest": [self.review(rating="5; rm", date="not-a-date", app="1/../x")]})
        self.assertIn("–", out)
        self.assertNotIn("Cevapla", out)  # non-numeric app id gets no link
        self.assertFalse(any("href=" in params(line) for line in swiftbar_lines(out)))

    def test_guard_removes_stray_breaks_from_any_field(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            devstats.emit_guarded(lambda: print("title\u2028injected | bash=x"))
        self.assertEqual(len(swiftbar_lines(buf.getvalue())), 1)

    def test_repo_link_only_for_github_urls(self):
        g = {"login": "me", "today": 1, "week": 1, "last_year": 1, "alltime": 1, "since": 2020,
             "breakdown": {"commit": 0, "pr": 0, "review": 0, "issue": 0, "private": 0}, "series": [],
             "top_repos": [{"name": "me/ok", "url": "https://github.com/me/ok", "commits": 2},
                           {"name": "me/bad", "url": "https://github.com/me/bad bash=/bin/sh", "commits": 1}]}
        buf = io.StringIO()
        with redirect_stdout(buf):
            devstats.render_github({"github": g}, {})
        out = buf.getvalue()
        self.assertIn("href=https://github.com/me/ok", out)
        self.assertNotIn("bash=", out)


class CredentialScopeTest(unittest.TestCase):
    def test_token_only_sent_to_apple_api_over_https(self):
        self.assertEqual(asc.api_url("/v1/apps"), "https://api.appstoreconnect.apple.com/v1/apps")
        for url in ("https://evil.example/v1/apps", "http://api.appstoreconnect.apple.com/v1/apps",
                    "https://api.appstoreconnect.apple.com.evil.example/x",
                    "https://evil.example@api.appstoreconnect.apple.com.evil.example/"):
            with self.assertRaises(ValueError, msg=url):
                asc.api_url(url)

    def test_paging_link_to_other_host_is_refused_before_signing(self):
        pages = iter([{"data": [1], "links": {"next": "https://evil.example/next"}}])
        with mock.patch.object(asc, "token", side_effect=AssertionError("signed")) as tok, \
                mock.patch.object(asc.urllib.request, "urlopen") as op:
            op.side_effect = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network"))
            with mock.patch.object(asc, "request", wraps=asc.request) as req:
                req.side_effect = [next(pages), asc.request]
                gen = asc.paginate({}, "/v1/apps")
                self.assertEqual(next(gen), 1)
                req.side_effect = None
                with self.assertRaises(ValueError):
                    next(gen)
        tok.assert_not_called()

    def test_key_id_cannot_escape_config_dir(self):
        with self.assertRaises(ValueError):
            asc.key_path({"key_id": "../../etc/x"})

    def test_private_dir_and_key_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "cfg")
            os.makedirs(d, mode=0o755)
            os.chmod(d, 0o755)
            with mock.patch.object(asc, "CONFIG_DIR", d):
                asc.ensure_private_dir()
                self.assertEqual(os.stat(d).st_mode & 0o777, 0o700)


class ConfigureTest(unittest.TestCase):
    def run_configure(self, *args, home):
        env = {"HOME": home, "PATH": "/usr/bin:/bin"}
        return subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "configure.py"), *args],
                              capture_output=True, text=True, env=env)

    def test_rejects_malformed_ids(self):
        with tempfile.TemporaryDirectory() as home:
            r = self.run_configure("--issuer-id", "x", "--key-id", "../evil", "--vendor-number", "1", home=home)
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse(os.path.exists(os.path.join(home, ".config", "asc-menubar", "config.json")))

    def test_moves_key_and_writes_private_files(self):
        with tempfile.TemporaryDirectory() as home:
            src = os.path.join(home, "AuthKey_ABCDE12345.p8")
            with open(src, "w") as f:
                f.write("-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----\n")
            os.chmod(src, 0o644)
            r = self.run_configure("--issuer-id", "00000000-0000-0000-0000-000000000000", "--key-id", "ABCDE12345",
                                   "--vendor-number", "12345678", "--p8", src, "--currency", "try", home=home)
            self.assertEqual(r.returncode, 0, r.stderr)
            cfg_dir = os.path.join(home, ".config", "asc-menubar")
            self.assertFalse(os.path.exists(src))
            self.assertEqual(os.stat(cfg_dir).st_mode & 0o777, 0o700)
            for name in ("AuthKey_ABCDE12345.p8", "config.json"):
                self.assertEqual(os.stat(os.path.join(cfg_dir, name)).st_mode & 0o777, 0o600, name)
            self.assertNotIn("PRIVATE KEY", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
