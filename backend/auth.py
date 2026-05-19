from passlib.context import CryptContext

from backend.database import SessionLocal, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def register_user(username: str, email: str, password: str) -> tuple[bool, str]:
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            return False, "Email already exists"

        new_user = User(
            username=username,
            email=email,
            password_hash=pwd_context.hash(password),
        )
        db.add(new_user)
        db.commit()
        return True, "Registration successful"
    finally:
        db.close()


def login_user(email: str, password: str) -> tuple[bool, User | None]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return False, None
        if not pwd_context.verify(password, user.password_hash):
            return False, None
        if hasattr(user, "is_active") and not user.is_active:
            return False, None
        return True, user
    finally:
        db.close()