import os
import socket

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import uvicorn

from database.db import SessionLocal, Email, Account
from backend.predictor import predict_email
from xai.explain import explain_email
from backend.email_receiver import EmailFetcher

app = FastAPI(title="PhishGuard API")

@app.get("/")
def read_root():
    return {"status": "online", "message": "PhishGuard API is running"}

# Enable CORS for React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from pydantic import BaseModel

class AccountCreate(BaseModel):
    email: str
    password: str
    imap_server: str = "imap.gmail.com"
    name: str | None = None

@app.get("/accounts")
def get_accounts(db: Session = Depends(get_db)):
    from backend.config import get_all_configured_accounts
    return get_all_configured_accounts()

@app.post("/accounts")
def add_account(account: AccountCreate, db: Session = Depends(get_db)):
    db_account = Account(
        email=account.email.strip().lower(),
        password=account.password,
        imap_server=account.imap_server,
        name=account.name or account.email
    )
    db.add(db_account)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Account already exists or error: {str(e)}")
    return {"status": "success"}

@app.get("/emails")
def get_emails(account: str = "All Accounts", folder: str = "all", db: Session = Depends(get_db)):
    query = db.query(Email)
    if account != "All Accounts":
        query = query.filter(Email.receiver == account.strip().lower())
    
    if folder == "inbox":
        query = query.filter(Email.prediction == "Legitimate")
    elif folder == "spam":
        query = query.filter(Email.prediction == "Phishing")
        
    emails = query.order_by(Email.timestamp.desc()).all()
    return emails

@app.delete("/accounts/{email}")
def delete_account(email: str, db: Session = Depends(get_db)):
    db_account = db.query(Account).filter(Account.email == email.strip().lower()).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found in database")
    db.delete(db_account)
    db.commit()
    return {"status": "success"}

@app.get("/explain/{email_id}")
def get_explanation(email_id: int, db: Session = Depends(get_db)):
    email_obj = db.query(Email).filter(Email.id == email_id).first()
    if not email_obj:
        raise HTTPException(status_code=404, detail="Email not found")
    
    exp = explain_email(
        email_obj.subject,
        email_obj.body,
        sender=email_obj.sender,
        prediction=email_obj.prediction,  # "Phishing" or "Legitimate"
    )
    return exp

@app.get("/stats")
def get_stats(account: str = "All Accounts", db: Session = Depends(get_db)):
    # Force 'All Accounts' if the string is literally that or empty
    is_all = not account or account == "All Accounts" or account == "undefined"
    
    query = db.query(Email)
    if not is_all:
        query = query.filter(Email.receiver == account.strip().lower())
    
    total = query.count()
    phishing = query.filter(Email.prediction == "Phishing").count()
    legitimate = query.filter(Email.prediction == "Legitimate").count()
    
    res = {
        "total": total,
        "phishing": phishing,
        "legitimate": legitimate,
        "phishing_percent": round((phishing / total * 100), 1) if total > 0 else 0
    }
    print(f"DEBUG: Stats for '{account}' (is_all={is_all}): {res}")
    return res

@app.post("/fetch")
def fetch_emails(db: Session = Depends(get_db)):
    from backend.config import get_all_configured_accounts
    accounts = get_all_configured_accounts()
    success_count = 0
    errors = []
    for acc in accounts:
        try:
            fetcher = EmailFetcher(acc["email"], acc["password"], acc.get("imap_server", "imap.gmail.com"))
            fetcher.fetch_and_scan(limit=500)
            success_count += 1
        except Exception as e:
            errors.append(f"{acc['email']}: {str(e)}")
    
    if errors and success_count == 0:
        raise HTTPException(status_code=500, detail="; ".join(errors))
    return {"status": "success", "fetched_accounts": success_count, "errors": errors}

@app.post("/reclassify")
def reclassify_all(db: Session = Depends(get_db)):
    emails = db.query(Email).all()
    count = 0
    for e in emails:
        # Re-run prediction with latest logic
        res = predict_email(e.subject, e.body, sender=e.sender)
        e.prediction = res["label"]
        e.risk_score = res["risk_score"]
        e.folder = res["folder"]
        count += 1
    db.commit()
    return {"status": "success", "count": count}

def is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


class PasteAnalysisRequest(BaseModel):
    subject: str
    body: str
    sender: str

@app.post("/analyze-paste")
async def analyze_paste(request: PasteAnalysisRequest):
    try:
        prediction = predict_email(request.subject, request.body, sender=request.sender)
        # Create a dummy email object for the explainer
        explanation = explain_email(request.subject, request.body, sender=request.sender, prediction=prediction["label"])
        return {
            "prediction": prediction,
            "explanation": explanation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/emails/{email_id}")
async def delete_email(email_id: int, db: Session = Depends(get_db)):
    email_obj = db.query(Email).filter(Email.id == email_id).first()
    if not email_obj:
        raise HTTPException(status_code=404, detail="Email not found")
    db.delete(email_obj)
    db.commit()
    return {"status": "success"}

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    start_port = int(os.getenv("PORT", "8000"))
    if start_port == 8000:
        ports_to_try = [8000, 8001, 8002, 8003]
    else:
        ports_to_try = [start_port, 8000, 8001, 8002]

    for port in ports_to_try:
        if not is_port_available(host, port):
            print(f"Port {port} is already in use; trying next port...")
            continue

        print(f"Starting PhishGuard API on {host}:{port}")
        uvicorn.run(app, host=host, port=port)
        break
    else:
        raise RuntimeError(f"Could not bind to any port in {ports_to_try}")
