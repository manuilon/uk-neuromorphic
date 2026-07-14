#!/usr/bin/env python3
"""
Pulls event listings (both upcoming and past) from the three initiative
sites and writes assets/events.json for the site to read at runtime. Every
event gets a status of "upcoming" or "past" so the page can render both
the "What's coming up" grid and a past-events archive from one file.

Sources are structurally very different:
  - NeuroSYNC (Wix): the homepage embeds an "upcoming only" widget, but
    the dedicated /event-list page server-renders full Upcoming AND Past
    sections, both using stable data-hook attributes. Trusted directly,
    no date filtering needed — Wix's own bucketing is authoritative.
  - NeuMat (custom site): has no dedicated events feed. Event mentions
    are free text inside "News" post excerpts. We regex for a date-like
    substring and classify it as upcoming/past by comparing to today.
  - NeuroWare (WordPress): has a clean REST API for its "Updates" post
    type, but no events content type at all. Same date-regex heuristic
    as NeuMat, applied to title + excerpt. Will legitimately yield zero
    results until they publish something with a date in it.

Run manually with: python3 scripts/scrape_events.py
"""

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; UKNeuromorphicEventsBot/1.0; +https://github.com/manuilon/uk-neuromorphic)"
TIMEOUT = 20

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}
MONTH_ALT = "|".join(MONTHS.keys())
# Wix's short-date widget uses 3-letter abbreviations ("Apr", "Oct"), which
# only coincidentally matched MONTHS before for "May" (same as its full name).
MONTH_ABBR = {name[:3]: num for name, num in MONTHS.items()}


def month_number(month_name):
    name = month_name.lower()
    return MONTHS.get(name) or MONTH_ABBR.get(name[:3])

# Ordered most- to least-specific so the first match wins.
DATE_PATTERNS = [
    re.compile(rf"\b(\d{{1,2}})\s*[-–]\s*\d{{1,2}}\s+({MONTH_ALT})\s+(\d{{4}})\b", re.I),  # 21-22 September 2026
    re.compile(rf"\b(\d{{1,2}})\s+({MONTH_ALT})\s+(\d{{4}})\b", re.I),                      # 22 June 2026
    re.compile(rf"\b()({MONTH_ALT})\s+(\d{{4}})\b", re.I),                                  # November 2026
]


def fetch(url, as_json=False):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        body = resp.read()
    return json.loads(body) if as_json else body.decode("utf-8", errors="replace")


def fetch_article_text(url):
    """Text of just the <article> element on a page — not the full page,
    which also contains nav/sidebar/related-post text that can pollute
    date extraction with dates that belong to a different story."""
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article")
    return (article or soup).get_text(" ", strip=True)


def find_date_mention(text):
    """Best-effort: first date-like substring in free text, or None."""
    for pattern in DATE_PATTERNS:
        m = pattern.search(text)
        if m:
            day, month_name, year = m.groups()
            month = MONTHS[month_name.lower()]
            day_num = int(day) if day else 1
            try:
                parsed = datetime(int(year), month, day_num, tzinfo=timezone.utc)
            except ValueError:
                continue
            return m.group(0).strip(), parsed
    return None, None


def guess_year_for_short_date(short_date, today, prefer_future=True):
    """NeuroSYNC's Wix widget renders 'Sat 01 May' with no year. Guess the
    nearest occurrence of that month/day in the requested direction —
    forward for an upcoming-listed event, backward for a past-listed one."""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)", short_date)
    if not m:
        return None
    day, month_name = m.groups()
    month = month_number(month_name)
    if not month:
        return None
    candidate_years = (today.year, today.year + 1) if prefer_future else (today.year, today.year - 1)
    for year in candidate_years:
        try:
            candidate = datetime(year, month, int(day), tzinfo=timezone.utc)
        except ValueError:
            continue
        if prefer_future and candidate.date() >= today.date():
            return candidate
        if not prefer_future and candidate.date() <= today.date():
            return candidate
    return None


def _neurosync_card_to_event(item, today, status):
    link = item.select_one('a[href*="/event-details/"]')
    if not link:
        return None
    title = link.get_text(strip=True)
    url = link.get("href", "")
    if url.startswith("/"):
        url = "https://www.uk-neuromorphic-centre.net" + url
    date_el = item.select_one('[data-hook="short-date"]')
    loc_el = item.select_one('[data-hook="short-location"]')
    widget_date_text = date_el.get_text(strip=True) if date_el else ""
    location = loc_el.get_text(strip=True) if loc_el else ""
    if not title or not url:
        return None

    # The widget's own short-date (e.g. "Sat 01 May") has no year and has
    # been observed to disagree with the event's real dates. If the title
    # itself spells out a date (Wix event titles often include one),
    # that's more trustworthy — prefer it.
    title_date_text, title_date_parsed = find_date_mention(title)
    if title_date_text:
        date_text = title_date_text
        sort_date = title_date_parsed
    else:
        date_text = widget_date_text
        guessed = guess_year_for_short_date(widget_date_text, today, prefer_future=(status == "upcoming"))
        sort_date = guessed or today

    return {
        "title": title,
        "date": date_text,
        "location": location,
        "url": url,
        "source": "neurosync",
        "sourceLabel": "NeuroSYNC",
        "status": status,
        "sortDate": sort_date.isoformat(),
    }


def scrape_neurosync(today):
    events, errors = [], []
    try:
        html = fetch("https://www.uk-neuromorphic-centre.net/event-list")
        soup = BeautifulSoup(html, "html.parser")
        for item in soup.select('[data-hook="side-by-side-item"]'):
            event = _neurosync_card_to_event(item, today, "upcoming")
            if event:
                events.append(event)
        for item in soup.select('[data-hook="events-card"]'):
            event = _neurosync_card_to_event(item, today, "past")
            if event:
                events.append(event)
    except Exception as exc:  # noqa: BLE001 - one source failing shouldn't kill the run
        errors.append({"source": "neurosync", "error": str(exc)})
    return events, errors


def scrape_neumat(today):
    events, errors = [], []
    try:
        html = fetch("https://www.neumat.co.uk/news/")
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select("a.nk-box-bi"):
            title_el = card.select_one(".nk-box-bi-title")
            desc_el = card.select_one(".nk-box-bi-desc")
            if not title_el or not desc_el:
                continue
            title = title_el.get_text(strip=True)
            desc_text = desc_el.get_text(" ", strip=True)
            href = card.get("href", "")
            if href.startswith("/"):
                href = "https://www.neumat.co.uk" + href
            date_text, parsed = find_date_mention(f"{title} {desc_text}")
            if not date_text or not parsed:
                continue  # no date mention to go on at all

            # The listing excerpt is often terser than the article itself
            # (e.g. "November 2026" vs. the full "23-25 November 2026").
            # Re-check against the full article body and prefer that if
            # it turns up a match too.
            try:
                full_date_text, full_parsed = find_date_mention(fetch_article_text(href))
                if full_date_text:
                    date_text, parsed = full_date_text, full_parsed
            except Exception:  # noqa: BLE001 - fall back to the excerpt-derived date
                pass

            events.append({
                "title": title,
                "date": date_text,
                "location": "",
                "url": href,
                "source": "neumat",
                "sourceLabel": "NeuMat",
                "status": "upcoming" if parsed.date() >= today.date() else "past",
                "sortDate": parsed.isoformat(),
            })
    except Exception as exc:  # noqa: BLE001
        errors.append({"source": "neumat", "error": str(exc)})
    return events, errors


def scrape_neuroware(today):
    events, errors = [], []
    try:
        posts = fetch(
            "https://neuroware-ikc.com/wp-json/wp/v2/updates?per_page=20&_fields=title,excerpt,link",
            as_json=True,
        )
        for post in posts:
            title = post.get("title", {}).get("rendered", "").strip()
            excerpt_html = post.get("excerpt", {}).get("rendered", "")
            excerpt_text = BeautifulSoup(excerpt_html, "html.parser").get_text(" ", strip=True)
            link = post.get("link", "")
            date_text, parsed = find_date_mention(f"{title} {excerpt_text}")
            if not date_text or not parsed:
                continue

            try:
                full_date_text, full_parsed = find_date_mention(fetch_article_text(link))
                if full_date_text:
                    date_text, parsed = full_date_text, full_parsed
            except Exception:  # noqa: BLE001
                pass

            events.append({
                "title": title,
                "date": date_text,
                "location": "",
                "url": link,
                "source": "neuroware",
                "sourceLabel": "NeuroWare",
                "status": "upcoming" if parsed.date() >= today.date() else "past",
                "sortDate": parsed.isoformat(),
            })
    except Exception as exc:  # noqa: BLE001
        errors.append({"source": "neuroware", "error": str(exc)})
    return events, errors


SPOTLIGHT_PREFIX = re.compile(r"^(neumat|neurosync|neuroware)\s+spotlight:\s*", re.I)
STOPWORDS = {"the", "and", "for", "with", "from", "this", "that", "workshop", "event", "events"}


def _significant_words(title):
    t = SPOTLIGHT_PREFIX.sub("", title)
    t = re.sub(r"[^a-z0-9 ]+", " ", t.lower())
    return {w for w in t.split() if len(w) > 3 and w not in STOPWORDS}


def dedupe(events):
    """Different sites often cover the same event (e.g. a NeuMat 'Spotlight'
    post about a NeuroSYNC-hosted conference). Collapse near-duplicate
    titles, preferring whichever isn't a "Spotlight:" repost.

    Only compares events from *different* sources: a single site can
    legitimately run several distinct events that share boilerplate
    wording (e.g. "NeuroSYNC Stakeholder Engagement Workshop - Research"
    vs. "... - Defence, Security, Industry"), and same-source titles are
    already that site's own distinct listing, so cross-title overlap
    there is never a repost."""
    kept = []
    for event in events:
        words = _significant_words(event["title"])
        match_idx = None
        for i, existing in enumerate(kept):
            if existing["source"] == event["source"]:
                continue
            existing_words = _significant_words(existing["title"])
            if not words or not existing_words:
                continue
            overlap = len(words & existing_words) / max(1, min(len(words), len(existing_words)))
            if overlap >= 0.6:
                match_idx = i
                break
        if match_idx is None:
            kept.append(event)
            continue
        existing = kept[match_idx]
        if SPOTLIGHT_PREFIX.match(existing["title"]) and not SPOTLIGHT_PREFIX.match(event["title"]):
            kept[match_idx] = event
    return kept


def main():
    today = datetime.now(timezone.utc)
    all_events, all_errors = [], []

    for scraper in (scrape_neurosync, scrape_neumat, scrape_neuroware):
        events, errors = scraper(today)
        all_events.extend(events)
        all_errors.extend(errors)

    all_events.sort(key=lambda e: e["sortDate"])
    all_events = dedupe(all_events)

    output = {
        "generatedAt": today.isoformat(),
        "events": all_events,
        "errors": all_errors,
    }

    out_path = Path(__file__).resolve().parent.parent / "assets" / "events.json"
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(all_events)} event(s) to {out_path}", file=sys.stderr)
    if all_errors:
        print(f"{len(all_errors)} source error(s):", file=sys.stderr)
        for err in all_errors:
            print(f"  - {err['source']}: {err['error']}", file=sys.stderr)


if __name__ == "__main__":
    main()
