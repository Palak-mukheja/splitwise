
from types import SimpleNamespace

from app.services.split import calculate_balances


def test_calculate_balances():
    expenses = [
        SimpleNamespace(
            paid_by=7,
            amount_paise=90000
        )
    ]

    expense_splits = [
        SimpleNamespace(user_id=7, share_paise=30000),
        SimpleNamespace(user_id=8, share_paise=30000),
        SimpleNamespace(user_id=9, share_paise=30000),
    ]

    balances = calculate_balances(expenses, expense_splits)

    assert balances == {
        7: 60000,
        8: -30000,
        9: -30000,
    }

    assert sum(balances.values()) == 0
