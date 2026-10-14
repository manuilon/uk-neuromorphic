#!/usr/bin/env python3
"""
Pulls the latest news posts from the three initiative sites and writes
assets/news.json for the "Latest news" section.

Unlike events, every source here publishes a proper post date, so no
date-guessing is needed:
  - NeuroSYNC (Wix): the blog's RSS feed at /blog-feed.xml.
  - NeuMat (custom site): /news/ lists cards with a DD/MM/YYYY date.
  - NeuroWare (WordPress): the "updates" post type via the REST API.

If a source fails, its items from the previous news.json are kept, so a
temporary outage doesn't empty that initiative's column on the site.

Run manually with: python3 scripts/scrape_news.py
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from bs4 import BeautifulSoup

from scrape_events import fetch

PER_SOURCE = 10
SUMMARY_CHARS = 220

OUT_PATH = Path(__file__).resolve().parent.parent / "assets" / "news.json"


def clean_text(markup):
    text = BeautifulSoup(markup or "", "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def summarise(markup):
    text = clean_text(markup)
    if len(text) <= SUMMARY_CHARS:
        return text
    return text[:SUMMARY_CHARS].rsplit(" ", 1)[0].rstrip(",;:–-") + "…"


def item(source, label, title, url, date, summary):
    return {
        "title": title,
        "url": url,
        "date": date.date().isoformat(),
        "summary": summary,
        "source": source,
        "sourceLabel": label,
    }


def scrape_neurosync():
    xml_text = fetch("https://www.uk-neuromorphic-centre.net/blog-feed.xml")
    root = ET.fromstring(xml_text.encode("utf-8"))
    items = []
    for entry in root.iter("item"):
        title = clean_text(entry.findtext("title"))
        link = (entry.findtext("link") or "").strip()
        pub = entry.findtext("pubDate")
        if not title or not link or not pub:
            continue
        items.append(item("neurosync", "NeuroSYNC", title, link,
                          parsedate_to_datetime(pub), summarise(entry.findtext("description"))))
    return items


def scrape_neumat():
    html = fetch("https://www.neumat.co.uk/news/")
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select("a.nk-box-bi"):
        title_el = card.select_one(".nk-box-bi-title")
        date_el = card.select_one(".nk-box-bi-date")
        desc_el = card.select_one(".nk-box-bi-desc")
        if not title_el or not date_el:
            continue
        try:
            date = datetime.strptime(date_el.get_text(strip=True), "%d/%m/%Y").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        href = card.get("href", "")
        if href.startswith("/"):
            href = "https://www.neumat.co.uk" + href
        items.append(item("neumat", "NeuMat", clean_text(str(title_el)), href,
                          date, summarise(str(desc_el) if desc_el else "")))
    return items


def scrape_neuroware():
    posts = fetch(
        f"https://neuroware-ikc.com/wp-json/wp/v2/updates?per_page={PER_SOURCE}&_fields=date,title,excerpt,link",
        as_json=True,
    )
    items = []
    for post in posts:
        title = clean_text(post.get("title", {}).get("rendered", ""))
        link = post.get("link", "")
        if not title or not link or not post.get("date"):
            continue
        date = datetime.fromisoformat(post["date"]).replace(tzinfo=timezone.utc)
        items.append(item("neuroware", "NeuroWare", title, link,
                          date, summarise(post.get("excerpt", {}).get("rendered", ""))))
    return items


def previous_items(source):
    try:
        old = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [n for n in old.get("news", []) if n.get("source") == source]


def main():
    all_items, errors = [], []

    for source, scraper in (("neurosync", scrape_neurosync),
                            ("neumat", scrape_neumat),
                            ("neuroware", scrape_neuroware)):
        try:
            items = scraper()
            if not items:
                raise ValueError("no posts found")
        except Exception as exc:  # noqa: BLE001 - one source failing shouldn't kill the run
            errors.append({"source": source, "error": str(exc)})
            items = previous_items(source)
        items.sort(key=lambda n: n["date"], reverse=True)
        all_items.extend(items[:PER_SOURCE])

    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "news": all_items,
        "errors": errors,
    }
    OUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote {len(all_items)} news item(s) to {OUT_PATH}", file=sys.stderr)
    for err in errors:
        print(f"  - {err['source']}: {err['error']}", file=sys.stderr)


if __name__ == "__main__":
    main()
