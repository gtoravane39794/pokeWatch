# PokeWatch

A local watcher that tracks **Pokemon Trading Card Game** drops at online retailers and posts a rich
alert (product image, price, links) to a **Discord channel** through a webhook. It runs in Docker on your machine.

Focus sets: **Prismatic Evolutions** and **30th Celebration** (edit `priority_terms` in `config.yaml`).
Other sealed Pokemon TCG products alert too, unless you set `alert_other_pokemon_tcg: false`.

## Quick start (5 minutes)

1. **Create the Discord webhook**: channel settings -> Integrations -> Webhooks -> New Webhook -> Copy URL.
2. `cp .env.example .env` and paste the URL into `DISCORD_WEBHOOK_URL=`. Optionally set:
   - `DISCORD_MENTION=@everyone` (or `<@your_user_id>`) so your phone buzzes.
3. Test the webhook:
   ```bash
   docker compose run --rm pokewatch python -m pokewatch --test-discord   # plain message
   docker compose run --rm pokewatch python -m pokewatch --demo           # sample drop embed with image
   ```
4. Start it (auto-restarts, survives reboots while Docker runs):
   ```bash
   docker compose up -d --build
   docker compose logs -f pokewatch
   ```
   Stop with `docker compose down`.

No Docker? `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && set -a && . ./.env && set +a && .venv/bin/python -m pokewatch`

CLI flags: `--once` (single sweep), `--dry-run` (log alerts, don't post), `--test-discord`, `--demo`, `--config PATH`.

## Target setup (important): a real Chrome window

Target blocks scripts and headless browsers, but accepts a normal Chrome. So PokeWatch reads Target *through a real Chrome window*:

1. Run `./scripts/start-chrome.sh` (opens a separate Chrome profile with a debug port). **Leave that window open** (minimizing is fine).
2. `.env` needs `TARGET_CDP_URL=http://host.docker.internal:9222` for Docker (or `http://127.0.0.1:9222` when running natively).
3. If Target ever shows a "Press & hold" check in that window, complete it yourself once.

If the window is closed you get a Discord message telling you so. Without `TARGET_CDP_URL` it falls back to direct requests, which Target may block.

## What an alert looks like

Embed with the product image, title, **Store**, **Current price**, **Normal range** (e.g. "Elite Trainer Box: up to $75"),
**Sold by**, and links. Priority sets (Prismatic Evolutions / 30th Celebration) get a gold "PRIORITY DROP" embed,
everything else green.

## Scalper protection (important)

An alert only fires when ALL are true:

1. Title is a sealed Pokemon TCG product (not plush, sleeves, singles, graded cards, etc. - see `exclude_terms`).
2. It is **in stock**.
3. It is sold by the **retailer itself** - third-party/marketplace sellers (Target Plus, Best Buy Marketplace...) are dropped.
4. Price is **at or under the cap** for its type (`price_caps` in `config.yaml`): ETB $75, booster bundle $40,
   booster box $190, tin $35, blister/pack $20, battle deck $35, collection box $65, default $60. Tune as you like.

Filtered items are logged at `LOG_LEVEL=DEBUG` (e.g. "scalper price $199.99 > cap $75") but never posted.
Real example: searching Target for Prismatic Evolutions currently returns ETBs from marketplace sellers at $199.99 - those are ignored.

## Retailer support (be realistic)

| Retailer | Method | Status |
|---|---|---|
| **Target** | Target's public web API (search + per-item stock, marketplace flag) | Works when not rate-limited. Sold-by/marketplace detection is reliable. Aggressive polling triggers Target's bot protection (HTTP 435); the watcher backs off automatically. |
| **Best Buy** | bestbuy.com search page data (no API key), seller flag (`3P` = marketplace), online add-to-cart state | Works. Ships-to-home only (pickup-only ignored). Gives a real **add-to-cart link**. |
| **Costco** | HTML search page | **Limited.** Costco renders results client-side, so nothing is parsed yet; it rarely lists Pokemon online anyway. |
| **Sam's Club** | search page embedded data, seller + stock state | Works (only Pokemon TCG matches alert; marketplace sellers filtered). |

**Add-to-cart links**: Best Buy provides a true add-to-cart URL. Target, Costco and Sam's have no public deep link
for carts, so the alert links straight to the product page (one tap from "Add to cart"). Being logged in with saved
payment on the retailer app/site is the biggest speed-up.

## Tuning

- `poll_seconds` (default 45, env `POLL_SECONDS`): faster = more chance of getting blocked. Do not go below ~30.
- `target.searches`: Target search terms per sweep. Keep it short.
- `notify_on_first_run: true`: alerts for items already in stock when you start (handy to prove it works).
- State lives in `./data/state.json`; delete it to re-alert on everything currently in stock. An item re-alerts
  after it goes out of stock and comes back.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest && .venv/bin/pytest -q
```
Layout: `pokewatch/rules.py` (scalper/price logic), `pokewatch/retailers/*` (one class per store),
`pokewatch/discord.py` (embeds), `pokewatch/main.py` (loop, dedupe state). See `AGENTS.md`.

## Limitations

- It notifies; it does **not** auto-checkout (and shouldn't - bots violate retailer terms and lose to humans on speed anyway).
- Target stock is checked for online shipping (no store/location needed). In-store-only stock isn't tracked.
- Retailer endpoints are unofficial (except Best Buy) and can change; check the logs if a store goes silent.
