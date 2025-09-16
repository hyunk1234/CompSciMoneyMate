# backend/app.py
import os
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# ── Load .env BEFORE importing routes/mailer ─────────────────────────────
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"


def _origin_from_url(url: str) -> str | None:
    """Return scheme+host origin from a full URL, or None if invalid/empty."""
    if not url:
        return None
    try:
        p = urlparse(url)
        if p.scheme and p.netloc:
            return f"{p.scheme}://{p.netloc}"
    except Exception:
        pass
    return None


def create_app():
    app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="/")

    # ── Session / cookie defaults (safe for local dev) ───────────────────
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",     # fine for same-site (localhost)
        # SESSION_COOKIE_SECURE=True,      # enable only when serving HTTPS
    )

    # If deploying the API on a different domain than the frontend (e.g. GitHub Pages),
    # enable cross-site cookies by setting ENABLE_CROSS_SITE_COOKIES=1 in env.
    if os.getenv("ENABLE_CROSS_SITE_COOKIES") == "1":
        # Required for cookies to be sent cross-site over HTTPS
        app.config["SESSION_COOKIE_SAMESITE"] = "None"
        app.config["SESSION_COOKIE_SECURE"] = True

    # DB init
    from .database import init_app as init_db
    init_db(app)

    # ── Import blueprints AFTER env is loaded ────────────────────────────
    # Each blueprint defines its own url_prefix (e.g., /api/auth, /api/transactions, ...)
    from .routes.auth import auth_bp
    from .routes.transactions import tx_bp
    from .routes.budgets import budgets_bp
    from .routes.insights import insights_bp
    from .routes.goals import goals_bp
    from .routes.settings import settings_bp
    from .routes.notifications import notifications_bp

    # ── Register blueprints (no double-prefixing) ────────────────────────
    app.register_blueprint(auth_bp)
    app.register_blueprint(tx_bp)
    app.register_blueprint(budgets_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(notifications_bp)

    # ── CORS: allow your public frontend (GitHub Pages) to call /api/* ───
    # Set FRONTEND_URL in env, e.g. https://softwareengineeer.github.io/MoneyMate
    frontend_url = os.getenv("FRONTEND_URL", "")
    frontend_origin = _origin_from_url(frontend_url)

    cors_kwargs = {
        "supports_credentials": True,
        "resources": {r"/api/*": {"origins": [frontend_origin] if frontend_origin else []}},
    }
    # If FRONTEND_URL unset, CORS will allow nothing (tight). For quick local dev
    # you can export FRONTEND_URL=http://127.0.0.1:5000 to allow same-origin tests.
    CORS(app, **cors_kwargs)

    # ── Static / frontend (handy for local dev) ──────────────────────────
    @app.route("/", methods=["GET"])
    def root():
        return send_from_directory(str(FRONTEND_DIR), "index.html")

    @app.route("/<path:path>", methods=["GET"])
    def static_proxy(path: str):
        return send_from_directory(str(FRONTEND_DIR), path)

    # Helpful sanity print (no secrets)
    print("\n[env] FRONTEND_URL:", frontend_url)
    print("[env] FRONTEND_ORIGIN:", frontend_origin)
    print("[env] SMTP_HOST:", os.getenv("SMTP_HOST"))
    print("[env] SMTP_USERNAME:", os.getenv("SMTP_USERNAME"))
    print("[env] EMAIL_FROM:", os.getenv("EMAIL_FROM"))
    print("[env] ENABLE_CROSS_SITE_COOKIES:", os.getenv("ENABLE_CROSS_SITE_COOKIES"), "\n")

    return app


app = create_app()

if __name__ == "__main__":
    # Local dev server
    app.run(debug=True)
