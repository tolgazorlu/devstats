import SwiftUI
import WidgetKit

struct Entry: TimelineEntry {
    let date: Date
    let snapshot: Snapshot?
}

struct Provider: TimelineProvider {
    func placeholder(in context: Context) -> Entry { Entry(date: .now, snapshot: .sample) }

    func getSnapshot(in context: Context, completion: @escaping (Entry) -> Void) {
        completion(Entry(date: .now, snapshot: context.isPreview ? (SnapshotStore.load() ?? .sample) : SnapshotStore.load()))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<Entry>) -> Void) {
        // The SwiftBar plugin rewrites the snapshot every 30 minutes; re-read it every 15.
        let entry = Entry(date: .now, snapshot: SnapshotStore.load())
        completion(Timeline(entries: [entry], policy: .after(.now.addingTimeInterval(15 * 60))))
    }
}

struct DevStatsWidgetView: View {
    @Environment(\.widgetFamily) private var family
    let entry: Entry

    var body: some View {
        Group {
            if let s = entry.snapshot {
                switch family {
                case .systemSmall: SmallView(s: s)
                case .systemLarge: LargeView(s: s)
                default: MediumView(s: s)
                }
            } else {
                EmptyState()
            }
        }
        .containerBackground(.background, for: .widget)
    }
}

@main
struct DevStatsWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "DevStatsWidget", provider: Provider()) { entry in
            DevStatsWidgetView(entry: entry)
        }
        .configurationDisplayName("Dev Stats")
        .description("App Store indirmeleri ve GitHub katkıları.")
        .supportedFamilies([.systemSmall, .systemMedium, .systemLarge])
    }
}
