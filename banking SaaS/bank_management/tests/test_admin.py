"""
tests/test_admin.py
=============================================================================
Automated Admin Management, Security & Lifecycle Tests for CORE BANKING SYSTEM
=============================================================================

PYTHON FUNDAMENTALS DEMONSTRATED IN THIS FILE:
1. Automated Testing with Python's standard `unittest` framework.
2. State isolation: resetting data models prior to each test run.
3. Verification of Boolean logic and conditional operators (and, or, not).
4. Role-based access control and session-based authorization testing.
5. Verification of financial data integrity: status modifications must never
   alter customer balances or purge ledger transaction history.
"""

import sys
import os
import unittest

# Ensure app package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.models import reset_customers_db, CUSTOMERS_DB, TRANSACTIONS_DB, SAMPLE_ADMIN
from app.services import (
    get_customer_by_id,
    get_all_customers,
    search_customers,
    approve_customer_account,
    reject_customer_account,
    freeze_customer_account,
    unfreeze_customer_account,
    close_customer_account,
    get_admin_dashboard_summary,
    get_all_transactions,
    get_transaction_history,
    deposit_money,
    withdraw_money,
    transfer_money,
)
from app.auth import authenticate_admin


class TestAdminManagement(unittest.TestCase):
    """Test suite covering Phase 4 Admin Management features and safety invariants."""

    def setUp(self):
        """Reset in-memory data store and initialize test client before each test."""
        reset_customers_db()
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret-admin"})
        self.client = self.app.test_client()

    def _login_as_admin(self):
        """Helper to establish an authenticated admin session."""
        with self.client.session_transaction() as sess:
            sess["admin_logged_in"] = True
            sess["admin_username"] = SAMPLE_ADMIN["username"]
            sess["admin_name"] = SAMPLE_ADMIN["name"]
            sess["role"] = "admin"

    def _login_as_customer(self, customer_id: int = 1, name: str = "Sarah Jenkins"):
        """Helper to establish an authenticated customer session."""
        with self.client.session_transaction() as sess:
            sess["customer_id"] = customer_id
            sess["customer_name"] = name
            sess["role"] = "customer"

    # =========================================================================
    # 1. Admin Authentication & Role Security Tests
    # =========================================================================

    def test_admin_authentication_success(self):
        """Verifies valid admin credentials authenticate successfully."""
        admin_obj, err = authenticate_admin(SAMPLE_ADMIN["username"], SAMPLE_ADMIN["password"])
        self.assertIsNone(err)
        self.assertIsNotNone(admin_obj)
        self.assertEqual(admin_obj["username"], "admin")

    def test_admin_authentication_invalid_password(self):
        """Verifies incorrect admin password fails authentication."""
        admin_obj, err = authenticate_admin(SAMPLE_ADMIN["username"], "wrong_password_99")
        self.assertIsNone(admin_obj)
        self.assertIn("Invalid administrator credentials", err)

    def test_admin_authentication_invalid_username(self):
        """Verifies unknown admin username fails authentication."""
        admin_obj, err = authenticate_admin("unknown_admin", "AdminSecure#2026")
        self.assertIsNone(admin_obj)
        self.assertIn("Invalid administrator credentials", err)

    def test_unauthenticated_visitor_blocked_from_admin_dashboard(self):
        """Verifies anonymous visitors cannot access admin pages."""
        response = self.client.get("/admin/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.location)

    def test_unauthorized_customer_blocked_from_admin_pages(self):
        """Verifies authenticated customers cannot access admin portal."""
        self._login_as_customer()

        # Customer attempts to view admin dashboard
        response = self.client.get("/admin/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.location)

        # Customer attempts to view admin customer directory
        response = self.client.get("/admin/customers", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.location)

        # Customer attempts to view admin transaction audit
        response = self.client.get("/admin/transactions", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.location)

    # =========================================================================
    # 2. Admin Dashboard Summary Metrics Tests
    # =========================================================================

    def test_admin_dashboard_summary(self):
        """Verifies admin summary metric calculation accuracy."""
        summary = get_admin_dashboard_summary()
        self.assertIn("total_customers", summary)
        self.assertIn("active_accounts", summary)
        self.assertIn("pending_accounts", summary)
        self.assertIn("frozen_accounts", summary)
        self.assertIn("closed_accounts", summary)
        self.assertIn("total_transactions", summary)

        # With default seed data (6 customers: 3 active, 1 inactive, 1 pending, 1 frozen)
        self.assertEqual(summary["total_customers"], 6)
        self.assertEqual(summary["active_accounts"], 3)
        self.assertEqual(summary["pending_accounts"], 1)
        self.assertEqual(summary["frozen_accounts"], 1)
        self.assertEqual(summary["closed_accounts"], 0)
        self.assertGreaterEqual(summary["total_transactions"], 6)

    # =========================================================================
    # 3. Customer Directory & Search Service Tests
    # =========================================================================

    def test_get_all_customers(self):
        """Verifies retrieval of all customer records."""
        customers = get_all_customers()
        self.assertEqual(len(customers), 6)

    def test_search_customers_by_id(self):
        """Verifies search by customer ID."""
        results = search_customers(query="1")
        self.assertTrue(any(c["customer_id"] == 1 for c in results))

    def test_search_customers_by_partial_name(self):
        """Verifies case-insensitive partial name search."""
        results = search_customers(query="jenk")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Sarah Jenkins")

        # Uppercase search
        results_upper = search_customers(query="JENKINS")
        self.assertEqual(len(results_upper), 1)
        self.assertEqual(results_upper[0]["name"], "Sarah Jenkins")

    def test_search_customers_by_email(self):
        """Verifies case-insensitive partial email search."""
        results = search_customers(query="marcus.chen")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["customer_id"], 2)

    def test_search_customers_by_account_number(self):
        """Verifies search by partial account number."""
        target_account = "1006731"  # Elena Rostova's account (ACC-1006731)
        results = search_customers(query=target_account)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Elena Rostova")

    def test_search_customers_status_filter(self):
        """Verifies filtering by account status."""
        pending_list = search_customers(status_filter="Pending")
        self.assertEqual(len(pending_list), 1)
        self.assertEqual(pending_list[0]["name"], "Elena Rostova")

        frozen_list = search_customers(status_filter="Frozen")
        self.assertEqual(len(frozen_list), 1)
        self.assertEqual(frozen_list[0]["name"], "Thomas Sterling")

        active_list = search_customers(status_filter="Active")
        self.assertEqual(len(active_list), 3)

    # =========================================================================
    # 4. Account Approval & Rejection Tests
    # =========================================================================

    def test_approve_pending_account(self):
        """Verifies approving a Pending account transitions it to Active."""
        customer_id = 5  # Elena Rostova (initially Pending)
        customer_before = get_customer_by_id(customer_id)
        self.assertEqual(customer_before["account_status"], "Pending")
        balance_before = customer_before["balance"]

        success, message = approve_customer_account(customer_id)
        self.assertTrue(success)

        customer_after = get_customer_by_id(customer_id)
        self.assertEqual(customer_after["account_status"], "Active")
        self.assertTrue(customer_after["is_active"])
        # DATA INTEGRITY: balance must NOT be altered
        self.assertEqual(customer_after["balance"], balance_before)

    def test_cannot_approve_already_active_account(self):
        """Verifies approving an already active account returns an error message."""
        customer_id = 1  # Sarah Jenkins (Active)
        success, message = approve_customer_account(customer_id)
        self.assertFalse(success)
        self.assertIn("already active", message.lower())

    def test_reject_pending_account(self):
        """Verifies rejecting a Pending account transitions it to Rejected."""
        customer_id = 5  # Elena Rostova
        customer_before = get_customer_by_id(customer_id)
        balance_before = customer_before["balance"]

        success, message = reject_customer_account(customer_id)
        self.assertTrue(success)

        customer_after = get_customer_by_id(customer_id)
        self.assertEqual(customer_after["account_status"], "Rejected")
        self.assertFalse(customer_after["is_active"])
        # DATA INTEGRITY: balance must NOT be altered
        self.assertEqual(customer_after["balance"], balance_before)

    def test_cannot_reject_active_account(self):
        """Verifies only pending accounts can be rejected."""
        customer_id = 1  # Active
        success, message = reject_customer_account(customer_id)
        self.assertFalse(success)
        self.assertIn("only pending accounts", message.lower())

    # =========================================================================
    # 5. Account Freeze & Unfreeze Tests
    # =========================================================================

    def test_freeze_active_account(self):
        """Verifies freezing an active account transitions status and blocks operations."""
        customer_id = 1  # Sarah Jenkins (Active, balance 4850.75)
        customer = get_customer_by_id(customer_id)
        initial_balance = customer["balance"]

        success, message = freeze_customer_account(customer_id)
        self.assertTrue(success)

        # Status check
        customer_after = get_customer_by_id(customer_id)
        self.assertEqual(customer_after["account_status"], "Frozen")
        self.assertFalse(customer_after["is_active"])
        # DATA INTEGRITY: balance must NOT be changed
        self.assertEqual(customer_after["balance"], initial_balance)

    def test_frozen_account_cannot_perform_banking_operations(self):
        """Verifies that a customer with a frozen account cannot deposit, withdraw, or transfer."""
        customer_id = 6  # Thomas Sterling (Frozen in seed data)
        customer = get_customer_by_id(customer_id)
        initial_balance = customer["balance"]

        # 1. Attempt Deposit
        dep_success, dep_msg, dep_bal = deposit_money(customer_id, 100.0)
        self.assertFalse(dep_success)
        self.assertIn("frozen", dep_msg.lower())
        self.assertIsNone(dep_bal)

        # 2. Attempt Withdrawal
        wd_success, wd_msg, wd_bal = withdraw_money(customer_id, 50.0)
        self.assertFalse(wd_success)
        self.assertIn("frozen", wd_msg.lower())
        self.assertIsNone(wd_bal)

        # 3. Attempt Transfer
        tr_success, tr_msg, tr_bal = transfer_money(
            sender_id=customer_id,
            recipient_account="ACC-1002941",
            amount=50.0,
        )
        self.assertFalse(tr_success)
        self.assertIn("frozen", tr_msg.lower())
        self.assertIsNone(tr_bal)

        # Verify balance remains unchanged
        self.assertEqual(get_customer_by_id(customer_id)["balance"], initial_balance)

    def test_unfreeze_account(self):
        """Verifies unfreezing restores an account to Active status."""
        customer_id = 6  # Thomas Sterling (Frozen)
        initial_balance = get_customer_by_id(customer_id)["balance"]

        success, message = unfreeze_customer_account(customer_id)
        self.assertTrue(success)

        customer_after = get_customer_by_id(customer_id)
        self.assertEqual(customer_after["account_status"], "Active")
        self.assertTrue(customer_after["is_active"])
        self.assertEqual(customer_after["balance"], initial_balance)

        # Verify customer can now perform a deposit
        dep_success, dep_msg, new_bal = deposit_money(customer_id, 100.0)
        self.assertTrue(dep_success)
        self.assertEqual(new_bal, round(initial_balance + 100.0, 2))

    # =========================================================================
    # 6. Account Closure Tests
    # =========================================================================

    def test_close_account_preserves_records_and_transactions(self):
        """Verifies closing an account preserves customer profile and historical transactions."""
        customer_id = 1  # Sarah Jenkins
        customer_before = get_customer_by_id(customer_id)
        initial_balance = customer_before["balance"]
        tx_count_before = len(get_transaction_history(customer_id))
        self.assertGreaterEqual(tx_count_before, 1)

        success, message = close_customer_account(customer_id)
        self.assertTrue(success)

        # Customer record must STILL exist
        customer_after = get_customer_by_id(customer_id)
        self.assertIsNotNone(customer_after)
        self.assertEqual(customer_after["account_status"], "Closed")
        self.assertFalse(customer_after["is_active"])
        # Balance must NOT be erased
        self.assertEqual(customer_after["balance"], initial_balance)

        # Historical transactions must NOT be deleted
        tx_count_after = len(get_transaction_history(customer_id))
        self.assertEqual(tx_count_after, tx_count_before)

    def test_cannot_close_already_closed_account(self):
        """Verifies an already closed account cannot be closed again."""
        customer_id = 1
        close_customer_account(customer_id)

        # Second closure attempt
        success, message = close_customer_account(customer_id)
        self.assertFalse(success)
        self.assertIn("already closed", message.lower())

    def test_closed_account_cannot_perform_banking_operations(self):
        """Verifies closed accounts cannot deposit, withdraw, or transfer."""
        customer_id = 1
        close_customer_account(customer_id)

        dep_success, dep_msg, _ = deposit_money(customer_id, 50.0)
        self.assertFalse(dep_success)
        self.assertIn("closed", dep_msg.lower())

        wd_success, wd_msg, _ = withdraw_money(customer_id, 50.0)
        self.assertFalse(wd_success)
        self.assertIn("closed", wd_msg.lower())

    # =========================================================================
    # 7. Transaction Audit & Filtering Tests
    # =========================================================================

    def test_get_all_transactions(self):
        """Verifies admin can retrieve all transactions across all accounts."""
        transactions = get_all_transactions()
        self.assertGreaterEqual(len(transactions), 6)

    def test_filter_transactions_by_type(self):
        """Verifies filtering transactions by Deposit, Withdrawal, Transfer."""
        deposits = get_all_transactions(filter_type="Deposit")
        self.assertTrue(all(t["type"] == "Deposit" for t in deposits))

        withdrawals = get_all_transactions(filter_type="Withdrawal")
        self.assertTrue(all(t["type"] == "Withdrawal" for t in withdrawals))

        transfers = get_all_transactions(filter_type="Transfer")
        self.assertTrue(all(t["type"] == "Transfer" for t in transfers))

    # =========================================================================
    # 8. Web Route Integration Tests (Admin Endpoints)
    # =========================================================================

    def test_admin_web_dashboard(self):
        """Verifies admin can view dashboard."""
        self._login_as_admin()
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"CORE BANKING SYSTEM", response.data)
        self.assertIn(b"Total Customers", response.data)
        self.assertIn(b"Active Accounts", response.data)
        self.assertIn(b"Pending Accounts", response.data)
        self.assertIn(b"Frozen Accounts", response.data)
        self.assertIn(b"Closed Accounts", response.data)
        self.assertIn(b"Total Transactions", response.data)

    def test_admin_web_customers_page(self):
        """Verifies admin can view and search customers page."""
        self._login_as_admin()
        response = self.client.get("/admin/customers")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Customer Management", response.data)
        self.assertIn(b"Sarah Jenkins", response.data)

        # Search query via GET
        search_response = self.client.get("/admin/customers?q=Elena")
        self.assertEqual(search_response.status_code, 200)
        self.assertIn(b"Elena Rostova", search_response.data)

    def test_admin_web_customer_details(self):
        """Verifies admin can view specific customer details."""
        self._login_as_admin()
        response = self.client.get("/admin/customer/1")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Sarah Jenkins", response.data)
        self.assertIn(b"Account Specifications", response.data)

    def test_admin_web_action_freeze_and_unfreeze_posts(self):
        """Verifies POST endpoints for freeze and unfreeze."""
        self._login_as_admin()
        # Freeze Sarah Jenkins
        response = self.client.post("/admin/customer/1/freeze", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_customer_by_id(1)["account_status"], "Frozen")

        # Unfreeze Sarah Jenkins
        response = self.client.post("/admin/customer/1/unfreeze", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_customer_by_id(1)["account_status"], "Active")

    def test_admin_web_action_approve_post(self):
        """Verifies POST endpoint for approving an account."""
        self._login_as_admin()
        response = self.client.post("/admin/customer/5/approve", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_customer_by_id(5)["account_status"], "Active")

    def test_admin_web_accounts_page(self):
        """Verifies admin can view accounts ledger view."""
        self._login_as_admin()
        response = self.client.get("/admin/accounts")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Accounts Ledger Registry", response.data)

    def test_admin_web_transactions_page(self):
        """Verifies admin can view transactions audit ledger with type filter."""
        self._login_as_admin()
        response = self.client.get("/admin/transactions?type=Deposit")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Transaction Management", response.data)

    def test_admin_web_placeholders(self):
        """Verifies placeholder pages for Loans, Cheques, and Reports load cleanly."""
        self._login_as_admin()

        for endpoint, title_snippet in [
            ("/admin/loans", b"Loan Management"),
            ("/admin/cheques", b"Cheque Requests"),
            ("/admin/reports", b"Reports &amp; Analytics"),
        ]:
            resp = self.client.get(endpoint)
            self.assertEqual(resp.status_code, 200)
            self.assertIn(title_snippet, resp.data)


if __name__ == "__main__":
    unittest.main()
