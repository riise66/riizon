import json
import os
import re
from pathlib import Path

import feedparser
import requests

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Feeds RSS de chollos (gratis, sin scraping frágil). Añade los que quieras.
FEEDS = [
    "https://www.chollometro.com/rss/hot",
]

# Solo avisa si el título contiene alguna de estas palabras (vacío = todo).
KEYWORDS = []  # ejemplo: ["ssd", "rtx", "ryzen", "monitor"]

# Descuento mínimo si el título lo indica (ej. "-40%"). 0 = no filtrar.
MIN_DISCOUNT = 0

SEEN_FILE = Path("seen.json")


def load_seen():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(sorted(seen)[-2000:]))


def discount(title):
    m = re.search(r"-?(\d{2,3})\s?%", title)
    return int(m.group(1)) if m else 0


def passes(title):
    if KEYWORDS and not any(k.lower() in title.lower() for k in KEYWORDS):
        return False
    if MIN_DISCOUNT and discount(title) < MIN_DISCOUNT:
        return False
    return True


def send(text):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text},
        timeout=20,
    ).raise_for_status()


def main():
    seen = load_seen()
    first_run = not seen
    for url in FEEDS:
        for e in feedparser.parse(url).entries:
            uid = e.get("id") or e.link
            if uid in seen:
                continue
            seen.add(uid)
            if first_run:  # no inundar el primer día
                continue
            if passes(e.title):
                send(f"🔥 {e.title}\n{e.link}")
    save_seen(seen)


if __name__ == "__main__":
    main()
