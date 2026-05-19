from backend.database import SessionLocal, Email
from backend.predictor import predict_email

def reclassify_all_emails():
    db = SessionLocal()
    emails = db.query(Email).all()
    
    total = len(emails)
    updated_count = 0
    phishing_count = 0
    safe_count = 0
    
    for e in emails:
        # Re-run prediction with current logic
        res = predict_email(e.subject, e.body, sender=e.sender)
        
        # Force update fields regardless of previous state to ensure synchronization
        e.prediction = res['label']
        e.risk_score = res['risk_score']
        e.folder = res['folder']
        
        if res['label'] == "Phishing":
            phishing_count += 1
        else:
            safe_count += 1
            
        updated_count += 1
            
    db.commit()
    db.close()
    print(f"Processed {total} emails. Current status: {phishing_count} Phishing, {safe_count} Safe.")

if __name__ == "__main__":
    reclassify_all_emails()
