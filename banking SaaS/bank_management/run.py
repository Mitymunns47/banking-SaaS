"""
run.py
=============================================================================
Application Entry Point for Bank Management Software (Phase 1)
=============================================================================

PYTHON FUNDAMENTALS DEMONSTRATED IN THIS FILE:
1. `if __name__ == "__main__":` idiom:
   - Ensures code only runs when this script is executed directly from the terminal,
     and not when imported as a module into another file.

2. Importing from custom packages:
   - Pulling `create_app()` from the local `app` directory.

HOW TO RUN:
   python run.py
   or
   flask --app run.py run
"""

import sys
import os

# Ensure the bank_management directory is on Python's module search path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

# Instantiate Flask application using the factory function
app = create_app()

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  [BANK] CORE BANKING SYSTEM")
    print("  Server is starting...")
    print("  Access the application at: http://127.0.0.1:5000")
    print("=" * 65 + "\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
