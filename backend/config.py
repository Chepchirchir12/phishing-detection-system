import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=_ROOT / ".env")


def get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def get_threshold() -> float:
    raw = get_env("PHISHGUARD_PHISHING_THRESHOLD", "0.5")
    try:
        v = float(raw)  # type: ignore[arg-type]
    except Exception:
        return 0.5
    return min(max(v, 0.0), 1.0)


def get_gmail_credentials() -> tuple[str | None, str | None]:
    return (
        get_env("PHISHGUARD_GMAIL_EMAIL"),
        get_env("PHISHGUARD_GMAIL_APP_PASSWORD"),
    )


def get_all_configured_accounts() -> list[dict]:
    """
    Returns a list of account dicts from the database and environment variables.
    """
    from database.db import SessionLocal, Account
    
    accounts = []
    
    # 1. Load from Database
    db = SessionLocal()
    try:
        db_accounts = db.query(Account).all()
        for acc in db_accounts:
            accounts.append({
                "email": acc.email.strip().lower(),
                "password": acc.password,
                "imap_server": acc.imap_server,
                "name": acc.name or acc.email
            })
    finally:
        db.close()
    
    # 2. Check for legacy single account in .env
    email = get_env("PHISHGUARD_GMAIL_EMAIL")
    password = get_env("PHISHGUARD_GMAIL_APP_PASSWORD")
    if email and password:
        email_clean = email.strip().lower()
        # Avoid duplicates
        if not any(a["email"] == email_clean for a in accounts):
            accounts.insert(0, {
                "email": email_clean,
                "password": password,
                "imap_server": "imap.gmail.com",
                "name": f"Original ({email_clean})"
            })
    
    return accounts


def get_allowlist_mode() -> str:
    """
    - "smart": override only if sender + link domains are trusted; otherwise raise_threshold
    - "override": trusted senders are forced Legitimate
    - "raise_threshold": trusted senders must exceed a higher threshold to be Phishing
    """
    return (get_env("PHISHGUARD_ALLOWLIST_MODE", "smart") or "smart").strip().lower()


def get_trusted_sender_threshold() -> float:
    raw = get_env("PHISHGUARD_TRUSTED_SENDER_THRESHOLD", "0.9")
    try:
        v = float(raw)  # type: ignore[arg-type]
    except Exception:
        return 0.9
    return min(max(v, 0.0), 1.0)

