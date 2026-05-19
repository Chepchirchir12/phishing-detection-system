import sys
import os
import time
import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime

# Add root to path to import modules if needed
sys.path.append(os.getcwd())

API_URL = "http://localhost:8000"

def log_test(name, status, details=""):
    color = "\033[92m" if status == "PASS" else "\033[91m"
    reset = "\033[0m"
    print(f"{color}[{status}]{reset} {name} {details}")

def run_system_tests():
    print("\n" + "="*50)
    print("PHISHGUARD SYSTEM STRESS TEST (20+ SCENARIOS)")
    print("="*50 + "\n")

    # 1. API HEALTH CHECK
    try:
        res = requests.get(f"{API_URL}/")
        log_test("API Health Check", "PASS" if res.status_code == 200 else "FAIL")
    except:
        log_test("API Health Check", "FAIL", "(Is api.py running?)")
        return

    # 2. ACCOUNT LISTING
    res = requests.get(f"{API_URL}/accounts")
    accounts = res.json()
    log_test("Account Listing", "PASS" if len(accounts) > 0 else "FAIL", f"({len(accounts)} found)")

    # 3. STATS INTEGRITY
    res = requests.get(f"{API_URL}/stats")
    stats = res.json()
    log_test("Global Stats Integrity", "PASS" if "total" in stats else "FAIL")

    # 4. PREDICTION LOGIC TESTS (20 SCENARIOS)
    from backend.predictor import predict_email
    
    test_cases = [
        # --- PERSONAL EMAILS (Should be Legitimate) ---
        {"s": "Lunch?", "b": "Wanna grab a burger at 12?", "sender": "friend@gmail.com", "expected": "Legitimate", "desc": "Simple personal text"},
        {"s": "Meeting Notes", "b": "Here are the notes from today. We need to finish the project by Friday.", "sender": "boss@work.com", "expected": "Legitimate", "desc": "Work email no links"},
        {"s": "Your Amazon Order", "b": "Your order #123 has shipped. Track it here: https://amazon.com/track", "sender": "auto-confirm@amazon.com", "expected": "Legitimate", "desc": "Legit brand with legit link"},
        {"s": "Hey from Mom", "b": "Call me when you can!", "sender": "mom@gmail.com", "expected": "Legitimate", "desc": "Trusted sender text"},
        {"s": "Re: Dinner", "b": "The usual place sounds good. See you then!", "sender": "partner@gmail.com", "expected": "Legitimate", "desc": "Reply chain"},
        {"s": "Flight Confirmation", "b": "Your flight to NY is confirmed. Seat 12A.", "sender": "booking@airline.com", "expected": "Legitimate", "desc": "Travel info"},
        {"s": "New Follower", "b": "Someone followed you on Twitter.", "sender": "notify@twitter.com", "expected": "Legitimate", "desc": "Social notification"},
        {"s": "Weekend trip", "b": "I'm thinking of going to the mountains. You in?", "sender": "buddy@gmail.com", "expected": "Legitimate", "desc": "Casual inquiry"},
        {"s": "Project Update", "b": "The client approved the design. Let's move to dev.", "sender": "lead@company.com", "expected": "Legitimate", "desc": "Professional update"},
        {"s": "Gym membership", "b": "Your monthly payment was successful.", "sender": "billing@gym.com", "expected": "Legitimate", "desc": "Receipt"},
        
        # --- PHISHING EMAILS (Should be Phishing) ---
        {"s": "URGENT: Account Locked", "b": "Click here to unlock your bank account: http://192.168.1.1/login", "sender": "security@bank-verify.tk", "expected": "Phishing", "desc": "IP address link"},
        {"s": "Win a Prize!", "b": "You won a $1000 gift card! Claim here: https://bit.ly/free-money-now", "sender": "rewards@prize-win.top", "expected": "Phishing", "desc": "Shortened link + .top TLD"},
        {"s": "Verify Your Identity", "b": "Unauthorized login attempt detected. Secure your account now: https://secure-login-amazon.xyz", "sender": "alert@amazon-security.net", "expected": "Phishing", "desc": "Brand impersonation .xyz"},
        {"s": "Action Required: Tax Refund", "b": "Your tax refund is ready. Submit details: http://gov-refund-portal.ml/apply", "sender": "refund@irs-gov.org", "expected": "Phishing", "desc": "Government impersonation .ml"},
        {"s": "Password Reset Requested", "b": "If you didn't request this, click here to cancel: http://verify-account-portal.buzz/cancel", "sender": "no-reply@security-center.com", "expected": "Phishing", "desc": "Security lure .buzz"},
        {"s": "Invoice Overdue", "b": "Please pay your invoice immediately: http://malicious-file-download.xyz/invoice.pdf", "sender": "billing@office-supplies.net", "expected": "Phishing", "desc": "Urgency lure + .xyz"},
        {"s": "Internal Document Shared", "b": "A document has been shared with you: https://docs.google.com.secure-view.tk/doc123", "sender": "colleague@company.com", "expected": "Phishing", "desc": "Subdomain spoofing"},
        {"s": "System Upgrade", "b": "Upgrade your email quota here: http://quota-increase.cf/login", "sender": "admin@it-support.com", "expected": "Phishing", "desc": "IT support lure .cf"},
        {"s": "Netflix: Payment Declined", "b": "Update your payment method to keep watching: https://netflix-update-billing.icu", "sender": "support@netflix-mail.com", "expected": "Phishing", "desc": "Subscription lure .icu"},
        {"s": "PayPal: Suspicious Activity", "b": "Your account is restricted. Verify here: https://paypal-verification-center.ga", "sender": "service@paypal-alerts.com", "expected": "Phishing", "desc": "Financial lure .ga"},
    ]

    pass_count = 0
    start_time = time.time()
    
    print(f"\n--- Running {len(test_cases)} Classification Tests ---")
    for i, tc in enumerate(test_cases):
        res = predict_email(tc["s"], tc["b"], sender=tc["sender"])
        actual = res["label"]
        if actual == tc["expected"]:
            log_test(f"Test #{i+1:02}", "PASS", f"[{tc['desc']}] -> {actual} ({res['risk_score']})")
            pass_count += 1
        else:
            log_test(f"Test #{i+1:02}", "FAIL", f"[{tc['desc']}] Expected {tc['expected']}, got {actual} ({res['risk_score']})")

    end_time = time.time()
    avg_speed = (end_time - start_time) / len(test_cases)
    
    print(f"\nResults: {pass_count}/{len(test_cases)} Passed")
    print(f"Average Inference Speed: {avg_speed*1000:.2f}ms per email")

    # 5. BOTTLENECK ANALYSIS: DATABASE SCALABILITY
    print("\n--- Bottleneck Analysis: Database Querying ---")
    start_db = time.time()
    res = requests.get(f"{API_URL}/emails?limit=1000")
    db_time = time.time() - start_db
    log_test("DB Fetch (All Emails)", "PASS" if db_time < 0.5 else "WARN", f"{db_time:.3f}s")

    # 6. BOTTLENECK ANALYSIS: EXPLAINABILITY (XAI)
    print("\n--- Bottleneck Analysis: XAI Generation ---")
    if len(accounts) > 0:
        res = requests.get(f"{API_URL}/emails")
        emails_list = res.json()
        if emails_list:
            target_id = emails_list[0]["id"]
            start_xai = time.time()
            res = requests.get(f"{API_URL}/explain/{target_id}")
            xai_time = time.time() - start_xai
            log_test("XAI Generation Speed", "PASS" if xai_time < 0.2 else "WARN", f"{xai_time:.3f}s")

    print("\n" + "="*50)
    print("STRESS TEST COMPLETE")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_system_tests()
