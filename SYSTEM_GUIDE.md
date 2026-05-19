# PhishGuard Operational Guide: Deployment & System Interaction

## 1. System Overview
PhishGuard is a full-stack phishing detection platform. It is designed to be deployed as a local or private cloud service, allowing users to monitor multiple email accounts through a single, secure dashboard.

## 2. Component Architecture & Data Flow

### 2.1 Backend Services (`api.py`)
The backend is a FastAPI application that serves as the central nervous system.
- **Communication Protocol**: RESTful API over HTTP.
- **Primary Responsibility**: Orchestrating the flow between the IMAP fetchers, the detection engine, and the SQLite database.
- **Security**: Database interactions are managed via SQLAlchemy ORM to prevent SQL injection.

### 2.2 Forensic Detection Engine (`backend/predictor.py`)
This is the core analytical component. It performs:
1. **Neural Inference**: Running the `TF-IDF` vectorizer and `Logistic Regression` / `Ensemble` models.
2. **Heuristic Forensics**: Real-time regex scanning of URLs and sender metadata.
3. **Logic Synthesis**: Applying safety and risk multipliers to reach a final "Risk Score".

### 2.3 IMAP Integration Layer (`backend/email_receiver.py`)
A highly optimized fetching service:
- **Fast-Scan Deduplication**: Fetches headers only (`Message-ID`) first. If the ID exists in the local database, the system skips the email instantly.
- **Batch Processing**: Downloads and analyzes emails in chunks of 25 to optimize network throughput and minimize IMAP session timeouts.

## 3. Operational Workflow

### 3.1 Initial Deployment
1. **Dependency Installation**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Database Initialization**: 
   The system automatically creates `phishing.db` on the first run.
3. **Starting the Service**:
   ```bash
   python api.py
   ```
Those steps activate the backend engine

To activate the user interface follow this steps:
1. Navigate to the frontend folder
```bash
cd frontend
```
2. Start the frontend
```bash
npm start 
```
OR 
```bash
npm run dev
```


### 3.2 Adding & Syncing Accounts
1. **Authentication**: Users must provide an **App Password** for Gmail accounts (standard passwords will be rejected by Google's IMAP).
2. **Synchronization**: 
   - When "Sync Emails" is clicked, the system targets the 500 most recent emails.
   - It performs the "Fast-Scan" to identify only *new* messages.
   - New messages are batch-fetched, analyzed by the `predictor`, and stored.

### 3.3 The Reclassification Workflow
- **When to use**: After updating the `KNOWN_LEGIT_DOMAINS` list in `predictor.py` or retraining the models.
- **Mechanism**: The system iterates through every email in the database and re-runs the full neural-heuristic analysis pipeline, updating scores and folders without re-downloading data.

## 4. Troubleshooting & Maintenance

- **Port Conflicts**: The API automatically tries ports 8000-8003 if the default is occupied.
- **Database Migrations**: The system includes an `_ensure_sqlite_columns()` helper to automatically add new columns (like `message_id`) to existing databases.
- **Performance Logs**: Check the console output for "⚡ Checking for new messages" and "🔄 Progress" logs to monitor sync speed.
