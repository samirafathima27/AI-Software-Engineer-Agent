from dataclasses import dataclass


@dataclass
class Order:
    price: float
    quantity: int
    discount_percent: float = 0.0