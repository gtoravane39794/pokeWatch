import json
from pathlib import Path

from pokewatch import config, discord
from pokewatch.main import sweep
from pokewatch.retailers.target import Target

SEARCH = {"data": {"search": {"products": [
    {"tcin": "111", "price": {"current_retail": 49.99}, "item": {
        "product_description": {"title": "Pok&#233;mon TCG Prismatic Evolutions Elite Trainer Box"},
        "enrichment": {"buy_url": "https://www.target.com/p/-/A-111", "image_info": {"primary_image": {"url": "http://img"}}},
        "fulfillment": {}}},
    {"tcin": "222", "price": {"current_retail": 199.99}, "item": {
        "product_description": {"title": "Pokemon Prismatic Evolutions Elite Trainer Box"},
        "product_vendors": [{"vendor_name": "Scalper LLC"}], "fulfillment": {"is_marketplace": True}}},
]}}}
FULFIL = {"data": {"product": {"fulfillment": {"sold_out": False, "shipping_options": {"availability_status": "IN_STOCK"}}}}}


def test_sweep_alerts_only_genuine(monkeypatch):
    cfg = config.load("config.yaml")
    t = Target(cfg)
    monkeypatch.setattr(t, "_get", lambda path, params: SEARCH if "search" in path else FULFIL)
    sent = []
    monkeypatch.setattr(discord, "send", lambda w, payload, dry=False: sent.append(payload) or True)
    state = {}
    assert sweep(cfg, [t], state, first_run=True) == 1
    e = sent[0]["embeds"][0]
    assert "Elite Trainer Box" in e["title"] and e["thumbnail"]["url"] == "http://img"
    assert sweep(cfg, [t], state) == 0  # deduped
