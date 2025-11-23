import os
import csv
import json
import sys
from datetime import datetime
from collections import defaultdict
from pyagentspec.property import StringProperty
from pyagentspec.tools import ServerTool

# Point to /workspace/src/website/data relative to THIS file, not the CWD
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # .../website
DATA_DIR = os.path.join(BASE_DIR, "data")

# Simple in-memory cache so we don't re-read CSVs every call
_CSV_CACHE = {}


def _load_csv(filename: str) -> list[dict]:
    """Load a CSV from DATA_DIR into a list of dicts (with caching)."""
    if filename in _CSV_CACHE:
        return _CSV_CACHE[filename]

    path = os.path.join(DATA_DIR, filename)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    _CSV_CACHE[filename] = rows
    return rows


def _parse_datetime(dt_str: str) -> datetime | None:
    if not dt_str:
        return None
    # transactions.csv uses "YYYY-MM-DD HH:MM"
    try:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _parse_date(d_str: str) -> datetime | None:
    if not d_str:
        return None
    try:
        return datetime.strptime(d_str, "%Y-%m-%d")
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Core joins: partner -> BRs -> accounts -> transactions
# ---------------------------------------------------------------------------

def _get_partner_record(partner_id: str) -> dict | None:
    partners = _load_csv("partner.csv")
    for row in partners:
        if row.get("partner_id") == partner_id:
            return row
    return None


def _get_partner_brs(partner_id: str) -> set[str]:
    """
    Return set of br_id values the partner participates in (BR roles only).
    """
    roles = _load_csv("partner_role.csv")
    br_ids: set[str] = set()
    for row in roles:
        if row.get("partner_id") != partner_id:
            continue
        if row.get("entity_type") != "BR":
            continue
        # You could filter by relationship_end_date if you only want active roles
        br_ids.add(row.get("entity_id"))
    return br_ids


def _get_br_accounts(br_ids: set[str]) -> set[str]:
    """
    Given BR IDs, return all linked account_ids (active or not).
    """
    if not br_ids:
        return set()

    links = _load_csv("br_to_account.csv")
    account_ids: set[str] = set()
    for row in links:
        if row.get("br_id") in br_ids:
            # You can choose to restrict to active relationships (status_code == "1")
            account_ids.add(row.get("account_id"))
    return account_ids


def _get_accounts(account_ids: set[str]) -> list[dict]:
    """
    Return account records for given account_ids.
    """
    if not account_ids:
        return []

    accounts = _load_csv("account.csv")
    result = [row for row in accounts if row.get("account_id") in account_ids]
    return result


def _get_transactions_for_accounts(account_ids: set[str]) -> list[dict]:
    """
    Return all transaction rows for the given internal account IDs.
    """
    if not account_ids:
        return []

    txs = _load_csv("transactions.csv")
    result = [row for row in txs if row.get("Account ID") in account_ids]
    return result


# ---------------------------------------------------------------------------
# Tool 1: resolve_customer (partner lookup)
# ---------------------------------------------------------------------------

def resolve_customer(query: str) -> str:
    """
    Resolve a user-provided client reference (name, partner_id, phone) into
    one or more internal partner IDs.

    Returns:
        JSON string:
        {
          "matches": [
            {
              "customer_id": "p_123",
              "partner_id": "p_123",
              "partner_name": "...",
              "partner_phone_number": "...",
              "score": 0.95
            },
            ...
          ]
        }
    """
    partners = _load_csv("partner.csv")
    q = query.strip().lower()

    matches = []

    # First, exact partner_id match
    for row in partners:
        if row.get("partner_id") == query:
            matches.append({
                "customer_id": row.get("partner_id"),
                "partner_id": row.get("partner_id"),
                "partner_name": row.get("partner_name"),
                "partner_phone_number": row.get("partner_phone_number"),
                "score": 1.0,
            })

    # Then, partial name or phone matches (if we still need more)
    if len(matches) < 5:
        for row in partners:
            pid = row.get("partner_id")
            if any(m["partner_id"] == pid for m in matches):
                continue

            name = (row.get("partner_name") or "").lower()
            phone = (row.get("partner_phone_number") or "").replace(" ", "").lower()

            if q in name or q in phone:
                matches.append({
                    "customer_id": pid,
                    "partner_id": pid,
                    "partner_name": row.get("partner_name"),
                    "partner_phone_number": row.get("partner_phone_number"),
                    "score": 0.7,
                })

            if len(matches) >= 5:
                break

    return json.dumps({"matches": matches}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool 2: get_customer_profile (summarised for a partner)
# ---------------------------------------------------------------------------

def get_customer_profile(customer_id: str) -> str:
    """
    Retrieve profile and high-level transactional summary for a given partner.

    customer_id == partner_id

    Returns JSON string:
    {
      "customer_id": "...",
      "partner_name": "...",
      "partner_class_code": "...",
      "partner_open_date": "...",
      "partner_close_date": "...",
      "country": "...",                 # domicile if available
      "num_accounts": 3,
      "currencies": ["CHF", "EUR"],
      "first_transaction_at": "...",
      "last_transaction_at": "...",
      "transaction_count": 42,
      "total_debit_amount": 1234.56,
      "total_credit_amount": 1500.00
    }
    """
    partner = _get_partner_record(customer_id)
    if not partner:
        return json.dumps(
            {
                "customer_id": customer_id,
                "partner_name": None,
                "partner_class_code": None,
                "partner_open_date": None,
                "partner_close_date": None,
                "country": None,
                "num_accounts": 0,
                "currencies": [],
                "first_transaction_at": None,
                "last_transaction_at": None,
                "transaction_count": 0,
                "total_debit_amount": 0.0,
                "total_credit_amount": 0.0,
            },
            ensure_ascii=False,
        )

    # Country: prefer domicile row from partner_country.csv
    country = None
    country_rows = _load_csv("partner_country.csv")
    for row in country_rows:
        if (
            row.get("partner_id") == customer_id
            and row.get("country_type") == "domicile"
            and row.get("partner_country_status_code") == "1"
        ):
            country = row.get("country_name")
            break

    # Accounts via BRs
    br_ids = _get_partner_brs(customer_id)
    account_ids = _get_br_accounts(br_ids)
    accounts = _get_accounts(account_ids)

    currencies = sorted({a.get("account_currency") for a in accounts if a.get("account_currency")})

    # Transactions
    txs = _get_transactions_for_accounts(account_ids)
    tx_count = len(txs)

    first_dt = None
    last_dt = None
    total_debit = 0.0
    total_credit = 0.0

    for tx in txs:
        dt = _parse_datetime(tx.get("Date", ""))
        if dt:
            if first_dt is None or dt < first_dt:
                first_dt = dt
            if last_dt is None or dt > last_dt:
                last_dt = dt

        amount_str = tx.get("Amount") or "0"
        try:
            amount = float(amount_str)
        except ValueError:
            amount = 0.0

        if (tx.get("Debit/Credit") or "").lower() == "debit":
            total_debit += amount
        else:
            total_credit += amount

    result = {
        "customer_id": customer_id,
        "partner_name": partner.get("partner_name"),
        "partner_class_code": partner.get("partner_class_code"),
        "partner_open_date": partner.get("partner_open_date"),
        "partner_close_date": partner.get("partner_close_date"),
        "country": country,
        "num_accounts": len(accounts),
        "currencies": currencies,
        "first_transaction_at": first_dt.isoformat(timespec="minutes") if first_dt else None,
        "last_transaction_at": last_dt.isoformat(timespec="minutes") if last_dt else None,
        "transaction_count": tx_count,
        "total_debit_amount": round(total_debit, 2),
        "total_credit_amount": round(total_credit, 2),
    }

    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool 3: list_transactions (for a client / partner)
# ---------------------------------------------------------------------------

def list_transactions(
    customer_id: str,
    start_datetime: str = "",
    end_datetime: str = "",
    limit: int = 50,
) -> str:

    # Tool input arrives as strings → cast
    try:
        limit = int(limit)
    except Exception:
        limit = 50

    start_dt = _parse_datetime(start_datetime) if start_datetime else None
    end_dt = _parse_datetime(end_datetime) if end_datetime else None

    br_ids = _get_partner_brs(customer_id)
    account_ids = _get_br_accounts(br_ids)
    txs = _get_transactions_for_accounts(account_ids)

    filtered = []
    for tx in txs:
        dt = _parse_datetime(tx.get("Date", ""))
        if dt is None:
            continue
        if start_dt and dt < start_dt:
            continue
        if end_dt and dt > end_dt:
            continue
        filtered.append((dt, tx))

    # Sort by datetime descending
    filtered.sort(key=lambda x: x[0], reverse=True)

    tx_rows = [tx for _, tx in filtered[:limit]]

    return json.dumps(
        {"customer_id": customer_id, "transactions": tx_rows},
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# Tool 4: summarize_customer_spend (per partner)
# ---------------------------------------------------------------------------

def summarize_customer_spend(
    customer_id: str,
    start_date: str = "",
    end_date: str = "",
    group_by: str = "month",
) -> str:
    """
    Compute aggregated 'spend' metrics (debits) for a customer.

    Args:
        customer_id: partner_id.
        start_date: "YYYY-MM-DD" inclusive, or empty string.
        end_date:   "YYYY-MM-DD" inclusive, or empty string.
        group_by:   "none", "day", "month", or "transfer_type".

    Returns JSON string:
    {
      "customer_id": "...",
      "total_amount": 1234.56,
      "currency": "MULTI" | "CHF" | ...,
      "period_start": "...",
      "period_end": "...",
      "group_by": "month",
      "groups": [
        {"key": "2025-01", "total_amount": 350.20, "transaction_count": 12},
        ...
      ]
    }
    """
    start_d = _parse_date(start_date) if start_date else None
    end_d = _parse_date(end_date) if end_date else None

    br_ids = _get_partner_brs(customer_id)
    account_ids = _get_br_accounts(br_ids)
    txs = _get_transactions_for_accounts(account_ids)

    # Only consider debits (money leaving the client's accounts) as "spend"
    spend_rows = []
    currencies = set()
    for tx in txs:
        if (tx.get("Debit/Credit") or "").lower() != "debit":
            continue

        dt = _parse_datetime(tx.get("Date", ""))
        if dt is None:
            continue

        if start_d and dt.date() < start_d.date():
            continue
        if end_d and dt.date() > end_d.date():
            continue

        amount_str = tx.get("Amount") or "0"
        try:
            amount = float(amount_str)
        except ValueError:
            amount = 0.0

        spend_rows.append((dt, amount, tx))
        if tx.get("Currency"):
            currencies.add(tx.get("Currency"))

    total_amount = sum(a for _, a, _ in spend_rows)

    # Choose currency label
    if not currencies:
        currency = None
    elif len(currencies) == 1:
        currency = list(currencies)[0]
    else:
        currency = "MULTI"

    # Determine grouping
    group_by = (group_by or "none").lower()
    groups = defaultdict(lambda: {"total_amount": 0.0, "transaction_count": 0})

    for dt, amount, tx in spend_rows:
        if group_by == "day":
            key = dt.date().isoformat()
        elif group_by == "month":
            key = f"{dt.year:04d}-{dt.month:02d}"
        elif group_by == "transfer_type":
            key = tx.get("Transfer_Type") or "UNKNOWN"
        else:
            key = "ALL"

        groups[key]["total_amount"] += amount
        groups[key]["transaction_count"] += 1

    group_list = [
        {
            "key": key,
            "total_amount": round(val["total_amount"], 2),
            "transaction_count": val["transaction_count"],
        }
        for key, val in sorted(groups.items(), key=lambda x: x[0])
    ]

    result = {
        "customer_id": customer_id,
        "total_amount": round(total_amount, 2),
        "currency": currency,
        "period_start": start_date or None,
        "period_end": end_date or None,
        "group_by": group_by,
        "groups": group_list,
    }

    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool specs (what the agent sees)
# ---------------------------------------------------------------------------
# 

resolve_customer_tool = ServerTool(
    name="resolve_customer",
    description=(
        "Resolve a user-provided client reference (name, partner_id, phone) into "
        "one or more internal customer IDs (partner_ids). Returns a JSON string "
        "with a 'matches' array."
    ),
    inputs=[
        StringProperty(title="query"),
    ],
    outputs=[
        StringProperty(title="matches_json"),
    ],
)

get_customer_profile_tool = ServerTool(
    name="get_customer_profile",
    description=(
        "Retrieve profile and high-level transactional metrics for a specific customer "
        "(partner). customer_id corresponds to partner_id. Returns a JSON string."
    ),
    inputs=[
        StringProperty(title="customer_id"),
    ],
    outputs=[
        StringProperty(title="profile_json"),
    ],
)

list_transactions_tool = ServerTool(
    name="list_transactions",
    description=(
        "List raw transactions for all accounts belonging to a given customer "
        "(partner). Allows optional datetime filters and a row limit. "
        "Returns a JSON string with a 'transactions' array."
    ),
    inputs=[
        StringProperty(title="customer_id"),
        StringProperty(
            title="start_datetime",
        ),
        StringProperty(
            title="end_datetime",
        ),
        StringProperty(
            title="limit",
        ),
    ],
    outputs=[
        StringProperty(title="transactions_json"),
    ],
)

summarize_customer_spend_tool = ServerTool(
    name="summarize_customer_spend",
    description=(
        "Compute aggregated spend (debits) for a customer across all their accounts. "
        "You can optionally filter by date range and group by day, month, or transfer_type. "
        "Returns a JSON string with totals and grouped breakdown."
    ),
    inputs=[
        StringProperty(title="customer_id"),
        StringProperty(title="start_date"),
        StringProperty(title="end_date"),
        StringProperty(
            title="group_by",
        ),
    ],
    outputs=[
        StringProperty(title="summary_json"),
    ],
)
