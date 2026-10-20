"""
app/utils.py
=============================================================================
Utility and Validation Helpers for CORE BANKING SYSTEM
=============================================================================

PYTHON FUNDAMENTALS DEMONSTRATED IN THIS FILE:
1. Control Flow (if / elif / else):
   - Checking multiple validation rules step-by-step.
   - Guarding against invalid inputs.

2. Exception Handling (try / except):
   - Gracefully converting strings to numeric types (int, float) without crashing.
   - Catching ValueError and TypeError specifically.

3. Type Hints:
   - Clear parameter and return type signatures for code readability.
   - Examples: `tuple[bool, list[str]]`, `int | None`, `float`.

4. String Manipulation & Formatting:
   - Methods like `.strip()`, string containment with `in`.
   - Python f-strings for currency formatting: `f"${amount:,.2f}"`.
"""


def safe_int(value: any, default: int | None = None) -> int | None:
    """
    Safely converts an unknown value or string into an integer.

    Demonstrates:
    - try/except block: Intercepts conversion errors instead of halting execution.
    - ValueError: Raised when string cannot be parsed as int (e.g. "abc").
    - TypeError: Raised when value type is unsupported (e.g. None).
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: any, default: float | None = None) -> float | None:
    """
    Safely converts an unknown value or string into a float.

    Demonstrates:
    - Exception handling for decimal conversion.
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def format_currency(amount: float | int) -> str:
    """
    Formats a numeric balance into standard currency display.
    Example: 12450.0 -> "$12,450.00"

    Demonstrates:
    - Python f-strings with format specifiers (, for thousands separator, .2f for 2 decimal places).
    """
    try:
        return f"${float(amount):,.2f}"
    except (ValueError, TypeError):
        return "$0.00"


def validate_age(age: any) -> tuple[bool, str]:
    """
    Validates a customer's age using if/elif/else checks.

    Returns:
        (is_valid: bool, error_message: str)
    """
    # Check if age was provided
    if age is None:
        return False, "Age is required."

    # Check if age is integer
    if not isinstance(age, int):
        return False, "Age must be a whole number (integer)."

    # Age boundary checks using if / elif / else
    if age < 18:
        return False, "Customer must be at least 18 years old to open a bank account."
    elif age > 120:
        return False, "Please enter a realistic age (120 years or below)."
    else:
        return True, ""


def validate_balance(balance: any) -> tuple[bool, str]:
    """
    Validates an opening account balance.

    Returns:
        (is_valid: bool, error_message: str)
    """
    if balance is None:
        return False, "Initial balance is required."

    # Validate numeric type
    if not isinstance(balance, (int, float)):
        return False, "Balance must be a valid numeric value."

    # Conditional logic
    if balance < 0:
        return False, "Opening balance cannot be negative."
    elif balance > 10_000_000:
        return False, "Single opening deposit exceeds branch limit ($10,000,000)."
    else:
        return True, ""


def validate_customer_data(customer_data: dict) -> tuple[bool, list[str]]:
    """
    Comprehensive validation for new or updated customer dictionaries.

    Demonstrates:
    - Dictionary lookup with `.get()`.
    - Combining multiple validations into an accumulated error list.
    - Returning a tuple of (boolean_status, error_list).

    Parameters:
        customer_data (dict): The dictionary containing customer details.

    Returns:
        tuple[bool, list[str]]: (True if all checks pass, list of error messages)
    """
    errors: list[str] = []

    # 1. Name validation
    name = customer_data.get("name")
    if not name or not isinstance(name, str) or len(name.strip()) < 2:
        errors.append("Customer name is required and must contain at least 2 characters.")

    # 2. Age validation
    age = customer_data.get("age")
    age_valid, age_err = validate_age(age)
    if not age_valid:
        errors.append(age_err)

    # 3. Email validation (basic string checks)
    email = customer_data.get("email")
    if not email or not isinstance(email, str):
        errors.append("Email address is required.")
    elif "@" not in email or "." not in email:
        errors.append("Email must be in a valid format (e.g., name@domain.com).")

    # 4. Phone validation
    phone = customer_data.get("phone")
    if not phone or not isinstance(phone, str) or len(phone.strip()) < 7:
        errors.append("A valid phone number with at least 7 characters is required.")

    # 5. Account type validation
    valid_account_types = ["Savings", "Checking", "Business"]
    account_type = customer_data.get("account_type")
    if not account_type or account_type not in valid_account_types:
        errors.append(f"Account type must be one of: {', '.join(valid_account_types)}.")

    # 6. Balance validation
    balance = customer_data.get("balance")
    balance_valid, balance_err = validate_balance(balance)
    if not balance_valid:
        errors.append(balance_err)

    # If no errors accumulated, is_valid is True
    is_valid = len(errors) == 0
    return is_valid, errors


def validate_transaction_amount(amount: any) -> tuple[bool, float, str]:
    """
    Validates a transaction amount for deposits, withdrawals, and transfers.

    Demonstrates:
    - Checking for empty or None inputs.
    - Safe conversion to float using safe_float().
    - Ensuring amount is strictly positive (> 0.00).
    - Rounding to 2 decimal places.

    Returns:
        tuple[bool, float, str]: (is_valid, parsed_amount, error_message)
    """
    if amount is None or str(amount).strip() == "":
        return False, 0.0, "Please enter an amount."

    parsed = safe_float(amount)
    if parsed is None:
        return False, 0.0, "Amount must be a valid numeric number."

    if parsed <= 0:
        return False, 0.0, "Amount must be greater than zero."

    if parsed > 1_000_000:
        return False, 0.0, "Single transaction amount cannot exceed $1,000,000.00."

    return True, round(parsed, 2), ""


def validate_loan_application_input(
    loan_type: any,
    requested_amount: any,
    tenure_months: any,
    purpose: any,
    monthly_income: any,
) -> tuple[bool, list[str], dict]:
    """
    Validates customer input for a new loan application.

    Demonstrates:
    - Multi-field input sanitization and verification.
    - Boundaries check using if/elif/else.
    - Accumulated errors collection.

    Returns:
        tuple[bool, list[str], dict]: (is_valid, errors_list, sanitized_data_dict)
    """
    errors: list[str] = []
    sanitized: dict = {}

    # 1. Loan type check
    valid_types = ["Personal", "Education", "Home", "Business"]
    clean_type = str(loan_type or "").strip()
    if not clean_type or clean_type not in valid_types:
        errors.append(f"Loan type must be one of: {', '.join(valid_types)}.")
    else:
        sanitized["loan_type"] = clean_type

    # 2. Requested amount check
    parsed_amount = safe_float(requested_amount)
    if parsed_amount is None:
        errors.append("Requested loan amount must be a valid number.")
    elif parsed_amount <= 0:
        errors.append("Requested loan amount must be strictly greater than $0.00.")
    elif parsed_amount > 1_000_000:
        errors.append("Requested loan amount cannot exceed the maximum branch limit of $1,000,000.00.")
    else:
        sanitized["requested_amount"] = round(parsed_amount, 2)

    # 3. Tenure check (in months)
    parsed_tenure = safe_int(tenure_months)
    if parsed_tenure is None:
        errors.append("Loan tenure must be a valid whole number of months.")
    elif parsed_tenure < 1:
        errors.append("Loan tenure must be at least 1 month.")
    elif parsed_tenure > 360:
        errors.append("Loan tenure cannot exceed 360 months (30 years).")
    else:
        sanitized["tenure_months"] = parsed_tenure

    # 4. Purpose check
    clean_purpose = str(purpose or "").strip()
    if not clean_purpose or len(clean_purpose) < 3:
        errors.append("Please provide a descriptive purpose for the loan (minimum 3 characters).")
    else:
        sanitized["purpose"] = clean_purpose

    # 5. Monthly income check
    parsed_income = safe_float(monthly_income)
    if parsed_income is None:
        errors.append("Monthly income must be a valid number.")
    elif parsed_income <= 0:
        errors.append("Monthly income must be strictly greater than $0.00.")
    else:
        sanitized["monthly_income"] = round(parsed_income, 2)

    return len(errors) == 0, errors, sanitized


def validate_loan_approval_input(
    requested_amount: float,
    approved_amount: any,
    interest_rate: any,
    tenure_months: any,
) -> tuple[bool, list[str], dict]:
    """
    Validates admin inputs when approving a loan application.

    Demonstrates:
    - Guard against approved amount exceeding requested amount.
    - Zero interest support (interest_rate >= 0).
    - Numeric tenure validation.

    Returns:
        tuple[bool, list[str], dict]: (is_valid, errors_list, sanitized_data_dict)
    """
    errors: list[str] = []
    sanitized: dict = {}

    # 1. Approved amount
    parsed_approved = safe_float(approved_amount)
    if parsed_approved is None:
        errors.append("Approved loan amount must be a valid number.")
    elif parsed_approved <= 0:
        errors.append("Approved loan amount must be greater than $0.00.")
    elif parsed_approved > requested_amount:
        errors.append(
            f"Approved amount (${parsed_approved:,.2f}) cannot exceed requested amount (${requested_amount:,.2f})."
        )
    else:
        sanitized["approved_amount"] = round(parsed_approved, 2)

    # 2. Annual interest rate (0% is allowed for zero-interest loans)
    parsed_rate = safe_float(interest_rate)
    if parsed_rate is None:
        errors.append("Annual interest rate must be a valid numeric percentage.")
    elif parsed_rate < 0:
        errors.append("Annual interest rate cannot be negative.")
    elif parsed_rate > 50:
        errors.append("Annual interest rate cannot exceed 50.00%.")
    else:
        sanitized["annual_interest_rate"] = round(parsed_rate, 2)

    # 3. Tenure in months
    parsed_tenure = safe_int(tenure_months)
    if parsed_tenure is None:
        errors.append("Approved tenure must be a valid number of months.")
    elif parsed_tenure < 1:
        errors.append("Approved tenure must be at least 1 month.")
    elif parsed_tenure > 360:
        errors.append("Approved tenure cannot exceed 360 months.")
    else:
        sanitized["approved_tenure_months"] = parsed_tenure

    return len(errors) == 0, errors, sanitized


def mask_account_number(account_number: str) -> str:
    """
    Formats an account number into a masked display format for customer privacy.
    Example: 'ACC-1002941' -> 'ACC-****941'
    Example: '1002941' -> '***2941'

    Demonstrates:
    - String slicing, prefix checking, and formatted strings.
    """
    if not account_number or not isinstance(account_number, str):
        return "N/A"

    clean = account_number.strip()
    if len(clean) <= 4:
        return "****"

    if clean.startswith("ACC-") and len(clean) > 7:
        suffix = clean[-3:]
        stars = "****"
        return f"ACC-{stars}{suffix}"

    return f"{'*' * (len(clean) - 4)}{clean[-4:]}"


def validate_cheque_request_input(
    account_number: any,
    leaves: any,
    customer_accounts: list[dict],
) -> tuple[bool, list[str], dict]:
    """
    Validates a customer's cheque book request submission.

    Rules:
    1. Account number must be provided and must belong to the customer.
    2. Selected account must be Active (Pending, Frozen, Closed, or Inactive are ineligible).
    3. Leaves count must be exactly 10, 25, or 50.

    Returns:
        (is_valid: bool, errors: list[str], sanitized: dict)
    """
    errors: list[str] = []
    sanitized: dict = {
        "account_number": "",
        "leaves": 25,
    }

    # 1. Account number validation
    clean_acc = str(account_number or "").strip()
    if not clean_acc:
        errors.append("Please select an eligible account for your cheque book request.")
    else:
        # Check against customer accounts
        matched_account = None
        for acc in customer_accounts:
            if acc.get("account_number") == clean_acc:
                matched_account = acc
                break

        if not matched_account:
            errors.append("Selected account does not belong to your customer profile.")
        else:
            status = matched_account.get("account_status", "Active")
            is_active = matched_account.get("is_active", True)
            if status != "Active" or not is_active:
                errors.append(
                    f"Account {clean_acc} is currently '{status}' and is not eligible for cheque book issuance. Only Active accounts may request a cheque book."
                )
            else:
                sanitized["account_number"] = clean_acc

    # 2. Number of leaves validation (10, 25, or 50)
    parsed_leaves = safe_int(leaves)
    if parsed_leaves is None or parsed_leaves not in [10, 25, 50]:
        errors.append("Cheque leaves must be 10, 25, or 50.")
    else:
        sanitized["leaves"] = parsed_leaves

    return len(errors) == 0, errors, sanitized


def validate_cheque_rejection_reason(reason: any) -> tuple[bool, str]:
    """
    Validates the rejection reason provided by an administrator.

    Returns:
        (is_valid: bool, error_message: str)
    """
    clean_reason = str(reason or "").strip()
    if not clean_reason:
        return False, "Rejection reason is required."
    if len(clean_reason) < 3:
        return False, "Please provide a descriptive rejection reason (minimum 3 characters)."
    return True, ""


def validate_date_range(start_date_str: str, end_date_str: str) -> tuple[bool, str, str | None, str | None]:
    """
    Validates optional start and end date parameters (YYYY-MM-DD).

    Rules:
    - If empty, allowed (returns None for that bound).
    - If provided, must match valid date format YYYY-MM-DD.
    - If both provided, start_date must not be after end_date.

    Returns:
        (is_valid: bool, error_message: str, clean_start: str | None, clean_end: str | None)
    """
    from datetime import datetime

    clean_start = (start_date_str or "").strip() or None
    clean_end = (end_date_str or "").strip() or None

    d_start = None
    d_end = None

    if clean_start:
        try:
            d_start = datetime.strptime(clean_start, "%Y-%m-%d").date()
        except ValueError:
            return False, "Invalid start date format. Please use YYYY-MM-DD.", None, None

    if clean_end:
        try:
            d_end = datetime.strptime(clean_end, "%Y-%m-%d").date()
        except ValueError:
            return False, "Invalid end date format. Please use YYYY-MM-DD.", None, None

    if d_start and d_end and d_start > d_end:
        return False, "Start date cannot be after end date.", None, None

    return True, "", clean_start, clean_end


def sanitize_csv_value(value: any) -> str:
    """
    Sanitizes values exported to CSV to prevent CSV Formula Injection (OWASP).
    If a string cell starts with '=', '+', '-', '@', tab, or carriage return,
    it is prepended with a single quote (') so spreadsheets treat it strictly as text.
    """
    if value is None:
        return ""
    val_str = str(value)
    if val_str and val_str[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{val_str}"
    return val_str


def generate_csrf_token() -> str:
    """Generates a cryptographically secure token for CSRF protection."""
    from flask import session
    import secrets
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def validate_csrf_token(token: str) -> bool:
    """Validates submitted token against session CSRF token."""
    from flask import session, current_app
    import hmac
    if current_app and current_app.config.get("TESTING"):
        return True
    expected = session.get("_csrf_token")
    if not expected or not token:
        return False
    return hmac.compare_digest(expected, token)



