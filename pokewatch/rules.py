import html
import re
from dataclasses import dataclass

from .models import Product


def clean_title(t: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(t or "")).strip()


def _has(text: str, term: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])", text) is not None


def _norm(text: str) -> str:
    return clean_title(text).lower().replace("é", "e")


@dataclass
class Verdict:
    alert: bool
    reason: str
    priority: bool = False
    kind: str = ""
    cap: float | None = None


def price_cap(title: str, cfg: dict) -> tuple[str, float]:
    t = _norm(title)
    for rule in cfg.get("price_caps", []):
        if any(_has(t, m) for m in rule["match"]):
            return rule["name"], float(rule["cap"])
    return "Pokemon TCG product", float(cfg.get("default_cap", 60))


def is_pokemon_tcg(title: str, cfg: dict) -> bool:
    t = _norm(title)
    if "pokemon" not in t:
        return False
    if any(_has(t, x) for x in cfg.get("exclude_terms", [])):
        return False
    return any(_has(t, x) for x in cfg.get("tcg_terms", []))


def is_priority(title: str, cfg: dict) -> bool:
    t = _norm(title)
    return any(_has(t, x) for x in cfg.get("priority_terms", []))


def evaluate(p: Product, cfg: dict) -> Verdict:
    """Decide whether a product is a genuine, in-stock, first-party Pokemon TCG drop."""
    if not is_pokemon_tcg(p.title, cfg):
        return Verdict(False, "not a Pokemon TCG product")
    prio = is_priority(p.title, cfg)
    kind, cap = price_cap(p.title, cfg)
    if not p.in_stock:
        return Verdict(False, "out of stock", prio, kind, cap)
    if p.third_party:
        return Verdict(False, f"third-party seller ({p.seller or 'marketplace'})", prio, kind, cap)
    if p.price is None:
        return Verdict(False, "no price", prio, kind, cap)
    if p.price > cap:
        return Verdict(False, f"scalper price ${p.price:.2f} > cap ${cap:.0f}", prio, kind, cap)
    if not prio and not cfg.get("alert_other_pokemon_tcg", True):
        return Verdict(False, "not a priority set", prio, kind, cap)
    return Verdict(True, "genuine drop", prio, kind, cap)
