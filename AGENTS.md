# AGENTS.md

Guidance for AI agents / contributors working on PokeWatch.

## Purpose
Poll retailers for Pokemon TCG drops and post a Discord embed for **genuine** (first-party, in-stock, at/below
retail cap) items only. Scalper protection is the core requirement - never weaken it silently.

## Layout
- `pokewatch/main.py` - CLI + loop. `sweep()` fetches, evaluates, dedupes via `data/state.json`, posts.
- `pokewatch/rules.py` - `evaluate(product, cfg) -> Verdict` (TCG match, exclusions, third-party, price cap, priority). Word-boundary matching (`_has`) so "Destined" != "tin".
- `pokewatch/retailers/` - one `Retailer` subclass per store with `fetch() -> list[Product]`. Set `third_party=True` for marketplace listings and `in_stock` accurately. Add new stores to `retailers/__init__.py:ALL` and `config.yaml: retailers`.
- `pokewatch/discord.py` - webhook posting (429 retry), embed builder.
- `config.yaml` - priority terms, exclusions, per-type `price_caps`, retailer toggles. Env vars (`.env`) hold secrets/overrides.

## Rules of the road
- Run `.venv/bin/pytest -q` before finishing. Add a test in `tests/test_rules.py` for any rule change.
- Target endpoints (`redsky.target.com`) sit behind PerimeterX: keep requests sequential, jittered, few, with backoff on 403/429/435. Do not add parallel bursts - that got the dev IP flagged.
- Never commit `.env` or `data/`. Never log the webhook URL.
- No auto-checkout / captcha bypass / login automation. Notification only.
- All retailers use `curl_cffi` (Chrome TLS impersonation) via `Retailer.s`; plain `requests` gets dropped by Best Buy/Target. Costco is not parsed (client-rendered); don't claim it works without verifying live.
- Keep alerts deduped: alert on out->in stock transition; `state.pop` on not-alertable so restocks re-alert.

- Target: prefer `TARGET_CDP_URL` mode (fetch() inside the user's real Chrome via CDP). Headless/curl clients get PerimeterX 435. Never automate the captcha.

## Ideas / TODO
Walmart, GameStop, Pokemon Center, Amazon (first-party only); direct-TCIN watching for Target; restock-pattern
timing; per-store price caps; headless-browser fetch for Costco/Sam's.
