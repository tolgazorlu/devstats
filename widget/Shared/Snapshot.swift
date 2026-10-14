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

struct AppStoreStats: Codable {
    let lastDay: String?
    let weekStart: String
    let day: Int
    let week: Int
    let all: Int
    let apps: [AppRow]
    let series: [DayCount]
}

struct GitHubStats: Codable {
    let login: String
    let since: Int
    let today: Int
    let week: Int
    let lastYear: Int
    let alltime: Int
    let series: [DayCount]
    let calendar: [DayCount]
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
    let github: GitHubStats?
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
                apps: [
                    AppRow(id: "1", name: "Demo App", day: k, week: k, all: Kinds(new: 100, re: 13, upd: 103, iap: 0)),
                    AppRow(id: "2", name: "Second App", day: k, week: k, all: Kinds(new: 17, re: 0, upd: 0, iap: 0)),
                    AppRow(id: "3", name: "Third App", day: k, week: k, all: Kinds(new: 6, re: 4, upd: 1, iap: 0)),
                ],
                series: (6...12).map { DayCount(date: "2026-10-\(String(format: "%02d", $0))", count: $0 % 4) }),
            analytics: AnalyticsStats(
                ready: true, lastDay: "2026-10-12",
                week: ["_all": Funnel(impressions: 1240, pageViews: 210, downloads: 31, conversion: 3.1)], all: nil),
            github: GitHubStats(
                login: "octocat", since: 2018, today: 12, week: 64, lastYear: 1450, alltime: 3200,
                series: (8...14).map { DayCount(date: "2026-10-\(String(format: "%02d", $0))", count: $0 * 20) },
                calendar: days))
    }()
}
