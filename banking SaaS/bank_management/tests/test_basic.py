"""
tests/test_basic.py
=============================================================================
Automated Unit and Integration Tests for Bank Management Software (Phase 1)
=============================================================================

PYTHON FUNDAMENTALS DEMONSTRATED IN THIS FILE:
1. Automated Testing with Python's built-in `unittest` framework.
2. Test isolation using `setUp()` to restore initial state before each test.
3. Assertions: `assertEqual`, `assertTrue`, `assertFalse`, `assertIsNone`, `assertIsNotNone`, `assertIn`.
4. Testing Flask client routes and HTTP response status codes (200, 400, 404).
"""

import sys
import os
import unittest

# Ensure app package is importable from tests directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.models import reset_customers_db, CUSTOMERS_DB
from app.services import (
    get_all_customers,
    get_customer_by_id,
    create_customer,
    is_account_active,
)
from app.utils import (
    validate_customer_data,
    safe_int,
    safe_float,
    format_currency,
)


class TestBankManagementPhase1(unittest.TestCase):
    """Test suite covering Phase 1 core functionality."""

    def setUp(self):
        """Runs before every single test to guarantee fresh, isolated state."""
        reset_customers_db()
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()

    # =========================================================================
    # 1. Tests for Data Retrieval & Search
    # =========================================================================

    def test_get_all_customers_returns_initial_records(self):
        """Verifies that all seed sample customers are loaded."""
        customers = get_all_customers()
        self.assertGreaterEqual(len(customers), 4)
        first_customer = customers[0]
        self.assertEqual(first_customer["customer_id"], 1)
        self.assertEqual(first_customer["name"], "Sarah Jenkins")

    def test_finding_existing_customer(self):
        """Verifies searching for an existing customer by their valid ID."""
        customer = get_customer_by_id(2)
        self.assertIsNotNone(customer)
        self.assertEqual(customer["name"], "Marcus Aurelius Chen")
        self.assertEqual(customer["account_type"], "Checking")
        self.assertEqual(customer["balance"], 12450.00)

    def test_handling_customer_that_does_not_exist(self):
        """Verifies that searching for a non-existent ID returns None."""
        customer = get_customer_by_id(99999)
        self.assertIsNone(customer)

    def test_account_active_status_check(self):
        """Verifies checking account active status."""
        self.assertTrue(is_account_active(1))   # Sarah is active
        self.assertFalse(is_account_active(3))  # Amira is inactive
        self.assertFalse(is_account_active(999)) # Non-existent returns False

    # =========================================================================
    # 2. Tests for Customer Creation & Validation
    # =========================================================================

    def test_customer_creation_success(self):
        """Verifies creating a customer with valid information."""
        new_customer, errors = create_customer(
            name="Robert Frost",
            age=34,
            email="robert.frost@poetry.org",
            phone="+1 (555) 777-8888",
            account_type="Savings",
            balance=1500.50,
            is_active=True,
        )
        self.assertEqual(len(errors), 0)
        self.assertIsNotNone(new_customer)
        self.assertEqual(new_customer["name"], "Robert Frost")
        self.assertEqual(new_customer["balance"], 1500.50)
        self.assertTrue(new_customer["account_number"].startswith("ACC-"))

        # Verify new customer exists in DB list
        fetched = get_customer_by_id(new_customer["customer_id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["email"], "robert.frost@poetry.org")

    def test_validation_rejects_underage_customer(self):
        """Verifies validation rejects customers below 18 years old."""
        invalid_data = {
            "name": "Tommy Underage",
            "age": 16,
            "email": "tommy@example.com",
            "phone": "+1 (555) 123-4567",
            "account_type": "Savings",
            "balance": 100.0,
        }
        is_valid, errors = validate_customer_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertTrue(any("18 years old" in err for err in errors))

    def test_validation_rejects_negative_balance(self):
        """Verifies validation rejects initial negative balance."""
        invalid_data = {
            "name": "Jane Debt",
            "age": 25,
            "email": "jane@example.com",
            "phone": "+1 (555) 123-4567",
            "account_type": "Savings",
            "balance": -250.0,
        }
        is_valid, errors = validate_customer_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertTrue(any("negative" in err for err in errors))

    def test_validation_rejects_empty_name_and_invalid_email(self):
        """Verifies validation catches missing name and malformed email."""
        invalid_data = {
            "name": "",
            "age": 30,
            "email": "bademailformat",
            "phone": "1234567",
            "account_type": "Savings",
            "balance": 50.0,
        }
        is_valid, errors = validate_customer_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertGreaterEqual(len(errors), 2)

    # =========================================================================
    # 3. Tests for Exception Handling Helpers
    # =========================================================================

    def test_safe_int_and_safe_float_conversions(self):
        """Tests that safe numeric converters catch errors and return defaults."""
        self.assertEqual(safe_int("42"), 42)
        self.assertEqual(safe_int("invalid_int", default=-1), -1)
        self.assertIsNone(safe_int(None))

        self.assertEqual(safe_float("125.75"), 125.75)
        self.assertEqual(safe_float("not_a_float", default=0.0), 0.0)

    def test_format_currency_helper(self):
        """Tests currency string representation."""
        self.assertEqual(format_currency(1234.5), "$1,234.50")
        self.assertEqual(format_currency(0), "$0.00")
        self.assertEqual(format_currency("invalid"), "$0.00")

    # =========================================================================
    # 4. Tests for Flask HTTP Routes
    # =========================================================================

    def test_route_index_status_200(self):
        """Tests home page returns HTTP 200 OK."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"CORE BANKING SYSTEM", response.data)
        self.assertIn(b"Total Customers", response.data)

    def test_route_customers_list_status_200(self):
        """Tests customers directory page returns HTTP 200 OK and lists sample customers."""
        response = self.client.get("/customers")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Customer Directory", response.data)
        self.assertIn(b"Sarah Jenkins", response.data)
        self.assertIn(b"Marcus Aurelius Chen", response.data)

    def test_route_customer_details_existing_status_200(self):
        """Tests viewing customer details for existing customer #1."""
        response = self.client.get("/customer/1")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Sarah Jenkins", response.data)
        self.assertIn(b"ACC-1002941", response.data)
        self.assertIn(b"Account Active", response.data)

    def test_route_customer_details_not_found_status_404(self):
        """Tests viewing customer details for non-existent ID returns 404."""
        response = self.client.get("/customer/9999")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Customer Record Not Found", response.data)

    def test_route_customer_details_invalid_id_status_400(self):
        """Tests non-integer ID in URL returns 400 Bad Request."""
        response = self.client.get("/customer/not-a-number")
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"must be a numeric integer", response.data)


if __name__ == "__main__":
    unittest.main()
