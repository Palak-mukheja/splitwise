
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


def test_balances_with_no_expenses():
    expenses = []
    expense_splits = []

    balances = calculate_balances(expenses, expense_splits)

    assert balances == {}
    assert sum(balances.values()) == 0


def test_balances_with_multiple_expenses():
    # Expense 1: User 7 pays Rs. 900
    # Everyone owes Rs. 300
    #
    # Expense 2: User 8 pays Rs. 600
    # Everyone owes Rs. 200

    expenses = [
        SimpleNamespace(paid_by=7, amount_paise=90000),
        SimpleNamespace(paid_by=8, amount_paise=60000),
    ]

    expense_splits = [
        # Expense 1
        SimpleNamespace(user_id=7, share_paise=30000),
        SimpleNamespace(user_id=8, share_paise=30000),
        SimpleNamespace(user_id=9, share_paise=30000),

        # Expense 2
        SimpleNamespace(user_id=7, share_paise=20000),
        SimpleNamespace(user_id=8, share_paise=20000),
        SimpleNamespace(user_id=9, share_paise=20000),
    ]

    balances = calculate_balances(expenses, expense_splits)

    assert balances == {
        7: 40000,
        8: 10000,
        9: -50000,
    }

    assert sum(balances.values()) == 0
