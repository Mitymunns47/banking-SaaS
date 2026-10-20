# CORE BANKING SYSTEM: PYTHON & FLASK LEARNING GUIDE

A concise guide to the core Python programming and Flask web development concepts implemented throughout the **CORE BANKING SYSTEM**. Each section explains the concept, provides a clear banking-related code example, and references the exact project file where it is demonstrated.

---

## 📚 Table of Contents
1. [Variables and Data Types](#1-variables-and-data-types)
2. [Lists and Dictionaries](#2-lists-and-dictionaries)
3. [Conditional Logic (`if`, `elif`, `else`)](#3-conditional-logic-if-elif-else)
4. [Loops (`for` and `while`)](#4-loops-for-and-while)
5. [Functions, Parameters, and Return Values](#5-functions-parameters-and-return-values)
6. [String Operations & Formatting](#6-string-operations--formatting)
7. [Exception Handling (`try` and `except`)](#7-exception-handling-try-and-except)
8. [Comparison and Logical Operators](#8-comparison-and-logical-operators)
9. [Modules and Package Imports](#9-modules-and-package-imports)
10. [Type Hints & Annotations](#10-type-hints--annotations)
11. [Project Structure & Separation of Concerns](#11-project-structure--separation-of-concerns)
12. [Flask Fundamentals (Routes, Requests, Responses, Sessions, Templates)](#12-flask-fundamentals)
13. [Authentication, Password Hashing & Role-Based Authorization](#13-authentication--authorization)
14. [Data Models and Service-Layer Business Logic](#14-data-models--service-layer)
15. [Automated Testing (`unittest`)](#15-automated-testing)
16. [Virtual Environments & Dependency Management](#16-virtual-environments--dependencies)
17. [Application Security, CSRF & Input Sanitization](#17-application-security--validation)

---

### 1. Variables and Data Types
Python is dynamically typed and supports fundamental primitive types: strings (`str`), integers (`int`), floating-point numbers (`float`), booleans (`bool`), and absence of value (`None`).

**Banking Example:**
```python
account_number: str = "ACC-1002941"
customer_age: int = 34
current_balance: float = 4850.75
is_account_active: bool = True
co_signer: str | None = None
```
**Project Reference:** [models.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/models.py#L30-L75), [utils.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/utils.py#L25-L60)

---

### 2. Lists and Dictionaries
- **Dictionaries (`dict`):** Key-value mappings represent database-like records (e.g., customer profiles, loan applications).
- **Lists (`list`):** Ordered collections store multiple entity records and transaction ledgers.

**Banking Example:**
```python
customer_record: dict = {
    "customer_id": 1,
    "name": "Sarah Jenkins",
    "balance": 4850.75,
    "account_status": "Active"
}

transaction_ledger: list[dict] = [
    {"txn_id": 101, "type": "Deposit", "amount": 500.0},
    {"txn_id": 102, "type": "Withdrawal", "amount": 100.0}
]
```
**Project Reference:** [models.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/models.py#L60-L150) (`CUSTOMERS_DB`, `TRANSACTIONS_DB`, `LOANS_DB`)

---

### 3. Conditional Logic (`if`, `elif`, `else`)
Evaluates conditions sequentially to enforce business rules and guard rails.

**Banking Example:**
```python
if amount <= 0:
    return False, "Deposit amount must be strictly greater than zero."
elif amount > 50000.00:
    return False, "Exceeds single transaction branch limit ($50,000.00)."
else:
    customer["balance"] += amount
    return True, "Deposit processed successfully."
```
**Project Reference:** [services.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/services.py#L110-L150) (`deposit_money`, `withdraw_money`, `transfer_money`)

---

### 4. Loops (`for` and `while`)
- `for` loops iterate over customer records and transaction histories for searching and aggregations.
- `while` loops or list comprehensions process queues and status filters.

**Banking Example:**
```python
total_deposits = 0.0
for txn in TRANSACTIONS_DB:
    if txn["transaction_type"] == "Deposit" and txn["status"] == "Completed":
        total_deposits += txn["amount"]
```
**Project Reference:** [services.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/services.py#L190-L240) (`generate_admin_comprehensive_report`, `search_customers`)

---

### 5. Functions, Parameters, and Return Values
Functions package reusable algorithms with explicit input arguments, default parameters, and structured return values (often tuples of `(success: bool, message: str)`).

**Banking Example:**
```python
def calculate_loan_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    if annual_rate == 0.0:
        return round(principal / tenure_months, 2)
    monthly_r = (annual_rate / 100.0) / 12.0
    factor = (1 + monthly_r) ** tenure_months
    emi = principal * monthly_r * factor / (factor - 1)
    return round(emi, 2)
```
**Project Reference:** [services.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/services.py#L520-L580) (`calculate_loan_repayment_details`)

---

### 6. String Operations & Formatting
String methods (`.strip()`, `.lower()`, `.startswith()`) sanitize user input, while f-strings format currency and mask private account numbers.

**Banking Example:**
```python
def mask_account_number(acc_num: str) -> str:
    if not acc_num or len(acc_num) < 4:
        return "N/A"
    return f"ACC-****{acc_num[-3:]}"

formatted_balance = f"${balance:,.2f}"  # Output: "$12,450.00"
```
**Project Reference:** [utils.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/utils.py#L54-L95) (`format_currency`, `mask_account_number`)

---

### 7. Exception Handling (`try` and `except`)
Defensive programming catches conversion and runtime exceptions without halting the server process.

**Banking Example:**
```python
def safe_float(value: any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
```
**Project Reference:** [utils.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/utils.py#L26-L52) (`safe_int`, `safe_float`), [routes.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/routes.py#L1270-L1305)

---

### 8. Comparison and Logical Operators
Comparison (`==`, `!=`, `<`, `>`, `<=`, `>=`) and Boolean operators (`and`, `or`, `not`) validate complex business conditions.

**Banking Example:**
```python
if account["status"] == "Active" and not account["is_frozen"] and balance >= transfer_amount:
    allow_transfer = True
else:
    allow_transfer = False
```
**Project Reference:** [services.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/services.py#L140-L200) (`transfer_money`, `is_account_active`)

---

### 9. Modules and Package Imports
Modular code structure uses `from package.module import symbol` to maintain separation between database layers, business controllers, and utility helpers.

**Banking Example:**
```python
from app.models import CUSTOMERS_DB
from app.services import get_customer_by_id
from app.utils import format_currency
```
**Project Reference:** [routes.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/routes.py#L22-L88)

---

### 10. Type Hints & Annotations
Type annotations document expectations for parameters and return types, improving editor autocompletion and static analysis.

**Banking Example:**
```python
def get_customer_by_id(customer_id: int) -> dict | None:
    for c in CUSTOMERS_DB:
        if c.get("customer_id") == customer_id:
            return c
    return None
```
**Project Reference:** [services.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/services.py#L40-L90), [auth.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/auth.py#L40-L70)

---

### 11. Project Structure & Separation of Concerns
The application follows clean architectural layering:
- `models.py`: State storage & schemas.
- `services.py`: Banking rules & domain calculations.
- `routes.py`: HTTP controller dispatch & template rendering.
- `auth.py`: Cryptographic credentials & session control.
- `utils.py`: General sanitizers & formatters.

---

### 12. Flask Fundamentals
- **Blueprints:** Modular dispatch (`main_bp = Blueprint("main", __name__)`).
- **Requests & Methods:** Handling `request.method == "POST"` vs `request.method == "GET"`.
- **Sessions:** Cryptographic signed client cookie sessions storing `session["customer_id"]` and `session["role"]`.
- **Jinja2 Templates:** Template inheritance, loops (`{% for %}`), conditionals (`{% if %}`), and filters.
- **Custom Error Handlers:** Clean recovery pages for HTTP 404, 403, and 500 status codes.

**Banking Example:**
```python
@main_bp.route("/deposit", methods=["GET", "POST"])
@customer_login_required
def deposit():
    customer_id = session.get("customer_id")
    if request.method == "POST":
        amount = request.form.get("amount")
        success, msg, _ = deposit_money(customer_id, amount)
        if success:
            flash(msg, "success")
            return redirect(url_for("main.customer_dashboard"))
    return render_template("deposit.html")
```
**Project Reference:** [routes.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/routes.py#L412-L445)

---

### 13. Authentication & Authorization
- **Password Hashing:** Passwords hashed using PBKDF2/scrypt (`generate_password_hash`, `check_password_hash`).
- **Decorators (`functools.wraps`):** Role-based access control gates:
  - `@customer_login_required`
  - `@admin_login_required`
- **Brute Force Protection:** IP/email cooldown timer tracking consecutive failed attempts in `LOGIN_ATTEMPTS`.

**Banking Example:**
```python
def customer_login_required(view_func):
    @wraps(view_func)
    def decorated_view(*args, **kwargs):
        if not (session.get("customer_id") and session.get("role") == "customer"):
            flash("Please sign in to access your banking portal.", "warning")
            return redirect(url_for("main.customer_login"))
        return view_func(*args, **kwargs)
    return decorated_view
```
**Project Reference:** [auth.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/auth.py#L358-L386)

---

### 14. Data Models & Service-Layer Business Logic
Transactions must be atomic: if any step of a transfer fails (e.g. sender balance insufficient or recipient account frozen), neither balance is altered, ensuring ledger integrity.

**Banking Example:**
```python
# Atomic transfer logic
sender["balance"] -= amount
recipient["balance"] += amount
log_transaction("Transfer (Debit)", sender_id, -amount)
log_transaction("Transfer (Credit)", recipient_id, amount)
```
**Project Reference:** [services.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/services.py#L140-L210) (`transfer_money`)

---

### 15. Automated Testing
Python's built-in `unittest` module provides test discovery, isolated test environments via `setUp()`, and comprehensive assertions (`assertEqual`, `assertTrue`, `assertIn`).

**Banking Example:**
```python
class TestBanking(unittest.TestCase):
    def setUp(self):
        reset_customers_db()
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()

    def test_deposit(self):
        resp = self.client.post("/deposit", data={"amount": "200.00"})
        self.assertEqual(resp.status_code, 200)
```
**Project Reference:** [tests/test_basic.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/tests/test_basic.py), [tests/test_phase8.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/tests/test_phase8.py)

---

### 16. Virtual Environments & Dependencies
Isolated Python runtime prevents dependency version conflicts across projects:
```bash
python -m venv venv
venv\Scripts\activate    # Windows
source venv/bin/activate # Unix
pip install -r requirements.txt
```
**Project Reference:** [requirements.txt](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/requirements.txt)

---

### 17. Application Security & Validation
- **CSRF Defense:** Cryptographic token `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` validated on every POST request.
- **OWASP CSV Injection Defense:** Leading characters (`=`, `+`, `-`, `@`) prepended with `'` during export to prevent remote spreadsheet code execution.
- **Generic Error Responses:** Prevent account enumeration by returning `"Invalid email or password."` regardless of whether the email or password was wrong.

**Project Reference:** [utils.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/utils.py#L380-L460), [routes.py](file:///c:/Users/HP/OneDrive/Desktop/banking%20SaaS/bank_management/app/routes.py#L1100-L1250)
