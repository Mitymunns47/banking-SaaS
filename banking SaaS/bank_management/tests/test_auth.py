"""
tests/test_auth.py
=============================================================================
Automated Authentication and Authorization Tests for Bank Management (Phase 2)
=============================================================================

PYTHON FUNDAMENTALS DEMONSTRATED IN THIS FILE:
1. Automated Testing with Python's standard `unittest` library.
2. Simulating HTTP POST/GET requests and tracking Flask sessions.
3. Asserting role-based security redirects (unauthorized access protection).
4. Testing in-memory rate limiting and account lockout after repeated failed attempts.
"""

import sys
import os
import unittest

# Ensure app package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.models import reset_customers_db, CUSTOMERS_DB, SAMPLE_ADMIN, LOGIN_ATTEMPTS
from app.auth import (
    register_customer,
    authenticate_customer,
    authenticate_admin,
    change_customer_password,
    clear_failed_logins,
    record_failed_login,
)
from app.services import get_customer_by_id


class TestBankAuthPhase2(unittest.TestCase):
    """Test suite covering Phase 2 authentication and authorization features."""

    def setUp(self):
        """Reset in-memory data store and initialize test client before each test."""
        reset_customers_db()
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret-phase2"})
        self.client = self.app.test_client()

    # =========================================================================
    # 1. Customer Registration Tests
    # =========================================================================

    def test_successful_customer_registration(self):
        """Verifies customer registration assigns unique ID, account number, Pending status, and balance 0."""
        customer, errors = register_customer(
            name="Alexander Pope",
            age=28,
            email="alexander.pope@example.com",
            phone="+1 (555) 999-0001",
            password="SecurePassword123",
            confirm_password="SecurePassword123",
            account_type="Savings",
        )
        self.assertEqual(len(errors), 0)
        self.assertIsNotNone(customer)
        self.assertEqual(customer["name"], "Alexander Pope")
        self.assertEqual(customer["email"], "alexander.pope@example.com")
        self.assertEqual(customer["balance"], 0.0)
        self.assertEqual(customer["account_status"], "Pending")
        self.assertFalse(customer["is_active"])
        self.assertTrue(customer["account_number"].startswith("ACC-"))

        # Verify added to database
        found = get_customer_by_id(customer["customer_id"])
        self.assertIsNotNone(found)
        self.assertEqual(found["email"], "alexander.pope@example.com")

    def test_registration_duplicate_email_rejected(self):
        """Verifies that attempting to register with an already existing email is rejected."""
        # 'sarah.jenkins@bankcorp.com' already exists in seed data
        customer, errors = register_customer(
            name="Sarah Duplicate",
            age=30,
            email="sarah.jenkins@bankcorp.com",
            phone="+1 (555) 123-4567",
            password="NewPassword123",
            confirm_password="NewPassword123",
        )
        self.assertIsNone(customer)
        self.assertTrue(any("already registered" in err for err in errors))

    def test_registration_password_mismatch_rejected(self):
        """Verifies that mismatched password and confirm_password yields an error."""
        customer, errors = register_customer(
            name="Mismatch User",
            age=25,
            email="mismatch@example.com",
            phone="+1 (555) 333-4444",
            password="PasswordAAA",
            confirm_password="PasswordBBB",
        )
        self.assertIsNone(customer)
        self.assertTrue(any("do not match" in err for err in errors))

    def test_registration_underage_rejected(self):
        """Verifies customers under 18 cannot register."""
        customer, errors = register_customer(
            name="Underage User",
            age=17,
            email="minor@example.com",
            phone="+1 (555) 555-5555",
            password="ValidPassword123",
            confirm_password="ValidPassword123",
        )
        self.assertIsNone(customer)
        self.assertTrue(any("18 years old" in err for err in errors))

    # =========================================================================
    # 2. Customer Login Tests
    # =========================================================================

    def test_successful_customer_login(self):
        """Verifies successful customer authentication with valid credentials."""
        # Sarah Jenkins has password 'Password123'
        customer, error = authenticate_customer("sarah.jenkins@bankcorp.com", "Password123")
        self.assertIsNotNone(customer)
        self.assertIsNone(error)
        self.assertEqual(customer["name"], "Sarah Jenkins")

    def test_failed_customer_login_gives_generic_error(self):
        """Verifies that incorrect credentials give a generic error message."""
        # Wrong password
        cust1, err1 = authenticate_customer("sarah.jenkins@bankcorp.com", "WrongPassword")
        self.assertIsNone(cust1)
        self.assertEqual(err1, "Invalid email or password.")

        # Non-existent email
        cust2, err2 = authenticate_customer("unknown@example.com", "Password123")
        self.assertIsNone(cust2)
        self.assertEqual(err2, "Invalid email or password.")

    def test_customer_login_route_creates_session(self):
        """Tests that submitting POST to /login creates session and redirects to /dashboard."""
        response = self.client.post(
            "/login",
            data={"email": "sarah.jenkins@bankcorp.com", "password": "Password123"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard", response.headers["Location"])

        # Check session using test client context
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("customer_id"), 1)
            self.assertEqual(sess.get("role"), "customer")

    def test_customer_logout_clears_session(self):
        """Tests customer logout route removes session keys and redirects to login."""
        # Log in first
        self.client.post(
            "/login",
            data={"email": "sarah.jenkins@bankcorp.com", "password": "Password123"},
        )
        # Log out
        response = self.client.get("/logout", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("customer_id"))
            self.assertIsNone(sess.get("role"))

    # =========================================================================
    # 3. Admin Login & Logout Tests
    # =========================================================================

    def test_admin_login_success(self):
        """Tests admin login with sample credentials creates admin session."""
        admin_obj, err = authenticate_admin(SAMPLE_ADMIN["username"], SAMPLE_ADMIN["password"])
        self.assertIsNotNone(admin_obj)
        self.assertIsNone(err)
        self.assertEqual(admin_obj["role"], "admin")

        # Test HTTP route
        response = self.client.post(
            "/admin/login",
            data={"username_or_email": SAMPLE_ADMIN["username"], "password": SAMPLE_ADMIN["password"]},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/dashboard", response.headers["Location"])

        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get("admin_logged_in"))
            self.assertEqual(sess.get("role"), "admin")

    def test_admin_logout_clears_session(self):
        """Tests admin logout clears admin session."""
        self.client.post(
            "/admin/login",
            data={"username_or_email": SAMPLE_ADMIN["username"], "password": SAMPLE_ADMIN["password"]},
        )
        response = self.client.get("/admin/logout", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.headers["Location"])

        with self.client.session_transaction() as sess:
            self.assertFalse(sess.get("admin_logged_in", False))

    # =========================================================================
    # 4. Role-Based Access Control Tests
    # =========================================================================

    def test_unauthorized_access_to_customer_dashboard_redirects_to_login(self):
        """Verifies that an unauthenticated visitor cannot access /dashboard."""
        response = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_customer_cannot_access_admin_dashboard(self):
        """Verifies that a customer cannot access /admin/dashboard."""
        # Log in as customer
        self.client.post(
            "/login",
            data={"email": "sarah.jenkins@bankcorp.com", "password": "Password123"},
        )
        response = self.client.get("/admin/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.headers["Location"])

    def test_admin_cannot_access_customer_dashboard_as_customer(self):
        """Verifies that an admin is not automatically treated as a customer."""
        # Log in as admin
        self.client.post(
            "/admin/login",
            data={"username_or_email": SAMPLE_ADMIN["username"], "password": SAMPLE_ADMIN["password"]},
        )
        response = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    # =========================================================================
    # 5. Password Change Tests
    # =========================================================================

    def test_password_change_success(self):
        """Tests changing password for customer."""
        success, errors = change_customer_password(
            customer_id=1,
            current_password="Password123",
            new_password="NewSecretPass99",
            confirm_new_password="NewSecretPass99",
        )
        self.assertTrue(success)
        self.assertEqual(len(errors), 0)

        # Verify login now works with new password and fails with old password
        cust_new, _ = authenticate_customer("sarah.jenkins@bankcorp.com", "NewSecretPass99")
        self.assertIsNotNone(cust_new)

        cust_old, _ = authenticate_customer("sarah.jenkins@bankcorp.com", "Password123")
        self.assertIsNone(cust_old)

    def test_password_change_failure_incorrect_current_password(self):
        """Tests password change fails when current password is wrong."""
        success, errors = change_customer_password(
            customer_id=1,
            current_password="IncorrectPassword",
            new_password="NewPassword123",
            confirm_new_password="NewPassword123",
        )
        self.assertFalse(success)
        self.assertTrue(any("Current password does not match" in err for err in errors))

    # =========================================================================
    # 6. Login Attempt Protection Tests
    # =========================================================================

    def test_login_attempt_protection_lockout(self):
        """Tests that 3 failed login attempts trigger temporary lockout."""
        email = "marcus.chen@horizontech.io"
        clear_failed_logins(email)

        # Attempt 1 failed
        _, err1 = authenticate_customer(email, "badpass1")
        self.assertEqual(err1, "Invalid email or password.")

        # Attempt 2 failed
        _, err2 = authenticate_customer(email, "badpass2")
        self.assertEqual(err2, "Invalid email or password.")

        # Attempt 3 failed -> should trigger lockout
        _, err3 = authenticate_customer(email, "badpass3")
        self.assertEqual(err3, "Invalid email or password.")

        # Attempt 4: Even with the CORRECT password, account should be temporarily locked!
        cust_locked, err_locked = authenticate_customer(email, "Password123")
        self.assertIsNone(cust_locked)
        self.assertTrue("Too many failed login attempts" in err_locked)


if __name__ == "__main__":
    unittest.main()
