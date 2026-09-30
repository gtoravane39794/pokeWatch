import argparse
import json
import logging
import os
import random
import signal
import sys
import time
from pathlib import Path

from . import config as config_mod
from . import discord
from .models import Product
from .retailers import ALL
from .rules import evaluate

log = logging.getLogger("pokewatch")
STOP = False


def load_state(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}


def save_state(path, state):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(path).with_suffix(".tmp")
    tmp.write_text(json.dumps(state))
    tmp.replace(path)


def sweep(cfg, retailers, state, dry_run=False, first_run=False) -> int:
    alerts = 0
    for r in retailers:
        try:
            products: list[Product] = r.fetch()
        except Exception as e:
            log.warning("%s sweep failed: %s", r.name, e)
            continue
        for note in r.notices:
            discord.send(cfg["discord_webhook"], discord.text_payload(f"[{r.name}] {note}"), dry_run)
        r.notices.clear()
        log.info("%s: %d listings seen", r.name, len(products))
        for p in products:
            v = evaluate(p, cfg)
            prev = state.get(p.key, {})
            if v.alert:
                fresh = not prev.get("alerted")
                if fresh and (not first_run or cfg.get("notify_on_first_run", True)):
                    log.info("DROP %s | %s | $%s", p.retailer, p.title, p.price)
                    if discord.send(cfg["discord_webhook"], discord.drop_payload(p, v, cfg["discord_mention"]), dry_run):
                        alerts += 1
                        state[p.key] = {"alerted": True, "t": time.time()}
                else:
                    state[p.key] = {"alerted": True, "t": prev.get("t", time.time())}
            else:
                if p.in_stock and p.third_party or (v.reason.startswith("scalper")):
                    log.debug("skip %s: %s (%s)", p.title[:60], v.reason, p.price)
                # reset so a future restock alerts again
                state.pop(p.key, None)
    return alerts


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pokewatch")
    ap.add_argument("--once", action="store_true", help="single sweep then exit")
    ap.add_argument("--dry-run", action="store_true", help="log alerts instead of posting")
    ap.add_argument("--test-discord", action="store_true", help="post a test message and exit")
    ap.add_argument("--demo", action="store_true", help="post a sample drop embed and exit")
    ap.add_argument("--config", default=None)
    a = ap.parse_args(argv)

    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = config_mod.load(a.config)

    if a.test_discord:
        ok = discord.send(cfg["discord_webhook"], discord.text_payload("PokeWatch is connected and watching."))
        print("OK" if ok else "FAILED")
        return 0 if ok else 1
    if a.demo:
        from .rules import evaluate as ev
        p = Product("Target", "0", "Pokemon TCG Prismatic Evolutions Elite Trainer Box (DEMO)", 49.99,
                    "https://www.target.com", True,
                    image="https://target.scene7.com/is/image/Target/GUEST_d3dadfe5-ae38-4db2-ae2d-d381a7b0cb2d")
        ok = discord.send(cfg["discord_webhook"], discord.drop_payload(p, ev(p, cfg), cfg["discord_mention"]))
        return 0 if ok else 1

    if not cfg["discord_webhook"] and not a.dry_run:
        log.error("DISCORD_WEBHOOK_URL is not set (see .env.example). Use --dry-run to test without it.")
        return 2

    retailers = [ALL[n](cfg) for n, c in cfg.get("retailers", {}).items() if c.get("enabled") and n in ALL]
    log.info("Watching: %s | every ~%ss", ", ".join(r.name for r in retailers), cfg["poll_seconds"])
    state = load_state(cfg["state_path"])
    signal.signal(signal.SIGTERM, lambda *_: globals().__setitem__("STOP", True))

    first = not state
    while not STOP:
        started = time.time()
        sweep(cfg, retailers, state, a.dry_run, first_run=first)
        first = False
        save_state(cfg["state_path"], state)
        if a.once:
            break
        time.sleep(max(1.0, cfg["poll_seconds"] - (time.time() - started) + random.uniform(0, 3)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
