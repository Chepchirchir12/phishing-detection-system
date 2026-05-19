import re
import joblib
from datetime import datetime

from backend.database import SessionLocal
from backend.database import Email
from backend.predictor import predict_email

# ---------------- LOAD MODEL ----------------

model = joblib.load('model/phishing_model.pkl')

vectorizer = joblib.load('model/tfidf_vectorizer.pkl')

# ---------------- SEND EMAIL ----------------

def send_email(sender, receiver, subject, body):

    db = SessionLocal()

    prediction_result = predict_email(subject, body, sender=sender)
    folder = prediction_result["folder"]
    label = prediction_result["label"]

    new_email = Email(

        sender=sender,

        receiver=receiver,

        subject=subject,

        body=body,

        prediction=label,

        folder=folder,

        risk_score=prediction_result["risk_score"],
        timestamp=datetime.utcnow(),

    )

    db.add(new_email)

    db.commit()

    db.close()

    return label