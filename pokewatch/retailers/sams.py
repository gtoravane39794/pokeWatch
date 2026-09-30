import json
import re
from urllib.parse import quote

from ..models import Product
from ..rules import clean_title
from .base import Retailer

NEXT = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def _products(o, out):
    if isinstance(o, dict):
        if o.get("__typename") == "Product" and o.get("usItemId"):
            out.append(o)
        for v in o.values():
            _products(v, out)
    elif isinstance(o, list):
        for v in o:
            _products(v, out)


def _price(s: str | None) -> float | None:
    m = re.search(r"\$([\d,]+(?:\.\d+)?)", s or "")
    return float(m.group(1).replace(",", "")) if m else None


class Sams(Retailer):
    name = "Sam's Club"

    def _search(self, kw: str) -> list[Product]:
        r = self.s.get(f"https://www.samsclub.com/s/{quote(kw)}", timeout=25)
        if r.status_code != 200:
            self.warn_once(f"Sam's Club returned HTTP {r.status_code} (bot protection)")
            return []
        m = NEXT.search(r.text)
        if not m:
            return []
        raw: list[dict] = []
        _products(json.loads(m.group(1)), raw)
        out = []
        for p in raw:
            seller = p.get("sellerName")
            third = bool(seller) and "sam" not in seller.lower()
            thumb = (p.get("imageInfo") or {}).get("thumbnailUrl")
            out.append(Product(
                retailer="Sam's Club", sku=str(p["usItemId"]), title=clean_title(p["name"]),
                price=_price((p.get("priceInfo") or {}).get("linePrice")),
                url="https://www.samsclub.com" + p["canonicalUrl"],
                in_stock=(p.get("availabilityStatusV2") or {}).get("value") == "IN_STOCK",
                image=thumb, seller=seller if third else None, third_party=third))
        return out

    def fetch(self):
        out = {}
        for kw in self.cfg.get("sams", {}).get("searches", ["pokemon trading cards"]):
            try:
                for p in self._search(kw):
                    out.setdefault(p.sku, p)
            except Exception as e:
                self.log.warning("search %r failed: %s", kw, e)
        return list(out.values())
