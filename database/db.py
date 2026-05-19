import os
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///phishing.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String)
    receiver = Column(String)
    subject = Column(String)
    body = Column(String)
    prediction = Column(String)
    risk_score = Column(String)
    folder = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # robust dedupe/import tracking
    message_id = Column(String, nullable=True)
    imap_uid = Column(String, nullable=True, index=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)  # App Password
    imap_server = Column(String, default="imap.gmail.com")
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def _ensure_sqlite_columns():
    """
    Keep existing local DBs working without manual migrations.
    """
    if not DATABASE_URL.startswith("sqlite:///"):
        return
    db_path = DATABASE_URL.replace("sqlite:///", "", 1)
    if db_path != ":memory:" and not os.path.exists(db_path):
        return
    with engine.connect() as conn:
        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(emails)").fetchall()}
        if "message_id" not in cols:
            conn.exec_driver_sql("ALTER TABLE emails ADD COLUMN message_id VARCHAR")
        if "imap_uid" not in cols:
            conn.exec_driver_sql("ALTER TABLE emails ADD COLUMN imap_uid VARCHAR")


Base.metadata.create_all(bind=engine)

try:
    _ensure_sqlite_columns()
except Exception:
    pass

