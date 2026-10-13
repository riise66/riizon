import json
import os
import re
from pathlib import Path

import feedparser
import requests

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# "nuevos" = ofertas recién publicadas (los errores de precio salen aquí primero)
FEEDS = [
    "https://www.chollometro.com/rss/nuevos",
    "https://www.chollometro.com/rss/hot",
]

# Solo ofertas de esta tienda (vacío = todas)
STORE = "amazon"

# Te avisa si se cumple CUALQUIERA de estas condiciones:
MIN_DISCOUNT = 40          # descuento >= 40% (si el título lo indica)
MAX_PRICE = 5.0            # precio <= 5 € (ej. las ofertas de 2 €)
ALERT_WORDS = ["error de precio", "error precio", "bug", "chollazo", "mínimo histórico", "minimo historico"]

SEEN_FILE = Path("seen.json")


def load_seen():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(sorted(seen)[-3000:]))


def discount(text):
    m = re.search(r"-\s?(\d{2,3})\s?%", text)
    return int(m.group(1)) if m else 0


def lowest_price(text):
    prices = []
    for m in re.finditer(r"(\d+(?:[.,]\d{1,2})?)\s?(?:€|eur)", text, re.I):
        try:
            prices.append(float(m.group(1).replace(",", ".")))
        except ValueError:
            pass
    return min(prices) if prices else None


def passes(entry):
    title = entry.get("title", "")
    blob = f"{title} {entry.get('summary', '')}".lower()
    if STORE and STORE not in blob:
        return False
    price = lowest_price(title)
    return (
        discount(title) >= MIN_DISCOUNT
        or (price is not None and price <= MAX_PRICE)
        or any(w in blob for w in ALERT_WORDS)
    )


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
            if passes(e):
                send(f"🔥 {e.title}\n{e.link}")
    save_seen(seen)


if __name__ == "__main__":
    main()
