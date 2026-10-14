"""Menu bar output (SwiftBar) for App Store and GitHub stats, plus the widget snapshot.

Run through plugins/devstats.30m.sh. Writes ~/.config/asc-menubar/snapshot.json,
which the desktop widget reads. When a source fails, its last good data is shown
with the time it was fetched, so the menu and widget never go blank.
"""
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
import textwrap
import unicodedata
import urllib.parse
from contextlib import redirect_stdout

import analytics
import appstore
import asc
import github
import ratings
import reviews

SNAPSHOT = os.path.join(asc.CONFIG_DIR, "snapshot.json")
MONO, BOLD, GRAY = "font=Menlo size=12", "font=Menlo-Bold size=12", "size=11 color=gray"
WEEKDAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
SYMBOLS = {"TRY": "₺", "USD": "$", "EUR": "€", "GBP": "£"}
PLUGIN_ID = "devstats.30m.sh"


# ---------- formatting ----------

def num(n):
    return "–" if n is None else f"{n:,}".replace(",", ".")


def pct(p):
    return "–" if p is None else f"%{p:.1f}".replace(".", ",")


def arrow(p):
    """Monochrome change marker: ▲%12, ▼%3, =, or '' when there is nothing to compare."""
    if p is None:
        return ""
    if p == 0:
        return "="
    return ("▲" if p > 0 else "▼") + f"%{abs(p):.0f}"


def money(v, currency):
    if v is None:
        return "–"
    s = f"{v:,.0f}" if v == 0 or abs(v) >= 100 else f"{v:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{SYMBOLS.get(currency, '')}{s}" if currency in SYMBOLS else f"{s} {currency}"


def stars(avg):
    return "–" if avg is None else f"★ {avg:.1f}".replace(".", ",")


# SwiftBar splits plugin output on every character in CharacterSet.newlines and treats
# the first '|' as the start of parameters (bash=, href=, ...), a leading '-' as nesting.
LINE_BREAKS = "\r\x0b\x0c\x85\u2028\u2029"
REPO_URL = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def safe(text):
    """Make untrusted text (reviews, names, errors) inert inside one SwiftBar line.

    Drops control, format (bidi overrides, zero-width) and line/paragraph separator
    characters, replaces '|' so no parameters can be injected, and strips leading '-'
    so the text cannot change nesting or become a separator.
    """
    text = "".join(" " if unicodedata.category(c) in ("Cc", "Cf", "Zl", "Zp") else c for c in str(text))
    text = " ".join(text.replace("|", "/").split())
    return text.lstrip("- ").strip()


def emit_guarded(render):
    """Run `render`, then remove any stray line breaks SwiftBar would split on.

    Defense in depth: even if a field escaped safe(), it cannot start a new menu line.
    """
    buf = io.StringIO()
    with redirect_stdout(buf):
        render()
    out = buf.getvalue().translate({ord(c): " " for c in LINE_BREAKS})
    sys.stdout.write(out)


def table_row(label, x, y, z, width):
    return f"{label.ljust(width)}  {x:>6} {y:>7} {z:>8}"


# ---------- data ----------

def load_old():
    if os.path.exists(SNAPSHOT):
        with open(SNAPSHOT) as f:
            return json.load(f)
    return {}


def write_snapshot(snap):
    tmp = SNAPSHOT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(snap, f, ensure_ascii=False)
    os.replace(tmp, SNAPSHOT)


def gather():
    """Run every source; on failure fall back to the previous snapshot's section."""
    old = load_old()
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    data, errors, fetched = {}, {}, dict(old.get("fetched", {}))

    def run(key, fn):
        try:
            data[key] = fn()
            fetched[key] = now
        except Exception as e:  # one source failing must not blank the others
            data[key] = old.get(key)
            errors[key] = f"{type(e).__name__}: {str(e)[:100]}"

    run("appstore", appstore.collect)
    run("analytics", analytics.collect)
    run("github", github.collect)
    a = data.get("appstore")
    if a:
        apps = {r["id"]: r["name"] for r in a["apps"]}
        run("ratings", lambda: ratings.collect(list(apps), a.get("storefronts", [])))
        run("reviews", lambda: reviews.collect(apps))
    snap = {"generated_at": now, "fetched": fetched, **data}
    write_snapshot(snap)
    return snap, errors


def notify(title, subtitle, body):
    q = urllib.parse.urlencode({"plugin": PLUGIN_ID, "title": title, "subtitle": subtitle, "body": body},
                               quote_via=urllib.parse.quote)
    subprocess.run(["open", "-g", f"swiftbar://notify?{q}"], check=False)


def notify_new_reviews(rv):
    new = (rv or {}).get("new") or []
    for r in new[:3]:
        stars_text = "★" * r["rating"] if isinstance(r.get("rating"), int) and 0 <= r["rating"] <= 5 else ""
        notify("Yeni yorum: " + safe(r["app_name"]), f"{stars_text} {safe(r['title'])}"[:120], safe(r["body"])[:200])
    if len(new) > 3:
        notify("Dev Stats", f"{len(new)} yeni yorum", "Menüden Yorumlar bölümüne bak.")


# ---------- rendering ----------

def stale_note(key, errors, snap):
    if key not in errors:
        return
    when = snap.get("fetched", {}).get(key)
    t = dt.datetime.fromisoformat(when).strftime("%d.%m %H:%M") if when else "hiç"
    print(f"Güncellenemedi, son veri {t}: {safe(errors[key])} | {GRAY}")


def funnel_rows(an, app, width, prefix=""):
    if not an or not an.get("ready"):
        return
    blocks = [an[p].get(app, {}) for p in ("day", "week", "all")]
    for label, key, fmt in (("Impressions", "impressions", num), ("Sayfa görüntüleme", "page_views", num),
                            ("Dönüşüm", "conversion", pct)):
        print(prefix + table_row(label, *(fmt(b.get(key)) for b in blocks), width) + f" | {MONO}")


def review_lines(rv, app=None, prefix=""):
    items = [r for r in rv.get("latest", []) if app is None or r["app"] == app]
    for r in items:
        rating = r["rating"] if isinstance(r.get("rating"), int) and 0 <= r["rating"] <= 5 else 0
        name = safe(r["app_name"]) + "  " if app is None else ""
        print(f"{prefix}{'★' * rating:<5} {name}{safe(r['title'])[:40]} | {MONO}")
        try:
            when = dt.date.fromisoformat(r["date"]).strftime("%d.%m.%Y")
        except (TypeError, ValueError):
            when = "–"
        print(f"{prefix}--{safe(r['territory'])[:3]} · {when} · {safe(r['nickname'])[:40]} | {GRAY}")
        for line in textwrap.wrap(safe(r["body"]), 60)[:6]:
            print(f"{prefix}--{safe(line)} | size=12")
        if str(r.get("app", "")).isdigit():
            print(f"{prefix}--Cevapla (App Store Connect) | href=https://appstoreconnect.apple.com/apps/{r['app']}"
                  "/distribution/activity/ios/ratingsResponses")


def compact_row(label, x, y, z, width):
    return f"{label[:width].ljust(width)} {x:>4} {y:>5} {z:>6}"


def app_submenu(r, an, rt, rv, cur):
    """Everything about one app, one level down."""
    w = len("Sayfa görüntüleme")
    print("--" + table_row("", "Gün", "Hafta", "Toplam", w) + f" | {BOLD}")
    for label, k in (("Yeni indirme", "new"), ("Yeniden indirme", "re"),
                     ("Güncelleme", "upd"), ("Satın alma", "iap")):
        print("--" + table_row(label, r["day"][k], r["week"][k], num(r["all"][k]), w) + f" | {MONO}")
    rev = r.get("revenue", {})
    if rev.get("all"):
        print("--" + table_row(f"Gelir ({cur})", money(rev.get("day"), cur), money(rev.get("week"), cur),
                               money(rev.get("all"), cur), w) + f" | {MONO}")
    funnel_rows(an, r["id"], w, "--")
    print("-----")
    app_rt = (rt or {}).get("apps", {}).get(r["id"], {})
    if app_rt.get("count"):
        by_cc = ", ".join(f"{cc.upper()} {v[0]:.1f}".replace(".", ",") + f" ({v[1]})"
                          for cc, v in list(app_rt["countries"].items())[:4])
        print(f"--Puan {stars(app_rt['average'])} · {app_rt['count']} puan · {by_cc} | {MONO}")
    if r.get("countries"):
        print("--Ülkeler: " + ", ".join(f"{c} {n}" for c, n in r["countries"]) + f" | {MONO}")
    if rv and rv.get("available"):
        review_lines(rv, r["id"], "--")
    if str(r["id"]).isdigit():
        print(f"--App Store Connect'te aç | href=https://appstoreconnect.apple.com/apps/{r['id']}/analytics")


def render_appstore(snap, errors):
    a, an, rt, rv = snap.get("appstore"), snap.get("analytics"), snap.get("ratings"), snap.get("reviews")
    if not a:
        print(f"App Store | {BOLD} sfimage=arrow.down.circle")
        stale_note("appstore", errors, snap)
        return
    cur = a.get("currency", "USD")
    change = arrow(a.get("week_change"))
    print(f"App Store   hafta {a['week']} {change}   toplam {num(a['all'])} | {BOLD} sfimage=arrow.down.circle")
    stale_note("appstore", errors, snap)

    active = [r for r in a["apps"] if r["all"]["new"] or r["all"]["re"]]
    idle = [r for r in a["apps"] if r not in active]
    w = min(14, max([len(r["name"]) for r in active] + [10]))
    print(compact_row("", "Gün", "Hafta", "Toplam", w) + f" | font=Menlo size=10 color=gray")
    for r in active:
        mark = arrow(appstore.change(r["week"]["new"], r["prev_week"]["new"]))
        print(compact_row(safe(r["name"]), r["day"]["new"], r["week"]["new"], num(r["all"]["new"]), w)
              + f" {mark} | {MONO}")
        app_submenu(r, an, rt, rv, cur)
    if idle:
        print(f"Henüz indirmesi olmayan {len(idle)} uygulama | {GRAY}")
        for r in idle:
            print(f"--{safe(r['name'])} | {MONO}")
            if str(r["id"]).isdigit():
                print(f"----App Store Connect'te aç | href=https://appstoreconnect.apple.com/apps/{r['id']}/analytics")

    # one summary row; the rest lives one level down
    parts = []
    if rt and rt.get("count"):
        parts.append(f"{stars(rt['average'])} · {rt['count']} puan")
    if rv and rv.get("available"):
        new = len(rv.get("new") or [])
        parts.append(f"{rv['total']} yorum" + (f" ({new} yeni)" if new else ""))
    print(("   ".join(parts) or "Ayrıntılar") + f" | {MONO}")
    if rv and rv.get("available") and rv.get("latest"):
        print(f"--Son yorumlar | {BOLD}")
        review_lines(rv, None, "--")
        print("-----")
    elif rv:
        print(f"--Yorumlar: {safe(rv.get('reason', ''))} | {GRAY}")
    rev = a.get("revenue", {})
    w2 = len("Sayfa görüntüleme")
    print("--" + table_row("", "Gün", "Hafta", "Toplam", w2) + f" | {BOLD}")
    print("--" + table_row(f"Gelir ({cur})", money(rev.get("day"), cur), money(rev.get("week"), cur),
                           money(rev.get("all"), cur), w2) + f" | {MONO}")
    funnel_rows(an, "_all", w2, "--")
    if a.get("countries"):
        print("-----")
        print("--Ülkeler (tüm zamanlar): " + ", ".join(f"{c} {n}" for c, n in a["countries"]) + f" | {MONO}")
    print("-----")
    day = dt.date.fromisoformat(a["last_day"]).strftime("%d.%m") if a["last_day"] else "–"
    print(f"--Gün: son rapor ({day}, Pasifik saati). ▲▼: geçen haftanın aynı günlerine göre. | {GRAY}")
    if not an or not an.get("ready"):
        print(f"--Impressions ve dönüşüm: Apple raporu hazırlanıyor (1-2 gün) | {GRAY}")
    else:
        print(f"--Dönüşüm = indirme / tekil impression. | {GRAY}")
    print(f"--Gelir: Apple kesintisi sonrası, bugünkü kurla çevrildi. | {GRAY}")
    for key in ("ratings", "reviews", "analytics"):
        stale_note(key, errors, snap)


def render_github(snap, errors):
    g = snap.get("github")
    if not g:
        print(f"GitHub | {BOLD} sfimage=square.grid.3x3.fill")
        stale_note("github", errors, snap)
        return
    s = g.get("streak") or {}
    streak = f"   seri {s['current']} gün" if s else ""
    login = g["login"] if re.fullmatch(r"[A-Za-z0-9-]{1,39}", str(g.get("login", ""))) else ""
    print(f"GitHub   bugün {num(g['today'])}{streak} | {BOLD} sfimage=square.grid.3x3.fill"
          + (f" href=https://github.com/{login}" if login else ""))
    stale_note("github", errors, snap)
    row = lambda label, n, extra="": f"{label.ljust(14)}{num(n):>7} {extra}"  # noqa: E731
    print(row("Bu hafta", g["week"], arrow(g.get("week_change"))) + f" | {MONO}")
    print(row("Son 1 yıl", g["last_year"]) + f" | {MONO}")

    top = g.get("top_repos") or []
    label = f"En çok: {safe(top[0]['name'].split('/')[-1])} {top[0]['commits']}" if top else "Ayrıntılar"
    print(f"{label} | {MONO}")
    if top:
        total = g.get("week_commits")
        print(f"--Bu hafta commit{f' ({num(total)})' if total else ''} | {BOLD}")
        for r in top:
            link = f" href={r['url']}" if REPO_URL.match(str(r.get("url", ""))) else ""
            print(f"--{safe(r['name'].split('/')[-1])[:24]:<26}{r['commits']:>5} | {MONO}{link}")
        print("-----")
    print("--" + row(f"Tüm zamanlar ({g['since']}-)", g["alltime"]).rstrip() + f" | {MONO}")
    if s:
        print("--" + row("En uzun seri", s["longest"]).rstrip() + " gün | " + MONO)
    b = g["breakdown"]
    print("-----")
    print(f"--Son 1 yıl | {BOLD}")
    for lbl, k in (("Commit", "commit"), ("Pull request", "pr"), ("Review", "review"),
                   ("Issue", "issue"), ("Özel repo", "private")):
        print("--" + row(lbl, b[k]).rstrip() + f" | {MONO}")
    print("-----")
    print(f"--Son 7 gün | {BOLD}")
    for d in reversed(g["series"]):
        day = dt.date.fromisoformat(d["date"])
        bar = "▇" * min(20, (d["count"] + 24) // 25)
        print(f"--{WEEKDAYS[day.weekday()]} {day.strftime('%d.%m')}  {d['count']:>5}  {bar} | {MONO}")
    rl = g.get("rate_limit")
    if rl:
        print("-----")
        print(f"--API kotası {num(rl['remaining'])}/{num(rl['limit'])}. Günler UTC'ye göre. | {GRAY}")


def main():
    os.umask(0o077)  # cache, snapshot and seen-review files hold private data
    asc.ensure_private_dir()
    snap, errors = gather()
    notify_new_reviews(snap.get("reviews") if "reviews" not in errors else None)
    a, g = snap.get("appstore"), snap.get("github")
    print(f":arrow.down.circle: {a['week'] if a else '!'}   :square.grid.3x3.fill: {g['today'] if g else '!'}")
    print("---")
    emit_guarded(lambda: render_appstore(snap, errors))
    print("---")
    emit_guarded(lambda: render_github(snap, errors))
    print("---")
    print(f"Yenile   {dt.datetime.now().strftime('%H:%M')} | refresh=true {GRAY}")


if __name__ == "__main__":
    main()
