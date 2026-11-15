#!/usr/bin/env python3
"""Build AltStore-format sources (Feather, SideStore, AltStore Classic) for YTKACE.

Reads the public GitHub releases of itzzace/ytkace and writes two files:
  ytkace.json        - iOS 17+ builds   (YTKACE_<v>_YouTube_<yt>.ipa)
  ytkace-ios16.json  - iOS 16 builds    (YTKACE_<v>_YouTube_iOS16_<yt>.ipa)

The two builds share one bundle ID, so they live in separate sources.
Standard library only. Set GITHUB_TOKEN to avoid API rate limits.
"""
import json
import os
import re
import sys
import urllib.request

UPSTREAM = "itzzace/ytkace"
OWNER = os.environ.get("SOURCE_OWNER", "Jimkaram2")
REPO = os.environ.get("SOURCE_REPO", "ytkace-source")
PAGES = f"https://{OWNER.lower()}.github.io/{REPO}"
BUNDLE_ID = "com.google.ios.youtube"
MAX_VERSIONS = 10

IPA_RE = re.compile(r"^YTKACE_(?P<v>[\d.]+)_YouTube_(?P<ios16>iOS16_)?(?P<yt>[\d.]+)\.ipa$")


def fetch_releases():
    req = urllib.request.Request(
        f"https://api.github.com/repos/{UPSTREAM}/releases?per_page=30",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "ytkace-source"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def build(releases, ios16):
    versions = []
    for rel in releases:
        if rel.get("draft"):
            continue
        for asset in rel.get("assets", []):
            m = IPA_RE.match(asset["name"])
            if not m or bool(m.group("ios16")) != ios16:
                continue
            versions.append({
                "version": m.group("v"),
                "buildVersion": m.group("yt"),
                "date": rel["published_at"],
                "localizedDescription": f"YTKACE {m.group('v')} on YouTube {m.group('yt')}.\n\n"
                                        + (rel.get("body") or "").strip()[:3000],
                "downloadURL": asset["browser_download_url"],
                "size": asset["size"],
                "minOSVersion": "16.0" if ios16 else "17.0",
            })
            break
        if len(versions) >= MAX_VERSIONS:
            break

    suffix = " (iOS 16)" if ios16 else ""
    latest = versions[0] if versions else None
    app = {
        "name": "YTKACE" + suffix,
        "bundleIdentifier": BUNDLE_ID,
        "developerName": "itzzace",
        "subtitle": "YouTube with downloads, SponsorBlock and background play",
        "localizedDescription": "Unofficial source that mirrors the IPAs published on "
                                f"github.com/{UPSTREAM}/releases. Files are downloaded "
                                "directly from those GitHub releases, unmodified.",
        "tintColor": "#E5372B",
        "category": "entertainment",
        "screenshotURLs": [
            f"https://raw.githubusercontent.com/{UPSTREAM}/main/screenshots/framed/glass-home.png",
            f"https://raw.githubusercontent.com/{UPSTREAM}/main/screenshots/framed/video-player.png",
        ],
        "versions": versions,
        "appPermissions": {"entitlements": [], "privacy": {}},
    }
    if latest:  # legacy top-level fields; Feather and older clients read these
        app.update({
            "version": latest["version"],
            "versionDate": latest["date"],
            "versionDescription": latest["localizedDescription"],
            "downloadURL": latest["downloadURL"],
            "size": latest["size"],
        })
    filename = "ytkace-ios16.json" if ios16 else "ytkace.json"
    return filename, {
        "name": "YTKACE" + suffix,
        "identifier": f"io.github.{OWNER.lower()}.ytkace" + (".ios16" if ios16 else ""),
        "sourceURL": f"{PAGES}/{filename}",
        "subtitle": f"Auto-updated mirror of {UPSTREAM} releases",
        "website": f"https://github.com/{UPSTREAM}",
        "tintColor": "#E5372B",
        "apps": [app],
        "news": [],
    }


def main(out_dir="."):
    releases = fetch_releases()
    for ios16 in (False, True):
        filename, source = build(releases, ios16)
        if not source["apps"][0]["versions"]:
            print(f"warning: no matching IPAs for {filename}", file=sys.stderr)
        with open(os.path.join(out_dir, filename), "w") as fh:
            json.dump(source, fh, indent=2)
            fh.write("\n")
        print(f"{filename}: {len(source['apps'][0]['versions'])} versions")


if __name__ == "__main__":
    main(*sys.argv[1:])
