import joblib
import re
import numpy as np
from urllib.parse import urlparse
from backend.preprocess import clean_email as clean_text
from backend.config import get_allowlist_mode, get_threshold, get_trusted_sender_threshold
from backend.policy import is_trusted_sender, extract_email_address

model_enhanced = joblib.load("model/phishing_model_enhanced.pkl")
vectorizer_enhanced = joblib.load("model/tfidf_vectorizer_enhanced.pkl")
feature_metadata = joblib.load("model/feature_metadata_enhanced.pkl")

def extract_urls(text):
    if not text: return []
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, str(text))

def count_urls(text):
    return len(extract_urls(text))

def has_suspicious_url(text):
    urls = extract_urls(text)
    suspicious_patterns = [
        r'bit\.ly', r'tinyurl', r'shorturl', r'goo\.gl',
        r'amazonaws\.com', r'azurewebsites\.net',
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',
        r'\.(tk|ml|ga|cf|gq|xyz|top|pw|loan|bid|date|win|icu|buzz)$',
        r'(login|verify|account|secure|update|banking|paypal|amazon|signin|password).*\.',
    ]
    for url in urls:
        for pattern in suspicious_patterns:
            if re.search(pattern, url.lower()): return 1
    return 0

def predict_email_enhanced(subject: str | None, body: str | None, sender: str | None = None) -> dict:
    raw_text = f"{subject or ''}\n{body or ''}".strip()
    cleaned_text = clean_text(raw_text)
    X_text_tfidf = vectorizer_enhanced.transform([cleaned_text]).toarray()

    url_count = count_urls(raw_text)
    has_susp = has_suspicious_url(raw_text)
    expected_engineered = feature_metadata.get('engineered_features', [])

    if expected_engineered:
        email_length = len(raw_text)
        char_count_uppercase = sum(1 for c in raw_text if c.isupper())
        exclamation_count = raw_text.count('!')
        question_count = raw_text.count('?')

        feat_map = {
            'url_count': url_count,
            'has_suspicious_url': has_susp,
            'email_length': email_length,
            'char_count_uppercase': char_count_uppercase,
            'exclamation_count': exclamation_count,
            'question_count': question_count
        }

        engineered_vals = np.array([[feat_map[f] for f in expected_engineered]])
        X_combined = np.hstack([X_text_tfidf, engineered_vals])
        proba = model_enhanced.predict_proba(X_combined)[0]
    else:
        proba = model_enhanced.predict_proba(X_text_tfidf)[0]

    phishing_proba = float(proba[1])

    # HEURISTIC ADJUSTMENTS (Strict for high personal accuracy)
    if url_count == 0:
        phishing_proba *= 0.2
    
    trusted = is_trusted_sender(sender)
    if trusted:
        phishing_proba *= 0.5

    if has_susp:
        phishing_proba = min(0.99, phishing_proba + 0.4)
    elif url_count > 5:
        phishing_proba = min(0.99, phishing_proba + 0.15)

    threshold = get_threshold()
    trusted = is_trusted_sender(sender)
    allowlist_mode = get_allowlist_mode()
    trusted_threshold = get_trusted_sender_threshold()

    if trusted and allowlist_mode == "smart":
        threshold = max(threshold, trusted_threshold) if allowlist_mode == "raise_threshold" else threshold

    if phishing_proba >= threshold:
        label, folder = "Phishing", "spam"
    else:
        label, folder = "Legitimate", "inbox"

    if trusted and allowlist_mode == "override":
        label, folder = "Legitimate", "inbox"

    return {
        "label": label,
        "folder": folder,
        "phishing_probability": phishing_proba,
        "risk_score": f"{round(phishing_proba * 100, 2)}%",
        "threshold": threshold,
        "trusted_sender": trusted,
        "model_type": "enhanced_rf",
        "url_count": url_count,
        "has_suspicious_url": bool(has_susp),
    }


def compare_predictions(subject: str | None, body: str | None, sender: str | None = None) -> dict:
    """
    Compare original model vs enhanced model predictions.
    Useful for testing/validation.
    """
    from backend.predictor import predict_email

    original_result = predict_email(subject, body, sender=sender)
    enhanced_result = predict_email_enhanced(subject, body, sender=sender)

    return {
        "original": original_result,
        "enhanced": enhanced_result,
        "agreement": original_result["label"] == enhanced_result["label"],
        "original_score": original_result["phishing_probability"],
        "enhanced_score": enhanced_result["phishing_probability"],
    }
