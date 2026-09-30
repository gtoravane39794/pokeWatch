import logging
import time

import requests

log = logging.getLogger("pokewatch.discord")

GOLD, GREEN = 0xF5C518, 0x2ECC71


def send(webhook: str, payload: dict, dry_run: bool = False) -> bool:
    if dry_run or not webhook:
        log.info("[dry-run] would post: %s", payload)
        return True
    for _ in range(3):
        try:
            r = requests.post(webhook, json=payload, timeout=15)
        except requests.RequestException as e:
            log.warning("discord post failed: %s", e)
            time.sleep(2)
            continue
        if r.status_code == 429:
            time.sleep(float(r.json().get("retry_after", 2)) + 0.2)
            continue
        if r.status_code >= 300:
            log.error("discord HTTP %s: %s", r.status_code, r.text[:200])
            return False
        return True
    return False


def _mention_fields(mention: str) -> dict:
    if not mention:
        return {}
    parse = []
    if mention in ("@everyone", "@here"):
        parse = ["everyone"]
    return {"content": mention, "allowed_mentions": {"parse": parse, "users": _ids(mention)}}


def _ids(m: str) -> list[str]:
    import re
    return re.findall(r"<@!?(\d+)>", m)


def drop_payload(p, verdict, mention: str = "") -> dict:
    price = f"${p.price:.2f}" if p.price is not None else "?"
    links = [f"[Open product]({p.url})"]
    if p.cart_url:
        links.insert(0, f"**[ADD TO CART]({p.cart_url})**")
    embed = {
        "title": ("PRIORITY DROP: " if verdict.priority else "DROP: ") + p.title[:200],
        "url": p.cart_url or p.url,
        "color": GOLD if verdict.priority else GREEN,
        "fields": [
            {"name": "Store", "value": p.retailer, "inline": True},
            {"name": "Current price", "value": price, "inline": True},
            {"name": "Normal range", "value": f"{verdict.kind}: up to ${verdict.cap:.0f}", "inline": True},
            {"name": "Sold by", "value": p.seller or f"{p.retailer} (first-party)", "inline": True},
            {"name": "Links", "value": "  |  ".join(links), "inline": False},
        ],
        "footer": {"text": "PokeWatch - verified first-party & under scalper cap. Buy fast."},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if p.image:
        embed["thumbnail"] = {"url": p.image}
        embed["image"] = {"url": p.image}
    return {"username": "PokeWatch", **_mention_fields(mention), "embeds": [embed]}


def text_payload(msg: str) -> dict:
    return {"username": "PokeWatch", "content": msg}
