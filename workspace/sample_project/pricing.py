from sample_project.calculator import calculate_discount


def calculate_subtotal(price: float, quantity: int) -> float:
    return price * quantity


def calculate_final_amount(
    price: float,
    quantity: int,
    discount_percent: float = 0.0,
) -> float:
    subtotal = calculate_subtotal(
        price,
        quantity,
    )

    return calculate_discount(
        subtotal,
        discount_percent,
    ) * 1.05