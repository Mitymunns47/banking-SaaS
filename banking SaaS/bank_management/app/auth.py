"""
app/auth.py
=============================================================================
Authentication, Authorization, and Session Protection for CORE BANKING SYSTEM
=============================================================================

PYTHON FUNDAMENTALS DEMONSTRATED IN THIS FILE:
1. Reusable Business Functions:
   - Dedicated service layer separating authentication mechanics from Flask routes.
   - Using explicit input parameters and structured return values.

2. Control Flow & Validation (if / elif / else):
   - Multi-tier validation for passwords, duplicate checking, and role permissions.

3. Exception Handling (try / except):
   - Catching input conversion exceptions or missing session attributes safely.

4. Python Dictionaries for In-Memory Rate Limiting:
   - Tracking failed login attempts and timestamps to guard against brute-force attacks.

5. Decorators & Higher-Order Functions:
   - Python decorator syntax (`@wraps`) to guard routes with role-based access control.

6. Modern Type Hints:
   - Clear type annotations e.g. `tuple[dict | None, list[str]]`, `bool`, `int`.
"""

import time
from functools import wraps
from flask import session, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import CUSTOMERS_DB, SAMPLE_ADMIN, LOGIN_ATTEMPTS
from app.utils import safe_int, validate_age

# Configuration for login attempt protection
MAX_FAILED_ATTEMPTS: int = 3
LOCKOUT_DURATION_SECONDS: int = 60  # 1 minute lockout for learning demo


def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using Werkzeug's secure hashing algorithm (PBKDF2/scrypt).
    Ensures passwords are never stored in plaintext.
    """
    if not password:
        return ""
    return generate_password_hash(password)


def verify_password(stored_password: str | None, candidate_password: str | None) -> bool:
    """
    Verifies candidate password against stored password string.
    Supports both hashed passwords and transparent migration of legacy plaintext seed records.
    """
    if not stored_password or not candidate_password:
        return False
    if stored_password == candidate_password:
        return True
    if stored_password.startswith(("pbkdf2:", "scrypt:", "argon2:")):
        try:
            return check_password_hash(stored_password, candidate_password)
        except Exception:
            return False
    return False



def get_failed_attempts_info(identifier: str) -> tuple[bool, int]:
    """
    Checks if an email or username is temporarily locked out.

    Demonstrates:
    - In-memory dictionary state lookup with `.get()`.
    - Time comparison with `time.time()`.
    - Returning a tuple with lockout status and remaining seconds.

    Parameters:
        identifier (str): Customer email or admin username.

    Returns:
        tuple[bool, int]: (is_locked, remaining_seconds)
    """
    record = LOGIN_ATTEMPTS.get(identifier.strip().lower())
    if not record:
        return False, 0

    now = time.time()
    locked_until = record.get("locked_until", 0.0)

    # Check if currently locked
    if locked_until > now:
        remaining = int(locked_until - now)
        return True, remaining

    # Lock period has expired; reset if needed
    if record.get("failed_count", 0) >= MAX_FAILED_ATTEMPTS and locked_until <= now:
        record["failed_count"] = 0
        record["locked_until"] = 0.0

    return False, 0


def record_failed_login(identifier: str) -> None:
    """
    Increments the failed login count for a user and locks the account if limit exceeded.

    Demonstrates:
    - Conditional dictionary modification.
    """
    key = identifier.strip().lower()
    if key not in LOGIN_ATTEMPTS:
        LOGIN_ATTEMPTS[key] = {"failed_count": 0, "locked_until": 0.0}

    LOGIN_ATTEMPTS[key]["failed_count"] += 1

    if LOGIN_ATTEMPTS[key]["failed_count"] >= MAX_FAILED_ATTEMPTS:
        LOGIN_ATTEMPTS[key]["locked_until"] = time.time() + LOCKOUT_DURATION_SECONDS


def clear_failed_logins(identifier: str) -> None:
    """Clears the failed login tracking after a successful authentication."""
    key = identifier.strip().lower()
    if key in LOGIN_ATTEMPTS:
        del LOGIN_ATTEMPTS[key]


def register_customer(
    name: str,
    age: int | str,
    email: str,
    phone: str,
    password: str,
    confirm_password: str,
    account_type: str = "Savings",
) -> tuple[dict | None, list[str]]:
    """
    Registers a new customer account in the system.

    Validates:
    - Required fields
    - Valid age (>= 18)
    - Email structure and uniqueness (no duplicate registrations)
    - Password matching and minimum length

    Returns:
        tuple[dict | None, list[str]]: (created_customer_dict, error_list)
    """
    errors: list[str] = []

    # 1. Clean and normalize inputs
    name_clean = (name or "").strip()
    email_clean = (email or "").strip().lower()
    phone_clean = (phone or "").strip()

    # 2. Check required fields
    if not name_clean:
        errors.append("Full name is required.")
    elif len(name_clean) < 2:
        errors.append("Full name must be at least 2 characters.")

    # Safe conversion of age using try/except
    parsed_age = safe_int(age)
    age_valid, age_err = validate_age(parsed_age)
    if not age_valid:
        errors.append(age_err)

    if not phone_clean or len(phone_clean) < 7:
        errors.append("A valid phone number (at least 7 characters) is required.")

    # 3. Email validation
    if not email_clean:
        errors.append("Email address is required.")
    elif "@" not in email_clean or "." not in email_clean:
        errors.append("Please provide a valid email address (e.g., user@domain.com).")
    else:
        # Check duplicate email in in-memory database
        for existing in CUSTOMERS_DB:
            if existing.get("email", "").strip().lower() == email_clean:
                errors.append(f"An account with email '{email_clean}' is already registered.")
                break

    # 4. Password validation
    if not password:
        errors.append("Password is required.")
    elif len(password) < 6:
        errors.append("Password must be at least 6 characters long.")

    if password != confirm_password:
        errors.append("Password and confirm password do not match.")

    # 5. Return errors if any rule was violated
    if errors:
        return None, errors

    # 6. Assign unique customer ID
    if len(CUSTOMERS_DB) > 0:
        new_id = max(c["customer_id"] for c in CUSTOMERS_DB) + 1
    else:
        new_id = 1

    # 7. Assign unique account number
    account_number = f"ACC-{2000000 + (new_id * 3147) % 799999}"

    # 8. Create new customer dictionary with status 'Pending' and initial balance 0.0
    new_customer = {
        "customer_id": new_id,
        "name": name_clean,
        "age": parsed_age,
        "email": email_clean,
        "phone": phone_clean,
        "password": hash_password(password),  # Stored as secure cryptographic hash
        "account_number": account_number,
        "account_type": account_type if account_type in ["Savings", "Checking", "Business"] else "Savings",
        "balance": 0.0,
        "is_active": False,  # Pending accounts are not active until approved
        "account_status": "Pending",
    }

    # Add to in-memory list
    CUSTOMERS_DB.append(new_customer)

    return new_customer, []


def authenticate_customer(email: str, password: str) -> tuple[dict | None, str | None]:
    """
    Authenticates customer credentials with brute-force attempt protection and secure password hashing.

    Demonstrates:
    - Attempt protection check.
    - Constant, generic error message to prevent user enumeration ("Invalid email or password").
    - Transparent migration of legacy passwords to cryptographic hashes.
    """
    email_clean = (email or "").strip().lower()

    # 1. Check if temporarily locked
    is_locked, remaining_seconds = get_failed_attempts_info(email_clean)
    if is_locked:
        return None, f"Too many failed login attempts. Please wait {remaining_seconds} seconds before trying again."

    # 2. Linear search for customer
    customer_match = None
    for c in CUSTOMERS_DB:
        if c.get("email", "").strip().lower() == email_clean:
            customer_match = c
            break

    # 3. Verify password using secure verification
    if customer_match and verify_password(customer_match.get("password"), password):
        # Transparent migration: if stored password was legacy plaintext, upgrade in-memory to hash
        stored_pw = str(customer_match.get("password", ""))
        if not stored_pw.startswith(("pbkdf2:", "scrypt:", "argon2:")):
            customer_match["password"] = hash_password(password)

        # Success: reset failed attempts
        clear_failed_logins(email_clean)
        return customer_match, None

    # 4. Failure: record attempt and return generic message
    record_failed_login(email_clean)
    return None, "Invalid email or password."


def authenticate_admin(username_or_email: str, password: str) -> tuple[dict | None, str | None]:
    """
    Authenticates administrator credentials against the SAMPLE_ADMIN configuration.
    Supports secure hash verification and transparent migration.
    """
    clean_identifier = (username_or_email or "").strip().lower()

    # Check lockout
    is_locked, remaining_seconds = get_failed_attempts_info(clean_identifier)
    if is_locked:
        return None, f"Too many failed login attempts. Please wait {remaining_seconds} seconds before trying again."

    admin_username = SAMPLE_ADMIN.get("username", "").lower()
    admin_email = SAMPLE_ADMIN.get("email", "").lower()

    if clean_identifier == admin_username or clean_identifier == admin_email:
        stored_pw = str(SAMPLE_ADMIN.get("password", ""))
        if verify_password(stored_pw, password):
            # Transparent migration for admin
            if not stored_pw.startswith(("pbkdf2:", "scrypt:", "argon2:")):
                SAMPLE_ADMIN["password"] = hash_password(password)
            clear_failed_logins(clean_identifier)
            return SAMPLE_ADMIN, None

    record_failed_login(clean_identifier)
    return None, "Invalid administrator credentials."


def change_customer_password(
    customer_id: int,
    current_password: str,
    new_password: str,
    confirm_new_password: str,
) -> tuple[bool, list[str]]:
    """
    Changes a customer's password after validating their current password and new password.
    Stores new password as secure hash.

    Returns:
        tuple[bool, list[str]]: (success_boolean, error_list)
    """
    errors: list[str] = []

    # Find customer
    customer = None
    for c in CUSTOMERS_DB:
        if c.get("customer_id") == customer_id:
            customer = c
            break

    if not customer:
        return False, ["Customer account not found."]

    # Validate current password using verify_password
    if not verify_password(customer.get("password"), current_password):
        errors.append("Current password does not match our records.")

    # Validate new password
    if not new_password:
        errors.append("New password cannot be empty.")
    elif len(new_password) < 6:
        errors.append("New password must be at least 6 characters long.")

    if new_password != confirm_new_password:
        errors.append("New password and confirm new password do not match.")

    if errors:
        return False, errors

    # Update in memory as secure hash
    customer["password"] = hash_password(new_password)
    return True, []


def require_customer_login() -> bool:
    """
    Helper function to check whether the active session belongs to an authenticated customer.
    """
    try:
        return bool(session.get("customer_id") and session.get("role") == "customer")
    except Exception:
        return False


def require_admin_login() -> bool:
    """
    Helper function to check whether the active session belongs to an authenticated admin.
    """
    try:
        return bool(session.get("admin_logged_in") is True and session.get("role") == "admin")
    except Exception:
        return False


def customer_login_required(view_func):
    """
    Decorator for views that strictly require customer authentication.
    Redirects unauthenticated users to the customer login page with a flash message.
    """
    @wraps(view_func)
    def decorated_view(*args, **kwargs):
        if not require_customer_login():
            flash("Please log in to access your customer dashboard.", "warning")
            return redirect(url_for("main.customer_login", next=request.path))
        return view_func(*args, **kwargs)

    return decorated_view


def admin_login_required(view_func):
    """
    Decorator for views that strictly require admin authentication.
    Redirects non-admin users to the admin login page with a flash message.
    """
    @wraps(view_func)
    def decorated_view(*args, **kwargs):
        if not require_admin_login():
            flash("Administrator login is required to access the staff portal.", "warning")
            return redirect(url_for("main.admin_login", next=request.path))
        return view_func(*args, **kwargs)

    return decorated_view
