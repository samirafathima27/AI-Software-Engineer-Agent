from sample_project.calculator import (
    calculate_total,
    calculate_discount,
    calculate_final_price,
)


def test_calculate_total():
    assert calculate_total(100, 2) == 200


def test_calculate_total_with_float():
    assert calculate_total(19.99, 3) == 59.97


def test_calculate_discount_basic():
    assert calculate_discount(100, 10) == 90


def test_calculate_discount_zero():
    assert calculate_discount(50, 0) == 50


def test_calculate_discount_full():
    assert calculate_discount(200, 100) == 0


def test_calculate_final_price():
    assert calculate_final_price(100, 10) == 90


def test_calculate_final_price_full_discount():
    assert calculate_final_price(200, 100) == 0