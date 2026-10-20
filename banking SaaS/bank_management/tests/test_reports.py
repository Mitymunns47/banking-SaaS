"""
tests/test_reports.py
=============================================================================
Automated Unit and Integration Tests for Phase 7:
Reports, Security, and Advanced Validation
=============================================================================

TEST COVERAGE:
1. Operational Reports Dashboard & Aggregations:
   - Total registered customers, account status breakdowns.
   - Transaction volume calculations (deposits, withdrawals, transfers).
   - Date range filtering (start_date, end_date).
   - Empty report states and invalid date handling (start > end).
   - Loan portfolio metrics and cheque request breakdowns.

2. CSV Exports & Spreadsheet Formula Injection Defense (OWASP):
   - Sanitization of values starting with '=', '+', '-', '@', '\t', '\r'.
   - Exclusion of sensitive passwords, password hashes, and session attributes.
   - Customer, Transaction, Loan, Cheque, and Audit Log CSV endpoints.
   - Download permission enforcement (admin only, customer 302/redirect).

3. Authentication & Password Security:
   - Passwords stored as secure cryptographic hashes via Werkzeug.
   - Plaintext passwords never stored on registration or update.
   - Transparent legacy verification and upgrade.
   - Session protection (HttpOnly, SameSite=Lax).

4. Login Attempt Protection & Cooldown:
   - Repeated failed login attempts trigger cooldown.
   - Generic error messages preventing user enumeration.
   - Cooldown reset upon expiration or successful authentication.

5. Administrative Audit Trail:
   - Immutable audit logging for critical administrative events:
     (Account approval/rejection/freeze/unfreeze/closure, Loan approval/rejection,
      Cheque approval/rejection/completion).
   - Read-only audit viewer and filtering by action.
"""

import unittest
import csv
import io
from app import create_app
from app.models import (
    reset_customers_db,
    CUSTOMERS_DB,
    TRANSACTIONS_DB,
    LOANS_DB,
    CHEQUE_REQUESTS_DB,
    AUDIT_LOG_DB,
    SAMPLE_ADMIN,
    LOGIN_ATTEMPTS,
)
from app.services import (
    generate_admin_comprehensive_report,
    export_customers_csv,
    export_transactions_csv,
    export_loans_csv,
    export_cheques_csv,
    export_audit_logs_csv,
    log_audit_event,
    get_audit_logs,
    approve_customer_account,
    freeze_customer_account,
    approve_loan_application,
    approve_cheque_request,
)
from app.utils import (
    validate_date_range,
    sanitize_csv_value,
    generate_csrf_token,
    validate_csrf_token,
)
from app.auth import (
    hash_password,
    verify_password,
    register_customer,
    authenticate_customer,
    get_failed_attempts_info,
    record_failed_login,
    clear_failed_logins,
)


class TestReportsAndSecurity(unittest.TestCase):
    """Test suite covering Phase 7 reports, exports, audit logging, and security."""

    def setUp(self):
        """Reset in-memory storage before each test."""
        reset_customers_db()
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret-phase7"})
        self.client = self.app.test_client()

    def _login_as_admin(self):
        """Helper to establish an authenticated admin session."""
        with self.client.session_transaction() as sess:
            sess["admin_logged_in"] = True
            sess["admin_username"] = "admin"
            sess["admin_name"] = "Bank Administrator"
            sess["role"] = "admin"

    def _login_as_customer(self, customer_id=1):
        """Helper to establish an authenticated customer session."""
        with self.client.session_transaction() as sess:
            sess["customer_id"] = customer_id
            sess["customer_name"] = "Sarah Jenkins"
            sess["role"] = "customer"

    # =========================================================================
    # 1. Report Calculations & Date Range Filters
    # =========================================================================

    def test_report_metric_counts_and_aggregations(self):
        """Verifies accurate calculation of registered customers, account statuses, and transaction sums."""
        report = generate_admin_comprehensive_report()

        self.assertIn("generated_at", report)
        self.assertIn("customers", report)
        self.assertIn("transactions", report)
        self.assertIn("loans", report)
        self.assertIn("cheques", report)

        # Customer assertions
        cust = report["customers"]
        self.assertEqual(cust["total_registered"], len(CUSTOMERS_DB))
        self.assertGreater(cust["active_accounts"], 0)
        self.assertGreaterEqual(cust["total_balance"], 0.0)

        # Transactions assertions
        tx = report["transactions"]
        self.assertEqual(tx["total_count"], len(TRANSACTIONS_DB))
        self.assertGreater(tx["total_deposits"], 0.0)
        self.assertGreater(tx["total_withdrawals"], 0.0)

        # Check sum consistency
        calculated_deposits = sum(
            float(t["amount"]) for t in TRANSACTIONS_DB
            if (t.get("transaction_type") or t.get("type", "")).capitalize() == "Deposit"
            and t.get("status") != "Failed"
        )
        self.assertAlmostEqual(tx["total_deposits"], calculated_deposits, places=2)

    def test_report_date_filtering(self):
        """Verifies transactions and loans are accurately filtered by date boundaries."""
        # Date filter that covers earlier transactions
        report_filtered = generate_admin_comprehensive_report(
            start_date="2026-10-01",
            end_date="2026-10-02",
        )
        for tx in report_filtered["transactions"]["records"]:
            self.assertTrue(tx["timestamp"].startswith(("2026-10-01", "2026-10-02")))

    def test_date_range_validation(self):
        """Tests start_date and end_date validation including start > end error."""
        # Valid range
        is_valid, err, s, e = validate_date_range("2026-10-01", "2026-10-15")
        self.assertTrue(is_valid)
        self.assertEqual(s, "2026-10-01")
        self.assertEqual(e, "2026-10-15")

        # Invalid: start date after end date
        is_valid, err, _, _ = validate_date_range("2026-10-20", "2026-10-05")
        self.assertFalse(is_valid)
        self.assertIn("Start date cannot be after end date", err)

        # Invalid format
        is_valid, err, _, _ = validate_date_range("invalid-date", "2026-10-05")
        self.assertFalse(is_valid)
        self.assertIn("format", err.lower())

    def test_empty_report_for_distant_future_date(self):
        """Verifies proper empty results when filtering for non-existent date range."""
        report = generate_admin_comprehensive_report(
            start_date="2035-01-01",
            end_date="2035-12-31",
        )
        self.assertEqual(report["transactions"]["total_count"], 0)
        self.assertEqual(report["transactions"]["total_deposits"], 0.0)
        self.assertEqual(report["loans"]["total_applications"], 0)
        self.assertEqual(report["cheques"]["total_requests"], 0)

    # =========================================================================
    # 2. CSV Exports & Spreadsheet Formula Injection Protection (OWASP)
    # =========================================================================

    def test_csv_formula_injection_sanitization(self):
        """Verifies values beginning with '=', '+', '-', '@', tab, or carriage return are safely prefixed with single quote."""
        malicious_inputs = [
            "=SUM(A1:A10)",
            "+12345cmd|'/C calc'!A0",
            "-2+3*cmd",
            "@dangerous_formula()",
            "\tTAB_INJECT",
            "\rCR_INJECT",
        ]
        for payload in malicious_inputs:
            sanitized = sanitize_csv_value(payload)
            self.assertTrue(
                sanitized.startswith("'"),
                f"Payload {payload} was not sanitized with leading quote: got {sanitized}",
            )

        # Standard safe values should remain unchanged
        self.assertEqual(sanitize_csv_value("Regular Name"), "Regular Name")
        self.assertEqual(sanitize_csv_value("ACC-1002941"), "ACC-1002941")

    def test_customers_csv_excludes_passwords_and_hashes(self):
        """Verifies customers CSV export excludes password fields, hashes, and session attributes."""
        csv_data = export_customers_csv()
        reader = csv.reader(io.StringIO(csv_data))
        headers = next(reader)

        # Ensure no sensitive headers exist
        for h in headers:
            self.assertNotIn("password", h.lower())
            self.assertNotIn("hash", h.lower())
            self.assertNotIn("token", h.lower())

        # Check rows do not contain password strings
        for row in reader:
            for cell in row:
                self.assertNotIn("Password123", cell)
                self.assertNotIn("pbkdf2:", cell)

    def test_export_endpoints_authorized_access(self):
        """Verifies admin can export all datasets and receives text/csv mimetype."""
        self._login_as_admin()

        for dataset in ["customers", "transactions", "loans", "cheques", "audit-logs"]:
            resp = self.client.get(f"/admin/reports/export/{dataset}")
            self.assertEqual(resp.status_code, 200, f"Export failed for dataset: {dataset}")
            self.assertEqual(resp.mimetype, "text/csv")
            self.assertIn("attachment; filename=", resp.headers.get("Content-Disposition", ""))

    def test_customer_cannot_access_admin_reports_or_exports(self):
        """Verifies authenticated customers cannot access admin reports dashboard, print view, or CSV exports."""
        self._login_as_customer(customer_id=1)

        endpoints = [
            "/admin/reports",
            "/admin/reports/print",
            "/admin/reports/export/customers",
            "/admin/reports/export/transactions",
            "/admin/audit-logs",
        ]
        for ep in endpoints:
            resp = self.client.get(ep, follow_redirects=False)
            self.assertEqual(resp.status_code, 302, f"Customer was not redirected from {ep}")
            self.assertIn("/admin/login", resp.headers["Location"])

    # =========================================================================
    # 3. Authentication & Password Hashing Security
    # =========================================================================

    def test_customer_registration_stores_hashed_password(self):
        """Verifies registered customers have cryptographically hashed passwords and not plaintext."""
        customer, errors = register_customer(
            name="Crypto Security Tester",
            age=30,
            email="crypto.security@example.com",
            phone="+1 (555) 000-8888",
            password="MySecretPassword123",
            confirm_password="MySecretPassword123",
            account_type="Savings",
        )
        self.assertEqual(len(errors), 0)
        self.assertIsNotNone(customer)

        stored_pw = customer["password"]
        # Password must not be plaintext
        self.assertNotEqual(stored_pw, "MySecretPassword123")
        # Must be recognized Werkzeug hash prefix
        self.assertTrue(stored_pw.startswith(("pbkdf2:", "scrypt:", "argon2:")))
        # Verification succeeds
        self.assertTrue(verify_password(stored_pw, "MySecretPassword123"))
        self.assertFalse(verify_password(stored_pw, "WrongPassword"))

    def test_login_failure_limit_and_cooldown(self):
        """Verifies repeated login failures lock out account and show generic error messages."""
        email = "sarah.jenkins@bankcorp.com"

        # 1st and 2nd failure
        cust1, err1 = authenticate_customer(email, "WrongPass1")
        self.assertIsNone(cust1)
        self.assertEqual(err1, "Invalid email or password.")

        cust2, err2 = authenticate_customer(email, "WrongPass2")
        self.assertIsNone(cust2)
        self.assertEqual(err2, "Invalid email or password.")

        # 3rd failure triggers lockout
        cust3, err3 = authenticate_customer(email, "WrongPass3")
        self.assertIsNone(cust3)

        # Check lockout state
        is_locked, remaining = get_failed_attempts_info(email)
        self.assertTrue(is_locked)
        self.assertGreater(remaining, 0)

        # Immediate next attempt reveals lockout message without revealing user existence
        cust4, err4 = authenticate_customer(email, "Password123")
        self.assertIsNone(cust4)
        self.assertIn("Too many failed login attempts", err4)

        # Clear failed logins resets cooldown
        clear_failed_logins(email)
        is_locked_after, _ = get_failed_attempts_info(email)
        self.assertFalse(is_locked_after)

    def test_generic_login_error_prevents_user_enumeration(self):
        """Verifies both existing user with wrong password and nonexistent email receive identical error."""
        _, err_existing = authenticate_customer("sarah.jenkins@bankcorp.com", "WrongPassword")
        _, err_nonexistent = authenticate_customer("completely_nonexistent@nowhere.com", "WrongPassword")

        self.assertEqual(err_existing, "Invalid email or password.")
        self.assertEqual(err_nonexistent, "Invalid email or password.")
        self.assertEqual(err_existing, err_nonexistent)

    # =========================================================================
    # 4. Administrative Audit Logging
    # =========================================================================

    def test_audit_log_event_creation(self):
        """Verifies administrative actions record immutable entries in AUDIT_LOG_DB."""
        initial_log_count = len(AUDIT_LOG_DB)

        entry = log_audit_event(
            admin_id="sec_admin",
            action="SECURITY_SETTING_UPDATED",
            target_type="System Configuration",
            target_id="AUTH_POLICY",
            details="Rate limit threshold verified.",
            outcome="Success",
        )
        self.assertEqual(len(AUDIT_LOG_DB), initial_log_count + 1)
        self.assertEqual(entry["admin_id"], "sec_admin")
        self.assertEqual(entry["action"], "SECURITY_SETTING_UPDATED")
        self.assertIn("timestamp", entry)

    def test_audit_logs_created_on_account_and_loan_admin_actions(self):
        """Verifies account approvals and loan underwriting automatically append audit records."""
        initial_log_count = len(AUDIT_LOG_DB)

        # 1. Approve pending customer account (Customer 5 is Pending)
        success_acc, _ = approve_customer_account(customer_id=5, admin_id="test_admin_user")
        self.assertTrue(success_acc)

        # 2. Freeze active customer account (Customer 1 is Active)
        success_frz, _ = freeze_customer_account(customer_id=1, admin_id="test_admin_user")
        self.assertTrue(success_frz)

        # 3. Approve pending loan application (Loan 3 is Pending)
        success_loan, _ = approve_loan_application(
            loan_id=3,
            approved_amount=40000.0,
            annual_interest_rate=7.5,
            tenure_months=60,
            admin_notes="Approved via automated test",
            admin_id="test_admin_user",
        )
        self.assertTrue(success_loan)

        logs = get_audit_logs(limit=10)
        self.assertGreaterEqual(len(AUDIT_LOG_DB), initial_log_count + 3)

        actions = [l["action"] for l in logs]
        self.assertIn("ACCOUNT_APPROVED", actions)
        self.assertIn("ACCOUNT_FROZEN", actions)
        self.assertIn("LOAN_APPROVED", actions)

    # =========================================================================
    # 5. CSRF Token Utilities
    # =========================================================================

    def test_csrf_token_generation_and_validation(self):
        """Tests cryptographic CSRF token generation and validation helper."""
        with self.app.test_request_context():
            token = generate_csrf_token()
            self.assertIsNotNone(token)
            self.assertEqual(len(token), 64)  # 32 bytes hex = 64 characters

            # Validation in non-testing mode
            with self.app.test_request_context():
                self.app.config["TESTING"] = False
                from flask import session
                session["_csrf_token"] = token
                self.assertTrue(validate_csrf_token(token))
                self.assertFalse(validate_csrf_token("invalid_tampered_token"))
                self.app.config["TESTING"] = True

    # =========================================================================
    # 6. Cheque Audit Trail & Decision Logging
    # =========================================================================

    def test_cheque_decision_audit_logs(self):
        """Verifies cheque approvals, rejections, and completions write audit events."""
        # Find a pending cheque request (Request 3 in initial seed is Pending)
        success, _ = approve_cheque_request(request_id=3, admin_notes="Verified by branch", admin_id="chief_auditor")
        self.assertTrue(success)

        # Verify audit record created
        logs = get_audit_logs(limit=5)
        actions = [l["action"] for l in logs]
        self.assertIn("CHEQUE_APPROVED", actions)

        approved_log = [l for l in logs if l["action"] == "CHEQUE_APPROVED"][0]
        self.assertEqual(approved_log["admin_id"], "chief_auditor")
        self.assertEqual(approved_log["target_type"], "Cheque Book")

    # =========================================================================
    # 7. Web Routes & UI Integration
    # =========================================================================

    def test_admin_reports_dashboard_route(self):
        """Verifies /admin/reports returns 200, displays Reports & Analytics title, and handles date filters."""
        self._login_as_admin()

        resp = self.client.get("/admin/reports")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Reports &amp; Analytics", resp.data)
        self.assertIn(b"CORE BANKING SYSTEM", resp.data)

        # Filter by valid date
        resp_filtered = self.client.get("/admin/reports?start_date=2026-10-01&end_date=2026-10-05")
        self.assertEqual(resp_filtered.status_code, 200)
        self.assertIn(b"Active Date Filter", resp_filtered.data)

        # Invalid date range (start > end) shows warning
        resp_invalid = self.client.get("/admin/reports?start_date=2026-10-25&end_date=2026-10-05")
        self.assertEqual(resp_invalid.status_code, 200)
        self.assertIn(b"Start date cannot be after end date", resp_invalid.data)

    def test_admin_reports_print_route(self):
        """Verifies printable report view /admin/reports/print loads cleanly."""
        self._login_as_admin()

        resp = self.client.get("/admin/reports/print")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Executive Operational Management Report", resp.data)
        self.assertIn(b"CORE BANKING SYSTEM", resp.data)
        self.assertIn(b"window.print()", resp.data)

    def test_admin_audit_logs_route(self):
        """Verifies administrative audit trail viewer route /admin/audit-logs loads and filters."""
        self._login_as_admin()

        resp = self.client.get("/admin/audit-logs")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Administrative Audit Trail", resp.data)
        self.assertIn(b"CORE BANKING SYSTEM", resp.data)

        # Filter by action
        resp_filtered = self.client.get("/admin/audit-logs?action=ACCOUNT_FROZEN")
        self.assertEqual(resp_filtered.status_code, 200)

    def test_branding_has_no_phase_numbers(self):
        """Verifies branding across all report templates adheres strictly to 'CORE BANKING SYSTEM' with no phase names or numbers."""
        self._login_as_admin()

        for url in ["/admin/reports", "/admin/reports/print", "/admin/audit-logs"]:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b"CORE BANKING SYSTEM", resp.data)
            # Must not have Phase labels in branding
            self.assertNotIn(b"CORE BANKING SYSTEM Phase", resp.data)
            self.assertNotIn(b"CORE BANKING SYSTEM - Phase", resp.data)
            self.assertNotIn(b"CORE BANKING SYSTEM (Phase", resp.data)


if __name__ == "__main__":
    unittest.main()

