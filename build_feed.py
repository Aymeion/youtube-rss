from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from googleapiclient.discovery import build
import html
import os
import config as c

API_KEY = os.environ["YOUTUBE_API_KEY"]

TITLE = f"Custom YouTube Playlist (last {c.NB_DAYS} days)"
DESC = "Auto-generated feed of recently published videos from YouTube playlist."
OUTPUT_DIR = "public"


def iso_to_dt(s):  # RFC3339 → aware datetime
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def main():
    yt = build("youtube", "v3", developerKey=API_KEY)

    # --- collect video IDs from ALL playlists ---
    # c.PLAYLISTS is expected to be a dict: {"Playlist Name": "PLxxxxx", ...}
    all_video_ids = set()
    belongs_to = {}  # videoId -> set of playlist names (for <category> tags)

    for plist_name, plist_id in c.PLAYLISTS.items():
        page = None
        while True:
            r = (
                yt.playlistItems()
                .list(
                    part="contentDetails",
                    playlistId=plist_id,
                    maxResults=50,
                    pageToken=page,
                )
                .execute()
            )

            for it in r.get("items", []):
                vid = it["contentDetails"]["videoId"]
                all_video_ids.add(vid)
                belongs_to.setdefault(vid, set()).add(plist_name)

            page = r.get("nextPageToken")
            if not page:
                break

    if not all_video_ids:
        # write an empty feed (keeps Pages happy)
        with open(os.path.join(OUTPUT_DIR, "feed.xml"), "w", encoding="utf-8") as f:
            f.write(
                f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
                f"<title>{html.escape(TITLE)}</title>"
                f"<description>{html.escape(DESC)}</description>"
                f"<lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>"
                f"</channel></rss>"
            )
        print("No videos found; wrote empty feed.xml")
        return

    # --- fetch metadata in batches and filter by publish date ---
    cutoff = datetime.now(timezone.utc) - timedelta(days=c.NB_DAYS)
    entries = []

    for batch in chunk(list(all_video_ids), 50):
        v = (
            yt.videos()
            .list(part="snippet,contentDetails", id=",".join(batch))
            .execute()
        )
        for it in v.get("items", []):
            sn = it["snippet"]
            pub_dt = iso_to_dt(sn["publishedAt"])
            if pub_dt >= cutoff:
                vid = it["id"]
                entries.append(
                    {
                        "title": sn["title"],
                        "link": f"https://www.youtube.com/watch?v={vid}",
                        "guid": vid,
                        "pub_dt": pub_dt,  # datetime for sorting
                        "pubDate": format_datetime(pub_dt),  # RSS string
                        "desc": sn.get("description", "")[:1000],
                        "cats": sorted(belongs_to.get(vid, [])),  # playlist names
                    }
                )

    # newest first
    entries.sort(key=lambda e: e["pub_dt"], reverse=True)

    # --- build RSS ---
    def item_xml(e):
        cats = "".join(f"<category>{html.escape(c)}</category>" for c in e["cats"])
        return (
            "<item>"
            f"<title>{html.escape(e['title'])}</title>"
            f"<link>{e['link']}</link>"
            f"<guid isPermaLink='false'>{html.escape(e['guid'])}</guid>"
            f"<pubDate>{e['pubDate']}</pubDate>"
            f"{cats}"
            f"<description><![CDATA[{e['desc']}]]></description>"
            "</item>"
        )

    items_xml = "".join(item_xml(e) for e in entries)

    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0"><channel>'
        f"<title>{html.escape(TITLE)}</title>"
        f"<link></link>"
        f"<description>{html.escape(DESC)}</description>"
        f"<lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>"
        f"<ttl>30</ttl>"
        f"{items_xml}"
        "</channel></rss>"
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(rss)

    print("Wrote feed.xml")


if __name__ == "__main__":
    main()
