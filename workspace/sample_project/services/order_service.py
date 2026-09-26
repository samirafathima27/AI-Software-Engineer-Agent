from sample_project.models import Order
from sample_project.pricing import calculate_final_amount


def calculate_order_total(order: Order) -> float:
    return calculate_final_amount(
        price=order.price,
        quantity=order.quantity,
        discount_percent=order.discount_percent,
    )