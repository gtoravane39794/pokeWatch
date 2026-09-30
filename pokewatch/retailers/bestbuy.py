import json
from urllib.parse import quote_plus

from ..models import Product
from ..rules import clean_title
from .base import Retailer

MARKER = '{"__typename":"SearchProduct","product":'
DECODER = json.JSONDecoder()


class BestBuy(Retailer):
    name = "Best Buy"

    def _search(self, kw: str) -> list[Product]:
        r = self.s.get(f"https://www.bestbuy.com/site/searchpage.jsp?st={quote_plus(kw)}&intl=nosplash", timeout=25)
        if r.status_code != 200:
            self.warn_once(f"Best Buy returned HTTP {r.status_code} (bot protection)")
            return []
        h, pos, out = r.text, 0, []
        while (i := h.find(MARKER, pos)) >= 0:
            try:
                obj, pos = DECODER.raw_decode(h, i)
                out.append(self._to_product(obj["product"]))
            except (ValueError, KeyError, TypeError):
                pos = i + len(MARKER)
        return out

    def _to_product(self, p: dict) -> Product:
        sku = str(p["skuId"])
        seller = p.get("seller") or {}
        cls = seller.get("classification")
        third = bool(cls) and cls not in ("1P", "BBY")
        states = {b.get("buttonState") for b in (p.get("fulfillmentOptions") or {}).get("buttonStates", [])}
        price = (p.get("price") or {}).get("displayableCustomerPrice")
        return Product(
            retailer="Best Buy", sku=sku,
            title=clean_title(p["name"]["short"]),
            price=float(price) if price is not None else None,
            url=p["url"]["pdp"],
            in_stock="ADD_TO_CART" in states,  # online ship-to-home only; pickup-only ("CHECK_STORES") ignored
            image=(p.get("primaryImage") or {}).get("href"),
            cart_url=f"https://api.bestbuy.com/click/-/{sku}/cart",
            seller="Best Buy Marketplace seller" if third else None,
            third_party=third)

    def fetch(self) -> list[Product]:
        out: dict[str, Product] = {}
        for kw in self.cfg.get("bestbuy", {}).get("searches", ["pokemon trading card game"]):
            try:
                for p in self._search(kw):
                    out.setdefault(p.sku, p)
            except Exception as e:
                self.log.warning("search %r failed: %s", kw, e)
        return list(out.values())
