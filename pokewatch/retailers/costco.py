from urllib.parse import quote_plus

from .base import Retailer
from .html_common import products_from_jsonld


class Costco(Retailer):
    name = "Costco"

    def fetch(self):
        out = {}
        for term in ["pokemon trading card"] + self.searches():
            url = f"https://www.costco.com/CatalogSearch?dept=All&keyword={quote_plus(term)}"
            try:
                r = self.s.get(url, timeout=20)
            except Exception as e:
                self.warn_once(f"Costco request failed: {e}")
                return []
            if r.status_code != 200:
                self.warn_once(f"Costco returned HTTP {r.status_code} (bot protection) - best effort only")
                return []
            for p in products_from_jsonld("Costco", r.text, url):
                out[p.sku] = p
        return list(out.values())
