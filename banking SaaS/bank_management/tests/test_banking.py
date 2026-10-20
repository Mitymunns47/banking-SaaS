"""
tests/test_banking.py
=============================================================================
Automated Core Banking Operations Tests for CORE BANKING SYSTEM
=============================================================================

PYTHON FUNDAMENTALS DEMONSTRATED IN THIS FILE:
1. Automated Testing with Python's standard `unittest` framework.
2. State isolation: resetting data models prior to each test run.
3. Testing financial invariants: balance updates, atomic transfers, and ledger history.
4. Testing role-based route security and session authentication.
"""

import sys
import os
import unittest

# Ensure app package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.models import reset_customers_db, CUSTOMERS_DB, TRANSACTIONS_DB
from app.services import (
    get_customer_by_id,
    get_customer_by_account_number,
    deposit_money,
    withdraw_money,
    transfer_money,
    get_transaction_history,
)


class TestCoreBankingOperations(unittest.TestCase):
    """Test suite covering core banking operations: deposit, withdraw, transfer, and transactions."""

    def setUp(self):
        """Reset in-memory data store and initialize test client."""
        reset_customers_db()
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret-banking"})
        self.client = self.app.test_client()

    # =========================================================================
    # 1. Deposit Tests
    # =========================================================================

    def test_successful_deposit(self):
        """Verifies deposit increases customer balance and creates a transaction record."""
        # Sarah Jenkins initial balance: 4850.75
        customer_id = 1
        initial_balance = get_customer_by_id(customer_id)["balance"]
        deposit_amount = 500.25

        success, message, new_balance = deposit_money(customer_id, deposit_amount)
        self.assertTrue(success)
        self.assertEqual(new_balance, round(initial_balance + deposit_amount, 2))

        # Verify customer in DB has updated balance
        customer = get_customer_by_id(customer_id)
        self.assertEqual(customer["balance"], 5351.00)

        # Verify transaction record created
        txs = get_transaction_history(customer_id)
        latest_tx = txs[0]
        self.assertEqual(latest_tx["transaction_type"], "Deposit")
        self.assertEqual(latest_tx["amount"], 500.25)
        self.assertEqual(latest_tx["status"], "Completed")

    def test_invalid_deposit_amounts_rejected(self):
        """Verifies zero, negative, and non-numeric deposit amounts are rejected."""
        customer_id = 1
        initial_balance = get_customer_by_id(customer_id)["balance"]

        # Zero deposit
        ok_zero, msg_zero, _ = deposit_money(customer_id, 0)
        self.assertFalse(ok_zero)
        self.assertIn("greater than zero", msg_zero)

        # Negative deposit
        ok_neg, msg_neg, _ = deposit_money(customer_id, -100)
        self.assertFalse(ok_neg)
        self.assertIn("greater than zero", msg_neg)

        # Non-numeric deposit
        ok_str, msg_str, _ = deposit_money(customer_id, "invalid_amount")
        self.assertFalse(ok_str)
        self.assertIn("valid numeric", msg_str)

        # Balance remains unchanged
        self.assertEqual(get_customer_by_id(customer_id)["balance"], initial_balance)

    def test_deposit_rejected_for_inactive_account(self):
        """Verifies deposit is rejected if the customer account is inactive or pending."""
        # Amira Patel (customer_id 3) is inactive in sample data
        ok, msg, _ = deposit_money(customer_id=3, amount=200.00)
        self.assertFalse(ok)
        self.assertIn("not active", msg)

    # =========================================================================
    # 2. Withdrawal Tests
    # =========================================================================

    def test_successful_withdrawal(self):
        """Verifies withdrawal decreases customer balance and creates a transaction record."""
        # Sarah Jenkins initial balance: 4850.75
        customer_id = 1
        withdraw_amount = 350.75

        success, message, new_balance = withdraw_money(customer_id, withdraw_amount)
        self.assertTrue(success)
        self.assertEqual(new_balance, 4500.00)

        customer = get_customer_by_id(customer_id)
        self.assertEqual(customer["balance"], 4500.00)

        # Verify transaction record created
        txs = get_transaction_history(customer_id)
        latest_tx = txs[0]
        self.assertEqual(latest_tx["transaction_type"], "Withdrawal")
        self.assertEqual(latest_tx["amount"], 350.75)
        self.assertEqual(latest_tx["status"], "Completed")

    def test_withdrawal_insufficient_balance_rejected(self):
        """Verifies withdrawal exceeding available balance is rejected without altering balance."""
        customer_id = 1
        initial_balance = get_customer_by_id(customer_id)["balance"]
        excessive_amount = initial_balance + 1000.00

        success, message, current_bal = withdraw_money(customer_id, excessive_amount)
        self.assertFalse(success)
        self.assertIn("Insufficient funds", message)
        self.assertEqual(get_customer_by_id(customer_id)["balance"], initial_balance)

    def test_invalid_withdrawal_amounts_rejected(self):
        """Verifies zero, negative, or non-numeric withdrawals are rejected."""
        customer_id = 1
        initial_balance = get_customer_by_id(customer_id)["balance"]

        ok_zero, _, _ = withdraw_money(customer_id, 0)
        self.assertFalse(ok_zero)

        ok_neg, _, _ = withdraw_money(customer_id, -50.0)
        self.assertFalse(ok_neg)

        ok_none, _, _ = withdraw_money(customer_id, None)
        self.assertFalse(ok_none)

        self.assertEqual(get_customer_by_id(customer_id)["balance"], initial_balance)

    def test_withdrawal_rejected_for_inactive_account(self):
        """Verifies withdrawal is rejected if account is inactive."""
        ok, msg, _ = withdraw_money(customer_id=3, amount=50.00)
        self.assertFalse(ok)
        self.assertIn("not active", msg)

    # =========================================================================
    # 3. Money Transfer Tests
    # =========================================================================

    def test_successful_transfer(self):
        """Verifies transferring funds decrements sender, increments recipient, and writes two records."""
        # Sarah Jenkins (ID 1, ACC-1002941, bal 4850.75)
        # Marcus Chen (ID 2, ACC-1003882, bal 12450.00)
        sender_id = 1
        recipient_acc = "ACC-1003882"
        transfer_amt = 1000.00

        success, message, sender_new_bal = transfer_money(sender_id, recipient_acc, transfer_amt)
        self.assertTrue(success)
        self.assertEqual(sender_new_bal, 3850.75)

        # Verify database balances
        sender = get_customer_by_id(1)
        recipient = get_customer_by_id(2)
        self.assertEqual(sender["balance"], 3850.75)
        self.assertEqual(recipient["balance"], 13450.00)

        # Verify transaction records for both parties
        sender_txs = get_transaction_history(1)
        self.assertEqual(sender_txs[0]["transaction_type"], "Transfer (Debit)")
        self.assertEqual(sender_txs[0]["reference_account"], recipient_acc)
        self.assertEqual(sender_txs[0]["amount"], 1000.00)

        recipient_txs = get_transaction_history(2)
        self.assertEqual(recipient_txs[0]["transaction_type"], "Transfer (Credit)")
        self.assertEqual(recipient_txs[0]["reference_account"], sender["account_number"])
        self.assertEqual(recipient_txs[0]["amount"], 1000.00)

    def test_transfer_invalid_recipient_rejected(self):
        """Verifies transfer to a non-existent account number is rejected."""
        sender_id = 1
        initial_balance = get_customer_by_id(sender_id)["balance"]

        success, message, _ = transfer_money(sender_id, "ACC-NONEXISTENT", 100.00)
        self.assertFalse(success)
        self.assertIn("was not found", message)
        self.assertEqual(get_customer_by_id(sender_id)["balance"], initial_balance)

    def test_self_transfer_rejected(self):
        """Verifies transfer to one's own account is strictly forbidden."""
        sender_id = 1
        sender_acc = get_customer_by_id(sender_id)["account_number"]
        initial_balance = get_customer_by_id(sender_id)["balance"]

        success, message, _ = transfer_money(sender_id, sender_acc, 200.00)
        self.assertFalse(success)
        self.assertIn("own account", message)
        self.assertEqual(get_customer_by_id(sender_id)["balance"], initial_balance)

    def test_transfer_insufficient_balance_rejected(self):
        """Verifies transfer exceeding available balance is rejected without altering balances."""
        sender_id = 1
        recipient_acc = "ACC-1003882"
        initial_sender_bal = get_customer_by_id(sender_id)["balance"]
        initial_recip_bal = get_customer_by_id(2)["balance"]

        excessive = initial_sender_bal + 5000.00
        success, message, _ = transfer_money(sender_id, recipient_acc, excessive)
        self.assertFalse(success)
        self.assertIn("Insufficient funds", message)

        self.assertEqual(get_customer_by_id(sender_id)["balance"], initial_sender_bal)
        self.assertEqual(get_customer_by_id(2)["balance"], initial_recip_bal)

    def test_transfer_to_inactive_recipient_rejected(self):
        """Verifies transfer to an inactive/pending recipient account is rejected."""
        # Amira Patel (ID 3, ACC-1004119) is inactive
        sender_id = 1
        success, message, _ = transfer_money(sender_id, "ACC-1004119", 100.00)
        self.assertFalse(success)
        self.assertIn("inactive or pending", message)

    # =========================================================================
    # 4. Transaction History Tests
    # =========================================================================

    def test_transaction_history_isolated_to_customer(self):
        """Verifies customer only sees their own transactions, ordered newest first."""
        # Seed has 2 txs for customer 1 and 1 tx for customer 2
        c1_txs = get_transaction_history(1)
        c2_txs = get_transaction_history(2)

        self.assertGreaterEqual(len(c1_txs), 2)
        for tx in c1_txs:
            self.assertEqual(tx["customer_id"], 1)

        self.assertGreaterEqual(len(c2_txs), 1)
        for tx in c2_txs:
            self.assertEqual(tx["customer_id"], 2)

        # Check descending order by transaction ID
        self.assertGreater(c1_txs[0]["transaction_id"], c1_txs[1]["transaction_id"])

    # =========================================================================
    # 5. Route Protection & Unauthorized Access Tests
    # =========================================================================

    def test_unauthorized_access_to_banking_routes(self):
        """Verifies unauthenticated visitors cannot access deposit, withdraw, transfer, or transactions."""
        for endpoint in ["/deposit", "/withdraw", "/transfer", "/transactions"]:
            resp = self.client.get(endpoint, follow_redirects=False)
            self.assertEqual(resp.status_code, 302)
            self.assertIn("/login", resp.headers["Location"])

    def test_authenticated_deposit_route_flow(self):
        """Tests logging in and posting a deposit through the web route."""
        # Log in as Sarah
        self.client.post("/login", data={"email": "sarah.jenkins@bankcorp.com", "password": "Password123"})

        # Submit deposit
        resp = self.client.post("/deposit", data={"amount": "250.00"}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Successfully deposited $250.00", resp.data)

        # Check balance in database
        self.assertEqual(get_customer_by_id(1)["balance"], 5100.75)


if __name__ == "__main__":
    unittest.main()
