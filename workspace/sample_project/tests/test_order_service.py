from sample_project.models import Order
from sample_project.services.order_service import calculate_order_total


def test_calculate_order_total():
    order = Order(
        price=100,
        quantity=2,
        discount_percent=10,
    )

    assert calculate_order_total(order) == 189.0


def test_calculate_order_total_without_discount():
    order = Order(
        price=50,
        quantity=3,
    )

    assert calculate_order_total(order) == 157.5


def test_calculate_order_total_full_discount():
    order = Order(
        price=200,
        quantity=2,
        discount_percent=100,
    )

    assert calculate_order_total(order) == 0


def test_calculate_order_total_service_fee_applied():
    order = Order(
        price=100,
        quantity=1,
        discount_percent=0,
    )

    assert calculate_order_total(order) == 105.0


def test_calculate_order_total_service_fee_with_discount():
    order = Order(
        price=100,
        quantity=1,
        discount_percent=50,
    )

    assert calculate_order_total(order) == 52.5