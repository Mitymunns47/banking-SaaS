"""
Core Banking System - Desktop Application Launcher
Bundled for standalone executable execution.
"""
import sys
import os
import time
import socket
import threading
import webbrowser

# Add appropriate paths whether running frozen (.exe) or as a script
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    bundle_dir = sys._MEIPASS
    sys.path.insert(0, bundle_dir)
    sys.path.insert(0, os.path.join(bundle_dir, "bank_management"))
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(current_dir, "bank_management"))

from app import create_app

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def find_available_port(start_port: int = 5000) -> int:
    port = start_port
    while port < 5050:
        if not is_port_in_use(port):
            return port
        port += 1
    return start_port

def launch_browser(url: str):
    time.sleep(1.2)
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not automatically open browser: {e}")

def main():
    port = 5000
    if is_port_in_use(port):
        # If 5000 is already in use by an existing instance
        port = find_available_port(5001)

    url = f"http://127.0.0.1:{port}"

    print("\n" + "=" * 68)
    print("           🏛️  CORE BANKING SYSTEM - DESKTOP APPLICATION")
    print("=" * 68)
    print(f"  Status   : Server is starting...")
    print(f"  URL      : {url}")
    print("  Browser  : Opening automatically in your default browser...")
    print("-" * 68)
    print("  DEMO CREDENTIALS:")
    print("  * Customer Portal : sarah.jenkins@bankcorp.com / Password123")
    print("  * Admin Console   : admin / AdminPassword123")
    print("-" * 68)
    print("  [NOTE] Keep this window open while using the application.")
    print("         Press CTRL + C or close this window to exit.")
    print("=" * 68 + "\n")

    # Start browser opener in background thread
    threading.Thread(target=launch_browser, args=(url,), daemon=True).start()

    app = create_app()
    # Disable debug reloader when packaged as standalone executable
    app.run(host="127.0.0.1", port=port, debug=False)

if __name__ == "__main__":
    main()
