from decimal import Decimal
import heapq
def calculate_equal_split(total_paise, member_ids):
    if total_paise <= 0:
        raise ValueError("Expense amount must be positive")

    if not member_ids:
        raise ValueError("At least one member is required")

    if len(set(member_ids)) != len(member_ids):
        raise ValueError("Member IDs must be unique")

    number_of_members = len(member_ids)

    base_share = total_paise // number_of_members
    remainder = total_paise % number_of_members

    splits = []

    for index, member_id in enumerate(member_ids):
        if index < remainder:
            share = base_share + 1
        else:
            share = base_share

        splits.append((member_id, share))

    return splits


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

    total_shares = sum(
        split.share_paise for split in splits
    )

    if total_shares != total_paise:
        raise ValueError(
            "Split amounts must equal the total expense"
        )

    return [
        (split.user_id, split.share_paise)
        for split in splits
    ]


def calculate_percentage_split(total_paise, splits):
    if total_paise <= 0:
        raise ValueError("Total expense must be positive")

    if not splits:
        raise ValueError("At least one split is required")

    user_ids = [split.user_id for split in splits]

    if len(user_ids) != len(set(user_ids)):
        raise ValueError("Duplicate users are not allowed")

    percentages = [split.percentage for split in splits]

    if any(p < 0 or p > 100 for p in percentages):
        raise ValueError("Percentages must be between 0 and 100")

    if sum(percentages, Decimal("0")) != Decimal("100"):
        raise ValueError("Percentages must add up to 100")

    # Calculate each exact share in paise.
    exact_shares = [
        Decimal(total_paise) * percentage / Decimal("100")
        for percentage in percentages
    ]

    # Initially assign only whole paise.
    whole_shares = [
        int(share) for share in exact_shares
    ]

    # How many paise remain undistributed?
    remaining = total_paise - sum(whole_shares)

    # Rank fractional remainders, largest first.
    order = sorted(
        range(len(splits)),
        key=lambda i: exact_shares[i] - whole_shares[i],
        reverse=True
    )

    # Give each remaining paisa to the next highest remainder.
    for i in order[:remaining]:
        whole_shares[i] += 1

    return [
        (split.user_id, whole_shares[i])
        for i, split in enumerate(splits)
    ]


def calculate_balances(expenses):
    """
    Calculate each user's net balance from a list of expenses.

    Each expense must have:
    - paid_by
    - amount_paise
    - splits: a list of objects with user_id and share_paise

    Positive balance = user should receive money.
    Negative balance = user owes money.
    """
    balances = {}

    for expense in expenses:
        # The person who paid gets credited.
        payer_id = expense.paid_by
        balances[payer_id] = (
            balances.get(payer_id, 0) + expense.amount_paise
        )

        # Each person's share is deducted from their balance.
        for split in expense.splits:
            user_id = split.user_id
            balances[user_id] = (
                balances.get(user_id, 0) - split.share_paise
            )

    return balances


def calculate_balances(expenses, expense_splits):
    """
    Calculate each user's net balance.

    Positive balance = user should receive money.
    Negative balance = user owes money.
    """

    balances = {}

    # Credit each payer with the amount they paid.
    for expense in expenses:
        balances[expense.paid_by] = (
            balances.get(expense.paid_by, 0)
            + expense.amount_paise
        )

    # Deduct each user's share from their balance.
    for split in expense_splits:
        balances[split.user_id] = (
            balances.get(split.user_id, 0)
            - split.share_paise
        )

    return balances


def suggest_settlements(balances):
    """
    Convert net balances into settlement transactions.

    Positive balance = should receive money.
    Negative balance = owes money.

    Returns tuples: (payer_id, receiver_id, amount_paise).
    """
    debtors = []
    creditors = []

    for user_id, balance in balances.items():
        if balance < 0:
            heapq.heappush(debtors, (balance, user_id))
        elif balance > 0:
            heapq.heappush(creditors, (-balance, user_id))

    settlements = []

    while debtors and creditors:
        debt, debtor_id = heapq.heappop(debtors)
        credit, creditor_id = heapq.heappop(creditors)

        debt = -debt
        credit = -credit

        amount = min(debt, credit)

        settlements.append(
            (debtor_id, creditor_id, amount)
        )

        debt -= amount
        credit -= amount

        if debt > 0:
            heapq.heappush(debtors, (-debt, debtor_id))

        if credit > 0:
            heapq.heappush(creditors, (-credit, creditor_id))

    return settlements
