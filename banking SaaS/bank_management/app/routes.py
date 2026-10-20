"""
app/routes.py
=============================================================================
Flask Route Definitions for CORE BANKING SYSTEM
=============================================================================

PYTHON FUNDAMENTALS DEMONSTRATED IN THIS FILE:
1. Blueprint Routing:
   - Clean, modular dispatching of web requests.

2. Session-Driven Identity:
   - Restricting banking operations to the authenticated customer stored in `session`.

3. Controller Separation:
   - Route handlers extract inputs, delegate business logic to `services.py`,
     and render appropriate Jinja2 templates with context data.

4. Form Sanitization & Exception Guarding:
   - Defensive checks against missing or invalid payloads.
"""

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response
from app.models import SAMPLE_ADMIN, LOAN_TYPES, LEAF_OPTIONS, CHEQUE_STATUSES
from app.services import (
    get_all_customers,
    get_customer_by_id,
    create_customer,
    get_account_summary,
    deposit_money,
    withdraw_money,
    transfer_money,
    get_transaction_history,
    get_admin_dashboard_summary,
    search_customers,
    approve_customer_account,
    reject_customer_account,
    freeze_customer_account,
    unfreeze_customer_account,
    close_customer_account,
    get_all_transactions,
    apply_for_loan,
    get_customer_loans,
    get_loan_by_id,
    cancel_loan_application,
    get_all_loans,
    get_admin_loan_summary,
    approve_loan_application,
    reject_loan_application,
    activate_loan,
    calculate_loan_repayment_details,
    request_cheque_book,
    get_customer_cheque_requests,
    get_cheque_request_by_id,
    cancel_cheque_request,
    get_all_cheque_requests,
    get_admin_cheque_summary,
    approve_cheque_request,
    reject_cheque_request,
    complete_cheque_request,
    log_audit_event,
    get_audit_logs,
    generate_admin_comprehensive_report,
    export_customers_csv,
    export_transactions_csv,
    export_loans_csv,
    export_cheques_csv,
    export_audit_logs_csv,
)
from app.utils import (
    safe_int,
    safe_float,
    format_currency,
    mask_account_number,
    validate_date_range,
    validate_csrf_token,
)
from app.auth import (
    register_customer,
    authenticate_customer,
    authenticate_admin,
    change_customer_password,
    require_customer_login,
    require_admin_login,
    customer_login_required,
    admin_login_required,
)

main_bp = Blueprint("main", __name__)


# =============================================================================
# Public & Directory Routes
# =============================================================================

@main_bp.route("/")
def index():
    """
    Home page route ("/")
    Presents the CORE BANKING SYSTEM landing overview with key stats and portals.
    """
    summary = get_account_summary()
    recent_customers = get_all_customers()[:4]

    return render_template(
        "index.html",
        summary=summary,
        recent_customers=recent_customers,
        format_currency=format_currency,
    )


@main_bp.route("/customers", methods=["GET", "POST"])
def customers_list():
    """
    Customers list route ("/customers")
    Displays a tabular view of all registered customers with status badges.
    """
    form_errors: list[str] = []
    success_message: str | None = None

    if request.method == "POST":
        name = request.form.get("name", "")
        age_str = request.form.get("age", "")
        email = request.form.get("email", "")
        phone = request.form.get("phone", "")
        account_type = request.form.get("account_type", "Savings")
        balance_str = request.form.get("balance", "0")
        is_active = request.form.get("is_active") == "on"

        age = safe_int(age_str, default=None)
        balance = safe_float(balance_str, default=None)

        new_customer, errors = create_customer(
            name=name,
            age=age,
            email=email,
            phone=phone,
            account_type=account_type,
            balance=balance if balance is not None else -1.0,
            is_active=is_active,
        )

        if errors:
            form_errors = errors
        else:
            success_message = f"Customer '{new_customer['name']}' created successfully with Account Number {new_customer['account_number']}!"

    customers = get_all_customers()
    return render_template(
        "customers.html",
        customers=customers,
        form_errors=form_errors,
        success_message=success_message,
        format_currency=format_currency,
    )


@main_bp.route("/customer/<customer_id>")
def customer_details(customer_id: str):
    """Customer profile details route ("/customer/<customer_id>")."""
    parsed_id = safe_int(customer_id)

    if parsed_id is None:
        return (
            render_template(
                "customer_details.html",
                customer=None,
                error_message=f"Invalid customer ID '{customer_id}'. Customer ID must be a numeric integer.",
                format_currency=format_currency,
            ),
            400,
        )

    customer = get_customer_by_id(parsed_id)

    if customer is None:
        return (
            render_template(
                "customer_details.html",
                customer=None,
                error_message=f"No customer was found with Customer ID #{parsed_id}.",
                format_currency=format_currency,
            ),
            404,
        )

    return render_template(
        "customer_details.html",
        customer=customer,
        error_message=None,
        format_currency=format_currency,
    )


# =============================================================================
# Authentication Routes
# =============================================================================

@main_bp.route("/register", methods=["GET", "POST"])
def customer_register():
    """Customer Registration Route ("/register")."""
    if require_customer_login():
        return redirect(url_for("main.customer_dashboard"))

    errors: list[str] = []
    form_data: dict = {}

    if request.method == "POST":
        form_data = {
            "name": request.form.get("name", ""),
            "age": request.form.get("age", ""),
            "email": request.form.get("email", ""),
            "phone": request.form.get("phone", ""),
            "account_type": request.form.get("account_type", "Savings"),
        }
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        created_customer, reg_errors = register_customer(
            name=form_data["name"],
            age=form_data["age"],
            email=form_data["email"],
            phone=form_data["phone"],
            password=password,
            confirm_password=confirm_password,
            account_type=form_data["account_type"],
        )

        if reg_errors:
            errors = reg_errors
        else:
            flash(
                f"Registration successful for {created_customer['name']}! "
                f"Your account status is currently 'Pending' approval. You can now log in.",
                "success",
            )
            return redirect(url_for("main.customer_login"))

    return render_template("register.html", errors=errors, form_data=form_data)


@main_bp.route("/login", methods=["GET", "POST"])
def customer_login():
    """Customer Login Route ("/login")."""
    if require_customer_login():
        return redirect(url_for("main.customer_dashboard"))

    error_message: str | None = None
    email_entered: str = ""

    if request.method == "POST":
        email_entered = request.form.get("email", "")
        password = request.form.get("password", "")

        customer, auth_error = authenticate_customer(email_entered, password)

        if auth_error:
            error_message = auth_error
        elif customer:
            session.pop("admin_logged_in", None)
            session.pop("admin_username", None)

            session["customer_id"] = customer["customer_id"]
            session["customer_name"] = customer["name"]
            session["role"] = "customer"

            flash(f"Welcome back, {customer['name']}!", "success")
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("main.customer_dashboard"))

    return render_template(
        "login.html",
        error_message=error_message,
        email_entered=email_entered,
    )


@main_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Admin Login Route ("/admin/login")."""
    if require_admin_login():
        return redirect(url_for("main.admin_dashboard"))

    error_message: str | None = None
    username_entered: str = ""

    if request.method == "POST":
        username_entered = request.form.get("username_or_email", "")
        password = request.form.get("password", "")

        admin_obj, auth_error = authenticate_admin(username_entered, password)

        if auth_error:
            error_message = auth_error
        elif admin_obj:
            session.pop("customer_id", None)
            session.pop("customer_name", None)

            session["admin_logged_in"] = True
            session["admin_username"] = admin_obj["username"]
            session["admin_name"] = admin_obj["name"]
            session["role"] = "admin"

            flash(f"Administrator portal accessed: {admin_obj['name']}", "success")
            return redirect(url_for("main.admin_dashboard"))

    return render_template(
        "admin_login.html",
        error_message=error_message,
        username_entered=username_entered,
        sample_admin=SAMPLE_ADMIN,
    )


@main_bp.route("/dashboard")
@customer_login_required
def customer_dashboard():
    """Customer Dashboard Route ("/dashboard")."""
    customer_id = session.get("customer_id")
    customer = get_customer_by_id(customer_id)

    if not customer:
        session.clear()
        flash("Your session could not be verified. Please log in again.", "warning")
        return redirect(url_for("main.customer_login"))

    recent_transactions = get_transaction_history(customer_id)[:5]

    return render_template(
        "dashboard.html",
        customer=customer,
        recent_transactions=recent_transactions,
        format_currency=format_currency,
    )


@main_bp.route("/admin/dashboard")
@admin_login_required
def admin_dashboard():
    """Admin Dashboard Route ("/admin/dashboard")."""
    summary = get_admin_dashboard_summary()
    recent_customers = get_all_customers()[:6]
    recent_transactions = get_all_transactions()[:6]

    return render_template(
        "admin_dashboard.html",
        admin_name=session.get("admin_name", "Administrator"),
        admin_username=session.get("admin_username", "admin"),
        summary=summary,
        recent_customers=recent_customers,
        recent_transactions=recent_transactions,
        format_currency=format_currency,
    )


@main_bp.route("/change-password", methods=["GET", "POST"])
@customer_login_required
def change_password():
    """Customer Password Change Route ("/change-password")."""
    customer_id = session.get("customer_id")
    errors: list[str] = []

    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_new_password = request.form.get("confirm_new_password", "")

        success, errs = change_customer_password(
            customer_id=customer_id,
            current_password=current_password,
            new_password=new_password,
            confirm_new_password=confirm_new_password,
        )

        if success:
            flash("Your password has been changed successfully!", "success")
            return redirect(url_for("main.customer_dashboard"))
        else:
            errors = errs

    return render_template("change_password.html", errors=errors)


@main_bp.route("/logout")
def customer_logout():
    """Customer Logout Route ("/logout")."""
    session.pop("customer_id", None)
    session.pop("customer_name", None)
    session.pop("role", None)
    flash("You have been signed out safely.", "info")
    return redirect(url_for("main.customer_login"))


@main_bp.route("/admin/logout")
def admin_logout():
    """Admin Logout Route ("/admin/logout")."""
    session.pop("admin_logged_in", None)
    session.pop("admin_username", None)
    session.pop("admin_name", None)
    session.pop("role", None)
    flash("Administrator session terminated.", "info")
    return redirect(url_for("main.admin_login"))


# =============================================================================
# Core Banking Operations Routes (Deposit, Withdraw, Transfer, Transactions)
# =============================================================================

@main_bp.route("/deposit", methods=["GET", "POST"])
@customer_login_required
def deposit():
    """
    Deposit Route ("/deposit")
    Allows authenticated customers to deposit funds into their account.
    """
    customer_id = session.get("customer_id")
    customer = get_customer_by_id(customer_id)

    if not customer:
        return redirect(url_for("main.customer_login"))

    error_message: str | None = None
    entered_amount: str = ""

    if request.method == "POST":
        entered_amount = request.form.get("amount", "")
        success, message, new_balance = deposit_money(customer_id, entered_amount)

        if success:
            flash(message, "success")
            return redirect(url_for("main.customer_dashboard"))
        else:
            error_message = message

    return render_template(
        "deposit.html",
        customer=customer,
        error_message=error_message,
        entered_amount=entered_amount,
        format_currency=format_currency,
    )


@main_bp.route("/withdraw", methods=["GET", "POST"])
@customer_login_required
def withdraw():
    """
    Withdrawal Route ("/withdraw")
    Allows authenticated customers to withdraw funds from their account.
    """
    customer_id = session.get("customer_id")
    customer = get_customer_by_id(customer_id)

    if not customer:
        return redirect(url_for("main.customer_login"))

    error_message: str | None = None
    entered_amount: str = ""

    if request.method == "POST":
        entered_amount = request.form.get("amount", "")
        success, message, new_balance = withdraw_money(customer_id, entered_amount)

        if success:
            flash(message, "success")
            return redirect(url_for("main.customer_dashboard"))
        else:
            error_message = message

    return render_template(
        "withdraw.html",
        customer=customer,
        error_message=error_message,
        entered_amount=entered_amount,
        format_currency=format_currency,
    )


@main_bp.route("/transfer", methods=["GET", "POST"])
@customer_login_required
def transfer():
    """
    Transfer Route ("/transfer")
    Allows authenticated customers to transfer funds to another valid customer account.
    """
    customer_id = session.get("customer_id")
    customer = get_customer_by_id(customer_id)

    if not customer:
        return redirect(url_for("main.customer_login"))

    error_message: str | None = None
    recipient_account: str = ""
    entered_amount: str = ""

    if request.method == "POST":
        recipient_account = request.form.get("recipient_account", "")
        entered_amount = request.form.get("amount", "")

        success, message, new_balance = transfer_money(
            sender_id=customer_id,
            recipient_account=recipient_account,
            amount=entered_amount,
        )

        if success:
            flash(message, "success")
            return redirect(url_for("main.customer_dashboard"))
        else:
            error_message = message

    return render_template(
        "transfer.html",
        customer=customer,
        error_message=error_message,
        recipient_account=recipient_account,
        entered_amount=entered_amount,
        format_currency=format_currency,
    )


@main_bp.route("/transactions")
@customer_login_required
def transactions():
    """
    Transaction History Route ("/transactions")
    Displays the authenticated customer's chronological transaction history.
    """
    customer_id = session.get("customer_id")
    customer = get_customer_by_id(customer_id)

    if not customer:
        return redirect(url_for("main.customer_login"))

    transaction_list = get_transaction_history(customer_id)

    return render_template(
        "transactions.html",
        customer=customer,
        transactions=transaction_list,
        format_currency=format_currency,
    )


# =============================================================================
# Customer Loan Management Routes
# =============================================================================

@main_bp.route("/loans")
@customer_login_required
def customer_loans():
    """
    Customer Loans Directory Route ("/loans").
    Displays customer's loan applications, statuses, and links to apply.
    """
    customer_id = session.get("customer_id")
    customer = get_customer_by_id(customer_id)
    if not customer:
        return redirect(url_for("main.customer_login"))

    loans = get_customer_loans(customer_id)
    pending_count = sum(1 for l in loans if l.get("status") == "Pending")
    approved_count = sum(1 for l in loans if l.get("status") in ["Approved", "Active"])

    return render_template(
        "customer_loans.html",
        customer=customer,
        loans=loans,
        pending_count=pending_count,
        approved_count=approved_count,
        format_currency=format_currency,
    )


@main_bp.route("/loans/apply", methods=["GET", "POST"])
@customer_login_required
def apply_loan():
    """
    Customer Loan Application Route ("/loans/apply").
    Accepts loan type, requested amount, tenure in months, purpose, and income.
    """
    customer_id = session.get("customer_id")
    customer = get_customer_by_id(customer_id)
    if not customer:
        return redirect(url_for("main.customer_login"))

    errors: list[str] = []
    form_data = {
        "loan_type": "Personal",
        "requested_amount": "",
        "tenure_months": "24",
        "purpose": "",
        "monthly_income": "",
    }

    if request.method == "POST":
        form_data = {
            "loan_type": request.form.get("loan_type", "Personal"),
            "requested_amount": request.form.get("requested_amount", ""),
            "tenure_months": request.form.get("tenure_months", ""),
            "purpose": request.form.get("purpose", ""),
            "monthly_income": request.form.get("monthly_income", ""),
        }

        success, message, created_loan = apply_for_loan(
            customer_id=customer_id,
            loan_type=form_data["loan_type"],
            requested_amount=form_data["requested_amount"],
            tenure_months=form_data["tenure_months"],
            purpose=form_data["purpose"],
            monthly_income=form_data["monthly_income"],
        )

        if success and created_loan:
            flash(message, "success")
            return redirect(url_for("main.customer_loan_details", loan_id=created_loan["loan_id"]))
        else:
            errors.append(message)

    return render_template(
        "loan_apply.html",
        customer=customer,
        loan_types=LOAN_TYPES,
        form_data=form_data,
        errors=errors,
        format_currency=format_currency,
    )


@main_bp.route("/loan/<int:loan_id>")
@customer_login_required
def customer_loan_details(loan_id: int):
    """
    Customer Loan Details Route ("/loan/<loan_id>").
    Displays terms, EMI calculations when approved, and status.
    Guards against unauthorized customer inspection.
    """
    customer_id = session.get("customer_id")
    customer = get_customer_by_id(customer_id)
    if not customer:
        return redirect(url_for("main.customer_login"))

    loan = get_loan_by_id(loan_id)
    if not loan:
        flash("Loan application was not found.", "warning")
        return redirect(url_for("main.customer_loans"))

    # Security check: customer may only view their own loan
    if loan.get("customer_id") != customer_id:
        flash("Unauthorized access. You may only view your own loan records.", "error")
        return redirect(url_for("main.customer_loans"))

    return render_template(
        "loan_details.html",
        customer=customer,
        loan=loan,
        format_currency=format_currency,
    )


@main_bp.route("/loan/<int:loan_id>/cancel", methods=["POST"])
@customer_login_required
def customer_cancel_loan(loan_id: int):
    """
    Customer Loan Cancellation Route ("/loan/<loan_id>/cancel").
    Allows cancellation only if the application is in 'Pending' status.
    """
    customer_id = session.get("customer_id")
    success, message = cancel_loan_application(loan_id, customer_id)
    flash(message, "info" if success else "warning")
    return redirect(url_for("main.customer_loans"))


# -----------------------------------------------------------------------------
# Customer Cheque Book Management Routes
# -----------------------------------------------------------------------------

@main_bp.route("/cheques")
@customer_login_required
def customer_cheques():
    """
    Customer Cheque Book Dashboard Route ("/cheques").
    Displays previous and current cheque book requests with masked account numbers.
    """
    customer_id = session.get("customer_id")
    customer = get_customer_by_id(customer_id)
    if not customer:
        return redirect(url_for("main.customer_login"))

    requests_list = get_customer_cheque_requests(customer_id)
    return render_template(
        "customer_cheques.html",
        customer=customer,
        requests=requests_list,
    )


@main_bp.route("/cheques/request", methods=["GET", "POST"])
@customer_login_required
def customer_request_cheque():
    """
    Customer Cheque Book Request Form Route ("/cheques/request").
    Allows requesting 10, 25, or 50 leaves for an eligible active account.
    """
    customer_id = session.get("customer_id")
    customer = get_customer_by_id(customer_id)
    if not customer:
        return redirect(url_for("main.customer_login"))

    customer_accounts = [customer] if customer.get("account_number") else []
    eligible_accounts = [
        acc for acc in customer_accounts
        if acc.get("account_status") == "Active" and acc.get("is_active", True)
    ]

    errors: list[str] = []
    form_data = {
        "account_number": eligible_accounts[0]["account_number"] if eligible_accounts else "",
        "leaves": "25",
        "delivery_notes": "",
    }

    if request.method == "POST":
        form_data = {
            "account_number": request.form.get("account_number", "").strip(),
            "leaves": request.form.get("leaves", "25"),
            "delivery_notes": request.form.get("delivery_notes", "").strip(),
        }

        success, message, created_request = request_cheque_book(
            customer_id=customer_id,
            account_number=form_data["account_number"],
            leaves=form_data["leaves"],
            delivery_notes=form_data["delivery_notes"],
        )

        if success:
            flash(message, "success")
            return redirect(url_for("main.customer_cheques"))
        else:
            errors.append(message)

    return render_template(
        "cheque_request.html",
        customer=customer,
        eligible_accounts=eligible_accounts,
        leaf_options=LEAF_OPTIONS,
        form_data=form_data,
        errors=errors,
    )


@main_bp.route("/cheque/<int:request_id>/cancel", methods=["POST"])
@customer_login_required
def customer_cancel_cheque(request_id: int):
    """
    Customer Cheque Request Cancellation Route ("/cheque/<request_id>/cancel").
    Enforces customer ownership and pending status.
    """
    customer_id = session.get("customer_id")
    success, message = cancel_cheque_request(request_id, customer_id)
    flash(message, "success" if success else "error")
    return redirect(url_for("main.customer_cheques"))


# =============================================================================
# Admin Management Routes
# =============================================================================

@main_bp.route("/admin/customers")
@admin_login_required
def admin_customers():
    """
    Admin Customers Directory Route ("/admin/customers").
    Supports filtering and searching by ID, Name, Email, or Account Number.
    Demonstrates practical use of Python query parameters and string operations.
    """
    search_query = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "All").strip()

    # Retrieve filtered customers list using the reusable search service
    customers = search_customers(query=search_query, status_filter=status_filter)

    return render_template(
        "admin_customers.html",
        customers=customers,
        search_query=search_query,
        status_filter=status_filter,
        total_found=len(customers),
        format_currency=format_currency,
    )


@main_bp.route("/admin/customer/<int:customer_id>")
@admin_login_required
def admin_customer_details(customer_id: int):
    """
    Admin Customer Details Route ("/admin/customer/<customer_id>").
    Displays comprehensive profile, account status, balance, and recent transaction history.
    """
    customer = get_customer_by_id(customer_id)

    if customer is None:
        flash(f"Customer #{customer_id} does not exist in the banking records.", "warning")
        return redirect(url_for("main.admin_customers"))

    # Historical transactions associated with this customer
    customer_transactions = get_transaction_history(customer_id)

    return render_template(
        "admin_customer_details.html",
        customer=customer,
        transactions=customer_transactions,
        format_currency=format_currency,
    )


@main_bp.route("/admin/customer/<int:customer_id>/approve", methods=["POST"])
@admin_login_required
def admin_approve_account(customer_id: int):
    """
    Account Approval Route ("/admin/customer/<customer_id>/approve").
    Transitions status from 'Pending' to 'Active'.
    """
    admin_id = session.get("admin_username", "admin")
    success, message = approve_customer_account(customer_id, admin_id=admin_id)
    flash(message, "success" if success else "warning")

    # Return admin to referrer or to customer details
    next_url = request.referrer or url_for("main.admin_customer_details", customer_id=customer_id)
    return redirect(next_url)


@main_bp.route("/admin/customer/<int:customer_id>/reject", methods=["POST"])
@admin_login_required
def admin_reject_account(customer_id: int):
    """
    Account Rejection Route ("/admin/customer/<customer_id>/reject").
    Transitions status from 'Pending' to 'Rejected'.
    """
    admin_id = session.get("admin_username", "admin")
    success, message = reject_customer_account(customer_id, admin_id=admin_id)
    flash(message, "info" if success else "warning")

    next_url = request.referrer or url_for("main.admin_customer_details", customer_id=customer_id)
    return redirect(next_url)


@main_bp.route("/admin/customer/<int:customer_id>/freeze", methods=["POST"])
@admin_login_required
def admin_freeze_account(customer_id: int):
    """
    Account Freeze Route ("/admin/customer/<customer_id>/freeze").
    Transitions status from 'Active' to 'Frozen'.
    Customer balances remain unchanged; banking transactions are halted.
    """
    admin_id = session.get("admin_username", "admin")
    success, message = freeze_customer_account(customer_id, admin_id=admin_id)
    flash(message, "warning" if success else "error")

    next_url = request.referrer or url_for("main.admin_customer_details", customer_id=customer_id)
    return redirect(next_url)


@main_bp.route("/admin/customer/<int:customer_id>/unfreeze", methods=["POST"])
@admin_login_required
def admin_unfreeze_account(customer_id: int):
    """
    Account Unfreeze Route ("/admin/customer/<customer_id>/unfreeze").
    Transitions status from 'Frozen' to 'Active'.
    """
    admin_id = session.get("admin_username", "admin")
    success, message = unfreeze_customer_account(customer_id, admin_id=admin_id)
    flash(message, "success" if success else "warning")

    next_url = request.referrer or url_for("main.admin_customer_details", customer_id=customer_id)
    return redirect(next_url)


@main_bp.route("/admin/customer/<int:customer_id>/close", methods=["POST"])
@admin_login_required
def admin_close_account(customer_id: int):
    """
    Account Closure Route ("/admin/customer/<customer_id>/close").
    Transitions status to 'Closed'.
    Ensures customer record and historical transactions are safely preserved.
    """
    admin_id = session.get("admin_username", "admin")
    success, message = close_customer_account(customer_id, admin_id=admin_id)
    flash(message, "info" if success else "error")

    next_url = request.referrer or url_for("main.admin_customer_details", customer_id=customer_id)
    return redirect(next_url)


@main_bp.route("/admin/accounts")
@admin_login_required
def admin_accounts():
    """
    Admin Accounts Ledger View Route ("/admin/accounts").
    Displays all accounts with their status, balance, type, and customer mapping.
    """
    status_filter = request.args.get("status", "All").strip()
    search_query = request.args.get("q", "").strip()

    accounts = search_customers(query=search_query, status_filter=status_filter)

    return render_template(
        "admin_accounts.html",
        accounts=accounts,
        status_filter=status_filter,
        search_query=search_query,
        total_accounts=len(accounts),
        format_currency=format_currency,
    )


@main_bp.route("/admin/transactions")
@admin_login_required
def admin_transactions():
    """
    Admin Transaction Audit Route ("/admin/transactions").
    Read-only view of historical banking transactions with type filtering.
    """
    tx_type = request.args.get("type", "All").strip()
    all_txs = get_all_transactions(filter_type=tx_type)

    return render_template(
        "admin_transactions.html",
        transactions=all_txs,
        selected_type=tx_type,
        total_transactions=len(all_txs),
        format_currency=format_currency,
    )


# -----------------------------------------------------------------------------
# Admin Loan Management Routes (Phase 5)
# -----------------------------------------------------------------------------

@main_bp.route("/admin/loans")
@admin_login_required
def admin_loans():
    """
    Admin Loans Management Console Route ("/admin/loans").
    Displays summary cards, search filter, and list of loan applications.
    """
    search_query = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "All").strip()
    type_filter = request.args.get("type", "All").strip()

    loans = get_all_loans(search_query=search_query, status_filter=status_filter, type_filter=type_filter)
    summary = get_admin_loan_summary()

    return render_template(
        "admin_loans.html",
        loans=loans,
        summary=summary,
        search_query=search_query,
        status_filter=status_filter,
        type_filter=type_filter,
        loan_types=LOAN_TYPES,
        total_found=len(loans),
        format_currency=format_currency,
    )


@main_bp.route("/admin/loan/<int:loan_id>")
@admin_login_required
def admin_loan_details(loan_id: int):
    """
    Admin Loan Review & Details Route ("/admin/loan/<loan_id>").
    Displays application information, applicant profile, and approval/rejection forms.
    """
    loan = get_loan_by_id(loan_id)
    if not loan:
        flash(f"Loan application #{loan_id} was not found.", "warning")
        return redirect(url_for("main.admin_loans"))

    applicant = get_customer_by_id(loan["customer_id"])

    return render_template(
        "admin_loan_details.html",
        loan=loan,
        applicant=applicant,
        format_currency=format_currency,
    )


@main_bp.route("/admin/loan/<int:loan_id>/approve", methods=["POST"])
@admin_login_required
def admin_approve_loan(loan_id: int):
    """
    Admin Loan Approval Route ("/admin/loan/<loan_id>/approve").
    Validates approved amount, interest rate, tenure, and computes EMI.
    """
    approved_amount = request.form.get("approved_amount", "")
    interest_rate = request.form.get("annual_interest_rate", "")
    tenure_months = request.form.get("approved_tenure_months", "")
    admin_notes = request.form.get("admin_notes", "")
    admin_id = session.get("admin_username", "admin")

    success, message = approve_loan_application(
        loan_id=loan_id,
        approved_amount=approved_amount,
        annual_interest_rate=interest_rate,
        tenure_months=tenure_months,
        admin_notes=admin_notes,
        admin_id=admin_id,
    )

    flash(message, "success" if success else "error")
    next_url = request.referrer or url_for("main.admin_loan_details", loan_id=loan_id)
    return redirect(next_url)


@main_bp.route("/admin/loan/<int:loan_id>/reject", methods=["POST"])
@admin_login_required
def admin_reject_loan(loan_id: int):
    """
    Admin Loan Rejection Route ("/admin/loan/<loan_id>/reject").
    Rejects application with a recorded reason.
    """
    rejection_reason = request.form.get("rejection_reason", "")
    admin_id = session.get("admin_username", "admin")
    success, message = reject_loan_application(
        loan_id=loan_id,
        rejection_reason=rejection_reason,
        admin_id=admin_id,
    )

    flash(message, "info" if success else "error")
    next_url = request.referrer or url_for("main.admin_loan_details", loan_id=loan_id)
    return redirect(next_url)


@main_bp.route("/admin/loan/<int:loan_id>/activate", methods=["POST"])
@admin_login_required
def admin_activate_loan(loan_id: int):
    """
    Admin Loan Activation Route ("/admin/loan/<loan_id>/activate").
    Transitions approved loan into active portfolio status.
    """
    admin_id = session.get("admin_username", "admin")
    success, message = activate_loan(loan_id, admin_id=admin_id)
    flash(message, "success" if success else "warning")
    next_url = request.referrer or url_for("main.admin_loan_details", loan_id=loan_id)
    return redirect(next_url)


# -----------------------------------------------------------------------------
# Admin Cheque Book Management Routes
# -----------------------------------------------------------------------------


@main_bp.route("/admin/cheques")
@admin_login_required
def admin_cheques():
    """
    Admin Cheque Book Management Console Route ("/admin/cheques").
    Displays summary cards, search filter, and all cheque requests.
    """
    search_query = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "All").strip()

    summary = get_admin_cheque_summary()
    cheque_requests = get_all_cheque_requests(
        search_query=search_query,
        status_filter=status_filter,
    )

    return render_template(
        "admin_cheques.html",
        summary=summary,
        cheque_requests=cheque_requests,
        search_query=search_query,
        status_filter=status_filter,
        statuses=CHEQUE_STATUSES,
        leaf_options=LEAF_OPTIONS,
    )


@main_bp.route("/admin/cheque/<int:request_id>/approve", methods=["POST"])
@admin_login_required
def admin_approve_cheque(request_id: int):
    """
    Admin Cheque Request Approval Route ("/admin/cheque/<request_id>/approve").
    Validates state transition: Pending -> Approved.
    """
    admin_notes = request.form.get("admin_notes", "").strip()
    admin_id = session.get("admin_username", "admin")
    success, message = approve_cheque_request(
        request_id=request_id,
        admin_notes=admin_notes,
        admin_id=admin_id,
    )
    flash(message, "success" if success else "error")
    return redirect(url_for("main.admin_cheques"))


@main_bp.route("/admin/cheque/<int:request_id>/reject", methods=["POST"])
@admin_login_required
def admin_reject_cheque(request_id: int):
    """
    Admin Cheque Request Rejection Route ("/admin/cheque/<request_id>/reject").
    Requires a valid rejection reason.
    """
    rejection_reason = request.form.get("rejection_reason", "").strip()
    admin_id = session.get("admin_username", "admin")
    success, message = reject_cheque_request(
        request_id=request_id,
        rejection_reason=rejection_reason,
        admin_id=admin_id,
    )
    flash(message, "info" if success else "error")
    return redirect(url_for("main.admin_cheques"))


@main_bp.route("/admin/cheque/<int:request_id>/complete", methods=["POST"])
@admin_login_required
def admin_complete_cheque(request_id: int):
    """
    Admin Cheque Request Completion Route ("/admin/cheque/<request_id>/complete").
    Marks Approved request as Completed.
    """
    admin_notes = request.form.get("admin_notes", "").strip()
    admin_id = session.get("admin_username", "admin")
    success, message = complete_cheque_request(
        request_id=request_id,
        admin_notes=admin_notes,
        admin_id=admin_id,
    )
    flash(message, "success" if success else "error")
    return redirect(url_for("main.admin_cheques"))


# -----------------------------------------------------------------------------
# Admin Reports & Analytics Console (Phase 7)
# -----------------------------------------------------------------------------


@main_bp.route("/admin/reports")
@admin_login_required
def admin_reports():
    """
    Admin Comprehensive Reports & Analytics Console ("/admin/reports").
    Aggregates metrics for customers, account statuses, transactions, loans,
    and cheque book requests with date-range filtering.
    """
    raw_start = request.args.get("start_date", "").strip()
    raw_end = request.args.get("end_date", "").strip()

    is_valid, err_msg, start_date, end_date = validate_date_range(raw_start, raw_end)
    if not is_valid:
        flash(err_msg, "warning")
        start_date = None
        end_date = None

    report = generate_admin_comprehensive_report(start_date=start_date, end_date=end_date)

    return render_template(
        "admin_reports.html",
        report=report,
        start_date=start_date or "",
        end_date=end_date or "",
        format_currency=format_currency,
        mask_account_number=mask_account_number,
    )


@main_bp.route("/admin/reports/print")
@admin_login_required
def admin_reports_print():
    """
    Printable and PDF-ready administrative operational report view.
    """
    raw_start = request.args.get("start_date", "").strip()
    raw_end = request.args.get("end_date", "").strip()

    is_valid, _, start_date, end_date = validate_date_range(raw_start, raw_end)
    if not is_valid:
        start_date = None
        end_date = None

    report = generate_admin_comprehensive_report(start_date=start_date, end_date=end_date)

    return render_template(
        "admin_reports_print.html",
        report=report,
        start_date=start_date or "",
        end_date=end_date or "",
        format_currency=format_currency,
        mask_account_number=mask_account_number,
    )


@main_bp.route("/admin/reports/export/<dataset>")
@admin_login_required
def admin_export_csv(dataset: str):
    """
    Exports administrative data collections as secure, sanitized CSV files.
    Allowed datasets: customers, transactions, loans, cheques, audit-logs.
    """
    raw_start = request.args.get("start_date", "").strip()
    raw_end = request.args.get("end_date", "").strip()
    filter_val = request.args.get("filter", "All").strip()

    is_valid, _, start_date, end_date = validate_date_range(raw_start, raw_end)
    if not is_valid:
        start_date = None
        end_date = None

    date_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_ds = dataset.lower().replace("-", "_")

    if clean_ds == "customers":
        csv_content = export_customers_csv(status_filter=filter_val)
        filename = f"customers_report_{date_tag}.csv"
    elif clean_ds == "transactions":
        csv_content = export_transactions_csv(start_date=start_date, end_date=end_date, transaction_type=filter_val)
        filename = f"transactions_report_{date_tag}.csv"
    elif clean_ds == "loans":
        csv_content = export_loans_csv(start_date=start_date, end_date=end_date, status_filter=filter_val)
        filename = f"loans_report_{date_tag}.csv"
    elif clean_ds in ("cheques", "cheque_requests"):
        csv_content = export_cheques_csv(start_date=start_date, end_date=end_date, status_filter=filter_val)
        filename = f"cheque_requests_report_{date_tag}.csv"
    elif clean_ds in ("audit_logs", "audit"):
        csv_content = export_audit_logs_csv(start_date=start_date, end_date=end_date, action_filter=filter_val)
        filename = f"audit_trail_report_{date_tag}.csv"
    else:
        flash(f"Unknown export dataset '{dataset}'.", "error")
        return redirect(url_for("main.admin_reports"))

    response = Response(csv_content, mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@main_bp.route("/admin/audit-logs")
@admin_login_required
def admin_audit_logs():
    """
    Admin Audit Trail Viewer Route ("/admin/audit-logs").
    Displays historical administrative security and governance logs.
    """
    action_filter = request.args.get("action", "All").strip()
    logs = get_audit_logs(limit=200, action_filter=action_filter)

    return render_template(
        "admin_audit_logs.html",
        logs=logs,
        selected_action=action_filter,
        total_logs=len(logs),
    )


# =============================================================================
# Custom Application Error Handlers
# =============================================================================


@main_bp.app_errorhandler(404)
def not_found_error(error):
    """Safe, custom 404 Not Found error handler."""
    return (
        render_template(
            "error.html",
            error_code=404,
            error_title="Resource Not Found",
            error_message="The banking page, customer profile, or resource you requested does not exist or has been moved.",
        ),
        404,
    )


@main_bp.app_errorhandler(403)
def forbidden_error(error):
    """Safe, custom 403 Forbidden error handler."""
    return (
        render_template(
            "error.html",
            error_code=403,
            error_title="Access Restricted",
            error_message="You do not have authorization to access this operational resource.",
        ),
        403,
    )


@main_bp.app_errorhandler(500)
def internal_server_error(error):
    """Safe, custom 500 Internal Server Error handler (masks stack traces)."""
    return (
        render_template(
            "error.html",
            error_code=500,
            error_title="Internal Processing Error",
            error_message="The banking platform encountered an unexpected recoverable error. Operational state remains secure.",
        ),
        500,
    )

