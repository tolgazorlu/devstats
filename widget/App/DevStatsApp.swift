import AppKit
import SwiftUI

/// Host app for the widget. `--render` writes PNG previews of every size and exits.
@main
enum Main {
    static func main() {
        if CommandLine.arguments.contains("--render") {
            MainActor.assumeIsolated { Renderer.renderAll() }
            exit(0)
        }
        if CommandLine.arguments.contains("--measure") {
            MainActor.assumeIsolated { Renderer.measureAll() }
            exit(0)
        }
        DevStatsApp.main()
    }
}

struct DevStatsApp: App {
    var body: some Scene {
        WindowGroup("Dev Stats") {
            PreviewGallery(snapshot: SnapshotStore.load() ?? .sample)
        }
        .windowResizability(.contentSize)
    }
}

struct WidgetFrame<Content: View>: View {
    let size: CGSize
    @ViewBuilder let content: Content

    var body: some View {
        content
            .padding(16)
            .frame(width: size.width, height: size.height)
            .background(Color(nsColor: .windowBackgroundColor))
            .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
    }
}

enum Sizes {
    static let small = CGSize(width: 170, height: 170)
    static let medium = CGSize(width: 364, height: 170)
    static let large = CGSize(width: 364, height: 382)
}

struct PreviewGallery: View {
    let snapshot: Snapshot

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Masaüstüne eklemek için: masaüstünde sağ tık > Widget'ları Düzenle > Dev Stats")
                .font(.callout).foregroundStyle(.secondary)
            HStack(alignment: .top, spacing: 16) {
                VStack(spacing: 16) {
                    WidgetFrame(size: Sizes.small) { SmallView(s: snapshot) }
                    WidgetFrame(size: Sizes.medium) { MediumView(s: snapshot) }
                }
                WidgetFrame(size: Sizes.large) { LargeView(s: snapshot) }
            }
        }
        .padding(24)
    }
}

@MainActor
enum Renderer {
    static func renderAll() {
        // --sample renders the bundled demo data (used for README screenshots)
        let snap = CommandLine.arguments.contains("--sample") ? .sample : (SnapshotStore.load() ?? .sample)
        let dir = URL(fileURLWithPath: NSTemporaryDirectory())
        for scheme in [ColorScheme.dark, .light] {
            let tag = scheme == .dark ? "dark" : "light"
            write(WidgetFrame(size: Sizes.small) { SmallView(s: snap) }, scheme, dir.appendingPathComponent("small-\(tag).png"))
            write(WidgetFrame(size: Sizes.medium) { MediumView(s: snap) }, scheme, dir.appendingPathComponent("medium-\(tag).png"))
            write(WidgetFrame(size: Sizes.large) { LargeView(s: snap) }, scheme, dir.appendingPathComponent("large-\(tag).png"))
        }
        print(dir.path)
    }

    /// Ideal content height of each layout at the widget's content width, compared with the
    /// height left inside 16 pt content margins. Taller content is centered by WidgetKit and
    /// loses its top rows (the clipped headers), so every layout has to report "fits".
    static func measureAll() {
        let snap = CommandLine.arguments.contains("--sample") ? .sample : (SnapshotStore.load() ?? .sample)
        func measure<V: View>(_ name: String, _ size: CGSize, _ view: V) {
            let width = size.width - 32, available = size.height - 32
            let r = ImageRenderer(content: view.frame(width: width).fixedSize(horizontal: false, vertical: true))
            let h = r.nsImage?.size.height ?? -1
            let verdict = h <= available ? "fits" : "OVERFLOW"
            print("\(name.padding(toLength: 7, withPad: " ", startingAt: 0)) content \(Int(h)) / available \(Int(available))  \(verdict)")
        }
        measure("small", Sizes.small, SmallView(s: snap))
        measure("medium", Sizes.medium, MediumView(s: snap))
        measure("large", Sizes.large, LargeView(s: snap))
    }

    private static func write<V: View>(_ view: V, _ scheme: ColorScheme, _ url: URL) {
        let r = ImageRenderer(content: view.environment(\.colorScheme, scheme)
            .preferredColorScheme(scheme))
        r.scale = 2
        guard let img = r.nsImage, let tiff = img.tiffRepresentation,
              let rep = NSBitmapImageRep(data: tiff), let png = rep.representation(using: .png, properties: [:])
        else { print("render failed: \(url.lastPathComponent)"); return }
        try? png.write(to: url)
    }
}
