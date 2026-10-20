"""
app/services.py
=============================================================================
Business Logic & Operations Service Layer for CORE BANKING SYSTEM
=============================================================================

PYTHON FUNDAMENTALS DEMONSTRATED IN THIS FILE:
1. Reusable Business Functions:
   - Encapsulating deposit, withdrawal, and transfer workflows.
   - Atomic balance updates and transaction record generation.

2. Loop Iteration & Linear Search:
   - Searching customers by ID or account number.
   - Filtering transactions for the authenticated customer only.

3. Control Flow & Error Guarding (if / elif / else):
   - Checking customer existence, active status, valid positive amounts,
     and sufficient available balance.

4. List & Dictionary Manipulation:
   - Appending to `CUSTOMERS_DB` and `TRANSACTIONS_DB`.
   - Mutating in-place balance attributes accurately with `round(..., 2)`.

5. Modern Type Hints:
   - Using `dict | None`, `tuple[bool, str, float | None]`, `list[dict]`.
"""

import io
import csv
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from app.models import (
    CUSTOMERS_DB,
    TRANSACTIONS_DB,
    LOANS_DB,
    LOAN_TYPES,
    CHEQUE_REQUESTS_DB,
    LEAF_OPTIONS,
    CHEQUE_STATUSES,
    AUDIT_LOG_DB,
)
from app.utils import (
    validate_customer_data,
    validate_transaction_amount,
    validate_loan_application_input,
    validate_loan_approval_input,
    mask_account_number,
    validate_cheque_request_input,
    validate_cheque_rejection_reason,
    validate_date_range,
    sanitize_csv_value,
    safe_int,
    safe_float,
)


def get_all_customers() -> list[dict]:
    """Retrieves all customers stored in memory."""
    return CUSTOMERS_DB


def get_customer_by_id(customer_id: int) -> dict | None:
    """
    Searches for a single customer by their primary customer_id.
    """
    if not isinstance(customer_id, int):
        return None

    for customer in CUSTOMERS_DB:
        if customer.get("customer_id") == customer_id:
            return customer

    return None


def get_customer_by_account_number(account_number: str) -> dict | None:
    """
    Searches for a customer by their unique account number (e.g. 'ACC-1002941').

    Demonstrates:
    - String normalization with .strip() and .upper().
    - Linear search loop.
    """
    if not account_number or not isinstance(account_number, str):
        return None

    clean_acc = account_number.strip().upper()
    for customer in CUSTOMERS_DB:
        if customer.get("account_number", "").strip().upper() == clean_acc:
            return customer

    return None


def validate_customer(customer_data: dict) -> tuple[bool, list[str]]:
    """Validates a customer data dictionary against business rules."""
    return validate_customer_data(customer_data)


def create_customer(
    name: str,
    age: int,
    email: str,
    phone: str,
    account_type: str,
    balance: float = 0.0,
    is_active: bool = True,
) -> tuple[dict | None, list[str]]:
    """Creates and stores a new customer after rigorous validation."""
    candidate_data = {
        "name": name,
        "age": age,
        "email": email,
        "phone": phone,
        "account_type": account_type,
        "balance": balance,
        "is_active": is_active,
    }

    is_valid, errors = validate_customer(candidate_data)
    if not is_valid:
        return None, errors

    if len(CUSTOMERS_DB) > 0:
        max_id = max(c["customer_id"] for c in CUSTOMERS_DB)
        new_id = max_id + 1
    else:
        new_id = 1

    account_number = f"ACC-{1000000 + new_id * 1103 % 899999}"

    new_customer = {
        "customer_id": new_id,
        "name": name.strip(),
        "age": age,
        "email": email.strip().lower(),
        "phone": phone.strip(),
        "password": "Password123",
        "account_number": account_number,
        "account_type": account_type,
        "balance": round(float(balance), 2),
        "is_active": is_active,
        "account_status": "Active" if is_active else "Pending",
    }

    CUSTOMERS_DB.append(new_customer)
    return new_customer, []


def is_account_active(customer_id: int) -> bool:
    """Checks if a given customer's account is currently active."""
    customer = get_customer_by_id(customer_id)
    if customer is not None:
        # Check both boolean flag and account status string
        return bool(customer.get("is_active") and customer.get("account_status", "Active") == "Active")
    return False


def get_account_summary() -> dict:
    """Calculates summary metrics across all customers."""
    total_customers = len(CUSTOMERS_DB)
    active_count = 0
    total_balance = 0.0

    for customer in CUSTOMERS_DB:
        if customer.get("is_active") and customer.get("account_status", "Active") == "Active":
            active_count += 1
        total_balance += customer.get("balance", 0.0)

    return {
        "total_customers": total_customers,
        "active_customers": active_count,
        "inactive_customers": total_customers - active_count,
        "total_balance": round(total_balance, 2),
    }


# =============================================================================
# Core Banking Operations (Deposit, Withdrawal, Transfer, Transactions)
# =============================================================================

def _generate_transaction_id() -> int:
    """Helper function to produce next unique transaction ID."""
    if len(TRANSACTIONS_DB) > 0:
        return max(t["transaction_id"] for t in TRANSACTIONS_DB) + 1
    return 1


def _check_account_status_for_banking(customer: dict) -> tuple[bool, str]:
    """
    Evaluates whether an account is eligible to conduct financial operations.
    Demonstrates Boolean logic: checks for 'Frozen', 'Closed', 'Pending', and 'Active' states.
    """
    status = customer.get("account_status", "")
    if status == "Frozen":
        return False, "Your account is frozen. Deposits, withdrawals, and transfers are paused."
    elif status == "Closed":
        return False, "Your account is closed. No further banking operations may be conducted."
    elif status == "Pending":
        return False, "Your account application is pending administrative approval."
    elif status == "Rejected":
        return False, "Your account application has been rejected."
    elif not customer.get("is_active", False) or status != "Active":
        return False, "Your account is not active. Deposits, withdrawals, and transfers are restricted."
    return True, ""


def deposit_money(customer_id: int, amount: float | str) -> tuple[bool, str, float | None]:
    """
    Deposits money into an authenticated customer's account.

    Validation:
    - Customer exists.
    - Customer account is active and not frozen/closed.
    - Amount is numeric and strictly greater than zero.

    Returns:
        tuple[bool, str, float | None]: (success, message, updated_balance)
    """
    customer = get_customer_by_id(customer_id)
    if not customer:
        return False, "Customer account not found.", None

    can_transact, status_msg = _check_account_status_for_banking(customer)
    if not can_transact:
        return False, status_msg, None

    is_valid, valid_amount, err = validate_transaction_amount(amount)
    if not is_valid:
        return False, err, None

    # Perform deposit
    customer["balance"] = round(customer["balance"] + valid_amount, 2)

    # Record transaction
    tx_record = {
        "transaction_id": _generate_transaction_id(),
        "customer_id": customer["customer_id"],
        "transaction_type": "Deposit",
        "type": "Deposit",
        "amount": valid_amount,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reference_account": customer["account_number"],
        "status": "Completed",
    }
    TRANSACTIONS_DB.append(tx_record)

    return True, f"Successfully deposited ${valid_amount:,.2f}. Updated balance: ${customer['balance']:,.2f}.", customer["balance"]


def withdraw_money(customer_id: int, amount: float | str) -> tuple[bool, str, float | None]:
    """
    Withdraws money from an authenticated customer's account.

    Validation:
    - Customer exists.
    - Customer account is active and not frozen/closed.
    - Amount is numeric and strictly greater than zero.
    - Customer must have sufficient balance.

    Returns:
        tuple[bool, str, float | None]: (success, message, updated_balance)
    """
    customer = get_customer_by_id(customer_id)
    if not customer:
        return False, "Customer account not found.", None

    can_transact, status_msg = _check_account_status_for_banking(customer)
    if not can_transact:
        return False, status_msg, None

    is_valid, valid_amount, err = validate_transaction_amount(amount)
    if not is_valid:
        return False, err, None

    # Check sufficient balance
    if customer["balance"] < valid_amount:
        return (
            False,
            f"Insufficient funds. Your available balance is ${customer['balance']:,.2f}.",
            customer["balance"],
        )

    # Deduct funds
    customer["balance"] = round(customer["balance"] - valid_amount, 2)

    # Record transaction
    tx_record = {
        "transaction_id": _generate_transaction_id(),
        "customer_id": customer["customer_id"],
        "transaction_type": "Withdrawal",
        "type": "Withdrawal",
        "amount": valid_amount,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reference_account": customer["account_number"],
        "status": "Completed",
    }
    TRANSACTIONS_DB.append(tx_record)

    return True, f"Successfully withdrew ${valid_amount:,.2f}. Updated balance: ${customer['balance']:,.2f}.", customer["balance"]


def transfer_money(sender_id: int, recipient_account: str, amount: float | str) -> tuple[bool, str, float | None]:
    """
    Transfers funds from an authenticated sender to a valid recipient account.

    Validation:
    - Sender exists and account is active and not frozen/closed.
    - Recipient account is provided, exists, and is active.
    - Amount is numeric and > 0.
    - Sender cannot transfer to their own account.
    - Sender must have sufficient balance.

    Atomic update:
    - If valid, subtracts from sender, adds to recipient, records both debit and credit transactions.

    Returns:
        tuple[bool, str, float | None]: (success, message, sender_updated_balance)
    """
    sender = get_customer_by_id(sender_id)
    if not sender:
        return False, "Sender account not found.", None

    can_transact, status_msg = _check_account_status_for_banking(sender)
    if not can_transact:
        return False, status_msg, None

    if not recipient_account or not isinstance(recipient_account, str) or not recipient_account.strip():
        return False, "Please enter a valid recipient account number.", None

    recipient_clean = recipient_account.strip().upper()

    # Reject self-transfer
    if recipient_clean == sender.get("account_number", "").strip().upper():
        return False, "You cannot transfer money to your own account.", None

    # Find recipient
    recipient = get_customer_by_account_number(recipient_clean)
    if not recipient:
        return False, f"Recipient account '{recipient_clean}' was not found.", None

    recipient_can_transact, rec_status_msg = _check_account_status_for_banking(recipient)
    if not recipient_can_transact:
        return False, f"Recipient account '{recipient_clean}' is currently inactive or pending and cannot receive funds: {rec_status_msg}", None

    # Validate amount
    is_valid, valid_amount, err = validate_transaction_amount(amount)
    if not is_valid:
        return False, err, None

    # Check sender balance
    if sender["balance"] < valid_amount:
        return (
            False,
            f"Insufficient funds for transfer. Your available balance is ${sender['balance']:,.2f}.",
            sender["balance"],
        )

    # Perform atomic transfer
    sender["balance"] = round(sender["balance"] - valid_amount, 2)
    recipient["balance"] = round(recipient["balance"] + valid_amount, 2)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Transaction record for Sender (Debit)
    sender_tx = {
        "transaction_id": _generate_transaction_id(),
        "customer_id": sender["customer_id"],
        "transaction_type": "Transfer (Debit)",
        "type": "Transfer",
        "amount": valid_amount,
        "timestamp": timestamp,
        "reference_account": recipient["account_number"],
        "status": "Completed",
    }
    TRANSACTIONS_DB.append(sender_tx)

    # Transaction record for Recipient (Credit)
    recipient_tx = {
        "transaction_id": _generate_transaction_id(),
        "customer_id": recipient["customer_id"],
        "transaction_type": "Transfer (Credit)",
        "type": "Transfer",
        "amount": valid_amount,
        "timestamp": timestamp,
        "reference_account": sender["account_number"],
        "status": "Completed",
    }
    TRANSACTIONS_DB.append(recipient_tx)

    return (
        True,
        f"Successfully transferred ${valid_amount:,.2f} to {recipient['name']} ({recipient['account_number']}).",
        sender["balance"],
    )


def get_transaction_history(customer_id: int) -> list[dict]:
    """
    Retrieves the chronological transaction history strictly for the authenticated customer.

    Demonstrates:
    - List filtering with list comprehension or loop.
    - Sorting by transaction_id in descending order (newest first).
    - Privacy protection: ensuring one customer cannot view another's transactions.

    Returns:
        list[dict]: List of transaction record dictionaries for the customer.
    """
    customer_transactions = [
        tx for tx in TRANSACTIONS_DB if tx.get("customer_id") == customer_id
    ]

    # Return newest first
    customer_transactions.sort(key=lambda t: t.get("transaction_id", 0), reverse=True)
    return customer_transactions


# =============================================================================
# Administrator Management Services (Customer, Account, Approval, Audit)
# =============================================================================

def get_admin_dashboard_summary() -> dict:
    """
    Calculates comprehensive operational metrics across the banking system.

    Demonstrates:
    - Counting and filtering using logical operators (and, or, not).
    - Accumulating ledger balances across multiple accounts.

    Returns:
        dict: Summary statistics including customers, statuses, and transactions.
    """
    total_customers = len(CUSTOMERS_DB)
    active_accounts = 0
    pending_accounts = 0
    frozen_accounts = 0
    closed_accounts = 0
    total_balance = 0.0

    for customer in CUSTOMERS_DB:
        status = customer.get("account_status", "Active")
        balance = customer.get("balance", 0.0)

        # Logical checks for each state
        if status == "Active" and customer.get("is_active"):
            active_accounts += 1
        elif status == "Pending":
            pending_accounts += 1
        elif status == "Frozen":
            frozen_accounts += 1
        elif status == "Closed":
            closed_accounts += 1

        total_balance += balance

    return {
        "total_customers": total_customers,
        "active_accounts": active_accounts,
        "pending_accounts": pending_accounts,
        "frozen_accounts": frozen_accounts,
        "closed_accounts": closed_accounts,
        "total_transactions": len(TRANSACTIONS_DB),
        "total_balance": round(total_balance, 2),
    }


def search_customers(query: str | None = None, status_filter: str | None = None) -> list[dict]:
    """
    Searches customers by ID, partial name, email, or account number with optional status filtering.

    Demonstrates:
    - Python logical operators: `and`, `or`, and `not`.
    - Case-insensitive string matching using `.lower()`.
    - Multi-criteria conditional evaluation.

    Parameters:
        query (str | None): Search keyword (matches ID, name, email, account_number).
        status_filter (str | None): Optional account status filter ('Active', 'Pending', etc.).

    Returns:
        list[dict]: Filtered list of customer dictionaries.
    """
    # If neither query nor status filter is provided, return all customers
    if not query and (not status_filter or status_filter == "All"):
        return CUSTOMERS_DB

    results = []
    clean_query = query.strip().lower() if query else ""

    for customer in CUSTOMERS_DB:
        # Extract fields for comparison
        customer_id_str = str(customer.get("customer_id", ""))
        name = customer.get("name", "").lower()
        email = customer.get("email", "").lower()
        account_num = customer.get("account_number", "").lower()
        account_status = customer.get("account_status", "Active")

        # 1. Evaluate query criteria using logical OR
        matches_query = False
        if not clean_query:
            matches_query = True
        elif (
            clean_query in name
            or clean_query in email
            or clean_query in account_num
            or clean_query == customer_id_str
            or clean_query == f"#{customer_id_str}"
        ):
            matches_query = True

        # 2. Evaluate status criteria
        matches_status = False
        if not status_filter or status_filter == "All" or status_filter.lower() == account_status.lower():
            matches_status = True

        # 3. Combine both criteria using logical AND
        if matches_query and matches_status:
            results.append(customer)

    return results


def log_audit_event(
    admin_id: str,
    action: str,
    target_type: str,
    target_id: str,
    details: str = "",
    outcome: str = "Success",
) -> dict:
    """
    Appends an immutable audit log entry for administrative activity.

    Parameters:
        admin_id: Username or identifier of the acting administrator.
        action: Standardized event verb (e.g., 'ACCOUNT_APPROVED', 'LOAN_APPROVED').
        target_type: Entity category ('Customer Account', 'Loan Facility', 'Cheque Book').
        target_id: Unique identifier of the affected record.
        details: Contextual details (amounts, reasons, parameters).
        outcome: Result of the action ('Success', 'Failed').
    """
    max_id = 0
    for entry in AUDIT_LOG_DB:
        e_id = entry.get("log_id", 0)
        if isinstance(e_id, int) and e_id > max_id:
            max_id = e_id
    next_id = max_id + 1

    log_entry = {
        "log_id": next_id,
        "admin_id": str(admin_id or "admin"),
        "action": action,
        "target_type": target_type,
        "target_id": str(target_id),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "outcome": outcome,
        "details": details.strip() if details else "",
    }
    AUDIT_LOG_DB.append(log_entry)
    return log_entry


def get_audit_logs(limit: int = 150, action_filter: str = "All") -> list[dict]:
    """
    Retrieves administrative audit records, optionally filtered by action, sorted newest first.
    """
    filtered = []
    clean_action = str(action_filter or "All").strip().upper()

    for entry in AUDIT_LOG_DB:
        if clean_action != "ALL" and entry.get("action", "").upper() != clean_action:
            continue
        filtered.append(dict(entry))

    filtered.sort(key=lambda x: x.get("log_id", 0), reverse=True)
    return filtered[:limit] if limit > 0 else filtered


def approve_customer_account(customer_id: int, admin_id: str = "admin") -> tuple[bool, str]:
    """
    Approves a customer account currently in 'Pending' status.
    Logs an audit event upon success.
    """
    customer = get_customer_by_id(customer_id)
    if not customer:
        return False, "Customer account not found."

    current_status = customer.get("account_status", "")
    if current_status == "Active":
        return False, f"Account #{customer_id} is already active. Only pending accounts can be approved."
    if current_status != "Pending":
        return False, f"Account cannot be approved because current status is '{current_status}'. Only Pending accounts can be approved."

    # Update account status and enable activity
    customer["account_status"] = "Active"
    customer["is_active"] = True

    log_audit_event(
        admin_id=admin_id,
        action="ACCOUNT_APPROVED",
        target_type="Customer Account",
        target_id=str(customer["account_number"]),
        details=f"Customer #{customer_id} ({customer['name']}) account approved to Active.",
    )

    return True, f"Account for {customer['name']} ({customer['account_number']}) has been successfully approved and activated."


def reject_customer_account(customer_id: int, admin_id: str = "admin") -> tuple[bool, str]:
    """
    Rejects a customer account currently in 'Pending' status.
    Logs an audit event upon success.
    """
    customer = get_customer_by_id(customer_id)
    if not customer:
        return False, "Customer account not found."

    current_status = customer.get("account_status", "")
    if current_status != "Pending":
        return False, f"Account cannot be rejected because current status is '{current_status}'. Only Pending accounts can be rejected."

    customer["account_status"] = "Rejected"
    customer["is_active"] = False

    log_audit_event(
        admin_id=admin_id,
        action="ACCOUNT_REJECTED",
        target_type="Customer Account",
        target_id=str(customer["account_number"]),
        details=f"Customer #{customer_id} ({customer['name']}) account application rejected.",
    )

    return True, f"Account for {customer['name']} ({customer['account_number']}) has been rejected."


def freeze_customer_account(customer_id: int, admin_id: str = "admin") -> tuple[bool, str]:
    """
    Freezes an active account to temporarily suspend financial operations.
    Logs an audit event upon success.
    """
    customer = get_customer_by_id(customer_id)
    if not customer:
        return False, "Customer account not found."

    current_status = customer.get("account_status", "")
    if current_status == "Closed":
        return False, "Cannot freeze an account that has already been closed."
    elif current_status == "Frozen":
        return False, "Account is already frozen."
    elif current_status != "Active":
        return False, f"Only Active accounts can be frozen. Current status is '{current_status}'."

    # Update status to Frozen (balance remains exactly intact)
    customer["account_status"] = "Frozen"
    customer["is_active"] = False

    log_audit_event(
        admin_id=admin_id,
        action="ACCOUNT_FROZEN",
        target_type="Customer Account",
        target_id=str(customer["account_number"]),
        details=f"Account {customer['account_number']} placed under administrative freeze.",
    )

    return True, f"Account for {customer['name']} ({customer['account_number']}) has been frozen. All deposit, withdrawal, and transfer operations are suspended."


def unfreeze_customer_account(customer_id: int, admin_id: str = "admin") -> tuple[bool, str]:
    """
    Unfreezes a previously frozen account and restores it to 'Active' status.
    Logs an audit event upon success.
    """
    customer = get_customer_by_id(customer_id)
    if not customer:
        return False, "Customer account not found."

    current_status = customer.get("account_status", "")
    if current_status != "Frozen":
        return False, f"Cannot unfreeze account because current status is '{current_status}'. Only Frozen accounts can be unfrozen."

    customer["account_status"] = "Active"
    customer["is_active"] = True

    log_audit_event(
        admin_id=admin_id,
        action="ACCOUNT_UNFROZEN",
        target_type="Customer Account",
        target_id=str(customer["account_number"]),
        details=f"Account {customer['account_number']} restored to Active status.",
    )

    return True, f"Account for {customer['name']} ({customer['account_number']}) has been unfrozen and returned to Active status."


def close_customer_account(customer_id: int, admin_id: str = "admin") -> tuple[bool, str]:
    """
    Closes a customer account. Preserves historical records.
    Logs an audit event upon success.
    """
    customer = get_customer_by_id(customer_id)
    if not customer:
        return False, "Customer account not found."

    current_status = customer.get("account_status", "")
    if current_status == "Closed":
        return False, "Account is already closed."

    customer["account_status"] = "Closed"
    customer["is_active"] = False

    log_audit_event(
        admin_id=admin_id,
        action="ACCOUNT_CLOSED",
        target_type="Customer Account",
        target_id=str(customer["account_number"]),
        details=f"Account {customer['account_number']} permanently closed.",
    )

    return True, f"Account for {customer['name']} ({customer['account_number']}) has been permanently closed. Historical transactions remain preserved."


def get_all_transactions(filter_type: str | None = None) -> list[dict]:
    """
    Retrieves transaction records for administrative auditing with optional type filtering.

    Demonstrates:
    - Data integrity: Read-only access to transaction history without mutating records.
    - Looking up associated customer details (name and account number) for presentation.
    - Filtering by type: Deposit, Withdrawal, Transfer.
    """
    enriched_transactions = []

    for tx in TRANSACTIONS_DB:
        # Clone record dictionary so original cannot be altered accidentally
        record = dict(tx)

        # Lookup customer name for context
        cust = get_customer_by_id(tx.get("customer_id", 0))
        record["customer_name"] = cust["name"] if cust else "Unknown Customer"
        record["customer_account"] = cust["account_number"] if cust else "N/A"

        # Apply filtering with logical operators
        tx_type = record.get("transaction_type") or record.get("type", "")
        record["transaction_type"] = tx_type
        record["type"] = record.get("type") or tx_type

        if not filter_type or filter_type == "All":
            enriched_transactions.append(record)
        elif filter_type == "Transfer" and "Transfer" in tx_type:
            enriched_transactions.append(record)
        elif filter_type.lower() == tx_type.lower():
            enriched_transactions.append(record)

    # Sort in reverse chronological order (newest transaction first)
    enriched_transactions.sort(key=lambda t: t.get("transaction_id", 0), reverse=True)
    return enriched_transactions


# =============================================================================
# Phase 5: Loan Management System Services
# =============================================================================

def calculate_loan_repayment_details(
    principal: float | Decimal | int,
    annual_interest_rate: float | Decimal | int,
    tenure_months: int,
) -> dict:
    """
    Calculates the estimated monthly instalment (EMI), total repayment, and estimated total interest.
    Uses the standard reducing-balance EMI formula:
        EMI = [P * r * (1 + r)^n] / [(1 + r)^n - 1]
    where:
        P = principal amount
        r = monthly interest rate = (annual_interest_rate / 100) / 12
        n = loan tenure in months

    Handles zero-interest loans separately to prevent ZeroDivisionError:
        EMI = P / n
    Uses Python's Decimal type for financial calculations to minimize float rounding errors.

    Returns:
        dict: {
            "emi": float,
            "total_repayment": float,
            "total_interest": float
        }
    """
    P = Decimal(str(principal))
    n = Decimal(str(tenure_months))
    rate_percent = Decimal(str(annual_interest_rate))

    if n <= 0 or P <= 0:
        return {
            "emi": 0.0,
            "total_repayment": 0.0,
            "total_interest": 0.0,
        }

    # Zero-interest loan calculation (avoids division by zero)
    if rate_percent == Decimal("0"):
        emi = (P / n).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_repayment = (emi * n).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_interest = Decimal("0.00")
    else:
        # Standard reducing-balance formula
        r_float = float(rate_percent) / (12.0 * 100.0)
        n_int = int(tenure_months)
        compound = (1.0 + r_float) ** n_int
        emi_float = float(P) * (r_float * compound) / (compound - 1.0)
        emi = Decimal(str(round(emi_float, 2))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_repayment = (emi * Decimal(str(n_int))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_interest = (total_repayment - P).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if total_interest < Decimal("0.00"):
            total_interest = Decimal("0.00")

    return {
        "emi": float(emi),
        "total_repayment": float(total_repayment),
        "total_interest": float(total_interest),
    }


def _generate_loan_id() -> tuple[int, str]:
    """Generates the next unique integer loan ID and formatted application code (e.g. 'LN-1006')."""
    if len(LOANS_DB) > 0:
        next_id = max(l["loan_id"] for l in LOANS_DB) + 1
    else:
        next_id = 1
    app_id = f"LN-{1000 + next_id}"
    return next_id, app_id


def apply_for_loan(
    customer_id: int,
    loan_type: str,
    requested_amount: float | str,
    tenure_months: int | str,
    purpose: str,
    monthly_income: float | str,
) -> tuple[bool, str, dict | None]:
    """
    Processes a customer loan application submission.

    Validation:
    - Customer exists and account is not frozen/closed.
    - Fields are validated via validate_loan_application_input().
    - Sets initial status strictly to 'Pending'.

    Returns:
        tuple[bool, str, dict | None]: (success, message, created_loan_dict)
    """
    customer = get_customer_by_id(customer_id)
    if not customer:
        return False, "Customer account not found.", None

    # Check account status (frozen/closed accounts cannot apply for new credit)
    can_transact, status_msg = _check_account_status_for_banking(customer)
    if not can_transact and customer.get("account_status") in ["Frozen", "Closed"]:
        return False, f"Loan applications are restricted: {status_msg}", None

    is_valid, errors, sanitized = validate_loan_application_input(
        loan_type=loan_type,
        requested_amount=requested_amount,
        tenure_months=tenure_months,
        purpose=purpose,
        monthly_income=monthly_income,
    )

    if not is_valid:
        return False, errors[0] if errors else "Invalid loan application parameters.", None

    next_id, app_code = _generate_loan_id()

    new_loan = {
        "loan_id": next_id,
        "application_id": app_code,
        "customer_id": customer["customer_id"],
        "customer_name": customer["name"],
        "loan_type": sanitized["loan_type"],
        "requested_amount": sanitized["requested_amount"],
        "tenure_months": sanitized["tenure_months"],
        "purpose": sanitized["purpose"],
        "monthly_income": sanitized["monthly_income"],
        "application_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Pending",
        "approved_amount": None,
        "annual_interest_rate": None,
        "approved_tenure_months": None,
        "estimated_emi": None,
        "total_repayment": None,
        "total_interest": None,
        "admin_decision_date": None,
        "admin_notes": None,
        "rejection_reason": None,
    }

    LOANS_DB.append(new_loan)

    return (
        True,
        f"Loan application {app_code} for ${sanitized['requested_amount']:,.2f} submitted successfully! Status is currently Pending review.",
        new_loan,
    )


def get_customer_loans(customer_id: int) -> list[dict]:
    """
    Retrieves all loan applications associated strictly with a customer ID.
    Sorted in reverse chronological order (newest application first).
    """
    cust_loans = [loan for loan in LOANS_DB if loan.get("customer_id") == customer_id]
    cust_loans.sort(key=lambda l: l.get("loan_id", 0), reverse=True)
    return cust_loans


def get_loan_by_id(loan_identifier: int | str) -> dict | None:
    """
    Retrieves a loan application by numeric loan_id or application_id code (e.g. 'LN-1001').
    """
    if loan_identifier is None:
        return None

    str_ident = str(loan_identifier).strip().upper()
    int_ident = safe_int(loan_identifier)

    for loan in LOANS_DB:
        if str(loan.get("application_id", "")).upper() == str_ident:
            return loan
        if int_ident is not None and loan.get("loan_id") == int_ident:
            return loan

    return None


def cancel_loan_application(loan_id: int | str, customer_id: int) -> tuple[bool, str]:
    """
    Allows a customer to cancel their own pending loan application.

    Security & Validation:
    - Customer cannot cancel another customer's loan.
    - Only applications in 'Pending' status can be cancelled.
    """
    loan = get_loan_by_id(loan_id)
    if not loan:
        return False, "Loan application not found."

    # Prevent customer from modifying another customer's loan
    if loan.get("customer_id") != customer_id:
        return False, "Unauthorized access. You may only manage your own loan applications."

    if loan.get("status") != "Pending":
        return False, f"Only pending applications can be cancelled. Current status is '{loan.get('status')}'."

    loan["status"] = "Cancelled"
    loan["admin_decision_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return True, f"Loan application {loan['application_id']} has been cancelled."


def get_all_loans(
    search_query: str = "",
    status_filter: str = "All",
    type_filter: str = "All",
) -> list[dict]:
    """
    Retrieves loan applications for admin management with search and multi-criteria filtering.
    """
    results: list[dict] = []
    clean_query = str(search_query or "").strip().lower()
    clean_status = str(status_filter or "All").strip().capitalize()
    clean_type = str(type_filter or "All").strip().capitalize()

    for loan in LOANS_DB:
        # Clone dictionary and enrich with customer account number
        rec = dict(loan)
        cust = get_customer_by_id(loan.get("customer_id", 0))
        rec["customer_account"] = cust["account_number"] if cust else "N/A"
        rec["customer_email"] = cust["email"] if cust else "N/A"

        # 1. Search query match
        matches_search = False
        if not clean_query:
            matches_search = True
        else:
            app_id = str(rec.get("application_id", "")).lower()
            name = str(rec.get("customer_name", "")).lower()
            cust_id = str(rec.get("customer_id", "")).lower()
            acc_num = str(rec.get("customer_account", "")).lower()
            purpose = str(rec.get("purpose", "")).lower()
            loan_type = str(rec.get("loan_type", "")).lower()

            if (
                clean_query in app_id
                or clean_query in name
                or clean_query in cust_id
                or clean_query in acc_num
                or clean_query in purpose
                or clean_query in loan_type
            ):
                matches_search = True

        # 2. Status match
        matches_status = False
        loan_st = str(rec.get("status", ""))
        if clean_status == "All" or clean_status.lower() == loan_st.lower():
            matches_status = True

        # 3. Type match
        matches_type = False
        loan_tp = str(rec.get("loan_type", ""))
        if clean_type == "All" or clean_type.lower() == loan_tp.lower():
            matches_type = True

        if matches_search and matches_status and matches_type:
            results.append(rec)

    results.sort(key=lambda l: l.get("loan_id", 0), reverse=True)
    return results


def get_admin_loan_summary() -> dict:
    """
    Calculates summary card metrics for the Admin Loans console:
    - Total Applications
    - Pending Applications
    - Approved Loans
    - Rejected Applications
    - Active Loans
    """
    total_applications = len(LOANS_DB)
    pending_applications = 0
    approved_loans = 0
    rejected_applications = 0
    active_loans = 0
    cancelled_applications = 0
    total_approved_amount = 0.0

    for loan in LOANS_DB:
        st = loan.get("status", "")
        if st == "Pending":
            pending_applications += 1
        elif st == "Approved":
            approved_loans += 1
            total_approved_amount += loan.get("approved_amount", 0.0) or 0.0
        elif st == "Rejected":
            rejected_applications += 1
        elif st == "Active":
            active_loans += 1
            total_approved_amount += loan.get("approved_amount", 0.0) or 0.0
        elif st == "Cancelled":
            cancelled_applications += 1

    return {
        "total_applications": total_applications,
        "pending_applications": pending_applications,
        "approved_loans": approved_loans,
        "rejected_applications": rejected_applications,
        "active_loans": active_loans,
        "cancelled_applications": cancelled_applications,
        "total_approved_amount": round(total_approved_amount, 2),
    }


def approve_loan_application(
    loan_id: int | str,
    approved_amount: float | str,
    annual_interest_rate: float | str,
    tenure_months: int | str,
    admin_notes: str = "",
    admin_id: str = "admin",
) -> tuple[bool, str]:
    """
    Approves a pending loan application and computes reducing-balance EMI.
    Logs an audit event upon success.

    Safety:
    - Only applications in 'Pending' status can be approved (prevents repeated decisions).
    - Approved amount cannot exceed requested amount.
    - Zero-interest loans supported.
    """
    loan = get_loan_by_id(loan_id)
    if not loan:
        return False, "Loan application not found."

    # Guard: Prevent repeated decisions
    if loan.get("status") != "Pending":
        return (
            False,
            f"Application cannot be approved because current status is '{loan.get('status')}'. Only pending applications can be processed.",
        )

    # Validate approval parameters
    is_valid, errors, sanitized = validate_loan_approval_input(
        requested_amount=loan["requested_amount"],
        approved_amount=approved_amount,
        interest_rate=annual_interest_rate,
        tenure_months=tenure_months,
    )

    if not is_valid:
        return False, errors[0] if errors else "Invalid approval parameters."

    # Calculate EMI repayment details
    repayment = calculate_loan_repayment_details(
        principal=sanitized["approved_amount"],
        annual_interest_rate=sanitized["annual_interest_rate"],
        tenure_months=sanitized["approved_tenure_months"],
    )

    loan["status"] = "Approved"
    loan["approved_amount"] = sanitized["approved_amount"]
    loan["annual_interest_rate"] = sanitized["annual_interest_rate"]
    loan["approved_tenure_months"] = sanitized["approved_tenure_months"]
    loan["estimated_emi"] = repayment["emi"]
    loan["total_repayment"] = repayment["total_repayment"]
    loan["total_interest"] = repayment["total_interest"]
    loan["admin_decision_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    loan["admin_notes"] = admin_notes.strip() if admin_notes else "Application authorized by branch administration."
    loan["rejection_reason"] = None

    log_audit_event(
        admin_id=admin_id,
        action="LOAN_APPROVED",
        target_type="Loan Facility",
        target_id=str(loan.get("application_id")),
        details=f"Approved ${sanitized['approved_amount']:,.2f} at {sanitized['annual_interest_rate']}% p.a. for {sanitized['approved_tenure_months']} mos.",
    )

    return (
        True,
        f"Loan {loan['application_id']} successfully approved for ${sanitized['approved_amount']:,.2f} at {sanitized['annual_interest_rate']}% p.a. (Estimated EMI: ${repayment['emi']:,.2f}/mo).",
    )


def reject_loan_application(
    loan_id: int | str,
    rejection_reason: str,
    admin_id: str = "admin",
) -> tuple[bool, str]:
    """
    Rejects a pending loan application with a recorded reason.
    Logs an audit event upon success.

    Safety:
    - Only applications in 'Pending' status can be rejected (prevents repeated decisions).
    """
    loan = get_loan_by_id(loan_id)
    if not loan:
        return False, "Loan application not found."

    # Guard: Prevent repeated decisions
    if loan.get("status") != "Pending":
        return (
            False,
            f"Application cannot be rejected because current status is '{loan.get('status')}'. Only pending applications can be processed.",
        )

    clean_reason = str(rejection_reason or "").strip()
    if not clean_reason or len(clean_reason) < 3:
        return False, "Please provide a valid rejection reason (minimum 3 characters)."

    loan["status"] = "Rejected"
    loan["rejection_reason"] = clean_reason
    loan["admin_decision_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_audit_event(
        admin_id=admin_id,
        action="LOAN_REJECTED",
        target_type="Loan Facility",
        target_id=str(loan.get("application_id")),
        details=f"Rejection reason: {clean_reason}",
    )

    return True, f"Loan application {loan['application_id']} has been rejected."


def activate_loan(loan_id: int | str, admin_id: str = "admin") -> tuple[bool, str]:
    """
    Transitions an Approved loan into Active portfolio status.
    Logs an audit event upon success.
    """
    loan = get_loan_by_id(loan_id)
    if not loan:
        return False, "Loan application not found."

    if loan.get("status") != "Approved":
        return False, f"Only Approved loans can be activated. Current status is '{loan.get('status')}'."

    loan["status"] = "Active"

    log_audit_event(
        admin_id=admin_id,
        action="LOAN_ACTIVATED",
        target_type="Loan Facility",
        target_id=str(loan.get("application_id")),
        details=f"Loan {loan.get('application_id')} transitioned to Active portfolio status.",
    )

    return True, f"Loan {loan['application_id']} is now marked as Active."


# =============================================================================
# CHEQUE BOOK REQUEST & DISPATCH OPERATIONS
# =============================================================================


def _generate_cheque_request_id() -> tuple[int, str]:
    """
    Generates a unique request_id integer and unique formatted reference code.
    Example: (7, 'CHQ-1007')

    Demonstrates:
    - Linear iteration over list of dicts to find maximum existing ID.
    - Python f-string formatting.
    """
    max_id = 0
    for req in CHEQUE_REQUESTS_DB:
        r_id = req.get("request_id", 0)
        if isinstance(r_id, int) and r_id > max_id:
            max_id = r_id
    next_id = max_id + 1
    return next_id, f"CHQ-{1000 + next_id}"


def request_cheque_book(
    customer_id: int,
    account_number: str,
    leaves: any,
    delivery_notes: str = "",
) -> tuple[bool, str, dict | None]:
    """
    Creates a new cheque book request for an authenticated customer's active account.

    Validations & Business Rules:
    - Customer record must exist.
    - Selected account must belong to the customer.
    - Selected account must have 'Active' status (ineligible for Pending, Frozen, Closed).
    - Leaf count must be exactly 10, 25, or 50.
    - Automatically assigns sequential reference ID (CHQ-100X).
    - Sets initial status to 'Pending'.

    Returns:
        (success: bool, message: str, created_request: dict | None)
    """
    customer = get_customer_by_id(customer_id)
    if not customer:
        return False, "Customer record not found.", None

    customer_accounts = [
        {
            "account_number": customer.get("account_number"),
            "account_type": customer.get("account_type"),
            "account_status": customer.get("account_status", "Active"),
            "is_active": customer.get("is_active", True),
        }
    ]

    is_valid, errors, sanitized = validate_cheque_request_input(
        account_number=account_number,
        leaves=leaves,
        customer_accounts=customer_accounts,
    )

    if not is_valid:
        return False, errors[0] if errors else "Invalid request data.", None

    next_id, ref_id = _generate_cheque_request_id()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_request = {
        "request_id": next_id,
        "cheque_request_id": ref_id,
        "customer_id": customer_id,
        "customer_name": customer.get("name", "Valued Customer"),
        "account_number": sanitized["account_number"],
        "leaves": sanitized["leaves"],
        "request_date": now_str,
        "status": "Pending",
        "admin_decision_date": None,
        "admin_notes": delivery_notes.strip() if delivery_notes else None,
        "rejection_reason": None,
    }

    CHEQUE_REQUESTS_DB.append(new_request)
    return (
        True,
        f"Cheque book request {ref_id} for {sanitized['leaves']} leaves submitted successfully.",
        new_request,
    )


def get_customer_cheque_requests(customer_id: int) -> list[dict]:
    """
    Retrieves all cheque book requests belonging to the given customer ID.
    Includes masked account numbers for privacy and sorts newest first.
    """
    requests: list[dict] = []
    for req in CHEQUE_REQUESTS_DB:
        if req.get("customer_id") == customer_id:
            req_copy = dict(req)
            req_copy["masked_account_number"] = mask_account_number(req.get("account_number", ""))
            requests.append(req_copy)

    requests.sort(key=lambda r: r.get("request_id", 0), reverse=True)
    return requests


def get_cheque_request_by_id(request_id: int | str) -> dict | None:
    """
    Finds a cheque book request by internal integer request_id or reference code (e.g. 'CHQ-1001').
    """
    if isinstance(request_id, int) or (isinstance(request_id, str) and request_id.isdigit()):
        req_int = int(request_id)
        for req in CHEQUE_REQUESTS_DB:
            if req.get("request_id") == req_int:
                return req

    if isinstance(request_id, str):
        clean_code = request_id.strip().upper()
        for req in CHEQUE_REQUESTS_DB:
            if req.get("cheque_request_id", "").upper() == clean_code:
                return req

    return None


def cancel_cheque_request(request_id: int | str, customer_id: int) -> tuple[bool, str]:
    """
    Allows a customer to cancel their own Pending cheque book request.

    Guards:
    1. Request must exist.
    2. Must belong to the requesting customer (ownership verification).
    3. Must currently be in 'Pending' status.
    """
    req = get_cheque_request_by_id(request_id)
    if not req:
        return False, "Cheque book request not found."

    # Ownership check
    if req.get("customer_id") != customer_id:
        return False, "Access denied: You are not authorized to cancel this cheque book request."

    # Status check
    current_status = req.get("status")
    if current_status != "Pending":
        return False, f"Only Pending requests can be cancelled. Current status is '{current_status}'."

    req["status"] = "Cancelled"
    req["admin_decision_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    req["admin_notes"] = "Cancelled by account holder."

    return True, f"Cheque book request {req.get('cheque_request_id')} has been cancelled."


def get_all_cheque_requests(
    search_query: str = "",
    status_filter: str = "All",
) -> list[dict]:
    """
    Retrieves all cheque requests with optional search query and status filter.
    Search matches request ID, customer ID, customer name, or account number.
    """
    results: list[dict] = []
    clean_query = str(search_query or "").strip().lower()
    clean_status = str(status_filter or "All").strip()

    for req in CHEQUE_REQUESTS_DB:
        # Status filter
        if clean_status != "All" and req.get("status", "").lower() != clean_status.lower():
            continue

        # Search query filter
        if clean_query:
            req_id_str = str(req.get("request_id", "")).lower()
            code_str = str(req.get("cheque_request_id", "")).lower()
            cust_id_str = str(req.get("customer_id", "")).lower()
            name_str = str(req.get("customer_name", "")).lower()
            acc_str = str(req.get("account_number", "")).lower()

            matches = (
                clean_query in req_id_str
                or clean_query in code_str
                or clean_query in cust_id_str
                or clean_query in name_str
                or clean_query in acc_str
            )
            if not matches:
                continue

        req_copy = dict(req)
        req_copy["masked_account_number"] = mask_account_number(req.get("account_number", ""))
        results.append(req_copy)

    results.sort(key=lambda r: r.get("request_id", 0), reverse=True)
    return results


def get_admin_cheque_summary() -> dict:
    """
    Computes summary metrics for admin dashboard cards:
    - total_requests
    - pending_requests
    - approved_requests
    - rejected_requests
    - completed_requests
    - cancelled_requests
    """
    summary = {
        "total_requests": len(CHEQUE_REQUESTS_DB),
        "pending_requests": 0,
        "approved_requests": 0,
        "rejected_requests": 0,
        "completed_requests": 0,
        "cancelled_requests": 0,
    }

    for req in CHEQUE_REQUESTS_DB:
        status = req.get("status")
        if status == "Pending":
            summary["pending_requests"] += 1
        elif status == "Approved":
            summary["approved_requests"] += 1
        elif status == "Rejected":
            summary["rejected_requests"] += 1
        elif status == "Completed":
            summary["completed_requests"] += 1
        elif status == "Cancelled":
            summary["cancelled_requests"] += 1

    return summary


def approve_cheque_request(
    request_id: int | str,
    admin_notes: str = "",
    admin_id: str = "admin",
) -> tuple[bool, str]:
    """
    Admin action: Approves a pending cheque book request.
    Allowed transition: Pending -> Approved.
    Repeated or invalid status transitions are rejected.
    Logs an audit event upon success.
    """
    req = get_cheque_request_by_id(request_id)
    if not req:
        return False, "Cheque book request not found."

    current_status = req.get("status")
    if current_status != "Pending":
        return (
            False,
            f"Cannot approve request with status '{current_status}'. Only Pending requests can be approved.",
        )

    req["status"] = "Approved"
    req["admin_decision_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if admin_notes and admin_notes.strip():
        req["admin_notes"] = admin_notes.strip()
    else:
        req["admin_notes"] = "Request approved by branch administration. Queued for printing."
    req["rejection_reason"] = None

    log_audit_event(
        admin_id=admin_id,
        action="CHEQUE_APPROVED",
        target_type="Cheque Book",
        target_id=str(req.get("cheque_request_id")),
        details=f"Approved {req.get('leaves')} leaves for account {req.get('account_number')}.",
    )

    return True, f"Cheque book request {req.get('cheque_request_id')} has been approved."


def reject_cheque_request(
    request_id: int | str,
    rejection_reason: str,
    admin_id: str = "admin",
) -> tuple[bool, str]:
    """
    Admin action: Rejects a pending cheque book request.
    Allowed transition: Pending -> Rejected.
    Requires a valid rejection reason.
    Logs an audit event upon success.
    """
    req = get_cheque_request_by_id(request_id)
    if not req:
        return False, "Cheque book request not found."

    current_status = req.get("status")
    if current_status != "Pending":
        return (
            False,
            f"Cannot reject request with status '{current_status}'. Only Pending requests can be processed.",
        )

    is_valid, err_msg = validate_cheque_rejection_reason(rejection_reason)
    if not is_valid:
        return False, err_msg

    req["status"] = "Rejected"
    req["rejection_reason"] = rejection_reason.strip()
    req["admin_decision_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_audit_event(
        admin_id=admin_id,
        action="CHEQUE_REJECTED",
        target_type="Cheque Book",
        target_id=str(req.get("cheque_request_id")),
        details=f"Reason: {rejection_reason.strip()}",
    )

    return True, f"Cheque book request {req.get('cheque_request_id')} has been rejected."


def complete_cheque_request(
    request_id: int | str,
    admin_notes: str = "",
    admin_id: str = "admin",
) -> tuple[bool, str]:
    """
    Admin action: Marks an Approved cheque book request as Completed (e.g., printed and dispatched).
    Allowed transition: Approved -> Completed.
    Logs an audit event upon success.
    """
    req = get_cheque_request_by_id(request_id)
    if not req:
        return False, "Cheque book request not found."

    current_status = req.get("status")
    if current_status != "Approved":
        return (
            False,
            f"Cannot complete request with status '{current_status}'. Only Approved requests can be marked as Completed.",
        )

    req["status"] = "Completed"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    req["admin_decision_date"] = now_str
    if admin_notes and admin_notes.strip():
        req["admin_notes"] = admin_notes.strip()
    else:
        req["admin_notes"] = "Cheque book printed and handed over / dispatched."

    log_audit_event(
        admin_id=admin_id,
        action="CHEQUE_COMPLETED",
        target_type="Cheque Book",
        target_id=str(req.get("cheque_request_id")),
        details=f"Completed {req.get('leaves')} leaves dispatch for {req.get('account_number')}.",
    )

    return True, f"Cheque book request {req.get('cheque_request_id')} is now marked as Completed."


# =============================================================================
# PHASE 7: COMPREHENSIVE REPORTS & CSV EXPORT SERVICES
# =============================================================================


def _is_date_in_range(date_str: str | None, start_date: str | None, end_date: str | None) -> bool:
    """
    Helper function to check if an ISO formatted datetime string falls within [start_date, end_date].
    Uses string comparison on YYYY-MM-DD components.
    """
    if not date_str:
        return True
    try:
        rec_date = str(date_str).split(" ")[0].strip()
        if start_date and rec_date < start_date:
            return False
        if end_date and rec_date > end_date:
            return False
        return True
    except Exception:
        return True


def generate_admin_comprehensive_report(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """
    Aggregates comprehensive operational metrics across the banking platform.
    Demonstrates:
    - Reusable Python functions for summaries and aggregations.
    - Python lists, dicts, arithmetic operations, and list comprehensions.
    - Date filtering across transactions, loans, and cheque requests.
    - Zero modification to existing customer balances or ledger records.
    """
    # 1. Customer Metrics (Current Snapshot)
    total_customers = len(CUSTOMERS_DB)
    active_accounts = 0
    pending_accounts = 0
    frozen_accounts = 0
    rejected_accounts = 0
    closed_accounts = 0
    total_balance = 0.0

    for c in CUSTOMERS_DB:
        status = str(c.get("account_status", "Active")).capitalize()
        if status == "Active":
            active_accounts += 1
        elif status == "Pending":
            pending_accounts += 1
        elif status == "Frozen":
            frozen_accounts += 1
        elif status == "Rejected":
            rejected_accounts += 1
        elif status == "Closed":
            closed_accounts += 1
        total_balance += float(c.get("balance", 0.0))

    # 2. Transaction Metrics (Date-Range Filtered)
    filtered_transactions = []
    total_deposits = 0.0
    total_withdrawals = 0.0
    total_transfers = 0.0
    deposit_count = 0
    withdrawal_count = 0
    transfer_count = 0

    for tx in TRANSACTIONS_DB:
        tx_time = tx.get("timestamp")
        if _is_date_in_range(tx_time, start_date, end_date):
            filtered_transactions.append(tx)
            tx_type = str(tx.get("transaction_type") or tx.get("type") or "").capitalize()
            amt = float(tx.get("amount", 0.0))
            is_successful = tx.get("status") != "Failed"

            if tx_type == "Deposit":
                deposit_count += 1
                if is_successful:
                    total_deposits += amt
            elif tx_type == "Withdrawal":
                withdrawal_count += 1
                if is_successful:
                    total_withdrawals += amt
            elif tx_type == "Transfer":
                transfer_count += 1
                if is_successful:
                    total_transfers += amt

    # 3. Loan Application Metrics (Date-Range Filtered by application_date)
    filtered_loans = []
    loan_status_counts = {
        "Pending": 0,
        "Approved": 0,
        "Active": 0,
        "Rejected": 0,
        "Cancelled": 0,
    }
    total_loan_requested = 0.0
    total_loan_approved = 0.0
    approved_loans_count = 0

    for loan in LOANS_DB:
        app_date = loan.get("application_date")
        if _is_date_in_range(app_date, start_date, end_date):
            filtered_loans.append(loan)
            st = str(loan.get("status", "Pending")).capitalize()
            loan_status_counts[st] = loan_status_counts.get(st, 0) + 1
            total_loan_requested += float(loan.get("requested_amount", 0.0))

            appr_amt = loan.get("approved_amount")
            if appr_amt is not None and st in ("Approved", "Active"):
                total_loan_approved += float(appr_amt)
                approved_loans_count += 1

    avg_approved_amount = (
        round(total_loan_approved / approved_loans_count, 2)
        if approved_loans_count > 0
        else 0.0
    )

    # 4. Cheque Request Metrics (Date-Range Filtered by request_date)
    filtered_cheques = []
    cheque_status_counts = {
        "Pending": 0,
        "Approved": 0,
        "Rejected": 0,
        "Completed": 0,
        "Cancelled": 0,
    }
    leaves_breakdown = {10: 0, 25: 0, 50: 0}

    for chq in CHEQUE_REQUESTS_DB:
        chq_date = chq.get("request_date")
        if _is_date_in_range(chq_date, start_date, end_date):
            filtered_cheques.append(chq)
            st = str(chq.get("status", "Pending")).capitalize()
            cheque_status_counts[st] = cheque_status_counts.get(st, 0) + 1
            leaf_cnt = chq.get("leaves", 10)
            if leaf_cnt in leaves_breakdown:
                leaves_breakdown[leaf_cnt] += 1

    # 5. Audit Log Count
    total_audit_logs = len(AUDIT_LOG_DB)

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "start_date": start_date or "",
        "end_date": end_date or "",
        "customers": {
            "total_registered": total_customers,
            "active_accounts": active_accounts,
            "pending_accounts": pending_accounts,
            "frozen_accounts": frozen_accounts,
            "rejected_accounts": rejected_accounts,
            "closed_accounts": closed_accounts,
            "total_balance": round(total_balance, 2),
        },
        "transactions": {
            "total_count": len(filtered_transactions),
            "total_deposits": round(total_deposits, 2),
            "total_withdrawals": round(total_withdrawals, 2),
            "total_transfers": round(total_transfers, 2),
            "deposit_count": deposit_count,
            "withdrawal_count": withdrawal_count,
            "transfer_count": transfer_count,
            "records": filtered_transactions[:50],  # Latest 50 for dashboard table preview
        },
        "loans": {
            "total_applications": len(filtered_loans),
            "status_counts": loan_status_counts,
            "total_requested_amount": round(total_loan_requested, 2),
            "total_approved_amount": round(total_loan_approved, 2),
            "average_approved_amount": avg_approved_amount,
            "records": filtered_loans[:50],
        },
        "cheques": {
            "total_requests": len(filtered_cheques),
            "status_counts": cheque_status_counts,
            "leaves_breakdown": leaves_breakdown,
            "records": filtered_cheques[:50],
        },
        "audit": {
            "total_logs": total_audit_logs,
            "recent_logs": AUDIT_LOG_DB[-10:] if AUDIT_LOG_DB else [],
        },
    }


def export_customers_csv(
    status_filter: str = "All",
) -> str:
    """
    Exports customer records into safe CSV format.
    Excludes sensitive passwords, hashes, and session attributes.
    Applies formula injection sanitization to all cell values.
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    # Safe CSV headers (strictly no passwords or security tokens)
    headers = [
        "Customer ID",
        "Full Name",
        "Email Address",
        "Phone Number",
        "Account Number",
        "Account Type",
        "Account Status",
        "Available Balance ($)",
        "Is Active",
    ]
    writer.writerow([sanitize_csv_value(h) for h in headers])

    clean_filter = (status_filter or "All").strip().capitalize()
    for c in CUSTOMERS_DB:
        acc_status = str(c.get("account_status", "Active")).capitalize()
        if clean_filter != "All" and acc_status != clean_filter:
            continue

        row = [
            sanitize_csv_value(c.get("customer_id")),
            sanitize_csv_value(c.get("name")),
            sanitize_csv_value(c.get("email")),
            sanitize_csv_value(c.get("phone")),
            sanitize_csv_value(c.get("account_number")),
            sanitize_csv_value(c.get("account_type")),
            sanitize_csv_value(acc_status),
            sanitize_csv_value(f"{float(c.get('balance', 0.0)):,.2f}"),
            sanitize_csv_value("Yes" if c.get("is_active") else "No"),
        ]
        writer.writerow(row)

    return output.getvalue()


def export_transactions_csv(
    start_date: str | None = None,
    end_date: str | None = None,
    transaction_type: str = "All",
) -> str:
    """
    Exports transaction history into safe CSV format.
    Filters by date range and transaction type.
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    headers = [
        "Transaction ID",
        "Customer ID",
        "Transaction Type",
        "Amount ($)",
        "Timestamp",
        "Reference / Counterpart Account",
        "Status",
    ]
    writer.writerow([sanitize_csv_value(h) for h in headers])

    clean_type = (transaction_type or "All").strip().capitalize()
    for tx in TRANSACTIONS_DB:
        tx_time = tx.get("timestamp")
        if not _is_date_in_range(tx_time, start_date, end_date):
            continue

        t_type = str(tx.get("transaction_type") or tx.get("type") or "").capitalize()
        if clean_type != "All" and t_type != clean_type:
            continue

        row = [
            sanitize_csv_value(tx.get("transaction_id")),
            sanitize_csv_value(tx.get("customer_id")),
            sanitize_csv_value(t_type),
            sanitize_csv_value(f"{float(tx.get('amount', 0.0)):,.2f}"),
            sanitize_csv_value(tx_time),
            sanitize_csv_value(tx.get("reference_account", "N/A")),
            sanitize_csv_value(tx.get("status", "Completed")),
        ]
        writer.writerow(row)

    return output.getvalue()


def export_loans_csv(
    start_date: str | None = None,
    end_date: str | None = None,
    status_filter: str = "All",
) -> str:
    """
    Exports loan application portfolio into safe CSV format.
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    headers = [
        "Application ID",
        "Customer ID",
        "Customer Name",
        "Loan Type",
        "Requested Amount ($)",
        "Tenure (Months)",
        "Monthly Income ($)",
        "Status",
        "Approved Amount ($)",
        "Interest Rate (%)",
        "Estimated EMI ($)",
        "Application Date",
        "Decision Date",
    ]
    writer.writerow([sanitize_csv_value(h) for h in headers])

    clean_status = (status_filter or "All").strip().capitalize()
    for loan in LOANS_DB:
        app_date = loan.get("application_date")
        if not _is_date_in_range(app_date, start_date, end_date):
            continue

        st = str(loan.get("status", "Pending")).capitalize()
        if clean_status != "All" and st != clean_status:
            continue

        appr_amt = loan.get("approved_amount")
        appr_str = f"{float(appr_amt):,.2f}" if appr_amt is not None else "N/A"
        rate = loan.get("annual_interest_rate")
        rate_str = f"{float(rate):.2f}%" if rate is not None else "N/A"
        emi = loan.get("estimated_emi")
        emi_str = f"{float(emi):,.2f}" if emi is not None else "N/A"

        row = [
            sanitize_csv_value(loan.get("application_id")),
            sanitize_csv_value(loan.get("customer_id")),
            sanitize_csv_value(loan.get("customer_name")),
            sanitize_csv_value(loan.get("loan_type")),
            sanitize_csv_value(f"{float(loan.get('requested_amount', 0.0)):,.2f}"),
            sanitize_csv_value(loan.get("tenure_months")),
            sanitize_csv_value(f"{float(loan.get('monthly_income', 0.0)):,.2f}"),
            sanitize_csv_value(st),
            sanitize_csv_value(appr_str),
            sanitize_csv_value(rate_str),
            sanitize_csv_value(emi_str),
            sanitize_csv_value(app_date),
            sanitize_csv_value(loan.get("admin_decision_date") or "Pending"),
        ]
        writer.writerow(row)

    return output.getvalue()


def export_cheques_csv(
    start_date: str | None = None,
    end_date: str | None = None,
    status_filter: str = "All",
) -> str:
    """
    Exports cheque book requests into safe CSV format.
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    headers = [
        "Request ID",
        "Reference ID",
        "Customer ID",
        "Customer Name",
        "Account Number",
        "Leaves",
        "Request Date",
        "Status",
        "Decision Date",
        "Admin Notes",
    ]
    writer.writerow([sanitize_csv_value(h) for h in headers])

    clean_status = (status_filter or "All").strip().capitalize()
    for chq in CHEQUE_REQUESTS_DB:
        req_date = chq.get("request_date")
        if not _is_date_in_range(req_date, start_date, end_date):
            continue

        st = str(chq.get("status", "Pending")).capitalize()
        if clean_status != "All" and st != clean_status:
            continue

        row = [
            sanitize_csv_value(chq.get("request_id")),
            sanitize_csv_value(chq.get("cheque_request_id")),
            sanitize_csv_value(chq.get("customer_id")),
            sanitize_csv_value(chq.get("customer_name")),
            sanitize_csv_value(chq.get("account_number")),
            sanitize_csv_value(chq.get("leaves")),
            sanitize_csv_value(req_date),
            sanitize_csv_value(st),
            sanitize_csv_value(chq.get("admin_decision_date") or "Pending"),
            sanitize_csv_value(chq.get("admin_notes") or ""),
        ]
        writer.writerow(row)

    return output.getvalue()


def export_audit_logs_csv(
    start_date: str | None = None,
    end_date: str | None = None,
    action_filter: str = "All",
) -> str:
    """
    Exports immutable administrative audit logs into safe CSV format.
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    headers = [
        "Log ID",
        "Admin ID",
        "Action",
        "Target Type",
        "Target ID",
        "Timestamp",
        "Outcome",
        "Details",
    ]
    writer.writerow([sanitize_csv_value(h) for h in headers])

    clean_action = (action_filter or "All").strip().upper()
    for log in AUDIT_LOG_DB:
        ts = log.get("timestamp")
        if not _is_date_in_range(ts, start_date, end_date):
            continue

        act = str(log.get("action", "")).upper()
        if clean_action != "ALL" and act != clean_action:
            continue

        row = [
            sanitize_csv_value(log.get("log_id")),
            sanitize_csv_value(log.get("admin_id")),
            sanitize_csv_value(log.get("action")),
            sanitize_csv_value(log.get("target_type")),
            sanitize_csv_value(log.get("target_id")),
            sanitize_csv_value(ts),
            sanitize_csv_value(log.get("outcome")),
            sanitize_csv_value(log.get("details")),
        ]
        writer.writerow(row)

    return output.getvalue()




