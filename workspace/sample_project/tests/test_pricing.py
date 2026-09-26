from sample_project.pricing import (
    calculate_subtotal,
    calculate_final_amount,
)


def test_calculate_subtotal():
    assert calculate_subtotal(100, 3) == 300


def test_calculate_final_amount_without_discount():
    assert calculate_final_amount(
        100,
        3,
        0,
    ) == 315.0


def test_calculate_final_amount_with_discount():
    assert calculate_final_amount(
        100,
        2,
        10,
    ) == 189.0


def test_calculate_final_amount_full_discount():
    assert calculate_final_amount(
        200,
        2,
        100,
    ) == 0


def test_calculate_final_amount_service_fee_with_discount():
    assert calculate_final_amount(
        100,
        1,
        50,
    ) == 52.5