"""
app/__init__.py
=============================================================================
Application Factory for CORE BANKING SYSTEM
=============================================================================

PYTHON FUNDAMENTALS DEMONSTRATED IN THIS FILE:
1. Application Factory Pattern:
   - A function `create_app()` that configures and returns a Flask instance.
   - Allows creating multiple app instances (e.g. for production, development, and unit testing).

2. Module Paths and System Interaction:
   - Using `os.path` to build platform-independent paths to templates and static assets.

3. Blueprint Registration:
   - Connecting modular routes into the main Flask application.
"""

import os
from flask import Flask


def create_app(test_config: dict | None = None) -> Flask:
    """
    Constructs and configures the Flask application.

    Parameters:
        test_config (dict | None): Optional configuration override (useful during tests).

    Returns:
        Flask: The configured Flask application object.
    """
    # Locate templates and static directories (supports PyInstaller frozen bundles)
    import sys
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundle_dir = sys._MEIPASS
        if os.path.isdir(os.path.join(bundle_dir, "templates")):
            base_dir = bundle_dir
        else:
            base_dir = os.path.join(bundle_dir, "bank_management")
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    template_dir = os.path.join(base_dir, "templates")
    static_dir = os.path.join(base_dir, "static")

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir,
    )

    # Session & Security configuration
    secret_key = os.environ.get("SECRET_KEY", "core-banking-default-dev-secret-key-educational-only")
    is_prod = os.environ.get("FLASK_ENV") == "production" or os.environ.get("ENABLE_HTTPS_COOKIES", "false").lower() == "true"

    app.config.from_mapping(
        SECRET_KEY=secret_key,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=is_prod,
    )

    # Apply test config if provided
    if test_config:
        app.config.update(test_config)

    # Context processors and template helpers
    from app.utils import generate_csrf_token
    app.jinja_env.globals["csrf_token"] = generate_csrf_token

    # Register application blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    return app
