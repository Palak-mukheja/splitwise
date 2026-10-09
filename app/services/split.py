
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
