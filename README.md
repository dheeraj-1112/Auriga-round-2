# Gift Pool

Track a shared gift/farewell pool — who owes what, how much is collected, and who should pay whom to settle up.

## Problem

A group is chipping in equally for a manager's farewell gift. In practice contributions are messy: some
members pay in full, some pay partially, one person overpays to cover a friend, and some haven't paid at
all. The organiser needs to see, at a glance, each member's balance, the total collected vs. remaining,
and the simplest possible list of who should pay whom.

This app supports **any** budget, organiser, and member count — not just one fixed scenario.

## Tech stack

- **Python 3 + Flask** — server-rendered HTML (no separate frontend build step)
- **SQLite** — zero-setup persistent storage (`gift_pool.db`, created automatically on first run)
- **Vanilla CSS/JS** — no frontend framework or build tooling
- **pytest** — unit tests for the core business logic

See `REASONING.md` for why this stack and design were chosen.

## Setup

```bash
python3 -m venv .venv          # optional but recommended
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the app

```bash
python3 main.py
```

Then open **http://127.0.0.1:5000** in a browser. A SQLite file `gift_pool.db` is created automatically
in the project root on first run (ignored by git).

## Run the tests

```bash
python3 -m pytest tests/ -v
```

All 22 unit tests cover the core money logic: share calculation (including uneven/remainder splits),
balance calculation, and the settlement algorithm (partial payments, overpayments, zero payments,
under-collected pools, over-collected pools, multiple debtors/creditors).

## Using the app

1. On the home page, enter an organiser name and a budget to create a pool.
2. On the pool page, add members.
3. Record a contribution for each member as they pay (can be partial, full, or more than their share).
4. The dashboard shows, per member: fair share, amount paid, and balance (owes / overpaid / settled).
5. The **Settlement** section lists the minimal-effort transfers (who pays whom) needed to settle
   everyone up, and separately flags any amount still owed to the pool overall (if under-collected) or
   any surplus held by the pool (if over-collected) — since that money isn't owed by/to any single member.

## Project structure

```
gift_pool/
├── main.py                 # entry point (python3 main.py)
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── db.py                 # SQLite schema + connection
│   ├── logic.py               # core business logic (pure functions, unit tested)
│   └── routes.py              # Flask views (HTTP layer)
├── templates/                # Jinja2 HTML templates
├── static/                   # CSS + JS
├── tests/
│   └── test_logic.py          # unit tests for app/logic.py
├── requirements.txt
└── gift_pool.db               # created on first run, not committed
```

## Known limitations

- Single-process dev server (`app.run(debug=True)`) — fine for this assessment, not for production use.
- No authentication — anyone with the URL/pool link can view and edit that pool.
- The settlement algorithm is a greedy largest-debtor/largest-creditor match. It produces a correct,
  valid settlement with few transactions in practice, but it is **not proven to be the mathematically
  minimum number of transactions** — see `REASONING.md` for detail.
