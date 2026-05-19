# PhishGuard: Advanced Phishing Detection & Forensic Analysis System

PhishGuard is a high-performance, cybersecurity solution designed for real-time phishing detection and email forensic analysis. It utilizes a **Hybrid Intelligence Architecture** that merges calibrated Machine Learning (ML) models with a sophisticated heuristic inference layer and Explainable AI (XAI).

## Key Features

- **Multi-Layered Detection**: Combines TF-IDF based Machine Learning with a deterministic heuristic layer (URL forensics, Brand discovery, Urgency analysis).
- **Explainable AI (XAI)**: Provides human-readable summaries and "Safe Indicators" or "Risk Factors" for every decision.
- **Optimized IMAP Sync**: Fast-scan deduplication and batch processing (50 emails/chunk) for high-speed synchronization.
- **Two-Way Deletion Sync**: Automatically removes local copies of emails that have been deleted from your actual inbox.
- **Real-Time Paste Analysis**: A dedicated portal to manually paste and analyze suspicious emails before they are even opened.
- **Decoupled Architecture**: Modern FastAPI backend and React frontend styled with Tailwind CSS.

## Tech Stack

- **Backend**: FastAPI (Python), SQLAlchemy (ORM), Scikit-learn (ML), Joblib.
- **Frontend**: React.js, Lucide Icons, Tailwind CSS, Axios.
- **Database**: SQLite (Local development ready).
- **ML Models**: Calibrated Logistic Regression and RandomForest ensembles.

---

## Installation & Setup

### 1. Prerequisites
- Python 3.9+
- Node.js & npm
- A Gmail account with an **App Password** enabled (if using Gmail).

### 2. Backend Setup
1. Clone the repository and navigate to the project root.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory (optional, for default accounts):
   ```env
   PHISHGUARD_GMAIL_EMAIL=your-email
   PHISHGUARD_GMAIL_APP_PASSWORD=your-16-char-app-password
   ```
4. Start the FastAPI server:
   ```bash
   python api.py
   ```
   The backend will run on `http://localhost:8000`.

### 3. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the React application:
   ```bash
   npm start
   ```
   The dashboard will open automatically at `http://localhost:3000`.

---

## Usage Guide

1. **Dashboard**: Get an immediate overview of your phishing risk across all connected accounts.
2. **Add Account**: Connect any IMAP-enabled email provider via the sidebar.
3. **Sync Emails**: Click "Sync Emails" to fetch and analyze the latest 500 messages. This process is optimized to skip previously scanned emails.
4. **Analysis Detail**: Click any email to see the **XAI Forensic Report**, which explains why the email was classified as Safe or Phishing.
5. **Paste Email**: Use the lightning bolt icon in the sidebar to manually analyze a suspicious email by pasting its content.
6. **Reclassify All**: If you update the detection engine or models, use this feature to re-analyze your entire local database instantly.

---

## Technical Methodology

PhishGuard analyzes emails through a four-stage sequential pipeline:

1.  **Normalization**: Strips HTML noise and tokenizes text while preserving structural URL data.
2.  **Forensic Heuristics**: Deterministic regex checks for suspicious TLDs (`.zip`, `.tk`), redirect obfuscation, and brand impersonation.
3.  **Neural-Heuristic Synthesis**: Combines ML probability (calibrated via Isotonic Regression) with safety/risk multipliers.
4.  **XAI Synthesis**: Maps mathematical weights to human-readable tokens, filtering out metadata noise to show only the most significant decision drivers.

## Project Structure
- `/backend`: Core detection engine and IMAP logic.
- `/database`: SQLAlchemy models and SQLite setup.
- `/frontend`: React dashboard source code.
- `/model`: Trained ML artifacts and metadata.
- `/xai`: Explainability logic.
- `api.py`: FastAPI server entry point.
- `train_enhanced_model.py`: Training pipeline for the detection models.

