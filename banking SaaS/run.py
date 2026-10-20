"""
Root Launcher for Bank Management Software.
Allows running the project directly from the workspace root directory:
    python run.py
"""
import sys
import os

# Add bank_management directory to sys.path
bank_mgmt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bank_management")
sys.path.insert(0, bank_mgmt_path)

from app import create_app

app = create_app()

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  [BANK] CORE BANKING SYSTEM")
    print("  Running from workspace root: http://127.0.0.1:5000")
    print("=" * 65 + "\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
