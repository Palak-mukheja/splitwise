
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


def calculate_exact_split(total_paise, splits):
    if total_paise <= 0:
        raise ValueError("Total expense must be positive")

    if not splits:
        raise ValueError("At least one split is required")

    user_ids = [split.user_id for split in splits]

    if len(user_ids) != len(set(user_ids)):
        raise ValueError("Duplicate users are not allowed")

    for split in splits:
        if split.share_paise < 0:
            raise ValueError("Share amounts cannot be negative")

    total_shares = sum(split.share_paise for split in splits)

    if total_shares != total_paise:
        raise ValueError("Split amounts must equal the total expense")

    return [
        (split.user_id, split.share_paise)
        for split in splits
    ]


import pytest
from app.schemas import ExactSplitItem
from app.services.split import calculate_exact_split


def test_exact_split_valid():
    splits = [
        ExactSplitItem(user_id=7, share_paise=40000),
        ExactSplitItem(user_id=8, share_paise=30000),
        ExactSplitItem(user_id=9, share_paise=20000),
    ]

    result = calculate_exact_split(90000, splits)

    assert result == [
        (7, 40000),
        (8, 30000),
        (9, 20000),
    ]


def test_exact_split_wrong_total():
    splits = [
        ExactSplitItem(user_id=7, share_paise=40000),
        ExactSplitItem(user_id=8, share_paise=30000),
    ]

    with pytest.raises(ValueError):
        calculate_exact_split(90000, splits)


def test_exact_split_duplicate_users():
    splits = [
        ExactSplitItem(user_id=7, share_paise=40000),
        ExactSplitItem(user_id=7, share_paise=50000),
    ]

    with pytest.raises(ValueError):
        calculate_exact_split(90000, splits)


from decimal import Decimal
from app.schemas import PercentageSplitItem
from app.services.split import calculate_percentage_split


def test_percentage_split_valid():
    splits = [
        PercentageSplitItem(user_id=7, percentage=Decimal("50")),
        PercentageSplitItem(user_id=8, percentage=Decimal("30")),
        PercentageSplitItem(user_id=9, percentage=Decimal("20")),
    ]

    result = calculate_percentage_split(90000, splits)

    assert result == [
        (7, 45000),
        (8, 27000),
        (9, 18000),
    ]


def test_percentage_split_wrong_total():
    splits = [
        PercentageSplitItem(user_id=7, percentage=Decimal("50")),
        PercentageSplitItem(user_id=8, percentage=Decimal("30")),
    ]

    with pytest.raises(ValueError):
        calculate_percentage_split(90000, splits)


def test_percentage_split_remainder():
    splits = [
        PercentageSplitItem(user_id=7, percentage=Decimal("33.33")),
        PercentageSplitItem(user_id=8, percentage=Decimal("33.33")),
        PercentageSplitItem(user_id=9, percentage=Decimal("33.34")),
    ]

    result = calculate_percentage_split(1, splits)

    assert sum(share for _, share in result) == 1

