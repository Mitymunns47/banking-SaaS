"""
tests/test_phase8.py
=============================================================================
Automated Unit and Integration Tests for Phase 8:
Final Testing, Optimization, Verification, and Error Handling
=============================================================================

TEST COVERAGE:
1. Custom Error Pages (404 Not Found, 403 Forbidden, 500 Internal Error)
2. CSRF Token Inclusion Across All Interactive Forms
3. Branding Integrity (Strictly "CORE BANKING SYSTEM", No Phase Suffixes)
4. Full Customer End-to-End Workflow & Session Invalidation on Logout
5. Full Admin End-to-End Workflow & Session Invalidation on Logout
6. Atomic Transactions & Zero Partial Updates
7. EMI Edge Cases (Zero Interest & Positive Interest)
"""

import sys
import os
import unittest
from flask import abort

# Ensure app package is importable from tests directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.models import (
    reset_customers_db,
    CUSTOMERS_DB,
    TRANSACTIONS_DB,
    LOANS_DB,
    CHEQUE_REQUESTS_DB,
    AUDIT_LOG_DB,
    SAMPLE_ADMIN,
)
from app.services import (
    calculate_loan_repayment_details,
    deposit_money,
    withdraw_money,
    transfer_money,
    apply_for_loan,
    request_cheque_book,
    get_customer_by_id,
    approve_customer_account,
    get_loan_by_id,
)


class TestPhase8FinalVerification(unittest.TestCase):
    """Comprehensive Phase 8 Verification Test Suite."""

    def setUp(self):
        """Reset data stores and initialize clean Flask test client."""
        reset_customers_db()
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()

    # =========================================================================
    # 1. Custom Error Pages Tests
    # =========================================================================

    def test_404_error_page(self):
        """Verifies that non-existent routes return HTTP 404 with friendly error.html."""
        resp = self.client.get("/non-existent-route-for-testing-404")
        self.assertEqual(resp.status_code, 404)
        self.assertIn(b"404", resp.data)
        self.assertIn(b"Resource Not Found", resp.data)
        self.assertIn(b"CORE BANKING SYSTEM", resp.data)
        self.assertIn(b"Return to Homepage", resp.data)

    def test_403_and_500_error_handlers(self):
        """Verifies custom error handler logic for 403 and 500 status codes."""
        test_app = create_app({"TESTING": True})

        @test_app.route("/trigger-403")
        def trigger_403():
            abort(403)

        @test_app.route("/trigger-500")
        def trigger_500():
            abort(500)

        test_client = test_app.test_client()

        # Test 403
        resp_403 = test_client.get("/trigger-403")
        self.assertEqual(resp_403.status_code, 403)
        self.assertIn(b"403", resp_403.data)
        self.assertIn(b"Access Restricted", resp_403.data)
        self.assertIn(b"CORE BANKING SYSTEM", resp_403.data)

        # Test 500
        resp_500 = test_client.get("/trigger-500")
        self.assertEqual(resp_500.status_code, 500)
        self.assertIn(b"500", resp_500.data)
        self.assertIn(b"Internal Processing Error", resp_500.data)
        self.assertIn(b"CORE BANKING SYSTEM", resp_500.data)

    # =========================================================================
    # 2. CSRF Token Inclusion Across State-Changing Forms
    # =========================================================================

    def test_csrf_token_rendered_in_forms(self):
        """Verifies that CSRF token hidden inputs exist in public and authenticated forms."""
        # Public forms
        public_urls = ["/login", "/register", "/admin/login"]
        for url in public_urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b'name="csrf_token"', resp.data, f"Missing CSRF token in {url}")

        # Customer authenticated forms
        with self.client.session_transaction() as sess:
            sess["customer_id"] = 1
            sess["customer_name"] = "Sarah Jenkins"
            sess["role"] = "customer"

        customer_urls = [
            "/deposit",
            "/withdraw",
            "/transfer",
            "/loans/apply",
            "/cheques/request",
            "/change-password",
        ]
        for url in customer_urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f"URL {url} returned {resp.status_code}")
            self.assertIn(b'name="csrf_token"', resp.data, f"Missing CSRF token in {url}")

    # =========================================================================
    # 3. Branding Integrity Audit
    # =========================================================================

    def test_strict_branding_across_views(self):
        """Verifies that branding is strictly 'CORE BANKING SYSTEM' with no phase suffixes."""
        urls_to_check = [
            "/",
            "/login",
            "/register",
            "/admin/login",
        ]
        for url in urls_to_check:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b"CORE BANKING SYSTEM", resp.data)
            self.assertNotIn(b"CORE BANKING SYSTEM Phase", resp.data)
            self.assertNotIn(b"CORE BANKING SYSTEM - Phase", resp.data)
            self.assertNotIn(b"CORE BANKING SYSTEM (Phase", resp.data)

    # =========================================================================
    # 4. Customer End-to-End Workflow & Session Handling
    # =========================================================================

    def test_customer_complete_lifecycle(self):
        """Tests complete customer lifecycle: register -> login -> deposit -> withdraw -> transfer -> apply loan -> logout."""
        # 1. Register new customer
        reg_payload = {
            "name": "Jane Doe",
            "age": "28",
            "email": "jane.doe.p8@banktest.com",
            "phone": "555-987-6543",
            "password": "Password123!",
            "confirm_password": "Password123!",
        }
        reg_resp = self.client.post("/register", data=reg_payload, follow_redirects=True)
        self.assertEqual(reg_resp.status_code, 200)
        self.assertIn(b"Registration successful for Jane Doe", reg_resp.data)

        # Find customer and activate account
        cust = next(c for c in CUSTOMERS_DB if c["email"] == "jane.doe.p8@banktest.com")
        cust_id = cust["customer_id"]
        approve_customer_account(cust_id)

        # 2. Login
        login_resp = self.client.post("/login", data={
            "email": "jane.doe.p8@banktest.com",
            "password": "Password123!",
        }, follow_redirects=True)
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn(b"Welcome, Jane Doe", login_resp.data)

        # 3. Customer accesses dashboard
        dash_resp = self.client.get("/dashboard")
        self.assertEqual(dash_resp.status_code, 200)
        self.assertIn(b"Jane Doe", dash_resp.data)

        # 4. Deposit funds
        dep_resp = self.client.post("/deposit", data={"amount": "500.00"}, follow_redirects=True)
        self.assertEqual(dep_resp.status_code, 200)
        self.assertIn(b"Successfully deposited", dep_resp.data)
        self.assertEqual(cust["balance"], 500.00)

        # 5. Withdraw funds
        wth_resp = self.client.post("/withdraw", data={"amount": "100.00"}, follow_redirects=True)
        self.assertEqual(wth_resp.status_code, 200)
        self.assertIn(b"Successfully withdrew", wth_resp.data)
        self.assertEqual(cust["balance"], 400.00)

        # 6. Transfer funds to Sarah Jenkins (Account ACC-1002941)
        sarah = CUSTOMERS_DB[0]
        trf_resp = self.client.post("/transfer", data={
            "recipient_account": sarah["account_number"],
            "amount": "150.00",
            "description": "Educational Project Test Transfer",
        }, follow_redirects=True)
        self.assertEqual(trf_resp.status_code, 200)
        self.assertIn(b"Successfully transferred", trf_resp.data)
        self.assertEqual(cust["balance"], 250.00)

        # 7. Apply for a Loan
        loan_resp = self.client.post("/loans/apply", data={
            "loan_type": "Personal",
            "requested_amount": "2500.00",
            "tenure_months": "12",
            "purpose": "Home study equipment",
            "monthly_income": "4000.00",
        }, follow_redirects=True)
        self.assertEqual(loan_resp.status_code, 200)
        self.assertIn(b"submitted successfully", loan_resp.data)

        # 8. Request a Cheque Book
        chq_resp = self.client.post("/cheques/request", data={
            "account_number": cust["account_number"],
            "leaves": "25",
            "delivery_notes": "Branch pickup",
        }, follow_redirects=True)
        self.assertEqual(chq_resp.status_code, 200)
        self.assertIn(b"submitted successfully", chq_resp.data)

        # 9. Logout
        logout_resp = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(logout_resp.status_code, 200)
        self.assertIn(b"signed out safely", logout_resp.data)

        # 10. Confirm session is cleared - accessing dashboard redirects to /login
        protected_resp = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(protected_resp.status_code, 302)
        self.assertIn("/login", protected_resp.headers["Location"])

    # =========================================================================
    # 5. Admin End-to-End Workflow & Session Handling
    # =========================================================================

    def test_admin_complete_lifecycle(self):
        """Tests complete admin lifecycle: login -> dashboard -> freeze/unfreeze -> approve loan -> approve cheque -> export CSV -> logout."""
        # 1. Admin login
        admin_login = self.client.post("/admin/login", data={
            "username_or_email": SAMPLE_ADMIN["username"],
            "password": SAMPLE_ADMIN["password"],
        }, follow_redirects=True)
        self.assertEqual(admin_login.status_code, 200)
        self.assertIn(b"Admin Dashboard", admin_login.data)

        # 2. View Accounts & Freeze Customer 1
        freeze_resp = self.client.post("/admin/customer/1/freeze", follow_redirects=True)
        self.assertEqual(freeze_resp.status_code, 200)
        self.assertEqual(CUSTOMERS_DB[0]["account_status"], "Frozen")

        # 3. Unfreeze Customer 1
        unfreeze_resp = self.client.post("/admin/customer/1/unfreeze", follow_redirects=True)
        self.assertEqual(unfreeze_resp.status_code, 200)
        self.assertEqual(CUSTOMERS_DB[0]["account_status"], "Active")

        # 4. View & Approve Loan (loan 3 is pending in seed with $50000 requested)
        approve_loan = self.client.post("/admin/loan/3/approve", data={
            "approved_amount": "50000.00",
            "annual_interest_rate": "8.25",
            "approved_tenure_months": "120",
            "admin_notes": "Verified property appraisal.",
        }, follow_redirects=True)
        self.assertEqual(approve_loan.status_code, 200)
        loan_3 = get_loan_by_id(3)
        self.assertEqual(loan_3["status"], "Approved")

        # 5. View & Approve Cheque Book Request (request 3 is pending in seed)
        approve_chq = self.client.post("/admin/cheque/3/approve", data={
            "admin_notes": "Batch verified.",
        }, follow_redirects=True)
        self.assertEqual(approve_chq.status_code, 200)
        chq_3 = next(c for c in CHEQUE_REQUESTS_DB if c["request_id"] == 3)
        self.assertEqual(chq_3["status"], "Approved")

        # 6. Export Reports CSV
        csv_resp = self.client.get("/admin/reports/export/transactions")
        self.assertEqual(csv_resp.status_code, 200)
        self.assertEqual(csv_resp.mimetype, "text/csv")
        self.assertIn(b"Transaction ID", csv_resp.data)

        # 7. View Audit Trail
        audit_resp = self.client.get("/admin/audit-logs")
        self.assertEqual(audit_resp.status_code, 200)
        self.assertIn(b"Administrative Audit Trail", audit_resp.data)

        # 8. Logout
        logout_resp = self.client.get("/admin/logout", follow_redirects=True)
        self.assertEqual(logout_resp.status_code, 200)
        self.assertIn(b"Administrator session terminated", logout_resp.data)

        # 9. Verify admin routes protected after logout
        admin_dash_resp = self.client.get("/admin/dashboard", follow_redirects=False)
        self.assertEqual(admin_dash_resp.status_code, 302)
        self.assertIn("/admin/login", admin_dash_resp.headers["Location"])

    # =========================================================================
    # 6. Banking Logic & EMI Calculations
    # =========================================================================

    def test_emi_calculations_zero_interest_and_positive(self):
        """Verifies EMI calculation handles both standard interest rates and zero-interest loans."""
        # Standard positive interest (P=10000, r=12% annual = 1% monthly, n=12 months)
        # EMI = 888.49
        details_pos = calculate_loan_repayment_details(
            principal=10000.0,
            annual_interest_rate=12.0,
            tenure_months=12,
        )
        self.assertEqual(details_pos["emi"], 888.49)
        self.assertEqual(details_pos["total_repayment"], 10661.88)
        self.assertEqual(details_pos["total_interest"], 661.88)

        # Zero-interest promotional/educational loan (P=12000, r=0%, n=12 months)
        # EMI = 12000 / 12 = 1000.00
        details_zero = calculate_loan_repayment_details(
            principal=12000.0,
            annual_interest_rate=0.0,
            tenure_months=12,
        )
        self.assertEqual(details_zero["emi"], 1000.00)
        self.assertEqual(details_zero["total_repayment"], 12000.00)
        self.assertEqual(details_zero["total_interest"], 0.00)

        # Edge cases: zero principal or zero tenure
        details_none = calculate_loan_repayment_details(
            principal=0.0,
            annual_interest_rate=10.0,
            tenure_months=12,
        )
        self.assertEqual(details_none["emi"], 0.0)

    def test_transfer_integrity_and_rejections(self):
        """Verifies transfers cannot succeed to inactive, frozen, non-existent, or self accounts."""
        sender = CUSTOMERS_DB[0]  # ACC-1002941, balance 4850.75
        initial_sender_balance = sender["balance"]

        # 1. Self transfer rejection
        success, msg, _ = transfer_money(sender["customer_id"], sender["account_number"], 100.0)
        self.assertFalse(success)
        self.assertIn("own account", msg.lower())
        self.assertEqual(sender["balance"], initial_sender_balance)

        # 2. Non-existent recipient
        success, msg, _ = transfer_money(sender["customer_id"], "ACC-9999NONEXISTENT", 100.0)
        self.assertFalse(success)
        self.assertIn("not found", msg.lower())
        self.assertEqual(sender["balance"], initial_sender_balance)

        # 3. Insufficient balance
        success, msg, _ = transfer_money(sender["customer_id"], CUSTOMERS_DB[1]["account_number"], 999999.0)
        self.assertFalse(success)
        self.assertIn("insufficient", msg.lower())
        self.assertEqual(sender["balance"], initial_sender_balance)

        # 4. Inactive/Frozen recipient rejection
        recipient = CUSTOMERS_DB[1]
        recipient["account_status"] = "Frozen"
        recipient["is_active"] = False
        success, msg, _ = transfer_money(sender["customer_id"], recipient["account_number"], 50.0)
        self.assertFalse(success)
        self.assertIn("inactive", msg.lower())
        self.assertEqual(sender["balance"], initial_sender_balance)


if __name__ == "__main__":
    unittest.main()
