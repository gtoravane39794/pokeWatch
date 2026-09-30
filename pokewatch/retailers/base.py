import logging
import random

from curl_cffi import requests  # impersonates Chrome's TLS fingerprint; plain requests gets blocked


class Retailer:
    name = "?"

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.log = logging.getLogger(f"pokewatch.{self.name.lower().replace(' ', '')}")
        self.s = requests.Session(impersonate="chrome")
        self._warned = False
        self.notices: list[str] = []

    def warn_once(self, msg: str):
        if not self._warned:
            self.log.warning(msg)
            self._warned = True

    def searches(self) -> list[str]:
        terms = list(self.cfg.get("priority_terms", []))
        return ["pokemon " + t for t in terms]

    def fetch(self) -> list:
        raise NotImplementedError


def visitor_id() -> str:
    return "".join(random.choice("0123456789ABCDEF") for _ in range(32))
