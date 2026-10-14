import Foundation

// Mirrors ~/.config/asc-menubar/snapshot.json written by the SwiftBar plugin.

struct DayCount: Codable, Hashable {
    let date: String
    let count: Int
}

struct Kinds: Codable, Hashable {
    let new: Int
    let re: Int
    let upd: Int
    let iap: Int
}

struct AppRow: Codable, Hashable, Identifiable {
    let id: String
    let name: String
    let day: Kinds
    let week: Kinds
    let all: Kinds
}

struct Revenue: Codable {
    let day: Double?
    let week: Double?
    let all: Double?
}

struct AppStoreStats: Codable {
    let lastDay: String?
    let weekStart: String
    let day: Int
    let week: Int
    let all: Int
    var weekChange: Double? = nil
    var currency: String? = nil
    var revenue: Revenue? = nil
    let apps: [AppRow]
    let series: [DayCount]
}

struct Streak: Codable {
    let current: Int
    let longest: Int
}

struct GitHubStats: Codable {
    let login: String
    let since: Int
    let today: Int
    let week: Int
    var weekChange: Double? = nil
    let lastYear: Int
    let alltime: Int
    var streak: Streak? = nil
    let series: [DayCount]
    let calendar: [DayCount]
}

struct AppRating: Codable {
    let average: Double?
    let count: Int
}

struct RatingsStats: Codable {
    let average: Double?
    let count: Int
    let apps: [String: AppRating]?
}

struct Funnel: Codable {
    let impressions: Int
    let pageViews: Int
    let downloads: Int
    let conversion: Double?
}

struct AnalyticsStats: Codable {
    let ready: Bool
    let lastDay: String?
    let week: [String: Funnel]?
    let all: [String: Funnel]?

    /// Totals across apps for this week, when Apple has published data.
    var weekTotal: Funnel? { ready ? week?["_all"] : nil }
}

struct Snapshot: Codable {
    let generatedAt: String
    let appstore: AppStoreStats?
    var analytics: AnalyticsStats? = nil
    var ratings: RatingsStats? = nil
    let github: GitHubStats?

    /// True when the snapshot is older than two plugin runs, i.e. the plugin stopped.
    var isStale: Bool {
        guard let d = ISO8601DateFormatter().date(from: generatedAt) else { return false }
        return Date().timeIntervalSince(d) > 75 * 60
    }
}

enum SnapshotStore {
    /// The real home directory; inside the sandbox NSHomeDirectory() points at the container.
    static var url: URL {
        let home = getpwuid(getuid()).map { String(cString: $0.pointee.pw_dir) } ?? NSHomeDirectory()
        return URL(fileURLWithPath: home).appendingPathComponent(".config/asc-menubar/snapshot.json")
    }

    static func load() -> Snapshot? {
        guard let data = try? Data(contentsOf: url) else { return nil }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try? decoder.decode(Snapshot.self, from: data)
    }
}

enum Fmt {
    private static let numberFormatter: NumberFormatter = {
        let f = NumberFormatter()
        f.numberStyle = .decimal
        f.locale = Locale(identifier: "tr_TR")
        return f
    }()

    static func n(_ v: Int) -> String { numberFormatter.string(from: NSNumber(value: v)) ?? "\(v)" }

    /// "%3,8" (Turkish percent style), "–" when unknown
    static func pct(_ v: Double?) -> String {
        guard let v else { return "–" }
        return "%" + String(format: "%.1f", v).replacingOccurrences(of: ".", with: ",")
    }

    /// "▲%12" / "▼%3" / "=" / "" (nothing to compare); monochrome on purpose
    static func delta(_ v: Double?) -> String {
        guard let v else { return "" }
        if v == 0 { return "=" }
        return (v > 0 ? "▲" : "▼") + "%" + String(Int(abs(v).rounded()))
    }

    /// "★ 4,8" or "–"
    static func stars(_ v: Double?) -> String {
        guard let v else { return "–" }
        return "★ " + String(format: "%.1f", v).replacingOccurrences(of: ".", with: ",")
    }

    /// "₺1.234" / "$12,50"; whole numbers from 100 up
    static func money(_ v: Double?, _ currency: String?) -> String {
        guard let v else { return "–" }
        let f = NumberFormatter()
        f.numberStyle = .decimal
        f.locale = Locale(identifier: "tr_TR")
        let whole = v == 0 || abs(v) >= 100
        f.minimumFractionDigits = whole ? 0 : 2
        f.maximumFractionDigits = whole ? 0 : 2
        let s = f.string(from: NSNumber(value: v)) ?? "\(v)"
        let symbols = ["TRY": "₺", "USD": "$", "EUR": "€", "GBP": "£"]
        guard let c = currency else { return s }
        return symbols[c].map { $0 + s } ?? "\(s) \(c)"
    }

    private static let iso: DateFormatter = {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .gregorian)
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyy-MM-dd"
        return f
    }()

    static func date(_ s: String) -> Date? { iso.date(from: s) }

    /// "12.10"
    static func dayMonth(_ s: String?) -> String {
        guard let s, let d = date(s) else { return "–" }
        let f = DateFormatter()
        f.dateFormat = "dd.MM"
        return f.string(from: d)
    }

    /// "12:25" from the ISO timestamp
    static func time(_ s: String) -> String {
        let f = ISO8601DateFormatter()
        guard let d = f.date(from: s) else { return "" }
        let out = DateFormatter()
        out.dateFormat = "HH:mm"
        return out.string(from: d)
    }

    /// Single-letter Turkish weekday for a yyyy-MM-dd string
    static func weekdayLetter(_ s: String) -> String {
        guard let d = date(s) else { return "" }
        let letters = ["Pz", "Pt", "Sa", "Ça", "Pe", "Cu", "Ct"]  // Sun..Sat
        return letters[Calendar(identifier: .gregorian).component(.weekday, from: d) - 1]
    }
}

extension Snapshot {
    static let sample: Snapshot = {
        let days = (0..<112).map { DayCount(date: "2026-06-\(String(format: "%02d", $0 % 28 + 1))", count: ($0 * 37) % 90) }
        let k = Kinds(new: 1, re: 0, upd: 2, iap: 0)
        return Snapshot(
            generatedAt: "2026-10-14T12:25:05+03:00",
            appstore: AppStoreStats(
                lastDay: "2026-10-12", weekStart: "2026-10-12", day: 2, week: 2, all: 123,
                weekChange: 18, currency: "TRY", revenue: Revenue(day: 120, week: 840, all: 12450),
                apps: [
                    AppRow(id: "1", name: "Demo App", day: k, week: k, all: Kinds(new: 100, re: 13, upd: 103, iap: 0)),
                    AppRow(id: "2", name: "Second App", day: k, week: k, all: Kinds(new: 17, re: 0, upd: 0, iap: 0)),
                    AppRow(id: "3", name: "Third App", day: k, week: k, all: Kinds(new: 6, re: 4, upd: 1, iap: 0)),
                ],
                series: (6...12).map { DayCount(date: "2026-10-\(String(format: "%02d", $0))", count: $0 % 4) }),
            analytics: AnalyticsStats(
                ready: true, lastDay: "2026-10-12",
                week: ["_all": Funnel(impressions: 1240, pageViews: 210, downloads: 31, conversion: 3.1)], all: nil),
            ratings: RatingsStats(average: 4.7, count: 38, apps: [
                "1": AppRating(average: 4.8, count: 30), "2": AppRating(average: 4.5, count: 8)]),
            github: GitHubStats(
                login: "octocat", since: 2018, today: 12, week: 64, weekChange: -12, lastYear: 1450, alltime: 3200,
                streak: Streak(current: 9, longest: 41),
                series: (8...14).map { DayCount(date: "2026-10-\(String(format: "%02d", $0))", count: $0 * 20) },
                calendar: days))
    }()
}
