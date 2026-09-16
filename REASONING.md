# Reasoning

## Requirements analysis

**Explicit requirements** (directly from the problem statement):
- A pool with a budget and an organiser (not fixed to ₹6000 — any pool)
- Equal share calculation among members
- Recording contributions, including partial payments, overpayments (covering someone else), and
  members who haven't paid
- Clear per-member balance ("how much do I still owe?")
- Total collected and remaining amount ("have we collected enough yet?")
- A simple who-pays-whom settlement list

**Implied requirements** (reasonable extensions of the above, not invented Auriga-specific criteria):
- Add / edit / remove members
- Record and update (delete) contributions, since payments are made incrementally in real life
- Input validation: negative/non-numeric amounts, duplicate member names, empty budget/organiser fields
- Empty states: no pools, no members, no member-to-member transfers needed
- Exact money arithmetic (no floating-point rounding drift)

**Explicitly out of scope** unless time allowed: authentication, multi-currency, real payment
integration, notifications. None of these were implemented, and none were claimed as implemented.

## Tech stack

**Flask + SQLite + server-rendered Jinja2 templates + vanilla CSS/JS.**

- A single Python stack (backend + templates) avoids the overhead of a separate JS frontend/API layer,
  which matters under the 150-minute time limit.
- SQLite requires no separate server process or setup — Python's built-in `sqlite3` module is sufficient
  — while still giving real, persistent storage (data survives restarts, unlike an in-memory list).
- No ORM: with only 3 tables, raw SQL via `sqlite3` is simpler to write and verify correctly than
  introducing and debugging an ORM under time pressure.
- No JS framework: interactivity needed (copy-to-clipboard for settlement) is small enough for a few
  lines of vanilla JS.

## Data model

```
Pool (id, organiser_name, budget_paise, created_at)
Member (id, pool_id, name, created_at)     -- UNIQUE(pool_id, name)
Contribution (id, member_id, amount_paise, note, created_at)
```

A member's `paid_paise` is derived as `SUM(contribution.amount_paise)` rather than stored directly on
`Member`. This models contributions as a real ledger — someone can pay in installments, and a specific
payment can be corrected or deleted — rather than collapsing "record and update contributions" into a
single editable number.

All money is stored as **integer paise** (₹1 = 100 paise). Rupee amounts are parsed from user input using
Python's `Decimal` (not `float`) and converted to integer paise once, at the input boundary; all
arithmetic afterward is plain integer math. This avoids classic floating-point bugs like `0.1 + 0.2 !=
0.3`, which would be unacceptable for money calculations.

## Fair share calculation

`budget_paise // n` almost never divides evenly. The remainder (`budget_paise % n`, always
`0 <= remainder < n`) is distributed **one paise at a time** to the first `remainder` members (by id
order), so:

- Every member's share is within 1 paise of every other member's share.
- The shares always sum to **exactly** `budget_paise` — verified by an assertion in `compute_fair_shares`
  and by the `test_uneven_split_distributes_remainder_exactly` test (₹6000 / 7 members).

## Settlement algorithm

**Approach:** separate members into debtors (`balance < 0`) and creditors (`balance > 0`). Sort each
group largest-first. Repeatedly match the current largest debtor against the current largest creditor,
transfer `min(remaining debt, remaining credit)`, reduce both, and advance past whichever side reaches
zero. Repeat until one list is exhausted.

**Correctness properties, each covered by a test in `tests/test_logic.py`:**
- Every generated transaction reflects a real debt and a real, currently-unpaid claim (no invented
  transfers).
- The sum of all amounts a given debtor pays across transactions equals exactly their debt; the sum a
  given creditor receives equals exactly their credit (`test_settlement_multiple_debtors_and_creditors_balances_exactly`).
- A fully-settled pool produces zero transactions.

**Under- and over-collected pools — an important nuance:**
Since fair shares always sum exactly to the budget, `sum(all balances) = total_collected - budget`.

- If the pool is **under-collected**, total debt among members exceeds total credit among members. After
  matching, some debt is left over with no member left to receive it — that leftover equals the pool's
  overall shortfall (`remaining_paise`). The UI reports this as *"still owed to the pool overall"*, not
  as owed to any specific member, because no member currently holds a claim on it.
- If the pool is **over-collected**, the reverse happens: leftover unmatched credit equals the pool's
  surplus. The UI reports this as *"collected more than the budget"* rather than inventing a debtor for
  it.

Both cases are covered by dedicated tests (`test_settlement_under_collected_pool_reports_unmatched_debt`,
`test_settlement_over_collected_pool_reports_unmatched_credit`), which also assert the unmatched amount
equals the independently-computed `totals["remaining_paise"]` — i.e. the two ways of computing "money
outstanding" agree.

**On optimality — stated precisely, as required:** the largest-first greedy match is a standard heuristic
that produces a small number of transactions in practice and is provably **valid** (every transfer is
backed by a real debt/credit and money is conserved). It is **not** proven, and not claimed, to produce
the mathematically minimum possible number of transactions for every input. Finding the true minimum is
equivalent to a partition/subset-sum-style combinatorial optimization problem, which is NP-hard in
general — solving it exactly was judged out of scope for the time available, and greedy largest-first is
the standard practical choice for this kind of debt-settlement problem.

## Testing strategy

Unit tests (`tests/test_logic.py`, run via `pytest`) exercise `app/logic.py` directly — no Flask, no
database — so the core money math is tested in isolation and fast to run. This was written and run
*before* the Flask routes/UI, so correctness of the calculations was established first, per the priority
order in the assessment brief.

22 tests, actually executed (not just written) — see `README.md` for the exact command and the chat log
for the full pytest output. Coverage: money parsing/validation (valid/negative/non-numeric/empty/too many
decimals), equal split, uneven split, single member, zero members, zero budget, full/partial/zero
contributions, overpayment, empty member list, simple settlement, fully-settled pool, multiple
debtors/creditors, under-collected pool, over-collected pool, and partial matching.

In addition, the full application was manually smoke-tested end-to-end against the running server
(pool creation, member add/rename/remove, contribution add/delete, duplicate-name rejection, invalid
amount rejection, 404 on a nonexistent pool, empty-pool rendering, and re-verification that balances and
settlement recompute correctly after every state change). Results are reported in the chat log; nothing
here is claimed without having been actually run.

## What was deliberately not built

- No minimum-transaction-count settlement solver (see above).
- No authentication/multi-user access control — any pool URL is viewable/editable by anyone who has it.
- No production WSGI server configuration (`debug=True` dev server is used, appropriate for this
  assessment only).

## Extensibility

The architecture was reviewed for extensibility (in case Auriga requests an additional feature after
the initial build). Findings:

**Already in place:**
- `app/logic.py` has no Flask or database dependency — pure functions, independently unit-testable.
- `compute_settlement()` only consumes each member's final `balance_paise`; it has no knowledge of how
  that balance was derived. This means a future change to *how shares are calculated* (e.g. non-equal or
  weighted shares) would only touch `compute_fair_shares()`/`compute_member_summaries()` — the settlement
  algorithm and its existing tests would not need to change.
- The `contribution` table already stores every individual payment with a timestamp and optional note
  (not just a running total), so a "payment history" feature is largely already supported by the data
  model.
- The SQLite schema is not committed (`gift_pool.db` is gitignored and created fresh by `init_db()` on
  first run), so additive schema changes (new columns/tables) don't require a migration system for this
  assessment's workflow.

**Most likely extension point:** custom/non-equal share calculation. Currently `compute_fair_shares()`
only implements equal division with remainder distribution. Supporting per-member weighted shares would
mean changing this one function's inputs (e.g. accepting per-member weights) and how
`compute_member_summaries()` calls it — a contained change, not a rewrite.

**Other plausible extensions, all additive (new route/template/column, no changes to existing logic):**
settlement export (CSV/text), a payment-history display, additional pool settings (due date, currency
label), and new validation rules (centralized in `parse_rupees_to_paise()` and a few route-level checks).

**Risks noted, not acted on (no current requirement justifies a fix):**
- SQL is written inline in `app/routes.py` rather than behind a query/repository module. Fine at the
  current size; worth reconsidering only if a future feature needs several new non-trivial queries.
- If schema changes were ever needed against a *persisted* (not freshly recreated) `gift_pool.db`, the
  current `CREATE TABLE IF NOT EXISTS` approach in `db.py` would not retroactively add new columns —
  this is not a concern under the current workflow (db file is not committed and is recreated on first
  run), but would matter if that assumption changes.

No speculative code (share-strategy parameters, export endpoints, new schema columns) was added for
these — only implemented once actually required, per the brief's instruction not to build hypothetical
features ahead of time.

