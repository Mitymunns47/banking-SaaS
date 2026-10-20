# CORE BANKING SYSTEM

A clean, modular, professional, and beginner-friendly web-based core banking application built with Python and Flask. Designed for comprehensive educational demonstration, code inspection, and architectural clarity.

---

## 🏛️ Project Overview & Educational Scope

The **CORE BANKING SYSTEM** is an educational simulation that models the architecture and operational workflows of modern commercial and retail banking institutions. It delivers a full suite of customer-facing portals and back-office administrative management tools without external paid dependencies or cloud database configurations.

> [!NOTE]
> **Educational Demonstration Scope:**
> This application uses a structured in-memory data store for fast startup, deterministic testing, and clean inspection. Records persist during runtime but reset upon application restart. All monetary transactions, loans, and cheque issuances are simulated logic and do not represent real-world bank transfers or legal financial instruments.

---

## 🚀 Key Features

### 👤 Customer Features
- **Account Registration & Login:** Safe registration with age validation, duplicate email prevention, and default `Pending` status.
- **Account Dashboard:** Overview of account number, balance, customer tier, and active operational status notices.
- **Deposits (`/deposit`):** Add funds to verified active accounts with real-time ledger updates.
- **Withdrawals (`/withdraw`):** Debit available funds with strict balance sufficiency validation.
- **Inter-Account Transfers (`/transfer`):** Atomic ledger transfers verifying recipient existence, preventing self-transfers, and generating paired debit/credit records.
- **Transaction History (`/transactions`):** Private statement view displaying deposits, withdrawals, and transfers with reference numbers and timestamps.
- **Loan Applications (`/loans/apply`):** Apply for Personal, Education, Home, or Business facilities with income declarations and reducing-balance EMI calculations.
- **Cheque Book Ordering (`/cheques/request`):** Order 10, 25, or 50 leaf personalized chequebooks with masked account numbers (`ACC-****941`).
- **Profile & Security (`/change-password`):** Change password with current credential validation and session invalidation upon sign-out (`/logout`).

### 🛡️ Administrator Features
- **Executive Console (`/admin/dashboard`):** 6 real-time metrics (*Total Customers*, *Active Accounts*, *Pending Accounts*, *Frozen Accounts*, *Closed Accounts*, *Total Transactions*).
- **Customer Management (`/admin/customers`):** Full customer directory with search by ID, name, email, or account number, plus status filters.
- **Account Lifecycle Operations:**
  - *Approve / Reject:* Evaluate initial customer registrations.
  - *Freeze / Unfreeze:* Restrict debits and transfers without altering balances or deleting history.
  - *Close Account:* Safely retire customer accounts while maintaining audit records.
- **Transaction Audit Ledger (`/admin/transactions`):** System-wide transaction log with type filtering (*Deposit*, *Withdrawal*, *Transfer*).
- **Loan Underwriting Console (`/admin/loans`):** Review applications, determine approved amounts and interest rates, or record rejection rationales.
- **Cheque Requisition Management (`/admin/cheques`):** Approve, dispatch, complete, or reject cheque requests with state transition validation.
- **Operational Reporting (`/admin/reports`):** Aggregated metrics with date-range filters, printable executive summaries (`/admin/reports/print`), and OWASP-sanitized CSV exports (`/admin/reports/export/<dataset>`).
- **Administrative Audit Trail (`/admin/audit-logs`):** Immutable chronological record of administrative security and financial decisions.

---

## 🛠️ Technology Stack

- **Backend:** Python 3.10+
- **Web Framework:** Flask (Blueprints, Request Context, Jinja2 Templates, Client Sessions)
- **Security:** Werkzeug Cryptography (`generate_password_hash`, `check_password_hash`), Cryptographic CSRF Tokens (`secrets.token_hex`), Rate Limiting Cooldowns
- **Frontend:** Vanilla HTML5, Vanilla CSS3 (Custom Responsive Design System, Light Palette with Navy/Dark-Blue Accents), Minimal Vanilla JavaScript
- **Testing:** Python Standard Library `unittest` (153 Automated Unit & Integration Tests)

---

## 📁 Project Directory Structure

```text
bank_management/
│
├── app/
│   ├── __init__.py        # Flask application factory, session cookie config, CSRF context processor
│   ├── routes.py          # Modular HTTP controllers (public, auth, banking, admin, reports, errors)
│   ├── models.py          # In-memory customer DB, ledger stores, loans, cheques, audit trail, seed records
│   ├── services.py        # Core banking business logic, atomic transfers, EMI calculator, CSV exports
│   ├── auth.py            # Authentication, PBKDF2/scrypt password hashing, session decorators, rate limiting
│   └── utils.py           # Defensive type converters, validations, currency formatting, CSRF generation
│
├── templates/
│   ├── index.html         # Public landing page with portal overviews
│   ├── customers.html     # Customer public directory with search
│   ├── customer_details.html  # Public customer preview card
│   ├── register.html      # Customer registration form with input validation
│   ├── login.html         # Customer sign-in portal with demo credentials
│   ├── admin_login.html   # Staff admin authentication portal with distinct security theme
│   ├── dashboard.html     # Customer account overview with balances and quick action bar
│   ├── admin_dashboard.html # Admin executive console with 6 summary cards and sidebar navigation
│   ├── admin_customers.html # Staff customer management, search, and lifecycle action buttons
│   ├── admin_customer_details.html # Comprehensive admin customer profile and transaction history
│   ├── admin_accounts.html  # Master accounts registry view
│   ├── admin_transactions.html # Transaction audit table with type filter
│   ├── admin_placeholder.html  # Fallback template for developmental views
│   ├── change_password.html # Customer password update form
│   ├── deposit.html       # Deposit funds form with balance check
│   ├── withdraw.html      # Withdraw funds form with overdraft prevention
│   ├── transfer.html      # Inter-account money transfer form with account validation
│   ├── transactions.html  # Customer account transaction statement
│   ├── customer_loans.html # Customer loan portfolio and application status
│   ├── loan_apply.html    # Customer loan application form with tenure and purpose
│   ├── loan_details.html  # Customer loan specifications and EMI breakdown
│   ├── customer_cheques.html # Customer cheque book request history & masked account numbers
│   ├── cheque_request.html # Customer cheque book ordering form
│   ├── admin_loans.html   # Admin loan portfolio overview and underwriting summary cards
│   ├── admin_loan_details.html # Admin loan underwriting, approval, and rejection
│   ├── admin_cheques.html # Admin cheque requests console with 5 summary cards
│   ├── admin_reports.html # Admin comprehensive reports console with date filtering
│   ├── admin_reports_print.html # Printable & browser-native PDF executive report view
│   ├── admin_audit_logs.html # Administrative immutable audit trail viewer
│   └── error.html         # Friendly custom error page for 404, 403, and 500 status codes
│
├── static/
│   └── style.css          # Bank UI stylesheet: customer portal, admin sidebar, badges, print layout
│
├── tests/
│   ├── test_basic.py      # Customer creation, retrieval, and validation tests
│   ├── test_auth.py       # Authentication, session, role access, and lockout tests
│   ├── test_banking.py    # Deposit, withdrawal, transfer, statement, and security tests
│   ├── test_admin.py      # Admin dashboard, search, approval, freeze, closure & audit tests
│   ├── test_loans.py      # Loan application, reducing-balance EMI, underwriting & privacy tests
│   ├── test_cheques.py    # Cheque book request, workflow transitions, underwriting & security tests
│   ├── test_reports.py    # Comprehensive reporting, date filters, CSV injection defense, password hashing & audit trail tests
│   └── test_phase8.py     # Final phase verification: 404/403/500 error pages, CSRF token forms, full workflows
│
├── .env.example           # Environment variable configuration template
├── requirements.txt       # Dependencies (Flask, pytest)
└── run.py                 # Application entry point
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites
- Python 3.10 or later installed on your system.
- Git (optional, for cloning).

### 2. Virtual Environment Setup

**On Windows (PowerShell):**
```powershell
# Navigate into the project folder
cd "bank_management"

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
venv\Scripts\Activate.ps1
```

**On macOS / Linux:**
```bash
cd bank_management
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` or set environment variables in your terminal:
```bash
# Optional: Set custom development secret key
set SECRET_KEY="my-custom-dev-secret-key"
```

---

## 🚀 Running the Application

Start the Flask development server using:
```bash
python run.py
```

The application will start and listen locally:
- **Local URL:** [http://127.0.0.1:5000](http://127.0.0.1:5000)

Open your web browser and navigate to `http://127.0.0.1:5000` to access the Core Banking System.

---

## 🧪 Automated Testing

The project includes an automated test suite containing **153 unit and integration tests** verifying all customer and administrative workflows.

Run all automated tests:
```bash
python -m unittest discover tests
```

Expected output:
```text
Ran 153 tests in ~16s
OK
```

Run a specific test module:
```bash
python -m unittest tests.test_phase8 -v
```

---

## 🔐 Authentication, RBAC & Security

### 1. Role-Based Access Control (RBAC)
- **Customer Role:** Verified via `session["customer_id"]` and `session["role"] == "customer"`. Guarded by `@customer_login_required`.
- **Administrator Role:** Verified via `session["admin_logged_in"]` and `session["role"] == "admin"`. Guarded by `@admin_login_required`.
- Cross-portal unauthorized access triggers an immediate safe HTTP 302 redirection to the respective sign-in portal.

### 2. Cryptographic Password Hashing
- Stored credentials use `werkzeug.security.generate_password_hash` with secure salting.
- Plaintext passwords are never persisted on registration or updates.
- Seed records undergo transparent cryptographic migration upon initial authentication.

### 3. CSRF Protection
- Cryptographically secure 64-character tokens generated via Python `secrets.token_hex(32)`.
- Embedded as hidden fields `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` across all state-changing forms.
- Validated via `validate_csrf_token()` prior to processing state-changing requests.

### 4. Brute-Force & Anti-Enumeration Defense
- Failed login attempts are recorded by identifier.
- 3 consecutive failures initiate an automated 60-second cooldown period.
- Constant-time generic error messaging prevents username and email harvesting.

### 5. OWASP CSV Formula Injection Mitigation
- Exported spreadsheet values starting with `=`, `+`, `-`, `@`, `\t`, or `\r` are prefixed with a single quotation mark (`'`).
- Prevents malicious command execution when exported files are opened in Microsoft Excel or Google Sheets.

---

## 🔑 Demo Credentials

### Customer Portal
- **URL:** [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login)
- **Active Account:** `sarah.jenkins@bankcorp.com` | `Password123`
- **Pending Account:** `elena.rostova@biolabs.org` | `Password123`
- **Frozen Account:** `thomas.sterling@capitalgroup.com` | `Password123`
- *(Or register any new customer at `/register`)*

### Administrator Portal
- **URL:** [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login)
- **Username:** `admin` (or `admin@bankcorp.com`)
- **Password:** `AdminPassword123`

---

## 📋 Architectural File Roles

| Module | Purpose & Separation of Concerns |
| :--- | :--- |
| `app/routes.py` | HTTP controller routing, request parsing, session verification, template dispatching, and custom error handlers (`404`, `403`, `500`). |
| `app/models.py` | In-memory data repositories (`CUSTOMERS_DB`, `TRANSACTIONS_DB`, `LOANS_DB`, `CHEQUE_REQUESTS_DB`, `AUDIT_LOG_DB`), seed data generators, and reset functions. |
| `app/services.py` | Pure banking business logic: atomic transfers, deposit/withdrawal validation, reducing-balance EMI mathematics, and CSV dataset compilation. |
| `app/auth.py` | Credential hashing, authentication verification, session decorators, rate limiting, and customer password modification. |
| `app/utils.py` | Defensive data type parsers (`safe_int`, `safe_float`), string formatters (`format_currency`, `mask_account_number`), CSRF token generators, and OWASP CSV sanitizers. |

---

## ⚠️ Known Limitations & Educational Scope

1. **In-Memory Volatility:** Application state is held in Python memory data structures. Changes made during a session reset to initial seed data when the server restarts.
2. **Simulated Financial Transactions:** Deposits, withdrawals, transfers, and loans are internal software calculations. No live connections exist to SWIFT, ACH, payment gateways, or real banking rails.
3. **Multi-Process Concurrency:** Because storage is in-memory Python structures, running across multiple WSGI worker processes (e.g., Gunicorn multi-worker) without a shared database would cause partition isolation. For production usage, a persistent SQL database (e.g., PostgreSQL / SQLAlchemy) would replace `models.py`.
