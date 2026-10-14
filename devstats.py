"""Menu bar output (SwiftBar) for App Store and GitHub stats, plus the widget snapshot.

Run through plugins/devstats.30m.sh. Writes ~/.config/asc-menubar/snapshot.json,
which the desktop widget reads.
"""
import datetime as dt
import json
import os

import analytics
import appstore
import asc
import github

SNAPSHOT = os.path.join(asc.CONFIG_DIR, "snapshot.json")
MONO, BOLD, GRAY = "font=Menlo size=12", "font=Menlo-Bold size=12", "size=11 color=gray"
WEEKDAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
SOURCES = {"appstore": appstore.collect, "analytics": analytics.collect, "github": github.collect}


def num(n):
    return "–" if n is None else f"{n:,}".replace(",", ".")


def pct(p):
    return "–" if p is None else f"%{p:.1f}".replace(".", ",")


def write_snapshot(snap):
    """Keep the last good section when a source fails, so the widget never goes blank."""
    old = {}
    if os.path.exists(SNAPSHOT):
        with open(SNAPSHOT) as f:
            old = json.load(f)
    for key in SOURCES:
        if snap[key] is None:
            snap[key] = old.get(key)
    tmp = SNAPSHOT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(snap, f, ensure_ascii=False)
    os.replace(tmp, SNAPSHOT)


def table_row(label, x, y, z, width):
    return f"{label.ljust(width)}  {x:>6} {y:>7} {z:>8}"


def funnel_rows(an, app, width, prefix=""):
    """Impressions, product page views and conversion for one app id (or '_all')."""
    if not an or not an.get("ready"):
        return
    blocks = [an[p].get(app, {}) for p in ("day", "week", "all")]
    for label, key, fmt in (("Impressions", "impressions", num), ("Sayfa görüntüleme", "page_views", num),
                            ("Dönüşüm", "conversion", pct)):
        print(prefix + table_row(label, *(fmt(b.get(key)) for b in blocks), width) + f" | {MONO}")


def render_appstore(a, an, err):
    print(f"App Store | {BOLD} sfimage=arrow.down.circle")
    if err:
        print(f"Hata: {err} | {GRAY}")
        return
    w = max([len(r["name"]) for r in a["apps"]] + [len("Sayfa görüntüleme")])
    print(table_row("Yeni indirme", "Gün", "Hafta", "Toplam", w) + f" | {BOLD}")
    for r in a["apps"]:
        print(table_row(r["name"], r["day"]["new"], r["week"]["new"], num(r["all"]["new"]), w) + f" | {MONO}")
        print("--" + table_row("", "Gün", "Hafta", "Toplam", w) + f" | {BOLD}")
        for label, k in (("Yeni indirme", "new"), ("Yeniden indirme", "re"),
                         ("Güncelleme", "upd"), ("Satın alma", "iap")):
            print("--" + table_row(label, r["day"][k], r["week"][k], num(r["all"][k]), w) + f" | {MONO}")
        funnel_rows(an, r["id"], w, "--")
        print("-----")
        print(f"--App Store Connect'te aç | href=https://appstoreconnect.apple.com/apps/{r['id']}/analytics")
    print(table_row("Toplam", a["day"], a["week"], num(a["all"]), w) + f" | {BOLD}")
    funnel_rows(an, "_all", w)
    day = dt.date.fromisoformat(a["last_day"]).strftime("%d.%m") if a["last_day"] else "–"
    print(f"Gün: son rapor ({day}, Pasifik saati). Hafta Pazartesi başlar. | {GRAY}")
    if not an or not an.get("ready"):
        print(f"Impressions ve dönüşüm: Apple raporu hazırlanıyor (1-2 gün) | {GRAY}")
    else:
        print(f"Impressions son gün {dt.date.fromisoformat(an['last_day']).strftime('%d.%m')}. "
              f"Dönüşüm = indirme / tekil impression. | {GRAY}")


def render_github(g, err):
    print(f"GitHub | {BOLD} sfimage=square.grid.3x3.fill href=https://github.com/{g['login'] if g else ''}")
    if err:
        print(f"Hata: {err} | {GRAY}")
        return
    row = lambda label, n: f"{label.ljust(22)}{num(n):>8}"  # noqa: E731
    print(row("Bugün", g["today"]) + f" | {MONO}")
    print(row("Bu hafta", g["week"]) + f" | {MONO}")
    print(row("Son 1 yıl", g["last_year"]) + f" | {MONO}")
    print(row(f"Tüm zamanlar ({g['since']}-)", g["alltime"]) + f" | {MONO}")
    print(f"Son 1 yıl dağılımı | {MONO}")
    b = g["breakdown"]
    for label, k in (("Commit", "commit"), ("Pull request", "pr"), ("Review", "review"),
                     ("Issue", "issue"), ("Özel repo katkıları", "private")):
        print("--" + row(label, b[k]) + f" | {MONO}")
    print(f"Son 7 gün | {MONO}")
    for d in reversed(g["series"]):
        day = dt.date.fromisoformat(d["date"])
        bar = "▇" * min(20, (d["count"] + 24) // 25)
        print(f"--{WEEKDAYS[day.weekday()]} {day.strftime('%d.%m')}  {d['count']:>5}  {bar} | {MONO}")


def main():
    data, errors = {}, {}
    for key, fn in SOURCES.items():
        try:
            data[key] = fn()
        except Exception as e:  # one source failing must not blank the others
            data[key], errors[key] = None, f"{type(e).__name__}: {str(e)[:100]}"
    a, an, g = data["appstore"], data["analytics"], data["github"]
    write_snapshot({"generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"), **data})

    print(f":arrow.down.circle: {a['week'] if a else '!'}   :square.grid.3x3.fill: {g['today'] if g else '!'}")
    print("---")
    render_appstore(a, an, errors.get("appstore"))
    if "analytics" in errors:
        print(f"Analytics hatası: {errors['analytics']} | {GRAY}")
    print("---")
    render_github(g, errors.get("github"))
    print("---")
    print(f"Menüde: App Store bu hafta, GitHub bugün. Güncellendi {dt.datetime.now().strftime('%H:%M')} | {GRAY}")
    print("Yenile | refresh=true")


if __name__ == "__main__":
    main()
