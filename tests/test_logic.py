import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.logic import (
    parse_rupees_to_paise,
    paise_to_rupees_str,
    compute_fair_shares,
    compute_member_summaries,
    compute_settlement,
    ValidationError,
)


# ---------------------------------------------------------------------------
# Money parsing
# ---------------------------------------------------------------------------

def test_parse_rupees_basic():
    assert parse_rupees_to_paise("100") == 10000
    assert parse_rupees_to_paise("100.5") == 10050
    assert parse_rupees_to_paise("100.50") == 10050
    assert parse_rupees_to_paise("0") == 0
    assert parse_rupees_to_paise(0) == 0


def test_parse_rupees_rejects_negative():
    with pytest.raises(ValidationError):
        parse_rupees_to_paise("-5")


def test_parse_rupees_rejects_non_numeric():
    with pytest.raises(ValidationError):
        parse_rupees_to_paise("abc")


def test_parse_rupees_rejects_empty():
    with pytest.raises(ValidationError):
        parse_rupees_to_paise("")
    with pytest.raises(ValidationError):
        parse_rupees_to_paise(None)


def test_parse_rupees_rejects_too_many_decimals():
    with pytest.raises(ValidationError):
        parse_rupees_to_paise("100.505")


def test_paise_to_rupees_str():
    assert paise_to_rupees_str(10050) == "100.50"
    assert paise_to_rupees_str(0) == "0.00"
    assert paise_to_rupees_str(-500) == "-5.00"


# ---------------------------------------------------------------------------
# Fair share calculation
# ---------------------------------------------------------------------------

def test_equal_split_no_remainder():
    shares = compute_fair_shares(600000, [1, 2, 3])  # 6000 / 3 = 2000 each
    assert shares == {1: 200000, 2: 200000, 3: 200000}
    assert sum(shares.values()) == 600000


def test_uneven_split_distributes_remainder_exactly():
    # 6000 / 7 members = 857.142857... -> must still sum exactly to 600000
    shares = compute_fair_shares(600000, list(range(1, 8)))
    assert sum(shares.values()) == 600000
    # remainder distributed 1 paise at a time to first N members
    values = list(shares.values())
    assert max(values) - min(values) <= 1


def test_single_member_gets_full_budget():
    shares = compute_fair_shares(600000, [1])
    assert shares == {1: 600000}


def test_zero_members_raises():
    with pytest.raises(ValidationError):
        compute_fair_shares(600000, [])


def test_negative_budget_raises():
    with pytest.raises(ValidationError):
        compute_fair_shares(-100, [1, 2])


def test_zero_budget_all_shares_zero():
    shares = compute_fair_shares(0, [1, 2, 3])
    assert shares == {1: 0, 2: 0, 3: 0}


# ---------------------------------------------------------------------------
# Member summaries (paid / share / balance / totals)
# ---------------------------------------------------------------------------

def test_member_summaries_full_contributions():
    members = [
        {"id": 1, "paid_paise": 200000},
        {"id": 2, "paid_paise": 200000},
        {"id": 3, "paid_paise": 200000},
    ]
    summaries, totals = compute_member_summaries(600000, members)
    for s in summaries:
        assert s["balance_paise"] == 0
    assert totals["total_collected_paise"] == 600000
    assert totals["remaining_paise"] == 0


def test_member_summaries_partial_and_zero_contributions():
    members = [
        {"id": 1, "paid_paise": 100000},  # paid half of 200000 share
        {"id": 2, "paid_paise": 0},        # paid nothing
        {"id": 3, "paid_paise": 200000},   # paid in full
    ]
    summaries, totals = compute_member_summaries(600000, members)
    by_id = {s["id"]: s for s in summaries}
    assert by_id[1]["balance_paise"] == -100000
    assert by_id[2]["balance_paise"] == -200000
    assert by_id[3]["balance_paise"] == 0
    assert totals["total_collected_paise"] == 300000
    assert totals["remaining_paise"] == 300000


def test_member_summaries_overpayment():
    # one generous member covers a friend's share
    members = [
        {"id": 1, "paid_paise": 400000},  # paid double their 200000 share
        {"id": 2, "paid_paise": 0},
        {"id": 3, "paid_paise": 200000},
    ]
    summaries, totals = compute_member_summaries(600000, members)
    by_id = {s["id"]: s for s in summaries}
    assert by_id[1]["balance_paise"] == 200000   # overpaid
    assert by_id[2]["balance_paise"] == -200000  # still owes
    assert by_id[3]["balance_paise"] == 0
    assert totals["total_collected_paise"] == 600000
    assert totals["remaining_paise"] == 0


def test_member_summaries_empty_member_list():
    summaries, totals = compute_member_summaries(600000, [])
    assert summaries == []
    assert totals["total_collected_paise"] == 0
    assert totals["remaining_paise"] == 600000


# ---------------------------------------------------------------------------
# Settlement algorithm
# ---------------------------------------------------------------------------

def _bal(id_, name, balance_paise):
    return {"id": id_, "name": name, "balance_paise": balance_paise}


def test_settlement_simple_one_debtor_one_creditor():
    balances = [_bal(1, "A", -200000), _bal(2, "B", 200000)]
    result = compute_settlement(balances)
    assert result["transactions"] == [
        {"from_id": 1, "from_name": "A", "to_id": 2, "to_name": "B", "amount_paise": 200000}
    ]
    assert result["unmatched_debt_paise"] == 0
    assert result["unmatched_credit_paise"] == 0


def test_settlement_fully_settled_pool_has_no_transactions():
    balances = [_bal(1, "A", 0), _bal(2, "B", 0)]
    result = compute_settlement(balances)
    assert result["transactions"] == []


def test_settlement_multiple_debtors_and_creditors_balances_exactly():
    # A owes 200000, B owes 100000; C is owed 150000, D is owed 150000
    balances = [
        _bal(1, "A", -200000),
        _bal(2, "B", -100000),
        _bal(3, "C", 150000),
        _bal(4, "D", 150000),
    ]
    result = compute_settlement(balances)
    assert result["unmatched_debt_paise"] == 0
    assert result["unmatched_credit_paise"] == 0
    # every transaction amount must be positive and reference real members
    total_transferred = sum(t["amount_paise"] for t in result["transactions"])
    assert total_transferred == 300000
    # sanity: total received by each creditor == their credit
    received = {}
    for t in result["transactions"]:
        received[t["to_id"]] = received.get(t["to_id"], 0) + t["amount_paise"]
    assert received[3] == 150000
    assert received[4] == 150000
    # total paid by each debtor == their debt
    paid = {}
    for t in result["transactions"]:
        paid[t["from_id"]] = paid.get(t["from_id"], 0) + t["amount_paise"]
    assert paid[1] == 200000
    assert paid[2] == 100000


def test_settlement_under_collected_pool_reports_unmatched_debt():
    # Budget 600000 among 3, only A and B contributed, C contributed nothing
    # and there is no one left to be a "creditor" for the shortfall.
    members = [
        {"id": 1, "paid_paise": 100000},  # share 200000 -> owes 100000
        {"id": 2, "paid_paise": 100000},  # share 200000 -> owes 100000
        {"id": 3, "paid_paise": 0},        # share 200000 -> owes 200000
    ]
    summaries, totals = compute_member_summaries(600000, members)
    balances = [_bal(s["id"], f"M{s['id']}", s["balance_paise"]) for s in summaries]
    result = compute_settlement(balances)
    # no creditors exist at all -> nothing can be matched
    assert result["transactions"] == []
    assert result["unmatched_debt_paise"] == 400000
    assert result["unmatched_credit_paise"] == 0
    assert result["unmatched_debt_paise"] == totals["remaining_paise"]


def test_settlement_over_collected_pool_reports_unmatched_credit():
    # Everyone paid their full share, but one member also paid extra.
    members = [
        {"id": 1, "paid_paise": 200000},
        {"id": 2, "paid_paise": 200000},
        {"id": 3, "paid_paise": 300000},  # paid 100000 extra
    ]
    summaries, totals = compute_member_summaries(600000, members)
    balances = [_bal(s["id"], f"M{s['id']}", s["balance_paise"]) for s in summaries]
    result = compute_settlement(balances)
    assert result["transactions"] == []  # no debtors to match against
    assert result["unmatched_debt_paise"] == 0
    assert result["unmatched_credit_paise"] == 100000
    assert result["unmatched_credit_paise"] == -totals["remaining_paise"]


def test_settlement_mixed_under_collected_with_partial_matching():
    # A owes 300000, B is owed 100000 (only partial match possible)
    balances = [_bal(1, "A", -300000), _bal(2, "B", 100000)]
    result = compute_settlement(balances)
    assert result["transactions"] == [
        {"from_id": 1, "from_name": "A", "to_id": 2, "to_name": "B", "amount_paise": 100000}
    ]
    assert result["unmatched_debt_paise"] == 200000
    assert result["unmatched_credit_paise"] == 0
