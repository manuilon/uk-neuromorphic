#!/usr/bin/env python3
"""
Copies the NeuMat Research Network Map (https://www.neumat.co.uk/network/)
into assets/network.json so the site can draw the same organisations on
its own map. NeuMat's page can't be embedded (it sends
X-Frame-Options: SAMEORIGIN), but the map is fed by two public endpoints:
  - GetNetworkData: every organisation with type, specialisms and lat/lng.
  - GetNetworkItem?id=: the detail pop-up, which holds the website link.

If the main endpoint fails, network.json is left untouched so the site
keeps showing the last good copy.

Run manually with: python3 scripts/scrape_network.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from scrape_events import fetch

DATA_URL = "https://www.neumat.co.uk/umbraco/surface/map/GetNetworkData"
ITEM_URL = "https://www.neumat.co.uk/umbraco/surface/map/GetNetworkItem?id={}"

OUT_PATH = Path(__file__).resolve().parent.parent / "assets" / "network.json"


def website_for(org_id):
    try:
        soup = BeautifulSoup(fetch(ITEM_URL.format(org_id)), "html.parser")
    except Exception:  # noqa: BLE001 - a missing link just means no "Website" in the pop-up
        return ""
    link = soup.select_one("a.nk-uri-2")
    href = (link.get("href", "") if link else "").strip()
    return href if href.startswith(("http://", "https://")) else ""


def main():
    try:
        data = fetch(DATA_URL, as_json=True)
        if not data.get("ok") or not data.get("results"):
            raise ValueError("GetNetworkData returned no results")
    except Exception as exc:  # noqa: BLE001
        print(f"NeuMat network map unavailable, keeping previous file: {exc}", file=sys.stderr)
        return

    orgs = []
    for row in data["results"]:
        try:
            lat, lng = float(row["lat"]), float(row["lng"])
        except (KeyError, TypeError, ValueError):
            continue
        orgs.append({
            "id": str(row.get("id", "")),
            "name": (row.get("title") or "").strip(),
            "type": (row.get("type") or "Other").strip(),
            "specialisms": [s for s in row.get("specialisms") or [] if s],
            "lat": lat,
            "lng": lng,
            "website": website_for(row.get("id")),
        })
    orgs.sort(key=lambda o: o["name"].lower())

    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "https://www.neumat.co.uk/network/",
        "organisations": orgs,
    }
    OUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(orgs)} organisation(s) to {OUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
