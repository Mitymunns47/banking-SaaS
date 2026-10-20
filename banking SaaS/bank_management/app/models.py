"""
app/models.py
=============================================================================
Data Layer and In-Memory Storage for CORE BANKING SYSTEM
=============================================================================

PYTHON FUNDAMENTALS DEMONSTRATED IN THIS FILE:
1. Python Dictionaries (dict):
   - Key-value data structures representing customer records, admin accounts,
     and financial transaction records.

2. Python Lists (list):
   - In-memory collections acting as database tables (CUSTOMERS_DB, TRANSACTIONS_DB).

3. In-Place Mutable List Operations (.clear() and .extend()):
   - Ensures memory references across modules remain consistent when resetting state.

4. Type Hints:
   - Defining collection structures such as `list[dict]`.
"""

# Initial seed data representing customers currently registered in the bank
INITIAL_CUSTOMERS: list[dict] = [
    {
        "customer_id": 1,
        "name": "Sarah Jenkins",
        "age": 29,
        "email": "sarah.jenkins@bankcorp.com",
        "phone": "+1 (555) 234-5678",
        "password": "Password123",
        "account_number": "ACC-1002941",
        "account_type": "Savings",
        "balance": 4850.75,
        "is_active": True,
        "account_status": "Active",
    },
    {
        "customer_id": 2,
        "name": "Marcus Aurelius Chen",
        "age": 42,
        "email": "marcus.chen@horizontech.io",
        "phone": "+1 (555) 876-5432",
        "password": "Password123",
        "account_number": "ACC-1003882",
        "account_type": "Checking",
        "balance": 12450.00,
        "is_active": True,
        "account_status": "Active",
    },
    {
        "customer_id": 3,
        "name": "Amira Patel",
        "age": 35,
        "email": "amira.patel@designhub.co",
        "phone": "+1 (555) 345-6789",
        "password": "Password123",
        "account_number": "ACC-1004119",
        "account_type": "Savings",
        "balance": 820.50,
        "is_active": False,  # Inactive / suspended account demonstration
        "account_status": "Inactive",
    },
    {
        "customer_id": 4,
        "name": "David Miller",
        "age": 58,
        "email": "david.miller@timbercraft.net",
        "phone": "+1 (555) 901-2345",
        "password": "Password123",
        "account_number": "ACC-1005224",
        "account_type": "Checking",
        "balance": 31200.25,
        "is_active": True,
        "account_status": "Active",
    },
    {
        "customer_id": 5,
        "name": "Elena Rostova",
        "age": 27,
        "email": "elena.rostova@biolabs.org",
        "phone": "+1 (555) 456-7890",
        "password": "Password123",
        "account_number": "ACC-1006731",
        "account_type": "Savings",
        "balance": 0.00,
        "is_active": False,
        "account_status": "Pending",
    },
    {
        "customer_id": 6,
        "name": "Thomas Sterling",
        "age": 50,
        "email": "thomas.sterling@capitalgroup.com",
        "phone": "+1 (555) 678-1234",
        "password": "Password123",
        "account_number": "ACC-1007892",
        "account_type": "Business",
        "balance": 18450.00,
        "is_active": False,
        "account_status": "Frozen",
    },
]

# Sample Admin account for Bank Staff login
SAMPLE_ADMIN: dict = {
    "admin_id": 1,
    "username": "admin",
    "email": "admin@bankcorp.com",
    "name": "Bank Administrator",
    "password": "AdminPassword123",
    "role": "admin",
}

# Initial seed transaction records
INITIAL_TRANSACTIONS: list[dict] = [
    {
        "transaction_id": 1,
        "customer_id": 1,
        "transaction_type": "Deposit",
        "type": "Deposit",
        "amount": 5000.00,
        "timestamp": "2026-10-01 09:30:00",
        "reference_account": "ACC-1002941",
        "status": "Completed",
    },
    {
        "transaction_id": 2,
        "customer_id": 1,
        "transaction_type": "Withdrawal",
        "type": "Withdrawal",
        "amount": 149.25,
        "timestamp": "2026-10-03 14:15:22",
        "reference_account": "ACC-1002941",
        "status": "Completed",
    },
    {
        "transaction_id": 3,
        "customer_id": 2,
        "transaction_type": "Deposit",
        "type": "Deposit",
        "amount": 12450.00,
        "timestamp": "2026-10-02 11:00:00",
        "reference_account": "ACC-1003882",
        "status": "Completed",
    },
    {
        "transaction_id": 4,
        "customer_id": 2,
        "transaction_type": "Transfer",
        "type": "Transfer",
        "amount": 500.00,
        "timestamp": "2026-10-04 16:45:10",
        "reference_account": "ACC-1005224",
        "status": "Completed",
    },
    {
        "transaction_id": 5,
        "customer_id": 4,
        "transaction_type": "Transfer",
        "type": "Transfer",
        "amount": 500.00,
        "timestamp": "2026-10-04 16:45:10",
        "reference_account": "ACC-1003882",
        "status": "Completed",
    },
    {
        "transaction_id": 6,
        "customer_id": 6,
        "transaction_type": "Deposit",
        "type": "Deposit",
        "amount": 18450.00,
        "timestamp": "2026-10-01 10:00:00",
        "reference_account": "ACC-1007892",
        "status": "Completed",
    },
]

# Loan Types supported by the Core Banking System
LOAN_TYPES: list[str] = ["Personal", "Education", "Home", "Business"]

# Initial seed loan applications
INITIAL_LOANS: list[dict] = [
    {
        "loan_id": 1,
        "application_id": "LN-1001",
        "customer_id": 1,
        "customer_name": "Sarah Jenkins",
        "loan_type": "Personal",
        "requested_amount": 5000.00,
        "tenure_months": 24,
        "purpose": "Home renovation and electronics purchase",
        "monthly_income": 4500.00,
        "application_date": "2026-10-01 10:30:00",
        "status": "Approved",
        "approved_amount": 5000.00,
        "annual_interest_rate": 8.5,
        "approved_tenure_months": 24,
        "estimated_emi": 227.32,
        "total_repayment": 5455.68,
        "total_interest": 455.68,
        "admin_decision_date": "2026-10-02 14:00:00",
        "admin_notes": "Application pre-approved based on positive ledger history.",
        "rejection_reason": None,
    },
    {
        "loan_id": 2,
        "application_id": "LN-1002",
        "customer_id": 2,
        "customer_name": "Marcus Aurelius Chen",
        "loan_type": "Business",
        "requested_amount": 25000.00,
        "tenure_months": 36,
        "purpose": "Working capital expansion for tech consulting enterprise",
        "monthly_income": 8200.00,
        "application_date": "2026-09-15 11:00:00",
        "status": "Active",
        "approved_amount": 25000.00,
        "annual_interest_rate": 9.0,
        "approved_tenure_months": 36,
        "estimated_emi": 794.99,
        "total_repayment": 28619.64,
        "total_interest": 3619.64,
        "admin_decision_date": "2026-09-16 16:30:00",
        "admin_notes": "Corporate registry verified. Active loan portfolio.",
        "rejection_reason": None,
    },
    {
        "loan_id": 3,
        "application_id": "LN-1003",
        "customer_id": 4,
        "customer_name": "David Miller",
        "loan_type": "Home",
        "requested_amount": 50000.00,
        "tenure_months": 120,
        "purpose": "Residential property mortgage and extension",
        "monthly_income": 6500.00,
        "application_date": "2026-10-05 09:15:00",
        "status": "Pending",
        "approved_amount": None,
        "annual_interest_rate": None,
        "approved_tenure_months": None,
        "estimated_emi": None,
        "total_repayment": None,
        "total_interest": None,
        "admin_decision_date": None,
        "admin_notes": None,
        "rejection_reason": None,
    },
    {
        "loan_id": 4,
        "application_id": "LN-1004",
        "customer_id": 1,
        "customer_name": "Sarah Jenkins",
        "loan_type": "Education",
        "requested_amount": 3500.00,
        "tenure_months": 12,
        "purpose": "Postgraduate professional certification course fees",
        "monthly_income": 4500.00,
        "application_date": "2026-10-06 14:20:00",
        "status": "Pending",
        "approved_amount": None,
        "annual_interest_rate": None,
        "approved_tenure_months": None,
        "estimated_emi": None,
        "total_repayment": None,
        "total_interest": None,
        "admin_decision_date": None,
        "admin_notes": None,
        "rejection_reason": None,
    },
    {
        "loan_id": 5,
        "application_id": "LN-1005",
        "customer_id": 6,
        "customer_name": "Thomas Sterling",
        "loan_type": "Business",
        "requested_amount": 80000.00,
        "tenure_months": 60,
        "purpose": "Capital machinery acquisition",
        "monthly_income": 12000.00,
        "application_date": "2026-09-28 15:45:00",
        "status": "Rejected",
        "approved_amount": None,
        "annual_interest_rate": None,
        "approved_tenure_months": None,
        "estimated_emi": None,
        "total_repayment": None,
        "total_interest": None,
        "admin_decision_date": "2026-09-29 11:10:00",
        "admin_notes": None,
        "rejection_reason": "Applicant account currently in restricted status; collateral verification required.",
    },
]

# Cheque Book Leaf Options and Statuses
LEAF_OPTIONS: list[int] = [10, 25, 50]
CHEQUE_STATUSES: list[str] = ["Pending", "Approved", "Rejected", "Cancelled", "Completed"]

# Initial seed data for cheque book requests
INITIAL_CHEQUE_REQUESTS: list[dict] = [
    {
        "request_id": 1,
        "cheque_request_id": "CHQ-1001",
        "customer_id": 1,
        "customer_name": "Sarah Jenkins",
        "account_number": "ACC-1002941",
        "leaves": 25,
        "request_date": "2026-10-01 11:20:00",
        "status": "Completed",
        "admin_decision_date": "2026-10-02 09:15:00",
        "admin_notes": "Printed and dispatched via courier.",
        "rejection_reason": None,
    },
    {
        "request_id": 2,
        "cheque_request_id": "CHQ-1002",
        "customer_id": 2,
        "customer_name": "Marcus Aurelius Chen",
        "account_number": "ACC-1003882",
        "leaves": 50,
        "request_date": "2026-10-03 14:10:00",
        "status": "Approved",
        "admin_decision_date": "2026-10-04 10:00:00",
        "admin_notes": "Authorized for print queue batch #104.",
        "rejection_reason": None,
    },
    {
        "request_id": 3,
        "cheque_request_id": "CHQ-1003",
        "customer_id": 4,
        "customer_name": "David Miller",
        "account_number": "ACC-1005224",
        "leaves": 25,
        "request_date": "2026-10-06 16:30:00",
        "status": "Pending",
        "admin_decision_date": None,
        "admin_notes": None,
        "rejection_reason": None,
    },
    {
        "request_id": 4,
        "cheque_request_id": "CHQ-1004",
        "customer_id": 1,
        "customer_name": "Sarah Jenkins",
        "account_number": "ACC-1002941",
        "leaves": 10,
        "request_date": "2026-10-07 09:45:00",
        "status": "Pending",
        "admin_decision_date": None,
        "admin_notes": None,
        "rejection_reason": None,
    },
    {
        "request_id": 5,
        "cheque_request_id": "CHQ-1005",
        "customer_id": 6,
        "customer_name": "Thomas Sterling",
        "account_number": "ACC-1007892",
        "leaves": 50,
        "request_date": "2026-09-29 12:00:00",
        "status": "Rejected",
        "admin_decision_date": "2026-09-30 11:20:00",
        "admin_notes": None,
        "rejection_reason": "Account is currently in Frozen status; cheque book facility restricted.",
    },
    {
        "request_id": 6,
        "cheque_request_id": "CHQ-1006",
        "customer_id": 2,
        "customer_name": "Marcus Aurelius Chen",
        "account_number": "ACC-1003882",
        "leaves": 10,
        "request_date": "2026-09-25 15:00:00",
        "status": "Cancelled",
        "admin_decision_date": None,
        "admin_notes": "Cancelled by customer.",
        "rejection_reason": None,
    },
]

# Initial seed data for administrative audit logging
INITIAL_AUDIT_LOGS: list[dict] = [
    {
        "log_id": 1,
        "admin_id": "admin",
        "action": "ACCOUNT_REJECTED",
        "target_type": "Customer Account",
        "target_id": "ACC-1006731",
        "timestamp": "2026-09-20 14:10:00",
        "outcome": "Success",
        "details": "Customer #5 account application rejected during onboarding review.",
    },
    {
        "log_id": 2,
        "admin_id": "admin",
        "action": "ACCOUNT_FROZEN",
        "target_type": "Customer Account",
        "target_id": "ACC-1007892",
        "timestamp": "2026-09-22 16:35:00",
        "outcome": "Success",
        "details": "Account ACC-1007892 placed under administrative freeze.",
    },
    {
        "log_id": 3,
        "admin_id": "admin",
        "action": "LOAN_APPROVED",
        "target_type": "Loan Facility",
        "target_id": "LN-1001",
        "timestamp": "2026-10-02 14:00:00",
        "outcome": "Success",
        "details": "Personal Loan LN-1001 approved for $5,000.00 at 8.5% p.a. (24 months).",
    },
    {
        "log_id": 4,
        "admin_id": "admin",
        "action": "CHEQUE_COMPLETED",
        "target_type": "Cheque Book",
        "target_id": "CHQ-1001",
        "timestamp": "2026-10-02 09:15:00",
        "outcome": "Success",
        "details": "Cheque book request CHQ-1001 for 25 leaves printed and dispatched via courier.",
    },
]

# In-memory "Database" tables
CUSTOMERS_DB: list[dict] = [dict(customer) for customer in INITIAL_CUSTOMERS]
TRANSACTIONS_DB: list[dict] = [dict(tx) for tx in INITIAL_TRANSACTIONS]
LOANS_DB: list[dict] = [dict(loan) for loan in INITIAL_LOANS]
CHEQUE_REQUESTS_DB: list[dict] = [dict(req) for req in INITIAL_CHEQUE_REQUESTS]
AUDIT_LOG_DB: list[dict] = [dict(log) for log in INITIAL_AUDIT_LOGS]

# In-memory tracking for failed login attempts to protect against brute force
LOGIN_ATTEMPTS: dict[str, dict] = {}


def reset_customers_db() -> None:
    """
    Resets the in-memory customer database, transactions, loans, cheque requests, audit logs, and login attempts.
    Uses in-place list modification (.clear() and .extend()) to ensure that all modules
    sharing the references stay synchronized across tests.
    """
    global CUSTOMERS_DB, LOGIN_ATTEMPTS, TRANSACTIONS_DB, LOANS_DB, CHEQUE_REQUESTS_DB, AUDIT_LOG_DB, SAMPLE_ADMIN
    CUSTOMERS_DB.clear()
    CUSTOMERS_DB.extend([dict(customer) for customer in INITIAL_CUSTOMERS])
    LOGIN_ATTEMPTS.clear()
    TRANSACTIONS_DB.clear()
    TRANSACTIONS_DB.extend([dict(tx) for tx in INITIAL_TRANSACTIONS])
    LOANS_DB.clear()
    LOANS_DB.extend([dict(loan) for loan in INITIAL_LOANS])
    CHEQUE_REQUESTS_DB.clear()
    CHEQUE_REQUESTS_DB.extend([dict(req) for req in INITIAL_CHEQUE_REQUESTS])
    AUDIT_LOG_DB.clear()
    AUDIT_LOG_DB.extend([dict(log) for log in INITIAL_AUDIT_LOGS])
    SAMPLE_ADMIN["password"] = "AdminPassword123"
