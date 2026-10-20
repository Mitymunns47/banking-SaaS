"""
tests/test_loans.py
=============================================================================
Automated Unit and Integration Tests for Loan Management System
=============================================================================

PYTHON FUNDAMENTALS DEMONSTRATED IN THIS FILE:
1. Automated Testing with Python's standard `unittest` framework.
2. State isolation: resetting data models prior to each test run.
3. Accurate financial mathematics: verifying reducing-balance EMI calculations
   and zero-interest edge cases using Decimal.
4. Access control, role authorization, and multi-tenant security verification.
5. Invariant checking: preventing repeated administrative determinations and
   ensuring approved credit limits never exceed requested principal.
"""

import sys
import os
import unittest
from decimal import Decimal

# Ensure app package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.models import reset_customers_db, LOANS_DB, CUSTOMERS_DB, SAMPLE_ADMIN
from app.services import (
    calculate_loan_repayment_details,
    apply_for_loan,
    get_customer_loans,
    get_loan_by_id,
    cancel_loan_application,
    get_all_loans,
    get_admin_loan_summary,
    approve_loan_application,
    reject_loan_application,
    activate_loan,
    freeze_customer_account,
)


class TestLoanManagement(unittest.TestCase):
    """Test suite covering Phase 5 Loan Management features, EMI calculations, and security."""

    def setUp(self):
        """Reset in-memory data store and initialize test client before each test."""
        reset_customers_db()
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret-loans"})
        self.client = self.app.test_client()

    def _login_as_customer(self, customer_id: int = 1, name: str = "Sarah Jenkins"):
        """Helper to establish an authenticated customer session."""
        with self.client.session_transaction() as sess:
            sess["customer_id"] = customer_id
            sess["customer_name"] = name
            sess["role"] = "customer"

    def _login_as_admin(self):
        """Helper to establish an authenticated admin session."""
        with self.client.session_transaction() as sess:
            sess["admin_logged_in"] = True
            sess["admin_username"] = SAMPLE_ADMIN["username"]
            sess["admin_name"] = SAMPLE_ADMIN["name"]
            sess["role"] = "admin"

    # =========================================================================
    # 1. EMI & Repayment Calculation Unit Tests
    # =========================================================================

    def test_emi_calculation_standard_reducing_balance(self):
        """Verifies reducing-balance EMI calculation for standard interest loan."""
        # Principal: $10,000, 12% annual rate, 12 months tenure
        # Monthly rate r = 12 / (12 * 100) = 0.01
        # EMI = 10000 * 0.01 * (1.01)^12 / ((1.01)^12 - 1) = 888.49
        details = calculate_loan_repayment_details(
            principal=10000.0,
            annual_interest_rate=12.0,
            tenure_months=12,
        )
        self.assertEqual(details["emi"], 888.49)
        self.assertEqual(details["total_repayment"], 10661.88)
        self.assertEqual(details["total_interest"], 661.88)

    def test_emi_calculation_zero_interest_edge_case(self):
        """Verifies zero-interest loan calculation avoids division-by-zero errors."""
        # Principal: $12,000, 0% annual rate, 12 months tenure
        # EMI = 12000 / 12 = 1000.00, Interest = 0.00
        details = calculate_loan_repayment_details(
            principal=12000.0,
            annual_interest_rate=0.0,
            tenure_months=12,
        )
        self.assertEqual(details["emi"], 1000.00)
        self.assertEqual(details["total_repayment"], 12000.00)
        self.assertEqual(details["total_interest"], 0.00)

    def test_emi_calculation_invalid_or_zero_principal(self):
        """Verifies safe fallback when principal or tenure is non-positive."""
        details = calculate_loan_repayment_details(
            principal=0.0,
            annual_interest_rate=10.0,
            tenure_months=12,
        )
        self.assertEqual(details["emi"], 0.0)
        self.assertEqual(details["total_repayment"], 0.0)

    # =========================================================================
    # 2. Customer Loan Application Submission Tests
    # =========================================================================

    def test_successful_loan_application_submission(self):
        """Verifies customer can submit a valid loan application with initial Pending status."""
        customer_id = 1  # Sarah Jenkins
        success, message, loan = apply_for_loan(
            customer_id=customer_id,
            loan_type="Personal",
            requested_amount=15000.00,
            tenure_months=24,
            purpose="Vehicle purchase and insurance",
            monthly_income=5000.00,
        )
        self.assertTrue(success)
        self.assertIsNotNone(loan)
        self.assertEqual(loan["status"], "Pending")
        self.assertEqual(loan["requested_amount"], 15000.00)
        self.assertEqual(loan["tenure_months"], 24)
        self.assertTrue(loan["application_id"].startswith("LN-"))
        self.assertIsNone(loan["approved_amount"])
        self.assertIsNone(loan["estimated_emi"])

    def test_loan_application_validation_negative_amount(self):
        """Verifies loan application rejects negative or zero requested amount."""
        success, message, loan = apply_for_loan(
            customer_id=1,
            loan_type="Personal",
            requested_amount=-500.0,
            tenure_months=12,
            purpose="Debt consolidation",
            monthly_income=4000.0,
        )
        self.assertFalse(success)
        self.assertIn("greater than $0.00", message)
        self.assertIsNone(loan)

    def test_loan_application_validation_invalid_tenure(self):
        """Verifies loan application rejects invalid tenure (0 or > 360 months)."""
        success, message, loan = apply_for_loan(
            customer_id=1,
            loan_type="Personal",
            requested_amount=5000.0,
            tenure_months=0,
            purpose="Debt consolidation",
            monthly_income=4000.0,
        )
        self.assertFalse(success)
        self.assertIn("at least 1 month", message)

        success_high, msg_high, _ = apply_for_loan(
            customer_id=1,
            loan_type="Personal",
            requested_amount=5000.0,
            tenure_months=400,
            purpose="Debt consolidation",
            monthly_income=4000.0,
        )
        self.assertFalse(success_high)
        self.assertIn("cannot exceed 360 months", msg_high)

    def test_loan_application_validation_invalid_income(self):
        """Verifies loan application rejects non-positive monthly income."""
        success, message, loan = apply_for_loan(
            customer_id=1,
            loan_type="Home",
            requested_amount=50000.0,
            tenure_months=120,
            purpose="Property purchase",
            monthly_income=0.0,
        )
        self.assertFalse(success)
        self.assertIn("Monthly income must be strictly greater than $0.00", message)

    def test_loan_application_validation_invalid_type(self):
        """Verifies loan application rejects unknown loan types."""
        success, message, loan = apply_for_loan(
            customer_id=1,
            loan_type="Cryptocurrency",
            requested_amount=5000.0,
            tenure_months=12,
            purpose="Speculative trading",
            monthly_income=4000.0,
        )
        self.assertFalse(success)
        self.assertIn("Loan type must be one of", message)

    def test_frozen_customer_account_cannot_apply_for_loan(self):
        """Verifies customers with frozen accounts cannot apply for loans."""
        customer_id = 6  # Thomas Sterling (Frozen in seed data)
        success, message, loan = apply_for_loan(
            customer_id=customer_id,
            loan_type="Business",
            requested_amount=10000.0,
            tenure_months=24,
            purpose="Inventory financing",
            monthly_income=8000.0,
        )
        self.assertFalse(success)
        self.assertIn("restricted", message.lower())

    # =========================================================================
    # 3. Customer Privacy, Retrieval & Cancellation Tests
    # =========================================================================

    def test_customer_view_own_loan_history(self):
        """Verifies customer can view their own loans in chronological order."""
        sarah_loans = get_customer_loans(customer_id=1)
        self.assertGreaterEqual(len(sarah_loans), 2)
        self.assertTrue(all(l["customer_id"] == 1 for l in sarah_loans))

    def test_customer_cannot_cancel_other_customer_loan(self):
        """Verifies a customer cannot cancel another customer's loan application."""
        # Loan 3 belongs to customer 4 (David Miller)
        loan_3 = get_loan_by_id(3)
        self.assertEqual(loan_3["customer_id"], 4)

        # Customer 1 attempts to cancel David's loan
        success, message = cancel_loan_application(loan_id=3, customer_id=1)
        self.assertFalse(success)
        self.assertIn("Unauthorized access", message)
        self.assertEqual(loan_3["status"], "Pending")

    def test_customer_cancel_own_pending_loan(self):
        """Verifies customer can cancel their own pending loan application."""
        # Loan 4 belongs to customer 1 (Sarah Jenkins) and is Pending
        loan_4 = get_loan_by_id(4)
        self.assertEqual(loan_4["customer_id"], 1)
        self.assertEqual(loan_4["status"], "Pending")

        success, message = cancel_loan_application(loan_id=4, customer_id=1)
        self.assertTrue(success)
        self.assertEqual(loan_4["status"], "Cancelled")

    def test_customer_cannot_cancel_non_pending_loan(self):
        """Verifies customer cannot cancel an already approved loan."""
        # Loan 1 is Approved for customer 1
        loan_1 = get_loan_by_id(1)
        self.assertEqual(loan_1["status"], "Approved")

        success, message = cancel_loan_application(loan_id=1, customer_id=1)
        self.assertFalse(success)
        self.assertIn("Only pending applications can be cancelled", message)

    # =========================================================================
    # 4. Admin Loan Underwriting & Approval Tests
    # =========================================================================

    def test_admin_loan_summary_metrics(self):
        """Verifies admin loan summary card metrics calculate accurately."""
        summary = get_admin_loan_summary()
        self.assertIn("total_applications", summary)
        self.assertIn("pending_applications", summary)
        self.assertIn("approved_loans", summary)
        self.assertIn("rejected_applications", summary)
        self.assertIn("active_loans", summary)

        # Default seed loans (5 total: 1 approved, 1 active, 2 pending, 1 rejected)
        self.assertEqual(summary["total_applications"], 5)
        self.assertEqual(summary["approved_loans"], 1)
        self.assertEqual(summary["active_loans"], 1)
        self.assertEqual(summary["pending_applications"], 2)
        self.assertEqual(summary["rejected_applications"], 1)

    def test_admin_search_and_filter_loans(self):
        """Verifies admin multi-criteria search and filter."""
        # Search by Application ID
        search_results = get_all_loans(search_query="LN-1002")
        self.assertEqual(len(search_results), 1)
        self.assertEqual(search_results[0]["customer_name"], "Marcus Aurelius Chen")

        # Filter by status
        pending_loans = get_all_loans(status_filter="Pending")
        self.assertEqual(len(pending_loans), 2)

        # Filter by type
        home_loans = get_all_loans(type_filter="Home")
        self.assertEqual(len(home_loans), 1)
        self.assertEqual(home_loans[0]["customer_name"], "David Miller")

    def test_admin_approve_loan_success(self):
        """Verifies admin can approve a pending loan, setting terms and calculating EMI."""
        # Loan 3 is Pending (David Miller, requested 50,000, 120 mos)
        loan_3 = get_loan_by_id(3)
        self.assertEqual(loan_3["status"], "Pending")

        success, message = approve_loan_application(
            loan_id=3,
            approved_amount=45000.00,
            annual_interest_rate=7.5,
            tenure_months=120,
            admin_notes="Approved with adjusted principal limit.",
        )
        self.assertTrue(success)
        self.assertEqual(loan_3["status"], "Approved")
        self.assertEqual(loan_3["approved_amount"], 45000.00)
        self.assertEqual(loan_3["annual_interest_rate"], 7.5)
        self.assertEqual(loan_3["approved_tenure_months"], 120)
        self.assertIsNotNone(loan_3["estimated_emi"])
        self.assertGreater(loan_3["estimated_emi"], 0)
        self.assertIsNotNone(loan_3["admin_decision_date"])

    def test_admin_approve_amount_cannot_exceed_requested(self):
        """Verifies approved amount cannot exceed the customer-requested amount."""
        loan_3 = get_loan_by_id(3)  # requested 50,000
        success, message = approve_loan_application(
            loan_id=3,
            approved_amount=60000.00,
            annual_interest_rate=8.0,
            tenure_months=120,
        )
        self.assertFalse(success)
        self.assertIn("cannot exceed requested amount", message)
        self.assertEqual(loan_3["status"], "Pending")

    def test_admin_approve_prevents_repeated_decision(self):
        """Verifies an already approved or rejected loan cannot be re-approved."""
        loan_1 = get_loan_by_id(1)  # already Approved
        success, message = approve_loan_application(
            loan_id=1,
            approved_amount=5000.0,
            annual_interest_rate=8.5,
            tenure_months=24,
        )
        self.assertFalse(success)
        self.assertIn("Only pending applications can be processed", message)

    def test_admin_reject_loan_success(self):
        """Verifies admin can reject a pending loan with recorded reason."""
        # Loan 4 is Pending (Sarah Jenkins)
        loan_4 = get_loan_by_id(4)
        self.assertEqual(loan_4["status"], "Pending")

        success, message = reject_loan_application(
            loan_id=4,
            rejection_reason="Debt-to-income ratio exceeds threshold for secondary facility.",
        )
        self.assertTrue(success)
        self.assertEqual(loan_4["status"], "Rejected")
        self.assertEqual(
            loan_4["rejection_reason"],
            "Debt-to-income ratio exceeds threshold for secondary facility.",
        )
        self.assertIsNotNone(loan_4["admin_decision_date"])

    def test_admin_reject_requires_reason(self):
        """Verifies rejection requires a non-empty reason."""
        success, message = reject_loan_application(loan_id=4, rejection_reason="")
        self.assertFalse(success)
        self.assertIn("minimum 3 characters", message)

    def test_admin_activate_loan(self):
        """Verifies promoting an Approved loan to Active status."""
        # Loan 1 is Approved
        loan_1 = get_loan_by_id(1)
        self.assertEqual(loan_1["status"], "Approved")

        success, message = activate_loan(loan_id=1)
        self.assertTrue(success)
        self.assertEqual(loan_1["status"], "Active")

    # =========================================================================
    # 5. Security & Route Protection Tests
    # =========================================================================

    def test_unauthenticated_user_cannot_access_loans(self):
        """Verifies unauthenticated visitors are redirected to login."""
        response = self.client.get("/loans", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

        admin_resp = self.client.get("/admin/loans", follow_redirects=False)
        self.assertEqual(admin_resp.status_code, 302)
        self.assertIn("/admin/login", admin_resp.location)

    def test_customer_cannot_access_admin_loans(self):
        """Verifies authenticated customers cannot access admin loan portals or actions."""
        self._login_as_customer()

        # Customer attempts admin loans list
        resp = self.client.get("/admin/loans", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/login", resp.location)

        # Customer attempts admin approve POST
        post_resp = self.client.post("/admin/loan/3/approve", follow_redirects=False)
        self.assertEqual(post_resp.status_code, 302)
        self.assertIn("/admin/login", post_resp.location)

    def test_web_routes_customer_loan_apply_and_view(self):
        """Integration test: Customer applies for loan via web form and inspects details."""
        self._login_as_customer(customer_id=1, name="Sarah Jenkins")

        # Submit new loan application via POST
        post_data = {
            "loan_type": "Education",
            "requested_amount": "8000.00",
            "tenure_months": "24",
            "purpose": "Data engineering advanced certification",
            "monthly_income": "4500.00",
        }
        resp = self.client.post("/loans/apply", data=post_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"submitted successfully", resp.data)
        self.assertIn(b"Education Loan Facility", resp.data)

        # View customer loans directory
        list_resp = self.client.get("/loans")
        self.assertEqual(list_resp.status_code, 200)
        self.assertIn(b"Personal Loan Portfolio", list_resp.data)
        self.assertIn(b"Education", list_resp.data)

    def test_web_routes_admin_underwriting_approval(self):
        """Integration test: Admin views loan details and approves via POST."""
        self._login_as_admin()

        # View admin loans page
        resp = self.client.get("/admin/loans")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Loan Underwriting", resp.data)

        # Approve loan 3 via POST
        approve_data = {
            "approved_amount": "50000.00",
            "annual_interest_rate": "8.25",
            "approved_tenure_months": "120",
            "admin_notes": "Verified property appraisal.",
        }
        post_resp = self.client.post("/admin/loan/3/approve", data=approve_data, follow_redirects=True)
        self.assertEqual(post_resp.status_code, 200)
        self.assertIn(b"successfully approved", post_resp.data)

        # Verify loan 3 details reflect approval
        loan_3 = get_loan_by_id(3)
        self.assertEqual(loan_3["status"], "Approved")
        self.assertIsNotNone(loan_3["estimated_emi"])


if __name__ == "__main__":
    unittest.main()
