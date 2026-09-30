from dataclasses import dataclass, field


@dataclass
class Product:
    retailer: str
    sku: str
    title: str
    price: float | None
    url: str
    in_stock: bool
    image: str | None = None
    cart_url: str | None = None
    seller: str | None = None
    third_party: bool = False
    extra: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.retailer}:{self.sku}"
