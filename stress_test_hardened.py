import pandas as pd
import numpy as np
import os
import re
from backend.predictor import predict_email

def strip_enron_headers(text):
    if not text or pd.isna(text): return ""
    parts = str(text).split('\n\n', 1)
    return parts[1] if len(parts) > 1 else text

def run_hardened_stress_test(sample_size=1200):
    print("🚀 INITIALIZING HARDENED STRESS TEST (Zero-Tolerance Mode)")
    print("----------------------------------------------------------")
    
    # 1. Load All Datasets
    modern_df = pd.read_csv("datasets/phishing_legit_dataset_KD_10000.csv")
    enron_df = pd.read_csv("datasets/emails.csv", usecols=['message'], nrows=20000)
    old_phish_df = pd.read_csv("datasets/phishing_email.csv")
    
    # 2. Extract specific "Pressure" groups
    
    # Group A: Modern Personal/Business (Safe) - High Priority for 0% FPR
    modern_safe = modern_df[modern_df['label'] == 0].sample(n=400, random_state=1)
    
    # Group B: Enron Corporate (Safe) - Legacy business tone
    enron_safe = enron_df.sample(n=300, random_state=2)
    enron_safe['text'] = enron_safe['message'].apply(strip_enron_headers)
    
    # Group C: Modern Phishing (The real threat)
    modern_phish = modern_df[modern_df['label'] == 1].sample(n=300, random_state=3)
    
    # Group D: Adversarial Synthetics (The "Hard" cases)
    # 1. Safe emails with "Trigger" words (urgent, password, bank, verify)
    adversarial_safe = [
        {"text": "Subject: URGENT: Team meeting moved\n\nHi team, we need to verify the conference room booking. Please update your calendars.", "label": 0},
        {"text": "Subject: Resetting your local workstation password\n\nYour internal system password expires in 3 days. Follow the standard IT portal procedure.", "label": 0},
        {"text": "Subject: Bank statement available\n\nYour monthly statement for account ending in 4421 is now ready for review in your secure document vault.", "label": 0},
        {"text": "Subject: Support ticket #9921 updated\n\nThanks for your patience. We have updated the status of your request regarding the login issue.", "label": 0}
    ] * 25 # 100 samples
    
    # 2. Phishing emails with "Safe" language (friend, catching up, thanks)
    adversarial_phish = [
        {"text": "Subject: Long time no see!\n\nHey friend, catching up would be great. I uploaded some photos from our trip here: https://bit.ly/3xYzLp", "label": 1},
        {"text": "Subject: Thanks for the great lunch\n\nIt was nice meeting you. Here is that document we discussed: https://secure-docs-share.tk/view/992", "label": 1},
        {"text": "Subject: Re: Your recent inquiry\n\nHello, thanks for contacting us. To better assist you, please confirm your identity at our portal: http://192.168.1.1/verify", "label": 1}
    ] * 33 # 99 samples

    adv_safe_df = pd.DataFrame(adversarial_safe)
    adv_phish_df = pd.DataFrame(adversarial_phish)

    # 3. Combine and Conquer
    test_data = []
    for _, r in modern_safe.iterrows(): test_data.append({'text': r['text'], 'label': 0, 'source': 'Modern Safe'})
    for _, r in enron_safe.iterrows(): test_data.append({'text': r['text'], 'label': 0, 'source': 'Enron Safe'})
    for _, r in modern_phish.iterrows(): test_data.append({'text': r['text'], 'label': 1, 'source': 'Modern Phish'})
    for _, r in adv_safe_df.iterrows(): test_data.append({'text': r['text'], 'label': 0, 'source': 'Adversarial Safe'})
    for _, r in adv_phish_df.iterrows(): test_data.append({'text': r['text'], 'label': 1, 'source': 'Adversarial Phish'})

    results = []
    print(f"Total Pressure Samples: {len(test_data)}")
    
    for item in test_data:
        text = item['text']
        true_label = "Phishing" if item['label'] == 1 else "Legitimate"
        
        lines = text.split('\n', 1)
        subject = lines[0] if len(lines) > 0 else ""
        body = lines[1] if len(lines) > 1 else text
        
        # We don't provide a sender to force the model to rely purely on content + URL logic
        prediction = predict_email(subject, body)
        pred_label = prediction['label']
        
        results.append({
            'source': item['source'],
            'true': true_label,
            'pred': pred_label,
            'score': float(prediction['risk_score'].replace('%', '')),
            'correct': true_label == pred_label,
            'text_peek': text[:60].replace('\n', ' ')
        })

    df_res = pd.DataFrame(results)
    
    # Metrics
    accuracy = df_res['correct'].mean()
    
    print("\n" + "█"*60)
    print("FINAL STRESS TEST REPORT")
    print("█"*60)
    print(f"OVERALL ACCURACY: {accuracy:.2%}")
    
    sources = df_res['source'].unique()
    for src in sources:
        sub = df_res[df_res['source'] == src]
        acc = sub['correct'].mean()
        print(f"\n[{src}]")
        print(f"  Accuracy: {acc:.2%}")
        if acc < 1.0:
            failures = sub[~sub['correct']]
            print(f"  Failures: {len(failures)}")
            for _, f in failures.head(3).iterrows():
                print(f"    - [{f['pred']} @ {f['score']}%] {f['text_peek']}...")

    # Critical Breakdown
    fpr = len(df_res[(df_res['true'] == 'Legitimate') & (df_res['pred'] == 'Phishing')])
    fnr = len(df_res[(df_res['true'] == 'Phishing') & (df_res['pred'] == 'Legitimate')])
    
    print("\n" + "-"*40)
    print(f"FALSE POSITIVES (Safe flagged as Phish): {fpr}")
    print(f"FALSE NEGATIVES (Phish flagged as Safe): {fnr}")
    print("-"*40)

if __name__ == "__main__":
    run_hardened_stress_test()
