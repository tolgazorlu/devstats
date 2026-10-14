"""Menu bar output (SwiftBar) for App Store and GitHub stats, plus the widget snapshot.

Run through plugins/devstats.30m.sh. Writes ~/.config/asc-menubar/snapshot.json,
which the desktop widget reads. When a source fails, its last good data is shown
with the time it was fetched, so the menu and widget never go blank.
"""
import datetime as dt
import json
import os
import subprocess
import textwrap
import urllib.parse

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


def safe(text):
    """SwiftBar treats '|' as the parameter separator and leading '-' as nesting."""
    return text.replace("|", "/").replace("\n", " ").lstrip("-").strip()


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
        notify("Yeni yorum: " + r["app_name"], f"{'★' * (r['rating'] or 0)} {r['title']}", r["body"][:200])
    if len(new) > 3:
        notify("Dev Stats", f"{len(new)} yeni yorum", "Menüden Yorumlar bölümüne bak.")


# ---------- rendering ----------

def stale_note(key, errors, snap):
    if key not in errors:
        return
    when = snap.get("fetched", {}).get(key)
    t = dt.datetime.fromisoformat(when).strftime("%d.%m %H:%M") if when else "hiç"
    print(f"Güncellenemedi, son veri {t}: {errors[key]} | {GRAY}")


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
        head = f"{'★' * (r['rating'] or 0):<5} {r['app_name'] + '  ' if app is None else ''}{safe(r['title'])[:40]}"
        print(f"{prefix}{head} | {MONO}")
        meta = f"{r['territory']} · {dt.date.fromisoformat(r['date']).strftime('%d.%m.%Y')} · {safe(r['nickname'])}"
        print(f"{prefix}--{meta} | {GRAY}")
        for line in textwrap.wrap(safe(r["body"]), 60)[:6]:
            print(f"{prefix}--{line} | size=12")
        print(f"{prefix}--Cevapla (App Store Connect) | href=https://appstoreconnect.apple.com/apps/{r['app']}"
              "/distribution/activity/ios/ratingsResponses")


def render_appstore(snap, errors):
    a, an, rt, rv = snap.get("appstore"), snap.get("analytics"), snap.get("ratings"), snap.get("reviews")
    print(f"App Store | {BOLD} sfimage=arrow.down.circle")
    if not a:
        stale_note("appstore", errors, snap)
        return
    stale_note("appstore", errors, snap)
    cur = a.get("currency", "USD")
    w = max([len(r["name"]) for r in a["apps"]] + [len("Sayfa görüntüleme")])
    print(table_row("Yeni indirme", "Gün", "Hafta", "Toplam", w) + f" | {BOLD}")
    for r in a["apps"]:
        mark = arrow(appstore.change(r["week"]["new"], r["prev_week"]["new"]))
        print(table_row(r["name"], r["day"]["new"], r["week"]["new"], num(r["all"]["new"]), w)
              + f"  {mark} | {MONO}")
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
        else:
            print(f"--Henüz puan yok | {GRAY}")
        if r.get("countries"):
            print("--Ülkeler: " + ", ".join(f"{c} {n}" for c, n in r["countries"]) + f" | {MONO}")
        if rv and rv.get("available"):
            review_lines(rv, r["id"], "--")
        print(f"--App Store Connect'te aç | href=https://appstoreconnect.apple.com/apps/{r['id']}/analytics")
    print(table_row("Toplam", a["day"], a["week"], num(a["all"]), w) + f"  {arrow(a.get('week_change'))} | {BOLD}")
    rev = a.get("revenue", {})
    print(table_row(f"Gelir ({cur})", money(rev.get("day"), cur), money(rev.get("week"), cur),
                    money(rev.get("all"), cur), w) + f" | {MONO}")
    funnel_rows(an, "_all", w)

    if rt and rt.get("count"):
        extra = f" · son 7 gün +{rt['new_7d']}" if rt.get("new_7d") else ""
        print(f"Puan {stars(rt['average'])} · {rt['count']} puan{extra} | {MONO}")
    if a.get("countries"):
        print(f"Ülkeler (tüm zamanlar) | {MONO}")
        for c, n in a["countries"]:
            print(f"--{c:<4}{n:>6} | {MONO}")
    if rv and rv.get("available"):
        new = len(rv.get("new") or [])
        print(f"Yorumlar ({rv['total']}{f', {new} yeni' if new else ''}) | {MONO}")
        review_lines(rv, None, "--")
    elif rv:
        print(f"Yorumlar: {rv.get('reason')} | {GRAY}")
    stale_note("ratings", errors, snap)
    stale_note("reviews", errors, snap)
    stale_note("analytics", errors, snap)

    day = dt.date.fromisoformat(a["last_day"]).strftime("%d.%m") if a["last_day"] else "–"
    print(f"Gün: son rapor ({day}, Pasifik saati). ▲▼: geçen haftanın aynı günlerine göre. | {GRAY}")
    if not an or not an.get("ready"):
        print(f"Impressions ve dönüşüm: Apple raporu hazırlanıyor (1-2 gün) | {GRAY}")
    else:
        print(f"Dönüşüm = indirme / tekil impression. Gelir bugünkü kurla çevrildi. | {GRAY}")


def render_github(snap, errors):
    g = snap.get("github")
    print(f"GitHub | {BOLD} sfimage=square.grid.3x3.fill href=https://github.com/{g['login'] if g else ''}")
    stale_note("github", errors, snap)
    if not g:
        return
    row = lambda label, n, extra="": f"{label.ljust(22)}{num(n):>8}  {extra}"  # noqa: E731
    print(row("Bugün", g["today"]) + f" | {MONO}")
    print(row("Bu hafta", g["week"], arrow(g.get("week_change"))) + f" | {MONO}")
    print(row("Son 1 yıl", g["last_year"]) + f" | {MONO}")
    print(row(f"Tüm zamanlar ({g['since']}-)", g["alltime"]) + f" | {MONO}")
    s = g.get("streak")
    if s:
        print(f"{'Seri'.ljust(22)}{s['current']:>4} gün  en uzun {s['longest']} | {MONO}")
    if g.get("top_repos"):
        print(f"Bu hafta en çok commit | {MONO}")
        for r in g["top_repos"]:
            print(f"--{r['name'].split('/')[-1][:24]:<26}{r['commits']:>5} | {MONO} href={r['url']}")
    print(f"Son 1 yıl dağılımı | {MONO}")
    b = g["breakdown"]
    for label, k in (("Commit", "commit"), ("Pull request", "pr"), ("Review", "review"),
                     ("Issue", "issue"), ("Özel repo katkıları", "private")):
        print("--" + row(label, b[k]).rstrip() + f" | {MONO}")
    print(f"Son 7 gün | {MONO}")
    for d in reversed(g["series"]):
        day = dt.date.fromisoformat(d["date"])
        bar = "▇" * min(20, (d["count"] + 24) // 25)
        print(f"--{WEEKDAYS[day.weekday()]} {day.strftime('%d.%m')}  {d['count']:>5}  {bar} | {MONO}")
    rl = g.get("rate_limit")
    if rl:
        print(f"API kotası {num(rl['remaining'])}/{num(rl['limit'])}. Günler UTC'ye göre. | {GRAY}")


def main():
    snap, errors = gather()
    notify_new_reviews(snap.get("reviews") if "reviews" not in errors else None)
    a, g = snap.get("appstore"), snap.get("github")
    print(f":arrow.down.circle: {a['week'] if a else '!'}   :square.grid.3x3.fill: {g['today'] if g else '!'}")
    print("---")
    render_appstore(snap, errors)
    print("---")
    render_github(snap, errors)
    print("---")
    print(f"Menüde: App Store bu hafta, GitHub bugün. Güncellendi {dt.datetime.now().strftime('%H:%M')} | {GRAY}")
    print("Yenile | refresh=true")


if __name__ == "__main__":
    main()
