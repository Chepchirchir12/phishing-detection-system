import pandas as pd
import numpy as np
import os
from backend.predictor import predict_email

def run_tests(sample_size=500, safe_ratio=0.8):
    print(f"Starting comprehensive test of {sample_size} emails...")
    
    # Load the modern dataset
    dataset_path = "datasets/phishing_legit_dataset_KD_10000.csv"
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset not found at {dataset_path}")
        return
        
    df = pd.read_csv(dataset_path)
    
    # Separate safe and phishing
    safe_df = df[df['label'] == 0]
    phish_df = df[df['label'] == 1]
    
    num_safe = int(sample_size * safe_ratio)
    num_phish = sample_size - num_safe
    
    # Sample with replacement if dataset is smaller than requested (not the case here)
    test_safe = safe_df.sample(n=min(len(safe_df), num_safe), random_state=42)
    test_phish = phish_df.sample(n=min(len(phish_df), num_phish), random_state=42)
    
    test_set = pd.concat([test_safe, test_phish]).sample(frac=1, random_state=42) # Shuffle
    
    results = []
    
    print(f"Testing {len(test_set)} emails ({len(test_safe)} safe, {len(test_phish)} phishing)...")
    
    for idx, row in test_set.iterrows():
        text = row['text']
        true_label = "Phishing" if row['label'] == 1 else "Legitimate"
        
        # Extract a subject-like first line and body
        lines = text.split('\n', 1)
        subject = lines[0] if len(lines) > 0 else ""
        body = lines[1] if len(lines) > 1 else text
        
        # Predict
        prediction = predict_email(subject, body)
        pred_label = prediction['label']
        risk_score = prediction['risk_score']
        
        results.append({
            'text': text[:100].replace('\n', ' '),
            'true_label': true_label,
            'pred_label': pred_label,
            'risk_score': float(risk_score.replace('%', '')),
            'correct': true_label == pred_label
        })

    # Calculate metrics
    results_df = pd.DataFrame(results)
    accuracy = results_df['correct'].mean()
    
    # False Positives (Safe misclassified as Phishing)
    safe_indices = results_df['true_label'] == "Legitimate"
    false_positives = results_df[safe_indices & (results_df['pred_label'] == "Phishing")]
    fpr = len(false_positives) / safe_indices.sum() if safe_indices.sum() > 0 else 0
    
    # False Negatives (Phishing misclassified as Safe)
    phish_indices = results_df['true_label'] == "Phishing"
    false_negatives = results_df[phish_indices & (results_df['pred_label'] == "Legitimate")]
    fnr = len(false_negatives) / phish_indices.sum() if phish_indices.sum() > 0 else 0
    
    print("\n" + "="*40)
    print("COMPREHENSIVE TEST RESULTS")
    print("="*40)
    print(f"Total Samples:    {len(results_df)}")
    print(f"Accuracy:         {accuracy:.2%}")
    print(f"False Positives:  {len(false_positives)} ({fpr:.2%})")
    print(f"False Negatives:  {len(false_negatives)} ({fnr:.2%})")
    print("="*40)
    
    if len(false_positives) > 0:
        print("\nTOP FALSE POSITIVES (Misclassified Safe Emails):")
        for idx, fp in false_positives.head(5).iterrows():
            print(f"- Risk: {fp['risk_score']}% | Text: {fp['text']}...")
            
    if len(false_negatives) > 0:
        print("\nTOP FALSE NEGATIVES (Missed Phishing Emails):")
        for idx, fn in false_negatives.head(5).iterrows():
            print(f"- Risk: {fn['risk_score']}% | Text: {fn['text']}...")

if __name__ == "__main__":
    run_tests()
