from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from googleapiclient.discovery import build
import html
import os

API_KEY = os.environ["YOUTUBE_API_KEY"]
PLAYLIST_ID = "PLUBKwq0XD0ueR3CXGUhGpsD1puLcYJPUp"  # must be public
PLAYLIST_URL = f"https://www.youtube.com/playlist?list={PLAYLIST_ID}"
SITE_LINK = PLAYLIST_URL  # channel/playlist homepage for <link> fields
TITLE = "Custom YouTube Playlist (last 14 days)"
DESC = "Auto-generated feed of recently published videos from a YouTube playlist."
OUTPUT_DIR = "public"


def iso_to_dt(s):  # RFC3339 → aware datetime
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def main():
    yt = build("youtube", "v3", developerKey=API_KEY)

    # Collect video IDs from playlist
    vids, page = [], None
    while True:
        r = (
            yt.playlistItems()
            .list(
                part="contentDetails",
                playlistId=PLAYLIST_ID,
                maxResults=50,
                pageToken=page,
            )
            .execute()
        )
        vids += [it["contentDetails"]["videoId"] for it in r.get("items", [])]
        page = r.get("nextPageToken")
        if not page:
            break

    if not vids:
        open("feed.xml", "w", encoding="utf-8").write(
            f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
            f"<title>{html.escape(TITLE)}</title><link>{SITE_LINK}</link>"
            f"<description>{html.escape(DESC)}</description>"
            f"<lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>"
            f"</channel></rss>"
        )
        print("No videos found; wrote empty feed.xml")
        return

    # Fetch metadata and filter by publishedAt
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    entries = []
    for batch in chunk(vids, 50):
        v = (
            yt.videos()
            .list(part="snippet,contentDetails", id=",".join(batch))
            .execute()
        )
        for it in v.get("items", []):
            sn = it["snippet"]
            pub = iso_to_dt(sn["publishedAt"])
            if pub >= cutoff:
                vid = it["id"]
                entries.append(
                    {
                        "title": sn["title"],
                        "link": f"https://www.youtube.com/watch?v={vid}",
                        "guid": vid,
                        "pubDate": format_datetime(pub),
                        "desc": sn.get("description", "")[:1000],  # trim a bit
                    }
                )

    # Sort newest first
    entries.sort(key=lambda e: e["pubDate"], reverse=True)

    # Build RSS XML
    items_xml = "".join(
        f"<item>"
        f"<title>{html.escape(e['title'])}</title>"
        f"<link>{e['link']}</link>"
        f"<guid isPermaLink='false'>{html.escape(e['guid'])}</guid>"
        f"<pubDate>{e['pubDate']}</pubDate>"
        f"<description><![CDATA[{e['desc']}]]></description>"
        f"</item>"
        for e in entries
    )

    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0"><channel>'
        f"<title>{html.escape(TITLE)}</title>"
        f"<link>{SITE_LINK}</link>"
        f"<description>{html.escape(DESC)}</description>"
        f"<lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>"
        f"<ttl>30</ttl>"
        f"{items_xml}"
        "</channel></rss>"
    )

    with open(os.path.join(OUTPUT_DIR, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(rss)

    print("Wrote feed.xml")


if __name__ == "__main__":
    main()
