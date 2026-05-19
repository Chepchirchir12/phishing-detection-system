import os
import pandas as pd

"""
Utility script: quick peek at datasets in ./datasets.

Run:
  python main.py
"""

folder_path = os.path.join(os.path.dirname(__file__), "datasets")

# 2. List all files in the folder
if not os.path.isdir(folder_path):
    raise SystemExit(f"Datasets folder not found: {folder_path}")

all_files = os.listdir(folder_path)
print("Files in folder:", all_files)

# 3. Load all CSV files into a dictionary
datasets = {}
for f in all_files:
    if f.endswith('.csv'):  # only CSV files
        file_path = os.path.join(folder_path, f)
        datasets[f] = pd.read_csv(file_path)

# 4. Display the first 5 rows of each dataset
for name, df in datasets.items():
    print(f"\nDataset: {name}")
    print(df.head())

