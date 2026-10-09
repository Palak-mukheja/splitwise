
import pytest

from app.services.split import calculate_equal_split


def test_equal_split_without_remainder():
    result = calculate_equal_split(100, [7, 8])

    assert result == [(7, 50), (8, 50)]


def test_equal_split_with_remainder():
    result = calculate_equal_split(100, [7, 8, 9])

    assert result == [(7, 34), (8, 33), (9, 33)]


def test_splits_always_add_up_to_total():
    result = calculate_equal_split(250, [7, 8, 9, 10])

    assert sum(share for _, share in result) == 250


def test_empty_members_are_rejected():
    with pytest.raises(ValueError):
        calculate_equal_split(100, [])


def test_non_positive_amount_is_rejected():
    with pytest.raises(ValueError):
        calculate_equal_split(0, [7, 8])

    with pytest.raises(ValueError):
        calculate_equal_split(-100, [7, 8])


def test_duplicate_members_are_rejected():
    with pytest.raises(ValueError):
        calculate_equal_split(100, [7, 7, 8])
