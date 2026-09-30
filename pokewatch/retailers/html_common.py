import json
import re

from ..models import Product
from ..rules import clean_title

LD = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.S | re.I)


def _walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from _walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk(v)


def products_from_jsonld(retailer: str, html: str, base: str) -> list[Product]:
    out = []
    for m in LD.finditer(html):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            continue
        for d in _walk(data):
            if d.get("@type") != "Product" or not d.get("name"):
                continue
            offers = d.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            try:
                price = float(offers.get("price"))
            except (TypeError, ValueError):
                price = None
            url = d.get("url") or offers.get("url") or base
            img = d.get("image")
            if isinstance(img, list):
                img = img[0] if img else None
            avail = str(offers.get("availability", ""))
            out.append(Product(retailer, str(d.get("sku") or url), clean_title(d["name"]), price,
                               url, "InStock" in avail, img if isinstance(img, str) else None))
    return out
