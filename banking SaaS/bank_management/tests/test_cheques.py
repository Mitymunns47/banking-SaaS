"""
tests/test_cheques.py
=============================================================================
Automated Unit and Integration Tests for Phase 6: Cheque Book Request and Management
=============================================================================

TEST COVERAGE:
1. Cheque Request Creation:
   - Successful creation for eligible active accounts (10, 25, 50 leaves).
   - Validation failures on invalid leaf counts, missing accounts, and non-active accounts.
   - Unique sequential request ID generation (CHQ-100X).
   - Initial status set to Pending.

2. Customer Access & Multi-Tenant Isolation:
   - Viewing personal cheque book history with masked account numbers.
   - Prevention of unauthorized access to other customers' requests.
   - Cancellation of customer's own pending request only.
   - Prevention of cancellation of non-pending or other customers' requests.

3. Admin Cheque Book Management:
   - Admin summary metric cards calculation (Total, Pending, Approved, Rejected, Completed).
   - Admin search and status filtering.
   - Admin approval of pending requests (Pending -> Approved).
   - Admin rejection requiring valid descriptive reason (Pending -> Rejected).
   - Admin completion of approved requests (Approved -> Completed).
   - Prevention of invalid status transitions (e.g. Rejected -> Approved, Cancelled -> Completed).
   - Prevention of repeated determinations on already-processed requests.

4. Web Route & Security Integrations:
   - Customer web request submission and list rendering.
   - Customer cancellation via POST.
   - Admin approval, rejection, and completion via POST.
   - Unauthenticated & non-admin role redirection guards.
"""

import unittest
from app import create_app
from app.models import reset_customers_db, CHEQUE_REQUESTS_DB, CUSTOMERS_DB
from app.utils import mask_account_number, validate_cheque_request_input, validate_cheque_rejection_reason
from app.services import (
    request_cheque_book,
    get_customer_cheque_requests,
    get_cheque_request_by_id,
    cancel_cheque_request,
    get_all_cheque_requests,
    get_admin_cheque_summary,
    approve_cheque_request,
    reject_cheque_request,
    complete_cheque_request,
)


class TestChequeManagement(unittest.TestCase):
    """Test suite for Phase 6 Cheque Book Request and Management features."""

    def setUp(self):
        """Set up test Flask client and reset database state before each test."""
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key-phase6"
        self.client = self.app.test_client()
        reset_customers_db()

    def tearDown(self):
        """Clean database state after each test."""
        reset_customers_db()

    def _login_as_customer(self, customer_id: int = 1, name: str = "Sarah Jenkins") -> None:
        """Helper to simulate an authenticated customer session."""
        with self.client.session_transaction() as sess:
            sess["customer_id"] = customer_id
            sess["customer_name"] = name
            sess["customer_email"] = "sarah.jenkins@bankcorp.com"
            sess["role"] = "customer"

    def _login_as_admin(self) -> None:
        """Helper to simulate an authenticated administrator session."""
        with self.client.session_transaction() as sess:
            sess["admin_logged_in"] = True
            sess["admin_username"] = "admin"
            sess["admin_name"] = "Bank Administrator"
            sess["admin_role"] = "admin"
            sess["role"] = "admin"

    # =========================================================================
    # 1. Validation & Masking Helpers
    # =========================================================================

    def test_mask_account_number_formats(self):
        """Verifies account masking protects privacy while revealing the last digits."""
        self.assertEqual(mask_account_number("ACC-1002941"), "ACC-****941")
        self.assertEqual(mask_account_number("ACC-1003882"), "ACC-****882")
        self.assertEqual(mask_account_number("12345678"), "****5678")
        self.assertEqual(mask_account_number(""), "N/A")
        self.assertEqual(mask_account_number(None), "N/A")

    def test_validate_cheque_request_input_valid(self):
        """Verifies valid input passes validation for 10, 25, and 50 leaves."""
        accounts = [{"account_number": "ACC-1002941", "account_status": "Active", "is_active": True}]

        for leaves in [10, 25, 50]:
            is_valid, errors, sanitized = validate_cheque_request_input("ACC-1002941", leaves, accounts)
            self.assertTrue(is_valid)
            self.assertEqual(len(errors), 0)
            self.assertEqual(sanitized["leaves"], leaves)
            self.assertEqual(sanitized["account_number"], "ACC-1002941")

    def test_validate_cheque_request_input_invalid_leaves(self):
        """Rejects invalid leaves such as 0, 15, 100, or negative numbers."""
        accounts = [{"account_number": "ACC-1002941", "account_status": "Active", "is_active": True}]

        for bad_leaves in [0, 15, 30, 100, -10, "invalid"]:
            is_valid, errors, _ = validate_cheque_request_input("ACC-1002941", bad_leaves, accounts)
            self.assertFalse(is_valid)
            self.assertTrue(any("leaves must be 10, 25, or 50" in e.lower() for e in errors))

    def test_validate_cheque_request_input_ineligible_account(self):
        """Rejects accounts that do not belong to customer or are not Active (Frozen, Pending, Closed)."""
        # Account not in list
        is_valid, errors, _ = validate_cheque_request_input("ACC-9999999", 25, [])
        self.assertFalse(is_valid)
        self.assertTrue(any("does not belong" in e for e in errors))

        # Account is Frozen
        frozen_accounts = [{"account_number": "ACC-1007892", "account_status": "Frozen", "is_active": False}]
        is_valid, errors, _ = validate_cheque_request_input("ACC-1007892", 25, frozen_accounts)
        self.assertFalse(is_valid)
        self.assertTrue(any("Frozen" in e or "not eligible" in e for e in errors))

    def test_validate_cheque_rejection_reason(self):
        """Verifies rejection reasons must be non-empty and descriptive."""
        is_valid, err = validate_cheque_rejection_reason("Account signature card expired.")
        self.assertTrue(is_valid)
        self.assertEqual(err, "")

        is_valid, err = validate_cheque_rejection_reason("")
        self.assertFalse(is_valid)
        self.assertIn("required", err.lower())

        is_valid, err = validate_cheque_rejection_reason("no")
        self.assertFalse(is_valid)
        self.assertIn("minimum 3 characters", err.lower())

    # =========================================================================
    # 2. Cheque Request Creation & Customer Operations
    # =========================================================================

    def test_request_cheque_book_success(self):
        """Customer successfully submits a cheque book request."""
        success, msg, new_req = request_cheque_book(
            customer_id=1,
            account_number="ACC-1002941",
            leaves=25,
            delivery_notes="Deliver to central office.",
        )
        self.assertTrue(success)
        self.assertIn("submitted successfully", msg)
        self.assertIsNotNone(new_req)
        self.assertEqual(new_req["status"], "Pending")
        self.assertEqual(new_req["leaves"], 25)
        self.assertEqual(new_req["customer_id"], 1)
        self.assertTrue(new_req["cheque_request_id"].startswith("CHQ-"))
        self.assertEqual(new_req["admin_notes"], "Deliver to central office.")

    def test_request_cheque_book_unique_id_generation(self):
        """Ensures successive requests generate strictly unique sequential reference codes."""
        _, _, req1 = request_cheque_book(1, "ACC-1002941", 10)
        _, _, req2 = request_cheque_book(1, "ACC-1002941", 50)
        self.assertNotEqual(req1["cheque_request_id"], req2["cheque_request_id"])
        self.assertGreater(req2["request_id"], req1["request_id"])

    def test_get_customer_cheque_requests(self):
        """Verifies customer only retrieves their own requests, sorted newest first."""
        sarah_requests = get_customer_cheque_requests(1)
        # Sarah Jenkins has seed requests #1 and #4
        self.assertTrue(len(sarah_requests) >= 2)
        for req in sarah_requests:
            self.assertEqual(req["customer_id"], 1)
            self.assertIn("masked_account_number", req)
            self.assertTrue(req["masked_account_number"].startswith("ACC-****"))

    def test_customer_cancel_own_pending_request(self):
        """Customer cancels their own Pending request; status changes to Cancelled."""
        # Request 4 belongs to Sarah (customer 1) and is Pending in seed data
        success, msg = cancel_cheque_request(request_id=4, customer_id=1)
        self.assertTrue(success)
        self.assertIn("cancelled", msg.lower())

        req = get_cheque_request_by_id(4)
        self.assertEqual(req["status"], "Cancelled")

    def test_customer_cannot_cancel_other_customer_request(self):
        """Security: Customer 1 cannot cancel Request 3 (belongs to Customer 4 David Miller)."""
        success, msg = cancel_cheque_request(request_id=3, customer_id=1)
        self.assertFalse(success)
        self.assertIn("access denied", msg.lower())

        # Status must remain unchanged
        req = get_cheque_request_by_id(3)
        self.assertEqual(req["status"], "Pending")

    def test_customer_cannot_cancel_non_pending_request(self):
        """Customer cannot cancel request that is already Approved or Completed."""
        # Request 1 is Completed in seed data
        success, msg = cancel_cheque_request(request_id=1, customer_id=1)
        self.assertFalse(success)
        self.assertIn("only pending requests can be cancelled", msg.lower())

        req = get_cheque_request_by_id(1)
        self.assertEqual(req["status"], "Completed")

    # =========================================================================
    # 3. Admin Underwriting & Status Workflow Operations
    # =========================================================================

    def test_admin_cheque_summary_calculation(self):
        """Verifies summary metrics dictionary correctly aggregates statuses."""
        summary = get_admin_cheque_summary()
        self.assertIn("total_requests", summary)
        self.assertIn("pending_requests", summary)
        self.assertIn("approved_requests", summary)
        self.assertIn("rejected_requests", summary)
        self.assertIn("completed_requests", summary)
        self.assertIn("cancelled_requests", summary)
        self.assertEqual(summary["total_requests"], len(CHEQUE_REQUESTS_DB))
        self.assertEqual(summary["pending_requests"], 2)  # Seed requests #3 and #4

    def test_admin_approve_pending_cheque_request(self):
        """Admin approves a Pending request; status transitions to Approved."""
        # Request 3 is Pending
        success, msg = approve_cheque_request(request_id=3, admin_notes="Batch #50 ready.")
        self.assertTrue(success)
        self.assertIn("approved", msg.lower())

        req = get_cheque_request_by_id(3)
        self.assertEqual(req["status"], "Approved")
        self.assertIsNotNone(req["admin_decision_date"])
        self.assertEqual(req["admin_notes"], "Batch #50 ready.")

    def test_admin_reject_pending_cheque_request(self):
        """Admin rejects a Pending request; requires a valid rejection reason."""
        # Request 4 is Pending
        success, msg = reject_cheque_request(request_id=4, rejection_reason="Account dormant; please visit branch.")
        self.assertTrue(success)
        self.assertIn("rejected", msg.lower())

        req = get_cheque_request_by_id(4)
        self.assertEqual(req["status"], "Rejected")
        self.assertEqual(req["rejection_reason"], "Account dormant; please visit branch.")

    def test_admin_reject_pending_cheque_request_requires_reason(self):
        """Rejects rejection attempts with blank or missing reason."""
        success, msg = reject_cheque_request(request_id=4, rejection_reason="")
        self.assertFalse(success)
        self.assertIn("required", msg.lower())

        # Status must remain Pending
        req = get_cheque_request_by_id(4)
        self.assertEqual(req["status"], "Pending")

    def test_admin_complete_approved_cheque_request(self):
        """Admin marks an Approved request as Completed (dispatched)."""
        # Request 2 is Approved in seed data
        success, msg = complete_cheque_request(request_id=2, admin_notes="Dispatched via express post.")
        self.assertTrue(success)
        self.assertIn("completed", msg.lower())

        req = get_cheque_request_by_id(2)
        self.assertEqual(req["status"], "Completed")

    def test_prevent_invalid_status_transitions(self):
        """Guards against invalid transitions: Rejected -> Approved, Cancelled -> Completed, etc."""
        # Request 5 is Rejected -> Cannot approve
        success, msg = approve_cheque_request(request_id=5)
        self.assertFalse(success)
        self.assertIn("cannot approve", msg.lower())

        # Request 6 is Cancelled -> Cannot complete
        success, msg = complete_cheque_request(request_id=6)
        self.assertFalse(success)
        self.assertIn("cannot complete", msg.lower())

        # Request 3 is Pending -> Cannot complete directly without approval
        success, msg = complete_cheque_request(request_id=3)
        self.assertFalse(success)
        self.assertIn("only approved requests can be marked as completed", msg.lower())

    def test_prevent_repeated_determinations(self):
        """Prevents repeated approvals or repeated rejections on already-decided records."""
        # Request 2 is Approved -> Cannot approve again
        success, msg = approve_cheque_request(request_id=2)
        self.assertFalse(success)
        self.assertIn("cannot approve", msg.lower())

        # Request 5 is Rejected -> Cannot reject again
        success, msg = reject_cheque_request(request_id=5, rejection_reason="Second reject attempt")
        self.assertFalse(success)
        self.assertIn("cannot reject", msg.lower())

    def test_admin_search_and_filter(self):
        """Verifies filtering by status and searching across query criteria."""
        # Filter by Pending
        pending_list = get_all_cheque_requests(status_filter="Pending")
        self.assertEqual(len(pending_list), 2)
        for req in pending_list:
            self.assertEqual(req["status"], "Pending")

        # Search by customer name "Marcus"
        marcus_results = get_all_cheque_requests(search_query="Marcus")
        self.assertTrue(len(marcus_results) >= 2)
        for req in marcus_results:
            self.assertIn("Marcus", req["customer_name"])

        # Search by Request code "CHQ-1001"
        code_results = get_all_cheque_requests(search_query="CHQ-1001")
        self.assertEqual(len(code_results), 1)
        self.assertEqual(code_results[0]["cheque_request_id"], "CHQ-1001")

    # =========================================================================
    # 4. Web Routes & RBAC Integration Tests
    # =========================================================================

    def test_web_routes_customer_cheque_request_flow(self):
        """Customer logs in, views cheque book page, submits a request, and cancels it."""
        self._login_as_customer(customer_id=1, name="Sarah Jenkins")

        # View customer cheques page
        resp = self.client.get("/cheques")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Cheque Book Services", resp.data)
        self.assertIn(b"CORE BANKING SYSTEM", resp.data)

        # View request form
        form_resp = self.client.get("/cheques/request")
        self.assertEqual(form_resp.status_code, 200)
        self.assertIn(b"Request Cheque Book", form_resp.data)

        # Submit request via POST
        post_data = {
            "account_number": "ACC-1002941",
            "leaves": "50",
            "delivery_notes": "Urgent branch pickup",
        }
        submit_resp = self.client.post("/cheques/request", data=post_data, follow_redirects=True)
        self.assertEqual(submit_resp.status_code, 200)
        self.assertIn(b"submitted successfully", submit_resp.data)
        self.assertIn(b"50 Leaves", submit_resp.data)

        # Cancel the newly created request (id 7)
        cancel_resp = self.client.post("/cheque/7/cancel", follow_redirects=True)
        self.assertEqual(cancel_resp.status_code, 200)
        self.assertIn(b"has been cancelled", cancel_resp.data)

    def test_web_routes_admin_cheque_management_flow(self):
        """Admin logs in, reviews cheque console, approves, and completes a request."""
        self._login_as_admin()

        # View admin cheques page
        resp = self.client.get("/admin/cheques")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Cheque Requests", resp.data)
        self.assertIn(b"Pending Review", resp.data)

        # Admin approves Pending request 3
        approve_resp = self.client.post(
            "/admin/cheque/3/approve",
            data={"admin_notes": "Batch authorized."},
            follow_redirects=True,
        )
        self.assertEqual(approve_resp.status_code, 200)
        self.assertIn(b"has been approved", approve_resp.data)

        # Admin completes Approved request 3
        complete_resp = self.client.post(
            "/admin/cheque/3/complete",
            data={"admin_notes": "Handed over at teller counter."},
            follow_redirects=True,
        )
        self.assertEqual(complete_resp.status_code, 200)
        self.assertIn(b"marked as Completed", complete_resp.data)

    def test_web_routes_admin_reject_cheque_flow(self):
        """Admin rejects a Pending request with reason."""
        self._login_as_admin()

        reject_resp = self.client.post(
            "/admin/cheque/4/reject",
            data={"rejection_reason": "Account balance insufficient for fee requirements."},
            follow_redirects=True,
        )
        self.assertEqual(reject_resp.status_code, 200)
        self.assertIn(b"has been rejected", reject_resp.data)

    def test_security_unauthorized_access_protection(self):
        """Verifies unauthenticated users and customers cannot perform admin actions."""
        # Unauthenticated customer accessing customer cheques
        resp = self.client.get("/cheques")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.location)

        # Customer attempting admin route
        self._login_as_customer(customer_id=1)
        admin_resp = self.client.get("/admin/cheques")
        self.assertEqual(admin_resp.status_code, 302)
        self.assertIn("/admin/login", admin_resp.location)

        # Customer attempting admin POST
        admin_post = self.client.post("/admin/cheque/3/approve")
        self.assertEqual(admin_post.status_code, 302)
        self.assertIn("/admin/login", admin_post.location)


if __name__ == "__main__":
    unittest.main()
