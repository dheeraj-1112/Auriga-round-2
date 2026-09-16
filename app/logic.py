"""
Pure business logic for gift_pool.

No Flask, no database access here — only plain Python functions operating on
plain data structures (ints, dicts, lists). This keeps the money math testable
in isolation and trustworthy.

All money is handled as integer PAISE (1 rupee = 100 paise) to avoid floating
point rounding errors. Conversion to/from rupee strings happens only at the
edges (parsing user input, formatting for display).
"""

from decimal import Decimal, InvalidOperation


class ValidationError(ValueError):
    """Raised when user-supplied input is invalid."""
    pass


# ---------------------------------------------------------------------------
# Money parsing / formatting
# ---------------------------------------------------------------------------

def parse_rupees_to_paise(value):
    """
    Parse a user-supplied rupee amount (string or number) into an integer
    number of paise. Raises ValidationError on anything invalid.

    Accepts: "100", "100.5", "100.50", 100, 100.5
    Rejects: negative amounts, non-numeric strings, more than 2 decimal places,
    empty/whitespace-only input.
    """
    if value is None:
        raise ValidationError("Amount is required.")

    text = str(value).strip()
    if text == "":
        raise ValidationError("Amount is required.")

    try:
        dec = Decimal(text)
    except InvalidOperation:
        raise ValidationError(f"'{value}' is not a valid amount.")

    if dec < 0:
        raise ValidationError("Amount cannot be negative.")

    # Reject more than 2 decimal places (e.g. 100.505) rather than silently
    # rounding, since silent rounding of money is a correctness risk.
    if dec.as_tuple().exponent < -2:
        raise ValidationError("Amount cannot have more than 2 decimal places.")

    paise = int((dec * 100).to_integral_value())
    return paise


def paise_to_rupees_str(paise):
    """Format an integer paise amount as a rupee string, e.g. 150050 -> '1500.50'."""
    rupees = paise // 100
    remainder = abs(paise) % 100
    sign = "-" if paise < 0 else ""
    return f"{sign}{abs(rupees)}.{remainder:02d}"


# ---------------------------------------------------------------------------
# Fair share calculation
# ---------------------------------------------------------------------------

def compute_fair_shares(budget_paise, member_ids):
    """
    Split budget_paise equally among member_ids, distributing any remainder
    (from integer division) one paise at a time to the first N members
    (by the order given) so shares always sum EXACTLY to budget_paise.

    Returns: dict {member_id: share_paise}

    Raises ValidationError if member_ids is empty or budget_paise is negative.
    """
    if budget_paise < 0:
        raise ValidationError("Budget cannot be negative.")
    if not member_ids:
        raise ValidationError("Cannot compute shares with no members.")

    n = len(member_ids)
    base_share = budget_paise // n
    remainder = budget_paise - (base_share * n)  # 0 <= remainder < n

    shares = {}
    for index, member_id in enumerate(member_ids):
        share = base_share + (1 if index < remainder else 0)
        shares[member_id] = share

    assert sum(shares.values()) == budget_paise, "share distribution must sum exactly to budget"
    return shares


# ---------------------------------------------------------------------------
# Member summary (paid, share, balance)
# ---------------------------------------------------------------------------

def compute_member_summaries(budget_paise, members):
    """
    members: list of dicts, each with at least {"id": int, "paid_paise": int}
             (paid_paise is the SUM of that member's contributions; 0 if none)

    Returns a new list of dicts, one per member, each with:
        id, paid_paise, share_paise, balance_paise
    balance_paise = paid_paise - share_paise
        > 0  -> member overpaid (is a creditor / is owed money back)
        < 0  -> member underpaid (is a debtor / still owes money)
        == 0 -> settled

    Also returns pool-level totals as a separate dict:
        total_collected_paise, remaining_paise (budget - collected, can be
        negative if over-collected)
    """
    member_ids = [m["id"] for m in members]
    shares = compute_fair_shares(budget_paise, member_ids) if member_ids else {}

    summaries = []
    total_collected = 0
    for m in members:
        paid = m.get("paid_paise", 0) or 0
        share = shares.get(m["id"], 0)
        balance = paid - share
        total_collected += paid
        summaries.append({
            **m,
            "paid_paise": paid,
            "share_paise": share,
            "balance_paise": balance,
        })

    totals = {
        "total_collected_paise": total_collected,
        "budget_paise": budget_paise,
        "remaining_paise": budget_paise - total_collected,
    }

    return summaries, totals


# ---------------------------------------------------------------------------
# Settlement algorithm
# ---------------------------------------------------------------------------

def compute_settlement(member_balances):
    """
    member_balances: list of dicts {"id": int, "name": str, "balance_paise": int}

    Matches debtors (balance < 0) against creditors (balance > 0) using a
    greedy largest-first strategy: repeatedly match the largest remaining
    debtor with the largest remaining creditor, transferring
    min(debt, credit), until one side is exhausted.

    This produces a VALID settlement (every transaction reflects a real debt
    and a real claim) using few transactions in practice, but this is NOT
    guaranteed to be the mathematically minimum number of transactions —
    finding the true minimum is an NP-hard combinatorial problem. We do not
    claim optimality.

    If the pool is under-collected, total debt > total credit among members,
    so some debt will remain unmatched after all creditors are paid out —
    that leftover is money still owed to the pool overall, not to any single
    member (it equals the pool's overall shortfall).

    If the pool is over-collected, total credit > total debt, so some credit
    remains unmatched — that leftover is a surplus the pool is holding /
    owes back, not owed by any single member.

    Returns:
        {
            "transactions": [{"from_id", "from_name", "to_id", "to_name", "amount_paise"}, ...],
            "unmatched_debt_paise": int,   # >= 0, owed to the pool overall
            "unmatched_credit_paise": int, # >= 0, surplus held by the pool
        }
    """
    debtors = []   # list of [id, name, amount_owed_paise] (positive numbers)
    creditors = []  # list of [id, name, amount_credit_paise] (positive numbers)

    for m in member_balances:
        bal = m["balance_paise"]
        if bal < 0:
            debtors.append([m["id"], m["name"], -bal])
        elif bal > 0:
            creditors.append([m["id"], m["name"], bal])
        # bal == 0 -> already settled, ignored

    # Largest-first ordering keeps the number of transactions small in
    # practice (a standard greedy heuristic), though not proven minimal.
    debtors.sort(key=lambda x: x[2], reverse=True)
    creditors.sort(key=lambda x: x[2], reverse=True)

    transactions = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        d_id, d_name, d_amt = debtors[i]
        c_id, c_name, c_amt = creditors[j]
        transfer = min(d_amt, c_amt)

        if transfer > 0:
            transactions.append({
                "from_id": d_id,
                "from_name": d_name,
                "to_id": c_id,
                "to_name": c_name,
                "amount_paise": transfer,
            })

        debtors[i][2] -= transfer
        creditors[j][2] -= transfer

        if debtors[i][2] == 0:
            i += 1
        if creditors[j][2] == 0:
            j += 1

    unmatched_debt = sum(d[2] for d in debtors[i:])
    unmatched_credit = sum(c[2] for c in creditors[j:])

    return {
        "transactions": transactions,
        "unmatched_debt_paise": unmatched_debt,
        "unmatched_credit_paise": unmatched_credit,
    }
