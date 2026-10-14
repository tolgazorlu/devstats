import SwiftUI

// Neutral, monochrome design: hierarchy comes from size and opacity, not color.

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
    var size: CGFloat = 32

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(Fmt.n(value))
                .font(.system(size: size, weight: .semibold, design: .rounded))
                .monospacedDigit()
                .minimumScaleFactor(0.6)
                .lineLimit(1)
            Text(caption).font(.system(size: 10)).foregroundStyle(.secondary)
        }
    }
}

struct StatLine: View {
    let label: String
    let text: String

    init(label: String, value: Int) { self.label = label; self.text = Fmt.n(value) }
    init(label: String, text: String) { self.label = label; self.text = text }

    var body: some View {
        HStack {
            Text(label).foregroundStyle(.secondary)
            Spacer(minLength: 4)
            Text(text).monospacedDigit().fontWeight(.medium)
        }
        .font(.system(size: 11))
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

// MARK: - Column building blocks

struct AppStoreColumn: View {
    let a: AppStoreStats
    var funnel: Funnel? = nil
    var showBars = true

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            SectionHeader(symbol: "arrow.down.circle", title: "App Store")
            if let f = funnel {
                BigNumber(value: a.week, caption: "bu hafta indirme · \(Fmt.n(a.all)) toplam")
                VStack(spacing: 2) {
                    StatLine(label: "Impressions", value: f.impressions)
                    StatLine(label: "Dönüşüm", text: Fmt.pct(f.conversion))
                }
            } else {
                BigNumber(value: a.week, caption: "bu hafta indirme")
                VStack(spacing: 2) {
                    StatLine(label: "Son gün (\(Fmt.dayMonth(a.lastDay)))", value: a.day)
                    StatLine(label: "Toplam", value: a.all)
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
                StatLine(label: "Bu hafta", value: g.week)
                StatLine(label: "Son 1 yıl", value: g.lastYear)
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
                        caption: "bu hafta · \(Fmt.n(a.all)) toplam")
            }
            Divider().opacity(0.5)
            if let g = s.github {
                compact(symbol: "square.grid.3x3.fill", title: "GitHub", value: g.today,
                        caption: "bugün · \(Fmt.n(g.lastYear)) / yıl")
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private func compact(symbol: String, title: String, value: Int, caption: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            SectionHeader(symbol: symbol, title: title)
            BigNumber(value: value, caption: caption, size: 26)
        }
    }
}

struct MediumView: View {
    let s: Snapshot

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            if let a = s.appstore { AppStoreColumn(a: a, funnel: s.analytics?.weekTotal) } else { EmptyState() }
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
            MediumView(s: s).frame(height: 136)
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
                        Text(Fmt.time(s.generatedAt)).font(.system(size: 9)).foregroundStyle(.tertiary)
                    }
                    HeatGrid(days: g.calendar, cell: 9).frame(maxWidth: .infinity, alignment: .center)
                }
            }
            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private func appTable(_ a: AppStoreStats) -> some View {
        let top = Array(a.apps.prefix(3))
        return Grid(alignment: .trailing, horizontalSpacing: 12, verticalSpacing: 3) {
            GridRow {
                Text("Uygulama").gridColumnAlignment(.leading)
                Text("Gün"); Text("Hafta"); Text("Toplam")
            }
            .font(.system(size: 9, weight: .semibold))
            .foregroundStyle(.tertiary)
            ForEach(top) { r in
                GridRow {
                    Text(r.name).lineLimit(1).frame(maxWidth: .infinity, alignment: .leading)
                    Text(Fmt.n(r.day.new)).foregroundStyle(.secondary)
                    Text(Fmt.n(r.week.new)).foregroundStyle(.secondary)
                    Text(Fmt.n(r.all.new)).fontWeight(.medium)
                }
                .font(.system(size: 11))
                .monospacedDigit()
            }
        }
    }
}
