from pokewatch.config import load
from pokewatch.models import Product
from pokewatch.rules import evaluate


def cfg():
    return load("config.yaml")


def P(title, price, stock=True, third=False):
    return Product("Target", "1", title, price, "http://x", stock, third_party=third)


def test_genuine_etb():
    assert evaluate(P("Pokemon TCG Prismatic Evolutions Elite Trainer Box", 49.99), cfg()).alert


def test_scalper_price_blocked():
    v = evaluate(P("Pokemon TCG Prismatic Evolutions Elite Trainer Box", 199.99), cfg())
    assert not v.alert and "scalper" in v.reason


def test_third_party_blocked():
    assert not evaluate(P("Pokemon Prismatic Evolutions Elite Trainer Box", 49.99, third=True), cfg()).alert


def test_oos_and_accessories():
    assert not evaluate(P("Pokemon Prismatic Evolutions Elite Trainer Box", 49.99, stock=False), cfg()).alert
    assert not evaluate(P("Pokemon Plush Booster Box toy", 20), cfg()).alert
    assert not evaluate(P("Ultra Pro Pokemon Card Sleeves", 10), cfg()).alert


def test_30th_battle_deck_priority():
    v = evaluate(P("Pokemon Trading Card Game: 30th Celebration Battle Deck", 24.99), cfg())
    assert v.alert and v.priority


def test_word_boundary_tin():
    # "Destined" contains "tin" but must not be treated as a Tin (cap 35)
    v = evaluate(P("Pokemon Destined Rivals Elite Trainer Box", 60), cfg())
    assert v.alert and v.kind == "Elite Trainer Box"


def test_books_and_video_games_rejected():
    for title in ["Pokémon Epic Sticker Collection 3rd Edition, Paperback", "Pokémon Storybook Collection, Hardcover",
                  "Pokemon Half Sheet Cookie Cake", "Pokémon Legends: Z-A - Nintendo Switch 2 Edition"]:
        assert not evaluate(P(title, 12), cfg()).alert, title


def test_real_products_accepted():
    for title in ["Pokémon TCG: Prismatic Evolutions Booster Bundle", "Pokemon Trading Card Game 30th Celebration Knock Out Collection",
                  "Pokémon Trading Card Game: Mega Evolution Booster Box"]:
        assert evaluate(P(title, 25 if "Bundle" in title else 50), cfg()).kind, title
