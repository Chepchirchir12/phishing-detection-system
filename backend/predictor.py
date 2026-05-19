import os
import joblib
import re
import numpy as np
from backend.preprocess import clean_email
from backend.config import get_threshold, get_trusted_sender_threshold, get_allowlist_mode
from backend.policy import is_trusted_sender, are_links_trusted, extract_email_address

# Load models
try:
    model_basic = joblib.load("model/phishing_model.pkl")
    vectorizer_basic = joblib.load("model/tfidf_vectorizer.pkl")
    BASIC_MODEL_LOADED = True
except Exception:
    BASIC_MODEL_LOADED = False

try:
    model_enhanced = joblib.load("model/phishing_model_enhanced.pkl")
    vectorizer_enhanced = joblib.load("model/tfidf_vectorizer_enhanced.pkl")
    feature_metadata = joblib.load("model/feature_metadata_enhanced.pkl")
    ENHANCED_MODEL_LOADED = True
except Exception:
    ENHANCED_MODEL_LOADED = False

# ── URL helpers ────────────────────────────────────────────────────────────────

def _extract_urls(text):
    if not text:
        return []
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, str(text))

def _count_urls(text):
    return len(_extract_urls(text))

def _has_suspicious_url(text):
    """
    Detect genuinely suspicious URLs.
    Deliberately EXCLUDES amazonaws.com / azurewebsites.net because
    many legitimate SaaS products (Notion, Dropbox, etc.) host assets there.
    """
    urls = _extract_urls(text)
    suspicious_patterns = [
        # URL shorteners (Expanded list)
        r'(bit\.ly|tinyurl\.com|shorturl\.at|goo\.gl|t\.co|tiny\.cc|is\.gd|buff\.ly|adf\.ly|bit\.do|mcaf\.ee|lnkd\.in|ow\.ly)/[a-z0-9]+',
        # Raw IP addresses used as host
        r'https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',
        # Suspicious TLDs (Truly high-risk only to avoid newsletter FPs)
        r'\.(tk|ml|ga|cf|gq|xyz|top|pw|loan|bid|date|win|icu|buzz|click|work|men|zip|mov|live|best|email|help|support)([/?#]|$)',
        # Lookalike keyword-dash domains
        r'(paypal|amazon|apple|microsoft|google|netflix|facebook|instagram|notion|dropbox|github|bank|secure|signin|verify|update|account|login|password|recovery|wallet|coinbase|binance|blockchain)-[a-z0-9]',
        # Verification portals (High risk in phishing)
        r'secure-verification|account-update|login-portal|verify-identity|activity-confirm',
        # Redirect/Ref parameters (common in phishing)
        r'(\?|&)(url|redirect|goto|link|ref|source|target|to)=http',
        # Base64 / heavily obfuscated path
        r'[a-zA-Z0-9+/]{40,}={0,2}',
    ]
    for url in urls:
        u_low = url.lower()
        # Exclusion for known safe cloud hosts
        if any(d in u_low for d in ['amazonaws.com', 'azurewebsites.net', 'googleusercontent.com', 'githubusercontent.com']):
            continue
        for pattern in suspicious_patterns:
            if re.search(pattern, u_low):
                return 1
    return 0

def _build_text(subject, body):
    s = subject or ""
    b = body or ""
    return f"{s}\n{b}".strip()

# ── Extended list of known-legitimate sending domains ─────────────────────────

KNOWN_LEGIT_DOMAINS = {
    # Big Tech
    'amazon.com', 'google.com', 'microsoft.com', 'apple.com', 'meta.com',
    'facebook.com', 'instagram.com', 'twitter.com', 'x.com', 'linkedin.com',
    'github.com', 'gitlab.com', 'stackoverflow.com', 'adobe.com', 'salesforce.com',
    'oracle.com', 'ibm.com', 'intel.com', 'cisco.com', 'hp.com', 'dell.com',
    # Streaming / Media
    'netflix.com', 'spotify.com', 'youtube.com', 'twitch.tv', 'hulu.com', 'disneyplus.com',
    'hbo.com', 'paramountplus.com', 'audible.com', 'medium.com', 'nytimes.com', 'wsj.com',
    # Finance / E-commerce / Payments
    'paypal.com', 'stripe.com', 'chase.com', 'bank.com', 'shopify.com',
    'ebay.com', 'etsy.com', 'wise.com', 'revolut.com', 'payoneer.com', 'square.com',
    'venmo.com', 'zellepay.com', 'mastercard.com', 'visa.com', 'americanexpress.com',
    'wellsfargo.com', 'bankofamerica.com', 'fidelity.com', 'schwab.com',
    # SaaS / Productivity / Collaboration
    'slack.com', 'zoom.us', 'notion.so', 'dropbox.com', 'box.com',
    'atlassian.com', 'jira.com', 'confluence.com', 'trello.com',
    'asana.com', 'monday.com', 'airtable.com', 'clickup.com',
    'figma.com', 'canva.com', 'miro.com', 'basecamp.com', 'evernote.com',
    'calendly.com', 'typeform.com', 'surveymonkey.com', 'docusign.com', 'hello-sign.com',
    # Ride-sharing / Delivery / Logistics
    'bolt.eu', 'bolt.com', 'uber.com', 'uber.com.eu', 'glovoapp.com', 'jumia.com',
    'jumia.co.ke', 'copia.co.ke', 'zuku.co.ke', 'safaricom.co.ke', 'safaricom.com',
    'airtel.com', 'kplc.co.ke', 'fedex.com', 'ups.com', 'dhl.com',
    # Communication / Mail / Marketing
    'mailchimp.com', 'sendgrid.net', 'sendgrid.com', 'mailgun.com',
    'postmarkapp.com', 'sparkpostmail.com', 'klaviyo.com',
    'constantcontact.com', 'hubspot.com', 'intercom.io', 'intercom.com',
    'zendesk.com', 'freshdesk.com', 'crisp.chat', 'frontapp.com',
    'mail.ru', 'outlook.com', 'hotmail.com', 'yahoo.com', 'icloud.com',
    # Recruiting / Jobs / HR
    'linkedin.com', 'lever.co', 'greenhouse.io', 'workday.com',
    'taleo.net', 'smartrecruiters.com', 'micro1.ai', 'breezy.hr',
    'recruitee.com', 'ashbyhq.com', 'dover.com', 'indeed.com', 'glassdoor.com',
    'ziprecruiter.com', 'monster.com', 'careerbuilder.com',
    # Cloud / Hosting / DevOps
    'heroku.com', 'vercel.com', 'netlify.com', 'render.com',
    'digitalocean.com', 'linode.com', 'cloudflare.com', 'aws.amazon.com',
    'azure.microsoft.com', 'firebase.google.com', 'sentry.io', 'datadoghq.com',
    'mongodb.com', 'redis.com', 'supabase.com', 'planetscale.com',
    # Travel / Logistics
    'emirates.com', 'booking.com', 'airbnb.com', 'expedia.com',
    'tripadvisor.com', 'skyscanner.com', 'uber.com', 'lyft.com',
    'delta.com', 'united.com', 'southwest.com', 'marriott.com', 'hilton.com',
    # Education / Study / Learning
    'studyportals.com', 'studyportalsmail.com', 'coursera.org',
    'udemy.com', 'edx.org', 'khanacademy.org', 'duolingo.com',
    'skillshare.com', 'pluralsight.com', 'linkedin.com/learning',
    # Other common / trusted services
    'eventbrite.com', 'meetup.com', 'bitbucket.org', 'docker.com',
    'npmjsw.com', 'pypi.org', 'anaconda.com', 'unity.com',
}

def _is_safe_tld(sender_addr):
    """Check if the sender's domain has an inherently high-trust TLD."""
    if not sender_addr:
        return False
    domain = sender_addr.split('@')[-1].lower().strip()
    # Note: .org is excluded as it is not restricted and frequently used in phishing.
    return any(domain.endswith(tld) for tld in ['.gov', '.edu', '.mil', '.ac.uk', '.int', '.go.ke', '.ac.ke'])

def _sender_is_known_legit(sender_addr, body=None):
    """
    Return True if the sender's domain is in KNOWN_LEGIT_DOMAINS
    OR if the sender domain matches the primary link domains in the body.
    """
    if not sender_addr:
        return False
    
    # 1. Check inherently safe TLDs
    if _is_safe_tld(sender_addr):
        return True
        
    domain = sender_addr.split('@')[-1].lower().strip()
    parts = domain.split('.')
    
    # Check all possible parent domains (e.g. kenya.rides-marketing.bolt.eu -> bolt.eu)
    candidates = {domain}
    for i in range(1, len(parts)):
        candidates.add('.'.join(parts[i:]))

    # 2. Check hardcoded reputable list
    if candidates & KNOWN_LEGIT_DOMAINS:
        return True

    # 3. Brand Matching Heuristic: Do the links in the body match the sender domain?
    if body:
        from backend.policy import extract_link_domains
        link_domains = extract_link_domains(body)
        if link_domains:
            # If any link domain matches any part of the sender domain, or is reputable
            for l_dom in link_domains:
                l_parts = l_dom.split('.')
                l_candidates = {l_dom}
                for i in range(1, len(l_parts)):
                    l_candidates.add('.'.join(l_parts[i:]))
                
                # If a link is reputable, or matches sender domain
                if (l_candidates & KNOWN_LEGIT_DOMAINS) or (l_candidates & candidates):
                    return True

    return False

def _has_urgency(text):
    if not text: return False
    # Flag high-pressure urgency patterns common in phishing
    # We distinguish between "high pressure" and "standard corporate notice"
    high_pressure = [
        r'(verify your account now|confirm your identity immediately|unauthorized access detected)',
        r'(action required: suspended|account locked: verify|security alert: unauthorized)',
        r'(unusual login attempt|new device|another location)',
        r'(password (is scheduled to )?expire(s)? (today|in \d+ (hour|min)))', # "today" is high pressure, "3 days" is standard
        r'(update your password immediately|reset your credentials (now|immediately))',
        r'(access to .* will be (temporarily )?restricted)',
        r'(prize winner|inheritance claim|lottery winnings|btc reward)',
        r'(final notice|last chance|urgent:? action needed)',
        r'(restore full access|verification portal|suspension of email)',
    ]
    t_low = text.lower()
    for pattern in high_pressure:
        if re.search(pattern, t_low):
            return True
    return False

# ── Main predictor ─────────────────────────────────────────────────────────────

def predict_email(subject, body, sender=None):
    raw_text = _build_text(subject, body)
    cleaned_text = clean_email(raw_text)

    probs = []

    if BASIC_MODEL_LOADED:
        X_basic = vectorizer_basic.transform([cleaned_text])
        probs.append(model_basic.predict_proba(X_basic)[0][1])

    if ENHANCED_MODEL_LOADED:
        X_text_tfidf = vectorizer_enhanced.transform([cleaned_text]).toarray()
        expected_engineered = feature_metadata.get('engineered_features', [])

        if expected_engineered:
            url_count = _count_urls(raw_text)
            has_susp_url = _has_suspicious_url(raw_text)
            email_length = len(raw_text)
            feat_map = {
                'url_count': url_count,
                'has_suspicious_url': has_susp_url,
                'email_length': email_length,
                'char_count_uppercase': sum(1 for c in raw_text if c.isupper()),
                'exclamation_count': raw_text.count('!'),
                'question_count': raw_text.count('?'),
            }
            engineered_vals = np.array([[feat_map.get(f, 0) for f in expected_engineered]])
            X_combined = np.hstack([X_text_tfidf, engineered_vals])
            probs.append(model_enhanced.predict_proba(X_combined)[0][1])
        else:
            probs.append(model_enhanced.predict_proba(X_text_tfidf)[0][1])

    # Ensemble: Conservative averaging
    if not probs:
        phishing_proba = 0.5
    elif len(probs) == 2:
        # Balanced ensemble
        phishing_proba = (probs[0] * 0.4) + (probs[1] * 0.6)
    else:
        phishing_proba = probs[0]

    # ── Heuristic adjustments ──────────────────────────────────────────────────
    url_count = _count_urls(raw_text)
    has_susp = _has_suspicious_url(raw_text)
    has_urgent = _has_urgency(raw_text)

    sender_addr = extract_email_address(sender)
    # Pass body to check link-sender consistency
    is_legit_brand = _sender_is_known_legit(sender_addr, body=body)
    trusted = is_trusted_sender(sender)

    # 1. Safety Signals (The most important for reducing False Positives)
    if is_legit_brand:
        # Known brand or consistent domain links
        phishing_proba *= 0.35
    elif trusted:
        phishing_proba *= 0.35
    
    # Newsletter check
    is_newsletter = any(w in raw_text.lower() for w in ['unsubscribe', 'view in browser', 'privacy policy'])
    if is_newsletter and not has_susp:
        phishing_proba *= 0.6

    if url_count == 0:
        # No links. Phishing usually requires a link or attachment.
        # However, if it's highly urgent or looks like IT support, don't reduce as much.
        is_it_impersonation = any(w in raw_text.lower() for w in ['it support', 'it department', 'service desk', 'system administrator', 'it service desk', 'microsoft 365 services'])
        
        if has_urgent or is_it_impersonation:
            # Urgent/IT text without links is highly suspicious (could be spear phishing)
            if phishing_proba < 0.85:
                phishing_proba *= 1.0  # No reduction for urgent IT mail
            else:
                phishing_proba *= 1.0
        else:
            # Non-urgent text without links is likely safe
            if phishing_proba < 0.85:
                phishing_proba *= 0.4
            else:
                phishing_proba *= 0.7

    # 2. Risk Signals (Additive but conservative)
    if has_susp and not is_legit_brand and not trusted:
        # Only boost if it's NOT a recognized brand
        phishing_proba = min(0.99, phishing_proba + 0.25)
    
    if has_urgent and not is_legit_brand and not trusted:
        # Check for specific high-risk phishing themes
        t_low = raw_text.lower()
        if 'password' in t_low and ('expire' in t_low or 'update' in t_low or 'reset' in t_low):
            phishing_proba = min(0.98, phishing_proba + 0.35) # High boost for password phishing
        elif 'login attempt' in t_low or 'new device' in t_low or 'unusual activity' in t_low:
            phishing_proba = min(0.98, phishing_proba + 0.35) # High boost for login phishing
        else:
            phishing_proba = min(0.98, phishing_proba + 0.20)
            
    if has_urgent and url_count > 0 and not is_legit_brand and not trusted:
        # Urgency + Link = High risk
        phishing_proba = min(0.99, phishing_proba + 0.15)

    # 3. High-Link Density Penalty (Only for unverified senders)
    if url_count > 10 and not is_legit_brand and not trusted and not is_newsletter:
        phishing_proba = min(0.99, phishing_proba + 0.15)

    # 4. Keyword-based override for extremely obvious phishing
    # Check for direct impersonation of security/support in unverified mail
    if url_count > 0 and not is_legit_brand and not trusted:
        suspicious_keywords = ['verify now', 'click here', 'login now', 'confirm activity', 'action required']
        if any(kw in raw_text.lower() for kw in suspicious_keywords):
            # Only override if the ML model is already somewhat suspicious (>25%)
            if phishing_proba > 0.25:
                phishing_proba = max(phishing_proba, 0.70)
        
        # Check for impersonation of high-value targets
        brand_impersonation = ['paypal', 'amazon', 'microsoft', 'google', 'apple', 'netflix', 'bank', 'binance', 'coinbase']
        if any(brand in raw_text.lower() for brand in brand_impersonation):
            # If the sender is NOT that brand but mentions it in the text with a link
            sender_domain = sender_addr.split('@')[-1].lower() if sender_addr else ""
            if not any(brand in sender_domain for brand in brand_impersonation):
                phishing_proba = min(0.99, phishing_proba + 0.20)

    # Clamp to [0, 1]
    phishing_proba = max(0.0, min(1.0, phishing_proba))

    # ── Threshold & allowlist logic ────────────────────────────────────────────
    threshold = get_threshold()
    links_trusted = are_links_trusted(body, sender=sender)
    allowlist_mode = get_allowlist_mode()
    trusted_threshold = get_trusted_sender_threshold()

    if links_trusted and allowlist_mode == "smart":
        if sender_addr:
            allowlist_mode = "override"

    if trusted and allowlist_mode == "smart":
        allowlist_mode = "override" if links_trusted else "raise_threshold"

    if trusted and allowlist_mode == "raise_threshold":
        threshold = max(threshold, trusted_threshold)

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
        "links_trusted": links_trusted,
        "allowlist_mode": allowlist_mode,
    }

# Export for explain.py — always use the basic model for explainability
# (clean linear coef_ weights, correctly aligned with its own vectorizer)
model = model_basic if BASIC_MODEL_LOADED else model_enhanced
vectorizer = vectorizer_basic if BASIC_MODEL_LOADED else vectorizer_enhanced