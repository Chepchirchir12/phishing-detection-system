import sys
import os
import time
import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime

# Add root to path
sys.path.append(os.getcwd())

from backend.predictor import predict_email

def log_test(name, status, details=""):
    color = "\033[92m" if status == "PASS" else "\033[91m"
    reset = "\033[0m"
    print(f"{color}[{status}]{reset} {name} {details}")

def run_60_tests():
    print("\n" + "="*60)
    print("PHISHGUARD EXTENSIVE TEST SUITE (60+ SCENARIOS)")
    print("="*60 + "\n")

    test_cases = [
        # --- PERSONAL/LEGITIMATE (Expected: Legitimate) ---
        {"s": "Dinner tonight?", "b": "Hey, are we still on for dinner at 7?", "sender": "friend@gmail.com", "expected": "Legitimate", "desc": "Simple personal"},
        {"s": "Meeting Notes", "b": "Here are the notes from the sync today.", "sender": "colleague@work.com", "expected": "Legitimate", "desc": "Work email"},
        {"s": "Your Amazon Order #123", "b": "Thank you for your order. Track it here: https://www.amazon.com/gp/your-account/order-history", "sender": "order-update@amazon.com", "expected": "Legitimate", "desc": "Amazon legit"},
        {"s": "Netflix: New Login", "b": "A new device logged into your account. If this was you, ignore this. https://www.netflix.com/YourAccount", "sender": "info@netflix.com", "expected": "Legitimate", "desc": "Netflix legit"},
        {"s": "Google: Security Alert", "b": "Your account was accessed from a new device. Check activity: https://myaccount.google.com/notifications", "sender": "no-reply@accounts.google.com", "expected": "Legitimate", "desc": "Google legit"},
        {"s": "LinkedIn: New Connection", "b": "John Doe wants to connect with you. View profile: https://www.linkedin.com/in/johndoe", "sender": "notifications@linkedin.com", "expected": "Legitimate", "desc": "LinkedIn legit"},
        {"s": "PayPal: Payment Received", "b": "You received $50.00 from Jane. Details: https://www.paypal.com/activity", "sender": "service@paypal.com", "expected": "Legitimate", "desc": "PayPal legit"},
        {"s": "GitHub: Sign-in from new device", "b": "A new public key was added. https://github.com/settings/keys", "sender": "noreply@github.com", "expected": "Legitimate", "desc": "GitHub legit"},
        {"s": "Dropbox: File Shared", "b": "Sarah shared 'Project.pdf' with you. View: https://www.dropbox.com/s/12345/Project.pdf", "sender": "no-reply@dropbox.com", "expected": "Legitimate", "desc": "Dropbox legit"},
        {"s": "StudyPortals: New Program", "b": "Check out these new masters programs: https://accounts.studyportalsmail.com/redirect?id=123", "sender": "info@studyportals.com", "expected": "Legitimate", "desc": "StudyPortals legit"},
        {"s": "Flight Confirmation", "b": "Your flight EK123 is confirmed. Check in: https://www.emirates.com/checkin", "sender": "booking@emirates.com", "expected": "Legitimate", "desc": "Travel legit"},
        {"s": "Mom: Happy Birthday", "b": "Hope you have a great day! Love, Mom.", "sender": "mom@gmail.com", "expected": "Legitimate", "desc": "Family"},
        {"s": "Dad: Grocery list", "b": "Don't forget the milk and bread.", "sender": "dad@yahoo.com", "expected": "Legitimate", "desc": "Family"},
        {"s": "Rent Payment", "b": "Your rent for May has been received. Thank you.", "sender": "landlord@property.com", "expected": "Legitimate", "desc": "Rent"},
        {"s": "Dentist Appointment", "b": "Reminder: You have an appointment tomorrow at 10 AM.", "sender": "reception@dentist-clinic.com", "expected": "Legitimate", "desc": "Medical"},
        {"s": "Bank Statement", "b": "Your April statement is now available in the portal. https://www.chase.com", "sender": "online-banking@chase.com", "expected": "Legitimate", "desc": "Bank legit"},
        {"s": "Slack: You have messages", "b": "You have 3 unread messages in #general. Open Slack: https://slack.com", "sender": "notifications@slack.com", "expected": "Legitimate", "desc": "Slack legit"},
        {"s": "Zoom: Meeting Invitation", "b": "Join Zoom Meeting: https://zoom.us/j/12345678", "sender": "invites@zoom.us", "expected": "Legitimate", "desc": "Zoom legit"},
        {"s": "Apple: Your Receipt", "b": "Thank you for your purchase. Total: $0.99. https://apple.com/bill", "sender": "no_reply@email.apple.com", "expected": "Legitimate", "desc": "Apple legit"},
        {"s": "Spotify: Your Year in Review", "b": "Discover your top songs of 2025. https://www.spotify.com/wrapped", "sender": "no-reply@spotify.com", "expected": "Legitimate", "desc": "Spotify legit"},
        {"s": "Project Deadline", "b": "The final report is due on Friday. Please review.", "sender": "manager@work.com", "expected": "Legitimate", "desc": "Work"},
        {"s": "Weekend BBQ", "b": "Come over for a BBQ this Saturday!", "sender": "neighbor@gmail.com", "expected": "Legitimate", "desc": "Social"},
        {"s": "Code Review Request", "b": "Please review my PR on GitHub.", "sender": "dev-peer@company.com", "expected": "Legitimate", "desc": "Dev"},
        {"s": "Internal Newsletter", "b": "Here is what happened this week at the company.", "sender": "hr@company.com", "expected": "Legitimate", "desc": "Internal"},
        {"s": "System Maintenance", "b": "The server will be down for 2 hours tonight.", "sender": "it-support@company.com", "expected": "Legitimate", "desc": "IT"},
        {"s": "Gym Schedule", "b": "New yoga classes starting next week.", "sender": "info@local-gym.com", "expected": "Legitimate", "desc": "Local"},
        {"s": "Library Book Due", "b": "Your book is due back in 2 days.", "sender": "notifications@city-library.org", "expected": "Legitimate", "desc": "Library"},
        {"s": "Newsletter: Tech Trends", "b": "Read about the latest in AI and robotics.", "sender": "news@tech-insider.com", "expected": "Legitimate", "desc": "Newsletter"},
        {"s": "Order Confirmation", "b": "Your pizza is on the way!", "sender": "orders@dominos.com", "expected": "Legitimate", "desc": "Food"},
        {"s": "Car Service Reminder", "b": "It's time for your annual car service.", "sender": "service@local-garage.com", "expected": "Legitimate", "desc": "Car"},

        # --- PHISHING/MALICIOUS (Expected: Phishing) ---
        {"s": "URGENT: Your account is locked", "b": "Unauthorized login detected. Click here to unlock: http://secure-bank-verify.ga/login", "sender": "security@bank.ga", "expected": "Phishing", "desc": "Bank phishing .ga"},
        {"s": "Netflix: Update Payment", "b": "Your subscription will be cancelled. Update here: http://netflix-billing-update.tk", "sender": "support@netflix-support.com", "expected": "Phishing", "desc": "Netflix phishing .tk"},
        {"s": "Win $1000 Amazon Gift Card", "b": "You have been selected! Claim now: http://bit.ly/free-amazon-prize", "sender": "rewards@prize-winner.xyz", "expected": "Phishing", "desc": "Amazon phishing .xyz"},
        {"s": "PayPal: Unauthorized Transaction", "b": "We detected a $500 payment to a new merchant. Dispute: http://paypal-dispute-center.ml", "sender": "alerts@paypal-security.net", "expected": "Phishing", "desc": "PayPal phishing .ml"},
        {"s": "Action Required: Tax Refund", "b": "Your tax refund of $1200 is ready. Claim here: http://irs-refund-portal.cf", "sender": "tax-refund@irs.gov.cf", "expected": "Phishing", "desc": "IRS phishing .cf"},
        {"s": "Microsoft: Security Alert", "b": "Your Windows license is expiring. Renew now: http://microsoft-license-renewal.gq", "sender": "admin@ms-support.com", "expected": "Phishing", "desc": "Microsoft phishing .gq"},
        {"s": "Dropbox: Shared Document", "b": "You have a new encrypted document. View: http://dropbox-secure-share.tk/doc", "sender": "shared-file@dropbox-docs.com", "expected": "Phishing", "desc": "Dropbox phishing .tk"},
        {"s": "Facebook: Someone tried to login", "b": "If this was not you, secure your account: http://facebook-security-verify.xyz", "sender": "security@fb-login.com", "expected": "Phishing", "desc": "Facebook phishing .xyz"},
        {"s": "Invoice Overdue", "b": "Please pay your invoice #1234 immediately. http://invoice-portal-malicious.buzz/pay", "sender": "billing@office-supplies.net", "expected": "Phishing", "desc": "Invoice phishing .buzz"},
        {"s": "Your Apple ID has been suspended", "b": "Verify your identity to restore access: http://apple-id-verify.icu", "sender": "support@apple-verify.com", "expected": "Phishing", "desc": "Apple phishing .icu"},
        {"s": "Google: Account Recovery", "b": "Reset your password immediately: http://google-account-recovery.top", "sender": "no-reply@google-security.net", "expected": "Phishing", "desc": "Google phishing .top"},
        {"s": "DHL: Delivery Failed", "b": "Your package could not be delivered. Reschedule: http://dhl-package-reschedule.pw", "sender": "delivery@dhl-tracking.com", "expected": "Phishing", "desc": "DHL phishing .pw"},
        {"s": "LinkedIn: Job Invitation", "b": "A recruiter wants to talk to you. View job: http://linkedin-jobs-portal.bid", "sender": "jobs@linkedin-recruit.com", "expected": "Phishing", "desc": "LinkedIn phishing .bid"},
        {"s": "Chase: Unusual Activity", "b": "Verify your card details: http://chase-online-verify.win", "sender": "security@chase-alerts.com", "expected": "Phishing", "desc": "Chase phishing .win"},
        {"s": "Amazon: Suspicious Login", "b": "Secure your account now: http://amazon-security-check.loan", "sender": "no-reply@amazon-alerts.net", "expected": "Phishing", "desc": "Amazon phishing .loan"},
        {"s": "Verify Your Wallet", "b": "Your crypto wallet is at risk. Secure it: http://metamask-verify-seed.xyz", "sender": "support@metamask.io.xyz", "expected": "Phishing", "desc": "Crypto phishing .xyz"},
        {"s": "IT Support: Quota Full", "b": "Upgrade your email quota here: http://email-quota-increase.ga", "sender": "it@company-support.com", "expected": "Phishing", "desc": "IT phishing .ga"},
        {"s": "Zoom: Meeting Recorded", "b": "Download your meeting recording: http://zoom-recording-download.tk", "sender": "no-reply@zoom-us.net", "expected": "Phishing", "desc": "Zoom phishing .tk"},
        {"s": "Employee Survey", "b": "Complete the survey for a $10 bonus: http://employee-survey-portal.cf", "sender": "hr@company-internal.com", "expected": "Phishing", "desc": "HR phishing .cf"},
        {"s": "Package Arrival", "b": "Your package is waiting at the post office. http://usps-package-delivery.ml", "sender": "notify@usps-tracking.net", "expected": "Phishing", "desc": "USPS phishing .ml"},
        {"s": "Bank Alert: New Payee", "b": "A new payee was added to your account. http://bank-payee-verify.gq", "sender": "alerts@bank-online.com", "expected": "Phishing", "desc": "Bank phishing .gq"},
        {"s": "System Error", "b": "A critical system error occurred. Fix: http://system-fix-portal.buzz", "sender": "admin@it-desk.com", "expected": "Phishing", "desc": "IT phishing .buzz"},
        {"s": "Your membership is expiring", "b": "Renew your membership now: http://membership-renewal.icu", "sender": "billing@gym-members.com", "expected": "Phishing", "desc": "Gym phishing .icu"},
        {"s": "Account Security Review", "b": "Please review your security settings: http://security-review-portal.top", "sender": "no-reply@account-security.net", "expected": "Phishing", "desc": "Security phishing .top"},
        {"s": "Unpaid Parking Ticket", "b": "You have an unpaid fine. Pay here: http://city-fines-portal.pw", "sender": "fines@city-traffic.org", "expected": "Phishing", "desc": "Fine phishing .pw"},
        {"s": "You have a new voicemail", "b": "Listen to your voicemail: http://voicemail-portal-malicious.bid", "sender": "notify@phone-service.net", "expected": "Phishing", "desc": "Voicemail phishing .bid"},
        {"s": "Bonus Payment", "b": "Your quarterly bonus is ready. http://bonus-payment-portal.win", "sender": "payroll@company.com.win", "expected": "Phishing", "desc": "Payroll phishing .win"},
        {"s": "Software Update", "b": "Update your antivirus software now: http://antivirus-update-portal.loan", "sender": "support@antivirus-tech.com", "expected": "Phishing", "desc": "Antivirus phishing .loan"},
        {"s": "Gift from friend", "b": "Someone sent you a gift. Claim: http://gift-claim-portal.ga", "sender": "notify@gifts.com", "expected": "Phishing", "desc": "Gift phishing .ga"},
        {"s": "Subscription Renewal", "b": "Your subscription will renew soon. Cancel: http://cancel-subscription.tk", "sender": "billing@subs-service.com", "expected": "Phishing", "desc": "Subscription phishing .tk"},
    ]

    pass_count = 0
    start_time = time.time()
    
    print(f"--- Running {len(test_cases)} Tests ---")
    for i, tc in enumerate(test_cases):
        res = predict_email(tc["s"], tc["b"], sender=tc["sender"])
        actual = res["label"]
        if actual == tc["expected"]:
            log_test(f"Test #{i+1:02}", "PASS", f"[{tc['desc']}] -> {actual} ({res['risk_score']})")
            pass_count += 1
        else:
            log_test(f"Test #{i+1:02}", "FAIL", f"[{tc['desc']}] Expected {tc['expected']}, got {actual} ({res['risk_score']})")

    end_time = time.time()
    print(f"\nResults: {pass_count}/{len(test_cases)} Passed")
    print(f"Total Time: {end_time - start_time:.2f}s")

if __name__ == "__main__":
    run_60_tests()
