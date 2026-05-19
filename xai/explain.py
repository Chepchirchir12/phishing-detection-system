import numpy as np
import joblib
from backend.preprocess import clean_email
from backend.policy import extract_link_domains, is_trusted_sender, extract_email_address

# Load the basic model for clean linear weights (logistic regression)
try:
    model = joblib.load("model/phishing_model.pkl")
    vectorizer = joblib.load("model/tfidf_vectorizer.pkl")
except Exception:
    # Fallback to empty/dummy if not found
    model = None
    vectorizer = None

# Minimum absolute contribution a token must have to be surfaced in explanations.
# This prevents near-zero-weight common words from appearing as "risk factors".
MIN_CONTRIBUTION_THRESHOLD = 0.005 # Increased slightly for better filtering


def explain_email(
    subject: str | None,
    body: str | None,
    sender: str | None = None,
    top_k: int = 12,
    prediction: str | None = None,  # "Phishing" or "Legitimate" (from stored DB value)
) -> dict:
    text = f"{subject or ''}\n{body or ''}".strip()
    # Keep URLs for explanation to allow tokens like 'http' to be surfaced if relevant
    cleaned = clean_email(text, strip_urls=False)
    
    if not model or not vectorizer:
        return {
            "top_positive": [],
            "top_negative": [],
            "summary": "AI model files missing; explanation unavailable.",
            "verdict_context": "Prediction engine unavailable.",
            "is_phishing": False,
        }

    X = vectorizer.transform([cleaned])

    # ── Compute per-token contributions ───────────────────────────────────────
    if hasattr(model, 'coef_'):
        # Logistic Regression / Linear SVC — clean linear weights
        coef = model.coef_[0]
        contrib = X.toarray()[0] * coef
    elif hasattr(model, 'feature_importances_'):
        # RandomForest — use feature importances * tfidf presence
        importances = model.feature_importances_
        num_tfidf = X.shape[1]
        contrib = X.toarray()[0] * importances[:num_tfidf]
    else:
        # Check if it's a CalibratedClassifierCV
        if hasattr(model, 'base_estimator') and hasattr(model.base_estimator, 'coef_'):
             coef = model.base_estimator.coef_[0]
             contrib = X.toarray()[0] * coef
        else:
             contrib = np.zeros(X.shape[1])

    feature_names = np.array(vectorizer.get_feature_names_out())

    # Common header/metadata/newsletter tokens that are never meaningful as risk signals
    ignore_keywords = {
        'pm', 'subject', 'date', 're', 'fw', 'to', 'from', 'original',
        'message', 'sent', 'received', 'email', 'mail', 'http', 'https',
        'com', 'www', 'org', 'net', 'unsubscribe', 'list', 'top', 'view',
        'browser', 'privacy', 'policy', 'rights', 'reserved', 'copyright',
        'click', 'here', 'link', 'please', 'thanks', 'best', 'regards',
        'hi', 'hello', 'dear', 'team', 'support', 'contact', 'questions',
    }

    pos_idx = np.argsort(contrib)[::-1]   # highest → most phishing-like
    neg_idx = np.argsort(contrib)          # lowest  → most legitimate-like

    def build(indices, want_positive: bool):
        items = []
        for i in indices:
            token = str(feature_names[i])
            if token.lower() in ignore_keywords:
                continue
            score = float(contrib[i])
            # Respect sign direction and minimum threshold
            if want_positive and (score <= MIN_CONTRIBUTION_THRESHOLD):
                break
            if not want_positive and (score >= -MIN_CONTRIBUTION_THRESHOLD):
                break
            if len(items) >= top_k:
                break
            items.append({"token": token, "contribution": score})
        return items

    top_positive = build(pos_idx, want_positive=True)   # phishing indicators
    top_negative = build(neg_idx, want_positive=False)  # legitimate indicators

    # ── Determine effective classification ────────────────────────────────────
    # Use the stored prediction if provided; fall back to contribution sum heuristic
    if prediction:
        is_phishing = prediction.strip().lower() == "phishing"
    else:
        # Heuristic if no prediction is passed: sum of linear contributions
        is_phishing = contrib.sum() > 0.1

    # ── Build human-readable reasons ──────────────────────────────────────────
    reasons = []

    # 1. Content pattern message — phrased according to actual classification
    if is_phishing:
        if top_positive:
            suspicious_tokens = [item["token"] for item in top_positive[:3]]
            reasons.append(
                f"Suspicious content patterns were detected: {', '.join(suspicious_tokens)}."
            )
        else:
            reasons.append(
                "The email's overall content pattern is characteristic of phishing messages."
            )
    else:
        if top_negative:
            safe_tokens = [item["token"] for item in top_negative[:3]]
            reasons.append(
                f"The content is consistent with legitimate email (key safe signals: {', '.join(safe_tokens)})."
            )
        else:
            reasons.append(
                "The email's content did not match known phishing patterns."
            )

    # 2. Sender & link analysis
    sender_addr = extract_email_address(sender)
    links = extract_link_domains(body)

    if sender_addr:
        is_trusted = is_trusted_sender(sender)
        sender_domain = sender_addr.split("@", 1)[-1].lower()
        sender_parts = sender_domain.split(".")
        base_domain = ".".join(sender_parts[-2:]) if len(sender_parts) >= 2 else sender_domain

        if is_trusted:
            reasons.append(f"The sender ({sender_addr}) is in your trusted senders list.")

        if links:
            mismatched_links = []
            for link in links:
                link_lower = link.lower()
                link_parts = link_lower.split(".")
                link_base = ".".join(link_parts[-2:]) if len(link_parts) >= 2 else link_lower

                is_same_domain = (
                    link_lower == base_domain
                    or link_lower.endswith(f".{base_domain}")
                    or link_base == base_domain
                )
                
                # Check against the expanded reputable domains
                is_reputable = any(
                    link_lower == d or link_lower.endswith(f".{d}") 
                    for d in {
                        'google.com', 'amazon.com', 'microsoft.com', 'netflix.com', 'apple.com',
                        'paypal.com', 'github.com', 'linkedin.com', 'facebook.com', 'dropbox.com',
                        'slack.com', 'zoom.us', 'notion.so', 'stripe.com', 'shopify.com',
                        'intercom.com', 'micro1.ai', 'greenhouse.io', 'lever.co', 'workday.com'
                    }
                )
                if not is_same_domain and not is_reputable:
                    mismatched_links.append(link)

            if mismatched_links and is_phishing:
                reasons.append(
                    f"Links in this email point to external domains "
                    f"({', '.join(mismatched_links[:2])}) that do not match the sender's domain ({base_domain})."
                )
            elif not mismatched_links:
                reasons.append("All links in the email point to the sender's own domain or verified reputable domains.")
            elif not is_phishing:
                # Safe email with external links (common for newsletters etc.)
                reasons.append(
                    f"The links in this email (e.g., {', '.join(mismatched_links[:2])}) are consistent with those found in legitimate service and marketing communications."
                )

    # 3. Verdict context — phrase according to actual classification
    if is_phishing:
        verdict_context = (
            "This email was classified as Phishing. "
            "Exercise caution — do not click links or provide personal information."
        )
    else:
        verdict_context = (
            "This email was classified as Safe. "
            "The content, sender, and links appear consistent with legitimate communication."
        )

    return {
        "top_positive": top_positive,
        "top_negative": top_negative,
        "summary": " ".join(reasons),
        "verdict_context": verdict_context,
        "is_phishing": is_phishing,
    }
