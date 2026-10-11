
from app.services.split import suggest_settlements


def test_suggest_settlements():
    balances = {
        7: 60000,
        8: -40000,
        9: -20000,
    }

    result = suggest_settlements(balances)

    assert result == [
        (8, 7, 40000),
        (9, 7, 20000),
    ]


def test_no_settlements_when_balanced():
    balances = {
        7: 0,
        8: 0,
    }

    assert suggest_settlements(balances) == []


def test_multiple_debtors_and_creditors():
    balances = {
        1: 5000,    # should receive Rs. 50
        2: 7000,    # should receive Rs. 70
        3: -4000,   # owes Rs. 40
        4: -8000,   # owes Rs. 80
    }

    settlements = suggest_settlements(balances)

    # Every settlement must be positive.
    assert all(amount > 0 for _, _, amount in settlements)

    # Calculate how much each person pays or receives.
    net = {user_id: 0 for user_id in balances}

    for payer_id, receiver_id, amount in settlements:
        net[payer_id] -= amount
        net[receiver_id] += amount

    # The suggested transfers must exactly settle the original balances.
    assert net == balances


def test_circular_debts():
    balances = {
        1: 0,
        2: 0,
        3: 0,
    }

    settlements = suggest_settlements(balances)

    assert settlements == []


def test_everyone_already_settled():
    balances = {
        1: 0,
        2: 0,
        3: 0,
    }

    settlements = suggest_settlements(balances)

    assert settlements == []


def test_suggested_settlements_clear_balances():
    balances = {
        1: 5000,
        2: 7000,
        3: -4000,
        4: -8000,
    }

    settlements = suggest_settlements(balances)

    remaining = balances.copy()

    for payer_id, receiver_id, amount in settlements:
        remaining[payer_id] += amount
        remaining[receiver_id] -= amount

    assert all(balance == 0 for balance in remaining.values())
