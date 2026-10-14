import SwiftUI

// Neutral, monochrome design: hierarchy comes from size and opacity, not color.
// Change markers (▲ ▼) are text, not color, so they work in light, dark and tinted modes.

struct SectionHeader: View {
    let symbol: String
    let title: String
    var trailing: String? = nil

    var body: some View {
        HStack(spacing: 5) {
            Image(systemName: symbol).font(.system(size: 10, weight: .semibold))
            Text(title).font(.system(size: 11, weight: .semibold))
            Spacer(minLength: 4)
            if let trailing {
                Text(trailing).font(.system(size: 10)).foregroundStyle(.tertiary)
            }
        }
        .foregroundStyle(.secondary)
    }
}

struct BigNumber: View {
    let value: Int
    let caption: String
    var delta: String = ""
    var size: CGFloat = 32

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .firstTextBaseline, spacing: 5) {
                Text(Fmt.n(value))
                    .font(.system(size: size, weight: .semibold, design: .rounded))
                    .monospacedDigit()
                    .minimumScaleFactor(0.6)
                    .lineLimit(1)
                if !delta.isEmpty {
                    Text(delta).font(.system(size: 11, weight: .medium)).monospacedDigit()
                        .foregroundStyle(.secondary)
                }
            }
            Text(caption).font(.system(size: 10)).foregroundStyle(.secondary).lineLimit(1)
        }
    }
}

struct StatLine: View {
    let label: String
    let text: String
    var trailing: String = ""

    init(label: String, value: Int, trailing: String = "") {
        self.label = label; self.text = Fmt.n(value); self.trailing = trailing
    }
    init(label: String, text: String) { self.label = label; self.text = text }

    var body: some View {
        HStack(spacing: 4) {
            Text(label).foregroundStyle(.secondary)
            Spacer(minLength: 4)
            Text(text).monospacedDigit().fontWeight(.medium)
            if !trailing.isEmpty {
                Text(trailing).monospacedDigit().foregroundStyle(.secondary).font(.system(size: 9))
            }
        }
        .font(.system(size: 11))
        .lineLimit(1)
    }
}

/// Seven bars; the most recent one is solid, the rest faded.
struct Bars: View {
    let series: [DayCount]
    var height: CGFloat = 26

    var body: some View {
        let peak = max(series.map(\.count).max() ?? 0, 1)
        HStack(alignment: .bottom, spacing: 4) {
            ForEach(Array(series.enumerated()), id: \.offset) { i, d in
                VStack(spacing: 2) {
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Color.primary.opacity(i == series.count - 1 ? 0.9 : 0.28))
                        .frame(height: max(2, height * CGFloat(d.count) / CGFloat(peak)))
                        .frame(height: height, alignment: .bottom)
                    Text(Fmt.weekdayLetter(d.date))
                        .font(.system(size: 8))
                        .foregroundStyle(.tertiary)
                }
                .frame(maxWidth: .infinity)
            }
        }
    }
}

/// GitHub-style heat grid, Monday-aligned weeks as columns.
struct HeatGrid: View {
    let days: [DayCount]
    var cell: CGFloat = 11

    var body: some View {
        let nonZero = days.map(\.count).filter { $0 > 0 }.sorted()
        let q = { (p: Double) -> Int in nonZero.isEmpty ? 1 : nonZero[min(nonZero.count - 1, Int(Double(nonZero.count) * p))] }
        let steps = [q(0.25), q(0.5), q(0.75)]
        let weeks = stride(from: 0, to: days.count, by: 7).map { Array(days[$0..<min($0 + 7, days.count)]) }
        HStack(spacing: 3) {
            ForEach(Array(weeks.enumerated()), id: \.offset) { _, week in
                VStack(spacing: 3) {
                    ForEach(week, id: \.date) { d in
                        RoundedRectangle(cornerRadius: 2.5)
                            .fill(Color.primary.opacity(level(d.count, steps)))
                            .frame(width: cell, height: cell)
                    }
                }
            }
        }
    }

    private func level(_ n: Int, _ steps: [Int]) -> Double {
        if n == 0 { return 0.07 }
        if n <= steps[0] { return 0.25 }
        if n <= steps[1] { return 0.45 }
        if n <= steps[2] { return 0.7 }
        return 0.95
    }
}

struct EmptyState: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Image(systemName: "tray").foregroundStyle(.secondary)
            Text("Veri yok").font(.system(size: 12, weight: .semibold))
            Text("SwiftBar eklentisi çalışınca dolar.").font(.system(size: 10)).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
}

/// One labelled figure for the large widget's summary strip.
struct Kpi: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 1) {
            Text(label).font(.system(size: 9, weight: .semibold)).foregroundStyle(.tertiary)
            Text(value).font(.system(size: 13, weight: .semibold, design: .rounded)).monospacedDigit().lineLimit(1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

// MARK: - Column building blocks

struct AppStoreColumn: View {
    let a: AppStoreStats
    var funnel: Funnel? = nil
    var rating: RatingsStats? = nil
    var showBars = true

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            SectionHeader(symbol: "arrow.down.circle", title: "App Store")
            BigNumber(value: a.week, caption: "bu hafta indirme", delta: Fmt.delta(a.weekChange))
            VStack(spacing: 2) {
                if let f = funnel {
                    StatLine(label: "Impressions", value: f.impressions)
                    StatLine(label: "Dönüşüm", text: Fmt.pct(f.conversion))
                } else {
                    StatLine(label: "Toplam", value: a.all)
                    if let r = rating, r.count > 0 {
                        StatLine(label: "Puan", text: "\(Fmt.stars(r.average)) (\(r.count))")
                    } else {
                        StatLine(label: "Son gün (\(Fmt.dayMonth(a.lastDay)))", value: a.day)
                    }
                }
            }
            if showBars {
                Spacer(minLength: 0)
                Bars(series: a.series)
            }
        }
    }
}

struct GitHubColumn: View {
    let g: GitHubStats
    var showBars = true

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            SectionHeader(symbol: "square.grid.3x3.fill", title: "GitHub")
            BigNumber(value: g.today, caption: "bugün katkı")
            VStack(spacing: 2) {
                StatLine(label: "Bu hafta", value: g.week, trailing: Fmt.delta(g.weekChange))
                if let s = g.streak {
                    StatLine(label: "Seri", text: "\(s.current) gün")
                } else {
                    StatLine(label: "Son 1 yıl", value: g.lastYear)
                }
            }
            if showBars {
                Spacer(minLength: 0)
                Bars(series: g.series)
            }
        }
    }
}

// MARK: - Family layouts

struct SmallView: View {
    let s: Snapshot

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if let a = s.appstore {
                compact(symbol: "arrow.down.circle", title: "App Store", value: a.week,
                        caption: "bu hafta · \(Fmt.n(a.all)) toplam", delta: Fmt.delta(a.weekChange))
            }
            Divider().opacity(0.5)
            if let g = s.github {
                let caption = g.streak.map { "bugün · \($0.current) gün seri" } ?? "bugün · \(Fmt.n(g.lastYear)) / yıl"
                compact(symbol: "square.grid.3x3.fill", title: "GitHub", value: g.today, caption: caption, delta: "")
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private func compact(symbol: String, title: String, value: Int, caption: String, delta: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            SectionHeader(symbol: symbol, title: title)
            BigNumber(value: value, caption: caption, delta: delta, size: 26)
        }
    }
}

struct MediumView: View {
    let s: Snapshot

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            if let a = s.appstore {
                AppStoreColumn(a: a, funnel: s.analytics?.weekTotal, rating: s.ratings)
            } else { EmptyState() }
            Divider().opacity(0.5)
            if let g = s.github { GitHubColumn(g: g) } else { EmptyState() }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
}

struct LargeView: View {
    let s: Snapshot

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            MediumView(s: s).frame(height: 130)
            Divider().opacity(0.5)
            kpis
            Divider().opacity(0.5)
            if let a = s.appstore { appTable(a) }
            Divider().opacity(0.5)
            if let g = s.github {
                VStack(alignment: .leading, spacing: 5) {
                    HStack(alignment: .firstTextBaseline) {
                        Text("Son \(g.calendar.count / 7) hafta")
                            .font(.system(size: 10, weight: .semibold)).foregroundStyle(.secondary)
                        Text("· \(Fmt.n(g.alltime)) katkı, \(String(g.since))'den beri")
                            .font(.system(size: 10)).foregroundStyle(.tertiary)
                        Spacer()
                        Text((s.isStale ? "eski veri · " : "") + Fmt.time(s.generatedAt))
                            .font(.system(size: 9)).foregroundStyle(.tertiary)
                    }
                    HeatGrid(days: g.calendar, cell: 8).frame(maxWidth: .infinity, alignment: .center)
                }
            }
            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private var kpis: some View {
        HStack(spacing: 8) {
            if let a = s.appstore, let all = a.revenue?.all, all > 0 {
                Kpi(label: "GELİR · TOPLAM", value: Fmt.money(all, a.currency))
            } else {
                Kpi(label: "PUAN", value: s.ratings.map { "\(Fmt.stars($0.average)) · \($0.count)" } ?? "–")
            }
            Kpi(label: "KATKI · SON 1 YIL", value: s.github.map { Fmt.n($0.lastYear) } ?? "–")
            Kpi(label: "EN UZUN SERİ", value: s.github?.streak.map { "\($0.longest) gün" } ?? "–")
        }
    }

    private func appTable(_ a: AppStoreStats) -> some View {
        let top = Array(a.apps.prefix(3))
        return Grid(alignment: .trailing, horizontalSpacing: 12, verticalSpacing: 3) {
            GridRow {
                Text("Uygulama").gridColumnAlignment(.leading)
                Text("Puan"); Text("Hafta"); Text("Toplam")
            }
            .font(.system(size: 9, weight: .semibold))
            .foregroundStyle(.tertiary)
            ForEach(top) { r in
                let rating = s.ratings?.apps?[r.id]
                GridRow {
                    Text(r.name).lineLimit(1).frame(maxWidth: .infinity, alignment: .leading)
                    Text(rating.flatMap { $0.count > 0 ? Fmt.stars($0.average) : nil } ?? "–")
                        .foregroundStyle(.secondary)
                    Text(Fmt.n(r.week.new)).foregroundStyle(.secondary)
                    Text(Fmt.n(r.all.new)).fontWeight(.medium)
                }
                .font(.system(size: 11))
                .monospacedDigit()
            }
        }
    }
}
