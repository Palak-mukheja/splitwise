
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
