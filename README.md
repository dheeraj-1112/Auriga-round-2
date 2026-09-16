
# Gift Pool

A simple web application for managing a shared gift or farewell fund.

Gift Pool helps a group track:

- How much money each member should contribute.
- How much each member has already paid.
- Who still owes money.
- Who has paid extra.
- How the group can settle payments between members.

## Problem

When a group collects money for a gift, everyone may not pay the same amount at the same time.

For example:

- One member may pay the full amount.
- Another member may pay only part of their share.
- Someone may pay extra for a friend.
- Some members may not have paid anything yet.

This makes it difficult to know who owes money and how the group should settle the remaining amount.

**Gift Pool solves this problem by showing each member's balance and generating a clear settlement plan.**

The application supports any budget, organiser, and number of members.

---

## Features

- Create a gift pool with an organiser and budget.
- Add any number of members.
- Record full, partial, or extra payments.
- Calculate each member's fair share.
- Display the total amount collected.
- Display the remaining amount.
- Show who owes money and who has overpaid.
- Generate a list of suggested payments between members.
- Handle under-collected and over-collected pools.
- Store data persistently using SQLite.
- Test the core money and settlement logic using pytest.

---

## Example

Suppose a group has:

- **Budget:** ₹3,000
- **Members:** 3
- **Fair share per member:** ₹1,000

Payments:

| Member | Amount Paid | Balance |
|---|---:|---:|
| Rahul | ₹1,000 | Settled |
| Aman | ₹500 | Owes ₹500 |
| Priya | ₹1,500 | Overpaid ₹500 |

The application may suggest:

```text
Aman pays Priya ₹500
```

This makes the settlement process easier and avoids unnecessary transactions.

---

## Tech Stack

- **Python 3** — application programming language
- **Flask** — server-side web framework
- **SQLite** — lightweight persistent database
- **HTML, CSS and JavaScript** — user interface
- **pytest** — unit testing

The application uses server-rendered HTML and does not require a separate frontend build process.

---

## Project Structure

```text
gift_pool/
├── main.py                  # Application entry point
├── app/
│   ├── __init__.py          # Flask application factory
│   ├── db.py                # Database connection and schema
│   ├── logic.py             # Core money and settlement logic
│   └── routes.py            # Flask routes and views
├── templates/               # HTML templates
├── static/                  # CSS and JavaScript files
├── tests/
│   └── test_logic.py        # Unit tests for business logic
├── requirements.txt         # Python dependencies
├── REASONING.md             # Design and technical decisions
└── gift_pool.db             # SQLite database created automatically
```

The `gift_pool.db` file is created automatically when the application runs for the first time. It is not committed to Git.

---

## Setup

### 1. Create a virtual environment

This step is optional but recommended.

```bash
python3 -m venv .venv
```

### 2. Activate the virtual environment

On Linux or macOS:

```bash
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Run the Application

Start the Flask development server:

```bash
python3 main.py
```

Open the following URL in your browser:

```text
http://127.0.0.1:5000
```

The SQLite database will be created automatically when the application starts.

---

## How to Use

### Step 1: Create a pool

Enter:

- Organiser name
- Gift budget

Then create the pool.

### Step 2: Add members

Add everyone who is contributing to the gift.

### Step 3: Record payments

Record how much each member has paid.

Payments can be:

- Partial
- Full
- More than the member's fair share
- Zero

### Step 4: View the dashboard

The dashboard displays:

- Each member's fair share
- Amount paid by each member
- Remaining balance
- Total amount collected
- Total amount still required

### Step 5: Check settlement suggestions

The Settlement section suggests who should pay whom.

It also separately displays:

- Money still needed when the pool is under-collected.
- Extra money held by the pool when the pool is over-collected.

---

## Run the Tests

Run all unit tests using:

```bash
python3 -m pytest tests/ -v
```

The test suite covers:

- Equal share calculation
- Uneven and remainder splits
- Member balance calculation
- Partial payments
- Full payments
- Overpayments
- Zero payments
- Under-collected pools
- Over-collected pools
- Multiple debtors and creditors
- Settlement calculation

---

## Settlement Logic

The application uses a greedy settlement algorithm.

It matches:

1. The member who owes the most money.
2. The member who should receive the most money.
3. The smaller of those two amounts is transferred.
4. The process continues until all member balances are settled.

This produces a valid settlement with a small number of transactions in common situations.

However, the algorithm is **not guaranteed to produce the mathematically minimum possible number of transactions**.

For more information about the design decisions and algorithm, see:

```text
REASONING.md
```

---

## Known Limitations

- The application uses Flask's single-process development server.
- There is no authentication or user login.
- Anyone with access to a pool link can view or edit that pool.
- The settlement algorithm is greedy and is not guaranteed to minimize the number of transactions.
- The application is intended for assessment and demonstration purposes, not production use.

---

## License

This project was created as part of a technical assessment.