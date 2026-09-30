import json
import os
import random
import socket
import time
from urllib.parse import quote_plus, urlencode, urlparse

from ..models import Product
from ..rules import clean_title, is_pokemon_tcg
from .base import Retailer, visitor_id

KEY = "9f36aeafbe60771e321a7cc95a78140772ab3e96"  # public key used by target.com web client
BASE = "https://redsky.target.com/redsky_aggregations/v1/web"
# Target requires some physical store id in the API call; results used are shipping-only, so it is location-independent.
REF_STORE, REF_ZIP, REF_STATE = "1375", "55403", "MN"
IN_STOCK = {"IN_STOCK", "LIMITED_STOCK", "PRE_ORDER_SELLABLE"}


class Target(Retailer):
    name = "Target"

    def __init__(self, cfg):
        super().__init__(cfg)
        self.t = cfg["target"]
        self.vid = visitor_id()
        self.blocked_until = 0.0
        self.fail_streak = 0
        self.cdp_url = os.getenv("TARGET_CDP_URL", "").strip()
        self._pw = self._page = None
        self._cdp_warned = False

    def _browser_page(self):
        """Attach to the user's own Chrome (started with --remote-debugging-port) and reuse a target.com tab."""
        if self._page is not None and not self._page.is_closed():
            return self._page
        from playwright.sync_api import sync_playwright
        u = urlparse(self.cdp_url)
        host = socket.gethostbyname(u.hostname)  # Chrome's debug port rejects non-IP Host headers
        if self._pw is None:
            self._pw = sync_playwright().start()
        browser = self._pw.chromium.connect_over_cdp(f"{u.scheme}://{host}:{u.port}")
        ctx = browser.contexts[0]
        page = next((p for p in ctx.pages if "target.com" in p.url), None) or ctx.new_page()
        if "target.com" not in page.url:
            page.goto("https://www.target.com/", wait_until="domcontentloaded", timeout=45000)
        self._page = page
        return page

    def _browser_get(self, path: str, params: dict):
        url = f"{BASE}/{path}?{urlencode(params)}"
        try:
            page = self._browser_page()
            res = page.evaluate(
                "async u => { const r = await fetch(u, {credentials: 'include'}); return {s: r.status, t: await r.text()}; }", url)
        except Exception as e:
            self._page = None
            if not self._cdp_warned:
                self._cdp_warned = True
                self.notices.append("Can't reach the Chrome window Target needs (%s). Run scripts/start-chrome.sh and keep that "
                                    "Chrome window open." % str(e)[:120])
            self.log.warning("browser fetch failed: %s", e)
            raise RuntimeError("browser")
        if self._cdp_warned:
            self._cdp_warned = False
            self.notices.append("Chrome window reconnected; Target is being watched again.")
        return res["s"], res["t"]

    def _get(self, path: str, params: dict):
        time.sleep(random.uniform(0.3, 1.0))
        if self.cdp_url:
            status, text = self._browser_get(path, params)
        else:
            r = self.s.get(f"{BASE}/{path}", params=params, timeout=15)
            status, text = r.status_code, r.text
        if status in (403, 429, 435) or "px-captcha" in text[:600]:
            if self.fail_streak == 0:
                self.notices.append("Target is blocking this network (HTTP %s / 'press & hold' check), so Target is NOT being "
                                    "watched right now. Open target.com in your normal browser, complete any verification, "
                                    "and it should recover on its own. I'll post again when it does." % status)
            self.fail_streak += 1
            wait = min(600, 30 * 2 ** self.fail_streak)
            self.blocked_until = time.time() + wait
            self.log.warning("Target bot-protection HTTP %s - backing off %ss (raise POLL_SECONDS if this repeats)",
                             status, wait)
            raise RuntimeError("blocked")
        if status >= 400:
            raise RuntimeError(f"HTTP {status}")
        if self.fail_streak:
            self.notices.append("Target is reachable again and being watched.")
        self.fail_streak = 0
        return json.loads(text)

    def _search(self, kw: str) -> list[dict]:
        d = self._get("plp_search_v2", {
            "key": KEY, "channel": "WEB", "count": 24, "offset": 0, "keyword": kw,
            "page": "/s/" + quote_plus(kw), "platform": "desktop",
            "pricing_store_id": 3991, "visitor_id": self.vid})
        return d["data"]["search"]["products"]

    def _in_stock(self, tcin: str) -> bool:
        sid = REF_STORE
        d = self._get("product_fulfillment_v1", {
            "key": KEY, "is_bot": "false", "tcin": tcin, "store_id": sid,
            "zip": REF_ZIP, "state": REF_STATE, "latitude": 44.97, "longitude": -93.27,
            "scheduled_delivery_store_id": sid, "required_store_id": sid,
            "has_required_store_id": "true", "channel": "WEB",
            "page": f"/p/A-{tcin}", "visitor_id": self.vid})
        f = d["data"]["product"]["fulfillment"]
        if f.get("sold_out"):
            return False
        if f.get("shipping_options", {}).get("availability_status") in IN_STOCK:
            return True
        return False

    def _to_product(self, raw: dict) -> Product:
        item, price = raw["item"], raw.get("price", {})
        tcin = raw["tcin"]
        vendors = item.get("product_vendors") or []
        marketplace = bool(item.get("fulfillment", {}).get("is_marketplace"))
        img = item.get("enrichment", {}).get("image_info", {}).get("primary_image", {}).get("url")
        url = item.get("enrichment", {}).get("buy_url") or f"https://www.target.com/p/-/A-{tcin}"
        return Product(
            retailer="Target", sku=tcin,
            title=clean_title(item["product_description"]["title"]),
            price=price.get("current_retail") or price.get("reg_retail"),
            url=url, in_stock=False, image=img,
            # Target has no public add-to-cart deep link; product page is one tap from cart.
            cart_url=None,
            seller=(vendors[0]["vendor_name"] if marketplace and vendors else None),
            third_party=marketplace)

    def fetch(self) -> list[Product]:
        if time.time() < self.blocked_until:
            return []
        raws: dict[str, dict] = {}
        for kw in self.t.get("searches", []):
            for raw in self._safe_search(kw):
                raws.setdefault(raw["tcin"], raw)
            if time.time() < self.blocked_until:
                return []
        products = []
        for raw in raws.values():
            p = self._to_product(raw)
            if is_pokemon_tcg(p.title, self.cfg):
                products.append(p)
        # Stock lookups only for first-party items (marketplace never alerts anyway).
        first_party = [p for p in products if not p.third_party]
        for p in first_party:
            p.in_stock = self._safe_stock(p.sku)
        for p in products:
            if p.third_party:
                p.in_stock = True  # marketplace listings are "buyable" but filtered as third-party
        return products

    def _safe_search(self, kw):
        try:
            return self._search(kw)
        except Exception as e:
            if str(e) not in ("blocked", "browser"):
                self.log.warning("search %r failed: %s", kw, e)
            return []

    def _safe_stock(self, tcin):
        try:
            return self._in_stock(tcin)
        except Exception as e:
            if str(e) not in ("blocked", "browser"):
                self.log.warning("stock check %s failed: %s", tcin, e)
            return False
