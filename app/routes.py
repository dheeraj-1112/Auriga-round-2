from flask import Blueprint, render_template, request, redirect, url_for, flash, abort

from app.db import get_connection
from app.logic import (
    parse_rupees_to_paise,
    paise_to_rupees_str,
    compute_member_summaries,
    compute_settlement,
    ValidationError,
)

bp = Blueprint("main", __name__)


def _get_pool_or_404(conn, pool_id):
    pool = conn.execute("SELECT * FROM pool WHERE id = ?", (pool_id,)).fetchone()
    if pool is None:
        abort(404)
    return pool


def _get_members_with_totals(conn, pool_id):
    """Members of a pool with their paid_paise = sum of contributions."""
    rows = conn.execute(
        """
        SELECT m.id, m.name,
               COALESCE(SUM(c.amount_paise), 0) AS paid_paise
        FROM member m
        LEFT JOIN contribution c ON c.member_id = m.id
        WHERE m.pool_id = ?
        GROUP BY m.id
        ORDER BY m.id
        """,
        (pool_id,),
    ).fetchall()
    return [{"id": r["id"], "name": r["name"], "paid_paise": r["paid_paise"]} for r in rows]


# ---------------------------------------------------------------------------
# Home — list pools + create pool
# ---------------------------------------------------------------------------

@bp.route("/", methods=["GET"])
def index():
    conn = get_connection()
    try:
        pools = conn.execute("SELECT * FROM pool ORDER BY id DESC").fetchall()
    finally:
        conn.close()
    return render_template("index.html", pools=pools, paise_to_rupees_str=paise_to_rupees_str)


@bp.route("/pool/create", methods=["POST"])
def create_pool():
    organiser_name = (request.form.get("organiser_name") or "").strip()
    budget_raw = request.form.get("budget")

    if not organiser_name:
        flash("Organiser name is required.", "error")
        return redirect(url_for("main.index"))

    try:
        budget_paise = parse_rupees_to_paise(budget_raw)
    except ValidationError as e:
        flash(str(e), "error")
        return redirect(url_for("main.index"))

    if budget_paise == 0:
        flash("Budget must be greater than zero.", "error")
        return redirect(url_for("main.index"))

    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO pool (organiser_name, budget_paise) VALUES (?, ?)",
            (organiser_name, budget_paise),
        )
        conn.commit()
        pool_id = cur.lastrowid
    finally:
        conn.close()

    return redirect(url_for("main.pool_detail", pool_id=pool_id))


# ---------------------------------------------------------------------------
# Pool dashboard
# ---------------------------------------------------------------------------

@bp.route("/pool/<int:pool_id>", methods=["GET"])
def pool_detail(pool_id):
    conn = get_connection()
    try:
        pool = _get_pool_or_404(conn, pool_id)
        members = _get_members_with_totals(conn, pool_id)
        summaries, totals = compute_member_summaries(pool["budget_paise"], members)

        balances_for_settlement = [
            {"id": s["id"], "name": s["name"], "balance_paise": s["balance_paise"]}
            for s in summaries
        ]
        settlement = compute_settlement(balances_for_settlement)
    finally:
        conn.close()

    progress_pct = 0
    if pool["budget_paise"] > 0:
        progress_pct = max(0, min(100, round(totals["total_collected_paise"] * 100 / pool["budget_paise"])))

    return render_template(
        "pool.html",
        pool=pool,
        members=summaries,
        totals=totals,
        settlement=settlement,
        progress_pct=progress_pct,
        paise_to_rupees_str=paise_to_rupees_str,
    )


# ---------------------------------------------------------------------------
# Members: add / edit / remove
# ---------------------------------------------------------------------------

@bp.route("/pool/<int:pool_id>/member/add", methods=["POST"])
def add_member(pool_id):
    name = (request.form.get("name") or "").strip()
    conn = get_connection()
    try:
        _get_pool_or_404(conn, pool_id)
        if not name:
            flash("Member name is required.", "error")
            return redirect(url_for("main.pool_detail", pool_id=pool_id))
        try:
            conn.execute("INSERT INTO member (pool_id, name) VALUES (?, ?)", (pool_id, name))
            conn.commit()
        except Exception:
            # UNIQUE(pool_id, name) constraint violation
            flash(f"A member named '{name}' already exists in this pool.", "error")
    finally:
        conn.close()
    return redirect(url_for("main.pool_detail", pool_id=pool_id))


@bp.route("/pool/<int:pool_id>/member/<int:member_id>/rename", methods=["POST"])
def rename_member(pool_id, member_id):
    new_name = (request.form.get("name") or "").strip()
    conn = get_connection()
    try:
        _get_pool_or_404(conn, pool_id)
        if not new_name:
            flash("Member name is required.", "error")
            return redirect(url_for("main.pool_detail", pool_id=pool_id))
        try:
            conn.execute(
                "UPDATE member SET name = ? WHERE id = ? AND pool_id = ?",
                (new_name, member_id, pool_id),
            )
            conn.commit()
        except Exception:
            flash(f"A member named '{new_name}' already exists in this pool.", "error")
    finally:
        conn.close()
    return redirect(url_for("main.pool_detail", pool_id=pool_id))


@bp.route("/pool/<int:pool_id>/member/<int:member_id>/remove", methods=["POST"])
def remove_member(pool_id, member_id):
    conn = get_connection()
    try:
        _get_pool_or_404(conn, pool_id)
        conn.execute("DELETE FROM member WHERE id = ? AND pool_id = ?", (member_id, pool_id))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for("main.pool_detail", pool_id=pool_id))


# ---------------------------------------------------------------------------
# Contributions: record / edit / delete
# ---------------------------------------------------------------------------

@bp.route("/pool/<int:pool_id>/member/<int:member_id>/contribute", methods=["POST"])
def add_contribution(pool_id, member_id):
    amount_raw = request.form.get("amount")
    note = (request.form.get("note") or "").strip() or None

    conn = get_connection()
    try:
        _get_pool_or_404(conn, pool_id)
        member = conn.execute(
            "SELECT * FROM member WHERE id = ? AND pool_id = ?", (member_id, pool_id)
        ).fetchone()
        if member is None:
            abort(404)

        try:
            amount_paise = parse_rupees_to_paise(amount_raw)
        except ValidationError as e:
            flash(str(e), "error")
            return redirect(url_for("main.pool_detail", pool_id=pool_id))

        if amount_paise == 0:
            flash("Contribution amount must be greater than zero.", "error")
            return redirect(url_for("main.pool_detail", pool_id=pool_id))

        conn.execute(
            "INSERT INTO contribution (member_id, amount_paise, note) VALUES (?, ?, ?)",
            (member_id, amount_paise, note),
        )
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for("main.pool_detail", pool_id=pool_id))


@bp.route("/pool/<int:pool_id>/contribution/<int:contribution_id>/delete", methods=["POST"])
def delete_contribution(pool_id, contribution_id):
    conn = get_connection()
    try:
        _get_pool_or_404(conn, pool_id)
        conn.execute(
            """DELETE FROM contribution
               WHERE id = ? AND member_id IN (SELECT id FROM member WHERE pool_id = ?)""",
            (contribution_id, pool_id),
        )
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for("main.pool_detail", pool_id=pool_id))
