# Reasoning

## 1. Problem Understanding

The purpose of this application is to make group expense management simple.

For example, a group of friends may create a pool for a trip, event, party, or shared purchase. Everyone is expected to contribute an equal amount, but in real situations:

* Some members pay partially.
* Some members pay the full amount.
* Some members do not pay anything.
* One member may pay extra for someone else.
* The total collected amount may be less than or greater than the budget.

The application solves this problem by showing:

* The total pool budget.
* The amount collected so far.
* The amount still remaining.
* Each member's expected share.
* Each member's actual payment.
* How much each member owes or should receive.
* A simple list of who should pay whom.

The main goal was to make the financial calculations correct and the result easy for users to understand.

---

## 2. Requirements Analysis

### Core Requirements

The application supports:

1. Creating a pool with an organiser and a budget.
2. Adding members to the pool.
3. Calculating an equal share for all members.
4. Recording member contributions.
5. Supporting multiple contributions from the same member.
6. Supporting partial payments.
7. Handling members who have not paid.
8. Handling overpayments.
9. Showing individual member balances.
10. Showing the total collected amount.
11. Showing the remaining amount.
12. Generating a settlement list.

### Additional Features

The following features were added to make the application more practical:

* Rename members.
* Remove members.
* Add contribution notes.
* Delete incorrect contributions.
* Reject duplicate member names.
* Reject invalid amounts.
* Handle empty pools.
* Handle pools with no members.
* Handle fully settled pools.
* Recalculate balances after every change.

### Features Not Included

The following features were intentionally kept outside the current scope:

* User authentication.
* User accounts.
* Multi-currency support.
* Real payment integration.
* Notifications.
* Production deployment.
* A mathematically perfect minimum-transaction settlement solver.

These features were not necessary for the current assessment and were not claimed as implemented.

---

## 3. Technology Choices

The application uses:

* **Flask** for the backend.
* **SQLite** for the database.
* **Jinja2** for HTML templates.
* **Vanilla CSS** for styling.
* **Vanilla JavaScript** for small frontend interactions.
* **pytest** for testing.

### Why Flask?

Flask was selected because it is lightweight and quick to develop with.

The application mainly requires:

* Form handling.
* Database operations.
* Page rendering.
* Validation.
* A few backend calculations.

Flask provides all of this without adding unnecessary complexity.

### Why SQLite?

SQLite was selected because:

* It does not require a separate database server.
* It works directly with Python.
* It stores data permanently.
* It is simple enough for a small application.
* It can be used quickly during an assessment.

The data remains available after restarting the application because it is stored in a database instead of only being kept in memory.

### Why Vanilla JavaScript?

The application does not require a large frontend framework.

The frontend only needs small interactions such as copying settlement instructions. Vanilla JavaScript is enough for these requirements and keeps the project easier to understand.

---

## 4. Database Design

The application uses three main tables.

```text
Pool
- id
- organiser_name
- budget_paise
- created_at

Member
- id
- pool_id
- name
- created_at

Contribution
- id
- member_id
- amount_paise
- note
- created_at
```

### Pool Table

The `Pool` table stores the main information about a pool:

* Organiser name.
* Total budget.
* Creation time.

### Member Table

The `Member` table stores the members belonging to a pool.

A member name must be unique inside the same pool. This prevents the same person from being added twice accidentally.

### Contribution Table

Every payment is stored as a separate contribution.

This is important because a member may pay in installments.

For example:

```text
Rahul pays ₹500
Rahul pays ₹300
Rahul pays ₹200
```

The application stores these as three contribution records and calculates Rahul's total payment as ₹1000.

This approach also makes it possible to delete an incorrect payment without changing the entire member record.

---

## 5. Handling Money Correctly

Money is stored as integer paise instead of floating-point rupees.

```text
₹1 = 100 paise
```

For example:

```text
₹125.50 = 12550 paise
```

### Why Integer Paise?

Floating-point calculations can create rounding problems.

For example:

```text
0.1 + 0.2
```

may not be represented exactly by a computer using floating-point arithmetic.

That type of error is not acceptable when calculating money.

Therefore:

1. User input is read as a decimal amount.
2. The amount is converted into paise.
3. All calculations are performed using integers.
4. The final result is converted back into rupees for display.

This keeps the calculations accurate and avoids unexpected rounding errors.

---

## 6. Equal Share Calculation

The expected share is calculated by dividing the pool budget by the number of members.

For example:

```text
Budget = ₹6000
Members = 6

Each member's share = ₹1000
```

However, some budgets cannot be divided equally into whole paise.

For example:

```text
Budget = ₹6000
Members = 7
```

The application first calculates:

```text
base_share = budget_paise // number_of_members
remainder = budget_paise % number_of_members
```

The remaining paise are distributed one by one to the first members in a consistent order.

This ensures that:

* The difference between members is never more than one paise.
* The total of all shares is exactly equal to the budget.
* No money is lost through rounding.
* The result is predictable every time.

The application also verifies that all calculated shares add up to the original budget.

---

## 7. Member Balance Calculation

Each member's balance is calculated using:

```text
balance = amount_paid - expected_share
```

The meaning is:

### Negative Balance

The member has paid less than their expected share.

They still owe money.

### Positive Balance

The member has paid more than their expected share.

They should receive money back or be reimbursed.

### Zero Balance

The member has paid exactly their expected share.

They are settled.

For example:

```text
Expected share = ₹1000
Amount paid = ₹700

Balance = ₹700 - ₹1000
Balance = -₹300
```

This member still owes ₹300.

Another example:

```text
Expected share = ₹1000
Amount paid = ₹1300

Balance = ₹1300 - ₹1000
Balance = ₹300
```

This member should receive ₹300.

---

## 8. Settlement Logic

The settlement system converts individual balances into simple payment instructions.

The application divides members into two groups.

### Debtors

Debtors are members with a negative balance.

They need to pay money.

### Creditors

Creditors are members with a positive balance.

They have paid extra and should receive money.

The application then:

1. Sorts debtors by the amount they owe.
2. Sorts creditors by the amount they should receive.
3. Matches the largest debtor with the largest creditor.
4. Transfers the smaller outstanding amount.
5. Updates both balances.
6. Continues until no further matching is possible.

The transfer amount is:

```text
min(debtor_amount, creditor_amount)
```

### Example

```text
A owes ₹1000
B owes ₹500

C should receive ₹800
D should receive ₹700
```

The settlement may become:

```text
A pays C ₹800
A pays D ₹200
B pays D ₹500
```

This is easier to understand than asking every member to pay every other member.

The algorithm ensures that:

* A member does not pay more than they owe.
* A member does not receive more than they should.
* The total money transferred is correct.
* Fully settled pools produce no unnecessary transactions.

---

## 9. Under-Collected and Over-Collected Pools

### Under-Collected Pool

An under-collected pool is one where:

```text
total_collected < budget
```

For example:

```text
Budget = ₹6000
Collected = ₹5000
Remaining = ₹1000
```

In this case, the application shows that ₹1000 is still owed to the pool overall.

It does not assign this amount to a specific member because the missing money does not belong to any individual creditor yet.

### Over-Collected Pool

An over-collected pool is one where:

```text
total_collected > budget
```

For example:

```text
Budget = ₹6000
Collected = ₹6200
Surplus = ₹200
```

The application reports the ₹200 as a surplus instead of creating an artificial debt or creditor.

This keeps the result honest and avoids showing incorrect settlement instructions.

---

## 10. Testing Strategy

The most important part of this application is the money calculation.

For that reason, the core logic was kept separate from Flask routes and database code.

The main logic is located in:

```text
app/logic.py
```

The tests are located in:

```text
tests/test_logic.py
```

The tests are executed using:

```bash
pytest
```

### Areas Covered by Tests

The tests cover:

* Valid money values.
* Empty amounts.
* Negative amounts.
* Non-numeric amounts.
* Too many decimal places.
* Equal share calculation.
* Uneven share calculation.
* Remainder distribution.
* Single-member pools.
* Empty member lists.
* Zero-budget pools.
* Full payments.
* Partial payments.
* Missing payments.
* Overpayments.
* Simple settlements.
* Multiple debtors.
* Multiple creditors.
* Fully settled pools.
* Under-collected pools.
* Over-collected pools.
* Partial settlement matching.

The test suite contains 22 tests.

The application was also manually checked for:

* Pool creation.
* Adding members.
* Renaming members.
* Removing members.
* Adding contributions.
* Deleting contributions.
* Duplicate-name validation.
* Invalid amount validation.
* Empty-pool rendering.
* Nonexistent pool handling.
* Balance recalculation.
* Settlement recalculation.

The calculations were tested separately before connecting them to the user interface. This reduced the chance of hiding calculation errors inside the Flask routes or templates.

---

## 11. Important Design Decisions

### Keep Business Logic Separate

The calculation functions are kept in `app/logic.py`.

This makes the logic:

* Easier to test.
* Easier to understand.
* Independent from Flask.
* Easier to reuse in the future.

### Store Contributions Individually

Payments are stored separately instead of only storing a final total.

This supports:

* Installments.
* Payment history.
* Notes.
* Deleting incorrect payments.
* Accurate recalculation.

### Use Exact Money Calculations

Integer paise are used to avoid rounding errors.

This is one of the most important decisions in the application because incorrect money calculations would make the entire application unreliable.

### Recalculate Instead of Duplicating Data

Balances are calculated from:

* The budget.
* The number of members.
* The member contributions.

The application does not permanently store calculated balances. This reduces the chance of old or incorrect balance values remaining in the database.

---

## 12. Limitations

The current application has the following limitations:

* It does not include authentication.
* Anyone with a pool URL may be able to view or edit that pool.
* It uses Flask's development server.
* It supports equal shares only.
* It does not support multiple currencies.
* It does not process real payments.
* The settlement algorithm does not guarantee the absolute minimum number of transactions.
* Database migrations would be needed if the database structure changes after deployment.
* SQL queries are currently written directly in the route layer.

These limitations are acceptable for the assessment version but should be addressed before using the application in a production environment.

---

## 13. Future Improvements

Possible future improvements include:

* User authentication.
* Private pools.
* Role-based access.
* Custom shares for different members.
* Weighted expense splitting.
* Multiple currencies.
* Payment reminders.
* CSV export.
* Settlement history.
* Payment history display.
* Due dates.
* Real payment integration.
* Production deployment.
* A more advanced settlement algorithm.

The current structure makes many of these improvements possible without rewriting the complete application.

For example, custom shares would mainly require changes to the share-calculation logic. The settlement algorithm could continue using the final balances generated by that calculation.

---

## 14. Final Summary

The application was designed around one main principle:

> Make shared expenses easy to calculate, easy to track, and easy to settle.

The main decisions were:

* Flask was used to keep the backend simple.
* SQLite was used for persistent storage.
* Contributions were stored individually.
* Money was stored as integer paise.
* Equal shares were calculated without rounding errors.
* Member balances were calculated from actual payments.
* A greedy settlement algorithm was used to create practical payment instructions.
* Core financial logic was separated and tested independently.
* Features outside the assessment scope were intentionally not added.

The result is a focused application that handles the main group-expense problem while keeping the code understandable, testable, and extendable.
